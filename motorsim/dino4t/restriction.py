"""Duct-end boundary through a flow restriction into a 0D volume.

Model ``QUASI_STEADY_RESTRICTION_V1`` (STANDARD_V1).  One restriction law is
used for poppet valves, open pipe ends (bellmouth/plain end into a reservoir)
and closed ends (zero area).  At the duct end face two relations are
imposed and solved for the face static pressure p_f:

1. Duct side - the characteristic arriving from the interior cell c,
   isentropic simple-wave relation with the cell's frozen gamma:
       w_f = w_c + 2 a_c/(g_c-1) [ (p_f/p_c)^((g_c-1)/(2 g_c)) - 1 ]
   where w is the velocity component pointing from the volume INTO the duct.
2. Restriction - quasi-steady compressible orifice flow (Heywood 1988,
   App. C) through the effective area, from the upstream stagnation state to
   the downstream static pressure:
     volume -> duct  (p_v > p_f): upstream (p_v, T_v), downstream p_f
     duct -> volume  (p_f > p_v): upstream (p_f, T0_c), downstream p_v
   (the duct-side dynamic head is not recovered, consistent with a sudden
   expansion; both branches give zero flow at p_f = p_v, so the residual is
   continuous and strictly monotone in p_f -> unique bracketed root).

Mass continuity at the duct face closes the system: A_pipe rho_f w_f = mdot.
Face density comes from the donor: volume gas with h_v = h_f + w_f^2/2
(volume -> duct) or isentropic cell gas (duct -> volume).

Conservation: the extensive face flux and the volume exchange are the same
numbers with opposite sign (mass, species, tracer, energy).  Energy is carried
as mdot * h0_donor with the exact mixture enthalpy (formation included);
frozen gamma is used only inside the orifice/characteristic relations.
The difference between the throat and duct kinetic energy is dissipated
into internal energy (Borda-Carnot), so the scheme generates the expected
entropy without any energy leak.
"""
from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as np
from scipy.optimize import brentq


class RestrictionError(ValueError):
    pass


@dataclass(frozen=True)
class VolumeGas:
    """Quiescent donor/receiver state of a 0D volume (cylinder, plenum, ambient)."""
    p: float
    T: float
    Y: np.ndarray
    xb: float
    h: float
    R: float
    cp: float

    @property
    def gamma(self):
        return self.cp / (self.cp - self.R)

    @classmethod
    def from_mixture(cls, mixture, p, T, Y, xb):
        Y = np.asarray(Y, dtype=float)
        return cls(p, T, Y, xb, float(mixture.enthalpy(Y, T)), float(mixture.gas_constant(Y)),
                   float(mixture.cp(Y, T)))


def psi(pressure_ratio: float, gamma: float) -> float:
    """Dimensionless orifice mass flux: mdot = A p0/sqrt(R T0) * psi."""
    critical = (2 / (gamma + 1)) ** (gamma / (gamma - 1))
    if pressure_ratio <= critical:
        return math.sqrt(gamma) * (2 / (gamma + 1)) ** ((gamma + 1) / (2 * (gamma - 1)))
    if pressure_ratio >= 1.0:
        return 0.0
    return math.sqrt(2 * gamma / (gamma - 1) * (pressure_ratio ** (2 / gamma)
                                                 - pressure_ratio ** ((gamma + 1) / gamma)))


def orifice_mass_flow(area, p0, T0, R, gamma, p_down):
    return area * p0 / math.sqrt(R * T0) * psi(p_down / p0, gamma)


@dataclass
class EndCell:
    rho: float
    u: float
    p: float
    T: float
    Y: np.ndarray
    xb: float
    R: float
    cp: float
    gamma: float
    a: float
    h: float

    @classmethod
    def from_primitive(cls, w, index):
        return cls(*(float(w[k][index]) for k in ("rho", "u", "p", "T")), w["Y"][index],
                   float(w["xb"][index]), *(float(w[k][index]) for k in ("R", "cp", "gamma", "a", "h")))


@dataclass
class RestrictionResult:
    flux_x: np.ndarray        # extensive face flux along duct +x (nv,)
    to_volume: np.ndarray     # rates into the volume: species (ns), tracer, energy
    mdot_into_duct: float
    p_face: float
    mach_face: float
    choked: bool
    branch: str


def restriction_flux(cell: EndCell, side: str, pipe_area: float, area_into_duct: float,
                     area_out_of_duct: float, vol: VolumeGas, ns: int, *,
                     stagnation: bool = True) -> RestrictionResult:
    """``stagnation=True`` is QUASI_STEADY_RESTRICTION_V2: the duct->volume orifice is fed
    with the face *stagnation* state.  ``stagnation=False`` reproduces V1 (face static
    pressure used as total pressure), kept only to reproduce the stage-1 evidence."""
    if side not in ("left", "right"):
        raise ValueError("side must be left or right")
    n_in = 1.0 if side == "left" else -1.0
    g, ac, pc = cell.gamma, cell.a, cell.p
    wc = n_in * cell.u
    k = (g - 1) / (2 * g)
    nv = ns + 3

    def w_of_p(p):
        return wc + 2 * ac / (g - 1) * ((p / pc) ** k - 1.0)

    def assemble(p_f, mdot, rho_f, branch, choked):
        w_f = mdot / (rho_f * pipe_area) if mdot != 0 else 0.0
        if mdot >= 0:
            Yd, xd, h0 = vol.Y, vol.xb, vol.h
            a_f = math.sqrt(vol.gamma * vol.R * max(vol.T - w_f * w_f / (2 * vol.cp), 1.0))
        else:
            if stagnation:
                T_f = p_f / (rho_f * cell.R)
                h0 = cell.h + cell.cp * (T_f - cell.T) + 0.5 * w_f * w_f
            else:
                h0 = cell.h + 0.5 * cell.u ** 2
            Yd, xd = cell.Y, cell.xb
            a_f = ac * (p_f / pc) ** k
        mass_x = n_in * mdot
        F = np.empty(nv)
        F[:ns] = mass_x * Yd
        F[ns] = mass_x * xd
        F[ns + 1] = mass_x * (n_in * w_f) + p_f * pipe_area
        F[ns + 2] = mass_x * h0
        to_vol = np.empty(ns + 2)
        to_vol[:ns] = -mdot * Yd
        to_vol[ns] = -mdot * xd
        to_vol[ns + 1] = -mdot * h0
        return RestrictionResult(F, to_vol, mdot, p_f, abs(w_f) / a_f, choked, branch)

    if wc <= -ac:  # supersonic outflow from the duct: no incoming characteristic
        mdot = cell.rho * wc * pipe_area
        return assemble(cell.p, mdot, cell.rho, "supersonic_outflow", True)

    if area_into_duct <= 0.0 and area_out_of_duct <= 0.0:
        base = 1.0 - (g - 1) / 2 * wc / ac
        if base <= 0:
            raise RestrictionError("closed end: rarefaction to vacuum")
        p_f = pc * base ** (2 * g / (g - 1))
        return assemble(p_f, 0.0, cell.rho, "closed", False)

    T0c = cell.T + 0.5 * cell.u ** 2 / cell.cp
    gv, Rv, Tv, pv = vol.gamma, vol.R, vol.T, vol.p
    crit_v = (2 / (gv + 1)) ** (gv / (gv - 1))
    crit_c = (2 / (g + 1)) ** (g / (g - 1))

    def face_mass_flux(p):
        w = w_of_p(p)
        if w >= 0:
            T_f = Tv - w * w / (2 * vol.cp)
            if T_f <= 0.05 * Tv:
                return 1e30, w, 0.0
            rho_f = p / (Rv * T_f)
        else:
            rho_f = cell.rho * (p / pc) ** (1 / g)
        return rho_f * w * pipe_area, w, rho_f

    def orifice(p):
        if stagnation:
            w = w_of_p(p)
            T_f = cell.T * (p / pc) ** ((g - 1) / g)
            if w < 0:
                T0 = T_f + 0.5 * w * w / cell.cp
                p0 = p * (T0 / T_f) ** (g / (g - 1))
            else:
                T0, p0 = T_f, p
            if p0 > pv:
                return -orifice_mass_flow(area_out_of_duct, p0, T0, cell.R, g, pv) if area_out_of_duct > 0 else 0.0
            return orifice_mass_flow(area_into_duct, pv, Tv, Rv, gv, p) if area_into_duct > 0 else 0.0
        if p <= pv:
            return orifice_mass_flow(area_into_duct, pv, Tv, Rv, gv, p) if area_into_duct > 0 else 0.0
        return -orifice_mass_flow(area_out_of_duct, p, T0c, cell.R, g, pv) if area_out_of_duct > 0 else 0.0

    def residual(s):
        p = math.exp(s)
        return face_mass_flux(p)[0] - orifice(p)

    lo, hi = math.log(0.5 * min(pc, pv)), math.log(2.0 * max(pc, pv))
    xs = (2.0 - (g - 1) * wc / ac) / (g + 1) if stagnation else 0.0
    if xs > 0.0:
        # V2 residual has spurious roots with a supersonic face (M > 1).  The admissible
        # branch starts at the sonic face state, closed form from the incoming characteristic.
        p_sonic = pc * xs ** (1.0 / k)
        lo = math.log(p_sonic)
        if residual(lo) >= 0.0:
            # the orifice would pass more than the duct can deliver: duct end is choked
            m_sonic, _, rho_sonic = face_mass_flux(p_sonic)
            return assemble(p_sonic, m_sonic, rho_sonic, "duct_to_volume", True)
    else:
        for _ in range(60):
            if residual(lo) < 0:
                break
            lo -= 0.7
        else:
            raise RestrictionError("restriction root not bracketed below")
    for _ in range(60):
        if residual(hi) > 0:
            break
        hi += 0.7
    else:
        raise RestrictionError("restriction root not bracketed above")
    s = brentq(residual, lo, hi, xtol=1e-15, rtol=4 * np.finfo(float).eps, maxiter=200)
    p_f = math.exp(s)
    mdot = orifice(p_f)
    _, w, rho_f = face_mass_flux(p_f)
    if mdot >= 0:
        choked = area_into_duct > 0 and p_f / pv <= crit_v
        rho_f = p_f / (Rv * max(Tv - w * w / (2 * vol.cp), 1e-3))
        branch = "volume_to_duct"
    else:
        p_up = p_f
        if stagnation:
            m_f = abs(w) / (ac * (p_f / pc) ** k)
            p_up = p_f * (1 + 0.5 * (g - 1) * m_f * m_f) ** (g / (g - 1))
        choked = area_out_of_duct > 0 and pv / p_up <= crit_c
        branch = "duct_to_volume"
    result = assemble(p_f, mdot, rho_f, branch, choked)
    if stagnation and branch == "volume_to_duct" and result.mach_face > 1.0 + 1e-9:
        # a single incoming characteristic cannot represent supersonic inflow through an
        # unobstructed opening (that needs a nozzle): fail closed instead of returning M > 1.
        # Outside the full-engine envelope of the example (max inflow M_face = 0.6, see audit).
        raise RestrictionError(f"supersonic inflow face (M={result.mach_face:.3f}): outside model validity")
    return result
