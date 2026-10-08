"""Configurable prescribed Wiebe burn-progress laws (no fuel chemistry).

The capability returns dimensionless progress and CA10/50/90 only. It does not
convert fuel species or release energy; those quantities require the separately
defined P6/P11 fuel and energy contracts.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any

SCHEMA = "COMBUSTION_MODEL_V2"
PROVENANCE = {"DOCUMENTED", "DERIVED_FROM_DOCUMENTED", "SYNTHETIC_ASSUMPTION", "UNKNOWN"}


def _finite(value: Any, label: str) -> float:
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError(f"{label} must be finite numeric data, excluding booleans")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{label} is outside the supported numeric range")
    return result


@dataclass(frozen=True)
class EfficiencyMap:
    rpm: tuple[float, ...]
    load: tuple[float, ...]
    values: tuple[tuple[float, ...], ...]

    def validate(self) -> None:
        if not self.rpm or not self.load or len(self.values) != len(self.rpm):
            raise ValueError("Combustion efficiency map dimensions are invalid")
        if any(len(row) != len(self.load) for row in self.values):
            raise ValueError("Combustion efficiency matrix does not match axes")
        for axis, name, minimum in ((self.rpm, "rpm", 0.0), (self.load, "load", 0.0)):
            values = tuple(_finite(value, f"efficiency_map.{name}") for value in axis)
            if any(value < minimum for value in values):
                raise ValueError(f"Efficiency map {name} values are invalid")
            if any(right <= left for left, right in zip(values, values[1:])):
                raise ValueError(f"Efficiency map {name} axis must increase strictly")
        if any(not 0.0 <= _finite(value, "efficiency_map.value") <= 1.0
               for row in self.values for value in row):
            raise ValueError("Combustion efficiency map values must be in [0,1]")

    @staticmethod
    def _bracket(axis: tuple[float, ...], value: float, label: str) -> tuple[int, int, float]:
        if value < axis[0] or value > axis[-1]:
            raise ValueError(f"{label} is outside the configured efficiency map")
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
        r0, r1, fr = self._bracket(self.rpm, _finite(rpm, "rpm"), "rpm")
        l0, l1, fl = self._bracket(self.load, _finite(load, "load"), "load")
        low = self.values[r0][l0] * (1 - fl) + self.values[r0][l1] * fl
        high = self.values[r1][l0] * (1 - fl) + self.values[r1][l1] * fl
        return low * (1 - fr) + high * fr

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return {"rpm": list(self.rpm), "load": list(self.load),
                "values": [list(row) for row in self.values]}

    @classmethod
    def from_dict(cls, value: Any) -> "EfficiencyMap":
        if not isinstance(value, dict) or set(value) != {"rpm", "load", "values"}:
            raise ValueError("Efficiency map schema is invalid")
        result = cls(tuple(value["rpm"]), tuple(value["load"]),
                     tuple(tuple(row) for row in value["values"]))
        result.validate()
        return result


@dataclass(frozen=True)
class WiebeComponent:
    weight: float
    duration_deg: float
    shape_a: float
    shape_m: float
    delay_deg: float = 0.0

    def validate(self) -> None:
        weight = _finite(self.weight, "wiebe.weight")
        duration = _finite(self.duration_deg, "wiebe.duration_deg")
        shape_a = _finite(self.shape_a, "wiebe.shape_a")
        shape_m = _finite(self.shape_m, "wiebe.shape_m")
        _finite(self.delay_deg, "wiebe.delay_deg")
        if not 0.0 < weight <= 1.0 or duration <= 0 or shape_a <= 0 or shape_m < 0:
            raise ValueError("Wiebe weight/duration/a/m are outside their physical domain")

    def to_dict(self) -> dict[str, float]:
        self.validate()
        return {"weight": self.weight, "duration_deg": self.duration_deg,
                "shape_a": self.shape_a, "shape_m": self.shape_m,
                "delay_deg": self.delay_deg}

    @classmethod
    def from_dict(cls, value: Any) -> "WiebeComponent":
        fields = {"weight", "duration_deg", "shape_a", "shape_m", "delay_deg"}
        if not isinstance(value, dict) or set(value) != fields:
            raise ValueError("Wiebe component schema is invalid")
        result = cls(**value)
        result.validate()
        return result


@dataclass(frozen=True)
class CombustionProfile:
    components: tuple[WiebeComponent, ...]
    ignition_timing_deg: float
    provenance: str
    efficiency: float = 1.0
    efficiency_map: EfficiencyMap | None = None

    def validate(self) -> None:
        if not isinstance(self.components, tuple) or len(self.components) not in (1, 2):
            raise ValueError("COMBUSTION_MODEL_V2 supports one or two Wiebe components")
        for item in self.components:
            if not isinstance(item, WiebeComponent):
                raise ValueError("Invalid Wiebe component type")
            item.validate()
        weights = math.fsum(item.weight for item in self.components)
        if not math.isfinite(weights) or not math.isclose(weights, 1.0, rel_tol=0, abs_tol=1e-12):
            raise ValueError("Wiebe component weights must sum to one")
        _finite(self.ignition_timing_deg, "ignition_timing_deg")
        if not isinstance(self.provenance, str) or self.provenance not in PROVENANCE:
            raise ValueError("Combustion provenance is invalid")
        if (self.efficiency_map is None) == (self.efficiency is None):
            raise ValueError("Specify exactly one fixed efficiency or efficiency map")
        if self.efficiency is not None and not 0.0 <= _finite(
                self.efficiency, "combustion_efficiency") <= 1.0:
            raise ValueError("Combustion efficiency must be in [0,1]")
        if self.efficiency_map is not None:
            if not isinstance(self.efficiency_map, EfficiencyMap):
                raise ValueError("efficiency_map must be an EfficiencyMap")
            self.efficiency_map.validate()

    def _efficiency(self, rpm: float, load: float) -> float:
        if self.efficiency is not None:
            return float(self.efficiency)
        return self.efficiency_map.at(rpm, load)

    @staticmethod
    def _component_progress(component: WiebeComponent, angle: float,
                            start: float) -> tuple[float, float]:
        offset = angle - start - component.delay_deg
        if offset <= 0.0:
            return 0.0, 0.0
        if offset >= component.duration_deg:
            return 1.0, 0.0
        z = offset / component.duration_deg
        exponent = component.shape_m + 1.0
        powered = z ** exponent
        denominator = -math.expm1(-component.shape_a)
        progress = -math.expm1(-component.shape_a * powered) / denominator
        rate = (component.shape_a * exponent * z ** (exponent - 1.0) *
                math.exp(-component.shape_a * powered) /
                (component.duration_deg * denominator))
        return progress, rate

    def evaluate(self, angle_deg: float, *, rpm: float, load: float) -> dict[str, Any]:
        self.validate()
        angle = _finite(angle_deg, "angle_deg")
        speed = _finite(rpm, "rpm")
        load_value = _finite(load, "load")
        if speed <= 0 or load_value < 0:
            raise ValueError("rpm must be positive and load nonnegative")
        efficiency = self._efficiency(speed, load_value)
        progress = rate = 0.0
        for component in self.components:
            value, derivative = self._component_progress(
                component, angle, self.ignition_timing_deg)
            progress += component.weight * value
            rate += component.weight * derivative
        final = efficiency * progress
        points = self.ca_points(rpm=speed, load=load_value)
        return {"schema": SCHEMA, "angle_deg": angle,
                "burned_fraction": final, "burn_rate_per_deg": efficiency * rate,
                "combustion_efficiency": efficiency, "CA10_deg": points["CA10_deg"],
                "CA50_deg": points["CA50_deg"], "CA90_deg": points["CA90_deg"],
                "interpretation": "prescribed progress; no species conversion or heat release"}

    def ca_points(self, *, rpm: float, load: float) -> dict[str, float | None]:
        self.validate()
        efficiency = self._efficiency(_finite(rpm, "rpm"), _finite(load, "load"))
        if efficiency == 0.0:
            return {f"CA{percent}_deg": None for percent in (10, 50, 90)}
        start = self.ignition_timing_deg + min(item.delay_deg for item in self.components)
        end = max(self.ignition_timing_deg + item.delay_deg + item.duration_deg
                  for item in self.components)
        output = {}
        for percent in (10, 50, 90):
            target = percent / 100.0
            low, high = start, end
            for _ in range(80):
                middle = (low + high) / 2
                progress = math.fsum(component.weight * self._component_progress(
                    component, middle, self.ignition_timing_deg)[0]
                                     for component in self.components)
                if progress < target:
                    low = middle
                else:
                    high = middle
            output[f"CA{percent}_deg"] = (low + high) / 2
        return output

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return {"schema": SCHEMA, "components": [item.to_dict() for item in self.components],
                "ignition_timing_deg": self.ignition_timing_deg,
                "provenance": self.provenance, "efficiency": self.efficiency,
                "efficiency_map": None if self.efficiency_map is None else self.efficiency_map.to_dict()}

    @classmethod
    def from_dict(cls, value: Any) -> "CombustionProfile":
        fields = {"schema", "components", "ignition_timing_deg", "provenance",
                  "efficiency", "efficiency_map"}
        if (not isinstance(value, dict) or set(value) != fields or value["schema"] != SCHEMA
                or not isinstance(value["components"], list)):
            raise ValueError("Combustion profile schema is invalid")
        data = dict(value)
        data.pop("schema")
        data["components"] = tuple(WiebeComponent.from_dict(row) for row in data["components"])
        if data["efficiency_map"] is not None:
            data["efficiency_map"] = EfficiencyMap.from_dict(data["efficiency_map"])
        result = cls(**data)
        result.validate()
        return result
