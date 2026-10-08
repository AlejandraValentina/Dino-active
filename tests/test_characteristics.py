import json
import math
import tempfile
import unittest
from pathlib import Path

from motorsim.project import NUMERIC_FIELDS, Project, ProjectError, displacements, parse_number
from motorsim.storage import load_project, save_project


class CharacteristicsTests(unittest.TestCase):
    def test_empty_and_decimal_inputs(self):
        for field in NUMERIC_FIELDS:
            self.assertIsNone(parse_number('  ', field))
        for text in ('54.123456789', '54,123456789', '5.4123456789e1'):
            self.assertEqual(parse_number(text, 'bore_mm'), 54.123456789)
        self.assertEqual(parse_number('2', 'cylinder_count'), 2)

    def test_invalid_numeric_inputs_are_not_absent(self):
        for field in NUMERIC_FIELDS:
            for text in ('0', '-1', 'NaN', 'inf', '1,234.5', '1.234,5', '1 234', 'abc'):
                with self.subTest(field=field, text=text), self.assertRaises(ProjectError):
                    parse_number(text, field)
        for text in ('1', '1.0', '0,9', '1e999'):
            with self.assertRaises(ProjectError):
                parse_number(text, 'compression_ratio')
        for text in ('2.0', '2,5', '2e1'):
            with self.assertRaises(ProjectError):
                parse_number(text, 'cylinder_count')

    def test_json_rejects_wrong_types_nonfinite_and_invalid_values(self):
        for field in NUMERIC_FIELDS:
            values = [True, '2', [], 0, -1, math.inf, math.nan]
            if field == 'cylinder_count':
                values.append(2.0)
            if field == 'compression_ratio':
                values.append(1)
            for value in values:
                with self.subTest(field=field, value=value), self.assertRaises(ProjectError):
                    Project.from_dict({**Project().to_dict(), field: value})
        for field in ('manufacturer', 'model', 'notes'):
            with self.assertRaises(ProjectError):
                Project.from_dict({**Project().to_dict(), field: None})

    def test_displacement_dependencies(self):
        per, total = displacements(80, 90, 4)
        self.assertAlmostEqual(float(per), math.pi * 80**2 * 90 / 4000)
        self.assertAlmostEqual(float(total), float(per) * 4)
        self.assertEqual(displacements(80, 90, None), (per, None))
        self.assertEqual(displacements(80, 90, -1), (per, None))
        for invalid in (None, 0, math.inf, math.nan):
            self.assertEqual(displacements(invalid, 90, 4), (None, None))
            self.assertEqual(displacements(80, invalid, 4), (None, None))
        self.assertTrue(displacements(1e308, 1e308, 4)[1].is_finite())

    def test_v1_read_does_not_write_and_explicit_save_upgrades(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'old.json'
            original = b'{"format_version":1,"name":"Antiguo","cycle":"4T"}'
            path.write_bytes(original)
            project = load_project(path)
            self.assertEqual(project, Project('Antiguo', '4T'))
            self.assertEqual(path.read_bytes(), original)
            save_project(path, project)
            self.assertEqual(json.loads(path.read_text(encoding='utf-8'))['format_version'], 6)

    def test_complete_and_incomplete_persistence(self):
        complete = Project('Prueba', '4T', 'Marca á', 'Modelo', 4, 80.123456789,
                           90.123456789, 150.123456789, 10.123456789, 'Notas\nsegunda línea')
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'motor.json'
            for project in (complete, Project(), Project(bore_mm=54.123456789)):
                save_project(path, project)
                self.assertEqual(load_project(path), project)
                data = json.loads(path.read_text(encoding='utf-8'))
                self.assertEqual(data['bore_mm'], project.bore_mm)
                self.assertEqual(data['cylinder_count'], project.cylinder_count)
