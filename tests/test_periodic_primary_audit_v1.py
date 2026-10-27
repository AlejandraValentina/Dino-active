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
