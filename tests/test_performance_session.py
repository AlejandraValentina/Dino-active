"""Flujo de sesión/proyecto: dobles de proceso y resultados preservados, sin solver."""
import gc,json,os,tempfile,unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from PySide6.QtCore import QEvent,QProcess
from PySide6.QtWidgets import QApplication
from motorsim.window import MainWindow
from motorsim.project import Project
from motorsim.examples import example_project
from motorsim.sweep import load_sweep
ROOT=Path(__file__).resolve().parents[1]
PATHS=[ROOT/'results/simulacion-2t/barrido-20260915/gui-sweep/series.json',ROOT/'results/simulacion-2t/cuatro-tiempos-20260916/R2/gui-sweep/series.json']
class PerformanceSessionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
    def setUp(self):
        self.w=MainWindow();self.p=self.w.performance_page;self.v=self.w.simulation_view
        self.w.show();self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
    def tearDown(self):
        if self.v.active:self.v._finish_cleanup()
        self.w.dirty=False;self.w.close();self.w.deleteLater()
        self.app.sendPostedEvents(None,QEvent.Type.DeferredDelete);self.app.processEvents();gc.collect()
    def activate_sweep_project(self,path):
        sweep=load_sweep(path);inputs=sweep['index']['common_inputs'];origin=inputs['origin']
        self.w._activate(Project.from_dict(inputs['project_snapshot']),Path(origin['source_path']) if origin['source_path'] else None)
        return sweep
    def test_high_rpm_2t_request_and_4t_block(self):
        self.w._activate(example_project('2t-reference'),None)
        self.w.navigation.go('performance')
        for edit,value in zip(self.p.rpm_edits,('5000','15000','2500')):
            edit.setText(value)
        self.assertTrue(self.p.calculate_button.isEnabled())
        with patch.object(QProcess,'start') as start:
            self.p.calculate(output=Path(self.tmp.name)/'high')
            self.assertEqual(start.call_count,1)
            request=json.loads(self.v._request_path.read_text(encoding='utf-8'))
            self.assertEqual(request['rpms'],[5000,7500,10000,12500,15000])
            self.v._finish_cleanup('Cancelado')
        self.w._activate(example_project('4t-reference'),None)
        self.assertFalse(self.p.calculate_button.isEnabled())

    def test_empty_examples_no_dialog_no_process(self):
        for key in ('2t-reference','2t-compression','4t-reference','4t-compression'):
            with patch('motorsim.performance_view.QFileDialog.getOpenFileName') as dialog,patch.object(QProcess,'start') as start:
                self.w._activate(example_project(key),None);self.w.navigation.go('performance')
                self.assertTrue(self.p.calculate_button.isVisible());self.assertIsNone(self.p.sweep)
                self.assertIn('2500 · 3000 · 3500 rpm',self.p.plan_label.text());dialog.assert_not_called();start.assert_not_called()
    def test_both_cycles_exact_shared_start_progress_cancel(self):
        for cycle,path in zip(('2T','4T'),PATHS):
            self.activate_sweep_project(path);self.w.navigation.go('performance')
            with patch.object(QProcess,'start') as start,patch.object(QProcess,'write',return_value=7) as write:
                self.p.calculate(output=Path(self.tmp.name)/cycle)
                self.assertEqual(start.call_count,1);self.assertIn('--sweep-input',self.v.process.arguments())
                request=json.loads(self.v._request_path.read_text(encoding='utf-8'))
                self.assertEqual(request['rpms'],[2500,3000,3500]);self.assertEqual(request['common_inputs']['project_snapshot']['cycle'],cycle)
                self.assertTrue(self.p.progress_panel.isVisible());self.assertFalse(self.p.main_plot.isVisible())
                self.v.finished_points={0:'converged'};self.v.progress_label.setText('Punto 2/3 · 3000 rpm · Ciclos completos: 4');self.v._tick()
                self.assertIn('Puntos convergidos: 1 · Pendientes: 2',self.p.progress_text.text())
                self.p.cancel_button.click();write.assert_called_once_with(b'cancel\n');self.assertFalse(self.p.cancel_button.isEnabled())
                self.v._finish_cleanup('Cancelado');self.assertTrue(self.p.calculate_button.isEnabled())
    def test_finish_from_each_workspace_automatic_and_preserved(self):
        for mode,path in zip(('performance','simulation'),PATHS):
            sweep=self.activate_sweep_project(path);self.w.navigation.go(mode)
            with patch.object(QProcess,'start'),patch('motorsim.simulation_view.load_sweep',return_value=deepcopy(sweep)),patch('motorsim.simulation_view.write_index'):
                if mode=='performance':self.p.calculate(output=Path(self.tmp.name)/mode)
                else:
                    self.v.origin_combo.setCurrentIndex(1);self.v.mode_combo.setCurrentIndex(1);self.v.start(output=Path(self.tmp.name)/mode)
                self.v._series_id=sweep['index']['series_id'];self.v._finished(0,QProcess.ExitStatus.NormalExit)
                if mode=='performance':self.assertEqual(self.w.navigation.current,'performance')
                self.w.navigation.go('performance');self.assertIs(self.p.sweep,self.v.sweep);self.assertEqual(len(self.p.rows),3)
                self.assertTrue(self.p.setup.isVisible())
                self.assertEqual(self.p.calculate_button.text(),'Recalcular rendimiento')
                previous=self.p.sweep;self.v.sweep=None;self.w.navigation.go('performance');self.assertIs(self.p.sweep,previous)
    def test_project_changes_no_old_curve_historical_explicit(self):
        sweep=self.activate_sweep_project(PATHS[0]);self.v.sweep=sweep;self.w.navigation.go('performance');self.assertIs(self.p.sweep,sweep)
        self.w.numeric_edits['compression_ratio'].setText('8.2');self.assertIsNone(self.p.sweep);self.assertFalse(self.p.main_plot.rows)
        self.p.open_sweep(path=PATHS[0]);self.assertIn('Análisis histórico',self.p.identity.text())
        self.w.navigation.go('summary');self.w.navigation.go('performance');self.assertIsNotNone(self.p.sweep)
        self.w._activate(example_project('4t-reference'),None);self.assertIsNone(self.p.sweep)
    def test_invalid_range_and_project_do_not_launch(self):
        with patch.object(QProcess,'start') as start:
            self.p.calculate(output=Path(self.tmp.name)/'invalid');start.assert_not_called();self.assertTrue(self.p.error.text())
            self.w._activate(example_project('2t-reference'),None);self.p.rpm_edits[2].setText('333')
            self.p.calculate(output=Path(self.tmp.name)/'range');start.assert_not_called();self.assertTrue(self.p.error.text())
    def test_cancelled_empty_sweep_offers_retry(self):
        sweep=self.activate_sweep_project(PATHS[0]);sweep['index']['state']='cancelled'
        for point in sweep['index']['points']:point.update(state='not_executed',reason='Cancelado antes del primer punto')
        sweep['results']=[None]*len(sweep['results']);self.v.sweep=sweep
        self.w.navigation.go('performance')
        self.assertTrue(self.p.calculate_button.isVisible());self.assertTrue(self.p.calculate_button.isEnabled())
        self.assertTrue(self.p.empty_label.isVisible());self.assertFalse(any(row['metrics'] for row in self.p.rows))
if __name__=='__main__':unittest.main()
