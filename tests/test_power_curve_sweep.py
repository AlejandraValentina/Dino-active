import json
import hashlib
import threading
import time

import motorsim.power_curve_sweep as sweep


def _patch_sweep(monkeypatch, tmp_path, outcomes):
    monkeypatch.setattr(sweep, "identity", lambda document: "doc-id")
    monkeypatch.setattr(sweep, "preflight", lambda document, **kwargs: {
        "identity_sha256": f"rpm-{kwargs['rpm']}", "configuration_sha256": f"config-{kwargs['rpm']}",
        "mechanical_loss_model_sha256": "loss-model", "fuel_id": "fuel-id",
        "periodicity_contract": "PERIODICITY_V2", "total_finite_volume_cells": 12,
        "status": "PASS", "solver_steps": 0})
    monkeypatch.setattr("motorsim.desktop.preferences.repository_root_containing", lambda path: None)
    calls = []

    def fake_run(document, *, project_id, run_id, artifact_root, rpm, resume, **kwargs):
        calls.append((rpm, resume))
        run_dir = (tmp_path / "artifacts" / "exploratory-workflow-v1" / project_id / run_id)
        run_dir.mkdir(parents=True, exist_ok=True)
        result_hash = f"result-{rpm}-{len(calls)}"
        checkpoint_payload = b"{}"
        checkpoint_hash = hashlib.sha256(checkpoint_payload).hexdigest()
        status, classification = outcomes.pop(0) if outcomes else ("COMPLETE", "EXPLORATORY_COMPLETE_PERIODICITY_OBSERVED")
        result_payload = json.dumps({"result_sha256": result_hash}).encode("utf-8")
        (run_dir / "run.json").write_text(json.dumps({
            "bindings": {"identity_sha256": f"rpm-{rpm}", "configuration_sha256": f"config-{rpm}"},
            "result_sha256": hashlib.sha256(result_payload).hexdigest(),
            "checkpoint_artifact": "checkpoint.json", "checkpoint_sha256": checkpoint_hash}), encoding="utf-8")
        (run_dir / "result.json").write_bytes(result_payload)
        (run_dir / "checkpoint.json").write_bytes(checkpoint_payload)
        return {"status": status, "classification": classification, "periodicity": "NOT_EVALUATED",
            "cycles_completed": 2, "elapsed_seconds": 0.01, "checkpoint_sha256": checkpoint_hash,
            "result_sha256": result_hash, "artifact_directory": str(run_dir),
            "bindings": {"identity_sha256": f"rpm-{rpm}", "configuration_sha256": f"config-{rpm}"}}

    monkeypatch.setattr(sweep, "run_exploratory", fake_run)
    return calls


def _kwargs(tmp_path):
    return dict(project_id="demo", variant_label="base", artifact_root=tmp_path / "artifacts",
        start_rpm=3000, stop_rpm=4000, step_rpm=1000, max_cycles=2,
        point_budget_seconds=5, total_budget_seconds=20, memory_limit_mib=512,
        sweep_id="sweep-test")


def test_sweep_preflights_all_points_without_solver(monkeypatch, tmp_path):
    calls = _patch_sweep(monkeypatch, tmp_path, [])
    result = sweep.prepare_power_curve({"engine": "test"}, **{k: v for k, v in _kwargs(tmp_path).items()
        if k not in {"sweep_id"}})
    assert result["rpms"] == [3000, 4000]
    assert result["solver_steps"] == 0
    assert len(result["point_preflights"]) == 2
    assert calls == []


def test_sweep_checkpoint_resume_and_no_duplicate_completed_points(monkeypatch, tmp_path):
    calls = _patch_sweep(monkeypatch, tmp_path, [("INTERRUPTED_CHECKPOINTED", "EXPLORATORY_TIMEOUT_CHECKPOINTED"),
                                                  ("COMPLETE", "EXPLORATORY_COMPLETE_PERIODICITY_OBSERVED")])
    first = sweep.run_power_curve({"engine": "test"}, **_kwargs(tmp_path))
    assert first["status"] == "INTERRUPTED_CHECKPOINTED"
    assert first["points"][0]["cycles_completed"] == 2
    second = sweep.run_power_curve({"engine": "test"}, **_kwargs(tmp_path), resume=True)
    assert second["status"] == "COMPLETE"
    assert calls == [(3000, False), (3000, True), (4000, False)]
    saved = json.loads((tmp_path / "artifacts" / "dino-power-curve-v1" / "demo" / "sweep-test" / "series.json").read_text())
    assert [p["rpm"] for p in saved["points"]] == [3000, 4000]


def test_sweep_rejects_changed_configuration_before_resume(monkeypatch, tmp_path):
    _patch_sweep(monkeypatch, tmp_path, [])
    sweep.run_power_curve({"engine": "test"}, **_kwargs(tmp_path))
    monkeypatch.setattr(sweep, "identity", lambda document: "changed-id")
    import pytest
    with pytest.raises(ValueError, match="binding mismatch"):
        sweep.run_power_curve({"engine": "changed"}, **_kwargs(tmp_path), resume=True)


def test_completed_points_are_reaudited_and_reused_without_duplicate_run(monkeypatch, tmp_path):
    calls = _patch_sweep(monkeypatch, tmp_path, [])
    monkeypatch.setattr("motorsim.exploratory_workflow.import_exploratory_runs",
        lambda paths: {"points": [{"audit_recomputed": True}]})
    first = sweep.run_power_curve({"engine": "test"}, **_kwargs(tmp_path))
    assert first["status"] == "COMPLETE"
    second = sweep.run_power_curve({"engine": "test"}, **_kwargs(tmp_path), resume=True)
    assert second["status"] == "COMPLETE"
    assert calls == [(3000, False), (4000, False)]


def test_sweep_cancellation_preserves_not_started_points(monkeypatch, tmp_path):
    calls = _patch_sweep(monkeypatch, tmp_path, [])
    cancelled = threading.Event(); cancelled.set()
    result = sweep.run_power_curve({"engine": "test"}, **_kwargs(tmp_path), cancel_event=cancelled)
    assert result["status"] == "INTERRUPTED_CHECKPOINTED"
    assert all(point["status"] == "NOT_STARTED" for point in result["points"])
    assert calls == []


def test_crashed_coordinator_time_is_charged_before_resume(monkeypatch, tmp_path):
    calls = _patch_sweep(monkeypatch, tmp_path, [("INTERRUPTED_CHECKPOINTED", "EXPLORATORY_TIMEOUT_CHECKPOINTED")])
    kwargs = _kwargs(tmp_path)
    first = sweep.run_power_curve({"engine": "test"}, **kwargs)
    manifest_path = tmp_path / "artifacts" / "dino-power-curve-v1" / "demo" / "sweep-test" / "series.json"
    persisted = json.loads(manifest_path.read_text(encoding="utf-8"))
    persisted["status"] = "RUNNING"
    persisted["elapsed_seconds"] = 19
    persisted["points"][0]["status"] = "RUNNING"
    persisted["points"][0]["started_unix"] = time.time() - 3
    manifest_path.write_text(json.dumps(persisted), encoding="utf-8")
    resumed = sweep.run_power_curve({"engine": "test"}, **kwargs, resume=True)
    assert resumed["status"] == "INTERRUPTED_CHECKPOINTED"
    assert resumed["classification"] == "EXPLORATORY_SWEEP_TOTAL_BUDGET_EXHAUSTED"
    assert calls == [(3000, False)]


def test_coordinator_lock_rejects_live_owner_and_quarantines_dead_owner(tmp_path):
    lock = tmp_path / "series" / ".coordinator.lock"
    lock.parent.mkdir()
    lock.write_text(json.dumps({"pid": __import__("os").getpid(), "token": "live",
        "schema": "DINO_SWEEP_LOCK_V1"}), encoding="utf-8")
    import pytest
    with pytest.raises(RuntimeError, match="active"):
        with sweep._coordinator_lock(lock):
            pass
    lock.write_text(json.dumps({"pid": 2147483647, "token": "dead",
        "schema": "DINO_SWEEP_LOCK_V1"}), encoding="utf-8")
    with sweep._coordinator_lock(lock):
        assert lock.exists()
    assert not lock.exists()
    assert list(lock.parent.glob(".coordinator.lock.orphaned-*"))
