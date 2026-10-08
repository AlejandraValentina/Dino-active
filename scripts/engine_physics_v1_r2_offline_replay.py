"""Offline ENGINE_PHYSICS_V1_R2 replay from accepted primary cycles.

This script never advances the solver.  It consumes the four already accepted
periodic primaries and regenerates only derived engineering output using the
corrected gross-crossing/sc species-conservation semantics.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from motorsim.engine_physics_v1 import evaluate_integrated_cycle_v2, synthetic_gasoline_v1
from motorsim.artifact_store import ArtifactStoreError, resolve_external_artifact
from motorsim.scavenging_partition_v1 import evaluate_scavenging_partition_v1
from motorsim.engine_physics_v1_r2_semantics import (
    load_fixture_model, recompute_partition_conservation, scavenging_identity_check,
    output_hard_checks, metering_ratios,
)

TOL = 1e-12
POINTS = (
    ("A3000", "R2_A3000", "FIXTURE_A_PRIME", 3000, 73,
     "results/engine-physics-v1/recovery-campaign-data-v2/engine_a_3000/cycle-073.json.gz",
     "results/engine-physics-v1/recovery-campaign-data-v2/engine_a_3000/engineering-v2-073.json",
     "results/engine-physics-v1/recovery-runlogs-v2/engine-physics-v1-recovery-v2.summary.json"),
    ("A4000", "R2_A4000", "FIXTURE_A_PRIME", 4000, 88,
     "results/engine-physics-v1/recovery-campaign-data-v2/engine_a_4000/cycle-088.json.gz",
     "results/engine-physics-v1/recovery-campaign-data-v2/engine_a_4000/engineering-v2-088.json",
     "results/engine-physics-v1/recovery-runlogs-v2/engine-physics-v1-recovery-v2.summary.json"),
    ("B3000", "R2_B3000", "FIXTURE_B_PRIME", 3000, 34,
     "results/engine-physics-v1/recovery-campaign-data-v2/engine_b_3000/cycle-034.json.gz",
     "results/engine-physics-v1/recovery-campaign-data-v2/engine_b_3000/engineering-v2-034.json",
     "results/engine-physics-v1/recovery-runlogs-v2/engine-physics-v1-recovery-v2.summary.json"),
    ("B4000", "R2_B4000", "FIXTURE_B_PRIME", 4000, 38,
     "results/engine-physics-v1/b4000-continuation-data-v2/cycle-038.json.gz",
     "results/engine-physics-v1/b4000-continuation-data-v2/engineering-v2-038.json",
     "results/engine-physics-v1/b4000-continuation-runlog-v2/engine-physics-v1-b4000-continuation-v2.summary.json"),
)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_primary(path: Path) -> dict[str, Any]:
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        return json.load(stream)


def finite(value: Any) -> bool:
    return type(value) in (int, float) and math.isfinite(float(value))


def record(value: Any, units: str, definition: str, source: str,
           *, reason: str | None = None, dependency: str = "REQUIRED",
           provenance: str = "DERIVED_FROM_DOCUMENTED") -> dict[str, Any]:
    if value is None:
        return {"value": None, "status": "UNDEFINED", "units": units,
                "reason": reason or "MISSING_DEPENDENCY", "definition_version": definition,
                "source": source, "provenance": provenance,
                "periodicity_dependency": dependency}
    if not finite(value):
        raise ValueError(f"non-finite derived output: {source}")
    return {"value": float(value), "status": "DEFINED", "units": units,
            "reason": None, "definition_version": definition, "source": source,
            "provenance": provenance, "periodicity_dependency": dependency}


def ratio_record(ratio: dict[str, Any], units: str, name: str) -> dict[str, Any]:
    if ratio.get("status") == "AVAILABLE":
        return record(ratio["value"], units, "SCAVENGING_PARTITION_CONSERVATION_V1", name)
    return record(None, units, "SCAVENGING_PARTITION_CONSERVATION_V1", name,
                  reason=ratio.get("reason") or "UNDEFINED_UNDER_GROSS_CROSSING_SEMANTICS")


def output_metric(name: str, base: dict[str, Any], units: str, source: str,
                  definition: str = "ENGINE_PHYSICS_V1_R2_OUTPUTS") -> dict[str, Any]:
    item = base.get("outputs", {}).get(name)
    if not isinstance(item, dict) or item.get("status") != "DEFINED":
        reason = item.get("reason") if isinstance(item, dict) else "MISSING_DEPENDENCY"
        if name == "BSFC":
            brake = base.get("outputs", {}).get("brake_power", {}).get("value")
            if brake is not None and brake <= 0:
                reason = "NONPOSITIVE_BRAKE_POWER"
        return record(None, units, definition, source, reason=reason)
    return record(item.get("value"), units, definition, source,
                  provenance="SYNTHETIC_ASSUMPTION")


def build_point(point: tuple[str, str, str, int, int, str, str, str]) -> dict[str, Any]:
    point_id, artifact_id, fixture, rpm, cycle_no, primary_rel, old_rel, runtime_rel = point
    primary_path = resolve_external_artifact(artifact_id)
    artifact_entry = next(item for item in load_json(ROOT / "artifacts/engine-physics-v1-r2.json")["artifacts"]
                          if item["artifact_id"] == artifact_id)
    old_path, runtime_path = ROOT / old_rel, ROOT / runtime_rel
    old_r2_path = ROOT / "results/engine-physics-v1/r2-offline/manifest.json"
    primary = load_primary(primary_path)
    legacy_output = load_json(old_path)
    old_r2_manifest = load_json(old_r2_path)
    old_r2 = next(item for item in old_r2_manifest["points"] if item["point_id"] == point_id)
    fuel = synthetic_gasoline_v1()
    fixture_path = ROOT / "results/2t-commercial-core-20261002/fixtures/v1-prime-mesh" / (
        "fixture_a_prime-mesh-0.json" if point_id.startswith("A") else
        "fixture_b_prime-mesh-0.json")
    expected_fixture_id = "FIXTURE_A_PRIME" if point_id.startswith("A") else "FIXTURE_B_PRIME"
    fixture_resolution_error = None
    try:
        loss_model, fixture_provenance = load_fixture_model(primary, fixture_path, expected_fixture_id)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        loss_model = None
        fixture_resolution_error = "FIXTURE_MECHANICAL_LOSS_UNRESOLVED"
        fixture_provenance = {"status": "UNRESOLVED", "reason": fixture_resolution_error,
                              "detail": type(exc).__name__}
    evaluation_primary = primary if loss_model is not None else {**primary, "swept_displacement_m3": None}
    base = evaluate_integrated_cycle_v2(evaluation_primary, rpm=rpm, fuel=fuel,
                                        periodicity_status="PERIOD_1",
                                        mechanical_losses=loss_model)
    partition = evaluate_scavenging_partition_v1(primary)
    ratios = partition["metrics"]["ratios"]
    snap = primary["port_closure_snapshots"]["snapshots"]["exhaust"]["cylinder_species_kg"]
    cylinder = primary["observables"]["chambers"]["cylinder"]
    exhaust_rows = primary["observables"]["ducts"]["exhaust"]
    exhaust_temp = exhaust_rows[-1].get("temperature_K") if exhaust_rows else None
    obs = primary["observables"]
    combustion = obs["fuel_coupled_combustion"]
    src = f"primary:{artifact_id};sha256:{sha(primary_path)};cycle:{cycle_no};offline:R2_CORRECTED"
    provenance = "SYNTHETIC_ASSUMPTION"
    air_metered = obs.get("fresh_air_intake_delivery_kg")
    fuel_metered = obs.get("fuel_delivered_kg")
    fuel_sha = fuel.validate().sha256
    fuel_snapshot_bound = (primary.get("evidence_binding", {}).get("fuel_sha256") == fuel_sha and
                           combustion.get("fuel_sha256") == fuel_sha)
    stoich = fuel.validate().effective_stoichiometric_afr if fuel_snapshot_bound else None
    metering = metering_ratios(air_metered, fuel_metered, stoich)
    afr_value = metering["AFR"]["value"]
    lambda_value = metering["lambda"]["value"]
    phi_value = metering["phi"]["value"]
    available = combustion.get("fuel_available_from_ignition_snapshot_kg")
    burned = combustion.get("fuel_burned_kg")
    unburned = float(available) - float(burned) if finite(available) and finite(burned) else None
    ratios = partition["metrics"]["ratios"]
    delivery = ratios["delivery_ratio"]
    dr = record(delivery.get("value") if delivery.get("status") == "AVAILABLE" else None,
                "1", "R2_DELIVERY_RATIO_V1", src,
                reason=delivery.get("reason") or "MISSING_VALID_DELIVERY_LEDGER",
                provenance=provenance)
    ambiguous = "CURRENT_CYCLE_FRESH_RETENTION_NOT_IDENTIFIABLE"
    def undefined_scav(name):
        return record(None, "1", f"R2_{name}_V1", src, reason=ambiguous,
                      provenance=provenance)
    snapshot_mass = math.fsum(float(x) for x in snap)
    residual_purity = record(float(snap[2]) / snapshot_mass if snapshot_mass > 0 else None,
                             "1", "P6_EXHAUST_CLOSE_COMPOSITION_V1", src,
                             reason="ZERO_EXHAUST_CLOSE_SNAPSHOT_MASS", provenance=provenance)
    burned_purity = record(float(snap[3]) / snapshot_mass if snapshot_mass > 0 else None,
                           "1", "P6_EXHAUST_CLOSE_COMPOSITION_V1", src,
                           reason="ZERO_EXHAUST_CLOSE_SNAPSHOT_MASS", provenance=provenance)
    independent_partition = recompute_partition_conservation(primary)
    identity = scavenging_identity_check(dr, undefined_scav("TE"), undefined_scav("CE"))
    outputs = {
        "trapped_air": record(snap[0], "kg", "P6_EXHAUST_CLOSE_SPECIES_V1", src),
        "trapped_fuel": record(snap[1], "kg", "P6_EXHAUST_CLOSE_SPECIES_V1", src),
        "delivered_air": record(obs.get("fresh_air_intake_delivery_kg"), "kg", "P6_GROSS_AIR_DELIVERY_V1", src),
        "delivered_fuel": record(obs.get("fuel_delivered_kg"), "kg", "P6_GROSS_FUEL_DELIVERY_V1", src),
        "AFR": record(afr_value, "1", "P6_METERED_AIR_FUEL_RATIO_V1", src,
                      reason=metering["AFR"]["reason"],
                      provenance=provenance),
        "stoichiometric_AFR": record(stoich, "1", "FUEL_ELEMENTAL_STOICHIOMETRY_V1", src,
                                      reason="MISSING_STOICHIOMETRIC_AFR", provenance=provenance),
        "lambda": record(lambda_value, "1", "AFR_OVER_STOICHIOMETRIC_AFR_V1", src,
                         reason=metering["lambda"]["reason"],
                         provenance=provenance),
        "phi": record(phi_value, "1", "RECIPROCAL_LAMBDA_V1", src,
                      reason=metering["phi"]["reason"], provenance=provenance),
        "fuel_available": record(available, "kg", "FUEL_AVAILABLE_AT_IGNITION_V1", src,
                                 reason="MISSING_FUEL_AVAILABILITY_LEDGER", provenance=provenance),
        "fuel_burned": record(burned, "kg", "PRIMARY_FUEL_BURNED_LEDGER_V1", src,
                               reason="MISSING_FUEL_BURNED_LEDGER", provenance=provenance),
        "fuel_unburned": record(unburned, "kg", "AVAILABLE_MINUS_BURNED_FUEL_V1", src,
                                 reason="MISSING_FUEL_ACCOUNTING_LEDGER", provenance=provenance),
        "chemical_heat": record(combustion.get("chemical_heat_added_J"), "J", "FUEL_COUPLED_COMBUSTION_V2", src),
        "exhaust_temperature": record(exhaust_temp, "K", "P6_EXHAUST_TERMINAL_DUCT_V1", src),
        "DR": dr,
        "TE": undefined_scav("TE"),
        "SE": undefined_scav("SE"),
        "CE": undefined_scav("CE"),
        "residual_purity": residual_purity,
        "burned_purity": burned_purity,
        "cylinder_indicated_work": output_metric("cylinder_indicated_work", base, "J", src),
        "IMEP": output_metric("cylinder_IMEP", base, "Pa", src),
        "crankcase_gas_work": output_metric("crankcase_gas_work", base, "J", src),
        "net_piston_gas_work": output_metric("net_piston_gas_work", base, "J", src),
        "FMEP": (output_metric("FMEP", base, "Pa", src) if loss_model is not None else
                 record(None, "Pa", "MECHANICAL_LOSS_MODEL_V1", src,
                        reason=fixture_resolution_error, provenance=provenance)),
        "BMEP": output_metric("BMEP", base, "Pa", src),
        "indicated_power": output_metric("indicated_power", base, "W", src),
        "indicated_torque": output_metric("indicated_torque", base, "N*m", src),
        "brake_power": output_metric("brake_power", base, "W", src),
        "brake_torque": output_metric("brake_torque", base, "N*m", src),
        "ISFC": output_metric("ISFC", base, "g/kWh", src),
        "BSFC": output_metric("BSFC", base, "g/kWh", src),
    }
    outputs["AFR"]["source"] = (src + ";air_ledger:observables.fresh_air_intake_delivery_kg"
                                 ";fuel_ledger:observables.fuel_delivered_kg")
    outputs["stoichiometric_AFR"]["source"] = (
        src + f";fuel_snapshot_sha256:{fuel_sha};method:ELEMENTAL_MASS_BALANCE_DRY_AIR_V1")
    outputs["lambda"]["source"] = src + ";afr:AFR;stoichiometry:fuel_snapshot.elemental_mass_fractions"
    outputs["phi"]["source"] = src + ";lambda:lambda"
    outputs["fuel_available"]["source"] = src + ";ledger:observables.fuel_coupled_combustion.fuel_available_from_ignition_snapshot_kg"
    outputs["fuel_burned"]["source"] = src + ";ledger:observables.fuel_coupled_combustion.fuel_burned_kg"
    outputs["fuel_unburned"]["source"] = src + ";derived:fuel_available-fuel_burned"
    outputs["FMEP"]["source"] = (src + f";fixture:{fixture_path.name if loss_model else 'UNRESOLVED'};fixture_sha256:{fixture_provenance.get('fixture_file_sha256', 'UNAVAILABLE')}"
                                  ";model:MECHANICAL_LOSS_MODEL_V1;fields:terms[].mep_pa")
    if loss_model is None:
        for name in ("BMEP", "brake_power", "brake_torque", "BSFC"):
            if outputs[name]["status"] == "UNDEFINED":
                outputs[name]["reason"] = fixture_resolution_error
    for output in outputs.values():
        output["provenance"] = "SYNTHETIC_ASSUMPTION"
    residuals = primary["conservation"]
    burned = float(combustion["fuel_burned_kg"])
    available = float(combustion["fuel_available_from_ignition_snapshot_kg"])
    expected_heat = burned * float(combustion["energy_per_burned_fuel_j_kg"])
    hard_checks = {
        "finite_thermodynamic_state": finite(cylinder["pressure_Pa"]) and finite(cylinder["temperature_K"]),
        "pressure_positive": cylinder["pressure_Pa"] > 0,
        "temperature_positive": cylinder["temperature_K"] > 0,
        "mass_conservation": abs(residuals["mass_residual_kg"]) <= 1e-8,
        "energy_conservation": abs(residuals["energy_residual_J"]) <= 1e-8,
        "species_conservation": max(abs(v) for v in residuals["species_residual_kg"]) <= TOL,
        "partition_conservation_independent": independent_partition["passed"],
        "no_fuel_creation": burned <= available + TOL,
        "fuel_burned_le_fuel_available": burned <= available + TOL,
        "fuel_accounting_closure": (unburned is not None and
                                     math.isclose(burned + unburned, available,
                                                  rel_tol=0.0, abs_tol=TOL)),
        "metering_afr_consistency": (afr_value is not None and
                                     math.isclose(afr_value, air_metered / fuel_metered,
                                                  rel_tol=1e-12, abs_tol=1e-12)),
        "fixture_mechanical_loss_consistency": (loss_model is not None and
            outputs["FMEP"]["value"] is not None and math.isclose(
                float(outputs["FMEP"]["value"]),
                math.fsum(term.value(rpm, 1.0) for term in loss_model.terms),
                rel_tol=0.0, abs_tol=1e-9)),
        "scavenging_metric_dependency_validity": all(
            outputs[name]["status"] == "UNDEFINED" and outputs[name]["reason"] == ambiguous
            for name in ("TE", "CE", "SE")),
        "scavenging_metric_identity": identity["status"] == "NOT_APPLICABLE" or identity["passed"],
        "chemical_heat_consistent": abs(float(combustion["chemical_heat_added_J"]) - expected_heat) <= 1e-10,
        "defined_efficiencies_in_domain": all(
            item["status"] == "UNDEFINED" or 0 <= item["value"] <= 1
            for item in (outputs[name] for name in ("DR", "TE", "SE", "CE", "residual_purity", "burned_purity"))),
        "no_invalid_defined_outputs": all(
            item["status"] != "DEFINED" or finite(item["value"]) for item in outputs.values()),
        "no_placeholders": all(
            item.get("source", "").startswith(f"primary:{artifact_id};sha256:{sha(primary_path)};") and
            item.get("definition_version") not in (None, "", "UNKNOWN") and
            not (item.get("status") == "UNDEFINED" and item.get("value") is not None) and
            item.get("provenance") in {"DERIVED_FROM_DOCUMENTED", "SYNTHETIC_ASSUMPTION"}
            for item in outputs.values()),
    }
    displacement = float(primary["swept_displacement_m3"])
    net_piston_work = float(obs["net_piston_gas_work_J"])
    expected_brake_work = (None if outputs["FMEP"]["value"] is None else
                           net_piston_work - float(outputs["FMEP"]["value"]) * displacement)
    hard_checks["bmep_brake_work_consistency"] = (expected_brake_work is not None and
        outputs["BMEP"]["value"] is not None and math.isclose(
            float(outputs["BMEP"]["value"]), expected_brake_work / displacement,
            rel_tol=1e-12, abs_tol=1e-9))
    brake_power = outputs["brake_power"].get("value")
    brake_torque = outputs["brake_torque"].get("value")
    hard_checks["brake_torque_power_consistency"] = (
        brake_power is not None and brake_torque is not None and
        math.isclose(float(brake_power), float(brake_torque) * 2 * math.pi * rpm / 60,
                     rel_tol=1e-12, abs_tol=1e-12))
    hard_checks.update(output_hard_checks(
        fmep_used_pa=outputs["FMEP"].get("value"), fixture_model=loss_model, rpm=rpm,
        afr=outputs["AFR"], air_kg=air_metered, metered_fuel_kg=fuel_metered,
        available_fuel_kg=available, burned_fuel_kg=burned,
        unburned_fuel_kg=unburned, outputs=outputs,
        fuel_snapshot_bound=fuel_snapshot_bound,
        partition=independent_partition, scavenging_identity=identity,
        expected_source_prefix=f"primary:{artifact_id};sha256:{sha(primary_path)};"))
    outputs["FMEP"]["provenance_details"] = fixture_provenance
    hard_failures = [name for name, passed in hard_checks.items() if not passed]
    warnings = list(base["hard_gate"].get("warnings", []))
    if float(obs["net_piston_gas_work_J"]) <= 0:
        warnings.append("PLAUSIBILITY_WARNING:nonpositive_net_piston_work indicates a motoring/low-load synthetic point")
    brake_power = base.get("outputs", {}).get("brake_power", {}).get("value")
    if brake_power is not None and brake_power <= 0:
        warnings.append("PLAUSIBILITY_WARNING:nonpositive_brake_power indicates a motoring/low-load synthetic point")
    runtime = load_json(runtime_path)
    binding = primary.get("evidence_binding", {})
    return {
        "schema": "ENGINE_PHYSICS_V1_R2_CORRECTED_POINT_RESULT",
        "point_id": point_id, "fixture": fixture, "rpm": rpm, "cycle": cycle_no,
        "swept_displacement_m3": displacement,
        "periodicity": {"status": "PERIOD_1", "detector": "PeriodicDetectorV2", "source": "existing campaign receipt"},
        "operating_point_status": "PERIODIC_ENGINEERING_RESULT",
        "primary": {"artifact_id": artifact_id,
                    "path": primary_rel,
                    "external_relative_path": artifact_entry["expected_external_relative_path"],
                    "sha256": sha(primary_path),
                    "byte_size": primary_path.stat().st_size,
                    "configuration_sha256": primary["configuration_hash"]},
        "historical_runtime": {"summary_path": runtime_rel, "summary_sha256": sha(runtime_path),
                               "campaign_duration_s": runtime.get("duration_s"),
                               "point_runtime_not_separately_recorded": True},
        "binding_hashes": binding,
        "model_versions": {
            "solver_primary": primary.get("schema", "REFERENCE_ENGINE_HYBRID_CYCLE_PRIMARY_V1"),
            "fuel": "FUEL_COUPLED_COMBUSTION_V2",
            "scavenging": "SCAVENGING_PARTITION_CONSERVATION_V1",
            "mechanical_losses": "MECHANICAL_LOSS_MODEL_V1",
            "output_adapter": "ENGINE_PHYSICS_V1_R2_SEMANTIC_CORRECTION_V1",
        },
        "fixture_mechanical_loss_provenance": fixture_provenance,
        "outputs": outputs,
        "scavenging_partition": partition,
        "scavenging_identity": identity,
        "independent_partition_conservation": independent_partition,
        "hard_physical_gate": {"classification": "PASS" if not hard_failures else "HARD_PHYSICAL_INVALID",
                                "checks": hard_checks, "hard_failures": hard_failures},
        "warnings": sorted(set(warnings)),
        "old_output": {"path": "results/engine-physics-v1/r2-offline/manifest.json",
                       "sha256": sha(old_r2_path), "point_id": point_id},
        "historical_engineering_reference": {"path": old_rel, "sha256": sha(old_path)},
        "provenance": {"trajectory_unchanged": True, "replay": "OFFLINE_DERIVED_OUTPUT_ONLY",
                        "physics_changed": False, "scope": "accounting/semantics/output serialization",
                        "supersedes": "R2 outputs only; accepted primaries and EP_R2_EXTERNAL_REVIEW_FAIL remain unchanged"},
    }


def comparison(point_result: dict[str, Any], old: dict[str, Any]) -> dict[str, Any]:
    names = {"FMEP": "FMEP", "AFR": "AFR", "lambda": "lambda", "phi": "phi",
             "DR": "DR", "SE": "SE", "CE": "CE", "TE": "TE",
             "fuel_available": "fuel_available", "fuel_burned": "fuel_burned",
             "fuel_unburned": "fuel_unburned", "residual_purity": "residual_purity",
             "burned_purity": "burned_purity", "IMEP": "cylinder_IMEP", "BMEP": "BMEP",
             "indicated_power": "indicated_power", "brake_power": "brake_power",
             "indicated_torque": "indicated_torque", "brake_torque": "brake_torque",
             "ISFC": "ISFC", "BSFC": "BSFC"}
    rows = {}
    for new_name, old_name in names.items():
        old_item = old.get("outputs", {}).get(old_name, {})
        new_item = point_result["outputs"][new_name]
        rows[new_name] = {"old": old_item.get("value"), "new": new_item.get("value"),
                          "old_status": old_item.get("status"), "new_status": new_item.get("status")}
    rows["TE"]["old_status"] = old.get("outputs", {}).get("TE", {}).get("status")
    rows["TE"]["new_reason"] = point_result["outputs"]["TE"].get("reason")
    old_species_closure = old.get("scavenging_partition", {}).get("species_closure", {})
    rows["partition_residual"] = {
        "old": old_species_closure.get("max_abs_residual_kg"),
        "new": point_result["independent_partition_conservation"]["max_abs_species_residual_kg"],
        "old_status": "PASS" if old_species_closure.get("passed") else "FAIL",
        "old_basis": "persisted R2 producer species residual; not an independent proof",
        "new_status": "PASS" if point_result["independent_partition_conservation"]["passed"] else "FAIL",
    }
    rows["legacy_gross_partition_residual"] = {
        "value": point_result.get("historical_engineering_reference", {}).get("partition_residual_kg"),
        "source": "historical engineering-v2 reference only; distinct from R2 independent species closure",
    }
    return rows


def run(out: Path) -> dict[str, Any]:
    out.mkdir(parents=True, exist_ok=True)
    results = []
    comparisons = {}
    old_r2_manifest = load_json(ROOT / "results/engine-physics-v1/r2-offline/manifest.json")
    old_r2_by_point = {item["point_id"]: item for item in old_r2_manifest["points"]}
    for point in POINTS:
        result = build_point(point)
        legacy_old = load_json(ROOT / point[6])
        result["historical_engineering_reference"]["partition_residual_kg"] = (
            legacy_old.get("scavenging", {}).get("conservation", {}).get("partition_residual_kg"))
        target = out / point[0]
        target.mkdir(exist_ok=True)
        (target / f"engineering-r2-{point[4]:03d}.json").write_text(
            json.dumps(result, sort_keys=True, indent=2, allow_nan=False) + "\n", encoding="utf-8")
        comparisons[point[0]] = comparison(result, old_r2_by_point[point[0]])
        results.append(result)
    all_hard_gates_pass = all(x["hard_physical_gate"]["classification"] == "PASS"
                              for x in results)
    all_periodic = all(x["periodicity"]["status"] == "PERIOD_1" for x in results)
    semantic_result = ("ENGINE_PHYSICS_V1_R2_SEMANTIC_CORRECTION_READY_FOR_REVIEW"
                       if len(results) == 4 and all_hard_gates_pass and all_periodic else
                       "ENGINE_PHYSICS_V1_R2_SEMANTIC_CORRECTION_BLOCKED")
    manifest = {"schema": "ENGINE_PHYSICS_V1_R2_CORRECTED_OFFLINE_MANIFEST", "status": "REVIEW",
                "semantic_correction_result": semantic_result,
                "first_review_result": "EP_R2_EXTERNAL_REVIEW_FAIL",
                "supersedes": "defective R2 outputs only; accepted primaries and first external review are preserved",
                "campaigns_started": 0, "points": results, "comparison": comparisons,
                "replay_script_sha256": sha(Path(__file__)),
                "partition_module_sha256": sha(ROOT / "motorsim/scavenging_partition_v1.py"),
                "producer_module_sha256": sha(ROOT / "motorsim/engine_physics_v1.py"),
                "source_policy": "four existing accepted periodic primaries only",
                "gate": {"all_periodic": all_periodic,
                         "all_hard_gates_pass": all_hard_gates_pass,
                         "result": "REVIEW", "external_review_task": "EP-R2-EXTERNAL-REVIEW"}}
    (out / "comparison.json").write_text(json.dumps(comparisons, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    (out / "manifest.json").write_text(json.dumps(manifest, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return {"status": "REVIEW", "points": len(results),
            "all_hard_gates_pass": manifest["gate"]["all_hard_gates_pass"],
            "manifest_sha256": sha(out / "manifest.json")}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=Path("results/engine-physics-v1/r2-semantic-correction"))
    args = parser.parse_args()
    try:
        print(json.dumps(run((ROOT / args.out).resolve()), sort_keys=True))
    except ArtifactStoreError as exc:
        parser.exit(2, f"{exc}\n")
