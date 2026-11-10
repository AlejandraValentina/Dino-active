"""CP1 portable project bundles with hash checks and legacy preservation."""
import hashlib
import json
import os
import zipfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import desktop_qsettings_isolation  # noqa: F401
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox

from motorsim.desktop.app import DinoDesktopWindow
from motorsim.desktop.project_bundles import (import_bundle, inspect_bundle,
                                              write_project_bundle)
from motorsim.desktop.services import new_design_project
from motorsim.desktop.four_stroke_project import project_from_example
from motorsim.four_stroke_project import (FOUR_MODEL_VERSION, project_identity,
                                          save_project, starter_project,
                                          with_curve_reference)

APP = QApplication.instance() or QApplication([])


def _digest(raw):
    return hashlib.sha256(raw).hexdigest()


def test_2t_bundle_round_trip_and_reference_paths(tmp_path):
    project = new_design_project("bundle-2t")
    project["result_references"] = [{
        "path": str(tmp_path / "result.json"),
        "identity_sha256": "a" * 64,
        "artifact_sha256": "b" * 64,
        "classification": "LEGACY_UNVERIFIED",
    }]
    (tmp_path / "result.json").write_text('{"result": 1}', encoding="utf-8")
    source = write_project_bundle(tmp_path / "bundle.dinobundle", project, family="2T")
    manifest, _ = inspect_bundle(source)
    assert manifest["family"] == "2T"
    assert manifest["legacy_reference_count"] == 1
    imported = import_bundle(source, tmp_path / "imported")
    assert imported["project"]["project_id"] == "bundle-2t"
    reference = imported["project"]["result_references"][0]
    assert reference["classification"] == "LEGACY_UNVERIFIED"
    assert os.path.isfile(reference["path"])
    assert Path(reference["path"]).is_relative_to(tmp_path / "imported")


def test_native_4t_bundle_copies_run_and_trace(tmp_path):
    project = project_from_example("bundle-native")
    result = tmp_path / "summary.json"
    trace = tmp_path / "run.json"
    result.write_text('{"status":"completed"}', encoding="utf-8")
    trace.write_text('{"run":"trace"}', encoding="utf-8")
    project["run_references"] = [{
        "schema": "DINO4T_RUN_REFERENCE_V2",
        "run_id": "run-1",
        "path": str(result),
        "run_manifest_path": str(trace),
        "run_manifest_sha256": "c" * 64,
        "result_sha256": "d" * 64,
        "config_sha256": "e" * 64,
        "status": "completed",
        "periodicity_status": "PERIODIC_CONVERGED",
        "variant_id": "base",
    }]
    source = write_project_bundle(tmp_path / "native.dinobundle", project, family="4T_native")
    imported = import_bundle(source, tmp_path / "native-imported")
    reference = imported["project"]["run_references"][0]
    assert os.path.isfile(reference["path"])
    assert os.path.isfile(reference["run_manifest_path"])
    assert Path(reference["path"]).is_relative_to(tmp_path / "native-imported")


def test_4t_0d_bundle_copies_curve_series(tmp_path):
    project = starter_project(name="bundle-4t0d", rpm=3000)
    series_id = "1" * 32
    series_path = f"curves/{series_id}/series.json"
    series_file = tmp_path / series_path
    series_file.parent.mkdir(parents=True)
    series_file.write_text('{"schema":"MOTORSIM_4T_REFERENCE_SERIES_V1","rpms":[3000,3500]}',
                           encoding="utf-8")
    reference = {
        "schema": "MOTORSIM_4T_REFERENCE_CURVE_V1",
        "series_path": series_path,
        "series_sha256": _digest(series_file.read_bytes()),
        "series_id": series_id,
        "project_sha256": project_identity(project),
        "status": "converged",
        "model_version": FOUR_MODEL_VERSION,
        "created_at": "2026-01-01T00:00:00+00:00",
        "rpms": [3000, 3500],
    }
    project = with_curve_reference(project, reference)
    project_file = tmp_path / "project.dino4t.json"
    save_project(project_file, project)
    source = write_project_bundle(tmp_path / "0d.dinobundle", project, family="4T_0D",
                                  project_path=project_file)
    imported = import_bundle(source, tmp_path / "0d-imported")
    imported_series = tmp_path / "0d-imported" / series_path
    assert imported_series.is_file()
    assert imported["project"].curve_references[0]["series_path"] == series_path


def test_bundle_rejects_tampered_project_hash(tmp_path):
    project = new_design_project("bundle-tamper")
    source = write_project_bundle(tmp_path / "tamper.dinobundle", project, family="2T")
    with zipfile.ZipFile(source) as bundle:
        payload = {name: bundle.read(name) for name in bundle.namelist()}
    payload["project.json"] = b'{"tampered": true}\n'
    tampered = tmp_path / "tampered.dinobundle"
    with zipfile.ZipFile(tampered, "w") as bundle:
        for name, raw in payload.items():
            bundle.writestr(name, raw)
    try:
        inspect_bundle(tampered)
    except ValueError as exc:
        assert "hash del proyecto" in str(exc)
    else:
        raise AssertionError("tampered bundle was accepted")


def test_unified_window_exports_and_imports_a_2t_bundle(tmp_path, monkeypatch):
    monkeypatch.setenv("DINO_ARTIFACT_ROOT", str(tmp_path / "artifacts"))
    window = DinoDesktopWindow(new_design_project("bundle-ui"))
    bundle_path = tmp_path / "ui.dinobundle"
    try:
        monkeypatch.setattr(QFileDialog, "getSaveFileName",
                            lambda *args: (str(bundle_path), "Bundle"))
        monkeypatch.setattr(QMessageBox, "information", lambda *args: None)
        window.export_project_bundle()
        assert bundle_path.is_file()
        monkeypatch.setattr(QFileDialog, "getOpenFileName",
                            lambda *args: (str(bundle_path), "Bundle"))
        monkeypatch.setattr(QFileDialog, "getExistingDirectory",
                            lambda *args: str(tmp_path / "imported"))
        window.import_project_bundle()
        assert window.context.project["project_id"] == "bundle-ui"
        assert window.project_mode_stack.currentIndex() == 0
    finally:
        window.context.dirty = False
        window.four_stroke_context.dirty = False
        window.native_four_stroke.context.dirty = False
        window.close()
