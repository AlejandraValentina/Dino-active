"""Per-cycle engine indicators and cycle-to-cycle periodicity assessment.

Definitions follow Heywood (1988) ch. 2 unless stated:
  IMEP_net   = (closed integral of p dV over 720 deg) / Vd
  IMEP_gross = work over compression + expansion strokes / Vd
  PMEP       = -(work over exhaust + intake strokes) / Vd   (positive = loss)
  eta_v      = net air mass through the intake valve / (rho_air,inlet Vd), eq. 2.27
  eta_f,i    = W_net / (m_fuel Q_LHV)  (LHV derived from the species data)
  residual   = burned-gas tracer mass fraction at IVC
Periodicity is a numerical property of the solution.  It says nothing
about validity against experiments.
"""
from __future__ import annotations

import math

import numpy as np

from .combustion import lower_heating_value
from .thermo import dry_air


def _air_density(mix, p, T):
    return p / (float(mix.gas_constant(dry_air(mix))) * T)


def temperature_from_enthalpy(mix, Y, h, guess=1000.0):
    T = guess
    for _ in range(50):
        f = float(mix.enthalpy(Y, T)) - h
        step = f / float(mix.cp(Y, T))
        T -= step
        if abs(step) < 1e-10 * T:
            break
    return T


def cycle_indicators(record, context) -> dict:
    mix, geo, cfg = context["mixture"], context["geometry"], context["config"]
    fuel = context["fuel"]
    ns = mix.ns
    ifuel = mix.index(fuel)
    rpm = cfg["operating_point"]["rpm"]
    vd = geo.displacement
    cycles_per_s = rpm / 120.0
    omega = 2 * math.pi * rpm / 60.0
    amb = cfg["ambient"]
    rho_air = _air_density(mix, amb["intake_pressure_pa"], amb["intake_temperature_K"])
    charge = np.asarray(context["charge"])
    air_fraction_charge = 1.0 - charge[ifuel]
    lhv = lower_heating_value(mix, fuel)

    w = record.work_by_stroke
    work_net = record.work_net
    work_gross = w["compression"] + w["expansion"]
    work_pump = w["intake"] + w["exhaust"]
    sp = geo.mean_piston_speed(rpm)
    fmep = context["friction"].fmep(record.p_max, sp)

    species = {k: np.asarray(v) for k, v in record.connection_species.items()}
    iv, ev = species["intake_valve"], species["exhaust_valve"]
    amb_in, amb_out = -species["intake_open_end"], -species["exhaust_open_end"]  # into the system
    intake_mass = iv[:ns].sum()
    intake_fresh = intake_mass - iv[ns]
    exhaust_out_mass = -ev[:ns].sum()
    exhaust_out_fresh = -(ev[:ns].sum() - ev[ns])
    air_iv = intake_fresh * air_fraction_charge
    fuel_system = amb_in[ifuel] + amb_out[ifuel]  # net fuel entering the whole system
    fuel_iv = iv[ifuel]
    system_in = amb_in[:ns].sum()
    system_out = -amb_out[:ns].sum()

    imep = work_net / vd
    p_ind = work_net * cycles_per_s
    bmep = imep - fmep
    p_brake = bmep * vd * cycles_per_s

    def sfc(fuel_mass, power):
        return fuel_mass * cycles_per_s / power * 3.6e9 if power > 0 else None

    ivc = record.snapshots.get("IVC", {})
    trapped = ivc.get("mass")
    residual = ivc.get("xb")
    trapped_fresh = trapped * (1 - residual) if trapped is not None else None
    exh_h = ev[ns + 1] / ev[:ns].sum() if abs(ev[:ns].sum()) > 0 else float("nan")
    exh_Y = ev[:ns] / ev[:ns].sum() if abs(ev[:ns].sum()) > 0 else charge
    t_exh = temperature_from_enthalpy(mix, exh_Y, exh_h) if math.isfinite(exh_h) else float("nan")
    fuel_energy = fuel_iv * lhv
    burn = np.asarray(record.trace.get("burn", [])) if record.trace.get("burn") else None
    theta = np.asarray(record.trace.get("theta", [])) if record.trace.get("theta") else None
    ca = {}
    if burn is not None and burn.size and burn[-1] > 0.5:
        x = burn / burn[-1]
        for level in (0.1, 0.5, 0.9):
            j = int(np.searchsorted(x, level))
            j = min(max(j, 1), x.size - 1)
            ca[f"CA{int(level * 100)}_deg"] = float(np.interp(level, x[j - 1:j + 1], theta[j - 1:j + 1]))

    out = {
        "work_net_J": work_net, "work_gross_J": work_gross, "work_pumping_J": work_pump,
        "imep_net_bar": imep / 1e5, "imep_gross_bar": work_gross / vd / 1e5, "pmep_bar": -work_pump / vd / 1e5,
        "fmep_bar": fmep / 1e5, "bmep_bar": bmep / 1e5,
        "indicated_power_kW": p_ind / 1e3, "indicated_torque_Nm": p_ind / omega,
        "brake_power_kW": p_brake / 1e3, "brake_torque_Nm": p_brake / omega,
        "mechanical_efficiency": bmep * vd / work_gross if work_gross > 0 else None,
        "volumetric_efficiency_intake_valve": air_iv / (rho_air * vd),
        "volumetric_efficiency_system_inlet": amb_in[:ns].sum() * air_fraction_charge / (rho_air * vd),
        "air_per_cycle_mg": air_iv * 1e6, "fuel_per_cycle_mg": fuel_iv * 1e6,
        "fuel_burned_per_cycle_mg": record.fuel_burned * 1e6,
        "trapped_mass_mg": trapped * 1e6 if trapped is not None else None,
        "residual_gas_fraction_ivc": residual,
        "trapping_efficiency": trapped_fresh / intake_fresh if trapped_fresh is not None and intake_fresh > 0 else None,
        "fresh_short_circuit_fraction": exhaust_out_fresh / intake_fresh if intake_fresh > 0 else None,
        "intake_backflow_mg": record.connection_mass["intake_valve"][1] * 1e6,
        "exhaust_backflow_mg": record.connection_mass["exhaust_valve"][0] * 1e6,
        "indicated_fuel_conversion_efficiency": work_net / fuel_energy if fuel_energy > 0 else None,
        "brake_fuel_conversion_efficiency": bmep * vd / fuel_energy if fuel_energy > 0 else None,
        "isfc_g_kWh": sfc(fuel_iv, p_ind), "bsfc_g_kWh": sfc(fuel_iv, p_brake),
        "heat_loss_J": record.heat_loss, "heat_loss_fraction_of_fuel_energy": record.heat_loss / fuel_energy if fuel_energy > 0 else None,
        "p_max_bar": record.p_max / 1e5, "theta_p_max_deg": record.theta_p_max, "T_max_K": record.T_max,
        "exhaust_valve_mean_enthalpy_temperature_K": t_exh,
        "lower_heating_value_MJ_kg": lhv / 1e6,
        "mass_balance": {
            "system_inlet_mg": system_in * 1e6, "system_outlet_mg": system_out * 1e6,
            "intake_valve_net_mg": intake_mass * 1e6, "exhaust_valve_net_mg": exhaust_out_mass * 1e6,
            "system_relative_imbalance": (system_in - system_out) / max(system_in, 1e-30),
            "fuel_system_net_mg": fuel_system * 1e6,
        },
        "thermo_fit_range_exceeded": record.T_max > mix.t_fit[1],
        "steps": record.steps, "rejected_steps": record.rejected_steps,
    }
    out.update(ca)
    return out


DEFAULT_TOLERANCES = {"imep_rel": 0.002, "trapped_mass_rel": 0.002, "pressure_trace_rel": 0.005,
                      "mass_imbalance_rel": 0.005, "consecutive": 2}


def periodicity_metrics(previous: dict, current: dict, prev_record, record) -> dict:
    p0 = np.asarray(prev_record.trace["pressure_grid"])
    p1 = np.asarray(record.trace["pressure_grid"])

    def rel(a, b):
        return abs(a - b) / max(abs(a), abs(b), 1e-30)

    return {
        "imep_rel": rel(previous["imep_net_bar"], current["imep_net_bar"]),
        "trapped_mass_rel": rel(previous["trapped_mass_mg"] or 0.0, current["trapped_mass_mg"] or 0.0),
        "pressure_trace_rel": float(np.max(np.abs(p1 - p0)) / max(p1.max(), 1e-30)),
        "mass_imbalance_rel": abs(current["mass_balance"]["system_relative_imbalance"]),
    }


class PeriodicityMonitor:
    """Callable used as ``convergence`` hook; keeps the metric history."""

    def __init__(self, context, tolerances=None, min_cycles=3):
        self.context = context
        self.tol = dict(DEFAULT_TOLERANCES, **(tolerances or {}))
        self.min_cycles = min_cycles
        self.indicators, self.metrics, self.streak = [], [], 0

    def __call__(self, records):
        rec = records[-1]
        self.indicators.append(cycle_indicators(rec, self.context))
        if len(records) < 2:
            self.metrics.append(None)
            return False
        m = periodicity_metrics(self.indicators[-2], self.indicators[-1], records[-2], rec)
        ok = all(m[k] <= self.tol[k] for k in m)
        m["passed"] = ok
        self.metrics.append(m)
        self.streak = self.streak + 1 if ok else 0
        return len(records) >= self.min_cycles and self.streak >= self.tol["consecutive"]

    @property
    def status(self):
        return "PERIODIC_CONVERGED" if self.streak >= self.tol["consecutive"] else "NOT_CONVERGED"
