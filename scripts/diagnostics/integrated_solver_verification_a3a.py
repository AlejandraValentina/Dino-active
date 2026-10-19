"""ISV1 A3a — preregistered single-run computational profile of the integrated 2T path.

Default invocation performs only the bound no-solver preflight and prints the
frozen identity/binding values (with optional --receipt PATH for a durable
receipt). A real run requires --execute plus the exact preregistration SHA-256
and a recorded owner-confirmation artifact; the run never resumes and never
retries. This driver does not modify motorsim/: it replicates the
exploratory-workflow cycle loop with the same imported primitives because the
workflow per-invocation contract caps budget at 600 s while A3a is authorized
for one instrumented run under a 1200 s external cap.

Declared divergences vs the exploratory workflow: internal stepping deadline
t0+1080 s; external cap 1200 s via run_logged --timeout; max_cycles 8; in-run
exclusive timers (no cProfile/tracemalloc inside the run); own artifact
schemas and file names (a3a-run/a3a-result/a3a-checkpoint); no resume; the
preflight budget echo (600 s) is the workflow contract maximum, NOT the
operative deadline.

Exit codes: 0 = completed or interrupted-checkpointed run; 1 = fail-closed run
failure; 2 = refused (binding/authorization/precondition error; no run).
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import re
import shutil
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from motorsim.desktop.preferences import repository_root_containing
from motorsim.engine_configuration import resolve_for_operating_point
from motorsim.engine_project import load_project
from motorsim.exhaust_mesh_v2 import refine_exhaust_configuration
from motorsim.exploratory_workflow import (
    MAX_RUN_ARTIFACT_BYTES, RunCancelled, RunDeadline, _advance_cycle,
    _atomic_write, _json_bytes, _periodicity_comparison_index,
    _periodicity_evaluation_status, _periodicity_source_sha256,
    _prepare_engineering_output_record, _rss_bytes, _sha, preflight)
from motorsim.integrated_2t import (IntegratedEngine2T,
                                    audit_integrated_cycle_primary,
                                    make_integrated_cycle_primary,
                                    make_integrated_engineering_output)
from motorsim.mechanical import MechanicalLossModel
from motorsim.reference_harness.convergence import (
    CONTRACT as CYCLE_PRIMARY_CONTRACT,
    CONTRACT_V2 as PERIODICITY_CONTRACT_V2,
    THRESHOLDS as PERIODICITY_THRESHOLDS_V2,
    PeriodicDetectorV2)
from motorsim import exploratory_workflow as exploratory_workflow_module

PROTOCOL = ROOT / "results/integrated-solver-verification-v1/a3a-preregistration.json"
CONFIRMATION = ROOT / "results/integrated-solver-verification-v1/a3a-owner-confirmation.json"
PROJECT = ROOT / "examples/projects/dino-2t-exhaust-comparison.dino2t.json"
VARIANT = "Escape original"
RPM = 3000
CELLS_PER_SECTION = 8
MAX_CYCLES = 8
MEMORY_LIMIT_MIB = 3072
PREFLIGHT_BUDGET_ECHO_SECONDS = 600
INTERNAL_DEADLINE_SECONDS = 1080.0
EXTERNAL_CAP_SECONDS = 1200.0
RUN_ID = "isv1-a3a-profile-3000rpm-mesh8-v1"

RUN_SCHEMA = "DINO_ISV1_A3A_RUN_V1"
CHECKPOINT_SCHEMA = "DINO_ISV1_A3A_CHECKPOINT_V1"
PREFLIGHT_SCHEMA = "DINO_ISV1_A3A_PREFLIGHT_V1"
RESULT_SCHEMA = "DINO_ISV1_A3A_RESULT_V1"
CONFIRMATION_SCHEMA = "DINO_ISV1_A3A_OWNER_CONFIRMATION_V1"

TIMER_KEYS = ("integration_physical_seconds",
              "audit_reconstruction_make_seconds",
              "audit_reconstruction_audit_seconds",
              "serialization_io_seconds",
              "state_snapshot_orchestration_seconds",
              "engineering_output_seconds",
              "periodicity_detector_seconds",
              "dispatch_overhead_seconds")


def _file_sha(path: Path) -> str:
    """SHA-256 over the file bytes with CRLF normalized to LF (stage1 convention)."""
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def _load_configuration():
    project = load_project(PROJECT)
    source = project["variants"][VARIANT]
    sections = source["native_configuration"]["geometry_identity"]["chamber"]["sections"]
    refined = refine_exhaust_configuration(source, [1] * len(sections))
    refined = refine_exhaust_configuration(refined, [CELLS_PER_SECTION] * len(sections))
    effective = resolve_for_operating_point(refined, rpm=RPM)
    check = preflight(
        refined,
        rpm=RPM,
        max_cycles=MAX_CYCLES,
        budget_seconds=PREFLIGHT_BUDGET_ECHO_SECONDS,
        memory_limit_mib=MEMORY_LIMIT_MIB,
    )
    return project, refined, effective, check


def _frozen_binding(effective: dict, check: dict) -> dict:
    return {
        "runner_sha256": _file_sha(Path(__file__)),
        "project_sha256": _file_sha(PROJECT),
        "configuration_sha256": check["configuration_sha256"],
        "identity_sha256": check["identity_sha256"],
        "mechanical_loss_model_sha256": check["mechanical_loss_model_sha256"],
        "fuel_id": check["fuel_id"],
        "solver_source_hashes": effective["source_hashes"],
        "periodicity_contract": PERIODICITY_CONTRACT_V2,
        "cycle_primary_contract": CYCLE_PRIMARY_CONTRACT,
        "periodicity_source_sha256": _periodicity_source_sha256(),
        "periodicity_thresholds_sha256": check["periodicity_thresholds_sha256"],
        "exploratory_workflow_source_sha256": _file_sha(
            Path(exploratory_workflow_module.__file__)),
    }


def _validate_binding(protocol: dict, actual: dict) -> None:
    expected = protocol.get("frozen_binding")
    if not isinstance(expected, dict):
        raise RuntimeError("FAIL_CLOSED preregistration is missing frozen_binding")
    mismatches = [key for key, value in expected.items() if actual.get(key) != value]
    if mismatches:
        raise RuntimeError("FAIL_CLOSED preregistration binding mismatch: " +
                           ", ".join(sorted(mismatches)))


def _artifact_root() -> Path:
    base = Path(os.environ.get("DINO_ARTIFACT_ROOT",
                               Path.home() / "Dino-artifacts")).expanduser().resolve()
    if repository_root_containing(base) is not None:
        raise RuntimeError("DINO_ARTIFACT_ROOT is inside a Git repository; refusing output")
    root = base / "integrated-solver-verification-v1" / "a3a"
    if repository_root_containing(root) is not None:
        raise RuntimeError("A3a artifact root is inside a Git repository; refusing output")
    return root


def _run_directory(root: Path, project_id: str) -> Path:
    for value, label in ((project_id, "project_id"), (RUN_ID, "run_id")):
        if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,79}", value):
            raise ValueError(f"{label} must be a safe path component")
    base = (root / project_id).resolve()
    target = (base / RUN_ID).resolve()
    if base not in target.parents:
        raise ValueError("resolved run path escaped the configured artifact root")
    return target


def _write_receipt(path: Path, payload: dict) -> None:
    _atomic_write(path, (json.dumps(payload, indent=2, ensure_ascii=False) + "\n").encode("utf-8"))


def run_validate(receipt: str | None) -> dict:
    started = time.monotonic()
    _project, _refined, effective, check = _load_configuration()
    binding = _frozen_binding(effective, check)
    output = {
        "schema": PREFLIGHT_SCHEMA,
        "classification": "PREFLIGHT_ONLY_NO_SOLVER_STEPS",
        "preflight": check,
        "frozen_binding": binding,
        "artifact_root": str(_artifact_root()),
        "protocol": {
            "run_id": RUN_ID,
            "variant": VARIANT,
            "rpm": RPM,
            "cells_per_section": CELLS_PER_SECTION,
            "max_cycles": MAX_CYCLES,
            "memory_limit_mib": MEMORY_LIMIT_MIB,
            "preflight_budget_echo_seconds": PREFLIGHT_BUDGET_ECHO_SECONDS,
            "internal_stepping_deadline_seconds": INTERNAL_DEADLINE_SECONDS,
            "external_cap_seconds": EXTERNAL_CAP_SECONDS,
            "resume_allowed": False,
            "retries_allowed": False,
        },
        "preregistration_check": "NOT_FOUND",
    }
    if PROTOCOL.is_file():
        protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
        _validate_binding(protocol, binding)
        output["preregistration_check"] = "PASS"
    output["elapsed_seconds"] = time.monotonic() - started
    if receipt is not None:
        _write_receipt(Path(receipt), output)
    return output


def _execute_locked(*, project: dict, effective: dict, check: dict, binding: dict,
                    preregistration_sha256: str, invocation_started: float,
                    output: Path) -> dict:
    deadline = invocation_started + INTERNAL_DEADLINE_SECONDS
    expected_binding = {
        "run_schema": RUN_SCHEMA,
        "identity_sha256": effective["identity_sha256"],
        "configuration_sha256": effective["native_configuration_sha256"],
        "source_hashes": effective["source_hashes"],
        "periodicity_contract": PERIODICITY_CONTRACT_V2,
        "cycle_primary_contract": CYCLE_PRIMARY_CONTRACT,
        "periodicity_source_sha256": binding["periodicity_source_sha256"],
        "periodicity_thresholds_sha256": binding["periodicity_thresholds_sha256"],
        "exploratory_workflow_source_sha256": binding["exploratory_workflow_source_sha256"],
        "driver_source_sha256": binding["runner_sha256"],
        "preregistration_sha256": preregistration_sha256,
        "project_id": project["project_id"],
        "variant_label": f"{VARIANT} / {CELLS_PER_SECTION} cells per section",
        "run_id": RUN_ID,
    }
    if output.exists():
        raise RuntimeError("FAIL_CLOSED run directory already exists; resume is not authorized")
    if shutil.disk_usage(output.parent).free < MAX_RUN_ARTIFACT_BYTES:
        raise OSError("artifact root has less free space than the bounded per-run artifact budget")
    output.mkdir(parents=True, exist_ok=False)
    manifest_path = output / "a3a-run.json"
    _atomic_write(output / "configuration.json", _json_bytes(effective))

    integration = {"seconds": 0.0, "calls": 0}
    original_step = IntegratedEngine2T.step

    def timed_step(self, *args, **kwargs):
        mark = time.perf_counter()
        try:
            return original_step(self, *args, **kwargs)
        finally:
            integration["seconds"] += time.perf_counter() - mark
            integration["calls"] += 1

    IntegratedEngine2T.step = timed_step

    rss_start = _rss_bytes()
    rss_peak = {"bytes": rss_start}
    sampler_stop = threading.Event()

    def _sample():
        while not sampler_stop.wait(0.2):
            try:
                value = _rss_bytes()
            except OSError:
                return
            if value > rss_peak["bytes"]:
                rss_peak["bytes"] = value

    sampler = threading.Thread(target=_sample, daemon=True)
    sampler.start()

    def _progress(info: dict) -> None:
        print(f"a3a-progress cycle={info['cycle']} angle_deg={info['angle_deg']:.3f} "
              f"cycles_completed={info['cycles_completed']} rss_bytes={info['rss_bytes']}",
              flush=True)

    engine = IntegratedEngine2T.from_configuration_dict(effective["native_configuration"])
    detector = PeriodicDetectorV2()
    records: list[dict] = []
    timers = {key: 0.0 for key in TIMER_KEYS}
    state_mark = time.perf_counter()
    start_state = engine.snapshot()
    timers["state_snapshot_orchestration_seconds"] += time.perf_counter() - state_mark
    cp = {"schema": CHECKPOINT_SCHEMA, "bindings": expected_binding, "next_cycle": 1,
          "engine_snapshot": start_state, "periodicity_snapshot": detector.snapshot()}
    cp_payload = _json_bytes(cp)
    checkpoint_artifact = "a3a-checkpoint.json"
    _atomic_write(output / checkpoint_artifact, cp_payload)
    _atomic_write(manifest_path, _json_bytes({
        "schema": RUN_SCHEMA, "status": "RUNNING", "classification": "A3A_PROVISIONAL",
        "bindings": expected_binding, "configuration_artifact": "configuration.json",
        "cycles": [], "configuration_sha256": _sha(_json_bytes(effective)),
        "checkpoint_sha256": _sha(cp_payload), "checkpoint_artifact": checkpoint_artifact,
        "protocol": {"run_id": RUN_ID,
                     "internal_stepping_deadline_seconds": INTERNAL_DEADLINE_SECONDS,
                     "external_cap_seconds": EXTERNAL_CAP_SECONDS,
                     "preflight_budget_echo_seconds": PREFLIGHT_BUDGET_ECHO_SECONDS,
                     "max_cycles": MAX_CYCLES, "memory_limit_mib": MEMORY_LIMIT_MIB,
                     "resume_allowed": False, "retries_allowed": False, "preflight": check}}))

    loss = MechanicalLossModel.from_dict(effective["mechanical_loss_model"])
    interrupted = False
    interruption_kind = None
    failure = None
    failure_kind = None
    runner_sha256 = binding["runner_sha256"]
    cycle_wall_total = 0.0
    for cycle in range(1, MAX_CYCLES + 1):
        cycle_mark = time.perf_counter()
        cycle_timers = {"step_calls_attempted": 0, "rejected_step_count": 0}
        state_base = timers["state_snapshot_orchestration_seconds"]
        state_mark = time.perf_counter()
        cycle_start = engine.snapshot()
        timers["state_snapshot_orchestration_seconds"] += time.perf_counter() - state_mark
        step_base = integration["seconds"]
        calls_base = integration["calls"]
        advance_mark = time.perf_counter()
        try:
            rejected = _advance_cycle(engine, cycle, deadline=deadline, cancel_event=None,
                                      progress=_progress, memory_limit_mib=MEMORY_LIMIT_MIB)
        except (RunCancelled, RunDeadline) as exc:
            restore_mark = time.perf_counter()
            engine.restore(cycle_start)
            timers["state_snapshot_orchestration_seconds"] += time.perf_counter() - restore_mark
            failure = str(exc)
            interrupted = True
            interruption_kind = "CANCELLED" if isinstance(exc, RunCancelled) else "TIMEOUT"
            break
        except Exception as exc:
            restore_mark = time.perf_counter()
            engine.restore(cycle_start)
            timers["state_snapshot_orchestration_seconds"] += time.perf_counter() - restore_mark
            failure = f"{type(exc).__name__}: {exc}"
            failure_kind = ("RESOURCE_LIMIT_EXCEEDED" if isinstance(exc, MemoryError)
                            else "NUMERICAL_INVALID")
            break
        advance_seconds = time.perf_counter() - advance_mark
        step_seconds = integration["seconds"] - step_base
        timers["integration_physical_seconds"] += step_seconds
        timers["dispatch_overhead_seconds"] += advance_seconds - step_seconds
        cycle_timers.update({
            "integration_physical_seconds": step_seconds,
            "advance_total_seconds": advance_seconds,
            "dispatch_overhead_seconds": advance_seconds - step_seconds,
            "step_calls_attempted": integration["calls"] - calls_base,
            "rejected_step_count": len(rejected)})
        state_mark = time.perf_counter()
        end = engine.snapshot()
        timers["state_snapshot_orchestration_seconds"] += time.perf_counter() - state_mark
        make_mark = time.perf_counter()
        primary = make_integrated_cycle_primary(engine, cycle_start, end, cycle,
            rejected_trials=rejected, runner_sha256=runner_sha256)
        make_seconds = time.perf_counter() - make_mark
        timers["audit_reconstruction_make_seconds"] += make_seconds
        cycle_timers["audit_reconstruction_make_seconds"] = make_seconds
        audit_mark = time.perf_counter()
        audit = audit_integrated_cycle_primary(primary, preserve_precycle_p7_baseline=True)
        audit_seconds = time.perf_counter() - audit_mark
        timers["audit_reconstruction_audit_seconds"] += audit_seconds
        cycle_timers["audit_reconstruction_audit_seconds"] = audit_seconds
        if audit.get("recomputed") is not True or primary.get("admissible") is not True:
            failure = "PRIMARY_AUDIT_FAIL"
            failure_kind = "AUDIT_FAIL"
            break
        detector_mark = time.perf_counter()
        update = detector.update({"cycle_index": cycle,
            "configuration_hash": primary["configuration_hash"],
            "contract": CYCLE_PRIMARY_CONTRACT,
            "observables": primary["observables"]})
        detector_seconds = time.perf_counter() - detector_mark
        timers["periodicity_detector_seconds"] += detector_seconds
        cycle_timers["periodicity_detector_seconds"] = detector_seconds
        serialization_mark = time.perf_counter()
        primary_payload = _json_bytes(primary)
        primary_sha = _sha(primary_payload)
        artifact_rel = f"cycle-{cycle:04d}.json.gz"
        compressed_primary = gzip.compress(primary_payload, compresslevel=6, mtime=0)
        committed_bytes = sum(path.stat().st_size for path in output.rglob("*") if path.is_file())
        if committed_bytes + len(compressed_primary) > MAX_RUN_ARTIFACT_BYTES:
            timers["serialization_io_seconds"] += time.perf_counter() - serialization_mark
            failure = "ARTIFACT_BUDGET_EXCEEDED"
            failure_kind = "ARTIFACT_BUDGET_EXCEEDED"
            break
        _atomic_write(output / artifact_rel, compressed_primary)
        serialization_seconds = time.perf_counter() - serialization_mark
        periodicity_evidence = None
        if detector.classification is not None:
            periodicity_evidence = {"status": detector.classification,
                "configuration_hash": primary["configuration_hash"],
                "terminal_cycle": cycle,
                "detector_sha256": _sha(_json_bytes(detector.snapshot()))}
        engineering_mark = time.perf_counter()
        output_record = _prepare_engineering_output_record(primary, periodicity_evidence)
        engineering = make_integrated_engineering_output(output_record,
            displacement_m3=primary.get("swept_displacement_m3"),
            mechanical_loss_model=loss,
            load=effective["operating_conditions"]["load"],
            periodicity_status=detector.classification or "NOT_EVALUATED")
        engineering_summary = {"schema": "DINO_EXPLORATORY_METRICS_V1",
            "outputs_schema": engineering["schema"],
            "configuration_sha256": engineering["configuration_sha256"],
            "claims": engineering["claims"],
            "operating_point": engineering["operating_point"],
            "cycle_metrics": engineering["cycle_metrics"]}
        engineering_seconds = time.perf_counter() - engineering_mark
        timers["engineering_output_seconds"] += engineering_seconds
        cycle_timers["engineering_output_seconds"] = engineering_seconds
        records.append({"cycle": cycle, "artifact": artifact_rel,
                        "primary_sha256": primary_sha, "audit": audit,
                        "audit_method": "INTEGRATED_CYCLE_REPLAY_V2_PRE_CYCLE_P7_BASELINE",
                        "periodicity_update": update,
                        "periodicity": detector.classification or "NOT_EVALUATED",
                        "periodicity_evidence": periodicity_evidence,
                        "conservation": primary["conservation"],
                        "engineering_output": engineering_summary,
                        "rejected_step_count": len(rejected),
                        "timers": cycle_timers,
                        "rss_bytes_at_cycle_end": _rss_bytes()})
        state_mark = time.perf_counter()
        engine.compact_cycle_trace()
        cp = {"schema": CHECKPOINT_SCHEMA, "bindings": expected_binding, "next_cycle": cycle + 1,
              "engine_snapshot": engine.snapshot(), "periodicity_snapshot": detector.snapshot()}
        timers["state_snapshot_orchestration_seconds"] += time.perf_counter() - state_mark
        serialization_mark = time.perf_counter()
        cp_payload = _json_bytes(cp)
        next_checkpoint_artifact = f"a3a-checkpoint-next-cycle-{cycle + 1:04d}.json"
        _atomic_write(output / next_checkpoint_artifact, cp_payload)
        manifest = {"schema": RUN_SCHEMA,
            "status": "INTERRUPTED_CHECKPOINTED" if interrupted else "RUNNING",
            "classification": "A3A_PROVISIONAL", "bindings": expected_binding,
            "configuration_artifact": "configuration.json", "cycles": records,
            "configuration_sha256": _sha(_json_bytes(effective)),
            "checkpoint_sha256": _sha(cp_payload), "checkpoint_artifact": next_checkpoint_artifact,
            "cycles_completed": cycle,
            "protocol": {"run_id": RUN_ID,
                         "internal_stepping_deadline_seconds": INTERNAL_DEADLINE_SECONDS,
                         "external_cap_seconds": EXTERNAL_CAP_SECONDS,
                         "preflight_budget_echo_seconds": PREFLIGHT_BUDGET_ECHO_SECONDS,
                         "max_cycles": MAX_CYCLES, "memory_limit_mib": MEMORY_LIMIT_MIB,
                         "resume_allowed": False, "retries_allowed": False, "preflight": check}}
        _atomic_write(manifest_path, _json_bytes(manifest))
        serialization_seconds += time.perf_counter() - serialization_mark
        timers["serialization_io_seconds"] += serialization_seconds
        cycle_timers["serialization_io_seconds"] = serialization_seconds
        cycle_timers["state_snapshot_orchestration_seconds"] = (
            timers["state_snapshot_orchestration_seconds"] - state_base)
        checkpoint_artifact = next_checkpoint_artifact
        cycle_wall_total += time.perf_counter() - cycle_mark
        if detector.classification is not None:
            break
    sampler_stop.set()
    finalization_mark = time.perf_counter()
    classification = (f"A3A_{interruption_kind}_CHECKPOINTED" if interrupted else
        f"A3A_{failure_kind}" if failure else
        "A3A_COMPLETE_PERIODICITY_NOT_IDENTIFIED" if detector.classification is None else
        "A3A_COMPLETE_PERIODICITY_OBSERVED")
    if failure and not interrupted:
        status = "FAILED_CLOSED"
    elif interrupted or (cp["next_cycle"] <= MAX_CYCLES and detector.classification is None):
        status = "INTERRUPTED_CHECKPOINTED"
    else:
        status = "COMPLETE"
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
    timers["finalization_seconds"] = time.perf_counter() - finalization_mark
    elapsed_seconds = time.monotonic() - invocation_started
    shares = {}
    for key in TIMER_KEYS:
        shares[key] = timers[key] / elapsed_seconds if elapsed_seconds > 0 else 0.0
    shares["finalization_seconds"] = (timers["finalization_seconds"] / elapsed_seconds
                                      if elapsed_seconds > 0 else 0.0)
    final = {"schema": RESULT_SCHEMA, "status": status, "classification": classification,
        "mode": "SINGLE_RUN_PROFILE", "scientific_validation": "NOT_CLAIMED",
        "verified_mode": "UNAVAILABLE", "failure": failure,
        "bindings": expected_binding, "preflight": check,
        "protocol": {"run_id": RUN_ID, "variant": VARIANT, "rpm": RPM,
            "cells_per_section": CELLS_PER_SECTION, "max_cycles": MAX_CYCLES,
            "memory_limit_mib": MEMORY_LIMIT_MIB,
            "preflight_budget_echo_seconds": PREFLIGHT_BUDGET_ECHO_SECONDS,
            "internal_stepping_deadline_seconds": INTERNAL_DEADLINE_SECONDS,
            "external_cap_seconds": EXTERNAL_CAP_SECONDS,
            "resume_allowed": False, "retries_allowed": False},
        "cycles_completed": len(records), "cycles": records,
        "periodicity": detector.classification or "NOT_EVALUATED",
        "periodicity_contract": PERIODICITY_CONTRACT_V2,
        "periodicity_diagnostics": periodicity_diagnostics,
        "elapsed_seconds": elapsed_seconds,
        "cycle_wall_seconds_total": cycle_wall_total,
        "timers_seconds": timers,
        "timer_shares_of_total_wall": shares,
        "measurement_note": ("single-sample shares over total wall; exclusive buckets; "
                             "no repeated control run is authorized; step_calls_attempted "
                             "counts failed CFL attempts"),
        "rss_bytes": {"start": rss_start, "peak_sampled": rss_peak["bytes"],
                      "finish": _rss_bytes()},
        "checkpoint_artifact": checkpoint_artifact, "checkpoint_sha256": _sha(cp_payload),
        "result_sha256": None}
    final["result_sha256"] = _sha(_json_bytes({k: v for k, v in final.items() if k != "result_sha256"}))
    _atomic_write(output / "a3a-result.json", _json_bytes(final))
    current = json.loads(manifest_path.read_text(encoding="utf-8"))
    current.update({"status": status, "classification": classification,
                    "cycles_completed": len(records), "result_artifact": "a3a-result.json",
                    "result_sha256": _sha((output / "a3a-result.json").read_bytes()),
                    "checkpoint_sha256": _sha(cp_payload)})
    _atomic_write(manifest_path, _json_bytes(current))
    final["artifact_directory"] = str(output)
    return final


def run_execute(preregistration_sha256: str) -> dict:
    invocation_started = time.monotonic()
    project, _refined, effective, check = _load_configuration()
    binding = _frozen_binding(effective, check)
    if not PROTOCOL.is_file():
        raise RuntimeError("FAIL_CLOSED preregistration file is missing")
    if preregistration_sha256 != _file_sha(PROTOCOL):
        raise RuntimeError("FAIL_CLOSED execution requires the exact preregistration SHA-256")
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    _validate_binding(protocol, binding)
    authorization = protocol.get("authorization", {})
    if (authorization.get("solver_execution_authorized_within_this_single_run_scope") is not True or
            authorization.get("campaign_authorization") is not False):
        raise RuntimeError("FAIL_CLOSED preregistration does not authorize this single run")
    if not CONFIRMATION.is_file():
        raise RuntimeError("FAIL_CLOSED recorded owner confirmation is missing; run not authorized")
    confirmation = json.loads(CONFIRMATION.read_text(encoding="utf-8"))
    if (confirmation.get("schema") != CONFIRMATION_SCHEMA or
            confirmation.get("confirmed") is not True or
            confirmation.get("preregistration_sha256") != preregistration_sha256 or
            not isinstance(confirmation.get("quote"), str) or
            not confirmation["quote"].strip()):
        raise RuntimeError("FAIL_CLOSED owner confirmation does not bind this preregistration")
    root = _artifact_root()
    output = _run_directory(root, project["project_id"])
    output.parent.mkdir(parents=True, exist_ok=True)
    lock = output.parent / f".{RUN_ID}.lock"
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise RuntimeError("another or interrupted process owns this run lock; "
                           "artifacts were left untouched") from exc
    try:
        payload = _json_bytes({"pid": os.getpid(), "project_id": project["project_id"],
                               "run_id": RUN_ID, "created_unix": time.time(),
                               "schema": "DINO_RUN_LOCK_V1"})
        with os.fdopen(fd, "wb") as stream:
            stream.write(payload); stream.flush(); os.fsync(stream.fileno())
        return _execute_locked(project=project, effective=effective, check=check,
                               binding=binding, preregistration_sha256=preregistration_sha256,
                               invocation_started=invocation_started, output=output)
    finally:
        try:
            lock.unlink(missing_ok=True)
        except OSError:
            pass


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true",
                        help="execute the one authorized run; default is no-solver preflight")
    parser.add_argument("--preregistration-sha256")
    parser.add_argument("--receipt", help="optional durable receipt path for the preflight output")
    args = parser.parse_args()
    if args.execute and not args.preregistration_sha256:
        parser.error("--execute requires --preregistration-sha256")
    if args.execute and args.receipt:
        parser.error("--receipt applies only to the no-solver preflight")
    try:
        if args.execute:
            result = run_execute(args.preregistration_sha256)
        else:
            result = run_validate(args.receipt)
    except Exception as exc:
        print(json.dumps({"status": "FAIL_CLOSED", "error": f"{type(exc).__name__}: {exc}"},
                         ensure_ascii=False))
        return 2
    if args.execute:
        summary = {"status": result["status"], "classification": result["classification"],
                   "cycles_completed": result["cycles_completed"],
                   "elapsed_seconds": result["elapsed_seconds"],
                   "timers_seconds": result["timers_seconds"],
                   "timer_shares_of_total_wall": result["timer_shares_of_total_wall"],
                   "rss_bytes": result["rss_bytes"],
                   "result_sha256": result["result_sha256"],
                   "artifact_directory": result["artifact_directory"]}
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0 if result["status"] in ("COMPLETE", "INTERRUPTED_CHECKPOINTED") else 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
