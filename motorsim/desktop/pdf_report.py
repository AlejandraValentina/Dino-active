"""PDF presentation for self-contained engineering reports.

This module only renders an already generated HTML document; it never
recomputes results or changes provenance.
"""
from __future__ import annotations

import re
from pathlib import Path

_SVG = re.compile(r"<svg\b.*?</svg>", re.IGNORECASE | re.DOTALL)
_DETAILS = re.compile(r"<details\b.*?</details>", re.IGNORECASE | re.DOTALL)


def pdf_safe_html(document: str) -> str:
    """Return HTML that Qt's rich-text engine can paginate for PDF."""
    text = _SVG.sub(
        '<p class="empty">Gráfico interactivo disponible en la exportación HTML.</p>',
        str(document),
    )
    text = _DETAILS.sub("", text)
    return text


def write_html_pdf(path, document: str, *, title: str = "Informe técnico Dino") -> Path:
    """Write an HTML report to PDF using Qt's document paginator."""
    from PySide6.QtCore import QMarginsF
    from PySide6.QtGui import QPageSize, QPdfWriter, QTextDocument
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance()
    if app is None:
        raise RuntimeError("La exportación PDF requiere una aplicación Qt activa")
    target = Path(path)
    writer = QPdfWriter(str(target))
    writer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
    writer.setPageMargins(QMarginsF(12, 12, 12, 12))
    writer.setTitle(title)
    text = QTextDocument()
    text.setHtml(pdf_safe_html(document))
    text.print_(writer)
    writer = None
    app.processEvents()
    if not target.is_file() or target.stat().st_size == 0:
        raise OSError("No se pudo generar el PDF")
    return target
