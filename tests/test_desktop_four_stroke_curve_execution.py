"""Contrato del barrido RPM 4T; no ejecuta el solver real."""
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
from motorsim.desktop.four_stroke_curve import (FourStrokeCurveExecution,
                                                FourStrokeCurveRunError)

APP = QApplication.instance() or QApplication([])


def fake_series(common_inputs, rpms):
    return {
        "format": "motorsim-rpm-sweep",
        "version": 1,
        "series_id": "a" * 32,
        "common_inputs": common_inputs,
        "rpms": rpms,
        "state": "stopped",
        "reason": "Prueba sintética",
        "integration_seconds": 0.0,
        "wall_seconds": 0.0,
        "points": [
            {"rpm": rpm, "state": "not_executed", "reason": "No ejecutado: prueba",
             "result": None, "run_id": None, "manifest_sha256": None, "timings": None}
            for rpm in rpms
        ],
    }


class FourStrokeCurveExecutionTests(unittest.TestCase):
    def setUp(self):
        self.context = FourStrokeContext()

    def test_prepare_builds_sweep_request_with_4t_inputs(self):
        adapter = FourStrokeCurveExecution(self.context)
        with tempfile.TemporaryDirectory() as folder:
            target, request, rpms = adapter.prepare([2500, 3000, 3500], Path(folder) / "curva")
            self.assertEqual(target, Path(folder) / "curva")
            self.assertEqual(rpms, [2500, 3000, 3500])
            data = json.loads(request.read_text(encoding="utf-8"))
            self.assertEqual(data["rpms"], [2500, 3000, 3500])
            self.assertEqual(data["common_inputs"]["project_snapshot"]["cycle"], "4T")
            self.assertEqual(data["common_inputs"]["operating_point"]["rpm"], 2500)

    def test_prepare_rejects_non_exact_or_out_of_domain_rpms(self):
        adapter = FourStrokeCurveExecution(self.context)
        with tempfile.TemporaryDirectory() as folder:
            for rpms in ([2500, 2600, 3500], [2500, 3000, 3000], [2400, 3000],
                         [2500, 3000, 3501], [2500]):
                with self.assertRaises(FourStrokeCurveRunError):
                    adapter.prepare(rpms, Path(folder) / "curva")

    def test_start_supervises_fake_worker_and_loads_series(self):
        adapter = FourStrokeCurveExecution(self.context)
        progress, finished = [], []
        adapter.progress.connect(progress.append)
        adapter.finished.connect(finished.append)
        with tempfile.TemporaryDirectory() as folder:
            script = Path(folder) / "fake_curve_worker.py"
            script.write_text(
                "import json,sys\n"
                "from pathlib import Path\n"
                "out=Path(sys.argv[sys.argv.index('--output')+1]); out.mkdir(parents=True)\n"
                "req=json.loads(Path(sys.argv[sys.argv.index('--sweep-input')+1]).read_text(encoding='utf-8'))\n"
                "index={'format':'motorsim-rpm-sweep','version':1,'series_id':'a'*32,\n"
                " 'common_inputs':req['common_inputs'],'rpms':req['rpms'],'state':'stopped',\n"
                " 'reason':'Prueba sintética','integration_seconds':0.0,'wall_seconds':0.0,\n"
                " 'points':[{'rpm':rpm,'state':'not_executed','reason':'No ejecutado: prueba',\n"
                "   'result':None,'run_id':None,'manifest_sha256':None,'timings':None}\n"
                "  for rpm in req['rpms']]}\n"
                "print(json.dumps({'event':'point_start','point_index':0,'point_total':3,'rpm':2500}),flush=True)\n"
                "(out/'series.json').write_text(json.dumps(index),encoding='utf-8')\n"
                "print(json.dumps({'event':'sweep_finished','state':'stopped','path':str(out/'series.json'),\n"
                " 'integration_seconds':0.0,'wall_seconds':0.0}),flush=True)\n",
                encoding="utf-8",
            )
            output = Path(folder) / "salida"
            with patch("motorsim.desktop.four_stroke_curve.worker_command",
                       return_value=(sys.executable, ["-u", str(script)], folder)):
                self.assertEqual(adapter.start([2500, 3000, 3500], output), output)
                for _ in range(300):
                    APP.processEvents()
                    QTest.qWait(10)
                    if finished:
                        break
        self.assertTrue(finished)
        self.assertIsNone(finished[0]["error"], finished[0]["error"])
        self.assertEqual(finished[0]["status"], "stopped")
        self.assertEqual(finished[0]["code"], 0)
        self.assertIsNotNone(finished[0]["series"])
        self.assertEqual(finished[0]["series"]["index"]["rpms"], [2500, 3000, 3500])
        self.assertTrue(progress)
        self.assertEqual(progress[0]["event"], "point_start")
        self.assertFalse(adapter.running)

    def test_cancel_without_run_is_noop(self):
        adapter = FourStrokeCurveExecution(self.context)
        adapter.cancel()
        self.assertFalse(adapter.running)


if __name__ == "__main__":
    unittest.main()
