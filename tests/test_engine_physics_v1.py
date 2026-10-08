import math

import pytest

from motorsim.combustion import WiebeComponent
from motorsim.engine_physics_v1 import (
    DuctHeatTransferV1,
    HeatTransferModelV1,
    IdealFuelMeteringV1,
    PortDischargeCoefficientsV1,
    ScavengingModelV1,
    engineering_plausibility_gates_v1,
    phase_model_provenance,
    standard_fmep_model_v1,
    synthetic_gasoline_v1,
)
from motorsim.fuel_combustion import FuelCoupledCombustionV2


def _combustion():
    return FuelCoupledCombustionV2(
        components=(WiebeComponent(1.0, 40.0, 5.0, 2.0),),
        ignition_timing_deg=15.0,
        combustion_efficiency=0.92,
        fuel_snapshot=synthetic_gasoline_v1(),
    )


def test_synthetic_fuel_is_frozen_and_metering_is_state_bound():
    fuel = synthetic_gasoline_v1()
    assert fuel.validate().id == "SYNTHETIC_GASOLINE_V1"
    assert fuel.content_hash == synthetic_gasoline_v1().content_hash
    result = IdealFuelMeteringV1(air_kg_per_cycle=0.8).evaluate(fuel)
    assert result["fuel_kg_per_cycle"] > 0.0
    assert result["fuel_snapshot_sha256"] == fuel.content_hash


def test_zero_phi_metering_is_explicitly_zero_and_zero_denominator_is_undefined():
    result = IdealFuelMeteringV1(target_phi=0.0).evaluate(synthetic_gasoline_v1())
    assert result["fuel_kg_per_cycle"] == 0.0
    assert result["target_afr"]["status"] == "UNDEFINED"


def test_port_scavenging_heat_duct_and_fmep_contracts():
    ports = PortDischargeCoefficientsV1({"transfer": {"forward": 0.72, "reverse": 0.68}})
    assert ports.to_dict()["sha256"]
    scavenging = ScavengingModelV1().evaluate(
        reference_air_kg=0.01, fresh_delivered_kg=0.012,
        fresh_short_circuit_kg=0.002, trapped_fresh_air_kg=0.009,
        trapped_residual_kg=0.001, trapped_fuel_kg=0.0003)
    assert scavenging["ratios"]["trapping_efficiency"]["status"] == "DEFINED"
    thermal = HeatTransferModelV1().evaluate(
        gas_temperature_K=800.0,
        areas_m2={"head": 0.01, "piston": 0.01, "liner": 0.02})
    assert set(thermal["heat_rate_W_by_surface"]) == {"head", "piston", "liner"}
    duct = DuctHeatTransferV1().evaluate(
        reynolds=10_000.0, hydraulic_diameter_m=0.01, length_m=0.2,
        wall_temperature_K=400.0, gas_temperature_K=700.0)
    assert duct["friction_factor"] > 0.0
    assert standard_fmep_model_v1().evaluate_2t(
        indicated_work_j=100.0, displacement_m3=0.0001, rpm=3000.0, load=1.0
    )["friction_mep_pa"] > 0.0


def test_hard_gate_and_warning_semantics():
    valid = engineering_plausibility_gates_v1(
        pressures_pa={"cylinder": 101325.0}, temperatures_K={"cylinder": 500.0},
        conservation_residuals={"mass": 0.0}, metrics={})
    assert valid["classification"] == "PASS"
    invalid = engineering_plausibility_gates_v1(
        pressures_pa={"cylinder": -1.0}, temperatures_K={"cylinder": 500.0},
        conservation_residuals={"mass": 0.0}, metrics={})
    assert invalid["classification"] == "HARD_PHYSICAL_INVALID"


def test_phase_provenance_binds_fuel_ports_and_combustion():
    fuel = synthetic_gasoline_v1()
    provenance = phase_model_provenance(
        fuel=fuel,
        port_coefficients=PortDischargeCoefficientsV1({
            "transfer": {"forward": 0.72, "reverse": 0.68}}),
        combustion=_combustion())
    assert len(provenance["sha256"]) == 64
    assert provenance["models"]["fuel"]["content_hash"] == fuel.content_hash


def test_engineering_fuel_burned_output_is_value_or_undefined_not_ratio_record():
    import gzip
    import json
    from motorsim.engine_physics_v1 import evaluate_integrated_cycle_v1
    primary = json.load(gzip.open(
        "results/2t-v1-closure-20261006/restart-replay-c11/fixture_a_prime/continuous-cycle-1.json.gz"))
    record = evaluate_integrated_cycle_v1(primary, rpm=3000.0, fuel=synthetic_gasoline_v1())
    assert record["fuel"]["fuel_burned_status"] in {"DEFINED", "UNDEFINED"}
    assert record["fuel"]["fuel_burned_kg_per_cycle"] is None or isinstance(
        record["fuel"]["fuel_burned_kg_per_cycle"], float)


def test_invalid_coefficients_are_rejected():
    with pytest.raises(ValueError, match="Cd"):
        PortDischargeCoefficientsV1({"transfer": {"forward": 0.0, "reverse": 0.7}}).validate()


def test_v2_adapter_uses_primary_ledgers_and_blocks_transient_regime_outputs():
    import gzip
    import json
    from motorsim.engine_physics_v1 import evaluate_integrated_cycle_v2

    primary = json.load(gzip.open(
        "results/engine-physics-v1/campaign-evidence-r3/engine_a_3000/cycle-012.json.gz"))
    record = evaluate_integrated_cycle_v2(
        primary, rpm=3000.0, fuel=synthetic_gasoline_v1(),
        periodicity_status="NO_CONVERGENCE_WITHIN_HORIZON")
    assert record["operating_point_status"] == "TRANSIENT_DIAGNOSTIC"
    assert record["outputs"]["brake_power"]["regime_status"] == "NOT_USABLE_UNTIL_PERIODIC"
    assert record["outputs"]["fuel_burned"]["value"] == pytest.approx(
        primary["observables"]["fuel_coupled_combustion"]["fuel_burned_kg"])
    assert record["hard_gate"]["classification"] == "HARD_PHYSICAL_INVALID"
    assert "RELATIONSHIP_INVALID:partition_conservation" in record["hard_gate"]["hard_failures"]
    assert record["outputs"]["AFR"]["status"] == "DEFINED"


def test_v2_adapter_never_fabricates_missing_dependencies():
    import gzip
    import json
    from motorsim.engine_physics_v1 import evaluate_integrated_cycle_v2

    primary = json.load(gzip.open(
        "results/engine-physics-v1/campaign-evidence-r3/engine_a_3000/cycle-012.json.gz"))
    primary["observables"].pop("fresh_delivery_kg")
    record = evaluate_integrated_cycle_v2(
        primary, rpm=3000.0, fuel=synthetic_gasoline_v1(), periodicity_status="PERIOD_1")
    assert record["outputs"]["AFR"]["status"] == "UNDEFINED"
    assert record["outputs"]["AFR"]["value"] is None
    assert record["hard_gate"]["classification"] == "HARD_PHYSICAL_INVALID"
    assert "REQUIRED_OUTPUT_UNDEFINED:air_fuel_ratio_dependency" in record["hard_gate"]["hard_failures"]


def test_v2_hard_gates_reject_species_contract_fuel_overburn_and_energy_drift():
    import copy
    import gzip
    import json
    from motorsim.engine_physics_v1 import evaluate_integrated_cycle_v2

    source = json.load(gzip.open(
        "results/engine-physics-v1/campaign-evidence-r3/engine_a_3000/cycle-012.json.gz"))
    bad_species = copy.deepcopy(source)
    bad_species["port_closure_snapshots"]["snapshots"]["exhaust"]["species_order"] = [
        "fuel", "fresh_air", "residual", "burned"]
    record = evaluate_integrated_cycle_v2(
        bad_species, rpm=3000.0, fuel=synthetic_gasoline_v1(), periodicity_status="PERIOD_1")
    assert record["hard_gate"]["classification"] == "HARD_PHYSICAL_INVALID"
    assert "REQUIRED_OUTPUT_UNDEFINED:partition_conservation" in record["hard_gate"]["hard_failures"]

    bad_fuel = copy.deepcopy(source)
    bad_fuel["observables"]["fuel_coupled_combustion"]["fuel_burned_kg"] = 1.0
    record = evaluate_integrated_cycle_v2(
        bad_fuel, rpm=3000.0, fuel=synthetic_gasoline_v1(), periodicity_status="PERIOD_1")
    assert "RELATIONSHIP_INVALID:fuel_availability" in record["hard_gate"]["hard_failures"]

    bad_energy = copy.deepcopy(source)
    bad_energy["cycle_ledgers"]["fuel_combustion_heat_added_J"] += 1.0
    record = evaluate_integrated_cycle_v2(
        bad_energy, rpm=3000.0, fuel=synthetic_gasoline_v1(), periodicity_status="PERIOD_1")
    assert "RELATIONSHIP_INVALID:fuel_energy_identity" in record["hard_gate"]["hard_failures"]
