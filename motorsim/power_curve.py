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


def build_curve_series(dataset: dict, selected_variants, *, power_unit: str = "HP", include_exploratory: bool = False) -> list[dict]:
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
        requested=dataset.get('requested_rpms',[])
        present={row['rpm'] for row in rows}
        rows += [dict(variant_id=name,rpm=rpm,classification='NOT_STARTED',periodicity='NOT_EVALUATED',
                      brake_power_reason='NOT_STARTED',brake_torque_reason='NOT_STARTED')
                 for rpm in requested if rpm not in present]
        rows.sort(key=lambda row: (float(row["rpm"]), str(row.get("run_id", "")), row.get("cycle") or 0))
        points = []
        for row in rows:
            power_kw = _defined_value(row, "brake_power")
            torque = _defined_value(row, "brake_torque")
            exploratory=False
            if (include_exploratory and row.get('mode')=='ENGINEERING_EXPLORATORY' and
                    row.get('classification') in {'MAX_CYCLES_NONCONVERGED','TIME_LIMIT_NONCONVERGED','CANCELLED_CHECKPOINTED'}):
                estimates=row.get('transient_estimates',{})
                power_kw=estimates.get('brake_power');torque=estimates.get('brake_torque')
                power_kw=power_kw if type(power_kw) in (int,float) and math.isfinite(power_kw) else None
                torque=torque if type(torque) in (int,float) and math.isfinite(torque) else None
                exploratory=power_kw is not None or torque is not None
            points.append({
                "rpm": float(row["rpm"]),
                "power": None if power_kw is None else convert_power_from_kw(power_kw, power_unit),
                "exploratory":exploratory,
                "power_status": 'TRANSIENT_ESTIMATE' if exploratory else row.get("brake_power_status", "NOT_REPORTED"),
                "power_reason": row.get("brake_power_reason"),
                "torque": torque,
                "torque_status": 'TRANSIENT_ESTIMATE' if exploratory else row.get("brake_torque_status", "NOT_REPORTED"),
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
            if a.get('exploratory') or b.get('exploratory'):
                row['warnings'].append('TRANSITORIO: diferencia de estimaciones, no ganancia estacionaria')
                row['power_status']='TRANSIENT_ESTIMATE' if row['power_delta'] is not None else row['power_status']
                row['torque_status']='TRANSIENT_ESTIMATE' if row['torque_delta'] is not None else row['torque_status']
                row['exploratory']=True
        rows.append(row)
    return rows


def import_curve_runs(paths):
    """Existing verified importer plus read-only engineering display metadata.

    Raw metric statuses are retained. Stability ranges are observations, never
    replacements for the global detector or estimates of stationary error.
    """
    import json,hashlib
    from pathlib import Path
    from .engineering_workflow import import_desktop_runs
    data=import_desktop_runs(paths)
    for row in data.get('points',[]):
        if row.get('mode')!='ENGINEERING_EXPLORATORY':continue
        root=Path(row['artifact_directory']);raw=(root/'result.json').read_bytes()
        if hashlib.sha256(raw).hexdigest()!=row['result_sha256']:raise ValueError('curve result changed after import')
        result=json.loads(raw);check=result['preflight'];cycles=result['cycles'];last=cycles[-1]
        row.update(mechanical_loss_model_sha256=check['mechanical_loss_model_sha256'],
            periodicity_contract=check['periodicity_contract'],cycles_requested=check['max_cycles'],
            elapsed_seconds=result['elapsed_seconds'])
        metrics=(last.get('comparison') or {}).get('metrics',{})
        regions={}
        for name,prefix in [('cylinder','cylinder.'),('crankcase','crankcase.'),('exhaust','ducts.exhaust'),('global_species','global_species.')]:
            items=[v for k,v in metrics.items() if k.startswith(prefix)]
            regions[name]=dict(evaluated=len(items),failed=sum(not v['passed'] for v in items),
                worst_threshold_ratio=max((v['value']/v['threshold'] for v in items),default=None))
        window=cycles[-5:]
        work=[c['cylinder_work_J'] for c in window]
        air=[c['closure_snapshots']['exhaust']['cylinder_species_kg'][0]*1e6 for c in window]
        row['stability_observed']=dict(window_cycles=[c['cycle'] for c in window],
            work_range_J=max(work)-min(work),trapped_air_range_mg=max(air)-min(air),
            brake_power_range_kW=(max(c['mechanical_estimate']['brake_power_w'] for c in window)-min(c['mechanical_estimate']['brake_power_w'] for c in window))/1000 if all(c.get('mechanical_estimate') for c in window) else None,
            regions=regions,stationary_uncertainty='NOT_QUANTIFIED; last-cycle variation is not a stationary error bound')
    return data
