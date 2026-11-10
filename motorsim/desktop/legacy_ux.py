"""Explicit comparison guidance and legacy-import messaging."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QMessageBox


def comparison_guide_text(family: str = "2T") -> str:
    family = str(family)
    return (
        "Guía de comparación\n\n"
        "• Sólo se comparan pares con RPM exacta y contexto operativo coincidente.\n"
        "• No se interpola, ajusta ni agrega entre RPM ni entre estudios.\n"
        "• Cada punto conserva estado, periodicidad, auditoría y hashes de origen.\n"
        "• Las diferencias son del modelo; no demuestran mejora en un motor real.\n"
        "• Un punto parcial, cancelado o no convergente permanece excluido o marcado.\n"
        f"• Familia activa: {family}. No compare familias distintas (2T, 4T 0D, 4T nativo).\n"
        "• La comparación no es validación experimental ni claim predictivo."
    )


def legacy_import_text(source, *, classification: str = "LEGACY_UNVERIFIED",
                       detail: str = "") -> str:
    return (
        "Importación histórica explícita\n\n"
        f"Archivo: {Path(source)}\n"
        f"Clasificación conservada: {classification}\n"
        f"{detail}\n\n"
        "Se copiará el artefacto sin modificar el original. No se promueve a "
        "resultado verificado, periódico o comparable; conserve la fuente original."
    )


def show_comparison_guide(parent, family: str = "2T") -> None:
    QMessageBox.information(parent, "Guía de comparación", comparison_guide_text(family))


def show_legacy_import_notice(parent, source, *, classification="LEGACY_UNVERIFIED",
                              detail="") -> None:
    QMessageBox.information(parent, "Importación histórica",
                            legacy_import_text(source, classification=classification,
                                               detail=detail))
