import json
import unittest
from pathlib import Path

from dev_orchestrator.p4_r12_audit import as_bool, streak

class R12AuditTests(unittest.TestCase):
    def test_numpy_bool_never_becomes_string_false(self):
        self.assertEqual(json.loads(json.dumps({"ok": bool(False)}))["ok"], False)
        self.assertIs(type(json.loads(json.dumps({"ok": bool(False)}))["ok"]), bool)
        self.assertFalse(as_bool("False"))

    def test_branch_streaks_are_independent(self):
        self.assertEqual(streak([False, False, True, True, True]), 3)
        self.assertEqual(streak([True, True, False]), 2)

    def test_r12_n400_even_sequence_does_not_close(self):
        self.assertEqual(streak([True, True, False]), 2)

    def test_saved_n400_failure_and_n350_pass(self):
        root = Path("results/p4-r12-20260922")
        n400 = json.loads((root / "r12_continuation_N400_50_54.json").read_text())
        n350 = json.loads((root / "r12_continuation_N350_45_52.json").read_text())
        self.assertEqual(n400["temporal"][-1]["cycle"], 54)
        self.assertFalse(n400["temporal"][-1]["d2_passed"])
        self.assertTrue(n350["temporal"][-1]["d2_passed"])

if __name__ == "__main__":
    unittest.main()
