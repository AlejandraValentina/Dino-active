"""Regresión de composición, sin nuevas integraciones físicas."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication,QPushButton,QToolButton
from motorsim.window import MainWindow
from motorsim.simulation_case import geometry
from motorsim.four_stroke import geometry as geometry4
from test_reference_results import diagnostic
from process_double import DiagnosticProcess


class WorkspaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
    def setUp(self):
        self.w=MainWindow();self.w.show();self.app.processEvents()
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
    def wait_idle(self):
        end=time.monotonic()+3
        while self.w.simulation_view.active and time.monotonic()<end:QTest.qWait(20)
        self.assertFalse(self.w.simulation_view.active)
    def tearDown(self):
        w=self.w
        if w.simulation_view.active:
            w.simulation_view.cancel();self.wait_idle()
        w.dirty=False;w.close();w.deleteLater();self.app.processEvents()
    def test_cycle_navigation_and_dirty_data_preserved(self):
        w=self.w;w._activate(geometry(),None);before=w.project()
        self.assertEqual(w.navigation.current,'summary')
        self.assertTrue(w.navigation.items['motor4'].isHidden())
        for key in ('geometry','motor2','simulation','results','compare','external','summary'):w.navigation.go(key)
        self.assertEqual(w.project(),before);self.assertFalse(w.dirty)
        w.navigation.go('motor2');w.cycle_combo.setCurrentText('4T')
        self.assertEqual(w.navigation.current,'motor4');self.assertTrue(w.navigation.items['motor2'].isHidden())
        w.cycle_combo.setCurrentText('2T');self.assertEqual(w.project(),before);self.assertTrue(w.dirty)
    def test_invalid_drafts_survive_navigation(self):
        w=self.w;w._activate(geometry(),None);w.ports_view.edits['height_mm'].setText('inválido')
        draft=list(w.ports_view.drafts)
        for key in ('results','external','compare','summary','motor2'):w.navigation.go(key)
        self.assertEqual(w.ports_view.drafts,draft);self.assertEqual(w.ports_view.edits['height_mm'].text(),'inválido')
        self.assertTrue(w.dirty)
    def test_summary_attention_routes_without_new_validation(self):
        w=self.w;self.assertIn('geometry',w.summary_page.issue_routes);self.assertIn('motor2',w.summary_page.issue_routes)
        button=next(b for b in w.summary_page.findChildren(QPushButton) if b.text().startswith('Motor 2T'))
        button.click();self.assertEqual(w.navigation.current,'motor2')
        w._activate(geometry4(),None);self.assertEqual(w.summary_page.ready.text(),'Listo para simular')
        self.assertEqual(w.summary_page.attention.count(),0)
        self.assertFalse(button.isVisible())
    def test_keyboard_and_compact_navigation(self):
        w=self.w;w.resize(640,480);w.navigation.tree.setFocus();QTest.keyClick(w.navigation.tree,Qt.Key.Key_End)
        self.assertEqual(w.navigation.current,'external');self.assertTrue(w.navigation.tree.isVisible())
        w.navigation.go('geometry');self.app.processEvents()
        self.assertFalse(w.geometry_view.editor_wide);self.assertEqual(w.geometry_view.horizontalScrollBar().maximum(),0)
    def test_summary_uses_active_cycle_execution_contract(self):
        w=self.w;w._activate(geometry4(),None);w.cycle_combo.setCurrentText('2T')
        w.ports_view.crankcase_edit.setText('abc');w.cycle_combo.setCurrentText('4T')
        self.assertEqual(w.summary_page.ready.text(),'Listo para simular')
        self.assertEqual(w.summary_page.issue_routes,{})
        self.assertEqual(w.ports_view.crankcase_edit.text(),'abc')
    @patch('motorsim.simulation_view.QProcess',DiagnosticProcess)
    def test_active_process_survives_navigation_and_cancel(self):
        w=self.w;v=w.simulation_view;v.start(output=Path(self.tmp.name)/'run');child=v.process
        for key in ('summary','geometry','results','compare','simulation'):
            w.navigation.go(key);self.assertIs(v.process,child)
        v.cancel();self.wait_idle()
    def test_result_shared_panel_and_project_independence(self):
        w=self.w;v=w.simulation_view;path=diagnostic(Path(self.tmp.name));original=path.read_bytes();v.open_result(path=path)
        result=v.result;inputs=v.inputs.copy();w.navigation.go('results')
        self.assertIs(v.result_panel.parentWidget(),w.result_workspace.detail)
        w._activate(geometry4(),None);self.assertIs(v.result,result);self.assertEqual(v.inputs,inputs)
        w.navigation.go('simulation');self.assertIs(v.result_panel.parentWidget(),v.run_workspace)
        self.assertEqual(path.read_bytes(),original)
    def test_analysis_embedded_and_does_not_launch_worker(self):
        w=self.w
        with patch('motorsim.simulation_view.QProcess') as process:
            for key in ('compare','external','results'):w.navigation.go(key)
            process.assert_not_called()
        self.assertFalse(w.comparison_page.isWindow());self.assertFalse(w.external_page.isWindow())
        for key,page in (('compare',w.comparison_page),('external',w.external_page)):
            w.navigation.go(key);QTest.keyClick(page,Qt.Key.Key_Escape)
            self.assertTrue(page.isVisible())
        self.assertFalse(w.external_page.sweep_button.isEnabled());self.assertFalse(w.external_page.export_button.isEnabled())
    def test_refined_placeholders_and_preparation_are_not_results(self):
        w=self.w;w._activate(geometry(),None);v=w.simulation_view
        v.origin_combo.setCurrentIndex(1);w.navigation.go('simulation')
        self.assertIsNone(v.result);self.assertTrue(v.identity_label.isHidden())
        self.assertIn('No hay resultado',v.result_status_label.text())
        self.assertTrue(w.comparison_page.tabs.isHidden())
        self.assertFalse(w.external_page.export_button.isEnabled())
        self.assertEqual(w.summary_page.example_combo.count(),4)
        self.assertTrue(w.summary_page.example_button.isEnabled())
    def test_refined_columns_stack_without_losing_controls(self):
        from motorsim.ui import Columns
        w=self.w;w._activate(geometry(),None)
        w.resize(900,650);self.app.processEvents()
        for columns in w.summary_page.findChildren(Columns):self.assertFalse(columns.wide)
        for key in ('summary','motor2','simulation','external'):
            w.navigation.go(key);self.app.processEvents()
            page=w.navigation.pages[key]
            self.assertEqual(page.horizontalScrollBar().maximum(),0,key)
    def test_embedded_csv_preview_confirmation_and_cancel(self):
        w=self.w;w.navigation.go('external');page=w.external_page
        path=Path(self.tmp.name)/'synthetic.csv';path.write_text('rpm,value\n2500,52\n3000,50\n')
        page.import_csv(path=path);dialog=page.import_dialog
        self.assertFalse(dialog.isWindow());self.assertFalse(page.import_button.isEnabled())
        dialog.magnitude.setCurrentIndex(dialog.magnitude.findData('W_C_4T_J'))
        dialog.unit.setCurrentIndex(1);dialog.confirm_definition.setChecked(True)
        dialog.preview();self.assertTrue(dialog.confirm_button.isEnabled())
        destination=Path(self.tmp.name)/'import'
        with patch('motorsim.external_view.QFileDialog.getSaveFileName',return_value=(str(destination),'')):
            dialog.confirm()
        self.assertIsNotNone(page.external);self.assertTrue(page.sweep_button.isEnabled())
        page.tabs.setCurrentIndex(1)
        self.assertFalse(page.plot.grab().isNull())
        previous=page.external;page.import_csv(path=path);page.import_dialog.reject()
        self.assertIs(page.external,previous);self.assertTrue(page.import_button.isEnabled())
    @patch('motorsim.simulation_view.QProcess',DiagnosticProcess)
    def test_close_while_in_another_workspace_cancels(self):
        w=self.w;w.simulation_view.start(output=Path(self.tmp.name)/'close')
        w.navigation.go('summary');w.close();self.wait_idle();QTest.qWait(20)
        self.assertFalse(w.simulation_view.active);self.assertFalse(w.isVisible())

if __name__=='__main__':unittest.main()
