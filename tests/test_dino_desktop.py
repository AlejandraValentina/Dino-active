"""Functional UI tests; all engine data are synthetic or historical read-only artifacts."""
from __future__ import annotations

import json
import hashlib
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
from motorsim.desktop.new_engine_dialog import NewEngineDialog
from motorsim.desktop.project_page import ProjectPage
from motorsim.desktop.results_page import ResultsPage
from motorsim.desktop.preferences import default_artifact_root,impl2_historical_report_candidate,set_artifact_root
from motorsim.desktop.services import load_results, new_project, new_design_project, run_background,run_parallel_curve_points
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
        self.assertEqual(window.mode_stack.count(), 3)
        self.assertEqual(window.component_stack.count(), 3)
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

    def test_main_navigation_reaches_existing_intake_transfer_and_reed_editor(self):
        window=DinoDesktopWindow(self.context.project);window.show();APP.processEvents()
        nav=window.component_nav
        QTest.mouseClick(nav,Qt.MouseButton.LeftButton,pos=nav.tabRect(6).center())
        APP.processEvents()
        self.assertEqual(window.pages[0].component_tabs.currentIndex(),4)
        self.assertTrue(window.pages[0].ducts.isVisible())
        self.assertTrue(window.pages[0].reeds.isVisible())
        editor=window.pages[0]
        editor.reeds.item(0,1).setText('not numeric');editor.apply()
        self.assertIn('✕',nav.tabText(6))
        editor.refresh();APP.processEvents()
        self.assertNotIn('✕',nav.tabText(6))
        window.context.dirty=False;window.close()

    def test_design_workbench_modes_reuse_editors_and_keep_traceability_accessible(self):
        window=DinoDesktopWindow(self.context.project);window.resize(964,641);window.show();APP.processEvents()
        original=identity(window.context.engine())
        QTest.mouseClick(window.simulate_mode,Qt.MouseButton.LeftButton);APP.processEvents()
        self.assertEqual(window.mode_stack.currentIndex(),2)
        self.assertTrue(window.pages[3].isVisible())
        self.assertFalse(window.execution_dialog.isVisible())
        QTest.mouseClick(window.analysis_mode,Qt.MouseButton.LeftButton);APP.processEvents()
        self.assertEqual(window.results.result_tabs.tabText(0),'Curvas')
        self.assertTrue(window.results.power_curves.isVisible())
        self.assertFalse(window.results.path_label.isVisible())
        self.assertFalse(window.results.measurement_plot.isVisible())
        window.results.dataset={'points':[{'classification':'MAX_CYCLES_NONCONVERGED'}]}
        window.results._dataset_summary()
        self.assertIn('no convergida',window.results.run_summary.text())
        self.assertNotIn('Sin una corrida seleccionada',window.results.run_summary.text())
        window.results.result_tabs.setCurrentIndex(5);APP.processEvents()
        self.assertTrue(window.results.path_label.isVisible())
        self.assertTrue(window.menuBar().isVisible())
        window.explorer_button.click();APP.processEvents()
        self.assertTrue(window.analysis_history.isVisible())
        window.explorer_tabs.setCurrentIndex(1);APP.processEvents()
        self.assertTrue(window.project_tree.isVisible())
        self.assertEqual(identity(window.context.engine()),original)
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

    def test_advanced_exhaust_mesh_collapses_and_expands_without_changing_counts(self):
        page=ExhaustPage(self.context)
        counts=page._resolutions()
        self.assertTrue(page.mesh_table.isHidden())
        page.mesh_group.setChecked(True);page.set_compact_layout(True)
        self.assertFalse(page.mesh_table.isHidden())
        self.assertGreater(page.mesh_group.maximumHeight(),180)
        page.mesh_group.setChecked(False)
        self.assertTrue(page.mesh_table.isHidden())
        self.assertEqual(page._resolutions(),counts)

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

    def test_desktop_synthetic_custom_engine_ab_roundtrip_one_cycle(self):
        """Exercise visible project creation through solver results and reopen."""
        from PySide6.QtWidgets import QInputDialog, QSpinBox

        with tempfile.TemporaryDirectory() as tmp:
            set_artifact_root(Path(tmp)/"history-artifacts")
            evidence_root=Path(os.environ["DINO_DESKTOP_CUSTOM_ENGINE_E2E_ROOT"]) if os.environ.get("DINO_DESKTOP_CUSTOM_ENGINE_E2E_ROOT") else None
            if evidence_root is not None:
                existing=set(child.name for child in evidence_root.iterdir()) if evidence_root.exists() else set()
                self.assertLessEqual(existing,{"logs"},"refusing to overwrite existing E2E evidence")
                self.assertFalse((evidence_root/"synthetic-user-engine.dino2t.json").exists(),"refusing to overwrite existing project")
                self.assertFalse((evidence_root/"receipt.json").exists(),"refusing to overwrite existing receipt")
                from motorsim.storage_preflight import check_storage_requirements
                check_storage_requirements([(evidence_root,512*1024**2)])
            output_root=evidence_root or Path(tmp)
            project_path=output_root/"synthetic-user-engine.dino2t.json"
            artifacts_root=(default_artifact_root()/"dino-desktop-custom-engine-e2e-20261029-v5"
                            if evidence_root is not None else Path(tmp)/"artifacts")
            if evidence_root is not None:
                self.assertFalse(artifacts_root.exists(),"refusing to overwrite existing external E2E artifacts")
                from motorsim.storage_preflight import check_storage_requirements
                check_storage_requirements([(evidence_root,512*1024**2),(artifacts_root,512*1024**2)])
            window=DinoDesktopWindow(new_project("desktop-shell"))
            dialog=NewEngineDialog(window)
            dialog.project_name.setText("synthetic-user-engine")
            dialog.engine_name.setText("Synthetic 2T - E2E")
            dialog.inputs["bore_mm"].setValue(56.5)
            dialog.inputs["stroke_mm"].setValue(50.6)
            dialog.inputs["volume_bdc_cm3"].setValue(360.0)
            dialog.intake.setCurrentIndex(dialog.intake.findData("reed"))
            dialog._create()
            self.assertIsNotNone(dialog.project)
            with patch("motorsim.desktop.app.NewEngineDialog",return_value=dialog), \
                 patch.object(dialog,"exec",return_value=QDialog.DialogCode.Accepted):
                window.new_file()

            engine_page=window.pages[0]
            engine_page.controls["bore_mm"].setValue(57.0)
            engine_page.controls["volume_bdc_cm3"].setValue(365.0)
            transfer_row=next(i for i in range(engine_page.ports.rowCount())
                if engine_page.ports.item(i,1).text().lower()=="transfer")
            old_port_height=float(engine_page.ports.item(transfer_row,3).text())
            engine_page.ports.item(transfer_row,3).setText(str(old_port_height+0.5))
            intake_row=next(i for i in range(engine_page.ducts.rowCount())
                if engine_page.ducts.item(i,0).text()=="intake")
            transfer_duct_row=next(i for i in range(engine_page.ducts.rowCount())
                if engine_page.ducts.item(i,0).text()=="primary")
            engine_page.ducts.item(intake_row,2).setText("96")
            engine_page.ducts.item(intake_row,3).setText("43")
            engine_page.ducts.item(transfer_duct_row,2).setText("63")
            engine_page.reeds.item(0,1).setText("9.1")
            engine_page.mixed_outflow.setValue(.61)
            engine_page.apply()
            self.assertIn("Validación correcta",engine_page.validation.text())
            base_identity=identity(window.context.project["base_engine"])
            self.assertEqual(window.context.project["scientific_validation_status"],"SYNTHETIC_UNVALIDATED")
            self.assertEqual(window.context.project["base_engine"]["provenance"]["design_inputs"]["port_dimensions"]["classification"],"SYNTHETIC_ASSUMPTION")
            self.assertEqual(window.context.project["base_engine"]["provenance"]["design_inputs"]["bore_mm"]["classification"],"UNKNOWN")
            with patch("motorsim.desktop.app.QFileDialog.getSaveFileName",return_value=(str(project_path),"Dino 2T (*.dino2t.json)")):
                self.assertTrue(window.save_as())
            self.assertTrue(window.close())

            reopened=DinoDesktopWindow(new_project("desktop-reopen-shell"))
            reopened._open(project_path)
            self.assertEqual(identity(reopened.context.project["base_engine"]),base_identity)
            effective=resolve_for_operating_point(reopened.context.engine())
            native=effective["native_configuration"]
            solver_engine=__import__("motorsim.integrated_2t",fromlist=["IntegratedEngine2T"]).IntegratedEngine2T.from_configuration_dict(native)
            self.assertEqual(solver_engine.slider_crank.crankcase.bore_mm,57.0)
            self.assertAlmostEqual(next(d for d in native["ducts"] if d["id"]=="intake")["mesh"]["faces"][-1]*1000,96.0)
            self.assertAlmostEqual(solver_engine.reed_petals[0].pressure_area_m2*1e4,9.1)

            reopened.context.select_variant(None)
            with patch("motorsim.desktop.project_page.QInputDialog.getText",return_value=("escape-candidate",True)):
                reopened.pages[2].duplicate_variant()
            reopened.context.select_variant("escape-candidate")
            exhaust_page=reopened.pages[1]
            original_diameter=float(exhaust_page.table.item(0,1).text())
            exhaust_page.table.item(0,1).setText(str(original_diameter+3.0))
            self.assertTrue(exhaust_page.save_current())
            self.assertNotEqual(identity(reopened.context.engine("escape-candidate")),base_identity)
            self.assertTrue(reopened.save_file())
            self.assertTrue(reopened.close())

            run_window=DinoDesktopWindow(new_project("desktop-run-shell"))
            run_window._open(project_path)
            run_window.context.select_variant("escape-candidate")
            execution=run_window.pages[3]
            with patch("motorsim.desktop.execution_page.QFileDialog.getExistingDirectory",return_value=str(artifacts_root)):
                execution.choose_root()
            execution.rpm.setValue(4500)
            execution.cycles.setValue(1)
            execution.budget.setValue(90)
            execution.memory.setValue(1024)

            def accept_curve(run_dialog):
                run_dialog.findChild(QSpinBox,"curveStartRpm").setValue(4500)
                run_dialog.findChild(QSpinBox,"curveStopRpm").setValue(5000)
                run_dialog.findChild(QSpinBox,"curveCycles").setValue(1)
                run_dialog.findChild(QSpinBox,"curvePointBudget").setValue(90)
                run_dialog.findChild(QSpinBox,"curveTotalBudget").setValue(180)
                run_dialog.findChild(QSpinBox,"curveMemory").setValue(1024)
                selector=run_dialog.findChild(QComboBox,"curveABParallelVariant")
                selector.setCurrentIndex(selector.findData("base"))
                return QDialog.DialogCode.Accepted

            preflight_warnings=[]
            with patch.object(QDialog,"exec",new=accept_curve), \
                 patch("motorsim.desktop.execution_page.QMessageBox.question",return_value=QMessageBox.StandardButton.Yes), \
                 patch("motorsim.desktop.execution_page.QMessageBox.warning",side_effect=lambda *args:preflight_warnings.append(args)):
                execution.start_power_curve()
            self.assertFalse(preflight_warnings,preflight_warnings)
            self.assertIsInstance(execution.active_sweep_settings,dict)
            self.assertEqual(execution.active_sweep_settings["max_cycles"],1)
            self.assertTrue(spin_until(lambda:execution.task is None,timeout_ms=60000),execution.output.toPlainText())
            self.assertIn("MAX_CYCLES_NONCONVERGED",execution.output.toPlainText())
            self.assertEqual(len(run_window.context.project["result_references"]),4)
            self.assertIn("MAX_CYCLES_NONCONVERGED",execution.output.toPlainText())
            self.assertTrue(run_window.save_file())
            self.assertTrue(spin_until(lambda:run_window.results.dataset is not None,timeout_ms=30000))
            classifications={point["classification"] for point in run_window.results.dataset["points"]}
            self.assertEqual(classifications,{"MAX_CYCLES_NONCONVERGED"})
            run_window.results.show_point(run_window.results.dataset["points"][0])
            self.assertIn("no convergida",run_window.results.run_summary.text().lower())
            self.assertNotIn("PERIOD_1",run_window.results.run_summary.text())
            self.assertIn("base vs escape-candidate",run_window.results.compare_notice.text())
            self.assertIn("TRANSITORIOS",run_window.results.compare_notice.text())
            self.assertGreater(run_window.results.compare_table.rowCount(),0)
            self.assertTrue(run_window.close())

            final_window=DinoDesktopWindow(new_project("desktop-final-shell"))
            final_window._open(project_path)
            self.assertAlmostEqual(final_window.context.engine()["native_configuration"]["slider_crank"]["crankcase"]["bore_mm"],57.0)
            self.assertIn("escape-candidate",final_window.context.project["variants"])
            self.assertEqual(len(final_window.context.project["result_references"]),4)
            self.assertEqual(final_window.context.project["scientific_validation_status"],"SYNTHETIC_UNVALIDATED")
            final_window.close()
            if evidence_root is not None:
                records=[]
                for point in run_window.results.dataset["points"]:
                    records.append({key:point.get(key) for key in (
                        "variant_id","rpm","classification","periodicity","cycles_completed",
                        "checkpoint_sha256","result_sha256","point_configuration_sha256")})
                package_spec=Path("packaging/MotorSim.spec").read_text(encoding="utf-8")
                self.assertIn("module_collection_mode={'motorsim':'py'}",package_spec)
                self.assertIn("(root/'motorsim').rglob('*.py')",package_spec)
                relative_refs=[]
                for ref in final_window.context.project["result_references"]:
                    external_relative=Path(ref["path"]).resolve().relative_to(artifacts_root.resolve()).as_posix()
                    relative_refs.append({**ref,"path":f"DINO_ARTIFACT_ROOT/{external_relative}"})
                receipt={"schema":"DINO_DESKTOP_CUSTOM_ENGINE_E2E_V1","project_file":project_path.name,
                    "project_id":final_window.context.project["project_id"],
                    "project_sha256":hashlib.sha256(project_path.read_bytes()).hexdigest(),
                    "scientific_validation_status":final_window.context.project["scientific_validation_status"],
                    "experimental_validation":"NOT_CLAIMED",
                    "base_engine_identity_sha256":identity(final_window.context.project["base_engine"]),
                    "escape_variant_identity_sha256":identity(final_window.context.project["variants"]["escape-candidate"]),
                    "result_references":relative_refs,"points":records,
                    "comparison_notice":run_window.results.compare_notice.text(),
                    "comparison_rows":run_window.results.compare_table.rowCount(),
                    "parallel_dispatch":"DINO_PARALLEL_POINT_SWEEP_V1",
                    "artifact_root":"DINO_ARTIFACT_ROOT/dino-desktop-custom-engine-e2e-20261029-v5",
                    "parallel_manifest":run_window.context.project["simulation_recipes"]["rpm_ab_parallel_v1"],
                    "cancel_error_recovery":"Covered by existing cancel event, fail-closed coordinator, hash-bound checkpoints, and per-point history resume paths; no interruption injected into the successful end-to-end run.",
                    "windows_packaging_compatibility":{"verified":"STATIC_SPEC_SOURCE_BUNDLE",
                        "source_backed_motorsim": "module_collection_mode={'motorsim':'py'}" in package_spec,
                        "recursive_motorsim_sources":"(root/'motorsim').rglob('*.py')" in package_spec,
                        "build_performed":False}}
                evidence_root.mkdir(parents=True,exist_ok=True)
                (evidence_root/"receipt.json").write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
                report=["# Desktop custom-engine A/B end-to-end proof","",
                    "Configuración enteramente sintética; no es validación experimental ni predicción respaldada.","",
                    "- Alta desde el diálogo Crear motor; cambios en cilindro, cárter, lumbreras, admisión, transferencia y láminas aplicados y resueltos por el solver.",
                    "- Proyecto guardado, ventana cerrada y proyecto reabierto; identidad de motor preservada.",
                    "- Variante duplicada desde Proyecto; geometría de escape editada, guardada y reabierta.",
                    "- Curva A/B paralela desde Desktop en 4500 y 5000 rpm, un ciclo por punto; artifacts ligados por hash al proyecto.",
                    "- Los cuatro puntos se muestran como MAX_CYCLES_NONCONVERGED; la comparación advierte TRANSITORIOS y no declara una mejora definitiva.",
                    "- Compatibilidad Windows verificada leyendo el spec de PyInstaller: el bundle Dino incluye fuentes `motorsim`; no se hizo build.",
                    "- La corrida de éxito no inyectó cancelación. Cancelación, fallos y recuperación individual conservan las rutas ya existentes y quedan listados en el recibo.","",
                    "Ver métricas, hashes y referencias en `receipt.json`.",""]
                (evidence_root/"report.md").write_text("\n".join(report),encoding="utf-8")

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

    def test_execution_page_dispatches_ab_curve_as_independent_rpm_workers(self):
        project=load_project(Path("configs/reference_cases/functional_exhaust_ab_125cc_v1.dino.json"))
        context=DesktopContext(project);context.select_variant("A_original")
        page=ExecutionPage(context)
        calls={}
        def accept_ab(dialog):
            choice=dialog.findChild(QComboBox,"curveABParallelVariant")
            choice.setCurrentIndex(choice.findData("B_header_plus20"))
            return QDialog.DialogCode.Accepted
        def prepare(document,**kwargs):
            from motorsim.engine_configuration import identity as engine_identity
            return {"identity_sha256":engine_identity(document),"point_preflights":[{"identity_sha256":engine_identity(document)} for _ in range(7)]}
        def dispatch(function,*args,**kwargs):
            calls.update(function=function,args=args,kwargs=kwargs);return object()
        with tempfile.TemporaryDirectory() as tmp, \
             patch.object(QDialog,"exec",new=accept_ab), \
             patch("motorsim.power_curve_sweep.prepare_power_curve",side_effect=prepare), \
             patch("motorsim.power_curve_sweep._reused_points",return_value=[]), \
             patch("motorsim.storage_preflight.check_storage_requirements",return_value={"status":"PASS"}), \
             patch("motorsim.desktop.execution_page.run_background",side_effect=dispatch), \
             patch("motorsim.desktop.execution_page.QMessageBox.question",return_value=QMessageBox.StandardButton.Yes):
            page.artifact_root=Path(tmp)
            page.start_power_curve()
        self.assertEqual(calls["function"].__name__,"run_parallel_curve_points")
        specs=calls["args"][0]
        self.assertEqual(len(specs),14)
        self.assertEqual({spec["variant_label"] for spec in specs},{"A_original","B_header_plus20"})
        self.assertEqual({spec["rpm"] for spec in specs},{3000,3500,4000,4500,5000,5500,6000})
        self.assertEqual(len({spec["run_id"] for spec in specs}),len(specs))
        self.assertGreaterEqual(calls["kwargs"]["max_workers"],2)
        self.assertEqual(context.project["simulation_recipes"]["rpm_ab_parallel_v1"]["workers"],calls["kwargs"]["max_workers"])

    def test_parallel_curve_point_coordinator_persists_each_solver_run_and_checkpoint(self):
        project=load_project(Path("configs/reference_cases/functional_exhaust_ab_125cc_v1.dino.json"))
        with tempfile.TemporaryDirectory() as tmp:
            specs=[]
            for label,engine in (("A_original",project["variants"]["A_original"]),
                                 ("B_header_plus20",project["variants"]["B_header_plus20"])):
                specs.append({"document":engine,"project_id":project["project_id"],"variant_label":label,
                    "rpm":5000,"artifact_root":tmp,"run_id":f"parallel-check-{label}",
                    "max_cycles":1,"point_budget_seconds":60,"memory_limit_mib":1024,
                    "identity_sha256":identity(engine)})
            result=run_parallel_curve_points(specs,max_workers=2,total_budget_seconds=60)
            self.assertEqual(result["status"],"COMPLETE")
            self.assertEqual(len(result["points"]),2)
            for point in result["points"]:
                self.assertEqual(point["cycles_completed"],1)
                self.assertEqual(point["status"],"COMPLETE")
                self.assertTrue(point["checkpoint_sha256"])
                self.assertTrue(Path(point["run_directory"],"checkpoint.json").is_file())
            manifest=json.loads(Path(result["parallel_manifest"]).read_text(encoding="utf-8"))
            self.assertEqual(manifest["schema"],"DINO_PARALLEL_POINT_SWEEP_V1")
            self.assertEqual(manifest["status"],"COMPLETE")

    def test_parallel_curve_point_cancel_and_fail_closed_states_are_durable(self):
        import threading
        project=load_project(Path("configs/reference_cases/functional_exhaust_ab_125cc_v1.dino.json"))
        with tempfile.TemporaryDirectory() as tmp:
            specs=[]
            for label,engine in (("A_original",project["variants"]["A_original"]),
                                 ("B_header_plus20",project["variants"]["B_header_plus20"])):
                specs.append({"document":engine,"project_id":project["project_id"],"variant_label":label,
                    "rpm":5000,"artifact_root":tmp,"run_id":f"cancel-check-{label}",
                    "max_cycles":1,"point_budget_seconds":30,"memory_limit_mib":1024,
                    "identity_sha256":identity(engine)})
            cancelled=threading.Event();cancelled.set()
            partial=run_parallel_curve_points(specs,max_workers=2,total_budget_seconds=30,cancel_event=cancelled)
            self.assertEqual(partial["status"],"PARTIAL")
            self.assertTrue(all(point["status"]=="INTERRUPTED_CHECKPOINTED" for point in partial["points"]))
            partial_manifest=json.loads(Path(partial["parallel_manifest"]).read_text(encoding="utf-8"))
            self.assertEqual(partial_manifest["status"],"PARTIAL")

            broken=[{**spec,"run_id":f"broken-{i}","document":{}} for i,spec in enumerate(specs)]
            with self.assertRaises(Exception):run_parallel_curve_points(broken,max_workers=2,total_budget_seconds=30)
            manifests=list((Path(tmp)/"dino-parallel-point-sweep-v1"/project["project_id"]).glob("*/dispatch.json"))
            failed=json.loads(max(manifests,key=lambda path:path.stat().st_mtime).read_text(encoding="utf-8"))
            self.assertEqual(failed["status"],"FAILED")
            self.assertIn("failure",failed)

    def test_history_resume_reuses_the_existing_guarded_single_point_recovery(self):
        project=load_project(Path("configs/reference_cases/functional_exhaust_ab_125cc_v1.dino.json"))
        context=DesktopContext(project);context.select_variant("A_original")
        page=ExecutionPage(context)
        point_identity=resolve_for_operating_point(context.engine(),rpm=5000)["identity_sha256"]
        with tempfile.TemporaryDirectory() as tmp,patch.object(page,"start_run") as start:
            page.resume_from_entry({"identity_sha256":point_identity,"artifact_root":tmp,
                "run_id":"cancel-check-A_original","rpm":5000,"details":{"cycles_requested":1}})
        start.assert_called_once_with(resume=True)
        self.assertEqual(page.run_id.text(),"cancel-check-A_original")

    def test_historical_csv_roundtrip_preserves_states_units_and_rejects_tampering(self):
        from motorsim.engine_results import SERIES
        row={"point_id":"synthetic-invalid","variant_id":"base","rpm":3000,
             "classification":"NUMERICAL_INVALID","result_sha256":"a"*64,
             "point_configuration_sha256":"b"*64}
        for field,_ in SERIES.values():
            row[field]=None;row[field+"_status"]="UNDEFINED"
        dataset={"schema":"MOTORSIM_IMPORTED_CURVE_DATASET_V1",
                 "identity":{key:"c"*64 for key in (
                     "implementation_identity_sha256","preregistration_sha256","producer_sha256")},
                 "units":dict(SERIES.values()),"points":[row]}
        page=ResultsPage(self.context);page.dataset=dataset
        with tempfile.TemporaryDirectory() as tmp:
            csv_path=Path(tmp)/"export.csv"
            with patch("motorsim.desktop.results_page.QFileDialog.getSaveFileName",return_value=(str(csv_path),"CSV")):
                page.export_csv()
            restored=load_results(csv_path)
            self.assertEqual(restored['points'],dataset['points'])
            self.assertEqual(restored['units'],dataset['units'])
            self.assertEqual(restored['identity'],dataset['identity'])
            reopened=ResultsPage(self.context);reopened.load(csv_path)
            self.assertTrue(spin_until(lambda: reopened.dataset is not None))
            self.assertEqual(reopened.source_kind,'HISTORICAL_IMPL2')
            self.assertEqual(reopened.dataset['points'],dataset['points'])
            before=csv_path.read_bytes()
            with patch("motorsim.desktop.results_page.QFileDialog.getSaveFileName",return_value=(str(csv_path),"CSV")),patch("motorsim.desktop.results_page.QMessageBox.warning") as warning:
                page.export_csv();warning.assert_called_once()
            self.assertEqual(csv_path.read_bytes(),before)
            csv_path.write_bytes(before+b'\n')
            with self.assertRaisesRegex(ValueError,'hash mismatch'):
                load_results(csv_path)

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

    def test_ab_comparison_labels_max_cycles_as_transient_not_confirmed_gain(self):
        self.context.duplicate_variant(None,"escape-candidate")
        page=ResultsPage(self.context)
        points=[]
        for variant in ("base","escape-candidate"):
            points.append({"variant_id":variant,"rpm":4500,
                "classification":"MAX_CYCLES_NONCONVERGED","periodicity":"INSUFFICIENT_CYCLES",
                "cycles_completed":1,"mode":"EXPLORATORY","experimental_validation":"NOT_CLAIMED",
                "brake_power_status":"INSUFFICIENT_CYCLES","brake_power":None,
                "brake_power_reason":"INSUFFICIENT_CYCLES","brake_torque_status":"INSUFFICIENT_CYCLES",
                "BMEP_status":"INSUFFICIENT_CYCLES","IMEP_status":"INSUFFICIENT_CYCLES",
                "FMEP_status":"INSUFFICIENT_CYCLES","transient_estimates":{"brake_power":12.0,"brake_torque":8.0}})
        page._loaded_exploratory({"schema":"DINO_EXPLORATORY_COMPARISON_V1","points":points,
            "traces":[],"experimental_validation":"NOT_CLAIMED","provenance":"EXPLORATORY"})
        self.assertIn("TRANSITORIOS",page.compare_notice.text())
        self.assertIn("no demuestra ganancia",page.compare_notice.text().lower())
        states={page.compare_table.item(row,0).text():page.compare_table.item(row,4).text()
            for row in range(page.compare_table.rowCount())}
        self.assertIn("no convergido",states["Potencia transitoria"].lower())
        self.assertEqual(page.compare_table.item(0,1).text(),"—")

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
