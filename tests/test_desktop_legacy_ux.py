"""CP1 explicit comparison guidance and legacy import messaging."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import desktop_qsettings_isolation  # noqa: F401
from PySide6.QtWidgets import QApplication

from motorsim.desktop.app import DinoDesktopWindow
from motorsim.desktop.legacy_ux import (comparison_guide_text,
                                        legacy_import_text)
from motorsim.desktop.services import new_design_project

APP = QApplication.instance() or QApplication([])


def test_comparison_guide_keeps_exactness_and_evidence_limits():
    text = comparison_guide_text("4T nativo")
    assert "RPM exacta" in text and "contexto operativo coincidente" in text
    assert "No se interpola" in text
    assert "no demuestran mejora" in text
    assert "No compare familias distintas" in text
    assert "no es validación experimental" in text


def test_legacy_import_text_preserves_classification_and_source(tmp_path):
    source = tmp_path / "legacy-result.json"
    text = legacy_import_text(source, classification="LEGACY_UNVERIFIED",
                              detail="Resumen histórico sin trazas.")
    assert str(source) in text
    assert "LEGACY_UNVERIFIED" in text
    assert "sin modificar el original" in text
    assert "No se promueve" in text


def test_unified_and_native_comparison_views_expose_the_guide(tmp_path, monkeypatch):
    monkeypatch.setenv("DINO_ARTIFACT_ROOT", str(tmp_path / "artifacts"))
    window = DinoDesktopWindow(new_design_project("legacy-ux"))
    try:
        assert window.results.compare_guide_button.text() == "Guía de comparación"
        assert window.native_four_stroke.results.compare_guide_button.text() == "Guía de comparación"
    finally:
        window.context.dirty = False
        window.four_stroke_context.dirty = False
        window.native_four_stroke.context.dirty = False
        window.close()
