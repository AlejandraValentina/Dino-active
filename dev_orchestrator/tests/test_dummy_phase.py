import json
from pathlib import Path
import sys
import threading
import unittest
from unittest.mock import patch

from dev_orchestrator.contracts import ContractError, read_json, validate_named
from dev_orchestrator.runners.run_phase import run_phase, dependency_errors
from dev_orchestrator.tests.helpers import repository,alter,save


class DummyTests(unittest.TestCase):
    def setUp(self): self.root=repository(self)

    def run_case(self,**kwargs): return run_phase(self.root,'dummy',**kwargs)

    def test_dummy_pass_artifact_evidence_summary_and_dirty(self):
        (self.root/'user.txt').write_text('user work',encoding='utf-8')
        (self.root/'personal.txt').write_text('untracked',encoding='utf-8')
        result=self.run_case(continue_requested=True); data=result['evidence']
        self.assertEqual(result['gate'],'PASS'); self.assertTrue(data['git_dirty'])
        self.assertEqual(data['files_changed'],[]); self.assertEqual(data['scope_violations'],[])
        self.assertIn('personal.txt',data['preexisting_untracked'])
        self.assertEqual((self.root/'user.txt').read_text(),'user work')
        folder=Path(result['run_dir']); self.assertTrue((folder/'summary.md').is_file())
        validate_named(read_json(folder/'evidence.json'),'evidence')
        self.assertEqual(data['metrics']['tests_run'],1)
        self.assertEqual(len(data['artifacts']),2); self.assertEqual(len(data['attempts']),1)
        self.assertEqual(len(list((self.root/'dev_orchestrator/runs').iterdir())),1)
        bad=dict(data,gate='WAITING_HUMAN_APPROVAL')
        with self.assertRaises(ContractError): validate_named(bad,'evidence')

    def test_dry_run_has_no_process_or_files(self):
        with patch('dev_orchestrator.runners.run_phase.run_command') as command:
            result=self.run_case(dry_run=True); command.assert_not_called()
        self.assertEqual(result['expected_gate'],'PASS')
        self.assertFalse((self.root/'dev_orchestrator/runs').exists())

    def test_disabled_future_phase_and_missing_dependency(self):
        self.assertEqual(run_phase(self.root,'P2',continue_requested=True)['gate'],'BLOCKED')
        alter(self.root,depends_on=['P0'])
        result=self.run_case()
        self.assertIn('missing_dependency:P0',result['evidence']['gate_reasons'])
        self.assertEqual(result['evidence']['commands'],[])

    def test_schema_and_missing_file_infrastructure(self):
        path=self.root/'dev_orchestrator/phases/dummy.json'
        phase=read_json(path); phase['invented_state']='DONE'; save(path,phase)
        result=self.run_case(); self.assertEqual(result['gate'],'FAILED_INFRASTRUCTURE')
        self.assertTrue((Path(result['run_dir'])/'evidence.json').exists())
        path.unlink()
        self.assertEqual(self.run_case()['gate'],'FAILED_INFRASTRUCTURE')

    def test_required_test_failure_and_repair_limit(self):
        alter(self.root,commands=[dict(id='dummy_test',argv=['{python}','-c','raise SystemExit(1)'],kind='test')],max_repair_attempts=2)
        result=self.run_case(retry_failed_checks=True); data=result['evidence']
        self.assertEqual(result['gate'],'BLOCKED'); self.assertEqual(len(data['attempts']),3)
        self.assertEqual(len(data['commands']),3); self.assertIn('max_repair_attempts_exhausted',data['gate_reasons'])

    def test_scientific_change_stops_no_retry(self):
        program="import json, pathlib; pathlib.Path(r'{run_dir}/artifacts/change.json').write_text(json.dumps(dict(checks=[],metrics={},scientific_change_required=True)))"
        alter(self.root,commands=[dict(id='dummy_test',argv=['{python}','-c',program],kind='test',result_file='artifacts/change.json')])
        result=self.run_case(retry_failed_checks=True)
        self.assertEqual(result['gate'],'SCIENTIFIC_CHANGE_REQUIRED')
        self.assertEqual(len(result['evidence']['attempts']),1)

    def test_scope_violation_stops_and_preserves_file(self):
        program="from pathlib import Path; Path('motorsim/sentinel.txt').write_text('unexpected')"
        alter(self.root,commands=[dict(id='dummy_test',argv=['{python}','-c',program],kind='test')])
        data=self.run_case(retry_failed_checks=True)['evidence']
        self.assertEqual(data['gate'],'BLOCKED')
        self.assertIn('motorsim/sentinel.txt',data['scope_violations'])
        self.assertEqual((self.root/'motorsim/sentinel.txt').read_text(),'unexpected')
        self.assertEqual(len(data['commands']),1)

    def test_modifying_already_dirty_allowed_file_is_reported(self):
        (self.root/'user.txt').write_text('prior user work',encoding='utf-8')
        alter(self.root,allowed_paths=['user.txt'],commands=[dict(id='dummy_test',argv=['{python}','-c',"from pathlib import Path; Path('user.txt').write_text('changed')"],kind='test')])
        data=self.run_case()['evidence']
        self.assertEqual(data['preexisting_touched'],['user.txt'])
        self.assertIn('preexisting:user.txt',data['scope_violations'])

    def test_cancel_partial_evidence(self):
        event=threading.Event(); event.set()
        data=self.run_case(cancel=event)['evidence']
        self.assertEqual(data['gate'],'FAILED_INFRASTRUCTURE'); self.assertIn('cancelled_by_user',data['errors'])
        with patch('dev_orchestrator.runners.run_phase.run_command',side_effect=KeyboardInterrupt):
            data=self.run_case()['evidence']
        self.assertIn('cancelled_by_user',data['errors']); self.assertEqual(len(data['attempts']),1)

    def test_human_gate_is_separate_and_cannot_satisfy_dependency(self):
        alter(self.root,human_gate=True)
        result=self.run_case(); data=result['evidence']
        self.assertEqual(data['gate'],'PASS'); self.assertEqual(data['execution_status'],'WAITING_HUMAN_APPROVAL')
        self.assertEqual(dependency_errors({'depends_on':['dummy']},{'dummy':Path(result['run_dir'])/'evidence.json'}),['dependency_not_approved:dummy'])

    def test_timeout_and_missing_evidence(self):
        alter(self.root,commands=[dict(id='dummy_test',argv=['{python}','-c','import time; time.sleep(10)'],kind='test',timeout=.1)])
        result=self.run_case(); self.assertEqual(result['gate'],'BLOCKED')
        self.assertEqual(result['evidence']['commands'][0]['status'],'timeout')
        alter(self.root,commands=[dict(id='dummy_test',argv=['{python}','-c','pass'],kind='test',result_file='artifacts/absent.json')])
        result=self.run_case(); self.assertEqual(result['gate'],'FAILED_INFRASTRUCTURE')
        self.assertEqual(len(result['evidence']['attempts']),1)

    def test_phase_total_timeout(self):
        alter(self.root,timeout=.05)
        self.assertEqual(self.run_case()['gate'],'FAILED_INFRASTRUCTURE')

    def test_runs_cannot_resolve_into_product(self):
        with patch('dev_orchestrator.runners.run_phase.inside',return_value=self.root/'motorsim'):
            result=self.run_case()
        self.assertEqual(result['gate'],'FAILED_INFRASTRUCTURE')
        self.assertIsNone(result['run_dir'])
        self.assertEqual([p.name for p in (self.root/'motorsim').iterdir()],['sentinel.txt'])

    def test_cancellation_still_reports_scope_as_blocked(self):
        def interrupted(*args,**kwargs):
            (self.root/'motorsim/sentinel.txt').write_text('unexpected',encoding='utf-8')
            raise KeyboardInterrupt
        with patch('dev_orchestrator.runners.run_phase.run_command',side_effect=interrupted):
            data=self.run_case()['evidence']
        self.assertEqual(data['gate'],'BLOCKED')
        self.assertIn('cancelled_by_user',data['errors'])
        self.assertIn('scope_violation',data['gate_reasons'])
        self.assertIn('motorsim/sentinel.txt',data['scope_violations'])
        self.assertEqual(data['attempts'][-1]['state'],'BLOCKED')

    def test_real_infrastructure_error_and_failed_numerical_check(self):
        alter(self.root,commands=[dict(id='dummy_test',argv=['missing-motorsim-tool-57391'],kind='test')])
        self.assertEqual(self.run_case()['gate'],'FAILED_INFRASTRUCTURE')
        code="import json,pathlib; pathlib.Path(r'{run_dir}/artifacts/result.json').write_text(json.dumps(dict(checks=[dict(id='numerical',passed=False,kind='numerical')],metrics={},scientific_change_required=False)))"
        alter(self.root,commands=[dict(id='dummy_test',argv=['{python}','-c',code],kind='test',result_file='artifacts/result.json')],
              required_checks=['dummy_test','numerical'],required_evidence=['artifacts/result.json'])
        self.assertEqual(self.run_case()['gate'],'BLOCKED')
