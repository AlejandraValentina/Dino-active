import pytest

from scripts.diagnostics.analyze_postopen_wave_transport_v1 import (
    compare_integrated_flux,
    maximum_normalized_conservation_residual,
)


def test_integrated_flux_comparison_reports_unsigned_and_signed_values():
    result = compare_integrated_flux({"intake": {"left": {"mass": [2.0, -1.0]}}},
                                     {"intake": {"left": {"mass": [1.0, -2.0]}}})

    assert result["intake.left.mass[0]"]["absolute_difference"] == 1.0
    assert result["intake.left.mass[0]"]["symmetric_relative_difference"] == .5
    assert result["intake.left.mass[1]"]["absolute_difference"] == 1.0
    assert result["intake.left.mass[1]"]["symmetric_relative_difference"] == .5


def test_integrated_flux_comparison_rejects_topology_mismatch():
    with pytest.raises(ValueError, match="topology differs"):
        compare_integrated_flux({"a": 1.0}, {"b": 1.0})


def test_conservation_residual_is_normalized_with_registered_scales():
    report = {
        "mass": {"initial": 1.0, "final": 2.0, "residual": 2e-12},
        "energy": {"initial": 100.0, "final": 200.0, "residual": 1e-9},
        "species": {"fresh": {"residual": -1e-12}},
    }

    assert maximum_normalized_conservation_residual(report) == pytest.approx(5e-12)
