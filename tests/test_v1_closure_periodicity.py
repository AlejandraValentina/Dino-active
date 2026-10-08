from motorsim.reference_harness.convergence import (
    CONTRACT, CONTRACT_V2, PeriodicDetectorV2,
)
from scripts.v1_closure_campaign import detector_projection, detector_status


def _record(index, phase=0.0):
    # This is the same detector contract used by the reference-harness tests;
    # the campaign runner only projects real V3 primary observables into it.
    chambers = {name: {"mass_kg": 1.0 + phase, "total_energy_J": 10.0 + phase,
                       "pressure_Pa": 100000.0 + phase,
                       "temperature_K": 300.0 + phase}
                for name in ("cylinder", "crankcase")}
    ducts = {name: [{"mass_kg": 0.1 + phase, "total_energy_J": 1.0 + phase,
                     "pressure_Pa": 100000.0 + phase,
                     "temperature_K": 300.0 + phase,
                     "velocity_over_sound_speed": 0.1 * phase,
                     "species_mass_fractions": [1.0, 0.0, 0.0, 0.0]}]
             for name in ("intake", "transfer1", "transfer2", "exhaust")}
    return {"cycle_index": index, "configuration_hash": "test-config",
            "contract": CONTRACT, "observables": {
                "chambers": chambers, "ducts": ducts,
                "global_species_kg": [1.0, 0.0, 0.0, 0.0],
                "cycle_start_total_mass_kg": 1.0,
                "cycle_start_total_energy_J": 10.0,
                "work_J": 2.0 + phase,
                "fresh_delivery_kg": 0.1 + phase,
                "fresh_short_circuit_kg": 0.01 + phase,
                "p7_burned_produced_kg": 0.001 + phase,
                "p7_heat_J": 800.0 + phase}}


def test_final_status_cannot_be_convergence_without_detector_classification():
    detector = PeriodicDetectorV2()
    assert detector_status(detector, exhausted=False) == "RUNNING"
    assert detector_status(detector, exhausted=True) == "NO_CONVERGENCE_WITHIN_HORIZON"


def test_period1_and_period2_are_detector_outputs():
    period1 = PeriodicDetectorV2()
    for index in range(1, 5):
        period1.update(_record(index))
    assert detector_status(period1, exhausted=False) == "PERIOD_1"

    period2 = PeriodicDetectorV2()
    for index in range(1, 9):
        period2.update(_record(index, 0.0 if index % 2 else 1.0))
    assert period2.classification == "PERIOD_2"
    assert period2.branch_streaks == {"A": 3, "B": 3}


def test_not_evaluated_primary_field_is_not_a_final_periodicity_status():
    primary = {"periodicity": {"status": "NOT_EVALUATED"},
               "cycle_index": 1, "configuration_hash": "x",
               "contract": CONTRACT, "observables": _record(1)["observables"]}
    projection = detector_projection(primary)
    assert projection["contract"] == CONTRACT
    detector = PeriodicDetectorV2()
    detector.update(projection)
    assert detector_status(detector, exhausted=False) == "RUNNING"
    assert detector_status(detector, exhausted=True) == "NO_CONVERGENCE_WITHIN_HORIZON"
