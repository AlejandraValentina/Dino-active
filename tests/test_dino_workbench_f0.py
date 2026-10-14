from __future__ import annotations

import os
os.environ.setdefault("QT_QPA_PLATFORM","offscreen")

import unittest
from pathlib import Path
from unittest.mock import patch
import desktop_qsettings_isolation  # noqa: F401
from PySide6.QtWidgets import QApplication,QListWidgetItem
from PySide6.QtCore import Qt
from PySide6.QtGui import QPaintDevice

from motorsim.desktop.context import DesktopContext
from motorsim.desktop.exhaust_page import ExhaustPage
from motorsim.desktop.execution_page import ExecutionPage
from motorsim.desktop.results_page import ResultsPage
from motorsim.desktop.plot import CurvePlot
from motorsim.desktop.preferences import default_artifact_root,set_artifact_root
from motorsim.desktop.services import new_project

APP=QApplication.instance() or QApplication([])


class WorkbenchF0Tests(unittest.TestCase):
    def test_project_change_refreshes_exhaust_overlay_choices(self):
        context=DesktopContext(new_project("first"));page=ExhaustPage(context)
        second=new_project("second");second["variants"]["Variant B"]=second["base_engine"]
        context.replace_project(second,None)
        self.assertEqual(page.overlay_selector.findData("Variant B")>=0,True)
        self.assertEqual(page.overlay_selector.currentData(),None)

    def test_changed_section_path_maps_to_index(self):
        context=DesktopContext(new_project("sections"));context.duplicate_variant(None,"Variant A");context.select_variant("Variant A")
        page=ExhaustPage(context)
        with patch("motorsim.desktop.exhaust_page.compare_configurations",return_value=[{"path":"/native_configuration/chamber/sections/1/length_mm"} ]):
            self.assertEqual(page._changed_sections(),{1})

    def test_long_horizon_preset_does_not_change_budget(self):
        page=ExecutionPage(DesktopContext(new_project("budget")))
        page.budget.setValue(60);page.preset.setCurrentIndex(1)
        self.assertEqual(page.cycles.value(),24)
        self.assertEqual(page.budget.value(),60)
        self.assertIn("nunca cambia",page.budget_estimate.text())
        self.assertIn("tope no alcanza",page.budget_estimate.text())
        page.apply_budget_estimate.click()
        self.assertEqual(page.budget.value(),600)

    def test_trace_scale_fits_signal_without_forcing_zero(self):
        plot=CurvePlot();plot.set_series([{"name":"p","x_key":"angle_deg","points":[{"angle_deg":0,"value":99000},{"angle_deg":1,"value":101000}]}],y_scale_mode="data_margin")
        plot._axis_ranges(plot._points())
        low,high=plot.axis_y_bounds
        self.assertLess(low,99000);self.assertGreater(high,101000);self.assertGreater(low,90000)

    def test_repository_artifact_root_is_rejected_and_default_is_external(self):
        with self.assertRaisesRegex(ValueError,"dentro del repositorio"):
            set_artifact_root(Path.cwd()/"results"/"bad")
        self.assertIsNone(__import__("motorsim.desktop.preferences",fromlist=["repository_root_containing"]).repository_root_containing(default_artifact_root()))

    def test_unsafe_artifact_environment_override_is_ignored(self):
        with patch.dict(os.environ,{"DINO_ARTIFACT_ROOT":str(Path.cwd()/"results"/"unsafe")}):
            root=default_artifact_root()
            self.assertIsNone(__import__("motorsim.desktop.preferences",fromlist=["repository_root_containing"]).repository_root_containing(root))

    def test_result_metric_widget_does_not_shadow_qwidget_metric(self):
        page=ResultsPage(DesktopContext(new_project("metric")))
        self.assertTrue(callable(page.metric))
        self.assertTrue(hasattr(page,"metric_selector"))
        self.assertGreaterEqual(page.metric(QPaintDevice.PaintDeviceMetric.PdmWidth),0)

    def test_component_build_uses_backend_derived_port_schedule(self):
        page=__import__("motorsim.desktop.engine_page",fromlist=["EnginePage"]).EnginePage(DesktopContext(new_project("components")))
        self.assertEqual([page.component_tabs.tabText(i) for i in range(4)],
                         ["Cilindro y operación","Lumbreras y distribución","Pérdidas","Combustión y combustible"])
        self.assertGreater(page.port_areas.rowCount(),0)
        self.assertIn("eventos angulares del perfil existente",page.derived.text())

    def test_results_angle_cell_map_preserves_discrete_samples_and_baseline(self):
        context=DesktopContext(new_project("trace-map"));page=ResultsPage(context)
        item=QListWidgetItem("base");item.setCheckState(Qt.CheckState.Checked);page.variants.addItem(item)
        config=context.project["base_engine"]
        exhaust=next(d for d in config["native_configuration"]["ducts"] if d["id"]=="exhaust")
        exact_position=exhaust["mesh"]["centers"][3]
        page.dataset={"schema":"DINO_EXPLORATORY_COMPARISON_V1","points":[
            {"point_id":"p1","variant_id":"base","rpm":3000,"point_configuration_sha256":config["native_configuration_sha256"],"brake_power":1.0,"brake_power_status":"DEFINED","classification":"PERIOD_1"},
            {"variant_id":"base","rpm":4000,"brake_power":None,"brake_power_status":"UNDEFINED","classification":"NOT_IDENTIFIABLE"}],"traces":[{
                "point_id":"p1","variant_id":"base","run_id":"r1","rpm":3000,"cycle":1,"angles_deg":[0.0,2.0],"channels":{
                "duct:exhaust:cell:3:pressure_pa":{"unit":"Pa","values":[99000.0,101000.0]}}}]}
        page.trace_metric.addItem("Presión celda 3","duct:exhaust:cell:3:pressure_pa")
        page.baseline_selector.addItem("base","base");page.baseline_selector.setCurrentIndex(1);page._baseline_changed()
        page._redraw_trace_map()
        self.assertEqual(page.trace_map.columnCount(),3)
        self.assertEqual(page.trace_map.item(0,1).text(),"99000")
        self.assertEqual(page.trace_map.item(0,2).text(),"101000")
        self.assertIn(f"x={float(exact_position):.6g} m",page.trace_map.item(0,0).text())
        self.assertIn("Baseline base",page.baseline_notice.text())
        self.assertTrue(any(p.get("value") is None for series in page.plot.series for p in series.get("points",[])))
        reopened=ResultsPage(DesktopContext(new_project("trace-map")))
        self.assertEqual(reopened.baseline_selector.currentData(),"base")

    def test_main_window_keeps_results_and_single_run_strip_visible(self):
        from motorsim.desktop.app import DinoDesktopWindow
        window=DinoDesktopWindow(new_project("workbench-shell"));window.resize(980,680);window.show();APP.processEvents()
        self.assertTrue(window.results_panel.isVisible());self.assertTrue(window.simulation_strip.isVisible())
        self.assertEqual(window.stack.count(),5)
        self.assertTrue(window.pages[3].start.isEnabled())
        window.close();APP.processEvents()
