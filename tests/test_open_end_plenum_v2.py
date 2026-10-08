"""Preregistered analytic checks for the additive OPEN_END_PLENUM_V2 model."""
from math import isfinite, sqrt

import pytest

from motorsim.gas1d.boundary import Boundary
from motorsim.gas1d.eos import IdealGas, InvalidState
from motorsim.gas1d.open_end_plenum_v2 import OpenEndPlenumV2Boundary


EOS = IdealGas()
P0 = 101325.0
T0 = 300.0


def state_pt(p, t, u=0.0, *, eos=EOS, marker=0.25):
    return (p / (eos.R * t), u, p, marker)


def entropy_matched_state(p, *, eos=EOS, p0=P0, t0=T0, w=0.0):
    rho0 = p0 / (eos.R * t0)
    k0 = p0 / rho0 ** eos.gamma
    rho = (p / k0) ** (1.0 / eos.gamma)
    return rho, w, p, 0.37


def test_subsonic_equal_entropy_reduces_to_frozen_reservoir_v1():
    eos = EOS
    v2 = OpenEndPlenumV2Boundary(P0, T0, 1.0)
    v1 = Boundary("reservoir", p0=P0, T0=T0, Y0=1.0)
    for pressure in (0.8 * P0, 1.2 * P0):
        interior = entropy_matched_state(pressure)
        actual = v2.face_state(interior, 1, eos)
        expected = v1.face_state(interior, 1, eos)
        assert actual == pytest.approx(expected, rel=2e-12, abs=2e-12)


@pytest.mark.parametrize("temperature", [245.0, 300.0, 415.0])
def test_analytic_fixed_point_and_reversal_are_contact_aware(temperature):
    boundary = OpenEndPlenumV2Boundary(P0, T0, 1.0)
    interior = state_pt(P0, temperature)
    face = boundary.resolve(interior, 1, EOS)
    assert face.branch == "subsonic_outflow"
    assert face.normal_velocity == pytest.approx(0.0, abs=2e-12)
    assert face.normal_mass_flux == pytest.approx(0.0, abs=2e-12)
    assert face.state[2] == P0
    assert face.interior_contact_state[0] == pytest.approx(interior[0])
    assert face.reservoir_donor is False


@pytest.mark.parametrize("temperature", [250.0, 300.0, 410.0])
def test_reversal_continuity_across_unequal_temperatures(temperature):
    boundary = OpenEndPlenumV2Boundary(P0, T0, 1.0)
    eps = 1e-7
    at = state_pt(P0, temperature)
    low_p = state_pt(P0 * (1.0 - eps), temperature)
    high_p = state_pt(P0 * (1.0 + eps), temperature)
    f0 = boundary.resolve(at, 1, EOS)
    fi = boundary.resolve(low_p, 1, EOS)
    fo = boundary.resolve(high_p, 1, EOS)
    assert fi.branch == "subsonic_inflow"
    assert fo.branch == "subsonic_outflow"
    assert abs(fi.normal_velocity) < 0.02
    assert abs(fo.normal_velocity) < 0.02
    assert abs(fi.state[2] - fo.state[2]) < 0.1
    assert abs(fi.normal_mass_flux) < 1e-4
    assert abs(fo.normal_mass_flux) < 1e-4
    assert f0.normal_mass_flux == pytest.approx(0.0, abs=2e-12)
    if temperature != T0:
        assert fi.state[0] != pytest.approx(fi.interior_contact_state[0])


def test_subsonic_inflow_energy_uses_reservoir_stagnation_enthalpy():
    boundary = OpenEndPlenumV2Boundary(P0, T0, 1.0)
    face = boundary.resolve(state_pt(0.75 * P0, 230.0), 1, EOS)
    assert face.branch == "subsonic_inflow"
    assert face.reservoir_donor
    rho, velocity, pressure, _ = face.state
    temperature = pressure / (rho * EOS.R)
    h_total = EOS.cp * temperature + 0.5 * velocity * velocity
    assert h_total == pytest.approx(EOS.cp * T0, rel=2e-12)
    assert face.incoming_total_enthalpy == EOS.cp * T0


def test_inflow_choking_uses_ideal_critical_state_and_caps_flux():
    boundary = OpenEndPlenumV2Boundary(P0, T0, 1.0)
    face = boundary.resolve(state_pt(0.02 * P0, 220.0), 1, EOS)
    assert face.branch == "choked_inflow"
    critical_ratio = (2.0 / (EOS.gamma + 1.0)) ** (EOS.gamma / (EOS.gamma - 1.0))
    assert face.state[2] == pytest.approx(P0 * critical_ratio)
    assert face.normal_velocity == pytest.approx(-EOS.sound_speed(face.state))
    temperature = face.state[2] / (face.state[0] * EOS.R)
    assert EOS.cp * temperature + 0.5 * face.normal_velocity ** 2 == pytest.approx(EOS.cp * T0)


def test_outflow_choking_uses_interior_entropy_and_sonic_cap():
    boundary = OpenEndPlenumV2Boundary(0.01 * P0, T0, 1.0)
    interior = state_pt(100.0 * P0, 300.0)
    face = boundary.resolve(interior, 1, EOS)
    assert face.branch == "choked_outflow"
    assert face.normal_velocity == pytest.approx(EOS.sound_speed(face.state))
    k_i = interior[2] / interior[0] ** EOS.gamma
    assert face.state[2] / face.state[0] ** EOS.gamma == pytest.approx(k_i)


def test_acoustic_pressure_reflection_is_unit_magnitude_and_sign_reversing():
    # An outgoing isentropic acoustic wave has du=dp/(rho*a). The pressure
    # outlet fixes dp_face=0; its reflected wave must therefore be -dp_inc,
    # with total face velocity 2*dp_inc/(rho*a).
    rho0 = P0 / (EOS.R * T0)
    a0 = sqrt(EOS.gamma * P0 / rho0)
    boundary = OpenEndPlenumV2Boundary(P0, T0, 1.0)
    for relative_amplitude in (1e-6, 1e-7, 1e-8):
        dp_incident = relative_amplitude * P0
        pressure = P0 + dp_incident
        temperature = T0 * (pressure / P0) ** ((EOS.gamma - 1.0) / EOS.gamma)
        incident_velocity = dp_incident / (rho0 * a0)
        face = boundary.resolve(state_pt(pressure, temperature, incident_velocity), 1, EOS)
        dp_face = face.state[2] - P0
        dp_reflected = dp_face - dp_incident
        assert dp_face == pytest.approx(0.0, abs=1e-12)
        assert dp_reflected / dp_incident == pytest.approx(-1.0, abs=1e-7)
        assert face.state[1] == pytest.approx(2.0 * dp_incident / (rho0 * a0), rel=1e-6)


def test_flipped_normal_mirrors_velocity_mass_flux_and_pressure_reaction():
    boundary = OpenEndPlenumV2Boundary(P0, T0, 1.0)
    interior = state_pt(0.8 * P0, 280.0, 0.0)
    left = boundary.resolve(interior, -1, EOS)
    right = boundary.resolve(interior, 1, EOS)
    assert left.branch == right.branch
    assert left.state[0] == pytest.approx(right.state[0])
    assert left.state[2] == pytest.approx(right.state[2])
    assert left.state[1] == pytest.approx(-right.state[1])
    assert left.normal_mass_flux == pytest.approx(right.normal_mass_flux)
    assert left.pressure_reaction_per_area == pytest.approx(-right.pressure_reaction_per_area)


def test_four_species_donor_follows_signed_mass_flux():
    reservoir = (1.0, 0.0, 0.0, 0.0)
    interior = (0.1, 0.2, 0.3, 0.4)
    for p, expect_reservoir in ((0.8 * P0, True), (1.2 * P0, False)):
        face = OpenEndPlenumV2Boundary(P0, T0).resolve(state_pt(p, T0), 1, EOS)
        donor = reservoir if face.normal_mass_flux < 0 else interior
        expected = reservoir if expect_reservoir else interior
        assert donor == expected
        assert face.reservoir_donor is expect_reservoir
        species_flux = tuple(face.normal_mass_flux * x for x in donor)
        assert sum(species_flux) == pytest.approx(face.normal_mass_flux)


def test_pressure_reaction_and_energy_flow_identities_are_explicit():
    boundary = OpenEndPlenumV2Boundary(P0, T0, 1.0)
    for pressure in (0.7 * P0, 1.3 * P0):
        face = boundary.resolve(state_pt(pressure, 300.0), 1, EOS)
        flux, _, _ = boundary.flux(state_pt(pressure, 300.0), 1, EOS)
        assert face.pressure_reaction_per_area == pytest.approx(-face.normal * face.state[2])
        if face.reservoir_donor and face.normal_mass_flux != 0:
            normal_energy_flux = face.normal * flux[2]
            assert normal_energy_flux / face.normal_mass_flux == pytest.approx(EOS.cp * T0)


def test_deterministic_admissibility_grid():
    boundary = OpenEndPlenumV2Boundary(P0, T0, 0.8)
    for pressure_ratio in (0.02, 0.2, 0.75, 1.0, 1.4, 4.0):
        for temperature in (180.0, 300.0, 650.0):
            for velocity in (-120.0, 0.0, 120.0):
                interior = state_pt(pressure_ratio * P0, temperature, velocity)
                one = boundary.resolve(interior, 1, EOS)
                two = boundary.resolve(interior, 1, EOS)
                assert one == two
                EOS.validate(one.state)
                EOS.validate(one.interior_contact_state)
                assert all(isfinite(x) for x in one.state)
                assert all(isfinite(x) for x in one.interior_contact_state)
                assert one.state[2] > 0.0 and one.state[0] > 0.0


def test_v1_regressions_remain_frozen_and_v2_is_additive():
    assert Boundary("reservoir", p0=P0, T0=T0).kind == "reservoir"
    assert Boundary("nonreflecting", state=(P0 / (EOS.R * T0), 0.0, P0, 1.0)).kind == "nonreflecting"
    interior = (100000.0 / (EOS.R * 301.0), -0.001, 100000.0, 0.2)
    with pytest.raises(InvalidState, match="No consistent reservoir inflow branch"):
        Boundary("reservoir", p0=P0, T0=T0).flux(interior, 1, EOS)
