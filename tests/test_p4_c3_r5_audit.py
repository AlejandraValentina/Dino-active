import copy
import hashlib
import struct
import unittest
from unittest.mock import patch

from dev_orchestrator.p4_c3_r5_audit import (
    CONTRACT, EOS, audit_a, audit_b0, audit_b1, audit_b2, canonical_binary64,
    canonical_digest, evaluate_c3_r5, reconstruct_all_faces, runtime_binding,
)
from dev_orchestrator.reference.hllc_audit import hllc
from dev_orchestrator.p4_sci_04b import solve_c2_one


GEOMETRY = {"areas": [1.0, 2.0], "faces": [0.0, 1.0], "centers": [0.5],
            "chamber_volume": 1.0}
STATE = (1.0, 0.0, 2.0, 0.2)


def _stage(q0=3.0, dt=0.25):
    chamber = [1.0, 2.0 / (EOS.gamma - 1.0), 0.2]
    faces = reconstruct_all_faces([STATE], GEOMETRY, chamber)
    riemann = []
    for face, area in zip(faces["faces"], GEOMETRY["areas"]):
        flux, waves, reason = hllc(tuple(face["left"]), tuple(face["right"]), EOS)
        scaled = tuple(area * value for value in flux)
        if face["kind"] == "wall":
            scaled = (0.0, scaled[1], 0.0, 0.0)
        riemann.append({"index": face["index"], "kind": face["kind"],
                        "flux": list(scaled), "waves": list(waves), "reason": reason})
    source = [2.0]
    rhs = [0.0]
    return {"dt": dt, "primitive": [list(STATE)],
            "conservative": [[1.0, q0, 2.0 / (EOS.gamma - 1.0), 0.2]],
            "chamber_state": chamber,
            "r5_momentum": {"faces": faces["faces"], "riemann": riemann,
                            "downgraded_cells": faces["downgraded_cells"],
                            "source": source, "rhs": rhs}}


def _passing_acquisition():
    stage_a = _stage(q0=3.0)
    stage_b = _stage(q0=3.0)
    stage_b["provisional"] = [[1.0, 3.0, 2.0 / (EOS.gamma - 1.0), 0.2]]
    after = {"conservative": [[1.0, 3.0, 2.0 / (EOS.gamma - 1.0), 0.2]]}
    item = {"sample_time_pre_step": 1.0, "mass_flux": 1.0,
            "audit_stages": {"stage_a": stage_a, "stage_b": stage_b,
                             "after": after}}
    return {"contract": CONTRACT, "acquisition_kind": "focal_c3_r5",
             "runtime": runtime_binding(), "max_global_resid": 0.0,
             "solver_status": "completed",
             "solver_time": 1.0, "target_final_time": 1.0,
             "expected_return_time": 1.0, "history": [item]}


class P4C3R5AuditTests(unittest.TestCase):
    def test_real_product_capture_passes_independent_b0_b1_b2(self):
        result = solve_c2_one(12, 0.2, 200000.0, 400.0, 0.5,
                              100000.0, 300.0, 0.2, t_final=1e-5)
        info = next(payload for _, payload in result["interface_history"]
                    if "audit_stages" in payload)
        stages = info["audit_stages"]
        geometry = result["audit_geometry"]
        self.assertEqual(audit_b0(stages["stage_a"], geometry)["status"], "PASS")
        self.assertEqual(audit_b1(stages["stage_a"], geometry)["status"], "PASS")
        self.assertEqual(audit_b1(stages["stage_b"], geometry)["status"], "PASS")
        self.assertEqual(audit_b2(stages["stage_a"], stages["stage_b"],
                                  stages["after"], geometry)["status"], "PASS")

    def test_b0_is_independent_and_mutation_is_detected(self):
        stage = _stage()
        self.assertEqual(audit_b0(stage, GEOMETRY)["status"], "PASS")
        mutated = copy.deepcopy(stage)
        mutated["r5_momentum"]["faces"][0]["right"][2] += 1.0
        self.assertEqual(audit_b0(mutated, GEOMETRY)["status"], "INCONCLUSIVE")

    def test_malformed_b0_face_values_are_inconclusive(self):
        stage = _stage()
        stage["r5_momentum"]["faces"][0]["left"] = [1.0, 0.0]
        self.assertEqual(audit_b0(stage, GEOMETRY)["status"], "INCONCLUSIVE")

    def test_malformed_a_waves_are_inconclusive(self):
        acquisition = _passing_acquisition()
        product = acquisition["history"][0]["audit_stages"]["stage_a"][
            "r5_momentum"]["riemann"][0]
        product["waves"] = [0.0, 1.0]
        self.assertEqual(audit_a(acquisition["history"][0])["status"], "INCONCLUSIVE")

    def test_b1_requires_exact_full_vector_waves_and_reason(self):
        stage = _stage()
        self.assertEqual(audit_b1(stage, GEOMETRY)["status"], "PASS")
        mutated = copy.deepcopy(stage)
        mutated["r5_momentum"]["riemann"][0]["flux"][1] = struct.unpack(
            "<d", struct.pack("<d", 2.0 + 2.0 ** -50))[0]
        self.assertEqual(audit_b1(mutated, GEOMETRY)["status"], "INCONCLUSIVE")

    def test_malformed_b1_flux_or_waves_are_inconclusive(self):
        for field, value in (("flux", [0.0]), ("waves", [0.0, "bad", 1.0])):
            stage = _stage()
            stage["r5_momentum"]["riemann"][0][field] = value
            self.assertEqual(audit_b1(stage, GEOMETRY)["status"], "INCONCLUSIVE")

    def test_nonfinite_b2_state_and_replay_values_are_inconclusive(self):
        stage_a = _stage(q0=3.0)
        stage_b = _stage(q0=3.0)
        stage_b["provisional"] = copy.deepcopy(stage_b["conservative"])
        after = {"conservative": copy.deepcopy(stage_b["conservative"])}
        cases = []
        broken = copy.deepcopy(stage_a); broken["conservative"][0][1] = float("nan"); cases.append((broken, stage_b, after))
        broken = copy.deepcopy(stage_a); broken["primitive"][0][2] = float("inf"); cases.append((broken, stage_b, after))
        broken = copy.deepcopy(stage_a); broken["r5_momentum"]["rhs"][0] = float("nan"); cases.append((broken, stage_b, after))
        broken_b = copy.deepcopy(stage_b); broken_b["provisional"][0][1] = float("nan"); cases.append((stage_a, broken_b, after))
        broken_after = copy.deepcopy(after); broken_after["conservative"][0][1] = float("inf"); cases.append((stage_a, stage_b, broken_after))
        for a, b, end in cases:
            with self.subTest(a=a is not stage_a, b=b is not stage_b, end=end is not after):
                self.assertEqual(audit_b2(a, b, end, GEOMETRY)["status"], "INCONCLUSIVE")

    def test_b2_analytic_case_has_manual_expected_result(self):
        stage_a = _stage(q0=3.0)
        stage_b = _stage(q0=3.0)
        stage_b["provisional"] = [[1.0, 3.0, 2.0 / (EOS.gamma - 1.0), 0.2]]
        after = {"conservative": [[1.0, 3.0, 2.0 / (EOS.gamma - 1.0), 0.2]]}
        report = audit_b2(stage_a, stage_b, after, GEOMETRY)
        self.assertEqual(report["status"], "PASS")
        # Analytic uniform-pressure result: 2 - (2*2) + 2*(2-1) = 0.
        self.assertEqual(report["rows"][0]["source"], [2.0])
        self.assertEqual(report["rows"][0]["rhs"], [0.0])
        self.assertEqual(report["final_expected"], [3.0])

    def test_canonical_binary64_and_digest_are_stable(self):
        values = [[1.0, [-0.0]], [2.5]]
        payload = canonical_binary64(values)
        self.assertEqual(payload[:8], struct.pack("<Q", 3))
        self.assertEqual(payload[8:], b"".join(struct.pack("<d", value)
                                               for value in (1.0, -0.0, 2.5)))
        self.assertEqual(payload, canonical_binary64(values))
        digest = canonical_digest(values)
        self.assertEqual(digest["count"], 3)
        self.assertEqual(digest["sha256"], hashlib.sha256(payload).hexdigest())
        self.assertNotEqual(canonical_digest([[1.0, [-0.0]], [2.5]])["sha256"],
                            canonical_digest([[1.0, [-0.0]], [2.5 + 2.0 ** -50]])["sha256"])
        self.assertNotEqual(canonical_binary64([0.0]), canonical_binary64([-0.0]))

    def test_a_fail_cannot_be_overridden_by_external_gate_a(self):
        acquisition = _passing_acquisition()
        acquisition["gate_a"] = "PASS"
        acquisition["history"][0]["audit_stages"]["stage_a"][
            "r5_momentum"]["riemann"][0]["waves"].reverse()
        report = evaluate_c3_r5(acquisition, GEOMETRY,
                                 expected_runtime=acquisition["runtime"])
        self.assertEqual(report["a"]["status"], "FAIL")
        self.assertEqual(report["classification"], "P4_SCI_C3_FAIL")

    def test_external_gate_and_return_record_cannot_forge_selection(self):
        acquisition = _passing_acquisition()
        acquisition["gate_a"] = "FAIL"
        acquisition["return_record"] = {"foreign": "evidence"}
        report = evaluate_c3_r5(acquisition, GEOMETRY,
                                 expected_runtime=acquisition["runtime"])
        self.assertEqual(report["classification"], "P4_SCI_C3_PASS")
        self.assertEqual(report["return_selection"]["index"], 0)
        self.assertEqual(report["a"]["status"], "PASS")

    def test_a_is_evaluated_once_on_first_causal_history_record(self):
        acquisition = _passing_acquisition()
        second = copy.deepcopy(acquisition["history"][0])
        second["sample_time_pre_step"] = 1.1
        acquisition["history"].append(second)
        first = acquisition["history"][0]
        with patch("dev_orchestrator.p4_c3_r5_audit.audit_a",
                   return_value={"status": "PASS"}) as mocked:
            report = evaluate_c3_r5(acquisition, GEOMETRY,
                                     expected_runtime=acquisition["runtime"])
        self.assertEqual(mocked.call_count, 1)
        self.assertIs(mocked.call_args.args[0], first)
        self.assertEqual(report["return_selection"]["index"], 0)
        self.assertEqual(report["classification"], "P4_SCI_C3_PASS")

    def test_matching_fallback_is_still_unexpected_for_gate_a(self):
        acquisition = _passing_acquisition()
        record = acquisition["history"][0]
        stage = record["audit_stages"]["stage_a"]
        product = stage["r5_momentum"]["riemann"][0]
        product["reason"] = "synthetic-fallback"
        original = tuple(product["flux"])
        waves = tuple(product["waves"])
        area = GEOMETRY["areas"][0]
        per_area = tuple(value / area for value in original)
        with patch("dev_orchestrator.p4_c3_r5_audit.audit_hllc",
                   return_value=(per_area, waves, "synthetic-fallback")):
            report = audit_a(record)
        self.assertEqual(report["status"], "FAIL")
        self.assertFalse(report["checks"]["no_unexpected_fallback"])

    def test_a_rejects_mixed_interface_riemann_provenance(self):
        acquisition = _passing_acquisition()
        record = acquisition["history"][0]
        record["audit_stages"]["stage_a"]["r5_momentum"]["riemann"][0][
            "kind"] = "interior"
        report = audit_a(record)
        self.assertEqual(report["status"], "INCONCLUSIVE")
        self.assertEqual(report["reason"], "mixed_or_missing_interface_provenance")

    def test_missing_expected_return_time_is_inconclusive(self):
        acquisition = _passing_acquisition()
        del acquisition["expected_return_time"]
        report = evaluate_c3_r5(acquisition, GEOMETRY,
                                 expected_runtime=acquisition["runtime"])
        self.assertEqual(report["classification"], "P4_SCI_C3_INCONCLUSIVE")
        self.assertEqual(report["reason"], "causal_return_not_selected_from_history")

    def test_malformed_b2_evidence_is_inconclusive_not_exception(self):
        stage_a = _stage(q0=3.0)
        stage_b = _stage(q0=3.0)
        stage_b["provisional"] = [[1.0, 3.0, 2.0 / (EOS.gamma - 1.0), 0.2]]
        after = {"conservative": [[1.0, 3.0, 2.0 / (EOS.gamma - 1.0), 0.2]]}
        broken_after = audit_b2(stage_a, stage_b, {}, GEOMETRY)
        self.assertEqual(broken_after["status"], "INCONCLUSIVE")
        broken_source = copy.deepcopy(stage_a)
        broken_source["r5_momentum"]["source"] = None
        report = audit_b2(broken_source, stage_b, after, GEOMETRY)
        self.assertEqual(report["status"], "INCONCLUSIVE")
        different_dt = copy.deepcopy(stage_b)
        different_dt["dt"] *= 2.0
        report = audit_b2(stage_a, different_dt, after, GEOMETRY)
        self.assertEqual(report["status"], "INCONCLUSIVE")

    def test_external_physical_pass_strings_cannot_forge_missing_metrics(self):
        acquisition = _passing_acquisition()
        acquisition["conservation"] = "PASS"
        acquisition["admissibility"] = "PASS"
        del acquisition["max_global_resid"]
        report = evaluate_c3_r5(acquisition, GEOMETRY,
                                 expected_runtime=acquisition["runtime"])
        self.assertEqual(report["classification"], "P4_SCI_C3_INCONCLUSIVE")
        self.assertEqual(report["reason"], "existing_physical_evidence_missing")

    def test_explicit_solver_failure_dominates_missing_conservation_metric(self):
        acquisition = _passing_acquisition()
        acquisition["solver_status"] = "failed_numerically"
        del acquisition["max_global_resid"]
        report = evaluate_c3_r5(acquisition, GEOMETRY,
                                 expected_runtime=acquisition["runtime"])
        self.assertEqual(report["classification"], "P4_SCI_C3_FAIL")
        self.assertEqual(report["reason"], "solver_admissibility_failed")

    def test_negative_conservation_residual_is_inconclusive(self):
        acquisition = _passing_acquisition()
        acquisition["max_global_resid"] = -1.0
        report = evaluate_c3_r5(acquisition, GEOMETRY,
                                 expected_runtime=acquisition["runtime"])
        self.assertEqual(report["classification"], "P4_SCI_C3_INCONCLUSIVE")
        self.assertEqual(report["reason"], "existing_physical_evidence_missing")

    def test_valid_fallback_with_none_middle_wave_is_semantic_fail(self):
        acquisition = _passing_acquisition()
        record = acquisition["history"][0]
        product = record["audit_stages"]["stage_a"]["r5_momentum"]["riemann"][0]
        product["reason"] = "synthetic-fallback"
        product["waves"] = [-1.0, None, 1.0]
        per_area = tuple(value / GEOMETRY["areas"][0] for value in product["flux"])
        with patch("dev_orchestrator.p4_c3_r5_audit.audit_hllc",
                   return_value=(per_area, (-1.0, None, 1.0), "synthetic-fallback")):
            report = audit_a(record)
        self.assertEqual(report["status"], "FAIL")
        self.assertFalse(report["checks"]["no_unexpected_fallback"])

    def test_existing_conservation_and_solver_status_fail_physically(self):
        acquisition = _passing_acquisition()
        acquisition["max_global_resid"] = 1e-9
        report = evaluate_c3_r5(acquisition, GEOMETRY,
                                 expected_runtime=acquisition["runtime"])
        self.assertEqual(report["classification"], "P4_SCI_C3_FAIL")
        self.assertEqual(report["reason"], "global_conservation_failed")
        acquisition = _passing_acquisition()
        acquisition["solver_status"] = "failed_numerically"
        report = evaluate_c3_r5(acquisition, GEOMETRY,
                                 expected_runtime=acquisition["runtime"])
        self.assertEqual(report["classification"], "P4_SCI_C3_FAIL")
        self.assertEqual(report["reason"], "solver_admissibility_failed")

    def test_completed_solver_requires_finite_target_and_reaches_it(self):
        for field in ("solver_time", "target_final_time"):
            acquisition = _passing_acquisition()
            del acquisition[field]
            report = evaluate_c3_r5(acquisition, GEOMETRY,
                                    expected_runtime=acquisition["runtime"])
            self.assertEqual(report["classification"], "P4_SCI_C3_INCONCLUSIVE")
        acquisition = _passing_acquisition()
        del acquisition["target_final_time"]
        report = evaluate_c3_r5(acquisition, GEOMETRY,
                                 expected_runtime=acquisition["runtime"])
        self.assertEqual(report["classification"], "P4_SCI_C3_INCONCLUSIVE")
        acquisition = _passing_acquisition()
        acquisition["solver_time"] = 0.5
        report = evaluate_c3_r5(acquisition, GEOMETRY,
                                 expected_runtime=acquisition["runtime"])
        self.assertEqual(report["classification"], "P4_SCI_C3_INCONCLUSIVE")
        self.assertEqual(report["reason"], "solver_completion_truncated")

    def test_timeout_truncation_is_inconclusive_but_explicit_failure_is_fail(self):
        acquisition = _passing_acquisition()
        acquisition["solver_status"] = "timeout"
        acquisition["solver_time"] = 0.5
        report = evaluate_c3_r5(acquisition, GEOMETRY,
                                 expected_runtime=acquisition["runtime"])
        self.assertEqual(report["classification"], "P4_SCI_C3_INCONCLUSIVE")
        acquisition["solver_status"] = "failed_numerically"
        report = evaluate_c3_r5(acquisition, GEOMETRY,
                                 expected_runtime=acquisition["runtime"])
        self.assertEqual(report["classification"], "P4_SCI_C3_FAIL")

    def test_runtime_binding_hashes_all_r5_reference_sources(self):
        names = {name.replace("\\", "/").split("/")[-1]
                 for name in runtime_binding()["source_sha256"]}
        self.assertTrue({"p4_sci_04b.py", "p4_c3_r5_audit.py",
                         "hllc_audit.py", "exact_riemann.py",
                         "second_order.py", "riemann.py", "eos.py"}.issubset(names))

    def test_runtime_binding_is_required_and_different_runtime_is_inconclusive(self):
        runtime = runtime_binding()
        acquisition = {"contract": CONTRACT, "acquisition_kind": "focal_c3_r5",
                       "runtime": runtime, "history": [], "gate_a": "PASS"}
        self.assertEqual(evaluate_c3_r5(acquisition, GEOMETRY,
                                        expected_runtime={})["classification"],
                         "P4_SCI_C3_INCONCLUSIVE")

    def test_fallback_reason_is_an_identity_field(self):
        stage = _stage()
        stage["r5_momentum"]["riemann"][0]["reason"] = "wrong-fallback"
        self.assertEqual(audit_b1(stage, GEOMETRY)["status"], "FAIL")


if __name__ == "__main__":
    unittest.main()
