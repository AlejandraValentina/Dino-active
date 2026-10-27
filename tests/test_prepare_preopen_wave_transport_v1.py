from pathlib import Path
from types import SimpleNamespace
import pytest
from scripts.diagnostics import prepare_preopen_wave_transport_v1 as module

ROOT=Path(__file__).resolve().parents[1]/'results/predictive-reliability-v1'


def test_three_grids_and_p1_prepared_without_integration(monkeypatch):
    monkeypatch.setattr(module.IntegratedEngine2T,'step',lambda *a,**k:pytest.fail('preparation cannot integrate'))
    templates,r=module.prepare(ROOT)
    assert r['solver_steps']==0 and r['closed_exhaust_proof']['geometric_margin_mm']>0
    assert [r['initialization'][n]['cells'] for n in ('p0-88','p0-176','p0-352')]==[88,176,352]
    assert all(d['fresh_constructor_native_roundtrip_exact'] for d in r['initialization'].values())
    for value in templates.values():assert value['checkpoint']['crank_angle_unwrapped_deg']==13680. and value['checkpoint']['angle_deg']==0.


def test_rejects_opening_exhaust_for_proposed_isolation():
    config=module.load(ROOT/'periodic88-window2-v1/run/configuration.json');e=module.IntegratedEngine2T.from_configuration_dict(config)
    binding=e.port_binding.to_dict()
    for p in binding['port_set']['ports']:
        if p['role']=='exhaust':p['top_mm']=0.
    e.port_binding=SimpleNamespace(to_dict=lambda:binding)
    with pytest.raises(ValueError,match='opens'):module.closed_interval(e)
