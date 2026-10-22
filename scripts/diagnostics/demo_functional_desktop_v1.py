"""Drive the existing Desktop controls for the authorized functional demo.

Not an alternative solver/runner. Opens the saved project, clicks the existing
execution button and then selects the actual history row to display results.
"""
import argparse
import json
import os
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
p=argparse.ArgumentParser();p.add_argument("--artifacts",type=Path,required=True);p.add_argument("--resume",action="store_true");p.add_argument("--view-only",action="store_true");p.add_argument("--cycles",type=int);p.add_argument("--run-id",default="functional-desktop-demo-v1");args=p.parse_args()
os.environ["DINO_ARTIFACT_ROOT"]=str(args.artifacts)
os.environ["DINO_TEST_SETTINGS_ROOT"]=str(args.artifacts/"settings")
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication,QMessageBox
from motorsim.desktop.app import DinoDesktopWindow
from motorsim.engine_project import load_project

args.artifacts.mkdir(parents=True,exist_ok=True)
app=QApplication([])
window=DinoDesktopWindow(load_project(ROOT/"configs/reference_cases/functional_reed_125cc_v1.dino.json"))
window.resize(1360,900);window.show()
execution=window.pages[3]
execution.rpm.setValue(9000);execution.cycles.setValue(args.cycles or (12 if args.resume else 10));execution.budget.setValue(180);execution.memory.setValue(512)
execution.run_id.setText(args.run_id)
state={"started":False,"loading":False,"done":False};start=time.monotonic()
root=args.artifacts/"exploratory-workflow-v1/functional-reed-125cc-v1"/args.run_id


def tick():
    try:
        for w in app.topLevelWidgets():
            if isinstance(w,QMessageBox) and w.isVisible():
                if w.windowTitle()=="Confirmación de ejecución":
                    next(b for b in w.buttons() if w.buttonRole(b)==QMessageBox.ButtonRole.AcceptRole).click()
                else:
                    raise RuntimeError(w.windowTitle()+": "+w.text())
        if not state["started"]:
            state["started"]=True
            window.grab().save(str(args.artifacts/"01-project.png"))
            if not execution.start.isEnabled():raise RuntimeError(execution.preflight_label.text())
            if not args.view_only:(execution.resume if args.resume else execution.start).click()
        elif (root/"result.json").exists() and execution.task is None and not state["loading"]:
            state["loading"]=True
            window.set_workspace_mode(1)
            window.analysis_history.refresh()
        elif state["loading"] and not window.results.dataset:
            if window.analysis_history.table.rowCount():
                window.analysis_history.table.selectRow(0)
                window.analysis_history.open_runs.emit([str(root)])
        elif window.results.dataset and not state["done"]:
            state["done"]=True
            rows=window.results.dataset["points"]
            assert rows and rows[0]["cycles_completed"]>0
            window.results.show_point(rows[0])
            assert window.results.trace_plot.series and window.results.trace_plot.series[0]["points"]
            app.processEvents()
            window.grab().save(str(args.artifacts/"02-results.png"))
            window.results.trace_group.grab().save(str(args.artifacts/"03-pressure-flow.png"))
            for key,name in [("duct:exhaust:face:0:mass_flow_kg_s","04-exhaust-flow.png"),
                    ("cylinder_pressure_pa","05-cylinder-pressure.png")]:
                index=window.results.trace_metric.findData(key)
                if index>=0:
                    window.results.trace_metric.setCurrentIndex(index);app.processEvents()
                    assert window.results.trace_plot.series
                    window.results.trace_group.grab().save(str(args.artifacts/name))
            receipt=dict(opened_project=True,existing_execution_button=True,history_selected=True,
                loaded_points=len(rows),cycles_completed=rows[0]["cycles_completed"],
                classification=rows[0]["classification"],audit_status=rows[0]["audit_status"],
                visible_cards=[x.text() for x in window.results.metric_cards],
                pressure_channels=list(window.results.dataset["traces"][0]["channels"]),
                run_directory=str(root),elapsed_s=time.monotonic()-start)
            (args.artifacts/"desktop-demo-receipt.json").write_text(json.dumps(receipt,indent=2),encoding="utf-8")
            print(json.dumps(receipt),flush=True);app.quit()
        if time.monotonic()-start>220:raise TimeoutError("functional demo wall guard")
    except BaseException as exc:
        (args.artifacts/"desktop-demo-error.txt").write_text(repr(exc),encoding="utf-8")
        print(repr(exc),flush=True)
        if execution.cancel_event is not None:execution.cancel_event.set()
        app.exit(1)

def confirm_authorized():
    for w in app.topLevelWidgets():
        if isinstance(w,QMessageBox) and w.isVisible() and w.windowTitle()=="Confirmación de ejecución":
            next(b for b in w.buttons() if w.buttonRole(b)==QMessageBox.ButtonRole.AcceptRole).click()

confirmation_timer=QTimer();confirmation_timer.timeout.connect(confirm_authorized);confirmation_timer.start(100)
timer=QTimer();timer.timeout.connect(tick);timer.start(500)
raise SystemExit(app.exec())
