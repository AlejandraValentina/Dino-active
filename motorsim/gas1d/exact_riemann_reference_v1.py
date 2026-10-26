"""Ideal-gas Euler Riemann reference, separate from the frozen HLLC kernel.

Pressure-wave curves, Rankine-Hugoniot shocks and self-similar fans. Vacuum is
reported explicitly: this reference never substitutes a pressure floor.
"""
from dataclasses import dataclass
from math import expm1, isfinite, log, sqrt

from .eos import IdealGas, InvalidState


class VacuumRiemannError(InvalidState):
    pass


def pressure_wave(pressure, state, eos):
    """Return f(p), star density for a side state (Toro wave convention)."""
    rho, _, p, _ = eos.validate(state)
    if not isfinite(pressure) or pressure < 0:
        raise InvalidState('wave pressure must be finite and nonnegative')
    g = eos.gamma
    if pressure == 0:
        return -2*eos.sound_speed(state)/(g-1), 0.
    ratio = pressure/p
    if pressure <= p:
        f = 2*eos.sound_speed(state)/(g-1)*expm1((g-1)/(2*g)*log(ratio))
        r = rho*ratio**(1/g)
    else:
        b = (g-1)/(g+1)
        f = (pressure-p)*sqrt(2/((g+1)*rho)/(pressure+b*p))
        r = rho*(ratio+b)/(b*ratio+1)
    return f, r


@dataclass(frozen=True)
class ExactRiemannV1:
    left: tuple
    right: tuple
    pressure: float
    velocity: float
    left_star: tuple
    right_star: tuple
    left_speeds: tuple
    right_speeds: tuple
    eos: IdealGas

    def sample(self, xi=0.):
        if not isfinite(xi):
            raise InvalidState('nonfinite similarity coordinate')
        if xi <= self.velocity:
            state, star = self.left, self.left_star
            head, tail = self.left_speeds
            if xi <= head:
                return state
            if xi >= tail:
                return star
            direction = 1.
        else:
            state, star = self.right, self.right_star
            tail, head = self.right_speeds
            if xi >= head:
                return state
            if xi <= tail:
                return star
            direction = -1.
        # A shock has identical head/tail, so only rarefactions reach here.
        rho, u, p, marker = state
        g = self.eos.gamma
        a = self.eos.sound_speed(state)
        v = 2/(g+1)*(direction*a+(g-1)*u/2+xi)
        sound = 2/(g+1)*(a+direction*(g-1)*(u-xi)/2)
        if sound <= 0:
            raise VacuumRiemannError('sample lies in vacuum')
        return (rho*(sound/a)**(2/(g-1)), v,
                p*(sound/a)**(2*g/(g-1)), marker)


def exact_riemann_v1(left, right, *, eos=None):
    eos = eos or IdealGas()
    eos.validate(left)
    eos.validate(right)
    al, ar = eos.sound_speed(left), eos.sound_speed(right)
    g = eos.gamma
    if right[1]-left[1] >= 2*(al+ar)/(g-1):
        raise VacuumRiemannError('Euler Riemann data generate vacuum')

    def residual(p):
        return (pressure_wave(p, left, eos)[0]+pressure_wave(p, right, eos)[0]
                +right[1]-left[1])

    lo, hi = 0., max(left[2], right[2])
    while residual(hi) < 0:
        hi *= 2
        if not isfinite(hi):
            raise InvalidState('Riemann pressure exceeds finite range')
    for _ in range(120):
        mid = (lo+hi)/2
        if mid == lo or mid == hi:
            break
        if residual(mid) > 0:
            hi = mid
        else:
            lo = mid
    p = (lo+hi)/2
    fl, rl = pressure_wave(p, left, eos)
    fr, rr = pressure_wave(p, right, eos)
    u = (left[1]+right[1]+fr-fl)/2
    ls = (rl, u, p, left[3])
    rs = (rr, u, p, right[3])
    eos.validate(ls)
    eos.validate(rs)
    if p > left[2]:
        speed = left[1]-al*sqrt((g+1)/(2*g)*p/left[2]+(g-1)/(2*g))
        sl = (speed, speed)
    else:
        sl = (left[1]-al, u-eos.sound_speed(ls))
    if p > right[2]:
        speed = right[1]+ar*sqrt((g+1)/(2*g)*p/right[2]+(g-1)/(2*g))
        sr = (speed, speed)
    else:
        sr = (u+eos.sound_speed(rs), right[1]+ar)
    return ExactRiemannV1(left, right, p, u, ls, rs, sl, sr, eos)
