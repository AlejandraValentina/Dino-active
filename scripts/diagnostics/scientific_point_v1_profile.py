"""Bounded 48-cell subsystem profile for Scientific Point V1.

Runs a fresh five-degree segment (never a complete cycle), audits one already
persisted primary, and benchmarks checkpoint serialization in a new external
artifact directory. It never opens the historical checkpoint for resume.
"""
from __future__ import annotations

import cProfile
import gzip
import hashlib
import json
import os
from pathlib import Path
import pstats
import sys
import threading
import time
import tracemalloc
from datetime import datetime, timezone

import psutil

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from motorsim.desktop.preferences import repository_root_containing
from motorsim.exploratory_workflow import (
    RunCancelled, _advance_cycle, _atomic_write, _json_bytes, _rss_bytes,
)
from motorsim.integrated_2t import IntegratedEngine2T, audit_integrated_cycle_primary
from scripts.diagnostics.stage1.run_stage1_periodicity_focal_v1 import _load_configuration


class _StopAtFiveDegrees:
    def __init__(self) -> None:
        self.stopped = False

    def is_set(self) -> bool:
        return self.stopped


class _RssSampler:
    def __init__(self, interval_s: float = 0.01) -> None:
        self.process = psutil.Process()
        self.interval_s = interval_s
        self.samples: list[int] = []
        self.stop = threading.Event()
        self.thread = threading.Thread(target=self._sample, daemon=True)

    def _sample(self) -> None:
        while not self.stop.is_set():
            try:
                self.samples.append(self.process.memory_info().rss)
            except psutil.Error:
                pass
            self.stop.wait(self.interval_s)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *_args):
        self.stop.set()
        self.thread.join()
        try:
            self.samples.append(self.process.memory_info().rss)
        except psutil.Error:
            pass

    @property
    def peak_bytes(self) -> int | None:
        return max(self.samples) if self.samples else None


def _sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _source_sha(path: Path) -> str:
    return _sha(path.read_bytes().replace(bytes([13, 10]), bytes([10])))


def _external_run_dir(historical_root: str) -> Path:
    inferred_root = Path(historical_root).resolve().parents[1]
    configured_root = Path(os.environ.get("DINO_ARTIFACT_ROOT", str(inferred_root)))
    root = configured_root.expanduser().resolve()
    if repository_root_containing(root) is not None:
        raise RuntimeError("FAIL_CLOSED: DINO_ARTIFACT_ROOT resolves inside a repository")
    run_id = datetime.now(timezone.utc).strftime("profile-%Y%m%dT%H%M%SZ")
    target = root / "dino-2t-scientific-point-v1" / run_id
    if repository_root_containing(target) is not None:
        raise RuntimeError("FAIL_CLOSED: profile output resolves inside a repository")
    target.mkdir(parents=True, exist_ok=False)
    return target


def _segment(*, mode: str, native: dict, profile: cProfile.Profile | None = None,
             trace_allocations: bool = False) -> dict:
    engine = IntegratedEngine2T.from_configuration_dict(native)
    cancel = _StopAtFiveDegrees()
    process = psutil.Process()
    cpu_start = process.cpu_times()
    rss_start = _rss_bytes()
    sampler = _RssSampler()
    if trace_allocations:
        tracemalloc.start()
    wall_start = time.perf_counter()
    sampler.__enter__()
    if profile is not None:
        profile.enable()
    status = "UNEXPECTED_SEGMENT_COMPLETION"
    try:
        def progress(row: dict) -> None:
            if row["angle_deg"] >= 5.0:
                cancel.stopped = True

        _advance_cycle(engine, 1, deadline=time.monotonic() + 60.0,
                       cancel_event=cancel, progress=progress, memory_limit_mib=2048)
    except RunCancelled:
        status = "CANCELLED_AT_FIVE_DEGREES"
    finally:
        if profile is not None:
            profile.disable()
        wall_s = time.perf_counter() - wall_start
        sampler.__exit__()
    cpu_end = process.cpu_times()
    cpu_s = ((cpu_end.user - cpu_start.user) + (cpu_end.system - cpu_start.system))
    allocation_data = None
    if trace_allocations:
        current_bytes, peak_bytes = tracemalloc.get_traced_memory()
        snapshot = tracemalloc.take_snapshot()
        allocation_data = {
            "tracemalloc_current_bytes": current_bytes,
            "tracemalloc_peak_bytes": peak_bytes,
            "live_allocation_blocks_at_end": sum(row.count for row in snapshot.statistics("filename")),
            "measurement_note": "Net live Python allocation blocks, not cumulative allocation events; native allocations may be omitted.",
        }
        tracemalloc.stop()
    return {
        "mode": mode,
        "status": status,
        "wall_seconds": wall_s,
        "process_cpu_seconds": cpu_s,
        "cpu_percent_one_core_scale": 100.0 * cpu_s / wall_s if wall_s else None,
        "rss_start_bytes": rss_start,
        "sampled_peak_rss_bytes": sampler.peak_bytes,
        "rss_at_finish_bytes": _rss_bytes(),
        "sample_interval_ms": sampler.interval_s * 1000,
        "angle_end_deg": engine.crank_angle_unwrapped_deg,
        "accepted_steps": engine.accepted_steps,
        "rejected_steps": engine.rejected_steps,
        "seconds_per_accepted_step": wall_s / engine.accepted_steps if engine.accepted_steps else None,
        "allocation_data": allocation_data,
    }


def _profile_functions(profile: cProfile.Profile, limit: int = 300) -> list[dict]:
    stats = pstats.Stats(profile)
    rows = []
    for (filename, line, function), (primitive_calls, calls, self_s, cumulative_s, _callers) in sorted(
            stats.stats.items(), key=lambda row: row[1][2], reverse=True)[:limit]:
        rows.append({"file": filename.replace(str(ROOT), "<repo>"), "line": line,
                     "function": function, "primitive_calls": primitive_calls,
                     "calls": calls, "exclusive_self_seconds": self_s,
                     "cumulative_seconds_overlap": cumulative_s})
    return rows


def _subsystem_groups(rows: list[dict], total_self_s: float, *,
                      profile_phase: str) -> dict:
    groups = {name: {"exclusive_self_seconds": 0.0, "function_count": 0} for name in (
        "temporal_orchestration", "integrated_solver", "duct_wave_numerics",
        "thermodynamics_eos", "boundary_conditions", "interface_and_component_flows",
        "species_transport", "geometry_kinematics", "replay_audit",
        "serialization_copy_and_io", "other")}
    for row in rows:
        f, name = row["file"].lower().replace("\\", "/"), row["function"].lower()
        if "audit_integrated_cycle_primary" in name or "recompute_trace" in name:
            bucket = "replay_audit"
        elif any(token in name or token in f for token in (
                "_json_bytes", "_atomic_write", "canonical_json", "iterencode", "json/encoder.py",
                "gzip.py", "copy.py", "checkpoint")):
            bucket = "serialization_copy_and_io"
        elif "boundary.py" in f or "open_end_plenum" in f or "boundary" in name:
            bucket = "boundary_conditions"
        elif "p6_species.py" in f or any(token in name for token in (
                "species_transport", "donor_species", "species_flux", "species_inventory")):
            bucket = "species_transport"
        elif "thermal.py" in f or "fuel_combustion.py" in f or "eos.py" in f:
            bucket = "thermodynamics_eos"
        elif "/gas1d/" in f:
            bucket = "duct_wave_numerics"
        elif any(token in f for token in ("coupling.py", "network_components.py", "reed.py", "reed_coupling.py")):
            bucket = "interface_and_component_flows"
        elif any(token in f for token in ("powervalve.py", "two_stroke_ports.py", "kinematics.py")):
            bucket = "geometry_kinematics"
        elif "exploratory_workflow.py" in f:
            bucket = "temporal_orchestration"
        elif "integrated_2t.py" in f:
            bucket = ("replay_audit" if profile_phase == "stored_primary_replay"
                      else "integrated_solver")
        else:
            bucket = "other"
        groups[bucket]["exclusive_self_seconds"] += row["exclusive_self_seconds"]
        groups[bucket]["function_count"] += 1
    for value in groups.values():
        value["percent_of_profile_self_time"] = (
            100.0 * value["exclusive_self_seconds"] / total_self_s if total_self_s else 0.0)
    return {"groups": groups, "total_profile_self_seconds": total_self_s,
            "classification_rule": "Each Python function's exclusive self time is assigned to one group by module/function; cumulative figures are shown separately and overlap.",
            "profile_phase": profile_phase,
            "unmeasured_live_phases": ["complete-cycle audit and primary construction are measured separately from the short live segment", "the live segment does not reach durable checkpoint creation"]}


def main() -> int:
    receipt_path = ROOT / "results/dino-stage1-scientific-readiness/evidence/focal-periodicity-v1-result.json"
    historic = json.loads(receipt_path.read_text(encoding="utf-8"))
    _project, _refined, effective, preflight = _load_configuration()
    if preflight.get("status") != "PASS" or preflight.get("total_finite_volume_cells") != 48:
        raise RuntimeError("FAIL_CLOSED: expected the frozen 48-cell diagnostic configuration")
    output = _external_run_dir(historic["durable_artifacts"]["artifact_root"])
    native = effective["native_configuration"]

    plain = _segment(mode="uninstrumented_five_degree_segment", native=native)
    prof = cProfile.Profile()
    profiled = _segment(mode="cprofile_five_degree_segment", native=native, profile=prof)
    traced = _segment(mode="tracemalloc_five_degree_segment", native=native,
                      trace_allocations=True)
    for row in (plain, profiled, traced):
        if row["status"] != "CANCELLED_AT_FIVE_DEGREES" or row["angle_end_deg"] < 5.0:
            raise RuntimeError(f"FAIL_CLOSED: bounded segment ended unexpectedly: {row}")
    pstats_path = output / "five-degree-segment.pstats"
    prof.dump_stats(pstats_path)
    prof_rows = _profile_functions(prof)
    stats = pstats.Stats(prof)

    run_dir = Path(historic["durable_artifacts"]["run_directory"])
    first_cycle = historic["cycles"][0]
    packed = (run_dir / first_cycle["artifact"]).read_bytes()
    if _sha(packed) != first_cycle["compressed_sha256"]:
        raise RuntimeError("FAIL_CLOSED: historical compressed cycle hash mismatch")
    primary_bytes = gzip.decompress(packed)
    if _sha(primary_bytes) != first_cycle["primary_sha256"]:
        raise RuntimeError("FAIL_CLOSED: historical primary hash mismatch")
    parse_start = time.perf_counter(); primary = json.loads(primary_bytes); parse_s = time.perf_counter()-parse_start
    audit_profile = cProfile.Profile(); audit_start = time.perf_counter(); audit_profile.enable()
    audit = audit_integrated_cycle_primary(primary, preserve_precycle_p7_baseline=True)
    audit_profile.disable(); audit_wall_s = time.perf_counter() - audit_start
    if audit.get("status") != "PASS" or audit.get("recomputed") is not True:
        raise RuntimeError("FAIL_CLOSED: independent replay of the existing primary did not PASS")
    canonical_start = time.perf_counter(); canonical = _json_bytes(primary); canonical_s = time.perf_counter()-canonical_start
    audit_profile_path = output / "stored-primary-audit.pstats"
    audit_profile.dump_stats(audit_profile_path)

    checkpoint_path = run_dir / "checkpoint.json"
    checkpoint_bytes = checkpoint_path.read_bytes()
    if _sha(checkpoint_bytes) != historic["durable_artifacts"]["checkpoint_sha256"]:
        raise RuntimeError("FAIL_CLOSED: historical checkpoint hash mismatch")
    checkpoint = json.loads(checkpoint_bytes)
    atomic_target = output / "checkpoint-persistence-microbenchmark.json"
    serialization_rows = []
    for iteration in range(5):
        start = time.perf_counter(); payload = _json_bytes(checkpoint); serialize_s = time.perf_counter()-start
        start = time.perf_counter(); _atomic_write(atomic_target, payload); atomic_s = time.perf_counter()-start
        if _sha(atomic_target.read_bytes()) != _sha(payload):
            raise RuntimeError("atomic checkpoint persistence round-trip hash mismatch")
        serialization_rows.append({"iteration": iteration+1, "serialize_seconds": serialize_s,
                                    "atomic_write_seconds": atomic_s, "payload_bytes": len(payload),
                                    "payload_sha256": _sha(payload)})

    report = {
        "schema": "DINO_SCIENTIFIC_POINT_V1_BOUNDED_PROFILE_V1",
        "classification": "BOUNDED_PROFILE_ONLY_NO_COMPLETE_CYCLE",
        "recorded_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "profile_producer_sha256_normalized_lf": _source_sha(Path(__file__)),
        "selected_configuration": {"rpm": preflight["rpm"], "mesh_cells": preflight["total_finite_volume_cells"],
            "configuration_sha256": effective["native_configuration_sha256"],
            "engine_identity_sha256": effective["identity_sha256"]},
        "current_source_hashes_normalized_lf": {name: _source_sha(ROOT / path) for name, path in {
            "integrated_2t": "motorsim/integrated_2t.py", "exploratory_workflow": "motorsim/exploratory_workflow.py",
            "powervalve": "motorsim/powervalve.py", "periodicity": "motorsim/reference_harness/convergence.py"}.items()},
        "live_segments": {"uninstrumented": plain, "cprofile": profiled, "tracemalloc": traced,
            "cprofile_overhead_wall_ratio": profiled["wall_seconds"]/plain["wall_seconds"] if plain["wall_seconds"] else None,
            "tracemalloc_overhead_wall_ratio": traced["wall_seconds"]/plain["wall_seconds"] if plain["wall_seconds"] else None,
            "cprofile_exclusive_subsystems": _subsystem_groups(
                prof_rows, stats.total_tt, profile_phase="live_solver_segment"),
            "cprofile_top_functions": prof_rows[:80], "raw_pstats": pstats_path.name},
        "historical_primary_replay": {"cycle": first_cycle["cycle"], "compressed_sha256": _sha(packed),
            "primary_sha256": _sha(primary_bytes), "parse_seconds": parse_s,
            "independent_audit_wall_seconds_cprofile_instrumented": audit_wall_s,
            "audit_status": audit["status"], "audit_recomputed": audit["recomputed"],
            "canonical_serialize_seconds": canonical_s, "canonical_bytes": len(canonical),
            "exclusive_subsystems": _subsystem_groups(
                _profile_functions(audit_profile), pstats.Stats(audit_profile).total_tt,
                profile_phase="stored_primary_replay"),
            "top_functions": _profile_functions(audit_profile, limit=80), "raw_pstats": audit_profile_path.name},
        "checkpoint_persistence_microbenchmark": {"historical_checkpoint_sha256": _sha(checkpoint_bytes),
            "input_checkpoint_bytes": len(checkpoint_bytes), "source_note": "Read-only historical checkpoint used as serialization input; never restored or overwritten.",
            "iterations": serialization_rows, "median_serialize_seconds": sorted(x["serialize_seconds"] for x in serialization_rows)[2],
            "median_atomic_write_seconds": sorted(x["atomic_write_seconds"] for x in serialization_rows)[2],
            "measurement_limit": "External-root atomic write timing on this host; not a cycle checkpoint production timing."},
        "historical_focal_context": {"solver_seconds": historic["execution"]["solver_elapsed_seconds"],
            "configured_budget_seconds": historic["execution"]["budget_seconds"],
            "cycles_completed": historic["execution"]["cycles_completed"], "max_cycles": historic["scope"]["max_cycles"],
            "status": historic["execution"]["status"], "resume_performed": False,
            "historical_artifacts_modified": False},
        "limits": ["Five-degree segments are diagnostic micro-workloads, not representative cycle runtime.",
            "cProfile and tracemalloc slow the segment; ratios quantify this instrumentation only.",
            "Tracemalloc counts live Python allocations at end, not cumulative allocations and not all native allocations.",
            "A single historical-primary replay profile is not an end-to-end cycle timing.",
            "No solver optimization or scientific performance improvement is claimed."],
        "external_artifact_directory": str(output),
    }
    report_path = output / "profile-report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PASS", "report": str(report_path),
        "report_sha256": _sha(report_path.read_bytes()), "uninstrumented_seconds": plain["wall_seconds"],
        "cprofile_seconds": profiled["wall_seconds"], "tracemalloc_seconds": traced["wall_seconds"],
        "primary_audit_seconds": audit_wall_s, "audit_status": audit["status"],
        "maximum_sampled_rss_bytes": max(r["sampled_peak_rss_bytes"] or 0 for r in (plain, profiled, traced))},
        ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
