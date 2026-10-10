import pytest
import concurrent.futures
import hashlib
import json
import multiprocessing
import os
import threading
import time
from pathlib import Path

from scripts import full_rpm_sweep_v1_campaign as campaign
from scripts.full_rpm_sweep_v1_campaign import _parallel_worker_plan


def _diagnostic_checkpoint_worker(root, point_id, steps, stop_after=None,
                                  crash=False, delay=0.0, cancel_event=None):
    """Small spawn-safe scheduler fixture; deliberately not a solver workload."""
    if crash:
        os._exit(73)
    point = Path(root) / point_id
    point.mkdir(parents=True, exist_ok=True)
    checkpoint_path = point / "checkpoint.json"
    if checkpoint_path.exists():
        checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
        if checkpoint.get("binding") != "diagnostic-v1":
            raise ValueError("incompatible diagnostic checkpoint")
        value = checkpoint["value"]
        next_step = checkpoint["next_step"]
        hashes = list(checkpoint["step_hashes"])
    else:
        value, next_step, hashes = 0, 1, []
    for step in range(next_step, steps + 1):
        if delay:
            time.sleep(delay)
        value += step
        state = {"step": step, "value": value}
        hashes.append(hashlib.sha256(json.dumps(
            state, sort_keys=True, separators=(",", ":")).encode()).hexdigest())
        payload = {"binding": "diagnostic-v1", "next_step": step + 1,
                   "value": value, "step_hashes": hashes}
        campaign._write_json_atomic(checkpoint_path, payload)
        if ((stop_after is not None and step == stop_after) or
                (cancel_event is not None and cancel_event.is_set())):
            return {"point_id": point_id, "classification": "INTERRUPTED_CHECKPOINTED",
                    "checkpoint_sha256": campaign._sha256(checkpoint_path.read_bytes()),
                    "value": value, "steps": step}
    result = {"point_id": point_id, "classification": "COMPLETE",
              "value": value, "step_hashes": hashes}
    campaign._write_json_atomic(point / "result.json", result)
    return result


def test_parallel_worker_plan_caps_by_memory_and_cpu():
    plan = _parallel_worker_plan(
        8, 4096 * 1024 * 1024, available_memory_bytes=1500 * 1024 * 1024,
        cpu_count=12)
    assert plan["effective_workers"] == 2


def test_parallel_worker_plan_honors_requested_workers():
    plan = _parallel_worker_plan(
        2, 4096 * 1024 * 1024, available_memory_bytes=4096 * 1024 * 1024,
        cpu_count=12)
    assert plan["effective_workers"] == 2


@pytest.mark.parametrize("workers", [1, 2, 4])
def test_parallel_worker_plan_supports_requested_diagnostic_sizes(workers):
    plan = _parallel_worker_plan(
        workers, 4096 * 1024 * 1024, available_memory_bytes=4096 * 1024 * 1024,
        cpu_count=8)
    assert plan["effective_workers"] == workers
    assert plan["effective_workers"] * plan["reserve_per_worker_bytes"] <= \
        plan["memory_budget_bytes"]


def test_parallel_worker_plan_fails_closed_below_one_worker_reserve():
    with pytest.raises(ValueError, match="memory budget"):
        _parallel_worker_plan(
            2, 128 * 1024 * 1024, available_memory_bytes=4096 * 1024 * 1024,
            cpu_count=12)


def test_spawn_workers_checkpoint_isolation_restart_and_canonical_identity(tmp_path):
    context = multiprocessing.get_context("spawn")
    output = tmp_path / "diagnostic"
    manifest_path = output / "coordinator-manifest.json"
    output.mkdir()
    points = ("A4000", "B4000")
    # Workers own only point directories; the parent is the sole manifest writer.
    with concurrent.futures.ProcessPoolExecutor(
            max_workers=2, mp_context=context) as executor:
        futures = [executor.submit(_diagnostic_checkpoint_worker, str(output), point,
                                   5, stop_after=2, delay=0.01)
                   for point in points]
        interrupted = [future.result(timeout=30) for future in futures]
    manifest = {row["point_id"]: row["checkpoint_sha256"] for row in interrupted}
    campaign._write_json_atomic(manifest_path, {"checkpoints": manifest})
    assert len(manifest) == 2
    for point in points:
        checkpoint = output / point / "checkpoint.json"
        assert campaign._sha256(checkpoint.read_bytes()) == manifest[point]
        assert not list(checkpoint.parent.glob("*.tmp"))

    # Resume both independent points and compare their canonical results with
    # a sequential uninterrupted diagnostic execution.
    with concurrent.futures.ProcessPoolExecutor(
            max_workers=2, mp_context=context) as executor:
        resumed = [future.result(timeout=30) for future in [
            executor.submit(_diagnostic_checkpoint_worker, str(output), point, 5)
            for point in points]]
    sequential_root = tmp_path / "sequential"
    sequential_root.mkdir()
    sequential = [_diagnostic_checkpoint_worker(str(sequential_root), point, 5)
                  for point in points]
    canonical = lambda row: json.dumps(row, sort_keys=True, separators=(",", ":"))
    assert [canonical(row) for row in resumed] == [canonical(row) for row in sequential]
    assert len({row["point_id"] for row in resumed}) == 2
    assert all(row["value"] == 15 for row in resumed)  # conserved integer sum 1..5
    completed_manifest = {row["point_id"]: hashlib.sha256(
        canonical(row).encode()).hexdigest() for row in resumed}
    campaign._write_json_atomic(manifest_path, {"results": completed_manifest})
    assert json.loads(manifest_path.read_text(encoding="utf-8"))["results"] == completed_manifest


def test_spawn_worker_crash_preserves_completed_artifact_and_rejects_bad_checkpoint(tmp_path):
    context = multiprocessing.get_context("spawn")
    output = tmp_path / "crash-diagnostic"
    output.mkdir()
    with concurrent.futures.ProcessPoolExecutor(
            max_workers=2, mp_context=context) as executor:
        completed = executor.submit(_diagnostic_checkpoint_worker,
                                    str(output), "A4000", 3)
        assert completed.result(timeout=30)["classification"] == "COMPLETE"
        crashed = executor.submit(_diagnostic_checkpoint_worker,
                                  str(output), "B4000", 3, crash=True)
        with pytest.raises((concurrent.futures.process.BrokenProcessPool, OSError)):
            crashed.result(timeout=30)
    good_result = output / "A4000" / "result.json"
    before = good_result.read_bytes()
    with concurrent.futures.ProcessPoolExecutor(
            max_workers=2, mp_context=context) as executor:
        recovered = executor.submit(_diagnostic_checkpoint_worker,
                                    str(output), "A4000", 3).result(timeout=30)
        assert recovered["classification"] == "COMPLETE"
    assert good_result.read_bytes() == before

    incompatible = tmp_path / "incompatible.json"
    campaign._write_json_atomic(incompatible, {"schema": "wrong",
        "implementation_version": campaign.IMPLEMENTATION_VERSION,
        "bindings": {}, "next_cycle": 1, "engine_snapshot": {},
        "periodicity_snapshot": {}})
    with pytest.raises(ValueError, match="schema mismatch"):
        campaign._load_checkpoint(incompatible, {})


def test_checkpoint_binding_mismatch_is_rejected(tmp_path):
    checkpoint = tmp_path / "bound.json"
    campaign._write_json_atomic(checkpoint, {
        "schema": "FULL_RPM_SWEEP_V1_IMPL2_POINT_CHECKPOINT",
        "implementation_version": campaign.IMPLEMENTATION_VERSION,
        "bindings": {"point_configuration_sha256": "a" * 64},
        "next_cycle": 1, "engine_snapshot": {}, "periodicity_snapshot": {}})
    with pytest.raises(ValueError, match="binding hash mismatch"):
        campaign._load_checkpoint(checkpoint,
                                  {"point_configuration_sha256": "b" * 64})


def test_spawn_timeout_keeps_checkpoint_for_cooperative_resume(tmp_path):
    context = multiprocessing.get_context("spawn")
    output = tmp_path / "timeout-diagnostic"
    output.mkdir()
    with concurrent.futures.ProcessPoolExecutor(
            max_workers=1, mp_context=context) as executor:
        future = executor.submit(_diagnostic_checkpoint_worker,
                                 str(output), "A4000", 4, stop_after=1, delay=0.1)
        with pytest.raises(concurrent.futures.TimeoutError):
            future.result(timeout=0.02)
        interrupted = future.result(timeout=30)
    assert interrupted["classification"] == "INTERRUPTED_CHECKPOINTED"
    checkpoint = output / "A4000" / "checkpoint.json"
    checkpoint_hash = campaign._sha256(checkpoint.read_bytes())
    with concurrent.futures.ProcessPoolExecutor(
            max_workers=1, mp_context=context) as executor:
        result = executor.submit(_diagnostic_checkpoint_worker,
                                 str(output), "A4000", 4).result(timeout=30)
    assert result["classification"] == "COMPLETE"
    assert checkpoint_hash != campaign._sha256((output / "A4000" / "result.json").read_bytes())


def test_spawn_coordinator_cancel_signal_stops_at_checkpoint_and_resumes(tmp_path):
    context = multiprocessing.get_context("spawn")
    output = tmp_path / "cancel-diagnostic"
    output.mkdir()
    with context.Manager() as manager:
        cancel_event = manager.Event()
        timer = threading.Timer(0.2, cancel_event.set)
        timer.start()
        try:
            with concurrent.futures.ProcessPoolExecutor(
                    max_workers=1, mp_context=context) as executor:
                interrupted = executor.submit(
                    _diagnostic_checkpoint_worker, str(output), "A4000", 100,
                    delay=0.03, cancel_event=cancel_event).result(timeout=30)
        finally:
            timer.cancel()
        assert interrupted["classification"] == "INTERRUPTED_CHECKPOINTED"
        assert interrupted["steps"] < 100
    with concurrent.futures.ProcessPoolExecutor(
            max_workers=1, mp_context=context) as executor:
        resumed = executor.submit(_diagnostic_checkpoint_worker,
                                  str(output), "A4000", interrupted["steps"] + 1).result(timeout=30)
    assert resumed["classification"] == "COMPLETE"
