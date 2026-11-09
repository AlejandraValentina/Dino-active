"""A2-03: la curva 4T 0D se vincula, persiste y se reabre sin mezclar 4T nativo."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from dataclasses import replace
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
                                                FourStrokeCurvePage)
from motorsim.four_stroke_project import assess_curve_reference, starter_project

APP = QApplication.instance() or QApplication([])


def stopped_series(common_inputs, rpms):
    return {
        "format": "motorsim-rpm-sweep", "version": 1, "series_id": "a" * 32,
        "common_inputs": common_inputs, "rpms": list(rpms),
        "state": "stopped", "reason": "Serie sintética parcial",
        "integration_seconds": 0.0, "wall_seconds": 0.0,
        "points": [{"rpm": rpm, "state": "not_executed", "reason": "No ejecutado: prueba",
                    "result": None, "run_id": None, "manifest_sha256": None,
                    "timings": None} for rpm in rpms],
    }


FAKE_WORKER = (
    "import json,sys\n"
    "from pathlib import Path\n"
    "out=Path(sys.argv[sys.argv.index('--output')+1]); out.mkdir(parents=True)\n"
    "req=json.loads(Path(sys.argv[sys.argv.index('--sweep-input')+1]).read_text(encoding='utf-8'))\n"
    "index={'format':'motorsim-rpm-sweep','version':1,'series_id':'a'*32,\n"
    " 'common_inputs':req['common_inputs'],'rpms':req['rpms'],'state':'stopped',\n"
    " 'reason':'Serie sintética parcial','integration_seconds':0.0,'wall_seconds':0.0,\n"
    " 'points':[{'rpm':rpm,'state':'not_executed','reason':'No ejecutado: prueba',\n"
    "   'result':None,'run_id':None,'manifest_sha256':None,'timings':None}\n"
    "  for rpm in req['rpms']]}\n"
    "print(json.dumps({'event':'point_start','point_index':0,'point_total':2,'rpm':2500}),flush=True)\n"
    "(out/'series.json').write_text(json.dumps(index),encoding='utf-8')\n"
    "print(json.dumps({'event':'sweep_finished','state':'stopped','path':str(out/'series.json'),\n"
    " 'integration_seconds':0.0,'wall_seconds':0.0}),flush=True)\n"
)


class CurveBindingTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name)
        self.project_path = self.root / "proyecto" / "motor.dino4t.json"
        self.project_path.parent.mkdir()
        self.context = FourStrokeContext(starter_project(rpm=3000), self.project_path)
        self.context.save()

    def _run_curve(self):
        adapter = FourStrokeCurveExecution(self.context)
        finished = []
        adapter.finished.connect(finished.append)
        script = self.root / "fake_curve_worker.py"
        script.write_text(FAKE_WORKER, encoding="utf-8")
        output = self.root / "salida"
        with patch("motorsim.desktop.four_stroke_curve.worker_command",
                   return_value=(sys.executable, ["-u", str(script)], str(self.root))):
            adapter.start([2500, 3000], output)
            for _ in range(400):
                APP.processEvents()
                QTest.qWait(10)
                if finished:
                    break
        self.assertTrue(finished, "la curva falsa no terminó")
        return finished[0]

    def _manual_finish(self, *, change_project=False, save=True):
        adapter = FourStrokeCurveExecution(self.context)
        if not save:
            self.context.path = None
        output = self.root / "manual"
        target, request, _ = adapter.prepare([2500, 3000], output)
        target.mkdir(parents=True)
        request_data = json.loads(request.read_text(encoding="utf-8"))
        (target / "series.json").write_text(
            json.dumps(stopped_series(request_data["common_inputs"], request_data["rpms"])),
            encoding="utf-8")
        adapter._series_path = target / "series.json"
        adapter._process = None
        if change_project:
            self.context.project = replace(self.context.project, bore_mm=60.0)
        finished = []
        adapter.finished.connect(finished.append)
        adapter._on_finished(0, 0)
        self.assertTrue(finished)
        return finished[0]

    def test_curve_is_copied_linked_persisted_and_reopened(self):
        result = self._run_curve()
        self.assertIsNone(result["error"])
        self.assertIsNotNone(result["reference"])
        self.assertEqual(result["assessment"]["state"], "FRESH_PARTIAL")
        self.assertEqual(len(self.context.project.curve_references), 1)
        reference = self.context.project.curve_references[0]
        self.assertTrue((self.project_path.parent / reference["series_path"]).is_file())
        self.context.save()

        reopened = FourStrokeContext()
        reopened.open(self.project_path)
        self.assertEqual(reopened.project.curve_references, (reference,))
        assessment = assess_curve_reference(reopened.project, reference,
                                            base_dir=self.project_path.parent)
        self.assertEqual(assessment["state"], "FRESH_PARTIAL")

        page = FourStrokeCurvePage(reopened)
        self.assertEqual(page.table.rowCount(), 2)
        self.assertIn("parcial restaurada", page.status.text())
        self.assertEqual(len(page.plot.points), 0)

        reopened.update(bore_mm=61.0)
        page.refresh_references()
        self.assertEqual(page.table.rowCount(), 0)
        self.assertIn("no vigente", page.status.text())

    def test_curve_from_changed_configuration_is_not_linked(self):
        result = self._manual_finish(change_project=True)
        self.assertTrue(result["stale"])
        self.assertIsNone(result["reference"])
        self.assertEqual(self.context.project.curve_references, ())
        self.assertIn("cambió durante", result["attach_error"])

    def test_unsaved_project_keeps_curve_but_does_not_bind_it(self):
        result = self._manual_finish(save=False)
        self.assertFalse(result["stale"])
        self.assertIsNone(result["reference"])
        self.assertEqual(self.context.project.curve_references, ())
        self.assertIn("Guardá", result["attach_error"])

    def test_reference_curves_stay_separate_from_the_native_4t_project(self):
        from motorsim.desktop.four_stroke_project import (SCHEMA, project_from_example,
                                                           validate_project)
        native = project_from_example("native-separate")
        self.assertEqual(native["schema"], SCHEMA)
        self.assertNotIn("curve_references", native)
        native["curve_references"] = []
        with self.assertRaises(ValueError):
            validate_project(native)


if __name__ == "__main__":
    unittest.main()
