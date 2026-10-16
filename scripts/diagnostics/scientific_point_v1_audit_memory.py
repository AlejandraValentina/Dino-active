"""Measure wall/CPU/RSS of one independent replay of the stored focal primary."""
from __future__ import annotations

import gzip
import hashlib
import json
from pathlib import Path
import sys
import time
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from motorsim.exploratory_workflow import _rss_bytes
from motorsim.integrated_2t import audit_integrated_cycle_primary
from scripts.diagnostics.scientific_point_v1_profile import _RssSampler, _sha


def main() -> int:
    focal_path = ROOT / "results/dino-stage1-scientific-readiness/evidence/focal-periodicity-v1-result.json"
    focal = json.loads(focal_path.read_text(encoding="utf-8"))
    run_dir = Path(focal["durable_artifacts"]["run_directory"])
    cycle = focal["cycles"][0]
    packed = (run_dir / cycle["artifact"]).read_bytes()
    if _sha(packed) != cycle["compressed_sha256"]:
        raise RuntimeError("FAIL_CLOSED: compressed primary hash mismatch")
    payload = gzip.decompress(packed)
    if _sha(payload) != cycle["primary_sha256"]:
        raise RuntimeError("FAIL_CLOSED: canonical primary hash mismatch")
    primary = json.loads(payload)
    sampler = _RssSampler()
    start_rss = _rss_bytes()
    start_cpu = time.process_time()
    start_wall = time.perf_counter()
    with sampler:
        audit = audit_integrated_cycle_primary(primary, preserve_precycle_p7_baseline=True)
    wall_s = time.perf_counter() - start_wall
    cpu_s = time.process_time() - start_cpu
    if audit.get("status") != "PASS" or audit.get("recomputed") is not True:
        raise RuntimeError("FAIL_CLOSED: recomputed independent primary audit failed")
    out_dir = Path(sys.argv[1]).resolve()
    out = out_dir / "replay-memory-audit.json"
    report = {
        "schema": "DINO_SCIENTIFIC_POINT_V1_REPLAY_RESOURCE_MEASUREMENT",
        "recorded_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "primary_artifact_sha256": _sha(payload),
        "compressed_artifact_sha256": _sha(packed),
        "audit_status": audit["status"],
        "audit_recomputed": audit["recomputed"],
        "audit_wall_seconds_uninstrumented": wall_s,
        "audit_process_cpu_seconds": cpu_s,
        "cpu_percent_one_core_scale": 100.0 * cpu_s / wall_s if wall_s else None,
        "rss_start_bytes": start_rss,
        "rss_peak_sampled_bytes": sampler.peak_bytes,
        "rss_finish_bytes": _rss_bytes(),
        "rss_sample_interval_ms": sampler.interval_s * 1000,
        "native_artifact_bytes": len(payload),
        "historical_artifacts_modified": False,
        "checkpoint_restored": False,
    }
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PASS", "report": str(out),
                      "report_sha256": _sha(out.read_bytes()),
                      "audit_wall_seconds": wall_s, "audit": audit["status"],
                      "rss_peak_sampled_bytes": sampler.peak_bytes}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
