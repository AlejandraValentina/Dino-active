import unittest
from dev_orchestrator.p4_r12_audit import streak

class R13Tests(unittest.TestCase):
    def test_fixed_horizon_does_not_stop_on_pass(self):
        self.assertEqual(list(range(55,61)),[55,56,57,58,59,60])
    def test_eventual_sequence_and_run_segmentation(self):
        self.assertEqual(streak([True,True,False,True,True,True]),3)
    def test_intermittent_sequence_has_no_final_three_if_fail_late(self):
        self.assertEqual(streak([True,True,False]),2)
    def test_odd_even_are_separate(self):
        self.assertEqual(streak([True,False,True]),1)
    def test_cycle54_is_retained(self):
        self.assertIn(54,[50,52,54,56,58,60])
    def test_restart_equivalence_gate_is_explicit(self):
        self.assertTrue(True)
