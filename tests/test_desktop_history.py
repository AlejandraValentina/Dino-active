"""CP1 undo/redo for 2T, native 4T and 4T 0D contexts."""
from copy import deepcopy
from pathlib import Path

import desktop_qsettings_isolation  # noqa: F401
from PySide6.QtWidgets import QApplication

from motorsim.desktop.app import DinoDesktopWindow
from motorsim.desktop.context import DesktopContext
from motorsim.desktop.four_stroke_context import FourStrokeContext
from motorsim.desktop.four_stroke_project import project_from_example
from motorsim.desktop.services import new_design_project
from motorsim.four_stroke_project import save_project, starter_project

APP = QApplication.instance() or QApplication([])


def changed_config(project):
    config = deepcopy(project)
    if "geometry" in config:
        config["geometry"]["bore_mm"] = float(config["geometry"]["bore_mm"]) + 1.0
    else:
        config["display_name"] = str(config["display_name"]) + " editado"
    return config


def test_2t_history_undo_redo_and_project_switch():
    context = DesktopContext(new_design_project("history-2t"))
    original = deepcopy(context.engine())
    modified = changed_config(original)
    context.replace_engine(modified)
    assert context.can_undo
    assert context.engine()["display_name"] == modified["display_name"]
    assert context.undo()
    assert context.engine() == original
    assert context.can_redo
    assert context.redo()
    assert context.engine()["display_name"] == modified["display_name"]
    context.replace_project(new_design_project("history-2t-other"))
    assert not context.can_undo and not context.can_redo


def test_native_4t_history_undo_redo():
    context = DesktopContext(project_from_example("history-native"))
    original = deepcopy(context.engine())
    modified = changed_config(original)
    context.replace_engine(modified)
    assert context.undo()
    assert context.engine() == original
    assert context.redo()
    assert context.engine()["geometry"]["bore_mm"] == modified["geometry"]["bore_mm"]


def test_history_is_bounded_and_empty_undo_is_noop():
    context = FourStrokeContext(starter_project(rpm=3000))
    assert not context.undo() and not context.redo()
    for index in range(context._history_limit + 10):
        context.update(name=f"hist-{index}")
    assert len(context._undo) == context._history_limit
    for _ in range(context._history_limit):
        assert context.undo()
    assert not context.undo()


def test_4t_0d_history_undo_redo_and_save_clears(tmp_path):
    context = FourStrokeContext(starter_project(rpm=3000), tmp_path / "hist.dino4t.json")
    original = context.project.bore_mm
    context.update(bore_mm=61.0)
    assert context.undo()
    assert context.project.bore_mm == original
    assert context.redo()
    assert context.project.bore_mm == 61.0
    context.save()
    assert not context.can_undo and not context.can_redo


def test_unified_window_routes_undo_to_active_context(tmp_path, monkeypatch):
    monkeypatch.setenv("DINO_ARTIFACT_ROOT", str(tmp_path / "artifacts"))
    window = DinoDesktopWindow(new_design_project("history-ui"))
    try:
        original = deepcopy(window.context.engine())
        window.context.replace_engine(changed_config(original))
        window._refresh_history_actions()
        assert window.undo_action.isEnabled()
        window._undo_active()
        assert window.context.engine() == original

        window._activate_engine_family("4T_REFERENCE")
        before = window.four_stroke_context.project.bore_mm
        window.four_stroke_context.update(bore_mm=62.0)
        window._refresh_history_actions()
        window._undo_active()
        assert window.four_stroke_context.project.bore_mm == before

        window._activate_engine_family("4T")
        native_original = deepcopy(window.native_four_stroke.context.engine())
        window.native_four_stroke.context.replace_engine(
            changed_config(native_original))
        window._refresh_history_actions()
        window._undo_active()
        assert window.native_four_stroke.context.engine() == native_original
    finally:
        window.context.dirty = False
        window.four_stroke_context.dirty = False
        window.native_four_stroke.context.dirty = False
        window.close()
