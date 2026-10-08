"""Configurable slider-crank volume and existing-orifice crankcase links."""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any

from .kinematics import piston_position
from .simulation import restriction

SCHEMA = "CRANKCASE_MODEL_V2"


def _finite(value: Any, label: str) -> float:
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError(f"{label} must be finite numeric data, excluding booleans")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{label} outside supported range")
    return result


@dataclass(frozen=True)
class CrankcaseGeometry:
    bore_mm: float
    stroke_mm: float
    rod_length_mm: float
    volume_bdc_cm3: float
    provenance: str

    def validate(self):
        for name in ("bore_mm", "stroke_mm", "rod_length_mm", "volume_bdc_cm3"):
            if _finite(getattr(self, name), name) <= 0:
                raise ValueError(f"{name} must be positive")
        if self.rod_length_mm <= self.stroke_mm / 2:
            raise ValueError("Rod length must exceed crank radius")
        if self.provenance not in {"DOCUMENTED", "DERIVED_FROM_DOCUMENTED",
                                   "SYNTHETIC_ASSUMPTION", "UNKNOWN"}:
            raise ValueError("Crankcase geometry provenance is invalid")

    @property
    def displacement_m3(self) -> float:
        self.validate()
        bore, stroke = self.bore_mm * 1e-3, self.stroke_mm * 1e-3
        result = math.pi * bore * bore * stroke / 4.0
        if not math.isfinite(result) or result <= 0:
            raise ValueError("Crankcase displacement outside supported range")
        return result

    @property
    def volume_bdc_m3(self) -> float:
        self.validate()
        result = self.volume_bdc_cm3 * 1e-6
        if not math.isfinite(result) or result <= 0:
            raise ValueError("Crankcase BDC volume outside supported range")
        return result

    @property
    def volume_tdc_m3(self) -> float:
        result = self.volume_bdc_m3 + self.displacement_m3
        if not math.isfinite(result):
            raise ValueError("Crankcase TDC volume outside supported range")
        return result

    @property
    def compression_ratio(self) -> float:
        result = self.volume_tdc_m3 / self.volume_bdc_m3
        if not math.isfinite(result) or result <= 1.0:
            raise ValueError("Crankcase compression ratio is invalid")
        return result

    def volume_m3(self, angle_deg: float) -> float:
        self.validate()
        angle = _finite(angle_deg, "angle_deg")
        x = piston_position(self.stroke_mm, self.rod_length_mm, angle)
        result = self.volume_bdc_m3 + self.displacement_m3 * (1.0 - x / self.stroke_mm)
        if not math.isfinite(result) or result <= 0:
            raise ValueError("Crankcase volume is invalid")
        return result

    def volume_rate_m3_s(self, angle_deg: float, rpm: float) -> float:
        self.validate()
        angle = _finite(angle_deg, "angle_deg")
        speed = _finite(rpm, "rpm")
        if speed <= 0:
            raise ValueError("RPM must be positive")
        radius = self.stroke_mm / 2.0
        rod = self.rod_length_mm
        theta = math.radians(angle % 360.0)
        sine, cosine = math.sin(theta), math.cos(theta)
        under_root = rod * rod - radius * radius * sine * sine
        if under_root <= 0 or not math.isfinite(under_root):
            raise ValueError("Slider-crank geometry has a singular derivative")
        dx_dtheta_rad = radius * sine + radius * radius * sine * cosine / math.sqrt(under_root)
        dx_dt_m_s = dx_dtheta_rad * 1e-3 * (2 * math.pi * speed / 60.0)
        result = -(self.displacement_m3 / (self.stroke_mm * 1e-3)) * dx_dt_m_s
        if not math.isfinite(result):
            raise ValueError("Crankcase volume rate outside supported range")
        return result

    def to_dict(self):
        self.validate()
        return {"schema": SCHEMA, "bore_mm": self.bore_mm, "stroke_mm": self.stroke_mm,
                "rod_length_mm": self.rod_length_mm,
                "volume_bdc_cm3": self.volume_bdc_cm3,
                "provenance": self.provenance}

    @classmethod
    def from_dict(cls, value):
        fields = {"schema", "bore_mm", "stroke_mm", "rod_length_mm",
                  "volume_bdc_cm3", "provenance"}
        if not isinstance(value, dict) or set(value) != fields or value["schema"] != SCHEMA:
            raise ValueError("Crankcase geometry schema is invalid")
        result = cls(value["bore_mm"], value["stroke_mm"], value["rod_length_mm"],
                     value["volume_bdc_cm3"], value["provenance"])
        result.validate()
        return result


def crankcase_link_flux(left: tuple, right: tuple, area_m2: float, *,
                        discharge_coefficient: float, gas_r: float = 287.0,
                        gamma: float = 1.35) -> tuple[float, float, float]:
    """Existing bidirectional 0D restriction for explicit intake/leak links.

    State tuples are `(absolute_pressure_Pa, temperature_K, fresh_fraction)`.
    The resolved donor composition and direction are returned by the shared
    restriction relation; callers own global species/energy ledgers.
    """
    area = _finite(area_m2, "area_m2")
    cd = _finite(discharge_coefficient, "discharge_coefficient")
    gas_r = _finite(gas_r, "gas_r")
    gamma = _finite(gamma, "gamma")
    if area < 0 or not 0 < cd <= 1 or gas_r <= 0 or gamma <= 1:
        raise ValueError("Invalid crankcase link configuration")
    for state in (left, right):
        if len(state) != 3:
            raise ValueError("Crankcase link state must contain pressure, temperature and fresh fraction")
        pressure, temperature, fresh = (_finite(value, "link_state") for value in state)
        if pressure <= 0 or temperature <= 0 or not 0 <= fresh <= 1:
            raise ValueError("Crankcase link state is inadmissible")
    if area == 0:
        return (0.0, 0.0, 0.0)
    return restriction(left, right, area, cd, gas_r, gamma)
