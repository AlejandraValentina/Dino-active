"""Reproducible mesh-study setup and comparison receipts (no acceptance gates)."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import math
from typing import Any

from .engine_configuration import canonical_json, implementation_source_hashes, sha256
from .exhaust_mesh_v2 import refine_exhaust_configuration

SCHEMA = "DINO_MESH_STUDY_V1"
RESOLUTIONS = (1, 2, 4, 8)


def _digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _extensive_state(native: dict, gamma: float) -> dict:
    exhaust = next(row for row in native["ducts"] if row["id"] == "exhaust")
    mesh = exhaust["mesh"]
    states = native["initial_duct_states"]["exhaust"]
    species = native["duct_species"]["exhaust"]
    volumes = mesh["volumes"]
    if not (len(states) == len(species) == len(volumes)):
        raise ValueError("exhaust state/species/mesh topology differs")
    mass = momentum = energy = 0.0
    species_totals = [0.0] * 4
    for row, species_row, volume in zip(states, species, volumes):
        rho, velocity, pressure = row[:3]
        mass += rho * volume
        momentum += rho * velocity * volume
        energy += (pressure / (gamma - 1.0) + 0.5 * rho * velocity * velocity) * volume
        for index, value in enumerate(species_row):
            species_totals[index] += value
    return {"mass_kg": mass, "momentum_kg_m_s": momentum,
            "total_energy_J": energy, "species_inventory_by_index": species_totals}


def _flatten_scalars(value: Any, prefix: str = "") -> dict[str, float]:
    result: dict[str, float] = {}
    if isinstance(value, dict):
        for key, child in value.items():
            if key == "ducts":
                continue  # cell-local values are resolution-specific; retain raw state separately.
            path = f"{prefix}.{key}" if prefix else key
            result.update(_flatten_scalars(child, path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            result.update(_flatten_scalars(child, f"{prefix}[{index}]"))
    elif type(value) in (int, float) and math.isfinite(value):
        result[prefix] = float(value)
    return result


def build_refinement_matrix(document: dict,
                            resolutions: tuple[int, ...] = RESOLUTIONS) -> dict:
    """Create immutable candidate configs and verify same-profile geometry/remap.

    This is setup infrastructure only. It neither executes the solver nor sets
    spatial tolerances or declares independence.
    """
    if not isinstance(resolutions, tuple) or not resolutions or any(
            type(value) is not int or value not in RESOLUTIONS for value in resolutions):
        raise ValueError("resolutions must be a non-empty tuple drawn from 1/2/4/8")
    if len(set(resolutions)) != len(resolutions):
        raise ValueError("mesh resolution entries must be unique")
    native = document.get("native_configuration") if isinstance(document, dict) else None
    if not isinstance(native, dict):
        raise ValueError("mesh study requires an engine configuration")
    sections = native.get("geometry_identity", {}).get("chamber", {}).get("sections")
    if not isinstance(sections, list) or not sections:
        raise ValueError("mesh study requires named exhaust section geometry")
    gamma = native.get("eos", {}).get("gamma", 1.35)
    baseline_extensive = _extensive_state(native, gamma)
    geometry = [{key: row[key] for key in
                 ("name", "kind", "length_mm", "inlet_diameter_mm", "outlet_diameter_mm")}
                for row in sections]
    geometry_hash = _digest(geometry)
    candidates = []
    for cells_per_section in resolutions:
        refined = refine_exhaust_configuration(
            document, [cells_per_section] * len(sections),
            display_name=f"{document['display_name']} / mesh {cells_per_section}")
        refined_native = refined["native_configuration"]
        refined_extensive = _extensive_state(refined_native, gamma)
        mesh = next(row["mesh"] for row in refined_native["ducts"] if row["id"] == "exhaust")
        relative_errors = {}
        for key, before in baseline_extensive.items():
            after = refined_extensive[key]
            if isinstance(before, list):
                relative_errors[key] = [abs(a - b) / max(abs(a), abs(b), 1e-30)
                                        for a, b in zip(before, after)]
            else:
                relative_errors[key] = abs(after - before) / max(abs(before), abs(after), 1e-30)
        if sha256([{key: row[key] for key in
                    ("name", "kind", "length_mm", "inlet_diameter_mm", "outlet_diameter_mm")}
                   for row in refined_native["geometry_identity"]["chamber"]["sections"]]) != geometry_hash:
            raise ValueError("refinement changed named section geometry")
        candidates.append({
            "cells_per_section": cells_per_section,
            "total_exhaust_cells": len(mesh["volumes"]),
            "configuration_sha256": sha256(refined),
            "native_configuration_sha256": refined["native_configuration_sha256"],
            "discrete_geometry_sha256": refined_native["geometry_identity"][
                "exhaust_mesh_discretization"]["discrete_geometry_sha256"],
            "mesh_adapter_sha256": refined_native["geometry_identity"][
                "exhaust_mesh_discretization"]["adapter_sha256"],
            "geometry": {"sections": geometry,
                "total_length_m": mesh["faces"][-1] - mesh["faces"][0],
                "total_volume_m3": sum(mesh["volumes"]),
                "interface_areas_m2": list(mesh["areas"])},
            "conservative_remap": {"baseline": baseline_extensive,
                "refined": refined_extensive, "relative_error": relative_errors},
            "configuration": refined,
        })
    return {"schema": SCHEMA, "status": "SETUP_ONLY_NOT_EXECUTED",
            "source_configuration_sha256": sha256(document),
            "section_geometry_sha256": geometry_hash,
            "implementation_source_hashes": implementation_source_hashes(),
            "resolutions": candidates,
            "spatial_independence": "NOT_EVALUATED",
            "acceptance_thresholds": "NOT_REGISTERED",
            "solver_steps": 0}


def make_resolution_receipt(*, configuration_sha256: str,
                            cells_per_section: int,
                            primary: dict,
                            primary_sha256: str,
                            audit: dict,
                            provenance: dict) -> dict:
    """Compact per-resolution record retaining classification and audit scope."""
    if cells_per_section not in RESOLUTIONS:
        raise ValueError("unsupported resolution")
    if not isinstance(primary, dict) or not isinstance(audit, dict):
        raise ValueError("primary and independent audit objects are required")
    if audit.get("recomputed") is not True or audit.get("status") != "PASS":
        raise ValueError("mesh receipt requires a passing recomputed independent audit")
    if primary.get("admissible") is not True:
        raise ValueError("mesh receipt cannot accept an inadmissible primary")
    trajectory = primary.get("trajectory", [])
    dt_values = [row["dt_s"] for row in trajectory
                 if isinstance(row, dict) and type(row.get("dt_s")) in (int, float)
                 and math.isfinite(row["dt_s"]) and row["dt_s"] > 0]
    return {"schema": "DINO_MESH_RESOLUTION_RECEIPT_V1",
            "configuration_sha256": configuration_sha256,
            "cells_per_section": cells_per_section,
            "cycle_index": primary.get("cycle_index"),
            "primary_sha256": primary_sha256,
            "audit": {"status": audit["status"], "recomputed": audit["recomputed"]},
            "periodicity": primary.get("periodicity", {}).get("status", "NOT_EVALUATED"),
            "classification": "AUDITED_CYCLE_NOT_A_STEADY_PERFORMANCE_CLAIM",
            "observables": deepcopy(primary.get("observables", {})),
            "conservation": deepcopy(primary.get("conservation", {})),
            "native_mesh_state": deepcopy(primary.get("terminal_state", {}).get("ducts", {})),
            "time_step_evidence": {"accepted_step_count": len(dt_values),
                "minimum_dt_s": min(dt_values) if dt_values else None,
                "maximum_dt_s": max(dt_values) if dt_values else None,
                "rejected_trial_count": len(primary.get("rejected_trials", [])),
                "per_step_detail_reference": "primary_sha256#/trajectory (native angles, dt, CFL and rejected-step data)"},
            "provenance": deepcopy(provenance),
            "scientific_validation": "NOT_CLAIMED"}


def extract_primary_phase_series(primary: dict, channel: str) -> dict:
    """Extract native accepted-step-start signals from an audited cycle primary.

    No interpolation, smoothing, or endpoint extrapolation is performed. Flow
    channels use the saved first-stage flux at the exact accepted step-start
    state; pressure channels use the saved q0 state and its bound geometry.
    """
    if not isinstance(primary, dict) or primary.get("admissible") is not True:
        raise ValueError("phase extraction requires an admissible cycle primary")
    trajectory = primary.get("trajectory")
    if not isinstance(trajectory, list) or not trajectory:
        raise ValueError("phase extraction requires a saved native trajectory")
    start_cycle, end_cycle = primary.get("cycle_start_deg"), primary.get("cycle_end_deg")
    if (type(start_cycle) not in (int, float) or type(end_cycle) not in (int, float) or
            end_cycle - start_cycle != 360.0 or
            trajectory[0].get("angle_start_deg") != start_cycle or
            trajectory[-1].get("angle_end_deg") != end_cycle):
        raise ValueError("phase extraction requires complete 360-degree native trajectory coverage")
    if not isinstance(channel, str) or not channel:
        raise ValueError("phase channel name is required")
    angles, values = [], []
    previous_end = None
    for row in trajectory:
        if not isinstance(row, dict):
            raise ValueError("native trajectory row is malformed")
        start, end = row.get("angle_start_deg"), row.get("angle_end_deg")
        if (type(start) not in (int, float) or type(end) not in (int, float) or
                not math.isfinite(start) or not math.isfinite(end) or end <= start or
                (previous_end is not None and start != previous_end)):
            raise ValueError("native trajectory angle coverage is invalid or discontinuous")
        states = row.get("stage_states")
        if not isinstance(states, (list, tuple)) or len(states) != 3:
            raise ValueError("native accepted-stage state evidence is incomplete")
        state = states[0]
        if channel in {"cylinder_pressure_pa", "crankcase_pressure_pa"}:
            chamber = channel.removesuffix("_pressure_pa")
            item = state.get("chambers", {}).get(chamber)
            gamma = primary.get("eos_gamma")
            if (not isinstance(item, (list, tuple)) or len(item) != 3 or
                    type(gamma) not in (int, float) or not math.isfinite(gamma) or gamma <= 1 or
                    type(item[1]) not in (int, float) or type(item[2]) not in (int, float) or
                    item[2] <= 0):
                raise ValueError("chamber state lacks usable energy/volume evidence")
            value = (gamma - 1.0) * item[1] / item[2]
            unit = "Pa"
            source = "saved q0 chamber total energy, volume and bound EOS gamma"
        elif channel.startswith("duct:"):
            fields = channel.split(":")
            if len(fields) != 5 or fields[4] != "pressure_pa":
                raise ValueError("duct pressure channel must be duct:<id>:cell:<index>:pressure_pa")
            duct_id, cell_index = fields[1], int(fields[3])
            cells = state.get("ducts", {}).get(duct_id)
            if not isinstance(cells, (list, tuple)) or not 0 <= cell_index < len(cells):
                raise ValueError("requested native duct cell is absent")
            cell = cells[cell_index]
            if not isinstance(cell, (list, tuple)) or len(cell) < 3:
                raise ValueError("native duct cell state is malformed")
            value, unit = cell[2], "Pa"
            source = f"saved q0 native duct state {duct_id}[{cell_index}]"
        elif channel.startswith("flow:"):
            fields = channel.split(":")
            if len(fields) != 3 or fields[2] not in {"left", "right"}:
                raise ValueError("flow channel must be flow:<duct_id>:<left|right>")
            face_stages = row.get("stage_face_fluxes")
            if not isinstance(face_stages, (list, tuple)) or len(face_stages) != 2:
                raise ValueError("native stage-face flux evidence is incomplete")
            flux = face_stages[0].get(fields[1], {}).get(fields[2])
            if not isinstance(flux, (list, tuple)) or not flux:
                raise ValueError("requested native duct boundary flux is absent")
            value, unit = flux[0], "kg/s"
            source = f"saved q0 signed stage-face mass flux {fields[1]}.{fields[2]}"
        else:
            raise ValueError(f"unsupported native phase channel: {channel}")
        if type(value) not in (int, float) or not math.isfinite(value):
            raise ValueError("native phase channel contains a non-finite value")
        angles.append(float(start)); values.append(float(value))
        previous_end = end
    return {"schema": "DINO_MESH_NATIVE_PHASE_SERIES_V1",
            "channel": channel, "unit": unit,
            "angles_deg": angles, "values": values,
            "sample_semantics": "ACCEPTED_STEP_START_NATIVE_STATE",
            "source_definition": source,
            "interpolation": "NONE",
            "scientific_validation": "NOT_CLAIMED"}


def compare_resolution_receipts(left: dict, right: dict) -> dict:
    """Compute raw scalar deltas; no tolerance or acceptance is inferred."""
    if (left.get("schema") != "DINO_MESH_RESOLUTION_RECEIPT_V1" or
            right.get("schema") != "DINO_MESH_RESOLUTION_RECEIPT_V1"):
        raise ValueError("unsupported mesh resolution receipt schema")
    if left.get("configuration_sha256") == right.get("configuration_sha256"):
        raise ValueError("mesh configurations must have distinct identities")
    if left.get("provenance") != right.get("provenance"):
        raise ValueError("mesh resolution receipts do not share a frozen study provenance")
    a = _flatten_scalars(left.get("observables", {}))
    b = _flatten_scalars(right.get("observables", {}))
    values = {}
    for key in sorted(set(a) & set(b)):
        va, vb = a[key], b[key]
        values[key] = {"left": va, "right": vb, "absolute_delta": abs(va - vb),
            "relative_delta": abs(va - vb) / max(abs(va), abs(vb), 1e-30)}
    if not values:
        raise ValueError("no common scalar observables are available for comparison")
    return {"schema": "DINO_MESH_RESOLUTION_COMPARISON_V1",
            "left_configuration_sha256": left["configuration_sha256"],
            "right_configuration_sha256": right["configuration_sha256"],
            "left_resolution": left["cells_per_section"],
            "right_resolution": right["cells_per_section"],
            "common_scalar_observables": values,
            "native_mesh_signals_preserved": True,
            "interpolation": "NONE",
            "assessment": "DIFFERENCES_RECORDED_NO_REGISTERED_ACCEPTANCE_TOLERANCE",
            "spatial_independence": "NOT_EVALUATED"}


def compare_phase_series(left: dict, right: dict, common_angles_deg: list[float]) -> dict:
    """Optional linear interpolation for traced comparisons only; inputs retained."""
    def validate_series(series: dict) -> tuple[list[float], list[float]]:
        angles, values = series.get("angles_deg"), series.get("values")
        if (not isinstance(angles, list) or not isinstance(values, list) or
                len(angles) != len(values) or len(angles) < 2):
            raise ValueError("phase series requires equal angle/value arrays with at least two samples")
        if (any(type(value) not in (int, float) or not math.isfinite(value)
                for value in angles + values) or
                any(b <= a for a, b in zip(angles, angles[1:]))):
            raise ValueError("phase series must contain finite values and strictly increasing angles")
        return angles, values

    def interpolate(series: tuple[list[float], list[float]], angle: float) -> float:
        angles, values = series
        if not angles[0] <= angle <= angles[-1]:
            raise ValueError("comparison angle is outside native signal coverage")
        for i in range(1, len(angles)):
            if angle <= angles[i]:
                fraction = (angle - angles[i - 1]) / (angles[i] - angles[i - 1])
                return values[i - 1] + fraction * (values[i] - values[i - 1])
        return values[-1]

    if (not isinstance(common_angles_deg, list) or not common_angles_deg or
            any(type(value) not in (int, float) or not math.isfinite(value)
                for value in common_angles_deg) or
            any(b <= a for a, b in zip(common_angles_deg, common_angles_deg[1:]))):
        raise ValueError("explicit common comparison angles are required")
    a, b = validate_series(left), validate_series(right)
    differences = []
    for angle in common_angles_deg:
        if type(angle) not in (int, float) or not math.isfinite(angle):
            raise ValueError("common comparison angles must be finite")
        va, vb = interpolate(a, angle), interpolate(b, angle)
        differences.append({"angle_deg": angle, "left": va, "right": vb,
                            "absolute_delta": abs(va - vb)})
    return {"schema": "DINO_MESH_PHASE_COMPARISON_V1",
            "left_native_signal": deepcopy(left), "right_native_signal": deepcopy(right),
            "common_angles_deg": list(common_angles_deg),
            "comparison_operator": "PIECEWISE_LINEAR_OFFLINE_ONLY",
            "differences": differences,
            "assessment": "DIFFERENCES_RECORDED_NO_REGISTERED_ACCEPTANCE_TOLERANCE",
            "spatial_independence": "NOT_EVALUATED"}
