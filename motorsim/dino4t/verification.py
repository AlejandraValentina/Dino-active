"""Numerical verification suite for Dino 4T (evidence level L0/L1).

Each case compares against an INDEPENDENT reference (tabulated data, exact
solution, analytic law, a separately implemented integrator or the frozen
Dino 2T kernels) with an acceptance tolerance fixed here, before running.
None of these cases is experimental validation.

Categories:
  thermo       - species data vs NIST-JANAF; inversion; stoichiometry
  geometry     - slider-crank vs shared kernel / finite differences
  flux         - HLLC vs frozen gas1d HLLC (oracle)
  duct         - Sod (exact Riemann), smooth-order study, well-balance,
                 quarter-wave resonance, choked steady nozzle
  cylinder     - isentropic motoring order; burn vs independent ODE
  engine       - conservation ledgers, periodicity, mesh convergence (GCI)
"""
from __future__ import annotations

import json
import math
from pathlib import Path
import time

import numpy as np

from .combustion import (Wiebe, lower_heating_value, premixed_charge, products_change,
                         stoichiometric_afr)
from .duct import Duct, DuctWall
from .engine import CombustionSpec, Cylinder, FourStrokeEngine
from .kinematics import SliderCrank
from .restriction import EndCell, VolumeGas, orifice_mass_flow, psi, restriction_flux
from .thermo import R_UNIVERSAL, Mixture, Species, dry_air

# NIST-JANAF Thermochemical Tables (Chase 1998), 298.15 K: cp J/(mol K), S J/(mol K), dHf kJ/mol
JANAF_298 = {"N2": (29.124, 191.609, 0.0), "O2": (29.376, 205.147, 0.0), "AR": (20.786, 154.845, 0.0),
             "CO2": (37.129, 213.795, -393.522), "H2O": (33.590, 188.834, -241.826),
             "CO": (29.142, 197.653, -110.527), "H2": (28.836, 130.680, 0.0)}


def _case(name, category, passed, metrics, tolerance, reference):
    return dict(name=name, category=category, passed=bool(passed), metrics=metrics,
                tolerance=tolerance, reference=reference)


def air_cp_mixture(gamma=1.4, R=287.0):
    return Mixture((Species.calorically_perfect("AIR_CP", R_UNIVERSAL / R, gamma),))


# ------------------------------------------------------------------ thermo
def thermo_reference():
    mix = Mixture.standard()
    worst = dict(cp=0.0, s=0.0, hf=0.0)
    rows = {}
    for name, (cp, s, hf) in JANAF_298.items():
        i = mix.index(name)
        y = np.eye(mix.ns)[i]
        w = mix.molar_mass[i]
        mine = (float(mix.cp(y, 298.15)) * w / 1e3, float(mix.standard_entropy(y, 298.15)) * w / 1e3,
                float(mix.enthalpy(y, 298.15)) * w / 1e6)
        rows[name] = mine
        worst["cp"] = max(worst["cp"], abs(mine[0] - cp) / cp)
        worst["s"] = max(worst["s"], abs(mine[1] - s) / s)
        worst["hf"] = max(worst["hf"], abs(mine[2] - hf))
    ok = worst["cp"] < 5e-3 and worst["s"] < 2e-3 and worst["hf"] < 0.1
    return _case("thermo_species_vs_janaf", "thermo", ok, dict(worst=worst, values=rows),
                 "cp rel<0.5%, S rel<0.2%, dHf<0.1 kJ/mol", "NIST-JANAF 298.15 K")


def thermo_inversion():
    mix = Mixture.standard()
    rng = np.random.default_rng(4)
    Y = rng.random((400, mix.ns))
    Y /= Y.sum(axis=1, keepdims=True)
    T = rng.uniform(250.0, 3400.0, 400)
    T[:20] = 1000.0  # fit seam
    Tback = mix.temperature_from_energy(Y, mix.internal_energy(Y, T))
    err = float(np.max(np.abs(Tback - T)))
    return _case("thermo_energy_inversion", "thermo", err < 1e-7, dict(max_abs_error_K=err),
                 "|T - T(e(T))| < 1e-7 K", "round trip")


def stoichiometry():
    mix = Mixture.standard()
    afr, lhv = stoichiometric_afr(mix, "IC8H18"), lower_heating_value(mix, "IC8H18")
    elem, mass = 0.0, 0.0
    for phi in np.linspace(0.5, 1.6, 23):
        y = premixed_charge(mix, "IC8H18", phi)
        d = products_change(mix, "IC8H18", y[0], y[1])
        elem = max(elem, float(np.max(np.abs(mix.element_masses(d)))))
        mass = max(mass, abs(float(d.sum())))
    ok = abs(afr - 15.13) / 15.13 < 2e-3 and abs(lhv / 1e6 - 44.3) / 44.3 < 0.015 and elem < 1e-15 and mass < 1e-15
    return _case("stoichiometry_afr_lhv_elements", "thermo", ok,
                 dict(afr=afr, lhv_MJ_kg=lhv / 1e6, max_element_change_kmol=elem, max_mass_change=mass),
                 "AFR 15.13 +/-0.2%, LHV 44.3 MJ/kg +/-1.5%, elements & mass < 1e-15",
                 "Heywood (1988) App. D isooctane; element balance")


# --------------------------------------------------------------- geometry
def geometry_checks():
    from ..kinematics import piston_position
    g = SliderCrank(0.086, 0.086, 0.143, 11.0)
    th = np.linspace(-360, 360, 1441)
    pos = max(abs(g.position(t) - piston_position(86, 143, t) * 1e-3) for t in th)
    h = 1e-4
    fd = max(abs((g.volume(t + h) - g.volume(t - h)) / math.radians(2 * h)
                 / (g.piston_area * g.dposition_dtheta(t)) - 1)
             for t in th if abs(g.dposition_dtheta(t)) > 1e-4)
    ends = abs(g.volume(0) - g.clearance_volume) + abs(g.volume(180) - g.clearance_volume - g.displacement)
    ok = pos < 1e-15 and fd < 1e-6 and ends < 1e-18
    return _case("slider_crank", "geometry", ok, dict(position_vs_shared_kernel=pos, dvdtheta_fd_rel=fd,
                 tdc_bdc_volume_error=ends), "exact reuse; FD rel<1e-6", "motorsim.kinematics, central FD")


# ------------------------------------------------------------------- flux
def hllc_vs_gas1d(samples=300):
    from ..gas1d.eos import IdealGas
    from ..gas1d.riemann import estimate_wave_speeds, hllc_flux
    from .duct import hllc
    eos = IdealGas(287.0, 1.35)
    mix = Mixture((Species.calorically_perfect("G", R_UNIVERSAL / 287.0, 1.35),))
    rng = np.random.default_rng(7)
    worst = 0.0
    for _ in range(samples):
        states = []
        for _side in range(2):
            rho, u, p, y = rng.uniform(0.2, 3), rng.uniform(-400, 400), rng.uniform(2e4, 5e5), rng.uniform(0, 1)
            states.append((rho, u, p, y))
        ref, _, _ = hllc_flux(states[0], states[1], eos)
        sl, sr = estimate_wave_speeds(states[0], states[1], eos)

        def face(s):
            rho, u, p, y = s
            T = p / (rho * 287.0)
            e = float(mix.internal_energy(np.ones(1), T))
            return dict(rho=np.array([rho]), u=np.array([u]), p=np.array([p]), Y=np.ones((1, 1)),
                        xb=np.array([y]), E=np.array([rho * (e + 0.5 * u * u)]),
                        a=np.array([math.sqrt(1.35 * p / rho)]))
        F, _, _ = hllc(face(states[0]), face(states[1]), 1, speeds=(np.array([sl]), np.array([sr])))
        mine = (F[0, 0], F[0, 2], F[0, 3], F[0, 1])  # mass, momentum, energy, tracer(=gas1d Y)
        scale = max(abs(v) for v in ref) + 1.0
        worst = max(worst, max(abs(a - b) for a, b in zip(mine, ref)) / scale)
    return _case("hllc_vs_frozen_gas1d", "flux", worst < 1e-12, dict(max_rel_difference=worst, samples=samples),
                 "max |F - F_gas1d| / scale < 1e-12 (same wave speeds)", "motorsim.gas1d.riemann.hllc_flux (frozen P1)")


# ------------------------------------------------------- duct test bench
class DuctBench:
    """SSPRK2 on one duct with two restriction ends (wall when area = 0)."""

    def __init__(self, duct: Duct, left: tuple, right: tuple, cfl=0.8):
        self.duct, self.ends, self.cfl = duct, {"left": left, "right": right}, cfl

    def _rhs(self, q):
        d = self.duct
        w = d.primitive(q)
        F = np.empty((d.n + 1, d.nv))
        s = np.empty(d.n + 1)
        F[1:-1], s[1:-1], _ = d.interior_flux(w)
        mdot = {}
        for side, index in (("left", 0), ("right", -1)):
            gas, a_in, a_out = self.ends[side]
            cell = EndCell.from_primitive(w, index)
            gas = gas or VolumeGas(cell.p, cell.T, cell.Y, cell.xb, cell.h, cell.R, cell.cp)
            r = restriction_flux(cell, side, float(d.area[index]), a_in, a_out, gas, d.ns)
            F[index], s[index] = r.flux_x, abs(cell.u) + cell.a
            mdot[side] = r.mdot_into_duct
        S, _ = d.sources(w)
        return (F[:-1] - F[1:] + S) / d.volume[:, None], F, d.time_step_limit(w, s), mdot

    def run(self, q, t_end, *, probe=None, max_steps=10 ** 7):
        t, steps = 0.0, 0
        boundary = np.zeros(self.duct.nv)
        trace = []
        while t < t_end - 1e-15 and steps < max_steps:
            d0, F0, lim, m0 = self._rhs(q)
            dt = min(self.cfl * lim, t_end - t)
            q1 = q + dt * d0
            d1, F1, _, m1 = self._rhs(q1)
            q = 0.5 * (q + q1 + dt * d1)
            boundary += 0.5 * dt * ((F0[0] - F0[-1]) + (F1[0] - F1[-1]))
            t += dt
            steps += 1
            if probe is not None:
                trace.append((t, probe(q), 0.5 * (m0["left"] + m1["left"]), 0.5 * (m0["right"] + m1["right"])))
        return dict(q=q, t=t, steps=steps, boundary=boundary, trace=trace)


def _uniform_duct(mix, n, length=1.0, diameter=0.04, second_order=True, limiter="minmod"):
    return Duct("bench", mix, [{"length": length * 1e3, "start_diameter": diameter * 1e3,
                                "end_diameter": diameter * 1e3}], length / n, second_order=second_order,
                limiter=limiter)


def _closed():
    return (None, 0.0, 0.0)


def sod_shock_tube(resolutions=(100, 200, 400, 800)):
    from ..gas1d.eos import IdealGas
    from ..gas1d.exact_riemann_reference_v1 import exact_riemann_v1
    mix = air_cp_mixture(1.4, 287.0)
    eos = IdealGas(287.0, 1.4)
    left, right = (1.0, 0.0, 1e5, 0.0), (0.125, 0.0, 1e4, 0.0)
    exact = exact_riemann_v1(left, right, eos=eos)
    t_end = 0.2 / math.sqrt(1e5)
    errors, conservation = [], []
    for n in resolutions:
        duct = _uniform_duct(mix, n)
        q = duct.uniform(1e5, 1e5 / 287.0, np.ones(1))
        hi = duct.centers > 0.5
        q[hi] = duct.uniform(1e4, 1e4 / (0.125 * 287.0), np.ones(1))[hi]
        inv0 = duct.inventory(q)
        out = DuctBench(duct, _closed(), _closed(), cfl=0.8).run(q, t_end)
        w = duct.primitive(out["q"])
        rho_ex = np.array([exact.sample((x - 0.5) / t_end)[0] for x in duct.centers])
        errors.append(float(np.sum(np.abs(w["rho"] - rho_ex) * duct.dx)))
        inv1 = duct.inventory(out["q"])
        conservation.append(float(max(abs(inv1[0] - inv0[0]) / inv0[0], abs(inv1[-1] - inv0[-1]) / inv0[-1])))
    orders = [math.log2(a / b) for a, b in zip(errors, errors[1:])]
    ok = all(b < a for a, b in zip(errors, errors[1:])) and orders[-1] > 0.6 and max(conservation) < 1e-13
    return _case("sod_shock_tube_exact_riemann", "duct", ok,
                 dict(resolutions=list(resolutions), L1_density_error=errors, observed_order=orders,
                      max_relative_conservation_error=conservation),
                 "monotone L1 decrease, finest order > 0.6 (discontinuous data), conservation < 1e-13",
                 "exact Riemann solution, motorsim.gas1d.exact_riemann_reference_v1")


ACOUSTIC_TARGETS = {"unlimited_central": 1.9, "van_leer": 1.6, "mc": 1.6, "minmod": 1.35, "first_order": 0.8}


def smooth_acoustic_order(resolutions=(100, 200, 400, 800), limiter="minmod"):
    """Self-convergence on a 1% Gaussian acoustic pulse (thermally perfect air).

    TVD limiters clip smooth extrema, so their L1 order sits between 1 and 2;
    the unlimited central slope isolates the formal order of the scheme."""
    mix = Mixture.standard()
    air = dry_air(mix)
    second_order = limiter != "first_order"
    sols = []
    for n in resolutions:
        duct = _uniform_duct(mix, n, second_order=second_order,
                             limiter=limiter if second_order else "minmod")
        x = duct.centers
        p = 1e5 * (1 + 0.01 * np.exp(-((x - 0.5) / 0.05) ** 2))
        T = 300.0 * (p / 1e5) ** (0.4 / 1.4)
        q = np.vstack([duct.uniform(pi, Ti, air)[0] for pi, Ti in zip(p, T)])
        out = DuctBench(duct, _closed(), _closed(), cfl=0.6).run(q, 8e-4)
        sols.append((duct, duct.primitive(out["q"])["p"]))
    errs = []
    for (dc, pc), (df, pf) in zip(sols, sols[1:]):
        restricted = (pf[0::2] * df.volume[0::2] + pf[1::2] * df.volume[1::2]) / (df.volume[0::2] + df.volume[1::2])
        errs.append(float(np.sum(np.abs(pc - restricted) * dc.dx)))
    orders = [math.log2(a / b) for a, b in zip(errs, errs[1:])]
    target = ACOUSTIC_TARGETS[limiter]
    return _case(f"acoustic_pulse_self_convergence_{limiter}", "duct", orders[-1] > target,
                 dict(resolutions=list(resolutions), successive_differences=errs, observed_order=orders),
                 f"observed L1 order (finest pair) > {target}", "Richardson self-convergence (smooth solution)")


def well_balanced_area_change():
    mix = Mixture.standard()
    air = dry_air(mix)
    duct = Duct("taper", mix, [{"length": 200, "start_diameter": 30, "end_diameter": 60},
                               {"length": 200, "start_diameter": 60, "end_diameter": 25}], 0.005)
    q = duct.uniform(1e5, 300.0, air)
    out = DuctBench(duct, _closed(), _closed()).run(q, 5e-3)
    umax = float(np.max(np.abs(duct.primitive(out["q"])["u"])))
    return _case("quiescent_variable_area", "duct", umax < 1e-9, dict(max_velocity_m_s=umax, steps=out["steps"]),
                 "|u| < 1e-9 m/s after 5 ms", "exact rest state")


def quarter_wave_resonance():
    mix = Mixture.standard()
    air = dry_air(mix)
    L = 0.5
    duct = _uniform_duct(mix, 200, length=L)
    q = duct.uniform(1.002e5, 300.0 * 1.002 ** (0.4 / 1.4), air)
    amb = VolumeGas.from_mixture(mix, 1e5, 300.0, air, 0.0)
    A = float(duct.area[-1])
    a = float(mix.sound_speed(air, 300.0))
    period = 4 * L / a
    out = DuctBench(duct, _closed(), (amb, A, A)).run(q, 6.2 * period,
                                                      probe=lambda qq: duct.primitive(qq[:1])["p"][0])
    t = np.array([r[0] for r in out["trace"]])
    p = np.array([r[1] for r in out["trace"]]) - 1e5
    crossings = []
    for i in range(1, len(p)):
        if p[i - 1] > 0 >= p[i] or p[i - 1] < 0 <= p[i]:
            crossings.append(t[i - 1] + (t[i] - t[i - 1]) * p[i - 1] / (p[i - 1] - p[i]))
    measured = 2 * float(np.mean(np.diff(crossings))) if len(crossings) > 3 else float("nan")
    rel = abs(measured - period) / period
    return _case("quarter_wave_closed_open_pipe", "duct", rel < 0.01,
                 dict(analytic_period_s=period, measured_period_s=measured, relative_error=rel,
                      zero_crossings=len(crossings)),
                 "|T - 4L/a| / T < 1%", "linear acoustics f = a/(4L), ideal open end")


def choked_nozzle_steady():
    mix = Mixture.standard()
    air = dry_air(mix)
    duct = _uniform_duct(mix, 60, length=0.3)
    A = float(duct.area[0])
    up = VolumeGas.from_mixture(mix, 2e5, 300.0, air, 0.0)
    down = VolumeGas.from_mixture(mix, 1e5, 300.0, air, 0.0)
    Ae = 0.1 * A
    q = duct.uniform(2e5, 300.0, air)
    out = DuctBench(duct, (up, A, A), (down, Ae, Ae)).run(q, 0.15, probe=lambda qq: 0.0)
    tr = np.array([(r[0], r[2], r[3]) for r in out["trace"]])
    window = tr[:, 0] > 0.12  # the start-up wave system decays geometrically (~1e-7 by 0.12 s)
    m_in, m_out = float(tr[window, 1].mean()), float(-tr[window, 2].mean())
    ideal = orifice_mass_flow(Ae, 2e5, 300.0, up.R, up.gamma, 1e5)
    rel = abs(m_out - ideal) / ideal
    steady = abs(m_in - m_out) / ideal
    return _case("choked_restriction_steady_flow", "duct", rel < 1e-3 and steady < 1e-4,
                 dict(mdot_kg_s=m_out, isentropic_choked_kg_s=ideal, relative_difference=rel,
                      inlet_outlet_relative_mismatch=steady,
                      note="stage-1 value was -0.234 % and was explained away as an 'expected' hypothesis "
                           "deficit; it was the signature of the static-as-total-pressure defect "
                           "(removed in QUASI_STEADY_RESTRICTION_V2, now ~3e-6)"),
                 "|mdot - mdot*| / mdot* < 0.1 % ; |mdot_in - mdot_out| / mdot* < 1e-4",
                 "isentropic choked orifice, Heywood App. C")


def orifice_function():
    g = 1.4
    star = psi(0.0, g)
    crit = (2 / (g + 1)) ** (g / (g - 1))
    jump = abs(psi(crit * (1 + 1e-9), g) - star)
    ok = abs(star - 0.684731) < 1e-6 and jump < 1e-6 and psi(1.0, g) == 0.0
    return _case("orifice_psi", "duct", ok, dict(choked=star, continuity_jump=jump),
                 "psi* = 0.684731 (gamma 1.4); continuous at critical ratio", "compressible orifice theory")


# --------------------------------------------------------------- cylinder
def _closed_engine(mix, geometry, *, combustion=None, dtheta=0.25, theta_start=-180.0):
    cyl = Cylinder("cylinder", mix, geometry, combustion=combustion)
    return FourStrokeEngine(mix, cyl, {}, [], 3000.0, max_dtheta=dtheta, theta_start=theta_start)


def _motoring_reference(mix, air, geo, m, p0, T0, theta0=-180.0, theta1=540.0):
    """Reversible adiabatic compression/expansion of a frozen mixture, dT/dtheta = -(R T / cv) V'/V,
    integrated with DOP853 (independent of the engine integrator and of its energy bookkeeping)."""
    from scipy.integrate import solve_ivp
    R = float(mix.gas_constant(air))

    def rhs(th, y):
        T = y[0]
        cv = float(mix.cp(air, T)) - R
        dV = geo.piston_area * geo.dposition_dtheta(math.degrees(th))
        return [-R * T / cv * dV / geo.volume(math.degrees(th))]
    sol = solve_ivp(rhs, (math.radians(theta0), math.radians(theta1)), [T0], method="DOP853",
                    rtol=1e-12, atol=1e-9, dense_output=True)
    return lambda th_deg: m * R * sol.sol(np.radians(th_deg))[0] / geo.volume(th_deg)


def isentropic_motoring(dthetas=(1.0, 0.5, 0.25)):
    """Criterion (a priori): observed order >= 2 - 0.3 against EXACT/independent references and
    p(theta) within 0.1 % of the independent ODE at the production step (0.5 deg)."""
    geo = SliderCrank(0.086, 0.086, 0.143, 11.0)
    cp_mix = air_cp_mixture(1.4, 287.0)
    errs = []
    for dth in dthetas:
        eng = _closed_engine(cp_mix, geo, dtheta=dth)
        st = eng.initial_state(cylinder=dict(p=1e5, T=300.0, Y=np.ones(1), xb=0.0), ducts={})
        r = eng.run(st, 1)
        tr = r["cycles"][0].trace
        pv = np.array(tr["p"]) * np.array(tr["V"]) ** 1.4
        errs.append(float(np.max(np.abs(pv / pv[0] - 1))))
    orders = [math.log2(a / b) for a, b in zip(errs, errs[1:])]
    mix = Mixture.standard()
    air = dry_air(mix)
    ref_errs, drifts, closures = [], [], []
    for dth in dthetas:
        eng = _closed_engine(mix, geo, dtheta=dth)
        st = eng.initial_state(cylinder=dict(p=1e5, T=300.0, Y=air, xb=0.0), ducts={})
        r = eng.run(st, 1)
        tr = r["cycles"][0].trace
        th, p = np.array(tr["theta"]), np.array(tr["p"])
        m = float(r["cycles"][0].trace["mass"][0])
        ref = _motoring_reference(mix, air, geo, m, 1e5, 300.0)
        ref_errs.append(float(np.max(np.abs(p / np.array([ref(t) for t in th]) - 1))))
        s = np.array([float(mix.entropy(air, T, pp)) for T, pp in zip(tr["T"], tr["p"])])
        drifts.append(float(np.max(np.abs(s - s[0])) / float(mix.cp(air, 300.0))))
        closures.append(r["closure"]["energy"])
    ref_orders = [math.log2(a / b) for a, b in zip(ref_errs, ref_errs[1:])]
    at_prod = ref_errs[dthetas.index(0.5)] if 0.5 in dthetas else ref_errs[-1]
    ok = (orders[-1] >= 1.7 and ref_orders[-1] >= 1.7 and at_prod < 1e-3 and max(closures) < 1e-12)
    return _case("isentropic_motoring", "cylinder", ok,
                 dict(dtheta=list(dthetas), max_rel_pV_gamma_error=errs, observed_order=orders,
                      nasa_gas_error_vs_independent_ode=ref_errs, nasa_gas_order_vs_ode=ref_orders,
                      nasa_gas_entropy_drift_over_cp=drifts, energy_closure=closures,
                      note="stage-1 entropy-drift threshold (1e-5) was set after seeing 3.65e-6 and is dropped; "
                           "entropy drift is reported only"),
                 "order >= 1.7 (pV^gamma and NASA gas vs independent ODE); NASA-gas p(theta) within 0.1 % of the "
                 "ODE at dtheta = 0.5 deg; energy closure < 1e-12",
                 "pV^gamma = const (exact, calorically perfect); DOP853 reversible-adiabatic ODE with NASA cp(T)")


def burn_vs_independent_ode(dthetas=(0.5, 0.25, 0.125)):
    """Closed adiabatic cylinder with Wiebe burn vs temperature-form ODE (SciPy DOP853)."""
    from scipy.integrate import solve_ivp
    mix = Mixture.standard()
    geo = SliderCrank(0.086, 0.086, 0.143, 11.0)
    wiebe = Wiebe(-20.0, 55.0)
    comb = CombustionSpec("IC8H18", wiebe, 0.98)
    charge = premixed_charge(mix, "IC8H18", 1.0)
    p0, T0 = 1e5, 330.0
    m0 = p0 * geo.volume(-180.0) / (float(mix.gas_constant(charge)) * T0)
    mi0 = m0 * charge
    delta = products_change(mix, "IC8H18", 0.98 * mi0[0], mi0[1])
    I = np.eye(mix.ns)
    rpm = 3000.0
    w_rad = rpm * 2 * math.pi / 60

    def u_species(T):
        return np.array([float(mix.internal_energy(I[i], T)) for i in range(mix.ns)])

    def cv_species(T):
        return np.array([float(mix.cp(I[i], T) - mix.gas_constant(I[i])) for i in range(mix.ns)])

    def rhs(theta, y):
        T = y[0]
        x = wiebe.fraction(theta - wiebe.start_deg)
        dx = wiebe.rate_per_deg(theta - wiebe.start_deg) * 180 / math.pi  # per rad
        mi = mi0 + delta * x
        m = mi.sum()
        V = geo.volume(theta)
        p = m * float(mix.gas_constant(mi / m)) * T / V
        dV = geo.piston_area * geo.dposition_dtheta(theta)  # per rad
        return [(-p * dV - u_species(T) @ delta * dx) / (mi @ cv_species(T))]

    def pressure(theta, T):
        mi = mi0 + delta * wiebe.fraction(theta - wiebe.start_deg)
        return mi.sum() * float(mix.gas_constant(mi / mi.sum())) * T / geo.volume(theta)

    errs, closures = [], []
    for dth in dthetas:
        eng = _closed_engine(mix, geo, combustion=comb, dtheta=dth)
        st = eng.initial_state(cylinder=dict(p=p0, T=T0, Y=charge, xb=0.0), ducts={})
        r = eng.run(st, 1)
        tr = r["cycles"][0].trace
        th = np.array(tr["theta"])
        sel = th <= 180.0
        th, pm = th[sel], np.array(tr["p"])[sel]
        ref = np.empty_like(pm)
        T_start = T0
        knots = [-180.0, wiebe.start_deg, wiebe.start_deg + wiebe.duration_deg, 180.0]
        for a, b in zip(knots, knots[1:]):
            mask = (th >= a) & (th <= b)
            sol = solve_ivp(lambda t, y: [v / w_rad * w_rad for v in rhs(math.degrees(t), y)],
                            (math.radians(a), math.radians(b)), [T_start], method="DOP853",
                            rtol=1e-12, atol=1e-9, dense_output=True)
            Ts = sol.sol(np.radians(th[mask]))[0]
            ref[mask] = [pressure(t, T) for t, T in zip(th[mask], Ts)]
            T_start = float(sol.y[0, -1])
        errs.append(float(np.max(np.abs(pm - ref)) / ref.max()))
        closures.append(r["closure"]["energy"])
    orders = [math.log2(a / b) for a, b in zip(errs, errs[1:])]
    ok = errs[-1] < 1e-4 and orders[-1] > 1.7 and max(closures) < 1e-12
    return _case("closed_cylinder_burn_vs_independent_ode", "cylinder", ok,
                 dict(dtheta=list(dthetas), max_rel_pressure_difference=errs, observed_order=orders,
                      energy_closure=closures),
                 "finest max |p - p_ref|/p_max < 1e-4; order > 1.7; energy closure < 1e-12",
                 "temperature-form single-zone ODE, scipy DOP853 rtol 1e-12 (independent formulation)")


# ----------------------------------------------------------------- engine
def engine_conservation_and_periodicity(config_path=None, max_cycles=12, dx_mm=10.0):
    from .config import EXAMPLE_PATH, load
    from .runner import run_operating_point
    cfg = load(config_path or EXAMPLE_PATH)
    out = run_operating_point(cfg, overrides={"numerics": {"dx_mm": dx_mm}}, max_cycles=max_cycles)
    s = out["summary"]
    closure = s["conservation"]["max_relative_closure"]
    ok = (s["status"] == "completed" and s["periodicity"]["status"] == "PERIODIC_CONVERGED"
          and max(closure.values()) < 1e-12)
    return _case(f"engine_example_dx{dx_mm:g}mm", "engine", ok,
                 dict(periodicity=s["periodicity"]["status"], cycles=s["cycles_run"], closure=closure,
                      final=s["final_cycle"], wall_seconds=s["wall_seconds"]),
                 "completed, periodic (preregistered tolerances), ledger closure < 1e-12",
                 "conservation identities; cycle-to-cycle periodicity"), s


def gci(f1, f2, f3, r=2.0, fs=1.25):
    """Celik et al. (2008) GCI for fine f1, medium f2, coarse f3 with ratio r."""
    e21, e32 = f2 - f1, f3 - f2
    if e21 == 0 or e32 == 0 or e32 / e21 <= 0:
        return dict(order=None, gci_fine=None, extrapolated=None, monotone=False)
    p = abs(math.log(abs(e32 / e21))) / math.log(r)
    ext = (r ** p * f1 - f2) / (r ** p - 1)
    return dict(order=p, gci_fine=fs * abs(e21 / f1) / (r ** p - 1), extrapolated=ext, monotone=True)


def engine_mesh_convergence(spacings=(20.0, 10.0, 5.0), max_cycles=14):
    results = {}
    cases = []
    for dx in spacings:
        case, s = engine_conservation_and_periodicity(max_cycles=max_cycles, dx_mm=dx)
        cases.append(case)
        results[dx] = s["final_cycle"]
    keys = ("imep_net_bar", "volumetric_efficiency_intake_valve", "p_max_bar", "pmep_bar", "trapped_mass_mg")
    coarse, medium, fine = (results[d] for d in spacings)
    study = {k: dict(values=[coarse[k], medium[k], fine[k]], **gci(fine[k], medium[k], coarse[k])) for k in keys}
    ok = all(c["passed"] for c in cases) and all(
        abs(study[k]["values"][2] - study[k]["values"][1]) / abs(study[k]["values"][2]) < 0.02 for k in keys)
    return cases + [_case("engine_mesh_convergence_gci", "engine", ok, dict(dx_mm=list(spacings), study=study),
                          "all runs periodic & conservative; medium-fine change < 2% for every indicator",
                          "Richardson/GCI, Celik et al. (2008) J. Fluids Eng. 130:078001")]


def run_suite(out_dir, quick=False):
    started = time.monotonic()
    cases = []
    for fn in (thermo_reference, thermo_inversion, stoichiometry, geometry_checks, orifice_function,
               hllc_vs_gas1d, sod_shock_tube, well_balanced_area_change,
               quarter_wave_resonance, choked_nozzle_steady, isentropic_motoring, burn_vs_independent_ode):
        t = time.monotonic()
        case = fn()
        case["wall_seconds"] = time.monotonic() - t
        cases.append(case)
    from .verification_stage2 import stage2_cases
    for case in stage2_cases():
        cases.append(case)
    if quick:
        case, _ = engine_conservation_and_periodicity(max_cycles=12, dx_mm=20.0)
        cases.append(case)
    else:
        cases.extend(engine_mesh_convergence())
    report = dict(schema="DINO4T_VERIFICATION_REPORT_V1", evidence_level="L1_NUMERICAL_VERIFICATION",
                  experimental_validation="NOT_PERFORMED",
                  passed=[c["name"] for c in cases if c["passed"] and not c.get("informational")],
                  failed=[c["name"] for c in cases if not c["passed"] and not c.get("informational")],
                  informational=[c["name"] for c in cases if c.get("informational")],
                  cases=cases, wall_seconds=time.monotonic() - started)
    from .runner import _jsonable
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "verification_report.json").write_text(json.dumps(_jsonable(report), indent=2), encoding="utf-8")
    return report
