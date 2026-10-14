from __future__ import annotations

import copy
import json
import threading

import pytest

from motorsim.engine_configuration import create, resolve_for_operating_point
from motorsim.exploratory_workflow import (import_exploratory_runs, preflight,
                                            run_exploratory,_run_directory)
from motorsim.integrated_2t import IntegratedEngine2T
from motorsim.mechanical import LossTerm, MechanicalLossModel
from test_integrated_2t import _internal_cycle_fixture

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "results/2t-commercial-core-20261002/fixtures/v1-prime-mesh/fixture_a_prime-mesh-0.json"


def engine_document():
    sample = json.loads(FIXTURE.read_text(encoding="utf-8"))
    native = _internal_cycle_fixture(rpm=3000.0).configuration_dict()
    return create(
        native_configuration=native,
        mechanical_loss_model=MechanicalLossModel((LossTerm(
            "synthetic-ring", "piston_ring", "SYNTHETIC_ASSUMPTION", mep_pa=1200.0),)).to_dict(),
        operating_conditions={"reference_rpm": 3000.0, "load": 1.0,
                              "fuel_id": "synthetic-fixture-fuel", "afr": 49.0},
        provenance={"configuration_source": {"classification": "SYNTHETIC_ASSUMPTION"},
                    "fuel": {"provenance": "SYNTHETIC_ASSUMPTION",
                             "fuel_sha256": sample["fuel_surrogate_snapshot"]["sha256"]}},
        display_name="Exploratory test engine")


def test_preflight_is_no_step_and_resolves_explicit_operating_point():
    document = engine_document()
    effective = resolve_for_operating_point(document, rpm=3200.0)
    native = IntegratedEngine2T.from_configuration_dict(effective["native_configuration"])
    assert native.reference_rpm == 3200.0
    assert document["native_configuration"]["reference_rpm"] == 3000.0
    assert len(effective["source_hashes"]) >= 24
    assert preflight(document, rpm=3200.0, max_cycles=1)["solver_steps"] == 0
    with pytest.raises(ValueError, match="max_cycles"):
        preflight(document, max_cycles=112)
    with pytest.raises(ValueError, match="memory_limit"):
        preflight(document, memory_limit_mib=64)


def test_escape_comparison_example_has_two_distinct_preflighted_solver_configs():
    from motorsim.engine_project import load_project
    example=load_project(ROOT/"examples/projects/dino-2t-exhaust-comparison.dino2t.json")
    original=example["variants"]["Escape original"]
    modified=example["variants"]["Escape modified +20 mm"]
    assert original["native_configuration_sha256"]!=modified["native_configuration_sha256"]
    assert preflight(original,rpm=3000)["status"]=="PASS"
    assert preflight(modified,rpm=3000)["status"]=="PASS"


def test_exploratory_run_cancels_at_step_boundary_and_resumes_audited_checkpoint(tmp_path):
    document = engine_document()
    cancel = threading.Event()
    def progress(row):
        if row["cycle"] == 2 and row["angle_deg"] >= 540.0:
            cancel.set()
    first = run_exploratory(document, project_id="test-project", run_id="cancel-resume",
        artifact_root=tmp_path, rpm=3000.0, max_cycles=2, budget_seconds=600,
        memory_limit_mib=1024, cancel_event=cancel, progress=progress)
    assert first["status"] == "INTERRUPTED_CHECKPOINTED"
    assert first["cycles_completed"] == 1
    resumed = run_exploratory(document, project_id="test-project", run_id="cancel-resume",
        artifact_root=tmp_path, rpm=3000.0, max_cycles=2, budget_seconds=600,
        memory_limit_mib=1024, resume=True)
    assert resumed["cycles_completed"] == 2
    assert resumed["mode"] == "EXPLORATORY"
    assert resumed["scientific_validation"] == "NOT_CLAIMED"
    assert resumed["cycles"][0]["audit"]["recomputed"] is True
    assert resumed["cycles"][0]["audit_method"]=="INTEGRATED_CYCLE_REPLAY_V2_PRE_CYCLE_P7_BASELINE"
    assert resumed["cycles"][0]["conservation"]["mass_residual_kg"] == pytest.approx(0.0, abs=1e-11)
    assert [row["cycle"] for row in resumed["cycles"]]==[1,2]
    assert resumed["cycles"][1]["audit"]["recomputed"] is True
    assert resumed["periodicity"] == "NOT_EVALUATED"
    imported=import_exploratory_runs([tmp_path/"exploratory-workflow-v1"/"test-project"/"cancel-resume"])
    assert len(imported["points"])==2
    assert imported["points"][0]["mode"]=="EXPLORATORY"
    assert imported["points"][0]["hard_gates"]["status"]=="NOT_EVALUATED_EXPLORATORY"
    assert imported["interpolation"]=="NONE"
    result_path=tmp_path/"exploratory-workflow-v1"/"test-project"/"cancel-resume"/"result.json"
    result_bytes=result_path.read_bytes(); result_path.write_bytes(result_bytes+b" ")
    with pytest.raises(ValueError,match="result artifact hash mismatch"):
        import_exploratory_runs([result_path])

    incompatible = copy.deepcopy(document)
    incompatible["operating_conditions"]["reference_rpm"] = 3100.0
    from motorsim.engine_configuration import sha256
    incompatible["native_configuration"]["reference_rpm"] = 3100.0
    incompatible["native_configuration_sha256"] = sha256(incompatible["native_configuration"])
    with pytest.raises(ValueError, match="resume rejected: run identity"):
        run_exploratory(incompatible, project_id="test-project", run_id="cancel-resume",
            artifact_root=tmp_path, rpm=3100.0, max_cycles=1, budget_seconds=600,
            memory_limit_mib=1024, resume=True)


def test_exploratory_runner_rejects_existing_partial_directory_without_resume(tmp_path):
    document = engine_document()
    cancel = threading.Event(); cancel.set()
    result = run_exploratory(document, project_id="p", run_id="run", artifact_root=tmp_path,
        max_cycles=1, budget_seconds=10, cancel_event=cancel)
    assert result["status"] == "INTERRUPTED_CHECKPOINTED"
    with pytest.raises(FileExistsError, match="explicit resume"):
        run_exploratory(document, project_id="p", run_id="run", artifact_root=tmp_path,
            max_cycles=1, budget_seconds=10)


def test_resume_rejects_corrupt_checkpoint_without_overwriting_it(tmp_path):
    document=engine_document(); cancel=threading.Event(); cancel.set()
    run_exploratory(document,project_id="p",run_id="corrupt",artifact_root=tmp_path,
        max_cycles=1,budget_seconds=10,cancel_event=cancel)
    path=tmp_path/"exploratory-workflow-v1"/"p"/"corrupt"/"checkpoint.json"
    original=path.read_bytes(); path.write_bytes(original+b"tamper")
    corrupted=path.read_bytes()
    with pytest.raises(ValueError,match="checkpoint artifact hash mismatch"):
        run_exploratory(document,project_id="p",run_id="corrupt",artifact_root=tmp_path,
            max_cycles=1,budget_seconds=10,resume=True)
    assert path.read_bytes()==corrupted


def test_exploratory_run_lock_rejects_concurrent_or_stale_owner_without_mutation(tmp_path):
    document=engine_document()
    target=_run_directory(tmp_path,"p","locked");target.parent.mkdir(parents=True,exist_ok=True)
    lock=target.parent/".locked.lock";lock.write_text('{"pid":123}',encoding="utf-8")
    with pytest.raises(RuntimeError,match="owns this run lock"):
        run_exploratory(document,project_id="p",run_id="locked",artifact_root=tmp_path)
    assert lock.read_text(encoding="utf-8")== '{"pid":123}'
    assert not target.exists()
