"""RPM-mapped, continuously interpolated exhaust-roof position model."""
from __future__ import annotations

from dataclasses import dataclass, replace
import math
from typing import Any

from .two_stroke_ports import PortDefinition, TwoStrokePortSet

SCHEMA = "POWERVALVE_GEOMETRY_V1"
PROVENANCE = {"DOCUMENTED", "DERIVED_FROM_DOCUMENTED", "SYNTHETIC_ASSUMPTION", "UNKNOWN"}


def _finite(value: Any, label: str) -> float:
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError(f"{label} must be finite numeric data, excluding booleans")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{label} is outside supported range")
    return result


@dataclass(frozen=True)
class PowerValve:
    id: str
    exhaust_port_id: str
    rpm: tuple[float, ...]
    position: tuple[float, ...]
    provenance: str

    def validate(self) -> None:
        if not isinstance(self.id, str) or not self.id.strip():
            raise ValueError("Powervalve id is required")
        if not isinstance(self.exhaust_port_id, str) or not self.exhaust_port_id.strip():
            raise ValueError("Powervalve must identify its main exhaust port")
        if not isinstance(self.provenance, str) or self.provenance not in PROVENANCE:
            raise ValueError("Powervalve provenance is invalid")
        if not self.rpm or len(self.rpm) != len(self.position):
            raise ValueError("Powervalve RPM map dimensions are invalid")
        rpm = tuple(_finite(value, "powervalve.rpm") for value in self.rpm)
        position = tuple(_finite(value, "powervalve.position") for value in self.position)
        if any(value <= 0 for value in rpm) or any(b <= a for a, b in zip(rpm, rpm[1:])):
            raise ValueError("Powervalve RPM map must be positive and strictly increasing")
        if any(not 0 <= value <= 1 for value in position):
            raise ValueError("Powervalve position must be in [0,1]")

    def at(self, rpm: float) -> float:
        self.validate()
        target = _finite(rpm, "rpm")
        if target < self.rpm[0] or target > self.rpm[-1]:
            raise ValueError("RPM is outside the configured powervalve map")
        if len(self.rpm) == 1:
            return self.position[0]
        for (r0, r1), (p0, p1) in zip(zip(self.rpm, self.rpm[1:]),
                                      zip(self.position, self.position[1:])):
            if r0 <= target <= r1:
                fraction = (target - r0) / (r1 - r0)
                return p0 + fraction * (p1 - p0)
        return self.position[-1]

    def apply(self, port: PortDefinition, rpm: float) -> PortDefinition:
        self.validate()
        if not isinstance(port, PortDefinition):
            raise ValueError("Powervalve target must be a port definition")
        port.validate()
        if (port.id != self.exhaust_port_id or port.role != "exhaust" or
                port.family != "rectangular_window" or port.roof_travel_mm <= 0):
            raise ValueError("Powervalve requires its configured movable-roof exhaust window")
        result = replace(port, roof_position=self.at(rpm))
        result.validate()
        return result

    def area_at(self, port_set: TwoStrokePortSet, rpm: float, angle_deg: float) -> float:
        if not isinstance(port_set, TwoStrokePortSet):
            raise ValueError("Powervalve needs a generic 2T port set")
        port = next((item for item in port_set.ports if item.id == self.exhaust_port_id), None)
        if port is None:
            raise ValueError("Configured main exhaust port is absent from the port set")
        return port_set.area_at(self.apply(port, rpm), angle_deg)

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return {"schema": SCHEMA, "id": self.id, "exhaust_port_id": self.exhaust_port_id,
                "rpm": list(self.rpm), "position": list(self.position),
                "provenance": self.provenance,
                "position_semantics": "0=roof fully raised/open; 1=lowered/closing"}

    @classmethod
    def from_dict(cls, value: Any) -> "PowerValve":
        fields = {"schema", "id", "exhaust_port_id", "rpm", "position",
                  "provenance", "position_semantics"}
        if (not isinstance(value, dict) or set(value) != fields or value["schema"] != SCHEMA
                or value["position_semantics"] != "0=roof fully raised/open; 1=lowered/closing"
                or not isinstance(value["rpm"], list) or not isinstance(value["position"], list)):
            raise ValueError("Powervalve schema/semantics are invalid")
        result = cls(value["id"], value["exhaust_port_id"], tuple(value["rpm"]),
                     tuple(value["position"]), value["provenance"])
        result.validate()
        return result
