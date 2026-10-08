"""Versioned post-processing for gross-crossing scavenging accounting.

This module deliberately does not change ``IntegratedEngine2T``.  It binds
existing primary ledgers, inventories and exact closure snapshots and audits
their species conservation semantics.
"""
from __future__ import annotations

import math
from typing import Any, Mapping

from .scavenging import ScavengingInput, calculate_scavenging_metrics_v2


SCHEMA = "SCAVENGING_PARTITION_CONSERVATION_V1"
SPECIES = ("fresh_air", "fuel", "residual", "burned")
TOLERANCE_KG = 1e-12


def _number(value: Any, name: str, *, nonnegative: bool = False) -> float:
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError(f"{name} must be finite numeric data")
    value = float(value)
    if nonnegative and value < 0.0:
        raise ValueError(f"{name} must be nonnegative")
    return value


def _species(value: Any, name: str, *, nonnegative: bool = True) -> tuple[float, float, float, float]:
    if not isinstance(value, (list, tuple)) or len(value) != 4:
        raise ValueError(f"{name} must contain four species")
    return tuple(_number(item, f"{name}[{index}]", nonnegative=nonnegative)
                 for index, item in enumerate(value))  # type: ignore[return-value]


def evaluate_scavenging_partition_v1(cycle: Mapping[str, Any]) -> dict[str, Any]:
    """Return an auditable partition record from one accepted primary.

    Gross transfer/exhaust crossings are intentionally not forced into a
    unique-molecule partition.  Full-cycle species conservation is the
    conservation identity; closure snapshots are used only for event-bound
    composition metrics.
    """
    if not isinstance(cycle, Mapping) or cycle.get("admissible") is not True:
        raise ValueError("an admissible integrated primary is required")
    observables = cycle.get("observables")
    ledgers = cycle.get("cycle_ledgers")
    conservation = cycle.get("conservation")
    closures = cycle.get("port_closure_snapshots")
    if not all(isinstance(item, Mapping) for item in (observables, ledgers, conservation, closures)):
        raise ValueError("primary lacks partition conservation inputs")
    snapshots = closures.get("snapshots")
    if closures.get("status") != "EXACT_EVENT_STATES_CAPTURED" or not isinstance(snapshots, Mapping):
        raise ValueError("exact port closure snapshots are required")
    if set(snapshots) != {"transfer", "exhaust"}:
        raise ValueError("transfer and exhaust snapshots are required")
    event_species: dict[str, dict[str, Any]] = {}
    for role in ("transfer", "exhaust"):
        snapshot = snapshots[role]
        if not isinstance(snapshot, Mapping) or list(snapshot.get("species_order", [])) != list(SPECIES):
            raise ValueError(f"{role} snapshot species order is invalid")
        values = _species(snapshot.get("cylinder_species_kg"), f"{role}.cylinder_species_kg")
        event_species[role] = {
            "angle_deg": _number(snapshot.get("angle_deg"), f"{role}.angle_deg"),
            "species_order": list(SPECIES),
            "species_kg": dict(zip(SPECIES, values)),
            "state_source": snapshot.get("state_source"),
        }
    fresh_delivery = _number(observables.get("fresh_delivery_kg"), "fresh_delivery_kg", nonnegative=True)
    fresh_short = _number(observables.get("fresh_short_circuit_kg"), "fresh_short_circuit_kg", nonnegative=True)
    external_species = _species(ledgers.get("external_species_kg"), "external_species_kg", nonnegative=False)
    internal_species = _species(ledgers.get("fuel_combustion_source_species_kg"),
                                "fuel_combustion_source_species_kg", nonnegative=False)
    species_residual = _species(conservation.get("species_residual_kg"), "species_residual_kg", nonnegative=False)
    max_residual = max(abs(value) for value in species_residual)
    transfer_values = tuple(event_species["transfer"]["species_kg"][name] for name in SPECIES)
    exhaust_values = tuple(event_species["exhaust"]["species_kg"][name] for name in SPECIES)
    reference = _number(snapshots["transfer"].get("cylinder_total_mass_kg"),
                        "transfer.cylinder_total_mass_kg", nonnegative=True)
    metrics = calculate_scavenging_metrics_v2(ScavengingInput(
        reference_mass_kg=reference,
        fresh_delivered_kg=fresh_delivery,
        fresh_short_circuit_kg=fresh_short,
        species_at_transfer_close_kg=transfer_values,
        species_at_exhaust_close_kg=exhaust_values))
    gross_partition = {
        "status": "NOT_APPLICABLE",
        "passed": None,
        "reason": "GROSS_CROSSING_LEDGERS_ARE_NOT_UNIQUE_MASS_PARTITIONS",
        "equation": "gross fresh crossing != unique retained + unique short-circuit parcel",
    }
    species_closure = {
        "status": "DEFINED",
        "passed": max_residual <= TOLERANCE_KG,
        "residual_kg_by_species": dict(zip(SPECIES, species_residual)),
        "max_abs_residual_kg": max_residual,
        "tolerance_kg": TOLERANCE_KG,
        "equation": "terminal_inventory = initial_inventory + external_species_exchange + internal_species_sources + residual",
        "external_species_kg": dict(zip(SPECIES, external_species)),
        "internal_species_sources_kg": dict(zip(SPECIES, internal_species)),
    }
    hard_failures = [] if species_closure["passed"] else ["SPECIES_CONSERVATION_INVALID"]
    return {
        "schema": SCHEMA,
        "cycle_index": cycle.get("cycle_index"),
        "configuration_hash": cycle.get("configuration_hash"),
        "classification": "PASS" if not hard_failures else "HARD_PHYSICAL_INVALID",
        "cause_classification": ["SEMANTIC_DEFINITION_BUG", "ACCOUNTING_BUG"],
        "gross_crossing_ledgers_kg": {
            "fresh_delivered": fresh_delivery,
            "fresh_short_circuit": fresh_short,
            "fuel_delivered": _number(observables.get("fuel_delivered_kg"), "fuel_delivered_kg", nonnegative=True),
            "fuel_short_circuit": _number(observables.get("fuel_short_circuited_kg"), "fuel_short_circuited_kg", nonnegative=True),
        },
        "event_snapshots": event_species,
        "species_closure": species_closure,
        "gross_partition": gross_partition,
        "metrics": metrics,
        "hard_gate": {"classification": "PASS" if not hard_failures else "HARD_PHYSICAL_INVALID",
                      "hard_failures": hard_failures,
                      "policy": "gross partition not applicable; species closure required; no clipping"},
        "physics_changed": False,
        "provenance": "DERIVED_FROM_DOCUMENTED",
    }
