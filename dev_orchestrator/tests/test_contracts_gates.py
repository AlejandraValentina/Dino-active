from copy import deepcopy
import unittest

from dev_orchestrator.contracts import BASE, ContractError, read_json, validate_named, validate, relative_path
from dev_orchestrator.gates.evaluate import evaluate
from dev_orchestrator.runners.run_review import run_review


class ContractGateTests(unittest.TestCase):
    def setUp(self):
        self.phase=read_json(BASE/'phases/dummy.json')
        self.checks=[dict(id=name,passed=True,kind='test') for name in self.phase['required_checks']]
        self.review=run_review(phase=self.phase,diff={},evidence={'scope_violations':[]},required_checks=self.checks)

    def test_phase_schema_valid_and_strict(self):
        validate_named(self.phase,'phase')
        for mutate in (lambda p:p.pop('objective'),lambda p:p.update(max_repair_attempts=True),
                       lambda p:p.update(max_repair_attempts=-1),lambda p:p.update(max_repair_attempts=11),
                       lambda p:p.update(human_gate='false'),lambda p:p.update(unexpected=1)):
            with self.subTest(mutate=mutate):
                p=deepcopy(self.phase); mutate(p)
                with self.assertRaises(ContractError): validate_named(p,'phase')
        with self.assertRaises(ContractError): validate({}, {'oneOf':[]})

    def test_path_contract(self):
        for bad in ('../motorsim','/tmp','C:/secret','a/../b','a\\b','*','.'):
            with self.subTest(path=bad),self.assertRaises(ContractError): relative_path(bad)

    def test_gate_four_terminal_states(self):
        self.assertEqual(evaluate(self.phase,self.checks,self.review)[0],'PASS')
        self.checks[0]['passed']=False
        self.assertEqual(evaluate(self.phase,self.checks,self.review)[0],'BLOCKED')
        self.assertEqual(evaluate(self.phase,self.checks,self.review,scientific_change_required=True)[0],'SCIENTIFIC_CHANGE_REQUIRED')
        self.assertEqual(evaluate(self.phase,self.checks,self.review,errors=['missing_tool'])[0],'FAILED_INFRASTRUCTURE')

    def test_all_pass_conditions_and_stub_not_independent(self):
        for kwargs in ({'scope_violations':['motorsim/x.py']},{'evidence_complete':False},{'exhausted':True}):
            self.assertEqual(evaluate(self.phase,self.checks,self.review,**kwargs)[0],'BLOCKED')
        self.assertEqual(evaluate(self.phase,self.checks,self.review,scope_violations=['x'],scientific_change_required=True)[0],'BLOCKED')
        self.review['blocking_findings']=['defect']
        self.assertEqual(evaluate(self.phase,self.checks,self.review)[0],'BLOCKED')
        self.review['blocking_findings']=[]; self.phase['phase']='P1'
        self.assertEqual(evaluate(self.phase,self.checks,self.review)[0],'BLOCKED')

    def test_stub_contract_read_only(self):
        before=deepcopy(self.phase)
        validate_named(self.review,'review')
        self.assertEqual(self.review['kind'],'dummy_stub'); self.assertIn('NO',self.review['notes'])
        self.assertEqual(self.phase,before)
        self.phase['phase']='P2'
        r=run_review(phase=self.phase,diff={},evidence={'scope_violations':[]},required_checks=[])
        self.assertEqual(r['status'],'BLOCKED')
