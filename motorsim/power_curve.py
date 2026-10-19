"""Validated helpers for sparse, status-bearing engine power curves."""
from __future__ import annotations

import math

from .project_case import validate_rpm


POWER_UNITS_W = {"HP": 745.6998715822702, "kW": 1000.0, "CV": 735.49875}
INVALID_CLASSIFICATIONS = {
    "NUMERICAL_INVALID", "INTERRUPTED_CHECKPOINTED", "NOT_STARTED",
    "NO_CONVERGENCE_WITHIN_HORIZON", "AUDIT_FAIL", "FAIL_CLOSED",
}


def plan_rpm_range(start: int, stop: int, step: int, *, cycle: str = "2T") -> list[int]:
    """Return an exact inclusive integer grid; never adjust the requested endpoint."""
    if type(start) is not int or type(stop) is not int or type(step) is not int:
        raise ValueError("RPM inicial, final e incremento deben ser enteros.")
    validate_rpm(start, cycle)
    validate_rpm(stop, cycle)
    if stop <= start:
        raise ValueError("RPM final debe ser mayor que RPM inicial.")
    if step <= 0 or (stop - start) % step:
        raise ValueError("El incremento debe ser positivo y alcanzar exactamente el RPM final.")
    return list(range(start, stop + 1, step))


def convert_power_from_kw(value: float, unit: str) -> float:
    if unit not in POWER_UNITS_W:
        raise ValueError(f"Unidad de potencia no admitida: {unit}")
    return float(value) * 1000.0 / POWER_UNITS_W[unit]


def _defined_value(row: dict, metric: str):
    if row.get("classification") in INVALID_CLASSIFICATIONS:
        return None
    if row.get(f"{metric}_status") != "DEFINED":
        return None
    value = row.get(metric)
    if type(value) not in (int, float) or not math.isfinite(value):
        return None
    return float(value)


def build_curve_series(dataset: dict, selected_variants, *, power_unit: str = "HP") -> list[dict]:
    """Build gap-preserving series from importer-validated rows only."""
    if power_unit not in POWER_UNITS_W:
        raise ValueError(f"Unidad de potencia no admitida: {power_unit}")
    selected = set(selected_variants or ())
    grouped: dict[str, list[dict]] = {}
    source_identity = dataset.get("identity") if isinstance(dataset.get("identity"), dict) else {}
    for row in dataset.get("points", []):
        name = str(row.get("variant_id") or "Variante sin nombre")
        if selected and name not in selected:
            continue
        if type(row.get("rpm")) not in (int, float) or not math.isfinite(row["rpm"]):
            continue
        grouped.setdefault(name, []).append({**source_identity, **row})
    output = []
    for name, rows in sorted(grouped.items()):
        rows.sort(key=lambda row: (float(row["rpm"]), str(row.get("run_id", "")), row.get("cycle") or 0))
        points = []
        for row in rows:
            power_kw = _defined_value(row, "brake_power")
            torque = _defined_value(row, "brake_torque")
            points.append({
                "rpm": float(row["rpm"]),
                "power": None if power_kw is None else convert_power_from_kw(power_kw, power_unit),
                "power_status": row.get("brake_power_status", "NOT_REPORTED"),
                "power_reason": row.get("brake_power_reason"),
                "torque": torque,
                "torque_status": row.get("brake_torque_status", "NOT_REPORTED"),
                "torque_reason": row.get("brake_torque_reason"),
                "classification": row.get("classification"),
                "periodicity": row.get("periodicity"),
                "row": row,
            })
        output.append({"name": name, "points": points})
    return output


def peak_points(series: list[dict], metric: str) -> list[dict]:
    """Return the largest defined point per series, preserving negative maxima."""
    if metric not in {"power", "torque"}:
        raise ValueError("metric must be power or torque")
    peaks = []
    for curve in series:
        values = [point for point in curve.get("points", []) if point.get(metric) is not None]
        if values:
            peak = max(values, key=lambda point: point[metric])
            peaks.append({"series": curve["name"], "rpm": peak["rpm"], "value": peak[metric], "point": peak})
    return peaks


def exact_rpm_differences(series: list[dict]) -> list[dict]:
    """Compare the first two series only at RPM values present in both; no interpolation."""
    if len(series) < 2:
        return []
    left, right = series[0], series[1]
    left_by_rpm = {point["rpm"]: point for point in left["points"]}
    right_by_rpm = {point["rpm"]: point for point in right["points"]}
    common = sorted(left_by_rpm.keys() & right_by_rpm.keys())
    rows = []
    for rpm in common:
        a, b = left_by_rpm[rpm], right_by_rpm[rpm]
        compatible = True
        warnings = []
        identity_fields = ("implementation_identity_sha256", "solver_identity_sha256",
                           "producer_sha256", "preregistration_sha256")
        shared_identity = False
        for key in identity_fields:
            av, bv = a["row"].get(key), b["row"].get(key)
            if av is not None and bv is not None:
                shared_identity = shared_identity or av == bv
                if av != bv:
                    compatible = False
                    warnings.append(key)
        if not shared_identity:
            compatible = False
            warnings.append("shared implementation identity not reported")
        for key in ("fuel_id", "mechanical_loss_model_sha256", "periodicity_contract"):
            av, bv = a["row"].get(key), b["row"].get(key)
            if av is None or bv is None:
                compatible = False
                warnings.append(f"{key} unknown")
            elif av != bv:
                compatible = False
                warnings.append(key)
        mesh_fields = ("total_finite_volume_cells", "mesh_resolution")
        mesh_known = False
        for key in mesh_fields:
            av, bv = a["row"].get(key), b["row"].get(key)
            if av is not None and bv is not None:
                mesh_known = True
                if av != bv:
                    compatible = False
                    warnings.append(key)
        if not mesh_known:
            compatible = False
            warnings.append("mesh identity unknown")
        row = {"rpm": rpm, "compatible": compatible, "warnings": warnings,
               "power_delta": None, "torque_delta": None,
               "power_status": "INCOMPATIBLE" if not compatible else "UNDEFINED",
               "torque_status": "INCOMPATIBLE" if not compatible else "UNDEFINED"}
        if compatible:
            if a["power"] is not None and b["power"] is not None:
                row["power_delta"] = b["power"] - a["power"]
                row["power_status"] = "DEFINED"
            if a["torque"] is not None and b["torque"] is not None:
                row["torque_delta"] = b["torque"] - a["torque"]
                row["torque_status"] = "DEFINED"
        rows.append(row)
    return rows
