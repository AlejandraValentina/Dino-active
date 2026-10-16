from __future__ import annotations

import pytest

from motorsim.engine_project import load_project
from motorsim.mesh_study_v1 import (build_refinement_matrix,
    compare_phase_series, compare_resolution_receipts, extract_primary_phase_series,
    make_resolution_receipt)
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_refinement_matrix_preserves_geometry_and_extensive_initial_state():
    project = load_project(ROOT / "examples/projects/dino-2t-exhaust-comparison.dino2t.json")
    source = project["variants"]["Escape original"]
    matrix = build_refinement_matrix(source)
    assert matrix["status"] == "SETUP_ONLY_NOT_EXECUTED"
    assert matrix["solver_steps"] == 0
    assert matrix["spatial_independence"] == "NOT_EVALUATED"
    assert matrix["acceptance_thresholds"] == "NOT_REGISTERED"
    rows = matrix["resolutions"]
    assert [row["cells_per_section"] for row in rows] == [1, 2, 4, 8]
    assert len({row["configuration_sha256"] for row in rows}) == 4
    assert len({row["geometry"]["total_length_m"] for row in rows}) == 1
    assert max(row["conservative_remap"]["relative_error"]["mass_kg"] for row in rows) < 1e-12
    assert max(row["conservative_remap"]["relative_error"]["total_energy_J"] for row in rows) < 1e-12
    assert max(max(row["conservative_remap"]["relative_error"]["species_inventory_by_index"])
               for row in rows) < 1e-12


def test_resolution_receipts_report_deltas_without_acceptance_or_interpolation():
    common = {"admissible": True, "cycle_index": 2,
        "observables": {"work_J": 2.0, "fresh_delivery_kg": .01},
        "conservation": {"mass_residual_kg": 1e-12},
        "terminal_state": {"ducts": {"exhaust": [[1.0, 0.0, 100000.0]]}},
        "periodicity": {"status": "NOT_EVALUATED"}}
    audit = {"status": "PASS", "recomputed": True}
    left = make_resolution_receipt(configuration_sha256="a" * 64,
        cells_per_section=1, primary=common, primary_sha256="b" * 64,
        audit=audit, provenance={"source": "fixture"})
    right_primary = {**common, "observables": {"work_J": 2.1, "fresh_delivery_kg": .011}}
    right = make_resolution_receipt(configuration_sha256="c" * 64,
        cells_per_section=2, primary=right_primary, primary_sha256="d" * 64,
        audit=audit, provenance={"source": "fixture"})
    comparison = compare_resolution_receipts(left, right)
    assert comparison["common_scalar_observables"]["work_J"]["absolute_delta"] == pytest.approx(.1)
    assert comparison["interpolation"] == "NONE"
    assert comparison["spatial_independence"] == "NOT_EVALUATED"
    assert comparison["assessment"] == "DIFFERENCES_RECORDED_NO_REGISTERED_ACCEPTANCE_TOLERANCE"
    with pytest.raises(ValueError, match="passing recomputed independent audit"):
        make_resolution_receipt(configuration_sha256="a" * 64,
            cells_per_section=1, primary=common, primary_sha256="b" * 64,
            audit={"status": "PASS", "recomputed": False}, provenance={})


def test_phase_comparison_interpolates_only_offline_and_preserves_native_signals():
    left = {"angles_deg": [0.0, 90.0, 180.0], "values": [1.0, 2.0, 3.0]}
    right = {"angles_deg": [0.0, 180.0], "values": [1.0, 5.0]}
    result = compare_phase_series(left, right, [45.0, 90.0, 135.0])
    assert result["comparison_operator"] == "PIECEWISE_LINEAR_OFFLINE_ONLY"
    assert result["left_native_signal"] == left
    assert result["right_native_signal"] == right
    assert result["differences"][1]["right"] == pytest.approx(3.0)
    assert result["spatial_independence"] == "NOT_EVALUATED"
    with pytest.raises(ValueError, match="strictly increasing"):
        compare_phase_series({"angles_deg": [0.0, 0.0], "values": [1.0, 2.0]},
                             right, [0.0])


def test_native_primary_phase_extraction_uses_saved_states_and_signed_fluxes():
    def step(start, end, mass, pressure, flow):
        state = {"chambers": {"cylinder": [1.0, pressure / .4, 1.0],
                              "crankcase": [1.0, pressure / .4, 1.0]},
                 "ducts": {"exhaust": [[1.0, 0.0, pressure, 1.0]]}}
        return {"angle_start_deg": start, "angle_end_deg": end,
            "stage_states": [state, state, state],
            "stage_face_fluxes": [{"exhaust": {"left": [flow, 0.0, 0.0],
                                                 "right": [-flow, 0.0, 0.0]}},
                                   {"exhaust": {"left": [0.0, 0.0, 0.0],
                                                 "right": [0.0, 0.0, 0.0]}}]}
    primary = {"admissible": True, "cycle_start_deg": 0.0, "cycle_end_deg": 360.0,
        "eos_gamma": 1.4,
        "trajectory": [step(0.0, 180.0, 1.0, 100000.0, 0.5),
                       step(180.0, 360.0, 1.0, 120000.0, -0.25)]}
    cyl = extract_primary_phase_series(primary, "cylinder_pressure_pa")
    cell = extract_primary_phase_series(primary, "duct:exhaust:cell:0:pressure_pa")
    flow = extract_primary_phase_series(primary, "flow:exhaust:left")
    assert cyl["angles_deg"] == [0.0, 180.0]
    assert cyl["values"] == pytest.approx([100000.0, 120000.0])
    assert cell["values"] == pytest.approx([100000.0, 120000.0])
    assert flow["unit"] == "kg/s"
    assert flow["values"] == pytest.approx([0.5, -0.25])
    assert flow["interpolation"] == "NONE"
