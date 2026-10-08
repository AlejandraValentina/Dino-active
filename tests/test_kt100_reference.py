import copy

import pytest

from motorsim.kt100_reference import (
    ACADEMIC_SOURCE, CLAIMS_PROHIBITED, DERIVED, DOCUMENTED, FIXTURE_ID,
    REFERENCE_CASE_STATUS, REFERENCE_ID, SIMULATION_ID, SYNTHETIC, UNKNOWN,
    build_fixture_config, build_provenance_manifest, canonical_json,
    cycle_frequency_hz, displacement_cm3, fixture_project,
    indicated_power_2t_w, indicated_torque_equivalent_nm,
    mean_piston_speed_m_s, piston_area_mm2, slider_crank_volume_cm3,
    validate_fixture_config, validate_provenance,
)
from motorsim.project_case import execution_errors
from motorsim.simulation import Model
from motorsim.kt100_reference import fixture_case


def test_manifest_provenance_is_complete_and_unknowns_are_not_values():
    manifest = build_provenance_manifest()
    validate_provenance(manifest)
    entries = [*manifest["parameters"].values(),
               *manifest["derived_parameters"].values(),
               *manifest["fixture_assumptions"].values()]
    assert all(row["status"] in {DOCUMENTED, DERIVED, SYNTHETIC, UNKNOWN}
               for row in entries)
    assert all(row["value"] is None for row in entries if row["status"] == UNKNOWN)
    assert all({"reason", "expected_sensitivity", "strongly_affects_results",
                "conceptual_origin"} <= row.keys()
               for row in manifest["fixture_assumptions"].values())


def test_provenance_guard_rejects_unknown_value_and_unreferenced_documented_claim():
    manifest = build_provenance_manifest()
    manifest["parameters"]["operating_rpm_range"]["value"] = [6000, 14000]
    with pytest.raises(ValueError, match="unknown parameter has a value"):
        validate_provenance(manifest)
    manifest = build_provenance_manifest()
    manifest["parameters"]["bore_mm"]["source"] = None
    with pytest.raises(ValueError, match="lacks source"):
        validate_provenance(manifest)


def test_documentary_reference_and_fixture_are_distinct_and_variant_bound():
    manifest = build_provenance_manifest()
    assert manifest["reference_case_id"] == REFERENCE_ID
    assert manifest["reference_kind"] == REFERENCE_CASE_STATUS
    assert manifest["fixture_id"] == FIXTURE_ID
    assert manifest["selected_variant"].startswith("Yamaha KT100SP")
    assert manifest["parameters"]["compression_ratio"]["value"] == 9.0
    assert manifest["parameters"]["compression_ratio"]["status"] == DOCUMENTED
    assert manifest["fixture_assumptions"]["connecting_rod_length_mm"]["status"] == SYNTHETIC
    assert len(manifest["source_reconciliation"]["not_merged"]) == 2
    assert ACADEMIC_SOURCE in manifest["sources"]["gore_2024_thesis"]["url"]


def test_displacement_and_independently_derived_kt100_geometry():
    exact = displacement_cm3(52.0, 46.0)
    assert exact == pytest.approx(97.6909651560)
    # If whole-mm dimensions are rounded to nearest mm, the declared value lies
    # within that dimension-rounding envelope. Yamaha gives no precision rule.
    assert displacement_cm3(51.5, 45.5) <= 97.6 <= displacement_cm3(52.5, 46.5)
    assert piston_area_mm2(52.0) == pytest.approx(2123.7166338267)
    assert slider_crank_volume_cm3(0, bore_mm=52, stroke_mm=46,
        rod_length_mm=100, compression_ratio=9) == pytest.approx(exact/8)
    assert slider_crank_volume_cm3(180, bore_mm=52, stroke_mm=46,
        rod_length_mm=100, compression_ratio=9) == pytest.approx(exact+exact/8)
    assert slider_crank_volume_cm3(360, bore_mm=52, stroke_mm=46,
        rod_length_mm=100, compression_ratio=9) == pytest.approx(exact/8)


def test_rpm_derived_metrics_and_two_stroke_work_power_conversion():
    assert mean_piston_speed_m_s(46.0, 10000) == pytest.approx(15.3333333333)
    assert cycle_frequency_hz(10000, "2T") == pytest.approx(166.6666667)
    assert cycle_frequency_hz(10000, "4T") == pytest.approx(83.3333333)
    assert indicated_power_2t_w(12.0, 10000) == pytest.approx(2000.0)
    assert indicated_torque_equivalent_nm(2*3.141592653589793) == pytest.approx(1.0)


def test_fixture_is_complete_traceable_and_deterministic():
    manifest = build_provenance_manifest()
    first = build_fixture_config()
    second = build_fixture_config()
    validate_fixture_config(first, manifest)
    assert canonical_json(first) == canonical_json(second)
    assert {"engine_geometry_and_project", "cylinder", "crank_slider", "crankcase",
            "intake", "transfer", "exhaust", "combustion", "thermodynamics",
            "boundaries", "solver"} <= first.keys()
    assert first["solver"]["integrator"] == "existing adaptive RK4 (two-half-step error estimate)"
    assert first["solver"]["profile"] == "B"
    assert first["solver"]["CFL"] == "NOT_APPLICABLE_ZERO_D"
    assert first["solver"]["restart_api"] == "NOT_SUPPORTED_BY_EXISTING_0D_APPLICATION_RUNNER"
    assert first["engine_geometry_and_project"]["model"] == "KT100_MODEL_FIXTURE_V1"
    states = first["boundaries"]["initial_states_pty"]
    assumptions = manifest["fixture_assumptions"]
    assert states[1][0] == assumptions["initial_crankcase_pressure_Pa"]["value"] == 120000.0
    assert states[2][0] == assumptions["initial_cylinder_pressure_Pa"]["value"] == 140000.0
    mapping = first["provenance_parameter_map"]
    assert mapping["boundaries.initial_states_pty[1].pressure_Pa"].endswith("initial_crankcase_pressure_Pa")
    assert mapping["boundaries.initial_states_pty[2].pressure_Pa"].endswith("initial_cylinder_pressure_Pa")
    fractions = assumptions["initial_fresh_fraction_by_cv"]["value"]
    assert [row[2] for row in states] == fractions
    for index in range(4):
        assert mapping[f"boundaries.initial_states_pty[{index}].fresh_fraction"].endswith(
            f"initial_fresh_fraction_by_cv[{index}]")
    assert first["boundaries"]["reservoir_states_pty"][0][2] == assumptions[
        "atmospheric_fresh_marker_fraction"]["value"] == 1.0
    assert mapping["boundaries.reservoir_states_pty[0].fresh_fraction"].endswith(
        "atmospheric_fresh_marker_fraction")
    assert first["boundaries"]["reservoir_states_pty"][1][2] == assumptions[
        "exhaust_reservoir_fresh_marker_fraction"]["value"] == 0.0
    assert mapping["boundaries.reservoir_states_pty[1].fresh_fraction"].endswith(
        "exhaust_reservoir_fresh_marker_fraction")
    assert "P5-C/P6/P7" not in fixture_case(9000).model
    assert first["combustion"]["fuel_chemistry"] == "NOT_MODELED"
    assert first["claims"]["experimental_validation"] == "NOT_PERFORMED"
    assert first["claims"]["predictive_validation"] == "NOT_CLAIMED"
    assert first["claims"]["p9_status_effect"] == "NONE"
    assert all(item in first["claims"]["prohibited"] for item in CLAIMS_PROHIBITED)
    assert SIMULATION_ID == "KT100_REFERENCE_SIMULATION"


def test_fixture_project_is_valid_for_existing_2t_geometry_path():
    project = fixture_project()
    assert execution_errors(project) == []
    assert project.bore_mm == 52.0 and project.stroke_mm == 46.0
    assert project.compression_ratio == 9.0


def test_fixture_case_constructs_existing_zero_d_application_model_without_new_physics():
    case = fixture_case(9000)
    model = Model(case, external_band_pa=100)
    assert model.case.project_geometry.bore_mm == 52.0
    assert model.case.project_geometry.stroke_mm == 46.0
    assert model.layout.cv == ("I", "K", "C", "E")
    assert model.layout.period == 360


def test_frozen_p9_status_is_guarded_in_fixture_config():
    config = build_fixture_config()
    poisoned = copy.deepcopy(config)
    poisoned["claims"]["p9_status_effect"] = "P9_PASS"
    with pytest.raises(ValueError, match="cannot modify P9"):
        validate_fixture_config(poisoned, build_provenance_manifest())
