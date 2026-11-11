"""CP2 packaged/source acceptance: licensing, manual updates and privacy posture."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path

from motorsim.licensing import ed25519
from motorsim.licensing.license import sign_license


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    args.output.mkdir(parents=True, exist_ok=False)
    os.environ["DINO_TEST_SETTINGS_ROOT"] = str(args.output / "settings")
    os.environ["DINO_ARTIFACT_ROOT"] = str(args.output / "artifacts")
    os.environ["DINO_LICENSE_ROOT"] = str(args.output / "license")
    os.environ["DINO_TRIAL_DAYS"] = "7"

    from unittest.mock import patch
    from PySide6.QtWidgets import QApplication, QMessageBox, QTabWidget
    from motorsim.desktop.app import DinoDesktopWindow
    from motorsim.desktop.license_dialog import LicenseDialog
    from motorsim.desktop.product import AboutDialog, product_info
    from motorsim.desktop.services import new_design_project
    from motorsim.desktop.update_policy import check_update
    from motorsim.desktop.update_policy import load_manifest
    from motorsim.external_view import ImportDialog

    app = QApplication.instance() or QApplication(["DinoCP2Acceptance"])
    app.setApplicationName("Dino Desktop")
    window = DinoDesktopWindow(new_design_project("cp2-acceptance"))
    checks = {}
    try:
        checks["trial_visible"] = "TRIAL" in window.license_label.text()
        dialog = LicenseDialog(root=args.output / "license", public_keys={})
        checks["license_dialog"] = "TRIAL" in dialog.status.text()
        dialog.close()

        secret = os.urandom(32)
        payload = {"schema": "DINO_LICENSE_V1", "product": "Dino Desktop",
                   "license_type": "PERPETUAL", "activation": "OFFLINE",
                   "license_id": "cp2-acceptance", "customer": "Synthetic",
                   "issued_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat()}
        document = sign_license(payload, secret, "cp2-test-key")
        license_path = args.output / "cp2.dinolicense"
        license_path.write_text(json.dumps(document), encoding="utf-8")
        keys = {"cp2-test-key": ed25519.public_key(secret)}
        dialog = LicenseDialog(root=args.output / "license", public_keys=keys)
        with patch.object(QMessageBox, "information", return_value=None):
            checks["offline_activation"] = dialog.activate(license_path)
        checks["licensed_visible"] = dialog.current["state"] == "LICENSED"
        dialog.close()

        update_manifest = args.output / "update.json"
        update_manifest.write_text(json.dumps({
            "schema": "DINO_UPDATE_MANIFEST_V1", "version": "9.9.9",
            "source_commit": "a" * 40, "channel": "engineering",
            "zip_sha256": "b" * 64, "dino2t_exe_sha256": "c" * 64,
            "worker_exe_sha256": "d" * 64, "released_at": "2026-11-11T12:00:00+00:00"}), encoding="utf-8")
        update = check_update(load_manifest(update_manifest), current_version="0.1.0-rc12",
                              current_commit="0" * 40)
        checks["manual_update"] = update["status"] == "UPDATE_AVAILABLE"
        import_dialog = ImportDialog(b"rpm,value\n2500,1\n", None)
        checks["legacy_import_dialog"] = import_dialog is not None
        import_dialog.close()
        about = AboutDialog(product_info())
        tabs = about.findChild(QTabWidget)
        titles = [tabs.tabText(i) for i in range(tabs.count())]
        checks["about_license_tab"] = "Licencia" in titles and "Estado científico" in titles
        checks["about"] = about.windowTitle().startswith("Acerca")
        about.close()
    finally:
        window.context.dirty = False
        window.four_stroke_context.dirty = False
        window.native_four_stroke.context.dirty = False
        window.close()
        app.processEvents()
    receipt = {"schema": "DINO_CP2_ACCEPTANCE_V1", "checks": checks,
               "result": "PASS" if all(checks.values()) else "FAIL",
               "scientific_claims": {"calibration": "NOT_PERFORMED",
                                     "experimental_validation": "NOT_PERFORMED",
                                     "predictive_capability": "NOT_CLAIMED"}}
    path = args.output / "acceptance.json"
    path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"acceptance": receipt["result"], "receipt": str(path),
                      "checks": checks}, ensure_ascii=False))
    return 0 if receipt["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
