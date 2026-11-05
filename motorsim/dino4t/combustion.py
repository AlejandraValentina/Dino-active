"""Fuel-air stoichiometry, burned-gas composition and the Wiebe burn law.

Model ``WIEBE_SINGLE_ZONE_V1`` (STANDARD_V1, Heywood 1988 §9.2.1 and §4.9):

* The fuel burns along a prescribed Wiebe mass-fraction-burned curve that
  starts at the start of combustion (SOC).  Phasing and duration are inputs
  (calibration parameters), not predictions.
* Products follow the "low-temperature" no-dissociation model: lean or
  stoichiometric mixtures burn completely to CO2/H2O; rich mixtures form
  CO/H2 with the water-gas shift equilibrium constant K (Heywood eq. 4.33,
  K = 3.5 by default).  Dissociation is neglected.
* No heat-release source term exists: species enthalpies include formation
  enthalpy, so energy is conserved and heat release follows from the change
  in composition at constant internal energy.
"""
from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as np

from .thermo import Mixture, dry_air, standard_heat_of_reaction


class StoichiometryError(ValueError):
    pass


def fuel_formula(mixture: Mixture, fuel: str) -> tuple[float, float, float]:
    s = mixture.species[mixture.index(fuel)]
    return float(s.elements.get("C", 0)), float(s.elements.get("H", 0)), float(s.elements.get("O", 0))


def stoichiometric_o2_per_fuel_mole(mixture: Mixture, fuel: str) -> float:
    x, y, z = fuel_formula(mixture, fuel)
    return x + y / 4 - z / 2


def stoichiometric_afr(mixture: Mixture, fuel: str) -> float:
    air = dry_air(mixture)
    w = mixture.molar_mass
    o2_mass = stoichiometric_o2_per_fuel_mole(mixture, fuel) * w[mixture.index("O2")] / w[mixture.index(fuel)]
    return o2_mass / air[mixture.index("O2")]


def premixed_charge(mixture: Mixture, fuel: str, equivalence_ratio: float) -> np.ndarray:
    """Mass fractions of a homogeneous vaporized fuel / dry-air mixture."""
    if not math.isfinite(equivalence_ratio) or equivalence_ratio < 0:
        raise StoichiometryError("equivalence ratio must be finite and nonnegative")
    far = equivalence_ratio / stoichiometric_afr(mixture, fuel)
    y = dry_air(mixture) / (1.0 + far)
    y[mixture.index(fuel)] += far / (1.0 + far)
    return y


def products_change(mixture: Mixture, fuel: str, fuel_mass: float, o2_mass: float,
                    water_gas_k: float = 3.5) -> np.ndarray:
    """Species mass changes (kg) when ``fuel_mass`` burns with up to ``o2_mass``.

    Element-conserving by construction; total mass change is zero to roundoff.
    """
    if fuel_mass < 0 or o2_mass < 0:
        raise StoichiometryError("negative reactant mass")
    delta = np.zeros(mixture.ns)
    if fuel_mass == 0:
        return delta
    w = mixture.molar_mass
    i = {n: mixture.index(n) for n in (fuel, "O2", "CO2", "H2O", "CO", "H2")}
    x, y, z = fuel_formula(mixture, fuel)
    nf = fuel_mass / w[i[fuel]]
    need = stoichiometric_o2_per_fuel_mole(mixture, fuel)
    available = o2_mass / w[i["O2"]] / nf  # O2 kmol per kmol fuel burned
    if available >= need:
        a, b, c, d, o2_used = x, 0.0, y / 2, 0.0, need
    else:
        # Rich: all O2 consumed; C,H,O balance plus K = [CO][H2O]/([CO2][H2]).
        o2_used = available
        q = 2 * available + z - x
        p = y / 2 - 2 * available - z + x
        if q < 0:
            raise StoichiometryError("mixture too rich: O2 insufficient to oxidize C to CO")
        k = water_gas_k
        A, B, C = k - 1.0, k * p + x + q, -x * q
        a = (-C / B) if abs(A) < 1e-14 else (-B + math.sqrt(B * B - 4 * A * C)) / (2 * A)
        b, c = x - a, q - a
        d = y / 2 - c
        if min(a, b, c, d) < -1e-12 * max(x, y):
            raise StoichiometryError("rich-products solution outside admissible domain")
        a, b, c, d = (max(0.0, v) for v in (a, b, c, d))
    delta[i[fuel]] -= nf * w[i[fuel]]
    delta[i["O2"]] -= nf * o2_used * w[i["O2"]]
    delta[i["CO2"]] += nf * a * w[i["CO2"]]
    delta[i["CO"]] += nf * b * w[i["CO"]]
    delta[i["H2O"]] += nf * c * w[i["H2O"]]
    delta[i["H2"]] += nf * d * w[i["H2"]]
    return delta


def burned_composition(mixture: Mixture, fuel: str, charge: np.ndarray,
                       water_gas_k: float = 3.5) -> np.ndarray:
    """Mass fractions after complete burning of a charge (initialization only)."""
    m = np.array(charge, dtype=float)
    m = m + products_change(mixture, fuel, m[mixture.index(fuel)], m[mixture.index("O2")], water_gas_k)
    m = np.maximum(m, 0.0)
    return m / m.sum()


def lower_heating_value(mixture: Mixture, fuel: str) -> float:
    """LHV (J/kg fuel) at 298.15 K implied by the species data (H2O vapour)."""
    delta = products_change(mixture, fuel, 1.0, 1.0e3)
    return -standard_heat_of_reaction(mixture, delta)


@dataclass(frozen=True)
class Wiebe:
    """x_b = (1 - exp(-a y^(m+1))) / (1 - exp(-a)), y = (theta - SOC)/duration,
    normalized so x_b(duration) = 1 exactly (Heywood eq. 9.23 form)."""
    start_deg: float
    duration_deg: float
    a: float = 5.0
    m: float = 2.0

    def __post_init__(self):
        if not (self.duration_deg > 0 and self.a > 0 and self.m >= 0 and math.isfinite(self.start_deg)):
            raise ValueError("invalid Wiebe parameters")

    def _y(self, since_start_deg):
        return min(max(since_start_deg / self.duration_deg, 0.0), 1.0)

    def fraction(self, since_start_deg: float) -> float:
        y = self._y(since_start_deg)
        return -math.expm1(-self.a * y ** (self.m + 1)) / -math.expm1(-self.a)

    def rate_per_deg(self, since_start_deg: float) -> float:
        if not 0.0 < since_start_deg < self.duration_deg:
            return 0.0
        y = since_start_deg / self.duration_deg
        return (self.a * (self.m + 1) / self.duration_deg * y ** self.m
                * math.exp(-self.a * y ** (self.m + 1)) / -math.expm1(-self.a))

    def angle_at_fraction(self, x: float) -> float:
        """Inverse of ``fraction`` (degrees after SOC), analytic."""
        if not 0.0 <= x <= 1.0:
            raise ValueError("fraction outside [0, 1]")
        y = (-math.log1p(x * math.expm1(-self.a)) / self.a) ** (1.0 / (self.m + 1))
        return y * self.duration_deg
