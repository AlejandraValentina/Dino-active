"""Causal equivalent ideal-nozzle connection, opt-in candidate (not default).

The assumed divergent profile differs from V1's separated sudden expansion.
See transonic-contract-v2.md. Neither model is experimental validation.
"""
from dataclasses import dataclass
from functools import lru_cache
from math import exp, isfinite, log, log1p, sqrt, ulp

from .gas1d.eos import IdealGas, InvalidState
from .gas1d.exact_riemann_reference_v1 import (
    _pressure_wave_prevalidated,
    exact_riemann_v1,
)

SCHEMA = 'EQUIVALENT_IDEAL_NOZZLE_CONNECTION_CANDIDATE_V2'


class NoAdmissiblePortState(InvalidState):
    """No positive quasi-steady state in this explicit model; never a fallback."""


def root(f, lo, hi, *, nonpositive_endpoint=False):
    """Deterministic 90-step bisection (default nozzle solver)."""
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
    if nonpositive_endpoint:
        return lo if f(lo) <= 0 else hi
    return (lo+hi)/2


def _brent_root(f, lo, hi, *, nonpositive_endpoint=False):
    """Opt-in bracketed Brent root with the original endpoint contract.

    Used only when ``port_connection_v2(..., root_solver='brent')`` is set by
    the bounded E2 candidate harness. The default remains deterministic
    bisection so no production path changes silently.
    """
    fa, fb = f(lo), f(hi)
    if fa == 0:
        return lo
    if fb == 0:
        return hi
    if not isfinite(fa) or not isfinite(fb) or (fa > 0) == (fb > 0):
        raise NoAdmissiblePortState('no bracket for admissible nozzle branch')
    f_lo = fa
    xlo, xhi = lo, hi
    fxlo = fa
    a, b = lo, hi
    c, fc = a, fa
    d = e = b-a
    eps = 2.220446049250313e-16
    for _ in range(100):
        if (fb > 0 and fc > 0) or (fb < 0 and fc < 0):
            c, fc = a, fa
            d = e = b-a
        if abs(fc) < abs(fb):
            a, b, c = b, c, b
            fa, fb, fc = fb, fc, fb
        tol = 2*eps*abs(b)
        m = 0.5*(c-b)
        if abs(m) <= tol or fb == 0:
            break
        if abs(e) < tol or abs(fa) <= abs(fb):
            d = e = m
        else:
            s = fb/fa
            if a == c:
                p = 2*m*s
                q = 1-s
            else:
                q = fa/fc
                r = fb/fc
                p = s*(2*m*q*(q-r)-(b-a)*(r-1))
                q = (q-1)*(r-1)*(s-1)
            if p > 0:
                q = -q
            else:
                p = -p
            s = e
            e = d
            if 2*p < 3*m*q-abs(tol*q) and p < abs(0.5*s*q):
                d = p/q
            else:
                d = e = m
        a, fa = b, fb
        if abs(d) > tol:
            b += d
        elif m > 0:
            b += tol
        else:
            b -= tol
        fb = f(b)
        if not isfinite(fb):
            raise NoAdmissiblePortState('nonfinite nozzle residual')
        if xlo < b < xhi:
            if (fb > 0) == (f_lo > 0):
                xlo, fxlo = b, fb
            else:
                xhi = b
    if nonpositive_endpoint:
        return xlo if fxlo <= 0 else xhi
    return b


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
                       normal, *, eos=None, root_solver='bisection'):
    eos = eos or IdealGas()
    if root_solver not in ('bisection', 'brent'):
        raise InvalidState("root_solver must be 'bisection' or 'brent'")
    solve = _brent_root if root_solver == 'brent' else root
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
        f, rho = _pressure_wave_prevalidated(p, inside, g, ai)
        return wi-f, rho

    def finish(state, branch, mt=0., pt=None, shock_area=None, causal=None,
               acoustic=True, wave_signals=()):
        rho, w, p, marker = eos.validate(state)
        physical = (rho, normal*w, p, marker)
        flux = tuple(ap*x for x in eos.flux(physical))
        if not all(isfinite(x) for x in flux):
            raise NoAdmissiblePortState('nonfinite nozzle flux')
        a = eos.sound_speed(state)
        p0, _ = total_state(state, eos)
        # Include waves traversing the *interior* gas as well as face-state
        # characteristics. A hot interior shocked by colder donor gas can
        # have a faster signal than |u_face|+a_face alone.
        signals = [physical[1]-a,physical[1]+a,ui-ai,ui+ai]
        if acoustic:
            left_speed = (wi-ai*sqrt((g+1)/(2*g)*p/pi+(g-1)/(2*g))
                          if p>pi else wi-ai)
            signals.append(normal*left_speed)
        signals.extend(normal*v for v in wave_signals)
        return PortExchangeV2(flux, tuple(normal*x for x in flux),
            (min(signals), physical[1], max(signals)), physical, branch,
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
        p_zero = solve(lambda p: wave(p)[0], 0., upper)
    if at == 0:
        _, rho = wave(p_zero)
        return finish((rho, 0., p_zero, yi), 'CLOSED_REFLECTED_WALL')
    if wi == 0 and pi == pc:
        return finish((rhoi, 0., pi, yi), 'EQUILIBRIUM')

    if wave(pc)[0] > 0:
        # Invert area-Mach and pressure relations, not the tiny stagnation-
        # pressure difference. The latter loses digits as velocity tends to
        # zero and spuriously destroys the outflow bracket at full pipe area.
        msub, _ = nozzle_mach_roots(ap/at,g)
        msub_area = area_mach(msub,g)

        def pipe(p):
            w,rho = wave(p)
            if p==p_zero:
                w=0.  # The analytic zero-velocity endpoint, not a deadband.
            return rho,w,p,yi

        def mach(state):
            return state[1]/eos.sound_speed(state)

        def throat(p, critical=False):
            state = pipe(p)
            mb = mach(state)
            if critical:
                mt = 1.
            elif mb == 0:
                mt = 0.
            elif at == ap:
                mt = mb
            else:
                ratio = msub_area/area_mach(mb,g)
                if ratio > 1:
                    if ratio-1 > 64*ulp(1.):
                        raise NoAdmissiblePortState('outflow exceeds contraction capacity')
                    mt = 1.  # ULP-only inversion of the critical endpoint.
                else:
                    mt = solve(lambda m: 1/area_mach(m,g)-ratio,.1*ratio,1.)
            pt = p if at==ap else p*exp(g/(g-1)*(
                log1p((g-1)*mb*mb/2)-log1p((g-1)*mt*mt/2)))
            return state,mt,pt

        pcritical = None
        if wi >= ai:
            lower = normal_shock(inside, eos)[2]
            if mach(pipe(lower)) > msub:
                pcritical = solve(lambda p: mach(pipe(p))-msub,lower,p_zero,
                                  nonpositive_endpoint=True)
            elif pc <= throat(lower)[2]:
                # A stationary or downstream-moving shock lies beyond the
                # pipe, so chamber data cannot change its supersonic face.
                p0,t0 = total_state(inside,eos)
                astar = ap/area_mach(wi/ai,g)
                if at < astar*(1-1e-12):
                    raise NoAdmissiblePortState('supersonic contraction has insufficient throat area')
                _,mt = nozzle_mach_roots(at/astar,g)
                pt = p0*(1+(g-1)*mt*mt/2)**(-g/(g-1))
                return finish(inside,'OUTFLOW_SUPERSONIC_TRANSMITTED',mt,pt,acoustic=False)
        else:
            a_sonic = (wi+2*ai/(g-1))*(g-1)/(g+1)
            if a_sonic <= 0:
                raise NoAdmissiblePortState('no positive outgoing sonic state')
            p_sonic = pi*(a_sonic/ai)**(2*g/(g-1))
            lower = pcritical = (p_sonic if at==ap else solve(
                lambda p: mach(pipe(p))-msub,p_sonic,p_zero,
                nonpositive_endpoint=True))
        prefix = 'OUTFLOW_UNSTART_SHOCK_' if wi>=ai else 'OUTFLOW_'
        if pcritical is not None:
            state,mt,pt = throat(pcritical,critical=True)
            if pc <= pt:
                return finish(state,prefix+'CHOKED',mt,pt)
            lower = pcritical
        p = solve(lambda p: throat(p)[2]-pc,lower,p_zero)
        state,mt,pt = throat(p)
        return finish(state,prefix+'SUBSONIC',mt,pt)

    # Chamber donor. The ideal nozzle's subsonic exit branch has no entropy loss.
    msub, msup = nozzle_mach_roots(ap/at, g)
    msub_area = area_mach(msub,g)
    sub = nozzle_state(pc, tc, msub, yc, eos)
    pmin = sub[2]

    if wave(pmin)[0]-sub[1] >= 0:
        # Mach parameter avoids subtracting nearly equal stagnation/static T
        # and keeps the critical endpoint identical in branch and root tests.
        def residual(m):
            state = nozzle_state(pc,tc,m,yc,eos)
            return wave(state[2])[0]-state[1]
        m = solve(residual, 0., msub)
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
            ratio = msub_area/area_mach(m,g)
            mt = solve(lambda mt: 1/area_mach(mt,g)-ratio, .1*ratio, 1.)
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
                  1., throat_p, causal=speed, acoustic=False,
                  wave_signals=(*rp.left_speeds,rp.velocity,*rp.right_speeds))
