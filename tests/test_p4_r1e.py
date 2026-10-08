import json
from math import nextafter,inf
import unittest
from dev_orchestrator.p4_r1e import same_json_value


class PrefixAuditTests(unittest.TestCase):
    def test_solver_tuples_and_stored_lists(self):
        actual={'cylinder':(100000.,300.,.001,.2),'sensors':[(100000.,0.,0.,.2)]}
        self.assertTrue(same_json_value(actual,json.loads(json.dumps(actual))))

    def test_one_ulp_change_is_not_hidden(self):
        self.assertFalse(same_json_value({'p':(100000.,)},{'p':[nextafter(100000.,inf)]}))

    def test_missing_stage_is_not_hidden(self):
        self.assertFalse(same_json_value([{'stage':(1.,)}],[]))
