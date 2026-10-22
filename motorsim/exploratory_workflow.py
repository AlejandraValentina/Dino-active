"""Versioned, local-only execution for one explicitly selected engine point.

This route is deliberately separate from FULL_RPM_SWEEP campaign runners.
Every complete cycle is written in the conventional primary format and
independently reconstructed before a result or restart checkpoint is accepted.
"""
from __future__ import annotations

import ctypes
import gzip
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import tempfile
import time
import zlib
from copy import deepcopy
from typing import Any

from .engine_configuration import (canonical_json, implementation_source_hashes,
                                   resolve_for_operating_point, sha256)
from .integrated_2t import (IntegratedEngine2T, audit_integrated_cycle_primary,
                            make_integrated_cycle_primary,
                            make_integrated_engineering_output)
from .mechanical import MechanicalLossModel
from ._evidence_io import read_primary, write_primary_atomic
from .reference_harness.convergence import (CONTRACT as CYCLE_PRIMARY_CONTRACT,
                                           CONTRACT_V2 as PERIODICITY_CONTRACT_V2,
                                           THRESHOLDS as PERIODICITY_THRESHOLDS_V2,
                                           PeriodicDetectorV2)

try:
    import resource as _resource  # POSIX
except ImportError:  # pragma: no cover - Windows uses GetProcessMemoryInfo.
    _resource = None

SCHEMA = "DINO_EXPLORATORY_RUN_V1"
_RECOVERABLE = ("inadmissible species mass", "CFL limit exceeded",
                "rho/p/Y inadmissible", "integrated dynamic reed state is inadmissible")
MAX_FINITE_VOLUME_CELLS = 128
MAX_RUN_ARTIFACT_BYTES = 512 * 1024 * 1024


class RunCancelled(Exception):
    pass


class RunDeadline(Exception):
    pass


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _periodicity_source_sha256() -> str:
    source = Path(__file__).with_name("reference_harness") / "convergence.py"
    return _sha(source.read_bytes().replace(b"\r\n", b"\n"))


def _replay_equivalent(left: Any, right: Any, path: str = "") -> bool:
    """Compare replay summaries exactly except for floating summation roundoff."""
    if isinstance(left, dict) and isinstance(right, dict):
        return (left.keys() == right.keys() and
                all(_replay_equivalent(left[key], right[key], f"{path}/{key}") for key in left))
    if isinstance(left, list) and isinstance(right, list):
        return len(left) == len(right) and all(
            _replay_equivalent(a, b, f"{path}/{index}")
            for index, (a, b) in enumerate(zip(left, right)))
    if (type(left) in (int, float) and not isinstance(left, bool) and
            type(right) in (int, float) and not isinstance(right, bool)):
        absolute_tolerance = (5e-12 if path.endswith("/energy_balance_residual_j/value")
                             else 2e-21)
        return (math.isfinite(left) and math.isfinite(right) and
                math.isclose(left, right, rel_tol=2e-15, abs_tol=absolute_tolerance))
    return left == right


def _json_bytes(value: Any) -> bytes:
    return (canonical_json(value) + "\n").encode("utf-8")


def _atomic_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    temp = Path(name)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(payload); stream.flush(); os.fsync(stream.fileno())
        os.replace(temp, path)
    finally:
        try: temp.unlink(missing_ok=True)
        except OSError: pass


def _read_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"artifact must contain an object: {path.name}")
    return value


def _periodicity_evaluation_status(*, complete_cycles: int,
                                   comparison_count: int,
                                   invalid_comparison_count: int = 0,
                                   accepted_period: str | None,
                                   termination_reason: str,
                                   failure_kind: str | None = None) -> str:
    """Classify detector evidence independently from the run termination."""
    if accepted_period:
        return "PERIOD_ACCEPTED"
    if invalid_comparison_count:
        return "INVALID_COMPARISON_EVIDENCE"
    if termination_reason == "TIMEOUT" and comparison_count:
        return "TIMEOUT_PARTIAL"
    if termination_reason == "CANCELLED" and comparison_count:
        return "CANCELLED_PARTIAL"
    if failure_kind == "NUMERICAL_INVALID":
        return "NUMERICAL_FAILURE"
    if complete_cycles == 0:
        return "NOT_EXECUTED"
    if failure_kind:
        return "EVALUATION_INTERRUPTED_BY_FAILURE"
    if comparison_count == 0:
        return "INSUFFICIENT_EVIDENCE"
    return "EXECUTED_NO_PERIOD_ACCEPTED"


def _prepare_engineering_output_record(primary: dict,
                                       periodicity_evidence: dict | None) -> dict:
    """Attach derived output metadata after the canonical primary is persisted.

    The caller has already serialized and hashed the scientific primary, so it
    is safe to enrich this single-use in-memory object without a JSON roundtrip.
    """
    if periodicity_evidence is not None:
        primary["periodicity_evidence"] = periodicity_evidence
    return primary


def _copy_primary_for_analysis(primary: dict) -> dict:
    """Isolate mutable metadata while sharing the sealed read-only trajectory."""
    return {key: value if key == 'trajectory' else deepcopy(value)
            for key, value in primary.items()}


def _periodicity_comparison_index(records: list[dict]) -> list[dict]:
    """Index persisted comparison vectors without duplicating their metrics."""
    index = []
    for row in records:
        update = row.get("periodicity_update", {})
        outcomes = update.get("outcomes", {})
        for name in ("lag1", "lag2"):
            comparison = outcomes.get(name)
            if comparison is not None:
                index.append({"cycle": row["cycle"], "comparison": name,
                    "branch": outcomes.get("lag2_branch") if name == "lag2" else None,
                    "status": comparison.get("status")})
    return index


def _rss_bytes() -> int:
    if os.name == "nt":
        from ctypes import wintypes
        class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
            _fields_ = [("cb", ctypes.c_ulong), ("PageFaultCount", ctypes.c_ulong),
                        ("PeakWorkingSetSize", ctypes.c_size_t),
                        ("WorkingSetSize", ctypes.c_size_t),
                        ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                        ("QuotaPagedPoolUsage", ctypes.c_size_t),
                        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                        ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                        ("PagefileUsage", ctypes.c_size_t),
                        ("PeakPagefileUsage", ctypes.c_size_t)]
        counters = PROCESS_MEMORY_COUNTERS(); counters.cb = ctypes.sizeof(counters)
        psapi = ctypes.WinDLL("psapi", use_last_error=True)
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        get_process = kernel32.GetCurrentProcess
        get_process.restype = wintypes.HANDLE
        get_info = psapi.GetProcessMemoryInfo
        get_info.argtypes = (wintypes.HANDLE, ctypes.POINTER(PROCESS_MEMORY_COUNTERS), wintypes.DWORD)
        get_info.restype = wintypes.BOOL
        if not get_info(get_process(), ctypes.byref(counters), counters.cb):
            raise OSError(ctypes.get_last_error(), "GetProcessMemoryInfo failed")
        return int(counters.WorkingSetSize)
    if _resource is not None:
        return int(_resource.getrusage(_resource.RUSAGE_SELF).ru_maxrss * 1024)
    raise OSError("process RSS measurement is unavailable on this platform")


def preflight(document: dict, *, rpm: float | None = None,
              max_cycles: int = 1, budget_seconds: float = 60.0,
              memory_limit_mib: int = 1024) -> dict:
    """No-step fail-closed validation of a single exploratory operating point."""
    if type(max_cycles) is not int or not 1 <= max_cycles <= 111:
        raise ValueError("max_cycles must be an integer from 1 through the 111-cycle ceiling")
    if type(budget_seconds) not in (int, float) or not math.isfinite(budget_seconds) or not 1 <= budget_seconds <= 600:
        raise ValueError("budget_seconds must be between 1 and 600 seconds")
    if type(memory_limit_mib) is not int or not 256 <= memory_limit_mib <= 4096:
        raise ValueError("memory_limit_mib must be between 256 and 4096 MiB")
    native=document.get("native_configuration") if isinstance(document,dict) else None
    if not isinstance(native,dict) or document.get("native_configuration_sha256")!=sha256(native):
        raise ValueError("preflight native configuration hash is missing or invalid")
    ducts=native.get("ducts")
    if not isinstance(ducts,list) or not ducts:
        raise ValueError("preflight requires explicit finite-volume duct meshes")
    try:
        cell_count=sum(len(row["mesh"]["volumes"]) for row in ducts)
    except (KeyError,TypeError) as exc:
        raise ValueError("preflight duct mesh/cell inventory is malformed") from exc
    if type(cell_count) is not int or cell_count<=0 or cell_count>MAX_FINITE_VOLUME_CELLS:
        raise ValueError(f"preflight total finite-volume cells must be between 1 and {MAX_FINITE_VOLUME_CELLS}")
    effective = resolve_for_operating_point(document, rpm=rpm)
    engine = IntegratedEngine2T.from_configuration_dict(effective["native_configuration"])
    configured_fuel = effective["native_configuration"].get("fuel_coupled_combustion")
    if configured_fuel is not None:
        fuel_hash = configured_fuel.get("fuel_sha256")
        snapshot_hash = configured_fuel.get("fuel_snapshot", {}).get("sha256")
        declared_hash = effective["fuel_provenance"].get("sha256")
        if (not isinstance(fuel_hash, str) or fuel_hash != snapshot_hash or
                fuel_hash != declared_hash or
                effective["operating_conditions"]["fuel_id"] != fuel_hash):
            raise ValueError("preflight fuel identity/provenance is incompatible with configured combustion")
    loss = MechanicalLossModel.from_dict(effective["mechanical_loss_model"])
    # Constructor validation has already checked topology, thermal and boundary
    # contracts; force geometry evaluation at the chosen point without stepping.
    engine._geometry(engine.angle_deg, engine.reference_rpm)
    displacement = getattr(getattr(engine.slider_crank, "crankcase", None),
                           "displacement_m3", None)
    if type(displacement) not in (int, float) or not math.isfinite(displacement) or displacement <= 0:
        raise ValueError("preflight requires supported positive slider-crank displacement")
    loss_preview = loss.evaluate_2t_net_piston_work(
        net_piston_gas_work_j=0.0, displacement_m3=float(displacement),
        rpm=effective["selected_rpm"],
        load=effective["operating_conditions"]["load"])
    return {"schema": "DINO_EXPLORATORY_PREFLIGHT_V1", "status": "PASS",
            "mode": "EXPLORATORY", "solver_steps": 0,
            "identity_sha256": effective["identity_sha256"],
            "configuration_sha256": effective["native_configuration_sha256"],
            "rpm": effective["selected_rpm"], "max_cycles": max_cycles,
            "budget_seconds": float(budget_seconds),
            "memory_limit_mib": memory_limit_mib, "workers": 1,
            "total_finite_volume_cells":cell_count,
            "artifact_limit_bytes":MAX_RUN_ARTIFACT_BYTES,
            "mechanical_loss_model_sha256": effective["mechanical_loss_model_sha256"],
            "mechanical_loss_preflight": {"compatible": True,
                "friction_mep_pa": loss_preview["friction_mep_pa"],
                "term_mep_pa_by_term": loss_preview["friction_mep_pa_by_term"]},
            "fuel_id": effective["operating_conditions"]["fuel_id"],
            "afr_kg_air_per_kg_fuel": effective["operating_conditions"]["afr"],
            "periodicity_contract": PERIODICITY_CONTRACT_V2,
            "cycle_primary_contract": CYCLE_PRIMARY_CONTRACT,
            "periodicity_source_sha256": _periodicity_source_sha256(),
            "periodicity_thresholds_sha256": _sha(_json_bytes(PERIODICITY_THRESHOLDS_V2)),
            "periodicity_initial": "NOT_EVALUATED",
            "verified_mode": "UNAVAILABLE_WITHOUT_PREREGISTRATION_AND_AUTHORIZATION",
            "classification": "PREFLIGHT_ONLY_NO_SOLVER_STEPS"}


def _advance_cycle(engine: IntegratedEngine2T, cycle: int, *, deadline: float,
                   cancel_event=None, progress=None, memory_limit_mib: int = 1024) -> list[dict]:
    rejected: list[dict] = []
    target_angle = cycle * 360.0
    ports = engine.port_binding.port_set if engine.port_binding is not None else None
    last_progress_angle = -5.0
    last_progress_time = time.monotonic()
    closure_angles = (sorted({angle for duct in ports.ducts
                              for angle in ports.duct_closing_angles(duct.id)})
                      if ports is not None else [])
    while engine.crank_angle_unwrapped_deg < target_angle - 1e-10:
        if cancel_event is not None and cancel_event.is_set():
            raise RunCancelled("cancel requested at solver-step boundary")
        if time.monotonic() >= deadline:
            raise RunDeadline("run budget exhausted at solver-step boundary")
        if _rss_bytes() > memory_limit_mib * 1024 * 1024:
            raise MemoryError("exploratory run exceeded configured process RSS limit")
        angle = engine.crank_angle_unwrapped_deg
        target = min(target_angle, (int((angle + 1e-10) / .5) + 1) * .5)
        scheduled = {float(event) for event in (40, 300, 340, 360)}
        scheduled.update(n * 360.0 + event for n in range(max(0, cycle - 1), cycle + 1)
                         for event in closure_angles)
        for boundary in scheduled:
            if angle < boundary < target:
                target = boundary
        step = target - angle
        for attempt in range(25):
            try:
                engine.step(step / (6.0 * engine.reference_rpm), step)
                break
            except ValueError as exc:
                if not any(reason in str(exc) for reason in _RECOVERABLE):
                    raise
                rejected.append({"angle_deg": angle, "attempted_step_deg": step,
                                 "reason": str(exc)})
                step *= .5
        else:
            raise RuntimeError(f"no admissible step at {angle:.12g} degrees")
        if time.monotonic() >= deadline:
            raise RunDeadline("run budget exhausted immediately after a solver-step boundary")
        if _rss_bytes() > memory_limit_mib * 1024 * 1024:
            raise MemoryError("exploratory run exceeded configured process RSS limit")
        now = time.monotonic()
        if progress is not None and (engine.crank_angle_unwrapped_deg-last_progress_angle >= 5.0 or now-last_progress_time >= 1.0):
            progress({"cycle": cycle, "angle_deg": engine.crank_angle_unwrapped_deg,
                      "cycles_completed": cycle - 1, "rss_bytes": _rss_bytes()})
            last_progress_angle = engine.crank_angle_unwrapped_deg
            last_progress_time = now
    return rejected


def _run_directory(root: Path, project_id: str, run_id: str) -> Path:
    for value, label in ((project_id, "project_id"), (run_id, "run_id")):
        if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,79}", value):
            raise ValueError(f"{label} must be a safe path component")
    base = (root / "exploratory-workflow-v1" / project_id).resolve()
    target = (base / run_id).resolve()
    if base not in target.parents:
        raise ValueError("resolved run path escaped the configured artifact root")
    return target


def _run_exploratory_unlocked(document: dict, *, project_id: str, run_id: str,
                    artifact_root: str | Path, rpm: float | None = None,
                    max_cycles: int = 1, budget_seconds: float = 60.0,
                    memory_limit_mib: int = 1024, resume: bool = False,
                    cancel_event=None, progress=None,
                    variant_label: str = "base") -> dict:
    """Run one user configuration; no campaign runner, campaign manifest, or FAST path."""
    check = preflight(document, rpm=rpm, max_cycles=max_cycles,
                      budget_seconds=budget_seconds, memory_limit_mib=memory_limit_mib)
    effective = resolve_for_operating_point(document, rpm=rpm)
    output = _run_directory(Path(artifact_root), project_id, run_id)
    manifest_path = output / "run.json"
    checkpoint_path = output / "checkpoint.json"
    checkpoint_artifact = "checkpoint.json"
    config_path = output / "configuration.json"
    started = time.monotonic(); deadline = started + float(budget_seconds)
    engine = IntegratedEngine2T.from_configuration_dict(effective["native_configuration"])
    detector = PeriodicDetectorV2()
    # Private temporary evidence storage; checkpoints remain self-contained JSON.
    # The frozen A3b drivers are deliberately not changed to select this path.
    engine.enable_trajectory_spooling()
    records: list[dict] = []
    expected_binding = {"workflow_schema": SCHEMA, "identity_sha256": effective["identity_sha256"],
                        "configuration_sha256": effective["native_configuration_sha256"],
                        "source_hashes": effective["source_hashes"],
                        "periodicity_contract": PERIODICITY_CONTRACT_V2,
                        "cycle_primary_contract": CYCLE_PRIMARY_CONTRACT,
                        "periodicity_source_sha256": _periodicity_source_sha256(),
                        "periodicity_thresholds_sha256": _sha(_json_bytes(PERIODICITY_THRESHOLDS_V2)),
                        "workflow_source_sha256": _sha(Path(__file__).read_bytes()),
                        "project_id": project_id, "variant_label": variant_label,
                        "run_id": run_id}
    configuration_sha = _sha(_json_bytes(effective))
    if output.exists():
        if not resume or not manifest_path.is_file():
            raise FileExistsError("run directory exists; explicit resume requires its manifest and checkpoint")
        existing = _read_json(manifest_path)
        if existing.get("bindings") != expected_binding:
            raise ValueError("resume rejected: run identity/configuration/solver binding mismatch")
        checkpoint_artifact = existing.get("checkpoint_artifact", "checkpoint.json")
        if (not isinstance(checkpoint_artifact, str) or
                Path(checkpoint_artifact).name != checkpoint_artifact or
                not (output / checkpoint_artifact).is_file()):
            raise ValueError("resume rejected: manifest checkpoint artifact is missing or invalid")
        config_payload = config_path.read_bytes()
        if existing.get("configuration_sha256") != _sha(config_payload):
            raise ValueError("resume rejected: executable configuration artifact hash mismatch")
        if json.loads(config_payload) != effective:
            raise ValueError("resume rejected: executable configuration artifact identity mismatch")
        cp_bytes = (output / checkpoint_artifact).read_bytes()
        if _sha(cp_bytes) != existing.get("checkpoint_sha256"):
            raise ValueError("resume rejected: checkpoint artifact hash mismatch")
        try: cp=json.loads(cp_bytes)
        except json.JSONDecodeError as exc:
            raise ValueError("resume rejected: checkpoint artifact JSON is corrupt") from exc
        if cp.get("bindings") != expected_binding:
            raise ValueError("resume rejected: checkpoint identity binding mismatch")
        engine.restore(cp["engine_snapshot"]); detector.restore(cp["periodicity_snapshot"])
        records = list(existing.get("cycles", []))
        if [row.get("cycle") for row in records] != list(range(1, cp["next_cycle"])):
            raise ValueError("resume rejected: cycle history is incomplete or duplicated")
        committed_primaries={row.get("artifact") for row in records}
        orphan_primaries={path.name for path in output.glob("cycle-*.json.gz")}-committed_primaries
        if orphan_primaries:
            raise ValueError("resume rejected: unmanifested cycle primary exists; artifacts preserved for recovery review")
        # Reconstruct every persisted primary before trusting history.
        for row in records:
            path = output / row["artifact"]
            primary = read_primary(path, expected_sha256=row["primary_sha256"])
            if audit_integrated_cycle_primary(
                    primary, preserve_precycle_p7_baseline=True).get("recomputed") is not True:
                raise ValueError("resume rejected: primary independent audit failed")
    else:
        if shutil.disk_usage(output.parent).free < MAX_RUN_ARTIFACT_BYTES:
            raise OSError("artifact root has less free space than the bounded per-run artifact budget")
        output.mkdir(parents=True, exist_ok=False)
        _atomic_write(config_path, _json_bytes(effective))
        start = engine.snapshot()
        cp = {"schema": "DINO_EXPLORATORY_CHECKPOINT_V1", "bindings": expected_binding,
              "next_cycle": 1, "engine_snapshot": start,
              "periodicity_snapshot": detector.snapshot()}
        payload = _json_bytes(cp); _atomic_write(checkpoint_path, payload)
        _atomic_write(manifest_path, _json_bytes({"schema": SCHEMA, "status": "RUNNING",
            "classification": "EXPLORATORY_PROVISIONAL", "bindings": expected_binding,
            "configuration_artifact": "configuration.json", "cycles": [],
            "configuration_sha256": configuration_sha,
            "checkpoint_sha256": _sha(payload), "checkpoint_artifact": checkpoint_artifact}))
    first_cycle = cp["next_cycle"]
    loss = MechanicalLossModel.from_dict(effective["mechanical_loss_model"])
    interrupted = False; interruption_kind = None; failure = None; failure_kind = None
    for cycle in range(first_cycle, max_cycles + 1):
        cycle_start = engine.snapshot(streaming=True)
        try:
            rejected = _advance_cycle(engine, cycle, deadline=deadline,
                cancel_event=cancel_event, progress=progress, memory_limit_mib=memory_limit_mib)
        except (RunCancelled, RunDeadline) as exc:
            engine.restore(cycle_start); failure = str(exc); interrupted = True
            interruption_kind = "CANCELLED" if isinstance(exc, RunCancelled) else "TIMEOUT"
            break
        except Exception as exc:
            engine.restore(cycle_start); failure = f"{type(exc).__name__}: {exc}"
            failure_kind = "RESOURCE_LIMIT_EXCEEDED" if isinstance(exc, MemoryError) else "NUMERICAL_INVALID"
            break
        end = engine.snapshot(streaming=True)
        primary = make_integrated_cycle_primary(engine, cycle_start, end, cycle,
            rejected_trials=rejected, runner_sha256=_sha(Path(__file__).read_bytes()))
        audit = audit_integrated_cycle_primary(
            primary, preserve_precycle_p7_baseline=True)
        if audit.get("recomputed") is not True or primary.get("admissible") is not True:
            failure = "PRIMARY_AUDIT_FAIL"; failure_kind="AUDIT_FAIL"; break
        # V2 versions the evaluator, while its compared primary records retain
        # their frozen V1 data contract.
        update = detector.update({"cycle_index": cycle,
            "configuration_hash": primary["configuration_hash"],
            "contract": CYCLE_PRIMARY_CONTRACT,
            "observables": primary["observables"]})
        artifact_rel = f"cycle-{cycle:04d}.json.gz"
        committed_bytes=sum(path.stat().st_size for path in output.rglob("*") if path.is_file())
        try:
            persisted = write_primary_atomic(output / artifact_rel, primary,
                maximum_bytes=MAX_RUN_ARTIFACT_BYTES-committed_bytes)
        except OSError as exc:
            if 'artifact budget exceeded' not in str(exc):
                raise
            failure="ARTIFACT_BUDGET_EXCEEDED";failure_kind="ARTIFACT_BUDGET_EXCEEDED"
            break
        primary_sha = persisted['primary_sha256']
        # Keep terminal cycle record for output derivation, but store only the
        # replay-baselined compact state for the following cycle's checkpoint.
        periodicity_evidence = None
        if detector.classification is not None:
            periodicity_evidence = {"status": detector.classification,
                "configuration_hash": primary["configuration_hash"],
                "terminal_cycle": cycle,
                "detector_sha256": _sha(_json_bytes(detector.snapshot()))}
        output_record = _prepare_engineering_output_record(primary, periodicity_evidence)
        engineering = make_integrated_engineering_output(output_record,
            displacement_m3=primary.get("swept_displacement_m3"),
            mechanical_loss_model=loss,
            load=effective["operating_conditions"]["load"],
            periodicity_status=detector.classification or "NOT_EVALUATED")
        engineering_summary={"schema":"DINO_EXPLORATORY_METRICS_V1",
            "outputs_schema":engineering["schema"],
            "configuration_sha256":engineering["configuration_sha256"],
            "claims":engineering["claims"],
            "operating_point":engineering["operating_point"],
            "cycle_metrics":engineering["cycle_metrics"]}
        records.append({"cycle": cycle, "artifact": artifact_rel,
                        "primary_sha256": primary_sha, "audit": audit,
                        "audit_method": "INTEGRATED_CYCLE_REPLAY_V2_PRE_CYCLE_P7_BASELINE",
                        "periodicity_update": update,
                        "periodicity": detector.classification or "NOT_EVALUATED",
                        "periodicity_evidence": periodicity_evidence,
                        "conservation": primary["conservation"],
                        "engineering_output": engineering_summary,
                        "rejected_step_count": len(rejected)})
        engine.compact_cycle_trace()
        cp = {"schema": "DINO_EXPLORATORY_CHECKPOINT_V1", "bindings": expected_binding,
              "next_cycle": cycle + 1, "engine_snapshot": engine.snapshot(),
              "periodicity_snapshot": detector.snapshot()}
        cp_payload = _json_bytes(cp)
        # Keep the previously committed checkpoint immutable until the new
        # cycle manifest commits.  A crash after this write leaves only an
        # unreferenced checkpoint file; the manifest still selects its valid
        # prior checkpoint and the orphan cycle primary remains fail-closed.
        next_checkpoint_artifact = f"checkpoint-next-cycle-{cycle + 1:04d}.json"
        _atomic_write(output / next_checkpoint_artifact, cp_payload)
        manifest = {"schema": SCHEMA,
            "status": "INTERRUPTED_CHECKPOINTED" if interrupted else "RUNNING",
            "classification": "EXPLORATORY_PROVISIONAL", "bindings": expected_binding,
            "configuration_artifact": "configuration.json", "cycles": records,
            "configuration_sha256": configuration_sha,
            "checkpoint_sha256": _sha(cp_payload), "checkpoint_artifact": next_checkpoint_artifact,
            "cycles_completed": cycle}
        _atomic_write(manifest_path, _json_bytes(manifest))
        checkpoint_artifact = next_checkpoint_artifact
        if detector.classification is not None:
            break
    classification = (f"EXPLORATORY_{interruption_kind}_CHECKPOINTED" if interrupted else
        f"EXPLORATORY_{failure_kind}" if failure else
        "EXPLORATORY_COMPLETE_PERIODICITY_NOT_IDENTIFIED" if detector.classification is None else
        "EXPLORATORY_COMPLETE_PERIODICITY_OBSERVED")
    if failure and not interrupted:
        status = "FAILED_CLOSED"
    elif interrupted or (cp["next_cycle"] <= max_cycles and detector.classification is None):
        status = "INTERRUPTED_CHECKPOINTED"
    else:
        status = "COMPLETE"
    # Preserve a restart point at the latest complete cycle, including when
    # all requested cycles completed (next_cycle=max_cycles+1).
    cp_payload = _json_bytes(cp)
    comparison_index = _periodicity_comparison_index(records)
    accepted_period = detector.classification
    termination_reason = ("TIMEOUT" if interruption_kind == "TIMEOUT" else
        "CANCELLED" if interruption_kind == "CANCELLED" else
        failure_kind if failure else "PERIOD_ACCEPTED" if accepted_period else
        "HORIZON_COMPLETED")
    periodicity_evaluation_status = _periodicity_evaluation_status(
        complete_cycles=len(records), comparison_count=len(comparison_index),
        invalid_comparison_count=sum(row["status"] == "INVALID" for row in comparison_index),
        accepted_period=accepted_period, termination_reason=termination_reason,
        failure_kind=failure_kind)
    periodicity_diagnostics = {
        "contract": PERIODICITY_CONTRACT_V2,
        "cycle_primary_contract": CYCLE_PRIMARY_CONTRACT,
        "source_sha256": expected_binding["periodicity_source_sha256"],
        "thresholds_sha256": expected_binding["periodicity_thresholds_sha256"],
        "detector_executed": bool(records),
        "evaluation_status": periodicity_evaluation_status,
        "termination_reason": termination_reason,
        "complete_cycles_evaluated": len(records),
        "comparison_count": len(comparison_index),
        "accepted_period": accepted_period,
        "converged_cycle": detector.converged_cycle,
        "thresholds": PERIODICITY_THRESHOLDS_V2,
        "comparison_index": comparison_index,
        "residuals_and_per_comparison_thresholds_at": "cycles[].periodicity_update.outcomes.lag1|lag2",
        "detector_snapshot_sha256": _sha(_json_bytes(detector.snapshot())),
    }
    final = {"schema": SCHEMA, "status": status, "classification": classification,
        "mode": "EXPLORATORY", "scientific_validation": "NOT_CLAIMED",
        "verified_mode": "UNAVAILABLE", "failure": failure,
        "bindings": expected_binding, "preflight": check,
        "cycles_completed": len(records), "cycles": records,
        "periodicity": detector.classification or "NOT_EVALUATED",
        "periodicity_contract": PERIODICITY_CONTRACT_V2,
        "periodicity_diagnostics": periodicity_diagnostics,
        "elapsed_seconds": time.monotonic() - started,
        "memory_rss_at_finish_bytes": _rss_bytes(),
        "checkpoint_artifact": checkpoint_artifact, "checkpoint_sha256": _sha(cp_payload),
        "result_sha256": None}
    final["result_sha256"] = _sha(_json_bytes({k:v for k,v in final.items() if k!="result_sha256"}))
    _atomic_write(output / "result.json", _json_bytes(final))
    current = _read_json(manifest_path)
    current.update({"status": status, "classification": classification,
                    "cycles_completed": len(records), "result_artifact": "result.json",
                    "result_sha256": _sha((output / "result.json").read_bytes()),
                    "checkpoint_sha256": _sha(cp_payload)})
    _atomic_write(manifest_path, _json_bytes(current))
    final["artifact_directory"] = str(output)
    return final


def run_exploratory(document: dict, *, project_id: str, run_id: str,
                    artifact_root: str | Path, rpm: float | None = None,
                    max_cycles: int = 1, budget_seconds: float = 60.0,
                    memory_limit_mib: int = 1024, resume: bool = False,
                    cancel_event=None, progress=None,
                    variant_label: str = "base") -> dict:
    """Serialize concurrent access to one project/run identity with an exclusive lock."""
    target=_run_directory(Path(artifact_root),project_id,run_id)
    target.parent.mkdir(parents=True,exist_ok=True)
    lock=target.parent/f".{run_id}.lock"
    try:
        fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
    except FileExistsError as exc:
        raise RuntimeError("another or interrupted process owns this run lock; artifacts were left untouched") from exc
    try:
        payload=_json_bytes({"pid":os.getpid(),"project_id":project_id,"run_id":run_id,
                             "created_unix":time.time(),"schema":"DINO_RUN_LOCK_V1"})
        with os.fdopen(fd,"wb") as stream:
            stream.write(payload);stream.flush();os.fsync(stream.fileno())
        return _run_exploratory_unlocked(document,project_id=project_id,run_id=run_id,
            artifact_root=artifact_root,rpm=rpm,max_cycles=max_cycles,
            budget_seconds=budget_seconds,memory_limit_mib=memory_limit_mib,
            resume=resume,cancel_event=cancel_event,progress=progress,
            variant_label=variant_label)
    finally:
        try:lock.unlink(missing_ok=True)
        except OSError:pass


def import_exploratory_runs(paths: list[str | Path]) -> dict:
    """Reverify exploratory primaries and load metrics plus angle traces.

    This import deliberately fails closed on stale audit code, altered primary
    evidence, a bad checkpoint binding, or a summary that differs from replay.
    Missing cycles remain classified gaps and are never interpolated.
    """
    if not paths:
        raise ValueError("at least one exploratory run is required")
    points=[]; traces=[]; identities=[]
    names={"brake_power_w":"brake_power", "brake_torque_nm":"brake_torque",
           "imep_pa":"IMEP", "fmep_pa":"FMEP", "bmep_pa":"BMEP",
           "bsfc_g_kwh":"BSFC"}
    scale={"brake_power_w":1e-3,"imep_pa":1e-3,"fmep_pa":1e-3,"bmep_pa":1e-3}
    for requested in paths:
        location=Path(requested)
        result_path=(location/"result.json" if location.is_dir() else location).resolve()
        root=result_path.parent.resolve()
        if result_path.name!="result.json":
            raise ValueError("exploratory import requires a result.json artifact")
        manifest=_read_json(root/"run.json"); payload=result_path.read_bytes()
        if manifest.get("result_sha256") != _sha(payload):
            raise ValueError(f"exploratory result artifact hash mismatch: {result_path}")
        result=json.loads(payload)
        if (result.get("schema") != SCHEMA or result.get("mode") != "EXPLORATORY" or
                result.get("scientific_validation") != "NOT_CLAIMED" or
                result.get("verified_mode") != "UNAVAILABLE"):
            raise ValueError("result is not a supported EXPLORATORY artifact")
        unsigned={k:v for k,v in result.items() if k not in {"result_sha256","artifact_directory"}}
        if result.get("result_sha256") != _sha(_json_bytes(unsigned)):
            raise ValueError("exploratory result canonical identity hash mismatch")
        binding=result.get("bindings",{}); identities.append(binding.get("identity_sha256"))
        manifest_binding=manifest.get("bindings")
        if manifest_binding != binding:
            raise ValueError("exploratory result/run manifest binding mismatch")
        if (not isinstance(binding,dict) or binding.get("workflow_schema")!=SCHEMA or
                result.get("preflight",{}).get("identity_sha256")!=binding.get("identity_sha256") or
                result.get("preflight",{}).get("configuration_sha256")!=binding.get("configuration_sha256")):
            raise ValueError("exploratory preflight/result identity binding is invalid")

        def child(name: Any, label: str) -> Path:
            if not isinstance(name,str) or not name or Path(name).name!=name:
                raise ValueError(f"exploratory {label} artifact path is invalid")
            path=(root/name).resolve()
            if path.parent!=root:
                raise ValueError(f"exploratory {label} artifact escaped its run directory")
            return path

        config_path=child(manifest.get("configuration_artifact"),"configuration")
        config_payload=config_path.read_bytes()
        if _sha(config_payload)!=manifest.get("configuration_sha256"):
            raise ValueError("exploratory configuration artifact hash mismatch")
        effective=json.loads(config_payload)
        if (effective.get("identity_sha256")!=binding.get("identity_sha256") or
                effective.get("native_configuration_sha256")!=binding.get("configuration_sha256") or
                effective.get("source_hashes")!=binding.get("source_hashes")):
            raise ValueError("exploratory configuration artifact binding mismatch")
        current_sources=implementation_source_hashes()
        for module in ("motorsim.integrated_2t","motorsim.mechanical",
                       "motorsim.engineering_outputs"):
            if binding.get("source_hashes",{}).get(module)!=current_sources.get(module):
                raise ValueError(f"exploratory replay source identity mismatch: {module}")

        checkpoint_path=child(manifest.get("checkpoint_artifact"),"checkpoint")
        checkpoint_payload=checkpoint_path.read_bytes()
        if (_sha(checkpoint_payload)!=result.get("checkpoint_sha256") or
                result.get("checkpoint_sha256")!=manifest.get("checkpoint_sha256")):
            raise ValueError("exploratory checkpoint artifact hash mismatch")
        checkpoint=json.loads(checkpoint_payload)
        cycles=result.get("cycles")
        manifest_cycles=manifest.get("cycles")
        count=result.get("cycles_completed")
        if (type(count) is not int or count<0 or not isinstance(cycles,list) or
                len(cycles)!=count or not isinstance(manifest_cycles,list) or
                len(manifest_cycles)!=count or
                [row.get("cycle") for row in cycles]!=list(range(1,count+1)) or
                checkpoint.get("bindings")!=binding or checkpoint.get("next_cycle")!=count+1):
            raise ValueError("exploratory completed-cycle/checkpoint history is inconsistent")
        if (checkpoint.get("schema")!="DINO_EXPLORATORY_CHECKPOINT_V1" or
                not isinstance(checkpoint.get("engine_snapshot"),dict) or
                not isinstance(checkpoint.get("periodicity_snapshot"),dict)):
            raise ValueError("exploratory checkpoint state is malformed")
        loss=MechanicalLossModel.from_dict(effective["mechanical_loss_model"])
        periodicity_diag = result.get("periodicity_diagnostics")
        if periodicity_diag is not None and (
                periodicity_diag.get("contract") != PERIODICITY_CONTRACT_V2 or
                periodicity_diag.get("cycle_primary_contract") != CYCLE_PRIMARY_CONTRACT or
                periodicity_diag.get("source_sha256") != _periodicity_source_sha256() or
                periodicity_diag.get("thresholds_sha256") !=
                    _sha(_json_bytes(PERIODICITY_THRESHOLDS_V2)) or
                periodicity_diag.get("thresholds") != PERIODICITY_THRESHOLDS_V2 or
                binding.get("periodicity_source_sha256") != _periodicity_source_sha256() or
                binding.get("periodicity_thresholds_sha256") !=
                    _sha(_json_bytes(PERIODICITY_THRESHOLDS_V2))):
            raise ValueError("exploratory periodicity diagnostic contract/threshold mismatch")
        periodicity_detector = PeriodicDetectorV2()
        variant_id=f"{binding.get('project_id')} / {binding.get('variant_label')}"
        rpm=result.get("preflight",{}).get("rpm")
        verified_cycles=[]
        for index,(cycle,manifest_cycle) in enumerate(zip(cycles,manifest_cycles),1):
            if any(cycle.get(key)!=manifest_cycle.get(key)
                   for key in ("cycle","artifact","primary_sha256")):
                raise ValueError("exploratory cycle manifest and result disagree")
            if cycle.get("cycle")!=index:
                raise ValueError("exploratory cycle sequence is duplicated or missing")
            primary_path=child(cycle.get("artifact"),"primary")
            try:
                primary=read_primary(primary_path,expected_sha256=cycle.get("primary_sha256"))
            except (OSError,EOFError,zlib.error,ValueError) as exc:
                raise ValueError("exploratory cycle primary is corrupt or canonical hash mismatch") from exc
            if (primary.get("cycle_index")!=index or
                    primary.get("configuration_hash")!=effective.get("solver_configuration_sha256")):
                raise ValueError("exploratory cycle primary identity mismatch")
            # The independent auditor may materialize replay baselines in its
            # input structure. Keep the persisted primary pristine for output
            # reconstruction so replay is deterministic and byte-bound.
            audit_primary=_copy_primary_for_analysis(primary)
            audit=audit_integrated_cycle_primary(
                audit_primary,preserve_precycle_p7_baseline=True)
            recorded_audit=cycle.get("audit")
            if (audit.get("status")!="PASS" or audit.get("recomputed") is not True or
                    not isinstance(recorded_audit,dict) or
                    recorded_audit.get("status")!="PASS" or
                    recorded_audit.get("recomputed") is not True):
                raise ValueError("exploratory cycle independent audit failed")
            if periodicity_diag is not None:
                replayed_update = periodicity_detector.update({
                    "cycle_index": index,
                    "configuration_hash": primary["configuration_hash"],
                    "contract": CYCLE_PRIMARY_CONTRACT,
                    "observables": primary["observables"]})
                if (cycle.get("periodicity_update") != replayed_update or
                        cycle.get("periodicity") !=
                        (periodicity_detector.classification or "NOT_EVALUATED")):
                    raise ValueError("exploratory periodicity update differs from canonical replay")
            analysis_primary=_copy_primary_for_analysis(primary)
            periodicity=cycle.get("periodicity") or "NOT_EVALUATED"
            if cycle.get("periodicity_evidence") is not None:
                analysis_primary={**primary,"periodicity_evidence":cycle["periodicity_evidence"]}
            output=make_integrated_engineering_output(
                analysis_primary,
                displacement_m3=primary.get("swept_displacement_m3"),
                mechanical_loss_model=loss,
                load=effective["operating_conditions"]["load"],
                periodicity_status=periodicity)
            summary={"schema":"DINO_EXPLORATORY_METRICS_V1",
                "outputs_schema":output["schema"],
                "configuration_sha256":output["configuration_sha256"],
                "claims":output["claims"],"operating_point":output["operating_point"],
                "cycle_metrics":output["cycle_metrics"]}
            if not _replay_equivalent(summary,cycle.get("engineering_output")):
                raise ValueError("exploratory engineering summary differs from audited primary replay")
            verified_cycles.append((cycle,audit,primary,output))

        if periodicity_diag is not None:
            replayed_snapshot = periodicity_detector.snapshot()
            replayed_comparison_index = _periodicity_comparison_index(result.get("cycles", []))
            termination = periodicity_diag.get("termination_reason")
            replayed_failure_kind = (termination if termination not in
                {"TIMEOUT", "CANCELLED", "HORIZON_COMPLETED", "PERIOD_ACCEPTED", None}
                else None)
            expected_status = _periodicity_evaluation_status(
                complete_cycles=count, comparison_count=len(replayed_comparison_index),
                invalid_comparison_count=sum(row["status"] == "INVALID"
                                             for row in replayed_comparison_index),
                accepted_period=periodicity_detector.classification,
                termination_reason=termination,
                failure_kind=replayed_failure_kind)
            expected_diagnostics = {
                "contract": PERIODICITY_CONTRACT_V2,
                "cycle_primary_contract": CYCLE_PRIMARY_CONTRACT,
                "source_sha256": binding["periodicity_source_sha256"],
                "thresholds_sha256": binding["periodicity_thresholds_sha256"],
                "detector_executed": count > 0,
                "evaluation_status": expected_status,
                "termination_reason": termination,
                "complete_cycles_evaluated": count,
                "comparison_count": len(replayed_comparison_index),
                "accepted_period": periodicity_detector.classification,
                "converged_cycle": periodicity_detector.converged_cycle,
                "thresholds": PERIODICITY_THRESHOLDS_V2,
                "comparison_index": replayed_comparison_index,
                "residuals_and_per_comparison_thresholds_at": "cycles[].periodicity_update.outcomes.lag1|lag2",
                "detector_snapshot_sha256": _sha(_json_bytes(replayed_snapshot)),
            }
            if periodicity_diag != expected_diagnostics:
                raise ValueError("exploratory periodicity diagnostics differ from canonical replay")

        if count==0:
            gap={"point_id":binding.get("run_id"),"variant_id":variant_id,"rpm":rpm,
                 "classification":result.get("classification"),"cycles_completed":0,
                 "result_sha256":result.get("result_sha256"),
                 "point_configuration_sha256":binding.get("configuration_sha256"),
                 "hard_gates":{"status":"NOT_EVALUATED_EXPLORATORY"},
                 "periodicity":result.get("periodicity"),"audit_status":"NO_COMPLETE_CYCLE",
                 "periodicity_diagnostics":result.get("periodicity_diagnostics"),
                 "audit_recomputed":False,"run_id":binding.get("run_id"),"cycle":None,
                 "mode":"EXPLORATORY","experimental_validation":"NOT_CLAIMED",
                 "conservation":None}
            for field in names.values():
                gap[field]=None;gap[field+"_status"]="NOT_REPORTED"
                gap[field+"_reason"]="No complete audited cycle was produced."
            points.append(gap)

        source_hashes=binding.get("source_hashes",{})
        implementation_identity_sha256=_sha(_json_bytes(source_hashes))
        preflight_identity=result.get("preflight",{})
        periodicity_contract=result.get("periodicity_contract")
        mesh_resolution=[len(duct.get("mesh",{}).get("volumes",[]))
                         for duct in effective.get("native_configuration",{}).get("ducts",[])]
        for cycle,audit,primary,output in verified_cycles:
            metrics=output.get("cycle_metrics",{})
            row={"point_id":f"{binding.get('run_id')}@cycle-{cycle.get('cycle')}",
                 "variant_id":variant_id,"rpm":rpm,
                 "classification":result.get("classification"),
                 "cycles_completed":result.get("cycles_completed"),
                 "result_sha256":result.get("result_sha256"),
                 "point_configuration_sha256":binding.get("configuration_sha256"),
                 "hard_gates":{"status":"NOT_EVALUATED_EXPLORATORY"},
                 "periodicity":cycle.get("periodicity") or "NOT_EVALUATED",
                 "periodicity_diagnostics":result.get("periodicity_diagnostics"),
                 "audit_status":audit.get("status"),"audit_recomputed":audit.get("recomputed"),
                 "primary_sha256":cycle.get("primary_sha256"),
                 "conservation":primary.get("conservation"),
                 "run_id":binding.get("run_id"),"cycle":cycle.get("cycle"),
                 "mode":"EXPLORATORY","experimental_validation":"NOT_CLAIMED",
                 "implementation_identity_sha256":implementation_identity_sha256,
                 "solver_identity_sha256":source_hashes.get("motorsim.integrated_2t"),
                 "producer_sha256":source_hashes.get("motorsim.exploratory_workflow"),
                 "fuel_id":preflight_identity.get("fuel_id"),
                 "mechanical_loss_model_sha256":preflight_identity.get("mechanical_loss_model_sha256"),
                 "periodicity_contract":periodicity_contract,
                 "total_finite_volume_cells":preflight_identity.get("total_finite_volume_cells"),
                 "mesh_resolution":mesh_resolution}
            for metric,field in names.items():
                record=metrics.get(metric,{})
                value=record.get("value") if record.get("status")=="DEFINED" else None
                row[field]=None if value is None else value*scale.get(metric,1.0)
                row[field+"_status"]=record.get("status","NOT_REPORTED")
                row[field+"_reason"]=record.get("reason")
            points.append(row)
            trace=output["crank_angle_trace"]
            traces.append({"point_id":row["point_id"],"variant_id":variant_id,
                "rpm":rpm,"run_id":binding.get("run_id"),"cycle":cycle.get("cycle"),
                "classification":result.get("classification"),"periodicity":row["periodicity"],
                "audit_status":audit.get("status"),"audit_recomputed":audit.get("recomputed"),
                "hard_gates":row["hard_gates"],"angles_deg":trace["angle_deg"],
                "channels":trace["channels"]})
    return {"schema":"DINO_EXPLORATORY_COMPARISON_V1","points":points,
            "traces":traces,
            "provenance":"EXPLORATORY · provisional · no scientific validation claim",
            "experimental_validation":"NOT_CLAIMED",
            "units":{"brake_power":"kW","brake_torque":"N*m","IMEP":"kPa",
                     "FMEP":"kPa","BMEP":"kPa","BSFC":"g/kWh"},
            "implementation_identity_sha256s":identities,
            "interpolation":"NONE"}
