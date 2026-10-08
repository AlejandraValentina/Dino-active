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
