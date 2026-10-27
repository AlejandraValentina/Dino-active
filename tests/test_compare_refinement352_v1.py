from pathlib import Path
import pytest
from scripts.diagnostics import compare_refinement352_v1 as module


@pytest.mark.parametrize('stopped',[False,True])
def test_reference_replay_analysis_does_not_execute_solver(monkeypatch,tmp_path,stopped):
    previous=Path(__file__).resolve().parents[1]/'results/predictive-reliability-v1/remap-uncertainty-v1'
    original_load=module.load;original_sha=module.sha
    def map_path(path):
        if path.is_relative_to(tmp_path/'p0-352'):
            return previous/'p0-176-timehalf'/path.relative_to(tmp_path/'p0-352')
        return path
    def load(path):
        value=original_load(map_path(path))
        if stopped and path==tmp_path/'p0-352/receipt.json':value['status']='STOPPED'
        return value
    monkeypatch.setattr(module,'load',load);monkeypatch.setattr(module,'sha',lambda p:original_sha(map_path(p)))
    monkeypatch.setattr(module.IntegratedEngine2T,'step',lambda *a,**k:pytest.fail('analysis must not integrate'))
    result=module.analyze(tmp_path,previous)
    if stopped:
        assert result['status']=='STOPPED'
        assert 'work_J' not in result['cases']['352']
        assert 'retained_material' not in result
    else:
        assert result['status']=='COMPLETE'
        assert result['cases']['352']['native_restore_exact']
        assert result['comparisons']['176-half__352'][-1]['common44']['exhaust']['burned_absolute_fraction']['L1']==0
