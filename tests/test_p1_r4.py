import unittest
from dev_orchestrator.p1_r4_cfl import differences, numerical_result, frozen_checks


class CFLStudyTests(unittest.TestCase):
    def test_metric_preserves_prescribed_ten_pa_denominator(self):
        d=differences(8.832393583405064,7.99875531278667)
        self.assertEqual(d['normalized'],0.0833638270618394)
        self.assertEqual(d,differences(7.99875531278667,8.832393583405064))
        self.assertNotEqual(d['normalized'],d['absolute_Pa']/7.99875531278667)

    def test_determinism_discards_only_wall_clock(self):
        a={'wall_seconds':1.,'cells':[[1.,2.,3.,4.]],'steps':8,'ledger':[{'dt':.1}]}
        b={**a,'wall_seconds':2.}
        self.assertEqual(numerical_result(a),numerical_result(b))
        self.assertIn('wall_seconds',a)
        b['steps']=9
        self.assertNotEqual(numerical_result(a),numerical_result(b))
        b={**a,'ledger':[{'dt':.2}]}
        self.assertNotEqual(numerical_result(a),numerical_result(b))

    def test_frozen_implementation_and_previous_contracts(self):
        checks=frozen_checks()
        self.assertTrue(all(checks.values()),checks)


if __name__=='__main__':unittest.main()
