"""Explicit two-stroke mechanical-loss and brake-performance accounting."""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any

SCHEMA = "MECHANICAL_LOSS_MODEL_V1"
LOSS_SOURCES = {"piston_ring", "bearing_accessory", "pumping"}
PROVENANCE = {"DOCUMENTED", "DERIVED_FROM_DOCUMENTED", "SYNTHETIC_ASSUMPTION", "UNKNOWN"}


def _finite(value: Any, label: str) -> float:
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError(f"{label} must be finite numeric data, excluding booleans")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{label} is outside supported range")
    return result


@dataclass(frozen=True)
class OperatingMap:
    rpm: tuple[float, ...]
    load: tuple[float, ...]
    values_pa: tuple[tuple[float, ...], ...]

    def validate(self) -> None:
        if not self.rpm or not self.load or len(self.values_pa) != len(self.rpm):
            raise ValueError("Loss map dimensions are invalid")
        if any(len(row) != len(self.load) for row in self.values_pa):
            raise ValueError("Loss map matrix does not match axes")
        for axis, name in ((self.rpm, "rpm"), (self.load, "load")):
            values = tuple(_finite(item, f"map.{name}") for item in axis)
            if any(item < 0 for item in values) or any(
                    b <= a for a, b in zip(values, values[1:])):
                raise ValueError(f"Loss map {name} axis must be nonnegative and strictly increasing")
        if any(_finite(value, "loss_map.values_pa") < 0
               for row in self.values_pa for value in row):
            raise ValueError("Friction MEP cannot be negative")

    @staticmethod
    def _bracket(axis: tuple[float, ...], value: float, label: str):
        if value < axis[0] or value > axis[-1]:
            raise ValueError(f"{label} is outside configured mechanical map")
        if len(axis) == 1:
            if value != axis[0]:
                raise ValueError(f"{label} does not match single-point map")
            return 0, 0, 0.0
        for i, (lo, hi) in enumerate(zip(axis, axis[1:])):
            if lo <= value <= hi:
                return i, i + 1, (value - lo) / (hi - lo)
        return len(axis) - 1, len(axis) - 1, 0.0

    def at(self, rpm: float, load: float) -> float:
        self.validate()
        r0, r1, fr = self._bracket(self.rpm, _finite(rpm, "rpm"), "rpm")
        l0, l1, fl = self._bracket(self.load, _finite(load, "load"), "load")
        low = self.values_pa[r0][l0] * (1 - fl) + self.values_pa[r0][l1] * fl
        high = self.values_pa[r1][l0] * (1 - fl) + self.values_pa[r1][l1] * fl
        return low * (1 - fr) + high * fr

    def to_dict(self):
        self.validate()
        return {"rpm": list(self.rpm), "load": list(self.load),
                "values_pa": [list(row) for row in self.values_pa]}

    @classmethod
    def from_dict(cls, value):
        if not isinstance(value, dict) or set(value) != {"rpm", "load", "values_pa"}:
            raise ValueError("Mechanical operating map schema is invalid")
        result = cls(tuple(value["rpm"]), tuple(value["load"]),
                     tuple(tuple(row) for row in value["values_pa"]))
        result.validate()
        return result


@dataclass(frozen=True)
class LossTerm:
    id: str
    source: str
    provenance: str
    mep_pa: float | None = None
    operating_map: OperatingMap | None = None

    def validate(self):
        if not isinstance(self.id, str) or not self.id.strip() or self.source not in LOSS_SOURCES:
            raise ValueError("Mechanical loss term id/source is invalid")
        if not isinstance(self.provenance, str) or self.provenance not in PROVENANCE:
            raise ValueError("Mechanical loss provenance is invalid")
        if (self.mep_pa is None) == (self.operating_map is None):
            raise ValueError("Specify exactly one fixed MEP or operating map")
        if self.mep_pa is not None and _finite(self.mep_pa, f"{self.id}.mep_pa") < 0:
            raise ValueError("Friction MEP cannot be negative")
        if self.operating_map is not None:
            if not isinstance(self.operating_map, OperatingMap):
                raise ValueError("operating_map must be an OperatingMap")
            self.operating_map.validate()

    def value(self, rpm: float, load: float) -> float:
        self.validate()
        return float(self.mep_pa) if self.mep_pa is not None else self.operating_map.at(rpm, load)

    def to_dict(self):
        self.validate()
        return {"id": self.id, "source": self.source, "provenance": self.provenance,
                "mep_pa": self.mep_pa,
                "operating_map": None if self.operating_map is None else self.operating_map.to_dict()}

    @classmethod
    def from_dict(cls, value):
        fields = {"id", "source", "provenance", "mep_pa", "operating_map"}
        if not isinstance(value, dict) or set(value) != fields:
            raise ValueError("Mechanical loss term schema is invalid")
        data = dict(value)
        if data["operating_map"] is not None:
            data["operating_map"] = OperatingMap.from_dict(data["operating_map"])
        result = cls(**data)
        result.validate()
        return result


@dataclass(frozen=True)
class MechanicalLossModel:
    terms: tuple[LossTerm, ...]

    def validate(self):
        if not isinstance(self.terms, tuple) or not self.terms:
            raise ValueError("MechanicalLossModel requires explicit loss terms")
        for term in self.terms:
            if not isinstance(term, LossTerm):
                raise ValueError("Invalid mechanical loss term")
            term.validate()
        if len({term.id for term in self.terms}) != len(self.terms):
            raise ValueError("Mechanical loss term ids must be unique")

    def evaluate_2t(self, *, indicated_work_j: float, displacement_m3: float,
                    rpm: float, load: float) -> dict[str, Any]:
        return self._evaluate_2t(work_j=indicated_work_j,
                                 work_name="indicated_work_j",
                                 displacement_m3=displacement_m3, rpm=rpm,
                                 load=load)

    def evaluate_2t_net_piston_work(self, *, net_piston_gas_work_j: float,
                                    displacement_m3: float, rpm: float,
                                    load: float) -> dict[str, Any]:
        """Apply mechanical losses once to cylinder plus crankcase gas work.

        This additive API keeps the historical indicated-work API intact and
        makes the input basis explicit for the integrated v1 engine.
        """
        result = self._evaluate_2t(work_j=net_piston_gas_work_j,
                                   work_name="net_piston_gas_work_j",
                                   displacement_m3=displacement_m3, rpm=rpm,
                                   load=load)
        result["schema"] = "MOTORSIM_MECHANICAL_LOSSES_2T_V2_NET_PISTON_WORK"
        result["net_piston_gas_work_j"] = result.pop("indicated_work_j")
        result["net_piston_mep_pa"] = result.pop("indicated_mep_pa")
        result["net_piston_power_w"] = result.pop("indicated_power_w")
        result["net_piston_torque_nm"] = result.pop("indicated_torque_nm")
        return result

    def _evaluate_2t(self, *, work_j: float, work_name: str,
                     displacement_m3: float, rpm: float,
                     load: float) -> dict[str, Any]:
        self.validate()
        work = _finite(work_j, work_name)
        displacement = _finite(displacement_m3, "displacement_m3")
        speed = _finite(rpm, "rpm")
        load_value = _finite(load, "load")
        if displacement <= 0 or speed <= 0 or load_value < 0:
            raise ValueError("Displacement/RPM must be positive and load nonnegative")
        mep_by_term = {term.id: term.value(speed, load_value) for term in self.terms}
        loss_mep = math.fsum(mep_by_term.values())
        indicated_mep = work / displacement
        loss_work = loss_mep * displacement
        brake_work = work - loss_work
        power_factor = speed / 60.0  # one 360-degree firing cycle per revolution
        losses = {key: value * displacement for key, value in mep_by_term.items()}
        output = {"schema": SCHEMA, "cycle_convention": "2T_360_DEG_ONE_CYCLE_PER_REV",
                "rpm": speed, "load": load_value, "displacement_m3": displacement,
                "indicated_work_j": work, "brake_work_j": brake_work,
                "loss_work_j_by_term": losses,
                "friction_mep_pa_by_term": mep_by_term,
                "friction_mep_pa": loss_mep, "indicated_mep_pa": indicated_mep,
                "brake_mep_pa": brake_work / displacement,
                "indicated_power_w": work * power_factor,
                "mechanical_loss_power_w": loss_work * power_factor,
                "brake_power_w": brake_work * power_factor,
                "indicated_torque_nm": work / (2 * math.pi),
                "mechanical_loss_torque_nm": loss_work / (2 * math.pi),
                "brake_torque_nm": brake_work / (2 * math.pi),
                "brake_power_positive": brake_work > 0.0,
                "clipped": False}
        numbers = [value for value in output.values() if type(value) is float]
        numbers.extend(value for mapping in (losses, mep_by_term)
                       for value in mapping.values())
        if not all(math.isfinite(value) for value in numbers):
            raise ValueError("Mechanical performance output is outside supported range")
        return output

    def to_dict(self):
        self.validate()
        return {"schema": SCHEMA, "cycle_convention": "2T_360_DEG_ONE_CYCLE_PER_REV",
                "terms": [term.to_dict() for term in self.terms]}

    @classmethod
    def from_dict(cls, value):
        if (not isinstance(value, dict) or set(value) != {"schema", "cycle_convention", "terms"}
                or value["schema"] != SCHEMA
                or value["cycle_convention"] != "2T_360_DEG_ONE_CYCLE_PER_REV"
                or not isinstance(value["terms"], list)):
            raise ValueError("Mechanical loss model schema is invalid")
        result = cls(tuple(LossTerm.from_dict(row) for row in value["terms"]))
        result.validate()
        return result
