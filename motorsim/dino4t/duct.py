"""Quasi-1D finite-volume duct for a thermally perfect multi-species gas.

Conservative variables per unit volume (one row per cell)::

    [rho_1 .. rho_ns, rho*X_b, rho*u, rho*E]

``X_b`` is a passive burned-gas tracer (mass that has passed through a
flame).  Mixture density is the sum of species densities, so total mass is
conserved exactly whenever every species is.  E includes formation enthalpy
(see ``thermo``).

Spatial scheme: HLLC (Toro, Spruce & Speares 1994) with Einfeldt-type
EOS-independent wave-speed bounds, HLLE fallback for degenerate star
states; MUSCL reconstruction of (rho, u, p) with a TVD limiter (minmod default; van Leer, MC) on the
nonuniform centroid spacing; species and tracer use first-order (donor-cell)
reconstruction so their face values stay in [0, 1] and sum to one exactly.
Area variation enters through the well-balanced pressure source
p_i (A_{i+1/2} - A_{i-1/2}).  Optional wall friction (Fanning, laminar /
Blasius) and wall heat transfer (Colburn-Reynolds analogy).
Geometry: exact frustum volumes from ``motorsim.gas1d.mesh.segments_mesh``.
"""
from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as np

from ..gas1d.mesh import segments_mesh
from .closures import fanning_friction, sutherland_viscosity_air
from .thermo import Mixture, ThermoError


class InadmissibleState(ValueError):
    pass


@dataclass(frozen=True)
class DuctWall:
    friction: bool = False
    heat_transfer: bool = False
    temperature_K: float = 300.0
    prandtl: float = 0.71
    friction_factor: float | None = None  # constant Fanning factor (verification); None = correlation


def physical_flux(state, ns):
    rho, u, p, Y, xb, E = (state[k] for k in ("rho", "u", "p", "Y", "xb", "E"))
    mass = rho * u
    F = np.empty((rho.size, ns + 3))
    F[:, :ns] = mass[:, None] * Y
    F[:, ns] = mass * xb
    F[:, ns + 1] = mass * u + p
    F[:, ns + 2] = u * (E + p)
    return F


def conservative(state, ns):
    rho = state["rho"]
    U = np.empty((rho.size, ns + 3))
    U[:, :ns] = rho[:, None] * state["Y"]
    U[:, ns] = rho * state["xb"]
    U[:, ns + 1] = rho * state["u"]
    U[:, ns + 2] = state["E"]
    return U


def wave_speeds(L, R):
    """Einfeldt-type bounds, valid for any EOS (Toro 2009, eq. 10.52)."""
    sl, sr = np.sqrt(L["rho"]), np.sqrt(R["rho"])
    w = sl + sr
    ub = (sl * L["u"] + sr * R["u"]) / w
    d2 = (sl * L["a"] ** 2 + sr * R["a"] ** 2) / w + 0.5 * sl * sr / w ** 2 * (R["u"] - L["u"]) ** 2
    db = np.sqrt(d2)
    return np.minimum(L["u"] - L["a"], ub - db), np.maximum(R["u"] + R["a"], ub + db)


def hllc(L, R, ns, speeds=None):
    """Vectorized HLLC; returns (flux, max |wave speed|, fallback count)."""
    SL, SR = speeds if speeds is not None else wave_speeds(L, R)
    FL, FR = physical_flux(L, ns), physical_flux(R, ns)
    rl, ul, pl, El = L["rho"], L["u"], L["p"], L["E"]
    rr, ur, pr, Er = R["rho"], R["u"], R["p"], R["E"]
    den = rl * (SL - ul) - rr * (SR - ur)
    with np.errstate(divide="ignore", invalid="ignore"):
        Sm = (pr - pl + rl * ul * (SL - ul) - rr * ur * (SR - ur)) / den
        rsl = rl * (SL - ul) / (SL - Sm)
        rsr = rr * (SR - ur) / (SR - Sm)
        esl = rsl * (El / rl + (Sm - ul) * (Sm + pl / (rl * (SL - ul))))
        esr = rsr * (Er / rr + (Sm - ur) * (Sm + pr / (rr * (SR - ur))))
        psl = pl + rl * (SL - ul) * (Sm - ul)
        psr = pr + rr * (SR - ur) * (Sm - ur)
        e0l = L.get("e0", 0.0)
        e0r = R.get("e0", 0.0)
        ok = (np.isfinite(Sm) & (den != 0) & (SL < Sm) & (Sm < SR) & (rsl > 0) & (rsr > 0)
              & np.isfinite(esl) & np.isfinite(esr) & (psl > 0) & (psr > 0)
              & (esl / rsl - 0.5 * Sm * Sm > e0l) & (esr / rsr - 0.5 * Sm * Sm > e0r))
    left_star = Sm >= 0
    rs = np.where(left_star, rsl, rsr)
    es = np.where(left_star, esl, esr)
    S = np.where(left_star, SL, SR)
    Fk = np.where(left_star[:, None], FL, FR)
    Uk_mom = np.where(left_star, rl * ul, rr * ur)
    Uk_E = np.where(left_star, El, Er)
    Yk = np.where(left_star[:, None], L["Y"], R["Y"])
    xk = np.where(left_star, L["xb"], R["xb"])
    F = np.empty_like(FL)
    mass = rs * Sm  # = F_mass + S (rho* - rho) by Rankine-Hugoniot
    F[:, :ns] = mass[:, None] * Yk
    F[:, ns] = mass * xk
    F[:, ns + 1] = Fk[:, ns + 1] + S * (rs * Sm - Uk_mom)
    F[:, ns + 2] = Fk[:, ns + 2] + S * (es - Uk_E)
    bad = ~ok & (SL < 0) & (SR > 0)
    if bad.any():
        UL, UR = conservative(L, ns), conservative(R, ns)
        hll = (SR[:, None] * FL - SL[:, None] * FR + (SL * SR)[:, None] * (UR - UL)) / (SR - SL)[:, None]
        F = np.where(bad[:, None], hll, F)
    F = np.where((SL >= 0)[:, None], FL, F)
    F = np.where((SR <= 0)[:, None], FR, F)
    return F, np.maximum(np.abs(SL), np.abs(SR)), int(bad.sum())


def _minmod(a, b):
    return np.where(a * b > 0, np.where(np.abs(a) < np.abs(b), a, b), 0.0)


def _van_leer(a, b):
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(a * b > 0, 2 * a * b / (a + b), 0.0)


def _monotonized_central(a, b):
    return _minmod(0.5 * (a + b), 2 * _minmod(a, b))


def _unlimited_central(a, b):
    """Verification only (not monotone): isolates limiter clipping in order studies."""
    return 0.5 * (a + b)


LIMITERS = {"minmod": _minmod, "van_leer": _van_leer, "mc": _monotonized_central,
            "unlimited_central": _unlimited_central}


class Duct:
    def __init__(self, name: str, mixture: Mixture, segments, dx_m: float, *,
                 wall: DuctWall | None = None, second_order: bool = True, limiter: str = "minmod"):
        if limiter not in LIMITERS:
            raise ValueError(f"limiter must be one of {sorted(LIMITERS)}")
        self.limiter = LIMITERS[limiter]
        mesh = segments_mesh(segments, dx_m)
        self.name, self.mix, self.ns = name, mixture, mixture.ns
        self.nv = self.ns + 3
        self.faces = np.array(mesh.faces)
        self.area = np.array(mesh.areas)
        self.volume = np.array(mesh.volumes)
        self.centers = np.array(mesh.centers)
        self.n = mesh.n
        self.dx = np.diff(self.faces)
        self.length = float(self.faces[-1])
        d = np.sqrt(4 * self.area / math.pi)
        self.diameter = 0.5 * (d[:-1] + d[1:])
        self.wall_area = math.pi * 0.5 * (d[:-1] + d[1:]) * np.sqrt(self.dx ** 2 + (0.5 * (d[1:] - d[:-1])) ** 2)
        self.dA = np.diff(self.area)
        self.wall = wall or DuctWall()
        self.second_order = second_order and self.n >= 3
        self._t_guess = None

    # ------------------------------------------------------------ states
    def uniform(self, p, T, Y, xb=0.0, u=0.0):
        Y = np.asarray(Y, dtype=float)
        rho = p / (self.mix.gas_constant(Y) * T)
        e = self.mix.internal_energy(Y, T)
        q = np.empty((self.n, self.nv))
        q[:, :self.ns] = rho * Y
        q[:, self.ns] = rho * xb
        q[:, self.ns + 1] = rho * u
        q[:, self.ns + 2] = rho * (e + 0.5 * u * u)
        return q

    def primitive(self, q):
        ns = self.ns
        rho_i = q[:, :ns]
        rho = rho_i.sum(axis=1)
        if not (np.all(rho > 0) and np.all(rho_i >= -1e-12 * rho[:, None])):
            raise InadmissibleState(f"{self.name}: negative density or species")
        Y = rho_i / rho[:, None]
        u = q[:, ns + 1] / rho
        e = q[:, ns + 2] / rho - 0.5 * u * u
        guess = self._t_guess if self._t_guess is not None and self._t_guess.shape == rho.shape else None
        pair = self.mix.coefficient_pair(Y)
        R = self.mix.gas_constant(Y)
        try:
            T = self.mix.temperature_from_energy(Y, e, guess, pair=pair, R=R)
        except ThermoError as exc:
            raise InadmissibleState(f"{self.name}: {exc}") from exc
        self._t_guess = T
        cp = self.mix.h_cp(pair, T)[1]
        gamma = cp / (cp - R)
        p = rho * R * T
        xb = q[:, ns] / rho
        return dict(rho=rho, u=u, p=p, T=T, Y=Y, xb=xb, E=q[:, ns + 2], R=R, cp=cp,
                    gamma=gamma, a=np.sqrt(gamma * R * T), h=e + R * T)

    def face_state(self, rho, u, p, Y, xb):
        R = self.mix.gas_constant(Y)
        T = p / (rho * R)
        h, cp = self.mix.h_cp(self.mix.coefficient_pair(Y), T)
        e = h - R * T
        gamma = cp / (cp - R)
        return dict(rho=rho, u=u, p=p, Y=Y, xb=xb, E=rho * (e + 0.5 * u * u), a=np.sqrt(gamma * R * T),
                    e0=self.mix.zero_kelvin_energy(Y))

    def _reconstruct(self, w):
        """Left/right states at the n-1 interior faces."""
        il, ir = slice(0, -1), slice(1, None)
        if not self.second_order:
            L ={k: w[k][il] for k in ("rho", "u", "p", "Y", "xb")}
            R = {k: w[k][ir] for k in ("rho", "u", "p", "Y", "xb")}
            return L, R
        h = np.diff(self.centers)
        xf = self.faces[1:-1]
        L, R = {}, {}
        for key in ("rho", "u", "p"):
            v = w[key]
            d = np.diff(v) / h
            slope = np.zeros(self.n)
            slope[1:-1] = self.limiter(d[:-1], d[1:])
            L[key] = v[:-1] + slope[:-1] * (xf - self.centers[:-1])
            R[key] = v[1:] + slope[1:] * (xf - self.centers[1:])
        bad = (L["rho"] <= 0) | (L["p"] <= 0) | (R["rho"] <= 0) | (R["p"] <= 0)
        if bad.any():
            for key in ("rho", "u", "p"):
                L[key] = np.where(bad, w[key][:-1], L[key])
                R[key] = np.where(bad, w[key][1:], R[key])
        for key in ("Y", "xb"):
            L[key], R[key] = w[key][il], w[key][ir]
        return L, R

    def interior_flux(self, w):
        if self.n < 2:
            return np.empty((0, self.nv)), np.empty(0), 0
        Lp, Rp = self._reconstruct(w)
        L = self.face_state(Lp["rho"], Lp["u"], Lp["p"], Lp["Y"], Lp["xb"])
        R = self.face_state(Rp["rho"], Rp["u"], Rp["p"], Rp["Y"], Rp["xb"])
        F, speeds, fallbacks = hllc(L, R, self.ns)
        return F * self.area[1:-1, None], speeds, fallbacks  # extensive

    def sources(self, w):
        """Per-cell extensive source (n, nv) and wall heat into gas (W)."""
        S = np.zeros((self.n, self.nv))
        S[:, self.ns + 1] = w["p"] * self.dA
        heat = 0.0
        if self.wall.friction or self.wall.heat_transfer:
            speed = np.abs(w["u"])
            mu = sutherland_viscosity_air(w["T"])
            cf = (fanning_friction(w["rho"] * speed * self.diameter / mu) if self.wall.friction_factor is None
                  else np.full_like(speed, self.wall.friction_factor))
            if self.wall.friction:
                S[:, self.ns + 1] -= cf * 0.5 * w["rho"] * w["u"] * speed * self.wall_area
            if self.wall.heat_transfer:
                hw = 0.5 * cf * w["rho"] * speed * w["cp"] * self.wall.prandtl ** (-2 / 3)
                q = hw * self.wall_area * (self.wall.temperature_K - w["T"])
                S[:, self.ns + 2] += q
                heat = float(q.sum())
        return S, heat

    def time_step_limit(self, w, face_speeds):
        cell = self.dx / (np.abs(w["u"]) + w["a"])
        faces = 2 * self.volume / (self.area[:-1] * face_speeds[:-1] + self.area[1:] * face_speeds[1:])
        return float(np.min(np.minimum(cell, faces)))

    def inventory(self, q):
        """Extensive totals: species masses (ns), tracer mass, momentum, energy."""
        return (q * self.volume[:, None]).sum(axis=0)
