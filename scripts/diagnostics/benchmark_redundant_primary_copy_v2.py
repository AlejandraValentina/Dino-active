"""Bounded component benchmark for the workflow's removed full-primary JSON copy."""
from __future__ import annotations

import gzip
import hashlib
import json
import os
from pathlib import Path
import sys
import time
import threading
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from motorsim.desktop.preferences import repository_root_containing
from motorsim.exploratory_workflow import (_prepare_engineering_output_record,
                                           _rss_bytes)


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sample_peak(stop: threading.Event, samples: list[int]) -> None:
    while not stop.wait(.02):
        try:
            samples.append(_rss_bytes())
        except OSError:
            pass


def main() -> int:
    focal_path = ROOT / "results/dino-stage1-scientific-readiness/evidence/focal-periodicity-v1-result.json"
    focal = json.loads(focal_path.read_text(encoding="utf-8"))
    run_dir = Path(focal["durable_artifacts"]["run_directory"])
    cycle = focal["cycles"][0]
    packed = (run_dir / cycle["artifact"]).read_bytes()
    primary_bytes = gzip.decompress(packed)
    if _sha(primary_bytes) != cycle["primary_sha256"]:
        raise RuntimeError("FAIL_CLOSED: archived source primary hash mismatch")
    primary = json.loads(primary_bytes)
    evidence = {"status": "PERIOD_1", "terminal_cycle": 4,
                "configuration_hash": primary["configuration_hash"],
                "detector_sha256": "diagnostic-fixture"}

    samples = [_rss_bytes()]
    stop_sampling = threading.Event()
    sampler = threading.Thread(target=_sample_peak, args=(stop_sampling, samples), daemon=True)
    sampler.start()
    started = time.perf_counter()
    expected = json.loads(json.dumps(primary, allow_nan=False))
    baseline_seconds = time.perf_counter() - started
    expected["periodicity_evidence"] = evidence
    baseline_peak_rss = max(samples)
    del expected

    samples[:] = [_rss_bytes()]
    operation_count = 250_000
    optimized_batch_seconds = []
    for _ in range(3):
        started = time.perf_counter()
        for _index in range(operation_count):
            optimized = _prepare_engineering_output_record(primary, evidence)
            del optimized["periodicity_evidence"]
        optimized_batch_seconds.append(time.perf_counter() - started)
    optimized_median = sorted(optimized_batch_seconds)[1] / operation_count
    stop_sampling.set(); sampler.join(timeout=1)
    optimized_peak_rss = max(samples)

    optimized = _prepare_engineering_output_record(primary, evidence)
    expected = json.loads(json.dumps(primary, allow_nan=False))
    expected["periodicity_evidence"] = evidence
    equivalent = optimized == expected
    del optimized["periodicity_evidence"]
    del expected
    if not equivalent:
        raise RuntimeError("FAIL_CLOSED: direct metadata attachment differs from prior JSON-copy semantics")

    root_default = Path(focal["durable_artifacts"]["artifact_root"]).resolve().parents[1]
    artifact_root = Path(os.environ.get("DINO_ARTIFACT_ROOT", root_default)).expanduser().resolve()
    if repository_root_containing(artifact_root) is not None:
        raise RuntimeError("DINO_ARTIFACT_ROOT resolves inside a Git repository")
    run_id = datetime.now(timezone.utc).strftime("primary-copy-%Y%m%dT%H%M%SZ")
    out = artifact_root / "dino-stage1-solver-diagnostic-recovery" / "v2" / run_id
    if repository_root_containing(out) is not None:
        raise RuntimeError("benchmark artifacts would be written inside a Git repository")
    out.mkdir(parents=True, exist_ok=False)
    report = {
        "schema": "DINO_PRIMARY_METADATA_COPY_MICROBENCHMARK_V1",
        "classification": "COMPONENT_ONLY_NOT_END_TO_END",
        "source_primary_sha256": _sha(primary_bytes),
        "source_configuration_sha256": focal["preregistration"]["configuration_sha256"],
        "primary_uncompressed_bytes": len(primary_bytes),
        "iterations_per_method": {"prior_json_roundtrip": 1,
                                   "direct_metadata_attachment": operation_count * 3},
        "prior_json_roundtrip": {"wall_seconds": baseline_seconds,
            "sampled_peak_working_set_bytes": baseline_peak_rss},
        "direct_metadata_attachment": {"batch_wall_seconds": optimized_batch_seconds,
            "iterations_per_batch": operation_count,
            "median_seconds_per_operation": optimized_median,
            "sampled_peak_working_set_bytes": optimized_peak_rss},
        "semantic_equivalence": "EXACT_OBJECT_EQUALITY_AFTER_SAME_METADATA_ATTACHMENT",
        "physical_values_changed": False,
        "historical_source_modified": False,
        "measurement_limits": [
            "This isolates one full-primary copy operation from the existing audited 48-cell primary.",
            "It does not measure full simulation, artifact write, independent replay, or end-to-end runtime.",
            "Working-set peak is sampled every 20 ms and may miss shorter transients.",
            "No full-case speedup is claimed.",
        ],
        "raw_artifact_root": "${DINO_ARTIFACT_ROOT}/dino-stage1-solver-diagnostic-recovery/v2/" + run_id,
    }
    path = out / "benchmark.json"
    path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PASS", "report": str(path),
        "report_sha256": _sha(path.read_bytes()), "equivalent": equivalent,
        "baseline_seconds": report["prior_json_roundtrip"]["wall_seconds"],
        "optimized_median_seconds": report["direct_metadata_attachment"]["median_seconds_per_operation"],
        "primary_bytes": len(primary_bytes)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
