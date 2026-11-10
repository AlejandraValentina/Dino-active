"""Shared 2T / native 4T / reference 4T navigation contracts."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from pathlib import Path

import desktop_qsettings_isolation
from PySide6.QtWidgets import QApplication

from motorsim.desktop.app import DinoDesktopWindow
from motorsim.desktop.four_stroke_project import project_from_example as native_project
from motorsim.desktop.services import new_design_project
from motorsim.engine_project import save_project, load_project
from motorsim.four_stroke_project import (
    starter_project as reference_project, save_project as save_reference,
)
from motorsim.power_curve import plan_rpm_range
from motorsim.project import ProjectError

APP = QApplication.instance() or QApplication([])


def _window():
    return DinoDesktopWindow(new_design_project("unified-navigation"))


def _close(window):
    window.context.dirty = False
    window.four_stroke_context.dirty = False
    window.native_four_stroke.context.dirty = False
    window.close()
    window.deleteLater()
    APP.processEvents()


def test_shared_header_navigation_preserves_independent_project_state():
    window = _window()
    try:
        assert window.centralWidget() is not window.project_mode_stack
        assert window.project_mode_stack.count() == 3
        assert window.engine_selector.currentData() == "2T"
        assert window.mode_stack.count() == 3

        window.engine_selector.setCurrentIndex(window.engine_selector.findData("4T"))
        assert window.project_mode_stack.currentWidget() is window.native_four_stroke
        assert window.engine_selector.currentData() == "4T"
        assert "4T nativo" in window.windowTitle()
        assert "DINO4T_API_V1" in window.native_four_stroke.banner.text()
        assert not window.import_config_action.isEnabled()
        assert not window.export_config_action.isEnabled()
        assert not window.context_bar.isVisibleTo(window)

        window.set_workspace_mode(2)
        assert window.native_four_stroke.stack.currentIndex() == 2
        window.set_workspace_mode(1)
        assert window.native_four_stroke.stack.currentWidget() is window.native_four_stroke.results
        window.set_workspace_mode(0)
        assert window.native_four_stroke.stack.currentIndex() == 0

        window.show_four_stroke_mode()
        assert window.project_mode_stack.currentIndex() == 1
        assert window.engine_selector.currentData() == "4T_REFERENCE"
        assert "NOT_VALIDATED" in window.four_stroke_indicator.text()
        window.set_workspace_mode(2)
        assert window.four_stroke_tabs.currentWidget() is window.four_stroke_curve

        window.show_two_stroke_mode()
        assert window.project_mode_stack.currentIndex() == 0
        assert window.engine_selector.currentData() == "2T"
        assert window.context.project["project_id"] == "unified-navigation"
    finally:
        _close(window)


def test_native_four_stroke_open_and_save_uses_same_window(tmp_path):
    window = _window()
    try:
        target = tmp_path / "motor.dino.json"
        original = native_project("motor-unificado")
        save_project(target, original)

        window._open(target)
        assert window.project_mode_stack.currentIndex() == 2
        assert window.native_four_stroke.context.project["project_id"] == "motor-unificado"
        assert window.native_four_stroke.context.path == target
        assert not hasattr(window, "_four_stroke_window")
        assert window.save_file() is True
        assert load_project(target)["schema"] == "DINO_DESKTOP_ENGINE_PROJECT_4T_V1"

        window.show_two_stroke_mode()
        assert window.context.project["project_id"] == "unified-navigation"
        window.show_native_four_stroke_mode()
        assert window.native_four_stroke.context.project["project_id"] == "motor-unificado"
    finally:
        _close(window)


def test_unified_open_recognizes_separate_synthetic_reference_schema(tmp_path):
    window = _window()
    try:
        target = tmp_path / "referencia.dino4t.json"
        save_reference(target, reference_project("ref-isolada"))
        window._open(target)
        assert window.project_mode_stack.currentIndex() == 1
        assert window.four_stroke_context.project.name == "ref-isolada"
        assert window.native_four_stroke.context.project["schema"] == "DINO_DESKTOP_ENGINE_PROJECT_4T_V1"
    finally:
        _close(window)


def test_wide_2t_curve_is_configurable_inside_public_domain():
    grid = plan_rpm_range(2500, 13000, 500)
    assert len(grid) == 22
    assert grid[0] == 2500 and grid[-1] == 13000
    try:
        plan_rpm_range(500, 13000, 500)
    except (ProjectError, ValueError):
        pass
    else:
        raise AssertionError("El UI no debe habilitar RPM que el contrato científico rechaza")
