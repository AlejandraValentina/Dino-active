import json
from pathlib import Path

import pytest

from motorsim import engine_platform
from motorsim.desktop.context import DesktopContext
from motorsim.desktop.four_stroke_project import project_from_example
from motorsim.engine_project import load_project, save_project


def test_4t_project_persists_and_keeps_family_contract_separate(tmp_path):
    project = project_from_example("synthetic-4t-project")
    source = json.loads(json.dumps(project))
    path = tmp_path / "engine.dino.json"
    save_project(path, project)
    reopened = load_project(path)
    assert reopened == source
    assert reopened["schema"] == "DINO_DESKTOP_ENGINE_PROJECT_4T_V1"
    assert reopened["engine_family"] == "4T"
    assert engine_platform.cycle_of(reopened["base_engine"]) == "4T"


def test_4t_variant_duplicate_and_edit_use_api_validation():
    context = DesktopContext(project_from_example("variant-case"))
    name = context.duplicate_variant(None, "Escape A")
    edited = json.loads(json.dumps(context.engine()))
    edited["exhaust_duct"]["segments"][0]["length_mm"] += 10.0
    context.replace_engine(edited, variant_name=name)
    checked = engine_platform.validate_config("4T", context.engine(name))
    assert checked["valid"] and not checked["unknown_keys"]
    assert context.project["base_engine"]["exhaust_duct"] != context.engine(name)["exhaust_duct"]
    assert context.project["base_identity_sha256"] == engine_platform.identity("4T", context.project["base_engine"])


def test_4t_unknown_key_is_not_silently_persisted_or_run():
    config = project_from_example("unknown-key")["base_engine"]
    config["numerics"]["typo_model"] = "V1"
    checked = engine_platform.validate_config("4T", config)
    assert checked["valid"]
    assert "numerics.typo_model" in checked["unknown_keys"]
    with pytest.raises(ValueError):
        from motorsim.desktop.four_stroke_project import create_project
        create_project("bad", config)


def test_4t_run_adapter_preserves_native_error_and_result_contract():
    config = project_from_example("bounded-4t-run")["base_engine"]
    envelope = engine_platform.run_api("4T", config, max_cycles=1,
        wall_limit_s=30.0, overrides={"numerics": {"dx_mm": 30.0}})
    assert envelope["api"] == "DINO4T_API_V1"
    assert envelope["summary"] is not None
    assert envelope["summary"]["schema"] == "DINO4T_OPERATING_POINT_RESULT_V1"
    assert envelope["summary"]["claims"]["experimental_validation"] == "NOT_PERFORMED"
    assert envelope["summary"]["claims"]["predictive_capability"] == "NOT_CLAIMED"
    assert envelope["error"]["code"] in {"NOT_PERIODIC", "WALL_LIMIT"}
    engine_platform.check_result("4T", envelope)


def test_4t_desktop_editor_edits_only_schema_fields_and_keeps_source_label(monkeypatch):
    from PySide6.QtWidgets import QApplication
    from motorsim.desktop.four_stroke_desktop import FourStrokeDesktopWindow
    app=QApplication.instance() or QApplication([])
    window=FourStrokeDesktopWindow(project_from_example("ui-editor"))
    window.resize(980,680);window.show();app.processEvents()
    table=window.editor.tables["geometry"]
    row=next(index for index in range(table.rowCount()) if table.item(index,0).text().endswith("diámetro (mm)"))
    table.item(row,1).setText("87.5")
    window.editor.apply();app.processEvents()
    assert window.context.engine()["geometry"]["bore_mm"]==87.5
    assert window.context.engine()["geometry"]["provenance"]=="SYNTHETIC_ASSUMPTION"
    assert window.tabs.tabText(0)=="MODELO" and window.tabs.tabText(1)=="SIMULAR" and window.tabs.tabText(2)=="RESULTADOS"
    window.context.duplicate_variant(None,"UI variant")
    app.processEvents()
    assert window.context.selected_variant=="UI variant"
    assert window.variant_list.currentItem().text()=="UI variant"
    window.context.dirty=False;window.close();app.processEvents()


def test_4t_report_explicitly_separates_periodicity_from_validation():
    from motorsim.desktop.technical_report import render_four_stroke_report
    document=render_four_stroke_report("project",[{"summary":{"operating_point":{"rpm":4000},"status":"completed",
        "periodicity":{"status":"PERIODIC_CONVERGED"},"final_cycle":{"brake_power_kW":12.3,"brake_torque_Nm":20.0,"bmep_bar":5.0},
        "evidence_level":"L1_ENGINEERING_RUN","claims":{"calibration":"NOT_PERFORMED","experimental_validation":"NOT_PERFORMED","predictive_capability":"NOT_CLAIMED"},
        "config_sha256":"c","code_commit":"d","code_dirty":False},"reference":{"run_id":"r","result_sha256":"h"}}])
    assert "Periódico · simulación no validada" in document
    assert "No realizado" in document and "No declarado" in document


def test_frozen_4t_provenance_uses_build_receipt(tmp_path,monkeypatch):
    from motorsim.dino4t import runner
    receipt=tmp_path/"build.json"
    payload={"source_commit":"a"*40,"trial":False,"packaged_inputs_clean":True}
    receipt.write_text(json.dumps(payload),encoding="utf-8")
    assert runner._packaged_build_metadata(receipt)==payload
    monkeypatch.setattr(runner.sys,"frozen",True,raising=False)
    monkeypatch.setattr(runner,"_packaged_build_metadata",lambda:payload)
    assert runner._git_commit()==payload["source_commit"] and runner._git_dirty() is False
    payload["trial"]=True
    assert runner._git_commit()==payload["source_commit"] and runner._git_dirty() is False
    payload["packaged_inputs_clean"]=False
    assert runner._git_dirty() is True


def test_windows_bundle_recipe_declares_4t_runtime_dependencies():
    requirements=Path("packaging/requirements-build.txt").read_text(encoding="utf-8")
    spec=Path("packaging/MotorSim.spec").read_text(encoding="utf-8")
    assert "numpy==2.3.0" in requirements and "scipy==1.15.2" in requirements
    assert "'numpy','scipy.optimize'" in spec
