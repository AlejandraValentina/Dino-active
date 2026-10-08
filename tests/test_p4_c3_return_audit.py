import unittest
import inspect
import ast
import copy
from unittest.mock import patch

from dev_orchestrator.p4_c3_return_audit import (
    _momentum_audit, _recompute_stage, _riemann_audit, _select_return,
    _b0_audit_stage, _b1_audit_stage, _recompute_stage_b,
    classify, _physical_flux, reconstruct_external_faces,
)
from dev_orchestrator.p4_sci_04b import C2_AREA, C2_VOLUME, EOS
from dev_orchestrator.p4_sci_04b import solve_c2_one
from dev_orchestrator.reference.exact_riemann import ExactRiemann
from dev_orchestrator.reference.hllc_audit import hllc as audit_hllc
from dev_orchestrator.reference.hllc_audit import hlle_flux as audit_hlle_flux
from motorsim.gas1d.riemann import hllc_flux as product_hllc
from motorsim.gas1d.boundary import Boundary
from motorsim.gas1d.mesh import uniform_mesh
from motorsim.gas1d.second_order import reconstruct as production_reconstruct


def _stage(states, geometry, dt=0.1):
    rows = [list(area * value for value in EOS.conservative(state))
            for state, area in zip(states, geometry["areas"][:-1])]
    rho, velocity, pressure, species = states[0]
    conservative = EOS.conservative((rho, 0.0, pressure, species))
    chamber = [rho * C2_VOLUME, conservative[2] * C2_VOLUME,
                rho * species * C2_VOLUME]
    stage = {"dt": dt, "primitive": [list(state) for state in states],
             "conservative": rows, "chamber_state": chamber}
    stage["external_faces"] = reconstruct_external_faces(states, geometry)
    stage["external_faces"]["reconstruction"] = {
        "downgraded_cells": list(stage["external_faces"]["downgraded"]["cells"])}
    stage["external_faces"]["interface"]["left"] = list(
        (rho, 0.0, pressure, species))
    interface = stage["external_faces"]["interface"]
    wall = stage["external_faces"]["wall"]
    # Persisted Riemann metadata represents the PRODUCT path.  The audit
    # implementation is evaluated later and compared against these values.
    interface_result = product_hllc(tuple(interface["left"]),
                                    tuple(interface["right"]), EOS)
    wall_result = product_hllc(tuple(wall["left"]), tuple(wall["right"]), EOS)
    stage["external_faces"]["riemann"] = {
        "interface": {"speeds": list(interface_result[1]),
                       "reason": interface_result[2]},
        "wall": {"speeds": list(wall_result[1]), "reason": wall_result[2]},
    }
    return stage


class P4C3ReturnAuditTests(unittest.TestCase):
    def test_b0_persists_used_external_faces_and_detects_mutation(self):
        result = solve_c2_one(12, 0.2, 200000.0, 400.0, 0.5,
                              100000.0, 300.0, 0.2, t_final=1e-5)
        _, info = next(item for item in result["interface_history"]
                       if "audit_stages" in item[1])
        stage = info["audit_stages"]["stage_a"]
        self.assertEqual(_b0_audit_stage(stage, result["audit_geometry"])["status"], "PASS")
        captured = stage["external_faces"]
        self.assertIsInstance(captured["reconstruction"]["downgraded_cells"], list)
        self.assertNotIn("sides", captured["reconstruction"])
        self.assertEqual(captured["wall"]["right"],
                         [captured["wall"]["left"][0],
                          -captured["wall"]["left"][1],
                          captured["wall"]["left"][2],
                          captured["wall"]["left"][3]])
        for path in (("interface", "left"), ("interface", "right"),
                     ("wall", "right")):
            original = captured[path[0]][path[1]][1]
            captured[path[0]][path[1]][1] += 1.0
            self.assertEqual(_b0_audit_stage(stage, result["audit_geometry"])["status"],
                             "FAIL", path)
            captured[path[0]][path[1]][1] = original

    def test_b0_failure_fails_fast_before_b1_or_b2(self):
        geometry = {"areas": [1.0, 1.0], "faces": [0.0, 1.0],
                    "centers": [0.5]}
        stage = _stage([(1.0, 0.0, 100000.0, 0.2)], geometry)
        stage["external_faces"]["wall"]["right"][0] += 1.0
        with self.assertRaisesRegex(ValueError, "B0 audit failed"):
            _recompute_stage_b(stage, geometry)

    def test_b0_external_face_downgrade_is_all_component_and_wall_reflects_it(self):
        class FaceGuardEOS:
            def __init__(self, reject=False):
                self.reject = reject

            def validate(self, state):
                if self.reject and abs(state[1]) < 1.0:
                    raise ValueError("synthetic inadmissible external face")
                return state

        geometry = {"areas": [1.0, 1.0, 1.0],
                    "faces": [0.0, 1.0, 10000.0],
                    "centers": [0.5, 1.5]}
        states = [(1.0, 30.0, 100000.0, 0.2),
                  (1.0, 10.0, 100000.0, 0.2)]
        faces = reconstruct_external_faces(states, geometry, FaceGuardEOS(True))
        self.assertEqual(faces["wall"]["left"], list(states[-1]))
        self.assertEqual(faces["wall"]["right"],
                         [states[-1][0], -states[-1][1],
                          states[-1][2], states[-1][3]])
        self.assertEqual(faces["downgraded"]["cells"], [1])
        self.assertFalse(faces["downgraded"]["sides"]["interface"]["right"])
        self.assertNotIn("left", faces["downgraded"]["sides"]["interface"])
        self.assertTrue(faces["downgraded"]["sides"]["wall"]["left"])
        self.assertTrue(faces["downgraded"]["sides"]["wall"]["right"])

        admissible = reconstruct_external_faces(states, {
            "areas": [1.0, 1.0, 1.0],
            "faces": [0.0, 1.0, 2.0],
            "centers": [0.5, 1.5]}, FaceGuardEOS(False))
        self.assertEqual(admissible["downgraded"]["cells"], [])
        self.assertNotEqual(admissible["wall"]["left"], list(states[-1]))

    def test_b0_one_cell_matches_production_muscl_boundary_faces(self):
        state = (1.0, 30.0, 100000.0, 0.2)
        geometry = {"areas": [1.0, 1.0], "faces": [0.0, 1.0],
                    "centers": [0.5]}
        audited = reconstruct_external_faces([state], geometry)
        mesh = uniform_mesh(1)
        left, right, downgraded = production_reconstruct(
            mesh, [state], (Boundary("outflow"), Boundary("wall")), EOS)

        self.assertEqual(audited["interface"]["right"], list(left[0]))
        self.assertEqual(audited["wall"]["left"], list(right[0]))
        self.assertEqual(audited["wall"]["right"],
                         [right[0][0], -right[0][1], right[0][2], right[0][3]])
        self.assertEqual(audited["downgraded"]["cells"], downgraded)
        self.assertIn("right", audited["downgraded"]["sides"]["interface"])
        self.assertNotIn("left", audited["downgraded"]["sides"]["interface"])

    def test_b0_product_cells_match_and_mutation_fails_without_product_sides(self):
        geometry = {"areas": [1.0, 1.0], "faces": [0.0, 1.0],
                    "centers": [0.5]}
        stage = _stage([(1.0, 0.0, 100000.0, 0.2)], geometry)
        self.assertEqual(_b0_audit_stage(stage, geometry)["status"], "PASS")
        stage["external_faces"]["reconstruction"]["downgraded_cells"] = [99]
        self.assertEqual(_b0_audit_stage(stage, geometry)["status"], "FAIL")

    def test_b1_microcases_are_independent_and_frozen_by_identities(self):
        from dev_orchestrator.reference import hllc_audit
        source = inspect.getsource(hllc_audit)
        tree = ast.parse(source)
        imported = [node for node in ast.walk(tree)
                    if isinstance(node, (ast.ImportFrom, ast.Import))]
        called = [node for node in ast.walk(tree) if isinstance(node, ast.Call)]
        forbidden = ("motorsim.gas1d.riemann", "hllc_flux", "hlle_flux",
                     "estimate_wave_speeds")
        for node in imported:
            if isinstance(node, ast.ImportFrom):
                self.assertFalse(node.module == forbidden[0]
                                 or (node.module or "").startswith(forbidden[0] + "."))
            else:
                self.assertFalse(any(alias.name == forbidden[0]
                                     or alias.name.startswith(forbidden[0] + ".")
                                     for alias in node.names))
        forbidden_import_names = {alias.asname or alias.name.split(".")[-1]
                                  for node in imported for alias in node.names
                                  if alias.name.split(".")[-1] in forbidden[1:]}
        self.assertFalse(any(isinstance(node, ast.Name)
                             and node.id in forbidden_import_names
                             for node in ast.walk(tree)))
        self.assertFalse(any(isinstance(node, ast.Attribute)
                             and node.attr in forbidden[1:]
                             for node in ast.walk(tree)))
        uniform = (1.0, 0.0, 100000.0, 0.2)
        flux, waves, reason = audit_hllc(uniform, uniform, EOS)
        self.assertIsNone(reason)
        self.assertEqual(flux, EOS.flux(uniform))
        self.assertLess(waves[0], waves[1])
        contact = (0.8, 0.0, 100000.0, 0.4)
        flux, waves, reason = audit_hllc(uniform, contact, EOS)
        self.assertIsNone(reason)
        self.assertEqual(flux, (0.0, 100000.0, 0.0, 0.0))
        self.assertEqual(waves[1], 0.0)
        wall_flux, wall_waves, reason = audit_hllc((1.2, 35., 100000., .25),
                                                   (1.2, -35., 100000., .25), EOS)
        self.assertIsNone(reason)
        self.assertEqual(wall_flux[0], 0.0)
        self.assertAlmostEqual(wall_flux[2], 0.0, places=6)
        self.assertEqual(wall_waves[1], 0.0)
        self.assertLess(wall_waves[0], wall_waves[1])
        self.assertLess(wall_waves[1], wall_waves[2])
        for left, right in (
                ((1.0, 20.0, 110000.0, .2), (.9, -10.0, 100000.0, .3)),
                ((1.0, -20.0, 100000.0, .2), (.9, 10.0, 110000.0, .3))):
            flux, waves, reason = audit_hllc(left, right, EOS)
            self.assertIsNone(reason)
            exact = ExactRiemann(left, right, EOS)
            self.assertLess(waves[0], waves[1])
            self.assertLess(waves[1], waves[2])
            self.assertTrue(all(abs(value) < float("inf") for value in flux))
            self.assertEqual(flux[0] > 0.0, exact.ustar > 0.0)

    def test_b1_hlle_helper_identity_and_supplemental_parity(self):
        # Supplemental parity: the independent implementation is checked
        # against production only for ordinary, non-fallback states.
        pairs = (
            ((1.0, 20.0, 110000.0, .2), (.9, -10.0, 100000.0, .3)),
            ((1.0, -20.0, 100000.0, .2), (.9, 10.0, 110000.0, .3)),
            ((1.1, 4.0, 90000.0, .1), (.8, 12.0, 130000.0, .7)),
            ((.7, -8.0, 140000.0, .6), (1.3, -2.0, 95000.0, .2)),
        )
        for left, right in pairs:
            audited = audit_hllc(left, right, EOS)
            product = product_hllc(left, right, EOS)
            self.assertIsNone(audited[2])
            self.assertIsNone(product[2])
            for actual, expected in zip(audited[:2], product[:2]):
                for a, b in zip(actual, expected):
                    self.assertAlmostEqual(a, b, places=12,
                                           msg="supplemental parity")

        left = (1.0, 20.0, 110000.0, .2)
        right = (.9, -10.0, 100000.0, .3)
        sl, sr = -300.0, 300.0
        actual = audit_hlle_flux(left, right, EOS, (sl, sr))
        fl, fr = EOS.flux(left), EOS.flux(right)
        ql, qr = EOS.conservative(left), EOS.conservative(right)
        expected = tuple((sr * l - sl * r + sl * sr * (b - a)) / (sr - sl)
                         for l, r, a, b in zip(fl, fr, ql, qr))
        self.assertEqual(actual, expected)

    def test_b2_synthetic_one_cell_and_variable_area_balance(self):
        # Analytic uniform state: u=0, constant area, Euler momentum flux p*A
        # at both exterior faces and zero geometric source.  No audit helper is
        # used to manufacture the expected balance; only the literal formula.
        geo = {"areas": [2.0, 2.0], "faces": [0., 1.], "centers": [.5]}
        states = [(1.0, 0.0, 100000.0, 0.2)]
        a = _stage(states, geo)
        b = copy.deepcopy(a)
        expected_force = 2.0 * 100000.0 - 2.0 * 100000.0 + 0.0
        predicted = 0.5 * a["dt"] * (expected_force + expected_force)
        after_rows = copy.deepcopy(a["conservative"])
        after_rows[0][1] += predicted
        report = _momentum_audit([(0.1, {"audit_stages": {
            "stage_a": a, "stage_b": b,
            "after": {"conservative": after_rows}}})], geo)
        self.assertAlmostEqual(report["rows"][0]["residual"], 0.0, places=12)
        delta = 1e-6
        after_rows[0][1] += delta
        report = _momentum_audit([(0.1, {"audit_stages": {
            "stage_a": a, "stage_b": b,
            "after": {"conservative": after_rows}}})], geo)
        self.assertAlmostEqual(report["rows"][0]["residual"], delta, places=12)
        self.assertNotEqual(report["rows"][0]["residual"], 0.0)

    def test_b2_ignores_poisoned_product_flux_fields(self):
        geometry = {"areas": [1.0, 1.0], "faces": [0., 1.], "centers": [.5]}
        stage = _stage([(1.0, 0.0, 100000.0, 0.2)], geometry)
        stage["conservative"] = [[1., 0., 250000., .2]]
        info = {"audit_stages": {"stage_a": stage, "stage_b": stage,
                                 "after": {"conservative": stage["conservative"]}},
                "interface_flux_observed": [1e99] * 4,
                "momentum_face_fluxes": {"left": 1e99, "right": -1e99},
                "momentum_source_sum": 1e99}
        clean = _momentum_audit([(0.1, info)], geometry)
        self.assertEqual(clean["product_field_names_used"], [])
        self.assertNotEqual(clean["rows"][0]["recomputed_stage_a"]["left"], 1e99)
    def test_riemann_audit_aligns_observed_flux_with_stage_a(self):
        stage_a = {
            "chamber_state": [0.1, 25000.0, 0.02],
            "primitive": [[1.0, 0.0, 100000.0, 0.2]],
        }
        stage_b = {
            "chamber_state": [0.2, 30000.0, 0.04],
            "primitive": [[1.2, 10.0, 120000.0, 0.3]],
        }
        left = (0.1 / 0.0001, 0.0, (EOS.gamma - 1.0) * 25000.0 / 0.0001, 0.02 / 0.1)
        sampled = ExactRiemann(left, tuple(stage_a["primitive"][0]), EOS).sample(0.0)
        observed = [C2_AREA * value for value in _physical_flux(sampled)]
        audit = _riemann_audit({
            "audit_stages": {"stage_a": stage_a, "stage_b": stage_b},
            "interface_flux_observed": observed,
            "interface_normal": -1.0,
            "interface_area": C2_AREA,
        })
        self.assertEqual(audit["left_state"], list(left))
        self.assertEqual(audit["right_state"], stage_a["primitive"][0])
        self.assertAlmostEqual(audit["relative_error"]["max"], 0.0)

    def test_recompute_stage_uses_exact_reflective_wall_for_moving_state(self):
        last = (1.2, 37.0, 125000.0, 0.25)
        stage = {
            "dt": 0.1,
            "primitive": [list(last)],
            "conservative": [[1.2, 1.2 * 37.0, 300000.0, 0.3]],
            "chamber_state": [0.1, 25000.0, 0.02],
        }
        audited = _recompute_stage(stage, {"areas": [1.0, 2.0]})
        ghost = (last[0], -last[1], last[2], last[3])
        reference = ExactRiemann(last, ghost, EOS)
        expected = 2.0 * _physical_flux(reference.sample(0.0))[1]
        self.assertAlmostEqual(audited["right"], expected, places=12)
        self.assertNotAlmostEqual(audited["right"], 2.0 * last[2], places=6)

    def test_momentum_audit_rejects_productive_terms(self):
        geometry = {"areas": [1.0, 1.0], "faces": [0.0, 1.0],
                    "centers": [0.5]}
        stage = _stage([(1.0, 0.0, 100000.0, 0.2)], geometry)
        info = {"audit_stages": {
            "stage_a": stage,
            "stage_b": stage,
            "after": {"conservative": copy.deepcopy(stage["conservative"])}
        }}
        geometry = {"areas": [1.0, 1.0]}
        # Poisoned names must not be read by the independent auditor.
        info["momentum_face_fluxes"] = {"left": 1e99, "right": -1e99}
        info["momentum_source_sum"] = 1e99
        audited = _momentum_audit([(0.1, info)], geometry)
        self.assertEqual(audited["product_field_names_used"], [])
        self.assertNotEqual(audited["rows"][0]["recomputed_stage_a"]["left"], 1e99)

    def test_no_unapproved_equality_threshold_can_pass_c3(self):
        self.assertEqual(classify(True, True, True,
                                  {"status": "PASS"},
                                  {"status": "PASS"}),
                         "P4_SCI_C3_INCONCLUSIVE")

    def test_b1_consumes_persisted_interface_left_and_verifies_fallback_reasons(self):
        geometry = {"areas": [1.0, 1.0], "faces": [0.0, 1.0], "centers": [0.5]}
        stage = _stage([(1.0, 0.0, 100000.0, 0.2)], geometry)
        # A changed chamber must not change B1's literal B0 input.
        stage["chamber_state"] = [0.2, 30000.0, 0.04]
        stage["external_faces"]["riemann"]["interface"]["reason"] = "forced_hlle"
        stage["external_faces"]["riemann"]["wall"]["reason"] = "forced_hlle"
        stage["external_faces"]["riemann"]["interface"]["speeds"] = [-1.0, 0.0, 1.0]
        stage["external_faces"]["riemann"]["wall"]["speeds"] = [-1.0, 0.0, 1.0]
        stage["external_faces"]["riemann"]["interface"]["speeds"] = [-1.0, 0.0, 1.0]
        stage["external_faces"]["riemann"]["wall"]["speeds"] = [-1.0, 0.0, 1.0]
        b0 = {"status": "PASS", "captured": stage["external_faces"]}
        with patch("dev_orchestrator.p4_c3_return_audit._b0_audit_stage",
                   return_value=b0), patch(
                "dev_orchestrator.p4_c3_return_audit.audit_hllc",
                return_value=((0.0, 1.0, 0.0, 0.0), (-1.0, 0.0, 1.0), "forced_hlle")):
            result = _b1_audit_stage(stage, geometry)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["result"]["fallback"],
                         {"interface": True, "wall": True})
        self.assertEqual(result["result"]["reason_checks"],
                         {"interface_reason_matches": True,
                          "wall_reason_matches": True})

    def test_b2_rejects_dt_mismatch_before_balance(self):
        geometry = {"areas": [1.0, 1.0], "faces": [0.0, 1.0], "centers": [0.5]}
        a = _stage([(1.0, 0.0, 100000.0, 0.2)], geometry, dt=0.1)
        b = copy.deepcopy(a)
        b["dt"] = 0.2
        report = _momentum_audit([(0.1, {"audit_stages": {
            "stage_a": a, "stage_b": b,
            "after": {"conservative": copy.deepcopy(a["conservative"])}
        }})], geometry)
        self.assertEqual(report["status"], "FAIL")
        self.assertEqual(report["rows"][0]["status_reason"], "stage_dt_mismatch")
        self.assertIn("Invalid audit evidence", report["status_reason"])

    def test_invalid_row_does_not_break_metric_aggregates(self):
        geometry = {"areas": [1.0, 1.0], "faces": [0.0, 1.0], "centers": [0.5]}
        valid = _stage([(1.0, 0.0, 100000.0, 0.2)], geometry)
        invalid = copy.deepcopy(valid)
        invalid["dt"] = 0.2
        history = [(0.1, {"audit_stages": {
            "stage_a": valid, "stage_b": valid,
            "after": {"conservative": copy.deepcopy(valid["conservative"])}}}),
                   (0.2, {"audit_stages": {
            "stage_a": valid, "stage_b": invalid,
            "after": {"conservative": copy.deepcopy(valid["conservative"])}}})]
        report = _momentum_audit(history, geometry)
        self.assertEqual(report["status_counts"], {"FAIL": 1, "METRIC_ONLY": 1})
        self.assertEqual(report["max_abs_residual"],
                         abs(report["rows"][0]["residual"]))

    def test_productive_reason_mismatch_blocks_b2_before_balance(self):
        geometry = {"areas": [1.0, 1.0], "faces": [0.0, 1.0], "centers": [0.5]}
        stage = _stage([(1.0, 0.0, 100000.0, 0.2)], geometry)
        stage["external_faces"]["riemann"]["interface"]["reason"] = "wrong"
        info = {"audit_stages": {"stage_a": stage, "stage_b": copy.deepcopy(stage),
                                 "after": {"conservative": copy.deepcopy(stage["conservative"])}}}
        report = _momentum_audit([(0.1, info)], geometry)
        self.assertEqual(report["status"], "FAIL")
        self.assertNotIn("residual", report["rows"][0])
        self.assertEqual(report["rows"][0]["status_reason"],
                         "productive_audit_fallback_reason_mismatch")

    def test_productive_wall_reason_mismatch_blocks_b2_before_balance(self):
        geometry = {"areas": [1.0, 1.0], "faces": [0.0, 1.0], "centers": [0.5]}
        stage = _stage([(1.0, 0.0, 100000.0, 0.2)], geometry)
        stage["external_faces"]["riemann"]["wall"]["reason"] = "wrong"
        info = {"audit_stages": {"stage_a": stage, "stage_b": copy.deepcopy(stage),
                                 "after": {"conservative": copy.deepcopy(stage["conservative"])}}}
        report = _momentum_audit([(0.1, info)], geometry)
        self.assertEqual(report["status"], "FAIL")
        self.assertEqual(report["rows"][0]["status_reason"],
                         "productive_audit_fallback_reason_mismatch")

    def test_missing_riemann_metadata_is_inconclusive_without_residual(self):
        geometry = {"areas": [1.0, 1.0], "faces": [0.0, 1.0], "centers": [0.5]}
        stage = _stage([(1.0, 0.0, 100000.0, 0.2)], geometry)
        del stage["external_faces"]["riemann"]
        info = {"audit_stages": {"stage_a": stage, "stage_b": copy.deepcopy(stage),
                                 "after": {"conservative": copy.deepcopy(stage["conservative"])}}}
        report = _momentum_audit([(0.1, info)], geometry)
        self.assertEqual(report["status"], "INCONCLUSIVE")
        self.assertNotIn("residual", report["rows"][0])

    def test_wave_parity_is_metric_only(self):
        geometry = {"areas": [1.0, 1.0], "faces": [0.0, 1.0], "centers": [0.5]}
        stage = _stage([(1.0, 0.0, 100000.0, 0.2)], geometry)
        stage["external_faces"]["riemann"]["interface"]["speeds"] = [1.0, 2.0, 3.0]
        result = _b1_audit_stage(stage, geometry)
        self.assertEqual(result["status"], "PASS")
        self.assertFalse(result["result"]["wave_parity"]["interface_waves_match"])

    def test_real_wall_fallback_is_preserved_and_checked(self):
        geometry = {"areas": [1.0, 1.0], "faces": [0.0, 1.0], "centers": [0.5]}
        stage = _stage([(1.0, -1000.0, 0.9999999999999999, 0.2)], geometry)
        result = _recompute_stage_b(stage, geometry)
        self.assertTrue(result["b1"]["fallback"]["wall"])
        self.assertEqual(result["b1"]["product_reasons"]["wall"],
                         result["b1"]["wall_reason"])

    def test_physical_flux_has_conservative_energy_and_species(self):
        flux = _physical_flux((2.0, 3.0, 5.0, 0.25))
        self.assertEqual(flux[0], 6.0)
        self.assertEqual(flux[3], 1.5)

    def test_return_selection_uses_pre_step_sample_time(self):
        history = [(0.004, {"mass_flux": 1.0,
                            "sample_time_pre_step": 0.002})]
        selected, window = _select_return(history, 0.002)
        self.assertEqual(selected[0], 0.002)
        self.assertEqual(window, (0.001, 0.003))

        fallback_history = [(0.0025, {"mass_flux": 1.0})]
        selected, window = _select_return(fallback_history, 0.0025)
        self.assertEqual(selected[0], 0.0025)
        self.assertEqual(window, (0.00125, 0.00375))

    def test_real_step_captures_stage_a_pre_step_and_primitive_consistently(self):
        result = solve_c2_one(12, 0.2, 200000.0, 400.0, 0.5,
                              100000.0, 300.0, 0.2, t_final=1e-5)
        audited = [(time_value, info) for time_value, info in
                    result["interface_history"] if "audit_stages" in info]
        self.assertTrue(audited)
        _, info = audited[0]
        stages = info["audit_stages"]
        stage_a = stages["stage_a"]
        self.assertNotEqual(stages["stage_a"]["conservative"],
                            stages["after"]["conservative"])
        self.assertNotEqual(stages["stage_a"]["chamber_state"],
                            stages["after"]["chamber_state"])
        for row, primitive, volume in zip(
                stages["stage_a"]["conservative"],
                stages["stage_a"]["primitive"],
                result["audit_geometry"]["volumes"]):
            derived = EOS.primitive(tuple(value / volume for value in row))
            for actual, expected in zip(primitive, derived):
                self.assertAlmostEqual(actual, expected, places=12)
        expected_pressure = (EOS.gamma - 1.0) * stage_a["chamber_state"][1] / C2_VOLUME
        self.assertAlmostEqual(info["p_chamber"], expected_pressure, places=12)
        self.assertEqual(info["chamber_state"], stage_a["chamber_state"])
        self.assertEqual(info["first_cell_state"], stage_a["conservative"][0])
        self.assertEqual(info["sample_time_pre_step"], stage_a["time"])
        self.assertGreater(info["history_record_time_post_step"],
                           info["sample_time_pre_step"])

if __name__ == "__main__":
    unittest.main()
