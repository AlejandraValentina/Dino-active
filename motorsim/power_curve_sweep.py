"""Bounded, resumable orchestration for exploratory integrated RPM curves.

Each RPM delegates to the existing independently audited single-point workflow.
This module adds only a serial coordinator and its own atomic sweep manifest.
It does not change solver identity, periodicity, or result classification.
"""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
import threading
import time
import uuid
from contextlib import contextmanager
from pathlib import Path

from .engine_configuration import identity
from .exploratory_workflow import preflight, run_exploratory
from .power_curve import plan_rpm_range


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def _atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    temp = Path(name)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(json.dumps(value, indent=2, ensure_ascii=False,
                                    allow_nan=False).encode("utf-8") + b"\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def _pid_is_alive(pid: int) -> bool:
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
        kernel32.OpenProcess.restype = wintypes.HANDLE
        kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
        kernel32.CloseHandle.restype = wintypes.BOOL
        handle = kernel32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
        if handle:
            kernel32.CloseHandle(handle)
            return True
        return ctypes.get_last_error() not in (87, 1168)  # invalid parameter / not found
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


@contextmanager
def _coordinator_lock(path: Path):
    """Serialize one sweep; quarantine only a lock whose recorded PID is dead."""
    path.parent.mkdir(parents=True, exist_ok=True)
    token = uuid.uuid4().hex
    payload = _canonical({"pid": os.getpid(), "token": token,
                          "created_unix": time.time(), "schema": "DINO_SWEEP_LOCK_V1"})
    while True:
        try:
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            with os.fdopen(fd, "wb") as stream:
                stream.write(payload); stream.flush(); os.fsync(stream.fileno())
            break
        except FileExistsError as exc:
            try:
                current = json.loads(path.read_text(encoding="utf-8"))
                pid = current.get("pid")
                if current.get("schema") != "DINO_SWEEP_LOCK_V1" or type(pid) is not int or pid <= 0:
                    raise ValueError("sweep coordinator lock is malformed; preserved for review") from exc
                try:
                    alive = _pid_is_alive(pid)
                except OSError as probe_error:
                    raise RuntimeError("cannot determine whether coordinator is active; lock preserved") from probe_error
                if not alive:
                    quarantine = path.with_name(path.name + f".orphaned-{uuid.uuid4().hex}")
                    try: os.replace(path, quarantine)
                    except FileNotFoundError: continue
                else:
                    raise RuntimeError("another sweep coordinator is active; lock preserved") from exc
            except (OSError, json.JSONDecodeError) as read_error:
                raise RuntimeError("cannot verify existing sweep lock; preserved for review") from read_error
    try:
        yield
    finally:
        try:
            current = json.loads(path.read_text(encoding="utf-8"))
            if current.get("token") == token:
                path.unlink(missing_ok=True)
        except (OSError, json.JSONDecodeError):
            pass


def prepare_power_curve(document: dict, *, project_id: str, variant_label: str,
                        artifact_root: str | Path, start_rpm: int, stop_rpm: int,
                        step_rpm: int, max_cycles: int, point_budget_seconds: float,
                        total_budget_seconds: float, memory_limit_mib: int) -> dict:
    """Preflight the whole requested grid without taking a solver step."""
    rpms = plan_rpm_range(start_rpm, stop_rpm, step_rpm)
    if len(rpms) > 30:
        raise ValueError("a single sweep is limited to 30 requested RPM points")
    if (not project_id or any(ch not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_" for ch in project_id)
            or not variant_label):
        raise ValueError("project and variant labels must be explicit")
    if type(max_cycles) is not int or not 1 <= max_cycles <= 111:
        raise ValueError("max_cycles must be from 1 through 111")
    if type(point_budget_seconds) not in (int, float) or not 1 <= point_budget_seconds <= 600:
        raise ValueError("per-point budget must be between 1 and 600 seconds")
    if type(total_budget_seconds) not in (int, float) or not 1 <= total_budget_seconds <= 3600:
        raise ValueError("total budget must be between 1 and 3600 seconds")
    if type(memory_limit_mib) is not int or not 256 <= memory_limit_mib <= 4096:
        raise ValueError("memory limit must be from 256 through 4096 MiB")
    root = Path(artifact_root).expanduser().resolve()
    from .desktop.preferences import repository_root_containing
    repository = repository_root_containing(root)
    if repository is not None:
        raise ValueError(f"artifact root is inside repository: {repository}")
    checks = [preflight(document, rpm=rpm, max_cycles=max_cycles,
                        budget_seconds=point_budget_seconds,
                        memory_limit_mib=memory_limit_mib) for rpm in rpms]
    return {"schema": "DINO_POWER_CURVE_PREFLIGHT_V1", "status": "PASS",
            "solver_steps": 0, "project_id": project_id,
            "variant_label": variant_label, "rpms": rpms,
            "identity_sha256": identity(document),
            "max_cycles": max_cycles,
            "point_budget_seconds": float(point_budget_seconds),
            "total_budget_seconds": float(total_budget_seconds),
            "memory_limit_mib": memory_limit_mib,
            "artifact_root": str(root), "point_preflights": checks}


def _run_power_curve_unlocked(document: dict, *, project_id: str, variant_label: str,
                    artifact_root: str | Path, start_rpm: int, stop_rpm: int,
                    step_rpm: int, max_cycles: int = 24,
                    point_budget_seconds: float = 600,
                    total_budget_seconds: float = 1800,
                    memory_limit_mib: int = 1024, sweep_id: str | None = None,
                    resume: bool = False, cancel_event=None, progress=None) -> dict:
    """Run a bounded serial sweep; interruption leaves point and series checkpoints."""
    prepared = prepare_power_curve(document, project_id=project_id,
        variant_label=variant_label, artifact_root=artifact_root,
        start_rpm=start_rpm, stop_rpm=stop_rpm, step_rpm=step_rpm,
        max_cycles=max_cycles, point_budget_seconds=point_budget_seconds,
        total_budget_seconds=total_budget_seconds, memory_limit_mib=memory_limit_mib)
    sweep_id = sweep_id or uuid.uuid4().hex
    if not sweep_id or any(ch not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_" for ch in sweep_id):
        raise ValueError("sweep_id contains unsupported characters")
    root = Path(prepared["artifact_root"]) / "dino-power-curve-v1" / project_id / sweep_id
    manifest_path = root / "series.json"
    binding = {key: prepared[key] for key in ("project_id", "variant_label", "rpms",
        "identity_sha256", "max_cycles", "point_budget_seconds", "total_budget_seconds",
        "memory_limit_mib", "artifact_root")}
    binding["document_sha256"] = _sha(_canonical(document))
    if manifest_path.exists():
        if not resume:
            raise FileExistsError("sweep exists; explicit resume is required")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("bindings") != binding:
            raise ValueError("resume rejected: sweep configuration binding mismatch")
        if manifest.get("schema") != "DINO_POWER_CURVE_SWEEP_V1":
            raise ValueError("resume rejected: unsupported sweep manifest")
    else:
        if resume:
            quarantined = (root.exists() and all(
                child.name.startswith(".coordinator.lock.orphaned-") for child in root.iterdir()))
            if not quarantined:
                raise FileNotFoundError("cannot resume: sweep manifest does not exist and the root is not an empty quarantined start")
        manifest = {"schema": "DINO_POWER_CURVE_SWEEP_V1", "status": "READY",
            "classification": "EXPLORATORY_CURVE_NOT_YET_AVAILABLE",
            "bindings": binding, "points": [], "created_unix": time.time(),
            "elapsed_seconds": 0.0}
        _atomic_json(manifest_path, manifest)
    existing = {row["rpm"]: row for row in manifest.get("points", [])}
    if len(existing) != len(manifest.get("points", [])) or set(existing) - set(prepared["rpms"]):
        raise ValueError("resume rejected: duplicate or out-of-grid point in series manifest")
    # Validate all saved per-point bindings before continuing any work.
    for rpm, row in existing.items():
        point_check = prepared["point_preflights"][prepared["rpms"].index(rpm)]
        if (row.get("identity_sha256") != point_check["identity_sha256"] or
                row.get("configuration_sha256", point_check["configuration_sha256"]) != point_check["configuration_sha256"] or
                row.get("mechanical_loss_model_sha256", point_check["mechanical_loss_model_sha256"]) != point_check["mechanical_loss_model_sha256"]):
            raise ValueError(f"resume rejected: point identity mismatch at {rpm} RPM")
        if row.get("run_directory"):
            run_dir = Path(row["run_directory"])
            run_manifest = run_dir / "run.json"
            if not run_manifest.is_file():
                raise ValueError(f"resume rejected: point manifest missing at {rpm} RPM")
            point_manifest = json.loads(run_manifest.read_text(encoding="utf-8"))
            if (point_manifest.get("bindings", {}).get("identity_sha256") != row["identity_sha256"] or
                    point_manifest.get("bindings", {}).get("configuration_sha256") != point_check["configuration_sha256"]):
                raise ValueError(f"resume rejected: point run binding mismatch at {rpm} RPM")
            if row.get("result_artifact_sha256") and point_manifest.get("result_sha256") != row["result_artifact_sha256"]:
                raise ValueError(f"resume rejected: point result hash mismatch at {rpm} RPM")
            checkpoint_name = point_manifest.get("checkpoint_artifact")
            engineering = point_manifest.get('schema') == 'DINO_ENGINEERING_RUN_V1'
            if (not isinstance(checkpoint_name, str) or Path(checkpoint_name).is_absolute() or
                    '..' in Path(checkpoint_name).parts or
                    (not engineering and Path(checkpoint_name).name != checkpoint_name)):
                raise ValueError(f"resume rejected: point checkpoint path is invalid at {rpm} RPM")
            checkpoint_path = run_dir / checkpoint_name
            if not checkpoint_path.resolve().is_relative_to(run_dir.resolve()):
                raise ValueError(f"resume rejected: point checkpoint escapes run directory at {rpm} RPM")
            if (not checkpoint_path.is_file() or
                    _sha(checkpoint_path.read_bytes()) != point_manifest.get("checkpoint_sha256") or
                    (row.get("checkpoint_sha256") and _sha(checkpoint_path.read_bytes()) != row["checkpoint_sha256"])):
                raise ValueError(f"resume rejected: point checkpoint hash mismatch at {rpm} RPM")
            if row.get("status") == "COMPLETE":
                if engineering:
                    from .engineering_workflow import import_desktop_runs
                    verified=import_desktop_runs([run_dir])
                    if not verified.get('points') or any(item.get('audit_status')!='NOT_PERFORMED' for item in verified['points']):
                        raise ValueError('engineering result verification failed')
                    row['resume_audit']='INTEGRITY_VERIFIED_NOT_INDEPENDENT_AUDIT'
                    continue
                from .exploratory_workflow import import_exploratory_runs
                audited = import_exploratory_runs([run_dir])
                if (not audited.get("points") or
                        not all(item.get("audit_recomputed") is True for item in audited["points"]) or
                        (row.get("result_canonical_sha256") and
                         json.loads((run_dir / "result.json").read_text(encoding="utf-8")).get("result_sha256") != row["result_canonical_sha256"])):
                    raise ValueError(f"resume rejected: completed point independent re-audit failed at {rpm} RPM")
                row["resume_audit"] = "PASS_RECOMPUTED"

    started = time.monotonic()
    elapsed_before = float(manifest.get("elapsed_seconds", 0.0))
    # If the coordinator died while a point was active, charge its observed wall
    # time before calculating the remaining cumulative sweep budget.
    for row in existing.values():
        if row.get("status") == "RUNNING":
            run_started = row.get("started_unix")
            if type(run_started) not in (int, float) or run_started <= 0:
                raise ValueError("resume rejected: running point has no valid start timestamp")
            elapsed_before += max(0.0, time.time() - float(run_started))
            row["status"] = "INTERRUPTED_CHECKPOINTED"
            row["classification"] = "EXPLORATORY_COORDINATOR_INTERRUPTED_CHECKPOINTED"
            row["last_interruption"] = "COORDINATOR_EXIT_OBSERVED_ON_RESUME"
    manifest["elapsed_seconds"] = elapsed_before
    manifest["points"] = [existing.get(value, {"rpm": value, "status": "NOT_STARTED",
        "classification": "NOT_STARTED", "identity_sha256": prepared["point_preflights"][i]["identity_sha256"]})
        for i, value in enumerate(prepared["rpms"])]
    manifest["status"] = "RUNNING"
    manifest["classification"] = "EXPLORATORY_SWEEP_IN_PROGRESS"
    _atomic_json(manifest_path, manifest)
    for index, rpm in enumerate(prepared["rpms"]):
        if rpm in existing and existing[rpm].get("status") == "COMPLETE":
            continue
        if cancel_event is not None and cancel_event.is_set():
            manifest["status"] = "INTERRUPTED_CHECKPOINTED"
            manifest["classification"] = "EXPLORATORY_SWEEP_CANCELLED"
            break
        if elapsed_before + time.monotonic() - started >= total_budget_seconds:
            manifest["status"] = "INTERRUPTED_CHECKPOINTED"
            manifest["classification"] = "EXPLORATORY_SWEEP_TOTAL_BUDGET_EXHAUSTED"
            break
        check = prepared["point_preflights"][index]
        point = existing.get(rpm, {"rpm": rpm, "status": "NOT_STARTED",
            "classification": "NOT_STARTED", "identity_sha256": check["identity_sha256"],
            "configuration_sha256": check["configuration_sha256"],
            "mechanical_loss_model_sha256": check["mechanical_loss_model_sha256"],
            "fuel_id": check["fuel_id"], "periodicity_contract": check["periodicity_contract"],
            "total_finite_volume_cells": check["total_finite_volume_cells"]})
        for key in ("configuration_sha256", "mechanical_loss_model_sha256", "fuel_id",
                    "periodicity_contract", "total_finite_volume_cells"):
            point.setdefault(key, check[key])
        run_id = point.get("run_id") or f"pc-{sweep_id}-{rpm}"
        point["run_id"] = run_id
        from .exploratory_workflow import _run_directory
        point["run_directory"] = str(_run_directory(Path(prepared["artifact_root"]), project_id, run_id))
        point["started_unix"] = time.time()
        point["status"] = "RUNNING"
        point["classification"] = "RUNNING"
        manifest["points"] = [existing.get(value, point if value == rpm else
            {"rpm": value, "status": "NOT_STARTED", "classification": "NOT_STARTED",
             "identity_sha256": prepared["point_preflights"][i]["identity_sha256"]})
            for i, value in enumerate(prepared["rpms"])]
        _atomic_json(manifest_path, manifest)
        try:
            remaining = total_budget_seconds - elapsed_before - (time.monotonic() - started)
            if remaining < 1:
                manifest["status"] = "INTERRUPTED_CHECKPOINTED"
                manifest["classification"] = "EXPLORATORY_SWEEP_TOTAL_BUDGET_EXHAUSTED"
                _atomic_json(manifest_path, manifest)
                break
            deadline_cancel = threading.Event()
            class _CombinedCancel:
                def is_set(self):
                    return deadline_cancel.is_set() or (cancel_event is not None and cancel_event.is_set())
            point_cancel = _CombinedCancel()
            timer = threading.Timer(min(point_budget_seconds, remaining), deadline_cancel.set)
            timer.daemon = True
            timer.start()
            def point_progress(row):
                if progress:
                    progress({"rpm": rpm, "solver_progress": row,
                              "point_index": index + 1, "point_count": len(prepared["rpms"])})
            result = run_exploratory(document, project_id=project_id, run_id=run_id,
                artifact_root=prepared["artifact_root"], rpm=rpm,
                max_cycles=max_cycles, budget_seconds=min(point_budget_seconds, remaining),
                memory_limit_mib=memory_limit_mib, resume=(point.get("run_directory") is not None and Path(point["run_directory"]).exists()),
                cancel_event=point_cancel, progress=point_progress, variant_label=variant_label)
            timer.cancel()
            point.update({"status": result.get("status"), "classification": result.get("classification"),
                "periodicity": result.get("periodicity"), "cycles_completed": result.get("cycles_completed"),
                "elapsed_seconds": result.get("elapsed_seconds"),
                "checkpoint_sha256": result.get("checkpoint_sha256"),
                "result_canonical_sha256": result.get("result_sha256"),
                "result_artifact_sha256": _sha((Path(result.get("artifact_directory")) / "result.json").read_bytes()),
                "run_directory": result.get("artifact_directory"),
                "identity_sha256": result.get("bindings", {}).get("identity_sha256", point["identity_sha256"])})
            point["configuration_sha256"] = result.get("bindings", {}).get("configuration_sha256", point["configuration_sha256"])
            point["source_hashes"] = result.get("source_hashes",result.get("bindings", {}).get("source_hashes"))
        except Exception as exc:
            if 'timer' in locals(): timer.cancel()
            point.update({"status": "FAILED_CLOSED", "classification": "FAIL_CLOSED",
                          "failure": f"{type(exc).__name__}: {exc}"})
            manifest["points"] = [existing.get(value, point if value == rpm else
                {"rpm": value, "status": "NOT_STARTED", "classification": "NOT_STARTED",
                 "identity_sha256": prepared["point_preflights"][i]["identity_sha256"]})
                for i, value in enumerate(prepared["rpms"])]
            manifest["points"][index] = point
            manifest["status"] = "FAILED_CLOSED"
            manifest["classification"] = "EXPLORATORY_SWEEP_POINT_FAILED_CLOSED"
            manifest["elapsed_seconds"] = elapsed_before + time.monotonic() - started
            _atomic_json(manifest_path, manifest)
            raise
        existing[rpm] = point
        manifest["points"] = [existing.get(value, {"rpm": value, "status": "NOT_STARTED",
            "classification": "NOT_STARTED", "identity_sha256": prepared["point_preflights"][i]["identity_sha256"]})
            for i, value in enumerate(prepared["rpms"])]
        manifest["elapsed_seconds"] = elapsed_before + time.monotonic() - started
        if progress:
            progress({"point_index": index + 1, "point_count": len(prepared["rpms"]),
                      "rpm": rpm, "point": point, "elapsed_seconds": manifest["elapsed_seconds"]})
        if point["status"] != "COMPLETE":
            manifest["status"] = "INTERRUPTED_CHECKPOINTED" if point["status"] == "INTERRUPTED_CHECKPOINTED" else "PARTIAL"
            manifest["classification"] = point["classification"]
            _atomic_json(manifest_path, manifest)
            break
        _atomic_json(manifest_path, manifest)
    else:
        manifest["status"] = "COMPLETE" if all(row.get("status") == "COMPLETE" for row in manifest["points"]) else "PARTIAL"
        manifest["classification"] = ("EXPLORATORY_SWEEP_EXECUTION_COMPLETE" if manifest["status"] == "COMPLETE"
                                      else "EXPLORATORY_SWEEP_PARTIAL")
    manifest["curve_availability"] = ("EXPLORATORY_CURVE_AVAILABLE"
        if manifest["status"] == "COMPLETE" and all(row.get("periodicity") in {"PERIOD_1", "PERIOD_2", "PERIOD_1_OBSERVED_EXPLORATORY_UNAUDITED"} for row in manifest["points"])
        else "EXPLORATORY_CURVE_PARTIAL")
    manifest["elapsed_seconds"] = elapsed_before + time.monotonic() - started
    manifest["updated_unix"] = time.time()
    _atomic_json(manifest_path, manifest)
    manifest["artifact_directory"] = str(root)
    return manifest


def run_power_curve(document: dict, *, project_id: str, variant_label: str,
                    artifact_root: str | Path, start_rpm: int, stop_rpm: int,
                    step_rpm: int, max_cycles: int = 24,
                    point_budget_seconds: float = 600,
                    total_budget_seconds: float = 1800,
                    memory_limit_mib: int = 1024, sweep_id: str | None = None,
                    resume: bool = False, cancel_event=None, progress=None) -> dict:
    """Lock one sweep coordinator identity and preserve single-writer manifests."""
    sweep_id = sweep_id or uuid.uuid4().hex
    if not sweep_id or any(ch not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_" for ch in sweep_id):
        raise ValueError("sweep_id contains unsupported characters")
    prepared = prepare_power_curve(document, project_id=project_id,
        variant_label=variant_label, artifact_root=artifact_root,
        start_rpm=start_rpm, stop_rpm=stop_rpm, step_rpm=step_rpm,
        max_cycles=max_cycles, point_budget_seconds=point_budget_seconds,
        total_budget_seconds=total_budget_seconds, memory_limit_mib=memory_limit_mib)
    root = Path(prepared["artifact_root"]) / "dino-power-curve-v1" / project_id / sweep_id
    with _coordinator_lock(root / ".coordinator.lock"):
        return _run_power_curve_unlocked(document, project_id=project_id,
            variant_label=variant_label, artifact_root=prepared["artifact_root"],
            start_rpm=start_rpm, stop_rpm=stop_rpm, step_rpm=step_rpm,
            max_cycles=max_cycles, point_budget_seconds=point_budget_seconds,
            total_budget_seconds=total_budget_seconds, memory_limit_mib=memory_limit_mib,
            sweep_id=sweep_id, resume=resume, cancel_event=cancel_event, progress=progress)
