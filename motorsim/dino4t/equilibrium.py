"""Chemical equilibrium of the burned gas and the two-zone cylinder closure.

Model ``TWO_ZONE_EQUILIBRIUM_V1`` (STANDARD_V1; Heywood 1988 sec. 9.2, 4.9; Gordon & McBride 1994):

* Burned gas: ideal-gas equilibrium among O2, N2, AR, CO2, H2O, CO, H2, H, O, OH (10 species, Gibbs
  minimisation by the element-potential Newton method).  NO is excluded: its formation is
  kinetically controlled (Zeldovich), equilibrium NO would overstate the energy stored in it.
  Unburnt fuel (1 - eta_c) is carried as an inert species of the burned zone.
* Unburned zone: frozen composition, adiabatic reversible compression (entropy is a state) except
  for its share of the wall heat loss.
* Both zones share the pressure.  The cylinder state stays (U_total, s_u): the algebraic closure
  below returns p, T_u, T_b and the burned composition for a given (U, s_u, V, x_b), so the engine
  integrator, ledgers and event machinery are unchanged.

Equations of the closure (m_u = (1-x) m, m_b = x m):
    s_u(T_u, p; Y_u) = s_u                              (unburned entropy)
    U = m_u e_u(T_u) + m_b e_b(T_b, p; elements)       (total energy)
    V = m_u R_u T_u / p + m_b R_b T_b / p               (volume)
"""
from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as np

from .thermo import P_STANDARD, R_UNIVERSAL, Mixture, Species, ThermoError

PRODUCTS = ("O2", "N2", "AR", "CO2", "H2O", "CO", "H2", "H", "O", "OH")
BURNED_SPECIES = PRODUCTS + ("IC8H18",)  # last = inert unburnt fuel
ELEMENTS = ("C", "H", "O", "N", "AR")


class EquilibriumError(ThermoError):
    pass


class EquilibriumSolver:
    """Gibbs-minimising composition at fixed (T, p, element moles)."""

    def __init__(self):
        sp = [Species.from_record(n) for n in PRODUCTS]
        self.names = PRODUCTS
        self.n = len(sp)
        self.low = np.array([s.low for s in sp])
        self.high = np.array([s.high for s in sp])
        self.t_mid = sp[0].t_mid
        self.a = np.array([[s.elements.get(e, 0) for e in ELEMENTS] for s in sp], dtype=float)
        self.molar_mass = np.array([s.molar_mass for s in sp])
        self._warm = None

    def gibbs_over_rt(self, T):
        c = self.low if T < self.t_mid else self.high
        h = c[:, 0] + T * (c[:, 1] / 2 + T * (c[:, 2] / 3 + T * (c[:, 3] / 4 + T * c[:, 4] / 5))) + c[:, 5] / T
        s = c[:, 0] * math.log(T) + T * (c[:, 1] + T * (c[:, 2] / 2 + T * (c[:, 3] / 3 + T * c[:, 4] / 4))) + c[:, 6]
        return h - s

    def solve(self, T, p, b, *, tol=1e-11, max_iter=60):
        """Return equilibrium moles (kmol) for element moles ``b`` (kmol, order ELEMENTS).

        A warm start (previous solution) is tried first; any failure falls back to the cold start."""
        b = np.asarray(b, dtype=float)
        if not np.all(b > 0):
            raise EquilibriumError("all elements must be present for the equilibrium solver")
        g = self.gibbs_over_rt(T) + math.log(p / P_STANDARD)
        scale = b.sum()
        bs = b / scale  # work with O(1) moles
        starts = []
        if self._warm is not None:
            n = np.maximum(self._warm, 1e-14)
            n = n * float(np.median(bs / np.maximum(n @ self.a, 1e-300)))
            starts.append(n)
        starts.append(np.full(self.n, 0.1 / self.n))
        last = None
        for n0 in starts:
            try:
                n = self._newton(g, bs, n0, tol, max_iter)
                break
            except EquilibriumError as exc:
                last = exc
        else:
            raise last
        self._warm = n.copy()
        return n * scale

    def _newton(self, g, bs, n, tol, max_iter):
        a = self.a
        for _ in range(max_iter):
            ntot = n.sum()
            mu = g + np.log(n / ntot)
            bc = n @ a
            M = np.zeros((6, 6))
            M[:5, :5] = (a * n[:, None]).T @ a
            M[:5, 5] = bc
            M[5, :5] = bc
            rhs = np.empty(6)
            rhs[:5] = bs - bc + (a * n[:, None]).T @ mu
            rhs[5] = n @ mu
            try:
                x = np.linalg.solve(M, rhs)
            except np.linalg.LinAlgError as exc:
                raise EquilibriumError("singular equilibrium system") from exc
            lam, dln = x[:5], x[5]
            delta = a @ lam + dln - mu
            if not np.all(np.isfinite(delta)):
                raise EquilibriumError("nonfinite equilibrium step")
            major = n / ntot > 1e-8
            cap1 = 2.0 / max(5.0 * abs(dln), float(np.max(np.abs(delta[major]))), 1e-300)
            cap = min(1.0, cap1)
            minor_up = (~major) & (delta > dln)
            if minor_up.any():
                cap2 = np.min(np.abs(-np.log(n[minor_up] / ntot) - 9.2103404) / (delta[minor_up] - dln))
                cap = min(cap, float(cap2))
            n = n * np.exp(cap * delta)
            err = float(np.max(np.abs(delta[major]) * n[major] / n.sum()))
            if err < tol and abs(dln) < 1e-8:
                break
        else:
            raise EquilibriumError("equilibrium iteration did not converge")
        resid = float(np.max(np.abs(n @ a - bs) / bs))
        if resid > 1e-8:
            raise EquilibriumError(f"element balance violated ({resid:.2e})")
        return n


def _secant(f, x0, x1, tol, ftol=0.0, max_iter=60, lo=None, hi=None):
    """Safeguarded secant / false position.  Stops on |f| <= ftol or relative step <= tol."""
    f0, f1 = f(x0), f(x1)
    a = b = fa = fb = None
    for _ in range(max_iter):
        if abs(f1) <= ftol:
            return x1
        if f0 * f1 < 0:
            a, b, fa, fb = x0, x1, f0, f1
        if a is not None:
            x = b - fb * (b - a) / (fb - fa)
            if not (min(a, b) < x < max(a, b)):
                x = 0.5 * (a + b)
            fx = f(x)
            if abs(fx) <= ftol or abs(b - a) <= tol * max(abs(a), abs(b), 1e-300):
                return x
            if fx * fa < 0:
                b, fb = x, fx
            else:
                a, fa = x, fx
            x0, f0, x1, f1 = a, fa, b, fb
            continue
        if f1 == f0:
            raise EquilibriumError("secant stalled")
        x2 = x1 - f1 * (x1 - x0) / (f1 - f0)
        if lo is not None:
            x2 = max(x2, lo)
        if hi is not None:
            x2 = min(x2, hi)
        if abs(x2 - x1) <= tol * max(abs(x2), 1e-300):
            return x2
        x0, f0, x1 = x1, f1, x2
        f1 = f(x1)
    raise EquilibriumError("scalar solve did not converge")


@dataclass
class ZoneState:
    p: float
    T_u: float
    T_b: float
    V_u: float
    V_b: float
    Y_u: np.ndarray        # unburned mass fractions (8-species standard mixture)
    Y_b: np.ndarray        # burned mass fractions (BURNED_SPECIES)
    m_u: float
    m_b: float
    R_mean: float
    T_mean: float


class TwoZoneClosure:
    def __init__(self, mix_u: Mixture):
        self.mix_u = mix_u
        self.eq = EquilibriumSolver()
        self.mix_b = Mixture(tuple(Species.from_record(n) for n in BURNED_SPECIES))
        self.w_b = self.mix_b.molar_mass
        self._p_guess = None
        self._tb_guess = None
        self._tu_last = 600.0
        # Below this burned mass fraction e_b = (U - U_u)/m_b divides a truncation-error-sized difference
        # by x_b.  There the burned zone is the adiabatic constant-pressure flame of the entrained gas.
        self.x_regular = 1e-4

    # ---- burned-zone helpers --------------------------------------------------------------
    def burned_composition(self, T, p, b, fuel_mass):
        n = self.eq.solve(T, p, b)
        m = np.empty(len(BURNED_SPECIES))
        m[:-1] = n * self.eq.molar_mass
        m[-1] = fuel_mass
        return m / m.sum()

    def _burned_state(self, p, e_target, b, fuel_mass, T_guess, enthalpy=False):
        prop = self.mix_b.enthalpy if enthalpy else self.mix_b.internal_energy

        def residual(T):
            Y = self.burned_composition(T, p, b, fuel_mass)
            return float(prop(Y, T)) - e_target
        T = _secant(residual, T_guess, T_guess * (1 + 1e-3), 1e-13, ftol=2e-4, lo=300.0, hi=6000.0)
        Y = self.burned_composition(T, p, b, fuel_mass)
        return T, Y

    # ---- closure -------------------------------------------------------------------------
    def solve(self, **kw):
        """Return ZoneState for total energy U (J), unburned entropy s_u (J/kg/K), volume V (m3).

        Warm guesses from the previous call are used first; on failure everything is reset and retried."""
        try:
            return self._solve_once(**kw)
        except EquilibriumError:
            self._p_guess = self._tb_guess = None
            self._tu_last = 600.0
            self.eq._warm = None
            return self._solve_once(**kw)

    def _solve_once(self, *, U, s_u, V, m, x_b, Y_u, b_full, fuel_inert_full):
        m_b, m_u = x_b * m, (1.0 - x_b) * m
        mix_u = self.mix_u
        R_u = float(mix_u.gas_constant(Y_u))
        if m_b <= 1e-12 * m:  # pure unburned: the energy alone fixes T
            T_u = mix_u.temperature_from_energy(Y_u, U / m, self._tb_guess or 600.0)
            p = m * R_u * T_u / V
            Yb = np.zeros(len(BURNED_SPECIES))
            return ZoneState(p, T_u, T_u, V, 0.0, Y_u, Yb, m, 0.0, R_u, T_u)
        b = x_b * np.asarray(b_full)
        fuel = x_b * fuel_inert_full

        def unburned(p):
            if m_u <= 1e-12 * m:
                return 0.0, 0.0, 0.0
            T = _secant(lambda T: float(mix_u.entropy(Y_u, T, p)) - s_u, self._tu_last, self._tu_last * (1 + 1e-4),
                        1e-13, ftol=1e-10, lo=150.0, hi=3000.0)
            self._tu_last = T
            return T, m_u * R_u * T / p, m_u * float(mix_u.internal_energy(Y_u, T))

        cache = {}

        def volume_gap(lnp):
            p = math.exp(lnp)
            T_u, V_u, U_u = unburned(p)
            guess = cache.get("T_b", self._tb_guess or 2500.0)
            if x_b < self.x_regular:
                T_b, Y_b = self._burned_state(p, float(mix_u.enthalpy(Y_u, T_u)), b, fuel, guess, enthalpy=True)
            else:
                T_b, Y_b = self._burned_state(p, (U - U_u) / m_b, b, fuel, guess)
            cache["T_b"] = T_b
            R_b = float(self.mix_b.gas_constant(Y_b))
            V_b = m_b * R_b * T_b / p
            cache.update(p=p, T_u=T_u, V_u=V_u, T_b=T_b, Y_b=Y_b, V_b=V_b, R_b=R_b)
            return (V_u + V_b - V) / V

        p0 = self._p_guess or (m * 300.0 * R_u * 2.0 / V)
        lnp = _secant(volume_gap, math.log(p0), math.log(p0) + 1e-4, 1e-13, ftol=2e-11, lo=math.log(1e3), hi=math.log(1e9))
        volume_gap(lnp)  # leave cache at the solution
        self._p_guess, self._tb_guess = cache["p"], cache["T_b"]
        R_mean = (m_u * R_u + m_b * cache["R_b"]) / m
        return ZoneState(cache["p"], cache["T_u"], cache["T_b"], cache["V_u"], cache["V_b"], Y_u, cache["Y_b"],
                         m_u, m_b, R_mean, cache["p"] * V / (m * R_mean))

    # ---- diagnostics / merge ---------------------------------------------------------------
    def project_to_standard(self, Y_b, mix_std: Mixture):
        """Element-conserving map of the burned composition onto the 8 standard species:
        H -> 1/2 H2, O -> 1/2 O2, OH -> 1/2 H2O + 1/4 O2 (recombination; energy handled by the caller)."""
        out = np.zeros(mix_std.ns)
        idx = {n: mix_std.index(n) for n in ("O2", "N2", "AR", "CO2", "H2O", "CO", "H2", "IC8H18")}
        names = BURNED_SPECIES
        mass = {n: Y_b[i] for i, n in enumerate(names)}
        w = {n: self.w_b[i] for i, n in enumerate(names)}
        for n in ("O2", "N2", "AR", "CO2", "H2O", "CO", "H2", "IC8H18"):
            out[idx[n]] += mass[n]
        kmol_h, kmol_o, kmol_oh = mass["H"] / w["H"], mass["O"] / w["O"], mass["OH"] / w["OH"]
        out[idx["H2"]] += 0.5 * kmol_h * mix_std.molar_mass[idx["H2"]]
        out[idx["O2"]] += 0.5 * kmol_o * mix_std.molar_mass[idx["O2"]]
        out[idx["H2O"]] += 0.5 * kmol_oh * mix_std.molar_mass[idx["H2O"]]
        out[idx["O2"]] += 0.25 * kmol_oh * mix_std.molar_mass[idx["O2"]]
        return out
