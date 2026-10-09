"""Classify rejected step attempts from hash-bound campaign primary evidence."""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any


def _canonical_sha(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"),
                         ensure_ascii=False, allow_nan=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _category(reason: str) -> str:
    if "CFL limit exceeded" in reason:
        return "CFL_LIMIT"
    if "inadmissible species mass" in reason:
        return "SPECIES_MASS_ADMISSIBILITY"
    if "rho/p/Y inadmissible" in reason:
        return "DENSITY_PRESSURE_SPECIES_ADMISSIBILITY"
    return "OTHER"


def analyze(campaign_root: Path) -> dict:
    manifest_path = campaign_root / "campaign.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    categories: Counter[str] = Counter()
    reasons: Counter[str] = Counter()
    variants: dict[str, Counter[str]] = {}
    cycles_checked = rejected_checked = 0
    errors = []
    for item in manifest["completed_or_checkpointed_points"]:
        if not item.get("result_path"):
            continue
        result_path = campaign_root / item["result_path"]
        result = json.loads(result_path.read_text(encoding="utf-8"))
        expected_primaries = result.get("cycle_primaries", [])
        variant_counter = variants.setdefault(item["variant_id"], Counter())
        if len(expected_primaries) != result.get("cycles_completed"):
            errors.append(f"CYCLE_PRIMARY_COUNT_MISMATCH:{item['point_id']}")
        for cycle, expected_sha in enumerate(expected_primaries, 1):
            point_dir = campaign_root / item["variant_id"] / f"rpm-{item['rpm']:05d}"
            primary_path = point_dir / f"cycle-{cycle:03d}.json.gz"
            metrics_path = point_dir / "cycle-metrics" / f"cycle-{cycle:03d}.json"
            primary = json.loads(gzip.decompress(primary_path.read_bytes()))
            if _canonical_sha(primary) != expected_sha:
                errors.append(f"PRIMARY_HASH_MISMATCH:{item['point_id']}:{cycle}")
                continue
            metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
            trial_rows = primary.get("rejected_trials", [])
            if len(trial_rows) != metrics.get("rejected_solver_steps"):
                errors.append(f"REJECTION_RECEIPT_COUNT_MISMATCH:{item['point_id']}:{cycle}")
            for trial in trial_rows:
                reason = str(trial.get("reason", ""))
                category = _category(reason)
                categories[category] += 1
                variant_counter[category] += 1
                reasons[reason] += 1
            cycles_checked += 1
            rejected_checked += len(trial_rows)
    expected_total = sum(int((row.get("performance_metrics") or {}).get(
        "rejected_steps", 0)) for row in manifest["completed_or_checkpointed_points"]
        if row.get("result_path"))
    if rejected_checked != expected_total:
        errors.append(f"TOTAL_REJECTED_COUNT_MISMATCH:{rejected_checked}!={expected_total}")
    return {
        "schema": "FULL_RPM_SWEEP_V1_REJECTION_FORENSICS_V1",
        "campaign_id": manifest.get("campaign_id"),
        "campaign_manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
        "cycles_checked": cycles_checked,
        "rejected_attempts_checked": rejected_checked,
        "expected_rejected_attempts": expected_total,
        "category_counts": dict(categories),
        "counts_by_variant": {key: dict(value) for key, value in variants.items()},
        "distinct_reason_counts": dict(reasons),
        "errors": errors,
        "all_pass": not errors,
        "evidence_basis": "Each per-cycle rejected_trials list is hash-bound inside the persisted primary and count-matched to the cycle performance receipt.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("campaign_root", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = analyze(args.campaign_root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True,
                                      ensure_ascii=False, allow_nan=False) + "\n",
                           encoding="utf-8")
    print(json.dumps({k: result[k] for k in (
        "schema", "cycles_checked", "rejected_attempts_checked",
        "category_counts", "errors", "all_pass")}, sort_keys=True))
    return 0 if result["all_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
