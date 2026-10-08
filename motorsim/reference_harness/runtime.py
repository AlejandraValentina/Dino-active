"""Composition of existing MotorSim P5-C/P6/P7 components for reference runs."""
from __future__ import annotations

from math import isfinite

from ..gas1d.eos import IdealGas
from ..gas1d.mesh import segments_mesh
from ..gas1d.solver import event_step
from ..p5b import Chamber
from ..p5c import IntegratedP5C
from ..p6_species import P6IntegratedSystem
from ..coupling import ChamberState
from ..duct_network import interface_exchange
from ..gas1d.boundary import Boundary
from ..gas1d.open_end_plenum_v2 import OpenEndPlenumV2Boundary
from ..simulation import Model
from ..simulation_case import SyntheticCase

START_DEG = 30.0
END_DEG = 390.0


def _segment_data(route):
    return [{"length": s.length_mm, "start_diameter": s.start_diameter_mm,
             "end_diameter": s.end_diameter_mm} for s in route]


def _primitive(state, eos):
    return (state["pressure_Pa"] / (eos.R * state["temperature_K"]),
            state["velocity_m_s"], state["pressure_Pa"],
            state["species_mass_fractions"]["fresh_air"] +
            state["species_mass_fractions"]["fuel"])


def _fractions(state):
    return tuple(state["species_mass_fractions"][name]
                 for name in ("fresh_air", "fuel", "residual", "burned"))


def build_system(config):
    """Build a P5-C/P6/P7 system solely from a validated generic config."""
    from .config import validate_config
    parsed = validate_config(config)
    project = parsed["project"]
    rpm = float(config["operating_point"]["rpm"])
    numerics = config["numerics"]
    eos = IdealGas(parsed["gas_R_J_kgK"], parsed["gamma"])
    states = config["initial_states"]
    pty = tuple((states[name]["pressure_Pa"], states[name]["temperature_K"],
                 states[name]["species_mass_fractions"]["fresh_air"] +
                 states[name]["species_mass_fractions"]["fuel"])
                for name in ("intake", "crankcase", "cylinder", "exhaust"))
    case = SyntheticCase(project_geometry=project, rpm=rpm,
                        gas_r=eos.R, gamma=eos.gamma, initial_pty=pty,
                        initial_angle_deg=START_DEG,
                        heat_start_deg=parsed["physical_event_phase_deg"],
                        heat_duration_deg=40.0, fresh_energy_j_kg=800000.0)
    model = Model(case)
    offset = 350.0 - parsed["physical_event_phase_deg"]

    def geometry_callback(scheduler_angle):
        physical_angle = float(scheduler_angle) - offset
        volumes, rates, areas = model.geometry(physical_angle)
        return {"volumes": volumes, "volume_rates": (rates[1], rates[2]),
                "areas": (areas[1], areas[2], areas[3], areas[4])}

    dx = parsed["dx_target_m"]
    intake_mesh = segments_mesh(_segment_data(project.ducts.intake), dx)
    transfer_meshes = tuple(segments_mesh(duct if isinstance(duct, list) else [duct], dx)
                            for duct in config["transfer_ducts"])
    exhaust_mesh = segments_mesh(_segment_data(project.ducts.exhaust), dx)
    meshes = (intake_mesh, *transfer_meshes)
    volumes = model.geometry(START_DEG)[0]

    def primitive_list(name, mesh):
        value = states[name]
        entries = value if isinstance(value, list) else [value] * mesh.n
        if len(entries) != mesh.n:
            raise ValueError(f"initial_states.{name} count must match its generated mesh")
        return tuple(_primitive(item, eos) for item in entries)

    intake = primitive_list("intake", intake_mesh)
    tr1 = primitive_list("transfer1", transfer_meshes[0])
    tr2 = primitive_list("transfer2", transfer_meshes[1])
    exhaust = primitive_list("exhaust", exhaust_mesh)
    cc, cy = states["crankcase"], states["cylinder"]
    chambers = []
    for name, volume in (("crankcase", volumes[1]), ("cylinder", volumes[2])):
        state = states[name]
        chambers.append(Chamber(_primitive(state, eos), volume))
    # P5-C's finite exhaust port couples against the exhaust-path area; intake
    # and transfer sections are separate physical boundaries and must not
    # cap the exhaust pipe area.
    pipe_area = min(exhaust_mesh.areas)
    boundary = None
    if parsed["external_boundary_capability"] == "OPEN_END_PLENUM_V2":
        boundary = OpenEndPlenumV2Boundary(
            p0=config["boundaries"]["atmosphere_pressure_Pa"],
            T0=config["boundaries"]["atmosphere_temperature_K"],
            Y0=config["boundaries"]["atmosphere_species_mass_fractions"]["fresh_air"] +
               config["boundaries"]["atmosphere_species_mass_fractions"]["fuel"])
    gas = IntegratedP5C(chambers[0], chambers[1], (intake, tr1, tr2), exhaust,
                        eos=eos, meshes=meshes, exhaust_mesh=exhaust_mesh,
                        exhaust_area=pipe_area, external_boundary=True,
                        geometry_callback=geometry_callback,
                        external_boundary_flux_convention="global_x",
                        external_boundary_model=boundary)
    start_scheduler = START_DEG + offset
    gas.angle = start_scheduler
    gas.core.angle = start_scheduler
    gas.geometry_callback = geometry_callback
    gas.core.geometry_callback = geometry_callback

    fractions = {name: _fractions(states[name]) for name in
                 ("crankcase", "cylinder", "intake", "transfer1", "transfer2", "exhaust")}
    species = {
        "crankcase": [fractions["crankcase"]],
        "cylinder": [fractions["cylinder"]],
        "intake": [fractions["intake"] for _ in range(intake_mesh.n)],
        "tr1": [fractions["transfer1"] for _ in range(transfer_meshes[0].n)],
        "tr2": [fractions["transfer2"] for _ in range(transfer_meshes[1].n)],
        "exhaust": [fractions["exhaust"] for _ in range(exhaust_mesh.n)],
    }
    system = P6IntegratedSystem(gas, component_species=species, capture_trace=True,
                                enable_p7=True, angular_rate_deg_s=6.0 * rpm)
    # The P5-C global totals and P6 species inventory start at this exact state.
    gas._initial = gas.totals()
    gas.core._initial = gas.core._totals()
    gas._previous_totals = dict(gas._initial)
    gas.core._previous_totals = dict(gas.core._initial)
    system._initial = system._species_totals()
    return system, model, offset


def _faces_speeds(path, eos):
    states = [eos.primitive(q) for q in path.conservative()]
    cell_speeds = [abs(w[1]) + eos.sound_speed(w) for w in states]
    return states, [cell_speeds[0], *[max(a, b) for a, b in zip(cell_speeds, cell_speeds[1:])], cell_speeds[-1]]


def _duct_cfl_step(mesh, states, speeds, face_areas, eos, cfl):
    """P2's cell CFL with the actual effective area at each coupled face."""
    if len(face_areas) != mesh.n + 1:
        raise ValueError("one effective face area is required per mesh face")
    limits = []
    for i, (state, volume, width) in enumerate(zip(states, mesh.volumes, mesh.widths)):
        area_speed = (face_areas[i] * speeds[i] +
                      face_areas[i + 1] * speeds[i + 1])
        if area_speed <= 0.0:
            raise ValueError("nonpositive finite-volume face wave capacity")
        spectral = width / (abs(state[1]) + eos.sound_speed(state))
        face_capacity = 2.0 * volume / area_speed
        limits.append(cfl * min(spectral, face_capacity))
    return min(limits)


def cfl_limit(system, cfl):
    gas, eos = system.gas, system.gas.eos
    limits = []
    paths = (gas.core.intake, *gas.core.transfers, gas.exhaust)
    path_states = []
    for path in paths:
        states, speeds = _faces_speeds(path, eos)
        path_states.append((states, speeds))

    # The product's duct-only CFL controls internal faces.  P5-C also couples
    # large, angle-dependent port areas directly to endpoint cells. Bound those
    # same resolved Riemann interfaces in the harness timestep; otherwise a
    # port area much larger than a duct cross-section can inject an unstable
    # amount of mass into its first/last cell while every internal-face CFL
    # remains below the requested value.
    geometry = gas.geometry_callback(float(gas.angle))
    areas = geometry["areas"] if isinstance(geometry, dict) else geometry[2]
    cc = gas.core.crankcase.primitive
    cy = gas.core.cylinder.primitive
    cc_inventory = gas.core.crankcase.inventory(eos)
    cc_state = ChamberState(cc_inventory[0], cc_inventory[2], cc_inventory[1],
                            gas.core.crankcase.volume)
    cy_inventory = gas.core.cylinder.inventory(eos)
    cy_state = ChamberState(cy_inventory[0], cy_inventory[2], cy_inventory[1],
                            gas.core.cylinder.volume)
    # Normal follows P5-B's existing interface convention. Returned wave
    # speeds are those from the actual product HLLC interface solve.
    interface_speed = {}
    intake_states = path_states[0][0]
    if float(areas[0]) > 0.0:
        interface_speed[(0, "right")] = max(abs(x) for x in interface_exchange(
            cc_state, intake_states[-1], float(areas[0]), 1, eos=eos)["wave_speeds"])
    for path_index, area_index in ((1, 1), (2, 2)):
        states = path_states[path_index][0]
        if float(areas[area_index]) > 0.0:
            interface_speed[(path_index, "left")] = max(abs(x) for x in interface_exchange(
                cc_state, states[0], float(areas[area_index]), -1, eos=eos)["wave_speeds"])
            interface_speed[(path_index, "right")] = max(abs(x) for x in interface_exchange(
                cy_state, states[-1], float(areas[area_index]), 1, eos=eos)["wave_speeds"])

    # P5-C's exhaust port uses its existing effective-area flux rather than
    # interface_exchange. Its local acoustic bound keeps that product flux
    # represented at the duct endpoint without changing its flux law.
    exhaust_states = path_states[3][0]
    interface_speed[(3, "left")] = max(abs(w[1]) + eos.sound_speed(w)
                                        for w in (cy, exhaust_states[0]))

    face_areas = [list(path.mesh.areas) for path in paths]
    # Replace mesh endpoint areas by the exact areas passed to the respective
    # product interfaces. The atmospheric end remains the intake mesh area.
    face_areas[0][-1] = float(areas[0])
    face_areas[1][0] = face_areas[1][-1] = float(areas[1])
    face_areas[2][0] = face_areas[2][-1] = float(areas[2])
    face_areas[3][0] = min(float(areas[3]), gas.exhaust_area)

    for path_index, (path, (states, speeds)) in enumerate(zip(paths, path_states)):
        boundary_speeds = list(speeds)
        for side in ("left", "right"):
            value = interface_speed.get((path_index, side))
            if value is not None:
                boundary_speeds[0 if side == "left" else -1] = max(
                    boundary_speeds[0 if side == "left" else -1], value)
        if path_index == 0:
            # The intake's left reservoir is an external P5-C boundary.
            boundary = (gas.external_boundary_model or
                        Boundary("reservoir", p0=101325.0, T0=300.0, Y0=0.0))
            _, reservoir_speeds, _ = boundary.flux(states[0], -1, eos)
            boundary_speeds[0] = max(boundary_speeds[0],
                                     *(abs(x) for x in reservoir_speeds))
        elif path_index == 3 and gas.external_boundary_model is not None:
            _, external_speeds, _ = gas.external_boundary_model.flux(states[-1], 1, eos)
            boundary_speeds[-1] = max(boundary_speeds[-1],
                                      *(abs(x) for x in external_speeds))
        dt = _duct_cfl_step(path.mesh, states, boundary_speeds,
                            face_areas[path_index], eos, cfl)
        limits.append(dt)
    return min(limits)


def event_cuts(model, offset, phase):
    physical = {float(x) for x in model.events}
    physical.update((float(phase), float(phase + 40.0)))
    cuts = {START_DEG + offset, END_DEG + offset, 350.0, 390.0}
    for value in physical:
        for lifted in (value - 360.0, value, value + 360.0):
            if START_DEG < lifted <= END_DEG:
                cuts.add(lifted + offset)
    return tuple(sorted(x for x in cuts if START_DEG + offset <= x <= END_DEG + offset))


def advance_cycle(system, model, config, offset, cycle_index):
    """Advance exactly one 360-degree physical revolution using product CFL."""
    from .evidence import make_cycle_record
    gas = system.gas
    omega = 6.0 * float(config["operating_point"]["rpm"])
    cfl = float(config["numerics"]["cfl"])
    phase = float(config["combustion"]["physical_event_phase_deg"])
    begin, end = START_DEG + offset, END_DEG + offset
    if abs(gas.angle - begin) > 1e-9:
        raise ValueError("system is not at the preregistered cycle boundary")
    before_totals = gas.totals()
    before_external = dict(gas._external_cumulative)
    before_delivery = system.fresh_delivered
    before_short = system.fresh_short_circuit
    before_heat = system.p7_source_delta[3] * 800000.0
    before_burned = system.p7_source_delta[3]
    before_source = tuple(system.p7_source_delta)
    before_species_external = tuple(system._external)
    start_species = system._species_totals()
    start_cumulative = {"gas_external": dict(before_external),
                        "species_external": tuple(before_species_external),
                        "p7_species_source": tuple(before_source),
                        "fresh_delivery": before_delivery,
                        "fresh_short_circuit": before_short,
                        "gas_totals": dict(before_totals),
                        "species_inventory": tuple(start_species),
                        "angle_deg": gas.angle}
    start_mass = before_totals["mass"]
    start_energy = before_totals["energy"]
    cuts = event_cuts(model, offset, phase)
    next_cut = 0
    cfl_values, work, peak_pressure = [], 0.0, 0.0
    trajectory = []
    while gas.angle < end - 1e-10:
        cfl_dt = cfl_limit(system, cfl)
        while next_cut < len(cuts) and cuts[next_cut] <= gas.angle + 1e-10:
            next_cut += 1
        stop_angle = cuts[next_cut] if next_cut < len(cuts) else end
        remaining_angle = min(end - gas.angle, stop_angle - gas.angle)
        dt = min(cfl_dt, event_step(cfl_dt, remaining_angle / omega))
        if dt <= 0 or not isfinite(dt):
            raise RuntimeError("invalid CFL/event time step")
        next_angle = min(stop_angle, gas.angle + dt * omega)
        before_len = len(gas.history)
        system.step(dt, angle=next_angle)
        record = gas.history[-1]
        cfl_values.append(cfl * dt / cfl_dt)
        work -= .5 * dt * sum(record["stage_work_rates"][i][1] for i in (0, 1))
        for state in record["stage_states"]:
            q = state[1]
            peak_pressure = max(peak_pressure,
                                (system.gas.eos.gamma - 1.0) *
                                (q[2] - 0.5*q[1]*q[1]/q[0]) / q[4])
        stage_pressures = []
        for state in record["stage_states"]:
            q = state[1]
            stage_pressures.append((system.gas.eos.gamma - 1.0) *
                                   (q[2] - 0.5*q[1]*q[1]/q[0]) / q[4])
        if len(gas.history) <= before_len:
            raise RuntimeError("product P5-C did not retain accepted step")
        trajectory.append({"angle_deg": gas.angle, "dt_s": dt,
                           "achieved_cfl": cfl_values[-1],
                           "state": gas._state(),
                           "species_mass": {key: [tuple(cell) for cell in cells]
                                            for key, cells in system.species_mass.items()},
                           "gas_totals": gas.totals(),
                           "gas_external_cumulative": dict(gas._external_cumulative),
                           "species_inventory": tuple(system._species_totals()),
                           "species_external_cumulative": tuple(system._external),
                           "p7_species_source_cumulative": tuple(system.p7_source_delta),
                           "p7_heat_cumulative_J": system.p7_source_delta[3] * 800000.0,
                           "fresh_delivery_cumulative_kg": system.fresh_delivered,
                           "fresh_short_circuit_cumulative_kg": system.fresh_short_circuit,
                           "cylinder_stage_pressure_Pa": stage_pressures,
                           "work_cumulative_J": work})
    system.validate()
    gas.admissible()
    if abs(system.species_sum_error()) > 1e-12 * max(1.0, start_mass):
        raise RuntimeError("P6 species sum differs from total gas mass")
    cycle = make_cycle_record(system, cycle_index,
                              config, work, min(cfl_values), max(cfl_values),
                              start_species, start_mass, start_energy,
                              before_delivery, before_short, before_burned,
                              before_heat, before_totals, before_external,
                              before_source, before_species_external, peak_pressure)
    cycle["trajectory_terminal_state"] = cycle["terminal_state"]
    cycle["trajectory_last_state"] = trajectory[-1]["state"] if trajectory else gas._state()
    cycle["trajectory_last_species_mass"] = trajectory[-1]["species_mass"] if trajectory else system.snapshot()["species_mass"]
    cycle["cycle_start_cumulative"] = start_cumulative
    cycle["accepted_steps"] = len(trajectory)
    cycle["trajectory"] = trajectory
    terminal = gas._state()
    end_geometry = model.geometry(END_DEG)[0]
    start_geometry = model.geometry(START_DEG)[0]
    if end_geometry != start_geometry:
        raise RuntimeError("cycle rebase would change configured physical geometry")
    gas.angle = begin
    gas.core.angle = begin
    if gas._state() != terminal:
        raise RuntimeError("cycle rebase changed conservative state")
    system.p7_event = None
    system.p7_events = []
    return cycle
