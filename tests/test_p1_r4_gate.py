import copy
import json
import unittest
from pathlib import Path
from dev_orchestrator.p1_r4_gate import refinement_checks,revised_t11


class R4GateTests(unittest.TestCase):
    def setUp(self):
        root=Path(__file__).resolve().parents[1]
        self.study=json.loads((root/'results/p1-r4-cfl-20260918/study/artifacts/study.json').read_text(encoding='utf-8'))
        self.original=json.loads((root/'results/p1-r3-fronteras-20260918/p2a-attempt-2/artifacts/p2a-summary.json').read_text(encoding='utf-8'))['matrix']['T11']

    def test_complete_evidence_passes_reviewed_criterion(self):
        result=revised_t11(self.original,self.study)
        self.assertEqual(result['status'],'PASS')
        self.assertFalse(result['superseded_diagnostics']['pulse_0.6_amplitude'])
        self.assertEqual(self.original['status'],'FAIL')

    def test_missing_mesh_blocks(self):
        self.study['rows']=[r for r in self.study['rows'] if r['N']!=1600]
        self.assertFalse(all(refinement_checks(self.study).values()))

    def test_nondecreasing_pair_blocks(self):
        rows={(r['N'],r['CFL']):r for r in self.study['rows']}
        rows[1600,.6]['amplitude_Pa']=rows[1600,.2]['amplitude_Pa']+2.
        self.assertFalse(refinement_checks(self.study)['sensitivity_decreases_0.2_0.6'])

    def test_common_bias_or_parent_failure_blocks(self):
        original=copy.deepcopy(self.study)
        for r in self.study['rows']:r['analytical_amplitude_error']=.2
        self.assertFalse(all(refinement_checks(self.study).values()))
        self.study=original
        next(r for r in self.study['rows'] if r['N']==1600 and r['CFL']==.6)['parent_checks']['pressure_L1']=False
        self.assertFalse(all(refinement_checks(self.study).values()))

    def test_sod_and_speed_failures_are_not_superseded(self):
        for key in ('Sod_0.6_u','pulse_0.6_speed'):
            bad=copy.deepcopy(self.original);bad['checks'][key]=False
            self.assertEqual(revised_t11(bad,self.study)['status'],'FAIL')


if __name__=='__main__':unittest.main()
