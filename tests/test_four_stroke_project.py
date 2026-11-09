"""Contrato del proyecto 4T 0D de referencia para Dino."""
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from motorsim.four_stroke_project import (CLASSIFICATION, DEFAULT_RPM, SCHEMA,
                                           SCIENTIFIC_STATUS, FourStrokeProject,
                                           FourStrokeProjectError, load_project,
                                           save_project, starter_project)
from motorsim.project import Project, Valve


class FourStrokeProjectTests(unittest.TestCase):
    def test_starter_is_runnable_and_roundtrips_without_2t_fields(self):
        project = starter_project()
        self.assertEqual(project.execution_errors(), [])
        self.assertEqual(project.rpm, DEFAULT_RPM)
        self.assertEqual(project.provenance["classification"], CLASSIFICATION)
        self.assertEqual(project.provenance["scientific_status"], SCIENTIFIC_STATUS)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "motor-4t.json"
            digest = save_project(path, project)
            raw = path.read_text(encoding="utf-8")
            data = json.loads(raw)
            self.assertEqual(digest, hashlib.sha256(raw.encode("utf-8")).hexdigest())
            self.assertEqual(data["schema"], SCHEMA)
            self.assertEqual(data["cycle"], "4T")
            for forbidden in ("two_stroke_reference", "ports", "crankcase_volume_bdc_cm3"):
                self.assertNotIn(forbidden, data)
            self.assertNotIn("intake", data)  # solo existe dentro de valves/ducts 4T
            self.assertEqual(load_project(path), project)
            self.assertEqual(list(path.parent.glob("*.tmp")), [])

    def test_to_project_uses_four_stroke_and_keeps_2t_defaults_valid(self):
        project = starter_project()
        legacy = project.to_project()
        self.assertEqual(legacy.cycle, "4T")
        self.assertEqual(legacy.cylinder_count, 1)
        self.assertEqual(legacy.four_stroke.intake, project.intake)
        self.assertEqual(legacy.four_stroke.ducts, project.ducts)
        legacy.validate()

    def test_incomplete_project_can_be_saved_but_not_executed(self):
        project = replace(starter_project(), intake=Valve(), rpm=None)
        project.validate()
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "incompleto.json"
            save_project(path, project)
            self.assertEqual(load_project(path), project)
        messages = project.execution_errors()
        self.assertTrue(messages)
        self.assertTrue(any("RPM" in message for message in messages))
        with self.assertRaises(FourStrokeProjectError):
            project.validate_for_execution()

    def test_invalid_schema_version_cycle_and_extra_fields_are_rejected(self):
        data = starter_project().to_dict()
        for key, value in (("schema", "OTRO"), ("version", 2), ("cycle", "2T")):
            broken = dict(data, **{key: value})
            with self.assertRaises(FourStrokeProjectError):
                FourStrokeProject.from_dict(broken)
        extra = dict(data)
        extra["ports"] = []
        with self.assertRaises(FourStrokeProjectError):
            FourStrokeProject.from_dict(extra)
        expected = replace(starter_project(), provenance=data["provenance"])
        self.assertEqual(FourStrokeProject.from_dict(data), expected)

    def test_invalid_geometry_rpm_and_provenance_are_rejected(self):
        base = starter_project()
        for broken in (
            replace(base, cylinder_count=2),
            replace(base, bore_mm=0),
            replace(base, compression_ratio=1),
            replace(base, rod_length_mm=base.stroke_mm / 2),
            replace(base, rpm=2499),
            replace(base, rpm=3501),
            replace(base, provenance={}),
            replace(base, provenance=dict(base.provenance, model_version="otro")),
        ):
            with self.assertRaises(FourStrokeProjectError):
                broken.validate()

    def test_from_project_rejects_2t_and_preserves_4t(self):
        with self.assertRaises(FourStrokeProjectError):
            FourStrokeProject.from_project(Project(cycle="2T"))
        source = starter_project().to_project()
        recovered = FourStrokeProject.from_project(source)
        self.assertEqual(recovered.bore_mm, source.bore_mm)
        self.assertEqual(recovered.ducts, source.four_stroke.ducts)
        self.assertEqual(recovered.provenance["origin"], "import")

    def test_json_with_non_finite_number_is_rejected(self):
        data = starter_project().to_dict()
        data["geometry"]["bore_mm"] = float("nan")
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "nan.json"
            path.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaises(FourStrokeProjectError):
                load_project(path)


if __name__ == "__main__":
    unittest.main()
