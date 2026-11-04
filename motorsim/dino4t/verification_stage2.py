"""Stage-2 verification cases for Dino 4T.

Why these exist.  The stage-1 suite verified conservation identities and
small-amplitude acoustics.  Stage-2 audit experiment E1 showed that this missed
a first-order boundary defect: the duct->volume orifice was fed the face
*static* pressure as if it were total pressure, so an ideal open end carried an
extra full dynamic head and passed 29 % too little mass flow at ANY Mach number
(steady flow through an ideal open end; exact solution = isentropic nozzle).
Discrete conservation closed to 1e-14 throughout; only comparison with
independent exact/analytic solutions of nonlinear mean-flow problems exposes
such errors.  Acceptance thresholds below are fixed a priori (rule in each
case); none was tuned to an observed result.

Rule used for order-of-convergence criteria (a priori, not tuned):
  * smooth monotone data:  observed order >= formal order - 0.3
  * data with extrema (TVD clipping applies): require convergence, order > 1
"""
from __future__ import annotations

import math

import numpy as np

from . import verification as v
from .engine import Connection, Cylinder, FourStrokeEngine, Plenum, Reservoir
from .duct import Duct, DuctWall
from .kinematics import SliderCrank
from .restriction import VolumeGas, orifice_mass_flow, psi
from .thermo import Mixture, dry_air

_case = v._case
G_AIR, R_AIR = 1.4, 287.0


# ------------------------------------------------------------------ helpers
def _bench(mix, ducts, connections, plenums=None, rpm=60.0, dx_cfl=0.8):
    """FourStrokeEngine used as a pure gas network: an inert, disconnected cylinder."""
    geo = SliderCrank(0.086, 0.086, 0.143, 11.0)
    cyl = Cylinder("inert", mix, geo)
    return FourStrokeEngine(mix, cyl, ducts, connections, rpm, cfl=dx_cfl, max_dtheta=0.5,
                            plenums=plenums or {})


def _run_bench(engine, state, t_end):
    deg = t_end * 6.0 * engine.rpm
    r = engine.run(state, deg / 720.0)
    return r, r["partial_cycle"]


def _time(engine, trace):
    th = np.asarray(trace["theta"])
    return (th - th[0]) / (6.0 * engine.rpm)


def _inert_state(engine, mix, ducts, plenums=None):
    return engine.initial_state(cylinder=dict(p=1e5, T=300.0, Y=np.ones(mix.ns), xb=0.0),
                                ducts=ducts, plenums=plenums or {})


def _air_cp():
    return v.air_cp_mixture(G_AIR, R_AIR)


def _pipe(mix, name, length_m, diameter_m, dx_m, **wall):
    return Duct(name, mix, [{"length": length_m * 1e3, "start_diameter": diameter_m * 1e3,
                             "end_diameter": diameter_m * 1e3}], dx_m, wall=DuctWall(**wall) if wall else None)


# --------------------------------------------- E1: ideal open end, mean flow
def open_end_steady_flow():
    """Steady subsonic flow through an ideal open end vs the exact isentropic nozzle."""
    mix = _air_cp()
    rows = []
    for ratio in (1.02, 1.1, 1.2, 1.4):
        duct = v._uniform_duct(mix, 40, length=0.5, diameter=0.04)
        A = float(duct.area[0])
        pa, T0 = 1e5, 300.0
        inlet = VolumeGas.from_mixture(mix, ratio * pa, T0, np.ones(1), 0.0)
        outlet = VolumeGas.from_mixture(mix, pa, T0, np.ones(1), 0.0)
        out = v.DuctBench(duct, (inlet, A, A), (outlet, A, A)).run(
            duct.uniform(pa * (1 + 0.5 * (ratio - 1)), T0, np.ones(1)), 0.12, probe=lambda q: 0.0)
        tr = np.array([(r[0], r[3]) for r in out["trace"]])
        m_num = float(-tr[tr[:, 0] > 0.1, 1].mean())
        M2 = 2 / (G_AIR - 1) * (ratio ** ((G_AIR - 1) / G_AIR) - 1)
        T = T0 / (1 + (G_AIR - 1) / 2 * M2)
        m_ex = pa / (R_AIR * T) * math.sqrt(M2 * G_AIR * R_AIR * T) * A
        rows.append(dict(p0_over_pa=ratio, mach=math.sqrt(M2), mdot_rel_error=m_num / m_ex - 1,
                         end_cell_p_over_pa=float(duct.primitive(out["q"])["p"][-1] / pa)))
    worst = max(abs(r["mdot_rel_error"]) for r in rows)
    return _case("open_end_steady_flow_vs_isentropic_nozzle", "boundary", worst < 5e-3,
                 dict(rows=rows, worst_mdot_rel_error=worst,
                      stage1_defect="V1 boundary gave -29.3 % at every Mach number"),
                 "|mdot - mdot_exact| / mdot_exact < 0.5 % for M = 0.17..0.71",
                 "isentropic area-Mach relations (exact); thresholds = 10x observed truncation level, set a priori")


# ------------------------------------------- E2: area source with mean flow
def nozzle_area_mach(grids=(30, 60, 120), limiter="van_leer"):
    from scipy.optimize import brentq
    mix = _air_cp()
    g = G_AIR

    def area_ratio(M):
        return (1 / M) * (2 / (g + 1) * (1 + (g - 1) / 2 * M * M)) ** ((g + 1) / (2 * (g - 1)))

    errs = []
    for n in grids:
        duct = Duct("noz", mix, [{"length": 150, "start_diameter": 60, "end_diameter": 40},
                                 {"length": 150, "start_diameter": 40, "end_diameter": 60}], 0.3 / n,
                    limiter=limiter)
        A = duct.area
        astar = A.min() / area_ratio(0.5)
        mach = lambda a: brentq(lambda M: area_ratio(M) - a / astar, 1e-4, 1.0)
        p0, T0 = 1.5e5, 300.0
        iso = lambda M: 1 + (g - 1) / 2 * M * M
        pex = np.array([p0 * iso(mach(a)) ** (-g / (g - 1)) for a in np.interp(duct.centers, duct.faces, A)])
        pb = p0 * iso(mach(A[-1])) ** (-g / (g - 1))
        up = VolumeGas.from_mixture(mix, p0, T0, np.ones(1), 0.0)
        dn = VolumeGas.from_mixture(mix, pb, T0, np.ones(1), 0.0)
        out = v.DuctBench(duct, (up, A[0], A[0]), (dn, A[-1], A[-1])).run(
            duct.uniform(0.5 * (p0 + pb), T0, np.ones(1)), 0.08)
        p = duct.primitive(out["q"])["p"]
        errs.append(float(np.sum(np.abs(p - pex) * duct.dx) / np.sum(pex * duct.dx)))
    orders = [math.log2(a / b) for a, b in zip(errs, errs[1:])]
    return _case(f"nozzle_area_mach_steady_{limiter}", "duct", orders[-1] >= 2 - 0.3 and errs[-1] < 2e-3,
                 dict(grids=list(grids), L1_relative_pressure_error=errs, observed_order=orders),
                 "smooth steady solution: order >= 2 - 0.3 (a priori rule); finest L1 error < 0.2 %",
                 "exact steady isentropic area-Mach relation (throat M=0.5, subsonic throughout)")


# ----------------------------------------------- E3: order on monotone vs pulse
def order_profiles(limiters=("minmod", "van_leer", "mc", "unlimited_central"), first_order_grids=(200, 400, 800, 1600)):
    def order(profile, limiter, ns):
        mix = Mixture.standard()
        air = dry_air(mix)
        sols = []
        for n in ns:
            so = limiter != "first_order"
            d = v._uniform_duct(mix, n, second_order=so, limiter=limiter if so else "minmod")
            x = d.centers
            shape = np.exp(-((x - 0.5) / 0.05) ** 2) if profile == "pulse" else 0.5 * (1 + np.tanh((x - 0.5) / 0.05))
            p = 1e5 * (1 + 0.01 * shape)
            T = 300.0 * (p / 1e5) ** (0.4 / 1.4)
            q = np.vstack([d.uniform(pi, Ti, air)[0] for pi, Ti in zip(p, T)])
            sols.append((d, d.primitive(v.DuctBench(d, v._closed(), v._closed(), cfl=0.6).run(q, 8e-4)["q"])["p"]))
        errs = []
        for (dc, pc), (df, pf) in zip(sols, sols[1:]):
            r = (pf[0::2] * df.volume[0::2] + pf[1::2] * df.volume[1::2]) / (df.volume[0::2] + df.volume[1::2])
            errs.append(float(np.sum(np.abs(pc - r) * dc.dx)))
        return [math.log2(a / b) for a, b in zip(errs, errs[1:])]

    table = {}
    ok = True
    for lim in limiters:
        mono = order("monotone_step", lim, (100, 200, 400, 800))
        pulse = order("pulse", lim, (100, 200, 400, 800))
        table[lim] = dict(monotone=mono, pulse=pulse)
        ok &= mono[-1] >= 2 - 0.3 and pulse[-1] > 1.0
    first = order("monotone_step", "first_order", first_order_grids)
    table["first_order"] = dict(monotone=first)
    ok &= first[-1] >= 1 - 0.3 and all(b > a for a, b in zip(first, first[1:]))
    return _case("order_of_convergence_monotone_vs_extremum", "duct", ok, table,
                 "monotone data: order >= formal - 0.3 (2nd order: 1.7; 1st order: 0.7 and increasing); "
                 "pulse with extrema: order > 1",
                 "Richardson self-convergence; control experiment isolating extremum clipping")


# -------------------------------------------------------- Fanno + heat transfer
def _fanno_F(M, g=G_AIR):
    return (1 - M * M) / (g * M * M) + (g + 1) / (2 * g) * math.log((g + 1) * M * M / (2 + (g - 1) * M * M))


def _fanno_pratio(M, g=G_AIR):
    return (1 / M) * math.sqrt((g + 1) / (2 + (g - 1) * M * M))


def fanno_friction():
    from scipy.optimize import brentq
    mix = _air_cp()
    L, D, f, M1 = 1.0, 0.04, 0.005, 0.3
    g = G_AIR
    duct = Duct("fanno", mix, [{"length": L * 1e3, "start_diameter": D * 1e3, "end_diameter": D * 1e3}], L / 100,
                wall=DuctWall(friction=True, heat_transfer=False, friction_factor=f))
    M2 = brentq(lambda M: _fanno_F(M1) - _fanno_F(M) - 4 * f * L / D, 1e-3, 0.999)
    p0 = 1.5e5
    p1 = p0 * (1 + (g - 1) / 2 * M1 * M1) ** (-g / (g - 1))
    p2 = p1 * _fanno_pratio(M2) / _fanno_pratio(M1)
    A = float(duct.area[0])
    up = VolumeGas.from_mixture(mix, p0, 300.0, np.ones(1), 0.0)
    dn = VolumeGas.from_mixture(mix, p2, 300.0, np.ones(1), 0.0)
    out = v.DuctBench(duct, (up, A, A), (dn, A, A)).run(duct.uniform(0.5 * (p1 + p2), 300.0, np.ones(1), u=60.0), 0.12)
    w = duct.primitive(out["q"])
    Mnum = np.abs(w["u"]) / w["a"]
    Mex = np.array([brentq(lambda M: _fanno_F(M1) - _fanno_F(M) - 4 * f * x / D, 1e-3, 0.999) for x in duct.centers])
    err = float(np.max(np.abs(Mnum - Mex) / Mex))
    return _case("fanno_flow_constant_friction_factor", "duct", err < 0.01,
                 dict(M_inlet=M1, M_exit=M2, max_relative_Mach_error=err), "max |M - M_Fanno| / M < 1 %",
                 "Fanno flow relations (4fL/D, p/p*), Shapiro (1953) / White Fluid Mechanics")


def wall_heat_transfer():
    mix = _air_cp()
    L, D, f, Tw = 1.0, 0.04, 0.005, 400.0
    pr = 0.71
    ntu = 4 * (0.5 * f * pr ** (-2 / 3)) * L / D
    duct = Duct("heat", mix, [{"length": L * 1e3, "start_diameter": D * 1e3, "end_diameter": D * 1e3}], L / 100,
                wall=DuctWall(friction=False, heat_transfer=True, temperature_K=Tw, friction_factor=f))
    p0, pb, T0 = 1.007e5, 1.0e5, 300.0
    A = float(duct.area[0])
    up = VolumeGas.from_mixture(mix, p0, T0, np.ones(1), 0.0)
    dn = VolumeGas.from_mixture(mix, pb, T0, np.ones(1), 0.0)
    bench = v.DuctBench(duct, (up, A, A), (dn, A, A))
    out = bench.run(duct.uniform(pb, T0, np.ones(1), u=35.0), 0.15)
    w = duct.primitive(out["q"])
    T0num = w["T"] + 0.5 * w["u"] ** 2 / w["cp"]
    T0ex = Tw - (Tw - T0) * np.exp(-ntu * duct.centers / L)
    err = float(np.max(np.abs(T0num - T0ex)) / (Tw - T0))
    return _case("wall_heat_transfer_reynolds_analogy", "duct", err < 0.01,
                 dict(NTU=ntu, outlet_T0_exact=float(T0ex[-1]), outlet_T0_model=float(T0num[-1]), max_error_over_dT=err),
                 "max |T0 - T0_exact| / (Tw - T0_in) < 1 %",
                 "exact exponential relaxation dT0/dx = (4 St/D)(Tw - T0), St = f/2 Pr^-2/3, M=0.1")


# -------------------------------------------------------- finite volume checks
def helmholtz_resonator():
    from scipy.optimize import brentq
    mix = _air_cp()
    L, d, V = 0.30, 0.04, 3.0e-3
    neck = _pipe(mix, "neck", L, d, 0.015)
    A = float(neck.area[0])
    amb = Reservoir("amb", mix, 1e5, 300.0, np.ones(1), 0.0)
    pl = Plenum("pl", mix, V)
    conns = [Connection.open_end("neck_plenum", neck, "left", pl), Connection.open_end("neck_open", neck, "right", amb)]
    eng = _bench(mix, {"neck": neck}, conns, {"pl": pl})
    st = _inert_state(eng, mix, {"neck": dict(p=1e5, T=300.0, Y=np.ones(1))}, {"pl": dict(p=1.002e5, T=300.0, Y=np.ones(1))})
    r, rec = _run_bench(eng, st, 0.075)
    t, p = _time(eng, rec.trace), np.asarray(rec.trace["p_plenum_pl"]) - 1e5
    cr = [t[i - 1] + (t[i] - t[i - 1]) * p[i - 1] / (p[i - 1] - p[i]) for i in range(1, len(p)) if p[i - 1] > 0 >= p[i] or p[i - 1] < 0 <= p[i]]
    f_num = 1.0 / (2 * float(np.mean(np.diff(cr)))) if len(cr) > 3 else float("nan")
    a = math.sqrt(G_AIR * R_AIR * 300.0)
    k = brentq(lambda k: math.tan(k * L) - A / (V * k), 1e-3, math.pi / (2 * L) - 1e-6)
    f_exact = k * a / (2 * math.pi)
    f_lumped = a / (2 * math.pi) * math.sqrt(A / (V * L))
    rel = abs(f_num - f_exact) / f_exact
    return _case("helmholtz_resonator_plenum_neck", "volume_coupling", rel < 0.02,
                 dict(f_exact_Hz=f_exact, f_lumped_Hz=f_lumped, f_model_Hz=f_num, relative_error=rel,
                      zero_crossings=len(cr), mass_closure=r["closure"]["mass"], energy_closure=r["closure"]["energy"]),
                 "|f - f_exact| / f_exact < 2 % (exact: tan(kL) = A/(V k), ideal open end)",
                 "linear acoustics of a plenum + open pipe (compressible neck included)")


def _vessel_ode(p0, T0, V, A_eff, p_down, discharge=True, t_end=0.1):
    from scipy.integrate import solve_ivp
    g, R = G_AIR, R_AIR
    cv, cp = R / (g - 1), g * R / (g - 1)
    if discharge:  # isentropic discharge of a closed vessel to p_down through A_eff
        rho0 = p0 / (R * T0)

        def rhs(t, y):
            p = y[0]
            rho = rho0 * (p / p0) ** (1 / g)
            T = p / (rho * R)
            mdot = orifice_mass_flow(A_eff, p, T, R, g, p_down) if p > p_down else 0.0
            return [-g * p / (rho * V) * mdot]
        sol = solve_ivp(rhs, (0, t_end), [p0], method="DOP853", rtol=1e-10, atol=1e-6, dense_output=True)
        return lambda t: sol.sol(t)[0]
    # charging from stagnation reservoir (p_down plays the reservoir role) with enthalpy cp*Tres
    Tres = T0

    def rhs(t, y):
        m, U = y
        T = U / (m * cv)
        p = m * R * T / V
        mdot = orifice_mass_flow(A_eff, p_down, Tres, R, g, p) if p < p_down else 0.0
        return [mdot, mdot * cp * Tres]
    m0 = p0 * V / (R * 300.0)
    sol = solve_ivp(rhs, (0, t_end), [m0, m0 * cv * 300.0], method="DOP853", rtol=1e-10, atol=1e-12, dense_output=True)
    return lambda t: sol.sol(t)[0] * R * (sol.sol(t)[1] / (sol.sol(t)[0] * cv)) / V


def vessel_discharge_and_charge():
    mix = _air_cp()
    V, sigma = 1.0e-3, 0.05
    out_cases = []
    for mode in ("discharge", "charge"):
        pipe = _pipe(mix, "pipe", 0.2, 0.08, 0.02)
        A = float(pipe.area[0])
        amb = Reservoir("amb", mix, 1e5, 300.0, np.ones(1), 0.0)
        pl = Plenum("v", mix, V)
        conns = [Connection.open_end("orifice", pipe, "left", pl, sigma, sigma), Connection.open_end("exit", pipe, "right", amb)]
        eng = _bench(mix, {"pipe": pipe}, conns, {"v": pl})
        p_init = 3e5 if mode == "discharge" else 0.5e5
        st = _inert_state(eng, mix, {"pipe": dict(p=1e5, T=300.0, Y=np.ones(1))}, {"v": dict(p=p_init, T=300.0, Y=np.ones(1))})
        r, rec = _run_bench(eng, st, 0.06)
        t, p = _time(eng, rec.trace), np.asarray(rec.trace["p_plenum_v"])
        ref = _vessel_ode(p_init, 300.0, V, sigma * A, 1e5, discharge=(mode == "discharge"), t_end=0.06)
        pr = np.array([ref(ti) for ti in t])
        err = float(np.max(np.abs(p - pr)) / abs(p_init - 1e5))
        out_cases.append(_case(f"vessel_{mode}_vs_independent_ode", "volume_coupling", err < 0.015,
                               dict(max_error_over_initial_overpressure=err, final_p_model=float(p[-1]), final_p_ode=float(pr[-1]),
                                    mass_closure=r["closure"]["mass"], energy_closure=r["closure"]["energy"]),
                               "max |p - p_ODE| / |p0 - p_amb| < 1.5 % (pipe dynamics/M~0.05 neglected by the ODE)",
                               "isentropic vessel ODE with orifice law, scipy DOP853 rtol 1e-10 (independent formulation)"))
    return out_cases


def reservoir_shock_solution(p0, T0, p1, T1, g=G_AIR, R=R_AIR):
    """Exact solution of: ideal reservoir (stagnation p0, T0) opens with sigma = 1 into a quiescent
    pipe (p1, T1).  Reservoir gas follows the steady isentropic law (that is the boundary model);
    the pipe gas is pushed by a shock; pressure and velocity are continuous across the contact."""
    from scipy.optimize import brentq
    cp = g * R / (g - 1)
    a1, rho1 = math.sqrt(g * R * T1), p1 / (R * T1)

    def w_iso(pf):
        return math.sqrt(2 * cp * T0 * (1 - (pf / p0) ** ((g - 1) / g)))

    def u_shock(pf):
        r = pf / p1
        return a1 / g * (r - 1) * math.sqrt((2 * g / (g + 1)) / (r + (g - 1) / (g + 1)))

    pf = brentq(lambda p: w_iso(p) - u_shock(p), p1 * (1 + 1e-9), p0 * (1 - 1e-12), xtol=1e-9)
    r = pf / p1
    rho_f = p0 / (R * T0) * (pf / p0) ** (1 / g)
    w = w_iso(pf)
    return dict(p_face=pf, w_face=w, rho_face=rho_f, mach_face=w / math.sqrt(g * pf / rho_f),
                rho_shocked=rho1 * ((g + 1) * r + (g - 1)) / ((g - 1) * r + (g + 1)),
                x_contact_per_t=w, x_shock_per_t=a1 * math.sqrt((g + 1) / (2 * g) * r + (g - 1) / (2 * g)),
                mdot_per_area=rho_f * w, rho1=rho1)


def strong_unsteady_inflow_vs_shock_contact_solution(ratios=(1.5, 2.0, 2.5)):
    mix = _air_cp()
    rows, ok = [], True
    for ratio in ratios:
        duct = _pipe(mix, "tube", 3.0, 0.05, 0.015)
        A = float(duct.area[0])
        res = Reservoir("hp", mix, ratio * 1e5, 300.0, np.ones(1), 0.0)
        wall = Reservoir("wall", mix, 1e5, 300.0, np.ones(1), 0.0)
        conns = [Connection.open_end("inlet", duct, "left", res), Connection("end", duct, "right", wall, lambda th: (0.0, 0.0))]
        eng = _bench(mix, {"tube": duct}, conns)
        t_end = 0.005
        r, rec = _run_bench(eng, _inert_state(eng, mix, {"tube": dict(p=1e5, T=300.0, Y=np.ones(1))}), t_end)
        ex = reservoir_shock_solution(ratio * 1e5, 300.0, 1e5, 300.0)
        m_model = rec.connection_mass["inlet"][1] / t_end
        w = duct.primitive(r["state"]["ducts"]["tube"])
        rho_ex = np.where(duct.centers < ex["x_contact_per_t"] * t_end, ex["rho_face"],
                          np.where(duct.centers < ex["x_shock_per_t"] * t_end, ex["rho_shocked"], ex["rho1"]))
        l1 = float(np.sum(np.abs(w["rho"] - rho_ex) * duct.dx) / np.sum(rho_ex * duct.dx))
        p_plateau = float(np.interp(0.5 * (ex["x_contact_per_t"] + ex["x_shock_per_t"]) * t_end, duct.centers, w["p"]))
        row = dict(p0_over_p1=ratio, mach_face_exact=ex["mach_face"], p_face_exact=ex["p_face"],
                   mdot_rel_error=m_model / (ex["mdot_per_area"] * A) - 1, density_L1_relative=l1,
                   plateau_pressure_rel_error=p_plateau / ex["p_face"] - 1, mass_closure=r["closure"]["mass"])
        rows.append(row)
        ok &= abs(row["mdot_rel_error"]) < 0.01 and l1 < 0.02 and abs(row["plateau_pressure_rel_error"]) < 0.01
    return _case("strong_unsteady_inflow_vs_shock_contact_solution", "boundary", ok, dict(rows=rows),
                 "face mass flow within 1 %, plateau pressure within 1 %, relative L1 density error < 2 % at t = 5 ms",
                 "exact solution: isentropic reservoir law + Rankine-Hugoniot shock + contact (p, u continuous); "
                 "NOT the diaphragm Riemann problem (a reservoir is not a quiescent tube: H is not conserved)")


def open_end_shock_reflection(ratios=(1.5, 2.0)):
    """Shock arriving at an ideal open end: exit state p = p_amb, isentropic rarefaction from the
    post-shock state (exact), compared with the exit mass flow during the plateau that follows."""
    mix = _air_cp()
    g = G_AIR
    rows, ok = [], True
    for ratio in ratios:
        L = 3.0
        duct = _pipe(mix, "tube", L, 0.05, 0.015)
        A = float(duct.area[0])
        res = Reservoir("hp", mix, ratio * 1e5, 300.0, np.ones(1), 0.0)
        amb = Reservoir("amb", mix, 1e5, 300.0, np.ones(1), 0.0)
        conns = [Connection.open_end("inlet", duct, "left", res), Connection.open_end("exit", duct, "right", amb)]
        eng = _bench(mix, {"tube": duct}, conns)
        ex = reservoir_shock_solution(ratio * 1e5, 300.0, 1e5, 300.0)
        t_arrive = L / ex["x_shock_per_t"]
        r, rec = _run_bench(eng, _inert_state(eng, mix, {"tube": dict(p=1e5, T=300.0, Y=np.ones(1))}), t_arrive + 0.0035)
        t = _time(eng, rec.trace)
        md = np.asarray(rec.trace["mdot_exit"])
        p2, u2, rho2 = ex["p_face"], ex["w_face"], ex["rho_shocked"]
        a2 = math.sqrt(g * p2 / rho2)
        u_exit = u2 + 2 * a2 / (g - 1) * (1 - (1e5 / p2) ** ((g - 1) / (2 * g)))
        rho_exit = rho2 * (1e5 / p2) ** (1 / g)
        m_exact = rho_exit * u_exit * A
        window = (t > t_arrive + 0.0006) & (t < t_arrive + 0.0030)
        m_model = float(md[window].mean())
        row = dict(p0_over_p1=ratio, exit_mach_exact=u_exit / math.sqrt(g * 1e5 / rho_exit), mdot_exact=m_exact,
                   mdot_model=m_model, mdot_rel_error=m_model / m_exact - 1, t_arrive_ms=1e3 * t_arrive)
        rows.append(row)
        ok &= abs(row["mdot_rel_error"]) < 0.01
    return _case("open_end_shock_reflection_vs_exact", "boundary", ok, dict(rows=rows),
                 "plateau exit mass flow within 1 % of the exact isentropic-release value",
                 "post-shock state from Rankine-Hugoniot + reservoir contact; open end p = p_amb, simple wave u_exit")


# --------------------------------------------------------------- engine level
def intake_ringing_vs_webster(rpm=6000.0):
    """Free ringing of the closed-valve intake runner after IVC vs a linear horn-equation eigenfrequency."""
    from scipy.linalg import eigh
    from scipy.optimize import curve_fit
    from .config import EXAMPLE_PATH, build, load
    from .runner import run_operating_point
    cfg = load(EXAMPLE_PATH)
    cfg["intake_duct"]["friction"] = True
    out = run_operating_point(cfg, overrides={"operating_point": {"rpm": rpm}, "numerics": {"dx_mm": 10.0}}, max_cycles=10)
    rec = out["records"][-1]
    eng, ctx = out["engine"], out["context"]
    th = np.asarray(rec.trace["theta"])
    p = np.asarray(rec.trace["p_intake_port"])
    ivc, ivo = cfg["intake_valve"]["lift"]["close_deg"], cfg["intake_valve"]["lift"]["open_deg"] - 360.0
    # valve closed between IVC (-130) and IVO (350 = -10 of the next cycle): runner is closed-open
    sel = (th > ivc + 15.0) & (th < ivo + 360.0 - 10.0)
    t = (th[sel] - th[sel][0]) / (6.0 * rpm)
    y = p[sel]
    a_mean = float(np.mean(np.asarray(rec.trace["a_mean_intake"])[sel]))
    # linear Webster horn equation for the actual geometry: closed at the valve, ideal open end
    duct = eng.ducts["intake"]
    n = 1200
    h = duct.length / n
    x_node = np.arange(n) * h
    # duct faces run ambient (x=0) -> valve (x=L); the eigenproblem coordinate runs valve -> ambient
    x_from_valve = duct.length - duct.faces[::-1]
    a_node = np.interp(x_node, x_from_valve, duct.area[::-1])
    a_half = np.interp(x_node + 0.5 * h, x_from_valve, duct.area[::-1])
    K = np.zeros((n, n))
    for i in range(n):
        K[i, i] = (a_half[i] + (a_half[i - 1] if i > 0 else 0.0)) / h
        if i + 1 < n:
            K[i, i + 1] = -a_half[i] / h
        if i > 0:
            K[i, i - 1] = -a_half[i - 1] / h
    weights = a_node * h
    weights[0] *= 0.5
    w2 = eigh(K, np.diag(weights), eigvals_only=True, subset_by_index=[0, 0])[0]
    f_lin = a_mean * math.sqrt(w2) / (2 * math.pi)

    def model(t, mean, amp, tau, f, ph):
        return mean + amp * np.exp(-t / tau) * np.cos(2 * np.pi * f * t + ph)

    best = None
    for seed in (0.8, 1.0, 1.2):
        try:
            popt, _ = curve_fit(model, t, y, p0=[y.mean(), 0.5 * np.ptp(y), 0.01, seed * f_lin, 0.0], maxfev=20000)
            res = float(np.sqrt(np.mean((model(t, *popt) - y) ** 2)))
            if best is None or res < best[1]:
                best = (popt, res)
        except RuntimeError:
            pass
    f_fit = float(abs(best[0][3])) if best else float("nan")
    rel = abs(f_fit - f_lin) / f_lin
    return _case("intake_runner_ringing_after_IVC_vs_webster_eigenfrequency", "engine", rel < 0.03,
                 dict(f_linear_Hz=f_lin, f_fit_Hz=f_fit, relative_error=rel, mean_sound_speed=a_mean,
                      window_ms=float(1e3 * (t[-1] - t[0])), periods_in_window=float((t[-1] - t[0]) * f_lin)),
                 "|f_fit - f_linear| / f_linear < 3 % (nonlinearity, damping, T-gradients allowed for)",
                 "Webster horn equation for the actual runner geometry, closed-open, solved independently (FD eigenproblem)")


def stage2_cases():
    cases = [open_end_steady_flow(), nozzle_area_mach(limiter="van_leer"), nozzle_area_mach(limiter="minmod"),
             order_profiles(), fanno_friction(), wall_heat_transfer(), helmholtz_resonator()]
    cases += vessel_discharge_and_charge()
    cases += [strong_unsteady_inflow_vs_shock_contact_solution(), open_end_shock_reflection(),
              intake_ringing_vs_webster()]
    return cases
