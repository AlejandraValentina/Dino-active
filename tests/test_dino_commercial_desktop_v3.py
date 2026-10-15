from __future__ import annotations

import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import unittest
from unittest.mock import patch
import desktop_qsettings_isolation  # noqa: F401
from PySide6.QtWidgets import QApplication

from motorsim.desktop.app import DinoDesktopWindow
from motorsim.desktop.context import DesktopContext
from motorsim.desktop.execution_page import ExecutionPage
from motorsim.desktop.engine_page import EnginePage
from motorsim.desktop.preferences import settings
from motorsim.desktop.results_page import ResultsPage
from motorsim.desktop.services import new_project
from motorsim.desktop.widgets.run_history import RunHistoryWidget

APP = QApplication.instance() or QApplication([])


class CommercialDesktopV3P0Tests(unittest.TestCase):
    def test_startup_forces_design_even_when_old_setting_points_to_results(self):
        settings().setValue("last_page", 4)
        window = DinoDesktopWindow(new_project("v3-startup"))
        window.show(); APP.processEvents()
        self.assertEqual(window.mode_stack.currentIndex(), 0)
        self.assertEqual(window.component_nav.currentIndex(), 0)
        self.assertFalse(window.results.isVisible())
        self.assertTrue(window.strip_run.isEnabled())
        self.assertEqual(window.design_mode.text(), "Diseño")
        window.close(); APP.processEvents()

    def test_design_analysis_switch_preserves_active_variant_and_baseline(self):
        project = new_project("v3-modes")
        project["variants"]["Variante A"] = project["base_engine"]
        window = DinoDesktopWindow(project); window.context.select_variant("Variante A")
        window.set_workspace_mode(1); window.set_workspace_mode(0)
        self.assertEqual(window.context.selected_variant, "Variante A")
        self.assertEqual(window.context_bar.variant.currentData(), "Variante A")
        self.assertEqual(window.results.baseline_selector.currentData(), "base")
        window.close()

    def test_preset_and_horizon_are_one_synchronized_value(self):
        page = ExecutionPage(DesktopContext(new_project("v3-preset")))
        page.preset.setCurrentIndex(1)
        self.assertEqual(page.cycles.value(), 24)
        page.cycles.setValue(8)
        self.assertEqual(page.preset.currentData(), -1)

    def test_progress_and_cancel_are_visible_in_persistent_status_strip(self):
        window = DinoDesktopWindow(new_project("v3-progress")); window.show(); APP.processEvents()
        execution = window.pages[3]
        execution.run_id.setText("fake-progress")
        with patch.object(execution,"_confirm_run",return_value=True), \
             patch("motorsim.exploratory_workflow._run_directory"), \
             patch("motorsim.desktop.execution_page.run_background",return_value=object()) as launch:
            execution.start_run(resume=False)
            launch.call_args.kwargs["progress"]({"cycle": 2, "angle_deg": 185.0, "rss_bytes": 32 * 1048576})
        APP.processEvents()
        self.assertTrue(window.run_progress.isVisible())
        self.assertTrue(window.strip_cancel.isEnabled())
        self.assertEqual(window.run_state.text(), "CORRIENDO")
        self.assertIn("Ciclo 2", window.run_progress.format())
        execution.task = None; execution.status_text = "LISTO"; execution.state_changed.emit(); APP.processEvents()
        window.close()

    def test_confirmation_copy_is_spanish(self):
        page = ExecutionPage(DesktopContext(new_project("v3-confirm")))
        with patch.object(page, "_preflight", return_value={"rpm":3000,"max_cycles":1,"budget_seconds":60,"memory_limit_mib":1024,"artifact_limit_bytes":1048576,"total_finite_volume_cells":13,"fuel_id":"test","afr_kg_air_per_kg_fuel":14.7}):
            message = page._confirmation_text("run-1", False)
        self.assertIn("Iniciar una simulación", message)
        self.assertEqual(page.confirmation_button_labels(False),("Iniciar corrida","Cancelar"))
        self.assertEqual(page.confirmation_button_labels(True),("Reanudar corrida","Cancelar"))

    def test_trace_pressure_uses_bar_abs_and_nonnegative_ticks(self):
        page = ResultsPage(DesktopContext(new_project("v3-pressure")))
        page._loaded_exploratory({"schema":"DINO_EXPLORATORY_COMPARISON_V1","points":[{"point_id":"p","variant_id":"base","rpm":3000,"classification":"EXPLORATORY","periodicity":"NOT_EVALUATED","audit_status":"PASS","audit_recomputed":True,"cycles_completed":1,"conservation":{"status":"PASS"}}],"traces":[{"point_id":"p","variant_id":"base","run_id":"r","rpm":3000,"cycle":1,"angles_deg":[0,180,360],"channels":{"cylinder_pressure_pa":{"unit":"Pa","values":[100000,150000,200000]}}}],"experimental_validation":"NOT_CLAIMED","provenance":"fixture"})
        self.assertEqual(page.trace_plot.series[0]["unit"], "bar abs")
        self.assertEqual(page.trace_plot.series[0]["points"][0]["value"], 1.0)
        self.assertGreaterEqual(min(page.trace_plot._axis_ranges(page.trace_plot._points())[2:3]), 0)
        self.assertEqual(page.trace_plot.series[0]["role"], "baseline")

    def test_tables_have_alternating_rows_and_visible_analysis_has_no_outer_horizontal_scroll(self):
        window = DinoDesktopWindow(new_project("v3-tables")); window.resize(1360,900); window.show(); window.set_workspace_mode(1); APP.processEvents()
        tables=window.results.findChildren(__import__("PySide6.QtWidgets",fromlist=["QTableWidget"]).QTableWidget)
        self.assertTrue(tables)
        self.assertTrue(all(table.alternatingRowColors() for table in tables))
        scroll=window.analysis_splitter.widget(0)
        self.assertEqual(scroll.horizontalScrollBarPolicy().name,"ScrollBarAlwaysOff")
        self.assertTrue("alternate-background-color" in window.styleSheet())
        window.close()

    def test_fuel_hash_is_not_exposed_in_main_execution_strip(self):
        window = DinoDesktopWindow(new_project("v3-hash"))
        self.assertNotRegex(window.simulation_strip.text() if hasattr(window.simulation_strip,"text") else window.run_state.text(),r"[0-9a-fA-F]{16,}")
        self.assertNotRegex(window.strip_run.text(),r"[0-9a-fA-F]{16,}")
        window.close()

    def test_history_default_includes_active_variant_and_baseline(self):
        project=new_project("v3-history")
        project["variants"]["Activa"]=project["base_engine"]
        context=DesktopContext(project);context.select_variant("Activa")
        settings().setValue("baseline_variant/v3-history","base")
        entries=[{"variant":"base","result_path":"base.json"},{"variant":"Activa","result_path":"active.json"},{"variant":"Otra","result_path":"other.json"}]
        with patch("motorsim.desktop.widgets.run_history.list_project_runs",return_value=entries):
            history=RunHistoryWidget(context,"unused")
        self.assertEqual(history.variant_filter.currentData(),"__active_baseline__")
        self.assertEqual({entry["variant"] for entry in history.entries},{"base","Activa"})

    def test_duration_estimate_uses_all_history_runs_with_matching_cell_count(self):
        page=ExecutionPage(DesktopContext(new_project("v3-estimator")))
        entries=[{"details":{"total_finite_volume_cells":13,"cycles_completed":1,"elapsed_seconds":26.5+i*.1}} for i in range(5)]
        page.set_history_entries([{"details":row["details"],"variant":"base","identity_sha256":"not-required"} for row in entries])
        estimate,source=page._cycle_seconds(13)
        self.assertAlmostEqual(estimate,26.7,places=6)
        self.assertIn("5 corridas",source)
        self.assertIn("13 celdas",source)

    def test_analysis_table_headers_fit_without_horizontal_scroll_at_1360(self):
        window=DinoDesktopWindow(new_project("v3-header-fit"));window.resize(1360,900);window.show();window.set_workspace_mode(1);APP.processEvents()
        table=window.results.point_table
        self.assertEqual(table.horizontalScrollBar().maximum(),0)
        metrics=table.horizontalHeader().fontMetrics()
        widths=[table.horizontalHeader().sectionSize(i) for i in range(table.columnCount())]
        labels=[table.horizontalHeaderItem(i).text() for i in range(table.columnCount())]
        self.assertTrue(all(metrics.horizontalAdvance(label)+12<=width for label,width in zip(labels,widths)),list(zip(labels,widths)))
        window.close()

    def test_cylinder_timing_uses_area_transitions_and_exposes_existing_area_curve(self):
        page=EnginePage(DesktopContext(new_project("v3-port-timing")))
        rows={page.timing.item(i,0).text():tuple(float(page.timing.item(i,j).text()) for j in range(1,4)) for i in range(page.timing.rowCount())}
        self.assertAlmostEqual(rows["main-exhaust"][0],94.2,delta=.1)
        self.assertAlmostEqual(rows["main-exhaust"][1],265.8,delta=.1)
        self.assertAlmostEqual(rows["primary-window"][0],99.0,delta=.1)
        self.assertAlmostEqual(rows["primary-window"][1],261.0,delta=.1)
        self.assertAlmostEqual(rows["inlet-window"][0],261.0,delta=.1)
        self.assertAlmostEqual(rows["inlet-window"][1],99.0,delta=.1)
        self.assertAlmostEqual(rows["inlet-window"][2],198.0,delta=.1)
        self.assertEqual(len(page.area_plot.series),6)
        self.assertEqual(len(page.area_plot.series[0]["points"]),181)
        self.assertIn("no son controles inversos",page.derived.toolTip())


if __name__ == "__main__":
    unittest.main()
