"""Profile a bounded in-memory FULL_RPM_SWEEP_V1 solver diagnostic only."""
from __future__ import annotations

import argparse
import cProfile
import gzip
import hashlib
import io
import json
import pstats
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.full_rpm_sweep_v1_campaign import (
    ROOT,
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
from motorsim.reference_harness.convergence import PeriodicDetectorV2


def _reason_category(reason: str) -> str:
    text = reason.lower()
    if "cfl limit exceeded" in text:
        return "CFL_LIMIT"
    if "species" in text or "rho/p/y inadmissible" in text:
        return "SPECIES_OR_STATE_ADMISSIBILITY"
    if "pressure" in text or "density" in text or "rho/p" in text:
        return "PRESSURE_OR_DENSITY"
    return "OTHER"


def profile_cycle(variant_id: str, rpm: int, degrees: float = 360.0) -> dict:
    prereg = _read_json(ROOT / PREREGISTRATION)
    variant = next((row for row in prereg["variants"]
                    if row["variant_id"] == variant_id), None)
    if variant is None or rpm not in prereg["rpm_grid"]["points_rpm"]:
        raise ValueError("variant/RPM must belong to the current preregistration")
    before = _solver_dependency_hashes()
    engine = IntegratedEngine2T.from_configuration_dict(
        _configuration_for(variant, rpm))
    if not 0.0 < degrees <= 360.0:
        raise ValueError("diagnostic angle must be in (0, 360]")
    rejected: list[dict] = []
    start_snapshot = engine.snapshot()
    profiler = cProfile.Profile()
    started = time.perf_counter()
    profiler.enable()
    _advance_to_bounded(engine, degrees, rejected, time.monotonic() + 540.0)
    end_snapshot = engine.snapshot()
    primary = make_integrated_cycle_primary(
        engine, start_snapshot, end_snapshot, 1, rejected_trials=rejected,
        runner_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    audit = audit_integrated_cycle_primary(primary)
    payload = json.dumps(primary, sort_keys=True, separators=(",", ":"),
                         ensure_ascii=False, allow_nan=False).encode("utf-8")
    with io.BytesIO() as compressed:
        with gzip.GzipFile(filename="", mode="wb", fileobj=compressed, mtime=0) as stream:
            stream.write(payload)
        primary_compressed_bytes = len(compressed.getvalue())
    detector = PeriodicDetectorV2()
    detector_observation = detector.update(_projection(primary))
    profiler.disable()
    elapsed = time.perf_counter() - started
    after = _solver_dependency_hashes()
    if before != after:
        raise RuntimeError("solver dependency hashes changed during diagnostic")

    stats = pstats.Stats(profiler)
    ranked = []
    for (filename, line, function), (primitive_calls, total_calls,
                                     self_seconds, cumulative_seconds, _) in sorted(
            stats.stats.items(), key=lambda item: item[1][3], reverse=True):
        ranked.append({
            "function": function,
            "file": Path(filename).name,
            "line": line,
            "primitive_calls": primitive_calls,
            "total_calls": total_calls,
            "self_seconds": self_seconds,
            "cumulative_seconds": cumulative_seconds,
        })
    categories = Counter(_reason_category(row["reason"]) for row in rejected)
    result_path = ROOT / "results/full-rpm-sweep-v1/preregistration.json"
    fixture_path = ROOT / variant["source_fixture_path"]
    return {
        "schema": "FULL_RPM_SWEEP_V1_DIAGNOSTIC_PROFILE_V1",
        "profile_scope": "one in-memory solver interval; no result, checkpoint, or campaign writes",
        "variant_id": variant_id,
        "rpm": rpm,
        "repository_head": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "crank_angle_degrees": degrees,
        "elapsed_seconds_with_cprofile": elapsed,
        "accepted_steps": engine.accepted_steps,
        "rejected_attempts": len(rejected),
        "rejection_reason_categories": dict(categories),
        "rejection_examples": rejected[:8],
        "solver_dependency_hashes_before": before,
        "solver_dependency_hashes_after": after,
        "preregistration_file_sha256": hashlib.sha256(result_path.read_bytes()).hexdigest(),
        "fixture_sha256": hashlib.sha256(fixture_path.read_bytes()).hexdigest(),
        "top_functions_by_cumulative_time": ranked[:50],
        "evidence_construction": {
            "primary_audit_recomputed": audit.get("recomputed"),
            "primary_sha256": hashlib.sha256(payload).hexdigest(),
            "primary_uncompressed_bytes": len(payload),
            "primary_compressed_bytes": primary_compressed_bytes,
            "periodicity_observation": detector_observation,
            "conservation": primary.get("conservation"),
        },
        "profile_overhead_warning": (
            "cProfile changes wall time; use this run only for relative hotspot ranking, "
            "not as the unprofiled baseline."),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--variant", default="A_PRIME_MESH_0")
    parser.add_argument("--rpm", type=int, default=4000)
    parser.add_argument("--degrees", type=float, default=360.0)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = profile_cycle(args.variant, args.rpm, args.degrees)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True,
                                      allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output),
                      "elapsed_seconds_with_cprofile": report["elapsed_seconds_with_cprofile"],
                      "accepted_steps": report["accepted_steps"],
                      "rejected_attempts": report["rejected_attempts"],
                      "rejection_reason_categories": report["rejection_reason_categories"],
                      "top_functions": report["top_functions_by_cumulative_time"][:12]},
                     sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
