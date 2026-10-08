"""Parameterized static and dynamic multi-petal reed intake models.

The module owns reed mechanics/area only. Gas flux reuses the existing 0D
restriction relation, and the caller remains responsible for SSPRK stages and
global ledgers.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from math import atan2, ceil, cos, exp, floor, fsum, log, pi, sin, sqrt
from typing import Any

from .simulation import restriction

SCHEMA = "DYNAMIC_REED_V1"
PROVENANCE = {"DOCUMENTED", "DERIVED_FROM_DOCUMENTED",
              "SYNTHETIC_ASSUMPTION", "UNKNOWN"}


def _finite(value: Any, label: str) -> float:
    try:
        valid = type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        valid = False
    if not valid:
        raise ValueError(f"{label}: se requiere un número finito, sin booleanos.")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{label}: fuera de rango numérico.")
    return result


@dataclass(frozen=True)
class ReedPetal:
    id: str
    mass_kg: float
    pressure_area_m2: float
    effective_width_m: float
    stiffness_n_m: float
    damping_n_s_m: float
    lift_stop_m: float
    discharge_coefficient: float
    provenance: str
    restitution: float = 0.0

    def validate(self) -> None:
        if not isinstance(self.id, str) or not self.id.strip():
            raise ValueError("Cada reed requiere un id no vacío.")
        for name in ("mass_kg", "pressure_area_m2", "effective_width_m",
                     "stiffness_n_m", "lift_stop_m", "discharge_coefficient"):
            if _finite(getattr(self, name), f"{self.id}.{name}") <= 0.0:
                raise ValueError(f"{self.id}.{name} debe ser positivo.")
        if _finite(self.damping_n_s_m, f"{self.id}.damping_n_s_m") < 0.0:
            raise ValueError(f"{self.id}.damping_n_s_m no puede ser negativo.")
        restitution = _finite(self.restitution, f"{self.id}.restitution")
        if not 0.0 <= restitution <= 1.0:
            raise ValueError(f"{self.id}.restitution debe estar en [0,1].")
        if self.discharge_coefficient > 1.0:
            raise ValueError(f"{self.id}.discharge_coefficient debe estar en (0,1].")
        if not isinstance(self.provenance, str) or self.provenance not in PROVENANCE:
            raise ValueError(f"{self.id}.provenance inválida.")

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return {"id": self.id, "mass_kg": self.mass_kg,
                "pressure_area_m2": self.pressure_area_m2,
                "effective_width_m": self.effective_width_m,
                "stiffness_n_m": self.stiffness_n_m,
                "damping_n_s_m": self.damping_n_s_m,
                "lift_stop_m": self.lift_stop_m,
                "discharge_coefficient": self.discharge_coefficient,
                "provenance": self.provenance, "restitution": self.restitution}

    @classmethod
    def from_dict(cls, value: Any) -> "ReedPetal":
        fields = {"id", "mass_kg", "pressure_area_m2", "effective_width_m",
                  "stiffness_n_m", "damping_n_s_m", "lift_stop_m",
                  "discharge_coefficient", "provenance", "restitution"}
        if not isinstance(value, dict) or set(value) != fields:
            raise ValueError("Campos de reed petal faltantes o inesperados.")
        result = cls(**value)
        result.validate()
        return result


@dataclass(frozen=True)
class ReedState:
    position_m: float
    velocity_m_s: float

    def to_dict(self) -> dict[str, float]:
        return {"position_m": self.position_m, "velocity_m_s": self.velocity_m_s}

    @classmethod
    def from_dict(cls, value: Any) -> "ReedState":
        if not isinstance(value, dict) or set(value) != {"position_m", "velocity_m_s"}:
            raise ValueError("Estado de reed inválido.")
        return cls(value["position_m"], value["velocity_m_s"])


def _validate_state(petal: ReedPetal, state: ReedState) -> tuple[float, float]:
    petal.validate()
    if not isinstance(state, ReedState):
        raise ValueError(f"{petal.id}: tipo de estado reed inválido.")
    x = _finite(state.position_m, f"{petal.id}.position_m")
    v = _finite(state.velocity_m_s, f"{petal.id}.velocity_m_s")
    if not 0.0 <= x <= petal.lift_stop_m:
        raise ValueError(f"{petal.id}: posición fuera de los stops.")
    return x, v


def static_lift(petal: ReedPetal, pressure_difference_pa: float) -> float:
    """Quasi-static spring equilibrium; positive dp opens the petal."""
    petal.validate()
    delta_p = _finite(pressure_difference_pa, "pressure_difference_pa")
    equilibrium = delta_p * petal.pressure_area_m2 / petal.stiffness_n_m
    if not math.isfinite(equilibrium):
        raise ValueError("Equilibrio estático reed fuera de rango numérico.")
    return min(petal.lift_stop_m, max(0.0, equilibrium))


def static_area(petals: tuple[ReedPetal, ...], pressure_difference_pa: float) -> float:
    try:
        area = fsum(petal.discharge_coefficient * petal.effective_width_m *
                    static_lift(petal, pressure_difference_pa) for petal in petals)
    except OverflowError as error:
        raise ValueError("Área estática reed fuera de rango numérico.") from error
    if not math.isfinite(area):
        raise ValueError("Área estática reed fuera de rango numérico.")
    return area


def _free_state(petal: ReedPetal, initial: ReedState, dp: float,
                elapsed: float) -> ReedState:
    """Exact damped linear oscillator state for constant pressure over elapsed."""
    x0, v0 = _validate_state(petal, initial)
    if elapsed == 0.0:
        return ReedState(x0, v0)
    m, c, k = petal.mass_kg, petal.damping_n_s_m, petal.stiffness_n_m
    alpha = c / (2.0 * m)
    omega_sq = k / m
    equilibrium = dp * petal.pressure_area_m2 / k
    z0 = x0 - equilibrium
    discriminant = omega_sq - alpha * alpha

    if discriminant > 0.0:
        omega_d = sqrt(discriminant)
        b = (v0 + alpha * z0) / omega_d
        angle = omega_d * elapsed
        decay = exp(-alpha * elapsed)
        ca, sa = cos(angle), sin(angle)
        z = decay * (z0 * ca + b * sa)
        velocity = decay * ((-alpha * z0 + b * omega_d) * ca +
                            (-alpha * b - z0 * omega_d) * sa)
    elif discriminant == 0.0:
        b = v0 + alpha * z0
        decay = exp(-alpha * elapsed)
        z = (z0 + b * elapsed) * decay
        velocity = (b - alpha * z0 - alpha * b * elapsed) * decay
    else:
        delta = sqrt(-discriminant)
        r1, r2 = -alpha + delta, -alpha - delta
        c1 = (v0 - r2 * z0) / (r1 - r2)
        c2 = (r1 * z0 - v0) / (r1 - r2)
        e1, e2 = exp(r1 * elapsed), exp(r2 * elapsed)
        z = c1 * e1 + c2 * e2
        velocity = r1 * c1 * e1 + r2 * c2 * e2
    result = ReedState(equilibrium + z, velocity)
    _finite(result.position_m, f"{petal.id}.free_position")
    _finite(result.velocity_m_s, f"{petal.id}.free_velocity")
    return result


def _extrema_times(petal: ReedPetal, initial: ReedState, dp: float,
                   duration: float) -> tuple[float, ...]:
    """Times with zero velocity, separating monotone free-response intervals."""
    x0, v0 = _validate_state(petal, initial)
    if duration <= 0.0:
        return ()
    m, c, k = petal.mass_kg, petal.damping_n_s_m, petal.stiffness_n_m
    alpha = c / (2.0 * m)
    omega_sq = k / m
    equilibrium = dp * petal.pressure_area_m2 / k
    z0 = x0 - equilibrium
    disc = omega_sq - alpha * alpha
    roots: list[float] = []
    if disc > 0.0:
        omega_d = sqrt(disc)
        b = (v0 + alpha * z0) / omega_d
        a_cos = -alpha * z0 + b * omega_d
        b_sin = -alpha * b - z0 * omega_d
        if a_cos != 0.0 or b_sin != 0.0:
            base = atan2(-a_cos, b_sin)
            first = floor((0.0 - base) / pi) - 1
            last = ceil((omega_d * duration - base) / pi) + 1
            roots = [(base + n * pi) / omega_d
                     for n in range(first, last + 1)]
    elif disc == 0.0:
        b = v0 + alpha * z0
        denominator = alpha * b
        if denominator != 0.0:
            roots = [(b - alpha * z0) / denominator]
    else:
        delta = sqrt(-disc)
        r1, r2 = -alpha + delta, -alpha - delta
        c1 = (v0 - r2 * z0) / (r1 - r2)
        c2 = (r1 * z0 - v0) / (r1 - r2)
        denominator = r1 * c1
        numerator = -r2 * c2
        if denominator != 0.0 and numerator != 0.0 and (numerator > 0.0) == (denominator > 0.0):
            # Difference of logs avoids overflowing the ratio even when the
            # resulting time is finite.
            roots = [(log(abs(numerator)) - log(abs(denominator))) / (r1 - r2)]
    return tuple(sorted({root for root in roots if 0.0 < root < duration}))


def _first_contact(petal: ReedPetal, state: ReedState, dp: float,
                   duration: float) -> tuple[float, float] | None:
    cuts = (0.0, *_extrema_times(petal, state, dp, duration), duration)
    upper = petal.lift_stop_m
    for lo, hi in zip(cuts, cuts[1:]):
        xlo = _free_state(petal, state, dp, lo).position_m
        xhi = _free_state(petal, state, dp, hi).position_m
        boundary = None
        if xlo <= upper and xhi >= math.nextafter(upper, -math.inf) and (
                xhi > upper or _free_state(petal, state, dp, hi).velocity_m_s > 0.0):
            boundary = upper
        elif xlo >= 0.0 and xhi <= math.nextafter(0.0, math.inf) and (
                xhi < 0.0 or _free_state(petal, state, dp, hi).velocity_m_s < 0.0):
            boundary = 0.0
        if boundary is None:
            continue
        left, right = lo, hi
        for _ in range(80):
            middle = (left + right) / 2.0
            if middle == left or middle == right:
                break
            xmid = _free_state(petal, state, dp, middle).position_m
            crossed = xmid >= boundary if boundary == upper else xmid <= boundary
            if crossed:
                right = middle
            else:
                left = middle
        return right, boundary
    return None


def advance_petal(petal: ReedPetal, state: ReedState,
                  pressure_difference_pa: float, dt_s: float) -> ReedState:
    """Advance exact constant-dp free motion with bounded inelastic/rebound stops."""
    _validate_state(petal, state)
    dp = _finite(pressure_difference_pa, "pressure_difference_pa")
    dt = _finite(dt_s, "dt_s")
    if dt <= 0.0:
        raise ValueError("dt_s debe ser positivo.")
    current = state
    remaining = dt
    force = dp * petal.pressure_area_m2
    if not math.isfinite(force):
        raise ValueError("Fuerza de presión fuera de rango numérico.")
    for _ in range(64):
        contact = _first_contact(petal, current, dp, remaining)
        if contact is None:
            result = _free_state(petal, current, dp, remaining)
            if result.position_m < 0.0 or result.position_m > petal.lift_stop_m:
                raise ValueError("Respuesta reed cruzó un stop sin evento detectado.")
            return result
        contact_time, boundary = contact
        at_contact = _free_state(petal, current, dp, contact_time)
        if boundary == petal.lift_stop_m:
            velocity = -petal.restitution * abs(at_contact.velocity_m_s)
        else:
            velocity = petal.restitution * abs(at_contact.velocity_m_s)
        current = ReedState(boundary, velocity)
        remaining -= contact_time
        acceleration = (force - petal.damping_n_s_m * velocity -
                        petal.stiffness_n_m * boundary) / petal.mass_kg
        if (boundary == petal.lift_stop_m and velocity == 0.0 and acceleration >= 0.0) or (
                boundary == 0.0 and velocity == 0.0 and acceleration <= 0.0):
            return ReedState(boundary, 0.0)
        if remaining <= 0.0:
            return current
    raise ValueError("Demasiados contactos reed en un único paso temporal.")


@dataclass
class ReedBank:
    petals: tuple[ReedPetal, ...]
    states: dict[str, ReedState]

    def validate(self) -> None:
        if not isinstance(self.petals, tuple) or not self.petals:
            raise ValueError("ReedBank requiere uno o más pétalos.")
        if any(not isinstance(petal, ReedPetal) for petal in self.petals):
            raise ValueError("ReedBank acepta únicamente ReedPetal.")
        ids = [petal.id for petal in self.petals]
        if len(set(ids)) != len(ids):
            raise ValueError("Los ids de pétalo deben ser únicos.")
        if not isinstance(self.states, dict) or set(self.states) != set(ids):
            raise ValueError("El estado debe contener exactamente un valor por pétalo.")
        for petal in self.petals:
            _validate_state(petal, self.states[petal.id])

    def advance(self, pressure_difference_pa: float, dt_s: float) -> None:
        self.validate()
        delta_p = _finite(pressure_difference_pa, "pressure_difference_pa")
        # Calculate every independent petal before mutating any bank state.
        next_states = {petal.id: advance_petal(petal, self.states[petal.id],
                                               delta_p, dt_s)
                       for petal in self.petals}
        self.states = next_states

    def dynamic_area_m2(self) -> float:
        self.validate()
        try:
            area = fsum(petal.discharge_coefficient * petal.effective_width_m *
                        self.states[petal.id].position_m for petal in self.petals)
        except OverflowError as error:
            raise ValueError("Área reed agregada fuera de rango numérico.") from error
        if not math.isfinite(area):
            raise ValueError("Área reed agregada fuera de rango numérico.")
        return area

    def static_area_m2(self, pressure_difference_pa: float) -> float:
        self.validate()
        return static_area(self.petals, pressure_difference_pa)

    def snapshot(self) -> dict[str, Any]:
        self.validate()
        return {"schema": SCHEMA,
                "petals": [petal.to_dict() for petal in self.petals],
                "states": {petal.id: self.states[petal.id].to_dict()
                           for petal in self.petals}}

    @classmethod
    def restore(cls, value: Any) -> "ReedBank":
        if (not isinstance(value, dict) or set(value) != {"schema", "petals", "states"}
                or value["schema"] != SCHEMA or not isinstance(value["petals"], list)
                or not isinstance(value["states"], dict)):
            raise ValueError("Checkpoint DYNAMIC_REED_V1 inválido.")
        result = cls(tuple(ReedPetal.from_dict(row) for row in value["petals"]),
                     {key: ReedState.from_dict(row)
                      for key, row in value["states"].items()})
        result.validate()
        return result


def static_reed_flow(petals: tuple[ReedPetal, ...], left: tuple,
                     right: tuple, **flow_options) -> tuple[float, float, float]:
    """Quasi-static check-valve flow, sign convention left to right."""
    if left[0] <= right[0]:
        return 0.0, 0.0, 0.0
    area = static_area(petals, left[0] - right[0])
    return restriction(left, right, area, 1.0, **flow_options)


def dynamic_reed_flow(bank: ReedBank, left: tuple, right: tuple,
                      **flow_options) -> tuple[float, float, float]:
    """Bidirectional flow through current dynamic opening; no hidden reverse gate."""
    area = bank.dynamic_area_m2()
    return restriction(left, right, area, 1.0, **flow_options)
