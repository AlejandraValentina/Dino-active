"""Contrato de la vista de resultados 4T; lectura declarativa, sin solver."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from pathlib import Path
import unittest

from PySide6.QtWidgets import QApplication

from motorsim.desktop.four_stroke_results import FourStrokeCurve, FourStrokeResultsPage
from motorsim.simulation import FOUR_LAYOUT

APP = QApplication.instance() or QApplication([])


def fake_result():
    cylinder = FOUR_LAYOUT.cylinder
    rows = []
    for index, angle in enumerate((0.0, 10.0, 20.0)):
        volume = [1e-6, 2e-6 + index * 1e-7, 3e-6]
        pressure = [[100000.0, 300.0, 1.0] for _ in range(3)]
        pressure[cylinder] = [1_000_000.0 + index * 100_000.0, 800.0, 1.0]
        rows.append({"angle_deg": angle, "V_m3": volume, "p_T_Y": pressure})
    return {
        "manifest": {"model_version": "three-cv-0d-prescribed-heat-720-v1"},
        "status": "converged",
        "result": {
            "cycles": [{"cycle": 7, "W_C_J": 50.5, "p_max_Pa": 2_600_000.0}],
            "seconds": 15.2,
            "peak_process_MiB": 47.0,
        },
        "samples": {"cycles": [rows]},
    }


class FourStrokeResultsTests(unittest.TestCase):
    def test_show_result_populates_summary_and_curves(self):
        page = FourStrokeResultsPage()
        page.show_result(fake_result())
        self.assertEqual(page.status.text(), "converged")
        self.assertEqual(page.cycles.text(), "1")
        self.assertIn("50.5", page.work.text())
        self.assertIn("2600", page.pmax.text())
        self.assertIn("15.2", page.seconds.text())
        self.assertIn("three-cv", page.model.text())
        self.assertEqual(len(page.pv.points), 3)
        self.assertEqual(len(page.angle.points), 3)
        self.assertAlmostEqual(page.pv.points[0][0], 2.0)
        self.assertAlmostEqual(page.pv.points[0][1], 1000.0)
        self.assertIn("no es validación", page.notice.text().lower())

    def test_clear_result_removes_points(self):
        page = FourStrokeResultsPage()
        page.show_result(fake_result())
        page.clear_result()
        self.assertIsNone(page.result)
        self.assertEqual(page.pv.points, [])
        self.assertEqual(page.angle.points, [])
        self.assertIn("Sin resultado", page.status.text())

    def test_load_manifest_missing_file_shows_error(self):
        page = FourStrokeResultsPage()
        self.assertFalse(page.load_manifest(Path("no-existe/manifest.json")))
        self.assertTrue(page.error.text())
        self.assertIsNone(page.result)

    def test_curve_handles_empty_and_nonempty_points(self):
        curve = FourStrokeCurve("x", "x", "y")
        self.assertEqual(curve.points, [])
        curve.set_points([(1.0, 2.0), (2.0, 3.0)])
        self.assertEqual(len(curve.points), 2)

    def test_load_real_4t_manifest_when_available(self):
        path = (Path(__file__).resolve().parents[1] / "results" / "simulacion-2t"
                / "cuatro-tiempos-20260916" / "R2" / "gui-sweep" / "point-01"
                / "manifest.json")
        if not path.is_file():
            self.skipTest("resultado 4T histórico no disponible")
        page = FourStrokeResultsPage()
        self.assertTrue(page.load_manifest(path))
        self.assertEqual(page.status.text(), "converged")
        self.assertTrue(page.pv.points)
        self.assertTrue(page.angle.points)


if __name__ == "__main__":
    unittest.main()
