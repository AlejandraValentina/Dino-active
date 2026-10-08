"""Explicit fuel-property and 2T cycle consumption bookkeeping."""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any

SCHEMA = "FUEL_ACCOUNTING_V1"
PROVENANCE = {"DOCUMENTED", "DERIVED_FROM_DOCUMENTED", "SYNTHETIC_ASSUMPTION", "UNKNOWN"}


def _finite(value: Any, label: str) -> float:
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError(f"{label} must be finite numeric data, excluding booleans")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{label} is outside supported range")
    return result


def _ratio(numerator: float, denominator: float, label: str) -> dict[str, Any]:
    if denominator == 0.0:
        return {"value": None, "status": "UNDEFINED", "reason": "ZERO_DENOMINATOR"}
    result = numerator / denominator
    if not math.isfinite(result):
        raise ValueError(f"{label} is outside supported range")
    return {"value": result, "status": "DEFINED", "reason": None}


@dataclass(frozen=True)
class FuelProperties:
    stoichiometric_afr: float
    lower_heating_value_j_kg: float
    provenance: str

    def validate(self):
        if not isinstance(self.provenance, str) or self.provenance not in PROVENANCE:
            raise ValueError("Fuel property provenance is invalid")
        if _finite(self.stoichiometric_afr, "stoichiometric_afr") <= 0:
            raise ValueError("Stoichiometric AFR must be positive")
        if _finite(self.lower_heating_value_j_kg, "lower_heating_value_j_kg") <= 0:
            raise ValueError("Fuel LHV must be positive")

    def to_dict(self):
        self.validate()
        return {"stoichiometric_afr": self.stoichiometric_afr,
                "lower_heating_value_j_kg": self.lower_heating_value_j_kg,
                "provenance": self.provenance}

    @classmethod
    def from_dict(cls, value):
        if not isinstance(value, dict) or set(value) != {
                "stoichiometric_afr", "lower_heating_value_j_kg", "provenance"}:
            raise ValueError("Fuel property schema is invalid")
        result = cls(**value)
        result.validate()
        return result


@dataclass(frozen=True)
class FuelAccounting:
    properties: FuelProperties

    def validate(self):
        if not isinstance(self.properties, FuelProperties):
            raise ValueError("FuelAccounting requires explicit FuelProperties")
        self.properties.validate()

    def evaluate_2t(self, *, fresh_air_delivered_kg: float,
                    fuel_delivered_kg: float, trapped_fresh_air_kg: float,
                    trapped_fuel_kg: float, fuel_short_circuited_kg: float,
                    burned_fraction: float,
                    rpm: float, indicated_work_j: float,
                    brake_work_j: float | None = None) -> dict[str, Any]:
        self.validate()
        values = {name: _finite(value, name) for name, value in {
            "fresh_air_delivered_kg": fresh_air_delivered_kg,
            "fuel_delivered_kg": fuel_delivered_kg,
            "trapped_fresh_air_kg": trapped_fresh_air_kg,
            "trapped_fuel_kg": trapped_fuel_kg,
            "fuel_short_circuited_kg": fuel_short_circuited_kg,
            "burned_fraction": burned_fraction,
            "rpm": rpm, "indicated_work_j": indicated_work_j}.items()}
        brake_work = None if brake_work_j is None else _finite(brake_work_j, "brake_work_j")
        if any(value < 0 for key, value in values.items()
               if key.endswith("_kg") or key in ("rpm",)):
            raise ValueError("Fuel masses and RPM must be nonnegative")
        if values["rpm"] <= 0:
            raise ValueError("RPM must be positive")
        if values["trapped_fresh_air_kg"] > values["fresh_air_delivered_kg"]:
            raise ValueError("Trapped fresh air cannot exceed delivered fresh air")
        if values["trapped_fuel_kg"] > values["fuel_delivered_kg"]:
            raise ValueError("Trapped fuel cannot exceed delivered fuel")
        if values["fuel_short_circuited_kg"] > values["fuel_delivered_kg"]:
            raise ValueError("Short-circuited fuel cannot exceed delivered fuel")
        if not 0.0 <= values["burned_fraction"] <= 1.0:
            raise ValueError("Burned fraction must be in [0,1]")
        burned = values["trapped_fuel_kg"] * values["burned_fraction"]
        unburned_trapped = values["trapped_fuel_kg"] - burned
        untrapped = values["fuel_delivered_kg"] - values["trapped_fuel_kg"]
        delivered_afr = _ratio(values["fresh_air_delivered_kg"],
                               values["fuel_delivered_kg"], "delivered_afr")
        trapped_afr = _ratio(values["trapped_fresh_air_kg"],
                             values["trapped_fuel_kg"], "trapped_afr")
        stoich = self.properties.stoichiometric_afr
        equivalence = {
            "delivered": _ratio(stoich, delivered_afr["value"], "delivered_equivalence_ratio")
            if delivered_afr["value"] not in (None, 0.0) else
            {"value": None, "status": "UNDEFINED", "reason": "ZERO_DENOMINATOR"},
            "trapped": _ratio(stoich, trapped_afr["value"], "trapped_equivalence_ratio")
            if trapped_afr["value"] not in (None, 0.0) else
            {"value": None, "status": "UNDEFINED", "reason": "ZERO_DENOMINATOR"},
        }
        frequency = values["rpm"] / 60.0  # 2T: one 360-degree cycle per revolution
        fuel_flow = values["fuel_delivered_kg"] * frequency
        indicated_power = values["indicated_work_j"] * frequency
        brake_power = None if brake_work is None else brake_work * frequency
        properties = self.properties
        result = {"schema": SCHEMA, "cycle_convention": "2T_360_DEG_ONE_CYCLE_PER_REV",
                  "fresh_air_delivered_kg_per_cycle": values["fresh_air_delivered_kg"],
                  "fuel_delivered_kg_per_cycle": values["fuel_delivered_kg"],
                  "fresh_air_trapped_kg_per_cycle": values["trapped_fresh_air_kg"],
                  "fuel_trapped_kg_per_cycle": values["trapped_fuel_kg"],
                  "fuel_burned_kg_per_cycle": burned,
                  "fuel_unburned_trapped_kg_per_cycle": unburned_trapped,
                  "fuel_not_trapped_kg_per_cycle": untrapped,
                  "fuel_short_circuited_kg_per_cycle": values["fuel_short_circuited_kg"],
                  "combustion_efficiency_fraction_of_trapped_fuel": values["burned_fraction"],
                  "delivered_afr": delivered_afr, "trapped_afr": trapped_afr,
                  "equivalence_ratio": equivalence,
                  "fuel_flow_kg_s": fuel_flow,
                  "released_energy_j_per_cycle": burned * properties.lower_heating_value_j_kg,
                  "indicated_power_w": indicated_power,
                  "indicated_sfc_g_kwh": self._sfc(fuel_flow, indicated_power),
                  "brake_power_w": brake_power,
                  "brake_sfc_g_kwh": None if brake_power is None else self._sfc(fuel_flow, brake_power),
                  "brake_sfc_status": "NOT_PROVIDED" if brake_power is None else
                      ("DEFINED" if brake_power > 0 else "UNDEFINED_NONPOSITIVE_BRAKE_POWER"),
                  "fuel_properties": properties.to_dict()}
        derived = (burned, unburned_trapped, untrapped, fuel_flow, indicated_power,
                   values["burned_fraction"] * properties.lower_heating_value_j_kg *
                   values["trapped_fuel_kg"])
        if not all(math.isfinite(value) for value in derived):
            raise ValueError("Fuel accounting output is outside supported range")
        return result

    @staticmethod
    def _sfc(flow_kg_s: float, power_w: float) -> float | None:
        if power_w <= 0:
            return None
        value = flow_kg_s * 3.6e9 / power_w
        if not math.isfinite(value):
            raise ValueError("Specific fuel consumption is outside supported range")
        return value

    def to_dict(self):
        self.validate()
        return {"schema": SCHEMA, "properties": self.properties.to_dict()}

    @classmethod
    def from_dict(cls, value):
        if (not isinstance(value, dict) or set(value) != {"schema", "properties"}
                or value["schema"] != SCHEMA):
            raise ValueError("Fuel accounting schema is invalid")
        result = cls(FuelProperties.from_dict(value["properties"]))
        result.validate()
        return result
