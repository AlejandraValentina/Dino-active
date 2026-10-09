"""Preregistered no-solver readiness preflight for FULL_RPM_SWEEP_V1."""
from __future__ import annotations

import copy
import hashlib
import json
import math
from pathlib import Path
from typing import Any

from .fuel_combustion import SyntheticFuelSurrogateV1
from .integrated_2t import IntegratedEngine2T, _solver_dependency_hashes
from .mechanical_loss_binding_v1 import (
    MechanicalLossBindingError,
    canonical_sha256,
    resolve_mechanical_loss_v1,
)
from .reference_harness.convergence import CONTRACT_V2, STREAK, THRESHOLDS


SCHEMA = "FULL_RPM_SWEEP_V1_PREREGISTRATION"
PREREGISTRATION = Path("results/full-rpm-sweep-v1/preregistration.json")


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"INVALID_SWEEP_PREREGISTRATION: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError("INVALID_SWEEP_PREREGISTRATION: expected a JSON object")
    return value


def rpm_points(preregistration: dict[str, Any]) -> tuple[int, ...]:
    grid = preregistration.get("rpm_grid")
    if not isinstance(grid, dict):
        raise ValueError("INVALID_SWEEP_RPM_DOMAIN: rpm_grid is missing")
    start, stop, step = (grid.get("start_rpm"), grid.get("stop_rpm"),
                         grid.get("increment_rpm"))
    if any(type(value) is not int for value in (start, stop, step)):
        raise ValueError("INVALID_SWEEP_RPM_DOMAIN: range values must be integers")
    if start <= 0 or stop < start or step <= 0:
        raise ValueError("INVALID_SWEEP_RPM_DOMAIN: invalid range or increment")
    points = list(range(start, stop + 1, step))
    if points[-1] != stop:
        if grid.get("include_stop_endpoint") is not True:
            raise ValueError("INVALID_SWEEP_RPM_DOMAIN: stop endpoint is not included")
        points.append(stop)
    if grid.get("points_rpm") != points or len(points) != len(set(points)):
        raise ValueError("INVALID_SWEEP_RPM_DOMAIN: explicit point list differs from range contract")
    return tuple(points)


def _expected_source_hashes(root: Path) -> tuple[dict[str, str], str, str]:
    solver = _solver_dependency_hashes()
    convergence_path = root / "motorsim/reference_harness/convergence.py"
    convergence_hash = hashlib.sha256(
        convergence_path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()
    threshold_hash = canonical_sha256(THRESHOLDS)
    return solver, convergence_hash, threshold_hash


def preflight_full_rpm_sweep_v1(
    preregistration_path: str | Path | None = None,
    *,
    repository_root: str | Path | None = None,
) -> dict[str, Any]:
    """Validate all preregistered RPM points without advancing the solver."""
    root = (Path(repository_root).resolve() if repository_root is not None
            else Path(__file__).resolve().parents[1])
    prereg_path = (Path(preregistration_path).resolve() if preregistration_path
                   else root / PREREGISTRATION)
    report: dict[str, Any] = {
        "schema": "FULL_RPM_SWEEP_V1_PREFLIGHT_REPORT",
        "campaigns_started": 0,
        "solver_steps_started": 0,
        "variants": [],
        "errors": [],
    }
    try:
        prereg = _read_json(prereg_path)
        if prereg.get("schema") != SCHEMA or prereg.get("version") != "1.0.0":
            raise ValueError("UNSUPPORTED_SWEEP_PREREGISTRATION_SCHEMA")
        if prereg.get("campaigns_started") != 0:
            raise ValueError("SWEEP_CAMPAIGN_ALREADY_STARTED")
        points = rpm_points(prereg)
        if prereg.get("horizon", {}).get("max_complete_cycles_per_point") != 111:
            raise ValueError("SWEEP_HORIZON_CONTRACT_MISMATCH")
        periodicity = prereg.get("periodicity", {})
        if (periodicity.get("contract") != CONTRACT_V2 or
                periodicity.get("streak") != STREAK or
                periodicity.get("thresholds") != THRESHOLDS or
                periodicity.get("thresholds_sha256") != canonical_sha256(THRESHOLDS)):
            raise ValueError("SWEEP_PERIODICITY_CONTRACT_MISMATCH")
        current_solver, current_detector, current_thresholds = _expected_source_hashes(root)
        if prereg.get("solver_dependency_hashes") != current_solver:
            raise ValueError("SWEEP_SOLVER_HASH_MISMATCH")
        if prereg.get("periodicity_source_sha256") != current_detector:
            raise ValueError("SWEEP_DETECTOR_HASH_MISMATCH")
        if prereg.get("periodicity", {}).get("thresholds_sha256") != current_thresholds:
            raise ValueError("SWEEP_THRESHOLDS_HASH_MISMATCH")

        variants = prereg.get("variants")
        if not isinstance(variants, list) or len(variants) != 2:
            raise ValueError("SWEEP_VARIANTS_INVALID: expected the two preregistered configurations")
        operation = prereg.get("operation", {})
        if (operation.get("mode") != "WOT" or operation.get("throttle_fraction") != 1.0 or
                operation.get("powervalve") != "existing RPM map retained unchanged"):
            raise ValueError("SWEEP_WOT_CONTRACT_INVALID")
        if prereg.get("budget", {}).get("wall_clock_seconds_per_invocation") != 3600:
            raise ValueError("SWEEP_BUDGET_CONTRACT_INVALID")

        for variant in variants:
            variant_id = variant.get("variant_id")
            row: dict[str, Any] = {
                "variant_id": variant_id,
                "fixture_sha256": variant.get("fixture_sha256"),
                "engine_configuration_sha256": variant.get("engine_configuration_sha256"),
                "rpm_points": [],
                "checks": {},
                "errors": [],
            }
            report["variants"].append(row)
            try:
                binding = resolve_mechanical_loss_v1(
                    preregistration_path=prereg_path,
                    variant_id=variant_id,
                    repository_root=root,
                    rpm_points=points,
                    load=operation["throttle_fraction"],
                )
                fixture_path = root / variant["source_fixture_path"]
                fixture = _read_json(fixture_path)
                base_config = fixture["engine_configuration"]
                mixture = base_config.get("atmosphere_species")
                if (not isinstance(mixture, list) or len(mixture) != 4 or
                        any(type(value) not in (int, float) or not math.isfinite(value)
                            or value < 0.0 for value in mixture) or
                        not math.isclose(math.fsum(mixture), 1.0,
                                         rel_tol=0.0, abs_tol=1e-12) or
                        mixture[1] <= 0.0):
                    raise ValueError("SWEEP_FUEL_MIXTURE_INVALID")
                mixture_contract = variant.get("mixture_input", {})
                measured_ratio = mixture[0] / mixture[1]
                if (mixture_contract.get("source") !=
                        "engine_configuration.atmosphere_species" or
                        not math.isclose(measured_ratio,
                                         mixture_contract.get("air_to_fuel_pseudo_species_mass_ratio"),
                                         rel_tol=0.0, abs_tol=1e-12) or
                        mixture_contract.get("species_mass_fractions") != mixture):
                    raise ValueError("SWEEP_FUEL_MIXTURE_BINDING_MISMATCH")
                if (base_config.get("geometry_identity", {}).get(
                        "intake_donor_species") != mixture):
                    raise ValueError("SWEEP_INTAKE_MIXTURE_BASIS_MISMATCH")
                fuel_config = base_config.get("fuel_coupled_combustion")
                fuel_snapshot = (fuel_config.get("fuel_snapshot")
                                 if isinstance(fuel_config, dict) else None)
                fuel = SyntheticFuelSurrogateV1.from_snapshot(fuel_snapshot)
                fuel_contract = variant.get("fuel", {})
                if (fuel.sha256 != fuel_contract.get("sha256") or
                        fuel_contract.get("provenance") != "SYNTHETIC_ASSUMPTION"):
                    raise ValueError("SWEEP_FUEL_SNAPSHOT_BINDING_MISMATCH")
                boundaries = base_config.get("boundaries", {})
                for name in ("inlet", "outlet"):
                    condition = boundaries.get(name)
                    if (not isinstance(condition, dict) or
                            condition.get("kind") != "open_end_plenum_v2" or
                            condition.get("state") is not None or
                            condition.get("p0") != 101325.0 or
                            condition.get("T0") != 300.0):
                        raise ValueError(f"SWEEP_WOT_BOUNDARY_INVALID:{name}")
                if (base_config.get("external_boundary_model") != "OPEN_END_PLENUM_V2" or
                        base_config.get("external_boundary_provenance") != "SYNTHETIC_ASSUMPTION"):
                    raise ValueError("SWEEP_WOT_BOUNDARY_MODEL_INVALID")
                valve = base_config.get("port_binding", {}).get("powervalve")
                if (not isinstance(valve, dict) or
                        valve.get("rpm") != variant.get("powervalve_rpm_domain") or
                        min(points) < min(valve.get("rpm", [])) or
                        max(points) > max(valve.get("rpm", []))):
                    raise ValueError("SWEEP_POWERVALVE_DOMAIN_INVALID")

                point_rows = []
                for rpm in points:
                    point_config = copy.deepcopy(base_config)
                    point_config["reference_rpm"] = float(rpm)
                    check_unchanged = copy.deepcopy(point_config)
                    check_unchanged["reference_rpm"] = base_config["reference_rpm"]
                    if check_unchanged != base_config:
                        raise ValueError("SWEEP_CONFIGURATION_MUTATION_OUTSIDE_RPM")
                    point_hash = canonical_sha256(point_config)
                    engine = IntegratedEngine2T.from_configuration_dict(point_config)
                    if (engine.reference_rpm != float(rpm) or engine.cycle != 0 or
                            engine.accepted_steps != 0 or engine.rejected_steps != 0):
                        raise ValueError("SWEEP_PREFLIGHT_ADVANCED_SOLVER")
                    if engine.port_binding is None or engine.slider_crank is None:
                        raise ValueError("SWEEP_GEOMETRY_OR_PORT_BINDING_MISSING")
                    if engine.thermal_system is None or engine.fuel_coupled_combustion is None:
                        raise ValueError("SWEEP_THERMAL_OR_COMBUSTION_CONFIGURATION_MISSING")
                    point_rows.append({"rpm": rpm,
                                       "point_configuration_sha256": point_hash,
                                       "loss_mep_pa": math.fsum(
                                           term.value(float(rpm), 1.0)
                                           for term in binding.model.terms),
                                       "solver_cycles_started": engine.cycle,
                                       "accepted_solver_steps": engine.accepted_steps,
                                       "rejected_solver_steps": engine.rejected_steps})

                row["mechanical_loss_provenance"] = binding.provenance
                row["fuel_sha256"] = fuel.sha256
                row["mixture_ratio_basis"] = mixture_contract["basis"]
                row["rpm_points"] = point_rows
                row["checks"] = {
                    "fixture_and_configuration_hashes": True,
                    "explicit_mechanical_loss_model": True,
                    "mechanical_model_compatible_all_rpms": True,
                    "fuel_snapshot_and_mixture_explicit": True,
                    "wot_boundaries_explicit": True,
                    "geometry_ports_chambers_thermal_combustion_valid": True,
                    "periodicity_and_solver_hashes_match": True,
                    "no_solver_steps": all(x["accepted_solver_steps"] == 0 and
                                            x["rejected_solver_steps"] == 0
                                            for x in point_rows),
                }
            except (MechanicalLossBindingError, KeyError, TypeError, ValueError,
                    OverflowError) as exc:
                row["errors"].append(str(exc))
        report["rpm_points_per_variant"] = len(points)
        report["points_preflighted"] = sum(len(v["rpm_points"]) for v in report["variants"])
    except (KeyError, TypeError, ValueError, OverflowError) as exc:
        report["errors"].append(str(exc))

    all_variants_pass = (len(report["variants"]) == 2 and all(
        not variant.get("errors") and variant.get("checks") and
        all(variant["checks"].values()) for variant in report["variants"]))
    report["preflight_status"] = "PASS" if all_variants_pass and not report["errors"] else "FAIL_CLOSED"
    report["readiness_claim"] = (
        "PRECONDITION_RESOLVED" if report["preflight_status"] == "PASS" else
        "EXPLICIT_MECHANICAL_LOSS_MODEL_REQUIRED")
    return report
