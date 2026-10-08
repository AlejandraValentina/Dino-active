"""Independent output contracts for offline ENGINE_PHYSICS_V1_R2 correction."""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any, Mapping

from .mechanical import MechanicalLossModel

SPECIES = ("fresh_air", "fuel", "residual", "burned")
CONSERVATION_TOLERANCE_KG = 1e-12
OUTPUT_RELATIVE_TOLERANCE = 1e-10
OUTPUT_ABSOLUTE_TOLERANCE = 1e-12
OUTPUT_PRESSURE_ABSOLUTE_TOLERANCE_PA = 1e-9
OUTPUT_SPECIFIC_FUEL_CONSUMPTION_ABSOLUTE_TOLERANCE = 1e-8


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def metering_ratios(air_kg: Any, fuel_kg: Any,
                    stoichiometric_afr: Any) -> dict[str, Any]:
    """Return same-boundary air/fuel ratio, lambda, and phi with causal reasons."""
    air_valid = type(air_kg) in (int, float) and math.isfinite(air_kg) and air_kg >= 0
    fuel_valid = type(fuel_kg) in (int, float) and math.isfinite(fuel_kg) and fuel_kg >= 0
    afr = None
    afr_reason = None
    if not air_valid:
        afr_reason = "MISSING_AIR_METERING_LEDGER"
    elif not fuel_valid:
        afr_reason = "MISSING_FUEL_METERING_LEDGER"
    elif fuel_kg == 0:
        afr_reason = "ZERO_FUEL_DELIVERY"
    else:
        afr = float(air_kg) / float(fuel_kg)
    stoich_valid = (type(stoichiometric_afr) in (int, float) and
                    math.isfinite(stoichiometric_afr) and stoichiometric_afr > 0)
    lam = (afr / float(stoichiometric_afr) if afr is not None and stoich_valid else None)
    lam_reason = ("MISSING_STOICHIOMETRIC_AFR" if afr is not None and not stoich_valid
                  else "AFR_UNDEFINED" if afr is None else None)
    phi = 1.0 / lam if lam is not None and lam > 0 else None
    phi_reason = "LAMBDA_UNDEFINED" if lam is None else None
    return {"AFR": {"value": afr, "status": "DEFINED" if afr is not None else "UNDEFINED",
                    "reason": afr_reason},
            "lambda": {"value": lam, "status": "DEFINED" if lam is not None else "UNDEFINED",
                       "reason": lam_reason},
            "phi": {"value": phi, "status": "DEFINED" if phi is not None else "UNDEFINED",
                    "reason": phi_reason}}


def load_fixture_model(primary: Mapping[str, Any], fixture_path: Path,
                       expected_fixture_id: str) -> tuple[MechanicalLossModel, dict[str, Any]]:
    """Load losses from the A-prime/B-prime fixture matching primary config."""
    fixture_bytes = fixture_path.read_bytes()
    fixture = json.loads(fixture_bytes.decode("utf-8"))
    configuration = primary.get("configuration")
    fixture_configuration = fixture.get("engine_configuration")
    identity = primary.get("configuration_identity")
    binding = primary.get("evidence_binding")
    if (fixture.get("fixture_id") != expected_fixture_id or
            not isinstance(configuration, Mapping) or
            not isinstance(fixture_configuration, Mapping) or
            not isinstance(identity, Mapping) or not isinstance(binding, Mapping)):
        raise ValueError("FIXTURE_MECHANICAL_LOSS_UNRESOLVED")
    # The fixture configuration must match the primary configuration except
    # for the versioned fuel-coupling schema and the point's declared RPM.
    allowed = {"schema", "fuel_coupled_combustion", "reference_rpm"}
    differences = {key for key in set(configuration) | set(fixture_configuration)
                   if configuration.get(key) != fixture_configuration.get(key)}
    if not differences <= allowed:
        raise ValueError("FIXTURE_CONFIGURATION_MISMATCH")
    fixture_config_bytes = json.dumps(
        fixture_configuration, sort_keys=True, separators=(",", ":"),
        ensure_ascii=False, allow_nan=False).encode("utf-8")
    fixture_config_sha = hashlib.sha256(fixture_config_bytes).hexdigest()
    if fixture.get("engine_configuration_sha256") != fixture_config_sha:
        raise ValueError("FIXTURE_CONFIGURATION_HASH_MISMATCH")
    encoded_identity = json.dumps(identity, sort_keys=True, separators=(",", ":"),
                                  allow_nan=False).encode("utf-8")
    bound_sha = hashlib.sha256(encoded_identity).hexdigest()
    identity_payload = dict(identity)
    claimed_configuration_sha = identity_payload.pop("configuration_sha256", None)
    encoded_configuration = json.dumps(identity_payload, sort_keys=True,
                                       separators=(",", ":"), ensure_ascii=False,
                                       allow_nan=False).encode("utf-8")
    calculated_configuration_sha = hashlib.sha256(encoded_configuration).hexdigest()
    if (identity.get("configuration_sha256") != primary.get("configuration_hash") or
            claimed_configuration_sha != calculated_configuration_sha or
            binding.get("fixture_sha256") != bound_sha):
        raise ValueError("FIXTURE_PRIMARY_BINDING_MISMATCH")
    raw_model = fixture.get("mechanical_loss_model")
    if not isinstance(raw_model, Mapping):
        raise ValueError("FIXTURE_MECHANICAL_LOSS_UNRESOLVED")
    model = MechanicalLossModel.from_dict(dict(raw_model))
    details = {
        "fixture_id": fixture["fixture_id"],
        "fixture_file_sha256": hashlib.sha256(fixture_bytes).hexdigest(),
        "primary_configuration_binding_sha256": bound_sha,
        "fixture_engine_configuration_sha256": fixture_config_sha,
        "mechanical_loss_model_sha256": hashlib.sha256(
            json.dumps(raw_model, sort_keys=True, separators=(",", ":"),
                       ensure_ascii=False, allow_nan=False).encode("utf-8")).hexdigest(),
        "association_method": "fixture_id plus exact engine_configuration match apart from allowed schema/fuel/RPM fields",
        "mechanical_loss_model_version": raw_model.get("schema"),
        "fields_used": ["terms[].id", "terms[].source", "terms[].mep_pa",
                        "terms[].operating_map", "terms[].provenance"],
        "model": model.to_dict(),
        "configuration_differences_allowed": sorted(differences),
        "provenance": sorted({term.provenance for term in model.terms}),
    }
    return model, details


def inventory_by_species(species_tree: Any) -> list[float]:
    """Sum every chamber, duct cell, and network volume species inventory."""
    totals = [0.0, 0.0, 0.0, 0.0]

    def visit(value: Any) -> None:
        if isinstance(value, Mapping):
            for child in value.values():
                visit(child)
        elif isinstance(value, (list, tuple)):
            if (len(value) == 4 and
                    all(type(item) in (int, float) and math.isfinite(item)
                        for item in value)):
                for index, item in enumerate(value):
                    totals[index] += float(item)
            else:
                for child in value:
                    visit(child)
        else:
            raise ValueError("INVALID_SPECIES_INVENTORY_PRIMITIVE")

    visit(species_tree)
    return totals


def recompute_partition_conservation(primary: Mapping[str, Any]) -> dict[str, Any]:
    start = primary.get("start_state", {}).get("species")
    terminal = primary.get("terminal_state", {}).get("species")
    ledgers = primary.get("cycle_ledgers", {})
    if start is None or terminal is None:
        raise ValueError("MISSING_SPECIES_INVENTORY_PRIMITIVES")
    initial = inventory_by_species(start)
    final = inventory_by_species(terminal)
    external = ledgers.get("external_species_kg")
    combustion = ledgers.get("fuel_combustion_source_species_kg")
    p7 = ledgers.get("p7_source_species_kg")
    if any(not isinstance(x, (list, tuple)) or len(x) != 4
           for x in (external, combustion, p7)):
        raise ValueError("MISSING_SPECIES_EXCHANGE_PRIMITIVES")
    residuals = [final[i] - initial[i] - float(external[i]) -
                 float(combustion[i]) - float(p7[i]) for i in range(4)]
    return {
        "equation": "terminal_inventory - initial_inventory - external_exchange - fuel_combustion_sources - p7_sources",
        "initial_inventory_kg": dict(zip(SPECIES, initial)),
        "terminal_inventory_kg": dict(zip(SPECIES, final)),
        "external_exchange_kg": dict(zip(SPECIES, map(float, external))),
        "fuel_combustion_sources_kg": dict(zip(SPECIES, map(float, combustion))),
        "p7_sources_kg": dict(zip(SPECIES, map(float, p7))),
        "residual_kg_by_species": dict(zip(SPECIES, residuals)),
        "total_mass_residual_kg": math.fsum(residuals),
        "max_abs_species_residual_kg": max(map(abs, residuals)),
        "tolerance_kg": CONSERVATION_TOLERANCE_KG,
        "passed": (max(map(abs, residuals)) <= CONSERVATION_TOLERANCE_KG and
                   abs(math.fsum(residuals)) <= CONSERVATION_TOLERANCE_KG),
    }


def scavenging_identity_check(dr: Mapping[str, Any], te: Mapping[str, Any],
                              ce: Mapping[str, Any], *, tolerance: float = 1e-10) -> dict[str, Any]:
    records = (dr, te, ce)
    if any(item.get("status") != "DEFINED" for item in records):
        return {"status": "NOT_APPLICABLE", "passed": None,
                "reason": "REQUIRED_SCAVENGING_METRIC_UNDEFINED"}
    values = [item.get("value") for item in records]
    if any(type(value) not in (int, float) or not math.isfinite(value)
           for value in values):
        return {"status": "FAIL", "passed": False, "reason": "INVALID_DEFINED_SCAVENGING_VALUE"}
    d, t, c = map(float, values)
    passed = (0 <= d <= 1 and 0 <= t <= 1 and 0 <= c <= 1 and
              abs(c - d * t) <= tolerance and c <= d + tolerance)
    return {"status": "DEFINED", "passed": passed,
            "equation": "CE = DR * TE", "residual": c - d * t,
            "tolerance": tolerance}


def _matches_defined(outputs: Mapping[str, Any], name: str, expected: float | None,
                     *, rel_tol: float = OUTPUT_RELATIVE_TOLERANCE,
                     abs_tol: float = OUTPUT_ABSOLUTE_TOLERANCE) -> bool:
    item = outputs.get(name, {})
    value = item.get("value") if isinstance(item, Mapping) else None
    return (expected is not None and item.get("status") == "DEFINED" and
            type(value) in (int, float) and math.isfinite(value) and
            math.isclose(float(value), float(expected), rel_tol=rel_tol, abs_tol=abs_tol))


def engineering_output_consistency(primary: Mapping[str, Any],
                                   outputs: Mapping[str, Any], *, rpm: float,
                                   displacement_m3: float,
                                   fmep_expected_pa: float | None,
                                   expected_source_prefix: str) -> dict[str, bool]:
    """Check published values against primary ledgers and closure snapshots.

    Expected values are deliberately reconstructed here from primary primitives,
    not read from the engineering output adapter result.
    """
    observables = primary.get("observables", {})
    ledgers = primary.get("cycle_ledgers", {})
    combustion = observables.get("fuel_coupled_combustion", {})
    # Cycle work ledgers are gas-energy changes (negative for piston work
    # delivered by the cylinder, positive for crankcase gas work here). The
    # engineering contract reports piston work positive out of the gas.
    cylinder_ledger_work = ledgers.get("cylinder_work_J")
    crankcase_ledger_work = ledgers.get("crankcase_work_J")
    cylinder_work = (-float(cylinder_ledger_work)
                     if finite_number(cylinder_ledger_work) else None)
    crankcase_work = (-float(crankcase_ledger_work)
                      if finite_number(crankcase_ledger_work) else None)
    metered_fuel = observables.get("fuel_delivered_kg")
    available = combustion.get("fuel_available_from_ignition_snapshot_kg")
    burned = combustion.get("fuel_burned_kg")
    trapped = (primary.get("port_closure_snapshots", {}).get("snapshots", {})
               .get("exhaust", {}).get("cylinder_species_kg"))
    valid_geometry = (finite_number(rpm) and rpm > 0 and
                      finite_number(displacement_m3) and displacement_m3 > 0)
    valid_work = finite_number(cylinder_work) and finite_number(crankcase_work)
    indicated_power = (float(cylinder_work) * float(rpm) / 60.0
                       if valid_geometry and finite_number(cylinder_work) else None)
    indicated_torque = (float(cylinder_work) / (2.0 * math.pi)
                        if finite_number(cylinder_work) else None)
    imep = (float(cylinder_work) / float(displacement_m3)
            if valid_geometry and finite_number(cylinder_work) else None)
    net_work = (math.fsum((float(cylinder_work), float(crankcase_work)))
                if valid_work else None)
    bmep = (net_work / float(displacement_m3) - float(fmep_expected_pa)
            if valid_geometry and net_work is not None and finite_number(fmep_expected_pa)
            else None)
    brake_power = (bmep * float(displacement_m3) * float(rpm) / 60.0
                   if bmep is not None else None)
    brake_torque = (bmep * float(displacement_m3) / (2.0 * math.pi)
                    if bmep is not None else None)
    delivery_frequency = float(rpm) / 60.0 if valid_geometry else None
    isfc = (float(metered_fuel) * delivery_frequency * 3.6e9 / indicated_power
            if finite_number(metered_fuel) and delivery_frequency is not None and
            indicated_power is not None and indicated_power > 0 else None)
    bsfc = (float(metered_fuel) * delivery_frequency * 3.6e9 / brake_power
            if finite_number(metered_fuel) and delivery_frequency is not None and
            brake_power is not None and brake_power > 0 else None)
    checks = {
        "cylinder_indicated_work_consistency": _matches_defined(
            outputs, "cylinder_indicated_work", cylinder_work),
        "indicated_work_imep_consistency": _matches_defined(outputs, "IMEP", imep),
        "indicated_power_2t_work_rpm_consistency": _matches_defined(
            outputs, "indicated_power", indicated_power),
        "indicated_torque_work_consistency": _matches_defined(
            outputs, "indicated_torque", indicated_torque),
        "indicated_power_torque_rpm_consistency": (
            indicated_power is not None and indicated_torque is not None and
            math.isclose(indicated_power, indicated_torque * 2.0 * math.pi * rpm / 60.0,
                         rel_tol=1e-10, abs_tol=1e-12)),
        "bmep_brake_work_fmep_consistency": _matches_defined(outputs, "BMEP", bmep,
                                      abs_tol=OUTPUT_PRESSURE_ABSOLUTE_TOLERANCE_PA),
        "brake_power_bmep_2t_consistency": _matches_defined(
            outputs, "brake_power", brake_power,
            abs_tol=OUTPUT_ABSOLUTE_TOLERANCE),
        "brake_torque_bmep_consistency": _matches_defined(
            outputs, "brake_torque", brake_torque),
        "brake_power_torque_rpm_consistency": (
            brake_power is not None and brake_torque is not None and
            math.isclose(brake_power, brake_torque * 2.0 * math.pi * rpm / 60.0,
                         rel_tol=1e-10, abs_tol=1e-12)),
        "ISFC_fuel_flow_indicated_power_consistency": (
            _matches_defined(outputs, "ISFC", isfc,
                             abs_tol=OUTPUT_SPECIFIC_FUEL_CONSUMPTION_ABSOLUTE_TOLERANCE)
            if isfc is not None else outputs.get("ISFC", {}).get("status") == "UNDEFINED"),
        "BSFC_fuel_flow_brake_power_consistency": (
            _matches_defined(outputs, "BSFC", bsfc,
                             abs_tol=OUTPUT_SPECIFIC_FUEL_CONSUMPTION_ABSOLUTE_TOLERANCE)
            if bsfc is not None else
            outputs.get("BSFC", {}).get("status") == "UNDEFINED" and
            (brake_power is None or brake_power <= 0) and
            outputs.get("BSFC", {}).get("reason") == "NONPOSITIVE_BRAKE_POWER"),
        "trapped_air_snapshot_consistency": (
            isinstance(trapped, (list, tuple)) and len(trapped) == 4 and
            _matches_defined(outputs, "trapped_air", trapped[0])),
        "trapped_fuel_snapshot_consistency": (
            isinstance(trapped, (list, tuple)) and len(trapped) == 4 and
            _matches_defined(outputs, "trapped_fuel", trapped[1])),
        "FMEP_fixture_value_consistency": _matches_defined(
            outputs, "FMEP", fmep_expected_pa, abs_tol=1e-9),
        "output_source_provenance_consistency": all(
            isinstance(item, Mapping) and
            isinstance(item.get("source"), str) and
            item["source"].startswith(expected_source_prefix) and
            item.get("definition_version") not in (None, "", "UNKNOWN") and
            item.get("provenance") in {"DERIVED_FROM_DOCUMENTED", "SYNTHETIC_ASSUMPTION"} and
            (item.get("status") != "DEFINED" or finite_number(item.get("value"))) and
            not (item.get("status") != "DEFINED" and item.get("value") is not None)
            for item in outputs.values()),
    }
    # Tie published fuel values to the primary ledgers independently of their
    # metadata, then verify the same-base availability closure.
    checks["fuel_available_primary_ledger_consistency"] = _matches_defined(
        outputs, "fuel_available", available)
    checks["fuel_burned_primary_ledger_consistency"] = _matches_defined(
        outputs, "fuel_burned", burned)
    expected_unburned = (float(available) - float(burned)
                         if finite_number(available) and finite_number(burned) else None)
    checks["fuel_unburned_primary_closure_consistency"] = _matches_defined(
        outputs, "fuel_unburned", expected_unburned)
    air = observables.get("fresh_air_intake_delivery_kg")
    afr = (float(air) / float(metered_fuel)
           if finite_number(air) and finite_number(metered_fuel) and metered_fuel > 0
           else None)
    checks["AFR_primary_metering_consistency"] = _matches_defined(outputs, "AFR", afr)
    stoich = outputs.get("stoichiometric_AFR", {}).get("value")
    lam = afr / float(stoich) if afr is not None and finite_number(stoich) and stoich > 0 else None
    phi = 1.0 / lam if lam is not None and lam > 0 else None
    checks["lambda_primary_metering_consistency"] = _matches_defined(outputs, "lambda", lam)
    checks["phi_primary_metering_consistency"] = _matches_defined(outputs, "phi", phi)
    checks["delivered_air_primary_ledger_consistency"] = _matches_defined(
        outputs, "delivered_air", air)
    checks["delivered_fuel_primary_ledger_consistency"] = _matches_defined(
        outputs, "delivered_fuel", metered_fuel)
    if isinstance(trapped, (list, tuple)) and len(trapped) == 4:
        total = math.fsum(float(value) for value in trapped)
        checks["residual_purity_snapshot_consistency"] = _matches_defined(
            outputs, "residual_purity", float(trapped[2]) / total if total > 0 else None)
        checks["burned_purity_snapshot_consistency"] = _matches_defined(
            outputs, "burned_purity", float(trapped[3]) / total if total > 0 else None)
    else:
        checks["residual_purity_snapshot_consistency"] = False
        checks["burned_purity_snapshot_consistency"] = False
    return checks


def finite_number(value: Any) -> bool:
    return type(value) in (int, float) and math.isfinite(float(value))


def output_mutation_audit(primary: Mapping[str, Any], outputs: Mapping[str, Any], *,
                          rpm: float, displacement_m3: float,
                          fmep_expected_pa: float | None,
                          expected_source_prefix: str) -> dict[str, Any]:
    """Exercise numeric and metadata gates with isolated, metadata-preserving edits."""
    import copy

    cases: list[tuple[str, str, tuple[str, ...], Any]] = [
        ("IMEP_x3", "indicated_work_imep_consistency", ("IMEP",),
         lambda o: o["IMEP"].__setitem__("value", o["IMEP"]["value"] * 3)),
        ("indicated_work_x2", "cylinder_indicated_work_consistency",
         ("cylinder_indicated_work",),
         lambda o: o["cylinder_indicated_work"].__setitem__(
             "value", o["cylinder_indicated_work"]["value"] * 2)),
        ("indicated_power_and_torque_x3", "indicated_power_2t_work_rpm_consistency",
         ("indicated_power", "indicated_torque"),
         lambda o: [o[name].__setitem__("value", o[name]["value"] * 3)
                    for name in ("indicated_power", "indicated_torque")]),
        ("ISFC_x0_5", "ISFC_fuel_flow_indicated_power_consistency",
         ("ISFC",),
         lambda o: o["ISFC"].__setitem__("value", o["ISFC"]["value"] * 0.5)),
        ("brake_power_and_torque_x5", "brake_power_bmep_2t_consistency",
         ("brake_power", "brake_torque"),
         lambda o: [o[name].__setitem__("value", o[name]["value"] * 5)
                    for name in ("brake_power", "brake_torque")]),
        ("trapped_air_x2", "trapped_air_snapshot_consistency", ("trapped_air",),
         lambda o: o["trapped_air"].__setitem__("value", o["trapped_air"]["value"] * 2)),
        ("incorrect_FMEP", "FMEP_fixture_value_consistency", ("FMEP",),
         lambda o: o["FMEP"].__setitem__("value", 85000.0)),
        ("incorrect_AFR", "AFR_primary_metering_consistency", ("AFR",),
         lambda o: o["AFR"].__setitem__("value", o["AFR"]["value"] * 1.1)),
        ("fuel_accounting_corrupt", "fuel_unburned_primary_closure_consistency",
         ("fuel_unburned",),
         lambda o: o["fuel_unburned"].__setitem__(
             "value", o["fuel_unburned"]["value"] + 1e-6)),
        ("false_fallback_metadata", "output_source_provenance_consistency", ("IMEP",),
         lambda o: o["IMEP"].__setitem__("source", "fallback: injected")),
    ]
    rows = []
    for name, gate, requires_defined, mutate in cases:
        mutated = copy.deepcopy(outputs)
        if any(mutated.get(key, {}).get("status") != "DEFINED" or
               not finite_number(mutated.get(key, {}).get("value"))
               for key in requires_defined):
            rows.append({"mutation": name, "gate": gate,
                         "metadata_preserved": name != "false_fallback_metadata",
                         "applicable": False, "detected": None})
            continue
        mutate(mutated)
        checks = engineering_output_consistency(
            primary, mutated, rpm=rpm, displacement_m3=displacement_m3,
            fmep_expected_pa=fmep_expected_pa,
            expected_source_prefix=expected_source_prefix)
        rows.append({"mutation": name, "gate": gate,
                     "metadata_preserved": name != "false_fallback_metadata",
                     "applicable": True, "detected": checks.get(gate) is False})
    if outputs.get("BSFC", {}).get("status") == "DEFINED":
        mutated = copy.deepcopy(outputs)
        mutated["BSFC"]["value"] *= 0.5
        checks = engineering_output_consistency(
            primary, mutated, rpm=rpm, displacement_m3=displacement_m3,
            fmep_expected_pa=fmep_expected_pa,
            expected_source_prefix=expected_source_prefix)
        rows.append({"mutation": "BSFC_x0_5", "gate": "BSFC_fuel_flow_brake_power_consistency",
                     "metadata_preserved": True,
                     "applicable": True,
                     "detected": checks["BSFC_fuel_flow_brake_power_consistency"] is False})
    corrupted_primary = copy.deepcopy(primary)
    corrupted_primary["cycle_ledgers"]["external_species_kg"][0] += 1e-6
    rows.append({"mutation": "partition_ledger_corrupt",
                 "gate": "partition_conservation_independent",
                 "metadata_preserved": True,
                 "applicable": True,
                 "detected": not recompute_partition_conservation(corrupted_primary)["passed"]})
    return {"schema": "ENGINE_PHYSICS_V1_R2_OUTPUT_MUTATION_AUDIT_V1",
            "cases": rows, "passed": all(row["detected"] is True
                                            for row in rows if row["applicable"])}


def output_hard_checks(*, fmep_used_pa: float | None,
                       fixture_model: MechanicalLossModel | None,
                       rpm: float,
                       afr: Mapping[str, Any], air_kg: float | None,
                       metered_fuel_kg: float | None,
                       available_fuel_kg: float | None,
                       burned_fuel_kg: float | None,
                       unburned_fuel_kg: float | None,
                       fuel_snapshot_bound: bool,
                       outputs: Mapping[str, Mapping[str, Any]],
                       partition: Mapping[str, Any],
                       scavenging_identity: Mapping[str, Any],
                       expected_source_prefix: str) -> dict[str, bool]:
    loss_expected = (None if fixture_model is None else
                     math.fsum(term.value(rpm, 1.0) for term in fixture_model.terms))
    checks = {
        "fixture_mechanical_loss_consistency": (
            loss_expected is not None and fmep_used_pa is not None and
            math.isclose(fmep_used_pa, loss_expected, rel_tol=0.0, abs_tol=1e-9)),
        "metering_afr_consistency": (
            air_kg is not None and metered_fuel_kg is not None and metered_fuel_kg > 0 and
            afr.get("status") == "DEFINED" and
            math.isclose(float(afr.get("value")), air_kg / metered_fuel_kg,
                         rel_tol=1e-12, abs_tol=1e-12)),
        "fuel_accounting_closure": (
            None not in (available_fuel_kg, burned_fuel_kg, unburned_fuel_kg) and
            math.isclose(float(burned_fuel_kg) + float(unburned_fuel_kg),
                         float(available_fuel_kg), rel_tol=0.0,
                         abs_tol=CONSERVATION_TOLERANCE_KG)),
        "fuel_burned_le_available": (
            None not in (available_fuel_kg, burned_fuel_kg) and
            burned_fuel_kg <= available_fuel_kg + CONSERVATION_TOLERANCE_KG),
        "fuel_property_source_consistency": fuel_snapshot_bound,
        "scavenging_metric_dependency_validity": all(
            outputs.get(name, {}).get("status") == "UNDEFINED" and
            outputs.get(name, {}).get("reason") == "CURRENT_CYCLE_FRESH_RETENTION_NOT_IDENTIFIABLE"
            for name in ("TE", "CE", "SE")),
        "scavenging_metric_identity": scavenging_identity.get("status") == "NOT_APPLICABLE" or
            scavenging_identity.get("passed") is True,
        "partition_conservation_independent": partition.get("passed") is True,
        "no_placeholders": all(
            isinstance(item.get("source"), str) and
            item["source"].startswith(expected_source_prefix) and
            item.get("definition_version") not in (None, "", "UNKNOWN") and
            (item.get("status") != "DEFINED" or
             (type(item.get("value")) in (int, float) and math.isfinite(item["value"]))) and
            not (item.get("status") == "UNDEFINED" and item.get("value") is not None)
            and item.get("provenance") in {"DERIVED_FROM_DOCUMENTED", "SYNTHETIC_ASSUMPTION"}
            and "fallback" not in str(item.get("source", "")).lower()
            and "placeholder" not in str(item.get("source", "")).lower()
            for item in outputs.values()),
    }
    checks["no_placeholders"] = checks["no_placeholders"] and all((
        token in str(outputs.get("AFR", {}).get("source", "")) for token in (
            "air_ledger:observables.fresh_air_intake_delivery_kg",
            "fuel_ledger:observables.fuel_delivered_kg")))
    checks["no_placeholders"] = checks["no_placeholders"] and all((
        token in str(outputs.get("FMEP", {}).get("source", "")) for token in (
            "fixture:", "fixture_sha256:", "model:MECHANICAL_LOSS_MODEL_V1")))
    checks["no_placeholders"] = checks["no_placeholders"] and all((
        token in str(outputs.get("stoichiometric_AFR", {}).get("source", "")) for token in (
            "fuel_snapshot_sha256:", "ELEMENTAL_MASS_BALANCE_DRY_AIR_V1")))
    return checks
