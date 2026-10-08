import math

import pytest

from motorsim.fuel import FuelAccounting, FuelProperties


def accounting():
    return FuelAccounting(FuelProperties(
        stoichiometric_afr=14.7,
        lower_heating_value_j_kg=43_000_000.0,
        provenance="DOCUMENTED",
    ))


def cycle(**changes):
    values = dict(fresh_air_delivered_kg=0.012, fuel_delivered_kg=0.001,
                  trapped_fresh_air_kg=0.010, trapped_fuel_kg=0.0008,
                  fuel_short_circuited_kg=0.00015, burned_fraction=0.8, rpm=6000,
                  indicated_work_j=100.0, brake_work_j=50.0)
    values.update(changes)
    return values


def test_four_species_cycle_fuel_air_energy_and_sfc_accounting():
    result = accounting().evaluate_2t(**cycle())
    assert result["cycle_convention"] == "2T_360_DEG_ONE_CYCLE_PER_REV"
    assert result["fuel_burned_kg_per_cycle"] == pytest.approx(0.00064)
    assert result["fuel_unburned_trapped_kg_per_cycle"] == pytest.approx(0.00016)
    assert result["fuel_not_trapped_kg_per_cycle"] == pytest.approx(0.0002)
    assert result["fuel_short_circuited_kg_per_cycle"] == pytest.approx(0.00015)
    assert result["delivered_afr"]["value"] == pytest.approx(12.0)
    assert result["trapped_afr"]["value"] == pytest.approx(12.5)
    assert result["equivalence_ratio"]["delivered"]["value"] == pytest.approx(14.7 / 12)
    assert result["released_energy_j_per_cycle"] == pytest.approx(27_520.0)
    assert result["fuel_flow_kg_s"] == pytest.approx(0.1)
    assert result["indicated_power_w"] == pytest.approx(10_000.0)
    assert result["indicated_sfc_g_kwh"] == pytest.approx(36_000.0)
    assert result["brake_power_w"] == pytest.approx(5_000.0)
    assert result["brake_sfc_g_kwh"] == pytest.approx(72_000.0)


def test_zero_fuel_and_nonpositive_brake_have_explicit_undefined_values():
    result = accounting().evaluate_2t(**cycle(fresh_air_delivered_kg=0.01,
        fuel_delivered_kg=0.0, trapped_fresh_air_kg=0.009,
        trapped_fuel_kg=0.0, fuel_short_circuited_kg=0.0,
        burned_fraction=0.0, brake_work_j=-1.0))
    assert result["delivered_afr"] == {"value": None, "status": "UNDEFINED",
                                        "reason": "ZERO_DENOMINATOR"}
    assert result["trapped_afr"]["value"] is None
    assert result["equivalence_ratio"]["trapped"]["value"] is None
    assert result["brake_sfc_g_kwh"] is None
    assert result["brake_sfc_status"] == "UNDEFINED_NONPOSITIVE_BRAKE_POWER"
    assert result["released_energy_j_per_cycle"] == 0


def test_project_properties_roundtrip_and_provenance():
    assert FuelAccounting.from_dict(accounting().to_dict()) == accounting()
    with pytest.raises(ValueError):
        FuelProperties(14.7, 43e6, "MEASURED").validate()
    with pytest.raises(ValueError):
        FuelProperties(True, 43e6, "DOCUMENTED").validate()


@pytest.mark.parametrize("changes", [
    {"trapped_fuel_kg": 0.002},
    {"trapped_fresh_air_kg": 0.02},
    {"burned_fraction": 1.1},
    {"rpm": 0},
    {"fuel_delivered_kg": math.inf},
    {"indicated_work_j": True},
])
def test_invalid_cycle_ledgers_are_rejected(changes):
    with pytest.raises(ValueError):
        accounting().evaluate_2t(**cycle(**changes))
