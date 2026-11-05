"""Poppet-valve lift laws and effective flow areas.

Effective area: A_eff = n_valves * Cd(L/D, direction) * A_ref(L), where the
reference area is either the curtain area pi*D*L or the inner-seat area
pi*D^2/4.  Cd tables must be quoted against the same reference area used in
the flow bench reduction (recorded with their provenance in the config).
Directions: ``forward`` is the design flow (port->cylinder for intake,
cylinder->port for exhaust); ``reverse`` is backflow.
"""
from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as np

CYCLE_DEG = 720.0


def wrap(theta_deg: float) -> float:
    """Map an angle to [-360, 360)."""
    return (theta_deg + 360.0) % CYCLE_DEG - 360.0


class HarmonicLift:
    """L = Lmax sin^2(pi*phi/duration) between opening and closing angles."""
    kind = "harmonic"

    def __init__(self, open_deg: float, close_deg: float, max_lift_m: float):
        duration = (close_deg - open_deg) % CYCLE_DEG
        if not (0 < duration < CYCLE_DEG and max_lift_m > 0):
            raise ValueError("invalid harmonic lift law")
        self.open_deg, self.close_deg = wrap(open_deg), wrap(close_deg)
        self.duration = duration
        self.max_lift_m = max_lift_m

    def lift(self, theta_deg: float) -> float:
        phase = (theta_deg - self.open_deg) % CYCLE_DEG
        if phase >= self.duration:
            return 0.0
        return self.max_lift_m * math.sin(math.pi * phase / self.duration) ** 2

    def events(self):
        return (self.open_deg, self.close_deg, wrap(self.open_deg + self.duration / 2))


class TabulatedLift:
    """Measured or designed lift table; PCHIP interpolation (monotone between
    nodes, never overshoots, keeps lift >= 0).  Angles are crank degrees,
    strictly increasing, may extend beyond +/-360 (wrapped); end lifts must be 0."""
    kind = "tabulated"

    def __init__(self, angles_deg, lifts_m):
        from scipy.interpolate import PchipInterpolator
        a = np.asarray(angles_deg, dtype=float)
        L = np.asarray(lifts_m, dtype=float)
        if a.ndim != 1 or a.size < 3 or a.size != L.size or np.any(np.diff(a) <= 0):
            raise ValueError("lift table requires >=3 strictly increasing angles")
        if a[-1] - a[0] >= CYCLE_DEG or L[0] != 0 or L[-1] != 0 or np.any(L < 0):
            raise ValueError("lift table must start/end at zero lift within one cycle")
        self.open_deg, self.close_deg = wrap(a[0]), wrap(a[-1])
        self.duration = a[-1] - a[0]
        self.max_lift_m = float(L.max())
        self._phase = a - a[0]
        self._interp = PchipInterpolator(self._phase, L, extrapolate=False)

    def lift(self, theta_deg: float) -> float:
        phase = (theta_deg - self.open_deg) % CYCLE_DEG
        if phase >= self.duration:
            return 0.0
        return max(0.0, float(self._interp(phase)))

    def events(self):
        return (self.open_deg, self.close_deg)


@dataclass(frozen=True)
class FlowCoefficients:
    l_over_d: tuple
    forward: tuple
    reverse: tuple

    def __post_init__(self):
        x = np.asarray(self.l_over_d, dtype=float)
        if x.size < 1 or np.any(np.diff(x) <= 0) or x[0] < 0:
            raise ValueError("L/D axis must be nonnegative and increasing")
        for row in (self.forward, self.reverse):
            r = np.asarray(row, dtype=float)
            if r.size != x.size or np.any(r < 0) or np.any(r > 1.2):
                raise ValueError("Cd table invalid")

    def cd(self, l_over_d: float, direction: str) -> float:
        table = self.forward if direction == "forward" else self.reverse
        return float(np.interp(l_over_d, self.l_over_d, table))


@dataclass
class Valve:
    lift_law: object
    diameter_m: float
    count: int
    flow: FlowCoefficients
    reference_area: str = "curtain"

    def __post_init__(self):
        if self.reference_area not in ("curtain", "inner_seat"):
            raise ValueError("reference_area must be curtain or inner_seat")
        if not (self.diameter_m > 0 and isinstance(self.count, int) and self.count >= 1):
            raise ValueError("invalid valve diameter/count")

    def lift(self, theta_deg: float) -> float:
        return self.lift_law.lift(theta_deg)

    def effective_area(self, theta_deg: float, direction: str) -> float:
        L = self.lift(theta_deg)
        if L <= 0.0:
            return 0.0
        ref = (math.pi * self.diameter_m * L if self.reference_area == "curtain"
               else math.pi * self.diameter_m ** 2 / 4)
        return self.count * self.flow.cd(L / self.diameter_m, direction) * ref

    def is_open(self, theta_deg: float) -> bool:
        return self.lift(theta_deg) > 0.0

    def max_effective_area(self) -> float:
        samples = np.linspace(-360, 360, 2881)
        return max(max(self.effective_area(t, d) for d in ("forward", "reverse")) for t in samples)
