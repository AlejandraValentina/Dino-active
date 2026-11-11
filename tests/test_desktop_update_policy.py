"""CP2 manual update manifest checks; no network and no auto-update."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import json
from pathlib import Path

import desktop_qsettings_isolation  # noqa: F401
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox

from motorsim.desktop.app import DinoDesktopWindow
from motorsim.desktop.services import new_design_project
from motorsim.desktop.update_policy import check_update, load_manifest, parse_version

APP = QApplication.instance() or QApplication([])


def manifest(**changes):
    data = {"schema": "DINO_UPDATE_MANIFEST_V1", "version": "0.2.0-rc1",
            "source_commit": "a" * 40, "channel": "engineering",
            "zip_sha256": "b" * 64, "dino2t_exe_sha256": "c" * 64,
            "worker_exe_sha256": "d" * 64, "released_at": "2026-11-11T12:00:00+00:00",
            "notes": "Candidato interno"}
    data.update(changes); return data


def test_manifest_version_and_hash_validation(tmp_path):
    good = manifest()
    path = tmp_path / "update.json"; path.write_text(json.dumps(good), encoding="utf-8")
    assert load_manifest(path)["version"] == "0.2.0-rc1"
    assert parse_version("0.2.0-rc1") < parse_version("0.2.0")
    for bad in (manifest(channel="nightly"), manifest(zip_sha256="not-a-hash"),
                manifest(version="v2")):
        path.write_text(json.dumps(bad), encoding="utf-8")
        try:
            load_manifest(path)
        except ValueError:
            pass
        else:
            raise AssertionError(f"invalid manifest accepted: {bad}")


def test_check_update_returns_status_without_network():
    assert check_update(manifest(source_commit="a" * 40), current_version="0.1.0-rc12",
                        current_commit="a" * 40)["status"] == "UP_TO_DATE"
    assert check_update(manifest(), current_version="0.1.0-rc12",
                        current_commit="b" * 40)["status"] == "UPDATE_AVAILABLE"
    assert check_update(manifest(version="0.0.1"), current_version="0.1.0-rc12",
                        current_commit="b" * 40)["status"] == "OLDER_CANDIDATE"


def test_update_check_is_manual_from_help_menu(tmp_path, monkeypatch):
    monkeypatch.setenv("DINO_ARTIFACT_ROOT", str(tmp_path / "artifacts"))
    path = tmp_path / "update.json"
    path.write_text(json.dumps(manifest()), encoding="utf-8")
    window = DinoDesktopWindow(new_design_project("update-check"))
    try:
        messages = []
        monkeypatch.setattr(QMessageBox, "information", lambda *args: messages.append(args))
        monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *args: (str(path), "JSON"))
        assert window.check_for_updates()
        assert messages and "Actualización disponible" in messages[0][1]
    finally:
        window.context.dirty = False
        window.four_stroke_context.dirty = False
        window.native_four_stroke.context.dirty = False
        window.close()
