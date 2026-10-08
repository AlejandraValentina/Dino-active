"""Integración asíncrona. Offscreen no acredita inspección visual Windows."""
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PySide6.QtCore import QProcess
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from motorsim.window import MainWindow
from motorsim.simulation_view import PressurePlot
from motorsim.reference_results import load_result
from test_reference_results import diagnostic, edit_payload
from process_double import DiagnosticProcess


class SimulationViewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.window = MainWindow()
        self.view = self.window.simulation_view
        self.window.show()

    def wait_until(self, condition, seconds=8):
        deadline = time.monotonic()+seconds
        while not condition() and time.monotonic() < deadline:
            QTest.qWait(20)
        self.assertTrue(condition())

    def tearDown(self):
        if self.view.active:
            self.view.cancel()
            self.wait_until(lambda: not self.view.active)
        self.window.dirty = False
        self.window.close()
        self.window.deleteLater()
        QTest.qWait(10)

    @patch('motorsim.simulation_view.QProcess', DiagnosticProcess)
    def test_process_double_start_progress_single_process_and_cancel(self):
        self.view.start(output=self.root/'run')
        process = self.view.process
        self.view.start(output=self.root/'duplicate')
        self.assertIs(self.view.process, process)
        self.wait_until(lambda: 'RHS:' in self.view.progress_label.text())
        started = time.monotonic()
        self.view.cancel()
        self.wait_until(lambda: not self.view.active)
        self.assertLess(time.monotonic()-started, 3)
        self.assertFalse(self.view.forced)
        self.assertEqual(self.view.state_label.text(), 'Cancelado')
        self.assertFalse(self.view.angle_plot.points)
        self.assertFalse((self.root/'duplicate').exists())
        self.assertEqual(load_result(self.root/'run/manifest.json')['status'], 'cancelled')
        self.assertFalse(self.window.dirty)

    @patch('motorsim.simulation_view.QProcess', DiagnosticProcess)
    def test_editor_close_protection_then_double_cancel(self):
        self.window.name_edit.setText('Proyecto propio')
        self.view.start(output=self.root/'close')
        with patch.object(self.window, '_ask_changes', return_value='cancel'):
            self.window.close()
        self.assertTrue(self.view.active)
        self.assertFalse(self.view.cancel_requested)
        with patch.object(self.window, '_ask_changes', return_value='discard'):
            self.window.close()
        self.wait_until(lambda: not self.view.active and not self.window.isVisible())
        self.assertFalse(self.view.forced)

    def test_reopen_invalid_preserves_valid_and_project_is_independent(self):
        path = diagnostic(self.root)
        self.view.open_result(path=path)
        previous = self.view.result
        inputs = self.view.inputs.copy()
        self.window.name_edit.setText('No es el caso')
        self.window.cycle_combo.setCurrentText('4T')
        with patch.object(self.window, '_ask_changes', return_value='discard'):
            self.window.new_project()
        self.assertIs(self.view.result, previous)
        self.assertEqual(self.view.inputs, inputs)
        self.assertFalse(self.window.dirty)
        (self.root/'case.json').write_text('malformado')
        self.view.open_result(path=path)
        self.assertIs(self.view.result, previous)
        self.assertIn('Se conserva', self.view.error_label.text())

    def test_error_clears_previous_and_zero_exit_does_not_mean_success(self):
        self.view.open_result(path=diagnostic(self.root))
        class ZeroProcess(QProcess):
            def setArguments(self, args):
                super().setArguments(['-c', 'raise SystemExit(0)'])
        with patch('motorsim.simulation_view.QProcess', ZeroProcess):
            self.view.start(output=self.root/'missing')
            self.wait_until(lambda: not self.view.active)
        self.assertIsNone(self.view.result)
        self.assertIn('Error', self.view.state_label.text())
        self.assertFalse(self.view.angle_plot.points)

    def test_failed_start_and_unresponsive_child_are_bounded(self):
        class MissingProcess(QProcess):
            def setProgram(self, program):
                super().setProgram(str(self_root/'python-missing.exe'))
        self_root = self.root
        with patch('motorsim.simulation_view.QProcess', MissingProcess):
            self.view.start(output=self.root/'fail')
            self.wait_until(lambda: not self.view.active)
        self.assertIn('Error', self.view.state_label.text())
        class HungProcess(QProcess):
            def setArguments(self, args):
                super().setArguments(['-c', 'import time; time.sleep(30)'])
        with patch('motorsim.simulation_view.QProcess', HungProcess):
            self.view.start(output=self.root/'hang')
            self.wait_until(lambda: self.view.process.state() == QProcess.ProcessState.Running)
            self.view.cancel()
            self.wait_until(lambda: not self.view.active, 6)
        self.assertTrue(self.view.forced)
        self.assertEqual(self.view.state_label.text(), 'Cancelado')

    def test_plot_keeps_time_order_and_continuous_angle(self):
        rows = [dict(angle_deg=a, V_m3=[0, 0, v, 0], p_T_Y=[[0, 0, 0]]*2+[[p, 300, 0]])
                for a, v, p in ((3420, 1e-4, 1e5), (3600, 2e-5, 1e6), (3780, 1e-4, 2e5))]
        pv, angle = PressurePlot(True), PressurePlot()
        pv.set_rows(rows)
        angle.set_rows(rows)
        self.assertEqual([x for x, _ in pv.points], [100, 20, 100])
        self.assertEqual([x for x, _ in angle.points], [180, 360, 540])
        self.assertEqual([y for _, y in pv.points], [100, 1000, 200])

    def test_open_button_and_nonconverged_result(self):
        path = diagnostic(self.root)
        def stopped(data):
            data['status'] = 'not_converged'
            data['result']['stop'] = 'límite de 60 segundos por resolución'
        edit_payload(self.root, 'summary.json', stopped)
        with patch('motorsim.simulation_view.QFileDialog.getOpenFileName', return_value=(str(path), '')):
            self.view.open_button.click()
        self.assertEqual(self.view.state_label.text(), 'Sin convergencia / presupuesto agotado')
        self.assertFalse(self.view.angle_plot.points)
        self.assertIn('Diagnóstico no aceptado', self.view.summary_label.text())
        self.assertFalse(self.window.dirty)


if __name__ == '__main__':
    unittest.main()
