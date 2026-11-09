"""F15: ciclo de vida de workers Qt 4T, reserva, cancelación y cierre."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import json
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from motorsim import engine_platform
from motorsim.desktop.context import DesktopContext
from motorsim.desktop.four_stroke_context import FourStrokeContext
from motorsim.desktop.four_stroke_project import project_from_example
from motorsim.desktop.four_stroke_curve import (FourStrokeCurveExecution,
                                                FourStrokeCurveRunError)
from motorsim.desktop.four_stroke_desktop import FourStrokeSimulation, _RunTask
from motorsim.desktop.four_stroke_execution import (FourStrokeExecution,
                                                     FourStrokeRunError)
from motorsim.four_stroke_project import FourStrokeProjectError

APP = QApplication.instance() or QApplication([])


def fake_control_worker(folder):
    script = Path(folder) / "fake_control_worker.py"
    script.write_text(
        "import json,sys,time\n"
        "print(json.dumps({'event':'progress','cycle':1}),flush=True)\n"
        "for line in sys.stdin:\n"
        "    if 'cancel' in line:\n"
        "        sys.exit(130)\n"
        "time.sleep(30)\n",
        encoding="utf-8",
    )
    return script


class QtLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.context = FourStrokeContext()

    def test_execution_reservation_blocks_mutation_and_duplicate_worker(self):
        token = self.context.begin_execution("prueba")
        self.assertTrue(self.context.execution_active)
        with self.assertRaises(FourStrokeProjectError):
            self.context.update(bore_mm=55.0)
        with self.assertRaises(Exception):
            self.context.begin_execution("otra")
        self.context.end_execution(token)
        self.assertFalse(self.context.execution_active)
        self.context.update(bore_mm=55.0)
        self.assertEqual(self.context.project.bore_mm, 55.0)

    def test_save_as_is_blocked_during_execution(self):
        token = self.context.begin_execution("prueba")
        try:
            with tempfile.TemporaryDirectory() as folder:
                with self.assertRaises(FourStrokeProjectError):
                    self.context.save(Path(folder) / "otro.json")
        finally:
            self.context.end_execution(token)

    def test_point_and_curve_cannot_run_concurrently(self):
        point = FourStrokeExecution(self.context)
        curve = FourStrokeCurveExecution(self.context)
        token = self.context.begin_execution("punto 4T")
        with self.assertRaises(FourStrokeCurveRunError):
            curve.start([2500, 3000])
        self.context.end_execution(token)
        token = self.context.begin_execution("curva 4T")
        with self.assertRaises(FourStrokeRunError):
            point.start()
        self.context.end_execution(token)

    def _start_control_process(self, adapter, folder, *, start):
        script = fake_control_worker(folder)
        with patch("motorsim.desktop.four_stroke_execution.worker_command",
                   return_value=(sys.executable, ["-u", str(script)], str(folder))), \
             patch("motorsim.desktop.four_stroke_curve.worker_command",
                   return_value=(sys.executable, ["-u", str(script)], str(folder))):
            target = start(adapter, Path(folder) / "resultado")
        self.assertTrue(adapter.running)
        self.assertTrue(self.context.execution_active)
        self.assertTrue(adapter.shutdown(timeout_ms=5000))
        self.assertFalse(adapter.running)
        self.assertFalse(self.context.execution_active)
        self.assertIsNone(adapter._request_path)
        return target

    def test_point_worker_shutdown_during_execution_leaves_no_orphan(self):
        with tempfile.TemporaryDirectory() as folder:
            self._start_control_process(
                FourStrokeExecution(self.context), folder,
                start=lambda adapter, output: adapter.start(output))

    def test_curve_worker_shutdown_during_execution_leaves_no_orphan(self):
        with tempfile.TemporaryDirectory() as folder:
            self._start_control_process(
                FourStrokeCurveExecution(self.context), folder,
                start=lambda adapter, output: adapter.start([2500, 3000], output))

    def test_qthreadpool_task_is_not_auto_deleted_and_ignores_stale_tokens(self):
        task = _RunTask({}, None, 1, 1.0)
        self.assertFalse(task.autoDelete())
        simulation = FourStrokeSimulation(DesktopContext(project_from_example("qt-lifecycle")))
        with tempfile.TemporaryDirectory() as folder:
            simulation.run_dir = Path(folder)
            simulation.task = task
            simulation._task_token = task.token
            simulation._failed("stale", "must be ignored")
            self.assertIs(simulation.task, task)
            simulation._failed(task.token, "real failure")
            self.assertIsNone(simulation.task)
            self.assertIsNone(simulation._task_token)
        simulation.close()

    def test_shutdown_waits_for_running_qthreadpool_task(self):
        started = threading.Event()

        def slow_run_api(*args, **kwargs):
            started.set()
            kwargs["cancel_event"].wait(2.0)
            raise RuntimeError("cancelado para la prueba")

        simulation = FourStrokeSimulation(DesktopContext(project_from_example("qt-lifecycle-shutdown")))
        task = _RunTask({}, None, 1, 1.0)
        with tempfile.TemporaryDirectory() as folder:
            simulation.run_dir = Path(folder)
            simulation.task = task
            simulation._task_token = task.token
            token = task.token
            task.signals.failed.connect(lambda message, token=token: simulation._failed(token, message))
            with patch.object(engine_platform, "run_api", side_effect=slow_run_api):
                simulation.thread_pool.start(task)
                self.assertTrue(started.wait(2.0))
                self.assertTrue(simulation.shutdown(timeout_ms=5000))
                self.assertIsNone(simulation.task)
                QTest.qWait(20)
                APP.processEvents()
        simulation.close()


if __name__ == "__main__":
    unittest.main()
