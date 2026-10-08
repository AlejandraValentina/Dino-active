"""Recálculo y retención: proceso doblado, históricos reales como datos de prueba."""
import json
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch
from PySide6.QtCore import QProcess
from test_performance_session import PerformanceSessionTests,PATHS

class PerformanceRecalculationTests(PerformanceSessionTests):
    # Solo heredar utilidades; los casos de sesión se descubren en su módulo.
    def baseline(self,path=PATHS[0]):
        sweep=self.activate_sweep_project(path);self.v.sweep=sweep;self.w.navigation.go('performance')
        return sweep
    def complete(self,sweep):
        self.v._series_id=sweep['index']['series_id']
        with patch('motorsim.simulation_view.load_sweep',return_value=sweep),patch('motorsim.simulation_view.write_index'):
            self.v._finished(0,QProcess.ExitStatus.NormalExit)
    def test_rpm_edit_keeps_curve_and_separates_project_and_plan(self):
        previous=self.baseline();rows=self.p.rows
        self.p.rpm_edits[2].setText('250')
        self.assertIs(self.p.sweep,previous);self.assertIs(self.p.rows,rows)
        self.assertTrue(self.p.compatible(previous));self.assertFalse(self.p.plan_matches_sweep(previous))
        self.assertIn('pendiente de actualización',self.p.plan_status.text());self.assertIn('2750',self.p.plan_status.text())
        self.assertTrue(self.p.calculate_button.isEnabled());self.assertTrue(self.p.setup.isVisible())
        self.assertTrue(self.p.main_plot.isVisible());self.assertEqual(self.p.calculate_button.text(),'Recalcular rendimiento')
        # Tampoco reemplazar por otra serie solo por editar opciones en Simulación.
        self.v.sweep=deepcopy(previous);self.v.step_rpm_edit.setText('500')
        self.assertIs(self.p.sweep,previous);self.assertEqual(self.p.rpm_edits[2].text(),'500')
        self.assertIn('Curva actualizada',self.p.plan_status.text())
        self.p.rpm_edits[2].setText('333');self.assertIs(self.p.sweep,previous)
        self.assertFalse(self.p.calculate_button.isEnabled());self.assertFalse(self.p.plan_matches_sweep(previous))
    def test_three_consecutive_calculations_replace_only_at_completion(self):
        original=self.baseline();previous=original
        with patch.object(QProcess,'start') as start:
            for i,count in enumerate((2,3,2)):
                self.p.rpm_edits[1].setText('3000' if count==2 else '3500')
                self.p.calculate(output=Path(self.tmp.name)/str(i))
                self.assertIs(self.p.sweep,previous);self.assertTrue(self.p.main_plot.isVisible())
                self.assertTrue(self.p.setup.isVisible());self.assertFalse(any(e.isEnabled() for e in self.p.rpm_edits))
                self.assertFalse(self.p.calculate_button.isEnabled());self.assertIn('Resultado anterior',self.p.plan_status.text())
                request=json.loads(self.v._request_path.read_text(encoding='utf-8'))
                self.assertEqual(request['rpms'],[2500,3000,3500][:count])
                new=deepcopy(original);new['index']['rpms']=new['index']['rpms'][:count];new['index']['points']=new['index']['points'][:count];new['results']=new['results'][:count]
                new['path']=Path(self.tmp.name)/str(i)/'series.json';self.complete(new)
                self.assertIs(self.p.sweep,new);self.assertEqual(len(self.p.rows),count)
                self.assertTrue(all(e.isEnabled() for e in self.p.rpm_edits));self.assertIn('Curva actualizada',self.p.plan_status.text())
                self.assertEqual(self.w.navigation.current,'performance');previous=new
            self.assertEqual(start.call_count,3)
    def test_cancel_recalculation_preserves_curve_plan_and_retry(self):
        for path in PATHS:
            previous=self.baseline(path);before=deepcopy(previous);self.p.rpm_edits[2].setText('250')
            with patch.object(QProcess,'start'),patch.object(QProcess,'write',return_value=7):
                self.p.calculate(output=Path(self.tmp.name)/path.parent.name)
                self.p.cancel_button.click();cancelled=deepcopy(previous);cancelled['index']['state']='cancelled';self.complete(cancelled)
                self.assertIs(self.p.sweep,previous);self.assertEqual(previous,before)
                self.assertEqual(self.p.rpm_edits[2].text(),'250');self.assertTrue(self.p.calculate_button.isEnabled())
                self.assertIn('Nuevo cálculo cancelado',self.p.error.text());self.w.navigation.go('performance')
                self.assertIs(self.p.sweep,previous);self.assertIn('pendiente de actualización',self.p.plan_status.text())
                self.p.calculate(output=Path(self.tmp.name)/'retry');self.assertTrue(self.v.active);self.v._finish_cleanup()
    def test_error_nonconvergence_and_first_failure_recover(self):
        previous=self.baseline()
        with patch.object(QProcess,'start'):
            self.p.calculate(output=Path(self.tmp.name)/'fail');self.v.error_label.setText('ERROR REAL DEL AUXILIAR')
            self.v._finish_cleanup('Error de ejecución')
            self.assertIs(self.p.sweep,previous);self.assertIn('ERROR REAL',self.p.error.text());self.assertTrue(self.p.calculate_button.isEnabled())
            self.p.calculate(output=Path(self.tmp.name)/'nonconverged')
            partial=deepcopy(previous);partial['index'].update(state='stopped',reason='No convergencia de prueba')
            partial['index']['points'][1].update(state='error');partial['results'][1]=None
            self.complete(partial);self.assertIs(self.p.sweep,previous);self.assertIn('No convergencia',self.p.error.text())
            self.w._activate(self.w.execution_snapshot()[0],None);self.v.sweep=None;self.p.clear_sweep()
            self.p.rpm_edits[1].setText('3000');self.p.calculate(output=Path(self.tmp.name)/'first-error')
            self.v.error_label.setText('Fallo inicial');self.v._finish_cleanup('Error de ejecución')
            self.assertIsNone(self.p.sweep);self.assertEqual(self.p.rpm_edits[1].text(),'3000');self.assertTrue(self.p.calculate_button.isEnabled())
    def test_history_edit_does_not_reclassify_as_current_motor(self):
        self.baseline(PATHS[1]);self.p.open_sweep(path=PATHS[0]);history=self.p.sweep
        self.p.rpm_edits[2].setText('250');self.assertIs(self.p.sweep,history)
        self.assertIn('Análisis histórico',self.p.identity.text());self.assertTrue(self.p.calculate_button.isEnabled())
        self.w.numeric_edits['compression_ratio'].setText('8.2');self.assertIsNone(self.p.sweep)
    def test_late_cancel_does_not_accept_already_closed_index(self):
        previous=self.baseline();new=deepcopy(previous)
        self.v.sweep=new;self.v.cancel_requested=True;self.v._running_sweep=True
        self.p.calculation_finished();self.assertIs(self.p.sweep,previous)
        self.assertIn('Nuevo cálculo cancelado',self.p.error.text())
        self.w.navigation.go('performance');self.assertIs(self.p.sweep,previous)
        self.p.clear_sweep();self.p.sync_session();self.assertIsNone(self.p.sweep)

# Evitar redescubrir los tests heredados de la suite de sesión.
for name in dir(PerformanceSessionTests):
    if name.startswith('test_'):setattr(PerformanceRecalculationTests,name,None)
del PerformanceSessionTests
