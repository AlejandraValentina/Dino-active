import math

import pytest

from motorsim.mechanical import (
    LossTerm,
    MechanicalLossModel,
    OperatingMap,
)


def model():
    return MechanicalLossModel((
        LossTerm("rings", "piston_ring", "SYNTHETIC_ASSUMPTION", mep_pa=10_000.0),
        LossTerm("bearings", "bearing_accessory", "DOCUMENTED", mep_pa=20_000.0),
        LossTerm("pumping", "pumping", "DERIVED_FROM_DOCUMENTED", mep_pa=5_000.0),
    ))


def test_two_stroke_indicated_to_brake_analytic_accounting():
    result = model().evaluate_2t(indicated_work_j=100.0, displacement_m3=0.001,
                                 rpm=6000, load=0.5)
    assert result["indicated_mep_pa"] == pytest.approx(100_000.0)
    assert result["friction_mep_pa"] == pytest.approx(35_000.0)
    assert result["brake_mep_pa"] == pytest.approx(65_000.0)
    assert result["mechanical_loss_power_w"] == pytest.approx(3500.0)
    assert result["brake_power_w"] == pytest.approx(6500.0)
    assert result["indicated_torque_nm"] == pytest.approx(100 / (2 * math.pi))
    assert result["brake_torque_nm"] == pytest.approx(65 / (2 * math.pi))
    assert result["cycle_convention"] == "2T_360_DEG_ONE_CYCLE_PER_REV"


def test_net_piston_work_api_applies_losses_once_to_combined_gas_work():
    result = model().evaluate_2t_net_piston_work(
        net_piston_gas_work_j=80.0, displacement_m3=0.001,
        rpm=6000, load=0.5)
    assert result["schema"] == "MOTORSIM_MECHANICAL_LOSSES_2T_V2_NET_PISTON_WORK"
    assert result["net_piston_gas_work_j"] == pytest.approx(80.0)
    assert result["brake_work_j"] == pytest.approx(45.0)
    assert result["brake_mep_pa"] == pytest.approx(45_000.0)
    assert result["mechanical_loss_power_w"] == pytest.approx(3500.0)
    assert result["clipped"] is False


def test_map_inputs_interpolate_without_extrapolation():
    loss_map = OperatingMap((1000.0, 3000.0), (0.0, 1.0),
                            ((10_000.0, 20_000.0), (30_000.0, 40_000.0)))
    configured = MechanicalLossModel((LossTerm(
        "mapped", "piston_ring", "SYNTHETIC_ASSUMPTION", operating_map=loss_map),))
    result = configured.evaluate_2t(indicated_work_j=100, displacement_m3=0.001,
                                    rpm=2000, load=0.5)
    assert result["friction_mep_pa"] == pytest.approx(25_000.0)
    with pytest.raises(ValueError, match="outside"):
        configured.evaluate_2t(indicated_work_j=100, displacement_m3=0.001,
                               rpm=4000, load=0.5)


def test_negative_brake_power_is_reported_not_clipped():
    result = model().evaluate_2t(indicated_work_j=10, displacement_m3=0.001,
                                rpm=6000, load=0.5)
    assert result["brake_work_j"] == pytest.approx(-25.0)
    assert result["brake_power_w"] == pytest.approx(-2500.0)
    assert not result["brake_power_positive"]
    assert result["clipped"] is False


def test_serialization_roundtrip_and_invalid_terms():
    configured = model()
    assert MechanicalLossModel.from_dict(configured.to_dict()) == configured
    with pytest.raises(ValueError):
        MechanicalLossModel((LossTerm("bad", "piston_ring", "UNKNOWN", mep_pa=-1),)).validate()
    with pytest.raises(ValueError):
        OperatingMap((1, 1), (0,), ((1,), (2,))).validate()
    with pytest.raises(ValueError):
        model().evaluate_2t(indicated_work_j=True, displacement_m3=0.001, rpm=6000, load=0.5)
