"""Contrato del adaptador de ejecución 4T; no ejecuta una campaña real."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from motorsim.desktop.four_stroke_context import FourStrokeContext
from motorsim.desktop.four_stroke_execution import (FourStrokeExecution,
                                                     FourStrokeRunError)
from motorsim.four_stroke_project import FOUR_MODEL_VERSION
from motorsim.project import Valve

APP = QApplication.instance() or QApplication([])


class FourStrokeExecutionTests(unittest.TestCase):
    def setUp(self):
        self.context = FourStrokeContext()

    def test_prepare_builds_4t_request_with_origin_and_rpm(self):
        adapter = FourStrokeExecution(self.context)
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "resultado"
            target, request, inputs = adapter.prepare(output)
            self.assertEqual(target, output)
            self.assertTrue(request.is_file())
            data = json.loads(request.read_text(encoding="utf-8"))
            self.assertEqual(data, inputs)
            self.assertEqual(data["model_version"], FOUR_MODEL_VERSION)
            self.assertEqual(data["project_snapshot"]["cycle"], "4T")
            self.assertEqual(data["case"]["project_geometry"]["cycle"], "4T")
            self.assertEqual(data["origin"]["project_name"], self.context.project.name)
            self.assertEqual(data["operating_point"]["rpm"], 3000)
            self.assertEqual(data["variant"]["external_links"], [0, 3])

    def test_prepare_rejects_missing_rpm_or_incomplete_valves(self):
        adapter = FourStrokeExecution(self.context)
        self.context.update(rpm=None)
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(FourStrokeRunError):
                adapter.prepare(Path(folder) / "sin-rpm")
        self.context.update(rpm=3000, intake=Valve())
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(FourStrokeRunError):
                adapter.prepare(Path(folder) / "sin-valvula")

    def test_start_supervises_fake_worker_progress_and_finished(self):
        adapter = FourStrokeExecution(self.context)
        progress, finished = [], []
        adapter.progress.connect(progress.append)
        adapter.finished.connect(finished.append)
        with tempfile.TemporaryDirectory() as folder:
            script = Path(folder) / "fake_worker.py"
            script.write_text(
                "import json,sys\n"
                "out=sys.argv[sys.argv.index('--output')+1]\n"
                "print(json.dumps({'event':'progress','cycle':1,'completed_cycles':0,"
                "'seconds':0.1,'rhs':10}),flush=True)\n"
                "print(json.dumps({'event':'finished','status':'converged',"
                "'manifest':out+'/manifest.json'}),flush=True)\n",
                encoding="utf-8",
            )
            output = Path(folder) / "salida"
            with patch("motorsim.desktop.four_stroke_execution.worker_command",
                       return_value=(sys.executable, ["-u", str(script)], folder)):
                self.assertEqual(adapter.start(output), output)
                for _ in range(300):
                    APP.processEvents()
                    QTest.qWait(10)
                    if finished:
                        break
        self.assertTrue(finished)
        self.assertEqual(finished[0]["status"], "converged")
        self.assertEqual(finished[0]["code"], 0)
        self.assertEqual(finished[0]["output"], output)
        self.assertTrue(progress)
        self.assertEqual(progress[0]["event"], "progress")
        self.assertFalse(adapter.running)

    def test_cancel_without_run_is_noop(self):
        adapter = FourStrokeExecution(self.context)
        adapter.cancel()
        self.assertFalse(adapter.running)

    def test_load_result_requires_manifest(self):
        adapter = FourStrokeExecution(self.context)
        with self.assertRaises(FourStrokeRunError):
            adapter.load_result()


if __name__ == "__main__":
    unittest.main()
