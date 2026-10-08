"""Offline P9 evidence auditor. Synthetic inputs can qualify only this pipeline."""

from __future__ import annotations

import csv
import gzip
import hashlib
import json
import math
import statistics
from pathlib import Path
from typing import Any

SCHEMA = "motorsim-p9-dataset-v1"
SYNTHETIC_LABEL = "SYNTHETIC_PIPELINE_QUALIFICATION_ONLY"
SYNTHETIC_FLAGS = {
    "dataset_kind": "SYNTHETIC",
    "experimental_dataset_required": True,
    "experimental_status": "NOT_EXPERIMENTAL",
    "decision_eligibility": "NOT_VALID_FOR_P9_DECISION",
    "must_not_produce_p9_pass": True,
}
_REQUIRED_P9A_GATES = (
    "periodic_state", "finite_state", "geometry", "admissibility", "species",
    "cfl", "mass_conservation", "energy_conservation", "species_conservation",
    "p7_nonvacuous", "p7_source_admissibility", "restart", "deterministic_replay",
)


class P9AuditError(ValueError):
    """Input evidence is malformed or internally inconsistent."""


def _finite(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise P9AuditError(f"{name} must be a numeric value, not {type(value).__name__}")
    result = float(value)
    if not math.isfinite(result):
        raise P9AuditError(f"{name} must be finite")
    return result


def _positive(value: Any, name: str) -> float:
    result = _finite(value, name)
    if result <= 0:
        raise P9AuditError(f"{name} must be positive")
    return result


def _csv_finite(value: str, name: str) -> float:
    try:
        return _finite(float(value), name)
    except (TypeError, ValueError) as exc:
        raise P9AuditError(f"CSV numeric field {name} is invalid") from exc


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise P9AuditError(f"cannot read JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise P9AuditError("manifest/primary evidence must be a JSON object")
    return value


def geometry_volumes_m3(geometry: dict[str, Any], angles_deg: list[float]) -> list[float]:
    """Compute slider-crank cylinder volume from the declared geometry."""
    bore = _positive(geometry.get("bore_mm"), "geometry.bore_mm") / 1000.0
    stroke = _positive(geometry.get("stroke_mm"), "geometry.stroke_mm") / 1000.0
    rod = _positive(geometry.get("rod_length_mm"), "geometry.rod_length_mm") / 1000.0
    cr = _finite(geometry.get("compression_ratio"), "geometry.compression_ratio")
    if cr <= 1:
        raise P9AuditError("geometry.compression_ratio must exceed one")
    r = stroke / 2
    if rod <= r:
        raise P9AuditError("geometry.rod_length_mm must exceed crank radius")
    area = math.pi * bore * bore / 4
    swept = area * stroke
    declared = _positive(geometry.get("displacement_cm3"), "geometry.displacement_cm3") / 1e6
    if not math.isclose(declared, swept, rel_tol=2e-6, abs_tol=1e-12):
        raise P9AuditError("declared displacement does not match bore and stroke")
    clearance = swept / (cr - 1)
    reference = geometry.get("reference_volumes_cm3")
    if reference is not None:
        if not isinstance(reference, dict):
            raise P9AuditError("geometry.reference_volumes_cm3 must be an object")
        expected_reference = {
            "tdc": clearance * 1e6,
            "bdc": (clearance + swept) * 1e6,
            "swept": swept * 1e6,
        }
        for name, expected in expected_reference.items():
            supplied = _positive(reference.get(name), f"geometry.reference_volumes_cm3.{name}")
            if not math.isclose(supplied, expected, rel_tol=2e-6, abs_tol=1e-10):
                raise P9AuditError(f"reference {name} volume does not match declared geometry")
    result = []
    for angle in angles_deg:
        theta = math.radians(_finite(angle, "angle_deg"))
        x = r * (1 - math.cos(theta)) + rod - math.sqrt(rod * rod - (r * math.sin(theta)) ** 2)
        result.append(clearance + area * x)
    return result


def integrate_indicated_work_j(pressure_pa: list[float], volume_m3: list[float]) -> float:
    if len(pressure_pa) != len(volume_m3) or len(pressure_pa) < 3:
        raise P9AuditError("pressure and volume traces must have equal length >= 3")
    p = [_positive(v, "pressure_pa") for v in pressure_pa]
    v = [_positive(v, "volume_m3") for v in volume_m3]
    return math.fsum(0.5 * (p0 + p1) * (v1 - v0)
                     for p0, p1, v0, v1 in zip(p, p[1:], v, v[1:]))


def indicated_power_2t_w(work_j: float, rpm: float, cylinders: int = 1) -> float:
    """Two-stroke indicated power: one power cycle per crank revolution."""
    work = _finite(work_j, "work_j")
    speed = _positive(rpm, "rpm")
    if type(cylinders) is not int or cylinders <= 0:
        raise P9AuditError("cylinders must be a positive integer")
    return work * speed * cylinders / 60.0


def _verify_raw(manifest: dict[str, Any], root: Path) -> dict[str, Path]:
    if manifest.get("schema") != SCHEMA:
        raise P9AuditError("unsupported dataset schema")
    files = manifest.get("raw_files")
    if not isinstance(files, list) or len(files) != 2:
        raise P9AuditError("manifest must bind separate experiment and simulation traces")
    verified = {}
    identities = set()
    for row in files:
        if not isinstance(row, dict):
            raise P9AuditError("raw file record must be an object")
        role = row.get("role")
        if role not in ("experiment_raw", "simulation_primary") or role in verified:
            raise P9AuditError("raw roles must uniquely bind experiment and primary simulation")
        rel = row.get("path")
        if not isinstance(rel, str) or Path(rel).is_absolute() or ".." in Path(rel).parts:
            raise P9AuditError("raw path must be a safe relative path")
        raw = (root / rel).resolve()
        try:
            raw.relative_to(root.resolve())
        except ValueError as exc:
            raise P9AuditError("raw path escapes dataset directory") from exc
        try:
            content = raw.read_bytes()
        except OSError as exc:
            raise P9AuditError(f"raw file unavailable: {exc}") from exc
        if type(row.get("size_bytes")) is not int or len(content) != row["size_bytes"]:
            raise P9AuditError("raw file size does not match manifest")
        digest = hashlib.sha256(content).hexdigest()
        if digest != row.get("sha256"):
            raise P9AuditError("raw file SHA-256 does not match manifest")
        if row.get("units") != {"rpm": "rev/min", "angle": "degCA", "pressure": "Pa",
                                "pressure_reference": "ABSOLUTE"}:
            raise P9AuditError("raw units must state RPM, degrees CA, and absolute pressure in Pa")
        identity = (str(raw), digest)
        if identity in identities:
            raise P9AuditError("experiment and simulation evidence must be separate raw files")
        identities.add(identity)
        verified[role] = raw
    if set(verified) != {"experiment_raw", "simulation_primary"}:
        raise P9AuditError("experiment and simulation raw files are both required")
    return verified


def _trace_groups(raw: Path) -> dict[tuple[int, str], dict[int, dict[int, float]]]:
    groups: dict[tuple[int, str], dict[int, dict[int, float]]] = {}
    try:
        opener = gzip.open if raw.suffix == ".gz" else open
        with opener(raw, "rt", encoding="utf-8", newline="") as stream:
            reader = csv.DictReader(stream)
            base_fields = ["rpm", "cycle", "angle_deg", "pressure_pa"]
            if reader.fieldnames not in (base_fields, ["rpm", "branch", "cycle", "angle_deg", "pressure_pa"]):
                raise P9AuditError("raw CSV header does not match schema")
            for record in reader:
                rpm_f = _csv_finite(record["rpm"], "rpm")
                cycle_f = _csv_finite(record["cycle"], "cycle")
                angle_f = _csv_finite(record["angle_deg"], "angle_deg")
                pressure = _positive(_csv_finite(record["pressure_pa"], "pressure_pa"), "pressure_pa")
                if not rpm_f.is_integer() or rpm_f <= 0:
                    raise P9AuditError("RPM must be a positive integer")
                if not cycle_f.is_integer() or cycle_f < 0:
                    raise P9AuditError("cycle index must be a nonnegative integer")
                if not angle_f.is_integer() or not 0 <= angle_f <= 360:
                    raise P9AuditError("angles must be integer degrees in [0, 360]")
                branch = record.get("branch") or "single"
                if branch not in {"single", "A", "B"}:
                    raise P9AuditError("simulation branch must be single, A, or B")
                trace = groups.setdefault((int(rpm_f), branch), {})
                angle = int(angle_f)
                if angle in trace.setdefault(int(cycle_f), {}):
                    raise P9AuditError("duplicate angle in cycle trace")
                trace[int(cycle_f)][angle] = pressure
    except (OSError, EOFError, UnicodeError) as exc:
        raise P9AuditError(f"cannot read raw CSV: {exc}") from exc
    return groups


def _series_work(groups, series: str, rpm: int, geometry: dict[str, Any],
                 expected_cycles: int, branch: str = "single"):
    traces = groups.get((rpm, branch))
    if not traces or len(traces) != expected_cycles:
        raise P9AuditError(f"{series} RPM {rpm}: cycle count mismatch")
    work_values = []
    mean_pressure = [0.0] * 361
    expected_angles = set(range(361))
    cycle_ids = sorted(traces)
    if cycle_ids != list(range(cycle_ids[0], cycle_ids[0] + expected_cycles)):
        raise P9AuditError(f"{series} RPM {rpm}: cycles are not a consecutive sequence")
    for cycle, samples in sorted(traces.items()):
        if set(samples) != expected_angles:
            raise P9AuditError(f"{series} RPM {rpm} cycle {cycle}: incomplete 360-degree trace")
        if samples[0] != samples[360]:
            raise P9AuditError(f"{series} RPM {rpm} cycle {cycle}: trace endpoints do not close")
        p = [samples[i] for i in range(361)]
        v = geometry_volumes_m3(geometry, [float(i) for i in range(361)])
        work_values.append(integrate_indicated_work_j(p, v))
        for i, value in enumerate(p):
            mean_pressure[i] += value / expected_cycles
    mean_volume = geometry_volumes_m3(geometry, [float(i) for i in range(361)])
    return {
        "work_j": statistics.fmean(work_values),
        "cycle_work_sd_j": statistics.stdev(work_values) if len(work_values) > 1 else 0.0,
        "cycle_count": len(work_values),
        "pressure_mean_pa": mean_pressure,
        "volume_m3": mean_volume,
    }


def _qualification_period(point: dict[str, Any], simulation_digest: str) -> int | None:
    qualification = point.get("p9a")
    if not isinstance(qualification, dict):
        return None
    cycles = qualification.get("cycles")
    gates = qualification.get("gates")
    period = qualification.get("period")
    if (type(cycles) is not int or not 1 <= cycles <= 400 or
            type(period) is not int or period not in (1, 2) or not isinstance(gates, dict)):
        return None
    if not all(gates.get(key) is True for key in _REQUIRED_P9A_GATES):
        return None
    if period == 1:
        return 1
    branches = qualification.get("branches")
    if not isinstance(branches, dict) or set(branches) != {"A", "B"}:
        return None
    for name in ("A", "B"):
        branch = branches[name]
        if (not isinstance(branch, dict) or branch.get("branch_id") != name or
                branch.get("simulation_sha256") != simulation_digest or
                branch.get("qualified") is not True):
            return None
    return 2


def _audit_uncertainty(value: Any, expected_cycles: int, synthetic: bool) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise P9AuditError("uncertainty metadata must be a JSON object")
    if synthetic and value.get("label") != SYNTHETIC_LABEL:
        raise P9AuditError("uncertainty metadata must identify its synthetic origin")
    if type(value.get("cycle_count")) is not int or value["cycle_count"] != expected_cycles:
        raise P9AuditError("uncertainty cycle_count does not match raw traces")
    if not synthetic and value.get("status") == "EXPERIMENTAL_UNCERTAINTY_UNKNOWN":
        return dict(value)
    pressure = _positive(value.get("pressure_standard_uncertainty_pa"), "uncertainty.pressure_standard_uncertainty_pa")
    angle = _positive(value.get("crank_angle_standard_uncertainty_deg"), "uncertainty.crank_angle_standard_uncertainty_deg")
    variation = _positive(value.get("cycle_variation_fraction"), "uncertainty.cycle_variation_fraction")
    normalized = dict(value)
    normalized.update({"pressure_standard_uncertainty_pa": pressure,
                       "crank_angle_standard_uncertainty_deg": angle,
                       "cycle_variation_fraction": variation,
                       "cycle_count": expected_cycles})
    if synthetic:
        normalized["label"] = SYNTHETIC_LABEL
    return normalized


def _shape_gate(results: list[dict[str, Any]]) -> tuple[bool, bool, int | float, int | float]:
    ordered = sorted(results, key=lambda row: row["rpm_exp"])
    powers = [row["power_exp_w"] for row in ordered]
    peak = max(powers)
    peak_indices = [index for index, value in enumerate(powers) if value == peak]
    if len(peak_indices) != 1 or peak_indices[0] == 0 or peak_indices[0] == len(ordered) - 1:
        sim_peak = max(results, key=lambda row: row["power_sim_w"])["rpm_sim"]
        exp_peak = ordered[peak_indices[0]]["rpm_exp"]
        return True, False, exp_peak, sim_peak
    index = peak_indices[0]
    exp_peak = ordered[index]["rpm_exp"]
    local_interval = max(exp_peak - ordered[index - 1]["rpm_exp"],
                         ordered[index + 1]["rpm_exp"] - exp_peak)
    sim_peak = max(results, key=lambda row: row["power_sim_w"])["rpm_sim"]
    return abs(sim_peak - exp_peak) <= local_interval, True, exp_peak, sim_peak


def audit_dataset(dataset_dir: str | Path, *, primary_simulation: dict[str, Any] | None = None,
                  requested_status: str | None = None) -> dict[str, Any]:
    """Recompute every value from raw p(theta); stored derived fields are ignored.

    The status returned for synthetic inputs is always a pipeline qualification
    class and can never equal P9_PASS, even when all performance gates pass.
    """
    root = Path(dataset_dir).resolve()
    manifest: dict[str, Any] = {}
    synthetic = False
    issues: list[str] = []
    try:
        manifest = _read_json(root / "manifest.json")
        synthetic = (manifest.get("dataset_kind") == "SYNTHETIC" or
                     manifest.get("synthetic_label") == SYNTHETIC_LABEL or
                     manifest.get("synthetic_flags") == SYNTHETIC_FLAGS)
        if requested_status == "P9_PASS" and synthetic:
            raise P9AuditError("synthetic dataset is ineligible for P9_PASS")
        if manifest.get("dataset_kind") not in {"SYNTHETIC", "EXPERIMENTAL"}:
            raise P9AuditError("dataset_kind must be explicitly SYNTHETIC or EXPERIMENTAL")
        raw = _verify_raw(manifest, root)
        geometry = manifest.get("geometry")
        if not isinstance(geometry, dict) or manifest.get("configuration_kind") != "FIXED_2T":
            raise P9AuditError("fixed 2T geometry/configuration is missing or not identified")
        if synthetic and (manifest.get("synthetic_label") != SYNTHETIC_LABEL or
                          manifest.get("synthetic_flags") != SYNTHETIC_FLAGS or
                          manifest.get("dataset_kind") != "SYNTHETIC" or
                          manifest.get("experimental_dataset_required") is not True):
            raise P9AuditError("synthetic classification markers are missing or inconsistent")
        if not synthetic and (manifest.get("dataset_kind") != "EXPERIMENTAL" or
                              manifest.get("experimental_dataset_required") is not True or
                              manifest.get("synthetic_label") is not None or
                              manifest.get("synthetic_flags") is not None):
            raise P9AuditError("P9 decision requires an explicitly eligible experimental dataset")
        provenance = manifest.get("provenance")
        if not isinstance(provenance, dict):
            raise P9AuditError("dataset provenance object is required")
        if synthetic and provenance.get("source_type") != "SYNTHETIC_ANALYTIC":
            raise P9AuditError("synthetic provenance must identify its analytical generator")
        if not synthetic and (provenance.get("source_type") != "EXPERIMENTAL_SOURCE" or
                              provenance.get("authorized") is not True):
            raise P9AuditError("experimental source provenance and authorization are required")
        if manifest.get("angle_convention") != {"cycle_deg": 360, "zero": "TDC", "direction": "forward"}:
            raise P9AuditError("angle convention must be an explicit forward 360-degree 2T cycle")
        points = manifest.get("operating_points")
        if not isinstance(points, list) or len(points) < 5:
            raise P9AuditError("at least five operating points are required")
        rpms = [_finite(row.get("rpm"), "operating_point.rpm") for row in points if isinstance(row, dict)]
        if len(rpms) != len(points) or len(set(rpms)) != len(rpms):
            raise P9AuditError("operating points must have unique RPM values")
        if any(value <= 0 or not value.is_integer() for value in rpms):
            raise P9AuditError("operating-point RPM values must be positive integers")
        cycles_per_point = manifest.get("cycles_per_point")
        if type(cycles_per_point) is not int or cycles_per_point <= 0:
            raise P9AuditError("cycles_per_point must be a positive integer")
        if manifest.get("uncertainty") is None:
            raise P9AuditError("uncertainty metadata is required")
        uncertainty = _audit_uncertainty(manifest["uncertainty"], cycles_per_point, synthetic)
        experimental_groups = _trace_groups(raw["experiment_raw"])
        simulation_groups = _trace_groups(raw["simulation_primary"])
        simulation_digest = next(row["sha256"] for row in manifest["raw_files"]
                                if row["role"] == "simulation_primary")
        if primary_simulation is not None:
            # An explicitly supplied object is only accepted if bound to raw-file provenance.
            raise P9AuditError("simulation evidence must be included in the hashed raw traces")
        results = []
        expected_rpm_set = {int(value) for value in rpms}
        if {rpm for rpm, _ in experimental_groups} != expected_rpm_set or any(
                branch != "single" for _, branch in experimental_groups):
            raise P9AuditError("experiment raw RPM set contains missing or unlisted operating points")
        periods = {}
        expected_simulation_keys = set()
        for point in points:
            point_rpm = int(point["rpm"])
            period = _qualification_period(point, simulation_digest)
            if period is None:
                raise P9AuditError(f"RPM {point_rpm}: incomplete P9-A primary qualification")
            periods[point_rpm] = period
            if period == 1:
                expected_simulation_keys.add((point_rpm, "single"))
            else:
                expected_simulation_keys.update({(point_rpm, "A"), (point_rpm, "B")})
        if set(simulation_groups) != expected_simulation_keys:
            raise P9AuditError("simulation raw RPM/branch set contains missing or unlisted outputs")
        for point in points:
            rpm = point["rpm"]
            rpm = int(rpm)
            expected_cycles = manifest["cycles_per_point"]
            exp = _series_work(experimental_groups, "experiment", rpm, geometry, expected_cycles)
            period = periods[rpm]
            if period == 1:
                sim = _series_work(simulation_groups, "simulation", rpm, geometry, expected_cycles)
                simulation_branch_work = {"single": sim["work_j"]}
            else:
                sim_a = _series_work(simulation_groups, "simulation", rpm, geometry,
                                     expected_cycles, "A")
                sim_b = _series_work(simulation_groups, "simulation", rpm, geometry,
                                     expected_cycles, "B")
                simulation_branch_work = {"A": sim_a["work_j"], "B": sim_b["work_j"]}
                sim = {"work_j": statistics.fmean((sim_a["work_j"], sim_b["work_j"])),
                       "cycle_work_sd_j": statistics.fmean((sim_a["cycle_work_sd_j"],
                                                             sim_b["cycle_work_sd_j"]))}
            sim_rpm = _finite(point.get("simulation_rpm"), "simulation_rpm")
            rpm_error = abs(sim_rpm - rpm) / rpm
            if rpm_error > 0.01:
                raise P9AuditError(f"RPM {rpm}: simulation mismatch exceeds 1%")
            w_exp, w_sim = exp["work_j"], sim["work_j"]
            if w_exp == 0.0:
                raise P9AuditError(f"RPM {rpm}: experimental indicated work is zero; relative error is undefined")
            relative = abs(w_sim - w_exp) / abs(w_exp)
            results.append({
                "rpm_exp": rpm, "rpm_sim": sim_rpm, "rpm_relative_mismatch": rpm_error,
                "work_exp_j": w_exp, "work_sim_j": w_sim,
                "period": period, "simulation_branch_work_j": simulation_branch_work,
                "power_exp_w": indicated_power_2t_w(w_exp, rpm, geometry.get("cylinders", 1)),
                "power_sim_w": indicated_power_2t_w(w_sim, sim_rpm, geometry.get("cylinders", 1)),
                "relative_error": relative, "sign_agrees": (w_exp > 0) == (w_sim > 0),
                "pressure_cycle_count": expected_cycles,
                "work_exp_cycle_sd_j": exp["cycle_work_sd_j"],
                "work_sim_cycle_sd_j": sim["cycle_work_sd_j"],
                "p9a_pass": True,
            })
        errors = [row["relative_error"] for row in results]
        mape = statistics.fmean(errors)
        within_10 = sum(error <= .10 for error in errors)
        all_15 = all(error <= .15 for error in errors)
        signs = all(row["sign_agrees"] for row in results)
        shape_pass, shape_applies, exp_max, sim_max = _shape_gate(results)
        metrics_pass = all_15 and within_10 / len(results) >= .8 and mape <= .10 and signs and shape_pass
        summary = {
            "point_count": len(results), "points_with_error_le_10_percent": within_10,
            "mape": mape, "all_points_le_15_percent": all_15,
            "signs_agree": signs, "experimental_peak_rpm": exp_max,
            "simulation_peak_rpm": sim_max, "shape_gate_applies": shape_applies,
            "shape_gate_pass": shape_pass, "performance_gates_pass": metrics_pass,
        }
        # The synthetic guard is deliberate and precedes every P9 classification.
        if synthetic:
            status = "P9_PIPELINE_QUALIFIED_WITH_SYNTHETIC_DATA" if metrics_pass else "PIPELINE_EXPECTED_FAIL"
        else:
            status = "P9_PASS" if metrics_pass else "P9_FAIL"
        if synthetic and status == "P9_PASS":
            raise AssertionError("anti-confusion invariant violated")
        return {
            "schema": "motorsim-p9-offline-audit-v1", "dataset_kind": manifest["dataset_kind"],
            "synthetic_label": manifest.get("synthetic_label"), "status": status,
            "experimental_validation": "NOT_PERFORMED" if synthetic else "PERFORMED",
            "predictive_validation": "NOT_CLAIMED", "raw_sha256": {
                row["role"]: row["sha256"] for row in manifest["raw_files"]},
            "geometry": geometry, "uncertainty": uncertainty, "operating_points": results,
            "summary": summary, "issues": [],
        }
    except (P9AuditError, KeyError, TypeError, ValueError, OverflowError) as exc:
        issues.append(str(exc))
        status = "PIPELINE_EXPECTED_INCONCLUSIVE" if synthetic else "P9_INCONCLUSIVE"
        return {
            "schema": "motorsim-p9-offline-audit-v1", "dataset_kind": manifest.get("dataset_kind"),
            "synthetic_label": manifest.get("synthetic_label"), "status": status,
            "experimental_validation": "NOT_PERFORMED",
            "predictive_validation": "NOT_CLAIMED", "operating_points": [],
            "summary": None, "issues": issues,
        }
