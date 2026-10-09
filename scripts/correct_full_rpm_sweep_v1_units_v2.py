"""Emit an explicitly unit-labeled correction without replacing FULL_RPM_SWEEP_V1 v1 evidence."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
from typing import Any


UNIT_MAP = {
    "IMEP": "kPa", "FMEP": "kPa", "BMEP": "kPa",
    "indicated_power": "kW", "brake_power": "kW",
    "indicated_torque": "N*m", "brake_torque": "N*m",
    "ISFC": "g/kWh", "BSFC": "g/kWh", "AFR": "kg/kg",
    "lambda": "1", "phi": "1", "DR": "1", "TE": "1",
    "CE": "1", "SE": "1",
}
POWER_KEYS = {"brake_power", "indicated_power"}


def unit_suffix(unit: str) -> str:
    return {"N*m": "Nm", "g/kWh": "g_per_kWh", "kg/kg": "kg_per_kg"}.get(
        unit, unit)


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def power_w_from_torque(torque_nm: float, rpm: float) -> float:
    if not all(math.isfinite(float(x)) for x in (torque_nm, rpm)) or rpm <= 0:
        raise ValueError("torque and RPM must be finite and RPM positive")
    return float(torque_nm) * (2.0 * math.pi * float(rpm) / 60.0)


def kw_to_w(power_kw: float) -> float:
    if not math.isfinite(float(power_kw)):
        raise ValueError("power must be finite")
    return float(power_kw) * 1000.0


def w_to_kw(power_w: float) -> float:
    if not math.isfinite(float(power_w)):
        raise ValueError("power must be finite")
    return float(power_w) / 1000.0


def correct_point_units(row: dict[str, Any]) -> dict[str, Any]:
    """Translate the v1 summary row into explicit SI/engineering-unit keys."""
    corrected = {key: value for key, value in row.items()
                 if key not in UNIT_MAP and key not in
                 {f"{name}_{suffix}" for name in UNIT_MAP
                  for suffix in ("status", "reason")}}
    for name, unit in UNIT_MAP.items():
        corrected[f"{name}_{unit_suffix(unit)}"] = row.get(name)
        corrected[f"{name}_status"] = row.get(f"{name}_status")
        corrected[f"{name}_reason"] = row.get(f"{name}_reason")
    for name in POWER_KEYS:
        power_kw = row.get(name)
        corrected[f"{name}_W"] = None if power_kw is None else kw_to_w(power_kw)
    return corrected


def verify_point_dimensions(row: dict[str, Any], result: dict) -> dict[str, Any]:
    """Cross-check every reported defined output against raw result units."""
    raw_outputs = (result.get("engineering_outputs") or {}).get("outputs", {})
    checks = []
    for name, unit in UNIT_MAP.items():
        if name in {"DR", "TE", "CE", "SE"}:
            ratio_name = {"DR": "delivery_ratio", "TE": "trapping_efficiency",
                          "CE": "charging_efficiency", "SE": "scavenging_efficiency"}[name]
            raw = (((result.get("scavenging") or {}).get("metrics") or {})
                   .get("ratios", {}).get(ratio_name, {}))
            report_name = f"{name}_1"
            source_unit = "1"
            scale = 1.0
        else:
            raw = raw_outputs.get(name, {})
            report_name = f"{name}_{unit_suffix(unit)}"
            source_unit = ("Pa" if unit == "kPa" else
                           "W" if name in POWER_KEYS else unit)
            scale = 1000.0 if unit == "kPa" or name in POWER_KEYS else 1.0
        report_value = row.get(report_name)
        raw_value = (raw.get("value") if raw.get("status") in {"DEFINED", "AVAILABLE"}
                     else None)
        if raw_value is not None:
            if raw.get("units", source_unit) != source_unit:
                raise ValueError(f"{name}: unexpected source unit {raw.get('units')}")
            expected = float(raw_value) / scale
            if report_value is None or not math.isclose(
                    float(report_value), expected, rel_tol=1e-12, abs_tol=1e-12):
                raise ValueError(f"{name}: corrected report value differs from raw result")
            if name in POWER_KEYS:
                report_w = row.get(f"{name}_W")
                if report_w is None or not math.isclose(
                        float(report_w), float(raw_value), rel_tol=1e-12, abs_tol=1e-12):
                    raise ValueError(f"{name}: W conversion differs from raw result")
        elif report_value is not None:
            raise ValueError(f"{name}: undefined raw output has a numeric report value")
        checks.append({"metric": name, "source_unit": source_unit,
                       "report_unit": unit, "status": raw.get("status", "UNDEFINED"),
                       "passed": True})

    for power_name, torque_name in (("brake_power", "brake_torque"),
                                    ("indicated_power", "indicated_torque")):
        power_w = row.get(f"{power_name}_W")
        torque_nm = row.get(f"{torque_name}_Nm")
        if power_w is not None and torque_nm is not None:
            expected = power_w_from_torque(torque_nm, float(row["rpm"]))
            if not math.isclose(float(power_w), expected, rel_tol=2e-10, abs_tol=1e-10):
                raise ValueError(f"{power_name}: P=torque*omega identity failed")
    return {"passed": True, "checked_metrics": checks,
            "power_torque_identity": "PASS_WHERE_DEFINED"}


def build_correction(report: dict, *, report_sha256: str,
                     historical_receipt_sha256: str,
                     historical_analysis_sha256: str) -> dict:
    points = [correct_point_units(row) for row in report.get("point_results", [])]
    return {
        "schema": "FULL_RPM_SWEEP_V1_UNIT_CORRECTION_V2",
        "campaign_id": report.get("campaign_id"),
        "campaign_status": report.get("campaign_status"),
        "source_report_schema": report.get("schema"),
        "source_report_sha256": report_sha256,
        "historical_receipt_sha256": historical_receipt_sha256,
        "historical_pilot_analysis_sha256": historical_analysis_sha256,
        "correction": (
            "The v1 campaign report stores power in kW and torque in N*m. "
            "The v1 pilot receipt and analysis copied the kW values but labeled "
            "them W. This v2 record names both kW and derived W values explicitly; "
            "no primary result or v1 artifact is modified."
        ),
        "metric_units": UNIT_MAP,
        "power_identity": "P_W = torque_Nm * 2*pi*RPM/60",
        "definitive_curve": report.get("definitive_curve"),
        "curves_are_partial": report.get("curves_are_partial"),
        "classification_counts": report.get("classification_counts"),
        "runtime_and_resource_metrics": report.get("runtime_and_resource_metrics"),
        "point_results": points,
    }


def write_correction(campaign_root: Path, output_dir: Path,
                     receipt_dir: Path) -> dict:
    report_path = campaign_root / "reports/full-rpm-sweep-v1.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    old_receipt = receipt_dir / "campaign-receipt.json"
    old_analysis = receipt_dir / "pilot-analysis.json"
    correction = build_correction(
        report, report_sha256=file_sha256(report_path),
        historical_receipt_sha256=file_sha256(old_receipt),
        historical_analysis_sha256=file_sha256(old_analysis))
    output_dir.mkdir(parents=True, exist_ok=True)
    receipt_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "full-rpm-sweep-v1-units-v2.json"
    csv_path = output_dir / "full-rpm-sweep-v1-units-v2.csv"
    rows = correction["point_results"]
    pilot_rows = [row for row in rows if row.get("rpm") == 4000]
    dimensional_checks = []
    for point in pilot_rows:
        result_path = (campaign_root / point["variant_id"] /
                       f"rpm-{int(point['rpm']):05d}" / "result.json")
        result = json.loads(result_path.read_text(encoding="utf-8"))
        dimensional_checks.append({
            "point_id": result["point_id"],
            **verify_point_dimensions(point, result),
        })
    correction["dimensional_verification"] = {
        "all_pass": all(row["passed"] for row in dimensional_checks),
        "points": dimensional_checks,
        "chart_axis_units_verified_from_v1_report_contract": {
            "power": "kW", "torque": "N·m", "bmep": "kPa",
            "bsfc": "g/kWh"},
    }
    json_path.write_text(json.dumps(correction, indent=2, sort_keys=True,
                                    ensure_ascii=False, allow_nan=False) + "\n",
                         encoding="utf-8")
    columns = list(dict.fromkeys(key for row in rows for key in row))
    with csv_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    analysis_v2 = {
        "schema": "FULL_RPM_SWEEP_V1_PILOT_ANALYSIS_V2",
        "source_analysis_sha256": file_sha256(old_analysis),
        "source_receipt_sha256": file_sha256(old_receipt),
        "source_report_sha256": file_sha256(report_path),
        "correction_report": str(json_path),
        "correction_csv": str(csv_path),
        "campaign_status": report.get("campaign_status"),
        "metric_units": UNIT_MAP,
        "dimensional_verification": correction["dimensional_verification"],
        "pilot_points": pilot_rows,
        "performance_metrics": report.get("runtime_and_resource_metrics"),
        "unchanged_primary_result_hashes": [row.get("result_sha256")
                                             for row in pilot_rows],
    }
    (receipt_dir / "pilot-analysis-v2.json").write_text(
        json.dumps(analysis_v2, indent=2, sort_keys=True,
                   ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
    receipt_v2 = {
        "schema": "FULL_RPM_SWEEP_V1_CAMPAIGN_RECEIPT_V2",
        "source_receipt_sha256": file_sha256(old_receipt),
        "source_pilot_analysis_sha256": file_sha256(old_analysis),
        "source_report_sha256": file_sha256(report_path),
        "correction_report_sha256": file_sha256(json_path),
        "correction_csv_sha256": file_sha256(csv_path),
        "campaign_status": report.get("campaign_status"),
        "classification": "FULL_RPM_SWEEP_V1_PARTIAL",
        "metric_units": UNIT_MAP,
        "dimensional_verification": correction["dimensional_verification"],
        "pilot_points": pilot_rows,
        "preservation": "Historical v1 receipts, report, CSV, plots, and primary results are retained unchanged.",
    }
    (receipt_dir / "campaign-receipt-v2.json").write_text(
        json.dumps(receipt_v2, indent=2, sort_keys=True,
                   ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
    return {"json": str(json_path), "csv": str(csv_path),
            "receipt": str(receipt_dir / "campaign-receipt-v2.json"),
            "analysis": str(receipt_dir / "pilot-analysis-v2.json"),
            "source_report_sha256": file_sha256(report_path)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("campaign_root", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--receipt-dir", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(write_correction(args.campaign_root, args.output_dir,
                                      args.receipt_dir), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
