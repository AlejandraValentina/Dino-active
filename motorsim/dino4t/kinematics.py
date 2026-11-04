"""Slider-crank cylinder geometry for a 720-degree cycle (SI units).

Angle convention: theta = 0 deg at firing TDC; gas-exchange TDC at +/-360 deg.
Piston position reuses ``motorsim.kinematics.piston_position`` (the shared,
cycle-agnostic geometric kernel); its derivative is analytic here.
"""
from __future__ import annotations

from dataclasses import dataclass
import math

from ..kinematics import piston_position


@dataclass(frozen=True)
class SliderCrank:
    bore_m: float
    stroke_m: float
    rod_m: float
    compression_ratio: float

    def __post_init__(self):
        values = (self.bore_m, self.stroke_m, self.rod_m, self.compression_ratio)
        if not all(math.isfinite(v) and v > 0 for v in values):
            raise ValueError("geometry requires positive finite values")
        if self.rod_m <= self.stroke_m / 2:
            raise ValueError("connecting rod must exceed stroke/2")
        if self.compression_ratio <= 1:
            raise ValueError("compression ratio must exceed 1")

    @property
    def piston_area(self) -> float:
        return math.pi * self.bore_m ** 2 / 4

    @property
    def displacement(self) -> float:
        return self.piston_area * self.stroke_m

    @property
    def clearance_volume(self) -> float:
        return self.displacement / (self.compression_ratio - 1)

    def position(self, theta_deg: float) -> float:
        """Piston distance from TDC (m)."""
        return piston_position(self.stroke_m * 1e3, self.rod_m * 1e3, theta_deg) * 1e-3

    def dposition_dtheta(self, theta_deg: float) -> float:
        """dx/dtheta (m/rad)."""
        r, l = self.stroke_m / 2, self.rod_m
        th = math.radians(theta_deg % 360.0)
        s, c = math.sin(th), math.cos(th)
        return r * s * (1 + r * c / math.sqrt(l * l - r * r * s * s))

    def volume(self, theta_deg: float) -> float:
        return self.clearance_volume + self.piston_area * self.position(theta_deg)

    def dvolume_dt(self, theta_deg: float, rpm: float) -> float:
        omega = rpm * 2 * math.pi / 60
        return self.piston_area * self.dposition_dtheta(theta_deg) * omega

    def liner_area(self, theta_deg: float) -> float:
        """Exposed liner area, using the equivalent clearance height Vc/Ap."""
        return math.pi * self.bore_m * (self.clearance_volume / self.piston_area + self.position(theta_deg))

    def mean_piston_speed(self, rpm: float) -> float:
        return 2 * self.stroke_m * rpm / 60
