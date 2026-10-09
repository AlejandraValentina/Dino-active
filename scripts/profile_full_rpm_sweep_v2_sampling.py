"""Low-rate, uninstrumented stack sampling of one in-memory cycle per mesh."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import threading
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.benchmark_full_rpm_sweep_v1_geometry_cache import (  # noqa: E402
    ROOT as REPO_ROOT, _read_json, _run_one,
)
from scripts.full_rpm_sweep_v1_campaign import PREREGISTRATION  # noqa: E402


def sample_variant(variant_id: str, interval_s: float = .01) -> dict:
    import psutil
    process = psutil.Process()
    prereg = _read_json(REPO_ROOT / PREREGISTRATION)
    variant = next(row for row in prereg["variants"]
                   if row["variant_id"] == variant_id)
    main_ident = threading.main_thread().ident
    stop = threading.Event()
    inclusive: Counter[tuple[str, str]] = Counter()
    self_samples: Counter[tuple[str, str]] = Counter()
    samples = 0
    peak_rss = process.memory_info().rss

    def sampler():
        nonlocal samples, peak_rss
        while not stop.wait(interval_s):
            frame = sys._current_frames().get(main_ident)
            if frame is None:
                continue
            samples += 1
            leaf = (Path(frame.f_code.co_filename).name, frame.f_code.co_name)
            self_samples[leaf] += 1
            while frame is not None:
                key = (Path(frame.f_code.co_filename).name, frame.f_code.co_name)
                inclusive[key] += 1
                frame = frame.f_back
            try:
                peak_rss = max(peak_rss, process.memory_info().rss)
            except (psutil.Error, OSError):
                pass

    worker = threading.Thread(target=sampler, name="rpm-stack-sampler", daemon=True)
    worker.start()
    runner_sha = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    started = time.perf_counter()
    try:
        run = _run_one(variant, 4000, cached=False, runner_sha256=runner_sha)
    finally:
        stop.set()
        worker.join()
    total = max(samples, 1)

    def rank(counter):
        return [{"file": key[0], "function": key[1], "samples": count,
                 "sampled_wall_fraction": count / total}
                for key, count in counter.most_common(40)]

    return {
        "schema": "FULL_RPM_SWEEP_V1_IMPL2_LOW_RATE_PROFILE_V1",
        "variant_id": variant_id,
        "rpm": 4000,
        "sampler_interval_seconds": interval_s,
        "sample_count": samples,
        "elapsed_seconds": run["elapsed_seconds"],
        "solver_interval_seconds": run["solver_interval_seconds"],
        "evidence_construction_seconds": run["evidence_construction_seconds"],
        "accepted_step_time": run["attempt_timing"]["accepted_seconds"],
        "rejected_step_time": run["attempt_timing"]["rejected_seconds"],
        "accepted_steps": run["attempt_timing"]["accepted_calls"],
        "rejected_steps": run["attempt_timing"]["rejected_calls"],
        "primary_audit_recomputed": run["primary_audit_recomputed"],
        "primary_bytes": run["primary_uncompressed_bytes"],
        "peak_sampled_rss_bytes": peak_rss,
        "inclusive_stack_samples": rank(inclusive),
        "self_stack_samples": rank(self_samples),
        "sampling_overhead_note": "10 ms stack sampling; no cProfile or trace hooks; RSS sampled in the same low-rate loop",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    results = [sample_variant(name) for name in
               ("A_PRIME_MESH_0", "B_PRIME_MESH_0")]
    report = {"schema": "FULL_RPM_SWEEP_V1_IMPL2_PROFILE_REPORT_V1",
              "campaign_started": False, "runs": results}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n",
                           encoding="utf-8")
    print(json.dumps({"output": str(args.output),
                      "variants": [{k: row[k] for k in (
                          "variant_id", "elapsed_seconds", "solver_interval_seconds",
                          "evidence_construction_seconds", "sample_count",
                          "peak_sampled_rss_bytes")}
                                    for row in results]}, sort_keys=True))
    return 0 if all(row["primary_audit_recomputed"] is True for row in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
