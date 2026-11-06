"""A/B application contracts. Synthetic bundles test presentation, never physics."""
import csv
import json
from copy import deepcopy
import pytest
from motorsim.dino4t.config import canonical_hash
from motorsim.desktop.four_stroke_comparison import ComparisonIneligible, build_comparison
from motorsim.desktop.four_stroke_desktop import _outcome_label
from c01_c03_fixtures import endpoint_factory

@pytest.fixture
def endpoints(tmp_path):
    return endpoint_factory(tmp_path)


def test_comparison_requires_periodicity_and_reports_only_declared_design_changes(endpoints):
    a,b=endpoints('A'),endpoints('B')
    result=build_comparison(a,b)
    assert result['schema']=='DINO4T_AB_COMPARISON_V2'
    assert result['classification']=='PERIODIC_MODEL_SENSITIVITY_ONLY'
    assert result['metrics'][0]['delta_b_minus_a']==-1.0
    assert result['metrics'][0]['relative_percent_to_abs_a']==-4.0
    assert result['design_changes']==[{'path':'intake_valve.lift.max_lift_mm','a':10.0,'b':8.0}]
    assert result['qualification']['experimental_validation']=='NOT_PERFORMED'
    assert result['qualification']['predictive_capability']=='NOT_CLAIMED'
    moved=deepcopy(a);moved['meta']['summary_path']='another-machine/summary.json'
    assert build_comparison(moved,b)['comparison_id']==result['comparison_id']


@pytest.mark.parametrize('mutation',[
    lambda s,c:s['periodicity'].update(status='NOT_CONVERGED'),
    lambda s,c:s.update(code_dirty=True),
    lambda s,c:s.update(code_commit='d'*40),
    lambda s,c:s['models'].update(valve_boundary='QUASI_STEADY_RESTRICTION_V1'),
    lambda s,c:c['numerics'].update(dx_mm=12.0),
    lambda s,c:s['operating_point'].update(rpm=6000.0001),
])
def test_comparison_rejects_incompatible_or_incomplete_endpoint(endpoints,mutation):
    a=endpoints('A');b=endpoints('B',mutate=mutation)
    with pytest.raises(ComparisonIneligible):build_comparison(a,b)


def test_comparison_rejects_same_design_and_nonfinite_metric(endpoints):
    a=endpoints('A');same=endpoints('A')
    with pytest.raises(ComparisonIneligible,match='no tienen diferencias'):build_comparison(a,same)
    b=endpoints('B');b['summary']['final_cycle']['brake_power_kW']=float('nan')
    with pytest.raises((ComparisonIneligible,ValueError)):build_comparison(a,b)


def test_relative_difference_is_undefined_for_zero_baseline(endpoints):
    result=build_comparison(endpoints('A',power=0.0),endpoints('B',power=1.0))
    assert result['metrics'][0]['delta_b_minus_a']==1.0
    assert result['metrics'][0]['relative_percent_to_abs_a'] is None


def test_history_does_not_label_cancelled_run_as_completed_transient():
    assert _outcome_label({'status':'incomplete','periodicity':{'status':'NOT_CONVERGED'}})=='Incompleto'
    assert _outcome_label({'status':'completed','periodicity':{'status':'NOT_CONVERGED'}})=='Transitorio · no periódico'
    assert _outcome_label({'status':'completed','periodicity':{'status':'PERIODIC_CONVERGED'}})=='Periódico'


def _widget(endpoints):
    from PySide6.QtWidgets import QApplication
    from motorsim.desktop.context import DesktopContext
    from motorsim.desktop.four_stroke_desktop import FourStrokeResults
    from motorsim.desktop.four_stroke_project import create_project
    app=QApplication.instance() or QApplication([])
    a,b=endpoints('A'),endpoints('B')
    project=create_project('synthetic-history',a['config'],variants={b['config']['identifier']:b['config']},
        run_references=[a['reference'],b['reference']])
    return app,FourStrokeResults(DesktopContext(project))


def test_history_loads_verified_run_references_and_shows_periodicity_tooltip(endpoints):
    app,widget=_widget(endpoints)
    assert widget.history.count()==2 and len(widget.loaded)==2
    assert 'Periódico' in widget.history.item(0).text()
    assert 'Periodicidad: Periódico' in widget.history.item(0).toolTip()
    widget.close();app.processEvents()


def test_ab_json_csv_and_html_keep_provenance_precision_and_caveat(tmp_path,monkeypatch,endpoints):
    from PySide6.QtGui import QDesktopServices
    from PySide6.QtWidgets import QFileDialog
    app,widget=_widget(endpoints)
    widget.compare_a.setCurrentIndex(0);widget.compare_b.setCurrentIndex(1);widget.compare()
    assert widget.comparison['schema']=='DINO4T_AB_COMPARISON_V2'
    assert widget.compare_table.columnCount()==5 and widget.compare_table.rowCount()==4
    widget.compare_a.setCurrentIndex(1)
    assert widget.comparison is None and not widget.compare_json_button.isEnabled()
    widget.compare_a.setCurrentIndex(0);widget.compare()
    json_path=tmp_path/'pair.json';csv_path=tmp_path/'pair.csv';html_path=tmp_path/'pair.html'
    monkeypatch.setattr(QFileDialog,'getSaveFileName',lambda *args:(str(json_path),''))
    widget.export_comparison_json()
    loaded=json.loads(json_path.read_text(encoding='utf-8'))
    assert loaded['endpoints'][1]['resolved_config']['intake_valve']['lift']['max_lift_mm']==8.0
    monkeypatch.setattr(QFileDialog,'getSaveFileName',lambda *args:(str(csv_path),''))
    widget.export_comparison_csv()
    with csv_path.open(encoding='utf-8-sig',newline='') as stream:rows=list(csv.DictReader(stream))
    assert float(rows[0]['a_full_precision'])==25.0
    assert float(rows[0]['delta_b_minus_a'])==-1.0
    assert rows[0]['source_qualification_a']=='COMPLETE_CLEAN_SOURCE_SNAPSHOT'
    assert json.loads(rows[0]['artifact_origin_a_json'])['kind']=='SYNTHETIC_PRESENTATION_FIXTURE'
    monkeypatch.setattr(QFileDialog,'getSaveFileName',lambda *args:(str(html_path),''))
    monkeypatch.setattr(QDesktopServices,'openUrl',lambda *args:True)
    widget.export_comparison_report()
    report=html_path.read_text(encoding='utf-8')
    assert 'No constituyen una mejora demostrada' in report and 'SYNTHETIC_ASSUMPTION' in report
    widget.close();app.processEvents()


def test_export_refuses_trace_changed_after_loading(tmp_path,monkeypatch,endpoints):
    from pathlib import Path
    from PySide6.QtWidgets import QFileDialog,QMessageBox
    app,widget=_widget(endpoints)
    widget.compare_a.setCurrentIndex(0);widget.compare_b.setCurrentIndex(1);widget.compare()
    assert widget.comparison
    warnings=[]
    monkeypatch.setattr(QMessageBox,'warning',lambda *args:warnings.append(args))
    monkeypatch.setattr(QFileDialog,'getSaveFileName',lambda *args:(str(tmp_path/'must-not-exist.json'),''))
    meta=next(iter(widget.loaded.values()))[1]
    Path(meta['trace_path']).write_bytes(b'theta,p\n0,4200000\n')
    widget.export_comparison_json()
    assert warnings and not (tmp_path/'must-not-exist.json').exists() and widget.comparison is None
    widget.export_csv()
    assert len(warnings)==2
    widget.close();app.processEvents()
