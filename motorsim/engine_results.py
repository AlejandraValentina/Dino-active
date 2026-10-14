"""Import and compare synthetic IMPL2 RPM result reports without filling gaps."""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
import re
from typing import Any

SCHEMA = "FULL_RPM_SWEEP_V1_IMPL2_AGGREGATE_REPORT_V1"
SERIES = {
    "power": ("brake_power", "kW"), "torque": ("brake_torque", "N*m"),
    "IMEP": ("IMEP", "kPa"), "FMEP": ("FMEP", "kPa"),
    "BMEP": ("BMEP", "kPa"), "ISFC": ("ISFC", "g/kWh"),
    "BSFC": ("BSFC", "g/kWh"),
}
_SHA = re.compile(r"^[0-9a-f]{64}$")


def import_report(path: str | Path, *, metadata_path: str | Path | None = None) -> dict[str, Any]:
    source = Path(path)
    if source.suffix.lower() == ".csv":
        if metadata_path is None:
            raise ValueError("CSV import requires its companion aggregate JSON to retain identities and hard gates")
        metadata = Path(metadata_path)
        if metadata.resolve() == source.resolve():
            raise ValueError("CSV metadata companion must be a separate aggregate JSON")
        data = json.loads(metadata.read_text(encoding="utf-8"))
        if Path(data.get("csv", "")).name != source.name:
            raise ValueError("CSV does not match the report's registered companion filename")
        expected_hash = data.get("csv_sha256")
        if expected_hash and hashlib.sha256(source.read_bytes()).hexdigest() != expected_hash:
            raise ValueError("CSV companion hash mismatch")
        with source.open("r", encoding="utf-8-sig", newline="") as handle:
            csv_rows = list(csv.DictReader(handle))
        indexed = {row.get("point_id"): row for row in csv_rows}
        if len(indexed) != len(csv_rows) or set(indexed) != {row.get("point_id") for row in data.get("points", [])}:
            raise ValueError("CSV point IDs do not match aggregate JSON")
        for row in data["points"]:
            csv_row = indexed[row["point_id"]]
            for key in ("variant_id", "classification", "result_sha256", "point_configuration_sha256"):
                if csv_row.get(key) != str(row.get(key, "")):
                    raise ValueError(f"CSV/JSON mismatch for {row['point_id']} field {key}")
            for metric, _unit in SERIES.values():
                status_key = metric + "_status"
                if csv_row.get(status_key) != row.get(status_key):
                    raise ValueError(f"CSV/JSON mismatch for {row['point_id']} field {status_key}")
                value_key = metric
                raw = csv_row.get(value_key, "")
                value = None if raw == "" else float(raw)
                expected = row.get(value_key)
                if value != expected:
                    raise ValueError(f"CSV/JSON mismatch for {row['point_id']} field {value_key}")
    else:
        data = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("schema") != SCHEMA:
        raise ValueError("unsupported IMPL2 report schema")
    required = ("implementation_identity_sha256", "preregistration_sha256", "producer_sha256")
    if any(not isinstance(data.get(key), str) or not _SHA.fullmatch(data[key]) for key in required):
        raise ValueError("report identity hashes are missing or invalid")
    if data.get("experimental_validation") != "NOT_PERFORMED":
        raise ValueError("report provenance must explicitly remain synthetic/nonexperimental")
    units = data.get("units")
    normalize = lambda value: "".join(ch for ch in value if ch.isascii() and ch.isalnum()).lower() if isinstance(value, str) else value
    if not isinstance(units, dict) or any(normalize(units.get(metric)) != normalize(unit) for metric, unit in SERIES.values()):
        raise ValueError("report units are missing or incompatible")
    rows = data.get("points")
    if not isinstance(rows, list) or not rows:
        raise ValueError("report points are missing")
    seen: set[str] = set()
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("report point must be an object")
        point_id = row.get("point_id")
        if not isinstance(point_id, str) or point_id in seen:
            raise ValueError("report point ids must be unique strings")
        seen.add(point_id)
        if type(row.get("rpm")) not in (int, float) or row["rpm"] <= 0:
            raise ValueError(f"{point_id}: invalid RPM")
        if row.get("classification") not in {"PERIOD_1", "NUMERICAL_INVALID", "INTERRUPTED_CHECKPOINTED", "NOT_STARTED"}:
            raise ValueError(f"{point_id}: unknown classification")
        for field in ("result_sha256", "point_configuration_sha256"):
            if not isinstance(row.get(field), str) or not _SHA.fullmatch(row[field]):
                raise ValueError(f"{point_id}: missing or invalid {field}")
        for metric, unit in SERIES.values():
            status = row.get(metric + "_status")
            value = row.get(metric)
            if status not in {"DEFINED", "UNDEFINED", "NOT_VALID_FOR_NONCONVERGED_POINT", "NOT_AVAILABLE"}:
                raise ValueError(f"{point_id}: missing/invalid {metric} status")
            if status == "DEFINED" and (type(value) not in (int, float) or not __import__('math').isfinite(value)):
                raise ValueError(f"{point_id}: {metric} marked DEFINED without finite value ({unit})")
    return {"schema": "MOTORSIM_IMPORTED_CURVE_DATASET_V1", "provenance": "SYNTHETIC",
            "experimental_validation": "NOT_PERFORMED", "identity": {k: data[k] for k in required},
            "units": dict(data["units"]), "points": rows,
            "campaign_status": data.get("campaign_status")}


def compare(datasets: dict[str, dict[str, Any]], metrics: tuple[str, ...] = tuple(SERIES)) -> dict[str, Any]:
    if not isinstance(datasets, dict) or len(datasets) < 2:
        raise ValueError("comparison requires at least two named datasets")
    out = {"schema": "MOTORSIM_CURVE_COMPARISON_V1", "provenance": "SYNTHETIC",
           "interpolation": "NONE", "datasets": {}, "metrics": {}}
    for name, dataset in datasets.items():
        if dataset.get("schema") != "MOTORSIM_IMPORTED_CURVE_DATASET_V1":
            raise ValueError(f"{name}: dataset must come from import_report")
        out["datasets"][name] = dataset["identity"]
    for metric in metrics:
        if metric not in SERIES:
            raise ValueError(f"unsupported curve metric {metric}")
        field, unit = SERIES[metric]
        rows_by_name = {name: {(r["variant_id"], r["rpm"]): r for r in ds["points"]}
                        for name, ds in datasets.items()}
        keys = sorted(set().union(*(set(rows) for rows in rows_by_name.values())), key=lambda x: (x[0], x[1]))
        curves = {}
        for name, rows in rows_by_name.items():
            values = []
            for variant, rpm in keys:
                row = rows.get((variant, rpm))
                status = "MISSING_POINT" if row is None else row.get(field + "_status", "MISSING_STATUS")
                value = row.get(field) if row is not None and status == "DEFINED" else None
                values.append({"variant_id": variant, "rpm": rpm, "value": value,
                               "status": status if row is None or status != "DEFINED" else row["classification"],
                               "classification": None if row is None else row["classification"],
                               "reason": None if row is None else row.get(field + "_reason"),
                               "periodicity": None if row is None else row.get("classification"),
                               "hard_gates": None if row is None else row.get("hard_gates")})
            curves[name] = values
        out["metrics"][metric] = {"unit": datasets[next(iter(datasets))]["units"].get(field, unit), "curves": curves}
    return out
