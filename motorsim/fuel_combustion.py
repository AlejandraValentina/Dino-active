"""Explicit synthetic fuel and fuel/oxygen-limited 2T combustion V1.

This module defines a synthetic surrogate, not a real or calibrated fuel. Its
combustion source is additive to the historical prescribed P7 capability.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
from typing import Any

from .combustion import WiebeComponent
from .fuel_library import FuelSimulationSnapshot
from .p6_species import validate_species


def _finite(value: Any, name: str) -> float:
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError(f"{name} must be finite numeric data")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{name} is outside supported range")
    return result


@dataclass(frozen=True)
class SyntheticFuelSurrogateV1:
    """Frozen elemental mass fractions and heating value for synthetic tests."""

    version: str = "1.0.0"
    carbon_mass_fraction: float = 0.86
    hydrogen_mass_fraction: float = 0.14
    oxygen_mass_fraction: float = 0.0
    air_oxygen_mass_fraction: float = 0.232
    lower_heating_value_j_kg: float = 43_000_000.0
    provenance: str = "SYNTHETIC_ASSUMPTION"

    def validate(self) -> None:
        if self.version != "1.0.0" or self.provenance != "SYNTHETIC_ASSUMPTION":
            raise ValueError("synthetic fuel identity/provenance is invalid")
        fractions = tuple(_finite(value, name) for name, value in (
            ("carbon_mass_fraction", self.carbon_mass_fraction),
            ("hydrogen_mass_fraction", self.hydrogen_mass_fraction),
            ("oxygen_mass_fraction", self.oxygen_mass_fraction)))
        if any(value < 0.0 or value > 1.0 for value in fractions) or not math.isclose(
                math.fsum(fractions), 1.0, rel_tol=0.0, abs_tol=1e-12):
            raise ValueError("fuel elemental mass fractions must sum to one")
        if not 0.0 < _finite(self.air_oxygen_mass_fraction,
                              "air_oxygen_mass_fraction") <= 1.0:
            raise ValueError("air oxygen mass fraction must be in (0,1]")
        if _finite(self.lower_heating_value_j_kg,
                   "lower_heating_value_j_kg") <= 0.0:
            raise ValueError("synthetic fuel LHV must be positive")
        oxygen_demand = ((8.0 / 3.0) * fractions[0] +
                         8.0 * fractions[1] - fractions[2])
        if not math.isfinite(oxygen_demand) or oxygen_demand <= 0.0:
            raise ValueError("fuel composition must require positive external oxygen")

    @property
    def oxygen_required_kg_per_kg_fuel(self) -> float:
        self.validate()
        # Complete oxidation demand: C + O2 -> CO2; H2 + 1/2 O2 -> H2O.
        return ((8.0 / 3.0) * self.carbon_mass_fraction +
                8.0 * self.hydrogen_mass_fraction - self.oxygen_mass_fraction)

    @property
    def stoichiometric_afr(self) -> float:
        return self.oxygen_required_kg_per_kg_fuel / self.air_oxygen_mass_fraction

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return {
            "schema": "SYNTHETIC_FUEL_SURROGATE_V1",
            "version": self.version,
            "composition_mass_fraction": {
                "C": self.carbon_mass_fraction,
                "H": self.hydrogen_mass_fraction,
                "O": self.oxygen_mass_fraction,
            },
            "fresh_air_oxygen_mass_fraction": self.air_oxygen_mass_fraction,
            "stoichiometric_afr": self.stoichiometric_afr,
            "oxygen_required_kg_per_kg_fuel": self.oxygen_required_kg_per_kg_fuel,
            "lower_heating_value_j_kg": self.lower_heating_value_j_kg,
            "provenance": self.provenance,
        }

    @property
    def sha256(self) -> str:
        encoded = json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"),
                             allow_nan=False).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def snapshot(self) -> dict[str, Any]:
        value = self.to_dict()
        value["sha256"] = self.sha256
        return value

    @classmethod
    def from_snapshot(cls, value: Any) -> "SyntheticFuelSurrogateV1":
        fields = {"schema", "version", "composition_mass_fraction",
                  "fresh_air_oxygen_mass_fraction", "stoichiometric_afr",
                  "oxygen_required_kg_per_kg_fuel", "lower_heating_value_j_kg",
                  "provenance", "sha256"}
        if not isinstance(value, dict) or set(value) != fields or value["schema"] != "SYNTHETIC_FUEL_SURROGATE_V1":
            raise ValueError("synthetic fuel snapshot schema is invalid")
        composition = value["composition_mass_fraction"]
        if not isinstance(composition, dict) or set(composition) != {"C", "H", "O"}:
            raise ValueError("synthetic fuel composition schema is invalid")
        result = cls(value["version"], composition["C"], composition["H"],
                     composition["O"], value["fresh_air_oxygen_mass_fraction"],
                     value["lower_heating_value_j_kg"], value["provenance"])
        if result.snapshot() != value:
            raise ValueError("synthetic fuel snapshot identity or derived value mismatch")
        return result


@dataclass(frozen=True)
class FuelCombustionEventV1:
    start_angle_deg: float
    fresh_air_at_ignition_kg: float
    fuel_at_ignition_kg: float
    fuel_available_for_burn_kg: float

    def validate(self) -> None:
        start = _finite(self.start_angle_deg, "start_angle_deg")
        if start < 0.0:
            raise ValueError("combustion event start angle must be nonnegative")
        values = tuple(_finite(value, name) for name, value in (
            ("fresh_air_at_ignition_kg", self.fresh_air_at_ignition_kg),
            ("fuel_at_ignition_kg", self.fuel_at_ignition_kg),
            ("fuel_available_for_burn_kg", self.fuel_available_for_burn_kg)))
        air, fuel, eligible = values
        if min(values) < 0.0 or eligible > fuel + 1e-15:
            raise ValueError("combustion event inventory is invalid")
        if air == 0.0 and eligible != 0.0:
            raise ValueError("combustion event cannot burn fuel without oxygen carrier")

    def to_dict(self) -> dict[str, float]:
        self.validate()
        return {"start_angle_deg": self.start_angle_deg,
                "fresh_air_at_ignition_kg": self.fresh_air_at_ignition_kg,
                "fuel_at_ignition_kg": self.fuel_at_ignition_kg,
                "fuel_available_for_burn_kg": self.fuel_available_for_burn_kg}

    @classmethod
    def from_dict(cls, value: Any) -> "FuelCombustionEventV1":
        fields = {"start_angle_deg", "fresh_air_at_ignition_kg",
                  "fuel_at_ignition_kg", "fuel_available_for_burn_kg"}
        if not isinstance(value, dict) or set(value) != fields:
            raise ValueError("fuel combustion event schema is invalid")
        result = cls(**value)
        result.validate()
        return result


@dataclass(frozen=True)
class FuelCoupledCombustionV1:
    components: tuple[WiebeComponent, ...]
    ignition_timing_deg: float
    combustion_efficiency: float
    fuel: SyntheticFuelSurrogateV1 = SyntheticFuelSurrogateV1()

    schema = "FUEL_COUPLED_COMBUSTION_V1"

    def validate(self) -> None:
        if not isinstance(self.components, tuple) or len(self.components) not in (1, 2):
            raise ValueError("FUEL_COUPLED_COMBUSTION_V1 supports one or two Wiebe components")
        for item in self.components:
            if not isinstance(item, WiebeComponent):
                raise ValueError("fuel combustion contains an invalid Wiebe component")
            item.validate()
            if (item.delay_deg < 0.0 or
                    item.delay_deg + item.duration_deg >= 360.0):
                raise ValueError("fuel combustion Wiebe window must fit within one 2T cycle")
        if not math.isclose(math.fsum(item.weight for item in self.components), 1.0,
                            rel_tol=0.0, abs_tol=1e-12):
            raise ValueError("fuel combustion Wiebe weights must sum to one")
        start = _finite(self.ignition_timing_deg, "ignition_timing_deg")
        if not 0.0 <= start < 360.0:
            raise ValueError("ignition timing must be in [0,360)")
        efficiency = _finite(self.combustion_efficiency, "combustion_efficiency")
        if not 0.0 <= efficiency <= 1.0:
            raise ValueError("combustion efficiency must be in [0,1]")
        if not isinstance(self.fuel, SyntheticFuelSurrogateV1):
            raise ValueError("fuel must be a versioned synthetic fuel surrogate")
        self.fuel.validate()

    def capture(self, start_angle_deg: float,
                cylinder_species_kg: tuple[float, float, float, float]) -> FuelCombustionEventV1:
        self.validate()
        if (not isinstance(cylinder_species_kg, (tuple, list)) or
                len(cylinder_species_kg) != 4):
            raise ValueError("cylinder species inventory must have four components")
        air, fuel, residual, burned = tuple(_finite(value, "species_mass_kg")
                                            for value in cylinder_species_kg)
        if min(air, fuel, residual, burned) < 0.0:
            raise ValueError("cylinder species inventory cannot be negative")
        oxygen_available = air * self.fuel.air_oxygen_mass_fraction
        eligible = min(fuel, oxygen_available / self.fuel.oxygen_required_kg_per_kg_fuel)
        event = FuelCombustionEventV1(float(start_angle_deg), air, fuel, eligible)
        event.validate()
        return event

    @staticmethod
    def _component_rate(component: WiebeComponent, angle_deg: float,
                        start_angle_deg: float) -> float:
        offset = angle_deg - start_angle_deg - component.delay_deg
        if offset <= 0.0 or offset >= component.duration_deg:
            return 0.0
        z = offset / component.duration_deg
        exponent = component.shape_m + 1.0
        denominator = -math.expm1(-component.shape_a)
        return (component.shape_a * exponent * z ** (exponent - 1.0) *
                math.exp(-component.shape_a * z ** exponent) /
                (component.duration_deg * denominator))

    def stage_source(self, *, event: FuelCombustionEventV1, angle_deg: float,
                     rpm: float, species_mass_kg: tuple[float, ...],
                     noncombustion_species_rhs_kg_s: tuple[float, ...],
                     dt_s: float) -> dict[str, Any]:
        """Return an SSPRK stage source limited by current fuel and oxygen.

        ``noncombustion_species_rhs_kg_s`` is the already assembled transport
        source. It is used only to ensure the explicit chemistry sink cannot
        consume reactants that the stage will not have available.
        """
        self.validate()
        event.validate()
        angle, speed, step = (_finite(angle_deg, "angle_deg"),
                              _finite(rpm, "rpm"), _finite(dt_s, "dt_s"))
        if speed <= 0.0 or step <= 0.0:
            raise ValueError("rpm and dt_s must be positive")
        if len(species_mass_kg) != 4 or len(noncombustion_species_rhs_kg_s) != 4:
            raise ValueError("combustion stage requires four species arrays")
        species = tuple(_finite(value, "species_mass_kg") for value in species_mass_kg)
        rhs = tuple(_finite(value, "species_rhs_kg_s")
                    for value in noncombustion_species_rhs_kg_s)
        # Match the integrated state validator's 1e-14 kg roundoff domain.
        # Availability below is clamped at zero, so a tolerated tiny negative
        # cannot create reactant or chemical heat.
        validate_species(species, math.fsum(species))
        derivative = math.fsum(
            item.weight * self._component_rate(item, angle, event.start_angle_deg)
            for item in self.components)
        requested = event.fuel_available_for_burn_kg * derivative * 6.0 * speed
        available_fuel_rate = max(0.0, species[1] + step * rhs[1]) / step
        oxygen_per_fuel = self.fuel.oxygen_required_kg_per_kg_fuel
        available_oxygen = max(0.0, species[0] + step * rhs[0]) * \
            self.fuel.air_oxygen_mass_fraction
        oxygen_limited_rate = available_oxygen / (oxygen_per_fuel * step)
        burned_rate = min(requested, available_fuel_rate, oxygen_limited_rate)
        air_rate = oxygen_per_fuel / self.fuel.air_oxygen_mass_fraction * burned_rate
        species_source = (-air_rate, -burned_rate, 0.0,
                          air_rate + burned_rate)
        heat_rate = (burned_rate * self.fuel.lower_heating_value_j_kg *
                     self.combustion_efficiency)
        return {"species_kg_s": species_source, "heat_w": heat_rate,
                "requested_fuel_rate_kg_s": requested,
                "burned_fuel_rate_kg_s": burned_rate,
                "oxygen_limited_fuel_rate_kg_s": oxygen_limited_rate,
                "energy_per_burned_fuel_j_kg": (
                    self.fuel.lower_heating_value_j_kg * self.combustion_efficiency)}

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return {"schema": "FUEL_COUPLED_COMBUSTION_V1",
                "components": [item.to_dict() for item in self.components],
                "ignition_timing_deg": self.ignition_timing_deg,
                "combustion_efficiency": self.combustion_efficiency,
                "fuel_snapshot": self.fuel.snapshot(),
                "fuel_sha256": self.fuel.sha256,
                "provenance": "SYNTHETIC_ASSUMPTION"}

    @classmethod
    def from_dict(cls, value: Any) -> "FuelCoupledCombustionV1":
        fields = {"schema", "components", "ignition_timing_deg",
                  "combustion_efficiency", "fuel_snapshot", "fuel_sha256",
                  "provenance"}
        if (not isinstance(value, dict) or set(value) != fields or
                value["schema"] != "FUEL_COUPLED_COMBUSTION_V1" or
                value["provenance"] != "SYNTHETIC_ASSUMPTION"):
            raise ValueError("fuel-coupled combustion configuration is invalid")
        fuel = SyntheticFuelSurrogateV1.from_snapshot(value["fuel_snapshot"])
        if value["fuel_sha256"] != fuel.sha256:
            raise ValueError("fuel-coupled combustion fuel hash mismatch")
        result = cls(tuple(WiebeComponent.from_dict(item)
                           for item in value["components"]),
                     value["ignition_timing_deg"], value["combustion_efficiency"],
                     fuel)
        result.validate()
        if result.to_dict() != value:
            raise ValueError("fuel-coupled combustion derived identity mismatch")
        return result


@dataclass(frozen=True)
class FuelCoupledCombustionV2:
    """Combustion capability bound to the reusable Fuel Library snapshot.

    The explicit efficiency remains a synthetic model input. Wiebe components
    only distribute the energy allowed by trapped fuel, oxygen, the frozen
    fuel definition's LHV, and that efficiency.
    """

    components: tuple[WiebeComponent, ...]
    ignition_timing_deg: float
    combustion_efficiency: float
    fuel_snapshot: FuelSimulationSnapshot
    combustion_efficiency_provenance: str = "SYNTHETIC_ASSUMPTION"

    schema = "FUEL_COUPLED_COMBUSTION_V2"

    @property
    def fuel(self):
        return self.fuel_snapshot.validate()

    @property
    def fuel_sha256(self) -> str:
        self.fuel_snapshot.validate()
        return self.fuel_snapshot.content_hash

    @property
    def stoichiometric_afr(self) -> float:
        value = self.fuel.effective_stoichiometric_afr
        if value is None:
            raise ValueError("fuel definition lacks combustion stoichiometry")
        return value

    def validate(self) -> None:
        if not isinstance(self.fuel_snapshot, FuelSimulationSnapshot):
            raise ValueError("fuel V2 requires an immutable Fuel Library snapshot")
        definition = self.fuel_snapshot.validate()
        if definition.provenance not in {"DOCUMENTED", "DERIVED_FROM_DOCUMENTED",
                                         "MODELED_SURROGATE",
                                         "USER_DEFINED_UNVERIFIED"}:
            raise ValueError("fuel V2 snapshot provenance is not usable")
        missing = definition.missing_combustion_properties()
        if missing:
            raise ValueError("fuel V2 definition lacks: " + ", ".join(missing))
        if not isinstance(self.components, tuple) or len(self.components) not in (1, 2):
            raise ValueError("FUEL_COUPLED_COMBUSTION_V2 supports one or two Wiebe components")
        for component in self.components:
            if not isinstance(component, WiebeComponent):
                raise ValueError("fuel V2 contains an invalid Wiebe component")
            component.validate()
            if (component.delay_deg < 0.0 or
                    component.delay_deg + component.duration_deg >= 360.0):
                raise ValueError("fuel V2 Wiebe window must fit within one 2T cycle")
        if not math.isclose(math.fsum(item.weight for item in self.components), 1.0,
                            rel_tol=0.0, abs_tol=1e-12):
            raise ValueError("fuel V2 Wiebe weights must sum to one")
        timing = _finite(self.ignition_timing_deg, "ignition_timing_deg")
        efficiency = _finite(self.combustion_efficiency, "combustion_efficiency")
        if not 0.0 <= timing < 360.0:
            raise ValueError("fuel V2 ignition timing must be in [0,360)")
        if not 0.0 <= efficiency <= 1.0:
            raise ValueError("fuel V2 combustion efficiency must be in [0,1]")
        if self.combustion_efficiency_provenance != "SYNTHETIC_ASSUMPTION":
            raise ValueError("fuel V2 efficiency requires explicit synthetic provenance")

    def capture(self, start_angle_deg: float,
                cylinder_species_kg: tuple[float, float, float, float]) -> FuelCombustionEventV1:
        self.validate()
        if not isinstance(cylinder_species_kg, (tuple, list)) or len(cylinder_species_kg) != 4:
            raise ValueError("cylinder species inventory must have four components")
        air, fuel_mass, residual, burned = tuple(
            _finite(value, "species_mass_kg") for value in cylinder_species_kg)
        if min(air, fuel_mass, residual, burned) < 0.0:
            raise ValueError("cylinder species inventory cannot be negative")
        oxygen_required_per_fuel = self.stoichiometric_afr * 0.232
        eligible = min(fuel_mass, air / self.stoichiometric_afr)
        event = FuelCombustionEventV1(float(start_angle_deg), air, fuel_mass, eligible)
        event.validate()
        # Make sure the conversion is finite and the frozen composition needs
        # a positive oxygen amount, without reinterpreting ANCAP limits.
        if not math.isfinite(oxygen_required_per_fuel) or oxygen_required_per_fuel <= 0.0:
            raise ValueError("fuel V2 oxygen demand is invalid")
        return event

    def stage_source(self, *, event: FuelCombustionEventV1, angle_deg: float,
                     rpm: float, species_mass_kg: tuple[float, ...],
                     noncombustion_species_rhs_kg_s: tuple[float, ...],
                     dt_s: float) -> dict[str, Any]:
        self.validate()
        event.validate()
        angle, speed, step = (_finite(angle_deg, "angle_deg"),
                              _finite(rpm, "rpm"), _finite(dt_s, "dt_s"))
        if speed <= 0.0 or step <= 0.0:
            raise ValueError("rpm and dt_s must be positive")
        if len(species_mass_kg) != 4 or len(noncombustion_species_rhs_kg_s) != 4:
            raise ValueError("combustion stage requires four species arrays")
        species = tuple(_finite(value, "species_mass_kg") for value in species_mass_kg)
        rhs = tuple(_finite(value, "species_rhs_kg_s")
                    for value in noncombustion_species_rhs_kg_s)
        if min(species) < 0.0:
            raise ValueError("combustion stage species cannot be negative")
        derivative = math.fsum(
            item.weight * FuelCoupledCombustionV1._component_rate(
                item, angle, event.start_angle_deg) for item in self.components)
        requested = event.fuel_available_for_burn_kg * derivative * 6.0 * speed
        available_fuel_rate = max(0.0, species[1] + step * rhs[1]) / step
        afr = self.stoichiometric_afr
        oxygen_limited_rate = max(0.0, species[0] + step * rhs[0]) / (afr * step)
        burned_rate = min(requested, available_fuel_rate, oxygen_limited_rate)
        air_rate = afr * burned_rate
        species_source = (-air_rate, -burned_rate, 0.0, air_rate + burned_rate)
        lhv = self.fuel.lower_heating_value_j_kg
        heat_rate = burned_rate * lhv * self.combustion_efficiency
        return {"species_kg_s": species_source, "heat_w": heat_rate,
                "requested_fuel_rate_kg_s": requested,
                "burned_fuel_rate_kg_s": burned_rate,
                "oxygen_limited_fuel_rate_kg_s": oxygen_limited_rate,
                "energy_per_burned_fuel_j_kg": lhv * self.combustion_efficiency,
                "actual_afr_at_ignition": (
                    None if event.fuel_at_ignition_kg <= 0.0 else
                    event.fresh_air_at_ignition_kg / event.fuel_at_ignition_kg)}

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return {"schema": self.schema,
                "components": [component.to_dict() for component in self.components],
                "ignition_timing_deg": self.ignition_timing_deg,
                "combustion_efficiency": self.combustion_efficiency,
                "combustion_efficiency_provenance": self.combustion_efficiency_provenance,
                "fuel_snapshot": self.fuel_snapshot.to_dict(),
                "fuel_sha256": self.fuel_sha256,
                "provenance": "SYNTHETIC_ASSUMPTION"}

    @classmethod
    def from_dict(cls, value: Any) -> "FuelCoupledCombustionV2":
        fields = {"schema", "components", "ignition_timing_deg",
                  "combustion_efficiency", "combustion_efficiency_provenance",
                  "fuel_snapshot", "fuel_sha256", "provenance"}
        if (not isinstance(value, dict) or set(value) != fields or
                value["schema"] != cls.schema or
                value["provenance"] != "SYNTHETIC_ASSUMPTION"):
            raise ValueError("fuel-coupled combustion V2 configuration is invalid")
        snapshot = FuelSimulationSnapshot.from_dict(value["fuel_snapshot"])
        if value["fuel_sha256"] != snapshot.content_hash:
            raise ValueError("fuel V2 snapshot hash mismatch")
        result = cls(tuple(WiebeComponent.from_dict(item)
                           for item in value["components"]),
                     value["ignition_timing_deg"], value["combustion_efficiency"],
                     snapshot, value["combustion_efficiency_provenance"])
        result.validate()
        if result.to_dict() != value:
            raise ValueError("fuel-coupled combustion V2 derived identity mismatch")
        return result
