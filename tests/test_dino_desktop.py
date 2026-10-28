"""Functional UI tests; all engine data are synthetic or historical read-only artifacts."""
from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from copy import deepcopy
from PySide6.QtCore import Qt,QTimer
from PySide6.QtWidgets import QApplication,QDialog,QLabel,QMessageBox,QTableWidget,QFileDialog,QComboBox
from PySide6.QtTest import QTest
import desktop_qsettings_isolation  # noqa: F401

from motorsim.desktop.app import DinoDesktopWindow
from motorsim.desktop.context import DesktopContext
from motorsim.desktop.engine_page import EnginePage
from motorsim.desktop.exhaust_page import ExhaustPage
from motorsim.desktop.execution_page import ExecutionPage
from motorsim.desktop.project_page import ProjectPage
from motorsim.desktop.results_page import ResultsPage
from motorsim.desktop.preferences import impl2_historical_report_candidate
from motorsim.desktop.services import load_results, new_project, new_design_project, run_background
from motorsim.engine_configuration import identity,create,resolve_for_operating_point
from motorsim.engine_project import create_project,load_project,save_project


APP = QApplication.instance() or QApplication([])


def spin_until(predicate, timeout_ms=10000):
    elapsed = 0
    while not predicate() and elapsed < timeout_ms:
        APP.processEvents()
        QTest.qWait(20)
        elapsed += 20
    APP.processEvents()
    return bool(predicate())


class DinoDesktopTests(unittest.TestCase):
    def setUp(self):
        self.context = DesktopContext(new_project("ui-test"))

    def test_startup_has_real_pages_and_explicitly_confirmed_exploratory_mode(self):
        window = DinoDesktopWindow(new_project("startup-test"))
        self.assertEqual(window.mode_stack.count(), 2)
        self.assertEqual(window.component_stack.count(), 4)
        self.assertEqual(window.mode_stack.currentIndex(),0)
        self.assertEqual(window.component_nav.tabText(0),"✓ Cilindro y distribución")
        self.assertTrue(window.pages[3].start.isEnabled())
        self.assertIn("Preflight PASS", window.pages[3].preflight_label.text())
        self.assertIn("EXPLORATORY", window.pages[3].mode.text())
        self.assertIsNone(window.pages[4].dataset)
        self.assertIn("no se cargó evidencia histórica",window.pages[4].source_notice.text())
        self.assertTrue(window.strip_run.isEnabled())
        self.assertFalse(window.results.isVisible())
        window.close()

    def test_engine_edit_validates_then_updates_identity_and_dirty_state(self):
        page = EnginePage(self.context)
        original = identity(self.context.engine())
        page.controls["reference_rpm"].setValue(3200)
        page.controls["bore_mm"].setValue(58)
        page.comb["combustion_efficiency"].setValue(.71)
        page.comb["ignition_timing_deg"].setValue(112)
        page.comb["duration_deg"].setValue(38)
        page.comb["shape_a"].setValue(5.5)
        page.comb["shape_m"].setValue(1.4)
        page.apply()
        self.assertNotEqual(identity(self.context.engine()), original)
        self.assertTrue(self.context.dirty)
        self.assertIn("Validación correcta", page.validation.text())
        effective=resolve_for_operating_point(self.context.engine())
        self.assertEqual(effective["native_configuration"]["reference_rpm"],3200)
        self.assertEqual(effective["native_configuration"]["slider_crank"]["crankcase"]["bore_mm"],58)
        self.assertEqual(effective["native_configuration"]["fuel_coupled_combustion"]["combustion_efficiency"],.71)
        from motorsim.engine_configuration import validate
        native=validate(self.context.engine())
        self.assertEqual(native.slider_crank.crankcase.bore_mm,58)
        self.assertEqual(native.fuel_coupled_combustion.ignition_timing_deg,112)
        self.assertEqual(native.fuel_coupled_combustion.components[0].duration_deg,38)
        self.assertEqual(native.fuel_coupled_combustion.components[0].shape_a,5.5)
        self.assertEqual(native.fuel_coupled_combustion.components[0].shape_m,1.4)
        before = identity(self.context.engine())
        editable_row = next(i for i in range(page.ports.rowCount())
                            if page.ports.item(i, 3).flags() & Qt.ItemFlag.ItemIsEditable)
        page.ports.item(editable_row, 3).setText("0")
        page.apply()
        self.assertEqual(identity(self.context.engine()), before)
        self.assertIn("rechazada", page.validation.text().lower())

    def test_mechanical_loss_terms_are_explicit_editable_and_validated(self):
        page = EnginePage(self.context)
        original = identity(self.context.engine())
        item = page.losses.item(0, 2)
        item.setText("1250")
        page.apply()
        self.assertNotEqual(identity(self.context.engine()), original)
        self.assertEqual(self.context.engine()["mechanical_loss_model"]["terms"][0]["mep_pa"], 1250)
        self.assertIn("SYNTHETIC_ASSUMPTION", page.losses.item(0, 3).text())
        new_identity = identity(self.context.engine())
        page.losses.item(0, 2).setText("-1")
        page.apply()
        self.assertEqual(identity(self.context.engine()), new_identity)
        self.assertIn("rechazada", page.validation.text().lower())

    def test_mechanical_loss_operating_map_has_visual_grid_editor(self):
        source=self.context.engine();model=deepcopy(source["mechanical_loss_model"])
        term=model["terms"][0];term["mep_pa"]=None
        term["operating_map"]={"rpm":[1000,5000],"load":[0.0,1.0],"values_pa":[[800,900],[1500,1700]]}
        mapped=create(native_configuration=source["native_configuration"],mechanical_loss_model=model,
                      operating_conditions=source["operating_conditions"],provenance=source["provenance"],
                      display_name=source["display_name"])
        self.context.replace_project(create_project("map-ui-test",mapped))
        page=EnginePage(self.context)
        self.assertIn("Mapa 2×2",page.losses.item(0,2).text())
        self.assertTrue(page.controls["load"].isEnabled())
        self.assertFalse(page.controls["afr"].isEnabled())
        page.controls["load"].setValue(.5)
        def edit_dialog():
            dialog=APP.activeModalWidget();grid=dialog.findChild(QTableWidget)
            grid.item(0,1).setText("850");dialog.accept()
        QTimer.singleShot(0,edit_dialog)
        page._edit_loss_map(0,2)
        page.apply()
        self.assertEqual(self.context.engine()["mechanical_loss_model"]["terms"][0]["operating_map"]["values_pa"][0][0],850)
        self.assertEqual(self.context.engine()["operating_conditions"]["load"],.5)

    def test_fixed_loss_load_and_declared_afr_are_not_presented_as_solver_controls(self):
        page=EnginePage(self.context)
        self.assertFalse(page.controls["load"].isEnabled())
        self.assertIn("no controla mariposa",page.controls["load"].toolTip())
        self.assertFalse(page.controls["afr"].isEnabled())
        self.assertIn("no modifica el solver",page.controls["afr"].toolTip())
        self.assertTrue(any("AFR guardado como metadata" in label.text() for label in page.findChildren(QLabel)))
        self.assertTrue(all(control.isEnabled() for control in page.comb.values()))
        self.assertIn("supuestos sintéticos",page.combustion_notice.text())

    def test_project_save_open_and_variant_edit_preserve_base(self):
        page = ProjectPage(self.context)
        base_hash = identity(self.context.project["base_engine"])
        with patch("motorsim.desktop.project_page.QInputDialog.getText", return_value=("Variante 1", True)):
            page.make_variant()
        self.assertEqual(identity(self.context.project["base_engine"]), base_hash)
        self.assertTrue(self.context.dirty)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "fixture.dino2t.json"
            save_project(path, self.context.project)
            loaded = load_project(path)
            self.assertIn("Variante 1", loaded["variants"])
            self.assertEqual(loaded["base_identity_sha256"], base_hash)
            self.assertFalse(any(k in path.read_text(encoding="utf-8") for k in ("cycle_primaries", "checkpoint_payload")))

    def test_exhaust_edit_changes_variant_using_backend_and_keeps_base(self):
        page = ExhaustPage(self.context)
        base_hash = identity(self.context.engine())
        first = float(page.table.item(0, 1).text())
        page.table.item(0, 1).setText(str(first + 1.0))
        page.mesh_table.cellWidget(0, 1).setCurrentText("2")
        page.apply(name="Escape 1")
        self.assertEqual(identity(self.context.project["base_engine"]), base_hash)
        self.assertEqual(self.context.selected_variant, "Escape 1")
        self.assertNotEqual(identity(self.context.engine()), base_hash)
        native=self.context.engine()["native_configuration"]
        mesh_meta=native["geometry_identity"]["exhaust_mesh_discretization"]
        self.assertEqual(mesh_meta["cells_per_section"][0],2)
        self.assertEqual(len(next(d for d in native["ducts"] if d["id"]=="exhaust")["mesh"]["volumes"]),6)
        self.assertIn("guardada", page.diff.text().lower())

    def test_custom_engine_intake_transfer_reeds_persist_and_reach_solver(self):
        context=DesktopContext(new_design_project("custom-engine"))
        page=EnginePage(context)
        self.assertEqual(page.ducts.rowCount(),4)
        self.assertEqual(page.reeds.rowCount(),6)
        self.assertIsNotNone(page.findChild(QTableWidget,"effectiveStaticReedParameters"))
        # Dynamic-only reed parameters are deliberately absent from the editor.
        self.assertNotIn("mass_kg",[page.reeds.horizontalHeaderItem(i).text() for i in range(page.reeds.columnCount())])
        intake_row=next(i for i in range(page.ducts.rowCount()) if page.ducts.item(i,0).text()=="intake")
        primary_row=next(i for i in range(page.ducts.rowCount()) if page.ducts.item(i,0).text()=="primary")
        page.ducts.item(intake_row,2).setText("95")
        page.ducts.item(intake_row,3).setText("42")
        page.ducts.item(primary_row,2).setText("62")
        page.reeds.item(0,1).setText("9.2")
        page.mixed_outflow.setValue(.63)
        page.apply()
        engine=context.engine();effective=resolve_for_operating_point(engine);native=effective["native_configuration"]
        self.assertIn("Validación correcta",page.validation.text())
        intake=next(d for d in native["ducts"] if d["id"]=="intake")
        primary=next(d for d in native["ducts"] if d["id"]=="primary")
        self.assertAlmostEqual(intake["mesh"]["faces"][-1]*1000,95)
        self.assertAlmostEqual((4*intake["mesh"]["areas"][0]/3.141592653589793)**.5*1000,42)
        self.assertAlmostEqual(primary["mesh"]["faces"][-1]*1000,62)
        self.assertAlmostEqual(native["reed_petals"][0]["pressure_area_m2"]*1e4,9.2)
        self.assertEqual(native["geometry_identity"]["gas_exchange_model"]["mixed_outflow_fraction"],.63)
        from motorsim.integrated_2t import IntegratedEngine2T
        solver=IntegratedEngine2T.from_configuration_dict(native)
        solver_intake=next(path for path in solver.ducts if path.id=="intake")
        self.assertAlmostEqual(solver_intake.mesh.faces[-1]*1000,95)
        self.assertAlmostEqual(solver.reed_petals[0].pressure_area_m2*1e4,9.2)
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"custom.dino2t.json";save_project(path,context.project)
            reopened=DesktopContext(load_project(path))
            self.assertAlmostEqual(resolve_for_operating_point(reopened.engine())["native_configuration"]["ducts"][0]["mesh"]["faces"][-1]*1000,95)
            reopened.duplicate_variant(None,"escape-var")
            exhaust=ExhaustPage(reopened);original=float(exhaust.table.item(0,1).text())
            exhaust.table.item(0,1).setText(str(original+3));self.assertTrue(exhaust.save_current())
            self.assertNotEqual(identity(reopened.engine("escape-var")),identity(reopened.project["base_engine"]))
            save_project(path,reopened.project)
            roundtrip=load_project(path)
            self.assertAlmostEqual(roundtrip["variants"]["escape-var"]["native_configuration"]["ducts"][-1]["mesh"]["faces"][-1],
                                   reopened.engine("escape-var")["native_configuration"]["ducts"][-1]["mesh"]["faces"][-1])

    def test_desktop_imports_measured_dynodata_persists_and_compares_exact_rpm(self):
        context=DesktopContext(new_project("measurement-ui"))
        with tempfile.TemporaryDirectory() as tmp:
            project_path=Path(tmp)/"measurement-ui.dino2t.json";save_project(project_path,context.project);context.path=project_path
            csv_path=Path(tmp)/"dyno.csv";csv_path.write_text("rpm,value,uncertainty\n5000,12.5,0.4\n6000,15,0.5\n",encoding="utf-8")
            page=ResultsPage(context)
            with patch("motorsim.desktop.results_page.QFileDialog.getOpenFileName",return_value=(str(csv_path),"CSV (*.csv)")), \
                 patch.object(QDialog,"exec",return_value=QDialog.DialogCode.Accepted):
                self.assertTrue(page.import_measurement())
            self.assertEqual(len(context.project["measurement_references"]),1)
            reference=context.project["measurement_references"][0]
            self.assertEqual(reference["classification"],"UNKNOWN")
            page.dataset={"points":[
                {"variant_id":"base","rpm":5000,"brake_power_status":"DEFINED","brake_power":12.0,"run_id":"run-1"},
                {"variant_id":"base","rpm":7000,"brake_power_status":"DEFINED","brake_power":16.0,"run_id":"run-1"}]}
            page.compare_measurement()
            self.assertEqual(page.measurement_table.rowCount(),2)
            self.assertEqual(page.measurement_table.item(0,0).text(),"5000")
            self.assertEqual(page.measurement_table.item(0,3).text(),"12000")
            self.assertEqual(page.measurement_table.item(1,3).text(),"—")
            self.assertIn("sin interpolación",page.measurement_notice.text().lower())
            contrast_path=Path(tmp)/"contrast.csv"
            with patch("motorsim.desktop.results_page.QFileDialog.getSaveFileName",return_value=(str(contrast_path),"CSV (*.csv)")):
                self.assertTrue(page.export_measurement_comparison())
            self.assertIn("run-1",contrast_path.read_text(encoding="utf-8-sig"))
            pressure_path=Path(tmp)/"pressure.csv";pressure_path.write_text("cycle,crank_angle_deg,value,uncertainty\n1,0,100000,1000\n1,360,110000,1000\n",encoding="utf-8")
            def accept_pressure(dialog):
                choices=dialog.findChildren(QComboBox)
                choices[0].setCurrentIndex(choices[0].findData("pressure_trace"))
                choices[1].setCurrentText("Pa")
                return QDialog.DialogCode.Accepted
            with patch("motorsim.desktop.results_page.QFileDialog.getOpenFileName",return_value=(str(pressure_path),"CSV (*.csv)")), \
                 patch.object(QDialog,"exec",new=accept_pressure):
                self.assertTrue(page.import_measurement())
            page.dataset["traces"]=[{"variant_id":"base","rpm":5000,"run_id":"run-1","cycle":1,
                "angles_deg":[0.0,360.0],"channels":{"cylinder_pressure_pa":{"values":[101000,111000]}}}]
            page.trace_rpm.clear();page.trace_rpm.addItem("5000 RPM",5000)
            page.measurement_selector.setCurrentIndex(1);page.compare_measurement()
            self.assertEqual(page.measurement_table.rowCount(),2)
            self.assertEqual(page.measurement_table.item(0,0).text(),"(1, 0.0)")
            self.assertEqual(page.measurement_table.item(0,3).text(),"101000")
            self.assertEqual(page.measurement_plot.series[0]["x_key"],"angle_deg")
            save_project(project_path,context.project)
            reopened=DesktopContext(load_project(project_path))
            reopened_page=ResultsPage(reopened)
            self.assertEqual(len(reopened_page.measurement_datasets),2)
            self.assertEqual(reopened_page.measurement_datasets[0]["metadata"]["provenance"],"UNKNOWN")

    def test_legacy_project_v1_migrates_without_changing_engine(self):
        project=new_project("legacy-v1");engine_hash=identity(project["base_engine"])
        legacy=deepcopy(project);legacy["schema"]="MOTORSIM_ENGINE_PROJECT_V1";legacy.pop("measurement_references")
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"legacy.dino2t.json";path.write_text(json.dumps(legacy),encoding="utf-8")
            loaded=load_project(path)
        self.assertEqual(loaded["schema"],"MOTORSIM_ENGINE_PROJECT_V2")
        self.assertEqual(loaded["measurement_references"],[])
        self.assertEqual(identity(loaded["base_engine"]),engine_hash)

    def test_real_impl2_import_keeps_invalid_points_as_gaps_and_exports_plot(self):
        report=impl2_historical_report_candidate()
        if not report.is_file():self.skipTest("external IMPL2 artifact root is not configured")
        data = load_results(report)
        self.assertEqual(len(data["points"]), 30)
        invalid = [p for p in data["points"] if p["classification"] == "NUMERICAL_INVALID"]
        self.assertEqual(len(invalid), 3)
        self.assertTrue(all(p["brake_power"] is None for p in invalid))
        page = ResultsPage(self.context)
        self.assertIsNone(page.dataset)
        page.load(report,historical=True)
        self.assertTrue(spin_until(lambda: page.dataset is not None))
        self.assertEqual(page.source_kind,"HISTORICAL_IMPL2")
        self.assertIn("EVIDENCIA HISTÓRICA IMPL2",page.source_notice.text())
        self.assertEqual(len(page.dataset["points"]), 30)
        self.assertTrue(any(p["value"] is None for s in page.plot.series for p in s["points"]))
        self.assertTrue(any(p["value"] < 0 for s in page.plot.series for p in s["points"] if p["value"] is not None))
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "curve.png"
            page.plot.resize(800, 400)
            page.plot.grab().save(str(target), "PNG")
            self.assertGreater(target.stat().st_size, 1000)
            target_csv = Path(tmp) / "results.csv"
            with patch("motorsim.desktop.results_page.QFileDialog.getSaveFileName", return_value=(str(target_csv), "CSV")):
                page.export_csv()
            self.assertTrue(target_csv.is_file())
            self.assertEqual(sum(1 for line in target_csv.open(encoding="utf-8-sig")) - 1, 30)

    def test_exploratory_results_keep_classification_periodicity_and_audit_separate(self):
        page=ResultsPage(self.context)
        point={"variant_id":"test / base","rpm":3000,
            "classification":"EXPLORATORY_COMPLETE_PERIODICITY_NOT_IDENTIFIED",
            "periodicity":"NOT_EVALUATED","audit_status":"PASS",
            "audit_recomputed":True,"cycles_completed":1,"BMEP":None,
            "BMEP_status":"UNDEFINED","hard_gates":{"status":"NOT_EVALUATED_EXPLORATORY"},
            "mode":"EXPLORATORY","experimental_validation":"NOT_CLAIMED",
            "conservation":{"mass_residual_kg":0.0}}
        page._loaded_exploratory({"schema":"DINO_EXPLORATORY_COMPARISON_V1",
            "points":[point],"traces":[{"variant_id":"test / base","rpm":3000,
                "cycle":1,"angles_deg":[0,360],"channels":{
                    "duct:exhaust:cell:1:pressure_pa":{"unit":"Pa","values":[1e5,1.1e5]}}}],
            "experimental_validation":"NOT_CLAIMED","provenance":"EXPLORATORY"})
        row=page.point_table.item(0,0).data(Qt.ItemDataRole.UserRole)
        self.assertEqual(row["classification"],"EXPLORATORY_COMPLETE_PERIODICITY_NOT_IDENTIFIED")
        self.assertEqual(row["periodicity"],"NOT_EVALUATED")
        self.assertEqual(row["audit_status"],"PASS")
        self.assertFalse(page.trace_group.isHidden())
        series=page.trace_plot.series[0]
        self.assertEqual(series["x_key"],"angle_deg")
        self.assertEqual(series["points"][1]["angle_deg"],360)
        page.show_point({"point":row})
        details={page.details.item(i,0).text():page.details.item(i,1).text()
                 for i in range(page.details.rowCount())}
        self.assertEqual(details["Periodicidad"],"NOT_EVALUATED")
        self.assertEqual(details["Auditoría primaria"],"PASS")
        self.assertEqual(details["Validación experimental"],"NOT_CLAIMED")

    def test_execution_request_never_starts_and_is_atomic(self):
        page = ExecutionPage(self.context)
        page.refresh()
        self.assertTrue(page.start.isEnabled())
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "request.json"
            with patch("motorsim.desktop.execution_page.QFileDialog.getSaveFileName", return_value=(str(target), "JSON")), \
                 patch("motorsim.desktop.execution_page.QMessageBox.information"):
                page.save_request()
            request = json.loads(target.read_text(encoding="utf-8"))
            self.assertFalse(request["preregistration_match"])
            self.assertFalse(request["authorization_match"])
            self.assertFalse(request["execution_started"])
            self.assertFalse(list(Path(tmp).glob("*.tmp")))

    def test_exploratory_run_requires_explicit_confirmation(self):
        page=ExecutionPage(self.context)
        with patch.object(page,"_confirm_run",return_value=False), \
             patch("motorsim.desktop.execution_page.run_background") as launch:
            page.start_run(resume=False)
        launch.assert_not_called()

    def test_async_boundary_returns_data_and_errors_without_ui_shutdown(self):
        completed, errors = [], []
        run_background(lambda: {"ok": True}, on_done=completed.append, on_error=errors.append)
        self.assertTrue(spin_until(lambda: bool(completed or errors)))
        self.assertEqual(completed, [{"ok": True}])
        self.assertEqual(errors, [])
        run_background(lambda: (_ for _ in ()).throw(ValueError("fixture error")), on_error=errors.append)
        self.assertTrue(spin_until(lambda: bool(errors)))
        self.assertIn("fixture error", errors[0])

    def test_project_io_errors_are_reported_and_leave_context_intact(self):
        window = DinoDesktopWindow(new_project("io-test"))
        before = identity(window.context.engine())
        with patch("motorsim.desktop.app.QMessageBox.warning") as warning:
            window._open(Path("missing-dino-project.json"))
            self.assertTrue(warning.called)
        self.assertEqual(identity(window.context.engine()), before)
        window.close()


if __name__ == "__main__":
    unittest.main()
