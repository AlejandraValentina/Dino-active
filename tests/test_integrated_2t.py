from copy import deepcopy
from dataclasses import replace
import hashlib
import inspect
import json
import math

import pytest

from motorsim.gas1d.mesh import Mesh, uniform_mesh
from motorsim.gas1d.boundary import Boundary
from motorsim.gas1d.eos import IdealGas
from motorsim.gas1d.open_end_plenum_v2 import OpenEndPlenumV2Boundary
from motorsim.fuel_combustion import (FuelCoupledCombustionV1,
                                      FuelCoupledCombustionV2)
from motorsim.fuel_library import FuelLibrary
from motorsim.combustion import WiebeComponent
from motorsim.crankcase import CrankcaseGeometry
from motorsim.expansion_chamber import ChamberSection, ExpansionChamber
from motorsim.integrated_2t import (
    DuctPath2T, DynamicReedBinding2T, EngineGeometry2T, IntegratedEngine2T, IntegratedIntakePlenum2T,
    IntegratedNetworkVolume2T,
    IntegratedPortBinding2T,
    SliderCrankChambers2T, audit_integrated_cycle_primary, make_integrated_cycle_primary,
    make_integrated_engineering_output, make_integrated_engineering_output_v4,
    _fresh_air_fuel_species_ratio, _duct_ids_by_role, _role_face_outputs,
    _specific_consumption_value, _gross_fresh_short_circuit_rate,
    _evidence_sha256, _angle_increment_matches,
)
from motorsim.engineering_outputs import (validate_integrated_engineering_output_v3,
                                          validate_integrated_engineering_output_v4,
                                          validate_integrated_engineering_output_v5)
from motorsim.reference_harness.convergence import PeriodicDetector, compare_cycles
from motorsim.kinematics import piston_position
from motorsim.p6_species import SPECIES
from motorsim.powervalve import PowerValve
from motorsim.reed import ReedPetal
from motorsim.reed import ReedState
from motorsim.reed_coupling import HingedFlapGeometryV1
from motorsim.thermal import ThermalSurface, ThermalSystem
from motorsim.two_stroke_ports import AreaKnot, DuctBinding, PortDefinition, TwoStrokePortSet
from motorsim.mechanical import LossTerm, MechanicalLossModel
from motorsim.network_components import NetworkConnection, VolumeGasState, VolumeNode


@pytest.mark.parametrize("fuel, duration, power", [
    (0.0, 1.0, 1000.0), (1e-6, 0.0, 1000.0), (1e-6, 1.0, 0.0),
])
def test_specific_fuel_consumption_is_undefined_without_positive_fuel_time_and_power(
        fuel, duration, power):
    assert _specific_consumption_value(fuel, duration, power) is None


def test_specific_fuel_consumption_uses_positive_p7_consumed_mass():
    assert _specific_consumption_value(0.01, 2.0, 1000.0) == pytest.approx(
        0.01 / 2.0 * 3.6e9 / 1000.0)


def test_reverse_exhaust_and_closed_paths_do_not_count_as_short_circuit():
    assert _gross_fresh_short_circuit_rate(1e-5, (1e-5, 0.0), (-2e-5, 0.0, 0.0, 0.0)) == 0.0
    assert _gross_fresh_short_circuit_rate(0.0, (1e-5,), (2e-5, 0.0, 0.0, 0.0)) == 0.0
    assert _gross_fresh_short_circuit_rate(1e-5, (0.0,), (2e-5, 0.0, 0.0, 0.0)) == 0.0
    assert _gross_fresh_short_circuit_rate(
        1e-5, (1e-5,), (2e-5, 1e-5, 0.0, 0.0)) == pytest.approx(3e-5)


def _case(*, crankcase_pressure=130000.0, cylinder_pressure=101325.0,
          exhaust_area=0.0, thermal_system=None, thermal_locations=None,
          geometry=None, max_cfl=0.4, duct_pressure=101325.0,
          reed_petals=(), intake_area=0.0, transfer_pressure=101325.0,
          transfer_area=1e-5, duct_length=.02, exhaust_mesh=None,
          port_binding=None, reference_rpm=1000.0, geometry_identity=None,
          duct_species=None, slider_crank=None,
          combustion_start_angle_deg=None, cylinder_species=None,
          intake_plenum=None, network_volumes=(), dynamic_reed_binding=None,
          fuel_coupled_combustion=None):
    def duct_mesh(duct_id):
        if duct_id == "exhaust" and exhaust_mesh is not None:
            return exhaust_mesh
        return uniform_mesh(2, duct_length, 1e-4)

    paths = (
        DuctPath2T("intake", duct_mesh("intake"), "intake"),
        DuctPath2T("primary", duct_mesh("primary"), "transfer"),
        DuctPath2T("secondary", duct_mesh("secondary"), "transfer"),
        DuctPath2T("boost", duct_mesh("boost"), "transfer"),
        DuctPath2T("exhaust", duct_mesh("exhaust"), "exhaust"),
    )

    if geometry is None:
        def geometry(angle):
            return EngineGeometry2T(.00015, .00018, 0.0, 0.0, intake_area,
                                    (transfer_area, transfer_area, transfer_area), exhaust_area)

    states = {path.id: ((1.1768, 0.0,
                         transfer_pressure if path.role == "transfer" else duct_pressure,
                         1.0),) * len(path.mesh.volumes) for path in paths}
    component_species = {
        "crankcase": (0.0, 0.0, 0.00017652, 0.0),
        "cylinder": (0.000211824, 0.0, 0.0, 0.0),
    }
    if slider_crank is not None:
        crankcase_volume, cylinder_volume, _, _ = slider_crank.resolve(
            0.0, reference_rpm)
        component_species["crankcase"] = (
            0.0, 0.0, 1.1768 * crankcase_volume, 0.0)
        component_species["cylinder"] = (
            1.1768 * cylinder_volume, 0.0, 0.0, 0.0)
    if cylinder_species is not None:
        component_species["cylinder"] = tuple(cylinder_species)
    for path in paths:
        if path.role == "transfer":
            component_species[path.id] = tuple(
                (1.1768 * volume, 0.0, 0.0, 0.0) for volume in path.mesh.volumes)
    component_species.update(duct_species or {})
    if dynamic_reed_binding is not None:
        cc_volume = (.00015 - dynamic_reed_binding.geometry.swept_volume_area_m2 *
                     dynamic_reed_binding.initial_state.position_m)
        component_species["crankcase"] = (0.0, 0.0, 1.1768 * cc_volume, 0.0)
    return IntegratedEngine2T(
        (1.1768, 0.0, crankcase_pressure, 1.0),
        (1.1768, 0.0, cylinder_pressure, 1.0),
        paths, states, geometry, species=component_species,
        inlet_boundary=Boundary("nonreflecting", state=(1.1768, 0.0, 101325.0, 1.0)),
        outlet_boundary=Boundary("nonreflecting", state=(1.1768, 0.0, 101325.0, 1.0)),
        geometry_identity=(geometry_identity or
                           {"fixture": "three-transfer-static-volume-v1"}),
        reed_petals=reed_petals,
        dynamic_reed_binding=dynamic_reed_binding,
        port_binding=port_binding, intake_plenum=intake_plenum,
        network_volumes=network_volumes,
        slider_crank=slider_crank,
        reference_rpm=reference_rpm,
        thermal_system=thermal_system, thermal_locations=thermal_locations,
        combustion_start_angle_deg=(None if fuel_coupled_combustion is not None else
                                    combustion_start_angle_deg),
        fuel_coupled_combustion=fuel_coupled_combustion,
        max_cfl=max_cfl)


def test_dynamic_reed_binds_to_integrated_intake_stage_volumes_and_restart():
    intake_mesh = uniform_mesh(2, .02, 1e-4)
    petal = ReedPetal("synthetic-integrated", .001, .0001, .01,
                      10.0, .01, .002, .8, "SYNTHETIC_ASSUMPTION")
    geometry = HingedFlapGeometryV1(
        "synthetic-integrated", "1", "SYNTHETIC_ASSUMPTION", .01, .02,
        intake_mesh.volumes[-1], .00015, .002, .8)
    binding = DynamicReedBinding2T(
        "intake", geometry, petal, ReedState(.001, 0.0))
    system = _case(
        crankcase_pressure=101325.0, cylinder_pressure=101325.0,
        duct_pressure=101325.0, intake_area=1e-5, transfer_area=0.0,
        exhaust_area=0.0, dynamic_reed_binding=binding)
    initial = system.inventory()
    initial_q = system.state["ducts"]["intake"][-1]
    start_lift = system.state["dynamic_reed"]["position_m"]

    trace = system.step(1e-7, .0006)

    assert trace["stage_states"][0]["dynamic_reed"]["position_m"] == start_lift
    assert len(trace["stage_dynamic_reed_rhs"]) == 2
    assert trace["stage_states"][1]["dynamic_reed"]["velocity_m_s"] < 0.0
    assert system.state["dynamic_reed"]["position_m"] < start_lift
    endpoint_volume = system._duct_cell_volume(
        next(path for path in system.ducts if path.id == "intake"), 1, system.state)
    assert endpoint_volume == pytest.approx(
        intake_mesh.volumes[-1] + geometry.swept_volume_area_m2 *
        system.state["dynamic_reed"]["position_m"])
    assert system.state["ducts"]["intake"][-1][0] == pytest.approx(initial_q[0])
    assert system.ledger["reed_dissipation_J"] >= 0.0
    assert system.inventory()["energy_J"] == pytest.approx(
        initial["energy_J"], rel=0.0, abs=2e-11)
    assert abs(system.conservation_report()["energy"]["residual"]) < 2e-11

    restored = _case(
        crankcase_pressure=101325.0, cylinder_pressure=101325.0,
        duct_pressure=101325.0, intake_area=1e-5, transfer_area=0.0,
        exhaust_area=0.0, dynamic_reed_binding=binding)
    restored.restore(system.snapshot())
    assert restored.snapshot() == system.snapshot()


def test_dynamic_reed_integrated_configuration_roundtrip_is_versioned():
    system = _internal_cycle_fixture(with_reed=False)
    intake = next(path for path in system.ducts if path.role == "intake")
    cc_volume = system._geometry(0.0, system.reference_rpm).crankcase_volume_m3
    petal = ReedPetal("synthetic-config", .001, .0001, .01,
                      10.0, .01, .002, .8, "SYNTHETIC_ASSUMPTION")
    geometry = HingedFlapGeometryV1(
        "synthetic-config", "1", "SYNTHETIC_ASSUMPTION", .01, .02,
        intake.mesh.volumes[-1], cc_volume, .002, .8)
    binding = DynamicReedBinding2T(
        intake.id, geometry, petal, ReedState(0.0, 0.0))
    config = system.configuration_dict()
    config["schema"] = "MOTORSIM_INTEGRATED_ENGINE_2T_CONFIG_V3"
    config["dynamic_reed_binding"] = binding.to_dict()

    rebuilt = IntegratedEngine2T.from_configuration_dict(config)

    assert rebuilt.configuration_schema == "MOTORSIM_INTEGRATED_ENGINE_2T_CONFIG_V3"
    assert rebuilt.configuration_dict() == config
    assert rebuilt.snapshot()["schema"] == "MOTORSIM_INTEGRATED_ENGINE_2T_STATE_V8"
    assert rebuilt.state["dynamic_reed"] == {
        "position_m": 0.0, "velocity_m_s": 0.0, "dissipation_J": 0.0}


@pytest.mark.parametrize(("crankcase_pressure", "direction", "donor"), [
    (90000.0, 1.0, "duct"), (120000.0, -1.0, "crankcase")])
def test_dynamic_reed_integrated_face_uses_actual_signed_species_donor(
        crankcase_pressure, direction, donor):
    intake_mesh = uniform_mesh(2, .02, 1e-4)
    petal = ReedPetal("synthetic-donor", .001, .0001, .01,
                      10.0, .01, .002, .8, "SYNTHETIC_ASSUMPTION")
    geometry = HingedFlapGeometryV1(
        "synthetic-donor", "1", "SYNTHETIC_ASSUMPTION", .01, .02,
        intake_mesh.volumes[-1], .00015, .002, .8)
    binding = DynamicReedBinding2T(
        "intake", geometry, petal, ReedState(.001, 0.0))
    duct_volumes = (*intake_mesh.volumes[:-1],
                    intake_mesh.volumes[-1] + geometry.swept_volume_area_m2 *
                    binding.initial_state.position_m)
    duct_cells = tuple((.8 * 1.1768 * volume, .2 * 1.1768 * volume,
                        0.0, 0.0) for volume in duct_volumes)
    system = _case(
        crankcase_pressure=crankcase_pressure, cylinder_pressure=101325.0,
        duct_pressure=101325.0, intake_area=1e-5, transfer_area=0.0,
        exhaust_area=0.0, duct_species={"intake": duct_cells},
        dynamic_reed_binding=binding)

    trace = system.step(1e-10, .0000006)
    signed_flux = trace["stage_face_fluxes"][0]["intake"]["right"]
    signed_species = trace["stage_face_fluxes"][0]["intake"]["right_species"]
    assert signed_flux[0] * direction > 0.0
    assert sum(signed_species) * direction > 0.0
    donor_mass = (system.state["species"]["ducts"]["intake"][-1]
                  if donor == "duct" else
                  system.state["species"]["chambers"]["crankcase"])
    total_donor_mass = sum(donor_mass)
    total_species_flux = sum(signed_species)
    assert tuple(value / total_species_flux for value in signed_species) == pytest.approx(
        tuple(value / total_donor_mass for value in donor_mass))
    report = system.conservation_report()
    assert abs(report["mass"]["residual"]) < 1e-14
    assert abs(report["energy"]["residual"]) < 1e-11
    assert all(abs(value["residual"]) < 1e-14
               for value in report["species"].values())


def test_dynamic_reed_out_of_domain_stage_rejects_without_mutating_engine_state():
    intake_mesh = uniform_mesh(2, .02, 1e-4)
    petal = ReedPetal("synthetic-reject", .001, .0001, .01,
                      10.0, .01, .002, .8, "SYNTHETIC_ASSUMPTION")
    geometry = HingedFlapGeometryV1(
        "synthetic-reject", "1", "SYNTHETIC_ASSUMPTION", .01, .02,
        intake_mesh.volumes[-1], .00015, .002, .8)
    binding = DynamicReedBinding2T(
        "intake", geometry, petal, ReedState(.0019, 100.0))
    system = _case(
        crankcase_pressure=101325.0, cylinder_pressure=101325.0,
        duct_pressure=101325.0, intake_area=1e-5, transfer_area=0.0,
        exhaust_area=0.0, dynamic_reed_binding=binding)
    before_state = deepcopy(system.state)
    before_ledger = deepcopy(system.ledger)
    before_trace = deepcopy(system.trace)
    before_clock = (system.time_s, system.crank_angle_unwrapped_deg,
                    system.accepted_steps, system.rejected_steps)

    with pytest.raises(ValueError, match="dynamic reed state is inadmissible"):
        system.step(1e-5, .06)

    assert system.state == before_state
    assert system.ledger == before_ledger
    assert system.trace == before_trace
    assert (system.time_s, system.crank_angle_unwrapped_deg,
            system.accepted_steps, system.rejected_steps) == before_clock


def test_dynamic_reed_stop_contact_requires_versioned_event_model():
    intake_mesh = uniform_mesh(2, .02, 1e-4)
    petal = ReedPetal("synthetic-stop-contact", .001, .0001, .01,
                      10.0, .01, .002, .8, "SYNTHETIC_ASSUMPTION")
    geometry = HingedFlapGeometryV1(
        "synthetic-stop-contact", "1", "SYNTHETIC_ASSUMPTION", .01, .02,
        intake_mesh.volumes[-1], .00015, .002, .8)
    binding = DynamicReedBinding2T(
        "intake", geometry, petal, ReedState(0.0, 0.0))
    system = _case(
        crankcase_pressure=120000.0, cylinder_pressure=101325.0,
        duct_pressure=101325.0, intake_area=1e-5, transfer_area=0.0,
        exhaust_area=0.0, dynamic_reed_binding=binding)
    before_state = deepcopy(system.state)
    before_ledger = deepcopy(system.ledger)

    with pytest.raises(ValueError, match="versioned event contract"):
        system.step(1e-10, .0000006)

    assert system.state == before_state
    assert system.ledger == before_ledger


def test_dynamic_reed_full_engine_cycle_rebuilds_primary_and_v4_collector():
    system = _internal_cycle_fixture(
        with_reed=False, dynamic_reed=True,
        fixture_name="dynamic-reed-integrated-synthetic-v1")
    start = deepcopy(system.snapshot())

    _advance_cycle_fixture(system, 360.0)

    end = deepcopy(system.snapshot())
    primary = make_integrated_cycle_primary(system, start, end, 1)
    assert primary["dynamic_reed_binding"]["geometry"]["provenance"] == (
        "SYNTHETIC_ASSUMPTION")
    assert len(primary["duct_cell_volumes_m3"]["intake"]) == 2
    assert abs(primary["conservation"]["energy_residual_J"]) < 1e-6
    output = make_integrated_engineering_output_v4(
        primary, displacement_m3=system.slider_crank.crankcase.displacement_m3)
    validate_integrated_engineering_output_v4(output)
    channels = output["crank_angle_trace"]["channels"]
    for suffix in ("position_m", "velocity_m_s", "mechanical_energy_j", "dissipation_j"):
        key = f"reed:integrated-dynamic-petal:{suffix}"
        assert key in channels
        assert len(channels[key]["values"]) == len(output["crank_angle_trace"]["angle_deg"])


def test_integrated_topology_resolves_three_transfer_routes_and_ledgers():
    system = _case()
    before = system.inventory()
    record = system.step(1e-8, .01)
    report = system.conservation_report()

    assert set(record["stage_face_fluxes"][0]) == {
        "intake", "primary", "secondary", "boost", "exhaust"}
    assert len(record["stage_geometry"]) == 2
    assert all(abs(report["species"][name]["residual"]) < 1e-15 for name in SPECIES)
    assert abs(report["mass"]["residual"]) < 1e-15
    assert abs(report["energy"]["residual"]) < 1e-10
    # Pressure drives the crankcase donor through the generic transfer routes.
    assert system.state["species"]["chambers"]["crankcase"][2] < before["species_kg"][2]
    assert all(sum(values) == pytest.approx(
        system.state["ducts"][path_id][i][0] * path.mesh.volumes[i], abs=1e-14)
        for path in system.transfers for path_id in (path.id,)
        for i, values in enumerate(system.state["species"]["ducts"][path_id]))


@pytest.mark.parametrize("opening_fraction", (0.0, 0.5, 1.0))
def test_uniform_static_gas_remains_at_rest_at_closed_partial_and_full_ports(
        opening_fraction):
    mesh_area = 1e-4
    opening = opening_fraction * mesh_area

    def geometry(_angle):
        return EngineGeometry2T(
            .00015, .00018, 0.0, 0.0, opening,
            (opening, opening, opening), opening)

    system = _case(
        crankcase_pressure=101325.0, cylinder_pressure=101325.0,
        duct_pressure=101325.0, transfer_pressure=101325.0,
        geometry=geometry)
    assembled = system._assemble(system.state, 0.0, 1000.0)

    for path in system.ducts:
        assert all(cell_rhs[1] == pytest.approx(0.0, abs=1e-10)
                   for cell_rhs in assembled["q"]["ducts"][path.id])
        faces = assembled["faces"][path.id]
        expected_wall_traction = 101325.0 * mesh_area
        if path.role == "intake":
            assert faces["right"][1] == pytest.approx(expected_wall_traction)
        elif path.role == "transfer":
            assert faces["left"][1] == pytest.approx(expected_wall_traction)
            assert faces["right"][1] == pytest.approx(expected_wall_traction)
        else:
            assert faces["left"][1] == pytest.approx(expected_wall_traction)


def test_internal_cycle_fixture_starts_at_atmospheric_pressure_and_temperature():
    system = _internal_cycle_fixture()
    for name, (mass, energy, volume) in system.state["chambers"].items():
        pressure = (system.eos.gamma - 1.0) * energy / volume
        temperature = pressure / ((mass / volume) * system.eos.R)
        assert pressure == pytest.approx(101325.0)
        assert temperature == pytest.approx(300.0, abs=0.01)


def test_exhaust_backflow_uses_fresh_air_not_the_intake_reservoir_mixture():
    system = _internal_cycle_fixture()
    assert system.atmosphere_species == pytest.approx((.98, .02, 0.0, 0.0))
    assert system.outlet_species == (1.0, 0.0, 0.0, 0.0)
    external = Boundary(
        "fixed", state=(150000.0 / (system.eos.R * 300.0),
                        0.0, 150000.0, 1.0))

    face, species_flux, _, _ = system._external_face(
        system.state, system.exhaust, "right", external)

    assert face[0] < 0.0
    assert species_flux == pytest.approx((face[0], 0.0, 0.0, 0.0))


def test_species_roundoff_keeps_extensive_values_without_eos_y_overshoot():
    system = _case()
    state = deepcopy(system.state)
    mass = state["chambers"]["crankcase"][0]
    slightly_over = (mass + 5e-16, 0.0, 0.0, 0.0)
    state["species"]["chambers"]["crankcase"] = slightly_over

    system._validate(state)

    assert state["species"]["chambers"]["crankcase"] == slightly_over
    fractions = system._fractions(slightly_over, mass)
    assert fractions == (1.0, 0.0, 0.0, 0.0)
    assert sum(slightly_over) != mass


def test_integrated_engine_checkpoint_restart_replays_identically():
    continuous = _case()
    continuous.step(1e-8, .01)
    checkpoint = continuous.snapshot()
    split = _case()
    split.restore(deepcopy(checkpoint))

    continuous.step(1e-8, .01)
    split.step(1e-8, .01)
    assert continuous.inventory() == split.inventory()
    assert continuous.conservation_report() == split.conservation_report()
    assert continuous.state == split.state
    json_checkpoint = json.loads(json.dumps(continuous.snapshot()))
    restored = _case()
    restored.restore(json_checkpoint)
    assert json.dumps(restored.state, sort_keys=True) == json.dumps(
        continuous.state, sort_keys=True)
    assert restored.conservation_report() == continuous.conservation_report()


def _intake_plenum(*, pressure=150000.0, fractions=(0.0, 0.5, 0.5, 0.0)):
    eos = IdealGas()
    volume = 0.001
    temperature = 300.0
    mass = pressure * volume / (eos.R * temperature)
    state = VolumeGasState(
        mass, pressure * volume / (eos.gamma - 1.0),
        tuple(mass * fraction for fraction in fractions))
    return IntegratedIntakePlenum2T(
        VolumeNode("intake-plenum", "plenum", volume, "SYNTHETIC_ASSUMPTION"),
        NetworkConnection("plenum-intake-neck", "intake-plenum", "intake",
                          1e-5, 0.05, "SYNTHETIC_ASSUMPTION"), state)


@pytest.mark.parametrize(("plenum_pressure", "duct_pressure", "plenum_fractions",
                          "duct_fractions", "expected_donor"), [
    (150000.0, 101325.0, (0.0, 0.5, 0.5, 0.0),
     (1.0, 0.0, 0.0, 0.0), "plenum"),
    (100000.0, 150000.0, (1.0, 0.0, 0.0, 0.0),
     (0.0, 0.0, 0.0, 1.0), "duct"),
])
def test_integrated_finite_intake_plenum_uses_real_donor_and_global_ledgers(
        plenum_pressure, duct_pressure, plenum_fractions, duct_fractions,
        expected_donor):
    intake_mesh_mass = 1.1768 * 1e-4 * .01
    duct_species = {"intake": tuple(
        tuple(intake_mesh_mass * fraction for fraction in duct_fractions)
        for _ in range(2))}
    system = _case(
        duct_pressure=duct_pressure,
        intake_plenum=_intake_plenum(pressure=plenum_pressure,
                                     fractions=plenum_fractions),
        duct_species=duct_species)
    path = system.intake
    def intake_subsystem():
        node = system.intake_plenum.node.id
        node_q = system.state["network_volumes"][node]
        mass = node_q[0]
        energy = node_q[1]
        species = list(system.state["species"]["network_volumes"][node])
        for q, comp, volume in zip(system.state["ducts"][path.id],
                                   system.state["species"]["ducts"][path.id],
                                   path.mesh.volumes):
            mass += q[0] * volume
            energy += q[2] * volume
            for index, value in enumerate(comp):
                species[index] += value
        return mass, energy, tuple(species)
    before_intake = intake_subsystem()
    record = system.step(1e-9, .001)
    first_stage = record["stage_network_exchanges"][0]["intake-plenum"]
    mass_rate = first_stage["mass_into_volume_kg_s"]
    assert mass_rate != 0.0
    donor_fraction = (first_stage["species_into_volume_kg_s"][1] / mass_rate
                      if expected_donor == "plenum" else
                      first_stage["species_into_volume_kg_s"][3] / mass_rate)
    assert donor_fraction == pytest.approx(0.5 if expected_donor == "plenum" else 1.0)
    after_intake = intake_subsystem()
    assert after_intake[0] == pytest.approx(before_intake[0], abs=1e-14)
    assert after_intake[1] == pytest.approx(before_intake[1], abs=1e-10)
    assert after_intake[2] == pytest.approx(before_intake[2], abs=1e-14)
    report = system.conservation_report()
    assert abs(report["mass"]["residual"]) < 1e-14
    assert abs(report["energy"]["residual"]) < 1e-10
    assert all(abs(item["residual"]) < 1e-14
               for item in report["species"].values())


def test_integrated_intake_plenum_is_checkpointed_and_replays_as_one_state():
    binding = _intake_plenum()
    continuous = _case(intake_plenum=binding)
    continuous.step(1e-9, .001)
    checkpoint = json.loads(json.dumps(continuous.snapshot()))
    restored = _case(intake_plenum=binding)
    restored.restore(checkpoint)
    continuous.step(1e-9, .001)
    restored.step(1e-9, .001)
    assert restored.state == continuous.state
    assert restored.inventory() == continuous.inventory()
    assert restored.conservation_report() == continuous.conservation_report()
    mismatch = _case(intake_plenum=_intake_plenum(pressure=149000.0))
    with pytest.raises(ValueError, match="configuration mismatch"):
        mismatch.restore(checkpoint)


def test_integrated_intake_plenum_uses_both_ssprk_stages_for_volume_update():
    binding = _intake_plenum(pressure=150000.0)
    system = _case(intake_plenum=binding)
    node_id = binding.node.id
    initial_mass, initial_energy, _ = system.state["network_volumes"][node_id]
    initial_species = system.state["species"]["network_volumes"][node_id]
    dt = 1e-9

    record = system.step(dt, .001)
    exchanges = record["stage_network_exchanges"]
    assert len(exchanges) == 2
    first, second = (exchange[node_id] for exchange in exchanges)
    assert first["mass_into_volume_kg_s"] != second["mass_into_volume_kg_s"]

    final_mass, final_energy, _ = system.state["network_volumes"][node_id]
    final_species = system.state["species"]["network_volumes"][node_id]
    assert final_mass == pytest.approx(
        initial_mass + .5 * dt * (first["mass_into_volume_kg_s"] +
                                   second["mass_into_volume_kg_s"]), abs=1e-16)
    assert final_energy == pytest.approx(
        initial_energy + .5 * dt * (first["energy_into_volume_w"] +
                                    second["energy_into_volume_w"]), abs=1e-12)
    for index in range(4):
        assert final_species[index] == pytest.approx(
            initial_species[index] + .5 * dt * (
                first["species_into_volume_kg_s"][index] +
                second["species_into_volume_kg_s"][index]), abs=1e-16)


def test_integrated_intake_plenum_outflow_participates_in_depletion_cfl():
    binding = _intake_plenum(pressure=200000.0)
    system = _case(intake_plenum=binding, duct_pressure=100000.0,
                   max_cfl=0.4)
    assembled = system._assemble(system.state, 0.0, 1000.0)
    outflow = assembled["network_outflow_kg_s"]["intake-plenum"]
    assert outflow > 0.0
    dt = system.state["network_volumes"]["intake-plenum"][0] / outflow * 0.5
    with pytest.raises(ValueError, match="CFL limit exceeded"):
        system._cfl(system.state, assembled, dt)


def test_integrated_network_volume_rejects_bad_face_orientation_and_duplicates():
    base = _intake_plenum()
    wrong_orientation = IntegratedNetworkVolume2T(
        base.node,
        NetworkConnection("reversed", "intake", base.node.id, 1e-5, .05,
                          "SYNTHETIC_ASSUMPTION"),
        "intake", "left", base.initial_state)
    with pytest.raises(ValueError, match="orientation"):
        _case(network_volumes=(wrong_orientation,))

    right_side_of_intake = IntegratedNetworkVolume2T(
        base.node, base.connection, "intake", "right", base.initial_state)
    with pytest.raises(ValueError, match="external duct endpoints"):
        _case(network_volumes=(right_side_of_intake,))

    duplicate_endpoint = IntegratedNetworkVolume2T(
        base.node,
        NetworkConnection("duplicate", base.node.id, "intake", 1e-5, .06,
                          "SYNTHETIC_ASSUMPTION"),
        "intake", "left", base.initial_state)
    valid = IntegratedNetworkVolume2T(
        base.node, base.connection, "intake", "left", base.initial_state)
    with pytest.raises(ValueError, match="ids must be unique"):
        _case(network_volumes=(valid, duplicate_endpoint))


def test_integrated_engine_rejects_incomplete_or_non_generic_topology():
    system = _case()
    with pytest.raises(ValueError, match="CONFIG_V2 supports"):
        IntegratedEngine2T(
            (1.1768, 0.0, 101325.0, 1.0), (1.1768, 0.0, 101325.0, 1.0),
            system.ducts[:4], {path.id: ((1.1768, 0.0, 101325.0, 1.0),) * 2
                               for path in system.ducts[:4]},
            system.geometry, geometry_identity={"fixture": "invalid-topology"})


def test_integrated_v2_output_roles_do_not_depend_on_duct_identifiers():
    roles = {"inlet": "intake", "tr-a": "transfer", "tr-b": "transfer",
             "tr-c": "transfer", "pipe": "exhaust"}
    assert _duct_ids_by_role(roles) == {
        "intake": ("inlet",), "transfer": ("tr-a", "tr-b", "tr-c"),
        "exhaust": ("pipe",)}
    two_route_roles = {"inlet": "intake", "tr-a": "transfer",
                       "tr-b": "transfer", "pipe": "exhaust"}
    assert _duct_ids_by_role(two_route_roles)["transfer"] == ("tr-a", "tr-b")
    assert _duct_ids_by_role({"inlet": "intake", "tr-a": "transfer",
                              "pipe": "exhaust"})["transfer"] == ("tr-a",)
    with pytest.raises(ValueError, match="CONFIG_V2 supports"):
        _duct_ids_by_role({"inlet": "intake", "pipe": "exhaust"})
    with pytest.raises(ValueError, match="CONFIG_V2 supports"):
        _duct_ids_by_role({"inlet-a": "intake", "inlet-b": "intake",
                           "tr-a": "transfer", "tr-b": "transfer",
                           "tr-c": "transfer", "pipe": "exhaust"})
    faces = {
        "inlet": {"effective_reed_area_m2": 2.0, "right": (1.0,)},
        "tr-a": {"right": (2.0,)}, "tr-b": {"right": (3.0,)},
        "tr-c": {"right": (4.0,)}, "pipe": {"left": (5.0,)},
    }
    assert _role_face_outputs(faces, _duct_ids_by_role(roles)) == {
        "intake_port_area_m2": 2.0,
        "intake_mass_flow_kg_s": 1.0,
        "transfer_mass_flow_kg_s": 9.0,
        "exhaust_mass_flow_kg_s": 5.0,
    }


def test_integrated_engine_enforces_cfl_without_accepting_partial_state():
    system = _case()
    original = deepcopy(system.snapshot())
    with pytest.raises(ValueError, match="CFL limit exceeded"):
        system.step(1e-4, .01)
    assert json.dumps(system.state, sort_keys=True) == json.dumps(
        original["state"], sort_keys=True)
    assert system.accepted_steps == 0
    assert system.rejected_steps == 1


def test_integrated_cfl_also_bounds_zero_dimensional_chamber_depletion():
    system = _case(crankcase_pressure=1e7, max_cfl=0.1)
    original = deepcopy(system.snapshot())
    with pytest.raises(ValueError, match="CFL limit exceeded"):
        system.step(6e-7, .01)
    assert json.dumps(system.state, sort_keys=True) == json.dumps(
        original["state"], sort_keys=True)
    assert system.accepted_steps == 0


def test_integrated_chamber_cfl_uses_gross_turnover_not_net_mass_rate():
    petal = ReedPetal("intake-petal", .001, 1e-4, .01, 10.0, .01,
                      .002, .8, "SYNTHETIC_ASSUMPTION")
    system = _case(crankcase_pressure=130000.0, duct_pressure=150000.0,
                   intake_area=1e-5, transfer_pressure=101325.0,
                   reed_petals=(petal,), transfer_area=1e-6,
                   duct_length=3000.0, max_cfl=0.6)
    assembled = system._assemble(system.state, 0.0, 1000.0)
    net_rate = assembled["q"]["chambers"]["crankcase"][0]
    gross_outflow = assembled["chamber_outflow_kg_s"]["crankcase"]
    assert net_rate > 0.0  # inlet dominates, but transfer outflow is simultaneous
    assert gross_outflow > 0.0
    dt = system.state["chambers"]["crankcase"][0] / gross_outflow * 0.5
    cfl = system._cfl(system.state, assembled, dt)
    assert cfl >= 0.5
    assert dt * max(0.0, -net_rate) / system.state["chambers"]["crankcase"][0] == 0.0


@pytest.mark.parametrize("field, message", [
    ("angle", "wrapped/unwrapped angle mismatch"),
    ("volume", "cylinder geometry mismatch"),
])
def test_integrated_checkpoint_rejects_inconsistent_clock_or_geometry_atomically(
        field, message):
    source = _case()
    source.step(1e-8, .01)
    snapshot = deepcopy(source.snapshot())
    if field == "angle":
        snapshot["angle_deg"] = 1.0
    else:
        chamber = snapshot["state"]["chambers"]["cylinder"]
        snapshot["state"]["chambers"]["cylinder"] = (*chamber[:2], .00019)
    target = _case()
    before = deepcopy(target.snapshot())
    with pytest.raises(ValueError, match=message):
        target.restore(snapshot)
    assert target.snapshot() == before


def test_integrated_checkpoint_rejects_geometry_callback_mismatch():
    source = _case()
    source.step(1e-8, .01)

    def different_geometry(angle):
        return EngineGeometry2T(.00015, .00018 if angle == 0 else .00019, 0.0, 0.0, 0.0,
                                (1e-5, 1e-5, 1e-5), 0.0)

    target = _case(geometry=different_geometry)
    with pytest.raises(ValueError, match="cylinder geometry mismatch"):
        target.restore(source.snapshot())


def test_integrated_checkpoint_restore_rejects_corrupt_trace_geometry_atomically():
    source = _case()
    source.step(1e-8, .01)
    corrupted = deepcopy(source.snapshot())
    corrupted["trace"][0]["stage_geometry"][0]["exhaust_area_m2"] = 1e-5
    target = _case()
    before = deepcopy(target.snapshot())
    with pytest.raises(ValueError, match="trace geometry mismatch"):
        target.restore(corrupted)
    assert target.snapshot() == before


def test_callback_volume_rates_match_independent_angular_derivative():
    from math import cos, pi, sin

    amplitude = 2e-5

    def geometry(angle):
        radians = angle * pi / 180.0
        cc_rate = amplitude * sin(radians) * pi / 180.0 * 6.0 * 3000.0
        return EngineGeometry2T(
            .00015 + amplitude * (1.0 - cos(radians)),
            .00018 - amplitude * (1.0 - cos(radians)),
            cc_rate, -cc_rate,
            1e-5, (1e-5, 1e-5, 1e-5), 1e-5)

    system = _case(geometry=geometry)
    angle, rpm, h = 71.0, 3000.0, 1e-4
    current = system._geometry(angle, rpm)
    before, after = system._geometry(angle - h, rpm), system._geometry(angle + h, rpm)
    radians_per_second = 6.0 * rpm
    for volume_name, rate_name in (
            ("crankcase_volume_m3", "crankcase_volume_rate_m3_s"),
            ("cylinder_volume_m3", "cylinder_volume_rate_m3_s")):
        finite_difference = (
            getattr(after, volume_name) - getattr(before, volume_name)
        ) / (2.0 * h) * radians_per_second
        assert getattr(current, rate_name) == pytest.approx(
            finite_difference, rel=1e-8, abs=1e-12)


def test_existing_crankcase_v2_drives_both_chamber_volumes_in_integrated_stages():
    crankcase = CrankcaseGeometry(56.0, 50.0, 100.0, 20.0,
                                  "SYNTHETIC_ASSUMPTION")
    model = SliderCrankChambers2T(crankcase, 8.0)
    geometry = model.resolve(90.0, 3000.0)
    assert geometry[0] == pytest.approx(crankcase.volume_m3(90.0))
    assert geometry[1] == pytest.approx(
        crankcase.displacement_m3 / 7.0 +
        crankcase.displacement_m3 * piston_position(50.0, 100.0, 90.0) / 50.0)
    assert geometry[2] == pytest.approx(crankcase.volume_rate_m3_s(90.0, 3000.0))
    assert geometry[3] == pytest.approx(-geometry[2])

    system = _case(crankcase_pressure=101325.0, cylinder_pressure=101325.0,
                   slider_crank=model, reference_rpm=3000.0,
                   geometry_identity={"slider_crank": model.to_dict(),
                                      "fixture": "shared-2t-slider-crank-v1"})
    initial = system._geometry(0.0, 3000.0)
    initial_volumes = (system.state["chambers"]["crankcase"][2],
                       system.state["chambers"]["cylinder"][2])
    assert initial_volumes == pytest.approx((initial.crankcase_volume_m3,
                                             initial.cylinder_volume_m3))
    record = system.step(1.25e-6, 0.0225)
    expected_end = model.resolve(0.0225, 3000.0)
    assert system.state["chambers"]["crankcase"][2] == pytest.approx(expected_end[0])
    assert system.state["chambers"]["cylinder"][2] == pytest.approx(expected_end[1])
    assert record["stage_geometry"][0]["crankcase_volume_rate_m3_s"] == pytest.approx(
        model.resolve(0.0, 3000.0)[2], rel=1e-6, abs=1e-15)
    assert record["stage_geometry"][1]["crankcase_volume_rate_m3_s"] == pytest.approx(
        expected_end[2], rel=1e-6, abs=1e-15)
    assert abs(system.conservation_report()["mass"]["residual"]) < 1e-14
    assert abs(system.conservation_report()["energy"]["residual"]) < 1e-10

    mismatched = _case(crankcase_pressure=101325.0, cylinder_pressure=101325.0,
                       slider_crank=SliderCrankChambers2T(crankcase, 9.0),
                       reference_rpm=3000.0,
                       geometry_identity={"slider_crank": model.to_dict(),
                                          "fixture": "shared-2t-slider-crank-v1"})
    with pytest.raises(ValueError, match="configuration mismatch"):
        mismatched.restore(system.snapshot())


def test_integrated_backflow_uses_the_actual_duct_species_donor():
    system = _case(crankcase_pressure=90000.0)
    initial_fresh = system.state["species"]["chambers"]["crankcase"][0]
    system.step(1e-8, .01)
    final = system.state["species"]["chambers"]["crankcase"]
    assert final[0] > initial_fresh
    assert final[2] == pytest.approx(.00017652, abs=1e-15)


def test_static_reed_is_evaluated_from_each_shared_stage_pressure():
    petal = ReedPetal("intake-petal", .001, 1e-4, .01, 10.0, .01,
                      .002, .8, "SYNTHETIC_ASSUMPTION")
    closed = _case(reed_petals=(petal,), intake_area=1e-5)
    closed_record = closed.step(1e-8, .01)
    assert closed_record["stage_face_fluxes"][0]["intake"][
        "effective_reed_area_m2"] == 0.0

    open_system = _case(reed_petals=(petal,), duct_pressure=150000.0,
                        intake_area=1e-5)
    open_record = open_system.step(1e-8, .01)
    assert open_record["stage_face_fluxes"][0]["intake"][
        "effective_reed_area_m2"] > 0.0
    assert open_record["stage_face_fluxes"][0]["intake"][
        "right_species"][0] > 0.0


def test_existing_expansion_chamber_mesh_participates_in_integrated_exhaust_stages():
    chamber = ExpansionChamber((
        ChamberSection("header", "header", 80.0, 20.0, 20.0),
        ChamberSection("diffuser", "diffuser", 180.0, 20.0, 52.0),
        ChamberSection("belly", "belly", 100.0, 52.0, 52.0),
        ChamberSection("baffle", "baffle_cone", 170.0, 52.0, 16.0),
        ChamberSection("stinger", "stinger", 120.0, 16.0, 16.0),
    ))
    exhaust_mesh = chamber.mesh(.01)
    system = _case(cylinder_pressure=130000.0, exhaust_area=1e-5,
                   exhaust_mesh=exhaust_mesh)
    record = system.step(1e-8, .01)
    assert system.exhaust.mesh.as_dict() == exhaust_mesh.as_dict()
    assert len(record["stage_face_fluxes"][0]["exhaust"]["all_faces"]) == len(
        exhaust_mesh.volumes) + 1
    assert len(record["stage_face_fluxes"][1]["exhaust"]["all_species_faces"]) == len(
        exhaust_mesh.volumes) + 1
    assert abs(system.conservation_report()["mass"]["residual"]) < 1e-15
    assert abs(system.conservation_report()["energy"]["residual"]) < 1e-10


def test_generic_ports_and_powervalve_resolve_into_integrated_stage_geometry():
    ports = TwoStrokePortSet(
        56.0, 100.0,
        (DuctBinding("inlet", "intake"),
         DuctBinding("primary", "transfer"),
         DuctBinding("secondary", "transfer"),
         DuctBinding("boost", "transfer"),
         DuctBinding("exhaust", "exhaust")),
        (PortDefinition("inlet-window", "Inlet", "intake", "piston_port", "inlet",
                        "piston_port", .9, "SYNTHETIC_ASSUMPTION", top_mm=64.0,
                        height_mm=10.0, width_mm=20.0, skirt_mm=42.0),
         PortDefinition("primary-window", "Primary", "transfer", "primary", "primary",
                        "rectangular_window", .8, "SYNTHETIC_ASSUMPTION", top_mm=32.0,
                        height_mm=10.0, width_mm=20.0),
         PortDefinition("secondary-window", "Secondary", "transfer", "secondary", "secondary",
                        "rectangular_window", .8, "SYNTHETIC_ASSUMPTION", top_mm=34.0,
                        height_mm=8.0, width_mm=12.0),
         PortDefinition("boost-window", "Boost", "transfer", "boost", "boost",
                        "rectangular_window", .7, "SYNTHETIC_ASSUMPTION", top_mm=36.0,
                        height_mm=7.0, width_mm=8.0),
         PortDefinition("main-exhaust", "Main exhaust", "exhaust", "main", "exhaust",
                        "rectangular_window", .9, "SYNTHETIC_ASSUMPTION", top_mm=30.0,
                        height_mm=10.0, width_mm=20.0, roof_travel_mm=4.0),
         PortDefinition("aux-exhaust", "Aux exhaust", "exhaust", "auxiliary", "exhaust",
                        "effective_profile", .5, "SYNTHETIC_ASSUMPTION",
                        area_profile=(AreaKnot(0.0, 0.0), AreaKnot(90.0, 25.0),
                                      AreaKnot(180.0, 50.0), AreaKnot(270.0, 25.0),
                                      AreaKnot(360.0, 0.0)))))
    valve = PowerValve("pv", "main-exhaust", (1000.0, 5000.0), (0.0, 1.0),
                       "SYNTHETIC_ASSUMPTION")
    path_mapping = {"inlet": "intake", "primary": "primary", "secondary": "secondary",
                    "boost": "boost", "exhaust": "exhaust"}
    binding = IntegratedPortBinding2T(ports, path_mapping, valve)
    path_mapping["primary"] = "secondary"  # caller mutations cannot stale a live binding
    assert binding.path_by_duct["primary"] == "primary"
    with pytest.raises(TypeError):
        binding.path_by_duct["primary"] = "secondary"
    identity = {"ports": ports.to_dict(), "powervalve": valve.to_dict()}
    duct_species = {
        path_id: ((0.0, 0.0, 1.1768e-6, 0.0), (1.1768e-6, 0.0, 0.0, 0.0))
        for path_id in path_mapping.values()
    }
    system = _case(port_binding=binding, reference_rpm=3000.0,
                   cylinder_pressure=130000.0,
                   geometry=lambda angle: EngineGeometry2T(.00015, .00018, 0.0, 0.0,
                                                           0.0, (0.0, 0.0, 0.0), 0.0),
                   geometry_identity=identity, duct_species=duct_species)
    closed = system._geometry(0.0, 3000.0)
    open_stage = system._assemble(system.state, 180.0, 3000.0)
    resolved = open_stage["geometry"]
    assert closed.exhaust_area_m2 < resolved.exhaust_area_m2
    assert len(resolved.transfer_areas_m2) == 3
    assert all(area > 0.0 for area in resolved.transfer_areas_m2)
    assert open_stage["faces"]["exhaust"]["left"][0] != 0.0
    checkpoint = system.snapshot()
    mismatched = _case(port_binding=binding, reference_rpm=3001.0,
                       cylinder_pressure=130000.0,
                       geometry=lambda angle: EngineGeometry2T(
                           .00015, .00018, 0.0, 0.0, 0.0, (0.0, 0.0, 0.0), 0.0),
                       geometry_identity=identity)
    with pytest.raises(ValueError, match="configuration mismatch"):
        mismatched.restore(checkpoint)
    for step_index in range(4000):
        system.step(1.25e-6, 0.0225)
    assert system.angle_deg == pytest.approx(90.0)
    assert any(stage["exhaust_area_m2"] > 0.0
               for trace in system.trace for stage in trace["stage_geometry"])
    assert all(len(trace["stage_face_fluxes"]) == 2 for trace in system.trace)
    reverse_donor_checked = False
    forward_donor_checked = False
    powervalve_effect_checked = False
    for trace in system.trace:
        stage_angles = (trace["angle_start_deg"], trace["angle_end_deg"])
        for stage_state, stage_faces, stage_angle in zip(
                trace["stage_states"][:2], trace["stage_face_fluxes"], stage_angles):
            expected_areas = binding.resolve(system.ducts, stage_angle, 3000.0)
            actual_geometry = trace["stage_geometry"][
                0 if stage_angle == trace["angle_start_deg"] else 1]
            assert actual_geometry["intake_area_m2"] == pytest.approx(expected_areas[0])
            assert actual_geometry["transfer_areas_m2"] == pytest.approx(expected_areas[1])
            assert actual_geometry["exhaust_area_m2"] == pytest.approx(expected_areas[2])
            main_port = next(port for port in ports.ports if port.id == "main-exhaust")
            raw_main_area = ports.area_at(main_port, stage_angle)
            controlled_main_area = valve.area_at(ports, 3000.0, stage_angle)
            if controlled_main_area != pytest.approx(raw_main_area, rel=1e-6, abs=1e-15):
                powervalve_effect_checked = True
            for duct in system.ducts:
                gas_faces = stage_faces[duct.id]["all_faces"]
                species_faces = stage_faces[duct.id]["all_species_faces"]
                cell_species = stage_state["species"]["ducts"][duct.id]
                for face_index in range(1, len(gas_faces) - 1):
                    mass_flux = gas_faces[face_index][0]
                    if mass_flux == 0.0:
                        continue
                    if mass_flux < 0.0:
                        donor = cell_species[face_index]
                        receiver = cell_species[face_index - 1]
                    else:
                        donor = cell_species[face_index - 1]
                        receiver = cell_species[face_index]
                    donor_total = sum(donor)
                    receiver_total = sum(receiver)
                    composition_gap = max(abs(donor[j] / donor_total -
                                              receiver[j] / receiver_total)
                                          for j in range(4))
                    if composition_gap < 1e-4:
                        continue
                    expected_flux = tuple(mass_flux * value / donor_total
                                          for value in donor)
                    assert species_faces[face_index] == pytest.approx(
                        expected_flux, rel=1e-12, abs=1e-15)
                    if mass_flux < 0.0:
                        reverse_donor_checked = True
                    else:
                        forward_donor_checked = True
    assert reverse_donor_checked
    assert forward_donor_checked
    assert powervalve_effect_checked


def test_fresh_exhaust_flow_is_counted_as_short_circuit_only_with_open_transfers():
    system = _case(cylinder_pressure=130000.0, exhaust_area=1e-5,
                   cylinder_species=(0.000105912, 0.000052956,
                                     0.000052956, 0.0))
    system.step(1e-8, .01)
    assert system.ledger["fresh_short_circuit_kg"] > 0.0
    assert system.ledger["fuel_short_circuited_kg"] > 0.0


def test_prescribed_wall_heat_uses_stage_state_and_global_energy_ledger():
    thermal = ThermalSystem((ThermalSurface(
        "cylinder-wall", "cylinder_wall", 1e-4, 1000.0,
        "SYNTHETIC_ASSUMPTION", wall_temperature_K=290.0),))
    system = _case(thermal_system=thermal,
                   thermal_locations={"cylinder-wall": "cylinder"})
    record = system.step(1e-8, .01)
    assert record["heat_to_wall_J"] > 0.0
    assert system.ledger["heat_to_wall_J"] == record["heat_to_wall_J"]
    assert abs(system.conservation_report()["energy"]["residual"]) < 1e-10


def test_p7_prescribed_combustion_shares_integrated_species_and_energy_stages():
    mass = 1.1768 * .00018
    initial_species = (.00018, .00001, mass - .00019, 0.0)
    system = _case(combustion_start_angle_deg=0.0,
                   cylinder_species=initial_species,
                   transfer_area=0.0, exhaust_area=0.0)
    initial_inventory = system.inventory()
    for _ in range(100):
        record = system.step(.05 / 18000.0, .05)
    assert system.p7_events == []
    final_species = system.state["species"]["chambers"]["cylinder"]
    event = system.p7_event
    assert event is not None
    assert record["stage_p7_source_rates"][0]["heat_w"] > 0.0
    assert record["stage_p7_source_rates"][1]["heat_w"] > 0.0
    assert final_species[0] < initial_species[0]
    assert final_species[1] < initial_species[1]
    assert final_species[3] > 0.0
    assert sum(final_species) == pytest.approx(
        system.state["chambers"]["cylinder"][0], abs=1e-14)
    assert event.ledger.fresh_air_converted == pytest.approx(
        initial_species[0] - final_species[0], abs=1e-14)
    assert event.ledger.fuel_converted == pytest.approx(
        initial_species[1] - final_species[1], abs=1e-14)
    assert system.ledger["p7_heat_added_J"] == pytest.approx(
        800000.0 * event.ledger.burned_produced, rel=1e-12)
    expected_energy_change = (
        system.ledger["external_energy_J"] + system.ledger["p7_heat_added_J"] +
        system.ledger["cylinder_work_J"] + system.ledger["crankcase_work_J"] -
        system.ledger["heat_to_wall_J"])
    assert system.inventory()["energy_J"] - initial_inventory["energy_J"] == pytest.approx(
        expected_energy_change, rel=1e-12, abs=1e-12)
    assert abs(system.conservation_report()["energy"]["residual"]) < 1e-10
    assert abs(system.conservation_report()["mass"]["residual"]) < 1e-14
    assert all(abs(item["residual"]) < 1e-14
               for item in system.conservation_report()["species"].values())


def test_p7_integrated_checkpoint_replays_event_and_rejects_skipped_phase():
    mass = 1.1768 * .00018
    initial_species = (.00018, .00001, mass - .00019, 0.0)
    continuous = _case(combustion_start_angle_deg=0.0,
                       cylinder_species=initial_species,
                       transfer_area=0.0, exhaust_area=0.0)
    for _ in range(60):
        continuous.step(.05 / 18000.0, .05)
    checkpoint = continuous.snapshot()
    expected = continuous.step(.05 / 18000.0, .05)
    replay = _case(combustion_start_angle_deg=0.0,
                   cylinder_species=initial_species,
                   transfer_area=0.0, exhaust_area=0.0)
    replay.restore(checkpoint)
    actual = replay.step(.05 / 18000.0, .05)
    assert replay.state == continuous.state
    assert replay.ledger == continuous.ledger
    assert actual["stage_p7_source_rates"] == expected["stage_p7_source_rates"]
    wrong_contract = _case(cylinder_species=initial_species,
                           transfer_area=0.0, exhaust_area=0.0)
    with pytest.raises(ValueError, match="configuration mismatch"):
        wrong_contract.restore(checkpoint)
    corrupted = deepcopy(checkpoint)
    corrupted["p7"]["active_event"]["start"] = float("nan")
    untouched = _case(combustion_start_angle_deg=0.0,
                      cylinder_species=initial_species,
                      transfer_area=0.0, exhaust_area=0.0)
    before = untouched.snapshot()
    with pytest.raises(ValueError, match="P7 event is invalid"):
        untouched.restore(corrupted)
    assert untouched.snapshot() == before
    skipped = _case(combustion_start_angle_deg=10.0,
                    cylinder_species=initial_species,
                    transfer_area=0.0, exhaust_area=0.0)
    with pytest.raises(ValueError, match="end exactly at ignition"):
        skipped.step(20.0 / 18000.0, 20.0)


def test_p7_ignition_capture_is_transactional_when_the_step_is_rejected():
    mass = 1.1768 * .00018
    initial_species = (.00018, .00001, mass - .00019, 0.0)
    system = _case(combustion_start_angle_deg=10.0,
                   cylinder_species=initial_species,
                   transfer_area=0.0, exhaust_area=0.0)
    system.angle_deg = system.crank_angle_unwrapped_deg = 10.0
    before_state = deepcopy(system.state)
    before_ledger = deepcopy(system.ledger)
    with pytest.raises(ValueError, match="CFL limit exceeded"):
        system.step(1.0, .05)
    assert system.p7_event is None
    assert system.p7_events == []
    assert system.state == before_state
    assert system.ledger == before_ledger
    system.step(.05 / 18000.0, .05)
    assert system.p7_event is not None
    assert system.p7_event.start == pytest.approx(10.0)
    assert system.p7_events == []
    corrupted = system.snapshot()
    corrupted["p7"]["active_event"] = None
    corrupted["p7"]["completed_events"] = []
    corrupted["ledger"]["p7_heat_added_J"] = 0.0
    corrupted["ledger"]["p7_source_species_kg"] = [0.0] * 4
    target = _case(combustion_start_angle_deg=10.0,
                   cylinder_species=initial_species,
                   transfer_area=0.0, exhaust_area=0.0)
    with pytest.raises(ValueError, match="missing the event"):
        target.restore(corrupted)


def test_p7_event_boundary_requires_exact_alignment_and_stops_cleanly():
    mass = 1.1768 * .00018
    initial_species = (.00018, .00001, mass - .00019, 0.0)
    system = _case(combustion_start_angle_deg=0.0,
                   cylinder_species=initial_species,
                   transfer_area=0.0, exhaust_area=0.0, duct_length=.2)
    rejected_trials = []
    def advance_to(target):
        while system.crank_angle_unwrapped_deg < target - 1e-12:
            delta = min(.05, target - system.crank_angle_unwrapped_deg)
            while True:
                try:
                    system.step(delta / 18000.0, delta)
                    break
                except ValueError as error:
                    if "inadmissible species mass" not in str(error):
                        raise
                    rejected_trials.append({"angle_deg": system.crank_angle_unwrapped_deg,
                                            "step_deg": delta,
                                            "reason": str(error)})
                    delta /= 2.0
                    assert delta > 1e-7
    advance_to(39.95)
    before_state = deepcopy(system.state)
    before_angle = system.crank_angle_unwrapped_deg
    before_heat = system.ledger["p7_heat_added_J"]
    with pytest.raises(ValueError, match="event boundary"):
        system.step(.1 / 18000.0, .1)
    assert system.state == before_state
    assert system.crank_angle_unwrapped_deg == before_angle
    assert system.ledger["p7_heat_added_J"] == before_heat
    advance_to(40.0)
    assert system.crank_angle_unwrapped_deg == pytest.approx(40.0)
    assert system.trace[-1]["stage_p7_source_rates"][1]["heat_w"] == pytest.approx(0.0)
    assert all(row["step_deg"] > 0 and "inadmissible species mass" in row["reason"]
               for row in rejected_trials)


def _internal_cycle_fixture(*, with_reed=True, chamber_length_scale=1.0,
                            fixture_name=None, intake_plenum=False,
                            network_volumes=(), dynamic_reed=False,
                            transfer_ids=("primary", "secondary", "boost"),
                            open_end_plenum_v2=False,
                            fuel_coupled_combustion=None,
                            p7_enabled_with_fuel=False, rpm=3000.0,
                            transfer_cells=2, exhaust_cell_length_m=.2,
                            inlet_species_donor=(.98, .02, 0.0, 0.0)):
    if not math.isfinite(rpm) or rpm <= 0.0:
        raise ValueError("fixture RPM must be positive and finite")
    rpm = float(rpm)
    if type(transfer_cells) is not int or transfer_cells < 1:
        raise ValueError("fixture transfer_cells must be a positive integer")
    if not math.isfinite(exhaust_cell_length_m) or exhaust_cell_length_m <= 0.0:
        raise ValueError("fixture exhaust cell length must be positive and finite")
    crankcase = CrankcaseGeometry(56.0, 50.0, 100.0, 80.0,
                                  "SYNTHETIC_ASSUMPTION")
    slider = SliderCrankChambers2T(crankcase, 8.0)
    transfer_definitions = {
        "primary": PortDefinition("primary-window", "Primary", "transfer", "primary", "primary",
                                   "rectangular_window", .8, "SYNTHETIC_ASSUMPTION", top_mm=32.0,
                                   height_mm=10.0, width_mm=20.0),
        "secondary": PortDefinition("secondary-window", "Secondary", "transfer", "secondary",
                                     "secondary", "rectangular_window", .8,
                                     "SYNTHETIC_ASSUMPTION", top_mm=34.0,
                                     height_mm=8.0, width_mm=12.0),
        "boost": PortDefinition("boost-window", "Boost", "transfer", "boost", "boost",
                                "rectangular_window", .7, "SYNTHETIC_ASSUMPTION", top_mm=36.0,
                                height_mm=7.0, width_mm=8.0),
    }
    assert transfer_ids and set(transfer_ids) <= set(transfer_definitions)
    ports = TwoStrokePortSet(
        50.0, 100.0,
        (DuctBinding("inlet", "intake"),
         *(DuctBinding(path_id, "transfer") for path_id in transfer_ids),
         DuctBinding("exhaust", "exhaust")),
        (PortDefinition("inlet-window", "Inlet", "intake", "piston_port", "inlet",
                        "piston_port", .9, "SYNTHETIC_ASSUMPTION", top_mm=64.0,
                        height_mm=10.0, width_mm=20.0, skirt_mm=42.0),
         *(transfer_definitions[path_id] for path_id in transfer_ids),
         PortDefinition("main-exhaust", "Main exhaust", "exhaust", "main", "exhaust",
                        "rectangular_window", .9, "SYNTHETIC_ASSUMPTION", top_mm=30.0,
                        height_mm=10.0, width_mm=20.0, roof_travel_mm=4.0),
         PortDefinition("aux-exhaust", "Aux exhaust", "exhaust", "auxiliary", "exhaust",
                        "effective_profile", .5, "SYNTHETIC_ASSUMPTION",
                        area_profile=(AreaKnot(0.0, 0.0), AreaKnot(60.0, 0.0),
                                      AreaKnot(90.0, 25.0), AreaKnot(180.0, 50.0),
                                      AreaKnot(270.0, 25.0), AreaKnot(310.0, 0.0),
                                      AreaKnot(360.0, 0.0)))))
    valve = PowerValve("pv", "main-exhaust", (1000.0, 5000.0), (0.0, 1.0),
                       "SYNTHETIC_ASSUMPTION")
    path_by_duct = {"inlet": "intake", "exhaust": "exhaust"}
    path_by_duct.update({path_id: path_id for path_id in transfer_ids})
    binding = IntegratedPortBinding2T(ports, path_by_duct, valve)
    assert chamber_length_scale > 0.0
    chamber = ExpansionChamber((
        ChamberSection("header", "header", 80.0 * chamber_length_scale, 20.0, 20.0),
        ChamberSection("diffuser", "diffuser", 180.0 * chamber_length_scale, 20.0, 52.0),
        ChamberSection("belly", "belly", 100.0 * chamber_length_scale, 52.0, 52.0),
        ChamberSection("baffle", "baffle_cone", 170.0 * chamber_length_scale, 52.0, 16.0),
        ChamberSection("stinger", "stinger", 120.0 * chamber_length_scale, 16.0, 16.0)))
    paths = (DuctPath2T("intake", uniform_mesh(2, .05, 1e-4), "intake"),
             *(DuctPath2T(path_id, uniform_mesh(transfer_cells, .05, 1e-4), "transfer")
               for path_id in transfer_ids),
             DuctPath2T("exhaust", chamber.mesh(exhaust_cell_length_m), "exhaust"))

    def geometry(angle):
        cc_vol, cy_vol, cc_rate, cy_rate = slider.resolve(angle, rpm)
        intake, transfer_areas, exhaust = binding.resolve(paths, angle, rpm)
        return EngineGeometry2T(cc_vol, cy_vol, cc_rate, cy_rate, intake,
                                transfer_areas, exhaust)

    states = {path.id: ((1.1768, 0.0, 101325.0, 1.0),) * len(path.mesh.volumes)
              for path in paths}
    cc_vol, cy_vol, _, _ = slider.resolve(0.0, rpm)
    cc_mass, cy_mass = 1.1768 * cc_vol, 1.1768 * cy_vol
    species = {"crankcase": (0.0, 0.0, cc_mass, 0.0),
               "cylinder": (.78 * cy_mass, .05 * cy_mass, .17 * cy_mass, 0.0)}
    for path in paths:
        if path.role == "transfer":
            species[path.id] = tuple((1.1768 * volume, 0.0, 0.0, 0.0)
                                     for volume in path.mesh.volumes)
    reed = ReedPetal("intake-petal", .001, 1e-4, .01, 10.0, .01,
                     .002, .8, "SYNTHETIC_ASSUMPTION")
    dynamic_reed_binding = None
    if dynamic_reed:
        if with_reed:
            raise ValueError("synthetic test cannot combine static and dynamic reed fixtures")
        intake_path = next(path for path in paths if path.role == "intake")
        dynamic_petal = ReedPetal(
            "integrated-dynamic-petal", 1000.0, .0001, .01, 10.0,
            1000.0, .002, .8, "SYNTHETIC_ASSUMPTION")
        dynamic_geometry = HingedFlapGeometryV1(
            "integrated-dynamic-reed", "1", "SYNTHETIC_ASSUMPTION", .01, .02,
            intake_path.mesh.volumes[-1], cc_vol, .002, .8)
        dynamic_reed_binding = DynamicReedBinding2T(
            intake_path.id, dynamic_geometry, dynamic_petal, ReedState(.001, 0.0))
        species["crankcase"] = (
            0.0, 0.0,
            1.1768 * (cc_vol - dynamic_geometry.swept_volume_area_m2 * .001),
            0.0)
    thermal = ThermalSystem((ThermalSurface(
        "cylinder-wall", "cylinder_wall", 1e-4, 1000.0,
        "SYNTHETIC_ASSUMPTION", wall_temperature_K=290.0),))
    return IntegratedEngine2T(
        # Start both chambers at the same atmospheric p/T as the ducts.
        (1.1768, 0.0, 101325.0, 1.0), (1.1768, 0.0, 101325.0, 1.0),
        paths, states, geometry, species=species,
        atmosphere_species=inlet_species_donor,
        inlet_boundary=(OpenEndPlenumV2Boundary(101325.0, 300.0, 1.0)
                        if open_end_plenum_v2 else
                        Boundary("nonreflecting", state=(1.1768, 0.0, 101325.0, 1.0))),
        outlet_boundary=(OpenEndPlenumV2Boundary(101325.0, 300.0, 1.0)
                         if open_end_plenum_v2 else
                         Boundary("nonreflecting", state=(1.1768, 0.0, 101325.0, 1.0))),
        geometry_identity={"fixture": (fixture_name or
                                        ("internal-cycle-b-piston-port-synthetic-v1"
                                         if not with_reed else
                                         "internal-cycle-a-synthetic-v1"
                                         if chamber_length_scale == 1.0 else
                                         "internal-cycle-b-long-chamber-synthetic-v1")),
                           "chamber_length_scale": chamber_length_scale,
                           "ports": ports.to_dict(), "chamber": chamber.to_dict(),
                           "intake_donor_species": list(inlet_species_donor),
                           "intake_donor_species_provenance": "SYNTHETIC_ASSUMPTION",
                           "intake_donor_interpretation": (
                               "synthetic premixed intake reservoir composition; "
                               "not ambient-air composition")},
        reed_petals=((reed,) if with_reed else ()),
        dynamic_reed_binding=dynamic_reed_binding,
        port_binding=binding, slider_crank=slider,
        intake_plenum=(_intake_plenum(
            pressure=101325.0, fractions=(1.0, 0.0, 0.0, 0.0))
                       if intake_plenum else None),
        network_volumes=network_volumes,
        reference_rpm=rpm, thermal_system=thermal,
        thermal_locations={"cylinder-wall": "cylinder"},
        combustion_start_angle_deg=(
            300.0 if p7_enabled_with_fuel or fuel_coupled_combustion is None else None),
        fuel_coupled_combustion=fuel_coupled_combustion, max_cfl=.4)


def _advance_cycle_fixture(system, target_angle):
    rejected_trials = getattr(system, "fixture_rejected_trials", None)
    if rejected_trials is None:
        rejected_trials = []
        system.fixture_rejected_trials = rejected_trials
    system.fixture_rejection_runner_sha256 = hashlib.sha256(
        inspect.getsource(_advance_cycle_fixture).encode("utf-8")).hexdigest()
    rpm = 3000.0
    binding = system.port_binding
    ports = binding.port_set
    if binding.powervalve is not None:
        valve = binding.powervalve
        ports = replace(ports, ports=tuple(
            valve.apply(port, rpm) if port.id == valve.exhaust_port_id else port
            for port in ports.ports))
    closure_angles = sorted({angle for duct in ports.ducts
                             for angle in ports.duct_closing_angles(duct.id)})
    while system.crank_angle_unwrapped_deg < target_angle - 1e-10:
        angle = system.crank_angle_unwrapped_deg
        target = min(target_angle, (int((angle + 1e-10) / .5) + 1) * .5)
        next_cycle = int(angle // 360.0)
        scheduled = {float(value) for value in
                     (40.0, 300.0, 340.0, 660.0, 700.0, 360.0, 720.0)}
        scheduled.update(cycle * 360.0 + event
                         for cycle in range(max(0, next_cycle - 1),
                                            int(target_angle // 360.0) + 2)
                         for event in closure_angles)
        for boundary in scheduled:
            if angle < boundary < target:
                target = boundary
        step = target - angle
        for attempt in range(25):
            try:
                system.step(step / (6.0 * rpm), step)
                break
            except ValueError as error:
                if not any(reason in str(error) for reason in
                           ("inadmissible species mass", "CFL limit exceeded",
                            "rho/p/Y inadmissible",
                            "integrated dynamic reed state is inadmissible")):
                    raise
                rejected_trials.append({"angle_deg": angle,
                                        "attempted_step_deg": step,
                                        "reason": str(error)})
                step *= .5
        else:
            raise AssertionError(f"fixture could not accept a step at {angle} degrees")


def test_internal_synthetic_integrated_engine_completes_two_cycles_and_replays():
    system = _internal_cycle_fixture()
    cycle_zero_checkpoint = deepcopy(system.snapshot())
    _advance_cycle_fixture(system, 360.0)
    cycle_one_checkpoint = deepcopy(system.snapshot())
    first_cycle = make_integrated_cycle_primary(
        system, cycle_zero_checkpoint, cycle_one_checkpoint, 1)
    corrupted_trace = deepcopy(cycle_one_checkpoint)
    corrupted_trace["trace"][-1]["stage_cycle_rates"][0][
        "fresh_delivery_kg_s"] += 1e-6
    with pytest.raises(ValueError, match="recomputed stage 0 cycle rates"):
        make_integrated_cycle_primary(
            system, cycle_zero_checkpoint, corrupted_trace, 1)
    missing_ledger_key = deepcopy(cycle_one_checkpoint)
    del missing_ledger_key["ledger"]["external_mass_kg"]
    with pytest.raises(ValueError, match="ledger schema is incomplete"):
        make_integrated_cycle_primary(
            system, cycle_zero_checkpoint, missing_ledger_key, 1)
    assert first_cycle["port_closure_snapshots"]["status"] == "EXACT_EVENT_STATES_CAPTURED"
    for role in ("transfer", "exhaust"):
        snapshot = first_cycle["port_closure_snapshots"]["snapshots"][role]
        assert sum(snapshot["cylinder_species_kg"]) == pytest.approx(
            snapshot["cylinder_total_mass_kg"])
        assert sum(row["angle_end_deg"] == pytest.approx(snapshot["angle_deg"])
                   for row in first_cycle["trajectory"]) == 1
    _advance_cycle_fixture(system, 720.0)
    second_cycle = make_integrated_cycle_primary(
        system, cycle_one_checkpoint, system.snapshot(), 2)
    assert second_cycle["port_closure_snapshots"]["status"] == "EXACT_EVENT_STATES_CAPTURED"

    assert system.cycle == 2
    assert system.crank_angle_unwrapped_deg == pytest.approx(720.0)
    assert cycle_one_checkpoint is not None
    assert len(system.transfers) == 3
    report = system.conservation_report()
    assert abs(report["mass"]["residual"]) < 1e-12
    assert abs(report["energy"]["residual"]) < 1e-9
    assert all(abs(item["residual"]) < 1e-12
               for item in report["species"].values())
    assert all(sum(values) == pytest.approx(
        system.state["ducts"][path.id][index][0] * path.mesh.volumes[index], abs=1e-14)
        for path in system.ducts
        for index, values in enumerate(system.state["species"]["ducts"][path.id]))
    assert system.ledger["fresh_delivered_kg"] > 0.0
    assert system.ledger["fresh_short_circuit_kg"] > 0.0
    assert system.ledger["fuel_delivered_kg"] > 0.0
    assert system.ledger["fuel_short_circuited_kg"] > 0.0
    assert system.ledger["p7_heat_added_J"] > 0.0
    assert system.ledger["heat_to_wall_J"] > 0.0
    assert system.ledger["cylinder_work_J"] > 0.0
    assert max(value for trace in system.trace for value in trace["stage_cfl"]) <= .4
    assert abs(first_cycle["conservation"]["mass_residual_kg"]) < 1e-12
    assert abs(first_cycle["conservation"]["energy_residual_J"]) < 1e-9
    assert all(abs(value) < 1e-12 for value in
               first_cycle["conservation"]["species_residual_kg"])
    assert second_cycle["CFL"]["max"] <= .4
    assert all(row["attempted_step_deg"] > 0 and row["reason"]
               for row in system.fixture_rejected_trials)
    # With the corrected atmospheric chamber fixture, prescribed P7 can be
    # availability-limited. Check that every accepted increment is visible in
    # the ledger instead of freezing the obsolete (wrong-initial-state) zero.
    assert system.ledger["p7_availability_limited_kg"] >= 0.0
    assert sum(trace["p7_availability_limited_kg"] for trace in system.trace) == \
        pytest.approx(system.ledger["p7_availability_limited_kg"], abs=1e-15)
    assert all(0.0 <= limiter["scale"] <= 1.0
               for trace in system.trace for limiter in trace["stage_p7_limiter"])
    comparison = compare_cycles(first_cycle, second_cycle)
    assert first_cycle["observables"]["work_J"] < 0.0
    assert second_cycle["observables"]["work_J"] > 0.0
    assert comparison["status"] == "INVALID"
    assert comparison["reason"] == "INVALID numeric observable"
    detector = PeriodicDetector()
    detector.update(first_cycle)
    update = detector.update(second_cycle)
    assert update["classification"] is None
    assert update["outcomes"]["lag1"]["status"] == "INVALID"
    assert update["lag1_streak"] == 0
    assert detector.converged_cycle is None

    output = make_integrated_engineering_output(
        first_cycle, displacement_m3=system.slider_crank.crankcase.displacement_m3,
        scavenging_reference_mass_kg=1e-4)
    assert validate_integrated_engineering_output_v3(output) == output
    assert output["operating_point"]["rpm"] == pytest.approx(3000.0)
    assert len(output["crank_angle_trace"]["angle_deg"]) == len(first_cycle["trajectory"]) + 1
    trace_channels = output["crank_angle_trace"]["channels"]
    assert "intake_port_area_m2" in trace_channels
    assert "transfer_mass_flow_kg_s" in trace_channels
    assert "duct:primary:cell:0:pressure_pa" in trace_channels
    assert "duct:primary:cell:0:fresh_air_mass_kg" in trace_channels
    assert "duct:primary:face:1:mass_flow_kg_s" in trace_channels
    assert output["cycle_metrics"]["indicated_work_j"]["value"] == pytest.approx(
        first_cycle["observables"]["work_J"])
    assert output["cycle_metrics"]["brake_power_w"]["status"] == "UNDEFINED"
    assert output["cycle_metrics"]["brake_work_j"]["status"] == "UNDEFINED"
    assert output["cycle_metrics"]["bsfc_g_kwh"]["status"] == "UNDEFINED"
    assert output["cycle_metrics"]["fuel_flow_kg_s"]["status"] == "DEFINED"
    assert output["cycle_metrics"]["fuel_flow_kg_s"]["value"] > 0.0
    assert output["cycle_metrics"]["afr"]["status"] == "UNDEFINED"
    assert output["cycle_metrics"]["gross_intake_air_fuel_ratio"]["status"] == "DEFINED"
    assert output["cycle_metrics"]["gross_intake_air_fuel_ratio"]["value"] == pytest.approx(
        first_cycle["observables"]["fresh_air_intake_delivery_kg"] /
        first_cycle["observables"]["fuel_delivered_kg"])
    assert output["cycle_metrics"]["gross_fresh_charge_delivery_kg"]["source"].startswith(
        "Gross sum of fresh_air + fuel")
    assert output["cycle_metrics"]["gross_fresh_charge_short_circuit_kg"]["source"].find(
        "reverse exhaust flow is excluded") >= 0
    assert output["cycle_metrics"]["fuel_delivered_per_cycle_kg"]["value"] == pytest.approx(
        first_cycle["observables"]["fuel_delivered_kg"])
    assert output["cycle_metrics"]["fuel_consumed_by_p7_per_cycle_kg"]["value"] == pytest.approx(
        first_cycle["observables"]["p7_fuel_consumed_kg"])
    assert output["cycle_metrics"]["fuel_unburned_terminal_global_kg"]["value"] == pytest.approx(
        first_cycle["observables"]["fuel_unburned_terminal_global_kg"])
    assert output["cycle_metrics"][
        "cylinder_fuel_species_at_exhaust_close_kg"]["status"] == "DEFINED"
    assert output["cycle_metrics"][
        "cylinder_fuel_species_at_exhaust_close_kg"]["value"] == pytest.approx(
            first_cycle["port_closure_snapshots"]["snapshots"]["exhaust"]
            ["cylinder_species_kg"][1])
    assert "not total trapped fuel" in output["cycle_metrics"][
        "cylinder_fuel_species_at_exhaust_close_kg"]["source"]
    assert abs(output["cycle_metrics"]["fuel_species_balance_residual_kg"]["value"]) < 1e-12
    assert output["cycle_metrics"]["equivalence_ratio"]["status"] == "UNDEFINED"

    output_v4 = make_integrated_engineering_output_v4(
        first_cycle, displacement_m3=system.slider_crank.crankcase.displacement_m3,
        scavenging_reference_mass_kg=1e-4)
    assert validate_integrated_engineering_output_v4(output_v4) == output_v4
    assert output_v4["schema"] == "MOTORSIM_ENGINEERING_OUTPUTS_V4"
    snapshots = first_cycle["port_closure_snapshots"]["snapshots"]
    last_close = max(snapshots.values(), key=lambda item: item["angle_deg"])
    assert output_v4["cycle_metrics"][
        "cylinder_fuel_species_at_last_port_close_kg"]["value"] == pytest.approx(
            last_close["cylinder_species_kg"][1])
    assert output_v4["cycle_metrics"][
        "cylinder_fresh_air_species_at_last_port_close_kg"]["value"] == pytest.approx(
            last_close["cylinder_species_kg"][0])
    assert output_v4["cycle_metrics"][
        "fresh_air_fuel_species_ratio_at_last_port_close"]["value"] == pytest.approx(
            last_close["cylinder_species_kg"][0] / last_close["cylinder_species_kg"][1])
    assert "not AFR" in output_v4["cycle_metrics"][
        "fresh_air_fuel_species_ratio_at_last_port_close"]["source"]
    assert output_v4["cycle_metrics"]["afr"]["status"] == "UNDEFINED"
    assert make_integrated_engineering_output(
        first_cycle, displacement_m3=system.slider_crank.crankcase.displacement_m3,
        scavenging_reference_mass_kg=1e-4) == output
    tampered_closure = deepcopy(first_cycle)
    tampered_species = tampered_closure["port_closure_snapshots"]["snapshots"][
        "exhaust"]["cylinder_species_kg"]
    tampered_species[1] += 1e-12
    tampered_species[2] -= 1e-12
    with pytest.raises(ValueError, match="stored exhaust closure species differ"):
        make_integrated_engineering_output_v4(
            tampered_closure,
            displacement_m3=system.slider_crank.crankcase.displacement_m3)
    assert _fresh_air_fuel_species_ratio((0.01, 0.0, 0.02, 0.0)) is None


    prior_v2_record = deepcopy(first_cycle)
    for row in prior_v2_record["trajectory"]:
        for stage in row["stage_cycle_rates"]:
            stage.pop("fresh_air_intake_delivery_kg_s", None)
    for key in ("fresh_air_intake_delivery_kg", "fuel_delivered_kg",
                "fuel_short_circuited_kg", "p7_fuel_consumed_kg",
                "fuel_unburned_terminal_global_kg", "fuel_inventory_start_global_kg",
                "fuel_external_net_kg", "fuel_mass_balance_residual_kg"):
        prior_v2_record["observables"].pop(key, None)
    prior_output = make_integrated_engineering_output(
        prior_v2_record, displacement_m3=system.slider_crank.crankcase.displacement_m3)
    assert prior_output["cycle_metrics"]["gross_intake_air_fuel_ratio"]["value"] == pytest.approx(
        output["cycle_metrics"]["gross_intake_air_fuel_ratio"]["value"])
    tampered_intake_rate = deepcopy(first_cycle)
    tampered_intake_rate["trajectory"][0]["stage_cycle_rates"][0][
        "fresh_air_intake_delivery_kg_s"] += 1e-4
    with pytest.raises(ValueError, match="differs from signed face flux"):
        make_integrated_engineering_output(
            tampered_intake_rate,
            displacement_m3=system.slider_crank.crankcase.displacement_m3)
    assert output["cycle_metrics"]["purity_at_transfer_close"]["status"] == "DEFINED"
    assert output["cycle_metrics"]["purity_at_exhaust_close"]["status"] == "DEFINED"
    assert output["cycle_metrics"]["fresh_retained_kg"]["status"] == "DEFINED"
    terminal_channels = output["crank_angle_trace"]["channels"]
    assert terminal_channels["cylinder_pressure_pa"]["values"][-1] == pytest.approx(
        first_cycle["observables"]["chambers"]["cylinder"]["pressure_Pa"])
    assert terminal_channels["exhaust_port_area_m2"]["values"][-1] == pytest.approx(
        first_cycle["terminal_diagnostic"]["geometry"]["exhaust_area_m2"])
    unavailable = deepcopy(first_cycle)
    unavailable["port_closure_snapshots"] = {
        "status": "UNAVAILABLE", "reason": "synthetic missing exact event", "snapshots": {}}
    unavailable_output = make_integrated_engineering_output(
        unavailable, displacement_m3=system.slider_crank.crankcase.displacement_m3,
        scavenging_reference_mass_kg=1e-4)
    assert unavailable_output["cycle_metrics"]["purity_at_exhaust_close"]["status"] == "UNDEFINED"
    assert unavailable_output["cycle_metrics"]["purity_at_exhaust_close"]["value"] is None
    assert unavailable_output["cycle_metrics"][
        "cylinder_fuel_species_at_exhaust_close_kg"]["status"] == "UNDEFINED"
    assert unavailable_output["cycle_metrics"][
        "cylinder_fuel_species_at_exhaust_close_kg"]["value"] is None
    unavailable_v4 = make_integrated_engineering_output_v4(
        unavailable, displacement_m3=system.slider_crank.crankcase.displacement_m3)
    assert validate_integrated_engineering_output_v4(unavailable_v4) == unavailable_v4
    for name in ("cylinder_fuel_species_at_last_port_close_kg",
                 "cylinder_fresh_air_species_at_last_port_close_kg",
                 "fresh_air_fuel_species_ratio_at_last_port_close"):
        assert unavailable_v4["cycle_metrics"][name]["status"] == "UNDEFINED"
        assert unavailable_v4["cycle_metrics"][name]["value"] is None
    tampered_primary = deepcopy(first_cycle)
    tampered_primary["observables"]["work_J"] += 1.0
    with pytest.raises(ValueError, match="observable work_J differs"):
        make_integrated_engineering_output(
            tampered_primary,
            displacement_m3=system.slider_crank.crankcase.displacement_m3)

    mechanical = MechanicalLossModel((LossTerm(
        "synthetic-friction", "piston_ring", "SYNTHETIC_ASSUMPTION", mep_pa=10_000.0),))
    brake = mechanical.evaluate_2t(
        indicated_work_j=second_cycle["observables"]["work_J"],
        displacement_m3=system.slider_crank.crankcase.displacement_m3,
        rpm=3000.0, load=0.0)
    assert brake["brake_work_j"] > 0.0
    assert brake["cycle_convention"] == "2T_360_DEG_ONE_CYCLE_PER_REV"
    output_with_losses = make_integrated_engineering_output(
        second_cycle, displacement_m3=system.slider_crank.crankcase.displacement_m3,
        mechanical_loss_model=mechanical)
    assert validate_integrated_engineering_output_v3(output_with_losses) == output_with_losses
    assert output_with_losses["cycle_metrics"]["brake_power_w"]["value"] == pytest.approx(
        second_cycle["observables"]["work_J"] * 3000.0 / 60.0 -
        brake["mechanical_loss_power_w"])
    assert output_with_losses["cycle_metrics"]["brake_work_j"]["value"] == pytest.approx(
        brake["brake_work_j"])
    assert output_with_losses["cycle_metrics"]["isfc_g_kwh"]["status"] == "DEFINED"
    assert output_with_losses["cycle_metrics"]["bsfc_g_kwh"]["status"] == "DEFINED"
    expected_fuel_flow = second_cycle["observables"]["p7_fuel_consumed_kg"] * 50.0
    assert output_with_losses["cycle_metrics"]["isfc_g_kwh"]["value"] == pytest.approx(
        expected_fuel_flow * 3.6e9 /
        output_with_losses["cycle_metrics"]["indicated_power_w"]["value"])

    replay = _internal_cycle_fixture()
    replay.restore(cycle_one_checkpoint)
    assert json.dumps(replay.state, sort_keys=True) == json.dumps(
        cycle_one_checkpoint["state"], sort_keys=True)
    _advance_cycle_fixture(replay, 720.0)
    assert replay.snapshot() == system.snapshot()


def test_multiple_finite_network_volumes_rebuild_cycle_and_engineering_output():
    eos = IdealGas()

    def volume_state(volume, fractions):
        pressure, temperature = 101325.0, 300.0
        mass = pressure * volume / (eos.R * temperature)
        return VolumeGasState(
            mass, pressure * volume / (eos.gamma - 1.0),
            tuple(mass * fraction for fraction in fractions))

    intake_node = VolumeNode("intake-plenum", "plenum", .001,
                             "SYNTHETIC_ASSUMPTION")
    exhaust_node = VolumeNode("exhaust-receiver", "airbox", .003,
                              "SYNTHETIC_ASSUMPTION")
    bindings = (
        IntegratedNetworkVolume2T(
            intake_node,
            NetworkConnection("intake-neck", intake_node.id, "intake",
                              1e-4, .05, "SYNTHETIC_ASSUMPTION"),
            "intake", "left", volume_state(.001, (1.0, 0.0, 0.0, 0.0))),
        IntegratedNetworkVolume2T(
            exhaust_node,
            NetworkConnection("exhaust-neck", "exhaust", exhaust_node.id,
                              1e-4, .08, "SYNTHETIC_ASSUMPTION"),
            "exhaust", "right", volume_state(.003, (0.0, 0.0, 0.0, 1.0))),
    )
    probe = _internal_cycle_fixture(network_volumes=bindings)
    replay = _internal_cycle_fixture(network_volumes=bindings)
    checkpoint = json.loads(json.dumps(probe.snapshot()))
    probe.step(1e-7, .001)
    replay.restore(checkpoint)
    replay.step(1e-7, .001)
    assert replay.snapshot() == probe.snapshot()
    assert replay.inventory() == probe.inventory()
    assert replay.conservation_report() == probe.conservation_report()

    system = _internal_cycle_fixture(network_volumes=bindings)
    start = deepcopy(system.snapshot())
    _advance_cycle_fixture(system, 360.0)
    end = deepcopy(system.snapshot())

    primary = make_integrated_cycle_primary(system, start, end, 1)
    assert primary["network_volume_definitions"] == {
        "intake-plenum": {"kind": "plenum", "volume_m3": .001},
        "exhaust-receiver": {"kind": "airbox", "volume_m3": .003}}
    output = make_integrated_engineering_output(
        primary, displacement_m3=system.slider_crank.crankcase.displacement_m3)
    assert validate_integrated_engineering_output_v3(output) == output
    channels = output["crank_angle_trace"]["channels"]
    for node_id in ("intake-plenum", "exhaust-receiver"):
        prefix = f"network:{node_id}:"
        for suffix in ("mass_kg", "pressure_pa", "temperature_k",
                       "fresh_air_mass_kg", "fuel_mass_kg", "residual_mass_kg",
                       "burned_mass_kg"):
            assert prefix + suffix in channels
            assert len(channels[prefix + suffix]["values"]) == len(
                output["crank_angle_trace"]["angle_deg"])
        sample_indices = (0, len(primary["trajectory"]) // 2, -1)
        for sample_index in sample_indices:
            state = (primary["terminal_state"] if sample_index == -1 else
                     primary["trajectory"][sample_index]["stage_states"][0])
            mass, energy, volume = state["network_volumes"][node_id]
            composition = state["species"]["network_volumes"][node_id]
            expected = {
                "mass_kg": mass,
                "pressure_pa": (eos.gamma - 1.0) * energy / volume,
                "temperature_k": energy / (mass * eos.cv),
                **{f"{name}_mass_kg": composition[index]
                   for index, name in enumerate(("fresh_air", "fuel", "residual", "burned"))},
            }
            channel_index = (len(primary["trajectory"]) if sample_index == -1 else
                             sample_index)
            for suffix, value in expected.items():
                assert channels[prefix + suffix]["values"][channel_index] == pytest.approx(value)
    exchange_nodes = {node_id for row in primary["trajectory"]
                      for stage in row["stage_network_exchanges"]
                      for node_id, exchange in stage.items()
                      if exchange["mass_into_volume_kg_s"] != 0.0}
    assert exchange_nodes == {"intake-plenum", "exhaust-receiver"}
    assert abs(primary["conservation"]["mass_residual_kg"]) < 1e-12
    assert abs(primary["conservation"]["energy_residual_J"]) < 1e-9
    assert all(abs(value) < 1e-12 for value in
               primary["conservation"]["species_residual_kg"])
    malformed = deepcopy(primary)
    malformed["network_volume_definitions"]["intake-plenum"]["volume_m3"] = True
    with pytest.raises(ValueError, match="definition is malformed"):
        make_integrated_engineering_output(
            malformed, displacement_m3=system.slider_crank.crankcase.displacement_m3)


def test_integrated_engine_config_roundtrip_rebuilds_without_external_callback():
    system = _internal_cycle_fixture(network_volumes=())
    encoded = system.configuration_json()
    rebuilt = IntegratedEngine2T.from_configuration_dict(json.loads(encoded))

    assert rebuilt.configuration_json() == encoded
    assert rebuilt.configuration_identity == system.configuration_identity
    assert rebuilt.snapshot() == system.snapshot()

    def forbidden_callback(_angle):
        raise AssertionError("explicit geometry path invoked caller callback")

    system.geometry = forbidden_callback
    rebuilt.geometry = forbidden_callback
    assert system._geometry(0.0, system.reference_rpm) == rebuilt._geometry(
        0.0, rebuilt.reference_rpm)

    system.step(1e-6, .01)
    rebuilt.restore(system.snapshot())
    assert rebuilt.snapshot() == system.snapshot()
    rebuilt.step(1e-6, .01)
    system.step(1e-6, .01)
    assert rebuilt.snapshot() == system.snapshot()


def test_integrated_engine_config_v1_read_preserves_legacy_outlet_composition():
    legacy = json.loads(_internal_cycle_fixture().configuration_json())
    legacy.pop("outlet_species")
    legacy["schema"] = "MOTORSIM_INTEGRATED_ENGINE_2T_CONFIG_V1"

    rebuilt = IntegratedEngine2T.from_configuration_dict(legacy)

    assert rebuilt.outlet_species == tuple(legacy["atmosphere_species"])
    current = rebuilt.configuration_dict()
    assert current["schema"] == IntegratedEngine2T.configuration_schema
    assert current["outlet_species"] == legacy["atmosphere_species"]


def test_integrated_engine_config_roundtrip_preserves_network_bindings():
    eos = IdealGas()
    volume = .001
    mass = 101325.0 * volume / (eos.R * 300.0)
    node = VolumeNode("intake-config", "plenum", volume,
                      "SYNTHETIC_ASSUMPTION")
    exhaust_node = VolumeNode("exhaust-config", "airbox", .003,
                              "SYNTHETIC_ASSUMPTION")
    bindings = (
      IntegratedNetworkVolume2T(
        node, NetworkConnection("neck-config", node.id, "intake", 1e-4,
                                .05, "SYNTHETIC_ASSUMPTION"),
        "intake", "left", VolumeGasState(
            mass, 101325.0 * volume / (eos.gamma - 1.0),
            (mass, 0.0, 0.0, 0.0))),
      IntegratedNetworkVolume2T(
        exhaust_node, NetworkConnection("exhaust-neck-config", "exhaust",
                                        exhaust_node.id, 1e-4, .08,
                                        "SYNTHETIC_ASSUMPTION"),
        "exhaust", "right", VolumeGasState(
            mass * 3.0, 101325.0 * .003 / (eos.gamma - 1.0),
            (0.0, 0.0, 0.0, mass * 3.0))))
    system = _internal_cycle_fixture(network_volumes=bindings)
    rebuilt = IntegratedEngine2T.from_configuration_dict(
        json.loads(system.configuration_json()))
    assert rebuilt.configuration_json() == system.configuration_json()
    assert rebuilt.snapshot() == system.snapshot()


@pytest.mark.parametrize(("duct_id", "side", "node_to", "face_side"), [
    ("intake", "left", "intake", "left"),
    ("exhaust", "right", "exhaust", "right"),
])
def test_network_endpoint_pressure_traction_covers_blocked_face_and_rest_equilibrium(
        duct_id, side, node_to, face_side):
    eos = IdealGas()
    volume = .001
    pressure, temperature = 101325.0, 300.0
    mass = pressure * volume / (eos.R * temperature)
    node = VolumeNode(f"{duct_id}-plenum", "plenum", volume,
                      "SYNTHETIC_ASSUMPTION")
    upstream, downstream = ((node.id, duct_id) if node_to == "intake" else
                            (duct_id, node.id))
    binding = IntegratedNetworkVolume2T(
        node, NetworkConnection(f"{duct_id}-neck", upstream, downstream,
                                1e-5, .05, "SYNTHETIC_ASSUMPTION"),
        duct_id, side,
        VolumeGasState(mass, pressure * volume / (eos.gamma - 1.0),
                       (mass, 0.0, 0.0, 0.0)))
    system = _case(crankcase_pressure=pressure, cylinder_pressure=pressure,
                   intake_area=0.0, transfer_area=0.0, exhaust_area=0.0,
                   network_volumes=(binding,))

    assembled = system._assemble(system.state, 0.0, system.reference_rpm)
    face = assembled["faces"][duct_id][face_side]
    exchange = assembled["network_exchanges"][node.id]

    assert face[0] == pytest.approx(0.0, abs=1e-14)
    assert face[1] == pytest.approx(pressure * 1e-4, rel=1e-14)
    assert exchange["blocked_area_m2"] == pytest.approx(9e-5)
    assert exchange["blocked_area_pressure_traction_n"] == pytest.approx(
        pressure * 9e-5)
    assert exchange["external_wall_reaction_n"] == pytest.approx(
        (1.0 if side == "right" else -1.0) * pressure * 9e-5)

    initial = deepcopy(system.state)
    system.step(1e-7, .001)
    assert system.state["ducts"] == initial["ducts"]
    assert system.state["chambers"] == initial["chambers"]
    assert system.state["network_volumes"] == initial["network_volumes"]


def test_integrated_open_end_plenum_v2_configuration_restore_and_equilibrium():
    system = _internal_cycle_fixture(open_end_plenum_v2=True)
    config = json.loads(system.configuration_json())

    assert config["schema"] == "MOTORSIM_INTEGRATED_ENGINE_2T_CONFIG_V4"
    assert config["external_boundary_model"] == "OPEN_END_PLENUM_V2"
    assert config["external_boundary_provenance"] == "SYNTHETIC_ASSUMPTION"
    restored = IntegratedEngine2T.from_configuration_dict(config)
    assert restored.configuration_dict() == config
    assert restored.snapshot() == system.snapshot()
    assert isinstance(restored.inlet_boundary, OpenEndPlenumV2Boundary)
    assert isinstance(restored.outlet_boundary, OpenEndPlenumV2Boundary)

    system.step(1e-8, .0001)
    # The frozen synthetic prime fixture starts at ambient pressure and the
    # first angle is at TDC with all cylinder ports closed.
    for primitive in (system._primitive(system.state["ducts"]["intake"][0]),
                      system._primitive(system.state["ducts"]["exhaust"][0])):
        assert primitive[2] == pytest.approx(101325.0, abs=1e-7)
        assert primitive[1] == pytest.approx(0.0, abs=1e-10)
    assert system.trace[-1]["stage_face_fluxes"][1]["intake"][
        "left_external_pressure_reaction_n"] == pytest.approx(101325.0 * 1e-4)
    exhaust_face_area = next(path for path in system.ducts
                             if path.id == "exhaust").mesh.areas[-1]
    assert system.trace[-1]["stage_face_fluxes"][1]["exhaust"][
        "right_external_pressure_reaction_n"] == pytest.approx(
            -101325.0 * exhaust_face_area)


@pytest.mark.parametrize("transfer_ids", [
    ("primary",), ("primary", "secondary"), ("primary", "secondary", "boost")])
def test_positive_transfer_route_topologies_construct_serialize_step_and_restore(
        transfer_ids):
    engine = _internal_cycle_fixture(transfer_ids=transfer_ids,
                                     open_end_plenum_v2=True)
    encoded = engine.configuration_json()
    config = json.loads(encoded)
    assert config["schema"] == "MOTORSIM_INTEGRATED_ENGINE_2T_CONFIG_V4"
    assert config["resolved_topology"]["transfers"] == list(transfer_ids)
    restored = IntegratedEngine2T.from_configuration_dict(config)
    assert restored.configuration_json() == encoded
    assert restored.snapshot() == engine.snapshot()
    engine.step(1e-8, .0001)
    restored.restore(engine.snapshot())
    assert restored.snapshot() == engine.snapshot()


def test_fuel_coupled_chemistry_uses_both_ssprk_stages_and_restores_independently_of_p7():
    combustion = FuelCoupledCombustionV1(
        (WiebeComponent(1.0, 40.0, 5.0, 2.0),),
        ignition_timing_deg=0.0, combustion_efficiency=.8)
    engine = _internal_cycle_fixture(fuel_coupled_combustion=combustion,
                                     open_end_plenum_v2=True)
    config = engine.configuration_dict()
    assert config["schema"] == "MOTORSIM_INTEGRATED_ENGINE_2T_CONFIG_V5"
    rebuilt = IntegratedEngine2T.from_configuration_dict(config)
    assert rebuilt.configuration_dict() == config
    assert rebuilt.schema == "MOTORSIM_INTEGRATED_ENGINE_2T_STATE_V10"
    assert rebuilt.p7_event is None
    assert rebuilt.fuel_combustion_event == engine.fuel_combustion_event

    rebuilt.step(.1 / (6.0 * rebuilt.reference_rpm), .1)
    trace = rebuilt.trace[-1]
    sources = trace["stage_fuel_combustion_source_rates"]
    assert sources[0]["burned_fuel_rate_kg_s"] == 0.0
    assert sources[1]["burned_fuel_rate_kg_s"] > 0.0
    assert trace["fuel_combustion_heat_increment_j"] > 0.0
    assert sum(trace["fuel_combustion_source_species_increment_kg"]) == pytest.approx(
        0.0, abs=1e-18)
    assert trace["fuel_combustion_source_species_increment_kg"][2] == 0.0
    assert trace["fuel_combustion_source_species_increment_kg"][3] > 0.0

    restored = IntegratedEngine2T.from_configuration_dict(config)
    restored.restore(rebuilt.snapshot())
    assert restored.snapshot() == rebuilt.snapshot()


def test_fuel_library_v2_snapshot_drives_integrated_combustion_and_roundtrips():
    library = FuelLibrary()
    snapshot = library.freeze("MOTORSIM_ISOOCTANE_SURROGATE_V1")
    combustion = FuelCoupledCombustionV2(
        (WiebeComponent(1.0, 40.0, 5.0, 2.0),),
        ignition_timing_deg=0.0, combustion_efficiency=.8,
        fuel_snapshot=snapshot)
    engine = _internal_cycle_fixture(fuel_coupled_combustion=combustion,
                                     open_end_plenum_v2=True)
    config = engine.configuration_dict()
    assert config["schema"] == "MOTORSIM_INTEGRATED_ENGINE_2T_CONFIG_V6"
    assert config["fuel_coupled_combustion"]["schema"] == (
        "FUEL_COUPLED_COMBUSTION_V2")
    assert config["fuel_coupled_combustion"]["fuel_snapshot"]["content_hash"] == (
        snapshot.content_hash)
    rebuilt = IntegratedEngine2T.from_configuration_dict(config)
    assert rebuilt.configuration_dict() == config
    assert rebuilt.schema == "MOTORSIM_INTEGRATED_ENGINE_2T_STATE_V11"

    rebuilt.step(.1 / (6.0 * rebuilt.reference_rpm), .1)
    trace = rebuilt.trace[-1]
    sources = trace["stage_fuel_combustion_source_rates"]
    assert sources[0]["burned_fuel_rate_kg_s"] == 0.0
    assert sources[1]["burned_fuel_rate_kg_s"] > 0.0
    assert sources[1]["energy_per_burned_fuel_j_kg"] == pytest.approx(
        44_343_551.390414825 * .8)
    restored = IntegratedEngine2T.from_configuration_dict(config)
    restored.restore(rebuilt.snapshot())
    assert restored.snapshot() == rebuilt.snapshot()


def test_fuel_library_v2_does_not_infer_ancap_afr_or_lhv_from_identity():
    incomplete = FuelCoupledCombustionV2(
        (WiebeComponent(1.0, 40.0, 5.0, 2.0),),
        ignition_timing_deg=0.0, combustion_efficiency=.8,
        fuel_snapshot=FuelLibrary().freeze("ANCAP_SUPER_95"))
    with pytest.raises(ValueError, match="lacks"):
        incomplete.validate()


def test_fuel_library_v2_cycle_primary_audits_snapshot_trapping_and_heat():
    snapshot = FuelLibrary().freeze("MOTORSIM_ISOOCTANE_SURROGATE_V1")
    combustion = FuelCoupledCombustionV2(
        (WiebeComponent(1.0, 40.0, 5.0, 2.0),),
        ignition_timing_deg=0.0, combustion_efficiency=.8,
        fuel_snapshot=snapshot)
    engine = _internal_cycle_fixture(fuel_coupled_combustion=combustion,
                                     open_end_plenum_v2=True)
    start = engine.snapshot()
    _advance_cycle_fixture(engine, 360.0)
    primary = make_integrated_cycle_primary(engine, start, engine.snapshot(), 1)
    chemistry = primary["observables"]["fuel_coupled_combustion"]
    assert chemistry["schema"] == "FUEL_COUPLED_COMBUSTION_V2"
    assert chemistry["fuel_snapshot"]["schema"] == "FUEL_SIMULATION_SNAPSHOT_V1"
    assert chemistry["fuel_sha256"] == snapshot.content_hash
    assert chemistry["fuel_snapshot"]["full_definition"]
    assert chemistry["fuel_trapped_at_ignition_snapshot_kg"] > 0.0
    assert chemistry["fresh_air_trapped_at_ignition_snapshot_kg"] > 0.0
    assert chemistry["fuel_burned_kg"] > 0.0
    assert chemistry["chemical_heat_added_J"] == pytest.approx(
        chemistry["fuel_burned_kg"] * 44_343_551.390414825 * .8)
    assert audit_integrated_cycle_primary(primary)["status"] == "PASS"
    output = make_integrated_engineering_output(primary)
    metrics = output["cycle_metrics"]
    expected_afr = (chemistry["fresh_air_trapped_at_ignition_snapshot_kg"] /
                    chemistry["fuel_trapped_at_ignition_snapshot_kg"])
    expected_stoich = combustion.stoichiometric_afr
    assert metrics["afr"]["value"] == pytest.approx(expected_afr)
    assert metrics["equivalence_ratio"]["value"] == pytest.approx(
        expected_stoich / expected_afr)


def test_fuel_coupled_combustion_rejects_simultaneous_historical_p7():
    combustion = FuelCoupledCombustionV1(
        (WiebeComponent(1.0, 40.0, 5.0, 2.0),),
        ignition_timing_deg=0.0, combustion_efficiency=.8)
    with pytest.raises(ValueError, match="cannot be enabled together"):
        _internal_cycle_fixture(fuel_coupled_combustion=combustion,
                                fixture_name="simultaneous-p7",
                                p7_enabled_with_fuel=True)


def test_fuel_coupled_cycle_primary_recomputes_species_and_energy_sources():
    combustion = FuelCoupledCombustionV1(
        (WiebeComponent(1.0, 40.0, 5.0, 2.0),),
        ignition_timing_deg=0.0, combustion_efficiency=.8)
    engine = _case(
        duct_length=.5, reference_rpm=1000.0,
        cylinder_species=(.00015, 1e-7, .000211824 - .0001501, 0.0),
        fuel_coupled_combustion=combustion)
    start = engine.snapshot()
    for _ in range(360):
        engine.step(1.0 / (6.0 * engine.reference_rpm), 1.0)
    end = engine.snapshot()
    primary = make_integrated_cycle_primary(engine, start, end, 1)
    chemistry = primary["observables"]["fuel_coupled_combustion"]

    assert chemistry["fuel_sha256"] == combustion.fuel.sha256
    assert chemistry["fuel_burned_kg"] > 0.0
    assert chemistry["fuel_burned_kg"] <= 1e-7
    assert chemistry["chemical_heat_added_J"] == pytest.approx(
        chemistry["fuel_burned_kg"] * 43_000_000.0 * .8)
    assert abs(primary["conservation"]["energy_residual_J"]) < 1e-10
    assert abs(primary["conservation"]["species_residual_kg"][1]) < 1e-15


def test_offline_angle_replay_uses_nominal_step_not_subtracted_float_coordinates():
    start = 261.0177177155575
    end = 261.13828828666817
    attempted = 0.12057057111061908
    # The accepted step was passed directly to SSPRK2. Reconstructing it from
    # the accumulated angular coordinates can differ by a few ULPs and changes
    # the replay's derived RPM/volume rates.
    assert _angle_increment_matches(end, start, attempted)
    assert not _angle_increment_matches(end + 1e-8, start, attempted)


def test_offline_cycle_audit_rebuilds_supported_configuration_and_rejects_tampering():
    combustion = FuelCoupledCombustionV1(
        (WiebeComponent(1.0, 40.0, 5.0, 2.0),),
        ignition_timing_deg=0.0, combustion_efficiency=.01)
    engine = _internal_cycle_fixture(
        fuel_coupled_combustion=combustion, open_end_plenum_v2=True)
    start = engine.snapshot()
    _advance_cycle_fixture(engine, 360.0)
    primary = make_integrated_cycle_primary(engine, start, engine.snapshot(), 1)

    assert primary["schema"] == "MOTORSIM_INTEGRATED_2T_CYCLE_PRIMARY_V3"
    assert primary["evidence_binding"]["rejection_status"] == (
        "COMPLETE_CALLER_RETRY_LOG_BOUND_TO_CYCLE")
    assert primary["evidence_binding"]["rejected_trial_count"] == len(
        primary["rejected_trials"])
    assert audit_integrated_cycle_primary(primary)["status"] == "PASS"
    tampered = deepcopy(primary)
    tampered["trajectory"][0]["stage_face_fluxes"][0]["intake"]["left"][0] += 1e-9
    with pytest.raises(ValueError, match="trajectory/fixture/terminal hash"):
        audit_integrated_cycle_primary(tampered)
    tampered_bounds = deepcopy(primary)
    tampered_bounds["evidence_binding"]["residual_bounds"]["energy_abs_j"] *= 2
    with pytest.raises(ValueError, match="residual bounds"):
        audit_integrated_cycle_primary(tampered_bounds)
    if primary["rejected_trials"]:
        false_rejection = deepcopy(primary)
        false_rejection["rejected_trials"][0]["attempted_step_deg"] *= .99
        false_rejection["evidence_binding"]["rejection_records_sha256"] = (
            _evidence_sha256(false_rejection["rejected_trials"]))
        with pytest.raises(ValueError, match="rejected-step|rejection reason"):
            audit_integrated_cycle_primary(false_rejection)
        missing_rejection = deepcopy(primary)
        missing_rejection["rejected_trials"].pop()
        missing_rejection["evidence_binding"]["rejected_trial_count"] -= 1
        missing_rejection["evidence_binding"]["rejection_records_sha256"] = (
            _evidence_sha256(missing_rejection["rejected_trials"]))
        with pytest.raises(ValueError, match="rejection|rejected"):
            audit_integrated_cycle_primary(missing_rejection)
        counts = {}
        for index, row in enumerate(primary["rejected_trials"]):
            if "CFL limit exceeded" in row["reason"]:
                counts[row["angle_deg"]] = counts.get(row["angle_deg"], 0) + 1
        omitted_angle = next(angle for angle, count in counts.items() if count == 1)
        omitted = deepcopy(primary)
        omitted["rejected_trials"] = [
            row for row in omitted["rejected_trials"]
            if row["angle_deg"] != omitted_angle]
        binding = omitted["checkpoint_binding"]
        binding["end_rejected_steps"] -= 1
        evidence = omitted["evidence_binding"]
        evidence["rejected_trial_count"] = len(omitted["rejected_trials"])
        evidence["rejected_cfl_count"] -= 1
        evidence["rejection_records_sha256"] = _evidence_sha256(
            omitted["rejected_trials"])
        evidence["restart_terminal_sha256"] = _evidence_sha256({
            "state": omitted["terminal_state"],
            "ledger": binding["end_ledger"], "p7": binding["end_p7"],
            "fuel_combustion": binding["end_fuel_combustion"],
            "time_s": binding["end_time_s"],
            "accepted_steps": binding["end_accepted_steps"],
            "rejected_steps": binding["end_rejected_steps"],
            "angle_deg": omitted["cycle_end_deg"],
            "initial_inventory": binding["initial_inventory"]})
        with pytest.raises(ValueError, match="CFL limit exceeded|omits a rejection"):
            audit_integrated_cycle_primary(omitted)
    corrupted_stage = deepcopy(primary)
    corrupted_stage["trajectory"][0]["stage_states"][1]["chambers"][
        "cylinder"][0] *= 1.000001
    corrupted_stage["evidence_binding"]["trajectory_sha256"] = _evidence_sha256(
        corrupted_stage["trajectory"])
    with pytest.raises(ValueError, match="SSPRK2 accepted-state replay"):
        audit_integrated_cycle_primary(corrupted_stage)


def test_fuel_coupled_observables_bind_delivered_trapped_burned_and_unburned_snapshots():
    combustion = FuelCoupledCombustionV1(
        (WiebeComponent(1.0, 40.0, 5.0, 2.0),),
        ignition_timing_deg=0.0, combustion_efficiency=.01)
    engine = _internal_cycle_fixture(fuel_coupled_combustion=combustion,
                                     open_end_plenum_v2=True)
    start = engine.snapshot()
    _advance_cycle_fixture(engine, 360.0)
    primary = make_integrated_cycle_primary(engine, start, engine.snapshot(), 1)
    metrics = primary["observables"]["fuel_coupled_combustion"]
    exhaust_snapshot = primary["port_closure_snapshots"]["snapshots"]["exhaust"]

    assert metrics["fuel_delivered_gross_kg"] == pytest.approx(
        primary["observables"]["fuel_delivered_kg"])
    assert metrics["fuel_short_circuited_gross_kg"] == pytest.approx(
        primary["observables"]["fuel_short_circuited_kg"])
    assert metrics["fuel_trapped_at_ignition_snapshot_kg"] > 0.0
    assert metrics["fuel_available_from_ignition_snapshot_kg"] <= \
        metrics["fuel_trapped_at_ignition_snapshot_kg"]
    assert metrics["unburned_fuel_at_exhaust_close_kg"] == pytest.approx(
        exhaust_snapshot["cylinder_species_kg"][1])
    assert metrics["fuel_burned_kg"] > 0.0
    assert metrics["unburned_fuel_in_cylinder_terminal_kg"] >= 0.0


def test_fuel_coupled_output_uses_net_piston_work_and_v5_periodicity_metadata():
    combustion = FuelCoupledCombustionV1(
        (WiebeComponent(1.0, 40.0, 5.0, 2.0),),
        ignition_timing_deg=0.0, combustion_efficiency=.8)
    engine = _internal_cycle_fixture(fuel_coupled_combustion=combustion,
                                     open_end_plenum_v2=True)
    start = engine.snapshot()
    _advance_cycle_fixture(engine, 360.0)
    primary = make_integrated_cycle_primary(engine, start, engine.snapshot(), 1)
    model = MechanicalLossModel((LossTerm(
        "loss", "piston_ring", "SYNTHETIC_ASSUMPTION", mep_pa=1000.0),))
    output = make_integrated_engineering_output(primary, mechanical_loss_model=model)
    metrics = output["cycle_metrics"]
    obs = primary["observables"]

    assert output["schema"] == "MOTORSIM_ENGINEERING_OUTPUTS_V5"
    assert metrics["cylinder_indicated_work_j"]["value"] == pytest.approx(
        obs["cylinder_indicated_work_J"])
    assert metrics["crankcase_gas_work_j"]["value"] == pytest.approx(
        obs["crankcase_gas_work_J"])
    assert metrics["net_piston_gas_work_j"]["value"] == pytest.approx(
        obs["net_piston_gas_work_J"])
    assert metrics["brake_work_j"]["status"] == "UNDEFINED"
    assert metrics["brake_work_j"]["periodicity_dependency"] == "REQUIRED"
    assert output["claims"]["periodicity"] == "NOT_EVALUATED"
    assert validate_integrated_engineering_output_v5(output) == output
    periodic_primary = deepcopy(primary)
    periodic_primary["periodicity_evidence"] = {
        "status": "PERIOD_1",
        "configuration_hash": primary["configuration_hash"],
        "terminal_cycle": primary["cycle_index"],
        "detector_sha256": "a" * 64,
    }
    periodic_output = make_integrated_engineering_output(
        periodic_primary, mechanical_loss_model=model,
        periodicity_status="PERIOD_1")
    periodic_metrics = periodic_output["cycle_metrics"]
    displacement = primary["swept_displacement_m3"]
    assert periodic_metrics["brake_work_j"]["value"] == pytest.approx(
        obs["net_piston_gas_work_J"] - 1000.0 * displacement)
    assert periodic_metrics["bsfc_g_kwh"]["status"] == "UNDEFINED"
    assert validate_integrated_engineering_output_v5(periodic_output) == periodic_output
    with pytest.raises(ValueError, match="differs from the frozen engine geometry"):
        make_integrated_engineering_output(
            primary, displacement_m3=1e-3, mechanical_loss_model=model)


def test_integrated_engine_config_rejects_unserializable_geometry_contract():
    with pytest.raises(ValueError, match="slider-crank and generic-port"):
        _case().configuration_dict()

    malformed = json.loads(_internal_cycle_fixture().configuration_json())
    malformed["geometry_contract"] = "CALLBACK_V1"
    with pytest.raises(ValueError, match="configuration schema is invalid"):
        IntegratedEngine2T.from_configuration_dict(malformed)


def test_internal_cycle_fixture_supports_frozen_rpm_and_nested_mesh_levels():
    engine = _internal_cycle_fixture(
        fixture_name="mesh-level-check", rpm=4000.0, transfer_cells=8,
        exhaust_cell_length_m=.05, transfer_ids=("primary", "secondary"),
        with_reed=False, open_end_plenum_v2=True)
    config = engine.configuration_dict()
    restored = IntegratedEngine2T.from_configuration_dict(config)

    assert engine.reference_rpm == 4000.0
    assert len([duct for duct in config["ducts"]
                if duct["role"] == "transfer"]) == 2
    assert all(len(duct["mesh"]["volumes"]) == 8 for duct in config["ducts"]
               if duct["role"] == "transfer")
    assert len(next(duct["mesh"]["volumes"] for duct in config["ducts"]
                    if duct["role"] == "exhaust")) > 5
    assert config["geometry_identity"]["intake_donor_species_provenance"] == \
        "SYNTHETIC_ASSUMPTION"
    assert config["atmosphere_species"] == [.98, .02, 0.0, 0.0]
    assert restored.configuration_dict() == config


def test_integrated_engine_rejects_live_configuration_drift():
    system = _internal_cycle_fixture()
    system.thermal_locations["cylinder-wall"] = "crankcase"
    with pytest.raises(ValueError, match="configuration changed after construction"):
        system.configuration_json()
    with pytest.raises(ValueError, match="configuration changed after construction"):
        system.step(1e-6, .01)


def test_integrated_duct_rejects_mutable_mesh_arrays():
    mutable_mesh = Mesh([0.0, 1.0], [1.0, 1.0], [1.0], [0.5])
    with pytest.raises(ValueError, match="immutable tuples"):
        DuctPath2T("mutable", mutable_mesh, "intake").validate()
