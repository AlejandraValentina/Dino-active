"""Contratos de presentación CAE, sin integración física adicional."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from motorsim.window import MainWindow
from motorsim.examples import PROJECT_FILES
from motorsim.storage import load_project
from motorsim.project import ProjectError
from motorsim.simulation_view import PressurePlot
from motorsim.simulation import FOUR_LAYOUT
from motorsim.project_case import validate_rpm
from motorsim.sweep import plan_rpms

ROOT=Path(__file__).resolve().parents[1]

class CAETests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
    def setUp(self):
        self.w=MainWindow();self.w.show();self.app.processEvents()
    def tearDown(self):
        self.w.dirty=False;self.w.close();self.w.deleteLater();self.app.processEvents()
    def test_new_project_and_real_preparation(self):
        w=self.w
        self.assertEqual(w.project().name,'Sin título');self.assertEqual(w.project().cycle,'2T')
        self.assertEqual(w.summary_page.ready_badge.text(),'DATOS INCOMPLETOS')
        self.assertEqual(w.simulation_view.state_badge.text(),'INACTIVO')
        self.assertFalse(w.simulation_view.preview_angle.points)
    def test_four_file_copies_save_without_touching_resources(self):
        w=self.w
        with tempfile.TemporaryDirectory() as folder,patch('motorsim.simulation_view.QProcess') as process:
            for index,(key,filename) in enumerate(PROJECT_FILES.items()):
                original=ROOT/'examples/projects'/filename;before=original.read_bytes()
                w.summary_page.example_combo.setCurrentIndex(index)
                with patch.object(w,'_ask_changes',return_value='discard'):
                    w.summary_page.example_button.click()
                self.assertEqual(w.project(),load_project(original));self.assertIsNone(w.path);self.assertTrue(w.dirty)
                self.assertEqual(w.summary_page.ready_badge.text(),'ENTRADAS ADMITIDAS')
                self.assertIsNone(w.simulation_view.result)
                target=Path(folder)/(key+'.json')
                with patch.object(w,'_choose_file',return_value=target) as choose:
                    self.assertTrue(w.save());choose.assert_called_once_with(True)
                self.assertEqual(load_project(target),load_project(original));self.assertEqual(original.read_bytes(),before)
            process.assert_not_called()
    def test_example_cancel_and_save_cancel_preserve_editor(self):
        w=self.w;w.name_edit.setText('BORRADOR');before=w.project()
        for answer in ('cancel','save'):
            with patch.object(w,'_ask_changes',return_value=answer),patch.object(w,'_choose_file',return_value=None):
                w.load_example_file('4t-reference')
            self.assertEqual(w.project(),before);self.assertTrue(w.dirty)
    def test_invalid_rpm_and_sweep_keep_drafts_and_contract(self):
        w=self.w;w.load_example_file('2t-reference');v=w.simulation_view
        for raw in ('abc','3000.5','2499','3501'):
            v.rpm_edit.setText(raw);v.check_inputs()
            self.assertEqual(v.rpm_edit.text(),raw);self.assertEqual(v.rpm_edit.property('state'),'error')
            with self.assertRaises(ProjectError):v._rpms()
        v.rpm_edit.setText('3000');self.assertEqual(v._rpms(),[validate_rpm(3000)])
        v.mode_combo.setCurrentIndex(1);v.step_rpm_edit.setText('333')
        with self.assertRaises(ProjectError):v._rpms()
        self.assertEqual(v.step_rpm_edit.text(),'333');self.assertEqual(v.step_rpm_edit.property('state'),'error')
        v.step_rpm_edit.setText('500');self.assertEqual(v._rpms(),plan_rpms(2500,3500,500))
    def test_context_collapses_keyboard_and_resize_without_horizontal_scroll(self):
        w=self.w;w.load_example_file('4t-reference');w.navigation.go('simulation');v=w.simulation_view
        for width,mode in ((1920,3),(1366,2),(900,1)):
            w.resize(width,768);self.app.processEvents();self.app.processEvents()
            self.assertEqual(v.columns.mode,mode);self.assertEqual(v.horizontalScrollBar().maximum(),0)
            self.assertEqual(v.context_panel.toggle.isChecked(),mode==3)
        button=v.context_panel.toggle;button.setFocus();QTest.keyClick(button,Qt.Key.Key_Space)
        self.assertTrue(button.isChecked());self.assertFalse(v.context_panel.body.isHidden())
        self.assertEqual(v.preview_angle.layout.period,720);self.assertIsNotNone(v.preview_pv.volume_range)
    def test_result_context_stays_with_evidence_and_stale_is_visible(self):
        w=self.w;v=w.simulation_view
        v.open_result(path=ROOT/'results/simulacion-2t/cuatro-tiempos-20260916/R2/gui-sweep/point-02/manifest.json')
        previous=v.context_table.values['Geometría'].text();points=list(v.angle_plot.points)
        with patch.object(w,'_ask_changes',return_value='discard'):w.load_example_file('2t-compression')
        self.assertEqual(v.context_table.values['Geometría'].text(),previous)
        self.assertEqual(v.angle_plot.points,points);self.assertEqual(v.preview_angle.points,points)
        self.assertEqual(v.state_badge.text(),'CONVERGIDO');self.assertTrue(v.context_stale.text())
        w.resize(900,650);w.navigation.go('simulation');self.app.processEvents()
        self.assertFalse(v.context_panel.toggle.isChecked());self.assertTrue(v.context_stale.isVisible())
    def test_details_opens_actual_parameters_without_worker(self):
        w=self.w;w.load_example_file('4t-reference');v=w.simulation_view
        w.navigation.go('simulation')
        with patch('motorsim.simulation_view.QProcess') as process:
            v.show_details()
            self.assertEqual(w.navigation.current,'results');self.assertEqual(v.result_tabs.currentIndex(),2)
            self.assertIn(v.inputs['model_version'],v.parameters_text.toPlainText())
            process.assert_not_called()

    def test_plot_preserves_temporal_order_and_empty_axes(self):
        plot=PressurePlot(True);mirror=PressurePlot(True);plot.mirror=mirror
        rows=[{'angle_deg':i*10,'V_m3':[0,volume,0],'p_T_Y':[[1],[pressure],[1]]}
              for i,(volume,pressure) in enumerate(((3e-6,1000),(1e-6,2000),(2e-6,1500)))]
        plot.set_rows(rows,FOUR_LAYOUT)
        self.assertEqual(plot.points,[(3.,1.),(1.,2.),(2.,1.5)])
        self.assertEqual(mirror.points,plot.points);plot.set_rows([])
        self.assertEqual(plot.layout.period,720);self.assertFalse(mirror.points)
        plot.close();mirror.close()

if __name__=='__main__':unittest.main()
