import copy
import unittest
from pathlib import Path

from dev_orchestrator.p1_r5_review import load_records, candidate_r5, ROOT

class RevisedGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records, cls.provenance = load_records(ROOT / 'results/p1-r5e-20260918/acquisition')

    def test_r4_failure_remains_visible(self):
        revised, original, rows = candidate_r5(self.records)
        self.assertFalse(original['checks']['sensitivity_0.4_0.6'])
        self.assertEqual(len(rows),9)
        self.assertTrue(all(r['complete'] for r in rows))
        for row in rows:
            self.assertEqual(row['amplitude_Pa'],row['metrics']['amplitude'])
            self.assertEqual(row['reference_Pa'],row['metrics']['analytical_amplitude'])
        self.assertEqual(original['metrics'],revised['T11']['metrics'])

    def test_missing_case_cannot_pass(self):
        records = dict(self.records)
        records.pop('T03_0.2_N1600')
        with self.assertRaises(KeyError):
            candidate_r5(records)

    def test_missing_sod_cannot_pass_with_complete_acoustics(self):
        records = dict(self.records)
        records.pop('T02_sod_0.2')
        matrix, _, _ = candidate_r5(records)
        self.assertEqual(matrix['T11']['status'], 'FAIL')
        self.assertFalse(matrix['T11']['checks']['complete_parent_suite'])
        self.assertFalse(matrix['T11']['checks']['comparisons_complete'])

    def test_partial_is_not_final(self):
        records = dict(self.records)
        row = copy.deepcopy(records['T03_0.2_N1600'])
        row['status']='FAIL'
        row['result']['status']='failed_infrastructure'
        records[row['name']]=row
        matrix, _, rows = candidate_r5(records)
        self.assertEqual(matrix['T11']['status'],'FAIL')
        self.assertFalse(matrix['T11']['checks']['all_nine_final'])
        self.assertIsNone(next(r for r in rows if r['name']==row['name'])['amplitude_Pa'])

    def test_middle_mesh_error_still_matters(self):
        records = dict(self.records)
        row = copy.deepcopy(records['T03_0.4'])
        row['metrics']['analytical_amplitude_error']=1.
        records[row['name']]=row
        matrix, _, _ = candidate_r5(records)
        self.assertFalse(matrix['T11']['checks']['analytical_error_0.4'])
        self.assertEqual(matrix['T11']['status'],'FAIL')

    def test_stage_conservation_is_not_bypassed(self):
        records = dict(self.records)
        row = copy.deepcopy(records['T03_0.4'])
        row['result']['stage_ledger'][0]['stage1_normalized'][0]=1e-8
        records[row['name']]=row
        matrix, _, _ = candidate_r5(records)
        self.assertFalse(matrix['T11']['checks']['four_balances_steps_stages'])

    def test_t10_order_threshold_unchanged(self):
        records = dict(self.records)
        row = copy.deepcopy(records['T10_800'])
        row['metrics']['density_L1']=records['T10_400']['metrics']['density_L1']
        records[row['name']]=row
        matrix, _, _ = candidate_r5(records)
        self.assertEqual(matrix['T10']['metrics']['order_400_800_density_L1'],0.)
        self.assertEqual(matrix['T10']['status'],'FAIL')

if __name__=='__main__':
    unittest.main()
