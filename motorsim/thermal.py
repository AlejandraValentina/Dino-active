"""Configurable prescribed-wall heat transfer and cycle energy ledger.

This module consumes gas-temperature samples from a caller. It does not alter
the gas solver or prescribe undocumented heat-transfer coefficients.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any

SCHEMA = "MOTORSIM_THERMAL_V1"
SURFACES = {"cylinder_wall", "cylinder_head", "piston_crown", "crankcase",
            "transfer_walls", "exhaust_walls"}
PROVENANCE = {"DOCUMENTED", "DERIVED_FROM_DOCUMENTED", "SYNTHETIC_ASSUMPTION", "UNKNOWN"}


def _finite(value: Any, label: str) -> float:
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError(f"{label} requires a finite number, excluding booleans")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{label} is outside the supported numeric range")
    return result


@dataclass(frozen=True)
class WallTemperatureMap:
    rpm: tuple[float, ...]
    load: tuple[float, ...]
    temperature_K: tuple[tuple[float, ...], ...]

    def validate(self) -> None:
        if not self.rpm or not self.load or len(self.temperature_K) != len(self.rpm):
            raise ValueError("Thermal map dimensions are invalid")
        if any(len(row) != len(self.load) for row in self.temperature_K):
            raise ValueError("Thermal map matrix does not match its axes")
        for axis, label in ((self.rpm, "rpm"), (self.load, "load")):
            values = tuple(_finite(value, f"map.{label}") for value in axis)
            if any(value <= 0 for value in values) if label == "rpm" else any(value < 0 for value in values):
                raise ValueError(f"Thermal map {label} axis has invalid values")
            if any(right <= left for left, right in zip(values, values[1:])):
                raise ValueError(f"Thermal map {label} axis must increase strictly")
        for row in self.temperature_K:
            if any(_finite(value, "map.temperature_K") <= 0 for value in row):
                raise ValueError("Wall temperatures must be positive kelvin")

    @staticmethod
    def _bracket(axis: tuple[float, ...], value: float, label: str) -> tuple[int, int, float]:
        if value < axis[0] or value > axis[-1]:
            raise ValueError(f"{label} is outside the configured thermal map")
        if len(axis) == 1:
            if value != axis[0]:
                raise ValueError(f"{label} does not match the single-point map")
            return 0, 0, 0.0
        for index, (low, high) in enumerate(zip(axis, axis[1:])):
            if low <= value <= high:
                return index, index + 1, (value - low) / (high - low)
        return len(axis) - 1, len(axis) - 1, 0.0

    def at(self, rpm: float, load: float) -> float:
        self.validate()
        target_rpm = _finite(rpm, "rpm")
        target_load = _finite(load, "load")
        r0, r1, fr = self._bracket(self.rpm, target_rpm, "rpm")
        l0, l1, fl = self._bracket(self.load, target_load, "load")
        low = self.temperature_K[r0][l0] * (1 - fl) + self.temperature_K[r0][l1] * fl
        high = self.temperature_K[r1][l0] * (1 - fl) + self.temperature_K[r1][l1] * fl
        result = low * (1 - fr) + high * fr
        if not math.isfinite(result) or result <= 0:
            raise ValueError("Interpolated wall temperature is invalid")
        return result

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return {"rpm": list(self.rpm), "load": list(self.load),
                "temperature_K": [list(row) for row in self.temperature_K]}

    @classmethod
    def from_dict(cls, value: Any) -> "WallTemperatureMap":
        if not isinstance(value, dict) or set(value) != {"rpm", "load", "temperature_K"}:
            raise ValueError("Wall temperature map schema is invalid")
        if not all(isinstance(value[key], list) for key in value):
            raise ValueError("Wall temperature map axes and data must be arrays")
        result = cls(tuple(value["rpm"]), tuple(value["load"]),
                     tuple(tuple(row) for row in value["temperature_K"]))
        result.validate()
        return result


@dataclass(frozen=True)
class ThermalSurface:
    id: str
    kind: str
    area_m2: float
    heat_transfer_w_m2k: float
    provenance: str
    wall_temperature_K: float | None = None
    wall_map: WallTemperatureMap | None = None

    def validate(self) -> None:
        if not isinstance(self.id, str) or not self.id.strip() or self.kind not in SURFACES:
            raise ValueError("Thermal surface id/kind is invalid")
        if self.provenance not in PROVENANCE:
            raise ValueError(f"{self.id}: parameter provenance is invalid")
        if _finite(self.area_m2, f"{self.id}.area_m2") <= 0:
            raise ValueError(f"{self.id}.area_m2 must be positive")
        if _finite(self.heat_transfer_w_m2k, f"{self.id}.heat_transfer_w_m2k") < 0:
            raise ValueError(f"{self.id}.heat_transfer_w_m2k cannot be negative")
        if (self.wall_temperature_K is None) == (self.wall_map is None):
            raise ValueError(f"{self.id}: specify exactly one fixed temperature or map")
        if self.wall_temperature_K is not None and _finite(
                self.wall_temperature_K, f"{self.id}.wall_temperature_K") <= 0:
            raise ValueError("Wall temperature must be positive kelvin")
        if self.wall_map is not None:
            if not isinstance(self.wall_map, WallTemperatureMap):
                raise ValueError("wall_map must be a WallTemperatureMap")
            self.wall_map.validate()

    def wall_temperature(self, rpm: float, load: float) -> float:
        self.validate()
        if self.wall_temperature_K is not None:
            return float(self.wall_temperature_K)
        return self.wall_map.at(rpm, load)

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return {"id": self.id, "kind": self.kind, "area_m2": self.area_m2,
                "heat_transfer_w_m2k": self.heat_transfer_w_m2k,
                "provenance": self.provenance,
                "wall_temperature_K": self.wall_temperature_K,
                "wall_map": None if self.wall_map is None else self.wall_map.to_dict()}

    @classmethod
    def from_dict(cls, value: Any) -> "ThermalSurface":
        fields = {"id", "kind", "area_m2", "heat_transfer_w_m2k", "provenance",
                  "wall_temperature_K", "wall_map"}
        if not isinstance(value, dict) or set(value) != fields:
            raise ValueError("Thermal surface schema is invalid")
        data = dict(value)
        if data["wall_map"] is not None:
            data["wall_map"] = WallTemperatureMap.from_dict(data["wall_map"])
        result = cls(**data)
        result.validate()
        return result


@dataclass(frozen=True)
class ThermalSystem:
    surfaces: tuple[ThermalSurface, ...]

    def validate(self) -> None:
        if not isinstance(self.surfaces, tuple) or not self.surfaces:
            raise ValueError("ThermalSystem requires at least one configured surface")
        if any(not isinstance(surface, ThermalSurface) for surface in self.surfaces):
            raise ValueError("ThermalSystem contains an invalid surface")
        for surface in self.surfaces:
            surface.validate()
        ids = [surface.id for surface in self.surfaces]
        if len(set(ids)) != len(ids):
            raise ValueError("Thermal surface ids must be unique")

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return {"schema": SCHEMA,
                "correlation": "CONSTANT_H_V1",
                "surfaces": [surface.to_dict() for surface in self.surfaces]}

    @classmethod
    def from_dict(cls, value: Any) -> "ThermalSystem":
        if (not isinstance(value, dict) or set(value) != {"schema", "correlation", "surfaces"}
                or value["schema"] != SCHEMA or value["correlation"] != "CONSTANT_H_V1"
                or not isinstance(value["surfaces"], list)):
            raise ValueError("Thermal system schema/correlation is invalid")
        result = cls(tuple(ThermalSurface.from_dict(row) for row in value["surfaces"]))
        result.validate()
        return result

    def heat_rate_w(self, surface_id: str, gas_temperature_K: float,
                    rpm: float, load: float) -> float:
        self.validate()
        surface = next((item for item in self.surfaces if item.id == surface_id), None)
        if surface is None:
            raise ValueError(f"Unknown thermal surface: {surface_id}")
        gas_temperature = _finite(gas_temperature_K, "gas_temperature_K")
        if gas_temperature <= 0:
            raise ValueError("Gas temperature must be positive kelvin")
        heat = surface.heat_transfer_w_m2k * surface.area_m2 * (
            gas_temperature - surface.wall_temperature(rpm, load))
        if not math.isfinite(heat):
            raise ValueError("Heat-transfer rate is outside the supported range")
        return heat

    def cycle_ledger(self, samples: tuple[dict[str, Any], ...], *, rpm: float,
                     load: float, period_deg: float = 360.0) -> dict[str, Any]:
        """Trapezoidal heat ledger; positive energy flows from gas to wall."""
        self.validate()
        speed = _finite(rpm, "rpm")
        if speed <= 0:
            raise ValueError("rpm must be positive")
        load_value = _finite(load, "load")
        period = _finite(period_deg, "period_deg")
        if period <= 0 or not isinstance(samples, tuple) or len(samples) < 2:
            raise ValueError("A cycle needs at least two ordered samples")
        for sample in samples:
            if not isinstance(sample, dict) or set(sample) != {"angle_deg", "gas_temperature_K"}:
                raise ValueError("Each thermal sample needs angle and gas temperatures")
            if not isinstance(sample["gas_temperature_K"], dict):
                raise ValueError("gas_temperature_K must map surface ids to temperatures")
            if set(sample["gas_temperature_K"]) != {surface.id for surface in self.surfaces}:
                raise ValueError("Each sample must include every configured surface exactly once")
        angles = tuple(_finite(sample["angle_deg"], "angle_deg") for sample in samples)
        if any(b <= a for a, b in zip(angles, angles[1:])):
            raise ValueError("Cycle sample angles must increase strictly")
        if not math.isclose(angles[-1] - angles[0], period, rel_tol=0.0,
                            abs_tol=16 * math.ulp(period)):
            raise ValueError("Thermal samples must span exactly one configured cycle")
        rates = {surface.id: [] for surface in self.surfaces}
        for sample in samples:
            for surface in self.surfaces:
                rates[surface.id].append(self.heat_rate_w(
                    surface.id, sample["gas_temperature_K"][surface.id], speed, load_value))
        energy = {surface_id: 0.0 for surface_id in rates}
        for index, (left, right) in enumerate(zip(samples, samples[1:])):
            dt = (angles[index + 1] - angles[index]) / (6.0 * speed)
            for surface_id, values in rates.items():
                energy[surface_id] += 0.5 * (values[index] + values[index + 1]) * dt
        if any(not math.isfinite(value) for value in energy.values()):
            raise ValueError("Thermal cycle energy is outside the supported range")
        total = math.fsum(energy.values())
        if not math.isfinite(total):
            raise ValueError("Total thermal cycle energy is outside the supported range")
        return {"schema": "THERMAL_CYCLE_LEDGER_V1", "period_deg": period,
                "rpm": speed, "load": load_value,
                "heat_to_wall_j_by_surface": energy,
                "heat_to_wall_total_j": total,
                "gas_heat_loss_j": total,
                "integration": "trapezoid over supplied cycle samples"}
