from __future__ import annotations

import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import unittest
from copy import deepcopy
from unittest.mock import patch
import desktop_qsettings_isolation  # noqa: F401
from PySide6.QtWidgets import QApplication, QTableWidget
from pathlib import Path

from motorsim.desktop.app import DinoDesktopWindow
from motorsim.desktop.context import DesktopContext
from motorsim.desktop.engine_page import EnginePage
from motorsim.desktop.execution_page import ExecutionPage
from motorsim.desktop.exhaust_page import ExhaustPage
from motorsim.desktop.preferences import set_artifact_root
from motorsim.desktop.results_page import DiscreteAngleCellMap, ResultsPage
from motorsim.desktop.services import new_project
from motorsim.engine_configuration import sha256

APP = QApplication.instance() or QApplication([])


class VisualParityV31Tests(unittest.TestCase):
    def test_saved_baseline_is_shared_with_escape_overlay_on_open(self):
        project=new_project("v31-baseline-sync")
        project["variants"]["Escape base guardada"]=deepcopy(project["base_engine"])
        from motorsim.desktop.preferences import settings
        settings().setValue(f"baseline_variant/{project['project_id']}","Escape base guardada")
        window=DinoDesktopWindow(project)
        self.assertEqual(window.context_bar.baseline.currentData(),"Escape base guardada")
        self.assertEqual(window.pages[1].overlay_selector.currentData(),"Escape base guardada")
        window.close()

    def test_escape_segment_outlet_is_editable_and_updates_shared_station(self):
        page = DinoDesktopWindow(new_project("v31-escape")).pages[1]
        item = page.table.item(1, 3)
        self.assertTrue(item.flags().value & 2)  # ItemIsEditable
        item.setText("53.5")
        APP.processEvents()
        self.assertEqual(page.stations.item(2, 2).text(), "53.5")
        self.assertEqual(page._rows()[1]["outlet_diameter_mm"], 53.5)
        self.assertNotIn("FAIL", page.diff.text())

    def test_escape_segment_delta_includes_length_angle_and_volume(self):
        project=new_project("v31-escape-delta")
        base=project["base_engine"]
        from motorsim.engine_variants import escape_sections,replace_escape_sections
        baseline_sections=escape_sections(base);baseline_sections[1]["length_mm"]+=20.0
        project["variants"]["Baseline con difusor largo"]=replace_escape_sections(
            base,baseline_sections,display_name="Baseline con difusor largo")
        page=ExhaustPage(DesktopContext(project))
        page.overlay_selector.setCurrentIndex(page.overlay_selector.findData("Baseline con difusor largo"))
        delta=page._section_delta(1,escape_sections(base)[1])
        self.assertIn("L -20 mm",delta)
        self.assertIn("θ",delta)
        self.assertIn("V",delta)

    def test_cylinder_and_distribution_are_in_one_engine_view(self):
        page = EnginePage(DesktopContext(new_project("v31-engine")))
        combined = page.component_tabs.widget(0)
        self.assertIsNotNone(combined.findChild(QTableWidget, "integratedPortTiming"))
        self.assertEqual(page.ports.horizontalHeaderItem(3).text(),"Alt. (mm)")
        self.assertEqual(page.ports.horizontalHeaderItem(9).text(),"Dur. (°)")
        self.assertGreater(page.ports.columnCount(), page.timing.columnCount())
        self.assertIsNotNone(combined.findChild(QTableWidget))
        self.assertIsNotNone(combined.findChild(type(page.area_plot), "portAreaAnglePlot"))
        self.assertEqual(page.controls["bore_mm"].decimals(), 2)

    def test_compact_navigation_and_prepare_panel_share_execution_state(self):
        window = DinoDesktopWindow(new_project("v31-compact"));window.resize(980,680);window.show();APP.processEvents()
        self.assertEqual(window.component_nav.shape().name, "RoundedNorth")
        self.assertEqual(window.component_nav.count(), 6)
        escape=window.pages[1]
        self.assertTrue(escape.title.isHidden())
        self.assertTrue(escape.intro.isHidden())
        self.assertEqual(escape.profile.minimumHeight(),90)
        self.assertGreaterEqual(escape.mesh_group.maximumHeight(),50)
        self.assertFalse(window.menuBar().isVisible())
        window.component_nav.setCurrentIndex(2);APP.processEvents()
        self.assertFalse(escape.diff_panel.isVisible())
        self.assertTrue(all(escape.table.rowHeight(row) == 20 for row in range(escape.table.rowCount())))
        self.assertGreaterEqual(escape.table.viewport().height(),sum(escape.table.rowHeight(row) for row in range(escape.table.rowCount())))
        rpm = window.pages[3].rpm.value()
        window.prepare_button.click();APP.processEvents()
        self.assertTrue(window.execution_dialog.isVisible())
        self.assertIs(window.pages[3].parentWidget(), window.execution_dialog_scroll.viewport())
        self.assertEqual(window.execution_dialog_tabs.count(), 2)
        self.assertIs(window.execution_dialog_tabs.widget(1), window.analysis_history)
        self.assertEqual(window.pages[3].rpm.value(), rpm)
        self.assertFalse(window.pages[3].cancel.isVisible())
        window.execution_dialog.reject();APP.processEvents()
        self.assertIs(window.pages[3].parentWidget(), window.execution_scroll.viewport())
        self.assertIs(window.analysis_history.parentWidget(), window.analysis_splitter)
        window.close()

    def test_design_has_one_horizontal_section_navigation_without_duplicate_engine_tabs(self):
        window=DinoDesktopWindow(new_project("v31-navigation"));window.resize(1360,900);window.show();APP.processEvents()
        labels=[window.component_nav.tabText(i).split(" ",1)[-1] for i in range(window.component_nav.count())]
        self.assertEqual(labels,["Cilindro y distribución","Eventos de área","Escape","Pérdidas","Combustión","Proyecto"])
        self.assertEqual(window.component_nav.shape().name,"RoundedNorth")
        self.assertTrue(window.pages[0].component_tabs.tabBar().isHidden())
        self.assertGreater(window.design_mode.width(),100)
        self.assertGreater(window.analysis_mode.x()-window.design_mode.geometry().right(),5)

        engine=window.pages[0]
        engine.controls["bore_mm"].setValue(55.25)
        window.component_nav.setCurrentIndex(1);APP.processEvents()
        self.assertEqual(engine.component_tabs.currentIndex(),1)
        window.component_nav.setCurrentIndex(3);APP.processEvents()
        self.assertEqual(engine.component_tabs.currentIndex(),2)
        window.component_nav.setCurrentIndex(4);APP.processEvents()
        self.assertEqual(engine.component_tabs.currentIndex(),3)
        window.component_nav.setCurrentIndex(0);APP.processEvents()
        self.assertEqual(engine.controls["bore_mm"].value(),55.25)
        window.component_nav.setCurrentIndex(5);APP.processEvents()
        self.assertEqual(window.component_stack.currentIndex(),2)

        window.set_workspace_mode(1)
        self.assertTrue(window.analysis_mode.isChecked());self.assertFalse(window.design_mode.isChecked())
        window.set_workspace_mode(0)
        self.assertTrue(window.design_mode.isChecked());self.assertEqual(window.component_nav.currentIndex(),5)
        window.resize(980,680);APP.processEvents()
        self.assertEqual(window.component_nav.shape().name,"RoundedNorth")
        self.assertTrue(window.component_nav.isVisible())
        window.close()

    def test_repository_artifact_roots_are_rejected_even_for_resume_compatibility(self):
        with self.assertRaisesRegex(ValueError, "no puede estar dentro del repositorio"):
            set_artifact_root(os.getcwd(), allow_repository=True)

    def test_resume_and_new_runs_fail_closed_for_repository_artifact_root(self):
        page=ExecutionPage(DesktopContext(new_project("v31-root")))
        page.artifact_root=Path(os.getcwd());page.run_id.setText("existing-run");page.refresh()
        self.assertFalse(page.start.isEnabled());self.assertFalse(page.resume.isEnabled())
        with patch("PySide6.QtWidgets.QMessageBox.warning") as warning, patch("motorsim.exploratory_workflow._run_directory") as make_run:
            page.start_run(resume=False)
        warning.assert_called_once();make_run.assert_not_called()

    def test_run_bar_summarizes_the_single_execution_configuration(self):
        window = DinoDesktopWindow(new_project("v31-runbar"));execution=window.pages[3]
        execution.rpm.setValue(3450);execution.cycles.setValue(7);execution.budget.setValue(90)
        APP.processEvents()
        self.assertEqual(window.run_config_summary.text(), "3450 rpm · 7 ciclos · 90 s")
        window.close()

    def test_engineering_comparison_keeps_undefined_metrics_empty(self):
        project=new_project("v31-compare");project["variants"]["Variante B"]=project["base_engine"]
        context=DesktopContext(project);page=ResultsPage(context)
        data={"schema":"DINO_EXPLORATORY_COMPARISON_V1","provenance":"diagnostic","experimental_validation":"NOT_CLAIMED",
              "points":[
                  {"variant_id":"base","rpm":3000,"classification":"EXPLORATORY","periodicity":"NOT_EVALUATED","audit_status":"PASS","cycles_completed":1,"conservation":{"status":"PASS"},"brake_power":None,"brake_power_status":"UNDEFINED","brake_power_reason":"periodicity required"},
                  {"variant_id":"Variante B","rpm":3000,"classification":"EXPLORATORY","periodicity":"NOT_EVALUATED","audit_status":"PASS","cycles_completed":1,"conservation":{"status":"PASS"},"brake_power":None,"brake_power_status":"UNDEFINED","brake_power_reason":"periodicity required"}],"traces":[]}
        page._loaded_exploratory(data)
        for i in range(page.variants.count()):page.variants.item(i).setCheckState(__import__("PySide6.QtCore",fromlist=["Qt"]).Qt.CheckState.Checked)
        page._update_engineering_compare()
        labels=[page.compare_table.item(i,0).text() for i in range(page.compare_table.rowCount())]
        self.assertIn("Potencia de freno",labels)
        index=labels.index("Potencia de freno")
        self.assertEqual(page.compare_table.item(index,3).text(),"—")
        self.assertIn("periodicity required",page.compare_table.item(index,4).text())

    def test_trace_view_precedes_sweep_table_and_missing_metrics_have_reason_text(self):
        page=ResultsPage(DesktopContext(new_project("v31-analysis")))
        layout=page.layout()
        self.assertLess(layout.indexOf(page.trace_group),layout.indexOf(page.plot))
        page.plot.set_series([{"name":"Power","unit":"kW","points":[{"rpm":3000,"value":None,"reason":"periodic cycle required"}]}])
        self.assertEqual(page.plot._points(),[])

    def test_discrete_wave_map_does_not_show_a_fake_scale_without_numeric_samples(self):
        view=DiscreteAngleCellMap()
        view.set_grid([0.0,90.0],[{"label":"duct cell","length_mm":10.0,"values":[None,None]}])
        self.assertTrue(view.image.isNull())
        self.assertIsNone(view.value_range)

    def test_analysis_defaults_to_an_available_exhaust_pressure_map(self):
        page=ResultsPage(DesktopContext(new_project("v31-map-default")))
        channel="duct:exhaust:cell:0:pressure_pa"
        page._loaded_exploratory({"schema":"DINO_EXPLORATORY_COMPARISON_V1",
          "points":[{"point_id":"p1","variant_id":"base","rpm":3000,"classification":"EXPLORATORY","point_configuration_sha256":"x"}],
          "traces":[{"point_id":"p1","variant_id":"base","rpm":3000,"cycle":1,"run_id":"r1","angles_deg":[0,90],
            "channels":{"cylinder_pressure_pa":{"values":[100000,110000]},channel:{"values":[90000,95000]}}}]})
        self.assertEqual(page.trace_metric.currentData(),channel)
        self.assertEqual(page.trace_map.raw_samples[0]["values"],[90000,95000])

    def test_comparison_does_not_pair_different_rpm_and_warns_when_solver_identity_missing(self):
        project=new_project("v31-match");project["variants"]["Variante B"]=project["base_engine"]
        page=ResultsPage(DesktopContext(project))
        page._loaded_exploratory({"schema":"DINO_EXPLORATORY_COMPARISON_V1","provenance":"test","experimental_validation":"NOT_CLAIMED","traces":[],
            "points":[
                {"variant_id":"base","rpm":3000,"classification":"EXPLORATORY","periodicity":"NOT_EVALUATED","audit_status":"PASS","cycles_completed":1,"conservation":{}},
                {"variant_id":"Variante B","rpm":4000,"classification":"EXPLORATORY","periodicity":"NOT_EVALUATED","audit_status":"PASS","cycles_completed":1,"conservation":{}}]})
        page._update_engineering_compare()
        self.assertIn("sin par de corridas a la misma RPM",page.compare_notice.text())

    def test_imported_history_labels_resolve_to_project_variants_for_same_rpm_comparison(self):
        project=new_project("v31-imported-history")
        original=deepcopy(project["base_engine"])
        from motorsim.engine_variants import variant
        modified=variant(original,display_name="Escape modified +20 mm",
                         native_patch={"reference_rpm":3500.0})
        original["native_configuration_sha256"]=sha256(original["native_configuration"])
        original_hash=original["native_configuration_sha256"]
        modified_hash=modified["native_configuration_sha256"]
        project["variants"]={"Escape original":original,"Escape modified +20 mm":modified}
        prefix=project["project_id"]+" / "
        points=[]
        for variant,config,rpm in (("Escape original",original_hash,3000),
                                   ("Escape modified +20 mm",modified_hash,3000)):
            points.append({"variant_id":prefix+variant,"rpm":rpm,"configuration_sha256":config,
                "classification":"EXPLORATORY","periodicity":"NOT_EVALUATED","audit_status":"PASS",
                "cycles_completed":1,"conservation":{"status":"PASS"},"brake_power":None,
                "brake_power_status":"UNDEFINED","brake_power_reason":"periodic cycle required"})
        page=ResultsPage(DesktopContext(project))
        page._loaded_exploratory({"schema":"DINO_EXPLORATORY_COMPARISON_V1","provenance":"test",
            "experimental_validation":"NOT_CLAIMED","traces":[],"points":points})
        page.baseline_selector.setCurrentIndex(page.baseline_selector.findData("Escape original"))
        page._update_engineering_compare()
        self.assertIn("3000 RPM",page.compare_notice.text())
        self.assertNotIn("sin par de corridas a la misma RPM",page.compare_notice.text())
        self.assertIn("Mismo RPM",page.compare_notice.text())
        labels=[page.compare_table.item(i,0).text() for i in range(page.compare_table.rowCount())]
        self.assertIn("rpm de referencia",[label.lower() for label in labels])
        self.assertNotIn("0",labels)
