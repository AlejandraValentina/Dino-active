"""Read-only replay of saved periodicity comparisons from the historical focal point."""
from __future__ import annotations

import gzip
import hashlib
import json
import os
from pathlib import Path
import sys
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from motorsim.desktop.preferences import repository_root_containing
from motorsim.exploratory_workflow import CYCLE_PRIMARY_CONTRACT
from motorsim.reference_harness.convergence import PeriodicDetectorV2


def _sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _canonical(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: scientific_point_v1_periodicity_replay.py OUTPUT_DIR")
    receipt_path = ROOT / "results/dino-stage1-scientific-readiness/evidence/focal-periodicity-v1-result.json"
    focal = json.loads(receipt_path.read_text(encoding="utf-8"))
    run_dir = Path(focal["durable_artifacts"]["run_directory"])
    manifest_path = Path(focal["durable_artifacts"]["manifest_path"])
    if not manifest_path.is_absolute():
        manifest_path = run_dir / manifest_path
    manifest_bytes = manifest_path.read_bytes()
    if _sha(manifest_bytes) != focal["durable_artifacts"]["manifest_sha256"]:
        raise RuntimeError("FAIL_CLOSED: historical manifest hash mismatch")
    manifest = json.loads(manifest_bytes)
    detector = PeriodicDetectorV2()
    cycles = []
    for row in focal["cycles"]:
        compressed = (run_dir / row["artifact"]).read_bytes()
        if _sha(compressed) != row["compressed_sha256"]:
            raise RuntimeError(f"FAIL_CLOSED: compressed primary hash mismatch for cycle {row['cycle']}")
        primary_bytes = gzip.decompress(compressed)
        if _sha(primary_bytes) != row["primary_sha256"]:
            raise RuntimeError(f"FAIL_CLOSED: canonical primary hash mismatch for cycle {row['cycle']}")
        primary = json.loads(primary_bytes)
        record = {
            "cycle_index": row["cycle"],
            "configuration_hash": primary["configuration_hash"],
            "contract": CYCLE_PRIMARY_CONTRACT,
            "observables": primary["observables"],
        }
        recomputed = detector.update(record)
        persisted_row = manifest["cycles"][row["cycle"] - 1]
        persisted = persisted_row["periodicity_update"]
        exact = _canonical(recomputed) == _canonical(persisted)
        if not exact:
            raise RuntimeError(f"FAIL_CLOSED: periodicity update replay differs at cycle {row['cycle']}")
        outcomes = recomputed["outcomes"]
        comparisons = {}
        for label in ("lag1", "lag2"):
            comparison = outcomes.get(label)
            if comparison is None:
                continue
            metrics = comparison.get("metrics", {})
            comparisons[label] = {
                "status": comparison["status"],
                "older_cycle": comparison.get("older_cycle"),
                "later_cycle": comparison.get("later_cycle"),
                "metrics_count": len(metrics),
                "failed_metric_count": sum(not metric["passed"] for metric in metrics.values()),
                "max_residual": max((metric["value"] for metric in metrics.values()), default=0.0),
                "max_threshold": max((metric["threshold"] for metric in metrics.values()), default=0.0),
            }
        cycles.append({"cycle": row["cycle"], "update_recomputed_exactly": exact,
                       "detector_executed": True, "classification_after_cycle": detector.classification,
                       "lag1_streak": recomputed["lag1_streak"],
                       "branch_streaks": recomputed["branch_streaks"],
                       "comparisons": comparisons,
                       "audit_recomputed_in_historical_receipt": row["audit_recomputed"]})

    assert detector.classification is None
    assert focal["execution"]["cycles_completed"] == 4
    assert focal["scope"]["max_cycles"] == 8
    assert focal["execution"]["periodicity"] == "NOT_EVALUATED"
    old_source = focal["preregistration"]["runner_sha256"]
    report = {
        "schema": "DINO_SCIENTIFIC_POINT_V1_PERIODICITY_REPLAY",
        "recorded_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "classification": "NO_PERIOD_ACCEPTED_BEFORE_TIMEOUT",
        "scope": {"rpm": focal["scope"]["rpm"], "mesh_cells": focal["scope"]["cells_total"],
                  "complete_cycles": focal["execution"]["cycles_completed"],
                  "registered_max_cycles": focal["scope"]["max_cycles"],
                  "periodicity_contract": focal["periodicity_contract"] if "periodicity_contract" in focal else "REFERENCE_PERIODIC_CONVERGENCE_V2"},
        "historical_result_field_preserved": focal["execution"]["periodicity"],
        "detector_executed": True,
        "recomputed_detector_classification": detector.classification,
        "lag1_comparisons": sum("lag1" in cycle["comparisons"] for cycle in cycles),
        "lag2_comparisons": sum("lag2" in cycle["comparisons"] for cycle in cycles),
        "detector_snapshot": detector.snapshot(),
        "cycle_evidence": cycles,
        "bindings": {"historical_manifest_sha256": _sha(manifest_bytes),
                     "historical_run_result_sha256": focal["durable_artifacts"]["result_file_sha256"],
                     "historical_runner_sha256": old_source,
                     "current_periodicity_module_sha256_normalized_lf": hashlib.sha256(
                         (ROOT / "motorsim/reference_harness/convergence.py").read_bytes().replace(bytes([13, 10]), bytes([10]))).hexdigest(),
                     "primary_contract": CYCLE_PRIMARY_CONTRACT},
        "interpretation": "The detector executed and the persisted cycle comparisons replay exactly. No period was accepted within the four completed cycles. The registered eight-cycle horizon was not reached, so this is not a claim of non-periodicity at the full horizon. Historical NOT_EVALUATED output is left unchanged.",
        "limitations": ["This read-only replay recomputes detector outcomes from stored observables; it does not rerun the physical solver or recompute primary audits.",
                        "Independent cycle audits are referenced from the original receipt and retain recomputed=true.",
                        "The historical checkpoint's producer binding predates Recovery V2 and is not authorized for resume."],
    }
    output_root = Path(sys.argv[1]).expanduser().resolve()
    if repository_root_containing(output_root) is not None:
        raise RuntimeError("FAIL_CLOSED: output directory resolves inside a repository")
    output_root.mkdir(parents=True, exist_ok=False)
    output = output_root / "periodicity-replay.json"
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PASS", "report": str(output),
                      "report_sha256": _sha(output.read_bytes()),
                      "cycles": len(cycles), "lag1": report["lag1_comparisons"],
                      "lag2": report["lag2_comparisons"],
                      "classification": report["classification"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
