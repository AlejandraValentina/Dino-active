import copy
import csv
import json
from pathlib import Path

import pytest

from motorsim import engine_platform
from motorsim.desktop.four_stroke_comparison import ComparisonIneligible, build_comparison
from motorsim.desktop.four_stroke_project import project_from_example
from motorsim.desktop.four_stroke_desktop import _outcome_label


def _synthetic_endpoint(side, *, periodic=True, dirty=False):
    """Presentation/contract fixture only; it is not a simulation result."""
    config=project_from_example("synthetic-ab")['base_engine']
    if side=="B":
        config['identifier']='synthetic-ab-B'
        config['intake_valve']['lift']['max_lift_mm']=8.0
    digest=engine_platform.identity("4T",config)
    base={"schema":"DINO4T_OPERATING_POINT_RESULT_V1","model_id":"DINO4T_FOUNDATION_V1",
        "models":{"cylinder":"TWO_ZONE_EQUILIBRIUM_V1","combustion":"WIEBE_PRESCRIBED_BURN_TWO_ZONE_EQUILIBRIUM_V1",
            "valve_boundary":"QUASI_STEADY_RESTRICTION_V2"},
        "config_sha256":digest,"code_commit":"a"*40,"code_dirty":dirty,
        "thermo_sources":{"gri30_sha256":"b"*64,"burcat_sha256":"c"*64,"accessed":[]},
        "provenance":{k:v['provenance'] for k,v in config.items() if isinstance(v,dict) and 'provenance' in v},
        "status":"completed","termination":"periodic_converged" if periodic else "requested_cycles",
        "periodicity":{"status":"PERIODIC_CONVERGED" if periodic else "NOT_CONVERGED",
            "tolerances":config['numerics']['periodicity'],"history":[]},
        "cycles_run":4,"operating_point":{"rpm":6000.0,"equivalence_ratio":1.0},
        "final_cycle":{"brake_power_kW":25.0,"brake_torque_Nm":39.8,"bmep_bar":10.0,"imep_net_bar":12.0},
        "conservation":{"final_relative_closure":{"mass":1e-14,"energy":1e-14,"elements":1e-14},
            "max_relative_closure":{"mass":2e-14,"energy":2e-14,"elements":2e-14}},
        "evidence_level":"L1_ENGINEERING_RUN","claims":{"calibration":"NOT_PERFORMED",
            "experimental_validation":"NOT_PERFORMED","predictive_capability":"NOT_CLAIMED"}}
    if side=="B":
        base['final_cycle'].update(brake_power_kW=24.0,brake_torque_Nm=38.2,bmep_bar=9.7,imep_net_bar=11.8)
    run_id=f"synthetic-{side}"
    ref={"run_id":run_id,"variant_id":"Lift 8 mm" if side=="B" else "Baseline",
        "config_sha256":digest,"result_sha256":(side.lower()*64)}
    meta={"api":"DINO4T_API_V1","result_sha256":ref['result_sha256'],
        "summary_path":f"synthetic/{side}/summary.json","config_path":f"synthetic/{side}/config.json",
        "trace_path":f"synthetic/{side}/trace.csv"}
    return {"summary":base,"config":config,"meta":meta,"reference":ref,"trace_sha256":None}


def test_comparison_requires_periodicity_and_reports_only_declared_design_changes():
    a=_synthetic_endpoint("A");b=_synthetic_endpoint("B")
    result=build_comparison(a,b)
    assert result['schema']=="DINO4T_AB_COMPARISON_V1"
    assert result['classification']=="PERIODIC_MODEL_SENSITIVITY_ONLY"
    assert result['metrics'][0]['delta_b_minus_a']==-1.0
    assert result['metrics'][0]['relative_percent_to_abs_a']==-4.0
    assert result['design_changes']==[{
        "path":"intake_valve.lift.max_lift_mm","a":10.0,"b":8.0}]
    assert result['qualification']['experimental_validation']=="NOT_PERFORMED"
    assert result['qualification']['predictive_capability']=="NOT_CLAIMED"
    moved=copy.deepcopy(a);moved['meta']['summary_path']="another-machine/runs/A/summary.json"
    moved['meta']['config_path']="another-machine/runs/A/config.json"
    assert build_comparison(moved,b)['comparison_id']==result['comparison_id']


@pytest.mark.parametrize("mutation,reason",[
    (lambda ep:ep['summary']['periodicity'].update(status="NOT_CONVERGED"),"no alcanzó periodicidad"),
    (lambda ep:ep['summary'].update(code_dirty=True),"no es reproducible"),
    (lambda ep:ep['summary'].update(code_commit="d"*40),"commits del solver"),
    (lambda ep:ep['summary']['models'].update(valve_boundary="QUASI_STEADY_RESTRICTION_V1"),"selecciones de modelo"),
    (lambda ep:ep['config']['numerics'].update(dx_mm=12.0),"diferencias fuera"),
    (lambda ep:ep['summary']['operating_point'].update(rpm=6000.0001),"condiciones de operación"),
])
def test_comparison_rejects_incompatible_or_incomplete_endpoint(mutation,reason):
    a=_synthetic_endpoint("A");b=_synthetic_endpoint("B")
    mutation(b)
    if reason=="diferencias fuera":
        b['summary']['config_sha256']=engine_platform.identity("4T",b['config'])
        b['reference']['config_sha256']=b['summary']['config_sha256']
    if "rpm" in reason:
        # Operating RPM is part of the result, but not the config identity.
        pass
    with pytest.raises(ComparisonIneligible,match=reason):
        build_comparison(a,b)


def test_comparison_rejects_same_design_and_nonfinite_metric():
    a=_synthetic_endpoint("A");b=_synthetic_endpoint("B")
    b['config']=copy.deepcopy(a['config'])
    b['summary']['config_sha256']=a['summary']['config_sha256']
    b['reference']['config_sha256']=a['reference']['config_sha256']
    with pytest.raises(ComparisonIneligible,match="no tienen diferencias"):
        build_comparison(a,b)
    b=_synthetic_endpoint("B");b['summary']['final_cycle']['brake_power_kW']=float('nan')
    with pytest.raises((ComparisonIneligible,ValueError)):
        build_comparison(a,b)


def test_relative_difference_is_undefined_for_zero_baseline():
    a=_synthetic_endpoint("A");b=_synthetic_endpoint("B")
    a['summary']['final_cycle']['brake_power_kW']=0.0
    b['summary']['final_cycle']['brake_power_kW']=1.0
    result=build_comparison(a,b)
    assert result['metrics'][0]['delta_b_minus_a']==1.0
    assert result['metrics'][0]['relative_percent_to_abs_a'] is None


def test_history_does_not_label_cancelled_run_as_completed_transient():
    assert _outcome_label({"status":"incomplete","periodicity":{"status":"NOT_CONVERGED"}})=="Incompleto"
    assert _outcome_label({"status":"completed","periodicity":{"status":"NOT_CONVERGED"}})=="Transitorio · no periódico"
    assert _outcome_label({"status":"completed","periodicity":{"status":"PERIODIC_CONVERGED"}})=="Periódico"


def test_history_loads_verified_run_references_and_shows_periodicity_tooltip(tmp_path):
    """Presentation fixture only; exercises history loading without claiming simulation evidence."""
    from PySide6.QtWidgets import QApplication
    from motorsim.desktop.context import DesktopContext
    from motorsim.desktop.four_stroke_desktop import FourStrokeResults, _curve_binding
    from motorsim.desktop.four_stroke_project import create_project

    app=QApplication.instance() or QApplication([])
    endpoints=[_synthetic_endpoint("A"),_synthetic_endpoint("B")]
    refs=[];variants={}
    for endpoint_index,endpoint in enumerate(endpoints):
        summary=endpoint["summary"];config=endpoint["config"];run_id=endpoint["reference"]["run_id"]
        root=tmp_path/run_id;artifacts=root/"artifacts";artifacts.mkdir(parents=True)
        summary_path=artifacts/"summary.json";config_path=artifacts/"config_resolved.json";trace_path=artifacts/"trace_last_cycle.csv"
        summary_path.write_text(json.dumps(summary),encoding="utf-8")
        config_path.write_text(json.dumps(config),encoding="utf-8")
        trace_path.write_text("theta,p,p_intake_port,p_exhaust_port\n0,100000,100000,100000\n",encoding="utf-8")
        digest=__import__("hashlib").sha256(summary_path.read_bytes()).hexdigest()
        variant=endpoint["reference"]["variant_id"] if endpoint_index else ""
        if endpoint_index:variants[config["identifier"]]=config
        meta={"schema":"DINO4T_DESKTOP_RUN_V1","run_id":run_id,"result_sha256":digest,
            "api":"DINO4T_API_V1","summary_path":str(summary_path),"config_path":str(config_path),
            "trace_path":str(trace_path),"config_identity_sha256":summary["config_sha256"],
            "curve_binding_sha256":_curve_binding(config)}
        (root/"run.json").write_text(json.dumps(meta),encoding="utf-8")
        refs.append({"run_id":run_id,"path":str(summary_path),"result_sha256":digest,
            "config_sha256":summary["config_sha256"],"status":"completed",
            "periodicity_status":"PERIODIC_CONVERGED","variant_id":variant})
    project=create_project("synthetic-history",endpoints[0]["config"],variants=variants,run_references=refs)
    widget=FourStrokeResults(DesktopContext(project))
    assert widget.history.count()==2
    assert "Periódico" in widget.history.item(0).text()
    assert "Periodicidad: Periódico" in widget.history.item(0).toolTip()
    widget.close();app.processEvents()


def test_ab_json_csv_and_html_keep_provenance_precision_and_caveat(tmp_path,monkeypatch):
    from PySide6.QtGui import QDesktopServices
    from PySide6.QtWidgets import QApplication, QFileDialog
    from motorsim.desktop.context import DesktopContext
    from motorsim.desktop.four_stroke_desktop import FourStrokeResults

    app=QApplication.instance() or QApplication([])
    a=_synthetic_endpoint("A");b=_synthetic_endpoint("B")
    files=[]
    for endpoint in (a,b):
        root=tmp_path/endpoint['reference']['run_id'];root.mkdir()
        summary_path=root/'summary.json';config_path=root/'config.json';trace_path=root/'trace.csv'
        summary_path.write_text(json.dumps(endpoint['summary']),encoding='utf-8')
        config_path.write_text(json.dumps(endpoint['config']),encoding='utf-8')
        trace_path.write_text('theta,p\n0,100000\n',encoding='utf-8')
        endpoint['meta'].update(summary_path=str(summary_path),config_path=str(config_path),trace_path=str(trace_path))
        files.append(endpoint)
    widget=FourStrokeResults(DesktopContext(project_from_example("synthetic-ab-ui")))
    widget.loaded={index:(ep['summary'],ep['meta'],ep['reference']) for index,ep in enumerate(files)}
    for index,ep in enumerate(files):
        widget.compare_a.addItem(ep['reference']['variant_id'],index)
        widget.compare_b.addItem(ep['reference']['variant_id'],index)
    widget.compare_a.setCurrentIndex(0);widget.compare_b.setCurrentIndex(1);widget.compare()
    assert widget.comparison['schema']=="DINO4T_AB_COMPARISON_V1"
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
    with csv_path.open(encoding='utf-8-sig',newline='') as stream:
        rows=list(csv.DictReader(stream))
    assert float(rows[0]['a_full_precision'])==25.0
    assert float(rows[0]['delta_b_minus_a'])==-1.0
    monkeypatch.setattr(QFileDialog,'getSaveFileName',lambda *args:(str(html_path),''))
    monkeypatch.setattr(QDesktopServices,'openUrl',lambda *args:True)
    widget.export_comparison_report()
    report=html_path.read_text(encoding='utf-8')
    assert "No constituyen una mejora demostrada" in report
    assert "SYNTHETIC_ASSUMPTION" in report
    widget.close();app.processEvents()
