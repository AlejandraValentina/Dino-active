import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from motorsim.project import Project, ProjectError
from motorsim.storage import load_project, save_project


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "proyecto.json"

    def test_round_trip_utf8_both_cycles(self):
        for cycle in ("2T", "4T"):
            project = Project("  Motor de María ñ 🚗  ", cycle)
            save_project(self.path, project)
            self.assertEqual(load_project(self.path), project)
            text = self.path.read_text(encoding="utf-8")
            self.assertIn("María", text)
            self.assertEqual(json.loads(text), project.to_dict())

    def test_unreadable_malformed_and_invalid_files(self):
        for content in (b"{", b"\xff", b"[]", b"null", b"{}",
                        b'{"format_version":true,"name":"a","cycle":"2T"}'):
            self.path.write_bytes(content)
            with self.subTest(content=content), self.assertRaises(ProjectError):
                load_project(self.path)
        self.path.unlink()
        with self.assertRaises(ProjectError):
            load_project(self.path)
        with self.assertRaises(ProjectError):
            load_project(self.path.parent)
        with patch("pathlib.Path.open", side_effect=PermissionError("Acceso denegado")):
            with self.assertRaises(ProjectError):
                load_project(self.path)

    def test_write_failures_preserve_old_file_and_remove_temporary(self):
        save_project(self.path, Project("Anterior", "2T"))
        original = self.path.read_bytes()
        for target in ("motorsim.storage.json.dump", "motorsim.storage.os.fsync",
                       "motorsim.storage.os.replace"):
            with self.subTest(target=target):
                with patch(target, side_effect=OSError("Fallo de escritura")):
                    with self.assertRaises(ProjectError):
                        save_project(self.path, Project("Nuevo", "4T"))
                self.assertEqual(self.path.read_bytes(), original)
                self.assertEqual(list(self.path.parent.iterdir()), [self.path])

    def test_invalid_data_or_missing_destination_preserves_file(self):
        save_project(self.path, Project())
        original = self.path.read_bytes()
        with self.assertRaises(ProjectError):
            save_project(self.path, Project(" ", "2T"))
        self.assertEqual(self.path.read_bytes(), original)
        with self.assertRaises(ProjectError):
            save_project(self.path.parent / "no-existe" / "p.json", Project())
