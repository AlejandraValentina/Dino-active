import gzip
import json

import pytest

from motorsim.scavenging_partition_v1 import evaluate_scavenging_partition_v1


def _primary(*, fresh_delivery=1.0, fresh_short=0.2, species=None, residual=None):
    species = species or [0.6, 0.1, 0.2, 0.1]
    residual = residual or [0.0, 0.0, 0.0, 0.0]
    snapshots = {
        "transfer": {"angle_deg": 100.0, "species_order": ["fresh_air", "fuel", "residual", "burned"],
                     "cylinder_species_kg": species, "cylinder_total_mass_kg": sum(species),
                     "state_source": "exact"},
        "exhaust": {"angle_deg": 120.0, "species_order": ["fresh_air", "fuel", "residual", "burned"],
                    "cylinder_species_kg": species, "cylinder_total_mass_kg": sum(species),
                    "state_source": "exact"},
    }
    return {"admissible": True, "cycle_index": 1, "configuration_hash": "c" * 64,
            "observables": {"fresh_delivery_kg": fresh_delivery,
                             "fresh_short_circuit_kg": fresh_short,
                             "fuel_delivered_kg": 0.1,
                             "fuel_short_circuited_kg": 0.01},
            "cycle_ledgers": {"external_species_kg": [0.0, 0.0, 0.0, 0.0],
                              "fuel_combustion_source_species_kg": [0.0, 0.0, 0.0, 0.0]},
            "conservation": {"species_residual_kg": residual},
            "port_closure_snapshots": {"status": "EXACT_EVENT_STATES_CAPTURED",
                                        "snapshots": snapshots}}


def test_closed_case_uses_species_conservation_not_gross_partition():
    record = evaluate_scavenging_partition_v1(_primary())
    assert record["classification"] == "PASS"
    assert record["species_closure"]["passed"] is True
    assert record["gross_partition"]["status"] == "NOT_APPLICABLE"
    assert record["metrics"]["schema"] == "MOTORSIM_2T_SCAVENGING_METRICS_V2"


def test_short_circuit_gross_crossing_is_not_clipped_or_double_counted():
    record = evaluate_scavenging_partition_v1(
        _primary(fresh_delivery=0.1, fresh_short=0.09, species=[0.8, 0.1, 0.05, 0.05]))
    assert record["gross_partition"]["passed"] is None
    assert record["metrics"]["ratios"]["trapping_efficiency"]["status"] == "UNDEFINED"
    assert record["metrics"]["ratios"]["trapping_efficiency"]["reason"] == \
        "OUTSIDE_PHYSICAL_DOMAIN_WITH_GROSS_CROSSING_BASIS"


def test_fuel_and_burned_species_are_separate_from_fresh_air():
    record = evaluate_scavenging_partition_v1(
        _primary(species=[0.6, 0.2, 0.1, 0.1]))
    assert record["gross_crossing_ledgers_kg"]["fresh_delivered"] == 1.0
    assert record["gross_crossing_ledgers_kg"]["fuel_delivered"] == 0.1
    assert record["event_snapshots"]["exhaust"]["species_kg"]["burned"] == 0.1
    assert record["event_snapshots"]["exhaust"]["species_kg"]["fuel"] == 0.2


def test_species_closure_and_sampling_contract_are_hard_checked():
    record = evaluate_scavenging_partition_v1(
        _primary(residual=[0.0, 2e-12, 0.0, 0.0]))
    assert record["classification"] == "HARD_PHYSICAL_INVALID"
    assert "SPECIES_CONSERVATION_INVALID" in record["hard_gate"]["hard_failures"]
    bad = _primary()
    bad["port_closure_snapshots"]["snapshots"]["exhaust"]["species_order"] = [
        "fuel", "fresh_air", "residual", "burned"]
    with pytest.raises(ValueError, match="species order"):
        evaluate_scavenging_partition_v1(bad)


def test_existing_periodic_primary_binds_integrated_flux_closure_and_burned_species():
    primary = json.load(gzip.open(
        "results/engine-physics-v1/recovery-campaign-data-v2/engine_a_3000/cycle-073.json.gz"))
    record = evaluate_scavenging_partition_v1(primary)
    assert record["species_closure"]["max_abs_residual_kg"] <= 1e-12
    assert set(record["species_closure"]["residual_kg_by_species"]) == {
        "fresh_air", "fuel", "residual", "burned"}
    assert record["event_snapshots"]["exhaust"]["species_kg"]["burned"] >= 0.0
    assert record["gross_crossing_ledgers_kg"]["fuel_delivered"] >= 0.0
