"""Open the saved actual Dino 4T A/B artifacts in Desktop and exercise exports.

This does not execute the solver. The two source results are synthetic model
sensitivity runs and keep their original validation/predictivity labels.
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
from pathlib import Path
import tempfile

os.environ.setdefault("QT_QPA_PLATFORM","offscreen")
ROOT=Path(__file__).resolve().parents[2]
import sys
sys.path.insert(0,str(ROOT))

from PySide6.QtWidgets import QApplication,QFileDialog
from PySide6.QtGui import QDesktopServices,QFontDatabase
from motorsim.desktop.context import DesktopContext
from motorsim.desktop.four_stroke_desktop import FourStrokeDesktopWindow
from motorsim.engine_project import load_project


def main() -> int:
    run_root=ROOT/"results/dino4t-ab-engineering-v1/runs"
    project_path=run_root/"dino4t-synthetic-ab-v1.dino.json"
    expected=json.loads((run_root/"comparison.json").read_text(encoding="utf-8"))
    project=load_project(project_path)
    app=QApplication.instance() or QApplication(["Dino4T-AB-source-verification"])
    system_font=Path(r"C:\Windows\Fonts\segoeui.ttf")
    if system_font.is_file():QFontDatabase.addApplicationFont(str(system_font))
    window=FourStrokeDesktopWindow(project,path=project_path)
    window.resize(1360,900);window.show();app.processEvents()
    if len(window.results.loaded)!=2 or window.results.history.count()!=2:
        raise AssertionError("verified project did not load both actual run references")
    window.tabs.setCurrentIndex(2);window.results.result_tabs.setCurrentIndex(5)
    window.results.compare_a.setCurrentIndex(0);window.results.compare_b.setCurrentIndex(1)
    window.results.compare()
    actual=window.results.comparison
    if actual is None or actual["comparison_id"]!=expected["comparison_id"]:
        raise AssertionError("Desktop did not reproduce the stored eligible A/B comparison")
    with tempfile.TemporaryDirectory(prefix="dino4t-ab-desktop-") as tmp:
        out=Path(tmp);json_path=out/"comparison.json";csv_path=out/"comparison.csv";html_path=out/"comparison.html"
        with __import__("unittest.mock",fromlist=["patch"]).patch.object(QFileDialog,"getSaveFileName",side_effect=[(str(json_path),""),(str(csv_path),""),(str(html_path),"")]), \
             __import__("unittest.mock",fromlist=["patch"]).patch.object(QDesktopServices,"openUrl",return_value=True):
            window.results.export_comparison_json();window.results.export_comparison_csv();window.results.export_comparison_report()
        exported=json.loads(json_path.read_text(encoding="utf-8"))
        with csv_path.open(encoding="utf-8-sig",newline="") as stream:rows=list(csv.DictReader(stream))
        report=html_path.read_text(encoding="utf-8")
        if exported["comparison_id"]!=expected["comparison_id"]:raise AssertionError("JSON comparison ID changed")
        if len(rows)!=4 or not all(row["result_sha256_a"] and row["result_sha256_b"] for row in rows):
            raise AssertionError("CSV export is missing metrics or endpoint hashes")
        if float(rows[0]["a_full_precision"])!=actual["metrics"][0]["a"]:
            raise AssertionError("CSV discarded metric precision")
        if "No constituyen una mejora demostrada" not in report:raise AssertionError("HTML omitted scientific caveat")
        capture=run_root/"source-desktop-ab-1360x900.png"
        if not window.grab().save(str(capture)):raise RuntimeError("source Desktop screenshot failed")
        export_meta={"json_sha256":hashlib.sha256(json_path.read_bytes()).hexdigest(),
            "csv_sha256":hashlib.sha256(csv_path.read_bytes()).hexdigest(),
            "html_sha256":hashlib.sha256(html_path.read_bytes()).hexdigest(),"csv_rows":len(rows)}
    receipt={"schema":"DINO4T_AB_DESKTOP_SOURCE_VERIFICATION_V1","result":"PASS",
        "solver_executed":False,"project_path":str(project_path.resolve()),
        "project_sha256":hashlib.sha256(project_path.read_bytes()).hexdigest(),
        "comparison_id":actual["comparison_id"],"comparison_classification":actual["classification"],
        "eligible":True,"loaded_run_count":len(window.results.loaded),"exports":export_meta,
        "capture":{"path":str(capture.resolve()),"sha256":hashlib.sha256(capture.read_bytes()).hexdigest(),
            "size_bytes":capture.stat().st_size,"window_size":[1360,900]},
        "claims":{"experimental_validation":"NOT_PERFORMED","predictive_capability":"NOT_CLAIMED"}}
    (run_root/"source-desktop-verification.json").write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    window.context.dirty=False;window.close();app.processEvents()
    print(json.dumps(receipt,ensure_ascii=False))
    return 0


if __name__=="__main__":raise SystemExit(main())
