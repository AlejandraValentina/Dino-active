"""In-cylinder heat transfer (Woschni 1967) and friction (Chen-Flynn).

Both are STANDARD_V1 textbook correlations; their constants are calibration
parameters and their default values are literature values, not measurements
of any specific engine.
"""
from __future__ import annotations

from dataclasses import dataclass
import math


@dataclass(frozen=True)
class WoschniHeatTransfer:
    """h = C0 B^-0.2 p^0.8 T^-0.55 w^0.8  [W/m2K; B m, p kPa, T K, w m/s]
    w = C1 Sp + C2 (Vd Tr / (pr Vr)) (p - p_motored)
    Heywood (1988) eq. 12.19-12.20: C1 = 6.18 gas exchange, 2.28 otherwise;
    C2 = 3.24e-3 m/(s K) combustion/expansion, 0 otherwise.  Swirl omitted.
    ``multiplier`` is the conventional calibration factor (1 = literature)."""
    t_head_K: float = 550.0
    t_piston_K: float = 580.0
    t_liner_K: float = 420.0
    head_area_factor: float = 1.0
    piston_area_factor: float = 1.0
    c0: float = 3.26
    c1_gas_exchange: float = 6.18
    c1_closed: float = 2.28
    c2_combustion: float = 3.24e-3
    multiplier: float = 1.0

    def coefficient(self, *, bore_m, p_pa, T_K, mean_piston_speed, displacement,
                    gas_exchange: bool, combustion_phase: bool, reference, volume):
        c1 = self.c1_gas_exchange if gas_exchange else self.c1_closed
        w = c1 * mean_piston_speed
        if combustion_phase and reference is not None:
            p_r, T_r, V_r, n = reference
            p_mot = p_r * (V_r / volume) ** n
            w += self.c2_combustion * displacement * T_r / (p_r * V_r) * max(0.0, p_pa - p_mot)
        return self.multiplier * self.c0 * bore_m ** -0.2 * (p_pa / 1e3) ** 0.8 * T_K ** -0.55 * w ** 0.8

    def heat_loss_rate(self, h, T_K, piston_area, liner_area):
        """Gas-to-wall heat rate (W, positive = loss from gas)."""
        return h * (self.head_area_factor * piston_area * (T_K - self.t_head_K)
                    + self.piston_area_factor * piston_area * (T_K - self.t_piston_K)
                    + liner_area * (T_K - self.t_liner_K))


@dataclass(frozen=True)
class ChenFlynnFriction:
    """FMEP = A + B p_max + C Sp + D Sp^2  (Pa; p_max Pa; Sp m/s).
    Includes accessories in A; pumping is excluded (it is in IMEP_net)."""
    a_pa: float = 0.3e5
    b: float = 0.005
    c_pa_s_m: float = 0.09e5
    d_pa_s2_m2: float = 0.0009e5

    def fmep(self, p_max_pa: float, mean_piston_speed: float) -> float:
        return (self.a_pa + self.b * p_max_pa + self.c_pa_s_m * mean_piston_speed
                + self.d_pa_s2_m2 * mean_piston_speed ** 2)


def sutherland_viscosity_air(T_K):
    """Dynamic viscosity of air (Pa s), Sutherland law (White, Viscous Fluid Flow)."""
    return 1.458e-6 * T_K ** 1.5 / (T_K + 110.4)


def fanning_friction(reynolds):
    """Laminar 16/Re, turbulent Blasius 0.079 Re^-0.25 (smooth pipe); max of both."""
    import numpy as np
    re = np.maximum(reynolds, 1.0)
    return np.maximum(16.0 / re, 0.079 * re ** -0.25)


def _check_positive(*values):
    if not all(math.isfinite(v) and v > 0 for v in values):
        raise ValueError("closure parameters must be positive")
