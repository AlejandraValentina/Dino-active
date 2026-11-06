"""Smoke real opcional de la curva 4T; se activa con DINO_RUN_4T_SMOKE=1."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from pathlib import Path
import tempfile
import unittest

from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from motorsim.desktop.four_stroke_context import FourStrokeContext
from motorsim.desktop.four_stroke_curve import FourStrokeCurveExecution

APP = QApplication.instance() or QApplication([])


@unittest.skipUnless(os.environ.get("DINO_RUN_4T_SMOKE") == "1",
                     "smoke real 4T desactivado; usar DINO_RUN_4T_SMOKE=1")
class FourStrokeCurveSmokeTests(unittest.TestCase):
    def test_real_three_point_curve(self):
        context = FourStrokeContext()
        adapter = FourStrokeCurveExecution(context)
        finished = []
        adapter.finished.connect(finished.append)
        with tempfile.TemporaryDirectory() as folder:
            adapter.start([2500, 3000, 3500], Path(folder) / "curva")
            for _ in range(6000):
                APP.processEvents()
                QTest.qWait(50)
                if finished:
                    break
        self.assertTrue(finished, "la curva 4T no terminó")
        result = finished[0]
        self.assertIsNone(result["error"])
        self.assertIsNotNone(result["series"])
        series = result["series"]
        self.assertEqual(series["index"]["rpms"], [2500, 3000, 3500])
        self.assertEqual(len(series["results"]), 3)
        for rpm, record in zip(series["index"]["rpms"], series["index"]["points"]):
            self.assertEqual(record["rpm"], rpm)
            self.assertIn(record["state"], ("converged", "not_converged", "cancelled",
                                            "not_executed", "error"))


if __name__ == "__main__":
    unittest.main()
