"""CP0 features integrated with the unified 2T / 4T 0D / native 4T shell."""
from pathlib import Path
from unittest.mock import patch

import desktop_qsettings_isolation  # noqa: F401
from PySide6.QtWidgets import QApplication, QMessageBox

from motorsim.desktop.app import DinoDesktopWindow
from motorsim.desktop.four_stroke_project import project_from_example
from motorsim.desktop.product import AboutDialog
from motorsim.desktop.services import new_design_project
from motorsim.engine_project import save_project as save_engine_project
from motorsim.four_stroke_project import save_project as save_reference_project, starter_project

APP = QApplication.instance() or QApplication([])


def make_window(tmp_path, monkeypatch, name="commercial-unified"):
    monkeypatch.setenv("DINO_ARTIFACT_ROOT", str(tmp_path / "artifacts"))
    return DinoDesktopWindow(new_design_project(name))


def test_unified_shell_exposes_three_modes_and_commercial_help(tmp_path, monkeypatch):
    window = make_window(tmp_path, monkeypatch)
    try:
        selector = window.engine_selector
        assert selector.count() == 3
        assert [selector.itemData(i) for i in range(3)] == ["2T", "4T", "4T_REFERENCE"]
        for family, index in (("2T", 0), ("4T_REFERENCE", 1), ("4T", 2)):
            window._activate_engine_family(family)
            assert window.project_mode_stack.currentIndex() == index
        labels = []
        for top in window.menuBar().actions():
            menu = top.menu()
            if menu is not None:
                labels.extend(action.text() for action in menu.actions())
        assert "Acerca de Dino…" in labels
        assert "Exportar diagnóstico…" in labels
        assert "Proyectos recientes 2T" in labels
        assert "Proyectos recientes 4T 0D" in labels
        assert "Proyectos recientes 4T nativo" in labels
    finally:
        window.context.dirty = False
        window.four_stroke_context.dirty = False
        window.native_four_stroke.context.dirty = False
        window.close()


def test_diagnostics_uses_the_active_project_in_all_three_modes(tmp_path, monkeypatch):
    window = make_window(tmp_path, monkeypatch, "diagnostics-unified")
    captured = []
    try:
        def fake_bundle(path, *, include_project=None, project=None, **kwargs):
            captured.append(project)
            return Path(path)
        with patch("motorsim.desktop.app.create_diagnostics_bundle", side_effect=fake_bundle), \
             patch("motorsim.desktop.app.QFileDialog.getSaveFileName",
                   return_value=(str(tmp_path / "diagnostico.zip"), "")), \
             patch("motorsim.desktop.app.QMessageBox.question",
                   return_value=QMessageBox.StandardButton.No), \
             patch("motorsim.desktop.app.QMessageBox.information", return_value=None):
            window._activate_engine_family("2T")
            window.export_diagnostics()
            window._activate_engine_family("4T_REFERENCE")
            window.export_diagnostics()
            window._activate_engine_family("4T")
            window.export_diagnostics()
        assert captured[0]["project_id"] == window.context.project["project_id"]
        assert captured[1]["name"] == window.four_stroke_context.project.name
        assert captured[2]["project_id"] == window.native_four_stroke.context.project["project_id"]
    finally:
        window.context.dirty = False
        window.four_stroke_context.dirty = False
        window.native_four_stroke.context.dirty = False
        window.close()


def test_recovery_is_a_copy_in_all_three_modes(tmp_path, monkeypatch):
    window = make_window(tmp_path, monkeypatch, "recovery-unified")
    try:
        window._restore_2t_recovery({
            "project": new_design_project("recovery-2t"),
            "original_path": str(tmp_path / "original.dino2t.json")})
        assert window.context.path is None and window.context.dirty
        window._restore_4t_recovery({
            "project": starter_project(rpm=3000).to_dict(),
            "original_path": str(tmp_path / "original.dino4t.json")})
        assert window.four_stroke_context.path is None and window.four_stroke_context.dirty
        window._restore_native_recovery({
            "project": project_from_example("recovery-native"),
            "original_path": str(tmp_path / "original.dino.json")})
        assert window.native_four_stroke.context.path is None
        assert window.native_four_stroke.context.dirty
    finally:
        window.context.dirty = False
        window.four_stroke_context.dirty = False
        window.native_four_stroke.context.dirty = False
        window.close()


def test_about_dialog_is_reachable_from_the_unified_shell(tmp_path, monkeypatch):
    window = make_window(tmp_path, monkeypatch, "about-unified")
    try:
        with patch.object(AboutDialog, "exec", return_value=0) as executed:
            window.show_about()
            executed.assert_called_once()
    finally:
        window.context.dirty = False
        window.four_stroke_context.dirty = False
        window.native_four_stroke.context.dirty = False
        window.close()


def test_recent_projects_are_recorded_for_all_three_modes(tmp_path, monkeypatch):
    window = make_window(tmp_path, monkeypatch, "recent-unified")
    try:
        p2t = tmp_path / "recent-2t.dino2t.json"
        save_engine_project(p2t, new_design_project("recent-2t"))
        p0d = tmp_path / "recent-4t0d.dino4t.json"
        save_reference_project(p0d, starter_project(name="recent-4t0d", rpm=3000))
        pnative = tmp_path / "recent-native.dino.json"
        save_engine_project(pnative, project_from_example("recent-native"))
        window._open(p2t)
        window._open(p0d)
        window._open(pnative)
        assert str(p2t.resolve()) in window.recent.items("2T")
        assert str(p0d.resolve()) in window.recent.items("4T0D")
        assert str(pnative.resolve()) in window.recent.items("4Tnative")
    finally:
        window.context.dirty = False
        window.four_stroke_context.dirty = False
        window.native_four_stroke.context.dirty = False
        window.close()


def test_commercial_help_actions_have_safe_shortcuts(tmp_path, monkeypatch):
    window = make_window(tmp_path, monkeypatch, "shortcuts-unified")
    try:
        actions = {}
        for top in window.menuBar().actions():
            menu = top.menu()
            if menu is not None:
                for action in menu.actions():
                    actions[action.text()] = action
        assert actions["Acerca de Dino…"].shortcut().toString() == "F1"
        assert actions["Exportar diagnóstico…"].shortcut().toString() == "Ctrl+Shift+D"
    finally:
        window.context.dirty = False
        window.four_stroke_context.dirty = False
        window.native_four_stroke.context.dirty = False
        window.close()
