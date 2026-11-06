"""Stage-1 P1 incompatibility contracts: V2 producer, reproducible audit, semantic binding and source identity."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import time

import pytest

from motorsim.dino4t import api
from motorsim.dino4t.artifacts import publish_primary
from motorsim.source_provenance import capture_source_identity, validate_source_identity
from motorsim.dino4t import studies
from c01_c03_fixtures import endpoint_factory

ROOT = Path(__file__).resolve().parents[1]


def _producer():
    path = ROOT / "scripts/dino4t/run_ab_pair_v1.py"
    spec = importlib.util.spec_from_file_location("p1_ab_producer", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_ab_producer_publishes_v2_run_and_reference_without_solver(tmp_path, monkeypatch):
    producer = _producer()
    endpoint = endpoint_factory(tmp_path / "fixtures")("A")
    summary, config = endpoint["summary"], endpoint["config"]
    def fake_run(config, *, out_dir, **kwargs):
        artifacts = publish_primary(
            out_dir, summary, config,
            {"theta": [0.0, 360.0, 720.0], "p": [100000.0, 200000.0, 100000.0],
             "p_intake_port": [100000.0] * 3, "p_exhaust_port": [100000.0] * 3},
            origin={"kind": "SYNTHETIC_P1_FIXTURE"})
        return {"api": api.API_VERSION, "ok": True, "error": None, "summary": summary,
                "artifacts": artifacts, "state": None}
    monkeypatch.setattr(producer.api, "run", fake_run)
    record = producer._endpoint(config, "", tmp_path / "pair", time.monotonic(), 1)
    assert record["reference"]["schema"] == "DINO4T_RUN_REFERENCE_V2"
    assert record["meta"]["schema"] == "DINO4T_DESKTOP_RUN_V2"
    assert Path(record["reference"]["run_manifest_path"]).is_file()
    assert record["source_qualification"] in {
        "COMPLETE_CLEAN_SOURCE_SNAPSHOT", "DIRTY_OR_UNKNOWN_SOURCE"}


@pytest.mark.parametrize("mutate", [
    lambda s, c: s["cycle_history"][-1].update(imep_net_bar=999.0),
    lambda s, c: s["thermo_sources"].update(gri30_sha256="a" * 64),
    lambda s, c: s.update(evidence_level="L3_MEASURED_VALIDATION"),
    lambda s, c: s.update(warm_start="exact_restart_verified"),
    lambda s, c: s.update(config_identifier="otro"),
    lambda s, c: s["models"].update(bogus_extra_model="X"),
])
def test_semantic_binding_rejects_tampered_native_summary(tmp_path, mutate):
    endpoint = endpoint_factory(tmp_path)("A")
    summary, config = deepcopy(endpoint["summary"]), endpoint["config"]
    mutate(summary, config)
    assert api.check_summary(summary, config=config)


def test_incomplete_source_identity_is_not_a_numeric_result_failure(tmp_path):
    endpoint = endpoint_factory(tmp_path / "fixtures")("A")
    summary, config = deepcopy(endpoint["summary"]), endpoint["config"]
    no_git = tmp_path / "no-git-source"
    no_git.mkdir()
    incomplete = capture_source_identity(no_git)
    assert incomplete["status"] == "INCOMPLETE"
    assert validate_source_identity(incomplete, require_complete=False) == []
    summary["source_identity"] = incomplete
    summary["code_commit"] = None
    summary["code_dirty"] = None
    assert api.check_summary(summary, config=config) == []


def test_studies_persist_source_identity_and_contract_issues(tmp_path, monkeypatch):
    endpoint = endpoint_factory(tmp_path / "fixtures")("A")
    summary, config = endpoint["summary"], endpoint["config"]
    def fake_run(cfg, **kwargs):
        return {"summary": deepcopy(summary), "result": {"state": None},
                "context": {"config": cfg}}
    monkeypatch.setattr(studies, "run_operating_point", fake_run)
    studies.sweep(config, [{}], out_dir=tmp_path / "sweep")
    sweep = json.loads((tmp_path / "sweep" / "sweep.json").read_text(encoding="utf-8"))
    assert sweep["source_identity"]["schema"] == summary["source_identity"]["schema"]
    assert sweep["runtime_environment"] == summary["runtime_environment"]
    assert sweep["rows"][0]["contract_issues"] == []
    studies.sensitivity(config, parameters=[], out_dir=tmp_path / "sensitivity")
    sensitivity = json.loads((tmp_path / "sensitivity" / "sensitivity.json").read_text(encoding="utf-8"))
    assert sensitivity["source_identity"]["schema"] == summary["source_identity"]["schema"]
    assert sensitivity["contract_issues"] == []


def test_documented_audit_script_is_reproducible(tmp_path):
    output = tmp_path / "audit.json"
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/audits/audit_dino_platform_v1.py"),
         "--out", str(output)],
        cwd=ROOT, capture_output=True, text=True, timeout=180)
    assert result.returncode == 0, result.stderr
    audit = json.loads(output.read_text(encoding="utf-8"))
    manifest = audit["package_manifest"]
    assert manifest["recorded_paths_missing_from_current"] == []
    assert manifest["comparison_policy"].startswith("recorded fields subset")
    assert audit["p9"]["all_match"] is True
