import gzip
import json

from scripts.evaluate_integrated_cycle_evidence import _sha256_bytes, evaluate
from motorsim.reference_harness.convergence import CONTRACT


def test_source_digest_accepts_normalized_bytes():
    assert _sha256_bytes(b"producer source\n") == _sha256_bytes(
        b"producer source\r\n".replace(b"\r\n", b"\n"))


def _record(index, phase=0):
    chambers = {name: {"mass_kg": 1.0 + phase,
                       "total_energy_J": 10.0 + phase,
                       "pressure_Pa": 100000.0 + phase,
                       "temperature_K": 300.0 + phase}
                for name in ("cylinder", "crankcase")}
    ducts = {name: [{"mass_kg": 0.1 + phase,
                     "total_energy_J": 1.0 + phase,
                     "pressure_Pa": 100000.0 + phase,
                     "temperature_K": 300.0 + phase,
                     "velocity_over_sound_speed": phase * 0.1,
                     "species_mass_fractions": [1.0, 0.0, 0.0, 0.0]}]
             for name in ("intake", "transfer1", "transfer2", "exhaust")}
    return {
        "schema": "MOTORSIM_INTEGRATED_2T_CYCLE_PRIMARY_V2",
        "cycle_index": index,
        "cycle_start_deg": (index - 1) * 360.0,
        "cycle_end_deg": index * 360.0,
        "contract": CONTRACT,
        "configuration_hash": "fixture-config-hash",
        "admissible": True,
        "observables": {
            "chambers": chambers,
            "ducts": ducts,
            "global_species_kg": [1.0, 0.0, 0.0, 0.0],
            "cycle_start_total_mass_kg": 1.0,
            "cycle_start_total_energy_J": 10.0,
            "work_J": 2.0 + phase,
            "fresh_delivery_kg": 0.1 + phase,
            "fresh_short_circuit_kg": 0.01 + phase,
            "p7_burned_produced_kg": 0.001 + phase,
            "p7_heat_J": 800.0 + phase,
        },
    }


def _write_campaign(root, phases):
    for index, phase in enumerate(phases, 1):
        with gzip.open(root / f"cycle-{index:03d}.json.gz", "wt", encoding="utf-8") as stream:
            json.dump(_record(index, phase), stream)
    (root / "manifest.json").write_text(json.dumps({
        "schema": "MOTORSIM_COMMERCIAL_CYCLE_PRODUCER_MANIFEST_V1",
        "fixture_id": "TEST",
        "horizon_cycles": len(phases),
        "output_cycle_count": len(phases),
    }), encoding="utf-8")
    (root / "restart-audit.json").write_text(json.dumps({
        "status": "EXACT_REPLAY_PASS",
        "restart_cycle": 1,
        "compared_terminal_cycle": 2,
        "snapshot_equal": True,
    }), encoding="utf-8")


def test_evaluator_reconstructs_registered_period_one_without_simulation(tmp_path):
    _write_campaign(tmp_path, [0, 0, 0, 0, 0])

    result = evaluate(tmp_path)

    assert result["classification"] == "PERIOD_1"
    assert result["converged_cycle"] == 4
    assert result["acceptance_claim"] is False
    assert result["period_1_comparison_counts"] == {"PASS": 4, "FAIL": 0, "INVALID": 0}
    assert len(result["cycle_artifacts"]) == 5


def test_evaluator_does_not_promote_failing_fixed_horizon_to_convergence(tmp_path):
    _write_campaign(tmp_path, [0, 10, 20, 30])

    result = evaluate(tmp_path)

    assert result["classification"] == "NO_PERIODIC_CONVERGENCE_WITHIN_PREREGISTERED_HORIZON"
    assert result["detected_period"] is None
    assert result["converged_cycle"] is None
    assert result["period_1_comparison_counts"] == {"PASS": 0, "FAIL": 3, "INVALID": 0}
    assert result["period_2_comparison_counts"] == {"PASS": 0, "FAIL": 2, "INVALID": 0}
