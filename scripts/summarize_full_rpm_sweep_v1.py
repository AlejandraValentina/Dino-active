"""Export auditable CSV/JSON and partial-safe plots from campaign artifacts."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
VALID_PERIODS = {"PERIOD_1", "PERIOD_2"}
SERIES = {
    "power": (("brake_power", "brake_power", "kW"),
              ("indicated_power", "indicated_power", "kW")),
    "torque": (("brake_torque", "brake_torque", "N·m"),
               ("indicated_torque", "indicated_torque", "N·m")),
    "bmep": (("BMEP", "BMEP", "kPa"),),
    "bsfc": (("BSFC", "BSFC", "g/kWh"),),
}


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _metric(outputs: dict, name: str, scale: float = 1.0) -> tuple[float | None, str, str | None]:
    item = outputs.get(name, {})
    status = item.get("status", "UNDEFINED")
    value = item.get("value") if status == "DEFINED" else None
    if type(value) not in (int, float):
        value = None
    elif scale != 1.0:
        value = float(value) / scale
    return value, status, item.get("reason")


def _point_row(root: Path, item: dict) -> dict[str, Any]:
    result_path = root / item["result_path"] if item.get("result_path") else None
    result = (json.loads(result_path.read_text(encoding="utf-8"))
              if result_path and result_path.is_file() else None)
    classification = (result or {}).get("classification", item.get("classification", "NOT_STARTED"))
    outputs = ((result or {}).get("engineering_outputs") or {}).get("outputs", {})
    valid = classification in VALID_PERIODS
    row: dict[str, Any] = {
        "variant_id": item["variant_id"], "rpm": item["rpm"],
        "classification": classification, "numerically_valid": valid,
        "cycles_completed": (result or {}).get("cycles_completed"),
        "converged_cycle": (result or {}).get("converged_cycle"),
        "result_sha256": _sha(result_path) if result_path and result_path.is_file() else None,
        "point_configuration_sha256": ((result or {}).get("bindings") or {}).get("point_configuration_sha256"),
        "hard_gates": (result or {}).get("hard_gates"),
        "conservation": (result or {}).get("conservation"),
        "scavenging": (result or {}).get("scavenging"),
        "performance_metrics": (result or {}).get("performance_metrics"),
        "warnings": (result or {}).get("warnings", []),
    }
    for name, divisor in (("IMEP", 1000.0), ("FMEP", 1000.0), ("BMEP", 1000.0),
                          ("brake_power", 1000.0), ("indicated_power", 1000.0),
                          ("brake_torque", 1.0), ("indicated_torque", 1.0),
                          ("ISFC", 1.0), ("BSFC", 1.0),
                          ("AFR", 1.0), ("lambda", 1.0), ("phi", 1.0)):
        value, status, reason = _metric(outputs, name, divisor)
        row[name] = value if valid else None
        row[f"{name}_status"] = status if valid else "NOT_VALID_FOR_NONCONVERGED_POINT"
        row[f"{name}_reason"] = reason if valid else classification
    scavenging = row.get("scavenging") or {}
    ratios = (scavenging.get("metrics") or {}).get("ratios", {})
    for output_name, ratio_name in (("DR", "delivery_ratio"),
                                    ("TE", "trapping_efficiency"),
                                    ("CE", "charging_efficiency"),
                                    ("SE", "scavenging_efficiency")):
        metric = ratios.get(ratio_name, {})
        row[output_name] = metric.get("value") if valid else None
        row[f"{output_name}_status"] = (
            metric.get("status", "UNDEFINED") if valid else
            "NOT_VALID_FOR_NONCONVERGED_POINT")
        row[f"{output_name}_reason"] = metric.get("reason") if valid else classification
    return row


def _plot(root: Path, rows: list[dict], outputs_dir: Path,
          *, definitive_by_chart: dict[str, bool]) -> list[str]:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    paths = []
    colors = {"A_PRIME_MESH_0": "#2563eb", "B_PRIME_MESH_0": "#dc2626"}
    status_colors = {"NO_CONVERGENCE_WITHIN_HORIZON": "#f59e0b",
                     "NUMERICAL_INVALID": "#991b1b", "PRIMARY_AUDIT_FAIL": "#7f1d1d",
                     "PHYSICAL_INVALID": "#b91c1c", "INTERRUPTED_CHECKPOINTED": "#d97706",
                     "NOT_STARTED": "#6b7280", "IN_PROGRESS": "#0891b2"}
    for chart, definitions in SERIES.items():
        fig, ax = plt.subplots(figsize=(9, 5.2), constrained_layout=True)
        for variant in ("A_PRIME_MESH_0", "B_PRIME_MESH_0"):
            variant_rows = sorted((row for row in rows if row["variant_id"] == variant),
                                  key=lambda row: row["rpm"])
            color = colors[variant]
            for metric, label, unit in definitions:
                scale = 1000.0 if metric in ("brake_power", "indicated_power") else 1.0
                xs = [row["rpm"] for row in variant_rows]
                ys = [row.get(metric) for row in variant_rows]
                style = "--" if metric.startswith("indicated") else "-"
                ax.plot(xs, ys, marker="o", linestyle=style, color=color,
                        label=f"{variant} {label}")
            invalid = [row for row in variant_rows if not row["numerically_valid"]]
            if invalid:
                bottom = ax.get_ylim()[0]
                groups = sorted({row["classification"] for row in invalid})
                for status in groups:
                    selected = [row for row in invalid if row["classification"] == status]
                    ax.scatter([row["rpm"] for row in selected], [bottom] * len(selected),
                               marker="x", color=status_colors.get(status, color),
                               label=f"{variant} {status}")
        axis_unit = definitions[0][2]
        partial_label = ("" if definitive_by_chart.get(chart) else
                         " — PARTIAL / NON-DEFINITIVE")
        ax.set_title(f"FULL_RPM_SWEEP_V1{partial_label} — {chart.upper()} (synthetic inputs)")
        ax.set_xlabel("RPM")
        ax.set_ylabel(axis_unit)
        ax.grid(True, alpha=0.25)
        ax.legend(fontsize=8)
        path = outputs_dir / f"{chart}-vs-rpm.png"
        fig.savefig(path, dpi=150)
        plt.close(fig)
        paths.append(str(path.relative_to(root)))
    return paths


def summarize_campaign(campaign_root: str | Path) -> dict:
    root = Path(campaign_root).resolve()
    manifest_path = root / "campaign.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    catalog = manifest.get("completed_or_checkpointed_points", [])
    rows = [_point_row(root, item) for item in catalog]
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["classification"]] = counts.get(row["classification"], 0) + 1
    all_gates_pass = all(
        (row.get("hard_gates") or {}).get("primary_admissible") is True and
        (row.get("hard_gates") or {}).get("primary_replay_audit") is True and
        (row.get("hard_gates") or {}).get("scavenging_partition", {}).get(
            "classification") == "PASS" and
        (row.get("hard_gates") or {}).get("conservation", {}).get("passed") is True
        for row in rows)
    chart_metrics = {
        "power": ("brake_power", "indicated_power"),
        "torque": ("brake_torque", "indicated_torque"),
        "bmep": ("BMEP",),
        "bsfc": ("BSFC",),
    }
    definitive_by_chart = {
        chart: (len(rows) == 30 and all(row["numerically_valid"] and
                                        all(row.get(metric) is not None for metric in metrics)
                                        for row in rows) and all_gates_pass)
        for chart, metrics in chart_metrics.items()
    }
    definitive = all(definitive_by_chart.values())
    output_dir = root / "reports"
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / "full-rpm-sweep-v1.csv"
    scalar_keys = ["variant_id", "rpm", "classification", "numerically_valid",
                   "cycles_completed", "converged_cycle", "result_sha256",
                   "point_configuration_sha256"]
    metrics = ["IMEP", "FMEP", "BMEP", "brake_power", "indicated_power",
               "brake_torque", "indicated_torque", "ISFC", "BSFC", "AFR", "lambda", "phi",
               "DR", "TE", "CE", "SE"]
    columns = scalar_keys + [field for metric in metrics for field in
                             (metric, f"{metric}_status", f"{metric}_reason")]
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    plots = _plot(root, rows, output_dir, definitive_by_chart=definitive_by_chart)
    report = {
        "schema": "FULL_RPM_SWEEP_V1_CAMPAIGN_REPORT",
        "campaign_id": manifest.get("campaign_id"),
        "campaign_status": manifest.get("campaign_status"),
        "campaigns_started": manifest.get("campaigns_started", 0),
        "registered_points": 30,
        "points_in_catalog": len(rows),
        "classification_counts": counts,
        "definitive_curve": definitive,
        "definitive_curve_by_chart": definitive_by_chart,
        "curves_are_partial": not definitive,
        "runtime_and_resource_metrics": {
            "campaign_invocation_seconds": sum(
                float(item.get("duration_seconds", 0))
                for item in manifest.get("invocations", [])),
            "measured_cycles": sum(
                int((row.get("performance_metrics") or {}).get("measured_cycles", 0))
                for row in rows),
            "mean_seconds_per_cycle": _weighted_cycle_mean(rows),
            "accepted_solver_steps": sum(
                int((row.get("performance_metrics") or {}).get("accepted_steps", 0))
                for row in rows),
            "rejected_solver_steps": sum(
                int((row.get("performance_metrics") or {}).get("rejected_steps", 0))
                for row in rows),
            "primary_compressed_bytes": sum(
                int((row.get("performance_metrics") or {}).get("primary_compressed_bytes", 0))
                for row in rows),
            "serialization_seconds": sum(
                float((row.get("performance_metrics") or {}).get("serialization_seconds", 0))
                for row in rows),
            "checkpoint_seconds": sum(
                float((row.get("performance_metrics") or {}).get("checkpoint_seconds", 0))
                for row in rows),
            "max_observed_process_rss_bytes": max((
                int((row.get("performance_metrics") or {}).get(
                    "max_observed_process_rss_bytes", 0) or 0) for row in rows),
                default=None),
        },
        "provenance": "SYNTHETIC_ASSUMPTION_CONDITIONAL_ON_P4; no experimental validation",
        "point_results": rows,
        "csv": str(csv_path.relative_to(root)),
        "plots": plots,
        "manifest_sha256": _sha(manifest_path),
    }
    report_path = output_dir / "full-rpm-sweep-v1.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True,
                                      ensure_ascii=False, allow_nan=False) + "\n",
                           encoding="utf-8")
    report["json"] = str(report_path.relative_to(root))
    return report


def _weighted_cycle_mean(rows: list[dict]) -> float | None:
    cycles = total_time = 0.0
    for row in rows:
        metrics = row.get("performance_metrics") or {}
        count = int(metrics.get("measured_cycles", 0))
        if count > 0:
            cycles += count
            total_time += float(metrics.get("total_measured_cycle_seconds", 0))
    return total_time / cycles if cycles else None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("campaign_root", type=Path)
    args = parser.parse_args()
    print(json.dumps(summarize_campaign(args.campaign_root), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
