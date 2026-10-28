"""Fail-closed GCI calculation from three independently audited periodic cases."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path


EXPECTED_CELLS = (44, 88, 176)
METRICS = ("imep_bar", "modeled_brake_power_kw")


def _finite_positive(value, field):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
        raise ValueError(f"{field} must be finite and positive")
    return float(value)


def analyze(cases: list[dict]) -> dict:
    if len(cases) != 3:
        raise ValueError("exactly three periodic mesh cases are required")
    ordered = sorted(cases, key=lambda row: row.get("grid_total_cells", -1))
    if tuple(row.get("grid_total_cells") for row in ordered) != EXPECTED_CELLS:
        raise ValueError("grid must be exactly 44/88/176 total cells")
    identities = []
    for row in ordered:
        if row.get("periodic_detector_status") != "PASS_PERIOD_1":
            return _no_gci("periodicity not demonstrated on every grid", ordered)
        if row.get("primary_audit_status") != "PASS" or row.get("replay_exact") is not True:
            return _no_gci("period primary audit/replay is incomplete", ordered)
        residual = row.get("maximum_normalized_conservation_residual")
        if isinstance(residual, bool) or not isinstance(residual, (int, float)) or not math.isfinite(residual) or residual > 1e-12:
            return _no_gci("conservation gate failed", ordered)
        identity = row.get("physics_identity_sha256")
        if not isinstance(identity, str) or len(identity) != 64:
            raise ValueError("physics identity SHA-256 is required")
        identities.append(identity)
        for metric in METRICS:
            _finite_positive(row.get(metric), metric)
        if row.get("period_cycles") not in (1, 2):
            raise ValueError("period length must be one or two full engine cycles")
    if len(set(identities)) != 1:
        return _no_gci("physics identity differs across grids", ordered)
    period_ids = {row["period_cycles"] for row in ordered}
    if len(period_ids) != 1:
        return _no_gci("period lengths differ across grids", ordered)

    results = {}
    for metric in METRICS:
        values = [float(row[metric]) for row in ordered]
        d1, d2 = values[0] - values[1], values[1] - values[2]
        if d1 == 0 or d2 == 0 or d1 * d2 <= 0:
            return _no_gci(f"{metric} is not strictly monotone", ordered)
        order = math.log(abs(d1 / d2), 2.0)
        if not 0.5 <= order <= 2.5:
            return _no_gci(f"{metric} observed order outside [0.5, 2.5]", ordered)
        fine_gci_percent = 1.25 * abs(d2 / values[2]) / (2.0**order - 1.0) * 100.0
        results[metric] = {
            "values_coarse_to_fine": values,
            "observed_order": order,
            "fine_grid_gci_percent": fine_gci_percent,
            "criterion_percent": 2.0,
            "passes": fine_gci_percent <= 2.0,
        }
    return {
        "schema": "DINO_PERIODIC_MESH_GCI_ANALYSIS_V1",
        "classification": "PASS" if all(x["passes"] for x in results.values()) else "PARTIAL_GCI_ABOVE_2_PERCENT",
        "grid_total_cells": list(EXPECTED_CELLS),
        "physics_identity_sha256": identities[0],
        "period_cycles": next(iter(period_ids)),
        "metrics": results,
        "source_artifacts": [row["source_artifact"] for row in ordered],
        "predictive_claim": False,
        "candidate_promotion": False,
    }


def _no_gci(reason: str, cases: list[dict]) -> dict:
    return {
        "schema": "DINO_PERIODIC_MESH_GCI_ANALYSIS_V1",
        "classification": "PARTIAL_NO_GCI",
        "reason": reason,
        "grid_total_cells": [row.get("grid_total_cells") for row in cases],
        "metrics": {},
        "source_artifacts": [row.get("source_artifact") for row in cases],
        "predictive_claim": False,
        "candidate_promotion": False,
    }


def load_case(path: Path) -> dict:
    row = json.loads(path.read_text(encoding="utf-8"))
    row["source_artifact"] = {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    return row


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("cases", nargs=3, type=Path, metavar="CASE.json")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(f"preserve prior output: {args.output}")
    result = analyze([load_case(path) for path in args.cases])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"classification": result["classification"], "output": str(args.output)}))


if __name__ == "__main__":
    main()
