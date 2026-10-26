"""Guard the donor-only species work optimization against the old formula."""

import pytest

from motorsim.p6_species import donor_species, validate_species
from test_integrated_2t import _case


@pytest.mark.parametrize("mass_flux", [0.25, -0.25, 0.0])
def test_face_species_flux_matches_preoptimization_formula_exactly(mass_flux):
    engine = _case()
    left = (0.8, 0.1, 0.1, 0.0)
    right = (0.1, 0.2, 0.3, 0.4)
    left_mass = sum(left)
    right_mass = sum(right)

    old_left = engine._fractions(left, left_mass)
    old_right = engine._fractions(right, right_mass)
    expected = donor_species(mass_flux, old_left, old_right)

    actual = engine._face_species_flux(
        mass_flux, left, left_mass, right, right_mass)

    assert actual == expected


def test_positive_flux_uses_left_donor_and_negative_flux_uses_right_donor():
    engine = _case()
    left = (0.8, 0.1, 0.1, 0.0)
    right = (0.1, 0.2, 0.3, 0.4)

    forward = engine._face_species_flux(0.25, left, 1.0, right, 1.0)
    reverse = engine._face_species_flux(-0.25, left, 1.0, right, 1.0)

    assert forward == donor_species(0.25, engine._fractions(left, 1.0),
                                    engine._fractions(right, 1.0))
    assert reverse == donor_species(-0.25, engine._fractions(left, 1.0),
                                     engine._fractions(right, 1.0))


def test_species_validation_fast_tuple_and_general_conversion_agree():
    expected = (0.5, 0.2, 0.2, 0.1)

    assert validate_species(expected, 1.0) == expected
    assert validate_species([0, 0.5, 0.2, 0.2, 0.1][1:], 1) == expected


@pytest.mark.parametrize("values", [
    (float("nan"), 0.0, 0.0, 0.0),
    (float("inf"), 0.0, 0.0, 0.0),
    (-1e-6, 0.5, 0.5, 0.0),
])
def test_species_validation_fast_tuple_keeps_fail_closed_checks(values):
    with pytest.raises(ValueError):
        validate_species(values, sum(values))
