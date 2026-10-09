import pytest

from scripts.full_rpm_sweep_v1_campaign import _parallel_worker_plan


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


def test_parallel_worker_plan_fails_closed_below_one_worker_reserve():
    with pytest.raises(ValueError, match="memory budget"):
        _parallel_worker_plan(
            2, 128 * 1024 * 1024, available_memory_bytes=4096 * 1024 * 1024,
            cpu_count=12)
