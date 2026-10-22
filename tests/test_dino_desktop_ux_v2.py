from __future__ import annotations

import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import tempfile
import unittest
from PySide6.QtWidgets import QApplication,QTableWidgetItem
from unittest.mock import patch
from PySide6.QtCore import QSettings,QEventLoop,QTimer
import desktop_qsettings_isolation  # noqa: F401

from motorsim.desktop.app import DinoDesktopWindow
from motorsim.desktop.context import DesktopContext
from motorsim.desktop.services import new_project
from motorsim.desktop.execution_page import ExecutionPage
from motorsim.desktop.results_page import ResultsPage
from motorsim.desktop.preferences import artifact_root,set_artifact_root,settings
from motorsim.desktop.exhaust_page import ExhaustPage
from motorsim.desktop.engine_page import EnginePage
from motorsim.desktop.project_page import ProjectPage
from motorsim.desktop.run_history import list_project_runs
from motorsim.desktop.widgets.run_history import RunHistoryWidget
from motorsim.engine_configuration import identity


APP=QApplication.instance() or QApplication([])


class DesktopContextV2Tests(unittest.TestCase):
    def test_run_history_uses_result_metadata_when_manifest_is_summary_only(self):
        with tempfile.TemporaryDirectory() as temp:
            root=__import__("pathlib").Path(temp)
            run=root/"run-3000";run.mkdir()
            manifest={"schema":"DINO_EXPLORATORY_RUN_V1","run_id":"run-3000","status":"COMPLETE",
                "classification":"EXPLORATORY_COMPLETE_PERIODICITY_NOT_IDENTIFIED",
                "result_sha256":"a"*64,"bindings":{"variant_label":"Escape original",
                    "identity_sha256":"b"*64,"configuration_sha256":"c"*64},
                "cycles":[{"audit":{"status":"PASS","recomputed":True},
                    "conservation":{"mass":"PASS","energy":"PASS","species":"PASS"}}]}
            result={"status":"COMPLETE","classification":"EXPLORATORY_COMPLETE_PERIODICITY_NOT_IDENTIFIED",
                "periodicity":"NOT_EVALUATED","preflight":{"rpm":3000.0,"max_cycles":1}}
            (run/"run.json").write_text(__import__("json").dumps(manifest),encoding="utf-8")
            (run/"result.json").write_text(__import__("json").dumps(result),encoding="utf-8")
            entries=list_project_runs({"project_id":"ux-summary-manifest","result_references":[
                {"path":str(run/"result.json"),"identity_sha256":"b"*64}]},root)
            self.assertEqual(len(entries),1)
            self.assertEqual(entries[0]["rpm"],3000.0)
            self.assertEqual(entries[0]["periodicity"],"NOT_EVALUATED")
            self.assertEqual(entries[0]["classification"],"EXPLORATORY_COMPLETE_PERIODICITY_NOT_IDENTIFIED")
            self.assertEqual(entries[0]["audit"],"PASS")

    def test_run_history_is_read_only_and_preserves_identity_and_status_gaps(self):
        with tempfile.TemporaryDirectory() as temp:
            root=__import__("pathlib").Path(temp)
            run=root/"exploratory-workflow-v1"/"ux-history"/"run-1";run.mkdir(parents=True)
            manifest={"run_id":"run-1","status":"INTERRUPTED_CHECKPOINTED",
                "classification":"INTERRUPTED_CHECKPOINTED","periodicity":"NOT_EVALUATED",
                "preflight":{"rpm":3100,"max_cycles":3},"checkpoint_artifact":"checkpoint.json",
                "checkpoint_sha256":"c"*64,"result_sha256":"r"*64,
                "bindings":{"variant_label":"Variante A","identity_sha256":"i"*64,
                    "configuration_sha256":"g"*64,"source_hashes":{"solver":"s"*64}},
                "cycles":[{"audit":{"status":"PASS","recomputed":True},
                    "conservation":{"mass":"PASS","energy":"PASS","species":"PASS"}}]}
            path=run/"run.json";path.write_text(__import__("json").dumps(manifest),encoding="utf-8")
            (run/"result.json").write_text("{}",encoding="utf-8");(run/"checkpoint.json").write_text("{}",encoding="utf-8")
            before={p.name:p.read_bytes() for p in run.iterdir()}
            entries=list_project_runs({"project_id":"ux-history","result_references":[]},root)
            self.assertEqual(len(entries),1);entry=entries[0]
            self.assertEqual(entry["identity_sha256"],"i"*64)
            self.assertEqual(entry["configuration_sha256"],"g"*64)
            self.assertEqual(entry["periodicity"],"NOT_EVALUATED")
            self.assertEqual(entry["audit"],"PASS");self.assertTrue(entry["audit_recomputed"])
            self.assertEqual(entry["conservation_cycles"],1);self.assertTrue(entry["resumable"])
            self.assertEqual(before,{p.name:p.read_bytes() for p in run.iterdir()})

    def test_history_compares_two_referenced_roots_without_moving_artifacts(self):
        with tempfile.TemporaryDirectory() as temp:
            root=__import__("pathlib").Path(temp);refs=[]
            for index in range(2):
                run=root/f"root-{index}"/"exploratory-workflow-v1"/"shared-project"/f"run-{index}"
                run.mkdir(parents=True);(run/"result.json").write_text("{}",encoding="utf-8")
                manifest={"run_id":f"run-{index}","status":"COMPLETE","classification":"EXPLORATORY_COMPLETE_PERIODICITY_NOT_IDENTIFIED",
                    "periodicity":"NOT_EVALUATED","preflight":{"rpm":3000,"max_cycles":2},
                    "bindings":{"variant_label":f"Variante {index}","identity_sha256":str(index)*64,"configuration_sha256":"a"*64},
                    "cycles":[]}
                (run/"run.json").write_text(__import__("json").dumps(manifest),encoding="utf-8")
                refs.append({"path":str(run/"result.json"),"identity_sha256":str(index)*64,"artifact_sha256":"b"*64,"classification":manifest["classification"]})
            project={"project_id":"shared-project","result_references":refs}
            entries=list_project_runs(project,root)
            self.assertEqual(len(entries),2)
            self.assertNotEqual(entries[0]["artifact_root"],entries[1]["artifact_root"])
            context=DesktopContext(new_project("ux-history-compare"));widget=RunHistoryWidget(context,root)
            widget.entries=entries;widget.table.setRowCount(2)
            for row in range(2):
                item=QTableWidgetItem(str(row));item.setData(__import__("PySide6.QtCore",fromlist=["Qt"]).Qt.ItemDataRole.UserRole,row)
                widget.table.setItem(row,0,item)
            selection=widget.table.selectionModel()
            from PySide6.QtCore import QItemSelectionModel
            for row in range(2):selection.select(widget.table.model().index(row,0),QItemSelectionModel.SelectionFlag.Select|QItemSelectionModel.SelectionFlag.Rows)
            got=[];widget.open_runs.connect(got.append);widget.compare_selected()
            self.assertTrue(widget.compare_button.isEnabled());self.assertEqual(len(got[0]),2)
            widget.close()

    def test_indexed_results_open_uses_background_reaudit_adapter(self):
        context=DesktopContext(new_project("ux-async-results"));page=ResultsPage(context)
        dataset={"schema":"DINO_EXPLORATORY_COMPARISON_V1","points":[],"traces":[],
            "provenance":"fixture","experimental_validation":"NOT_CLAIMED"}
        loop=QEventLoop();timer=QTimer();timer.setInterval(10)
        timer.timeout.connect(lambda:loop.quit() if page.dataset is not None else None);timer.start()
        with patch("motorsim.engineering_workflow.import_desktop_runs",return_value=dataset) as importer:
            page.open_runs(["read-only-fixture/result.json"])
            QTimer.singleShot(3000,loop.quit);loop.exec()
        timer.stop();self.assertIs(page.dataset,dataset);importer.assert_called_once()
        self.assertIn("corridas EXPLORATORY importadas",page.source_notice.text())
        page.close()

    def test_history_widget_compare_requires_two_readable_runs(self):
        with tempfile.TemporaryDirectory() as temp:
            context=DesktopContext(new_project("ux-history-widget"))
            widget=RunHistoryWidget(context,temp)
            self.assertFalse(widget.compare_button.isEnabled())
            widget.close()

    def test_engine_editor_uses_backend_port_angles_and_locale_decimal_input(self):
        page=EnginePage(DesktopContext(new_project("ux-engine-responsive")))
        self.assertIn("cm³",page.derived.text())
        self.assertGreater(page.timing.rowCount(),0)
        self.assertEqual(page._decimal("21,5"),21.5)
        self.assertEqual(page._decimal("21.5"),21.5)
        with self.assertRaises(ValueError):page._decimal("21,5.2")

    def test_simulation_presets_explain_non_guaranteed_periodicity(self):
        page=ExecutionPage(DesktopContext(new_project("ux-presets")))
        page.preset.setCurrentIndex(1)
        self.assertEqual(page.cycles.value(),24)
        self.assertIn("no garantiza periodicidad",page.expected.text())
        self.assertIn("no permite potencia o torque periódicos",page.expected.text())

    def test_variant_creation_uses_owner_selected_name(self):
        context=DesktopContext(new_project("ux-named-variant"));page=ProjectPage(context)
        with patch("motorsim.desktop.project_page.QInputDialog.getText",return_value=("Escape prueba",True)):
            page.make_variant()
        self.assertIn("Escape prueba",context.project["variants"])
        self.assertEqual(context.selected_variant,"Escape prueba")

    def test_resume_from_history_requires_exact_engine_identity(self):
        context=DesktopContext(new_project("ux-resume-binding"));page=ExecutionPage(context)
        with tempfile.TemporaryDirectory(prefix="dino-ux-resume-") as artifact_root:
            entry={"identity_sha256":identity(context.engine()),"run_id":"interrupted","artifact_root":artifact_root,
                "rpm":3100,"details":{"cycles_requested":3}}
            with patch.object(page,"start_run") as start:
                page.resume_from_entry(entry)
            start.assert_called_once_with(resume=True)
            with patch("motorsim.desktop.execution_page.QMessageBox.warning") as warning,patch.object(page,"start_run") as start:
                page.resume_from_entry({**entry,"identity_sha256":"0"*64})
            warning.assert_called_once();start.assert_not_called()

    def test_project_tree_and_splitter_fit_minimum_supported_window(self):
        window=DinoDesktopWindow(new_project("ux-small-window"));window.resize(980,680);window.show();APP.processEvents()
        self.assertGreaterEqual(window.width(),980);self.assertEqual(window.project_tree.topLevelItemCount(),1)
        self.assertGreaterEqual(window.nav.width(),128);self.assertTrue(window.nav.isVisible())
        window.close()

    def test_variant_selection_stays_visible_across_pages(self):
        project=new_project("ux-v2-context-test")
        context=DesktopContext(project)
        name=context.duplicate_variant(None,"Escape prueba")
        window=DinoDesktopWindow(context.project)
        window.context.select_variant(name)
        for page in range(window.nav.count()):
            window.nav.setCurrentIndex(page)
            self.assertEqual(window.context.selected_variant,name)
            self.assertEqual(window.context_bar.variant.currentData(),name)
            self.assertEqual(window.inspector_variant.text(),"Escape prueba")
        self.assertIn("no demostraron independencia espacial",window.inspector_science.text())
        window.close()

    def test_variant_lifecycle_is_named_and_does_not_propagate_base_changes(self):
        context=DesktopContext(new_project("ux-v2-variant-test"))
        context.duplicate_variant(None,"Primera")
        variant_identity=identity(context.engine())
        changed=context.project["base_engine"]
        changed["display_name"]="Motor base renombrado"
        self.assertEqual(identity(context.engine("Primera")),variant_identity)
        self.assertEqual(context.engine("Primera")["display_name"],"Primera")
        context.rename_variant("Primera","Escape A")
        self.assertEqual(context.selected_variant,"Escape A")
        context.delete_variant("Escape A")
        self.assertIsNone(context.selected_variant)

    def test_variant_delete_fails_closed_when_external_run_references_exist(self):
        context=DesktopContext(new_project("ux-v2-referenced-test"))
        context.duplicate_variant(None,"Con corrida")
        context.project["result_references"]=[{"path":"run.json","identity_sha256":"a"*64,
            "artifact_sha256":"b"*64,"classification":"EXPLORATORY"}]
        with self.assertRaisesRegex(ValueError,"referencias externas"):
            context.delete_variant("Con corrida")
        self.assertIn("Con corrida",context.project["variants"])

    def test_artifact_root_preference_is_shared_by_simulation_and_results(self):
        prefs=settings();old=prefs.value("artifact_root")
        try:
            with tempfile.TemporaryDirectory() as temp:
                root=set_artifact_root(temp)
                self.assertEqual(artifact_root(),root)
                execution=ExecutionPage(DesktopContext(new_project("ux-v2-root")))
                results=ResultsPage(DesktopContext(new_project("ux-v2-root")))
                self.assertEqual(execution.artifact_root,root)
                with patch("motorsim.desktop.results_page.QFileDialog.getOpenFileName",return_value=("","")) as dialog:
                    results.choose()
                self.assertEqual(dialog.call_args.args[2],str(root))
        finally:
            if old is None:prefs.remove("artifact_root")
            else:prefs.setValue("artifact_root",old);prefs.sync()

    def test_escape_editor_uses_each_shared_station_once_and_rebuilds_widgets_safely(self):
        page=ExhaustPage(DesktopContext(new_project("ux-v2-stations")))
        count=page.mesh_table.rowCount()
        self.assertEqual(page.table.rowCount(),count)
        self.assertEqual(page.stations.rowCount(),count+1)
        page.refresh();page.refresh()
        combos=[page.mesh_table.cellWidget(i,1) for i in range(count)]
        self.assertEqual(sum(widget is not None for widget in combos),count)
        # One station diameter feeds both adjoining segments without duplicate fields.
        page.stations.item(1,2).setText("21,5")
        rows=page._rows()
        self.assertEqual(rows[0]["outlet_diameter_mm"],21.5)
        self.assertEqual(rows[1]["inlet_diameter_mm"],21.5)
        self.assertEqual(sum(1 for i in range(count) if page.mesh_table.cellWidget(i,1) is not None),count)

    def test_escape_variant_save_is_named_and_current_variant_is_updated_in_place(self):
        context=DesktopContext(new_project("ux-v2-escape-save"));page=ExhaustPage(context)
        self.assertTrue(page.save_as_new(name="Resonador B"))
        self.assertEqual(context.selected_variant,"Resonador B")
        variant_count=len(context.project["variants"])
        page.table.item(1,1).setText("185,5")
        self.assertTrue(page.save_current())
        self.assertEqual(len(context.project["variants"]),variant_count)
        self.assertEqual(context.engine()["native_configuration"]["geometry_identity"]["chamber"]["sections"][1]["length_mm"],185.5)


if __name__=="__main__":
    unittest.main()
