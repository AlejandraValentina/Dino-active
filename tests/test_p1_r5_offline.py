import unittest

from dev_orchestrator.p1_r5_offline import reproduce


class OfflineReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = reproduce()

    def test_partial_is_not_final_evidence(self):
        rows = self.report['rows']
        self.assertEqual(sum(r['complete'] for r in rows), 8)
        missing = next(r for r in rows if not r['complete'])
        self.assertEqual((missing['N'], missing['CFL']), (1600, .2))
        self.assertIsNone(missing['amplitude_Pa'])
        self.assertIsNone(missing['normalized_error_to_10Pa'])
        self.assertFalse(self.report['R5_adopted'])
        self.assertFalse(self.report['phase_B_authorized_by_gate'])

    def test_available_failure_not_masked(self):
        pair = next(p for p in self.report['pairs'] if p['CFL_pair'] == [.4, .6])
        coarse, middle, fine = pair['S400_S800_S1600']
        self.assertGreater(middle, coarse)
        self.assertLess(fine, coarse)
        for p in self.report['pairs']:
            if .2 in p['CFL_pair']:
                self.assertIsNone(p['S400_S800_S1600'][2])

    def test_reference_and_conservation_reproduced(self):
        for r in self.report['rows']:
            self.assertTrue(r['admissible_recorded_interval'])
            self.assertLessEqual(max(r['residual_components'] + r['stage_residual_components']), 1e-10)
            if r['complete']:
                self.assertEqual(r['amplitude_Pa'], r['metrics']['amplitude'])
                self.assertEqual(r['reference_Pa'], r['metrics']['analytical_amplitude'])
                self.assertEqual(r['normalized_error_to_10Pa'], r['metrics']['analytical_amplitude_error'])


if __name__ == '__main__':
    unittest.main()
