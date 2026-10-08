import math
import unittest

from motorsim.scavenging import (ScavengingInput, calculate_scavenging_metrics,
                                 calculate_scavenging_metrics_v2,
                                 reference_charge_mass,
                                 scavenging_metrics_from_cycle,
                                 scavenging_metrics_from_generic_ports,
                                 scavenging_engineering_records,
                                 scavenging_series_from_primary_cycles)
from motorsim.two_stroke_ports import DuctBinding, PortDefinition, TwoStrokePortSet


class ScavengingMetricTests(unittest.TestCase):
    def setUp(self):
        self.inputs = ScavengingInput(
            reference_mass_kg=0.01,
            fresh_delivered_kg=0.012,
            fresh_short_circuit_kg=0.002,
            species_at_transfer_close_kg=(0.003, 0.001, 0.006, 0.0),
            species_at_exhaust_close_kg=(0.004, 0.001, 0.004, 0.001),
        )

    @staticmethod
    def primary_cycle():
        terminal_gas = [1.0, 2.0, 3.0]
        terminal_species = {"cylinder": [[0.004, 0.001, 0.004, 0.001]]}
        rows = [
            {"angle_deg": 40.0, "state": [0.0],
             "species_mass": {"cylinder": [[0.0, 0.0, 0.0, 0.0]]},
             "fresh_delivery_cumulative_kg": 0.0,
             "fresh_short_circuit_cumulative_kg": 0.0},
            {"angle_deg": 100.0, "state": [1.0],
             "species_mass": {"cylinder": [[0.003, 0.001, 0.006, 0.0]]},
             "fresh_delivery_cumulative_kg": 0.004,
             "fresh_short_circuit_cumulative_kg": 0.0002},
            {"angle_deg": 250.0, "state": terminal_gas,
             "species_mass": terminal_species,
             "fresh_delivery_cumulative_kg": 0.012,
             "fresh_short_circuit_cumulative_kg": 0.002},
            {"angle_deg": 390.0, "state": terminal_gas,
             "species_mass": terminal_species,
             "fresh_delivery_cumulative_kg": 0.012,
             "fresh_short_circuit_cumulative_kg": 0.002},
        ]
        return {
            "schema": "REFERENCE_ENGINE_HYBRID_CYCLE_PRIMARY_V1",
            "terminal_state": {"gas_conservative": terminal_gas,
                               "species_mass": terminal_species},
            "trajectory_terminal_state": terminal_gas,
            "trajectory_last_state": terminal_gas,
            "trajectory_last_species_mass": terminal_species,
            "trajectory": rows,
            "cycle_start_cumulative": {"fresh_delivery": 0.0,
                                       "fresh_short_circuit": 0.0,
                                       "angle_deg": 30.0},
            "scheduler_angle_deg": 390.0,
            "observables": {"fresh_delivery_kg": 0.012,
                            "fresh_short_circuit_kg": 0.002},
        }

    def test_all_metrics_match_independent_analytic_values(self):
        result = calculate_scavenging_metrics(self.inputs)
        ratios = result["ratios"]
        self.assertEqual(result["schema"], "MOTORSIM_2T_SCAVENGING_METRICS_V1")
        self.assertAlmostEqual(ratios["delivery_ratio"]["value"], 1.2)
        self.assertAlmostEqual(ratios["trapping_efficiency"]["value"], 5.0 / 12.0)
        self.assertAlmostEqual(ratios["scavenging_efficiency"]["value"], 0.5)
        self.assertAlmostEqual(ratios["charging_efficiency"]["value"], 0.5)
        self.assertAlmostEqual(ratios["trapping_ratio"]["value"], 2.4)
        self.assertAlmostEqual(ratios["residual_fraction"]["value"], 0.4)
        self.assertAlmostEqual(ratios["purity_at_transfer_close"]["value"], 0.4)
        self.assertAlmostEqual(ratios["purity_at_exhaust_close"]["value"], 0.5)
        self.assertAlmostEqual(ratios["short_circuit_fraction"]["value"], 1.0 / 6.0)
        self.assertEqual(result["masses_kg"]["fresh_retained"], 0.005)
        self.assertEqual(result["masses_kg"]["fresh_lost"], 0.002)
        records = scavenging_engineering_records(result)
        self.assertEqual(records["purity_at_transfer_close"]["status"], "DEFINED")
        self.assertAlmostEqual(records["purity_at_exhaust_close"]["value"], 0.5)
        self.assertEqual(records["fresh_lost_kg"]["value"], 0.002)

    def test_v2_declares_perfect_mixing_and_preserves_valid_metrics(self):
        result = calculate_scavenging_metrics_v2(self.inputs)
        self.assertEqual(result["schema"], "MOTORSIM_2T_SCAVENGING_METRICS_V2")
        self.assertEqual(result["assumption"],
                         "SINGLE_ZONE_PERFECT_MIXING_SCAVENGING_ASSUMPTION")
        self.assertEqual(result["domain_policy"],
                         "MARK_UNDEFINED_OUT_OF_DOMAIN; NEVER_CLIP")
        self.assertAlmostEqual(result["ratios"]["trapping_efficiency"]["value"],
                               5.0 / 12.0)
        records = scavenging_engineering_records(result)
        self.assertEqual(records["trapping_efficiency"]["status"], "DEFINED")
        self.assertIn("SINGLE_ZONE_PERFECT_MIXING_SCAVENGING_ASSUMPTION",
                      records["trapping_efficiency"]["source"])
        self.assertIn("MARK_UNDEFINED_OUT_OF_DOMAIN; NEVER_CLIP",
                      records["trapping_efficiency"]["source"])

    def test_v2_marks_unidentifiable_out_of_domain_metrics_undefined(self):
        cases = (
            ("trapping_efficiency", ScavengingInput(
                0.01, 0.001, 0.0, (0.1, 0.0, 0.9, 0.0),
                (0.002, 0.0, 0.0, 0.0))),
            ("short_circuit_fraction", ScavengingInput(
                0.01, 0.001, 0.002, (0.001, 0.0, 0.0, 0.0),
                (0.001, 0.0, 0.0, 0.0))),
            ("charging_efficiency", ScavengingInput(
                0.001, 0.01, 0.0, (0.001, 0.0, 0.0, 0.0),
                (0.002, 0.0, 0.0, 0.0))),
        )
        for name, source in cases:
            with self.subTest(name=name):
                result = calculate_scavenging_metrics_v2(source)
                metric = result["ratios"][name]
                self.assertIsNone(metric["value"])
                self.assertEqual(metric["status"], "UNDEFINED")
                self.assertEqual(
                    metric["reason"],
                    "OUTSIDE_PHYSICAL_DOMAIN_WITH_GROSS_CROSSING_BASIS")
                record = scavenging_engineering_records(result)[name]
                self.assertEqual(record["status"], "UNDEFINED")

    def test_reference_mass_uses_single_cylinder_swept_volume(self):
        mass = reference_charge_mass(52.0, 46.0, 101325.0, 300.0, 287.0)
        volume_m3 = math.pi * (0.052 ** 2) * 0.046 / 4.0
        expected = (101325.0 / (287.0 * 300.0)) * volume_m3
        self.assertAlmostEqual(mass, expected, places=15)

    def test_cycle_metrics_bind_to_exact_primary_event_snapshots_and_ledgers(self):
        result = scavenging_metrics_from_cycle(
            self.primary_cycle(), reference_mass_kg=0.01,
            transfer_close_angle_deg=100.0, exhaust_close_angle_deg=250.0)
        self.assertAlmostEqual(result["ratios"]["purity_at_transfer_close"]["value"], 0.4)
        self.assertAlmostEqual(result["ratios"]["purity_at_exhaust_close"]["value"], 0.5)
        self.assertAlmostEqual(result["masses_kg"]["fresh_lost"], 0.002)

    def test_cycle_metrics_reject_missing_events_and_stale_summaries(self):
        cycle = self.primary_cycle()
        with self.assertRaisesRegex(ValueError, "Falta snapshot"):
            scavenging_metrics_from_cycle(cycle, reference_mass_kg=0.01,
                                          transfer_close_angle_deg=101.0,
                                          exhaust_close_angle_deg=250.0)
        cycle = self.primary_cycle()
        cycle["observables"]["fresh_delivery_kg"] = 99.0
        with self.assertRaisesRegex(ValueError, "no coinciden"):
            scavenging_metrics_from_cycle(cycle, reference_mass_kg=0.01,
                                          transfer_close_angle_deg=100.0,
                                          exhaust_close_angle_deg=250.0)

    def test_generic_geometry_selects_last_transfer_and_exhaust_closures(self):
        ports = TwoStrokePortSet(
            56.0, 100.0,
            (DuctBinding("in", "intake"), DuctBinding("tr", "transfer"),
             DuctBinding("ex", "exhaust")),
            (PortDefinition("inlet", "inlet", "intake", "piston_port", "in",
                            "piston_port", 1.0, "SYNTHETIC_ASSUMPTION",
                            top_mm=64.0, height_mm=10.0, width_mm=20.0,
                            skirt_mm=42.0),
             PortDefinition("tr-a", "primary", "transfer", "primary", "tr",
                            "rectangular_window", 1.0, "SYNTHETIC_ASSUMPTION",
                            top_mm=32.0, height_mm=10.0, width_mm=20.0),
             PortDefinition("tr-b", "boost", "transfer", "boost", "tr",
                            "rectangular_window", 0.8, "SYNTHETIC_ASSUMPTION",
                            top_mm=36.0, height_mm=7.0, width_mm=8.0),
             PortDefinition("ex-main", "main", "exhaust", "main", "ex",
                            "rectangular_window", 1.0, "SYNTHETIC_ASSUMPTION",
                            top_mm=30.0, height_mm=10.0, width_mm=20.0)))
        start_angle = 30.0
        transfer_angle = max(start_angle + ((angle - start_angle) % 360.0)
                             for angle in ports.duct_closing_angles("tr"))
        exhaust_angle = max(start_angle + ((angle - start_angle) % 360.0)
                            for angle in ports.duct_closing_angles("ex"))
        terminal_gas = [1.0, 2.0, 3.0]
        transfer_species = [[0.003, 0.001, 0.006, 0.0]]
        exhaust_species = [[0.004, 0.001, 0.004, 0.001]]
        angles = sorted({40.0, transfer_angle, exhaust_angle, 390.0})
        rows = []
        for angle in angles:
            if abs(angle - transfer_angle) < 1e-9:
                species = transfer_species
            else:
                species = exhaust_species
            rows.append({"angle_deg": angle, "state": terminal_gas,
                         "species_mass": {"cylinder": species},
                         "fresh_delivery_cumulative_kg": 0.012 if angle == 390.0 else 0.0,
                         "fresh_short_circuit_cumulative_kg": 0.002 if angle == 390.0 else 0.0})
        cycle = {"schema": "REFERENCE_ENGINE_HYBRID_CYCLE_PRIMARY_V1",
                 "terminal_state": {"gas_conservative": terminal_gas,
                                    "species_mass": {"cylinder": exhaust_species}},
                 "trajectory_terminal_state": terminal_gas,
                 "trajectory_last_state": terminal_gas,
                 "trajectory_last_species_mass": {"cylinder": exhaust_species},
                 "trajectory": rows,
                 "cycle_index": 1,
                 "configuration_hash": "generic-test-config",
                 "cycle_start_cumulative": {"angle_deg": 30.0,
                                             "fresh_delivery": 0.0,
                                             "fresh_short_circuit": 0.0},
                 "scheduler_angle_deg": 390.0,
                 "observables": {"fresh_delivery_kg": 0.012,
                                 "fresh_short_circuit_kg": 0.002}}
        result = scavenging_metrics_from_generic_ports(
            cycle, ports=ports, reference_mass_kg=0.01)
        self.assertAlmostEqual(result["ratios"]["purity_at_transfer_close"]["value"], 0.4)
        self.assertAlmostEqual(result["ratios"]["purity_at_exhaust_close"]["value"], 0.5)
        series = scavenging_series_from_primary_cycles(
            [cycle], ports=ports, reference_mass_kg=0.01)
        self.assertEqual(series["periodicity"], "NOT_EVALUATED")
        self.assertEqual(series["cycles"][0]["cycle_index"], 1)

    def test_generic_closure_rejects_missing_exact_snapshot(self):
        ports = TwoStrokePortSet(
            56.0, 100.0,
            (DuctBinding("in", "intake"), DuctBinding("tr", "transfer"),
             DuctBinding("ex", "exhaust")),
            (PortDefinition("inlet", "inlet", "intake", "piston_port", "in",
                            "piston_port", 1.0, "SYNTHETIC_ASSUMPTION",
                            top_mm=64.0, height_mm=10.0, width_mm=20.0, skirt_mm=42.0),
             PortDefinition("tr-a", "primary", "transfer", "primary", "tr",
                            "rectangular_window", 1.0, "SYNTHETIC_ASSUMPTION",
                            top_mm=32.0, height_mm=10.0, width_mm=20.0),
             PortDefinition("tr-b", "boost", "transfer", "boost", "tr",
                            "rectangular_window", 0.8, "SYNTHETIC_ASSUMPTION",
                            top_mm=36.0, height_mm=7.0, width_mm=8.0),
             PortDefinition("ex-main", "main", "exhaust", "main", "ex",
                            "rectangular_window", 1.0, "SYNTHETIC_ASSUMPTION",
                            top_mm=30.0, height_mm=10.0, width_mm=20.0)))
        cycle = self.primary_cycle()
        cycle["cycle_start_cumulative"]["angle_deg"] = 30.0
        with self.assertRaisesRegex(ValueError, "Falta snapshot"):
            scavenging_metrics_from_generic_ports(cycle, ports=ports,
                                                  reference_mass_kg=0.01)
        cycle = self.primary_cycle()
        cycle["observables"]["fresh_delivery_kg"] = True
        with self.assertRaisesRegex(ValueError, "número"):
            scavenging_metrics_from_cycle(cycle, reference_mass_kg=0.01,
                                          transfer_close_angle_deg=100.0,
                                          exhaust_close_angle_deg=250.0)

    def test_cycle_metrics_reject_partial_cycle_span(self):
        cycle = self.primary_cycle()
        cycle["scheduler_angle_deg"] = 250.0
        with self.assertRaisesRegex(ValueError, "ciclo completo"):
            scavenging_metrics_from_cycle(cycle, reference_mass_kg=0.01,
                                          transfer_close_angle_deg=100.0,
                                          exhaust_close_angle_deg=250.0)

    def test_zero_denominators_are_explicitly_undefined(self):
        zero = ScavengingInput(0.0, 0.0, 0.0, (0.0,) * 4, (0.0,) * 4)
        result = calculate_scavenging_metrics(zero)
        ratios = result["ratios"]
        for name in ("delivery_ratio", "trapping_efficiency", "scavenging_efficiency",
                     "charging_efficiency", "trapping_ratio", "residual_fraction",
                     "purity_at_transfer_close", "purity_at_exhaust_close",
                     "short_circuit_fraction"):
            with self.subTest(name=name):
                self.assertIsNone(ratios[name]["value"])
                self.assertEqual(ratios[name]["status"], "UNDEFINED")
                self.assertEqual(ratios[name]["reason"], "ZERO_DENOMINATOR")

    def test_each_denominator_is_independent(self):
        # Delivery=0 but retained state exists; transfer purity is still valid.
        source = ScavengingInput(0.01, 0.0, 0.0, (0.2, 0.0, 0.8, 0.0),
                                 (0.1, 0.0, 0.9, 0.0))
        ratios = calculate_scavenging_metrics(source)["ratios"]
        self.assertEqual(ratios["trapping_efficiency"]["status"], "UNDEFINED")
        self.assertEqual(ratios["short_circuit_fraction"]["status"], "UNDEFINED")
        self.assertAlmostEqual(ratios["purity_at_transfer_close"]["value"], 0.2)
        self.assertAlmostEqual(ratios["purity_at_exhaust_close"]["value"], 0.1)

    def test_invalid_masses_and_boolean_numerics_are_rejected(self):
        for value in (-1.0, math.nan, math.inf, True, "0.1"):
            with self.subTest(value=value):
                bad = ScavengingInput(value, 0.012, 0.002,
                                      (0.003, 0.001, 0.006, 0.0),
                                      (0.004, 0.001, 0.004, 0.001))
                with self.assertRaises(ValueError):
                    calculate_scavenging_metrics(bad)
        bad_species = ScavengingInput(0.01, 0.012, 0.002,
                                      (0.003, -0.001, 0.006, 0.0),
                                      (0.004, 0.001, 0.004, 0.001))
        with self.assertRaises(ValueError):
            calculate_scavenging_metrics(bad_species)


if __name__ == "__main__":
    unittest.main()
