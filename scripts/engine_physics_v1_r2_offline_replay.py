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

from motorsim.engine_physics_v1 import (evaluate_integrated_cycle_v2,
                                        standard_fmep_model_v1,
                                        synthetic_gasoline_v1)
from motorsim.artifact_store import ArtifactStoreError, resolve_external_artifact
from motorsim.scavenging_partition_v1 import evaluate_scavenging_partition_v1

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
           *, reason: str | None = None, dependency: str = "REQUIRED") -> dict[str, Any]:
    if value is None:
        return {"value": None, "status": "UNDEFINED", "units": units,
                "reason": reason or "MISSING_DEPENDENCY", "definition_version": definition,
                "source": source, "provenance": "DERIVED_FROM_DOCUMENTED",
                "periodicity_dependency": dependency}
    if not finite(value):
        raise ValueError(f"non-finite derived output: {source}")
    return {"value": float(value), "status": "DEFINED", "units": units,
            "reason": None, "definition_version": definition, "source": source,
            "provenance": "DERIVED_FROM_DOCUMENTED", "periodicity_dependency": dependency}


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
        return record(None, units, definition, source, reason=reason)
    return record(item.get("value"), units, definition, source)


def build_point(point: tuple[str, str, str, int, int, str, str, str]) -> dict[str, Any]:
    point_id, artifact_id, fixture, rpm, cycle_no, primary_rel, old_rel, runtime_rel = point
    primary_path = resolve_external_artifact(artifact_id)
    old_path, runtime_path = ROOT / old_rel, ROOT / runtime_rel
    primary = load_primary(primary_path)
    old = load_json(old_path)
    fuel = synthetic_gasoline_v1()
    loss_model = standard_fmep_model_v1()
    base = evaluate_integrated_cycle_v2(primary, rpm=rpm, fuel=fuel,
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
    src = f"primary:{primary_rel};cycle:{cycle_no};offline:R2"
    outputs = {
        "trapped_air": record(snap[0], "kg", "P6_EXHAUST_CLOSE_SPECIES_V1", src),
        "trapped_fuel": record(snap[1], "kg", "P6_EXHAUST_CLOSE_SPECIES_V1", src),
        "delivered_air": record(obs.get("fresh_air_intake_delivery_kg"), "kg", "P6_GROSS_AIR_DELIVERY_V1", src),
        "delivered_fuel": record(obs.get("fuel_delivered_kg"), "kg", "P6_GROSS_FUEL_DELIVERY_V1", src),
        "AFR": output_metric("AFR", base, "1", src),
        "lambda": output_metric("lambda", base, "1", src),
        "phi": output_metric("phi", base, "1", src),
        "fuel_burned": record(combustion.get("fuel_burned_kg"), "kg", "FUEL_COUPLED_COMBUSTION_V2", src),
        "fuel_unburned": record(combustion.get("unburned_fuel_at_exhaust_close_kg"), "kg", "FUEL_COUPLED_COMBUSTION_V2", src),
        "chemical_heat": record(combustion.get("chemical_heat_added_J"), "J", "FUEL_COUPLED_COMBUSTION_V2", src),
        "exhaust_temperature": record(exhaust_temp, "K", "P6_EXHAUST_TERMINAL_DUCT_V1", src),
        "DR": ratio_record(ratios["delivery_ratio"], "1", src),
        "TE": ratio_record(ratios["trapping_efficiency"], "1", src),
        "SE": ratio_record(ratios["scavenging_efficiency"], "1", src),
        "CE": ratio_record(ratios["charging_efficiency"], "1", src),
        "residual_purity": ratio_record(ratios["residual_fraction"], "1", src),
        "burned_purity": record(snap[3] / sum(snap), "1", "P6_EXHAUST_CLOSE_SPECIES_V1", src),
        "cylinder_indicated_work": output_metric("cylinder_indicated_work", base, "J", src),
        "IMEP": output_metric("cylinder_IMEP", base, "Pa", src),
        "crankcase_gas_work": output_metric("crankcase_gas_work", base, "J", src),
        "net_piston_gas_work": output_metric("net_piston_gas_work", base, "J", src),
        "FMEP": output_metric("FMEP", base, "Pa", src),
        "BMEP": output_metric("BMEP", base, "Pa", src),
        "indicated_power": output_metric("indicated_power", base, "W", src),
        "indicated_torque": output_metric("indicated_torque", base, "N*m", src),
        "brake_power": output_metric("brake_power", base, "W", src),
        "brake_torque": output_metric("brake_torque", base, "N*m", src),
        "ISFC": output_metric("ISFC", base, "g/kWh", src),
        "BSFC": output_metric("BSFC", base, "g/kWh", src),
    }
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
        "partition_conservation": partition["species_closure"]["passed"],
        "no_fuel_creation": burned <= available + TOL,
        "fuel_burned_le_fuel_available": burned <= float(obs["fuel_delivered_kg"]) + TOL,
        "chemical_heat_consistent": abs(float(combustion["chemical_heat_added_J"]) - expected_heat) <= 1e-10,
        "defined_efficiencies_in_domain": all(
            item["status"] == "UNDEFINED" or 0 <= item["value"] <= 1
            for item in (outputs[name] for name in ("DR", "TE", "SE", "CE", "residual_purity", "burned_purity"))),
        "no_invalid_defined_outputs": all(
            item["status"] != "DEFINED" or finite(item["value"]) for item in outputs.values()),
        "no_placeholders": all(item.get("source") and item.get("definition_version") for item in outputs.values()),
    }
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
        "schema": "ENGINE_PHYSICS_V1_R2_POINT_RESULT",
        "point_id": point_id, "fixture": fixture, "rpm": rpm, "cycle": cycle_no,
        "periodicity": {"status": "PERIOD_1", "detector": "PeriodicDetectorV2", "source": "existing campaign receipt"},
        "operating_point_status": "PERIODIC_ENGINEERING_RESULT",
        "primary": {"path": primary_rel, "sha256": sha(primary_path), "configuration_sha256": primary["configuration_hash"]},
        "historical_runtime": {"summary_path": runtime_rel, "summary_sha256": sha(runtime_path),
                               "campaign_duration_s": runtime.get("duration_s"),
                               "point_runtime_not_separately_recorded": True},
        "binding_hashes": binding,
        "model_versions": {
            "solver_primary": primary.get("schema", "REFERENCE_ENGINE_HYBRID_CYCLE_PRIMARY_V1"),
            "fuel": "FUEL_COUPLED_COMBUSTION_V2",
            "scavenging": "SCAVENGING_PARTITION_CONSERVATION_V1",
            "mechanical_losses": "MECHANICAL_LOSSES_STANDARD_V1",
            "output_adapter": "ENGINE_PHYSICS_V1_R2_OFFLINE",
        },
        "outputs": outputs,
        "scavenging_partition": partition,
        "hard_physical_gate": {"classification": "PASS" if not hard_failures else "HARD_PHYSICAL_INVALID",
                                "checks": hard_checks, "hard_failures": hard_failures},
        "warnings": sorted(set(warnings)),
        "old_output": {"path": old_rel, "sha256": sha(old_path)},
        "provenance": {"trajectory_unchanged": True, "replay": "OFFLINE_DERIVED_OUTPUT_ONLY",
                        "physics_changed": False, "scope": "accounting/semantics/output serialization"},
    }


def comparison(point_result: dict[str, Any], old: dict[str, Any]) -> dict[str, Any]:
    names = {"AFR": "AFR", "DR": "DR", "SE": "SE", "CE": "CE", "TE": "TE",
             "fuel_burned": "fuel_burned", "IMEP": "cylinder_IMEP", "BMEP": "BMEP",
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
    rows["partition_residual"] = {
        "old": old.get("scavenging", {}).get("conservation", {}).get("partition_residual_kg"),
        "new": point_result["scavenging_partition"]["species_closure"]["max_abs_residual_kg"],
        "new_status": "PASS",
    }
    return rows


def run(out: Path) -> dict[str, Any]:
    out.mkdir(parents=True, exist_ok=True)
    results = []
    comparisons = {}
    for point in POINTS:
        result = build_point(point)
        target = out / point[0]
        target.mkdir(exist_ok=True)
        (target / f"engineering-r2-{point[4]:03d}.json").write_text(
            json.dumps(result, sort_keys=True, indent=2, allow_nan=False) + "\n", encoding="utf-8")
        old = load_json(ROOT / point[6])
        comparisons[point[0]] = comparison(result, old)
        results.append(result)
    manifest = {"schema": "ENGINE_PHYSICS_V1_R2_OFFLINE_MANIFEST", "status": "REVIEW",
                "campaigns_started": 0, "points": results, "comparison": comparisons,
                "replay_script_sha256": sha(Path(__file__)),
                "partition_module_sha256": sha(ROOT / "motorsim/scavenging_partition_v1.py"),
                "producer_module_sha256": sha(ROOT / "motorsim/engine_physics_v1.py"),
                "source_policy": "four existing accepted periodic primaries only",
                "gate": {"all_periodic": all(x["periodicity"]["status"] == "PERIOD_1" for x in results),
                         "all_hard_gates_pass": all(x["hard_physical_gate"]["classification"] == "PASS" for x in results),
                         "result": "REVIEW", "external_review_task": "EP-R2-EXTERNAL-REVIEW"}}
    (out / "comparison.json").write_text(json.dumps(comparisons, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    (out / "manifest.json").write_text(json.dumps(manifest, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return {"status": "REVIEW", "points": len(results),
            "all_hard_gates_pass": manifest["gate"]["all_hard_gates_pass"],
            "manifest_sha256": sha(out / "manifest.json")}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=Path("results/engine-physics-v1/r2-offline"))
    args = parser.parse_args()
    try:
        print(json.dumps(run((ROOT / args.out).resolve()), sort_keys=True))
    except ArtifactStoreError as exc:
        parser.exit(2, f"{exc}\n")
