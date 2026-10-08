"""P8 bounded transient driver with two fixed preparation cycles."""
from dataclasses import dataclass, replace
from copy import deepcopy
from hashlib import sha256
from math import pi, isfinite, floor
import csv, gzip, json
from pathlib import Path

from .project import ProjectError
from .gas1d.solver import cfl_step, event_step
from .p7_prescribed import Q_F

RPM_MIN, RPM_MAX = 2500, 15000
P8_ANCHORS = (2500, 5000, 8000, 11000, 15000)
P8_CFL = .4
PREPARATION_CYCLES = 2
PREPARATION_START_DEG = 180.0
PREPARATION_END_DEG = PREPARATION_START_DEG + 360.0 * PREPARATION_CYCLES
MEASURED_START_DEG = 180.0
MEASURED_END_DEG = 540.0
P7_START_DEG = 350.0
P7_END_DEG = 390.0
RESTART_PROBE_DEG = 370.0

def validate_p8_rpm(rpm):
    if type(rpm) is not int or not RPM_MIN <= rpm <= RPM_MAX:
        raise ProjectError(f"P8 RPM must be an integer in [{RPM_MIN}, {RPM_MAX}]")
    return rpm

def omega_deg_s(rpm): return 6.0 * validate_p8_rpm(rpm)
def cycle_duration_s(rpm): return 60.0 / validate_p8_rpm(rpm)

def indicated_metrics(work_j, rpm, pmax_pa):
    validate_p8_rpm(rpm)
    if not all(isfinite(float(x)) for x in (work_j, pmax_pa)):
        raise ValueError("P8 metrics must be finite")
    return {"W_cycle_J": float(work_j), "P_indicated_W": float(work_j) * rpm / 60.0,
            "T_indicated_Nm": float(work_j) / (2*pi), "p_max_Pa": float(pmax_pa)}

def work_from_pressure_volume(p, v):
    if len(p) != len(v) or len(p) < 2:
        raise ValueError("pressure and volume paths must have equal length >= 2")
    return sum(.5*(a+b)*(d-c) for a,b,c,d in zip(p, p[1:], v, v[1:]))

@dataclass(frozen=True)
class P8Semantics:
    contract_version: str = "P8-WIDE-RPM-TRANSIENT-V9-PREP-TWO-CYCLES"
    steady_state: bool = False
    periodic_convergence: str = "NOT_GRANTED_BY_P4"
    metric_semantics: str = "BOUNDED_TRANSIENT_INDICATED"
    conditional_on_p4: bool = True
    experimental_validation: str = "NOT_PERFORMED"
    independent_review: str = "INDEPENDENT_REVIEW_PENDING"

def model_geometry_callback(model):
    def callback(angle):
        volumes, rates, areas = model.geometry(float(angle))
        return {"volumes": volumes, "volume_rates": (rates[1], rates[2]),
                "areas": (areas[1], areas[2], areas[3], areas[4])}
    return callback

def build_event_cuts(case, start, end, *, p7_enabled=False, restart_probe=False):
    """Build absolute cuts from the authoritative event phases.

    ``Model.events`` contains one 360-degree phase.  P8 integrates absolute
    angles, so every phase is repeated over all turns intersecting the
    interval.  The measured path additionally cuts at the P7 interval.
    """
    from .simulation import Model
    phases = tuple(float(x) for x in Model(case).events)
    if p7_enabled:
        phases += (P7_START_DEG, P7_END_DEG)
    cuts = set()
    for k in range(int(floor(start/360.0))-1, int(floor(end/360.0))+2):
        for phase in phases:
            x = phase + 360.0*k
            if start < x <= end:
                cuts.add(x)
    if restart_probe:
        cuts.add(RESTART_PROBE_DEG)
    cuts.add(float(end))
    return tuple(sorted(cuts))


def event_cuts(case, start, end, *, p7_enabled=True, restart_probe=False):
    """Compatibility wrapper for callers of the original P8 helper."""
    return build_event_cuts(case, start, end, p7_enabled=p7_enabled,
                            restart_probe=restart_probe)

def _new_system(rpm, *, enable_p7=False):
    from .simulation_case import SyntheticCase
    from .simulation import Model
    from .p5c import make_p5c_full_fixture
    from .p6_species import P6IntegratedSystem, legacy_to_species
    from .gas1d.eos import IdealGas
    case = replace(SyntheticCase(), rpm=rpm)
    model = Model(case, external_band_pa=100)
    gas = make_p5c_full_fixture(eos=IdealGas(R=287, gamma=1.35), cells=2)
    gas.geometry_callback = model_geometry_callback(model)
    gas.core.geometry_callback = gas.geometry_callback
    gas.angle = case.initial_angle_deg
    volumes = model.geometry(180)[0]
    for chamber, pty, volume in ((gas.core.crankcase, case.initial_pty[1], volumes[1]),
                                 (gas.core.cylinder, case.initial_pty[2], volumes[2])):
        p, t, marker = pty
        chamber.volume = volume
        chamber.primitive = (p/(gas.eos.R*t), 0.0, p, float(marker))
    gas.core._initial = gas.core._totals()
    gas._initial = gas.totals()
    gas._previous_totals = dict(gas._initial)
    def mapped(mass, marker):
        values = legacy_to_species(mass, float(marker))
        return tuple(x/mass for x in values)
    species = {
        "crankcase": [mapped(gas.core.crankcase.inventory(gas.eos)[0], 1)],
        "cylinder": [mapped(gas.core.cylinder.inventory(gas.eos)[0], 0)],
    }
    for name, path in (("intake", gas.core.intake), ("tr1", gas.core.transfers[0]),
                       ("tr2", gas.core.transfers[1]), ("exhaust", gas.exhaust)):
        species[name] = [mapped(q[0]*v, q[3]/q[0])
                         for q, v in zip(path.conservative(), path.mesh.volumes)]
    return case, P6IntegratedSystem(gas, component_species=species, capture_trace=True,
                                    enable_p7=enable_p7, angular_rate_deg_s=omega_deg_s(rpm))

def _cfl_dt(gas):
    limits = []
    for path in (gas.core.intake, *gas.core.transfers, gas.exhaust):
        states = [gas.eos.primitive(q) for q in path.conservative()]
        speeds = [abs(w[1]) + gas.eos.sound_speed(w) for w in states]
        speeds = [speeds[0], *[max(a,b) for a,b in zip(speeds, speeds[1:])], speeds[-1]]
        dt, _, unit = cfl_step(path.mesh, states, speeds, gas.eos, P8_CFL)
        limits.append((dt, unit))
    return min(limits)

def _step_dt(gas, rpm, end, cuts):
    cfl_dt, _ = _cfl_dt(gas)
    remaining = (end-gas.angle) / omega_deg_s(rpm)
    dt = event_step(cfl_dt, remaining)
    nxt = next((x for x in cuts if x > gas.angle + 1e-12), end)
    return min(dt, (nxt-gas.angle) / omega_deg_s(rpm)), cfl_dt

def _advance(system, case, rpm, start, end, *, record_cfl=False):
    dts, cfls = [], []
    cuts = build_event_cuts(case, start, end, p7_enabled=system.p7_enabled)
    while system.gas.angle < end - 1e-12:
        dt, cfl_dt = _step_dt(system.gas, rpm, end, cuts)
        system.step(dt, angle=system.gas.angle + dt*omega_deg_s(rpm))
        dts.append(dt)
        cfls.append(dt/(cfl_dt/P8_CFL))
    return dts, cfls

def _reset_measurement(system, *, case):
    gas = system.gas
    source = gas.geometry_callback(PREPARATION_END_DEG)
    target = gas.geometry_callback(MEASURED_START_DEG)
    if source != target:
        raise RuntimeError("900-to-180 geometry rebase is not equivalent")
    physical_before = (gas._state(), system.species_mass)
    gas.angle = MEASURED_START_DEG
    gas.core.angle = MEASURED_START_DEG
    if (gas._state(), system.species_mass) != physical_before:
        raise RuntimeError("geometry rebase changed physical gas/species state")

    gas.history = []
    gas.ledger = {k: 0.0 for k in gas.ledger}
    gas._last_external = {"mass": 0.0, "energy": 0.0, "species": 0.0}
    gas._external_cumulative = {"mass": 0.0, "energy": 0.0, "species": 0.0}
    gas._initial = gas.totals(); gas._previous_totals = dict(gas._initial)
    core = gas.core
    core.history = []
    core.ledger = {k: 0.0 for k in core.ledger}
    if hasattr(core, "_applied"):
        core._applied = {k: 0.0 for k in core._applied}
    if hasattr(core, "_applied_deltas"):
        core._applied_deltas = {k: 0.0 for k in core._applied_deltas}
    if hasattr(core, "_accepted_updates"):
        core._accepted_updates = 0
    core._initial = core._totals()
    if hasattr(gas, "_previous_totals"):
        gas._previous_totals = dict(gas._initial)
    system._initial = system._species_totals()
    system._external = [0.0] * 4
    system.fresh_delivered = system.fresh_delivered_tr1 = system.fresh_delivered_tr2 = 0.0
    system.fresh_short_circuit = 0.0
    system.verification_trace = []; system.external_flux_trace = []
    system.p7_event = None; system.p7_events = []; system.p7_source_delta = [0.0] * 4
    system._count_transport = True
    system._stage_active = False
    system.p7_enabled = True
    return {
        "source_angle_deg": PREPARATION_END_DEG,
        "target_angle_deg": MEASURED_START_DEG,
        "volumes_equal": source["volumes"] == target["volumes"],
        "volume_rates_equal": source["volume_rates"] == target["volume_rates"],
        "areas_equal": source["areas"] == target["areas"],
    }

def _current(system):
    events = tuple((event.start, event.fresh_air, event.fuel,
                    vars(event.ledger).copy()) for event in system.p7_events)
    gas = system.gas
    return {
        "angle": gas.angle,
        "elapsed_time_s": system.p8_elapsed_time_s,
        "cycle_index": 1,
        "conservative_state": gas._state(),
        "species_mass": system.species_mass,
        "species_external": system._external,
        "species_initial": system._initial,
        "gas_initial": gas._initial,
        "gas_previous_totals": gas._previous_totals,
        "gas_external_cumulative": gas._external_cumulative,
        "gas_ledger": gas.ledger,
        "p7_events": events,
        "p7_source_delta": system.p7_source_delta,
        "p7_enabled": system.p7_enabled,
        "p7_angular_rate_deg_s": system.p7_angular_rate_deg_s,
        "fresh_delivered": system.fresh_delivered,
        "fresh_delivered_tr1": system.fresh_delivered_tr1,
        "fresh_delivered_tr2": system.fresh_delivered_tr2,
        "fresh_short_circuit": system.fresh_short_circuit,
        "p8_boundary_species_trace": system.p8_boundary_species_trace,
    }


def _accepted_trajectory_state(system, *, step_index, dt, achieved_cfl):
    """Snapshot the fully accepted coupled state after one SSPRK2 step.

    The gas history keeps the SSPRK2 ``q_n`` candidate, while ``system.step``
    returns after installing it into chambers and completing P6/P7 updates.
    This captures the exact post-install state used by the next step, including
    its species state and cumulative ledgers.
    """
    state = _current(system)
    return {
        "step_index": step_index,
        "dt": dt,
        "achieved_cfl": achieved_cfl,
        "angle": state["angle"],
        "elapsed_time_s": state["elapsed_time_s"],
        "cycle_index": state["cycle_index"],
        "conservative_state": deepcopy(state["conservative_state"]),
        "species_masses": deepcopy(system.species_mass),
        "species_initial": deepcopy(state["species_initial"]),
        "species_external": deepcopy(state["species_external"]),
        "gas_external_cumulative": deepcopy(state["gas_external_cumulative"]),
        "gas_last_external": deepcopy(system.gas._last_external),
        "gas_ledger": deepcopy(state["gas_ledger"]),
        "gas_initial": deepcopy(state["gas_initial"]),
        "gas_previous_totals": deepcopy(state["gas_previous_totals"]),
        "fresh_delivered": state["fresh_delivered"],
        "fresh_delivered_tr1": state["fresh_delivered_tr1"],
        "fresh_delivered_tr2": state["fresh_delivered_tr2"],
        "fresh_short_circuit": state["fresh_short_circuit"],
        "p7_events": deepcopy([{"start": event.start, "fresh_air": event.fresh_air,
                                 "fuel": event.fuel, "ledger": vars(event.ledger).copy()}
                                for event in system.p7_events]),
        "p7_source_delta": deepcopy(state["p7_source_delta"]),
        "p7_enabled": state["p7_enabled"],
        "p7_angular_rate_deg_s": state["p7_angular_rate_deg_s"],
    }


def _capture_boundary_species(system, prefix=()):
    """Record the exact species deltas accepted at both external boundaries.

    This wraps only the P8 instance method and observes before/after inventories;
    it does not alter fluxes, donor selection, or state updates.
    """
    system.p8_boundary_species_trace = list(prefix)
    original = system._boundary_exchange

    def capture(mass_flux, component, dt, *, incoming):
        index = 0 if incoming else -1
        before = tuple(system.species_mass[component][index])
        original(mass_flux, component, dt, incoming=incoming)
        after = tuple(system.species_mass[component][index])
        # The coupled gas solver has appended this accepted step before P6
        # applies its two-stage species boundary exchanges (one-based index).
        step_index = len(system.gas.history)
        calls = [row for row in system.p8_boundary_species_trace
                 if row["step_index"] == step_index]
        stage_index = len(calls) // 2
        system.p8_boundary_species_trace.append({
            "step_index": step_index,
            "stage_index": stage_index,
            "boundary_index": len(calls) % 2,
            "component": component,
            "incoming": bool(incoming),
            "mass_flux": float(mass_flux),
            "dt": float(dt),
            "species_before": before,
            "species_after": after,
            "delta_species_mass": tuple(a - b for a, b in zip(after, before)),
        })

    system._boundary_exchange = capture


def _terminal_digest_payload(system, accepted_steps):
    """Return the exact contractual terminal replay preimage.

    The durable auditor rebuilds this payload from the primary terminal state
    and raw flux traces. Keep the field set explicit and version it alongside
    the durable evidence schema.
    """
    gas = system.gas
    events = [{"start": event.start, "fresh_air": event.fresh_air,
               "fuel": event.fuel, "ledger": vars(event.ledger).copy()}
              for event in system.p7_events]
    payload = {
        "angle": gas.angle,
        "elapsed_time_s": system.p8_elapsed_time_s,
        "cycle_index": 1,
        "conservative_state": gas._state(),
        "species_masses": system.species_mass,
        "species_initial": system._initial,
        "species_external": system._external,
        "gas_external_cumulative": gas._external_cumulative,
        "gas_last_external": gas._last_external,
        "gas_ledger": gas.ledger,
        "gas_initial": gas._initial,
        "gas_previous_totals": gas._previous_totals,
        "fresh_delivered": system.fresh_delivered,
        "fresh_delivered_tr1": system.fresh_delivered_tr1,
        "fresh_delivered_tr2": system.fresh_delivered_tr2,
        "fresh_short_circuit": system.fresh_short_circuit,
        "p7_events": events,
        "p7_source_delta": system.p7_source_delta,
        "p7_enabled": system.p7_enabled,
        "p7_angular_rate_deg_s": system.p7_angular_rate_deg_s,
        "p8_boundary_species_trace": system.p8_boundary_species_trace,
        "external_flux_trace": system.external_flux_trace,
        "verification_trace": system.verification_trace,
        "gas_history": _primary_gas_history(system.gas.history),
        "accepted_steps": accepted_steps,
    }
    return payload

def _terminal_replay_digest(system, accepted_steps):
    """Hash the canonical JSON representation of the terminal preimage."""
    encoded = json.dumps(_terminal_digest_payload(system, accepted_steps), sort_keys=True,
                         separators=(",", ":"), allow_nan=False).encode("utf-8")
    return sha256(encoded).hexdigest()

def _physical_state_digest(system):
    value = repr((system.gas._state(), system.species_mass)).encode("utf-8")
    return sha256(value).hexdigest()

def _primary_gas_history(history):
    """Select durable numeric SSPRK2 records; omit runtime-only object graphs."""
    fields = ("angle", "angle_start", "dt", "stage_states", "stage_work_rates",
              "stage_external", "stage_exhaust_external", "prescribed_heat", "totals",
              "p8_accepted_state")
    return [{key: record[key] for key in fields if key in record} for record in history]

def _run_once(rpm, *, capture_primary=False):
    case, system = _new_system(rpm, enable_p7=False)
    prep_start, prep_end = PREPARATION_START_DEG, PREPARATION_END_DEG
    prep_cuts = build_event_cuts(case, prep_start, prep_end, p7_enabled=False)
    prep_dts, _ = _advance(system, case, rpm, prep_start, prep_end)
    prep_heat = sum(record["prescribed_heat"] for record in system.gas.history)
    if system.p7_events or prep_heat != 0.0:
        raise RuntimeError("preparation must have P7 disabled and zero heat")
    prepared_fresh = sum(system.species_mass["cylinder"][0][:2])
    geometry_rebase = _reset_measurement(system, case=case)
    _capture_boundary_species(system)
    system.p8_elapsed_time_s = 0.0
    prepared_state_digest = _physical_state_digest(system)
    prepared_snapshot = system.snapshot()
    _, prepared_restored = _new_system(rpm, enable_p7=True)
    prepared_restored.restore(prepared_snapshot)
    prepared_state_reproduced = (_physical_state_digest(prepared_restored) ==
                                 prepared_state_digest)
    measured_start, measured_end = MEASURED_START_DEG, MEASURED_END_DEG
    checkpoint = None; checkpoint_primary_state = None
    checkpoint_boundary_species_trace = None; dts = []; cfls = []
    cuts = build_event_cuts(case, measured_start, measured_end,
                            p7_enabled=True, restart_probe=True)
    while system.gas.angle < measured_end - 1e-12:
        dt, cfl_dt = _step_dt(system.gas, rpm, measured_end, cuts)
        if checkpoint is None and abs(system.gas.angle - RESTART_PROBE_DEG) <= 1e-12:
            # The probe is an exact shared scheduler cut inside P7.
            checkpoint = system.snapshot()
            checkpoint_primary_state = _current(system)
            checkpoint_boundary_species_trace = list(system.p8_boundary_species_trace)
        system.step(dt, angle=system.gas.angle + dt*omega_deg_s(rpm))
        accepted_dt = system.gas.history[-1]["dt"]
        system.p8_elapsed_time_s += accepted_dt
        achieved_cfl = dt/(cfl_dt/P8_CFL)
        dts.append(dt); cfls.append(achieved_cfl)
        if capture_primary:
            system.gas.history[-1]["p8_accepted_state"] = _accepted_trajectory_state(
                system, step_index=len(system.gas.history), dt=accepted_dt,
                achieved_cfl=achieved_cfl)
    if checkpoint is None:
        raise RuntimeError("restart checkpoint was not reached inside measured P7 event")
    from .coupling import ChamberState
    def pressure(q): return ChamberState(q[0], q[2], q[3], q[4]).thermodynamics(system.gas.eos)[1]
    pmax = max((pressure(h["stage_states"][i][1]) for h in system.gas.history for i in range(3)), default=0.0)
    work = -sum(.5*h["dt"]*sum(h["stage_work_rates"][i][1] for i in (0,1)) for h in system.gas.history)
    ccwork = -sum(.5*h["dt"]*sum(h["stage_work_rates"][i][0] for i in (0,1)) for h in system.gas.history)
    system.validate(); system.gas.admissible(); ledger = system.p7_event.ledger
    final = system.gas.totals(); ext = system.gas._external_cumulative
    heat = sum(h["prescribed_heat"] for h in system.gas.history)
    mres = final["mass"] - system.gas._initial["mass"] - ext["mass"]
    eres = final["energy"] - system.gas._initial["energy"] - ext["energy"] - heat + work + ccwork
    accepted_steps = [{"dt": record["dt"], "achieved_cfl": cfl}
                      for record, cfl in zip(system.gas.history, cfls)]
    if len(accepted_steps) != len(system.gas.history):
        raise RuntimeError("accepted CFL samples do not cover the gas history")
    r = {"rpm": rpm, "omega_deg_s": omega_deg_s(rpm), "prepared_cylinder_fresh_kg": prepared_fresh,
         "window_deg": [MEASURED_START_DEG, MEASURED_END_DEG], "window_s": cycle_duration_s(rpm), "step_count": len(dts),
         "actual_dt_min_s": min(dts), "actual_dt_max_s": max(dts), "achieved_CFL_min": min(cfls),
         "achieved_CFL_max": max(cfls), "cfl_contract": P8_CFL, "prep_step_count": len(prep_dts),
         "geometry_rebase": geometry_rebase,
         "geometry_900_180_equal": all(geometry_rebase.values()), **indicated_metrics(work, rpm, pmax),
         "preparation_state_digest": prepared_state_digest,
         "prepared_initial_state_reproduced": prepared_state_reproduced,
         "preparation": {"start_angle_deg": prep_start, "end_angle_deg": prep_end,
                         "cycles": PREPARATION_CYCLES, "p7_enabled": False, "prescribed_heat_J": prep_heat,
                         "step_count": len(prep_dts), "event_cuts_deg": list(prep_cuts),
                         "fixed_transient": True, "periodic_convergence": "NOT_GRANTED_BY_P4"},
         # The ledger is the durable authoritative P7 heat value. Keep the
         # direct gas-hook sum beside it so the closure gate compares both
         # accounting paths explicitly.
         "prescribed_heat_J": ledger.heat_added,
         "measured_gas_prescribed_heat_J": heat,
         "gas_heat_ledger_residual_J": heat - ledger.heat_added,
         "fresh_mass_delivered_kg": system.fresh_delivered,
         "fresh_short_circuit_mass_kg": system.fresh_short_circuit,
         "species_residual_kg": system.species_sum_error(), "global_mass_residual_kg": mres,
         "global_energy_residual_J": eres, "delivered_work_crankcase_J": ccwork,
         "p7_ledger": vars(ledger).copy(),
         "event_cuts_deg": list(cuts),
         "p7_capture": {"start_angle_deg": P7_START_DEG,
                         "end_angle_deg": P7_END_DEG,
                         "captured_fresh_kg": system.p7_event.fresh,
                         "burned_produced_kg": ledger.burned_produced,
                         "prescribed_heat_J": ledger.heat_added},
         "mass_balance_terms": {"delta_mass": final["mass"] - system.gas._initial["mass"],
                                "external_mass": ext["mass"], "residual": mres},
         "energy_balance_terms": {"delta_energy": final["energy"] - system.gas._initial["energy"],
                                  "external_energy": ext["energy"],
                                  "prescribed_heat": heat,
                                  "crankcase_p_dv_energy": -ccwork,
                                  "cylinder_p_dv_energy": -work,
                                   "residual": eres},
         "terminal_replay_digest": _terminal_replay_digest(system, accepted_steps)}
    r["gates"] = {
        "finite": all(isfinite(float(x)) for x in (work, pmax, *dts, *cfls)),
        "geometry_rebased": all(geometry_rebase.values()), "admissible": bool(system.gas.admissible()),
        "species": abs(system.species_sum_error()) < 1e-12, "p7_one_event": len(system.p7_events) == 1,
        "p7_nonvacuous": (system.p7_event.fresh > 0 and ledger.burned_produced > 0 and ledger.heat_added > 0),
        "p7_source_admissible": abs(ledger.source_mass_residual) < 1e-14 and ledger.burned_produced <= system.p7_event.fresh + 1e-12,
        "p7_heat_consistent": abs(ledger.heat_burn_residual) < 1e-10, "cfl": max(cfls) <= P8_CFL + 1e-12,
        "source_heat_consistent": abs(ledger.heat_added - Q_F*ledger.burned_produced) < 1e-10,
        "prescribed_heat_matches_ledger": abs(heat - ledger.heat_added) < 1e-10,
        "global_mass_conservation": abs(mres) < 1e-12,
        "global_energy_conservation": abs(eres) < 1e-8,
        "prepared_initial_state": prepared_state_reproduced,
    }
    _, restored = _new_system(rpm, enable_p7=True)
    restored.restore(checkpoint)
    restored.p8_elapsed_time_s = checkpoint_primary_state["elapsed_time_s"]
    _capture_boundary_species(restored, checkpoint_boundary_species_trace)
    while restored.gas.angle < measured_end - 1e-12:
        step, _ = _step_dt(restored.gas, rpm, measured_end, cuts)
        restored.step(step, angle=restored.gas.angle + step*omega_deg_s(rpm))
        restored.p8_elapsed_time_s += restored.gas.history[-1]["dt"]
    restarted_state = _current(restored)
    original_state = _current(system)
    r["restart"] = {"executed": True, "checkpoint_angle_deg": checkpoint["gas"]["angle"],
                     "checkpoint_inside_p7": P7_START_DEG < checkpoint["gas"]["angle"] < P7_END_DEG,
                     "state_equal": restarted_state == original_state,
                     "state_mismatch_fields": [key for key in original_state
                                                if restarted_state[key] != original_state[key]],
                      "species_mass_equal": restored.species_mass == system.species_mass,
                      "p7_ledger_equal": vars(restored.p7_event.ledger) == vars(system.p7_event.ledger),
                      "external_equal": restored._external == system._external,
                      "fresh_delivery_equal": restored.fresh_delivered == system.fresh_delivered,
                      "fresh_delivery_tr1_equal": restored.fresh_delivered_tr1 == system.fresh_delivered_tr1,
                      "fresh_delivery_tr2_equal": restored.fresh_delivered_tr2 == system.fresh_delivered_tr2,
                      "short_circuit_equal": restored.fresh_short_circuit == system.fresh_short_circuit}
    r["gates"]["restart"] = all(r["restart"][key] for key in (
        "executed", "checkpoint_inside_p7", "state_equal", "species_mass_equal",
        "p7_ledger_equal", "external_equal", "fresh_delivery_equal",
        "fresh_delivery_tr1_equal", "fresh_delivery_tr2_equal",
        "short_circuit_equal"))
    if capture_primary:
        # These are execution outputs, not the flattened campaign summaries.
        # The offline auditor independently integrates delivery metrics from
        # the raw interface fluxes and rebuilds the terminal digest.
        r["_primary_evidence"] = {
            "schema": "P8_PRIMARY_ANCHOR_V2",
            "rpm": rpm,
            "configuration": {"mechanics": "S2T-0D-01", "cfl": P8_CFL,
                              "eos_R_J_kgK": 287.0, "eos_gamma": 1.35,
                              "preparation_deg": [PREPARATION_START_DEG, PREPARATION_END_DEG],
                              "measured_deg": [MEASURED_START_DEG, MEASURED_END_DEG],
                              "p7_deg": [P7_START_DEG, P7_END_DEG],
                              "restart_probe_deg": RESTART_PROBE_DEG,
                              "float_format": "binary64"},
            "producer_terminal_digest": r["terminal_replay_digest"],
            "terminal": _terminal_digest_payload(system, accepted_steps),
            "restart": {
                "checkpoint_state": checkpoint_primary_state,
                "checkpoint_angle_deg": checkpoint_primary_state["angle"],
                "terminal_state": {**restarted_state,
                                    "gas_last_external": restored.gas._last_external},
            },
        }
    return r

def _write_primary_evidence(output_dir, rpm, label, evidence):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(evidence, ensure_ascii=False, allow_nan=False,
                         separators=(",", ":")).encode("utf-8")
    compressed = gzip.compress(encoded, compresslevel=6, mtime=0)
    name = f"primary-{rpm}-{label}.json.gz"
    path = output_dir / name
    path.write_bytes(compressed)
    return {"schema": evidence["schema"], "path": name,
            "sha256": sha256(compressed).hexdigest(), "size_bytes": len(compressed)}

def run_anchor(rpm, *, primary_output_dir=None, **kwargs):
    capture_primary = primary_output_dir is not None
    a = _run_once(rpm, capture_primary=capture_primary)
    b = _run_once(rpm, capture_primary=capture_primary)
    primary_a = a.pop("_primary_evidence", None)
    primary_b = b.pop("_primary_evidence", None)
    digest_a = a.get("terminal_replay_digest")
    digest_b = b.get("terminal_replay_digest")
    a["deterministic_replay"] = {
        "executed": True,
        "state_equal": (type(digest_a) is str and len(digest_a) == 64
                        and digest_a == digest_b),
        "preparation_state_equal": a["preparation_state_digest"] == b["preparation_state_digest"],
        "metrics_equal": all(a[k] == b[k] for k in ("W_cycle_J", "p_max_Pa", "global_mass_residual_kg", "global_energy_residual_J")),
        "p7_ledger_equal": a["p7_ledger"] == b["p7_ledger"],
        "fresh_delivery_equal": a["fresh_mass_delivered_kg"] == b["fresh_mass_delivered_kg"],
        "short_circuit_equal": a["fresh_short_circuit_mass_kg"] == b["fresh_short_circuit_mass_kg"],
        "external_accounting_equal": (a["mass_balance_terms"] == b["mass_balance_terms"]
                                       and a["energy_balance_terms"] == b["energy_balance_terms"]),
    }
    a["replay_terminal_digests"] = {"first": digest_a, "second": digest_b}
    a["gates"]["deterministic_replay"] = all(a["deterministic_replay"].values())
    if primary_output_dir is not None:
        a["primary_evidence"] = {
            "first": _write_primary_evidence(primary_output_dir, rpm, "first", primary_a),
            "second": _write_primary_evidence(primary_output_dir, rpm, "second", primary_b),
        }
    return a

def run_campaign(output_dir):
    from .simulation_case import SyntheticCase
    output_dir = Path(output_dir); output_dir.mkdir(parents=True, exist_ok=True)
    anchors = [run_anchor(r, primary_output_dir=output_dir) for r in P8_ANCHORS]
    failures = [f"{a['rpm']}:{k}" for a in anchors for k, v in a["gates"].items() if not v]
    ok = not failures
    payload = {"status": "P8_WIDE_RPM_PERFORMANCE_VERIFIED_CONDITIONAL" if ok else "P8_NUMERICAL_GATE_BLOCKED",
               "closure": "P8_READY_FOR_P9_DATA" if ok else "P8_NUMERICAL_GATE_BLOCKED", "failures": failures,
               "semantics": vars(P8Semantics()), "provenance": {"mechanics": "S2T-0D-01", "initial_angle_deg": 180,
               "preparation": {"cycles": PREPARATION_CYCLES, "start_angle_deg": PREPARATION_START_DEG,
                               "end_angle_deg": PREPARATION_END_DEG, "p7_enabled": False,
                               "prescribed_heat_J": 0.0, "fixed_transient": True,
                               "measured_window": [MEASURED_START_DEG, MEASURED_END_DEG],
                               "rebase": [PREPARATION_END_DEG, MEASURED_START_DEG],
                               "periodic_convergence": "NOT_GRANTED_BY_P4"},
               "event_scheduler": "authoritative Model(case).events repeated by 360*k over every absolute interval; measured/restart also cut P7 at 350/390 and restart at 370",
               "residual_accounting": "external mass/energy is intake into stored topology minus exhaust outflow; internal interfaces cancel; energy also includes accepted P7 heat and both chamber -p*dV terms",
               "durable_primary_evidence": "P8_PRIMARY_ANCHOR_V2 gzip JSON per run; every accepted endpoint binds coupled state and ledgers to the terminal before digest/restart/replay; offline auditor recomputes deliveries, short-circuit, balances, work, power and species inventory before evaluating summaries",
               "initial_states_pty": SyntheticCase().initial_pty, "topology": "frozen P5-C/P6/P7 full-topology fixture",
               "synthetic_not_measured": True}, "p4": "BLOCKED / NOT_GRANTED", "p9": "STOPPED", "anchors": anchors}
    (output_dir / "p8-wide-rpm.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    for a in anchors:
        (output_dir / f"anchor-{a['rpm']}.json").write_text(json.dumps(a, indent=2), encoding="utf-8")
    fields = ["rpm", "prepared_cylinder_fresh_kg", "captured_fresh_kg", "burned_produced_kg",
              "prescribed_heat_J", "W_cycle_J", "P_indicated_W", "T_indicated_Nm", "p_max_Pa",
              "restart_state_equal", "checkpoint_angle_deg", "achieved_CFL_max",
              "global_mass_residual_kg", "global_energy_residual_J"]
    with (output_dir / "p8-wide-rpm.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader()
        for a in anchors:
            row = {k: a[k] for k in fields if k not in ("captured_fresh_kg", "burned_produced_kg", "restart_state_equal", "checkpoint_angle_deg")}
            row["captured_fresh_kg"] = a["p7_capture"]["captured_fresh_kg"]
            row["burned_produced_kg"] = a["p7_capture"]["burned_produced_kg"]
            row["restart_state_equal"] = a["restart"]["state_equal"]
            row["checkpoint_angle_deg"] = a["restart"]["checkpoint_angle_deg"]
            w.writerow(row)
    return payload
