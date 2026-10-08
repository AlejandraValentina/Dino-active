"""Producer and P5-C wiring checks for the preregistered KT100 V2 variant."""
import copy
import json

from motorsim.gas1d.boundary import Boundary
from motorsim.gas1d.open_end_plenum_v2 import OpenEndPlenumV2Boundary
from motorsim.reference_harness.config import validate_config
from motorsim.reference_harness.runtime import build_system
from motorsim.reference_harness.evidence import _duct_observables
from scripts.build_kt100_hybrid_fixture_v2 import build as build_base
from scripts.build_kt100_open_end_plenum_v2 import build as build_open


def test_v2_producer_changes_only_boundary_identity_and_provenance():
    base = build_base()
    new = build_open()
    assert new["fixture_id"] == "KT100_HYBRID_MODEL_FIXTURE_V2_OPEN_END_PLENUM_V2"
    assert new["engine"] == base["engine"]
    assert new["transfer_ducts"] == base["transfer_ducts"]
    assert new["initial_states"] == base["initial_states"]
    assert new["numerics"] == base["numerics"]
    assert new["operating_points_rpm"] == base["operating_points_rpm"]
    assert new["convergence_contract"] == base["convergence_contract"]
    expected_boundaries = copy.deepcopy(base["boundaries"])
    expected_boundaries["external_boundary_capability"] = "OPEN_END_PLENUM_V2"
    expected_boundaries["external_boundary_provenance"] = "SYNTHETIC_ASSUMPTION"
    assert new["boundaries"] == expected_boundaries
    assert new["boundary_model"]["provenance"] == "SYNTHETIC_ASSUMPTION"
    assert "not calibrated WB40" in new["boundary_model"]["description"]


def test_v2_campaign_config_validates_and_keeps_fixed_contract():
    config = build_open()
    parsed = validate_config(config)
    assert parsed["external_boundary_capability"] == "OPEN_END_PLENUM_V2"
    assert parsed["cfl"] == 0.4
    assert parsed["dx_target_m"] == 0.03
    assert parsed["max_cycles"] == 400
    invalid = copy.deepcopy(config)
    invalid["boundary_model"]["provenance"] = "MEASURED"
    try:
        validate_config(invalid)
    except ValueError as error:
        assert "synthetic boundary-model identity" in str(error)
    else:
        raise AssertionError("unmarked V2 boundary configuration was accepted")


def test_kt100_runtime_selects_v2_at_intake_and_exhaust_edges():
    config = build_open()
    system, _, _ = build_system(config)
    gas = system.gas
    assert isinstance(gas.external_boundary_model, OpenEndPlenumV2Boundary)
    assert gas.core.external_boundary_model is gas.external_boundary_model
    intake_state = gas.eos.primitive(gas.core.intake.conservative()[0])
    _, external_trace = gas.core._rhs(gas.core._state(), gas.angle)
    expected_intake, _, _ = gas.external_boundary_model.flux(intake_state, -1, gas.eos)
    intake_area = gas.core.intake.mesh.areas[0]
    assert external_trace["external"] == tuple(intake_area * value for value in expected_intake)
    exhaust_q = list(gas.exhaust.conservative())
    exhaust_q[-1] = gas.eos.conservative((
        120000.0 / (gas.eos.R * 500.0), 0.0, 120000.0, 0.0))
    cylinder_q = gas.core._state()[1]
    exhaust_rhs, _, external, _ = gas._exhaust_rhs(
        exhaust_q, cylinder_q, 0.0)
    last = gas.eos.primitive(exhaust_q[-1])
    expected, _, _ = gas.external_boundary_model.flux(last, 1, gas.eos)
    legacy, _, _ = Boundary("outflow").flux(last, 1, gas.eos)
    area = gas.exhaust_mesh.areas[-1]
    assert external == tuple(area * value for value in expected)
    assert external != tuple(area * value for value in legacy)
    assert len(exhaust_rhs) == len(exhaust_q)


def test_cycle_evidence_maps_transfer_output_names_to_p6_species_names():
    system, _, _ = build_system(build_open())
    gas = system.gas
    for output_name, path in (
            ("transfer1", gas.core.transfers[0]),
            ("transfer2", gas.core.transfers[1])):
        rows = _duct_observables(system, output_name, path)
        assert len(rows) == len(path.cells)
        assert all(len(row["species_mass_fractions"]) == 4 for row in rows)


def test_p6_external_species_donors_follow_actual_boundary_flow_direction():
    system, _, _ = build_system(build_open())
    state = {"intake": [(1.0, 2.0, 3.0, 4.0)],
             "exhaust": [(4.0, 3.0, 2.0, 1.0)]}
    record = {
        "core_interfaces": [None, None],
        "stage_external": [(2.0, 0.0, 0.0, 0.0),
                           (-2.0, 0.0, 0.0, 0.0)],
        "stage_exhaust_external": [(3.0, 0.0, 0.0, 0.0),
                                   (-3.0, 0.0, 0.0, 0.0)],
    }
    inflow = system._external_trace(0, record, state)
    backflow = system._external_trace(1, record, state)
    assert inflow["atmosphere_intake"]["donor_component"] == "atmosphere"
    assert inflow["atmosphere_intake"]["species_flux"]["fresh_air"] == 2.0
    assert inflow["exhaust_atmosphere"]["donor_component"] == "exhaust"
    assert inflow["exhaust_atmosphere"]["species_flux"]["fresh_air"] == 1.2
    assert backflow["atmosphere_intake"]["donor_component"] == "intake"
    assert backflow["atmosphere_intake"]["species_flux"]["fresh_air"] == -0.2
    assert backflow["exhaust_atmosphere"]["donor_component"] == "atmosphere"
    assert backflow["exhaust_atmosphere"]["species_flux"]["fresh_air"] == -3.0


def test_frozen_v2_source_config_file_matches_deterministic_producer():
    config = json.loads(open("configs/fixtures/kt100_open_end_plenum_v2.json", encoding="utf-8").read())
    assert config == build_open()
