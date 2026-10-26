"""Append-only authorized extension supervisor for the remaining IMPL2 RPM points.

The frozen campaign module remains the scientific producer. This supervisor
adds only scoped authorization, a separate extension artifact root, and a
single-coordinator manifest/budget ledger for the user's 26-point extension.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import multiprocessing
import os
import platform
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scripts import full_rpm_sweep_v1_campaign as campaign
from motorsim.full_rpm_sweep_v1_impl2 import audit_impl2_campaign_preflight


ROOT = campaign.ROOT
AUTHORIZATION_RELATIVE = Path(
    "results/full-rpm-sweep-v1/implementation-v2-extension-authorization-20261013-v3.json"
)
PILOT_POINT_IDS = {
    "A_PRIME_MESH_0@3100RPM", "A_PRIME_MESH_0@4000RPM",
    "B_PRIME_MESH_0@3100RPM", "B_PRIME_MESH_0@4000RPM",
}
GLOBAL_BUDGET_SECONDS = 21600
INVOCATION_LIMIT_SECONDS = 3600
WORKER_LIMIT = 4
MEMORY_LIMIT_MIB = 4096
WORKER_RESERVE_MIB = 512
SHUTDOWN_HEADROOM_SECONDS = 120
EXTENSION_NAME = "authorized-extension-26-v1"


def _sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _file_sha(path: Path) -> str:
    return _sha(path.read_bytes().replace(b"\r\n", b"\n"))


def _read(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def _write_exclusive(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=False) + "\n"
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def _atomic_write(path: Path, payload: dict) -> None:
    campaign._write_json_atomic(path, payload)


def _artifact_base() -> Path:
    return campaign.default_artifact_root().resolve() / \
        "engine-physics-v1/full-rpm-sweep-v1-impl2"


def _point_id(variant: dict, rpm: int) -> str:
    return f"{variant['variant_id']}@{rpm}RPM"


def _all_points(prereg: dict) -> list[tuple[dict, int]]:
    return campaign._selected_points(prereg, pilot=False)


def _extension_points(prereg: dict) -> list[tuple[dict, int]]:
    return [(variant, rpm) for variant, rpm in _all_points(prereg)
            if _point_id(variant, rpm) not in PILOT_POINT_IDS]


def _expected_identity() -> tuple[dict, str, dict]:
    prereg_path = ROOT / "results/full-rpm-sweep-v1/implementation-v2-campaign-preregistration.json"
    identity_path = ROOT / "results/full-rpm-sweep-v1/implementation-v2-campaign-identity.json"
    prereg = _read(prereg_path)
    identity = _read(identity_path)
    prereg_sha = _file_sha(prereg_path)
    if prereg_sha != "e26c0599325a9e6296291178ffd2e36457838052f1d9b59de7b6dc0f282d59e3":
        raise RuntimeError("frozen IMPL2 preregistration SHA-256 mismatch")
    if identity.get("preregistration_sha256") != prereg_sha:
        raise RuntimeError("IMPL2 campaign identity does not bind the frozen preregistration")
    return prereg, prereg_sha, identity


def _validate_authorization(path: Path, prereg_sha: str, identity: dict,
                            point_ids: list[str]) -> dict:
    authorization = _read(path)
    exact = {
        "schema": "FULL_RPM_SWEEP_V1_IMPL2_APPEND_ONLY_EXTENSION_AUTHORIZATION_V3",
        "authorization_type": "EXPLICIT_REMAINING_26_POINT_EXTENSION",
        "authorized": True,
        "implementation_version": campaign.IMPLEMENTATION_VERSION,
        "preregistration_sha256": prereg_sha,
        "implementation_identity_sha256": _file_sha(
            ROOT / "results/full-rpm-sweep-v1/implementation-v2-campaign-identity.json"),
        "campaign_runner_sha256": _file_sha(ROOT / identity["source_paths"]["runner"]),
        "execution_supervisor_sha256": _file_sha(Path(__file__)),
    }
    for key, value in exact.items():
        if authorization.get(key) != value:
            raise RuntimeError(f"extension authorization binding mismatch: {key}")
    scope = authorization.get("scope", {})
    expected_ids = sorted(point_ids)
    if (scope.get("point_ids") != expected_ids or scope.get("maximum_points") != 26 or
            scope.get("global_budget_seconds") != GLOBAL_BUDGET_SECONDS or
            scope.get("maximum_invocation_seconds") != INVOCATION_LIMIT_SECONDS or
            scope.get("maximum_workers") != WORKER_LIMIT or
            scope.get("memory_budget_mib") != MEMORY_LIMIT_MIB or
            scope.get("worker_reservation_mib") != WORKER_RESERVE_MIB):
        raise RuntimeError("extension authorization scope or resource limits mismatch")
    if authorization.get("exclusions") != [
            "the four completed pilot points and their artifacts",
            "all v1 points and artifacts",
            "any point outside the remaining 26 preregistered IMPL2 points",
            "new configurations, models, solver/physics changes, and FAST_RECIPE_V1"]:
        raise RuntimeError("extension authorization exclusions mismatch")
    return authorization


def _preflight() -> tuple[dict, str, dict, list[tuple[dict, int]], dict]:
    prereg, prereg_sha, identity = _expected_identity()
    preflight = audit_impl2_campaign_preflight(ROOT)
    if preflight.get("preflight_status") != "PASS" or \
            preflight.get("preregistration_sha256") != prereg_sha:
        raise RuntimeError("IMPL2 full-campaign preflight did not pass")
    current_runner_sha = _file_sha(ROOT / identity["source_paths"]["runner"])
    if identity.get("source_hashes", {}).get("runner") != current_runner_sha:
        raise RuntimeError("frozen scientific campaign producer hash changed")
    points = _extension_points(prereg)
    if len(points) != 26 or len({ _point_id(v, rpm) for v, rpm in points }) != 26:
        raise RuntimeError("remaining-point selection is not exactly 26 unique preregistered points")
    auth_path = ROOT / AUTHORIZATION_RELATIVE
    auth = _validate_authorization(auth_path, prereg_sha, identity,
                                   [_point_id(v, rpm) for v, rpm in points])
    _validate_pilot_artifacts(prereg, prereg_sha, identity)
    return prereg, prereg_sha, identity, points, auth


def _validate_pilot_artifacts(prereg: dict, prereg_sha: str, identity: dict) -> dict:
    """Validate pilot in its original isolated root; never alter it."""
    root = _artifact_base() / "controlled-pilot-attempt-2"
    manifest_path = root / "campaign.json"
    manifest = _read(manifest_path)
    producer_prereg_sha = campaign.canonical_sha256(prereg)
    if (manifest.get("pre-registration_sha256") != producer_prereg_sha or
            manifest.get("implementation_version") != campaign.IMPLEMENTATION_VERSION or
            manifest.get("campaign_id") != f"{campaign.IMPLEMENTATION_VERSION}_{producer_prereg_sha[:16]}"):
        raise RuntimeError("pilot campaign manifest identity mismatch")
    rows = {row.get("point_id"): row for row in manifest.get(
        "completed_or_checkpointed_points", [])}
    for point_id in PILOT_POINT_IDS:
        row = rows.get(point_id)
        if not isinstance(row, dict) or row.get("classification") != "PERIOD_1":
            raise RuntimeError(f"historical pilot point is not intact PERIOD_1: {point_id}")
        for field, digest_field in (("result_path", "result_sha256"),
                                    ("checkpoint_path", "checkpoint_sha256")):
            rel = row.get(field)
            path = root / rel if rel else None
            if path is None or not path.is_file() or _sha(path.read_bytes()) != row.get(digest_field):
                raise RuntimeError(f"historical pilot artifact integrity mismatch: {point_id} {field}")
        result = _read(root / row["result_path"])
        if result.get("classification") != "PERIOD_1" or \
            result.get("bindings", {}).get("preregistration_sha256") != producer_prereg_sha:
            raise RuntimeError(f"historical pilot result binding mismatch: {point_id}")
        if result.get("bindings", {}).get("campaign_producer_sha256") != identity[
                "source_hashes"]["runner"]:
            raise RuntimeError(f"historical pilot producer binding mismatch: {point_id}")
    return manifest


def _validate_extension_manifest(root: Path, point_ids: list[str], prereg_sha: str,
                                 auth_sha: str, identity_sha: str) -> dict:
    path = root / "campaign.json"
    expected_id = f"{campaign.IMPLEMENTATION_VERSION}_{prereg_sha[:16]}_EXT26"
    if not path.is_file():
        rows = [{"point_id": point_id, "classification": "NOT_STARTED",
                 "cycles_completed": None, "next_cycle": None,
                 "checkpoint_path": None, "checkpoint_sha256": None,
                 "result_path": None, "result_sha256": None}
                for point_id in point_ids]
        manifest = {
            "schema": "FULL_RPM_SWEEP_V1_IMPL2_EXTENSION_CAMPAIGN_MANIFEST_V1",
            "campaign_id": expected_id,
            "implementation_version": campaign.IMPLEMENTATION_VERSION,
            "preregistration_sha256": prereg_sha,
            "producer_canonical_preregistration_sha256": campaign.canonical_sha256(
                _read(ROOT / "results/full-rpm-sweep-v1/implementation-v2-campaign-preregistration.json")),
            "authorization_sha256": auth_sha,
            "implementation_identity_sha256": identity_sha,
            "campaign_producer_sha256": _file_sha(ROOT / "scripts/full_rpm_sweep_v1_campaign.py"),
            "execution_supervisor_version": "FULL_RPM_SWEEP_V1_IMPL2_EXTENSION_SUPERVISOR_V1",
            "evidence_pipeline": "CONVENTIONAL_FULL_AUDIT",
            "fast_recipe_enabled": False,
            "scope": point_ids,
            "pilot_artifact_root": str(_artifact_base() / "controlled-pilot-attempt-2"),
            "pilot_artifacts_are_separate_and_read_only": True,
            "campaigns_started": 0,
            "campaign_status": "PREPARED",
            "completed_or_checkpointed_points": rows,
            "invocations": [],
        }
        _atomic_write(path, manifest)
        return manifest
    manifest = _read(path)
    if (manifest.get("campaign_id") != expected_id or
            manifest.get("preregistration_sha256") != prereg_sha or
            manifest.get("authorization_sha256") != auth_sha or
            manifest.get("implementation_identity_sha256") != identity_sha or
            manifest.get("campaign_producer_sha256") != _file_sha(
                ROOT / "scripts/full_rpm_sweep_v1_campaign.py") or
            manifest.get("scope") != point_ids or
            manifest.get("fast_recipe_enabled") is not False):
        raise RuntimeError("extension manifest identity, scope, or authorization mismatch")
    rows = manifest.get("completed_or_checkpointed_points")
    if not isinstance(rows, list) or {row.get("point_id") for row in rows} != set(point_ids):
        raise RuntimeError("extension manifest point catalog mismatch")
    return manifest


def _refresh_point_rows(root: Path, manifest: dict, point_map: dict[str, tuple[dict, int]],
                        prereg: dict, prereg_sha: str) -> bool:
    changed = False
    producer_prereg_sha = campaign.canonical_sha256(prereg)
    catalog = {row["point_id"]: row for row in manifest["completed_or_checkpointed_points"]}
    for point_id, (variant, rpm) in point_map.items():
        row = catalog[point_id]
        point_dir = root / variant["variant_id"] / f"rpm-{rpm:05d}"
        result_path = point_dir / "result.json"
        checkpoint_path = point_dir / "checkpoint.json"
        status_path = point_dir / "checkpoint-status.json"
        result = _read(result_path) if result_path.is_file() else None
        status = _read(status_path) if status_path.is_file() else None
        if result is not None:
            bindings = result.get("bindings", {})
            if (bindings.get("preregistration_sha256") != producer_prereg_sha or
                    bindings.get("campaign_producer_sha256") != _file_sha(
                        ROOT / "scripts/full_rpm_sweep_v1_campaign.py")):
                raise RuntimeError(f"result scientific binding mismatch: {point_id}")
            digest = _sha(result_path.read_bytes())
            if row.get("result_sha256") != digest:
                row.update({"result_path": str(result_path.relative_to(root)),
                            "result_sha256": digest,
                            "classification": result.get("classification"),
                            "cycles_completed": result.get("cycles_completed"),
                            "next_cycle": result.get("next_cycle"),
                            "hard_gates": result.get("hard_gates"),
                            "engineering_outputs": result.get("engineering_outputs"),
                            "performance_metrics": result.get("performance_metrics")})
                changed = True
        elif status is not None and status.get("classification"):
            if row.get("classification") != status["classification"] or \
                    row.get("cycles_completed") != status.get("cycles_completed"):
                row.update({"classification": status["classification"],
                            "cycles_completed": status.get("cycles_completed"),
                            "next_cycle": status.get("next_cycle"),
                            "performance_metrics": status.get("performance_metrics")})
                changed = True
        if checkpoint_path.is_file():
            digest = _sha(checkpoint_path.read_bytes())
            if row.get("checkpoint_sha256") != digest:
                # A worker may have atomically finished a checkpoint just before
                # interruption. Validate its scientific bindings and complete
                # cycle history before the coordinator adopts that exact hash.
                expected_loss = campaign.resolve_mechanical_loss_v1(
                    preregistration_path=ROOT / "results/full-rpm-sweep-v1/implementation-v2-campaign-preregistration.json",
                    variant_id=variant["variant_id"], repository_root=ROOT,
                    rpm_points=prereg["rpm_grid"]["points_rpm"], load=1.0)
                expected = campaign._point_contract_hashes(
                    prereg, producer_prereg_sha, variant, expected_loss, rpm)
                checkpoint = campaign._load_checkpoint(checkpoint_path, expected)
                campaign._checkpoint_cycle_history(point_dir, checkpoint["next_cycle"])
                row.update({"checkpoint_path": str(checkpoint_path.relative_to(root)),
                            "checkpoint_sha256": digest,
                            "next_cycle": checkpoint["next_cycle"],
                            "cycles_completed": checkpoint["next_cycle"] - 1})
                changed = True
    if changed:
        manifest["campaigns_started"] = 1
        manifest["campaign_status"] = "IN_PROGRESS"
    return changed


def _budget_records(ledger_dir: Path) -> tuple[float, list[dict]]:
    consumed = 0.0
    rows = []
    for started_path in sorted(ledger_dir.glob("invocation-*-STARTED.json")):
        start = _read(started_path)
        suffix = started_path.name.removesuffix("-STARTED.json")
        completed_path = ledger_dir / f"{suffix}-COMPLETED.json"
        if completed_path.is_file():
            completed = _read(completed_path)
            duration = float(completed["duration_seconds"])
        else:
            duration = min(INVOCATION_LIMIT_SECONDS,
                           max(0.0, time.time() - float(start["started_at_unix"])))
        consumed += duration
        rows.append({"invocation_id": start["invocation_id"],
                     "status": "COMPLETED" if completed_path.is_file() else "OPEN_OR_INTERRUPTED",
                     "duration_seconds": duration})
    return consumed, rows


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _create_invocation_start(ledger_dir: Path, auth_sha: str, maximum: int) -> tuple[str, Path, float]:
    ledger_dir.mkdir(parents=True, exist_ok=True)
    consumed, records = _budget_records(ledger_dir)
    for record in records:
        if record["status"] == "OPEN_OR_INTERRUPTED":
            starts = list(ledger_dir.glob(f"{record['invocation_id']}-STARTED.json"))
            if starts and _pid_alive(int(_read(starts[0]).get("pid", 0))):
                raise RuntimeError("another extension supervisor invocation is active")
    remaining = GLOBAL_BUDGET_SECONDS - consumed
    if remaining <= 0:
        raise RuntimeError("new 21,600-second extension budget is exhausted")
    invocation_limit = min(INVOCATION_LIMIT_SECONDS, maximum, int(remaining))
    if invocation_limit < 1:
        raise RuntimeError("no invocation budget remains")
    invocation_id = f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{uuid.uuid4().hex[:8]}"
    started = time.time()
    receipt = {"schema": "FULL_RPM_SWEEP_V1_IMPL2_EXTENSION_INVOCATION_STARTED_V1",
               "invocation_id": invocation_id,
               "authorization_sha256": auth_sha,
               "started_at_utc": datetime.now(timezone.utc).isoformat(),
               "started_at_unix": started,
               "pid": os.getpid(),
               "maximum_wall_seconds": invocation_limit,
               "global_budget_seconds": GLOBAL_BUDGET_SECONDS,
               "global_budget_consumed_before_seconds": consumed}
    path = ledger_dir / f"invocation-{invocation_id}-STARTED.json"
    _write_exclusive(path, receipt)
    return invocation_id, path, float(invocation_limit)


def _finish_invocation(ledger_dir: Path, invocation_id: str, started_monotonic: float,
                       result: dict) -> float:
    duration = time.monotonic() - started_monotonic
    started_path = next(ledger_dir.glob(f"invocation-{invocation_id}-STARTED.json"))
    started = _read(started_path)
    completion = {"schema": "FULL_RPM_SWEEP_V1_IMPL2_EXTENSION_INVOCATION_COMPLETED_V1",
                  "invocation_id": invocation_id,
                  "started_receipt_sha256": _file_sha(started_path),
                  "finished_at_utc": datetime.now(timezone.utc).isoformat(),
                  "duration_seconds": duration,
                  "authorization_sha256": started["authorization_sha256"],
                  "result_classification": result.get("campaign_status"),
                  "results": result.get("invocation_results", [])}
    _write_exclusive(ledger_dir / f"invocation-{invocation_id}-COMPLETED.json", completion)
    return duration


def _acquire_lock(root: Path) -> Path:
    lock = root / ".extension-coordinator.lock"
    lock.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        try:
            pid = int(lock.read_text(encoding="ascii").strip().split()[0])
        except (OSError, ValueError, IndexError):
            raise RuntimeError("unreadable extension coordinator lock; refusing concurrent writes")
        if _pid_alive(pid):
            raise RuntimeError("extension coordinator already active")
        lock.unlink()
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    with os.fdopen(fd, "w", encoding="ascii") as stream:
        stream.write(f"{os.getpid()} {time.time()}\n")
        stream.flush()
        os.fsync(stream.fileno())
    return lock


def _run_invocation(*, resume: bool, workers: int, memory_budget_mib: int,
                    max_seconds: int) -> dict:
    total_started = time.monotonic()
    auth_path = ROOT / AUTHORIZATION_RELATIVE
    auth_sha = _file_sha(auth_path)
    if workers < 1 or workers > WORKER_LIMIT or memory_budget_mib < 512 or \
            memory_budget_mib > MEMORY_LIMIT_MIB:
        raise ValueError("workers or memory exceed the explicit extension authorization")
    if max_seconds < 1 or max_seconds > INVOCATION_LIMIT_SECONDS:
        raise ValueError("invocation limit must be in [1, 3600]")
    root = _artifact_base() / EXTENSION_NAME
    if not root.resolve().is_relative_to(_artifact_base().resolve()):
        raise RuntimeError("extension artifact root escaped IMPL2 isolated root")
    ledger_dir = root / "authorization-ledger"
    root.mkdir(parents=True, exist_ok=True)
    lock = _acquire_lock(root)
    invocation_id = None
    started_mono = time.monotonic()
    completion_result = {"campaign_status": "FAILED_OR_INTERRUPTED", "invocation_results": []}
    try:
        invocation_id, _, invocation_limit = _create_invocation_start(
            ledger_dir, auth_sha, max_seconds)
        prereg, prereg_sha, identity, points, authorization = _preflight()
        point_ids = sorted(_point_id(v, rpm) for v, rpm in points)
        identity_sha = _file_sha(ROOT / "results/full-rpm-sweep-v1/implementation-v2-campaign-identity.json")
        budget = max(1, int(invocation_limit))
        execution_budget = max(1, budget - min(SHUTDOWN_HEADROOM_SECONDS,
                                                 max(1, budget // 20)) -
                           min(15, max(0, budget - min(SHUTDOWN_HEADROOM_SECONDS,
                                                       max(1, budget // 20)) - 1)))
        execution_deadline = started_mono + execution_budget
        manifest = _validate_extension_manifest(
            root, point_ids, prereg_sha, auth_sha, identity_sha)
        point_map = {_point_id(v, rpm): (v, rpm) for v, rpm in points}
        manifest_rows = {row["point_id"]: row for row in manifest[
            "completed_or_checkpointed_points"]}
        if not resume and any(row.get("classification") != "NOT_STARTED"
                              for row in manifest_rows.values()):
            raise RuntimeError("extension contains work; resume must be explicit")
        if resume:
            changed = _refresh_point_rows(root, manifest, point_map, prereg, prereg_sha)
            if changed:
                _atomic_write(root / "campaign.json", manifest)
        pending = []
        terminal = {"PERIOD_1", "PERIOD_2", "NO_CONVERGENCE_WITHIN_HORIZON",
                    "NUMERICAL_INVALID", "PRIMARY_AUDIT_FAIL", "PHYSICAL_INVALID"}
        for variant, rpm in points:
            pid = _point_id(variant, rpm)
            row = manifest_rows[pid]
            if row.get("classification") in terminal:
                if not row.get("result_sha256"):
                    raise RuntimeError(f"terminal result lacks manifest hash: {pid}")
                continue
            if row.get("classification") not in {"NOT_STARTED", "INTERRUPTED_CHECKPOINTED",
                                                    "IN_PROGRESS_CHECKPOINTED", "RUNNING"}:
                raise RuntimeError(f"unrecognized prior classification for {pid}")
            pending.append((variant, rpm))
        manifest["campaigns_started"] = 1 if pending or manifest.get("campaigns_started") else 0
        manifest["campaign_status"] = "IN_PROGRESS" if pending else "COMPLETE"
        _atomic_write(root / "campaign.json", manifest)
        invocation_results: list[dict] = []
        if not pending:
            manifest["campaign_status"] = "COMPLETE"
            completion_result = {**manifest, "invocation_results": invocation_results}
            return completion_result

        try:
            import psutil
            available_memory = int(psutil.virtual_memory().available)
        except ImportError:
            available_memory = memory_budget_mib * 1024 * 1024
        plan = campaign._parallel_worker_plan(
            workers, memory_budget_mib * 1024 * 1024,
            available_memory_bytes=available_memory)
        context = multiprocessing.get_context("spawn")
        manager = context.Manager()
        cancel_event = manager.Event()
        executor = concurrent.futures.ProcessPoolExecutor(
            max_workers=plan["effective_workers"], mp_context=context)
        iterator = iter(pending)
        futures: dict[concurrent.futures.Future, tuple[dict, int]] = {}
        worker_started = started_mono

        def submit_next() -> bool:
            if time.monotonic() >= execution_deadline:
                return False
            try:
                variant, rpm = next(iterator)
            except StopIteration:
                return False
            future = executor.submit(
                campaign._run_point_process, prereg, campaign.canonical_sha256(prereg), variant, rpm,
                str(root), resume, worker_started, execution_budget, cancel_event,
                "results/full-rpm-sweep-v1/implementation-v2-campaign-preregistration.json")
            futures[future] = (variant, rpm)
            return True

        for _ in range(plan["effective_workers"]):
            if not submit_next():
                break
        while futures:
            remaining = max(0.0, execution_deadline - time.monotonic())
            done, _ = concurrent.futures.wait(
                futures, timeout=min(1.0, remaining),
                return_when=concurrent.futures.FIRST_COMPLETED)
            if _refresh_point_rows(root, manifest, point_map, prereg, prereg_sha):
                _atomic_write(root / "campaign.json", manifest)
            if not done and time.monotonic() < execution_deadline:
                continue
            expired = time.monotonic() >= execution_deadline
            if expired:
                cancel_event.set()
                for future in futures:
                    future.cancel()
            should_stop = False
            for future in done:
                variant, rpm = futures.pop(future)
                point_result = future.result()
                pid = _point_id(variant, rpm)
                invocation_results.append({"point_id": pid,
                                           "classification": point_result["classification"],
                                           "cycles_completed": point_result.get("cycles_completed")})
                if point_result["classification"] == "INTERRUPTED_CHECKPOINTED":
                    should_stop = True
            changed = _refresh_point_rows(root, manifest, point_map, prereg, prereg_sha)
            if done or changed:
                _atomic_write(root / "campaign.json", manifest)
            if should_stop:
                cancel_event.set()
                for future in futures:
                    future.cancel()
                expired = True
            if expired:
                # Wait only through the explicit shutdown headroom; every live
                # producer checks cancellation at a complete-cycle boundary.
                done_remaining, not_done = concurrent.futures.wait(
                    futures, timeout=min(SHUTDOWN_HEADROOM_SECONDS,
                                        max(1, budget - execution_budget -
                                            min(15, max(0, budget - execution_budget - 1)))),
                    return_when=concurrent.futures.ALL_COMPLETED)
                if not_done:
                    raise TimeoutError("workers did not reach checkpoint shutdown within headroom")
                for future in done_remaining:
                    variant, rpm = futures.pop(future)
                    point_result = future.result()
                    invocation_results.append({"point_id": _point_id(variant, rpm),
                                               "classification": point_result["classification"],
                                               "cycles_completed": point_result.get("cycles_completed")})
                _refresh_point_rows(root, manifest, point_map, prereg, prereg_sha)
                _atomic_write(root / "campaign.json", manifest)
                break
            for _ in done:
                submit_next()

        executor.shutdown(wait=True, cancel_futures=True)
        manager.shutdown()
        # Detect worker failures and reflect exact durable outputs before close.
        _refresh_point_rows(root, manifest, point_map, prereg, prereg_sha)
        terminal_count = sum(row.get("classification") in terminal for row in
                             manifest["completed_or_checkpointed_points"])
        manifest["campaign_status"] = "COMPLETE" if terminal_count == 26 else \
            "INTERRUPTED_CHECKPOINTED" if any(
                row.get("classification") == "INTERRUPTED_CHECKPOINTED"
                for row in manifest["completed_or_checkpointed_points"]) else "PARTIAL_IN_PROGRESS"
        manifest["last_invocation"] = {"invocation_id": invocation_id,
                                       "duration_seconds": time.monotonic() - total_started,
                                       "requested_workers": workers,
                                       "effective_workers": plan["effective_workers"],
                                       "memory_budget_mib": memory_budget_mib,
                                       "worker_reservation_mib": WORKER_RESERVE_MIB,
                                       "execution_budget_seconds": execution_budget,
                                       "python_version": sys.version,
                                       "platform": platform.platform(),
                                       "supervisor_sha256": _file_sha(Path(__file__))}
        _atomic_write(root / "campaign.json", manifest)
        manifest["invocation_results"] = invocation_results
        completion_result = manifest
        return completion_result
    finally:
        if invocation_id is not None:
            try:
                _finish_invocation(ledger_dir, invocation_id, started_mono,
                                   completion_result)
            except FileExistsError:
                pass
        try:
            lock.unlink()
        except FileNotFoundError:
            pass


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--implementation", required=True, choices=["impl2"])
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--memory-budget-mib", type=int, default=4096)
    parser.add_argument("--max-seconds", type=int, default=3600)
    args = parser.parse_args(argv)
    if not args.execute:
        _preflight()
        print(json.dumps({"preflight": "PASS", "execution": "NOT_STARTED"}))
        return 0
    result = _run_invocation(resume=args.resume, workers=args.workers,
                             memory_budget_mib=args.memory_budget_mib,
                             max_seconds=args.max_seconds)
    print(json.dumps({"campaign_status": result.get("campaign_status"),
                      "extension_root": str(_artifact_base() / EXTENSION_NAME),
                      "invocation_results": result.get("invocation_results", []),
                      "completed_or_checkpointed_points": result.get(
                          "completed_or_checkpointed_points", [])},
                     sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
