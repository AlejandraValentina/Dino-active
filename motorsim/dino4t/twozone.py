"""Two-zone cylinder state handling (TWO_ZONE_EQUILIBRIUM_V1) on top of ``equilibrium.TwoZoneClosure``.

During the burn the cylinder state is just ``[U_total, s_u]`` (energy, specific entropy of the unburned
zone).  Everything else follows from the prescribed Wiebe burned fraction x_b(theta) and the algebraic
closure.  The state returns to the ordinary single-zone layout [species(ns), tracer, U] when the exhaust
valve opens (burned gas recombined onto the 8 standard species at constant U: radicals are negligible
there and the projection conserves elements and energy exactly).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .combustion import Wiebe
from .equilibrium import ELEMENTS, TwoZoneClosure, ZoneState
from .restriction import VolumeGas
from .thermo import Mixture
from .valves import CYCLE_DEG, wrap


@dataclass
class ZoneContext:
    m: float
    Y_u: np.ndarray
    xb_u: float
    b_full: np.ndarray          # kmol of C,H,O,N,AR taking part in equilibrium when x_b = 1
    fuel_inert_full: float      # kg of unburnt fuel carried (inert) by the burned zone when x_b = 1
    wiebe: Wiebe


class TwoZoneModel:
    def __init__(self, mix: Mixture, geometry):
        self.mix, self.geometry = mix, geometry
        self.closure = TwoZoneClosure(mix)
        self.ctx: ZoneContext | None = None
        self.last: ZoneState | None = None
        self.last_x = 0.0
        self._cache = None

    # ------------------------------------------------------------------------------ transitions
    def begin(self, z, gas: VolumeGas, wiebe: Wiebe, fuel: str, efficiency: float):
        """Single-zone vector -> two-zone vector at SOC.  Returns None if there is nothing to burn."""
        mix, ns = self.mix, self.mix.ns
        species = z[:ns]
        m = float(species.sum())
        ifuel = mix.index(fuel)
        reactive = species.copy()
        reactive[ifuel] *= efficiency
        elements = mix.element_masses(reactive)
        b_full = np.array([elements[mix.elements.index(e)] for e in ELEMENTS])
        if not np.all(b_full > 0) or reactive[ifuel] <= 1e-9 * m:
            return None
        Y_u = species / m
        self.ctx = ZoneContext(m, Y_u, float(z[ns]) / m, b_full, float(species[ifuel] * (1.0 - efficiency)), wiebe)
        self._cache = None
        return np.array([float(z[ns + 1]), float(mix.entropy(Y_u, gas.T, gas.p))])

    def merge(self, z2, theta):
        """Two-zone vector -> single-zone vector (species masses, tracer, U)."""
        out = self.totals(z2, theta)
        self.ctx = None
        self._cache = None
        return out

    # ------------------------------------------------------------------------------- evaluation
    def x_b(self, theta):
        w = self.ctx.wiebe
        return w.fraction((wrap(theta) - w.start_deg) % CYCLE_DEG)

    def evaluate(self, z2, theta):
        key = (z2.tobytes(), float(theta))
        if self._cache is not None and self._cache[0] == key:
            self.last, self.last_x = self._cache[1], self._cache[2]
            return self.last
        ctx = self.ctx
        x = self.x_b(theta)
        zs = self.closure.solve(U=float(z2[0]), s_u=float(z2[1]), V=self.geometry.volume(theta), m=ctx.m, x_b=x,
                                Y_u=ctx.Y_u, b_full=ctx.b_full, fuel_inert_full=ctx.fuel_inert_full)
        self._cache = (key, zs, x)
        self.last, self.last_x = zs, x
        return zs

    def totals(self, z2, theta):
        ns = self.mix.ns
        zs = self.evaluate(z2, theta)
        ctx = self.ctx
        burned8 = self.closure.project_to_standard(zs.Y_b, self.mix)
        out = np.empty(ns + 2)
        out[:ns] = zs.m_u * ctx.Y_u + zs.m_b * burned8
        out[ns] = zs.m_u * ctx.xb_u + zs.m_b
        out[ns + 1] = z2[0]
        return out

    def gas_view(self, z2, theta):
        """(VolumeGas, mass, volume) with the mean-temperature state; valves are closed in this phase."""
        mix = self.mix
        zs = self.evaluate(z2, theta)
        tot = self.totals(z2, theta)
        m = self.ctx.m
        Y = tot[:mix.ns] / m
        R = float(mix.gas_constant(Y))
        T = zs.p * self.geometry.volume(theta) / (m * R)
        return (VolumeGas(zs.p, T, Y, tot[mix.ns] / m, float(mix.enthalpy(Y, T)), R, float(mix.cp(Y, T))),
                m, self.geometry.volume(theta))
