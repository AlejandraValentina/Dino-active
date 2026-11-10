"""CP1 onboarding, synthetic examples and first-step checks."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import desktop_qsettings_isolation  # noqa: F401
from PySide6.QtWidgets import QApplication

from motorsim.desktop.app import DinoDesktopWindow
from motorsim.desktop.onboarding import (GUIDE_STEPS, OnboardingDialog,
                                         first_steps_status, guide_html,
                                         status_html)
from motorsim.desktop.services import new_design_project

APP = QApplication.instance() or QApplication([])


def test_guide_states_limits_and_five_steps():
    text = guide_html()
    assert "Guía breve de inicio" in text
    assert "no equivale a calibración, validación experimental" in text
    assert len(GUIDE_STEPS) == 5
    for title, _ in GUIDE_STEPS:
        assert title in text


def test_onboarding_dialog_can_create_a_synthetic_2t_example(tmp_path, monkeypatch):
    monkeypatch.setenv("DINO_ARTIFACT_ROOT", str(tmp_path / "artifacts"))
    window = DinoDesktopWindow(new_design_project("onboarding-host"))
    dialog = OnboardingDialog(window)
    try:
        assert "Primeros pasos" in dialog.browser.toHtml()
        dialog._create_example("new_example_2t")
        assert window.context.project["project_id"] == "demo-2t-sintetico"
        statuses = first_steps_status(window)
        assert len(statuses) == 3
        assert statuses[0]["ok"] and statuses[1]["ok"]
        assert "Verificación de primeros pasos" in status_html(window)
    finally:
        window.context.dirty = False
        window.four_stroke_context.dirty = False
        window.native_four_stroke.context.dirty = False
        dialog.close()
        window.close()


def test_examples_switch_modes_and_keep_families_separate(tmp_path, monkeypatch):
    monkeypatch.setenv("DINO_ARTIFACT_ROOT", str(tmp_path / "artifacts"))
    window = DinoDesktopWindow(new_design_project("onboarding-modes"))
    try:
        window.new_example_native_4t()
        assert window.project_mode_stack.currentIndex() == 2
        assert window.native_four_stroke.context.project["project_id"] == "demo-4t-nativo-sintetico"
        window.new_example_4t_0d()
        assert window.project_mode_stack.currentIndex() == 1
        assert window.four_stroke_context.name == "demo-4t-0d-sintetico"
        assert window.context.project["project_id"] == "onboarding-modes"
    finally:
        window.context.dirty = False
        window.four_stroke_context.dirty = False
        window.native_four_stroke.context.dirty = False
        window.close()
