"""Independent HLLC evaluator for the P4-C3 B1 audit.

This module deliberately has no import path through ``motorsim.gas1d``.  It
uses only the small EOS protocol needed by the audit (gamma, sound_speed,
validate, conservative and flux).
"""
from math import isfinite, sqrt


def _waves(left, right, eos):
    rl, ul, pl, _ = left
    rr, ur, pr, _ = right
    al = eos.sound_speed(left)
    ar = eos.sound_speed(right)
    wl, wr = sqrt(rl), sqrt(rr)
    g = eos.gamma
    hl = g * pl / ((g - 1.0) * rl) + ul * ul / 2.0
    hr = g * pr / ((g - 1.0) * rr) + ur * ur / 2.0
    u = (wl * ul + wr * ur) / (wl + wr)
    h = (wl * hl + wr * hr) / (wl + wr)
    a2 = (g - 1.0) * (h - u * u / 2.0)
    if not isfinite(a2) or a2 <= 0.0:
        raise ValueError("invalid audit Roe sound speed")
    a = sqrt(a2)
    sl = min(ul - al, ur - ar, u - a)
    sr = max(ul + al, ur + ar, u + a)
    if not isfinite(sl) or not isfinite(sr) or sl >= sr:
        raise ValueError("invalid audit wave bounds")
    return sl, sr


def hlle_flux(left, right, eos, speeds=None):
    """Local HLLE formula used by the audit fallback."""
    sl, sr = speeds or _waves(left, right, eos)
    fl, fr = eos.flux(left), eos.flux(right)
    if sl >= 0.0:
        return tuple(fl)
    if sr <= 0.0:
        return tuple(fr)
    ql, qr = eos.conservative(left), eos.conservative(right)
    return tuple((sr * l - sl * r + sl * sr * (b - a)) / (sr - sl)
                 for l, r, a, b in zip(fl, fr, ql, qr))


def hllc(left, right, eos):
    """Return ``(flux, (SL, SM, SR), reason)`` with a local HLLE fallback."""
    eos.validate(left)
    eos.validate(right)
    sl, sr = _waves(left, right, eos)
    rl, ul, pl, yl = left
    rr, ur, pr, yr = right
    fl, fr = eos.flux(left), eos.flux(right)
    if left == right:
        return tuple(fl), (sl, ul, sr), None
    if sl >= 0.0:
        return tuple(fl), (sl, ul, sr), None
    if sr <= 0.0:
        return tuple(fr), (sl, ur, sr), None
    denominator = rl * (sl - ul) - rr * (sr - ur)
    reason = None
    sm = None
    if denominator == 0.0 or not isfinite(denominator):
        reason = "degenerate_contact_denominator"
    else:
        sm = (pr - pl + rl * ul * (sl - ul) - rr * ur * (sr - ur)) / denominator
        if not isfinite(sm) or not sl < sm < sr:
            reason = "unordered_wave_speeds"
    stars = []
    if reason is None:
        for state, speed in ((left, sl), (right, sr)):
            rho, velocity, pressure, species = state
            if speed == sm or speed == velocity:
                reason = "degenerate_star_denominator"
                break
            rho_star = rho * (speed - velocity) / (speed - sm)
            pressure_star = pressure + rho * (speed - velocity) * (sm - velocity)
            energy_star = pressure / ((eos.gamma - 1.0) * rho)
            energy_star += velocity * velocity / 2.0
            energy_star += (sm - velocity) * (sm + pressure / (rho * (speed - velocity)))
            if (not all(isfinite(v) for v in
                        (rho_star, pressure_star, energy_star))
                    or rho_star <= 0.0 or pressure_star <= 0.0
                    or energy_star - sm * sm / 2.0 <= 0.0):
                reason = "inadmissible_star"
                break
            stars.append((rho_star, rho_star * sm, rho_star * energy_star,
                          rho_star * species))
    if reason is not None:
        return hlle_flux(left, right, eos, (sl, sr)), (sl, sm, sr), reason
    state, speed, star, physical = ((left, sl, stars[0], fl)
                                    if sm >= 0.0 else (right, sr, stars[1], fr))
    conservative = eos.conservative(state)
    flux = tuple(f + speed * (s - q)
                 for f, s, q in zip(physical, star, conservative))
    mass = star[0] * sm
    return (mass, flux[1], flux[2], mass * state[3]), (sl, sm, sr), None
