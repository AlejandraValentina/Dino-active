"""CP0 commercial hardening: product identity, diagnostics, recent projects and recovery."""
import json
from pathlib import Path
import zipfile

import desktop_qsettings_isolation  # noqa: F401
import pytest
from PySide6.QtWidgets import QApplication

from motorsim.desktop.app import DinoDesktopWindow
from motorsim.desktop.context import DesktopContext
from motorsim.desktop.four_stroke_context import FourStrokeContext
from motorsim.desktop.four_stroke_desktop import FourStrokeDesktopWindow
from motorsim.desktop.four_stroke_project import project_from_example
from motorsim.desktop.product import (AboutDialog, RecentProjects, RecoveryController,
                                      create_diagnostics_bundle, product_info)
from motorsim.desktop.services import new_design_project
from motorsim.four_stroke_project import save_project, starter_project

APP = QApplication.instance() or QApplication([])


def test_product_info_exposes_commercial_identity_and_scientific_limits():
    info = product_info()
    assert info["product"] == "Dino Desktop"
    assert info["version"]
    assert info["project_schemas"]["4T_native"]
    assert info["scientific_status"] == {
        "calibration": "NOT_PERFORMED",
        "experimental_validation": "NOT_PERFORMED",
        "predictive_capability": "NOT_CLAIMED",
    }
    assert isinstance(info["licenses"], list)
    dialog = AboutDialog(info)
    try:
        assert "Dino Desktop" in dialog.windowTitle()
    finally:
        dialog.close()


def test_diagnostics_bundle_is_self_contained_and_optional_project(tmp_path, monkeypatch):
    monkeypatch.setenv("DINO_ARTIFACT_ROOT", str(tmp_path / "artifacts"))
    target = create_diagnostics_bundle(
        tmp_path / "diagnostico.zip", include_project=True,
        project={"project_id": "demo", "engine_family": "2T"},
        settings_snapshot={"artifact_root": "E:/safe"}, log_limit=0)
    assert target.is_file()
    with zipfile.ZipFile(target) as bundle:
        names = set(bundle.namelist())
        assert {"product.json", "build.json", "system.json", "settings.json",
                "project.json", "README.txt"} <= names
        assert json.loads(bundle.read("project.json"))["project_id"] == "demo"
        assert "token" not in bundle.read("settings.json").decode().lower()
    without = create_diagnostics_bundle(tmp_path / "sin-proyecto.zip",
                                        include_project=False, log_limit=0)
    with zipfile.ZipFile(without) as bundle:
        assert "project.json" not in bundle.namelist()


def test_recent_projects_are_bounded_and_pruned(tmp_path, monkeypatch):
    monkeypatch.setenv("DINO_ARTIFACT_ROOT", str(tmp_path / "artifacts"))
    recent = RecentProjects()
    recent.clear("2T")
    paths = []
    for index in range(10):
        path = tmp_path / f"proyecto-{index}.json"
        path.write_text("{}", encoding="utf-8")
        paths.append(path)
        recent.add("2T", path)
    items = recent.items("2T")
    assert len(items) == RecentProjects.LIMIT
    assert items[0] == str(paths[-1].resolve())
    paths[-1].unlink()
    remaining = recent.prune("2T")
    assert str(paths[-1].resolve()) not in remaining


def test_recovery_controller_writes_and_clears_without_touching_original(tmp_path, monkeypatch):
    monkeypatch.setenv("DINO_ARTIFACT_ROOT", str(tmp_path / "artifacts"))
    context = FourStrokeContext(starter_project(rpm=3000), tmp_path / "original.dino4t.json")
    context.save()
    original = context.path.read_bytes()
    context.update(bore_mm=61.0)
    controller = RecoveryController("test", context, lambda: context.project.to_dict(),
                                    interval_ms=600_000)
    try:
        target = controller.autosave()
        assert target is not None and target.is_file()
        entries = RecoveryController.pending("test")
        assert entries and entries[0]["project"]["geometry"]["bore_mm"] == 61.0
        assert context.path.read_bytes() == original
        controller.clear()
        assert not target.exists()
    finally:
        controller.timer.stop()


def test_main_window_exposes_about_diagnostics_and_recent_menus(tmp_path, monkeypatch):
    monkeypatch.setenv("DINO_ARTIFACT_ROOT", str(tmp_path / "artifacts"))
    window = DinoDesktopWindow(new_design_project("commercial-menu"))
    try:
        labels = []
        for top in window.menuBar().actions():
            menu = top.menu()
            if menu is not None:
                labels.extend(action.text() for action in menu.actions())
        assert "Acerca de Dino…" in labels
        assert "Exportar diagnóstico…" in labels
        assert "Proyectos recientes 2T" in labels
        assert "Proyectos recientes 4T 0D" in labels
    finally:
        window.context.dirty = False
        window.four_stroke_context.dirty = False
        window.close()


def test_native_4t_window_exposes_about_and_diagnostics(tmp_path, monkeypatch):
    monkeypatch.setenv("DINO_ARTIFACT_ROOT", str(tmp_path / "artifacts"))
    window = FourStrokeDesktopWindow(project_from_example("commercial-native"))
    try:
        labels = []
        for top in window.menuBar().actions():
            menu = top.menu()
            if menu is not None:
                labels.extend(action.text() for action in menu.actions())
        assert "Acerca de Dino…" in labels
        assert "Exportar diagnóstico…" in labels
        assert "Proyectos recientes 4T" in labels
    finally:
        window.context.dirty = False
        window.close()
