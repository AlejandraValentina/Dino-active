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
