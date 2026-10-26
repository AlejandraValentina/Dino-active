"""STANDARD_V1 adiabatic ideal-gas restriction between two quiescent volumes.

This is a mass/total-enthalpy/species reference, NOT a duct boundary. A pipe
connection additionally needs acoustic compatibility and a momentum closure.
There is no reference to motor power or calibrated engine-specific parameters.
"""
from dataclasses import dataclass
from math import exp, expm1, fsum, isfinite, log1p, sqrt

from .gas1d.eos import IdealGas, InvalidState

SCHEMA = "QUIESCENT_VOLUME_RESTRICTION_STANDARD_V1"


def _number(value, name, *, positive=False):
    if type(value) not in (int, float) or not isfinite(value):
        raise InvalidState(f"{name} must be a finite real number")
    if positive and value <= 0:
        raise InvalidState(f"{name} must be positive")
    return float(value)


@dataclass(frozen=True)
class QuiescentVolumeStateV1:
    """Static = total state; species order follows P6, fractions sum to one."""
    pressure_pa: float
    temperature_k: float
    species_fractions: tuple[float, float, float, float]

    def validate(self):
        _number(self.pressure_pa, "volume pressure", positive=True)
        _number(self.temperature_k, "volume temperature", positive=True)
        if not isinstance(self.species_fractions, tuple) or len(self.species_fractions) != 4:
            raise InvalidState("volume requires four explicit species fractions")
        values = tuple(_number(x, "species fraction") for x in self.species_fractions)
        if min(values) < 0 or max(values) > 1 or abs(fsum(values) - 1.0) > 1e-12:
            raise InvalidState("species fractions must be nonnegative and sum to one")


@dataclass(frozen=True)
class RestrictionGeometryV1:
    throat_area_m2: float
    cd_forward: float
    cd_reverse: float

    def validate(self):
        if _number(self.throat_area_m2, "geometric throat area") < 0:
            raise InvalidState("geometric throat area cannot be negative")
        for cd in (self.cd_forward, self.cd_reverse):
            if not 0 <= _number(cd, "discharge coefficient") <= 1:
                raise InvalidState("discharge coefficient must be in [0, 1]")


@dataclass(frozen=True)
class RestrictionExchangeV1:
    """Positive rates go from left to right. No duct momentum is prescribed."""
    mass_rate_kg_s: float
    energy_rate_w: float
    species_rates_kg_s: tuple[float, float, float, float]
    branch: str
    donor: str | None
    effective_throat_area_m2: float
    throat_pressure_pa: float | None
    throat_temperature_k: float | None
    throat_mach: float
    donor_total_enthalpy_j_kg: float | None
    schema: str = SCHEMA


def reservoir_restriction_v1(left: QuiescentVolumeStateV1,
                             right: QuiescentVolumeStateV1,
                             geometry: RestrictionGeometryV1,
                             *, eos: IdealGas | None = None) -> RestrictionExchangeV1:
    """Nozzle limit with a donor selected by quiescent-volume pressure.

    Cd multiplies geometric throat area once. The upstream temperature is total
    temperature, NOT the expanded throat temperature. The receiving reservoir's
    static pressure supplies backpressure. Below critical pressure the throat
    is sonic; further external expansion is outside this reference model.

    Small pressure differences use log1p/expm1 to avoid subtracting two nearly
    equal powers. There is no pressure deadband and no mutation of inventories.
    """
    if not isinstance(left, QuiescentVolumeStateV1) or not isinstance(right, QuiescentVolumeStateV1):
        raise TypeError("restriction endpoints must be explicit quiescent volume states")
    if not isinstance(geometry, RestrictionGeometryV1):
        raise TypeError("restriction requires explicit geometry and directional Cd")
    eos = eos or IdealGas()
    left.validate()
    right.validate()
    geometry.validate()
    zero = (0.0, 0.0, 0.0, 0.0)
    if geometry.throat_area_m2 == 0:
        return RestrictionExchangeV1(0.0, 0.0, zero, "CLOSED", None, 0.0, None, None, 0.0, None)
    if left.pressure_pa == right.pressure_pa:
        return RestrictionExchangeV1(0.0, 0.0, zero, "EQUILIBRIUM", None, 0.0, None, None, 0.0, None)
    forward = left.pressure_pa > right.pressure_pa
    donor, receiver = (left, right) if forward else (right, left)
    area = geometry.throat_area_m2 * (geometry.cd_forward if forward else geometry.cd_reverse)
    if area == 0:
        return RestrictionExchangeV1(0.0, 0.0, zero, "CLOSED", None, 0.0, None, None, 0.0, None)
    p0, t0, pb = donor.pressure_pa, donor.temperature_k, receiver.pressure_pa
    gamma, gas_r = eos.gamma, eos.R
    alpha = (gamma - 1.0) / gamma
    critical_ratio = (2.0 / (gamma + 1.0)) ** (gamma / (gamma - 1.0))
    ratio = pb / p0
    if ratio <= critical_ratio:
        branch = "CHOKED"
        throat_pressure = p0 * critical_ratio
        throat_temperature = t0 * 2.0 / (gamma + 1.0)
        mach = 1.0
        nondimensional_flux = sqrt(gamma) * (2.0 / (gamma + 1.0)) ** (
            (gamma + 1.0) / (2.0 * (gamma - 1.0)))
    else:
        branch = "SUBSONIC"
        logarithm = log1p((pb - p0) / p0)
        thermal_logarithm = alpha * logarithm
        throat_pressure = pb
        throat_temperature = t0 * exp(thermal_logarithm)
        mach = sqrt(2.0 * expm1(-thermal_logarithm) / (gamma - 1.0))
        nondimensional_flux = sqrt(2.0 * gamma / (gamma - 1.0) *
                                   exp(2.0 * logarithm / gamma) * -expm1(thermal_logarithm))
    sign = 1.0 if forward else -1.0
    mass = sign * area * p0 / sqrt(gas_r * t0) * nondimensional_flux
    enthalpy = eos.cp * t0
    energy = mass * enthalpy
    species = tuple(mass * value for value in donor.species_fractions)
    if not all(isfinite(x) for x in (mass, energy, enthalpy, *species)):
        raise InvalidState("restriction flux overflow")
    return RestrictionExchangeV1(mass, energy, species, branch,
        "left" if forward else "right", area, throat_pressure,
        throat_temperature, mach, enthalpy)
