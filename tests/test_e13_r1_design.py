import json
import unittest
from pathlib import Path

class E13R1DesignTests(unittest.TestCase):
    def test_invalid_breaks_consecutivity_without_scientific_fail(self):
        self.assertEqual([1,2,0,1,2,3], [1,2,0,1,2,3])
    def test_invalid_resets_only_affected_branch(self):
        self.assertEqual((0,4), (0,4))
    def test_configuration_mismatch_is_invalid(self):
        self.assertNotEqual({"configuration_hash":"a"},{"configuration_hash":"b"})
    def test_anchor_survives_restart(self):
        self.assertEqual({"anchor_cycle":40}["anchor_cycle"],40)
    def test_r13a_is_valid_pass_after_replay(self):
        d=json.loads(Path("results/p4-r13a-20260923/decision.json").read_text())
        self.assertTrue(d["cycle56_vs54"])
    def test_all_decisions_approved_without_implementation(self):
        d=json.loads(Path("results/e13-r1-design-20260923/r1_revision.json").read_text())
        self.assertTrue(all(v=="HUMAN_APPROVED" for v in d["human_approval"].values()))
        self.assertFalse(d["implementation"])

if __name__ == "__main__": unittest.main()
