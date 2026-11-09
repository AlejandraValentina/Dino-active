"""A2-03: vínculo persistente entre proyecto 4T 0D, configuración y curva RPM."""
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from motorsim.four_stroke_project import (CURVE_REFERENCE_SCHEMA,
                                           FOUR_MODEL_VERSION,
                                           FourStrokeProjectError,
                                           assess_curve_reference,
                                           load_project, project_identity,
                                           save_project, starter_project,
                                           validate_curve_reference,
                                           with_curve_reference)
from motorsim.reference_results import project_inputs
from motorsim.sweep import execute_sweep


def common_inputs(project, rpm=2500):
    return project_inputs(project.to_project(),
                          {"kind": "project", "project_name": project.name,
                           "source_path": None, "dirty": False}, rpm=rpm)


def stopped_index(project, rpms=(2500, 3000), series_id="a" * 32):
    return {
        "format": "motorsim-rpm-sweep", "version": 1, "series_id": series_id,
        "common_inputs": common_inputs(project, rpms[0]), "rpms": list(rpms),
        "state": "stopped", "reason": "Serie sintética parcial",
        "integration_seconds": 0.0, "wall_seconds": 0.0,
        "points": [{"rpm": rpm, "state": "not_executed", "reason": "No ejecutado: prueba",
                    "result": None, "run_id": None, "manifest_sha256": None,
                    "timings": None} for rpm in rpms],
    }


def link(project, series_dir, project_dir, *, status="stopped", series_id="a" * 32,
         rpms=(2500, 3000)):
    target = series_dir / "series.json"
    return {
        "schema": CURVE_REFERENCE_SCHEMA,
        "series_path": target.relative_to(project_dir).as_posix(),
        "series_sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
        "series_id": series_id,
        "project_sha256": project_identity(project),
        "status": status,
        "model_version": FOUR_MODEL_VERSION,
        "created_at": "2026-11-09T00:00:00+00:00",
        "rpms": list(rpms),
    }


def converged_series(folder, project, rpms=(2500, 3000), series_id="b" * 32):
    stored = {}

    def run_point(point_folder, cancelled, report, *, inputs):
        point_folder.mkdir()
        (point_folder / "manifest.json").write_text("DOUBLE", encoding="utf-8")
        stored[str(point_folder / "manifest.json")] = {
            "inputs": inputs, "status": "converged",
            "manifest": {"run_id": "double", "model_version": FOUR_MODEL_VERSION},
            "result": {"seconds": 0.1, "stop": "control de prueba", "cycles": []},
        }
        report({"event": "finished", "timings": {
            "setup_seconds": 0.01, "writing_seconds": 0.02,
            "integration_seconds": 0.1, "wall_seconds": 0.13}})

    class FixedUUID:
        def __init__(self, value):
            self.hex = value

    request = {"common_inputs": common_inputs(project, rpms[0]), "rpms": list(rpms)}
    with patch("motorsim.sweep.load_result",
               side_effect=lambda path: stored[str(path)]), \
            patch("motorsim.sweep.uuid.uuid4", return_value=FixedUUID(series_id)):
        execute_sweep(folder, threading.Event(), lambda event: None, request,
                      run_point=run_point)
    return stored


class FourStrokeCurveReferenceTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.project_dir = Path(self.folder.name) / "proyecto"
        self.project_dir.mkdir()
        self.project_path = self.project_dir / "motor.dino4t.json"
        self.project = starter_project(rpm=3000)
        save_project(self.project_path, self.project)
        self.series_dir = self.project_dir / "curves" / ("a" * 32)
        self.series_dir.mkdir(parents=True)
        (self.series_dir / "series.json").write_text(
            json.dumps(stopped_index(self.project)), encoding="utf-8")

    def test_identity_is_stable_when_a_reference_is_linked(self):
        identity = project_identity(self.project)
        reference = link(self.project, self.series_dir, self.project_dir)
        linked = with_curve_reference(self.project, reference)
        self.assertEqual(project_identity(linked), identity)
        self.assertEqual(len(linked.curve_references), 1)
        self.assertEqual(linked.curve_references[0]["series_id"], "a" * 32)

    def test_same_series_replaces_instead_of_duplicating(self):
        reference = link(self.project, self.series_dir, self.project_dir)
        linked = with_curve_reference(self.project, reference)
        again = with_curve_reference(linked, reference)
        self.assertEqual(len(again.curve_references), 1)

    def test_roundtrip_preserves_reference_and_legacy_files_still_load(self):
        reference = link(self.project, self.series_dir, self.project_dir)
        linked = with_curve_reference(self.project, reference)
        save_project(self.project_path, linked)
        reopened = load_project(self.project_path)
        self.assertEqual(reopened.curve_references, linked.curve_references)
        self.assertEqual(project_identity(reopened), project_identity(self.project))
        legacy = self.project.to_dict()
        self.assertNotIn("curve_references", legacy)
        self.assertEqual(load_project(self._write_legacy(legacy)).curve_references, ())

    def _write_legacy(self, data):
        path = self.project_dir / "legacy.dino4t.json"
        path.write_text(json.dumps(data), encoding="utf-8")
        return path

    def test_invalid_reference_shapes_are_rejected(self):
        reference = link(self.project, self.series_dir, self.project_dir)
        broken = [
            dict(reference, series_path=str(self.series_dir / "series.json")),
            dict(reference, series_path="curves/../series.json"),
            dict(reference, status="running"),
            dict(reference, series_sha256="x" * 64),
            dict(reference, rpms=[3000, 2500]),
            dict(reference, rpms=[2500, 3000, 3400]),
            dict(reference, model_version="otro"),
        ]
        for item in broken:
            with self.subTest(item=item):
                with self.assertRaises(FourStrokeProjectError):
                    validate_curve_reference(item)

    def test_assessment_distinguishes_partial_stale_missing_and_corrupt(self):
        reference = link(self.project, self.series_dir, self.project_dir)
        linked = with_curve_reference(self.project, reference)
        fresh = assess_curve_reference(linked, reference, base_dir=self.project_dir)
        self.assertEqual(fresh["state"], "FRESH_PARTIAL")
        self.assertEqual(fresh["series"]["index"]["rpms"], [2500, 3000])

        edited = replace(linked, bore_mm=60.0)
        stale = assess_curve_reference(edited, reference, base_dir=self.project_dir)
        self.assertEqual(stale["state"], "STALE_PROJECT")

        unbound = assess_curve_reference(linked, reference)
        self.assertEqual(unbound["state"], "UNBOUND_PROJECT")

        target = self.project_dir / reference["series_path"]
        original = target.read_bytes()
        target.write_text("alterado", encoding="utf-8")
        corrupt = assess_curve_reference(linked, reference, base_dir=self.project_dir)
        self.assertEqual(corrupt["state"], "CORRUPT")

        target.write_bytes(original)
        target.unlink()
        missing = assess_curve_reference(linked, reference, base_dir=self.project_dir)
        self.assertEqual(missing["state"], "UNAVAILABLE")

    def test_converged_series_is_complete_only_when_every_point_converged(self):
        series_id = "b" * 32
        folder = self.project_dir / "curves" / series_id
        stored = converged_series(folder, self.project, series_id=series_id)
        with patch("motorsim.sweep.load_result",
                   side_effect=lambda path: stored[str(path)]):
            index = json.loads((folder / "series.json").read_text(encoding="utf-8"))
            self.assertEqual(index["series_id"], series_id)
            reference = link(self.project, folder, self.project_dir,
                             status="converged", series_id=series_id)
            linked = with_curve_reference(self.project, reference)
            assessment = assess_curve_reference(linked, reference,
                                                base_dir=self.project_dir)
        self.assertEqual(assessment["state"], "FRESH_COMPLETE")
        self.assertEqual(assessment["issues"], [])

    def test_running_series_is_stale_and_never_complete(self):
        index = stopped_index(self.project)
        index.update(state="running", reason="En curso")
        index["points"][0].update(state="running", reason="En ejecución")
        (self.series_dir / "series.json").write_text(json.dumps(index), encoding="utf-8")
        reference = link(self.project, self.series_dir, self.project_dir)
        linked = with_curve_reference(self.project, reference)
        assessment = assess_curve_reference(linked, reference,
                                            base_dir=self.project_dir)
        self.assertEqual(assessment["state"], "STALE_IN_PROGRESS")
        self.assertIsNone(assessment["series"])


if __name__ == "__main__":
    unittest.main()
