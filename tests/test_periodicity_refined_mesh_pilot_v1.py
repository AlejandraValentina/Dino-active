from pathlib import Path
import pytest
from scripts.diagnostics import periodicity_refined_mesh_pilot_v1 as module

ROOT=Path(__file__).resolve().parents[1]/'results/predictive-reliability-v1'


def test_audited_source_preparation_has_new_identity_and_empty_detector(monkeypatch):
    monkeypatch.setattr(module.IntegratedEngine2T,'step',lambda *a,**k:pytest.fail('no integration during initialization'))
    e,c,d,p=module.prepare(ROOT)
    assert sum(len(path['mesh']['volumes']) for path in c['ducts'])==88
    assert e.crank_angle_unwrapped_deg==10800. and d.history==[]
    assert d.detected_period is None and p['origin_absolute_cycle']==30
    assert p['initialization']['inventory_max_relative_error']<2e-14


def test_unverified_source_is_rejected(monkeypatch):
    original=module.load
    def changed(p):
        value=original(p)
        if p.name=='receipt.json' and p.parent.name=='reconstruction':value['periodicity_audited']=False
        return value
    monkeypatch.setattr(module,'load',changed)
    with pytest.raises(ValueError,match='audited periodic source'):module.prepare(ROOT)


def test_first_cycle_has_no_invented_comparison():
    assert module.statistics(dict(status='NOT_EVALUATED',metrics={})) is None
