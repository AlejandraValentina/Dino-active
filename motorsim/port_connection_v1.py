"""Candidate adiabatic chamber/throat/duct connection; not enabled in product.

See the preregistered connection-contract.md for assumptions and domain. In
particular, a choked throat does not imply a sonic mean flow in a larger duct.
"""
from dataclasses import dataclass
from math import isfinite, sqrt

from .coupling import ChamberState
from .gas1d.eos import IdealGas, InvalidState
from .port_restriction_v1 import (QuiescentVolumeStateV1, RestrictionGeometryV1,
                                  reservoir_restriction_v1)

SCHEMA = "ADIABATIC_PORT_CONNECTION_CANDIDATE_V1"


class PortDomainError(InvalidState):
    """The candidate has no supported admissible boundary state."""


@dataclass(frozen=True)
class PortExchangeV1:
    flux_x: tuple
    outward: tuple
    wave_speeds: tuple
    boundary_state: tuple
    branch: str
    throat_mach: float
    throat_pressure_pa: float | None
    duct_area_m2: float
    effective_area_m2: float
    acoustic_velocity_residual_m_s: float
    boundary_total_pressure_pa: float
    fallback_reason: str | None = None
    schema: str = SCHEMA


def _bisect(function, lo, hi):
    a, b = function(lo), function(hi)
    if a == 0:
        return lo
    if b == 0:
        return hi
    if not isfinite(a) or not isfinite(b) or (a > 0) == (b > 0):
        raise PortDomainError("port boundary root is not bracketed")
    for _ in range(80):
        mid = (lo + hi) * .5
        if mid == lo or mid == hi:
            break
        f = function(mid)
        if not isfinite(f):
            raise PortDomainError("nonfinite port boundary residual")
        if f == 0:
            return mid
        if (f > 0) == (a > 0):
            lo, a = mid, f
        else:
            hi = mid
    return (lo + hi) * .5


def port_connection_v1(chamber: ChamberState, interior: tuple,
                       effective_area_m2: float, duct_area_m2: float, normal: int,
                       *, eos: IdealGas | None = None) -> PortExchangeV1:
    """Return a FULL duct-face flux; do not add blocked-area traction twice.

    Inputs are not changed. No silent fallback to equal-section HLLC is allowed.
    The model supports subsonic interior states and sonic boundary limits only.
    """
    eos = eos or IdealGas()
    eos.validate(interior)
    _, pc, tc, yc = chamber.thermodynamics(eos)
    if normal not in (-1, 1) or type(normal) is bool:
        raise InvalidState("normal must be -1 or +1")
    for area in (effective_area_m2, duct_area_m2):
        if type(area) not in (int, float) or not isfinite(area):
            raise InvalidState("port areas must be finite real numbers")
    if duct_area_m2 <= 0 or not 0 <= effective_area_m2 <= duct_area_m2:
        raise InvalidState("require 0 <= effective throat area <= positive duct area")
    rhoi, ui, pi, yi = interior
    wi = normal * ui
    ai = eos.sound_speed(interior)
    g, gas_r, cp = eos.gamma, eos.R, eos.cp
    ap, at = duct_area_m2, effective_area_m2

    def wave(pressure):
        ratio = pressure / pi
        if pressure <= pi:
            f = 2*ai/(g-1)*(ratio**((g-1)/(2*g))-1)
            rho = rhoi*ratio**(1/g)
        else:
            f = (pressure-pi)*sqrt(2/((g+1)*rhoi)/(pressure+(g-1)/(g+1)*pi))
            rho = rhoi*(ratio+(g-1)/(g+1))/((g-1)/(g+1)*ratio+1)
        return wi-f, rho

    def finish(rho, w, pressure, marker, branch, mt=0., pt=None, h0=None):
        u = normal*w
        state = eos.validate((rho, u, pressure, marker))
        sound = eos.sound_speed(state)
        if abs(w) > sound*(1+1e-10):
            raise PortDomainError("candidate boundary bulk flow is supersonic")
        temp = pressure/(rho*gas_r)
        total_t = temp+w*w/(2*cp)
        total_p = pressure*(total_t/temp)**(g/(g-1))
        acoustic_residual = wave(pressure)[0]-w
        mass_x = ap*rho*u
        total_enthalpy = cp*total_t if h0 is None else h0
        energy_x = mass_x*total_enthalpy
        momentum_x = ap*(rho*u*u+pressure)
        flux = (mass_x, momentum_x, energy_x, mass_x*marker)
        if not all(isfinite(x) for x in flux):
            raise PortDomainError("nonfinite port flux")
        return PortExchangeV1(flux, tuple(normal*x for x in flux),
            (u-sound, u, u+sound), state, branch, mt, pt, ap, at,
            acoustic_residual, total_p)

    if at == 0:
        return finish(rhoi, 0., pi, yi, "CLOSED")
    if abs(wi) >= ai:
        raise PortDomainError("candidate requires a subsonic duct interior")
    if wi == 0 and pi == pc:
        return finish(rhoi, 0., pi, yi, "EQUILIBRIUM")

    # Pressure at zero velocity, including a possible compression shock.
    hi = pi
    while wave(hi)[0] > 0:
        hi *= 2
    p_zero = _bisect(lambda p: wave(p)[0], 0., hi)
    w_at_pc = wave(pc)[0]
    if w_at_pc > 0:
        # Pipe donor contracts isentropically to a restriction before mixing
        # into the receiving chamber. Solve on the subsonic pipe branch.
        sonic_sound = (wi+2*ai/(g-1))*(g-1)/(g+1)
        p_sonic = pi*(sonic_sound/ai)**(2*g/(g-1))
        low = max(pc, p_sonic)

        def out_state(p):
            w, rho = wave(p)
            temp = p/(rho*gas_r)
            t0 = temp+w*w/(2*cp)
            p0 = p*(t0/temp)**(g/(g-1))
            nozzle = reservoir_restriction_v1(
                QuiescentVolumeStateV1(p0, t0, (1.,0.,0.,0.)),
                QuiescentVolumeStateV1(pc, tc, (1.,0.,0.,0.)),
                RestrictionGeometryV1(at, 1., 1.), eos=eos)
            return w, rho, nozzle

        def residual(p):
            w, rho, nozzle = out_state(p)
            return ap*rho*w-nozzle.mass_rate_kg_s

        r_low = residual(low)
        scale = ap*wave(low)[1]*max(wave(low)[0], 1.)
        if abs(r_low) < 1e-13*scale:
            p = low
        else:
            p = _bisect(residual, low, p_zero)
        w, rho, nozzle = out_state(p)
        return finish(rho, w, p, yi, "OUTFLOW_"+nozzle.branch,
                      nozzle.throat_mach, nozzle.throat_pressure_pa)

    if w_at_pc == 0:
        return finish(pc/(gas_r*tc), 0., pc, yc, "EQUILIBRIUM")

    def inflow_mixing(mt):
        tt = tc/(1+(g-1)*mt*mt/2)
        pt = pc*(tt/tc)**(g/(g-1))
        vt = mt*sqrt(g*gas_r*tt)
        q = at*pt/(gas_r*tt)*vt
        if at == ap:
            return pt, vt, pt/(gas_r*tt), q, pt
        b = ap*pt+q*vt
        discriminant = b*b-4*(g+1)/(2*g)*q*q*gas_r*tc
        if discriminant < 0:
            raise PortDomainError("negative mixing quadratic discriminant")
        v = 2*q*gas_r*tc/(b+sqrt(discriminant))
        p = pt+q*(vt-v)/ap
        t = tc-v*v/(2*cp)
        if t <= 0:
            raise PortDomainError("inadmissible mixing temperature")
        return p, v, p/(gas_r*t), q, pt

    def in_residual(mt):
        p, v, _, _, _ = inflow_mixing(mt)
        return wave(p)[0]+v

    if in_residual(1.) >= 0:
        mt = _bisect(in_residual, 0., 1.)
        p, v, rho, q, pt = inflow_mixing(mt)
        result = finish(rho, -v, p, yc, "INFLOW_SUBSONIC", mt, pt, cp*tc)
    else:
        # Sonic throat: match mass and energy to the pipe acoustic curve.
        tt = tc*2/(g+1)
        throat_p = pc*(2/(g+1))**(g/(g-1))
        throat_speed = sqrt(g*gas_r*tt)
        q = at*throat_p/(gas_r*tt)*throat_speed
        if at == ap:
            return finish(throat_p/(gas_r*tt), -throat_speed, throat_p, yc,
                          "INFLOW_CHOKED_SONIC_FACE", 1., throat_p, cp*tc)
        upper = max(pc, pi)
        while wave(upper)[0] > -throat_speed:
            upper *= 2
        p_limit = _bisect(lambda p: wave(p)[0]+throat_speed, p_zero, upper)

        def choked_residual(p):
            v = -wave(p)[0]
            t = tc-v*v/(2*cp)
            return ap*p*v/(gas_r*t)-q

        if choked_residual(p_limit) < 0:
            raise PortDomainError("choked throat requires unsupported supersonic duct face")
        p = _bisect(choked_residual, p_zero, p_limit)
        v = -wave(p)[0]
        t = tc-v*v/(2*cp)
        result = finish(p/(gas_r*t), -v, p, yc, "INFLOW_CHOKED", 1., throat_p, cp*tc)
    if result.boundary_total_pressure_pa > pc*(1+1e-10):
        raise PortDomainError("port inflow would decrease donor entropy")
    return result
