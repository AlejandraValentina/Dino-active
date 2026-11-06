"""Contratos de UI 4T: geometría, válvulas y conductos, sin ejecutar solver."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import unittest

from PySide6.QtWidgets import QApplication

from motorsim.desktop.four_stroke_context import FourStrokeContext
from motorsim.desktop.four_stroke_workspace import (FourStrokeDuctsPage,
                                                     FourStrokeGeometryPage,
                                                     FourStrokeValvesPage,
                                                     FourStrokeWorkspace,
                                                     REFERENCE_BANNER)

APP = QApplication.instance() or QApplication([])


class FourStrokeWorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.context = FourStrokeContext()
        self.workspace = FourStrokeWorkspace(self.context)

    def test_reference_banner_and_status_are_visible(self):
        self.assertIn("SYNTHETIC_REFERENCE_0D", REFERENCE_BANNER)
        self.assertIn("NOT_VALIDATED", REFERENCE_BANNER)
        self.assertEqual(self.workspace.tabs.count(), 3)
        self.assertIn("completo", self.workspace.status.text())

    def test_geometry_apply_updates_project(self):
        page = FourStrokeGeometryPage(self.context)
        page.name.setText("4T de prueba")
        page.bore.setText("56")
        page.stroke.setText("58")
        page.rod.setText("104")
        page.compression.setText("9")
        page.rpm.setText("3200")
        self.assertTrue(page.apply())
        self.assertEqual(self.context.project.name, "4T de prueba")
        self.assertEqual(self.context.project.bore_mm, 56)
        self.assertEqual(self.context.project.stroke_mm, 58)
        self.assertEqual(self.context.project.rod_length_mm, 104)
        self.assertEqual(self.context.project.compression_ratio, 9)
        self.assertEqual(self.context.project.rpm, 3200)
        self.assertTrue(self.context.dirty)

    def test_geometry_invalid_text_does_not_update(self):
        page = FourStrokeGeometryPage(self.context)
        before = self.context.project
        page.bore.setText("no-numero")
        self.assertFalse(page.apply())
        self.assertTrue(page.error.text())
        self.assertEqual(self.context.project, before)
        self.assertFalse(self.context.dirty)

    def test_empty_geometry_is_saved_but_not_runnable(self):
        page = FourStrokeGeometryPage(self.context)
        page.bore.setText("")
        self.assertTrue(page.apply())
        self.assertIsNone(self.context.project.bore_mm)
        self.assertFalse(self.context.is_runnable)
        self.assertIn("No calculable", self.workspace.status.text())

    def test_valves_apply_and_invalid_text(self):
        page = FourStrokeValvesPage(self.context)
        page.fields["intake"]["seat_mm"].setText("26")
        page.fields["intake"]["throat_mm"].setText("22")
        self.assertTrue(page.apply())
        self.assertEqual(self.context.project.intake.seat_mm, 26)
        self.assertEqual(self.context.project.intake.throat_mm, 22)
        before = self.context.project
        page.fields["exhaust"]["duration_deg"].setText("texto")
        self.assertFalse(page.apply())
        self.assertTrue(page.error.text())
        self.assertEqual(self.context.project, before)

    def test_ducts_apply_and_remove(self):
        page = FourStrokeDuctsPage(self.context)
        page.intake.table.setRowCount(0)
        page.intake.add_row("Tubo I", 120, 22, 22)
        page.exhaust.table.setRowCount(0)
        page.exhaust.add_row("Tubo E", 90, 18, 18)
        self.assertTrue(page.apply())
        self.assertEqual(len(self.context.project.ducts.intake), 1)
        self.assertEqual(self.context.project.ducts.intake[0].name, "Tubo I")
        self.assertEqual(self.context.project.ducts.intake[0].length_mm, 120)
        self.assertEqual(len(self.context.project.ducts.exhaust), 1)

    def test_duct_invalid_number_does_not_update(self):
        page = FourStrokeDuctsPage(self.context)
        page.intake.table.setRowCount(0)
        page.intake.add_row("Tubo I", "largo", 22, 22)
        before = self.context.project
        self.assertFalse(page.apply())
        self.assertTrue(page.error.text())
        self.assertEqual(self.context.project, before)

    def test_workspace_refresh_after_open_new(self):
        self.context.update(name="Cambiado")
        self.workspace.refresh(self.context.project)
        self.assertEqual(self.workspace.geometry.name.text(), "Cambiado")
        self.context.new_project(name="Nuevo")
        APP.processEvents()
        self.assertEqual(self.workspace.geometry.name.text(), "Nuevo")
        self.assertIn("completo", self.workspace.status.text())


if __name__ == "__main__":
    unittest.main()
