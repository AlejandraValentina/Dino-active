"""CP1 packaged/source acceptance: workflows only, no solver or scientific claim."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys


def _fake_batch_checks(root: Path) -> dict:
    from PySide6.QtCore import QObject, Signal
    from motorsim.desktop.batch_queue import FourStrokeBatchQueue
    from motorsim.four_stroke_project import starter_project

    class Fake(QObject):
        finished = Signal(object)
        failed = Signal(str)

        def __init__(self):
            super().__init__()
            self.running = False
            self.cancelled = False
            self.rpms = None

        def start(self, rpms, output=None):
            self.rpms = list(rpms)
            self.running = True

        def cancel(self):
            self.cancelled = True
            self.running = False
            self.finished.emit({"cancelled": True, "series": None})

        def shutdown(self, timeout_ms=10000):
            if self.running:
                self.cancel()
            return True

        def complete(self, series):
            self.running = False
            self.finished.emit({"cancelled": False, "series": Path(series)})

    created = []

    def factory():
        value = Fake(); created.append(value); return value

    queue = FourStrokeBatchQueue(starter_project(rpm=3000), path=root / "batch-queue.json",
                                 execution_factory=factory)
    queue.add_curve([2500, 3000]); queue.add_curve([3000, 3500])
    queue.start(300)
    created[0].complete(root / "series-1.json")
    created[1].complete(root / "series-2.json")
    return {"run_state": queue.state,
            "all_done": all(item["status"] == "DONE" for item in queue.items),
            "persisted": (root / "batch-queue.json").is_file()}


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    args.output.mkdir(parents=True, exist_ok=False)
    os.environ["DINO_TEST_SETTINGS_ROOT"] = str(args.output / "settings")
    os.environ["DINO_ARTIFACT_ROOT"] = str(args.output / "artifacts")

    from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox
    from unittest.mock import patch
    from motorsim.desktop.app import DinoDesktopWindow
    from motorsim.desktop.legacy_ux import comparison_guide_text, legacy_import_text
    from motorsim.desktop.onboarding import OnboardingDialog, first_steps_status
    from motorsim.desktop.project_bundles import import_bundle, write_project_bundle
    from motorsim.desktop.services import new_design_project
    from motorsim.desktop.technical_report import write_technical_report_pdf

    app = QApplication.instance() or QApplication(["DinoCP1Acceptance"])
    app.setApplicationName("Dino Desktop")
    checks = {}
    window = DinoDesktopWindow(new_design_project("cp1-acceptance"))
    try:
        original = window.context.engine()
        changed = json.loads(json.dumps(original)); changed["display_name"] += " aceptación"
        window.context.replace_engine(changed)
        undone = window.context.undo() and window.context.engine() == original
        redone = window.context.redo() and window.context.engine()["display_name"] == changed["display_name"]
        checks["undo_redo"] = bool(undone and redone and window.undo_action.isEnabled())

        dataset = {"points": [{
            "variant_id": "A", "rpm": 3000.0, "status": "COMPLETE",
            "classification": "PERIOD_1", "periodicity": "PERIOD_1",
            "cycles_completed": 10, "brake_power": 10.0,
            "brake_power_status": "DEFINED", "brake_torque": 30.0,
            "brake_torque_status": "DEFINED", "BMEP": 200.0,
            "BMEP_status": "DEFINED", "run_id": "cp1-run",
            "engine_identity_sha256": "a" * 64, "identity_sha256": "b" * 64,
            "result_sha256": "c" * 64, "result_artifact_sha256": "d" * 64,
            "run_directory": "acceptance/run",
        }], "experimental_validation": "NOT_PERFORMED"}
        pdf_path = args.output / "technical-report.pdf"
        write_technical_report_pdf(pdf_path, dataset, source_kind="EXPLORATORY",
                                   generated_at="fixed")
        checks["pdf"] = pdf_path.read_bytes().startswith(b"%PDF") and pdf_path.stat().st_size > 1000
        checks["pdf_button"] = hasattr(window.results, "export_report_pdf_button")

        onboarding = OnboardingDialog(window)
        checks["onboarding_guide"] = "Guía breve de inicio" in onboarding.browser.toHtml()
        checks["first_steps"] = len(first_steps_status(window)) == 3
        onboarding.close()

        bundle_project = new_design_project("cp1-acceptance-bundle")
        bundle = write_project_bundle(args.output / "acceptance.dinobundle", bundle_project,
                                      family="2T")
        imported = import_bundle(bundle, args.output / "imported-bundle")
        checks["portable_bundle"] = (imported["project"]["project_id"] ==
                                     "cp1-acceptance-bundle")
        checks["bundle_hash"] = Path(imported["project_path"]).is_file()

        checks["comparison_guide"] = "No compare familias distintas" in comparison_guide_text("2T")
        checks["legacy_notice"] = "No se promueve" in legacy_import_text(
            args.output / "legacy.json", classification="LEGACY_UNVERIFIED")
        checks["legacy_control"] = window.native_four_stroke.results.compare_guide_button.text() == "Guía de comparación"
        checks.update(_fake_batch_checks(args.output / "batch"))
        checks["batch_button"] = window.four_stroke_curve.batch_button.text() == "Cola de curvas…"
    finally:
        window.context.dirty = False
        window.four_stroke_context.dirty = False
        window.native_four_stroke.context.dirty = False
        window.close()
        app.processEvents()

    receipt = {"schema": "DINO_CP1_ACCEPTANCE_V1", "checks": checks,
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
