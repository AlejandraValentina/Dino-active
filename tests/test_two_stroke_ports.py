import copy
import json
import math
import unittest
from dataclasses import replace

from motorsim.project import ProjectError
from motorsim.simulation import restriction
from motorsim.two_stroke_ports import (AreaKnot, DuctBinding, PortDefinition,
                                       TwoStrokePortSet)


def generic_fixture():
    return TwoStrokePortSet(
        56.0, 100.0,
        (DuctBinding("inlet", "intake"),
         DuctBinding("transfer-a", "transfer"),
         DuctBinding("transfer-b", "transfer"),
         DuctBinding("transfer-boost", "transfer"),
         DuctBinding("header", "exhaust")),
        (
            PortDefinition("intake", "Test piston port", "intake", "piston_port",
                           "inlet", "piston_port", 1.0, "SYNTHETIC_ASSUMPTION",
                           top_mm=64.0, height_mm=10.0, width_mm=20.0,
                           skirt_mm=42.0),
            PortDefinition("tr-primary", "Primary transfer", "transfer", "primary",
                           "transfer-a", "rectangular_window", 0.7,
                           "SYNTHETIC_ASSUMPTION", top_mm=32.0,
                           height_mm=10.0, width_mm=20.0),
            PortDefinition("tr-secondary", "Secondary transfer", "transfer", "secondary",
                           "transfer-b", "rectangular_window", 0.8,
                           "SYNTHETIC_ASSUMPTION", top_mm=34.0,
                           height_mm=8.0, width_mm=12.0),
            PortDefinition("tr-boost", "Boost transfer", "transfer", "boost",
                           "transfer-boost", "rectangular_window", 0.6,
                           "SYNTHETIC_ASSUMPTION", top_mm=36.0,
                           height_mm=7.0, width_mm=8.0),
            PortDefinition("ex-bridge-left", "Bridged left aperture", "exhaust",
                           "bridged_segment", "header", "rectangular_window", 0.75,
                           "SYNTHETIC_ASSUMPTION", top_mm=30.0,
                           height_mm=10.0, width_mm=7.0, group_id="main-bridge"),
            PortDefinition("ex-bridge-right", "Bridged right aperture", "exhaust",
                           "bridged_segment", "header", "rectangular_window", 0.75,
                           "SYNTHETIC_ASSUMPTION", top_mm=30.0,
                           height_mm=10.0, width_mm=7.0, group_id="main-bridge"),
            PortDefinition("ex-aux", "Auxiliary profile", "exhaust", "auxiliary",
                           "header", "effective_profile", 0.8,
                           "SYNTHETIC_ASSUMPTION", area_profile=(
                               AreaKnot(0.0, 0.0), AreaKnot(90.0, 40.0),
                               AreaKnot(180.0, 80.0), AreaKnot(270.0, 40.0),
                               AreaKnot(360.0, 0.0))),
        ))


class GenericTwoStrokePortTests(unittest.TestCase):
    def test_multiple_transfer_and_bridged_auxiliary_exhaust_compile_separately(self):
        model = generic_fixture()
        profiles = {item.port_id: item for item in model.compile_profiles()}
        self.assertEqual(len([p for p in model.ports if p.role == "transfer"]), 3)
        self.assertEqual(profiles["tr-primary"].effective_area_mm2[180], 140.0)
        self.assertAlmostEqual(profiles["tr-secondary"].effective_area_mm2[180], 76.8)
        self.assertEqual(profiles["ex-bridge-left"].effective_area_mm2[180], 52.5)
        self.assertEqual(profiles["ex-aux"].effective_area_mm2[90], 32.0)
        self.assertAlmostEqual(model.duct_area_at("header", 180), 169.0)
        duct_profile = next(p for p in model.compile_duct_profiles()
                            if p.duct_id == "header")
        self.assertAlmostEqual(duct_profile.effective_area_mm2[180], 169.0)

    def test_single_transfer_uses_additive_v2_schema_and_round_trips(self):
        full = generic_fixture()
        one_transfer = replace(
            full,
            ducts=tuple(duct for duct in full.ducts
                        if duct.id not in {"transfer-b", "transfer-boost"}),
            ports=tuple(port for port in full.ports
                        if port.duct_id not in {"transfer-b", "transfer-boost"}))
        encoded = one_transfer.dumps()
        self.assertEqual(json.loads(encoded)["schema"], "GENERIC_2T_PORTS_V2")
        self.assertEqual(TwoStrokePortSet.loads(encoded), one_transfer)
        self.assertEqual(len(one_transfer.compile_profiles()), len(one_transfer.ports))

        malformed = json.loads(encoded)
        malformed["schema"] = "GENERIC_2T_PORTS_V1"
        with self.assertRaisesRegex(ProjectError, "no coincide con la topología"):
            TwoStrokePortSet.from_dict(malformed)

    def test_rectangular_window_event_angles_are_analytic_not_degree_samples(self):
        model = generic_fixture()
        profile = next(x for x in model.compile_profiles() if x.port_id == "tr-primary")
        self.assertAlmostEqual(profile.event_angles_deg[1], 90.0, places=9)
        self.assertAlmostEqual(profile.event_angles_deg[-2], 270.0, places=9)
        self.assertNotEqual(profile.event_angles_deg[1], 90.0001)

    def test_intake_area_remains_available_for_forward_and_reverse_flow(self):
        model = generic_fixture()
        inlet = next(port for port in model.ports if port.id == "intake")
        area_m2 = model.area_at(inlet, 0.0) * 1e-6
        self.assertAlmostEqual(area_m2, 200.0e-6)
        high_fresh = (120000.0, 300.0, 1.0)
        low_residual = (100000.0, 300.0, 0.0)
        forward = restriction(high_fresh, low_residual, area_m2, 1.0)
        reverse = restriction((100000.0, 300.0, 1.0),
                              (120000.0, 300.0, 0.0), area_m2, 1.0)
        self.assertGreater(forward[0], 0.0)
        self.assertLess(reverse[0], 0.0)
        self.assertEqual(forward[2] / forward[0], 1.0)
        self.assertEqual(reverse[2] / reverse[0], 0.0)

    def test_powervalve_ready_roof_travel_changes_geometry_only(self):
        model = generic_fixture()
        exhaust = PortDefinition(
            "pv-ready", "Exhaust geometry", "exhaust", "main", "header",
            "rectangular_window", 1.0, "SYNTHETIC_ASSUMPTION",
            top_mm=30.0, height_mm=10.0, width_mm=20.0,
            roof_travel_mm=4.0, roof_position=0.5)
        self.assertEqual(model.area_at(exhaust, 180.0), 200.0)

    def test_generic_ports_v1_rejects_zero_discharge_coefficient(self):
        model = generic_fixture()
        ports = tuple(replace(p, discharge_coefficient=0.0)
                      if p.id == "tr-primary" else p for p in model.ports)
        closed_model = replace(model, ports=ports)
        with self.assertRaisesRegex(ProjectError, "debe ser positivo"):
            closed_model.validate()

    def test_profile_interpolates_periodically_and_preserves_explicit_values(self):
        model = generic_fixture()
        profile = next(p for p in model.ports if p.id == "ex-aux")
        self.assertEqual(model.area_at(profile, 45.0), 16.0)
        self.assertEqual(model.area_at(profile, 405.0), 16.0)
        self.assertEqual(model.area_at(profile, 360.0), 0.0)

    def test_round_trip_recomputes_and_binds_derived_profiles(self):
        model = generic_fixture()
        restored = TwoStrokePortSet.loads(model.dumps())
        self.assertEqual(restored, model)
        payload = json.loads(model.dumps())
        self.assertEqual(len(payload["derived_profiles"]["profiles"]["ports"][0]["angles_deg"]), 361)
        self.assertEqual(len(payload["derived_profiles"]["profiles"]["ducts"]), 5)
        changed_input = copy.deepcopy(payload)
        changed_input["ports"][1]["width_mm"] += 1.0
        with self.assertRaisesRegex(ProjectError, "desactualizados"):
            TwoStrokePortSet.from_dict(changed_input)
        changed_profile = copy.deepcopy(payload)
        changed_profile["derived_profiles"]["profiles"]["ports"][0]["effective_area_mm2"][180] += 1.0
        with self.assertRaisesRegex(ProjectError, "desactualizados"):
            TwoStrokePortSet.from_dict(changed_profile)

    def test_negative_inputs_and_malformed_profiles_are_rejected(self):
        model = generic_fixture()
        payload = json.loads(model.dumps())
        for coefficient in (-1.0, 0.0, math.inf, math.nan, True):
            bad = copy.deepcopy(payload)
            bad["ports"][1]["discharge_coefficient"] = coefficient
            with self.subTest(coefficient=coefficient), self.assertRaises(ProjectError):
                TwoStrokePortSet.from_dict(bad)
        bad = copy.deepcopy(payload)
        bad["ports"][-1]["area_profile"][-1]["area_mm2"] = 1.0
        with self.assertRaisesRegex(ProjectError, "periódico"):
            TwoStrokePortSet.from_dict(bad)
        bad = copy.deepcopy(payload)
        bad["ports"][1]["duct_id"] = "missing"
        with self.assertRaisesRegex(ProjectError, "no existe"):
            TwoStrokePortSet.from_dict(bad)
        bad = copy.deepcopy(payload)
        bad["ports"][4]["group_id"] = "solo-one"
        bad["ports"][5]["group_id"] = "different-group"
        with self.assertRaisesRegex(ProjectError, "bridged"):
            TwoStrokePortSet.from_dict(bad)
        bad = copy.deepcopy(payload)
        bad["ports"][-1]["role"] = "transfer"
        bad["ports"][-1]["feature"] = "boost"
        with self.assertRaisesRegex(ProjectError, "perfiles explícitos"):
            TwoStrokePortSet.from_dict(bad)

    def test_non_json_numeric_constants_are_rejected(self):
        with self.assertRaises(ProjectError):
            TwoStrokePortSet.loads('{"area": NaN}')


if __name__ == "__main__":
    unittest.main()
