"""Independent offline audit for durable P8 replay evidence.

This module deliberately does not import ``motorsim.p8_performance``. It first
binds the accepted coupled SSPRK2 trajectory endpoint to terminal state and
ledgers, then reconstructs fresh delivery/short-circuit and the digest before
comparing those results with campaign/anchor summaries.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import math
from math import fsum
from pathlib import Path
import zlib

SCHEMA = "P8_PRIMARY_ANCHOR_V2"
ANCHORS = (2500, 5000, 8000, 11000, 15000)
FRESH_NAMES = ("fresh_air", "fuel")


class EvidenceError(ValueError):
    pass


def _reject_constant(value):
    raise EvidenceError(f"non-finite JSON constant: {value}")


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise EvidenceError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _number(value, label):
    if type(value) not in (int, float) or not math.isfinite(float(value)):
        raise EvidenceError(f"{label} must be a finite JSON number")
    return float(value)


def _finite_tree(value, label="evidence"):
    if isinstance(value, bool) or value is None or isinstance(value, str):
        return
    if type(value) in (int, float):
        if not math.isfinite(float(value)):
            raise EvidenceError(f"{label} contains a non-finite number")
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _finite_tree(item, f"{label}[{index}]")
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise EvidenceError(f"{label} has a non-string object key")
            _finite_tree(item, f"{label}.{key}")
        return
    raise EvidenceError(f"{label} contains unsupported type {type(value).__name__}")


def canonical_bytes(payload):
    """Stable UTF-8 JSON: sorted keys, compact separators, finite numbers only.

    Python's shortest-round-trip binary64 JSON text is used. Arrays retain
    order, integers use base-10 JSON integer syntax, field presence is exact,
    and signed zero remains distinguishable as ``-0.0`` versus ``0.0``.
    NaN and infinities are rejected.
    """
    _finite_tree(payload)
    return json.dumps(payload, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def _fresh_metrics(primary):
    terminal = primary["terminal"]
    history = terminal["gas_history"]
    steps = terminal["accepted_steps"]
    traces = terminal["verification_trace"]
    if type(len(history)) is not int or not history or len(history) != len(steps):
        raise EvidenceError("gas history and accepted-step evidence differ")
    if len(traces) != 2 * len(history):
        raise EvidenceError("each accepted step must have exactly two resolved species traces")

    delivered = {"tr1<->cylinder": 0.0, "tr2<->cylinder": 0.0}
    short_circuit = 0.0
    seen = set()
    observed = []
    for trace in traces:
        step_index = trace.get("step_index")
        stage_index = trace.get("stage_index")
        if type(step_index) is not int or type(stage_index) is not int:
            raise EvidenceError("trace step/stage identity must be integer, not boolean")
        if not 1 <= step_index <= len(history) or stage_index not in (0, 1):
            raise EvidenceError("trace step/stage identity is outside accepted history")
        identity = (step_index, stage_index)
        if identity in seen:
            raise EvidenceError("duplicate stage flux trace")
        seen.add(identity)
        observed.append(identity)
        history_index = step_index - 1
        dt = _number(history[history_index]["dt"], "gas_history.dt")
        accepted_dt = _number(steps[history_index]["dt"], "accepted_steps.dt")
        if dt <= 0.0 or dt != accepted_dt:
            raise EvidenceError("accepted dt does not match raw gas history")
        _number(steps[history_index]["achieved_cfl"], "accepted_steps.achieved_cfl")
        factor = 0.5 * dt
        for interface in trace.get("interfaces", []):
            name = interface.get("interface_name")
            if name not in (*delivered.keys(), "cylinder<->exhaust"):
                continue
            mass_flux = _number(interface.get("gas_mass_flux"), "interface.gas_mass_flux")
            fractions = interface.get("donor_species_fractions")
            if not isinstance(fractions, dict):
                raise EvidenceError("interface donor fractions are missing")
            fresh_fraction = sum(_number(fractions.get(species),
                                         f"donor_species_fractions.{species}")
                                 for species in FRESH_NAMES)
            signed_fresh_flux = mass_flux * fresh_fraction
            if signed_fresh_flux > 0.0:
                increment = factor * signed_fresh_flux
                if name in delivered:
                    delivered[name] += increment
                else:
                    short_circuit += increment

    expected = [(step, stage) for step in range(1, len(history) + 1)
                for stage in (0, 1)]
    if observed != expected:
        raise EvidenceError("resolved species traces do not preserve every SSPRK2 stage in order")
    tr1 = delivered["tr1<->cylinder"]
    tr2 = delivered["tr2<->cylinder"]
    return {"fresh_delivered_tr1": tr1, "fresh_delivered_tr2": tr2,
            "fresh_delivered": tr1 + tr2,
            "fresh_short_circuit": short_circuit}


def _validate_trajectory_terminal(terminal, rpm):
    """Bind terminal state/ledgers to the final accepted coupled SSPRK2 path."""
    history = terminal.get("gas_history")
    steps = terminal.get("accepted_steps")
    if (not isinstance(history, list) or not history
            or not isinstance(steps, list) or len(history) != len(steps)):
        raise EvidenceError("trajectory_terminal_mismatch: accepted history is incomplete")
    elapsed = 0.0
    previous_angle = 180.0
    last = None
    for index, (record, step) in enumerate(zip(history, steps), start=1):
        accepted = record.get("p8_accepted_state")
        if not isinstance(accepted, dict):
            raise EvidenceError("trajectory_terminal_mismatch: accepted coupled state is missing")
        if accepted.get("step_index") != index:
            raise EvidenceError("trajectory_terminal_mismatch: step identity differs from history")
        dt = _number(record.get("dt"), "gas_history.dt")
        if dt != _number(step.get("dt"), "accepted_steps.dt") or dt != _number(
                accepted.get("dt"), "accepted_state.dt"):
            raise EvidenceError("trajectory_terminal_mismatch: accepted dt differs from history")
        cfl = _number(step.get("achieved_cfl"), "accepted_steps.achieved_cfl")
        if cfl != _number(accepted.get("achieved_cfl"), "accepted_state.achieved_cfl"):
            raise EvidenceError("trajectory_terminal_mismatch: accepted CFL differs from history")
        stage_states = record.get("stage_states")
        if not isinstance(stage_states, list) or len(stage_states) != 3:
            raise EvidenceError("trajectory_terminal_mismatch: SSPRK2 stages are incomplete")
        # The accepted coupled endpoint is captured immediately after
        # system.step returns. The SSPRK2 q_n candidate is installed into
        # chamber primitives and reconstructed by _state(), which can differ
        # by one binary64 ulp; record.totals and the accepted snapshot are the
        # exact post-install state used by the next step.
        angle = record.get("angle")
        if (angle != accepted.get("angle") or record.get("angle_start") != previous_angle
                or accepted.get("cycle_index") != 1):
            raise EvidenceError("trajectory_terminal_mismatch: accepted cycle/angle identity differs")
        if angle != previous_angle + dt * (6.0 * rpm):
            raise EvidenceError("trajectory_terminal_mismatch: accepted angle does not follow dt/RPM")
        elapsed += dt
        if accepted.get("elapsed_time_s") != elapsed:
            raise EvidenceError("trajectory_terminal_mismatch: accepted elapsed time differs")
        previous_angle = angle
        last = accepted
    if (last is None or previous_angle != 540.0
            or terminal.get("angle") != previous_angle
            or terminal.get("elapsed_time_s") != last.get("elapsed_time_s")
            or terminal.get("cycle_index") != last.get("cycle_index")):
        raise EvidenceError("trajectory_terminal_mismatch: terminal cycle/time/angle differs")
    if history[-1].get("totals") != terminal.get("gas_previous_totals"):
        raise EvidenceError("trajectory_terminal_mismatch: terminal gas totals differ")

    fields = (
        "conservative_state", "species_masses", "species_initial", "species_external",
        "gas_external_cumulative", "gas_last_external", "gas_ledger", "gas_initial",
        "gas_previous_totals", "fresh_delivered", "fresh_delivered_tr1",
        "fresh_delivered_tr2", "fresh_short_circuit", "p7_events", "p7_source_delta",
        "p7_enabled", "p7_angular_rate_deg_s",
    )
    for field in fields:
        if terminal.get(field) != last.get(field):
            raise EvidenceError(f"trajectory_terminal_mismatch: {field}")
    if terminal.get("p7_angular_rate_deg_s") != 6.0 * rpm:
        raise EvidenceError("trajectory_terminal_mismatch: angular rate differs from anchor")


def _derive_one(primary):
    if primary.get("schema") != SCHEMA:
        raise EvidenceError("unsupported primary evidence schema")
    rpm = primary.get("rpm")
    if type(rpm) is not int or rpm not in ANCHORS:
        raise EvidenceError("primary RPM is not a contractual anchor")
    _finite_tree(primary)
    terminal = primary.get("terminal")
    if not isinstance(terminal, dict):
        raise EvidenceError("terminal primary state is missing")
    if terminal.get("p7_enabled") is not True:
        raise EvidenceError("terminal primary state is outside the measured contract")
    _validate_trajectory_terminal(terminal, rpm)
    if terminal.get("p7_angular_rate_deg_s") != 6.0 * rpm:
        raise EvidenceError("terminal angular rate does not match the anchor RPM")

    counters = _fresh_metrics(primary)
    # The output counters in the producer terminal object are evidence to be
    # checked, never the values used to construct the independently rebuilt
    # preimage.
    for name, value in counters.items():
        if _number(terminal.get(name), f"terminal.{name}") != value:
            raise EvidenceError(f"primary counter disagrees with raw fluxes: {name}")
    preimage = dict(terminal)
    preimage.update(counters)
    digest = hashlib.sha256(canonical_bytes(preimage)).hexdigest()
    if primary.get("producer_terminal_digest") != digest:
        raise EvidenceError("producer digest does not match independently rebuilt preimage")

    history = terminal["gas_history"]
    steps = terminal["accepted_steps"]
    configuration = primary.get("configuration")
    if not isinstance(configuration, dict) or configuration.get("mechanics") != "S2T-0D-01":
        raise EvidenceError("primary configuration/provenance is missing")
    if (configuration.get("float_format") != "binary64"
            or configuration.get("cfl") != 0.4
            or configuration.get("eos_R_J_kgK") != 287.0
            or configuration.get("preparation_deg") != [180.0, 900.0]
            or configuration.get("measured_deg") != [180.0, 540.0]
            or configuration.get("p7_deg") != [350.0, 390.0]
            or configuration.get("restart_probe_deg") != 370.0):
        raise EvidenceError("primary numerical configuration differs from P8 contract")
    gamma = _number(configuration.get("eos_gamma"), "configuration EOS gamma")
    if gamma != 1.35:
        raise EvidenceError("primary EOS configuration differs from frozen P8 fixture")
    work = 0.0
    crankcase_work = 0.0
    heat = 0.0
    max_cfl = 0.0
    min_cfl = math.inf
    pmax = 0.0
    external_totals = {"mass": 0.0, "energy": 0.0, "species": 0.0}
    species_names = ("fresh_air", "fuel", "residual", "burned")
    external_species = [0.0] * 4
    external_trace = terminal.get("external_flux_trace")
    if not isinstance(external_trace, list) or len(external_trace) != 2 * len(history):
        raise EvidenceError("resolved external flux trace is incomplete")
    boundary_trace = terminal.get("p8_boundary_species_trace")
    if not isinstance(boundary_trace, list) or len(boundary_trace) != 4 * len(history):
        raise EvidenceError("accepted external species boundary deltas are incomplete")
    for record, step in zip(history, steps):
        dt = _number(record["dt"], "gas_history.dt")
        rates = record.get("stage_work_rates")
        if not isinstance(rates, list) or len(rates) != 2:
            raise EvidenceError("raw history must contain both SSPRK2 work-rate stages")
        # Same trapezoidal SSPRK2 quadrature, applied offline to saved rates.
        work -= 0.5 * dt * sum(_number(rates[i][1], "cylinder work rate") for i in (0, 1))
        crankcase_work -= 0.5 * dt * sum(_number(rates[i][0], "crankcase work rate") for i in (0, 1))
        heat += _number(record["prescribed_heat"], "prescribed heat")
        cfl = _number(step["achieved_cfl"], "achieved CFL")
        max_cfl = max(max_cfl, cfl)
        min_cfl = min(min_cfl, cfl)
        stage_states = record.get("stage_states")
        if not isinstance(stage_states, list) or len(stage_states) != 3:
            raise EvidenceError("raw gas history lacks SSPRK2 stage states")
        for stage_state in stage_states:
            cylinder = stage_state[1]
            pressure = (gamma - 1.0) * _number(cylinder[2], "cylinder internal energy") / _number(
                cylinder[4], "cylinder volume")
            pmax = max(pmax, pressure)
        stage_external = record.get("stage_external")
        stage_exhaust_external = record.get("stage_exhaust_external")
        if not isinstance(stage_external, list) or not isinstance(stage_exhaust_external, list):
            raise EvidenceError("raw external boundary fluxes are missing")
        if len(stage_external) != 2 or len(stage_exhaust_external) != 2:
            raise EvidenceError("raw external boundary fluxes lack two SSPRK2 stages")
        for key, index in (("mass", 0), ("energy", 2), ("species", 3)):
            intake0 = _number(stage_external[0][index], f"intake {key} flux")
            intake1 = _number(stage_external[1][index], f"intake {key} flux")
            exhaust0 = _number(stage_exhaust_external[0][index], f"exhaust {key} flux")
            exhaust1 = _number(stage_exhaust_external[1][index], f"exhaust {key} flux")
            step_exchange = 0.5 * (intake0 + intake1 - exhaust0 - exhaust1) * dt
            external_totals[key] += step_exchange
    # Recompute accepted species boundary deltas from before/after primary
    # inventories and verify the donor formula, including atmospheric backflow.
    for trace_index, trace in enumerate(boundary_trace):
        step_index = trace_index // 4 + 1
        within_step = trace_index % 4
        stage_index, boundary_index = divmod(within_step, 2)
        if (trace.get("step_index") != step_index
                or trace.get("stage_index") != stage_index
                or trace.get("boundary_index") != boundary_index):
            raise EvidenceError("external species boundary trace order/identity is malformed")
        record = history[step_index - 1]
        dt = _number(record["dt"], "gas_history.dt")
        if _number(trace.get("dt"), "boundary trace dt") != dt:
            raise EvidenceError("external species boundary dt differs from gas step")
        component = "intake" if boundary_index == 0 else "exhaust"
        incoming = boundary_index == 0
        if trace.get("component") != component or trace.get("incoming") is not incoming:
            raise EvidenceError("external species boundary identity is invalid")
        mass_flux = _number(trace.get("mass_flux"), "boundary mass flux")
        raw = record["stage_external"][stage_index] if incoming else record["stage_exhaust_external"][stage_index]
        if mass_flux != _number(raw[0], "raw boundary gas mass flux"):
            raise EvidenceError("species boundary flux differs from raw gas boundary flux")
        before = trace.get("species_before")
        after = trace.get("species_after")
        delta = trace.get("delta_species_mass")
        if not all(isinstance(vector, list) and len(vector) == 4
                   for vector in (before, after, delta)):
            raise EvidenceError("malformed accepted species boundary vectors")
        before = [_number(x, "species boundary before") for x in before]
        after = [_number(x, "species boundary after") for x in after]
        delta = [_number(x, "species boundary delta") for x in delta]
        donor_total = fsum(before)
        if donor_total <= 0.0:
            raise EvidenceError("external species donor inventory is empty")
        donor = ([1.0, 0.0, 0.0, 0.0]
                 if (mass_flux > 0.0) == incoming
                 else [value / donor_total for value in before])
        donor_sum = fsum(donor)
        signed_flux = mass_flux if incoming else -mass_flux
        expected_delta_from_flux = [dt * (signed_flux * donor[i] / donor_sum)
                                    for i in range(4)]
        expected_after = [before[i] + expected_delta_from_flux[i] for i in range(4)]
        expected_delta = [after[i] - before[i] for i in range(4)]
        if expected_after != after or expected_delta != delta:
            raise EvidenceError("accepted species boundary delta does not follow resolved donor semantics")
        # The P6 state is SSPRK2: each accepted stage exchange contributes
        # half of its stage delta to the final blended state.
        for species_index in range(4):
            external_species[species_index] += 0.5 * delta[species_index]

    final_totals = history[-1].get("totals")
    gas_initial = terminal.get("gas_initial")
    external = terminal.get("gas_external_cumulative")
    if not all(isinstance(x, dict) for x in (final_totals, gas_initial, external)):
        raise EvidenceError("mass/energy primary ledger is incomplete")
    for key in ("mass", "energy", "species"):
        if external_totals[key] != _number(external[key], f"stored external {key}"):
            raise EvidenceError(f"raw external {key} fluxes do not reproduce accumulated ledger")
    mass_residual = (_number(final_totals["mass"], "final mass")
                     - _number(gas_initial["mass"], "initial mass")
                     - external_totals["mass"])
    energy_residual = (_number(final_totals["energy"], "final energy")
                       - _number(gas_initial["energy"], "initial energy")
                       - external_totals["energy"]
                       - heat + work + crankcase_work)

    species_masses = terminal.get("species_masses")
    if not isinstance(species_masses, dict):
        raise EvidenceError("terminal species state is missing")
    all_cells = []
    for component, cells in species_masses.items():
        for cell in cells:
            if not isinstance(cell, list) or len(cell) != 4:
                raise EvidenceError(f"malformed four-species cell in {component}")
            all_cells.append([_number(x, f"species_mass.{component}") for x in cell])
    species_totals = tuple(fsum(cell[index] for cell in all_cells) for index in range(4))
    species_residual = sum(species_totals) - _number(
        terminal["gas_previous_totals"]["mass"], "terminal gas mass")
    initial_species = terminal.get("species_initial")
    p7_delta = terminal.get("p7_source_delta")
    if not isinstance(initial_species, list) or len(initial_species) != 4 or not isinstance(p7_delta, list) or len(p7_delta) != 4:
        raise EvidenceError("species initial/source ledgers are incomplete")
    species_balance = [species_totals[i] - _number(initial_species[i], "initial species")
                       - external_species[i] - _number(p7_delta[i], "P7 species source")
                       for i in range(4)]

    p7_events = terminal.get("p7_events")
    if not isinstance(p7_events, list) or len(p7_events) != 1:
        raise EvidenceError("primary terminal state must contain exactly one P7 event")
    ledger = p7_events[0].get("ledger")
    if not isinstance(ledger, dict):
        raise EvidenceError("primary P7 ledger is missing")
    return {
        "rpm": rpm,
        "terminal_digest": digest,
        "terminal_core": {key: value for key, value in preimage.items()
                           if key not in ("verification_trace", "external_flux_trace",
                                          "gas_history", "accepted_steps")},
        "recomputed_preimage": preimage,
        "counters": counters,
        "work": work,
        "crankcase_work": crankcase_work,
        "power": work * rpm / 60.0,
        "torque": work / (2.0 * math.pi),
        "p_max": pmax,
        "heat": heat,
        "mass_residual": mass_residual,
        "energy_residual": energy_residual,
        "species_residual": species_residual,
        "external_totals": external_totals,
        "external_species": external_species,
        "species_balance": species_balance,
        "max_cfl": max_cfl,
        "min_cfl": min_cfl,
        "p7_ledger": ledger,
        "captured_fresh": _number(p7_events[0]["fresh_air"], "P7 captured fresh air")
                          + _number(p7_events[0]["fuel"], "P7 captured fuel"),
        "burned_produced": _number(ledger["burned_produced"], "P7 burned produced"),
        "p7_heat": _number(ledger["heat_added"], "P7 heat"),
    }


def _matches_summary(derived, anchor):
    checks = {
        "fresh_mass_delivered_kg": derived["counters"]["fresh_delivered"],
        "fresh_short_circuit_mass_kg": derived["counters"]["fresh_short_circuit"],
        "W_cycle_J": derived["work"],
        "P_indicated_W": derived["power"],
        "T_indicated_Nm": derived["torque"],
        "p_max_Pa": derived["p_max"],
        "prescribed_heat_J": derived["p7_heat"],
        "global_mass_residual_kg": derived["mass_residual"],
        "global_energy_residual_J": derived["energy_residual"],
        "species_residual_kg": derived["species_residual"],
        "achieved_CFL_max": derived["max_cfl"],
    }
    for field, value in checks.items():
        stored = anchor.get(field)
        if type(stored) not in (int, float) or not math.isfinite(float(stored)) or stored != value:
            raise EvidenceError(f"anchor summary differs from primary recomputation: {field} ({stored!r} != {value!r})")
    if anchor.get("p7_ledger") != derived["p7_ledger"]:
        raise EvidenceError("anchor P7 ledger differs from primary state")
    capture = anchor.get("p7_capture", {})
    if capture.get("captured_fresh_kg") != derived["captured_fresh"]:
        raise EvidenceError("anchor P7 capture differs from primary event")
    if capture.get("burned_produced_kg") != derived["burned_produced"]:
        raise EvidenceError("anchor P7 burn differs from primary ledger")


def audit_anchor_primary(anchor, first, second):
    """Validate one summary against two raw runs and directly compare states."""
    try:
        a = _derive_one(first)
        b = _derive_one(second)
        if a["rpm"] != b["rpm"] or a["rpm"] != anchor.get("rpm"):
            raise EvidenceError("primary and summary RPM identities differ")
        if a["terminal_core"] != b["terminal_core"]:
            raise EvidenceError("terminal primary state/ledgers differ across replay runs")
        if a["recomputed_preimage"] != b["recomputed_preimage"]:
            raise EvidenceError("raw histories/flux traces differ across replay runs")
        if a["counters"] != b["counters"]:
            raise EvidenceError("recomputed counters differ across replay runs")
        restart = first.get("restart", {})
        if restart.get("checkpoint_angle_deg") != 370.0:
            raise EvidenceError("restart primary checkpoint is not inside the P7 interval")
        replay_terminal = restart.get("terminal_state")
        if not isinstance(replay_terminal, dict):
            raise EvidenceError("restart terminal primary state is missing")
        # Compare the common, directly available state fields, not saved PASS
        # flags and not one digest against another digest.
        raw_events = replay_terminal.get("p7_events")
        if not isinstance(raw_events, list):
            raise EvidenceError("restart terminal P7 events are missing")
        normalized_events = []
        for event in raw_events:
            if not isinstance(event, list) or len(event) != 4:
                raise EvidenceError("malformed restart P7 event state")
            normalized_events.append({"start": event[0], "fresh_air": event[1],
                                      "fuel": event[2], "ledger": event[3]})
        direct = {
            "angle": replay_terminal.get("angle"),
            "elapsed_time_s": replay_terminal.get("elapsed_time_s"),
            "cycle_index": replay_terminal.get("cycle_index"),
            "conservative_state": replay_terminal.get("conservative_state"),
            "species_masses": replay_terminal.get("species_mass"),
            "species_initial": replay_terminal.get("species_initial"),
            "species_external": replay_terminal.get("species_external"),
            "gas_initial": replay_terminal.get("gas_initial"),
            "gas_previous_totals": replay_terminal.get("gas_previous_totals"),
            "gas_external_cumulative": replay_terminal.get("gas_external_cumulative"),
            "gas_last_external": replay_terminal.get("gas_last_external"),
            "gas_ledger": replay_terminal.get("gas_ledger"),
            "p7_events": normalized_events,
            "p7_source_delta": replay_terminal.get("p7_source_delta"),
            "p7_enabled": replay_terminal.get("p7_enabled"),
            "p7_angular_rate_deg_s": replay_terminal.get("p7_angular_rate_deg_s"),
            "p8_boundary_species_trace": replay_terminal.get("p8_boundary_species_trace"),
            "fresh_delivered": replay_terminal.get("fresh_delivered"),
            "fresh_delivered_tr1": replay_terminal.get("fresh_delivered_tr1"),
            "fresh_delivered_tr2": replay_terminal.get("fresh_delivered_tr2"),
            "fresh_short_circuit": replay_terminal.get("fresh_short_circuit"),
        }
        if direct != a["terminal_core"]:
            mismatches = [key for key in a["terminal_core"]
                          if direct.get(key) != a["terminal_core"][key]]
            raise EvidenceError("restart terminal state differs in: " + ", ".join(mismatches))
        if (abs(a["mass_residual"]) >= 1e-12
                or abs(a["energy_residual"]) >= 1e-8
                or abs(a["species_residual"]) >= 1e-12
                or any(abs(value) >= 1e-12 for value in a["species_balance"])
                or a["max_cfl"] > 0.4 + 1e-12
                or a["captured_fresh"] <= 0.0
                or a["burned_produced"] <= 0.0
                or a["p7_heat"] <= 0.0):
            raise EvidenceError(
                "independently recomputed gates fail: "
                f"mass={a['mass_residual']!r}, energy={a['energy_residual']!r}, "
                f"species={a['species_residual']!r}, species_ledger={a['species_balance']!r}, "
                f"cfl={a['max_cfl']!r}, fresh={a['captured_fresh']!r}, "
                f"burned={a['burned_produced']!r}, heat={a['p7_heat']!r}")
        ledger = a["p7_ledger"]
        if (abs(_number(ledger["source_mass_residual"], "P7 source residual")) >= 1e-14
                or a["burned_produced"] > a["captured_fresh"] + 1e-12
                or abs(a["p7_heat"] - 800000.0 * a["burned_produced"]) >= 1e-10):
            raise EvidenceError("independently recomputed P7 source/heat gates fail")
        _matches_summary(a, anchor)
        _matches_summary(b, {**anchor,
                             "fresh_mass_delivered_kg": b["counters"]["fresh_delivered"],
                             "fresh_short_circuit_mass_kg": b["counters"]["fresh_short_circuit"],
                             "W_cycle_J": b["work"], "P_indicated_W": b["power"],
                             "T_indicated_Nm": b["torque"],
                             "p_max_Pa": b["p_max"],
                             "prescribed_heat_J": b["p7_heat"],
                             "global_mass_residual_kg": b["mass_residual"],
                             "global_energy_residual_J": b["energy_residual"],
                             "species_residual_kg": b["species_residual"],
                             "achieved_CFL_max": b["max_cfl"],
                             "p7_ledger": b["p7_ledger"],
                             "p7_capture": {"captured_fresh_kg": b["captured_fresh"],
                                             "burned_produced_kg": b["burned_produced"]}})
        digests = anchor.get("replay_terminal_digests", {})
        if digests.get("first") != a["terminal_digest"] or digests.get("second") != b["terminal_digest"]:
            raise EvidenceError("stored replay digest differs from independently rebuilt preimage")
        deterministic = anchor.get("deterministic_replay", {})
        for key in ("executed", "state_equal", "preparation_state_equal", "metrics_equal",
                    "p7_ledger_equal", "fresh_delivery_equal", "short_circuit_equal",
                    "external_accounting_equal"):
            if deterministic.get(key) is not True:
                raise EvidenceError(f"stored replay gate is not true: {key}")
        def compact(item):
            return {key: item[key] for key in (
                "terminal_digest", "counters", "work", "crankcase_work", "power",
                "torque", "p_max", "heat", "mass_residual", "energy_residual",
                "species_residual", "external_totals", "external_species",
                "species_balance", "max_cfl", "min_cfl", "p7_ledger",
                "captured_fresh", "burned_produced", "p7_heat")}
        return {"passed": True, "rpm": a["rpm"],
                "first": compact(a), "second": compact(b), "reason": None}
    except (EvidenceError, KeyError, TypeError, AttributeError, IndexError,
            OverflowError, ValueError) as exc:
        return {"passed": False, "rpm": anchor.get("rpm"), "reason": str(exc)}


def _load_json(path):
    return json.loads(path.read_text(encoding="utf-8"), parse_constant=_reject_constant,
                      object_pairs_hook=_unique_object)


def _load_primary(result_dir, reference):
    if not isinstance(reference, dict) or reference.get("schema") != SCHEMA:
        raise EvidenceError("primary artifact reference/schema is missing")
    relative = Path(reference.get("path", ""))
    if relative.is_absolute() or ".." in relative.parts:
        raise EvidenceError("primary artifact path escapes campaign directory")
    path = result_dir / relative
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != reference.get("sha256"):
        raise EvidenceError("primary artifact SHA-256 mismatch")
    if len(raw) != reference.get("size_bytes"):
        raise EvidenceError("primary artifact size mismatch")
    data = json.loads(gzip.decompress(raw).decode("utf-8"),
                      parse_constant=_reject_constant, object_pairs_hook=_unique_object)
    _finite_tree(data)
    return data


def audit_campaign(result_dir):
    """Independently audit campaign files; summaries are consumers, never proof."""
    result_dir = Path(result_dir)
    try:
        campaign = _load_json(result_dir / "p8-wide-rpm.json")
        semantics = campaign.get("semantics", {})
        if (campaign.get("status") != "P8_WIDE_RPM_PERFORMANCE_VERIFIED_CONDITIONAL"
                or campaign.get("p4") != "BLOCKED / NOT_GRANTED"
                or campaign.get("p9") != "STOPPED"
                or semantics.get("metric_semantics") != "BOUNDED_TRANSIENT_INDICATED"
                or semantics.get("experimental_validation") != "NOT_PERFORMED"
                or semantics.get("periodic_convergence") != "NOT_GRANTED_BY_P4"
                or semantics.get("independent_review") != "INDEPENDENT_REVIEW_PENDING"
                or semantics.get("conditional_on_p4") is not True
                or semantics.get("steady_state") is not False):
            raise EvidenceError("campaign status/provenance differs from conditional P8 contract")
        provenance = campaign.get("provenance", {})
        preparation = provenance.get("preparation", {})
        if (provenance.get("mechanics") != "S2T-0D-01"
                or provenance.get("initial_angle_deg") != 180
                or provenance.get("topology") != "frozen P5-C/P6/P7 full-topology fixture"
                or provenance.get("synthetic_not_measured") is not True
                or preparation.get("cycles") != 2
                or preparation.get("start_angle_deg") != 180.0
                or preparation.get("end_angle_deg") != 900.0
                or preparation.get("p7_enabled") is not False
                or preparation.get("prescribed_heat_J") != 0.0
                or preparation.get("measured_window") != [180.0, 540.0]
                or preparation.get("rebase") != [900.0, 180.0]):
            raise EvidenceError("frozen P8 topology/preparation provenance mismatch")
        anchors_list = campaign.get("anchors", [])
        if not isinstance(anchors_list, list) or any(
                not isinstance(row, dict) or type(row.get("rpm")) is not int
                for row in anchors_list):
            raise EvidenceError("campaign anchors must have strict integer RPM identities")
        anchors = {row["rpm"]: row for row in anchors_list}
        if tuple(sorted(anchors)) != ANCHORS or len(anchors_list) != len(ANCHORS):
            raise EvidenceError("campaign anchors are incomplete or duplicated")
        per_file_equal = True
        results = {}
        for rpm in ANCHORS:
            anchor = anchors[rpm]
            per_path = result_dir / f"anchor-{rpm}.json"
            per_anchor = _load_json(per_path)
            per_file_equal &= per_anchor == anchor
            refs = anchor.get("primary_evidence", {})
            first = _load_primary(result_dir, refs.get("first"))
            second = _load_primary(result_dir, refs.get("second"))
            results[rpm] = audit_anchor_primary(anchor, first, second)
        ok = per_file_equal and all(result["passed"] for result in results.values())
        return {"schema": "P8_DURABLE_AUDIT_V1", "passed": ok,
                "classification": "P8_PRIMARY_EVIDENCE_REAUDIT_PASS" if ok else "P8_PRIMARY_EVIDENCE_BLOCKED",
                "campaign_path": str(result_dir), "anchor_file_copies_equal": per_file_equal,
                "anchors": results}
    except (EvidenceError, OSError, json.JSONDecodeError, KeyError, TypeError,
            AttributeError, IndexError, OverflowError, ValueError, gzip.BadGzipFile,
            EOFError, zlib.error) as exc:
        return {"schema": "P8_DURABLE_AUDIT_V1", "passed": False,
                "classification": "P8_PRIMARY_EVIDENCE_BLOCKED",
                "campaign_path": str(result_dir), "reason": str(exc), "anchors": {}}


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("campaign", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = audit_campaign(args.campaign)
    rendered = json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False)
    if args.output:
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
