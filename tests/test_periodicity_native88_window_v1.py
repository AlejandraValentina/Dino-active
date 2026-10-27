from pathlib import Path
import pytest
from scripts.diagnostics import periodicity_native88_window_v1 as module

ROOT=Path(__file__).resolve().parents[1]/'results/predictive-reliability-v1'


def test_native39_and_detector_restore_without_reintegration(monkeypatch):
    monkeypatch.setattr(module.IntegratedEngine2T,'step',lambda *a,**k:pytest.fail('preparation must not integrate'))
    e,c,d,p=module.prepare_native39(ROOT)
    assert e.crank_angle_unwrapped_deg==14040. and len(d.history)==9
    assert p['first_detector_cycle_index']==10 and len(p['source_previous_cycles_paths'])==2
    assert e.configuration_identity['configuration_sha256']==d.history[-1]['configuration_hash']


def test_rejects_source_detector_with_missing_cycle(monkeypatch):
    original=module.load
    def altered(path):
        value=original(path)
        if path.name=='detector.json':value['history']=value['history'][:-1]
        return value
    monkeypatch.setattr(module,'load',altered)
    with pytest.raises(ValueError,match='transient9'):module.prepare_native39(ROOT)


def test_rejects_failed_flux_measurement(monkeypatch):
    original=module.load
    def altered(path):
        value=original(path)
        if path.name=='receipt.json' and path.parent.parent.name=='periodic88-front-flux-v1':value['status']='FAIL'
        return value
    monkeypatch.setattr(module,'load',altered)
    with pytest.raises(ValueError,match='replay not compatible'):module.prepare_native39(ROOT)
