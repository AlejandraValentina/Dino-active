"""Versioned bounded supervisor for resuming the authorized IMPL2 subset.

The frozen campaign runner remains the worker and scientific producer. This
module changes only coordinator waiting: empty one-second polls are retried,
and an empty result is returned only at the bounded invocation deadline.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import os
import sys
import time
from pathlib import Path
from typing import Iterable

from scripts import full_rpm_sweep_v1_campaign as campaign


SUPERVISOR_VERSION = "FULL_RPM_SWEEP_V1_IMPL2_SUPERVISOR_V1"
POLL_INTERVAL_SECONDS = 1.0
CHECKPOINT_SHUTDOWN_HEADROOM_SECONDS = 120
AUTHORIZED_POINT_IDS = (
    "A_PRIME_MESH_0@3100RPM",
    "A_PRIME_MESH_0@4000RPM",
    "B_PRIME_MESH_0@3100RPM",
    "B_PRIME_MESH_0@4000RPM",
)


def wait_until_completion_or_deadline(
    futures: Iterable[concurrent.futures.Future],
    deadline: float,
    *,
    return_when=concurrent.futures.FIRST_COMPLETED,
    wait_impl=concurrent.futures.wait,
    poll_interval_seconds: float = POLL_INTERVAL_SECONDS,
):
    """Wait at a bounded polling interval; empty polls never cancel workers."""
    future_set = set(futures)
    if not future_set:
        return set(), set()
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return wait_impl(future_set, timeout=0, return_when=return_when)
        done, pending = wait_impl(
            future_set,
            timeout=min(poll_interval_seconds, remaining),
            return_when=return_when,
        )
        if done:
            return done, pending
        if time.monotonic() >= deadline:
            return done, pending


def _normalized_file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def _parse_execution_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--implementation")
    parser.add_argument("--output-root", type=Path)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--pilot", action="store_true")
    parser.add_argument("--point", action="append", dest="point_ids")
    parser.add_argument("--budget-seconds", type=int, default=campaign.MAX_INVOCATION_SECONDS)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--memory-budget-mib", type=int, default=4096)
    parsed, _ = parser.parse_known_args(argv)
    return parsed


def _authorized_remaining_budget(args: argparse.Namespace) -> tuple[float, int, Path]:
    artifact_root = campaign.default_artifact_root().resolve()
    artifact_base = artifact_root / "engine-physics-v1/full-rpm-sweep-v1-impl2"
    authorization_path = campaign.ROOT / (
        "results/full-rpm-sweep-v1/implementation-v2-campaign-authorization.json"
    )
    authorization = campaign._read_json(authorization_path)
    if authorization.get("authorized") is not True:
        raise RuntimeError("IMPL2 subset authorization is not active")
    authorized_points = authorization.get("scope", {}).get("point_ids")
    if (not isinstance(args.point_ids, list) or len(args.point_ids) != 4 or
            len(set(args.point_ids)) != 4 or set(args.point_ids) != set(AUTHORIZED_POINT_IDS) or
            set(args.point_ids) != set(authorized_points or [])):
        raise RuntimeError("supervisor only accepts the exact four authorized pilot points")
    if args.implementation != "impl2" or not args.execute or not args.resume or args.pilot:
        raise RuntimeError("supervisor requires --execute --implementation impl2 --resume")
    if args.workers < 1 or args.workers > authorization["scope"]["maximum_workers"]:
        raise RuntimeError("worker request exceeds the explicit pilot authorization")
    if args.memory_budget_mib < 512 or args.memory_budget_mib > authorization[
            "scope"]["memory_budget_mib"]:
        raise RuntimeError("memory request exceeds the explicit pilot authorization")
    if args.budget_seconds < 1 or args.budget_seconds > authorization[
            "scope"]["maximum_invocation_seconds"]:
        raise RuntimeError("invocation budget exceeds the explicit pilot authorization")
    if args.output_root is None:
        raise RuntimeError("safe resume requires the existing explicit --output-root")
    if not args.output_root.resolve().is_relative_to(artifact_base):
        raise RuntimeError("resume output is outside the isolated IMPL2 artifact root")

    authorization_sha = _normalized_file_sha(authorization_path)
    prereg_path = campaign.ROOT / (
        "results/full-rpm-sweep-v1/implementation-v2-campaign-preregistration.json"
    )
    prereg = campaign._read_json(prereg_path)
    campaign_id = f"{campaign.IMPLEMENTATION_VERSION}_{campaign.canonical_sha256(prereg)[:16]}"
    prior_elapsed = 0.0
    if artifact_base.exists():
        for manifest_path in artifact_base.rglob("campaign.json"):
            manifest = campaign._read_json(manifest_path)
            if manifest.get("campaign_id") != campaign_id:
                continue
            prior_elapsed += sum(
                float(row.get("duration_seconds", 0.0))
                for row in manifest.get("invocations", [])
                if row.get("authorization_sha256") == authorization_sha
            )
    global_budget = int(authorization["scope"]["global_budget_seconds"])
    remaining = global_budget - prior_elapsed
    if remaining <= 0:
        raise RuntimeError("authorized pilot global wall-clock budget is exhausted")
    headroom = min(CHECKPOINT_SHUTDOWN_HEADROOM_SECONDS,
                   max(1, int(remaining) // 20))
    safe_execution_budget = min(args.budget_seconds, int(remaining) - headroom)
    if safe_execution_budget <= 0:
        raise RuntimeError("no safe execution time remains after checkpoint headroom")
    return remaining, safe_execution_budget, artifact_base


def _install_manifest_provenance(supervisor_sha256: str):
    original_writer = campaign._write_json_atomic
    identity_path = campaign.ROOT / "results/full-rpm-sweep-v1/implementation-v2-campaign-identity.json"
    identity = campaign._read_json(identity_path)
    runner_relpath = identity["source_paths"]["runner"]
    runner_sha256 = _normalized_file_sha(campaign.ROOT / runner_relpath)

    def write_with_supervisor(path: Path, value: dict) -> None:
        if Path(path).name == "campaign.json" and isinstance(value, dict):
            value = dict(value)
            value["execution_supervisor"] = {
                "schema": "FULL_RPM_SWEEP_V1_EXECUTION_SUPERVISOR_PROVENANCE",
                "version": SUPERVISOR_VERSION,
                "source_path": "scripts/full_rpm_sweep_v1_impl2_supervisor_v1.py",
                "source_sha256": supervisor_sha256,
                "campaign_worker_runner_sha256": runner_sha256,
                "role": "COORDINATOR_WAIT_AND_RESUME_ORCHESTRATION_ONLY",
            }
        original_writer(path, value)

    campaign._write_json_atomic = write_with_supervisor
    return original_writer


def main(argv: list[str] | None = None) -> int:
    forwarded = list(sys.argv[1:] if argv is None else argv)
    args = _parse_execution_args(forwarded)
    if not args.execute:
        return campaign.main(forwarded)

    remaining, safe_execution_budget, _ = _authorized_remaining_budget(args)
    supervisor_path = Path(__file__).resolve()
    supervisor_sha256 = _normalized_file_sha(supervisor_path)
    original_wait = campaign.concurrent.futures.wait
    original_writer = _install_manifest_provenance(supervisor_sha256)
    # Conservative outer deadline starts before campaign preflight. The runner
    # applies the same remaining-budget/headroom calculation to worker deadlines.
    outer_deadline = time.monotonic() + safe_execution_budget

    def bounded_wait(futures, timeout=None, return_when=concurrent.futures.ALL_COMPLETED):
        if timeout is None:
            # The runner uses this after cooperative cancellation to collect
            # workers at their next complete-cycle checkpoint.
            return original_wait(futures, timeout=CHECKPOINT_SHUTDOWN_HEADROOM_SECONDS,
                                 return_when=return_when)
        return wait_until_completion_or_deadline(
            futures, outer_deadline, return_when=return_when,
            wait_impl=original_wait,
        )

    campaign.concurrent.futures.wait = bounded_wait
    try:
        result = campaign.main(forwarded)
        print(json.dumps({
            "supervisor": SUPERVISOR_VERSION,
            "supervisor_sha256": supervisor_sha256,
            "campaign_runner_sha256": _normalized_file_sha(
                campaign.ROOT / "scripts/full_rpm_sweep_v1_campaign.py"),
            "authorization_sha256": _normalized_file_sha(
                campaign.ROOT / "results/full-rpm-sweep-v1/implementation-v2-campaign-authorization.json"),
            "global_budget_seconds": 3600,
            "budget_consumed_before_invocation_seconds": round(3600 - remaining, 6),
            "safe_invocation_budget_seconds": safe_execution_budget,
            "result_code": result,
        }, sort_keys=True))
        return result
    finally:
        campaign.concurrent.futures.wait = original_wait
        campaign._write_json_atomic = original_writer


if __name__ == "__main__":
    raise SystemExit(main())
