"""Contrato documental P1: sin integraciones 0D/1D ni validación experimental."""
from copy import deepcopy
import math
import unittest
from unittest.mock import patch
from dev_orchestrator import p1_contract as p


class ContractTests(unittest.TestCase):
    def setUp(self):
        self.m=p.read_json(p.ROOT/p.MANIFEST)

    def test_complete_and_accepted_dependency(self):
        self.assertTrue(p.validate_contract(self.m))

    def test_missing_case_rejected(self):
        self.m['verification_cases'].pop(7)
        with self.assertRaisesRegex(ValueError,'T01'): p.validate_contract(self.m)

    def test_unresolved_science_stops(self):
        self.m['unresolved_blocking_decisions']=['EOS']
        with self.assertRaisesRegex(ValueError,'SCIENTIFIC_CHANGE_REQUIRED'): p.validate_contract(self.m)

    def test_area_sign_rejected(self):
        self.m['equations']['source'][1]='-p*d_x A'
        with self.assertRaisesRegex(ValueError,'Fuente'): p.validate_contract(self.m)

    def test_eos_consistency(self):
        self.m['eos']['cp_J_kgK']=1000
        with self.assertRaisesRegex(ValueError,'EOS'): p.validate_contract(self.m)

    def test_broken_document_hash_rejected(self):
        self.m['documents'][next(iter(self.m['documents']))]='0'*64
        with self.assertRaisesRegex(ValueError,'Hash'): p.validate_contract(self.m)

    def test_no_false_numerical_verification(self):
        self.m['verification_cases'][0]['status']='PASS'
        with self.assertRaisesRegex(ValueError,'ejecución atribuida'): p.validate_contract(self.m)

    def test_no_automatic_p2_enablement(self):
        original=p.read_json
        def read(path):
            data=original(path)
            if str(path).endswith('P2.json'): data['enabled']=True
            return data
        with patch.object(p,'read_json',side_effect=read):
            with self.assertRaisesRegex(ValueError,'posterior'): p.validate_contract(self.m)

    def test_acceptance_cannot_change_scientific_evidence(self):
        original=p.read_json
        def read(path):
            data=original(path)
            if str(path).endswith('p0_accepted_dependency.json'): data['git_commit']='invented'
            return data
        with patch.object(p,'read_json',side_effect=read):
            with self.assertRaisesRegex(ValueError,'altera evidencia'): p.validate_contract(self.m)

    def test_rest_area_balance_algebra(self):
        # Analytical identities only, not a mesh or numerical solver implementation.
        pressure=100000
        for left,right in ((.01,.01),(.01,.03),(.03,.01)):
            momentum_faces=pressure*left-pressure*right
            source=pressure*(right-left)
            self.assertAlmostEqual(momentum_faces+source,0,places=10)

    def test_reflection_windows_and_no_exact_vacuum(self):
        incident=.7-.3; reflected=(1-.3)+(1-.7)
        self.assertTrue(.30<incident<.50)
        self.assertTrue(.90<reflected<1.10)
        g=1.4;a=math.sqrt(g*.4)
        self.assertLess(2-(-2),2*(a+a)/(g-1))


if __name__=='__main__': unittest.main()
