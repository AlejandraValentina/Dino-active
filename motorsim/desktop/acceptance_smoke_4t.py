"""Maintainer-only GUI acceptance route used against source and frozen Dino Desktop."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import sys


def main(argv=None):
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--historical-summary",type=Path,required=True)
    parser.add_argument("--historical-2t-project",type=Path)
    parser.add_argument("--run",action="store_true",help="execute one cycle-limited 4T Desktop point")
    args=parser.parse_args(argv)
    args.output.mkdir(parents=True,exist_ok=False)
    os.environ["DINO_TEST_SETTINGS_ROOT"]=str(args.output/"settings")
    os.environ["DINO_ARTIFACT_ROOT"]=str(args.output/"artifacts")
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication,QFileDialog,QMessageBox
    from PySide6.QtGui import QDesktopServices
    from .four_stroke_project import project_from_example
    from .four_stroke_desktop import FourStrokeDesktopWindow
    from ..engine_project import load_project,save_project
    from ..engine_platform import identity

    app=QApplication.instance() or QApplication(["DinoDesktop-smoke"]);app.setApplicationName("Dino Desktop")
    project=project_from_example("dino4t-smoke-synthetic")
    source_config=json.loads(json.dumps(project["base_engine"]))
    capture_dir=args.output/"captures";capture_dir.mkdir(exist_ok=True)
    legacy_2t_verified=False;legacy_2t_results_verified=0
    if args.historical_2t_project:
        from .app import DinoDesktopWindow
        legacy_project=load_project(args.historical_2t_project)
        if legacy_project.get("engine_family")=="4T":raise AssertionError("legacy project unexpectedly identifies as 4T")
        for ref in legacy_project.get("result_references",[]):
            source=Path(ref["path"])
            if not source.is_absolute():source=args.historical_2t_project.parent/source
            if not source.is_file() or hashlib.sha256(source.read_bytes()).hexdigest()!=ref.get("artifact_sha256"):
                raise AssertionError(f"historical 2T result failed source hash verification: {source}")
            legacy_2t_results_verified+=1
        if legacy_2t_results_verified<1:raise AssertionError("historical 2T project has no verified results")
        legacy_window=DinoDesktopWindow(legacy_project);legacy_window.show();app.processEvents()
        if legacy_window.context.project!=legacy_project or len(legacy_project.get("result_references",[]))<1:
            raise AssertionError("historical 2T project/results failed to open in Desktop")
        legacy_window.resize(1360,900);app.processEvents()
        image=capture_dir/"proyecto-2t-historico-1360x900.png"
        if not legacy_window.grab().save(str(image)):raise RuntimeError("failed to capture 2T Desktop")
        legacy_2t_verified=True
        legacy_window._launch_four_stroke(project,None)
        window=legacy_window._four_stroke_window
    else:
        window=FourStrokeDesktopWindow(project);window.show();app.processEvents()
    window.resize(980,680);app.processEvents();
    captures=[]

    def capture(label,width,height,page):
        window.resize(width,height);window.tabs.setCurrentIndex(page);app.processEvents()
        path=capture_dir/f"{label}-{width}x{height}.png"
        if not window.grab().save(str(path)):raise RuntimeError(f"failed to capture {path}")
        captures.append({"path":str(path),"sha256":hashlib.sha256(path.read_bytes()).hexdigest(),"size":[width,height],"tab":window.tabs.tabText(page)})

    # Edit a physical geometry value through the schema-derived UI table.
    table=window.editor.tables["geometry"]
    row=next(i for i in range(table.rowCount()) if table.item(i,0).text().endswith("diámetro (mm)"))
    table.item(row,1).setText("87.0");window.editor.apply();app.processEvents()
    if window.context.engine()["geometry"]["bore_mm"]!=87.0:raise AssertionError("4T editor did not apply bore edit")
    if window.context.engine()["geometry"]["provenance"]!="SYNTHETIC_ASSUMPTION":raise AssertionError("provenance changed silently")
    window.context.duplicate_variant(None,"Escape B")
    variant=json.loads(json.dumps(window.context.engine()));variant["exhaust_duct"]["segments"][0]["length_mm"]+=8.0
    window.context.replace_engine(variant,variant_name="Escape B")
    if window.context.engine("Escape B")["exhaust_duct"]==window.context.project["base_engine"]["exhaust_duct"]:raise AssertionError("escape variant edit not preserved")
    project_path=args.output/"synthetic-4t-project.dino.json";save_project(project_path,window.context.project)
    persisted=load_project(project_path)
    if persisted!=window.context.project:raise AssertionError("4T save/reopen changed project data")

    # Import a pre-existing 4T result by hash and companion configuration; the source stays read-only.
    with __import__("unittest.mock",fromlist=["patch"]).patch.object(QFileDialog,"getOpenFileName",return_value=(str(args.historical_summary),"")), \
         __import__("unittest.mock",fromlist=["patch"]).patch.object(QMessageBox,"information",return_value=None):
        window.results.import_historical()
    if not window.context.project["run_references"]:raise AssertionError("historical 4T result not imported")
    save_project(project_path,window.context.project)
    if len(load_project(project_path)["run_references"])!=1:raise AssertionError("historical import did not persist")
    window.results.refresh()
    if not window.results.loaded:raise AssertionError("imported historical result not loadable")
    history_labels=[window.results.history.item(i).text() for i in range(window.results.history.count())]
    if any(label.startswith("Fuente no verificable") for label in history_labels):
        raise AssertionError("history rendered an imported result as unverifiable: "+" | ".join(history_labels))
    capture("modelo",980,680,0)
    capture("resultados",1360,900,2)
    capture("historial",1920,1080,2)

    run_record=None
    if args.run:
        window.simulation.cycles.setValue(1);window.simulation.wall.setValue(30)
        completed=[];window.simulation.runFinished.connect(lambda record:(completed.append(record),app.quit()))
        window.simulation.execute()
        QTimer.singleShot(45000,app.quit);app.exec()
        if not completed:raise AssertionError("4T run did not reach a terminal result in 45 s")
        run_record=completed[0];window.results.refresh()
        history_labels=[window.results.history.item(i).text() for i in range(window.results.history.count())]
        if any(label.startswith("Fuente no verificable") for label in history_labels):
            raise AssertionError("history rendered a completed run as unverifiable: "+" | ".join(history_labels))
        if run_record["periodicity_status"]=="PERIODIC_CONVERGED":raise AssertionError("one-cycle smoke unexpectedly claimed periodic convergence")
        if not any(summary["periodicity"]["status"]=="PERIODIC_CONVERGED" for summary,_,_ in window.results.loaded.values()):
            raise AssertionError("historical periodic result missing from results view")
        window.tabs.setCurrentIndex(2);app.processEvents()
        capture("resultado-ejecucion-acotada",1360,900,2)
        # Exercise export precision and report claims without opening external UI.
        csv_path=args.output/"results.csv"
        with __import__("unittest.mock",fromlist=["patch"]).patch.object(QFileDialog,"getSaveFileName",return_value=(str(csv_path),"")), \
             __import__("unittest.mock",fromlist=["patch"]).patch.object(QMessageBox,"information",return_value=None):
            window.results.export_csv()
        rows=list(csv.DictReader(csv_path.open(encoding="utf-8-sig",newline="")))
        if len(rows)!=2:raise AssertionError(f"expected two exported records, got {len(rows)}")
        report_path=args.output/"technical-report.html"
        with __import__("unittest.mock",fromlist=["patch"]).patch.object(QFileDialog,"getSaveFileName",return_value=(str(report_path),"")), \
             __import__("unittest.mock",fromlist=["patch"]).patch.object(QDesktopServices,"openUrl",return_value=True):
            window.results.export_report()
        report=report_path.read_text(encoding="utf-8")
        if "No realizado" not in report or "No declarado" not in report:raise AssertionError("report lost scientific claim states")
        save_project(project_path,window.context.project)
        reopened=load_project(project_path)
        if len(reopened["run_references"])!=2:raise AssertionError("run history not persisted through reopen")

    window.context.dirty=False;window.close();app.processEvents()
    receipt={"schema":"DINO4T_DESKTOP_ACCEPTANCE_SMOKE_V1","project_path":str(project_path),
        "engine_family":"4T","configuration_schema":source_config["schema"],
        "starter_config_identity_sha256":identity("4T",source_config),"variant_edit_verified":True,
        "save_reopen_verified":True,"historical_result_import_verified":True,"run_performed":bool(args.run),
        "run_status":run_record.get("status") if run_record else None,"legacy_2t_project_verified":legacy_2t_verified,
        "legacy_2t_result_count_verified":legacy_2t_results_verified,
        "periodicity_status":run_record.get("periodicity_status") if run_record else None,
        "claims":{"experimental_validation":"NOT_PERFORMED","predictive_capability":"NOT_CLAIMED"},
        "captures":captures}
    receipt_path=args.output/"acceptance.json";receipt_path.write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"acceptance":"PASS","receipt":str(receipt_path),"captures":len(captures),"run":run_record},ensure_ascii=False))
    return 0
