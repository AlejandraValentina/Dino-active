import copy
import hashlib
import json
import unittest

from motorsim.reference_harness.campaign import _record_for_detector
from motorsim.reference_harness.checkpoint import (checkpoint_payload,
                                                   restore_checkpoint,
                                                   replay_comparison)
from motorsim.reference_harness.config import CONTRACT_ID, validate_config
from motorsim.reference_harness.convergence import (PeriodicDetector, PeriodicDetectorV2,
                                                     compare_cycles, compare_cycles_v2)
from motorsim.reference_harness.evidence import (audit_cycles, configuration_hash,
                                                  source_binding, verify_source_binding)
from motorsim.reference_harness.runtime import _duct_cfl_step, build_system
from motorsim.gas1d.eos import IdealGas
from motorsim.gas1d.mesh import uniform_mesh
from scripts.build_kt100_hybrid_fixture_v2 import ROOT, V1_PATH, OUT_PATH, build as build_kt100_config


SPECIES = ["fresh_air", "fuel", "residual", "burned"]


def cycle(index, phase=0):
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
    obs = {"chambers": chambers, "ducts": ducts,
           "global_species_kg": [1.0, 0.0, 0.0, 0.0],
           "cycle_start_total_mass_kg": 1.0,
           "cycle_start_total_energy_J": 10.0,
           "work_J": 2.0 + phase,
           "fresh_delivery_kg": 0.1 + phase,
           "fresh_short_circuit_kg": 0.01 + phase,
           "p7_burned_produced_kg": 0.001 + phase,
           "p7_heat_J": 800.0 + phase}
    return {"cycle_index": index, "configuration_hash": "config",
            "contract": CONTRACT_ID, "observables": obs}


def synthetic_configuration():
    config = build_kt100_config()
    config["fixture_id"] = "INTERNAL_CONTROLLED_HARNESS_FIXTURE"
    config["engine"]["project"]["name"] = "INTERNAL CONTROLLED FIXTURE — SYNTHETIC"
    config["engine"]["project"]["bore_mm"] = 54.0
    config["engine"]["project"]["stroke_mm"] = 56.0
    config["combustion"]["physical_event_phase_deg"] = 100.0
    config["operating_point"]["rpm"] = 3000
    config["numerics"]["dx_target_m"] = 0.5
    return config


class ReferenceHarnessTests(unittest.TestCase):
    def test_kt100_v2_config_is_reproducible_and_provenance_bound(self):
        config = build_kt100_config()
        saved = json.loads(OUT_PATH.read_text(encoding="utf-8"))
        self.assertEqual(config, saved)
        self.assertEqual(config["base_v1"]["sha256"], hashlib.sha256(V1_PATH.read_bytes()).hexdigest())
        self.assertEqual(config["operating_points_rpm"], [5000, 7000, 9000, 11000, 13000])
        self.assertTrue(all(x["provenance"] == "SYNTHETIC_ASSUMPTION"
                            for x in config["transfer_ducts"]))
        self.assertEqual(config["port_flow_model"]["provenance"], "MODEL_FORM_DIFFERENCE")
        self.assertEqual(config["claims"]["experimental_validation"], "NOT_PERFORMED")
        validate_config(config)

    def test_period1_three_consecutive_comparisons(self):
        detector = PeriodicDetector()
        for i in range(1, 5):
            result = detector.update(cycle(i))
        self.assertEqual(result["classification"], "PERIOD_1")
        self.assertEqual(detector.converged_cycle, 4)

    def test_period2_independent_anchor_relative_branches(self):
        detector = PeriodicDetector()
        for i in range(1, 9):
            phase = 0 if i % 2 else 1
            result = detector.update(cycle(i, phase))
        self.assertEqual(result["classification"], "PERIOD_2")
        self.assertEqual(detector.branch_streaks, {"A": 3, "B": 3})
        self.assertEqual(detector.converged_cycle, 8)

    def test_detector_snapshot_restore_preserves_streaks(self):
        first = PeriodicDetector()
        for i in range(1, 5):
            first.update(cycle(i, 0 if i % 2 else 1))
        second = PeriodicDetector(first.snapshot())
        self.assertEqual(first.snapshot(), second.snapshot())
        for i in range(5, 9):
            sample = cycle(i, 0 if i % 2 else 1)
            first.update(sample)
            second.update(sample)
        self.assertEqual(first.snapshot(), second.snapshot())
        self.assertEqual(first.classification, "PERIOD_2")

    def test_compare_rejects_bool_nan_and_mesh_identity_mismatch(self):
        a, b = cycle(1), cycle(2)
        b["observables"]["work_J"] = True
        self.assertEqual(compare_cycles(a, b)["status"], "INVALID")
        b = cycle(2)
        b["observables"]["work_J"] = float("nan")
        self.assertEqual(compare_cycles(a, b)["status"], "INVALID")
        b = cycle(2)
        b["observables"]["ducts"]["exhaust"].append(
            copy.deepcopy(b["observables"]["ducts"]["exhaust"][0]))
        self.assertEqual(compare_cycles(a, b)["status"], "INVALID")

    def test_signed_work_is_supported_by_v2_while_v1_remains_frozen(self):
        a, b = cycle(1), cycle(2)
        a["observables"]["work_J"] = -2.0
        b["observables"]["work_J"] = -2.01
        self.assertEqual(compare_cycles(a, b)["status"], "INVALID")
        result = compare_cycles_v2(a, b)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["contract"], "REFERENCE_PERIODIC_CONVERGENCE_V2")
        self.assertAlmostEqual(result["metrics"]["work_J"]["value"], .01 / 2.01)

        b["observables"]["work_J"] = 2.0
        self.assertEqual(compare_cycles_v2(a, b)["status"], "FAIL")
        b["observables"]["work_J"] = True
        self.assertEqual(compare_cycles_v2(a, b)["status"], "INVALID")

    def test_signed_work_v2_detector_period1_period2_and_restart(self):
        period1 = PeriodicDetectorV2()
        for i in range(1, 5):
            record = cycle(i)
            record["observables"]["work_J"] = -2.0
            result = period1.update(record)
        self.assertEqual(result["classification"], "PERIOD_1")
        self.assertEqual(period1.snapshot()["contract"], "REFERENCE_PERIODIC_CONVERGENCE_V2")
        restored = PeriodicDetectorV2(period1.snapshot())
        self.assertEqual(restored.snapshot(), period1.snapshot())

        period2 = PeriodicDetectorV2()
        for i in range(1, 9):
            phase = 0 if i % 2 else 1
            record = cycle(i, phase)
            record["observables"]["work_J"] = -2.0 - phase * .01
            result = period2.update(record)
        self.assertEqual(result["classification"], "PERIOD_2")
        self.assertEqual(period2.branch_streaks, {"A": 3, "B": 3})
        self.assertEqual(period2.converged_cycle, 8)
        with self.assertRaisesRegex(ValueError, "contract mismatch"):
            PeriodicDetectorV2(PeriodicDetector().snapshot())

    def test_config_schema_and_cycle_relative_geometry_adapter(self):
        config = synthetic_configuration()
        parsed = validate_config(config)
        self.assertEqual(parsed["physical_event_phase_deg"], 100.0)
        system, model, offset = build_system(config)
        self.assertEqual(offset, 250.0)
        self.assertEqual(system.species_sum_error(), 0.0)
        self.assertEqual(system.p7_enabled, True)
        self.assertEqual(system.gas.geometry_callback(350.0)["volumes"], model.geometry(100.0)[0])
        self.assertEqual(tuple(system.species_mass),
                         ("crankcase", "cylinder", "intake", "tr1", "tr2", "exhaust"))
        config["combustion"]["physical_event_phase_deg"] = 351.0
        with self.assertRaises(ValueError):
            validate_config(config)
        config = synthetic_configuration()
        config["engine"]["project"]["ports"][0]["discharge_coefficient"] = 0.8
        with self.assertRaisesRegex(ValueError, "no configurable discharge"):
            validate_config(config)

    def test_boundary_cfl_uses_the_resolved_geometric_face_area(self):
        eos = IdealGas(287.0, 1.35)
        mesh = uniform_mesh(1, length=0.03, area=1.0e-4)
        state = eos.validate((1.0, 0.0, 101325.0, 1.0))
        speed = abs(state[1]) + eos.sound_speed(state)
        mesh_bound = _duct_cfl_step(mesh, [state], [speed, speed],
                                    mesh.areas, eos, 0.4)
        larger_port_bound = _duct_cfl_step(
            mesh, [state], [speed, speed], (mesh.areas[0], 1.04e-4), eos, 0.4)
        self.assertLess(larger_port_bound, mesh_bound)
        self.assertAlmostEqual(larger_port_bound / mesh_bound, 2.0 / 2.04)

    def test_json_checkpoint_restore_and_full_state_replay_comparison(self):
        config = synthetic_configuration()
        system, _, _ = build_system(config)
        detector = PeriodicDetector()
        checkpoint = checkpoint_payload(system, detector, config,
                                        cycle_index=0, elapsed_time_s=0.0)
        restored, _, _ = build_system(config)
        restored_detector = PeriodicDetector()
        info = restore_checkpoint(restored, restored_detector, checkpoint, config)
        self.assertEqual(info, {"cycle_index": 0, "elapsed_time_s": 0.0})
        self.assertTrue(replay_comparison(system, restored)["passed"])
        checkpoint["payload_sha256"] = "corrupted"
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            restore_checkpoint(restored, restored_detector, checkpoint, config)

    def test_accepted_ssprk_step_checkpoint_restart_matches_continuous_run(self):
        """Exercise restart continuity after a real P5-C/P6 accepted step."""
        config = synthetic_configuration()
        continuous, _, _ = build_system(config)
        detector = PeriodicDetector()
        omega = 6.0 * config["operating_point"]["rpm"]
        dt = 1.0e-7
        next_angle = continuous.gas.angle + omega * dt
        continuous.step(dt, angle=next_angle)

        checkpoint = checkpoint_payload(continuous, detector, config,
                                        cycle_index=0, elapsed_time_s=dt)
        restarted, _, _ = build_system(config)
        restarted_detector = PeriodicDetector()
        info = restore_checkpoint(restarted, restarted_detector, checkpoint, config)
        self.assertEqual(info, {"cycle_index": 0, "elapsed_time_s": dt})
        self.assertTrue(replay_comparison(continuous, restarted)["passed"])

        next_dt = 1.0e-7
        target_angle = continuous.gas.angle + omega * next_dt
        continuous.step(next_dt, angle=target_angle)
        restarted.step(next_dt, angle=target_angle)
        self.assertTrue(replay_comparison(continuous, restarted)["passed"])
        self.assertEqual(detector.snapshot(), restarted_detector.snapshot())

    def test_source_binding_detects_changed_component_set(self):
        binding = source_binding()
        self.assertTrue(verify_source_binding(binding))
        binding["motorsim/p8_performance.py"] = "not-included"
        with self.assertRaises(ValueError):
            verify_source_binding(binding)

    def test_offline_auditor_rejects_terminal_mismatch_and_bool_numeric(self):
        config_hash = "config"
        raw_state = [[1.0, 0.0, 2.0, 0.0, 1.0]]
        species_state = {"cylinder": [[1.0, 0.0, 0.0, 0.0]]}
        trajectory_step = {"angle_deg": 31.0, "state": raw_state,
                           "species_mass": species_state,
                           "gas_totals": {"mass": 1.0, "energy": 2.0},
                           "gas_external_cumulative": {"mass": 0.0, "energy": 0.0},
                           "species_inventory": [1.0,0.0,0.0,0.0],
                           "species_external_cumulative": [0.0]*4,
                           "p7_species_source_cumulative": [0.0]*4,
                           "p7_heat_cumulative_J": 0.0,
                           "work_cumulative_J": 0.0}
        trajectory_step["cylinder_stage_pressure_Pa"] = [100000.0, 100000.0, 100000.0]
        record = {"schema": "REFERENCE_ENGINE_HYBRID_CYCLE_PRIMARY_V1",
                  "contract": CONTRACT_ID, "cycle_index": 1,
                  "configuration_hash": config_hash,
                  "rpm": 3000,
                  "terminal_state": {"gas_conservative": raw_state,
                                     "species_mass": species_state},
                  "trajectory": [trajectory_step],
                  "trajectory_last_state": raw_state,
                  "trajectory_last_species_mass": species_state,
                  "scheduler_angle_deg": 32.0,
                  "cycle_start_cumulative": {"angle_deg": 30.0,
                                              "gas_totals": {"mass": 1.0, "energy": 2.0},
                                              "gas_external": {"mass": 0.0, "energy": 0.0},
                                              "species_inventory": [1.0,0.0,0.0,0.0],
                                              "species_external": [0.0]*4,
                                              "p7_species_source": [0.0]*4},
                  "admissible": True, "species_sum_error_kg": 0.0,
                  "observables": cycle(1)["observables"],
                  "performance": {"indicated_work_J": 2.0,
                                  "indicated_power_W": 100.0,
                                  "equivalent_indicated_torque_Nm": 2.0/(2*3.141592653589793),
                                  "peak_pressure_Pa": 100000.0},
                  "p7_ledger": {"burned_produced": 0.0, "heat_added": 0.0},
                  "conservation": {"mass_residual_kg": 0.0,
                                   "energy_residual_J": 0.0,
                                   "species_residual_kg_by_component": [0.0]*4,
                                   "mass_terms": {"start_kg": 1.0, "end_kg": 1.0,
                                                  "external_delta_kg": 0.0},
                                   "energy_terms": {"start_J": 2.0, "end_J": 2.0,
                                                    "external_delta_J": 0.0,
                                                    "p7_heat_J": 0.0,
                                                    "indicated_work_J": 0.0},
                                   "species_terms": {"start_kg": [1.0,0.0,0.0,0.0],
                                                     "end_kg": [1.0,0.0,0.0,0.0],
                                                     "external_delta_kg": [0.0]*4,
                                                     "p7_delta_kg": [0.0]*4}}}
        self.assertIsNone(audit_cycles([record], config_hash)["classification"])
        bad = copy.deepcopy(record)
        bad["trajectory_last_state"] = []
        with self.assertRaisesRegex(ValueError, "terminal"):
            audit_cycles([bad], config_hash)
        bad = copy.deepcopy(record)
        bad["observables"]["work_J"] = True
        with self.assertRaisesRegex(ValueError, "boolean"):
            audit_cycles([bad], config_hash)


if __name__ == "__main__":
    unittest.main()
