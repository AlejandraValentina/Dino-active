"""Native 4T wide-RPM curve: scheduler and fail-closed presentation, no long solver."""
import json

import desktop_qsettings_isolation
import pytest

from PySide6.QtWidgets import QApplication

from motorsim.desktop.four_stroke_project import project_from_example
from motorsim.desktop.native_four_stroke_curve import (
    _NativeCurveTask, NativeFourStrokeCurvePage, plan_native_rpms,
    NATIVE_CURVE_SCHEMA,
)
from motorsim.desktop.native_four_stroke_workspace import NativeFourStrokeWorkspace
from motorsim import engine_platform

APP = QApplication.instance() or QApplication([])


def test_wide_native_4t_rpm_grid_has_explicit_bound_and_budget():
    assert plan_native_rpms(500,13000,500) == list(range(500,13001,500))
    assert len(plan_native_rpms(1000,13000,500)) == 25
    for args in ((0,13000,500),(1000,16000,500),(1000,13000,0),
                 (500,15000,100),(1000,13000,333)):
        with pytest.raises(ValueError):
            plan_native_rpms(*args)


def _task(tmp_path,rpms):
    cfg=project_from_example("curve-native")["base_engine"]
    return _NativeCurveTask(cfg,"curve-native","",rpms,3,30,tmp_path/"series")


def _fake_envelope(rpm,periodic=True):
    return {
        "error": None if periodic else {"code":"NOT_PERIODIC"},
        "summary": {
            "operating_point": {"rpm":rpm},
            "periodicity": {"status":"PERIODIC_CONVERGED" if periodic else "NOT_CONVERGED"},
            "final_cycle":{"brake_power_kW":rpm/1000.0,"brake_torque_Nm":rpm/100.0},
        },
        "result_validation":{"issues":[]},
    }


def test_native_curve_persists_points_without_inventing_power(monkeypatch,tmp_path):
    task=_task(tmp_path,[500,1000,1500])
    stored=[]
    task.signals.point.connect(stored.append)
    monkeypatch.setattr(engine_platform,"check_result",lambda *args:None)
    monkeypatch.setattr(engine_platform,"run_api",
        lambda cycle, config, **kwargs:_fake_envelope(
            config["operating_point"]["rpm"],config["operating_point"]["rpm"]!=1000))
    monkeypatch.setattr(
        "motorsim.desktop.four_stroke_artifacts.publish_desktop_run",
        lambda run_dir, envelope, project_id, variant:{
            "run_id":run_dir.name,"config_sha256":"fixture"},
    )
    terminal=[]
    task.signals.completed.connect(terminal.append)
    task.run()
    assert terminal[0]["state"]=="PARTIAL"
    assert len(stored)==3
    assert [r["state"] for r in stored]==[
        "PERIODIC_CONVERGED","NOT_CONVERGED","PERIODIC_CONVERGED"]
    assert stored[1]["brake_power_kW"] is None
    assert stored[1]["brake_torque_Nm"] is None
    series=json.loads((tmp_path/"series"/"series.json").read_text(encoding="utf-8"))
    assert series["schema"]==NATIVE_CURVE_SCHEMA
    assert series["state"]=="PARTIAL"
    assert series["rpms"]==[500,1000,1500]
    assert series["claims"]["predictive_capability"]=="NOT_CLAIMED"


def test_native_curve_cancel_preserves_completed_points(monkeypatch,tmp_path):
    task=_task(tmp_path,[500,1000,1500])
    monkeypatch.setattr(engine_platform,"check_result",lambda *args:None)
    def fake_run(cycle, config, **kwargs):
        task.cancel_event.set()
        return _fake_envelope(config["operating_point"]["rpm"])
    monkeypatch.setattr(engine_platform,"run_api",fake_run)
    monkeypatch.setattr(
        "motorsim.desktop.four_stroke_artifacts.publish_desktop_run",
        lambda run_dir, envelope, project_id, variant:{
            "run_id":run_dir.name,"config_sha256":"fixture"},
    )
    terminal=[]
    task.signals.completed.connect(terminal.append)
    task.run()
    assert terminal[0]["state"]=="CANCELLED"
    assert len(terminal[0]["rows"])==1
    assert json.loads((tmp_path/"series"/"series.json").read_text())["state"]=="CANCELLED"


def test_native_ui_shows_real_4t_power_and_torque_controls():
    workspace=NativeFourStrokeWorkspace()
    assert workspace.curve.start_rpm.value()==1000
    assert workspace.curve.end_rpm.value()==13000
    assert workspace.curve.step_rpm.value()==500
    assert workspace.simulation_pages.count()==2
    assert workspace.simulation_pages.tabText(1)=="Curva de potencia / torque"
    assert workspace.curve.power_plot.connect_points is False
    assert workspace.curve.torque_plot.connect_points is False
    workspace.close()
    workspace.deleteLater()
    APP.processEvents()


def test_reopen_fails_closed_when_curve_sidecar_lacks_verified_primary(monkeypatch,tmp_path):
    from motorsim.desktop.native_four_stroke_curve import load_native_curve_series
    task=_task(tmp_path,[500,1000])
    monkeypatch.setattr(engine_platform,"check_result",lambda *args:None)
    monkeypatch.setattr(engine_platform,"run_api",
        lambda cycle, config, **kwargs:_fake_envelope(config["operating_point"]["rpm"]))
    monkeypatch.setattr(
        "motorsim.desktop.four_stroke_artifacts.publish_desktop_run",
        lambda run_dir, envelope, project_id, variant:{"run_id":run_dir.name},
    )
    task.run()
    path=tmp_path/"series"/"series.json"
    workspace=NativeFourStrokeWorkspace()
    try:
        workspace.replace_project(project_from_example("curve-native"))
        with pytest.raises(ValueError,match="completa"):
            workspace.curve.load_saved_curve(path)

        data=json.loads(path.read_text(encoding="utf-8"))
        data["state"]="PARTIAL"
        path.write_text(json.dumps(data),encoding="utf-8")
        loaded=load_native_curve_series(path,workspace.context)
        assert [point["state"] for point in loaded["rows"]]==["CORRUPT","CORRUPT"]
        workspace.curve.load_saved_curve(path)
        assert workspace.curve.power_plot.points==[]
        assert workspace.curve.torque_plot.points==[]

        data["claims"]["predictive_capability"]="VALIDATED"
        path.write_text(json.dumps(data),encoding="utf-8")
        with pytest.raises(ValueError,match="declaraciones"):
            load_native_curve_series(path,workspace.context)
    finally:
        workspace.context.dirty=False
        workspace.close()
        workspace.deleteLater()
        APP.processEvents()


def test_reopen_displays_only_assessed_native_primary_values(monkeypatch,tmp_path):
    from motorsim.desktop.four_stroke_artifacts import (
        RunAssessment, REFERENCE_SCHEMA, curve_binding,
    )
    from motorsim.desktop.native_four_stroke_curve import load_native_curve_series
    workspace=NativeFourStrokeWorkspace()
    try:
        workspace.replace_project(project_from_example("curve-native"))
        cfg=workspace.context.engine()
        rpms=[500,1000]
        folder=tmp_path/"native-saved"
        folder.mkdir()
        rows=[]
        for i,rpm in enumerate(rpms,1):
            run_dir=folder/f"point-{i:02d}-{rpm}"
            run_dir.mkdir()
            (run_dir/"reference.json").write_text(json.dumps({
                "schema":REFERENCE_SCHEMA,
                "path":"./artifacts/summary.json",
                "run_manifest_path":"./run.json",
            }),encoding="utf-8")
            rows.append({
                "rpm":rpm,"state":"PERIODIC_CONVERGED",
                "brake_power_kW":rpm/100.0,
                "brake_torque_Nm":rpm/1000.0,
                "reason":"","run_path":str(run_dir),
            })
        sidecar={
            "schema":NATIVE_CURVE_SCHEMA,"source":"DINO4T_API_V1",
            "state":"COMPLETE","project_id":"curve-native",
            "config_sha256":engine_platform.identity("4T",cfg),
            "rpms":rpms,"rows":rows,
            "claims":{"experimental_validation":"NOT_PERFORMED",
                      "predictive_capability":"NOT_CLAIMED"},
        }
        series=folder/"series.json"
        series.write_text(json.dumps(sidecar),encoding="utf-8")
        def fake_assess(reference):
            rpm=int(__import__("pathlib").Path(reference["run_manifest_path"]).parent.name.split("-")[-1])
            return RunAssessment(
                "VERIFIED",
                summary={"periodicity":{"status":"PERIODIC_CONVERGED"},
                         "operating_point":{"rpm":rpm},
                         "final_cycle":{"brake_power_kW":rpm/100.0,
                                        "brake_torque_Nm":rpm/1000.0}},
                meta={"curve_binding_sha256":curve_binding(cfg)},
            )
        monkeypatch.setattr(
            "motorsim.desktop.four_stroke_artifacts.assess_run_reference",fake_assess
        )
        reopened=workspace.curve.load_saved_curve(series)
        assert reopened["state"]=="COMPLETE"
        assert len(workspace.curve.power_plot.points)==2
        assert workspace.curve.power_plot.points==[(500,5.0),(1000,10.0)]
        assert len(workspace.curve.torque_plot.points)==2

        sidecar["rows"][0]["brake_power_kW"]=999
        series.write_text(json.dumps(sidecar),encoding="utf-8")
        with pytest.raises(ValueError,match="no verificados"):
            load_native_curve_series(series,workspace.context)
    finally:
        workspace.context.dirty=False
        workspace.close()
        workspace.deleteLater()
        APP.processEvents()
