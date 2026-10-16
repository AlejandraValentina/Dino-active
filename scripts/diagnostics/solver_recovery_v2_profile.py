"""Bounded profiler: a short 48-cell solver segment plus one stored-cycle replay.

This does not complete a cycle, create a checkpoint, or resume a historical run.
Raw profiler files are written only to an external artifact root.
"""
from __future__ import annotations

import cProfile
import gzip
import hashlib
import json
import os
from pathlib import Path
import pstats
import re
import sys
import threading
import time
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from motorsim.desktop.preferences import repository_root_containing
from motorsim.exploratory_workflow import (_advance_cycle, _json_bytes, _rss_bytes,
                                           RunCancelled)
from motorsim.integrated_2t import (IntegratedEngine2T,
                                    audit_integrated_cycle_primary)
from scripts.diagnostics.stage1.run_stage1_periodicity_focal_v1 import _load_configuration


class _StopAfterFiveDegrees:
    def __init__(self):
        self.stopped = False

    def is_set(self):
        return self.stopped


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _external_root(focal_artifact_root: str) -> Path:
    default_root = Path(focal_artifact_root).resolve().parents[1]
    root = Path(os.environ.get("DINO_ARTIFACT_ROOT", default_root)).expanduser().resolve()
    if repository_root_containing(root) is not None:
        raise RuntimeError("DINO_ARTIFACT_ROOT resolves inside a Git repository")
    run_id = datetime.now(timezone.utc).strftime("profile-%Y%m%dT%H%M%SZ")
    target = root / "dino-stage1-solver-diagnostic-recovery" / "v2" / run_id
    if repository_root_containing(target) is not None:
        raise RuntimeError("profile output path resolves inside a Git repository")
    target.mkdir(parents=True, exist_ok=True)
    return target


def _profile_rows(profile: cProfile.Profile, limit: int = 200) -> list[dict]:
    stats = pstats.Stats(profile)
    ordered = sorted(stats.stats.items(), key=lambda row: row[1][3], reverse=True)[:limit]
    rows = []
    for (filename, line, name), (primitive, calls, self_seconds, cumulative, _callers) in ordered:
        rows.append({"function": name, "file": filename.replace(str(ROOT), "<repo>"),
                     "line": line, "primitive_calls": primitive, "calls": calls,
                     "self_seconds": self_seconds, "cumulative_seconds": cumulative})
    return rows


def _group_totals(rows: list[dict], total_self_seconds: float, *, phase: str) -> dict:
    groups = {key: {"self_seconds": 0.0, "function_count": 0} for key in (
        "copies_and_serialization", "species_validation_and_transport",
        "duct_numerics", "interfaces_and_geometry", "replay_primary_audit",
        "engine_integration_and_other")}
    for row in rows:
        name, filename = row["function"].lower(), row["file"].lower()
        if "copy.py" in filename or any(token in name for token in
                ("_jsonify", "canonical_json", "iterencode", "dumps", "encode")):
            bucket = "copies_and_serialization"
        elif "p6_species" in filename or any(token in name for token in
                ("species", "transport", "donor_species", "inventory")):
            bucket = "species_validation_and_transport"
        elif "gas1d" in filename or any(token in name for token in
                ("_assemble", "hllc_flux", "primitive", "wave_speed", "duct")):
            bucket = "duct_numerics"
        elif any(token in name for token in ("interface", "area_at", "powervalve", "port")):
            bucket = "interfaces_and_geometry"
        elif phase == "stored_primary_replay" and any(token in name for token in
                ("audit_integrated_cycle_primary", "make_integrated_cycle_primary",
                 "recompute_trace", "evidence_sha256")):
            bucket = "replay_primary_audit"
        else:
            bucket = "engine_integration_and_other"
        groups[bucket]["self_seconds"] += row["self_seconds"]
        groups[bucket]["function_count"] += 1
    for item in groups.values():
        item["percent_of_profile_self_time"] = (
            100.0 * item["self_seconds"] / total_self_seconds
            if total_self_seconds else 0.0)
    return {"exclusive_self_time_groups": groups,
            "sum_self_seconds": sum(row["self_seconds"] for row in rows),
            "total_profile_self_seconds": total_self_seconds,
            "cumulative_functions_overlap_and_are_reported_separately": True}


def main() -> int:
    focal = json.loads((ROOT / "results/dino-stage1-scientific-readiness/evidence/focal-periodicity-v1-result.json").read_text(encoding="utf-8"))
    output = _external_root(focal["durable_artifacts"]["artifact_root"])
    _project, refined, effective, preflight = _load_configuration()
    if preflight.get("status") != "PASS" or preflight.get("total_finite_volume_cells") != 48:
        raise RuntimeError("FAIL_CLOSED: expected frozen 48-cell Stage 1 configuration")
    engine = IntegratedEngine2T.from_configuration_dict(effective["native_configuration"])
    cancel = _StopAfterFiveDegrees()
    profile = cProfile.Profile()
    segment_started = time.perf_counter()
    segment_cpu_started = time.process_time()
    profile.enable()
    try:
        def progress(row):
            if row["angle_deg"] >= 5.0:
                cancel.stopped = True
        _advance_cycle(engine, 1, deadline=time.monotonic() + 60.0,
                       cancel_event=cancel, progress=progress, memory_limit_mib=2048)
        segment_status = "UNEXPECTED_SEGMENT_COMPLETION"
    except RunCancelled:
        segment_status = "CANCELLED_AT_BOUNDARY_AFTER_PROGRESS_CALLBACK"
    finally:
        profile.disable()
    segment_wall = time.perf_counter() - segment_started
    segment_cpu = time.process_time() - segment_cpu_started
    segment_rows = _profile_rows(profile)
    segment_total_self = pstats.Stats(profile).total_tt
    segment_prof_path = output / "48cell-short-segment.pstats"
    profile.dump_stats(segment_prof_path)

    durable = focal["durable_artifacts"]
    run_dir = Path(durable["run_directory"])
    cycle_row = focal["cycles"][0]
    packed = (run_dir / cycle_row["artifact"]).read_bytes()
    primary_bytes = gzip.decompress(packed)
    if _sha(primary_bytes) != cycle_row["primary_sha256"]:
        raise RuntimeError("FAIL_CLOSED: stored focal primary hash does not match receipt")
    primary_profile = cProfile.Profile()
    replay_started = time.perf_counter()
    primary_profile.enable()
    try:
        primary = json.loads(primary_bytes)
        audit = audit_integrated_cycle_primary(primary, preserve_precycle_p7_baseline=True)
        canonical_bytes = _json_bytes(primary)
    finally:
        primary_profile.disable()
    replay_wall = time.perf_counter() - replay_started
    if audit.get("status") != "PASS" or audit.get("recomputed") is not True:
        raise RuntimeError("FAIL_CLOSED: stored focal primary failed current independent replay")
    replay_rows = _profile_rows(primary_profile)
    replay_total_self = pstats.Stats(primary_profile).total_tt
    replay_prof_path = output / "48cell-stored-primary-replay.pstats"
    primary_profile.dump_stats(replay_prof_path)

    report = {
        "schema": "DINO_SOLVER_RECOVERY_V2_BOUNDED_PROFILE_V1",
        "classification": "BOUNDED_PROFILE_ONLY_NO_COMPLETE_CYCLE",
        "source_focal_receipt": "results/dino-stage1-scientific-readiness/evidence/focal-periodicity-v1-result.json",
        "frozen_preregistration_sha256": focal["preregistration"]["sha256"],
        "configuration_sha256": preflight["configuration_sha256"],
        "mesh_cells": preflight["total_finite_volume_cells"],
        "rpm": preflight["rpm"],
        "solver_segment": {
            "status": segment_status,
            "angle_end_deg": engine.crank_angle_unwrapped_deg,
            "wall_seconds": segment_wall,
            "process_cpu_seconds": segment_cpu,
            "rss_at_finish_bytes": _rss_bytes(),
            "cprofile_artifact": segment_prof_path.name,
            "functions": segment_rows,
            "subsystem_groups": _group_totals(segment_rows, segment_total_self,
                                                phase="solver_segment"),
        },
        "stored_primary_replay": {
            "cycle": cycle_row["cycle"],
            "compressed_sha256": _sha(packed),
            "primary_sha256": _sha(primary_bytes),
            "audit_status": audit["status"],
            "audit_recomputed": audit["recomputed"],
            "wall_seconds_including_parse_audit_canonical_serialization": replay_wall,
            "canonical_serialized_bytes": len(canonical_bytes),
            "cprofile_artifact": replay_prof_path.name,
            "functions": replay_rows,
            "subsystem_groups": _group_totals(replay_rows, replay_total_self,
                                                phase="stored_primary_replay"),
        },
        "historical_production_run_context": {
            "whole_run_seconds": focal["execution"]["solver_elapsed_seconds"],
            "completed_cycles": focal["execution"]["cycles_completed"],
            "resumed": False,
            "historical_artifacts_modified": False,
        },
        "measurement_limits": [
            "The live 48-cell profile is a short segment ending after the progress callback near 5 degrees; it is not a cycle or representative runtime estimate.",
            "The replay profile uses a verified stored primary and includes JSON parsing, current independent audit and canonical serialization.",
            "No before/after optimization or full 48-cell performance improvement is claimed.",
            "Cumulative function timings overlap; grouped totals are diagnostic only.",
        ],
        "raw_artifact_root": str(output),
    }
    report_path = output / "bounded-profile.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PASS", "report": str(report_path),
        "report_sha256": _sha(report_path.read_bytes()),
        "segment_wall_seconds": segment_wall, "segment_status": segment_status,
        "replay_wall_seconds": replay_wall, "audit": audit["status"],
        "rss_bytes": _rss_bytes()}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
