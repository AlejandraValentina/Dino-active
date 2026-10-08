import copy
import gzip
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from dev_orchestrator import p2b_resume as p
from dev_orchestrator.p2b_campaign import run_case


class ResumeTests(unittest.TestCase):
    def test_relative_checkpoint_path_from_cli(self):
        records,_=p.load_reusable('results/p2b-gas1d-20260918/attempt-2',p.source_hashes())
        self.assertEqual(len(records),8)

    def test_current_scientific_failure_not_hidden_by_previous_timeout(self):
        checks=dict(baseline_intact=True,solver_unchanged=True,P2B=False)
        failures=[dict(solver_status='failed_infrastructure')]
        self.assertEqual(p.classify_state(checks,None,failures),'FAILED_INFRASTRUCTURE')
        for stop,expected in ((dict(solver_status='failed_numerical'),'P2_BLOCKED_POSITIVITY'),
            (dict(solver_status='completed',reason='final_time'),'P2_BLOCKED_SECOND_ORDER'),
            (dict(reason='contractual aggregate failure'),'P2_BLOCKED_SECOND_ORDER')):
            self.assertEqual(p.classify_state(checks,stop,failures),expected)
        checks['baseline_intact']=False
        self.assertEqual(p.classify_state(checks,None,failures),'P2_BLOCKED_REGRESSION')

    def test_only_completed_identical_records_reused(self):
        records,origins=p.load_reusable(p.PREVIOUS,p.source_hashes())
        self.assertEqual(len(records),8)
        self.assertNotIn('T04',records)
        self.assertEqual(set(records),set(origins))
        self.assertTrue(all(len(o['sha256'])==64 for o in origins.values()))

    def test_changed_solver_refuses_reuse(self):
        source=p.source_hashes();source['motorsim/gas1d/second_order.py']='changed'
        with self.assertRaisesRegex(ValueError,'source hashes differ'):p.load_reusable(p.PREVIOUS,source)

    def test_timeout_retention_is_explicit_and_never_accepted(self):
        folder=p.ROOT/'results/p2b-gas1d-20260918/resume-300-attempt-1'
        normal,_=p.load_reusable(folder,p.source_hashes())
        self.assertNotIn('T10_800',normal)
        records,origins=p.load_reusable(folder,p.source_hashes(),retain_timeouts=True)
        self.assertIn('T10_800',records)
        self.assertFalse(origins['T10_800']['accepted'])
        self.assertEqual(records['T10_800']['result']['status'],'failed_infrastructure')
        self.assertEqual(p.test_gate('T10',records)['status'],'FAIL')

    def test_changed_inputs_change_signature(self):
        path=p.PREVIOUS/'artifacts/cases/T01_rest.json.gz'
        record=json.loads(gzip.decompress(path.read_bytes()))
        expected=p.expected_signature('T01_rest')
        self.assertEqual(p.signature(record),expected)
        record['configuration']['CFL']=.2
        self.assertNotEqual(p.signature(record),expected)

    def test_corrupt_checkpoint_evidence_rejected(self):
        with tempfile.TemporaryDirectory(dir=p.ROOT/'dev_orchestrator/runs') as directory:
            folder=Path(directory);(folder/'artifacts').mkdir()
            (folder/'bad.gz').write_bytes(b'bad')
            p.write(folder/'artifacts/resume-checkpoint.json',dict(source_sha256=p.source_hashes(),cases={'T01_rest':dict(path='bad.gz',sha256='wrong')}))
            with self.assertRaisesRegex(ValueError,'artifact hash mismatch'):p.load_reusable(folder,p.source_hashes())

    def test_incomplete_t12_never_passes(self):
        records={name:dict(status='PASS') for name in ('T12_contact','T12_expansion','T12_pure0','T12_pure1')}
        gate=p.test_gate('T12',records)
        self.assertEqual(gate['status'],'PARTIAL');self.assertEqual(gate['expected_subcases'],10)

    def test_t10_requires_both_contractual_pairs(self):
        records={f'T10_{n}':dict(status='PASS',metrics=dict(density_L1=n**-1.6,fresh_L1=n**-1.6)) for n in (100,200,400,800)}
        self.assertEqual(p.test_gate('T10',records)['status'],'PASS')
        records['T10_800']['metrics']['fresh_L1']=records['T10_400']['metrics']['fresh_L1']/2
        self.assertEqual(p.test_gate('T10',records)['status'],'FAIL')
        records.pop('T10_800');self.assertEqual(p.test_gate('T10',records)['status'],'PARTIAL')

    def test_available_r4_failure_not_hidden_by_other_missing_case(self):
        records={}
        for n,sensitivity in ((400,.000161),(800,.000203),(1600,.000098)):
            for c in (.4,.6):
                name=f'T03_{c}'+('' if n==800 else f'_N{n}')
                records[name]=dict(status='PASS',result=dict(status='completed'),configuration=dict(N=n,CFL=c),
                    checks=dict(worst_ledger=True,stage_conservation=True,stage_CFL=True),
                    metrics=dict(amplitude=9.+(10*sensitivity if c==.6 else 0.),analytical_amplitude_error=1/n))
        gate=p.test_gate('T11',records)
        self.assertEqual(gate['status'],'FAIL')
        self.assertFalse(gate['checks']['sensitivity_0.4_0.6'])
        self.assertNotIn('sensitivity_0.2_0.4',gate['checks'])
        self.assertEqual(gate['completed_subcases'],6)
        failures=[dict(test='T11',case='T03_0.2_N1600',solver_status='failed_infrastructure')]
        gate['checks']['T03_0.2_N1600']=False
        self.assertFalse(p.only_infrastructure_failure(gate,failures,'T11'))
        gate['checks']['sensitivity_0.4_0.6']=True
        self.assertTrue(p.only_infrastructure_failure(gate,failures,'T11'))

    def test_runtime_override_does_not_change_physical_arguments(self):
        with patch('dev_orchestrator.p2b_campaign.solve',side_effect=RuntimeError('captured')) as solve:
            with self.assertRaisesRegex(RuntimeError,'captured'):run_case('T04',wall_limit=300.)
            args,kwargs=solve.call_args;case=p.v.definition('T04')
            self.assertEqual(kwargs['wall_limit'],300.)
            self.assertEqual(args[2],case['end']);self.assertEqual(args[0].n,800)
            self.assertEqual(kwargs['cfl'],.4);self.assertEqual(kwargs['method'],'MUSCL_SSPRK2')


if __name__=='__main__':unittest.main()
