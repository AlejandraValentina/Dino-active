from __future__ import annotations

import copy
import json
import threading

import pytest

from motorsim import exploratory_workflow as workflow
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


@pytest.mark.parametrize(("kwargs", "expected"), [
    ({"complete_cycles": 0, "comparison_count": 0, "accepted_period": None,
      "termination_reason": "TIMEOUT"}, "NOT_EXECUTED"),
    ({"complete_cycles": 1, "comparison_count": 0, "accepted_period": None,
      "termination_reason": "HORIZON_COMPLETED"}, "INSUFFICIENT_EVIDENCE"),
    ({"complete_cycles": 4, "comparison_count": 4, "accepted_period": None,
      "termination_reason": "HORIZON_COMPLETED"}, "EXECUTED_NO_PERIOD_ACCEPTED"),
    ({"complete_cycles": 4, "comparison_count": 3, "accepted_period": None,
      "termination_reason": "TIMEOUT"}, "TIMEOUT_PARTIAL"),
    ({"complete_cycles": 4, "comparison_count": 3, "accepted_period": None,
      "termination_reason": "CANCELLED"}, "CANCELLED_PARTIAL"),
    ({"complete_cycles": 2, "comparison_count": 1, "accepted_period": None,
      "termination_reason": "NUMERICAL_INVALID", "failure_kind": "NUMERICAL_INVALID"},
     "NUMERICAL_FAILURE"),
    ({"complete_cycles": 2, "comparison_count": 1, "invalid_comparison_count": 1,
      "accepted_period": None, "termination_reason": "HORIZON_COMPLETED"},
     "INVALID_COMPARISON_EVIDENCE"),
    ({"complete_cycles": 5, "comparison_count": 4, "accepted_period": "PERIOD_1",
      "termination_reason": "PERIOD_ACCEPTED"}, "PERIOD_ACCEPTED"),
])
def test_periodicity_evaluation_status_distinguishes_evidence_and_termination(kwargs, expected):
    assert workflow._periodicity_evaluation_status(**kwargs) == expected


def test_engineering_output_metadata_avoids_primary_json_roundtrip():
    primary = {"schema": "primary", "trajectory": [{"angle": 12.0}],
               "conservation": {"mass": 0.0}}
    canonical_primary_bytes = workflow._json_bytes(primary)
    prior_roundtrip = json.loads(json.dumps(primary, allow_nan=False))
    evidence = {"status": "PERIOD_1", "terminal_cycle": 4}
    output_record = workflow._prepare_engineering_output_record(primary, evidence)
    prior_roundtrip["periodicity_evidence"] = evidence
    assert output_record is primary
    assert output_record == prior_roundtrip
    assert workflow._json_bytes({key: value for key, value in primary.items()
                                  if key != "periodicity_evidence"}) == canonical_primary_bytes


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
    assert first["periodicity_diagnostics"]["evaluation_status"] == "INSUFFICIENT_EVIDENCE"
    assert first["periodicity_diagnostics"]["detector_executed"] is True
    assert first["periodicity_diagnostics"]["comparison_count"] == 0
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
    assert resumed["periodicity_contract"] == "REFERENCE_PERIODIC_CONVERGENCE_V2"
    assert resumed["bindings"]["periodicity_contract"] == resumed["periodicity_contract"]
    assert resumed["periodicity_diagnostics"]["evaluation_status"] == "EXECUTED_NO_PERIOD_ACCEPTED"
    assert resumed["periodicity_diagnostics"]["complete_cycles_evaluated"] == 2
    assert resumed["periodicity_diagnostics"]["comparison_count"] == 1
    assert resumed["periodicity_diagnostics"]["comparison_index"][0]["status"] in {"PASS", "FAIL"}
    assert resumed["periodicity_diagnostics"]["residuals_and_per_comparison_thresholds_at"].startswith("cycles[]")
    assert resumed["cycles"][1]["periodicity_update"]["outcomes"]["lag1"]["contract"] == resumed["periodicity_contract"]
    imported=import_exploratory_runs([tmp_path/"exploratory-workflow-v1"/"test-project"/"cancel-resume"])
    assert len(imported["points"])==2
    assert imported["points"][0]["mode"]=="EXPLORATORY"
    assert imported["points"][0]["hard_gates"]["status"]=="NOT_EVALUATED_EXPLORATORY"
    assert imported["points"][0]["audit_status"]=="PASS"
    assert imported["points"][0]["audit_recomputed"] is True
    point_provenance=imported["points"][0]
    assert len(point_provenance["implementation_identity_sha256"])==64
    assert point_provenance["solver_identity_sha256"]==resumed["bindings"]["source_hashes"]["motorsim.integrated_2t"]
    assert point_provenance["producer_sha256"]==resumed["bindings"]["source_hashes"]["motorsim.exploratory_workflow"]
    assert point_provenance["fuel_id"]==resumed["preflight"]["fuel_id"]
    assert point_provenance["mechanical_loss_model_sha256"]==resumed["preflight"]["mechanical_loss_model_sha256"]
    assert point_provenance["periodicity_contract"]==resumed["periodicity_contract"]
    assert point_provenance["total_finite_volume_cells"]==resumed["preflight"]["total_finite_volume_cells"]
    assert point_provenance["mesh_resolution"]
    assert imported["points"][0]["periodicity"]=="NOT_EVALUATED"
    assert imported["points"][0]["periodicity_diagnostics"] == resumed["periodicity_diagnostics"]
    assert imported["points"][0]["conservation"]["mass_residual_kg"]==pytest.approx(0.0,abs=1e-11)
    assert len(imported["traces"])==2
    assert imported["traces"][0]["audit_recomputed"] is True
    assert imported["traces"][0]["angles_deg"]
    assert "cylinder_pressure_pa" in imported["traces"][0]["channels"]
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


@pytest.mark.parametrize(("failure", "status", "classification"), [
    (workflow.RunDeadline("test deadline"), "INTERRUPTED_CHECKPOINTED",
     "EXPLORATORY_TIMEOUT_CHECKPOINTED"),
    (MemoryError("test memory limit"), "FAILED_CLOSED",
     "EXPLORATORY_RESOURCE_LIMIT_EXCEEDED"),
    (ValueError("synthetic numerical failure"), "FAILED_CLOSED",
     "EXPLORATORY_NUMERICAL_INVALID"),
])
def test_runner_persists_timeout_and_memory_failure_classifications_without_solver(
        tmp_path, monkeypatch, failure, status, classification):
    def fail_before_step(*args, **kwargs):
        raise failure

    monkeypatch.setattr(workflow, "_advance_cycle", fail_before_step)
    result = run_exploratory(
        engine_document(), project_id="bounded-failure", run_id=classification.lower(),
        artifact_root=tmp_path, rpm=3000.0, max_cycles=1, budget_seconds=10,
        memory_limit_mib=1024,
    )

    assert result["status"] == status
    assert result["classification"] == classification
    assert result["cycles_completed"] == 0
    assert result["periodicity"] == "NOT_EVALUATED"
    assert result["checkpoint_sha256"]
    run_dir = tmp_path / "exploratory-workflow-v1" / "bounded-failure" / classification.lower()
    checkpoint = json.loads((run_dir / "checkpoint.json").read_text(encoding="utf-8"))
    manifest = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
    assert checkpoint["next_cycle"] == 1
    assert manifest["status"] == status
    assert manifest["cycles_completed"] == 0
    expected_periodicity_status = ("NUMERICAL_FAILURE" if isinstance(failure, ValueError)
                                   else "NOT_EXECUTED")
    assert result["periodicity_diagnostics"]["evaluation_status"] == expected_periodicity_status
    expected_termination = ("TIMEOUT" if isinstance(failure, workflow.RunDeadline) else
                            "NUMERICAL_INVALID" if isinstance(failure, ValueError) else
                            "RESOURCE_LIMIT_EXCEEDED")
    assert result["periodicity_diagnostics"]["termination_reason"] == expected_termination


def test_resume_rejects_pre_v2_periodicity_binding(tmp_path):
    cancel = threading.Event(); cancel.set()
    run_exploratory(engine_document(), project_id="binding", run_id="legacy-contract",
        artifact_root=tmp_path, max_cycles=1, budget_seconds=10,
        memory_limit_mib=1024, cancel_event=cancel)
    run_dir = tmp_path / "exploratory-workflow-v1" / "binding" / "legacy-contract"
    manifest_path = run_dir / "run.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["bindings"].pop("periodicity_contract")
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="resume rejected: run identity/configuration/solver binding mismatch"):
        run_exploratory(engine_document(), project_id="binding", run_id="legacy-contract",
            artifact_root=tmp_path, max_cycles=1, budget_seconds=10,
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


def test_exploratory_import_reports_zero_cycle_gap_without_metrics(tmp_path):
    document=engine_document(); cancel=threading.Event(); cancel.set()
    result=run_exploratory(document,project_id="p",run_id="zero-cycle",artifact_root=tmp_path,
        rpm=3000,max_cycles=1,budget_seconds=10,cancel_event=cancel)
    assert result["cycles_completed"]==0
    imported=import_exploratory_runs([tmp_path/"exploratory-workflow-v1"/"p"/"zero-cycle"])
    assert imported["traces"]==[]
    point=imported["points"][0]
    assert point["classification"]=="EXPLORATORY_CANCELLED_CHECKPOINTED"
    assert point["audit_status"]=="NO_COMPLETE_CYCLE"
    assert point["audit_recomputed"] is False
    assert point["brake_power"] is None
    assert point["brake_power_status"]=="NOT_REPORTED"


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
