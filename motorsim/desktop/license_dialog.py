"""Offline license activation dialog; never blocks project access."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (QDialog, QDialogButtonBox, QFileDialog,
                               QLabel, QMessageBox, QPushButton, QVBoxLayout)

from ..licensing.license import activate_license, license_status


class LicenseDialog(QDialog):
    def __init__(self, parent=None, *, root=None, public_keys=None):
        super().__init__(parent)
        self.root = root
        self.public_keys = public_keys
        self.setWindowTitle("Licencia de Dino Desktop")
        self.resize(640, 420)
        layout = QVBoxLayout(self)
        title = QLabel("Licencia perpetua · activación offline")
        title.setStyleSheet("font-size: 17px; font-weight: 600;")
        layout.addWidget(title)
        self.status = QLabel()
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.detail = QLabel()
        self.detail.setWordWrap(True)
        layout.addWidget(self.detail)
        note = QLabel("Un error de activación no bloquea proyectos ni resultados. "
                      "La licencia del producto es independiente de la versión y de "
                      "la validación científica.")
        note.setWordWrap(True)
        layout.addWidget(note)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        activate = QPushButton("Activar licencia…")
        activate.clicked.connect(self.activate)
        buttons.addButton(activate, QDialogButtonBox.ButtonRole.ActionRole)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)
        self.refresh()

    def refresh(self):
        status = license_status(root=self.root, public_keys=self.public_keys)
        self.current = status
        self.status.setText(status.get("label", "SIN LICENCIA"))
        lines = [f"Producto: {status.get('product', 'Dino Desktop')}",
                 "Licencia perpetua; sin vencimiento de uso."]
        if status.get("license_id"):
            lines.append(f"Licencia: {status['license_id']}")
            lines.append(f"Cliente: {status.get('customer') or 'No informado'}")
            lines.append(f"Emitida: {status.get('issued_at')}")
        else:
            trial = status.get("trial") or {}
            lines.append(f"TRIAL: {trial.get('days_remaining', '—')} días restantes")
            if status.get("error"):
                lines.append(f"Licencia inválida: {status['error']}")
        lines.append("Acceso a proyectos/resultados: siempre disponible.")
        self.detail.setText("\n".join(lines))
        return status

    def activate(self, path=None):
        if path is None:
            path, _ = QFileDialog.getOpenFileName(self, "Activar licencia offline",
                                                  str(Path.home()),
                                                  "Licencia Dino (*.dinolicense *.json)")
            if not path:
                return False
        try:
            status = activate_license(path, root=self.root, public_keys=self.public_keys)
        except Exception as exc:
            QMessageBox.warning(self, "Activación rechazada", str(exc))
            self.refresh()
            return False
        self.refresh()
        QMessageBox.information(self, "Licencia activada",
                                f"{status.get('label')}. La licencia es perpetua y offline.")
        return True
