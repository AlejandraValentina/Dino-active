import math

import pytest

from motorsim.expansion_chamber import (
    ChamberSection,
    ExpansionChamber,
    map_solver_state,
    reflection_timing_estimates,
)
from motorsim.gas1d.eos import IdealGas
from motorsim.gas1d.mesh import uniform_mesh
from motorsim.gas1d.solver import solve


def chamber():
    return ExpansionChamber((
        ChamberSection("header", "header", 100.0, 30.0, 30.0),
        ChamberSection("diffuser", "diffuser", 200.0, 30.0, 60.0),
        ChamberSection("belly", "belly", 100.0, 60.0, 60.0),
        ChamberSection("baffle", "baffle_cone", 100.0, 60.0, 30.0),
        ChamberSection("stinger", "stinger", 100.0, 30.0, 20.0),
        ChamberSection("silencer", "silencer", 100.0, 20.0, 20.0),
    ))


def test_expansion_geometry_sections_mesh_and_roundtrip():
    system = chamber()
    restored = ExpansionChamber.from_dict(system.to_dict())
    assert restored == system
    assert system.length_mm == pytest.approx(700.0)
    mesh = system.mesh(0.01)
    assert mesh.faces[0] == 0.0
    assert mesh.faces[-1] == pytest.approx(0.7)
    assert len(mesh.volumes) == mesh.n
    assert all(volume > 0 for volume in mesh.volumes)


def test_solver_trace_pressure_temperature_mach_mass_flow_and_waves():
    system = chamber()
    mesh = system.mesh(0.025)
    gas = IdealGas(R=287.0, gamma=1.4)
    base = (1.0, 0.0, 100_000.0, 0.0)
    current = (1.0, 1.0, 101_000.0, 0.0)
    trace = map_solver_state(mesh, (current,) * mesh.n, eos=gas,
                             base_primitives=(base,) * mesh.n)
    first = trace["cells"][0]
    sound = math.sqrt(1.4 * 101_000.0)
    assert first["pressure_wave_pa"] == 101_000.0
    assert first["temperature_K"] == pytest.approx(101_000.0 / 287.0)
    assert first["mach"] == pytest.approx(1.0 / sound)
    assert first["mass_flow_kg_s"] == pytest.approx(first["area_m2"])
    assert first["characteristic_right_m_s"] == pytest.approx(1.0 + sound)
    linear = first["linear_acoustic"]
    assert linear["right_pressure_perturbation_pa"] == pytest.approx(
        0.5 * (1000.0 + math.sqrt(140_000.0)))
    assert linear["left_pressure_perturbation_pa"] == pytest.approx(
        0.5 * (1000.0 - math.sqrt(140_000.0)))
    assert trace["right_characteristic_travel_time_s"][-1] is not None
    assert trace["left_characteristic_travel_time_s"][0] is not None


def test_reflection_station_reports_characteristic_arrival_and_return_time():
    system = chamber()
    mesh = system.mesh(0.025)
    state = (1.0, 0.0, 100_000.0, 0.0)
    trace = map_solver_state(mesh, (state,) * mesh.n)
    boundary = sum(section.length_mm for section in system.sections[:2]) / 1000
    (estimate,) = reflection_timing_estimates(mesh, trace, (boundary,))
    sound = math.sqrt(1.35 * 100_000.0)
    assert estimate["location_m"] == pytest.approx(boundary)
    assert estimate["incident_arrival_s"] == pytest.approx(boundary / sound)
    assert estimate["return_to_inlet_s"] == pytest.approx(2 * boundary / sound)


def test_left_characteristic_is_unreachable_when_flow_is_supersonic():
    system = chamber()
    mesh = system.mesh(0.05)
    trace = map_solver_state(mesh, ((1.0, 1000.0, 100_000.0, 0.0),) * mesh.n)
    assert all(value is None for value in trace["left_characteristic_travel_time_s"])
    estimate = reflection_timing_estimates(mesh, trace, (0.2,))[0]
    assert estimate["status"] == "NO_UPSTREAM_ACOUSTIC_PATH"
    assert estimate["return_to_inlet_s"] is None


@pytest.mark.parametrize("value", [True, math.nan, math.inf, 0.0])
def test_bad_section_numbers_are_rejected(value):
    section = ChamberSection("bad", "header", value, 20.0, 20.0)
    with pytest.raises(ValueError):
        section.validate()


def test_disconnected_or_unknown_sections_are_rejected():
    with pytest.raises(ValueError, match="Disconnected"):
        ExpansionChamber((ChamberSection("a", "header", 10, 10, 20),
                          ChamberSection("b", "belly", 10, 21, 21))).validate()
    with pytest.raises(ValueError):
        ChamberSection("x", "arbitrary", 10, 10, 10).validate()


def test_trace_rejects_missing_or_nonphysical_state():
    mesh = chamber().mesh(0.05)
    with pytest.raises(ValueError, match="state count"):
        map_solver_state(mesh, ())
    with pytest.raises(ValueError, match="Invalid expansion state"):
        map_solver_state(mesh, ((1.0, 0.0, -1.0, 0.0),) * mesh.n)
    with pytest.raises(ValueError):
        reflection_timing_estimates(mesh, {"cells": []}, (0.1,))


def test_actual_quasi_1d_solver_state_maps_to_expansion_outputs():
    mesh = uniform_mesh(4, length=0.4, area=0.01)
    gas = IdealGas()
    primitive = (1.2, 15.0, 120_000.0, 0.25)
    conserved = gas.conservative(primitive)
    initial = [tuple(value * volume for value in conserved) for volume in mesh.volumes]
    result = solve(mesh, initial, 1e-5, "periodic", eos=gas, cfl=0.4)
    assert result["status"] == "completed"
    states = tuple(gas.primitive(tuple(value / volume for value in cell))
                   for cell, volume in zip(result["cells"], mesh.volumes))
    trace = map_solver_state(mesh, states, eos=gas)
    assert all(row["pressure_wave_pa"] == pytest.approx(primitive[2]) for row in trace["cells"])
    assert all(row["mass_flow_kg_s"] == pytest.approx(primitive[0] * primitive[1] * 0.01)
               for row in trace["cells"])
