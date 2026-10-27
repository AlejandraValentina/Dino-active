from pathlib import Path
import pytest
from scripts.diagnostics import periodicity_extension_v4 as module

ROOT=Path(__file__).resolve().parents[1]/'results/predictive-reliability-v1'
SOURCE=ROOT/'exhaust-composition-plateau-v1/relaxation-check'
CONFIG=ROOT/'spatial-boundary-v2-engine'


def test_native_and_detector_restore_without_reintegrating(monkeypatch):
    monkeypatch.setattr(module.IntegratedEngine2T,'step',lambda *a,**k:pytest.fail('no integration in restore'))
    e,cp,d,base=module.load_source(SOURCE,CONFIG)
    assert len(d.history)==25 and e.crank_angle_unwrapped_deg==9000.
    assert module.conserved(e.conservation_report())
    assert base[-1]['cycle']==25


def test_modified_source_is_rejected(monkeypatch):
    real=module.sha
    monkeypatch.setattr(module,'sha',lambda p:'corrupt' if p.name=='checkpoint-025.json' else real(p))
    with pytest.raises(ValueError,match='source hash mismatch'):module.load_source(SOURCE,CONFIG)


def test_dependency_mismatch_is_rejected(monkeypatch):
    monkeypatch.setattr(module,'_solver_dependency_hashes',lambda:{'invalid':'hash'})
    with pytest.raises(ValueError,match='solver source mismatch'):module.load_source(SOURCE,CONFIG)


def test_cycle29_restores_existing_streak_without_reintegrating(monkeypatch):
    monkeypatch.setattr(module.IntegratedEngine2T,'step',lambda *a,**k:pytest.fail('no integration in restore'))
    e,cp,d,base=module.load_native_source(ROOT/'periodicity-extension-v4/run',CONFIG,29,'run')
    assert e.crank_angle_unwrapped_deg==10440.
    assert d.lag1_streak==2 and d.detected_period is None


def test_finite_execution_bounds_are_enforced(tmp_path):
    with pytest.raises(ValueError,match='invalid finite execution bounds'):
        module.run(SOURCE,CONFIG,tmp_path/'out',first_cycle=26,last_cycle=100)
