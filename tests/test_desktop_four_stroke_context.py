"""Contrato del contexto desktop 4T; sin solver ni procesos."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import json
from pathlib import Path
import tempfile
import unittest

import desktop_qsettings_isolation  # noqa: F401
from PySide6.QtWidgets import QApplication

from motorsim.desktop.four_stroke_context import FourStrokeContext
from motorsim.four_stroke_project import (FourStrokeProjectError, load_project,
                                           starter_project)
from motorsim.project import Valve

APP = QApplication.instance() or QApplication([])


class FourStrokeContextTests(unittest.TestCase):
    def test_starter_state_is_clean_and_runnable(self):
        context = FourStrokeContext()
        self.assertFalse(context.dirty)
        self.assertIsNone(context.path)
        self.assertTrue(context.is_runnable)
        self.assertEqual(context.execution_errors(), [])

    def test_update_replaces_project_and_marks_dirty(self):
        context = FourStrokeContext()
        changes = []
        context.changed.connect(lambda: changes.append(True))
        updated = context.update(bore_mm=56.0, rpm=3200)
        self.assertEqual(updated.bore_mm, 56.0)
        self.assertEqual(context.project.rpm, 3200)
        self.assertTrue(context.dirty)
        self.assertEqual(len(changes), 1)

    def test_invalid_or_unknown_update_does_not_mutate(self):
        context = FourStrokeContext()
        before = context.project
        with self.assertRaises(FourStrokeProjectError):
            context.update(bore_mm=0)
        with self.assertRaises(FourStrokeProjectError):
            context.update(unknown_field=1)
        self.assertEqual(context.project, before)
        self.assertFalse(context.dirty)

    def test_save_and_open_roundtrip_resets_dirty_and_path(self):
        context = FourStrokeContext()
        context.update(bore_mm=55.5, intake=Valve(24, 20, 5, 5, 0, 220))
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "motor-4t.json"
            saved = context.save(path)
            self.assertEqual(saved, path)
            self.assertEqual(context.path, path)
            self.assertFalse(context.dirty)
            self.assertEqual(load_project(path), context.project)
            opened = FourStrokeContext()
            opened.open(path)
            self.assertEqual(opened.project, context.project)
            self.assertEqual(opened.path, path)
            self.assertFalse(opened.dirty)

    def test_failed_open_leaves_current_project_untouched(self):
        context = FourStrokeContext()
        before = context.project
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "malo.json"
            path.write_text(json.dumps({"schema": "OTRO"}), encoding="utf-8")
            with self.assertRaises(FourStrokeProjectError):
                context.open(path)
        self.assertEqual(context.project, before)
        self.assertIsNone(context.path)

    def test_new_project_clears_path_and_makes_it_runnable(self):
        context = FourStrokeContext()
        with tempfile.TemporaryDirectory() as folder:
            context.save(Path(folder) / "previo.json")
            context.update(intake=Valve())
            self.assertFalse(context.is_runnable)
            context.new_project(name="Nuevo 4T", rpm=3000)
            self.assertIsNone(context.path)
            self.assertFalse(context.dirty)
            self.assertEqual(context.project.name, "Nuevo 4T")
            self.assertTrue(context.is_runnable)

    def test_incomplete_project_can_be_saved_but_not_run(self):
        context = FourStrokeContext()
        context.update(intake=Valve(), rpm=None)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "incompleto.json"
            context.save(path)
            self.assertIsNotNone(load_project(path))
        self.assertFalse(context.is_runnable)
        with self.assertRaises(FourStrokeProjectError):
            context.validate_for_execution()


if __name__ == "__main__":
    unittest.main()
