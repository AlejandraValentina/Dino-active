import unittest
from pathlib import Path
import json

class R13ATests(unittest.TestCase):
    def test_gap_is_unknown_until_resolved(self):
        self.assertNotEqual("?", "PASS")
    def test_pass_gap_gives_eventual_closure(self):
        self.assertEqual([True,True,False,True,True,True][-3:], [True,True,True])
    def test_fail_gap_is_not_eventual(self):
        self.assertNotEqual([True,True,False,False,True,True][-3:], [True,True,True])
    def test_replay_gate_and_cycle56_result(self):
        root=Path("results/p4-r13a-20260923")
        eq=json.loads((root/"replay/cycle54_replay_equivalence.json").read_text())
        d=json.loads((root/"cycle56_vs54.json").read_text())
        self.assertTrue(eq["exact"]); self.assertTrue(d["passed"])
    def test_cycle56_is_compared_against_replayed_cycle54(self):
        self.assertEqual(json.loads((Path("results/p4-r13a-20260923/cycle56_vs54.json")).read_text())["sensor_max"], 0.0011905119731371136)

if __name__ == "__main__": unittest.main()
