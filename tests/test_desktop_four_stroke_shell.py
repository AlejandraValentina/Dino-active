"""Integración del modo 4T en el shell; no ejecuta una corrida real."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

import desktop_qsettings_isolation
from PySide6.QtWidgets import QApplication, QMessageBox

from motorsim.desktop.app import DinoDesktopWindow
from motorsim.desktop.services import new_design_project
from motorsim.four_stroke_project import load_project


APP = QApplication.instance() or QApplication([])


class FourStrokeShellTests(unittest.TestCase):
    def setUp(self):
        self.window = DinoDesktopWindow(new_design_project("shell-4t"))

    def tearDown(self):
        self.window.four_stroke_context.dirty = False
        self.window.context.dirty = False
        self.window.close()

    def test_shell_keeps_2t_workspaces_and_starts_in_2t(self):
        self.assertEqual(self.window.mode_stack.count(), 3)
        self.assertEqual(self.window.project_mode_stack.currentIndex(), 0)
        self.assertTrue(self.window.windowTitle().startswith("Dino 2T"))
        self.assertEqual(self.window.four_stroke_workspace.tabs.count(), 3)
        self.assertEqual(self.window.four_stroke_tabs.count(), 3)
        self.assertEqual(self.window.four_stroke_tabs.tabText(2), "Curva RPM 4T")

    def test_switch_to_4t_updates_title_indicator_and_back(self):
        self.window.show_four_stroke_mode()
        self.assertEqual(self.window.project_mode_stack.currentIndex(), 1)
        self.assertTrue(self.window.windowTitle().startswith("Dino 4T 0D —"))
        self.assertIn("NOT_VALIDATED", self.window.four_stroke_indicator.text())
        self.window.show_two_stroke_mode()
        self.assertEqual(self.window.project_mode_stack.currentIndex(), 0)
        self.assertTrue(self.window.windowTitle().startswith("Dino 2T"))

    def test_new_4t_discards_dirty_context_and_switches_mode(self):
        self.window.four_stroke_context.update(name="Borrador 4T")
        self.assertTrue(self.window.four_stroke_context.dirty)
        with patch("motorsim.desktop.app.QMessageBox.question",
                   return_value=QMessageBox.StandardButton.Discard):
            self.window.new_four_stroke_file()
        self.assertFalse(self.window.four_stroke_context.dirty)
        self.assertEqual(self.window.project_mode_stack.currentIndex(), 1)
        self.assertTrue(self.window.windowTitle().startswith("Dino 4T 0D —"))

    def test_save_and_open_4t_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "proyecto.dino4t.json"
            self.window.four_stroke_context.update(name="Guardado 4T")
            self.window.four_stroke_context.path = target
            self.assertTrue(self.window.save_four_stroke_file())
            self.assertTrue(target.is_file())
            self.assertFalse(self.window.four_stroke_context.dirty)
            self.assertEqual(load_project(target).name, "Guardado 4T")
            self.window.four_stroke_context.update(name="Otro nombre")
            with patch("motorsim.desktop.app.QMessageBox.question",
                       return_value=QMessageBox.StandardButton.Discard), \
                 patch("motorsim.desktop.app.QFileDialog.getOpenFileName",
                       return_value=(str(target), "")):
                self.window.open_four_stroke_file()
            self.assertEqual(self.window.four_stroke_context.name, "Guardado 4T")
            self.assertEqual(self.window.project_mode_stack.currentIndex(), 1)

    def test_save_as_adds_four_stroke_suffix(self):
        with tempfile.TemporaryDirectory() as tmp:
            raw = Path(tmp) / "sin_extension"
            with patch("motorsim.desktop.app.QFileDialog.getSaveFileName",
                       return_value=(str(raw), "")):
                self.assertTrue(self.window.save_four_stroke_as())
            expected = Path(str(raw) + ".dino4t.json")
            self.assertTrue(expected.is_file())
            self.assertEqual(self.window.four_stroke_context.path, expected)

    def test_run_stops_on_invalid_workspace_without_starting_worker(self):
        self.window.four_stroke_workspace.geometry.bore.setText("no-numero")
        self.window.start_four_stroke_run()
        self.assertIn("Corregí", self.window.four_stroke_status.text())
        self.assertFalse(self.window.four_stroke_execution.running)

    def test_curve_uses_same_workspace_validation(self):
        self.window.show_four_stroke_mode()
        self.window.four_stroke_curve.start_edit.setText("2500")
        self.window.four_stroke_curve.end_edit.setText("3500")
        self.window.four_stroke_curve.step_edit.setText("500")
        self.window.four_stroke_workspace.geometry.bore.setText("no-numero")
        self.window.four_stroke_curve.start_curve()
        self.assertIn("Corregí", self.window.four_stroke_curve.status.text())
        self.assertFalse(self.window.four_stroke_curve.execution.running)


if __name__ == "__main__":
    unittest.main()
