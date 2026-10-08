"""Contact-aware ideal stationary-plenum boundary, version 2.

This is an opt-in synthetic assumption. It does not model a calibrated
carburetor, a restricted nozzle, or the legacy characteristic boundary.
"""
from dataclasses import dataclass
from math import isfinite, sqrt

from .boundary import Boundary
from .eos import InvalidState


@dataclass(frozen=True)
class OpenEndFace:
    state: tuple
    interior_contact_state: tuple
    branch: str
    normal: int
    normal_velocity: float
    normal_mass_flux: float
    pressure_reaction_per_area: float
    incoming_total_enthalpy: float | None
    reservoir_donor: bool


class OpenEndPlenumV2Boundary(Boundary):
    """Lossless stationary atmosphere/plenum with explicit pressure outlet.

    ``p0`` is both the ambient static pressure and reservoir stagnation
    pressure. ``T0`` is reservoir stagnation temperature. ``Y0`` is the
    legacy scalar marker; integrated P6 callers still use their four-species
    reservoir composition for donor selection.
    """

    def __init__(self, p0=101325.0, T0=300.0, Y0=1.0):
        for name, value in (("p0", p0), ("T0", T0)):
            if type(value) not in (int, float) or not isfinite(value) or value <= 0:
                raise InvalidState(f"{name} must be positive and finite")
        if (type(Y0) not in (int, float) or not isfinite(Y0) or
                not 0.0 <= Y0 <= 1.0):
            raise InvalidState("Y0 must be finite and in [0, 1]")
        object.__setattr__(self, "kind", "open_end_plenum_v2")
        object.__setattr__(self, "state", None)
        object.__setattr__(self, "p0", float(p0))
        object.__setattr__(self, "T0", float(T0))
        object.__setattr__(self, "Y0", float(Y0))

    def resolve(self, interior, normal, eos):
        eos.validate(interior)
        if type(normal) not in (int, float) or normal not in (-1, 1):
            raise InvalidState("one-dimensional boundary normal must be +1 or -1")
        normal = int(normal)
        rho_i, velocity_i, pressure_i, marker_i = interior
        gamma = eos.gamma
        alpha = (gamma - 1.0) / gamma
        w_i = normal * velocity_i
        a_i = eos.sound_speed(interior)

        def result(state, contact_state, branch, donor, h0=None):
            w = normal * state[1]
            mass = state[0] * w
            return OpenEndFace(
                state=state,
                interior_contact_state=contact_state,
                branch=branch,
                normal=normal,
                normal_velocity=w,
                normal_mass_flux=mass,
                pressure_reaction_per_area=-normal * state[2],
                incoming_total_enthalpy=h0,
                reservoir_donor=donor)

        # Supersonic outflow carries no incoming information from the plenum.
        if w_i >= a_i:
            return result(interior, interior, "supersonic_outflow", False)

        k_i = pressure_i / rho_i ** gamma
        invariant = w_i + 2.0 * a_i / (gamma - 1.0)

        def inner_side(pressure):
            rho = (pressure / k_i) ** (1.0 / gamma)
            sound = sqrt(gamma * pressure / rho)
            w = invariant - 2.0 * sound / (gamma - 1.0)
            return rho, sound, w

        rho_ambient_side, a_ambient_side, w_ambient_side = inner_side(self.p0)
        if w_ambient_side >= 0.0:
            if w_ambient_side >= a_ambient_side:
                sound = invariant * (gamma - 1.0) / (gamma + 1.0)
                if not isfinite(sound) or sound <= 0.0:
                    raise InvalidState("invalid sonic outflow characteristic")
                rho = (sound * sound / (gamma * k_i)) ** (1.0 / (gamma - 1.0))
                pressure = k_i * rho ** gamma
                state = eos.validate((rho, normal * sound, pressure, marker_i))
                return result(state, state, "choked_outflow", False)
            state = eos.validate((rho_ambient_side, normal * w_ambient_side,
                                  self.p0, marker_i))
            return result(state, state, "subsonic_outflow", False)

        # Inflow contact: the interior acoustic side retains K_i, while the
        # plenum side retains K_0 and the stagnation enthalpy cp*T0.
        rho_0 = self.p0 / (eos.R * self.T0)
        k_0 = self.p0 / rho_0 ** gamma
        h0 = eos.cp * self.T0
        if invariant <= 0.0:
            p_zero = 0.0
        else:
            a_zero = invariant * (gamma - 1.0) / 2.0
            rho_zero = (a_zero * a_zero / (gamma * k_i)) ** (1.0 / (gamma - 1.0))
            p_zero = k_i * rho_zero ** gamma
        p_zero = min(max(p_zero, 0.0), self.p0)

        def residual(pressure):
            _, _, w = inner_side(pressure)
            t_reservoir = self.T0 * (pressure / self.p0) ** alpha
            return eos.cp * t_reservoir + 0.5 * w * w - h0

        p_critical = self.p0 * (2.0 / (gamma + 1.0)) ** (gamma / (gamma - 1.0))
        if p_critical > p_zero and residual(p_critical) >= 0.0:
            pressure = p_critical
            temperature = 2.0 * self.T0 / (gamma + 1.0)
            sound = sqrt(gamma * eos.R * temperature)
            w = -sound
            rho_reservoir = pressure / (eos.R * temperature)
            rho_inner, _, _ = inner_side(pressure)
            contact = eos.validate((rho_inner, normal * w, pressure, marker_i))
            donor_state = eos.validate((rho_reservoir, normal * w, pressure, self.Y0))
            return result(donor_state, contact, "choked_inflow", True, h0)

        lo, hi = p_zero, self.p0
        # F is strictly increasing on this interval wherever w<0.  A fixed
        # bisection count makes the solve deterministic and independent of
        # solver history/campaign outcome.
        for _ in range(80):
            mid = (lo + hi) * 0.5
            if residual(mid) < 0.0:
                lo = mid
            else:
                hi = mid
        pressure = (lo + hi) * 0.5
        rho_inner, _, w = inner_side(pressure)
        temperature = self.T0 * (pressure / self.p0) ** alpha
        rho_reservoir = (pressure / k_0) ** (1.0 / gamma)
        contact = eos.validate((rho_inner, normal * w, pressure, marker_i))
        donor_state = eos.validate((rho_reservoir, normal * w, pressure, self.Y0))
        return result(donor_state, contact, "subsonic_inflow", True, h0)

    def face_state(self, interior, normal, eos):
        return self.resolve(interior, normal, eos).state

    def flux(self, interior, normal, eos):
        face = self.resolve(interior, normal, eos)
        state = face.state
        sound = eos.sound_speed(state)
        velocity = state[1]
        return eos.flux(state), (velocity - sound, velocity, velocity + sound), None
