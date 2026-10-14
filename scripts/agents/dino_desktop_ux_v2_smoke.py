"""Visual and interaction smoke for DINO_DESKTOP_UX_V2; never starts a solver."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile

parser=argparse.ArgumentParser()
parser.add_argument("--scale",type=float,default=1.0)
parser.add_argument("--functional",action="store_true",help="Edit project and compare two existing read-only runs.")
args=parser.parse_args()
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
os.environ.setdefault("QT_QPA_PLATFORM","offscreen")
os.environ["QT_SCALE_FACTOR"]=str(args.scale)

from PySide6.QtCore import QItemSelectionModel
from PySide6.QtGui import QFontDatabase,QImage
from PySide6.QtWidgets import QApplication

from motorsim.desktop.app import DinoDesktopWindow
from motorsim.desktop.preferences import set_artifact_root
from motorsim.engine_project import load_project,save_project

CAPTURES=ROOT/"docs/dino_desktop_ux_v2/captures/after"
RECEIPT=ROOT/f"results/dino-desktop-ux-v2/visual-check-receipt-{int(args.scale*100)}pct.json"
ARTIFACT_ROOT=Path(r"E:\Dino-artifacts")
RUNS=(Path(r"E:\Dino-artifacts\exhaust-numerical-convergence-v2\exploratory-workflow-v1\dino-exhaust-comparison-starter\encv2-escape-modified-plus20-mm-3000rpm-2c\result.json"),
      Path(r"E:\Dino-artifacts\exhaust-mesh-v1\exploratory-workflow-v1\dino-exhaust-comparison-starter\exm-escape-modified-plus20-mm-3000rpm-2c\result.json"))


def project_with_run_references():
    project=load_project(ROOT/"examples/projects/dino-2t-exhaust-comparison.dino2t.json")
    references=[]
    for path in RUNS:
        manifest=json.loads((path.parent/"run.json").read_text(encoding="utf-8"))
        references.append({"path":str(path),"identity_sha256":manifest["bindings"]["identity_sha256"],
            "artifact_sha256":manifest["result_sha256"],"classification":manifest["classification"]})
    project["result_references"]=references
    return project


def main():
    CAPTURES.mkdir(parents=True,exist_ok=True);RECEIPT.parent.mkdir(parents=True,exist_ok=True)
    project=project_with_run_references() if args.functional else load_project(ROOT/"examples/projects/dino-2t-exhaust-comparison.dino2t.json")
    app=QApplication.instance() or QApplication([])
    # The offscreen Qt plugin does not enumerate Windows system fonts by itself.
    system_font=Path(r"C:\Windows\Fonts\segoeui.ttf")
    if system_font.is_file():QFontDatabase.addApplicationFont(str(system_font))
    window=DinoDesktopWindow(project);window.resize(1360,900);window.show();app.processEvents()
    assert window.isVisible()
    execution=window.pages[3];results=window.pages[4]
    loaded_points=0
    if args.functional:
        window.new_file()
        window._open(ROOT/"examples/projects/dino-2t-exhaust-comparison.dino2t.json")
        window.context.project["result_references"]=project["result_references"]
        window.context.changed.emit()
        context=window.context
        context.duplicate_variant(None,"Escape UX")
        exhaust=window.pages[1]
        exhaust.stations.item(1,2).setText("21,5")
        assert exhaust.save_current()
        context.rename_variant("Escape UX","Escape editado")
        context.duplicate_variant("Escape editado","Escape comparación")
        with tempfile.TemporaryDirectory() as temp:
            project_path=Path(temp)/"ux-smoke.dino2t.json"
            save_project(project_path,context.project)
            context.replace_project(load_project(project_path),project_path)
        set_artifact_root(ARTIFACT_ROOT)
        execution.artifact_root=ARTIFACT_ROOT;execution.history.artifact_root=ARTIFACT_ROOT
        execution.history.refresh();execution.preset.setCurrentIndex(1)
        assert len(execution.history.entries)==2
        selection=execution.history.table.selectionModel()
        for row in range(2):
            selection.select(execution.history.table.model().index(row,0),
                QItemSelectionModel.SelectionFlag.Select|QItemSelectionModel.SelectionFlag.Rows)
        assert execution.history.compare_button.isEnabled()
        # Exercise the real history->navigation->ResultsPage route while running
        # its existing full importer synchronously for deterministic visual capture.
        from motorsim.exploratory_workflow import import_exploratory_runs
        results.open_runs=lambda paths: results._loaded_exploratory(import_exploratory_runs(paths))
        execution.history.compare_selected()
        if results.dataset is None:
            raise RuntimeError("Indexed run comparison failed: "+results.path_label.text())
        loaded_points=len(results.dataset["points"])

    capture_names=[]
    pages=[(0,"motor"),(1,"escape"),(2,"proyecto"),(3,"simulacion_preparada")]
    if args.functional:pages.append((4,"resultados_comparados"))
    for index,name in pages:
        window.nav.setCurrentRow(index);window.resize(1360,900);app.processEvents()
        path=CAPTURES/f"{name}-1360x900-{int(args.scale*100)}pct.png"
        if not window.grab().save(str(path)):raise RuntimeError(f"Could not save {path}")
        capture_names.append(path)
    for index,name in ((0,"motor"),(4,"resultados")):
        window.resize(980,680);window.nav.setCurrentRow(index);app.processEvents()
        path=CAPTURES/f"{name}-980x680-{int(args.scale*100)}pct.png"
        if not window.grab().save(str(path)):raise RuntimeError(f"Could not save {path}")
        capture_names.append(path)
    records=[]
    for path in capture_names:
        image=QImage(str(path));blob=path.read_bytes()
        records.append({"path":str(path.relative_to(ROOT)),"bytes":len(blob),
            "width_px":image.width(),"height_px":image.height(),
            "sha256":hashlib.sha256(blob).hexdigest()})
    receipt={"qt_scale_factor":args.scale,"render_mode":"Qt offscreen; visual layout and Qt scale factors exercised, Windows display setting unchanged",
        "workflow":"create project; open engine project; create/edit/rename/duplicate variant; edit escape without solver; save/reopen; simulation preflight only; compare two existing referenced runs through independent importer" if args.functional else "layout-only; no simulation",
        "imported_points":loaded_points,"captures":records}
    RECEIPT.write_text(json.dumps(receipt,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps(receipt,ensure_ascii=False))
    window.close();app.processEvents();app.quit()


if __name__=="__main__":
    main()
