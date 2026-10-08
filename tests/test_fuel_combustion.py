import copy
import pytest

from motorsim.combustion import WiebeComponent
from motorsim.fuel_combustion import (
    FuelCombustionEventV1, FuelCoupledCombustionV1,
    SyntheticFuelSurrogateV1,
)


def model(**changes):
    values = dict(components=(WiebeComponent(1.0, 40.0, 5.0, 2.0),),
                  ignition_timing_deg=350.0, combustion_efficiency=0.8)
    values.update(changes)
    return FuelCoupledCombustionV1(**values)


def test_synthetic_fuel_snapshot_is_explicit_derived_and_hash_bound():
    fuel = SyntheticFuelSurrogateV1()
    snapshot = fuel.snapshot()
    assert snapshot["provenance"] == "SYNTHETIC_ASSUMPTION"
    assert snapshot["stoichiometric_afr"] == pytest.approx(14.71264367816092)
    assert len(snapshot["sha256"]) == 64
    assert SyntheticFuelSurrogateV1.from_snapshot(snapshot) == fuel
    damaged = copy.deepcopy(snapshot)
    damaged["lower_heating_value_j_kg"] += 1.0
    with pytest.raises(ValueError, match="identity|derived"):
        SyntheticFuelSurrogateV1.from_snapshot(damaged)


def test_capture_limits_eligible_fuel_by_ignition_time_oxygen():
    combustion = model()
    event = combustion.capture(350.0, (0.0001, 0.001, 0.002, 0.0))
    assert event.fuel_at_ignition_kg == pytest.approx(0.001)
    assert event.fuel_available_for_burn_kg == pytest.approx(
        .0001 * .232 / combustion.fuel.oxygen_required_kg_per_kg_fuel)
    assert FuelCombustionEventV1.from_dict(event.to_dict()) == event
    no_oxygen = combustion.capture(350.0, (0.0, .001, .002, 0.0))
    assert no_oxygen.fuel_available_for_burn_kg == 0.0


def test_stage_source_converts_only_stoichiometric_reactants_and_closes_mass_energy():
    combustion = model()
    initial = (0.01, 0.001, 0.002, 0.0)
    event = combustion.capture(350.0, initial)
    result = combustion.stage_source(
        event=event, angle_deg=370.0, rpm=3000.0,
        species_mass_kg=initial,
        noncombustion_species_rhs_kg_s=(0.0, 0.0, 0.0, 0.0), dt_s=1e-5)
    rates = result["species_kg_s"]
    assert sum(rates) == pytest.approx(0.0, abs=1e-18)
    assert rates[0] < 0.0 and rates[1] < 0.0 and rates[2] == 0.0 and rates[3] > 0.0
    assert result["heat_w"] == pytest.approx(
        result["burned_fuel_rate_kg_s"] * 43_000_000.0 * 0.8)
    assert -rates[0] / -rates[1] == pytest.approx(combustion.fuel.stoichiometric_afr)


def test_stage_source_respects_zero_fuel_and_stage_oxygen_availability():
    combustion = model()
    event = combustion.capture(350.0, (0.01, .001, 0.0, 0.0))
    zero = combustion.stage_source(
        event=event, angle_deg=370.0, rpm=3000.0,
        species_mass_kg=(.01, 0.0, 0.0, 0.0),
        noncombustion_species_rhs_kg_s=(0.0, 0.0, 0.0, 0.0), dt_s=1e-5)
    assert zero["burned_fuel_rate_kg_s"] == 0.0
    assert zero["heat_w"] == 0.0
    oxygen_limited = combustion.stage_source(
        event=event, angle_deg=370.0, rpm=3000.0,
        species_mass_kg=(1e-12, .001, 0.0, 0.0),
        noncombustion_species_rhs_kg_s=(0.0, 0.0, 0.0, 0.0), dt_s=1e-5)
    assert oxygen_limited["burned_fuel_rate_kg_s"] == pytest.approx(
        1e-12 * combustion.fuel.air_oxygen_mass_fraction /
        combustion.fuel.oxygen_required_kg_per_kg_fuel / 1e-5)
    assert oxygen_limited["heat_w"] > 0.0


def test_stage_source_matches_species_roundoff_admissibility_without_burning_negative_fuel():
    combustion = model()
    event = combustion.capture(350.0, (.01, .001, 0.0, 0.0))
    tiny_negative = combustion.stage_source(
        event=event, angle_deg=370.0, rpm=3000.0,
        species_mass_kg=(.01, -1e-15, 0.0, 0.0),
        noncombustion_species_rhs_kg_s=(0.0, 0.0, 0.0, 0.0), dt_s=1e-5)
    assert tiny_negative["burned_fuel_rate_kg_s"] == 0.0
    assert tiny_negative["heat_w"] == 0.0
    with pytest.raises(ValueError, match="inadmissible species mass"):
        combustion.stage_source(
            event=event, angle_deg=370.0, rpm=3000.0,
            species_mass_kg=(.01, -2e-14, 0.0, 0.0),
            noncombustion_species_rhs_kg_s=(0.0, 0.0, 0.0, 0.0), dt_s=1e-5)


def test_fuel_combustion_configuration_roundtrip_binds_provenance_and_hash():
    combustion = model()
    encoded = combustion.to_dict()
    assert FuelCoupledCombustionV1.from_dict(encoded) == combustion
    corrupted = copy.deepcopy(encoded)
    corrupted["provenance"] = "DOCUMENTED"
    with pytest.raises(ValueError, match="invalid"):
        FuelCoupledCombustionV1.from_dict(corrupted)
    corrupted = copy.deepcopy(encoded)
    corrupted["fuel_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="hash"):
        FuelCoupledCombustionV1.from_dict(corrupted)


@pytest.mark.parametrize("fractions", [
    (0.5, 0.6, 0.0), (0.86, -0.14, 0.28), (0.86, 0.13, 0.0)])
def test_synthetic_fuel_rejects_invalid_elemental_composition(fractions):
    with pytest.raises(ValueError):
        SyntheticFuelSurrogateV1(carbon_mass_fraction=fractions[0],
                                 hydrogen_mass_fraction=fractions[1],
                                 oxygen_mass_fraction=fractions[2]).validate()
