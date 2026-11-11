"""CP2 licensing UI: visible status and offline activation without project loss."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import json
from datetime import datetime, timezone
from pathlib import Path

import desktop_qsettings_isolation  # noqa: F401
from PySide6.QtWidgets import QApplication, QMessageBox, QTabWidget

from motorsim.desktop.app import DinoDesktopWindow
from motorsim.desktop.license_dialog import LicenseDialog
from motorsim.desktop.product import AboutDialog, product_info
from motorsim.desktop.services import new_design_project
from motorsim.licensing import ed25519
from motorsim.licensing.license import sign_license

APP = QApplication.instance() or QApplication([])


def _signed(tmp_path, secret):
    payload = {"schema": "DINO_LICENSE_V1", "product": "Dino Desktop",
               "license_type": "PERPETUAL", "activation": "OFFLINE",
               "license_id": "ui-license-001", "customer": "Synthetic UI",
               "issued_at": datetime(2026, 11, 11, tzinfo=timezone.utc).isoformat()}
    document = sign_license(payload, secret, "test-ui-key")
    path = tmp_path / "ui.dinolicense"
    path.write_text(json.dumps(document), encoding="utf-8")
    return path, {"test-ui-key": ed25519.public_key(secret)}


def test_status_is_visible_and_activation_is_offline(tmp_path, monkeypatch):
    monkeypatch.setenv("DINO_LICENSE_ROOT", str(tmp_path / "license-root"))
    window = DinoDesktopWindow(new_design_project("license-ui"))
    dialog = LicenseDialog(root=tmp_path / "dialog-root", public_keys={})
    try:
        assert "TRIAL" in window.license_label.text()
        assert "TRIAL" in dialog.status.text()
        path, keys = _signed(tmp_path, os.urandom(32))
        dialog = LicenseDialog(root=tmp_path / "dialog-root", public_keys=keys)
        messages = []
        monkeypatch.setattr(QMessageBox, "information", lambda *args: messages.append(args))
        assert dialog.activate(path)
        assert dialog.current["state"] == "LICENSED"
        assert "LICENCIA PERPETUA" in dialog.status.text()
        assert messages
    finally:
        dialog.close()
        window.context.dirty = False
        window.four_stroke_context.dirty = False
        window.native_four_stroke.context.dirty = False
        window.close()


def test_about_exposes_license_tab_and_scientific_status(tmp_path, monkeypatch):
    monkeypatch.setenv("DINO_LICENSE_ROOT", str(tmp_path / "license-root"))
    info = product_info()
    dialog = AboutDialog(info)
    try:
        tabs = dialog.findChild(QTabWidget)
        titles = [tabs.tabText(index) for index in range(tabs.count())]
        assert "Licencia" in titles and "Estado científico" in titles
        assert info["scientific_status"]["experimental_validation"] == "NOT_PERFORMED"
    finally:
        dialog.close()
