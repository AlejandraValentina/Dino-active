from __future__ import annotations

import concurrent.futures
import time
from pathlib import Path

import pytest

from scripts import full_rpm_sweep_v1_impl2_supervisor_v1 as supervisor


def test_empty_polls_continue_until_a_slow_future_finishes():
    empty_polls = 0
    real_wait = concurrent.futures.wait

    def observe_empty_polls(futures, timeout=None, return_when=concurrent.futures.ALL_COMPLETED):
        nonlocal empty_polls
        done, pending = real_wait(futures, timeout=timeout, return_when=return_when)
        if not done:
            empty_polls += 1
        return done, pending

    started = time.monotonic()
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(time.sleep, 1.35)
        done, pending = supervisor.wait_until_completion_or_deadline(
            {future}, time.monotonic() + 5,
            wait_impl=observe_empty_polls, poll_interval_seconds=0.25)
        elapsed = time.monotonic() - started
        assert done == {future}
        assert not pending
        assert future.result() is None
    assert empty_polls >= 3
    assert elapsed > 1.0


def test_empty_result_is_returned_only_at_the_actual_deadline():
    real_wait = concurrent.futures.wait
    started = time.monotonic()
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(time.sleep, 0.8)
        done, pending = supervisor.wait_until_completion_or_deadline(
            {future}, time.monotonic() + 0.2, wait_impl=real_wait,
            poll_interval_seconds=0.05)
        elapsed = time.monotonic() - started
        assert done == set()
        assert pending == {future}
        assert elapsed >= 0.18


def test_completed_worker_exception_is_returned_for_propagation():
    def fail():
        time.sleep(0.05)
        raise RuntimeError("diagnostic worker failure")

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(fail)
        done, pending = supervisor.wait_until_completion_or_deadline(
            {future}, time.monotonic() + 5)
        assert done == {future}
        assert not pending
        with pytest.raises(RuntimeError, match="diagnostic worker failure"):
            future.result()


def test_manifest_records_distinct_supervisor_and_unchanged_runner_hash(tmp_path,
                                                                        monkeypatch):
    from scripts import full_rpm_sweep_v1_campaign as campaign

    supervisor_sha = supervisor._normalized_file_sha(Path(supervisor.__file__))
    original = supervisor._install_manifest_provenance(supervisor_sha)
    path = tmp_path / "campaign.json"
    try:
        campaign._write_json_atomic(path, {"schema": "DIAGNOSTIC_CAMPAIGN", "invocations": []})
    finally:
        campaign._write_json_atomic = original
    manifest = campaign._read_json(path)
    provenance = manifest["execution_supervisor"]
    assert provenance["version"] == supervisor.SUPERVISOR_VERSION
    assert provenance["source_sha256"] == supervisor_sha
    assert provenance["role"] == "COORDINATOR_WAIT_AND_RESUME_ORCHESTRATION_ONLY"
    identity = campaign._read_json(
        campaign.ROOT / "results/full-rpm-sweep-v1/implementation-v2-campaign-identity.json")
    runner_path = campaign.ROOT / identity["source_paths"]["runner"]
    assert provenance["campaign_worker_runner_sha256"] == \
        identity["source_hashes"]["runner"] == supervisor._normalized_file_sha(runner_path)
