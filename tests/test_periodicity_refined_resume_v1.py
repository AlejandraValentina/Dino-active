from pathlib import Path
import pytest
from scripts.diagnostics import periodicity_refined_resume_v1 as module
from scripts.diagnostics.periodicity_refined_mesh_pilot_v1 import run

ROOT=Path(__file__).resolve().parents[1]/'results/predictive-reliability-v1'


def test_native35_detector_and_partial_sources_bound_without_steps(monkeypatch):
    monkeypatch.setattr(module.IntegratedEngine2T,'step',lambda *a,**k:pytest.fail('no integration in source preparation'))
    e,c,d,p=module.prepare_resume(ROOT)
    assert e.crank_angle_unwrapped_deg==12600. and len(d.history)==5
    assert p['first_detector_cycle_index']==6 and d.detected_period is None
    partial=module.load(Path(p['source_partial_path']))
    assert partial['crank_angle_unwrapped_deg']==12814.


def test_wrong_detector_prefix_rejected(monkeypatch):
    original=module.load
    def altered(path):
        value=original(path)
        if path.name=='detector.json':value['history']=value['history'][:-1]
        return value
    monkeypatch.setattr(module,'load',altered)
    with pytest.raises(ValueError):module.prepare_resume(ROOT)


def test_unbounded_resume_not_allowed(tmp_path):
    with pytest.raises(ValueError,match='bounded window'):run(ROOT,tmp_path/'out',first_absolute=36,last_absolute=100)


def test_first_saved_partial_step_replays_exactly():
    from motorsim.integrated_2t import _json_evidence_equal
    e,c,d,p=module.prepare_resume(ROOT)
    row=next(r for r in module.load(Path(p['source_partial_recipe_path'])) if r['angle_start_deg']==12600.)
    for rejected in row['rejected_proposals']:
        with pytest.raises(ValueError) as error:e.step(rejected['step_deg']/(6*9000.),rejected['step_deg'],capture_trace=False)
        assert str(error.value)==rejected['error']
    actual=e.step(row['dt_s'],row['angle_end_deg']-row['angle_start_deg'],capture_trace=False)
    assert _json_evidence_equal(actual,{k:v for k,v in row.items() if k!='rejected_proposals'})
