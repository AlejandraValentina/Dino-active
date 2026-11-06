"""Prospective remediation checks, not altered historical scientific criteria."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from motorsim.dino4t import api, config


def real_endpoint():
    path = sorted(Path('results/dino4t-ab-engineering-v1/runs/runs').glob('*/artifacts/summary.json'))[0]
    return json.loads(path.read_text(encoding='utf-8')), json.loads(
        path.with_name('config_resolved.json').read_text(encoding='utf-8'))


def test_unknown_combustion_legacy_model_label_is_not_silent_metadata():
    cfg = config.load(config.EXAMPLE_PATH)
    cfg['combustion']['model'] = 'THIS_MODEL_DOES_NOT_EXIST'
    assert not api.validate(cfg)['valid']
    assert api.run(cfg, max_cycles=1)['error']['code'] == 'CONFIG_INVALID'


def test_extreme_finite_operating_point_returns_semantic_issue_not_overflow():
    summary, cfg = real_endpoint()
    cfg['operating_point']['rpm'] = 1e300
    summary['operating_point'] = deepcopy(cfg['operating_point'])
    summary['config_sha256'] = config.canonical_hash(cfg)
    assert api.check_summary(summary, config=cfg)


@pytest.mark.parametrize('section,key,value', [
    ('intake_valve', 'count', 1.9), ('intake_valve', 'count', True),
    ('friction', 'a_pa', float('nan')), ('numerics', 'max_cycles', True),
])
def test_invalid_native_inputs_cannot_be_runnable(section, key, value):
    cfg = config.load(config.EXAMPLE_PATH)
    cfg[section][key] = value
    checked = api.validate(cfg)
    assert not checked['valid'] and checked['config_sha256'] is None
    assert api.run(cfg, max_cycles=1)['error']['code'] == 'CONFIG_INVALID'


def test_malformed_section_returns_config_error_instead_of_attribute_error():
    cfg = config.load(config.EXAMPLE_PATH); cfg['geometry'] = None
    checked = api.validate(cfg)
    assert not checked['valid'] and checked['issues'][0]['code'] == 'CONFIG_INVALID'


def test_nested_unread_controls_are_rejected():
    cfg = config.load(config.EXAMPLE_PATH)
    cfg['intake_valve']['lift']['typo_ignored'] = 42
    cfg['numerics']['bore_mm'] = 123
    checked = api.validate(cfg)
    assert not checked['valid']
    assert set(checked['unknown_keys']) == {'intake_valve.lift.typo_ignored', 'numerics.bore_mm'}


def test_periodicity_property_cannot_disagree_with_minimum_cycle_decision(monkeypatch):
    from motorsim.dino4t import cycle_analysis as ca
    monkeypatch.setattr(ca, 'cycle_indicators', lambda *args: {})
    monkeypatch.setattr(ca, 'periodicity_metrics', lambda *args: {
        key: 0.0 for key in ('imep_rel', 'trapped_mass_rel', 'pressure_trace_rel', 'mass_imbalance_rel')})
    monitor = ca.PeriodicityMonitor({}, {'consecutive': 1}, min_cycles=3)
    assert monitor([SimpleNamespace()]) is False
    assert monitor([SimpleNamespace(), SimpleNamespace()]) is False
    assert monitor.status == 'NOT_CONVERGED'


def test_periodic_summary_requires_actual_cycle_comparisons():
    summary, _ = real_endpoint()
    summary['cycles_run'] = 0; summary['periodicity']['history'] = []
    assert api.check_summary(summary)


def test_real_historical_summary_and_exact_config_remain_compatible():
    summary, cfg = real_endpoint()
    assert api.check_summary(summary, config=cfg) == []
    changed = deepcopy(summary); changed['operating_point']['rpm'] = 7000
    assert api.check_summary(changed, config=cfg)


def test_unbound_replacement_trace_cannot_be_plotted_as_verified(tmp_path):
    from PySide6.QtWidgets import QApplication
    from motorsim.desktop.context import DesktopContext
    from motorsim.desktop.four_stroke_desktop import FourStrokeResults, _curve_binding
    from motorsim.desktop.four_stroke_project import create_project
    app = QApplication.instance() or QApplication([])
    summary, cfg = real_endpoint()
    run = tmp_path/'legacy'; artifacts = run/'artifacts'; artifacts.mkdir(parents=True)
    sp=artifacts/'summary.json'; cp=artifacts/'config_resolved.json'; tp=artifacts/'trace.csv'
    sp.write_text(json.dumps(summary),encoding='utf-8'); cp.write_text(json.dumps(cfg),encoding='utf-8')
    tp.write_text('theta,p\n0,4200000\n',encoding='utf-8')
    digest=hashlib.sha256(sp.read_bytes()).hexdigest()
    meta={'schema':'DINO4T_DESKTOP_RUN_V1','run_id':'legacy','api':'DINO4T_API_V1',
          'result_sha256':digest,'config_identity_sha256':summary['config_sha256'],
          'summary_path':str(sp),'config_path':str(cp),'trace_path':str(tp),'curve_binding_sha256':_curve_binding(cfg)}
    (run/'run.json').write_text(json.dumps(meta),encoding='utf-8')
    ref={'run_id':'legacy','path':str(sp),'result_sha256':digest,'config_sha256':summary['config_sha256'],
         'status':summary['status'],'periodicity_status':summary['periodicity']['status'],'variant_id':''}
    widget=FourStrokeResults(DesktopContext(create_project('legacy',cfg,run_references=[ref])))
    assert not widget.loaded and not widget.pressure_plot.series
    widget.close();app.processEvents()


@pytest.mark.parametrize('value',[0,-1,True,1.5,float('nan'),float('inf')])
def test_invalid_detector_counts_fail_before_any_calculation(value):
    cfg=config.load(config.EXAMPLE_PATH);cfg['numerics']['periodicity']['consecutive']=value
    assert not api.validate(cfg)['valid']
    assert api.run(cfg,max_cycles=1)['summary'] is None


@pytest.mark.parametrize('mutation',[
    lambda s:s.update(operating_point=None),
    lambda s:s.update(code_commit=''),
    lambda s:s['periodicity']['history'][-1].update(passed=False),
    lambda s:s['final_cycle'].update(brake_power_kW=999),
    lambda s:s['final_cycle'].update(brake_torque_Nm=999),
    lambda s:s['models'].update(valve_boundary='QUASI_STEADY_RESTRICTION_V1'),
    lambda s:s['conservation']['max_relative_closure'].update(mass=1.0),
    lambda s:s.update(validation_evidence={'anything':'not a verified authority'},claims={
        'calibration':'NOT_PERFORMED','experimental_validation':'PERFORMED','predictive_capability':'CLAIMED'}),
])
def test_semantic_contradictions_cannot_become_eligible_even_with_valid_byte_hashes(mutation):
    summary,cfg=real_endpoint();mutation(summary)
    before=deepcopy(summary);assert api.check_summary(summary,config=cfg)
    assert summary==before  # classification never rewrites evidence


def test_zero_cycle_incomplete_has_no_performance_but_is_not_a_corrupt_result():
    summary,cfg=real_endpoint()
    summary.update(status='incomplete',termination='wall_limit',cycles_run=0,final_cycle=None,cycle_history=[])
    summary['periodicity'].update(status='NOT_CONVERGED',history=[])
    assert api.check_summary(summary,config=cfg)==[]


def test_signed_friction_coefficient_is_allowed_but_negative_calculated_loss_is_not():
    import math
    summary,cfg=real_endpoint()
    # Contract-only counterfactual postprocessing, not new engine evidence.
    for coefficient,expected_valid in [(-1000.,True),(-1e10,False)]:
        cfg['friction']['a_pa']=coefficient
        assert api.validate(cfg)['valid']
        summary['config_sha256']=config.canonical_hash(cfg)
        final=summary['final_cycle'];fr=cfg['friction'];rpm=cfg['operating_point']['rpm']
        speed=2*cfg['geometry']['stroke_mm']*1e-3*rpm/60
        final['fmep_bar']=(fr['a_pa']+fr['b']*final['p_max_bar']*1e5+fr['c_pa_s_m']*speed+fr['d_pa_s2_m2']*speed**2)/1e5
        final['bmep_bar']=final['imep_net_bar']-final['fmep_bar']
        displacement=math.pi/4*(cfg['geometry']['bore_mm']*1e-3)**2*cfg['geometry']['stroke_mm']*1e-3
        final['brake_power_kW']=final['bmep_bar']*1e5*displacement*rpm/120/1000
        final['brake_torque_Nm']=final['brake_power_kW']*1000/(2*math.pi*rpm/60)
        problems=api.check_summary(summary,config=cfg)
        assert (not problems)==expected_valid
        if not expected_valid:assert any('negative evaluated friction' in x for x in problems)


def test_overflowing_finite_geometry_is_a_structured_configuration_error():
    cfg=config.load(config.EXAMPLE_PATH);cfg['geometry']['bore_mm']=1e300
    assert not api.validate(cfg)['valid']


def test_existing_artifacts_are_never_overwritten_or_recomputed(tmp_path,monkeypatch):
    from motorsim.dino4t import runner
    original=tmp_path/'summary.json';original.write_bytes(b'original evidence')
    monkeypatch.setattr(runner,'run_operating_point',lambda *a,**k:pytest.fail('must reject before calculation'))
    result=api.run(config.load(config.EXAMPLE_PATH),out_dir=tmp_path,max_cycles=1)
    assert result['error']['code']=='OPTION_INVALID'
    assert original.read_bytes()==b'original evidence'


def test_finished_signal_uses_persisted_reference_and_never_undefined_metadata(tmp_path):
    from PySide6.QtWidgets import QApplication
    from motorsim.desktop.context import DesktopContext
    from motorsim.desktop.four_stroke_project import create_project
    from motorsim.desktop.four_stroke_desktop import FourStrokeSimulation
    from motorsim.dino4t.artifacts import publish_primary
    summary,cfg=real_endpoint();app=QApplication.instance() or QApplication([])
    run=tmp_path/'finished';source=sorted(Path('results/dino4t-ab-engineering-v1/runs/runs').glob('*/artifacts/summary.json'))[0]
    raw={k:(source if k=='summary' else source.with_name(name)).read_bytes() for k,name in [
        ('summary','summary.json'),('config','config_resolved.json'),('trace','trace_last_cycle.csv')]}
    artifacts=publish_primary(run/'artifacts',summary,cfg,raw_primary=raw,origin={'kind':'SYNTHETIC_CONTRACT_FIXTURE'})
    widget=FourStrokeSimulation(DesktopContext(create_project('finish-contract',cfg)))
    widget.task=SimpleNamespace(config=cfg);widget.run_dir=run;widget.run_project_id='finish-contract';widget.run_variant_id=''
    events=[];widget.runFinished.connect(events.append)
    widget._finished({'api':api.API_VERSION,'summary':summary,'artifacts':artifacts,'error':None})
    assert events and events[0]['schema']=='DINO4T_RUN_REFERENCE_V2'
    widget.close();app.processEvents()
