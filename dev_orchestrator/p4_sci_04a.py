"""P4-SCI-04A foundational benchmarks B1 + C1 isolated execution.

B1: linear acoustic outgoing pulse, characteristic + extended domain.
C1: instantaneous 0D/1D interface vs independent exact Riemann.

No G2, no E13-R1, no productive change.
"""
import json
import math
import time
from pathlib import Path
from bisect import bisect_right

from motorsim.gas1d.eos import IdealGas
from motorsim.gas1d.mesh import uniform_mesh
from motorsim.gas1d.second_order import reconstruct, cfl_step, event_step, inventories
from motorsim.gas1d.boundary import Boundary
from motorsim.coupling import ChamberState, interface_flux
from motorsim.gas1d.riemann import hllc_flux

# Use isolated exact Riemann (copy of reference, independent from productive HLLC)
try:
    from dev_orchestrator.reference.exact_riemann import ExactRiemann
except ImportError:
    from motorsim.gas1d.reference import ExactRiemann  # fallback

OUT = Path("results/p4-sci-04a-foundational-benchmarks-20260923")

EOS = IdealGas(R=287.0, gamma=1.35)
P0 = 100000.0
T0 = 300.0
RHO0 = P0 / (EOS.R * T0)
C0 = EOS.sound_speed((RHO0, 0.0, P0, 0.2))
Z0 = RHO0 * C0

# B1 pre-registered pulse
EPS = 100.0  # Pa, small acoustic amplitude
SIGMA = 0.02  # m, Gaussian width
X0 = 0.30  # m, pulse centre
L_TRUNC = 1.0  # m, truncated duct length
L_EXT = 2.0  # m, extended domain length (far wall beyond window)
DIAM_MM = 20.0
AREA = math.pi * (DIAM_MM * 0.001) ** 2 / 4
SENSOR = 0.80  # m, interior sensor near outlet (distance to outlet 0.20)
CFL = 0.4
N_LEVELS = [50, 100, 200]
T_FINAL = 0.004  # s, covers outgoing + truncated reflection, before extended return

# Characteristic definitions
CHARACTERISTIC_DOC = {
    "variables": "L_out = du + dp/Z0 , L_in = du - dp/Z0, with dp=p-p0, du=u-u0, Z0=rho0*c0",
    "outgoing": "L_out (right-going at right outlet)",
    "incoming": "L_in (left-going at right outlet, spurious reflection)",
    "impedance": Z0,
    "base_state": {"p0": P0, "T0": T0, "rho0": RHO0, "c0": C0, "gamma": EOS.gamma, "R": EOS.R, "Y0": 0.2},
    "ideal_pure_outgoing": "L_in ≈ 0, L_out = 2*dp/Z0 for pure right-going wave"
}


def primitive_pure_right(x):
    dp = EPS * math.exp(-((x - X0) / SIGMA) ** 2)
    # pure right-going: rho' = dp/c0^2, u' = dp/Z0
    rho = RHO0 + dp / (C0 ** 2)
    u = dp / Z0
    p = P0 + dp
    y = 0.2
    return (rho, u, p, y)


def build_initial(mesh, trunc=True):
    cells = []
    for xm, vol in zip(mesh.centers, mesh.volumes):
        if trunc:
            w = primitive_pure_right(xm)
        else:
            # extended: same pulse only within truncated region, base beyond
            if xm <= L_TRUNC:
                w = primitive_pure_right(xm)
            else:
                w = (RHO0, 0.0, P0, 0.2)
        cells.append(tuple(vol * q for q in EOS.conservative(w)))
    return cells


def solve_b1_with_sensor(mesh, initial, boundaries, cfl=CFL, t_final=T_FINAL, sensor=SENSOR):
    # Custom SSP-RK2 loop that records p,u at sensor each accepted step
    eos = EOS
    cells = [tuple(q) for q in initial]
    if len(cells) != mesh.n:
        raise ValueError("mesh/initial mismatch")
    def primitive(cells_):
        return [eos.primitive(tuple(x / v for x in row)) for row, v in zip(cells_, mesh.volumes)]
    states = primitive(cells)
    initial_inventory = inventories(cells)
    initial_abs = [math.fsum(abs(c[k]) for c in cells) for k in range(4)]
    a0 = eos.sound_speed(states[0])
    scales = [initial_inventory[0], initial_inventory[0] * a0, initial_inventory[2], initial_inventory[0]]
    boundary_int = [0.0] * 4
    boundary_abs = [0.0] * 4
    source_int = [0.0] * 4
    source_abs = [0.0] * 4
    import time as _time
    started = _time.monotonic()
    hllc_count = 0
    characteristic_count = 0
    fallbacks = {}
    downgrade_count = 0
    step = 0
    t = 0.0
    rejections = 0
    history = []
    sensor_history = []  # list of (t, p, u)
    minimum_dt = None
    maximum_dt = 0.0
    max_cfl = 0.0

    def extrema(ws):
        return [min(w[0] for w in ws), min(w[2] for w in ws),
                min(w[2] / (w[0] * eos.R) for w in ws), min(w[3] for w in ws),
                max(w[3] for w in ws), max(abs(w[1]) / eos.sound_speed(w) for w in ws)]
    cur_extrema = extrema(states)
    from motorsim.gas1d.second_order import minmod  # for reconstruction need but we reimplement operator below
    # we will reuse logic from second_order.solve but inline for sensor capture with both p,u

    def operator(ws, stage_idx):
        nonlocal hllc_count, characteristic_count, downgrade_count
        # reconstruct
        periodic = boundaries == 'periodic'
        length = mesh.faces[-1] - mesh.faces[0]
        lf, rf, down = reconstruct(mesh, ws, boundaries, eos)
        downgrade_count += len(down)
        data = []
        # interior interfaces
        for i in range(mesh.n - 1):
            item = hllc_flux(rf[i], lf[i + 1], eos)
            # count fallback/hllc? simplified count
            data.append(item)
            if item[2]:
                fallbacks[item[2]] = fallbacks.get(item[2], 0) + 1
            else:
                hllc_count += 1
        if periodic:
            # not used for B1
            shared = hllc_flux(rf[-1], lf[0], eos)
            if shared[2]:
                fallbacks[shared[2]] = fallbacks.get(shared[2], 0) + 1
            else:
                hllc_count += 1
            data = [shared, *data, shared]
        else:
            exterior = []
            for bc, w, normal, face in ((boundaries[0], lf[0], -1, 0), (boundaries[1], rf[-1], 1, mesh.n)):
                if bc.kind in ('wall', 'fixed', 'outflow'):
                    ghost = bc.face_state(w, normal, eos)
                    item = hllc_flux(ghost, w, eos) if normal == -1 else hllc_flux(w, ghost, eos)
                    if bc.kind == 'wall':
                        item = ((0.0, item[0][1], 0.0, 0.0), item[1], item[2])
                    if item[2]:
                        fallbacks[item[2]] = fallbacks.get(item[2], 0) + 1
                    else:
                        hllc_count += 1
                    # need to count correctly?already
                else:
                    item = bc.flux(w, normal, eos)
                    characteristic_count += 1
                exterior.append(item)
            data = [exterior[0], *data, exterior[1]]
        flux = [tuple(a * x for x in d[0]) for a, d in zip(mesh.areas, data)]
        speeds = [max(abs(d[1][0]), abs(d[1][2])) for d in data]
        limit, limiting, unit = cfl_step(mesh, ws, speeds, eos, cfl)
        source = [w[2] * (mesh.areas[i + 1] - mesh.areas[i]) for i, w in enumerate(ws)]
        rhs = [tuple(flux[i][k] - flux[i + 1][k] + (source[i] if k == 1 else 0.0) for k in range(4)) for i in range(mesh.n)]
        return rhs, flux, source, limit, limiting, unit, data

    def sensor_sample(ws, time_val):
        if sensor is not None:
            j = max(0, min(mesh.n - 2, bisect_right(mesh.centers, sensor) - 1))
            xl, xr = mesh.centers[j:j+2]
            # linear interpolation of primitive
            wj = ws[j]
            wj1 = ws[j+1]
            frac = (sensor - xl) / (xr - xl) if xr != xl else 0.0
            p = wj[2] + (wj1[2] - wj[2]) * frac
            u = wj[1] + (wj1[1] - wj[1]) * frac
            sensor_history.append((time_val, p, u))

    sensor_sample(states, t)
    status = 'completed'
    reason = 'final_time'
    while t < t_final:
        if _time.monotonic() - started > 120:
            status = 'failed_infrastructure'
            reason = 'wall_timeout'
            break
        rhs0, f0, s0, limit0, limiting0, unit0, data0 = operator(states, 0)
        dt = event_step(limit0, t_final - t)
        # SSPRK2 attempt loop (simplified: no retry halve except admissibility)
        accepted = False
        # need to handle admissibility retries halving dt similar to second_order
        for attempt in range(13):
            if dt < 1e-12 or t + dt == t:
                if t_final - t <= 16 * 2.220446049250313e-16 * max(1.0, abs(t_final)):
                    t = t_final
                    accepted = True
                    dt = 0.0
                    break
                raise RuntimeError('dt_below_min')
            try:
                stage1 = [tuple(v + dt * d for v, d in zip(q, rhs)) for q, rhs in zip(cells, rhs0)]
                w1 = primitive(stage1)
                rhs1, f1, s1, limit1, limiting1, unit1 = operator(w1, 1)[:6]
                if dt > limit1:
                    raise ValueError('stage_CFL_exceeded')
                stage2 = [tuple(v + dt * d for v, d in zip(q, rhs)) for q, rhs in zip(stage1, rhs1)]
                w2 = primitive(stage2)
                candidate = [tuple(0.5 * v + 0.5 * z for v, z in zip(q, r)) for q, r in zip(cells, stage2)]
                new_states = primitive(candidate)
                accepted = True
                break
            except Exception as exc:
                # check InvalidState etc.
                rejections += 1
                if attempt == 12:
                    status = 'failed_numerical'
                    reason = str(exc)
                    accepted = False
                    break
                dt /= 2
        if dt == 0:
            break
        if not accepted:
            if status == 'completed':
                status = 'failed_numerical'
                reason = 'step_rejected'
            break
        # commit step: ledger similar to second_order but simplified scales
        cells = candidate
        states = new_states
        t += dt
        step += 1
        minimum_dt = dt if minimum_dt is None else min(minimum_dt, dt)
        maximum_dt = max(maximum_dt, dt)
        max_cfl = max(max_cfl, dt / unit0, dt / unit1)
        # boundary/source integrals weighted 0.5 each stage
        for k in range(4):
            boundary_int[k] += 0.5 * dt * ((f0[-1][k] - f0[0][k]) + (f1[-1][k] - f1[0][k]))
        source_int[1] += 0.5 * dt * (math.fsum(s0) + math.fsum(s1))
        for k in range(4):
            boundary_abs[k] += 0.5 * dt * (abs(f0[-1][k]) + abs(f0[0][k]) + abs(f1[-1][k]) + abs(f1[0][k]))
        source_abs[1] += 0.5 * dt * (math.fsum(abs(s) for s in s0) + math.fsum(abs(s) for s in s1))
        # also record sensor after step
        sensor_sample(states, t)
        # ledger for conservation check simplified: not storing full history arrays but we compute residual later via inventories
        # we store minimal
        # update extrema
        cur_extrema = [min(a, b) if i < 4 else max(a, b) for i, (a, b) in enumerate(zip(cur_extrema, extrema(w1)))]
        cur_extrema = [min(a, b) if i < 4 else max(a, b) for i, (a, b) in enumerate(zip(cur_extrema, extrema(w2)))]
        cur_extrema = [min(a, b) if i < 4 else max(a, b) for i, (a, b) in enumerate(zip(cur_extrema, extrema(states)))]
        # store history dt etc for diagnosis maybe
        history.append({"time": t, "dt": dt, "max_CFL": max(dt / unit0, dt / unit1)})
        # no early break
    wall_seconds = _time.monotonic() - started
    final_inventory = inventories(cells)
    residual = [final_inventory[k] - initial_inventory[k] + boundary_int[k] - source_int[k] for k in range(4)]
    # normalized as in solver: max(initial_abs, boundary_abs, source_abs, scales)
    normalized = [abs(residual[k]) / max(initial_abs[k], boundary_abs[k], source_abs[k], scales[k]) for k in range(4)]
    max_res = max(normalized)
    return {
        "status": status,
        "reason": reason,
        "time": t,
        "steps": step,
        "wall_seconds": wall_seconds,
        "cells": cells,
        "primitive": states,
        "minimum_dt": minimum_dt,
        "maximum_dt": maximum_dt,
        "max_CFL": max_cfl,
        "rejected_steps": rejections,
        "initial_inventory": initial_inventory,
        "final_inventory": final_inventory,
        "boundary_flux_integral": boundary_int,
        "source_integral": source_int,
        "residual": residual,
        "normalized_residual": normalized,
        "max_normalized": max_res,
        "extrema": dict(zip(("min_rho", "min_p", "min_T", "min_Y", "max_Y", "max_Mach"), cur_extrema)),
        "sensor_history": sensor_history,
        "hllc_count": hllc_count,
        "characteristic_count": characteristic_count,
        "fallbacks": fallbacks,
        "history": history,
    }


def compute_characteristics(sensor_history):
    # returns list of (t, L_out, L_in, p, u, dp, du)
    out = []
    for t, p, u in sensor_history:
        dp = p - P0
        du = u  # u0=0
        L_out = du + dp / Z0
        L_in = du - dp / Z0
        out.append((t, L_out, L_in, p, u))
    return out


def analytic_signal(t):
    # pure right-going Gaussian traveling at c0 from X0
    pos = X0 + C0 * t
    dp = EPS * math.exp(-((SENSOR - pos) / SIGMA) ** 2)
    # for times before pulse reaches sensor, dp approx 0
    u = dp / Z0
    L_out = u + dp / Z0  # =2*dp/Z0
    L_in = 0.0
    p = P0 + dp
    return p, u, L_out, L_in


def truncated_vs_extended_metrics(trunc_hist, ext_hist):
    # trunc_hist and ext_hist are characteristic lists (t, Lout, Lin, p, u)
    # Need to interpolate ext onto trunc times for comparison within valid window
    # valid window: before extended far return
    t_out = (SENSOR - X0) / C0
    t_ref_trunc = ((L_TRUNC - X0) + (L_TRUNC - SENSOR)) / C0
    t_ref_ext = ((L_EXT - X0) + (L_EXT - SENSOR)) / C0
    # windows
    # outgoing window 3 sigma before/after t_out
    win_out = (t_out - 3 * SIGMA / C0, t_out + 3 * SIGMA / C0)
    win_refl = (t_ref_trunc - 3 * SIGMA / C0, t_ref_trunc + 3 * SIGMA / C0)
    # valid comparison window: from 0 to min(t_ref_ext - 3 sigma) to avoid extended return, also before t_ref_ext
    valid_end = t_ref_ext - 3 * SIGMA / C0 - 2 * (L_TRUNC / 100) / C0  # safety margin 2dx/c
    # compute metrics within windows
    def window_values(hist, window):
        return [(t, Lo, Li, p, u) for t, Lo, Li, p, u in hist if window[0] <= t <= window[1]]
    trunc_out_vals = window_values(trunc_hist, win_out)
    trunc_refl_vals = window_values(trunc_hist, win_refl)
    ext_refl_vals = window_values(ext_hist, win_refl)
    # amplitudes
    def max_abs(vals, idx):
        if not vals:
            return 0.0
        # idx 1=Lo,2=Li
        return max(abs(v[idx]) for v in vals)
    amp_out_trunc = max_abs(trunc_out_vals, 1) if trunc_out_vals else 0.0
    amp_in_trunc_out = max_abs(trunc_out_vals, 2)  # should be small
    amp_in_trunc_refl = max_abs(trunc_refl_vals, 2)
    amp_out_trunc_refl = max_abs(trunc_refl_vals, 1)
    amp_in_ext_refl = max_abs(ext_refl_vals, 2)
    # reflection ratios
    eps = 1e-12
    refl_ratio_trunc = amp_in_trunc_refl / max(amp_out_trunc, eps)
    refl_ratio_ext = amp_in_ext_refl / max(amp_out_trunc, eps)
    # pressure reflected amplitude (approx Z*Lin/2)
    p_refl_trunc = Z0 * amp_in_trunc_refl / 2
    p_refl_ext = Z0 * amp_in_ext_refl / 2
    # arrival time: first crossing of L_out > threshold? use p threshold 1 Pa interpolated
    def arrival_time(hist, threshold_p=1.0):
        # find first time where p exceeds P0+threshold
        for i in range(1, len(hist)):
            t0, _, _, p0_, _ = hist[i - 1]
            t1, _, _, p1_, _ = hist[i]
            if p0_ < P0 + threshold_p <= p1_:
                # linear interpolate
                frac = (P0 + threshold_p - p0_) / (p1_ - p0_) if p1_ != p0_ else 0
                return t0 + frac * (t1 - t0)
        return None
    arr_trunc = arrival_time(trunc_hist)
    arr_ext = arrival_time(ext_hist)
    # error vs analytic: compare trunc_hist during outgoing window to analytic
    # compute max error in that window
    err_Lout_analytic = 0.0
    err_Lin_analytic = 0.0
    err_p_analytic = 0.0
    for t, Lo, Li, p, u in trunc_out_vals:
        p_a, u_a, Lo_a, Li_a = analytic_signal(t)
        err_Lout_analytic = max(err_Lout_analytic, abs(Lo - Lo_a))
        err_Lin_analytic = max(err_Lin_analytic, abs(Li - Li_a))
        err_p_analytic = max(err_p_analytic, abs(p - p_a))
    # error vs extended: truncated vs extended during valid window before extended return
    # need interpolated ext signal onto trunc times within valid window [0, valid_end]
    # create ext interpolation dictionary via linear interp
    # build ext arrays for fast lookup: create list of (t, p, u, Lo, Li)
    # for each trunc time in valid window, interpolate ext
    err_vs_ext_p = 0.0
    err_vs_ext_Lin = 0.0
    err_vs_ext_Lout = 0.0
    # build ext lookup: assume monotonic t
    ext_times = [t for t, _, _, _, _ in ext_hist]
    ext_p = [p for _, _, _, p, _ in ext_hist]
    ext_Lo = [Lo for _, Lo, _, _, _ in ext_hist]
    ext_Li = [Li for _, _, Li, _, _ in ext_hist]
    def interp_ext(t_query):
        # linear interpolation
        if t_query <= ext_times[0]:
            return ext_p[0], ext_Lo[0], ext_Li[0]
        if t_query >= ext_times[-1]:
            return ext_p[-1], ext_Lo[-1], ext_Li[-1]
        import bisect
        idx = bisect.bisect_left(ext_times, t_query)
        t0 = ext_times[idx - 1]; t1 = ext_times[idx]
        frac = (t_query - t0) / (t1 - t0) if t1 != t0 else 0
        p0 = ext_p[idx - 1]; p1 = ext_p[idx]
        lo0 = ext_Lo[idx - 1]; lo1 = ext_Lo[idx]
        li0 = ext_Li[idx - 1]; li1 = ext_Li[idx]
        return p0 + frac * (p1 - p0), lo0 + frac * (lo1 - lo0), li0 + frac * (li1 - li0)
    trunc_valid = [(t, Lo, Li, p) for t, Lo, Li, p, _ in trunc_hist if 0 <= t <= valid_end]
    for t, Lo, Li, p, _ in trunc_hist:
        if not (0 <= t <= valid_end):
            continue
        p_e, Lo_e, Li_e = interp_ext(t)
        err_vs_ext_p = max(err_vs_ext_p, abs(p - p_e))
        err_vs_ext_Lout = max(err_vs_ext_Lout, abs(Lo - Lo_e))
        err_vs_ext_Lin = max(err_vs_ext_Lin, abs(Li - Li_e))
    return {
        "t_out": t_out,
        "t_ref_trunc": t_ref_trunc,
        "t_ref_ext": t_ref_ext,
        "valid_end": valid_end,
        "window_out": win_out,
        "window_refl": win_refl,
        "amp_out_trunc": amp_out_trunc,
        "amp_in_trunc_out": amp_in_trunc_out,
        "amp_in_trunc_refl": amp_in_trunc_refl,
        "amp_out_trunc_refl": amp_out_trunc_refl,
        "amp_in_ext_refl": amp_in_ext_refl,
        "reflection_ratio_trunc": refl_ratio_trunc,
        "reflection_ratio_ext": refl_ratio_ext,
        "p_reflected_trunc": p_refl_trunc,
        "p_reflected_ext": p_refl_ext,
        "arrival_trunc": arr_trunc,
        "arrival_ext": arr_ext,
        "err_Lout_analytic": err_Lout_analytic,
        "err_Lin_analytic": err_Lin_analytic,
        "err_p_analytic": err_p_analytic,
        "err_vs_ext_p": err_vs_ext_p,
        "err_vs_ext_Lout": err_vs_ext_Lout,
        "err_vs_ext_Lin": err_vs_ext_Lin,
        "valid_window_duration": valid_end,
    }


def run_b1():
    results = []
    start_all = time.perf_counter()
    for N in N_LEVELS:
        tic = time.perf_counter()
        mesh_trunc = uniform_mesh(N, length=L_TRUNC, area=AREA)
        # extended mesh with same dx
        N_ext = int(round(N * L_EXT / L_TRUNC))
        mesh_ext = uniform_mesh(N_ext, length=L_EXT, area=AREA)
        init_trunc = build_initial(mesh_trunc, trunc=True)
        init_ext = build_initial(mesh_ext, trunc=False)
        dx_trunc = mesh_trunc.widths[0] if mesh_trunc.n else 0
        dx_ext = mesh_ext.widths[0] if mesh_ext.n else 0
        # boundaries
        left = Boundary('wall')
        right_trunc = Boundary('nonreflecting', p0=P0, T0=T0, Y0=0.2)
        right_ext = Boundary('wall')
        res_trunc = solve_b1_with_sensor(mesh_trunc, init_trunc, (left, right_trunc))
        res_ext = solve_b1_with_sensor(mesh_ext, init_ext, (left, right_ext))
        # characteristic histories
        char_trunc = compute_characteristics(res_trunc["sensor_history"])
        char_ext = compute_characteristics(res_ext["sensor_history"])
        metrics = truncated_vs_extended_metrics(char_trunc, char_ext)
        toc = time.perf_counter()
        results.append({
            "N": N,
            "N_ext": N_ext,
            "dx_trunc": dx_trunc,
            "dx_ext": dx_ext,
            "CFL": CFL,
            "dt_min_trunc": res_trunc["minimum_dt"],
            "dt_max_trunc": res_trunc["maximum_dt"],
            "dt_min_ext": res_ext["minimum_dt"],
            "dt_max_ext": res_ext["maximum_dt"],
            "wall_seconds_trunc": res_trunc["wall_seconds"],
            "wall_seconds_ext": res_ext["wall_seconds"],
            "wall_seconds_total": toc - tic,
            "status_trunc": res_trunc["status"],
            "status_ext": res_ext["status"],
            "steps_trunc": res_trunc["steps"],
            "steps_ext": res_ext["steps"],
            "max_normalized_trunc": res_trunc["max_normalized"],
            "max_normalized_ext": res_ext["max_normalized"],
            "extrema_trunc": res_trunc["extrema"],
            "extrema_ext": res_ext["extrema"],
            "metrics": metrics,
            "sensor_count_trunc": len(char_trunc),
            "sensor_count_ext": len(char_ext),
        })
    total_wall = time.perf_counter() - start_all
    return results, total_wall


# C1 part

def c1_fixtures():
    # chamber defined via p,T,Y,V ; pipe via rho,u,p,Y
    # For interface_flux we need ChamberState and interior primitive
    # We define fixtures as dicts with description, normal, chamber, pipe
    eos = EOS
    fixtures = []
    # helper to create chamber from p,T,Y
    def cham(p,T,Y,V=0.0001):
        m=p*V/(eos.R*T)
        return {"p":p,"T":T,"Y":Y,"V":V, "m":m, "U":m*eos.cv*T, "fresh":Y*m}
    # F1 near equal
    fixtures.append({
        "id":"F1_NEAR_EQUAL",
        "description":"near-equal states small dp",
        "normal":-1,
        "chamber":cham(100000,300,0.3),
        "pipe":{"rho": 100050/(eos.R*300), "u":2.0, "p":100050, "Y":0.3}
    })
    # F2 shock dominated: high chamber to low pipe
    fixtures.append({
        "id":"F2_SHOCK_DOMINATED",
        "description":"shock-dominated high chamber pressure",
        "normal":-1,
        "chamber":cham(300000,600,0.8),
        "pipe":{"rho": P0/(EOS.R*T0), "u":0.0, "p":P0, "Y":0.2}
    })
    # F3 rarefaction dominated: low chamber
    fixtures.append({
        "id":"F3_RAREFACTION_DOMINATED",
        "description":"rarefaction-dominated low chamber",
        "normal":-1,
        "chamber":cham(80000,300,0.2),
        "pipe":{"rho": P0/(EOS.R*T0), "u":0.0, "p":P0, "Y":0.3}
    })
    # F4 left-to-right flow chamber high driving outward with pipe velocity outward
    fixtures.append({
        "id":"F4_LEFT_TO_RIGHT",
        "description":"left-to-right flow outward",
        "normal":-1,
        "chamber":cham(120000,350,0.5),
        "pipe":{"rho": P0/(EOS.R*T0), "u":30.0, "p":P0, "Y":0.2}
    })
    # F5 right-to-left backflow: pipe higher pressure + velocity toward chamber
    fixtures.append({
        "id":"F5_BACKFLOW",
        "description":"right-to-left backflow into chamber",
        "normal":-1,
        "chamber":cham(80000,300,0.3),
        "pipe":{"rho": 100000/(EOS.R*300), "u":-40.0, "p":100000, "Y":0.2}
    })
    # F6 subsonic inflow/outflow with moderate velocity both subsonic
    fixtures.append({
        "id":"F6_SUBSONIC_INOUT",
        "description":"subsonic inflow/outflow low Mach",
        "normal":-1,
        "chamber":cham(110000,320,0.4),
        "pipe":{"rho": 95000/(EOS.R*300), "u":-15.0, "p":95000, "Y":0.25}
    })
    # F7 typical cylinder->pipe P4 condition: high T, high p chamber typical of blowdown early
    fixtures.append({
        "id":"F7_TYPICAL_P4",
        "description":"typical cylinder->pipe P4 blowdown early",
        "normal":-1,
        "chamber":cham(250000,800,0.6),
        "pipe":{"rho": 100000/(EOS.R*500), "u":10.0, "p":100000, "Y":0.2}
    })
    # F8 normal +1 orientation test (chamber on right)
    fixtures.append({
        "id":"F8_NORMAL_PLUS1",
        "description":"normal +1 orientation cylinder on right",
        "normal":1,
        "chamber":cham(130000,400,0.7),
        "pipe":{"rho": P0/(EOS.R*T0), "u":-20.0, "p":P0, "Y":0.2}
    })
    # F9 Sod-like with gamma1.35 for reference sanity (shock tube)
    # Use classic Sod normalized: left p=100000, rho=1.0 right 0.125 etc but scaled
    # For coupling interface we'd need stagnant chamber equivalent; use left/right direct pair not via chamber for sanity?
    # We include as additional direct Riemann test not via interface_flux but direct hllc vs exact with both moving
    fixtures.append({
        "id":"F9_SOD",
        "description":"Sod shock tube normalized direct left/right",
        "normal":-1,
        "is_direct": True,
        "left":{"rho":1.0,"u":0.0,"p":100000,"Y":1.0},
        "right":{"rho":0.125,"u":0.0,"p":10000,"Y":0.0},
        "direct_left": (1.0,0.0,100000,1.0),
        "direct_right": (0.125,0.0,10000,0.0)
    })
    return fixtures


def compute_exact_for_fixture(fix):
    eos = EOS
    # For normal -1, left= chamber stagnant, right= pipe
    # For direct fixtures, use provided left/right
    if fix.get("is_direct"):
        left = fix["direct_left"]
        right = fix["direct_right"]
        ref = ExactRiemann(left, right, eos)
        # interface state at xi=0
        iface = ref.sample(0.0)
        flux = eos.flux(iface)
        return {
            "p_star": ref.pstar,
            "u_star": ref.ustar,
            "left": left,
            "right": right,
            "iface_state": iface,
            "flux": flux,
            "waves": ref.waves,
            "residual": ref.residual,
        }
    normal = fix["normal"]
    ch = fix["chamber"]
    pipe = fix["pipe"]
    # chamber primitive stagnant
    rho_c = ch["p"]/(eos.R*ch["T"])
    left_c = (rho_c, 0.0, ch["p"], ch["Y"])
    right_p = (pipe["rho"], pipe["u"], pipe["p"], pipe["Y"])
    if normal == -1:
        left, right = left_c, right_p
    else:
        left, right = right_p, left_c
    ref = ExactRiemann(left, right, eos)
    iface = ref.sample(0.0)
    flux = eos.flux(iface)
    # also compute left/right star states via sample slightly on each side? Use sample at ustar +/- small?
    # left star: sample at ustar - eps if available? Instead compute via sampling at xi = ustar - 1e-6*a ?
    # Simpler: sample at xi = ustar if needed: left star is sample at ustar? But we can derive left star density via isentropic relations already in sample? Instead we sample just left of ustar
    # For reporting, we can compute star states as iface if iface is star region, else need both.
    # To get left/right star, sample at xi = ustar -/+ small delta within star region.
    # Use 0.5 * (wave tail + ustar) etc but easier: if ref.waves shock, star = iface if iface donor matches side; if rarefaction, star still same but we may not have both.
    # We'll report iface_state as central star, and also left_star/right_star via sampling at slightly offset.
    # Use offset = 1.0 m/s small
    eps = 1.0
    try:
        left_star = ref.sample(ref.ustar - eps) if ref.ustar - eps > ref.waves[0][0] else ref.sample(ref.ustar)
    except:
        left_star = iface
    try:
        right_star = ref.sample(ref.ustar + eps) if ref.ustar + eps < ref.waves[1][1] else ref.sample(ref.ustar)
    except:
        right_star = iface
    return {
        "p_star": ref.pstar,
        "u_star": ref.ustar,
        "left": left,
        "right": right,
        "iface_state": iface,
        "flux": flux,
        "waves": ref.waves,
        "residual": ref.residual,
        "left_star": left_star,
        "right_star": right_star,
    }


def compute_productive_for_fixture(fix, area=0.000314):
    eos = EOS
    if fix.get("is_direct"):
        left = fix["direct_left"]
        right = fix["direct_right"]
        flux, speeds, reason = hllc_flux(left, right, eos)
        # flux already per unit area
        scaled = tuple(f for f in flux)
        # compute star pressure if available via reconstruct like in riemann.py
        # duplicate star computation similar to hllc_flux
        p_star_prod = None
        u_star_prod = None
        # try to compute sm as in hllc_flux
        try:
            sl, sr = speeds[0], speeds[2]
            rl, ul, pl, yl = left
            rr, ur, pr, yr = right
            denom = rl*(sl-ul)-rr*(sr-ur)
            if denom !=0:
                sm = (pr-pl+rl*ul*(sl-ul)-rr*ur*(sr-ur))/denom
                if sl< sm < sr:
                    u_star_prod = sm
                    # compute star pressure from left star formula if sm>=0 else right
                    # use similar to riemann: rs = r*(s-u)/(s-sm), ps = p + r*(s-u)*(sm-u)
                    if sm >=0:
                        r,u,p,y = left; s=sl
                    else:
                        r,u,p,y = right; s=sr
                    if s != sm and s != u:
                        ps = p + r*(s-u)*(sm-u)
                        p_star_prod = ps
        except Exception:
            pass
        return {
            "flux": flux,
            "speeds": speeds,
            "reason": reason,
            "p_star": p_star_prod,
            "u_star": u_star_prod,
            "mass_flux": flux[0],
            "energy_flux": flux[2],
            "species_flux": flux[3],
        }
    normal = fix["normal"]
    ch = fix["chamber"]
    pipe = fix["pipe"]
    eos = EOS
    # build ChamberState
    ch_state = ChamberState(mass=ch["m"], internal_energy=ch["U"], fresh_mass=ch["fresh"], volume=ch["V"])
    interior = (pipe["rho"], pipe["u"], pipe["p"], pipe["Y"])
    res = interface_flux(ch_state, interior, area, normal, eos=eos)
    # res.flux_x is area * hllc flux, outward = normal * flux_x
    # For comparison to exact flux_x (per area* flux), we need to compare flux_x
    # attempt to extract p_star productive similarly via hllc star logic but interface_flux doesn't expose it
    # we reconstruct via direct hllc_flux call with same left/right as interface_flux used internally
    rho_c = ch["p"]/(eos.R*ch["T"])
    left_c = (rho_c, 0.0, ch["p"], ch["Y"])
    right_p = interior
    if normal == -1:
        left, right = left_c, right_p
    else:
        left, right = right_p, left_c
    flux, speeds, reason = hllc_flux(left, right, eos)
    p_star_prod = None
    u_star_prod = None
    try:
        sl, sr = speeds[0], speeds[2]
        # speeds tuple is (SL,SM,SR) where SM may be None if fallback
        sm = speeds[1]
        if sm is not None and sl < sm < sr:
            u_star_prod = sm
            if sm >=0:
                r,u,p,y = left; s=sl
            else:
                r,u,p,y = right; s=sr
            if s != sm and s != u:
                p_star_prod = p + r*(s-u)*(sm-u)
    except Exception:
        pass
    return {
        "flux_x": res.flux_x,
        "outward": res.outward,
        "speeds": res.wave_speeds,
        "reason": res.fallback_reason,
        "mass_flux": res.outward[0],
        "momentum_flux": res.outward[1],
        "energy_flux": res.outward[2],
        "species_flux": res.outward[3],
        "donor": res.outward, # not needed
        "p_star": p_star_prod,
        "u_star": u_star_prod,
        "left": left,
        "right": right,
        "hllc_flux": flux,
    }


def c1_errors(fix, exact, prod):
    # compute errors normalized; for direct fixtures flux per area comparison
    eps = 1e-12
    # flux normalization: use max(|exact_flux|, scale)
    # exact flux per unit area is exact["flux"]; prod flux per unit area is prod["hllc_flux"] or flux_x/area
    if fix.get("is_direct"):
        exact_flux = exact["flux"]
        prod_flux = prod["flux"]
        # per component errors
        errs = {}
        for i, name in enumerate(["mass","mom","energy","species"]):
            ef = exact_flux[i]
            pf = prod_flux[i]
            # normalized error
            denom = max(abs(ef), 1.0, abs(pf))  # avoid tiny denominator
            # for mass/energy use relative where meaningful
            if abs(ef) < 1e-12 and abs(pf) < 1e-12:
                errs[name] = 0.0
            else:
                errs[name] = abs(pf - ef) / max(abs(ef), 1e-12, 1.0)
        # p_star error
        p_star_err = abs(prod["p_star"] - exact["p_star"])/ max(abs(exact["p_star"]), 1.0) if prod["p_star"] is not None else None
        u_star_err = abs(prod["u_star"] - exact["u_star"])/ max(abs(exact["u_star"])+1.0, 1.0) if prod["u_star"] is not None else None
        # flow direction check: sign of u_star vs sign of mass flux
        exact_dir = "none" if abs(exact["u_star"]) < 1e-12 else ("positive" if exact["u_star"]>0 else "negative")
        prod_dir = "none" if prod["u_star"] is None or abs(prod["u_star"])<1e-12 else ("positive" if prod["u_star"]>0 else "negative")
        correct_dir = exact_dir == prod_dir
        # wave ordering check already via fallback? if reason is None then ordering ok else fallback
        ordering_ok = prod["reason"] is None
        # admissibility etc
        admiss = True
        return {
            "mass_flux_error": errs["mass"],
            "momentum_error": errs["mom"],
            "energy_flux_error": errs["energy"],
            "species_flux_error": errs["species"],
            "p_star_error": p_star_err,
            "u_star_error": u_star_err,
            "correct_direction": correct_dir,
            "exact_dir": exact_dir,
            "prod_dir": prod_dir,
            "ordering_ok": ordering_ok,
            "fallback_reason": prod["reason"],
        }
    else:
        # coupling case: compare outward fluxes scaled by area
        area = 0.000314
        exact_flux_per_area = exact["flux"]
        exact_outward = tuple(fix["normal"] * area * f for f in exact_flux_per_area)
        prod_outward = prod["outward"]
        errs = {}
        for i, name in enumerate(["mass","mom","energy","species"]):
            ef = exact_outward[i]
            pf = prod_outward[i]
            # normalization
            if abs(ef) < 1e-12 and abs(pf) < 1e-12:
                errs[name] = 0.0
            else:
                # relative error normalized by max(|ef|, scale)
                # use mass scale: area * something? choose max
                denom = max(abs(ef), abs(pf), 1e-6)
                errs[name] = abs(pf - ef) / max(abs(ef), 1e-12, 1.0) if abs(ef) > 1e-12 else abs(pf-ef)/max(1.0, abs(pf))
        p_star_err = abs(prod["p_star"] - exact["p_star"])/max(abs(exact["p_star"]), 1.0) if prod["p_star"] is not None else None
        u_star_err = abs(prod["u_star"] - exact["u_star"])/max(abs(exact["u_star"])+10.0, 1.0) if prod["u_star"] is not None else None
        # direction: sign of mass flux outward indicates flow out of pipe (positive outward = leaving pipe)
        # exact mass outward sign = sign(exact_outward[0])
        exact_dir = "outward" if exact_outward[0] > 1e-12 else ("inward" if exact_outward[0] < -1e-12 else "none")
        prod_dir = "outward" if prod_outward[0] > 1e-12 else ("inward" if prod_outward[0] < -1e-12 else "none")
        correct_dir = exact_dir == prod_dir
        ordering_ok = prod["reason"] is None
        # species transport consistency: species flux should be mass_flux * donor Y
        # check prod species vs donor expectation
        # donor Y determined by exact u_star sign?
        # For this check, compute donor Y exact: if exact u_star >=0 then left Y else right Y
        left = exact["left"]; right = exact["right"]
        donor_Y_exact = left[3] if exact["u_star"] >=0 else right[3]
        # product donor: if prod u_star >=0 left Y else right Y, but if fallback maybe different
        # compute expected species flux = mass_flux * donor_Y
        expected_species_exact = exact_outward[0] * donor_Y_exact
        species_consistent_exact = abs(exact_outward[3] - expected_species_exact) < 1e-9
        # for prod
        if prod["u_star"] is not None:
            donor_Y_prod = left[3] if prod["u_star"] >=0 else right[3]
        else:
            donor_Y_prod = None
        expected_species_prod = prod_outward[0] * donor_Y_prod if donor_Y_prod is not None else None
        species_consistent_prod = abs(prod_outward[3] - expected_species_prod) < 1e-9 if expected_species_prod is not None else False
        return {
            "mass_flux_error": errs["mass"],
            "momentum_error": errs["mom"],
            "energy_flux_error": errs["energy"],
            "species_flux_error": errs["species"],
            "p_star_error": p_star_err,
            "u_star_error": u_star_err,
            "correct_direction": correct_dir,
            "exact_dir": exact_dir,
            "prod_dir": prod_dir,
            "ordering_ok": ordering_ok,
            "fallback_reason": prod["reason"],
            "species_consistent_exact": species_consistent_exact,
            "species_consistent_prod": species_consistent_prod,
        }

