import copy
import pytest

from motorsim.gas1d.eos import IdealGas
from motorsim.reed import ReedPetal, ReedState
from motorsim.reed_coupling import (
    DynamicReedTwoVolumeCouplingV1, GasVolumeState4, HingedFlapGeometryV1,
)


def setup_case(p_left=120_000.0, p_right=100_000.0, *, lift=2e-4,
               velocity=0.0, damping=0.02):
    width, length = 0.02, 0.01
    geometry = HingedFlapGeometryV1(
        "synthetic-reed-interface", "1.0.0", "SYNTHETIC_ASSUMPTION",
        width, length, 2e-5, 2e-5, 1e-3, 0.7)
    petal = ReedPetal(
        "synthetic-petal", mass_kg=1e-3,
        pressure_area_m2=width * length / 2.0,
        effective_width_m=width, stiffness_n_m=10.0,
        damping_n_s_m=damping, lift_stop_m=1e-3,
        discharge_coefficient=0.7,
        provenance="SYNTHETIC_ASSUMPTION", restitution=0.0)
    eos = IdealGas()
    left_volume, right_volume = geometry.volumes_m3(lift)

    def gas_state(pressure, volume, fractions):
        temperature = 300.0
        mass = pressure * volume / (eos.R * temperature)
        energy = pressure * volume / (eos.gamma - 1.0)
        return GasVolumeState4(mass, energy,
                               tuple(mass * fraction for fraction in fractions))

    left = gas_state(p_left, left_volume, (0.8, 0.1, 0.1, 0.0))
    right = gas_state(p_right, right_volume, (0.1, 0.0, 0.6, 0.3))
    system = DynamicReedTwoVolumeCouplingV1(
        geometry, petal, left, right, ReedState(lift, velocity), eos=eos)
    return system, (geometry, petal, left, right, ReedState(lift, velocity), eos)


def test_linear_hinged_geometry_separates_flow_curtain_from_swept_volume():
    system, (geometry, petal, *_rest) = setup_case()
    assert geometry.swept_volume_area_m2 == pytest.approx(geometry.width_m * geometry.length_m / 2)
    assert petal.pressure_area_m2 == pytest.approx(geometry.swept_volume_area_m2)
    assert geometry.flow_area_m2(2e-4) == pytest.approx(0.7 * 0.02 * 2e-4)
    assert geometry.flow_area_m2(0.0) == 0.0
    left, right = geometry.volumes_m3(2e-4)
    assert left + right == pytest.approx(
        geometry.left_closed_volume_m3 + geometry.right_closed_volume_m3)
    assert system.ledger()["flow_area_m2"] == geometry.flow_area_m2(2e-4)


def test_geometry_rejects_pressure_area_mismatch_and_nonpositive_right_volume():
    _system, (geometry, petal, left, right, reed, eos) = setup_case()
    wrong = ReedPetal(**(petal.to_dict() | {"pressure_area_m2": petal.pressure_area_m2 * 1.01}))
    with pytest.raises(ValueError, match="swept-volume"):
        DynamicReedTwoVolumeCouplingV1(geometry, wrong, left, right, reed, eos=eos)
    invalid = HingedFlapGeometryV1(
        "bad", "1", "SYNTHETIC_ASSUMPTION", 0.02, 0.01, 2e-5,
        1e-8, 1e-3, 0.7)
    with pytest.raises(ValueError, match="positive"):
        invalid.validate()


def test_equal_pressure_closed_reed_is_a_fixed_point():
    system, _ = setup_case(p_left=100_000.0, p_right=100_000.0, lift=0.0)
    before = system.state
    system.step(1e-6)
    assert system.state == before


@pytest.mark.parametrize("p_left,p_right,donor", [
    (120_000.0, 100_000.0, "left"),
    (100_000.0, 120_000.0, "right"),
])
def test_forward_and_reverse_flow_use_stage_donor_and_conserve_four_species(
        p_left, p_right, donor):
    system, _ = setup_case(p_left=p_left, p_right=p_right, damping=0.0)
    before = system.ledger()
    initial = system.state
    system.step(1e-6)
    after = system.ledger()
    assert system.state != initial
    assert abs(after["mass_residual_kg"]) < 2e-15
    assert max(abs(x) for x in after["species_residual_kg"]) < 2e-15
    assert abs(after["species_sum_residual_kg"]) < 2e-15
    assert abs(after["total_energy_residual_J"]) < 1e-10
    if donor == "left":
        assert system.state[8] > initial[8]  # right receives left fresh_air
        assert system.state[9] > initial[9]  # right receives left fuel
    else:
        assert system.state[4] > initial[4]  # left receives right residual
        assert system.state[5] > initial[5]  # left receives right burned gas


def test_damping_is_explicit_in_energy_ledger_and_steps_are_stage_coupled():
    system, _ = setup_case(p_left=120_000.0, p_right=100_000.0, damping=0.02)
    initial_state = system.state
    initial_energy = system.ledger()["total_energy_residual_J"]
    system.step(1e-6)
    result = system.ledger()
    assert system.state[12:14] != initial_state[12:14]
    assert result["reed_dissipation_J"] > 0.0
    assert abs(result["total_energy_residual_J"] - initial_energy) < 1e-10


def test_rejected_out_of_domain_stage_is_transactional():
    system, _ = setup_case(lift=9.9e-4, velocity=1.0, damping=0.0)
    before = system.state
    with pytest.raises(ValueError):
        system.step(1e-4)
    assert system.state == before


@pytest.mark.parametrize("p_left,p_right,lift", [
    (100_000.0, 120_000.0, 0.0),
    (150_000.0, 100_000.0, 1e-3),
])
def test_unsupported_stop_contact_rejects_instead_of_constraining_petals(
        p_left, p_right, lift):
    system, _ = setup_case(p_left=p_left, p_right=p_right, lift=lift,
                           damping=0.0)
    before = system.state
    with pytest.raises(ValueError, match="versioned event contract"):
        system.step(1e-8)
    assert system.state == before


def test_checkpoint_restore_replays_exactly_and_rejects_configuration_drift():
    system, config = setup_case()
    for _ in range(5):
        system.step(1e-7)
    checkpoint = system.checkpoint()
    restored, (geometry, petal, _left, _right, reed, eos) = setup_case()
    restored.restore(copy.deepcopy(checkpoint))
    assert restored.state == system.state
    system.step(1e-7)
    restored.step(1e-7)
    assert restored.state == system.state
    assert restored.ledger() == system.ledger()

    changed_geometry = HingedFlapGeometryV1(
        geometry.id, "1.0.1", geometry.provenance, geometry.width_m,
        geometry.length_m, geometry.left_closed_volume_m3,
        geometry.right_closed_volume_m3, geometry.lift_stop_m,
        geometry.discharge_coefficient)
    changed = DynamicReedTwoVolumeCouplingV1(
        changed_geometry, petal, _left, _right, reed, eos=eos)
    with pytest.raises(ValueError, match="configuration mismatch"):
        changed.restore(checkpoint)

    tampered = copy.deepcopy(checkpoint)
    tampered["state"][0] *= 1.001
    with pytest.raises(ValueError, match="state hash"):
        restored.restore(tampered)


def test_geometry_json_schema_round_trip_is_versioned():
    system, _ = setup_case()
    checkpoint = system.checkpoint()
    restored = HingedFlapGeometryV1.from_dict(checkpoint["geometry"])
    assert restored == system.geometry
    malformed = checkpoint["geometry"] | {"swept_volume_law": "WIDTH_TIMES_LIFT"}
    with pytest.raises(ValueError, match="schema/law"):
        HingedFlapGeometryV1.from_dict(malformed)
