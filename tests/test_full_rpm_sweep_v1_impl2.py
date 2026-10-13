from __future__ import annotations

import json
from pathlib import Path

import pytest

from motorsim import full_rpm_sweep_v1_impl2 as preflight


ROOT = Path(__file__).resolve().parents[1]


def test_legacy_diagnostic_proposal_stays_fail_closed_on_stale_hash(tmp_path: Path) -> None:
    before = (ROOT / preflight.IDENTITY).read_bytes()
    report = preflight.audit_impl2_preflight(ROOT, artifact_root=tmp_path)
    after = (ROOT / preflight.IDENTITY).read_bytes()

    assert report["status"] == "FAIL_CLOSED"
    assert report["checks"]["solver_dependency_hashes"] is False
    assert report["campaign_started"] is False
    assert report["campaign_execution_authorized"] is False
    assert report["checks"]["no_v1_campaign_artifacts_or_campaign_started"] is True
    assert before == after


def test_impl2_campaign_preflight_passes_all_30_without_solver() -> None:
    report = preflight.audit_impl2_campaign_preflight(ROOT)
    assert report["preflight_status"] == "PASS"
    assert report["campaigns_started"] == report["solver_steps_started"] == 0
    assert report["points_preflighted"] == 30
    assert report["checks"]["source_hashes_exact"] is True
    assert report["checks"]["fast_disabled"] is True
    assert all(v["checks"]["no_solver_steps"] for v in report["variants"])


def test_campaign_preflight_fails_closed_on_altered_source_hash(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = preflight._sha256

    def altered(path: Path) -> str:
        result = original(path)
        if path.name == "full_rpm_sweep_v1_campaign.py":
            return "0" * 64
        return result

    monkeypatch.setattr(preflight, "_sha256", altered)
    report = preflight.audit_impl2_campaign_preflight(ROOT)
    assert report["preflight_status"] == "FAIL_CLOSED"
    assert report["checks"]["source_hashes_exact"] is False


def test_impl2_preflight_fails_closed_on_runner_hash_mismatch(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    original_json = preflight._json

    def corrupted_identity(path: Path) -> dict:
        value = original_json(path)
        if path.name == preflight.IDENTITY.name:
            value["source_identity"]["campaign_runner_sha256"] = "0" * 64
        return value

    monkeypatch.setattr(preflight, "_json", corrupted_identity)
    report = preflight.audit_impl2_preflight(ROOT, artifact_root=tmp_path)
    assert report["status"] == "FAIL_CLOSED"
    assert report["checks"]["producer_and_benchmark_hashes"] is False


def test_impl2_preflight_rejects_campaign_artifact_in_output_root(tmp_path: Path) -> None:
    output = tmp_path / "engine-physics-v1" / "full-rpm-sweep-v1-impl2"
    output.mkdir(parents=True)
    (output / "campaign.json").write_text(json.dumps({"campaigns_started": 0}))

    report = preflight.audit_impl2_preflight(ROOT, artifact_root=tmp_path)
    assert report["status"] == "FAIL_CLOSED"
    assert report["checks"]["no_v1_campaign_artifacts_or_campaign_started"] is False


def test_impl2_preflight_validates_explicit_loss_models_and_resource_plans(
    tmp_path: Path,
) -> None:
    report = preflight.audit_impl2_preflight(ROOT, artifact_root=tmp_path)
    assert report["checks"]["explicit_configuration_and_loss_models"] is True
    assert report["checks"]["mechanical_model_provenance"] is True
    assert report["checks"]["worker_memory_bounds"] is True
    plans = report["worker_plans_4gib_budget"]
    assert [plans[str(n)]["effective_workers"] for n in (1, 2, 4)] == [1, 2, 4]
    assert all(
        p["effective_workers"] * p["reserve_per_worker_bytes"]
        <= min(p["memory_budget_bytes"], p["available_memory_bytes"])
        for p in plans.values()
    )


def test_impl2_preflight_preserves_v1_fail_closed_compatibility(tmp_path: Path) -> None:
    report = preflight.audit_impl2_preflight(ROOT, artifact_root=tmp_path)
    assert report["checks"]["v1_isolation_and_fail_closed"] is True
    assert report["checks"]["checkpoint_restart_evidence_present"] is True
    assert report["no_campaign_execution"] is True
