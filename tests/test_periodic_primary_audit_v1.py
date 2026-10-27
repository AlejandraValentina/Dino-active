from pathlib import Path
import pytest
from scripts.diagnostics import periodic_primary_audit_v1 as module

ROOT=Path(__file__).resolve().parents[1]/'results/predictive-reliability-v1'


@pytest.mark.parametrize('cycle',[27,28,29,30])
def test_existing_cycles_bound_without_solver_steps(cycle,monkeypatch):
    monkeypatch.setattr(module.IntegratedEngine2T,'step',lambda *a,**k:pytest.fail('read-only input validation'))
    config,start,end,recipe,binding=module.read_bound_cycle(ROOT,cycle)
    assert start['cycle']==cycle-1 and end['cycle']==cycle
    assert recipe[0]['angle_start_deg']==360*(cycle-1)
    assert recipe[-1]['angle_end_deg']==360*cycle
    assert binding['start_sha256']


def test_no_new_cycle_allowed():
    with pytest.raises(ValueError,match='only existing'):module.read_bound_cycle(ROOT,31)


def test_v2_detector_requires_v1_cycle_data_contract():
    from copy import deepcopy
    from motorsim.reference_harness.convergence import compare_cycles_v2,CONTRACT_V2
    history=module.load(ROOT/'periodicity-cycle30-control-v1/run/detector.json')['history']
    a=module.primary_observation_record(history[27]);b=module.primary_observation_record(history[28])
    assert compare_cycles_v2(a,b)['status']=='PASS'
    wrong=deepcopy(b);wrong['contract']=CONTRACT_V2
    assert compare_cycles_v2(a,wrong)['reason']=='contract identity mismatch'
    with pytest.raises(ValueError,match='data contract'):module.primary_observation_record(wrong)
