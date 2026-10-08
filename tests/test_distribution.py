"""Arranque y distribución: dobles, sin integraciones numéricas."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch, MagicMock

os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from PySide6.QtCore import QProcess
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from motorsim.runtime import worker_command,build_info,diagnostic,resource,APP_VERSION
from motorsim.window import MainWindow
from motorsim.reference_results import save_result, load_result, reference_inputs
from tests.test_reference_results import diagnostic as result_fixture


class DistributionTests(unittest.TestCase):
    def test_source_command_absolute_and_cwd_independent(self):
        executable,args,cwd=worker_command()
        self.assertTrue(Path(executable).is_absolute())
        self.assertEqual(args,['-u','-m','motorsim.reference_run'])
        self.assertTrue((Path(cwd)/'motorsim/reference_run.py').is_file())
        self.assertTrue(resource('theme.qss').is_file());self.assertTrue(resource('ayuda.txt').is_file())

    def test_frozen_worker_unicode_missing_and_found(self):
        with tempfile.TemporaryDirectory(prefix='MotorSim á ') as root:
            with patch.object(sys,'frozen',True,create=True),patch.object(sys,'executable',str(Path(root)/'MotorSim.exe')):
                with self.assertRaisesRegex(FileNotFoundError,'carpeta completa'):worker_command()
                (Path(root)/'MotorSimWorker.exe').write_bytes(b'fixture; no executable')
                executable,args,cwd=worker_command()
                self.assertEqual(Path(executable),(Path(root)/'MotorSimWorker.exe').resolve())
                self.assertEqual(args,[]);self.assertEqual(Path(cwd),Path(root).resolve())

    def test_build_identity_and_diagnostics_outside_resources(self):
        self.assertEqual(build_info()['app_version'],APP_VERSION)
        with tempfile.TemporaryDirectory() as root,patch.dict(os.environ,LOCALAPPDATA=root):
            first=diagnostic('controlado uno');second=diagnostic('controlado dos')
            self.assertNotEqual(first,second);self.assertIn('controlado uno',first.read_text(encoding='utf-8'))
            self.assertEqual(first.parent,Path(root)/'MotorSim/Diagnostico')

    def test_optional_timings_v1_controlled_clock_and_historical_read(self):
        with tempfile.TemporaryDirectory() as root:
            folder=Path(root);path=result_fixture(folder);old=path.read_bytes()
            result=load_result(path)
            self.assertNotIn('timings',result['manifest']);self.assertEqual(path.read_bytes(),old)
            summary=json.loads((folder/'summary.json').read_text())['result']
            summary['last_two_cycles']=[];summary['partial']['samples']=result['samples']['partial']
            with patch('motorsim.reference_results.time.monotonic',side_effect=[10.,10.25,10.5]):
                timing=save_result(folder,summary,'cancelled',reference_inputs(),{},
                    timing_context=dict(setup_seconds=.2,started=9.))
            self.assertEqual(timing,dict(setup_seconds=.2,writing_seconds=.25,integration_seconds=.1,wall_seconds=1.5))
            loaded=load_result(path);self.assertEqual(loaded['manifest']['version'],1)
            self.assertEqual(loaded['manifest']['timings'],timing)

    def test_worker_imports_no_qt(self):
        code='import sys;import motorsim.reference_run;assert not any(k.startswith(("PySide6","shiboken6")) for k in sys.modules)'
        subprocess.run([sys.executable,'-c',code],check=True)


class DistributionWindowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])

    def test_interface_timings_only_current_result_and_permission_error(self):
        w=MainWindow();v=w.simulation_view
        try:
            with tempfile.TemporaryDirectory() as root:
                path=result_fixture(Path(root));r=load_result(path)
                r['manifest']['timings']=dict(setup_seconds=.1,writing_seconds=.1,integration_seconds=.1,wall_seconds=.3)
                original=path.read_bytes();v._started=10
                v._finished_manifest=None
                v._record_timing(r);self.assertEqual(path.read_bytes(),original)
                v._finished_manifest=path.resolve()
                with patch('motorsim.simulation_view.time.monotonic',return_value=12):v._record_timing(r)
                self.assertEqual(load_result(path)['manifest']['timings']['interface_wall_seconds'],2)
                with patch('motorsim.simulation_view.write_json',side_effect=PermissionError('controlado')):
                    with self.assertRaises(PermissionError):v._record_timing(r)
        finally:w.dirty=False;w.close();w.deleteLater()

    def test_forced_stop_keeps_diagnostic_and_does_not_kill_other_process(self):
        w=MainWindow();v=w.simulation_view
        try:
            with tempfile.TemporaryDirectory() as root,patch.dict(os.environ,LOCALAPPDATA=root):
                child=MagicMock();child.processId.return_value=123;child.program.return_value='MotorSimWorker.exe'
                v.process=child;v.output=Path(root)/'resultado';v._stderr=b'controlled stderr'
                v.progress_label.setText('Ciclos: 0; RHS: 3048')
                v._kill_if_active(MagicMock());child.kill.assert_not_called()
                v._kill_if_active(child);child.kill.assert_called_once();self.assertTrue(v.forced)
                logs=list((Path(root)/'MotorSim/Diagnostico').glob('*.txt'));self.assertEqual(len(logs),1)
                text=logs[0].read_text(encoding='utf-8');self.assertIn('3048',text);self.assertIn('123',text);self.assertIn('controlled stderr',text)
                v.process=None
        finally:v.process=None;w.dirty=False;w.close();w.deleteLater()

    def test_unwritable_target_does_not_start_or_destroy_previous_selection(self):
        w=MainWindow();v=w.simulation_view
        try:
            with patch('motorsim.simulation_view.new_output_path',side_effect=PermissionError('Sin permisos — prueba controlada')):
                v.start()
            self.assertFalse(v.active);self.assertTrue(v.run_button.isEnabled())
            self.assertIn('Sin permisos',v.error_label.text())
        finally:w.dirty=False;w.close();w.deleteLater()

    def test_absent_or_failed_worker_preserves_coherent_state(self):
        w=MainWindow();v=w.simulation_view
        try:
            with tempfile.TemporaryDirectory() as root,patch.dict(os.environ,LOCALAPPDATA=root):
                with patch('motorsim.simulation_view.worker_command',side_effect=FileNotFoundError('Falta auxiliar')):
                    v.start(output=Path(root)/'absent')
                self.assertFalse(v.active);self.assertIn('Falta auxiliar',v.error_label.text())
                with patch('motorsim.simulation_view.worker_command',return_value=(str(Path(root)/'missing.exe'),[],root)):
                    v.start(output=Path(root)/'failure')
                for _ in range(100):
                    if not v.active:break
                    QTest.qWait(10)
                self.assertFalse(v.active);self.assertIsNone(v.result)
                self.assertTrue(v.run_button.isEnabled());self.assertFalse(v.cancel_button.isEnabled())
                self.assertIn('auxiliar de cálculo',v.error_label.text())
                self.assertEqual(len(list((Path(root)/'MotorSim/Diagnostico').glob('*.txt'))),1)
        finally:w.dirty=False;w.close();w.deleteLater()


if __name__=='__main__':unittest.main()
