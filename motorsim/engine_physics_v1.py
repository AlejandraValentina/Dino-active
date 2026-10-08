"""Versioned engineering physics contracts for the post-R2 production phase.

This module is deliberately additive.  It provides auditable model inputs and
derived quantities for ``IntegratedEngine2T`` outputs without changing any
historical P0-P8 or closure evidence contract.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
from typing import Any, Mapping

from .fuel_combustion import FuelCoupledCombustionV2
from .fuel_library import FuelDefinition, FuelSimulationSnapshot, FuelSource
from .mechanical import MechanicalLossModel


SCHEMA = "ENGINE_PHYSICS_V1"
PROVENANCE = {"DOCUMENTED", "DERIVED_FROM_DOCUMENTED", "SYNTHETIC_ASSUMPTION"}


def _finite(value: Any, name: str, *, nonnegative: bool = False) -> float:
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError(f"{name} must be finite numeric data")
    result = float(value)
    if nonnegative and result < 0.0:
        raise ValueError(f"{name} must be nonnegative")
    return result


def _ratio(numerator: float, denominator: float, reason: str = "ZERO_DENOMINATOR") -> dict[str, Any]:
    if denominator == 0.0:
        return {"value": None, "status": "UNDEFINED", "reason": reason}
    value = numerator / denominator
    if not math.isfinite(value):
        return {"value": None, "status": "UNDEFINED", "reason": "NONFINITE_RESULT"}
    return {"value": value, "status": "DEFINED", "reason": None}


def _hash(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"),
                         ensure_ascii=False, allow_nan=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True)
class PortDischargeCoefficientsV1:
    """Explicit per-port and flow-sense Cd values."""

    values: Mapping[str, Mapping[str, float]]
    provenance: str = "SYNTHETIC_ASSUMPTION"
    version: str = "STANDARD_V1"

    def validate(self) -> None:
        if self.version != "STANDARD_V1" or self.provenance not in PROVENANCE:
            raise ValueError("port coefficient identity/provenance is invalid")
        if not self.values:
            raise ValueError("at least one port coefficient is required")
        for port, senses in self.values.items():
            if not isinstance(port, str) or not port.strip() or not isinstance(senses, Mapping):
                raise ValueError("port coefficients require named port mappings")
            if set(senses) != {"forward", "reverse"}:
                raise ValueError("each port requires forward and reverse Cd")
            for sense, value in senses.items():
                if _finite(value, f"{port}.{sense}") <= 0.0 or value > 1.0:
                    raise ValueError("STANDARD_V1 Cd must be in (0,1]")

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return {"schema": "PORT_DISCHARGE_COEFFICIENTS_STANDARD_V1",
                "version": self.version, "provenance": self.provenance,
                "values": {key: dict(value) for key, value in sorted(self.values.items())},
                "sha256": _hash({"version": self.version, "provenance": self.provenance,
                                  "values": {key: dict(value) for key, value in sorted(self.values.items())}})}


@dataclass(frozen=True)
class IdealFuelMeteringV1:
    target_phi: float = 1.0
    air_kg_per_cycle: float = 1.0
    provenance: str = "SYNTHETIC_ASSUMPTION"
    model: str = "IDEAL_FUEL_METERING"

    def evaluate(self, fuel: FuelSimulationSnapshot) -> dict[str, Any]:
        if self.provenance not in PROVENANCE or self.model != "IDEAL_FUEL_METERING":
            raise ValueError("fuel metering identity/provenance is invalid")
        phi = _finite(self.target_phi, "target_phi")
        air = _finite(self.air_kg_per_cycle, "air_kg_per_cycle", nonnegative=True)
        if phi < 0.0:
            raise ValueError("target phi cannot be negative")
        definition = fuel.validate()
        afr = definition.effective_stoichiometric_afr
        if afr is None:
            raise ValueError("fuel snapshot lacks stoichiometric AFR")
        fuel_mass = 0.0 if phi == 0.0 else air * phi / afr
        return {"schema": "IDEAL_FUEL_METERING_V1", "model": self.model,
                "target_phi": phi, "target_afr": _ratio(afr, phi, "ZERO_PHI"),
                "air_kg_per_cycle": air, "fuel_kg_per_cycle": fuel_mass,
                "fuel_snapshot_sha256": fuel.content_hash,
                "provenance": self.provenance}


def synthetic_gasoline_v1() -> FuelSimulationSnapshot:
    """Return the immutable synthetic gasoline surrogate used by this phase."""
    definition = FuelDefinition(
        id="SYNTHETIC_GASOLINE_V1", version="1.0.0",
        display_name="MotorSim synthetic gasoline engineering surrogate",
        family_category="SYNTHETIC_ENGINEERING_SURROGATE",
        provenance="MODELED_SURROGATE", builtin=False, enabled=True,
        density_kg_m3=720.0, lower_heating_value_j_kg=43_000_000.0,
        stoichiometry_method_version="ELEMENTAL_MASS_BALANCE_DRY_AIR_V1",
        elemental_mass_fractions={"C": 0.86, "H": 0.14, "O": 0.0},
        oxygen_fraction=0.0, oxygen_fraction_basis="MASS_FRACTION",
        reference_temperature_K=293.15,
        sources=(FuelSource("MotorSim versioned synthetic assumption", 
                            "https://example.invalid/motorsim/synthetic-gasoline-v1",
                            "2026-10-07", "Frozen engineering surrogate parameters."),),
        note="Synthetic engineering surrogate; not ANCAP, commercial fuel, or experimental validation.")
    definition.validate()
    return FuelSimulationSnapshot.freeze(definition)


@dataclass(frozen=True)
class ScavengingModelV1:
    version: str = "SCAVENGING_MODEL_V1"
    zone_profile: str = "TWO_ZONE_PROFILE"
    provenance: str = "SYNTHETIC_ASSUMPTION"

    def evaluate(self, *, reference_air_kg: float, fresh_delivered_kg: float,
                 fresh_short_circuit_kg: float, trapped_fresh_air_kg: float,
                 trapped_residual_kg: float, trapped_fuel_kg: float,
                 trapped_burned_kg: float = 0.0,
                 port_closure_snapshots: Mapping[str, Any] | None = None) -> dict[str, Any]:
        if self.provenance not in PROVENANCE or self.zone_profile != "TWO_ZONE_PROFILE":
            raise ValueError("scavenging model identity/provenance is invalid")
        values = {name: _finite(value, name, nonnegative=True) for name, value in {
            "reference_air_kg": reference_air_kg, "fresh_delivered_kg": fresh_delivered_kg,
            "fresh_short_circuit_kg": fresh_short_circuit_kg,
            "trapped_fresh_air_kg": trapped_fresh_air_kg,
            "trapped_residual_kg": trapped_residual_kg,
            "trapped_fuel_kg": trapped_fuel_kg,
            "trapped_burned_kg": trapped_burned_kg}.items()}
        snapshot_basis = "EXPLICIT_INPUTS"
        if port_closure_snapshots is not None:
            if set(port_closure_snapshots) != {"transfer", "exhaust"}:
                raise ValueError("port closure snapshots require transfer and exhaust states")
            transfer = port_closure_snapshots["transfer"]
            exhaust = port_closure_snapshots["exhaust"]
            for name, snapshot in (("transfer", transfer), ("exhaust", exhaust)):
                if not isinstance(snapshot, Mapping) or snapshot.get("species_order") != [
                        "fresh_air", "fuel", "residual", "burned"]:
                    raise ValueError(f"{name} port closure snapshot species contract is invalid")
                species = snapshot.get("cylinder_species_kg")
                if not isinstance(species, (list, tuple)) or len(species) != 4:
                    raise ValueError(f"{name} port closure snapshot species are missing")
                for item in species:
                    _finite(item, f"{name}.species", nonnegative=True)
            transfer_species = tuple(float(item) for item in transfer["cylinder_species_kg"])
            exhaust_species = tuple(float(item) for item in exhaust["cylinder_species_kg"])
            values.update({"trapped_fresh_air_kg": exhaust_species[0],
                           "trapped_fuel_kg": exhaust_species[1],
                           "trapped_residual_kg": exhaust_species[2],
                           "trapped_burned_kg": exhaust_species[3]})
            snapshot_basis = "PORT_CLOSURE_SNAPSHOTS_EXACT_EVENT_STATES"
        retained = values["trapped_fresh_air_kg"]
        total_trapped = math.fsum(values[name] for name in (
            "trapped_fresh_air_kg", "trapped_fuel_kg", "trapped_residual_kg",
            "trapped_burned_kg"))
        ratios = {
            "delivery_ratio": _ratio(values["fresh_delivered_kg"], values["reference_air_kg"]),
            "trapping_efficiency": _ratio(retained, values["fresh_delivered_kg"]),
            "scavenging_efficiency": _ratio(retained, total_trapped),
            "charging_efficiency": _ratio(retained, values["reference_air_kg"]),
            "short_circuit_fraction": _ratio(values["fresh_short_circuit_kg"], values["fresh_delivered_kg"]),
            "residual_fraction": _ratio(values["trapped_residual_kg"], total_trapped),
            "fresh_charge_fraction": _ratio(retained, total_trapped),
        }
        for name in ("trapping_efficiency", "scavenging_efficiency", "charging_efficiency",
                     "short_circuit_fraction", "residual_fraction", "fresh_charge_fraction"):
            if ratios[name]["status"] == "DEFINED" and not 0.0 <= ratios[name]["value"] <= 1.0:
                ratios[name] = {"value": None, "status": "UNDEFINED",
                                "reason": "OUTSIDE_PHYSICAL_DOMAIN"}
        partition_residual = values["fresh_delivered_kg"] - values["fresh_short_circuit_kg"] - retained
        if partition_residual < 0.0:
            for name in ("trapping_efficiency", "short_circuit_fraction"):
                ratios[name] = {"value": None, "status": "UNDEFINED",
                                "reason": "GROSS_CROSSING_PARTITION_INVALID"}
        return {"schema": self.version, "zone_profile": self.zone_profile,
                "snapshot_basis": snapshot_basis,
                "masses_kg": values | {"trapped_total_kg": total_trapped},
                "ratios": ratios, "conservation": {
                    "delivered_partition_kg": values["fresh_short_circuit_kg"] + retained,
                    "partition_residual_kg": partition_residual,
                    "partition_identity": "fresh_delivered = fresh_short_circuit + trapped_fresh_air_at_exhaust_close",
                    "partition_tolerance_kg": 1e-12},
                "provenance": self.provenance}


@dataclass(frozen=True)
class HeatTransferModelV1:
    correlation: str = "ANNAND_V1"
    wall_surfaces: tuple[str, ...] = ("head", "piston", "liner")
    wall_temperature_K: float = 450.0
    coefficient_W_m2K: float = 250.0
    provenance: str = "SYNTHETIC_ASSUMPTION"

    def evaluate(self, *, gas_temperature_K: float, areas_m2: Mapping[str, float]) -> dict[str, Any]:
        gas = _finite(gas_temperature_K, "gas_temperature_K")
        wall = _finite(self.wall_temperature_K, "wall_temperature_K")
        coefficient = _finite(self.coefficient_W_m2K, "coefficient_W_m2K", nonnegative=True)
        if gas <= 0.0 or wall <= 0.0 or set(areas_m2) != set(self.wall_surfaces):
            raise ValueError("heat-transfer state/surface contract is invalid")
        heat = {}
        for surface, area in areas_m2.items():
            value = coefficient * _finite(area, f"{surface}.area", nonnegative=True) * (gas - wall)
            heat[surface] = value
        return {"schema": "HEAT_TRANSFER_STANDARD_V1", "correlation": self.correlation,
                "heat_rate_W_by_surface": heat, "wall_temperature_K": wall,
                "provenance": self.provenance}


@dataclass(frozen=True)
class DuctHeatTransferV1:
    friction_model: str = "REYNOLDS_FRICTION_V1"
    heat_transfer_model: str = "DUCT_WALL_NUSSELT_V1"
    provenance: str = "SYNTHETIC_ASSUMPTION"

    def evaluate(self, *, reynolds: float, hydraulic_diameter_m: float,
                 length_m: float, wall_temperature_K: float,
                 gas_temperature_K: float) -> dict[str, Any]:
        re = _finite(reynolds, "reynolds", nonnegative=True)
        diameter = _finite(hydraulic_diameter_m, "hydraulic_diameter_m")
        length = _finite(length_m, "length_m", nonnegative=True)
        wall = _finite(wall_temperature_K, "wall_temperature_K")
        gas = _finite(gas_temperature_K, "gas_temperature_K")
        if diameter <= 0.0 or wall <= 0.0 or gas <= 0.0:
            raise ValueError("duct geometry/temperature is invalid")
        friction = 0.0 if re == 0.0 else 0.3164 / re ** 0.25
        nusselt = 3.66 if re == 0.0 else 0.023 * re ** 0.8
        return {"schema": "DUCT_HEAT_TRANSFER_STANDARD_V1", "reynolds": re,
                "friction_factor": friction, "nusselt": nusselt,
                "length_m": length, "hydraulic_diameter_m": diameter,
                "wall_heat_direction": "GAS_TO_WALL" if gas >= wall else "WALL_TO_GAS",
                "provenance": self.provenance}


def standard_fmep_model_v1() -> MechanicalLossModel:
    from .mechanical import LossTerm
    # A + B*Up + C*Up^2 in Pa; coefficients are synthetic engineering inputs.
    return MechanicalLossModel(terms=(
        LossTerm("fmep_standard_v1", "piston_ring", "SYNTHETIC_ASSUMPTION",
                 operating_map=None, mep_pa=85_000.0),))


def engineering_plausibility_gates_v1(*, pressures_pa: Mapping[str, float],
                                      temperatures_K: Mapping[str, float],
                                      conservation_residuals: Mapping[str, float],
                                      metrics: Mapping[str, Any],
                                      relationships: Mapping[str, Any] | None = None) -> dict[str, Any]:
    hard = []
    warnings = []
    for name, value in pressures_pa.items():
        if not math.isfinite(value) or value <= 0.0:
            hard.append(f"PRESSURE_INVALID:{name}")
    for name, value in temperatures_K.items():
        if not math.isfinite(value) or value <= 0.0:
            hard.append(f"TEMPERATURE_INVALID:{name}")
    for name, value in conservation_residuals.items():
        if not math.isfinite(value) or abs(value) > 1e-8:
            hard.append(f"CONSERVATION_INVALID:{name}")
    for name, record in metrics.items():
        if isinstance(record, Mapping) and record.get("status") == "DEFINED":
            value = record.get("value")
            if value is not None and not 0.0 <= value <= 1.0:
                warnings.append(f"PLAUSIBILITY_WARNING:{name}=outside_[0,1]")
    relationships = relationships or {}
    for name, relationship in relationships.items():
        if not isinstance(relationship, Mapping):
            hard.append(f"DEPENDENCY_INVALID:{name}")
            continue
        status = relationship.get("status", "DEFINED")
        if status == "UNDEFINED":
            if relationship.get("required", True):
                hard.append(f"REQUIRED_OUTPUT_UNDEFINED:{name}")
            continue
        if status != "DEFINED" or relationship.get("passed") is False:
            hard.append(f"RELATIONSHIP_INVALID:{name}")
    return {"schema": "ENGINE_PLAUSIBILITY_GATES_V2",
            "classification": "HARD_PHYSICAL_INVALID" if hard else "PASS",
            "hard_failures": hard, "warnings": warnings,
            "warning_policy": "warnings require explanation and do not override physical validity"}


def phase_model_provenance(*, fuel: FuelSimulationSnapshot,
                           port_coefficients: PortDischargeCoefficientsV1,
                           combustion: FuelCoupledCombustionV2) -> dict[str, Any]:
    fuel.validate(); port_coefficients.validate(); combustion.validate()
    payload = {"module": SCHEMA, "fuel": fuel.to_dict(),
               "port_coefficients": port_coefficients.to_dict(),
               "combustion": combustion.to_dict()}
    return {"models": payload, "sha256": _hash(payload)}


def evaluate_integrated_cycle_v1(cycle: Mapping[str, Any], *, rpm: float,
                                 fuel: FuelSimulationSnapshot,
                                 mechanical_losses: MechanicalLossModel | None = None,
                                 port_coefficients: PortDischargeCoefficientsV1 | None = None) -> dict[str, Any]:
    """Build the phase engineering record from an accepted integrated primary.

    The primary is the authoritative state/ledger product of
    ``IntegratedEngine2T``.  This adapter does not infer chemistry from a
    terminal inventory: it uses the explicit cycle fuel and species ledgers.
    """
    if not isinstance(cycle, Mapping) or cycle.get("admissible") is not True:
        raise ValueError("ENGINE_PHYSICS_V1 requires an admissible integrated primary")
    fuel.validate()
    observables = cycle.get("observables")
    ledgers = cycle.get("cycle_ledgers", {})
    conservation = cycle.get("conservation")
    terminal = cycle.get("terminal_state")
    if not isinstance(observables, Mapping) or not isinstance(conservation, Mapping):
        raise ValueError("integrated primary lacks observables/conservation")
    cylinder = observables.get("chambers", {}).get("cylinder", {})
    species = observables.get("cylinder_species_kg", (0.0, 0.0, 0.0, 0.0))
    if not species or len(species) != 4:
        species = terminal.get("species", {}).get("chambers", {}).get("cylinder", (0.0, 0.0, 0.0, 0.0))
    fresh_delivered = _finite(observables.get("fresh_delivered_kg", 0.0), "fresh_delivered_kg", nonnegative=True)
    fuel_delivered = _finite(observables.get("fuel_delivered_kg", 0.0), "fuel_delivered_kg", nonnegative=True)
    fuel_burned = _ratio(ledgers.get("fuel_combustion_heat_added_J", 0.0),
                          fuel.validate().lower_heating_value_j_kg, "ZERO_LHV")
    afr = _ratio(fresh_delivered, fuel_delivered)
    phi = _ratio(fuel.validate().effective_stoichiometric_afr,
                 afr["value"] if afr["value"] is not None else 0.0, "ZERO_AFR")
    scavenging = ScavengingModelV1().evaluate(
        reference_air_kg=max(fresh_delivered, 1e-30),
        fresh_delivered_kg=fresh_delivered,
        fresh_short_circuit_kg=_finite(observables.get("fresh_short_circuit_kg", 0.0),
                                       "fresh_short_circuit_kg", nonnegative=True),
        trapped_fresh_air_kg=_finite(species[0], "trapped_fresh_air_kg", nonnegative=True),
        trapped_residual_kg=_finite(species[2], "trapped_residual_kg", nonnegative=True),
        trapped_fuel_kg=_finite(species[1], "trapped_fuel_kg", nonnegative=True))
    loss_model = mechanical_losses or standard_fmep_model_v1()
    displacement = _finite(cycle.get("swept_displacement_m3", 0.0), "swept_displacement_m3")
    net_work = _finite(observables.get("net_piston_gas_work_J", 0.0), "net_piston_gas_work_J")
    performance = loss_model.evaluate_2t_net_piston_work(
        net_piston_gas_work_j=net_work, displacement_m3=displacement,
        rpm=_finite(rpm, "rpm"), load=1.0)
    cylinder_temperature = _finite(cylinder.get("temperature_K", 300.0), "cylinder_temperature_K")
    heat = HeatTransferModelV1().evaluate(
        gas_temperature_K=cylinder_temperature,
        areas_m2={"head": 0.01, "piston": 0.01, "liner": 0.02})
    gates = engineering_plausibility_gates_v1(
        pressures_pa={"cylinder": _finite(cylinder.get("pressure_Pa", 0.0), "cylinder_pressure_Pa")},
        temperatures_K={"cylinder": cylinder_temperature},
        conservation_residuals={
            "mass": _finite(conservation.get("mass_residual_kg", 0.0), "mass_residual_kg"),
            "energy": _finite(conservation.get("energy_residual_J", 0.0), "energy_residual_J")},
        metrics=scavenging["ratios"])
    if performance["brake_power_w"] <= 0.0:
        gates["warnings"].append(
            "PLAUSIBILITY_WARNING:nonpositive_brake_power indicates a motoring/low-load synthetic point")
    if net_work <= 0.0:
        gates["warnings"].append(
            "PLAUSIBILITY_WARNING:nonpositive_net_piston_work indicates a motoring/low-load synthetic point")
    return {"schema": "ENGINEERING_OUTPUTS_ENGINE_PHYSICS_V1",
            "cycle_index": cycle.get("cycle_index"), "rpm": float(rpm),
            "periodicity": cycle.get("periodicity", {"status": "NOT_EVALUATED"}),
            "hard_gate": gates, "fuel": {
                "fuel_id": fuel.fuel_id, "fuel_sha256": fuel.content_hash,
                "fuel_delivered_kg_per_cycle": fuel_delivered,
                "fuel_burned_kg_per_cycle": fuel_burned["value"],
                "fuel_burned_status": fuel_burned["status"],
                "fresh_air_delivered_kg_per_cycle": fresh_delivered,
                "afr": afr, "phi": phi},
            "scavenging": scavenging, "heat_transfer": heat,
            "performance": performance,
            "conservation": dict(conservation),
            "model_versions": {"port_cd": "STANDARD_V1", "scavenging": "SCAVENGING_MODEL_V1",
                                "fuel_metering": "IDEAL_FUEL_METERING", "heat_transfer": "ANNAND_V1",
                                "duct_heat_transfer": "DUCT_HEAT_TRANSFER_STANDARD_V1",
                                "mechanical_losses": "MECHANICAL_LOSSES_STANDARD_V1"},
            "provenance": "SYNTHETIC_ASSUMPTION"}


def _defined(value: Any, *, units: str | None = None, reason: str | None = None) -> dict[str, Any]:
    if value is None:
        return {"value": None, "status": "UNDEFINED", "reason": reason or "MISSING_DEPENDENCY",
                "units": units}
    number = _finite(value, "output")
    return {"value": number, "status": "DEFINED", "reason": None, "units": units}


def _undefined(reason: str, *, units: str | None = None) -> dict[str, Any]:
    return {"value": None, "status": "UNDEFINED", "reason": reason, "units": units}


def evaluate_integrated_cycle_v2(cycle: Mapping[str, Any], *, rpm: float,
                                 fuel: FuelSimulationSnapshot,
                                 periodicity_status: str,
                                 mechanical_losses: MechanicalLossModel | None = None) -> dict[str, Any]:
    """Contract-correct output adapter used by recovery and future campaigns.

    Missing physical dependencies stay undefined.  Regime outputs are marked
    unusable until PeriodicDetectorV2 accepts the operating point.
    """
    if not isinstance(cycle, Mapping) or cycle.get("admissible") is not True:
        raise ValueError("ENGINE_PHYSICS_V2 requires an admissible integrated primary")
    fuel_definition = fuel.validate()
    observables = cycle.get("observables")
    ledgers = cycle.get("cycle_ledgers")
    conservation = cycle.get("conservation")
    if not isinstance(observables, Mapping) or not isinstance(ledgers, Mapping) or not isinstance(conservation, Mapping):
        raise ValueError("integrated primary lacks required physical ledgers")
    fuel_obs = observables.get("fuel_coupled_combustion")
    snapshots = cycle.get("port_closure_snapshots")
    if isinstance(snapshots, Mapping) and isinstance(snapshots.get("snapshots"), Mapping):
        snapshots = snapshots["snapshots"]
    fresh_delivery = observables.get("fresh_delivery_kg")
    fresh_short = observables.get("fresh_short_circuit_kg")
    fuel_delivered = observables.get("fuel_delivered_kg")
    fuel_burned = fuel_obs.get("fuel_burned_kg") if isinstance(fuel_obs, Mapping) else None
    heat_released = ledgers.get("fuel_combustion_heat_added_J")
    lhv = fuel_definition.lower_heating_value_j_kg
    efficiency = (fuel_obs.get("energy_per_burned_fuel_j_kg") / lhv
                  if isinstance(fuel_obs, Mapping) and lhv and
                  fuel_obs.get("energy_per_burned_fuel_j_kg") is not None else None)
    energy_expected = (fuel_burned * lhv * efficiency
                       if fuel_burned is not None and efficiency is not None else None)
    energy_error = (None if energy_expected is None or heat_released is None
                    else float(heat_released) - float(energy_expected))
    heat_rel = {"status": "DEFINED" if energy_error is not None else "UNDEFINED",
                "passed": (energy_error is not None and
                           abs(energy_error) <= max(1e-10, abs(float(energy_expected)) * 1e-8)),
                "required": True}
    if fresh_delivery is None or fresh_short is None or not isinstance(snapshots, Mapping):
        scavenging = {"schema": "SCAVENGING_MODEL_V1", "snapshot_basis": "UNDEFINED",
                      "ratios": {name: _undefined("MISSING_PORT_CLOSURE_OR_DELIVERY_DEPENDENCY")
                                 for name in ("delivery_ratio", "trapping_efficiency",
                                              "scavenging_efficiency", "charging_efficiency",
                                              "short_circuit_fraction", "residual_fraction",
                                              "fresh_charge_fraction")},
                      "masses_kg": {}, "conservation": {
                          "partition_residual_kg": None,
                          "partition_identity": "UNDEFINED",
                          "partition_tolerance_kg": 1e-12}}
        partition_rel = {"status": "UNDEFINED", "passed": False, "required": True}
    else:
        transfer_snapshot = snapshots.get("transfer")
        reference = (transfer_snapshot.get("cylinder_total_mass_kg")
                     if isinstance(transfer_snapshot, Mapping) else None)
        try:
            scavenging = ScavengingModelV1().evaluate(
                reference_air_kg=reference,
                fresh_delivered_kg=fresh_delivery,
                fresh_short_circuit_kg=fresh_short,
                trapped_fresh_air_kg=0.0, trapped_residual_kg=0.0,
                trapped_fuel_kg=0.0, trapped_burned_kg=0.0,
                port_closure_snapshots=snapshots)
            residual = scavenging["conservation"]["partition_residual_kg"]
            partition_rel = {"status": "DEFINED", "passed": abs(residual) <= 1e-12,
                             "required": True}
        except (TypeError, ValueError):
            scavenging = {"schema": "SCAVENGING_MODEL_V1", "snapshot_basis": "UNDEFINED",
                          "ratios": {name: _undefined("INVALID_PORT_CLOSURE_SNAPSHOT")
                                     for name in ("delivery_ratio", "trapping_efficiency",
                                                  "scavenging_efficiency", "charging_efficiency",
                                                  "short_circuit_fraction", "residual_fraction",
                                                  "fresh_charge_fraction")},
                          "masses_kg": {}, "conservation": {
                              "partition_residual_kg": None,
                              "partition_identity": "UNDEFINED",
                              "partition_tolerance_kg": 1e-12}}
            partition_rel = {"status": "UNDEFINED", "passed": False, "required": True}
    cylinder = observables.get("chambers", {}).get("cylinder", {})
    displacement = cycle.get("swept_displacement_m3")
    cylinder_work = observables.get("cylinder_indicated_work_J")
    crankcase_work = observables.get("crankcase_gas_work_J")
    net_work = observables.get("net_piston_gas_work_J")
    performance = None
    if displacement is not None and net_work is not None:
        performance = (mechanical_losses or standard_fmep_model_v1()).evaluate_2t_net_piston_work(
            net_piston_gas_work_j=net_work, displacement_m3=displacement, rpm=rpm, load=1.0)
    freq = float(rpm) / 60.0
    indicated_power = None if cylinder_work is None else float(cylinder_work) * freq
    brake_power = None if performance is None else performance["brake_power_w"]
    regime_ok = periodicity_status in {"PERIOD_1", "PERIOD_2"}
    regime_status = "PERIODIC_ENGINEERING_RESULT" if regime_ok else "TRANSIENT_DIAGNOSTIC"
    usability = "USABLE" if regime_ok else "NOT_USABLE_UNTIL_PERIODIC"
    afr = _ratio(float(fresh_delivery), float(fuel_delivered), "MISSING_OR_ZERO_FUEL") \
        if fresh_delivery is not None and fuel_delivered is not None and fuel_delivered != 0 else \
        _undefined("ZERO_FUEL_OR_MISSING_AIR", units="kg/kg")
    stoich = fuel_definition.effective_stoichiometric_afr
    phi = (_ratio(stoich, afr["value"], "ZERO_AFR") if afr["status"] == "DEFINED" else
           _undefined("AFR_UNDEFINED", units="1"))
    trapped = snapshots.get("exhaust") if isinstance(snapshots, Mapping) else None
    trapped_species = trapped.get("cylinder_species_kg") if isinstance(trapped, Mapping) else None
    trapped_afr = (_ratio(trapped_species[0], trapped_species[1], "ZERO_TRAPPED_FUEL")
                   if isinstance(trapped_species, (list, tuple)) and len(trapped_species) == 4 and trapped_species[1] != 0
                   else _undefined("TRAPPED_FUEL_ZERO_OR_SNAPSHOT_MISSING", units="kg/kg"))
    lambda_value = (_ratio(afr["value"], stoich, "ZERO_STOICH_AFR")
                    if afr["status"] == "DEFINED" else _undefined("AFR_UNDEFINED", units="1"))
    exhaust_rows = observables.get("ducts", {}).get("exhaust", [])
    exhaust_temp = (_defined(exhaust_rows[-1].get("temperature_K"), units="K")
                    if exhaust_rows and isinstance(exhaust_rows[-1], Mapping)
                    else _undefined("EXHAUST_TEMPERATURE_MISSING", units="K"))
    outputs = {
        "cylinder_indicated_work": _defined(cylinder_work, units="J"),
        "cylinder_IMEP": _defined(None if cylinder_work is None or displacement is None else float(cylinder_work) / float(displacement), units="Pa"),
        "crankcase_gas_work": _defined(crankcase_work, units="J"),
        "net_piston_gas_work": _defined(net_work, units="J"),
        "FMEP": _defined(None if performance is None else performance["friction_mep_pa"], units="Pa"),
        "BMEP": _defined(None if performance is None else performance["brake_mep_pa"], units="Pa"),
        "indicated_power": _defined(indicated_power, units="W"),
        "indicated_torque": _defined(None if cylinder_work is None else float(cylinder_work) / (2 * math.pi), units="N m"),
        "brake_power": _defined(brake_power, units="W"),
        "brake_torque": _defined(None if performance is None else performance["brake_torque_nm"], units="N m"),
        "ISFC": _defined(None if fuel_delivered is None or indicated_power is None or indicated_power <= 0 else float(fuel_delivered) * freq * 3.6e9 / indicated_power, units="g/kWh"),
        "BSFC": _defined(None if fuel_delivered is None or brake_power is None or brake_power <= 0 else float(fuel_delivered) * freq * 3.6e9 / brake_power, units="g/kWh"),
        "exhaust_gas_temperature": exhaust_temp,
        "trapped_AFR": trapped_afr,
        "AFR": afr,
        "lambda": lambda_value,
        "phi": phi,
        "fuel_delivered": _defined(fuel_delivered, units="kg/cycle"),
        "fuel_trapped": _defined(None if not isinstance(trapped_species, (list, tuple)) else trapped_species[1], units="kg/cycle"),
        "fuel_burned": _defined(fuel_burned, units="kg/cycle"),
        "fuel_unburned": _defined(None if not isinstance(fuel_obs, Mapping) else fuel_obs.get("unburned_fuel_at_exhaust_close_kg"), units="kg/cycle"),
        "heat_released": _defined(heat_released, units="J/cycle"),
        "DR": scavenging["ratios"].get("delivery_ratio", _undefined("MISSING_SCAVENGING_METRIC")),
        "TE": scavenging["ratios"].get("trapping_efficiency", _undefined("MISSING_SCAVENGING_METRIC")),
        "SE": scavenging["ratios"].get("scavenging_efficiency", _undefined("MISSING_SCAVENGING_METRIC")),
        "CE": scavenging["ratios"].get("charging_efficiency", _undefined("MISSING_SCAVENGING_METRIC")),
        "residual_fraction": scavenging["ratios"].get("residual_fraction", _undefined("MISSING_SCAVENGING_METRIC")),
        "short_circuit_fraction": scavenging["ratios"].get("short_circuit_fraction", _undefined("MISSING_SCAVENGING_METRIC")),
    }
    for value in outputs.values():
        value["regime_status"] = usability
    relationships = {"partition_conservation": partition_rel,
                     "fuel_energy_identity": heat_rel}
    if fresh_delivery is None or fuel_delivered is None:
        relationships["air_fuel_ratio_dependency"] = {
            "status": "UNDEFINED", "passed": False, "required": True}
    elif fuel_delivered == 0.0:
        relationships["air_fuel_ratio_dependency"] = {
            "status": "UNDEFINED", "passed": False, "required": True}
    else:
        relationships["air_fuel_ratio_dependency"] = {
            "status": "DEFINED", "passed": math.isfinite(float(fresh_delivery)) and
            math.isfinite(float(fuel_delivered)) and float(fresh_delivery) >= 0.0,
            "required": True}
    if fuel_burned is None:
        relationships["primary_fuel_burned_dependency"] = {
            "status": "UNDEFINED", "passed": False, "required": True}
    else:
        relationships["primary_fuel_burned_dependency"] = {
            "status": "DEFINED", "passed": math.isfinite(float(fuel_burned)) and
            float(fuel_burned) >= 0.0, "required": True}
    if fuel_delivered is not None and fuel_burned is not None:
        relationships["fuel_availability"] = {
            "status": "DEFINED", "passed": float(fuel_burned) <= float(fuel_delivered) + 1e-15,
            "required": True}
    gates = engineering_plausibility_gates_v1(
        pressures_pa={"cylinder": cylinder.get("pressure_Pa")} if cylinder.get("pressure_Pa") is not None else {},
        temperatures_K={"cylinder": cylinder.get("temperature_K")} if cylinder.get("temperature_K") is not None else {},
        conservation_residuals={key: value for key, value in {
            "mass": conservation.get("mass_residual_kg"),
            "energy": conservation.get("energy_residual_J")}.items() if value is not None},
        metrics={key: outputs[key] for key in ("DR", "TE", "SE", "CE", "residual_fraction", "short_circuit_fraction")},
        relationships=relationships)
    if fuel_delivered is not None and fuel_burned is not None and fuel_burned > fuel_delivered + 1e-15:
        gates["hard_failures"].append("FUEL_BURNED_EXCEEDS_FUEL_DELIVERED")
    if gates["hard_failures"]:
        gates["classification"] = "HARD_PHYSICAL_INVALID"
    return {"schema": "ENGINEERING_OUTPUTS_ENGINE_PHYSICS_V2",
            "cycle_index": cycle.get("cycle_index"), "rpm": float(rpm),
            "operating_point_status": regime_status,
            "periodicity": {"status": periodicity_status},
            "outputs": outputs, "scavenging": scavenging,
            "fuel": {"fuel_sha256": fuel.content_hash, "stoichiometric_afr": stoich,
                      "combustion_efficiency": efficiency,
                      "energy_identity_error_J": energy_error},
            "hard_gate": gates, "conservation": dict(conservation),
            "provenance": "SYNTHETIC_ASSUMPTION"}
