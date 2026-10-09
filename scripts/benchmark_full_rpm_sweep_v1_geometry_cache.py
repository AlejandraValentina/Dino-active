"""Small in-memory baseline vs geometry-memoization benchmark.

The candidate wraps an existing engine instance. It does not change or patch
the protected solver implementation and writes no campaign point artifacts.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import statistics
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.full_rpm_sweep_v1_campaign import (
    PREREGISTRATION,
    _advance_to_bounded,
    _configuration_for,
    _projection,
    _read_json,
)
from motorsim.integrated_2t import (
    IntegratedEngine2T,
    _solver_dependency_hashes,
    audit_integrated_cycle_primary,
    make_integrated_cycle_primary,
)
from motorsim.performance_geometry_cache_v1 import install_immutable_geometry_cache_v1
from motorsim.reference_harness.convergence import PeriodicDetectorV2


def _rss_bytes() -> int | None:
    try:
        import psutil
        import os
        return int(psutil.Process(os.getpid()).memory_info().rss)
    except (ImportError, OSError):
        return None


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def _run_one(variant: dict, rpm: int, *, cached: bool, runner_sha256: str) -> dict:
    engine = IntegratedEngine2T.from_configuration_dict(
        _configuration_for(variant, rpm))
    geometry_cache = install_immutable_geometry_cache_v1(engine) if cached else None
    started = time.perf_counter()
    stage_timings = {}
    stage = time.perf_counter()
    start_snapshot = engine.snapshot()
    stage_timings["start_snapshot_seconds"] = time.perf_counter() - stage
    rejected = []
    step_times = {"accepted_seconds": 0.0, "rejected_seconds": 0.0,
                  "accepted_calls": 0, "rejected_calls": 0}
    original_step = engine.step

    def timed_step(*args, **kwargs):
        call_started = time.perf_counter()
        try:
            value = original_step(*args, **kwargs)
        except ValueError:
            step_times["rejected_seconds"] += time.perf_counter() - call_started
            step_times["rejected_calls"] += 1
            raise
        step_times["accepted_seconds"] += time.perf_counter() - call_started
        step_times["accepted_calls"] += 1
        return value

    engine.step = timed_step
    rss_before = _rss_bytes()
    solver_started = time.perf_counter()
    _advance_to_bounded(engine, 360.0, rejected, time.monotonic() + 540.0)
    solver_elapsed = time.perf_counter() - solver_started
    stage = time.perf_counter()
    end_snapshot = engine.snapshot()
    stage_timings["end_snapshot_seconds"] = time.perf_counter() - stage
    stage = time.perf_counter()
    primary = make_integrated_cycle_primary(
        engine, start_snapshot, end_snapshot, 1,
        rejected_trials=rejected, runner_sha256=runner_sha256)
    stage_timings["primary_construction_seconds"] = time.perf_counter() - stage
    stage = time.perf_counter()
    audit = audit_integrated_cycle_primary(primary)
    stage_timings["primary_audit_seconds"] = time.perf_counter() - stage
    stage = time.perf_counter()
    detector = PeriodicDetectorV2()
    periodicity_observation = detector.update(_projection(primary))
    stage_timings["periodicity_seconds"] = time.perf_counter() - stage
    stage = time.perf_counter()
    primary_payload = _canonical(primary)
    with io.BytesIO() as compressed:
        with gzip.GzipFile(filename="", mode="wb", fileobj=compressed, mtime=0) as stream:
            stream.write(primary_payload)
        primary_compressed_bytes = len(compressed.getvalue())
    stage_timings["primary_serialization_compression_seconds"] = time.perf_counter() - stage
    stage = time.perf_counter()
    engine.compact_cycle_trace()
    checkpoint_snapshot = engine.snapshot()
    checkpoint_payload = json.dumps(
        {"engine_snapshot": checkpoint_snapshot,
         "periodicity_snapshot": detector.snapshot()},
        sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        allow_nan=False).encode("utf-8")
    stage_timings["checkpoint_serialization_seconds"] = time.perf_counter() - stage
    elapsed = time.perf_counter() - started
    rss_after = _rss_bytes()
    return {
        "elapsed_seconds": elapsed,
        "solver_interval_seconds": solver_elapsed,
        "attempt_timing": step_times,
        "stage_timings_seconds": stage_timings,
        "evidence_construction_seconds": sum(stage_timings.values()),
        "primary_uncompressed_bytes": len(primary_payload),
        "primary_compressed_bytes": primary_compressed_bytes,
        "checkpoint_serialized_bytes": len(checkpoint_payload),
        "accepted_steps": engine.accepted_steps,
        "rejected_steps": len(rejected),
        "rejection_categories": dict(Counter(
            "CFL_LIMIT" if "CFL limit exceeded" in row["reason"] else
            "SPECIES_OR_STATE" if "species" in row["reason"].lower() else "OTHER"
            for row in rejected)),
        "process_rss_before_bytes": rss_before,
        "process_rss_after_bytes": rss_after,
        "primary_sha256": hashlib.sha256(_canonical(primary)).hexdigest(),
        "primary": primary,
        "engine_terminal_snapshot_sha256": hashlib.sha256(
            _canonical(end_snapshot)).hexdigest(),
        "primary_audit_recomputed": audit.get("recomputed"),
        "conservation": primary.get("conservation"),
        "species_inventory": primary.get("species_inventory"),
        "energy_inventory": primary.get("energy_inventory"),
        "periodicity_observation": periodicity_observation,
        "geometry_cache": ({**geometry_cache.receipt(),
                            "estimated_container_bytes": (
                                sys.getsizeof(geometry_cache._cache) +
                                sum(sys.getsizeof(key) + sys.getsizeof(value)
                                    for key, value in geometry_cache._cache.items()))}
                           if geometry_cache else None),
    }


def benchmark(variant_id: str = "A_PRIME_MESH_0", rpm: int = 4000,
              repeats: int = 3) -> dict:
    if repeats < 3:
        raise ValueError("at least three paired repeats are required")
    prereg = _read_json(ROOT / PREREGISTRATION)
    variant = next(row for row in prereg["variants"]
                   if row["variant_id"] == variant_id)
    if rpm not in prereg["rpm_grid"]["points_rpm"]:
        raise ValueError("RPM is outside the preregistered grid")
    dependency_hashes = _solver_dependency_hashes()
    runner_sha256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    baseline, candidate = [], []
    for _ in range(repeats):
        baseline.append(_run_one(variant, rpm, cached=False,
                                 runner_sha256=runner_sha256))
        candidate.append(_run_one(variant, rpm, cached=True,
                                  runner_sha256=runner_sha256))
    baseline_times = [row["elapsed_seconds"] for row in baseline]
    candidate_times = [row["elapsed_seconds"] for row in candidate]
    equivalent = all(
        base["primary_sha256"] == opt["primary_sha256"] and
        base["engine_terminal_snapshot_sha256"] ==
        opt["engine_terminal_snapshot_sha256"] and
        base["primary_audit_recomputed"] is True and
        opt["primary_audit_recomputed"] is True and
        base["periodicity_observation"] == opt["periodicity_observation"]
        for base, opt in zip(baseline, candidate))
    if any(_solver_dependency_hashes() != dependency_hashes for _ in (0,)):
        raise RuntimeError("protected solver hashes changed during benchmark")
    return {
        "schema": "FULL_RPM_SWEEP_V1_GEOMETRY_CACHE_BENCHMARK_V1",
        "scope": "in-memory one-cycle diagnostics; no campaign result/checkpoint writes",
        "variant_id": variant_id,
        "rpm": rpm,
        "repeats": repeats,
        "candidate": "instance-local memoization of frozen EngineGeometry2T by (angle mod 360, rpm); end-to-end includes primary build/audit, compression, detector update and checkpoint JSON serialization, excludes filesystem writes",
        "protected_solver_dependency_hashes": dependency_hashes,
        "baseline_seconds": baseline_times,
        "candidate_seconds": candidate_times,
        "baseline_median_seconds": statistics.median(baseline_times),
        "candidate_median_seconds": statistics.median(candidate_times),
        "measured_speedup": statistics.median(baseline_times) /
        statistics.median(candidate_times),
        "numerically_equivalent": equivalent,
        "all_baseline_primaries_replayed": all(row["primary_audit_recomputed"]
                                                is True for row in baseline),
        "all_candidate_primaries_replayed": all(row["primary_audit_recomputed"]
                                                is True for row in candidate),
        "conservation_species_energy_periodicity_equal": equivalent,
        "baseline_process_rss_before_bytes": [row["process_rss_before_bytes"]
                                              for row in baseline],
        "baseline_process_rss_after_bytes": [row["process_rss_after_bytes"]
                                             for row in baseline],
        "candidate_process_rss_before_bytes": [row["process_rss_before_bytes"]
                                               for row in candidate],
        "candidate_process_rss_after_bytes": [row["process_rss_after_bytes"]
                                              for row in candidate],
        "baseline_rejected_steps": [row["rejected_steps"] for row in baseline],
        "candidate_rejected_steps": [row["rejected_steps"] for row in candidate],
        "baseline_rejection_categories": baseline[0]["rejection_categories"],
        "candidate_rejection_categories": candidate[0]["rejection_categories"],
        "candidate_geometry_cache_counts": [row["geometry_cache"]
                                            for row in candidate],
        "baseline_stage_timing_medians_seconds": {
            key: statistics.median(row["stage_timings_seconds"][key]
                                   for row in baseline)
            for key in baseline[0]["stage_timings_seconds"]},
        "candidate_stage_timing_medians_seconds": {
            key: statistics.median(row["stage_timings_seconds"][key]
                                   for row in candidate)
            for key in candidate[0]["stage_timings_seconds"]},
        "equivalence_basis": "exact primary and terminal snapshot hashes plus replay, conservation, species, energy, periodicity observation, and rejected-step counts",
        "baseline_runs": [{k: v for k, v in row.items() if k != "primary"}
                          for row in baseline],
        "candidate_runs": [{k: v for k, v in row.items() if k != "primary"}
                           for row in candidate],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--variant", default="A_PRIME_MESH_0")
    parser.add_argument("--rpm", type=int, default=4000)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = benchmark(args.variant, args.rpm, args.repeats)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True,
                                      ensure_ascii=False, allow_nan=False) + "\n",
                           encoding="utf-8")
    print(json.dumps({k: report[k] for k in (
        "schema", "baseline_median_seconds", "candidate_median_seconds",
        "measured_speedup", "numerically_equivalent",
        "conservation_species_energy_periodicity_equal",
        "baseline_rejected_steps", "candidate_rejected_steps")}, sort_keys=True))
    return 0 if report["numerically_equivalent"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
