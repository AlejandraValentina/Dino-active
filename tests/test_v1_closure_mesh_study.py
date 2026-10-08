from scripts.v1_closure_mesh_study import _pairwise


def _row(**overrides):
    value = {
        "peak_cylinder_pressure_Pa": 100.0,
        "retained_fresh_air_kg": 1.0,
        "trapped_fuel_kg": .1,
        "cylinder_indicated_work_J": 10.0,
        "mass_residual_fraction": 0.0,
        "energy_residual_fraction": 0.0,
    }
    return {**value, **overrides}


def test_v1_mesh_study_uses_preregistered_symmetric_two_percent_metrics():
    exact = _pairwise(_row(peak_cylinder_pressure_Pa=98.0), _row())
    assert exact["observables"]["peak_cylinder_pressure_Pa"]["pass"] is True
    assert exact["observables"]["peak_cylinder_pressure_Pa"][
        "relative_difference"] == .02

    outside = _pairwise(_row(), _row(peak_cylinder_pressure_Pa=103.0))
    assert outside["observables"]["peak_cylinder_pressure_Pa"]["pass"] is False


def test_v1_mesh_study_residual_comparison_is_signed_and_ledger_scaled():
    at_limit = _pairwise(
        _row(mass_residual_fraction=-.01),
        _row(mass_residual_fraction=.01))
    assert at_limit["observables"]["mass_residual_fraction"][
        "absolute_ledger_scale_fraction_difference"] == .02
    assert at_limit["observables"]["mass_residual_fraction"]["pass"] is True

    beyond = _pairwise(
        _row(energy_residual_fraction=-.011),
        _row(energy_residual_fraction=.01))
    assert beyond["observables"]["energy_residual_fraction"]["pass"] is False
