"""Contrato de la página de curva RPM 4T; sin solver real."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import unittest

from PySide6.QtWidgets import QApplication

from motorsim.desktop.four_stroke_context import FourStrokeContext
from motorsim.desktop.four_stroke_curve import FourStrokeCurvePage
from motorsim.desktop.four_stroke_workspace import REFERENCE_BANNER

APP = QApplication.instance() or QApplication([])


def loaded_series():
    return {
        "index": {
            "state": "converged",
            "rpms": [2500, 3000],
            "points": [
                {"state": "converged", "result": "point-01/manifest.json",
                 "timings": {"integration_seconds": 1.2}},
                {"state": "converged", "result": "point-02/manifest.json",
                 "timings": {"integration_seconds": 1.4}},
            ],
        },
        "results": [
            {"result": {"cycles": [{"W_C_J": 10.5, "p_max_Pa": 2_000_000.0}]}},
            {"result": {"cycles": [{"W_C_J": 12.5, "p_max_Pa": 2_200_000.0}]}},
        ],
    }


class FourStrokeCurvePageTests(unittest.TestCase):
    def setUp(self):
        self.context = FourStrokeContext()
        self.page = FourStrokeCurvePage(self.context)

    def test_banner_and_default_inputs_are_reference_only(self):
        self.assertIn("SYNTHETIC_REFERENCE_0D", REFERENCE_BANNER)
        self.assertEqual(self.page.start_edit.text(), "2500")
        self.assertEqual(self.page.end_edit.text(), "3500")
        self.assertEqual(self.page.step_edit.text(), "500")
        self.assertIn("NOT_VALIDATED", self.page.findChild(type(self.page.status), "fourStrokeCurveBanner").text())

    def test_show_series_populates_table_and_plot(self):
        self.page.show_series(loaded_series())
        self.assertEqual(self.page.table.rowCount(), 2)
        self.assertEqual(self.page.table.item(0, 0).text(), "2500")
        self.assertEqual(self.page.table.item(1, 0).text(), "3000")
        self.assertEqual(self.page.table.item(0, 1).text(), "converged")
        self.assertIn("10.5", self.page.table.item(0, 2).text())
        self.assertIn("2000", self.page.table.item(0, 3).text())
        self.assertEqual(len(self.page.plot.points), 2)
        self.assertEqual(self.page.plot.points[0], (2500, 10.5))

    def test_invalid_step_keeps_inputs_and_reports_error(self):
        self.page.step_edit.setText("333")
        self.page.start_curve()
        self.assertIn("Barrido", self.page.status.text())
        self.assertEqual(self.page.step_edit.text(), "333")
        self.assertFalse(self.page.execution.running)

    def test_partial_series_marks_nonconverged_points_and_never_plots_them(self):
        loaded = loaded_series()
        loaded["index"]["state"] = "stopped"
        loaded["index"]["points"][0]["state"] = "not_converged"
        self.page.show_series(loaded)
        self.assertEqual(self.page.table.item(0, 1).text(), "not_converged")
        self.assertEqual(len(self.page.plot.points), 1)
        self.assertEqual(self.page.plot.points[0], (3000, 12.5))

    def test_clear_removes_series(self):
        self.page.show_series(loaded_series())
        self.page.clear()
        self.assertEqual(self.page.table.rowCount(), 0)
        self.assertEqual(self.page.plot.points, [])
        self.assertIn("sin barrido", self.page.status.text())


if __name__ == "__main__":
    unittest.main()
