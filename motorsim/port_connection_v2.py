"""Causal equivalent ideal-nozzle connection, opt-in candidate (not default).

The assumed divergent profile differs from V1's separated sudden expansion.
See transonic-contract-v2.md. Neither model is experimental validation.
"""
from dataclasses import dataclass
from functools import lru_cache
from math import isfinite, log, sqrt, ulp

from .gas1d.eos import IdealGas, InvalidState
from .gas1d.exact_riemann_reference_v1 import exact_riemann_v1, pressure_wave
from .port_restriction_v1 import (QuiescentVolumeStateV1, RestrictionGeometryV1,
                                  reservoir_restriction_v1)

SCHEMA = 'EQUIVALENT_IDEAL_NOZZLE_CONNECTION_CANDIDATE_V2'


class NoAdmissiblePortState(InvalidState):
    """No positive quasi-steady state in this explicit model; never a fallback."""


def root(f, lo, hi):
    a, b = f(lo), f(hi)
    if a == 0:
        return lo
    if b == 0:
        return hi
    if not isfinite(a) or not isfinite(b) or (a > 0) == (b > 0):
        raise NoAdmissiblePortState('no bracket for admissible nozzle branch')
    for _ in range(90):
        mid = (lo+hi)/2
        if mid in (lo, hi):
            break
        value = f(mid)
        if not isfinite(value):
            raise NoAdmissiblePortState('nonfinite nozzle residual')
        if value == 0:
            return mid
        if (value > 0) == (a > 0):
            lo, a = mid, value
        else:
            hi = mid
    return (lo+hi)/2


def area_mach(mach, gamma):
    return (2/(gamma+1)*(1+(gamma-1)*mach*mach/2))**(
        (gamma+1)/(2*(gamma-1)))/mach


@lru_cache(maxsize=4096)
def nozzle_mach_roots(area_ratio, gamma):
    if not isfinite(area_ratio) or area_ratio < 1:
        raise InvalidState('nozzle exit area must be at least the throat area')
    if area_ratio == 1:
        return 1., 1.
    low = root(lambda m: area_mach(m, gamma)-area_ratio, .1/area_ratio, 1.)
    hi = 2.
    while area_mach(hi, gamma) < area_ratio:
        hi *= 2
    high = root(lambda m: area_mach(m, gamma)-area_ratio, 1., hi)
    return low, high


def nozzle_state(p0, t0, mach, marker, eos):
    t = t0/(1+(eos.gamma-1)*mach*mach/2)
    p = p0*(t/t0)**(eos.gamma/(eos.gamma-1))
    return p/(eos.R*t), -mach*sqrt(eos.gamma*eos.R*t), p, marker


def normal_shock(state, eos):
    """Stationary entropy-admissible normal shock, sign of velocity retained."""
    r, u, p, marker = eos.validate(state)
    m2 = u*u/(eos.gamma*p/r)
    if m2 < 1-1e-12:
        raise InvalidState('normal shock requires supersonic upstream state')
    g = eos.gamma
    compression = (g+1)*m2/(2+(g-1)*m2)
    ratio = 1+2*g/(g+1)*(m2-1)
    return eos.validate((r*compression, u/compression, p*ratio, marker))


def total_state(state, eos):
    rho, u, p, _ = state
    t = p/(rho*eos.R)
    t0 = t+u*u/(2*eos.cp)
    return p*(t0/t)**(eos.gamma/(eos.gamma-1)), t0


@dataclass(frozen=True)
class PortExchangeV2:
    flux_x: tuple
    outward: tuple
    wave_speeds: tuple
    boundary_state: tuple
    branch: str
    throat_mach: float
    throat_pressure_pa: float | None
    duct_area_m2: float
    effective_area_m2: float
    acoustic_velocity_residual_m_s: float | None
    boundary_total_pressure_pa: float
    shock_area_ratio: float | None
    causality_rightmost_speed_m_s: float | None
    fallback_reason: str | None = None
    schema: str = SCHEMA


def port_connection_v2(chamber, interior, effective_area_m2, duct_area_m2,
                       normal, *, eos=None):
    eos = eos or IdealGas()
    eos.validate(interior)
    _, pc, tc, yc = chamber.thermodynamics(eos)
    if type(normal) is not int or normal not in (-1, 1):
        raise InvalidState('normal must be -1 or +1')
    if any(type(a) not in (int, float) or not isfinite(a)
           for a in (effective_area_m2, duct_area_m2)):
        raise InvalidState('areas must be finite real numbers')
    at, ap = effective_area_m2, duct_area_m2
    if ap <= 0 or not 0 <= at <= ap:
        raise InvalidState('require 0 <= throat area <= positive pipe area')
    rhoi, ui, pi, yi = interior
    wi = normal*ui
    g, gas_r, cp = eos.gamma, eos.R, eos.cp
    ai = eos.sound_speed(interior)
    inside = (rhoi, wi, pi, yi)

    def wave(p):
        f, rho = pressure_wave(p, inside, eos)
        return wi-f, rho

    def finish(state, branch, mt=0., pt=None, shock_area=None, causal=None,
               acoustic=True):
        rho, w, p, marker = eos.validate(state)
        physical = (rho, normal*w, p, marker)
        flux = tuple(ap*x for x in eos.flux(physical))
        if not all(isfinite(x) for x in flux):
            raise NoAdmissiblePortState('nonfinite nozzle flux')
        a = eos.sound_speed(state)
        p0, _ = total_state(state, eos)
        return PortExchangeV2(flux, tuple(normal*x for x in flux),
            (physical[1]-a, physical[1], physical[1]+a), physical, branch,
            mt, pt, ap, at, wave(p)[0]-w if acoustic else None, p0,
            shock_area, causal)

    # Exact zero-flow pressure on the incoming Euler wave, including reflection.
    if wave(0.)[0] <= 0:
        if at == 0:
            raise NoAdmissiblePortState('closed wall reflection generates vacuum')
        p_zero = None
    else:
        upper = pi
        while wave(upper)[0] > 0:
            upper *= 2
            if not isfinite(upper):
                raise NoAdmissiblePortState('wall wave pressure exceeds finite range')
        p_zero = root(lambda p: wave(p)[0], 0., upper)
    if at == 0:
        _, rho = wave(p_zero)
        return finish((rho, 0., p_zero, yi), 'CLOSED_REFLECTED_WALL')
    if wi == 0 and pi == pc:
        return finish((rhoi, 0., pi, yi), 'EQUILIBRIUM')

    if wave(pc)[0] > 0:
        # Pipe donor: subsonic face, or an upstream-moving unstart shock.
        if wi >= ai:
            lower = max(pc, normal_shock(inside, eos)[2])
        else:
            a_sonic = (wi+2*ai/(g-1))*(g-1)/(g+1)
            if a_sonic <= 0:
                raise NoAdmissiblePortState('no positive outgoing sonic state')
            p_sonic = pi*(a_sonic/ai)**(2*g/(g-1))
            lower = max(pc, p_sonic)

        def out_state(p):
            w, rho = wave(p)
            state = (rho, w, p, yi)
            p0, t0 = total_state(state, eos)
            restriction = reservoir_restriction_v1(
                QuiescentVolumeStateV1(p0, t0, (1.,0.,0.,0.)),
                QuiescentVolumeStateV1(pc, tc, (1.,0.,0.,0.)),
                RestrictionGeometryV1(at, 1., 1.), eos=eos)
            return state, restriction

        def residual(p):
            state, restriction = out_state(p)
            return ap*state[0]*state[1]-restriction.mass_rate_kg_s

        if wi >= ai and residual(lower) <= 0:
            # No shock can propagate upstream through this supersonic outflow.
            # The contraction and/or a downstream shock are outside the pipe.
            p0, t0 = total_state(inside, eos)
            q = ap*rhoi*wi
            tcrit = t0*2/(g+1)
            pcrit = p0*(2/(g+1))**(g/(g-1))
            astar = q/(pcrit/(gas_r*tcrit)*sqrt(g*gas_r*tcrit))
            if at < astar*(1-1e-12):
                raise NoAdmissiblePortState('supersonic contraction has insufficient throat area')
            _, mt = nozzle_mach_roots(max(1., at/astar), g)
            pt = p0*(1+(g-1)*mt*mt/2)**(-g/(g-1))
            return finish(inside, 'OUTFLOW_SUPERSONIC_TRANSMITTED', mt, pt,
                          acoustic=False)
        if p_zero is None or lower > p_zero:
            raise NoAdmissiblePortState('no admissible upstream outflow shock')
        rlow = residual(lower)
        scale = max(ap*wave(lower)[1]*abs(wave(lower)[0]), 1e-300)
        if abs(rlow) <= 1e-13*scale:
            p = lower
        else:
            p = root(residual, lower, p_zero)
        state, restriction = out_state(p)
        branch = ('OUTFLOW_UNSTART_SHOCK_' if wi >= ai else 'OUTFLOW_')+restriction.branch
        return finish(state, branch, restriction.throat_mach,
                      restriction.throat_pressure_pa)

    # Chamber donor. The ideal nozzle's subsonic exit branch has no entropy loss.
    msub, msup = nozzle_mach_roots(ap/at, g)
    sub = nozzle_state(pc, tc, msub, yc, eos)
    pmin = sub[2]

    if wave(pmin)[0]-sub[1] >= 0:
        # Mach parameter avoids subtracting nearly equal stagnation/static T
        # and keeps the critical endpoint identical in branch and root tests.
        def residual(m):
            state = nozzle_state(pc,tc,m,yc,eos)
            return wave(state[2])[0]-state[1]
        m = root(residual, 0., msub)
        state = nozzle_state(pc,tc,m,yc,eos)
        q = -ap*state[0]*state[1]
        # Infer subsonic throat Mach from mass, not pipe Mach.
        tcrit = tc*2/(g+1)
        pcrit = pc*(2/(g+1))**(g/(g-1))
        qcrit = at*pcrit/(gas_r*tcrit)*sqrt(g*gas_r*tcrit)
        if q == 0:
            mt = 0.
        elif at == ap:
            mt = m
        elif m == msub:
            mt = 1.
        else:
            # Normalize to the same computed critical pipe endpoint. This
            # avoids an above-one quotient from independently rounded areas.
            ratio = area_mach(msub,g)/area_mach(m,g)
            mt = root(lambda mt: 1/area_mach(mt,g)-ratio, .1*ratio, 1.)
        pt = pc*(1+(g-1)*mt*mt/2)**(-g/(g-1))
        return finish(state, 'INFLOW_ISENTROPIC_SUBSONIC', mt, pt)

    # Choked throat. Internal shock position is determined by entropy loss.
    jet = nozzle_state(pc, tc, msup, yc, eos)
    after = normal_shock(jet, eos)
    q = -ap*jet[0]*jet[1]
    throat_p = pc*(2/(g+1))**(g/(g-1))

    def choked(v):
        t = tc-v*v/(2*cp)
        if t <= 0 or v <= 0:
            raise NoAdmissiblePortState('nonpositive choked temperature or velocity')
        rho = q/(ap*v)
        return rho, -v, rho*gas_r*t, yc

    def residual(v):
        state = choked(v)
        return wave(state[2])[0]+v

    vlow, vhigh = -sub[1], -after[1]
    # At the shared analytic endpoint, two independently rounded forms of p
    # may differ by ULPs. Accept ONLY a bounded floating-point residual, never
    # a physical pressure/flow deadband or a clipped mass rate.
    if 0 < residual(vlow) <= 64*ulp(max(ai,abs(wi),vlow)):
        return finish(choked(vlow), 'INFLOW_CHOKED_ONSET', 1., throat_p, 1.)
    if residual(vhigh) >= 0 and vhigh > vlow:
        v = root(residual, vlow, vhigh)
        state = choked(v)
        p0, _ = total_state(state, eos)

        def loss(m):
            post = normal_shock(nozzle_state(pc, tc, m, yc, eos), eos)
            return log(total_state(post, eos)[0]/pc)

        # Match the stagnation-pressure ratio rather than choosing a shock.
        target = log(p0/pc)
        low_loss, high_loss = loss(1.), loss(msup)
        if target > low_loss+1e-11 or target < high_loss-1e-11:
            raise NoAdmissiblePortState('choked state cannot be produced by an internal shock')
        if abs(target-low_loss) < 1e-13:
            shock_m = 1.
        elif abs(target-high_loss) < 1e-13:
            shock_m = msup
        else:
            shock_m = root(lambda m: loss(m)-target, 1., msup)
        return finish(state, 'INFLOW_CHOKED_INTERNAL_SHOCK', 1., throat_p,
                      area_mach(shock_m,g))

    # Supersonic/sonic source is legal only if no information escapes the pipe.
    rp = exact_riemann_v1(inside, jet, eos=eos)
    speed = max(*rp.left_speeds, rp.velocity, *rp.right_speeds)
    if speed > 1e-10*max(ai, eos.sound_speed(jet)):
        raise NoAdmissiblePortState('supersonic nozzle exit incompatible with downstream waves')
    return finish(jet, 'INFLOW_CHOKED_SUPERSONIC' if msup > 1 else 'INFLOW_CHOKED_SONIC',
                  1., throat_p, causal=speed, acoustic=False)
