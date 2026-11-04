"""Thermally perfect ideal-gas mixtures (NASA-7), vectorized over states.

Energy convention: species enthalpies include the enthalpy of formation at
298.15 K (NASA convention).  Total internal energy is therefore conserved
through combustion without any heat-release source term; heat release is
the change of composition at fixed internal energy.

Arrays: mass fractions ``Y`` have shape (N, ns) (or (ns,) for one state),
temperatures have shape (N,) (or scalar).  All quantities are SI, per kg.
"""
from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as np

from .thermo_data import ATOMIC_WEIGHT, RECORDS, parse_nasa7

R_UNIVERSAL = 8314.462618  # J/(kmol K), CODATA 2018
P_STANDARD = 101325.0       # Pa, reference pressure of the NASA entropy fits
T_ADMISSIBLE = (100.0, 6000.0)


class ThermoError(ValueError):
    """Inadmissible thermodynamic state (never silently clipped)."""


@dataclass(frozen=True)
class Species:
    name: str
    elements: dict
    t_low: float
    t_mid: float
    t_high: float
    low: tuple
    high: tuple
    source: str

    @property
    def molar_mass(self) -> float:
        return sum(ATOMIC_WEIGHT[e] * n for e, n in self.elements.items())

    @classmethod
    def from_record(cls, name: str) -> "Species":
        source, elements, text = RECORDS[name]
        data = parse_nasa7(text)
        return cls(name, dict(elements), data["t_low"], data["t_mid"], data["t_high"],
                   data["low"], data["high"], source)

    @classmethod
    def calorically_perfect(cls, name: str, molar_mass: float, gamma: float,
                            elements: dict | None = None) -> "Species":
        """Constant-cp verification species with h(0 K)=0, i.e. e = cv*T.

        Expressed as a degenerate NASA-7 record so that it shares every code
        path with the thermally perfect species.
        """
        cp_over_r = gamma / (gamma - 1.0)
        coefficients = (cp_over_r, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        species = cls(name, dict(elements or {}), 1.0, 1000.0, 1.0e5,
                      coefficients, coefficients, "VERIFICATION_CALORICALLY_PERFECT")
        object.__setattr__(species, "_molar_mass", molar_mass)
        return species


def _molar_mass(species: Species) -> float:
    return getattr(species, "_molar_mass", None) or species.molar_mass


STANDARD_SPECIES = ("IC8H18", "O2", "N2", "AR", "CO2", "H2O", "CO", "H2")


class Mixture:
    """Fixed species set; mixture coefficients are linear in Y because all
    species share T_mid (checked), so each property is one polynomial."""

    def __init__(self, species: tuple[Species, ...]):
        if not species:
            raise ValueError("mixture requires species")
        mids = {s.t_mid for s in species}
        if len(mids) != 1:
            raise ValueError("all species must share T_mid")
        self.species = tuple(species)
        self.names = tuple(s.name for s in species)
        if len(set(self.names)) != len(self.names):
            raise ValueError("duplicate species")
        self.ns = len(species)
        self.t_mid = mids.pop()
        self.t_fit = (max(s.t_low for s in species), min(s.t_high for s in species))
        self.molar_mass = np.array([_molar_mass(s) for s in species])
        scale = (R_UNIVERSAL / self.molar_mass)[:, None]
        self._low = np.array([s.low for s in species]) * scale
        self._high = np.array([s.high for s in species]) * scale
        self._inv_w = 1.0 / self.molar_mass
        self.elements = tuple(sorted({e for s in species for e in s.elements}))
        # atoms of element e per kg of species i  [kmol/kg]
        self.element_matrix = np.array(
            [[s.elements.get(e, 0) / _molar_mass(s) for e in self.elements] for s in species])

    @classmethod
    def standard(cls) -> "Mixture":
        return cls(tuple(Species.from_record(n) for n in STANDARD_SPECIES))

    def index(self, name: str) -> int:
        return self.names.index(name)

    # ------------------------------------------------------------------ basics
    def _coefficients(self, Y, T):
        T = np.asarray(T, dtype=float)
        low = Y @ self._low
        high = Y @ self._high
        mask = (T < self.t_mid)[..., None]
        return np.where(mask, low, high), T

    def gas_constant(self, Y):
        return R_UNIVERSAL * (Y @ self._inv_w)

    def mean_molar_mass(self, Y):
        return 1.0 / (Y @ self._inv_w)

    def cp(self, Y, T):
        a, T = self._coefficients(Y, T)
        a1, a2, a3, a4, a5 = (a[..., k] for k in range(5))
        return a1 + T * (a2 + T * (a3 + T * (a4 + T * a5)))

    def enthalpy(self, Y, T):
        a, T = self._coefficients(Y, T)
        a1, a2, a3, a4, a5, a6 = (a[..., k] for k in range(6))
        return T * (a1 + T * (a2 / 2 + T * (a3 / 3 + T * (a4 / 4 + T * a5 / 5)))) + a6

    def internal_energy(self, Y, T):
        return self.enthalpy(Y, T) - self.gas_constant(Y) * np.asarray(T, dtype=float)

    def standard_entropy(self, Y, T):
        """sum_i Y_i s_i°(T) at P_STANDARD, without the mixing term."""
        a, T = self._coefficients(Y, T)
        a1, a2, a3, a4, a5, _, a7 = (a[..., k] for k in range(7))
        return a1 * np.log(T) + T * (a2 + T * (a3 / 2 + T * (a4 / 3 + T * a5 / 4))) + a7

    def entropy(self, Y, T, p):
        """Mixture specific entropy including the ideal mixing term."""
        Y = np.asarray(Y, dtype=float)
        moles = Y * self._inv_w
        total = moles.sum(axis=-1, keepdims=True)
        with np.errstate(divide="ignore", invalid="ignore"):
            x = np.where(moles > 0, moles / total, 1.0)
        mixing = -(R_UNIVERSAL * moles * np.log(x)).sum(axis=-1)
        return (self.standard_entropy(Y, T) - self.gas_constant(Y) * np.log(np.asarray(p) / P_STANDARD)
                + mixing)

    def zero_kelvin_energy(self, Y):
        """Internal energy of the low-T fit extrapolated to T = 0 (admissibility floor)."""
        return Y @ self._low[:, 5]

    def frozen_gamma(self, Y, T):
        cp = self.cp(Y, T)
        return cp / (cp - self.gas_constant(Y))

    def sound_speed(self, Y, T):
        return np.sqrt(self.frozen_gamma(Y, T) * self.gas_constant(Y) * np.asarray(T, dtype=float))

    # --------------------------------------------------------------- inversion
    def coefficient_pair(self, Y):
        """Mixture (low, high) coefficient arrays; reuse while Y is fixed."""
        return Y @ self._low, Y @ self._high

    def h_cp(self, pair, T):
        """Enthalpy and cp from precomputed mixture coefficients."""
        a = np.where((T < self.t_mid)[..., None], pair[0], pair[1])
        a1, a2, a3, a4, a5, a6 = (a[..., k] for k in range(6))
        cp = a1 + T * (a2 + T * (a3 + T * (a4 + T * a5)))
        h = T * (a1 + T * (a2 / 2 + T * (a3 / 3 + T * (a4 / 4 + T * a5 / 5)))) + a6
        return h, cp

    def temperature_from_energy(self, Y, e, guess=None, *, tol=1e-11, pair=None, R=None):
        """Solve e(T, Y) = e for T.  Newton, then bracketed bisection for any
        state that has not converged (e.g. jitter at the T_mid fit seam)."""
        e = np.asarray(e, dtype=float)
        scalar = e.ndim == 0
        Y2 = np.atleast_2d(np.asarray(Y, dtype=float))
        e1 = np.atleast_1d(e)
        pair = pair if pair is not None else self.coefficient_pair(Y2)
        R = self.gas_constant(Y2) if R is None else np.atleast_1d(R)
        T = np.full(e1.shape, 1000.0) if guess is None else np.array(np.atleast_1d(guess), dtype=float)
        T = np.clip(np.where(np.isfinite(T), T, 1000.0), *T_ADMISSIBLE)
        done = np.zeros(e1.shape, dtype=bool)
        for _ in range(30):
            h, cp = self.h_cp(pair, T)
            step = (h - R * T - e1) / (cp - R)
            T = np.clip(T - step, *T_ADMISSIBLE)
            done = np.abs(step) <= tol * T
            if done.all():
                break

        def energy(temperature):
            return self.h_cp(pair, temperature)[0] - R * temperature

        if not done.all():
            lo = np.full(e1.shape, T_ADMISSIBLE[0])
            hi = np.full(e1.shape, T_ADMISSIBLE[1])
            bad = ~done
            for _ in range(80):
                mid = 0.5 * (lo + hi)
                above = energy(mid) > e1
                hi = np.where(bad & above, mid, hi)
                lo = np.where(bad & ~above, mid, lo)
            T = np.where(bad, 0.5 * (lo + hi), T)
            out_of_range = (energy(np.full(e1.shape, T_ADMISSIBLE[0])) > e1) | (
                energy(np.full(e1.shape, T_ADMISSIBLE[1])) < e1)
            if out_of_range.any():
                raise ThermoError("temperature outside admissible range [100, 6000] K")
        if not np.isfinite(T).all() or (T <= T_ADMISSIBLE[0]).any() or (T >= T_ADMISSIBLE[1]).any():
            raise ThermoError("temperature outside admissible range [100, 6000] K")
        return float(T[0]) if scalar else T

    # ------------------------------------------------------------ composition
    def mass_fractions(self, **moles) -> np.ndarray:
        """Mass fractions from mole numbers given by species name."""
        n = np.zeros(self.ns)
        for name, value in moles.items():
            n[self.index(name)] = value
        m = n * self.molar_mass
        return m / m.sum()

    def element_masses(self, masses) -> np.ndarray:
        """kmol of each element for species masses (kg); shape (..., ne)."""
        return np.asarray(masses) @ self.element_matrix


def dry_air(mixture: Mixture) -> np.ndarray:
    """Dry air, mole fractions N2 0.78084, O2 0.20946, Ar 0.00934 (CO2 and
    trace gases folded into N2 by renormalization; documented simplification)."""
    total = 0.78084 + 0.20946 + 0.00934
    return mixture.mass_fractions(N2=0.78084 / total, O2=0.20946 / total, AR=0.00934 / total)


def molar_mass_check(species: Species) -> float:
    return _molar_mass(species)


def standard_heat_of_reaction(mixture: Mixture, delta_mass, T=298.15) -> float:
    """Enthalpy change (J) of a mass-conserving composition change at T."""
    delta = np.asarray(delta_mass, dtype=float)
    h_species = np.array([mixture.enthalpy(np.eye(mixture.ns)[i], T) for i in range(mixture.ns)])
    return float(delta @ h_species)


def isclose_rel(a, b, rel):
    return math.isclose(a, b, rel_tol=rel)
