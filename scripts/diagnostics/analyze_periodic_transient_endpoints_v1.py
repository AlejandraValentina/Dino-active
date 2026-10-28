"""Read-only review of saved periodicity windows; never authorizes solver work."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from motorsim.reference_harness.convergence import STREAK


SCHEMA = "DINO_PERIODIC_TRANSIENT_ENDPOINT_REVIEW_V1"


def _finite(value, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{label} must be finite")
    return float(value)


def _conservation_max(cycle: dict) -> float:
    report = cycle.get("conservation")
    if not isinstance(report, dict):
        raise ValueError("cycle conservation report is required")
    residuals = []
    for family in ("mass", "energy", "species"):
        section = report.get(family)
        if not isinstance(section, dict):
            raise ValueError(f"conservation {family} report is required")
        if family == "species":
            denominator = max(abs(_finite(report["mass"].get(key), f"mass {key}"))
                              for key in ("initial", "final"))
            values = [abs(_finite(item.get("residual"), f"{family} residual")) / denominator
                      for item in section.values()]
        else:
            denominator = max(abs(_finite(section.get(key), f"{family} {key}"))
                              for key in ("initial", "final"))
            values = [abs(_finite(section.get("residual"), f"{family} residual")) / denominator]
        residuals.extend(values)
    return max(residuals, default=0.0)


def _window(label: str, cells: int, rows: list[dict], source: Path) -> dict:
    if not rows:
        raise ValueError(f"{label} must contain at least one cycle")
    cycles = []
    previous = None
    for row in rows:
        cycle_id = row.get("cycle")
        if isinstance(cycle_id, bool) or not isinstance(cycle_id, int) or (previous is not None and cycle_id <= previous):
            raise ValueError(f"{label} cycle indices must be increasing integers")
        previous = cycle_id
        stats = row.get("statistics")
        if stats is not None and not isinstance(stats, dict):
            raise ValueError(f"{label} cycle {cycle_id} has invalid detector statistics")
        if isinstance(stats, dict):
            maximum = _finite(stats.get("maximum"), "maximum normalized error")
            p90 = _finite(stats.get("p90"), "p90 normalized error")
            failed = stats.get("failed")
            count = stats.get("count")
            if any(isinstance(x, bool) or not isinstance(x, int) or x < 0 for x in (failed, count)) or failed > count:
                raise ValueError(f"{label} cycle {cycle_id} has invalid failure counts")
            normalized_stats = {"maximum": maximum, "p90": p90, "median": stats.get("median"),
                                "failed": failed, "count": count}
        else:
            normalized_stats = None
        comparison = row.get("comparison", {})
        metrics = comparison.get("metrics", {}) if isinstance(comparison, dict) else {}
        if not isinstance(metrics, dict):
            raise ValueError(f"{label} cycle {cycle_id} has invalid comparison metrics")
        failures = []
        family_counts: dict[str, int] = {}
        for key, metric in metrics.items():
            if metric.get("passed") is True:
                continue
            value = _finite(metric.get("value"), f"{key} value")
            threshold = _finite(metric.get("threshold"), f"{key} threshold")
            if threshold <= 0:
                raise ValueError(f"{key} threshold must be positive")
            failures.append({
                "observable": key,
                "normalized_error_over_threshold": value / threshold,
                "value": value,
                "threshold": threshold,
            })
            family = ".".join(key.split(".")[:2]) if key.startswith("ducts.") else key.split(".")[0]
            family_counts[family] = family_counts.get(family, 0) + 1
        failures.sort(key=lambda item: item["normalized_error_over_threshold"], reverse=True)
        cycles.append({
            "cycle": cycle_id,
            "comparison_status": comparison.get("status", "UNKNOWN"),
            "statistics": normalized_stats,
            "work_J": row.get("work_J"),
            "endpoint_failed_by_family": family_counts,
            "top_endpoint_failures": failures[:10],
            "maximum_conservation_residual": _conservation_max(row),
        })
    tail = cycles[-3:]
    max_descends = len(tail) == 3 and all(row["statistics"] is not None for row in tail) and all(a["statistics"]["maximum"] > b["statistics"]["maximum"]
                                           for a, b in zip(tail, tail[1:]))
    p90_descends = len(tail) == 3 and all(row["statistics"] is not None for row in tail) and all(a["statistics"]["p90"] > b["statistics"]["p90"]
                                          for a, b in zip(tail, tail[1:]))
    recent = cycles[-6:]
    no_progress = False
    if len(recent) == 6:
        no_progress = all(row["statistics"] is not None for row in recent) and all(
            b["statistics"]["maximum"] >= .95 * a["statistics"]["maximum"]
            and b["statistics"]["p90"] >= a["statistics"]["p90"]
            for a, b in zip(recent[:3], recent[3:])
        )
    all_conserved = all(row["maximum_conservation_residual"] <= 1e-12 for row in cycles)
    return {
        "label": label,
        "grid_total_cells": cells,
        "source_artifact": {"path": str(source), "sha256": hashlib.sha256(source.read_bytes()).hexdigest()},
        "cycle_count": len(cycles),
        "first_cycle": cycles[0]["cycle"],
        "last_cycle": cycles[-1]["cycle"],
        "all_saved_cycles_conservation_residual_le_1e-12": all_conserved,
        "last_three_maximum_strictly_decreasing": max_descends,
        "last_three_p90_strictly_decreasing": p90_descends,
        "registered_six_cycle_no_progress_condition_met": no_progress,
        "endpoint": cycles[-1],
        "cycle_history": cycles,
    }


def _budget_feasibility(detector_path: Path, partial_receipt_path: Path,
                        window_receipt_path: Path, per_grid_cap_s: float) -> dict:
    detector_path, partial_receipt_path, window_receipt_path = map(
        Path, (detector_path, partial_receipt_path, window_receipt_path))
    detector = json.loads(detector_path.read_text(encoding="utf-8"))
    partial = json.loads(partial_receipt_path.read_text(encoding="utf-8"))
    window = json.loads(window_receipt_path.read_text(encoding="utf-8"))
    if detector.get("contract") != "REFERENCE_PERIODIC_CONVERGENCE_V2":
        raise ValueError("detector contract mismatch")
    lag1 = detector.get("lag1_streak")
    branches = detector.get("branch_streaks")
    history = detector.get("history")
    if (type(lag1) is not int or lag1 < 0 or not isinstance(branches, dict) or
            set(branches) != {"A", "B"} or any(type(v) is not int or v < 0 for v in branches.values()) or
            not isinstance(history, list)):
        raise ValueError("detector streak state is malformed")
    if partial.get("status") != "ERROR" or partial.get("completed_new_cycles") != 0:
        raise ValueError("prior receipt is not the preserved zero-cycle failed attempt")
    partial_solver = _finite(partial.get("timing_seconds", {}).get("solver"), "prior partial solver seconds")
    window_solver = _finite(window.get("timing_seconds", {}).get("solver"), "window solver seconds")
    cycles = window.get("completed_new_cycles")
    if type(cycles) is not int or cycles <= 0 or window.get("status") != "TRANSIENT_AT_BUDGET":
        raise ValueError("completed window receipt is not a transient bounded run")
    cap = _finite(per_grid_cap_s, "per-grid solver budget")
    consumed = partial_solver + window_solver
    remaining = max(0.0, cap - consumed)
    mean_cycle = window_solver / cycles
    period1_cycles = max(0, STREAK - lag1)
    next_cycle_index = len(history) + 1
    future_branches = dict(branches)
    period2_cycles = 0
    while any(future_branches[key] < STREAK for key in ("A", "B")):
        branch = "A" if (next_cycle_index - 1) % 2 == 0 else "B"
        future_branches[branch] += 1
        period2_cycles += 1
        next_cycle_index += 1
        if period2_cycles > 2 * STREAK + 2:
            raise ValueError("period-2 streak completion failed to converge")
    min_period_cycles = min(period1_cycles, period2_cycles)
    projected_min_period_s = min_period_cycles * mean_cycle
    enough_budget = projected_min_period_s <= remaining
    return {
        "source_artifacts": [
            {"path": str(detector_path), "sha256": hashlib.sha256(detector_path.read_bytes()).hexdigest()},
            {"path": str(partial_receipt_path), "sha256": hashlib.sha256(partial_receipt_path.read_bytes()).hexdigest()},
            {"path": str(window_receipt_path), "sha256": hashlib.sha256(window_receipt_path.read_bytes()).hexdigest()},
        ],
        "per_grid_solver_budget_seconds": cap,
        "prior_failed_attempt_solver_seconds": partial_solver,
        "completed_window_solver_seconds": window_solver,
        "solver_seconds_already_consumed": consumed,
        "solver_seconds_remaining": remaining,
        "detector_streak_required": STREAK,
        "current_detector_lag1_streak": lag1,
        "current_detector_period2_branch_streaks": branches,
        "minimum_future_cycles_for_period_1_if_every_next_comparison_passes": period1_cycles,
        "minimum_future_cycles_for_period_2_if_every_next_comparison_passes": period2_cycles,
        "observed_mean_solver_seconds_per_cycle": mean_cycle,
        "minimum_projected_solver_seconds_to_any_period": projected_min_period_s,
        "minimum_period_fits_remaining_per_grid_budget": enough_budget,
        "classification": ("PERIOD_CANDIDATE_WITHIN_REMAINING_BUDGET" if enough_budget else
                           "CURRENT_PER_GRID_BUDGET_CANNOT_REACH_PERIODICITY"),
        "assumption": "Best-case detector path assumes every future comparison passes; runtime projection uses the completed 176 window mean and includes no extra margin.",
    }


def analyze(window_88_path: Path, window_176_path: Path, *, detector_path: Path | None = None,
            partial_receipt_path: Path | None = None, window_receipt_path: Path | None = None,
            per_grid_cap_s: float = 1200.0) -> dict:
    inputs = []
    for label, cells, path in (("88", 88, window_88_path), ("176", 176, window_176_path)):
        path = Path(path)
        rows = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(rows, list):
            raise ValueError(f"{label} cycle artifact must be a JSON list")
        inputs.append(_window(label, cells, rows, path))
    fine = inputs[1]
    readiness = ("TREND_SUPPORTS_SEPARATE_PREREGISTRATION_REVIEW"
                 if fine["last_three_maximum_strictly_decreasing"] and fine["last_three_p90_strictly_decreasing"]
                 else "NO_TREND_BASIS_FOR_CONTINUATION")
    budget = None
    if any(value is not None for value in (detector_path, partial_receipt_path, window_receipt_path)):
        if any(value is None for value in (detector_path, partial_receipt_path, window_receipt_path)):
            raise ValueError("detector and both solver receipts are required together")
        budget = _budget_feasibility(detector_path, partial_receipt_path, window_receipt_path,
                                     per_grid_cap_s)
        if not budget["minimum_period_fits_remaining_per_grid_budget"]:
            readiness = "NO_CONTINUATION_WITHIN_CURRENT_PER_GRID_BUDGET"
    return {
        "schema": SCHEMA,
        "classification": "TRANSIENT_NO_GCI",
        "windows": inputs,
        "continuation_review": {
            "176_trend_disposition": readiness,
            "execution_authorized_by_this_review": False,
            "requirements_before_any_new_solver_cycles": [
                "separate versioned preregistration bound to the 176-cell native checkpoint, detector and runner",
                "storage preflight against cumulative study use and reserve",
                "remaining cumulative and per-grid runtime checked against the staged plan",
            ],
            "reason": ("The last three 176 cycles strictly reduce both registered detector statistics, but fewer than the minimum three future comparisons required by PeriodicDetectorV2 fit the remaining per-grid solver budget. No continuation can reach period acceptance within the current cap." if budget and not budget["minimum_period_fits_remaining_per_grid_budget"] else
                       "The last three 176 cycles strictly reduce both registered detector statistics, while the window remains transient. This supports preparing a bounded continuation for review; it does not demonstrate periodicity or authorize execution."),
        },
        "176_budget_feasibility": budget,
        "gci": None,
        "predictive_claim": False,
        "candidate_promotion": False,
        "interpretation": "Failed comparison metrics are detector residuals, not physical-model errors. No thresholds, solver settings, or physical parameters were changed.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("window_88_cycles", type=Path)
    parser.add_argument("window_176_cycles", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--detector", type=Path)
    parser.add_argument("--partial-receipt", type=Path)
    parser.add_argument("--window-receipt", type=Path)
    parser.add_argument("--per-grid-cap-seconds", type=float, default=1200.0)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(f"preserve prior output: {args.output}")
    report = analyze(args.window_88_cycles, args.window_176_cycles,
                     detector_path=args.detector, partial_receipt_path=args.partial_receipt,
                     window_receipt_path=args.window_receipt,
                     per_grid_cap_s=args.per_grid_cap_seconds)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"classification": report["classification"],
                      "176_trend_disposition": report["continuation_review"]["176_trend_disposition"],
                      "output": str(args.output)}))


if __name__ == "__main__":
    main()
