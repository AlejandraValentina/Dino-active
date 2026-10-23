from __future__ import annotations

import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import tempfile
import unittest
from pathlib import Path

import desktop_qsettings_isolation  # noqa: F401
from PySide6.QtWidgets import QApplication

from motorsim.desktop.new_engine_dialog import NewEngineDialog
from motorsim.desktop.services import new_design_project
from motorsim.engine_configuration import identity, validate
from motorsim.engine_project import load_project, save_project, validate_project

APP=QApplication.instance() or QApplication([])


class CommercialReadinessV1Tests(unittest.TestCase):
    def test_new_design_is_clean_and_supports_both_declared_intake_choices(self):
        for intake in ("reed","piston_port"):
            with self.subTest(intake=intake):
                project=new_design_project("new-design",{"intake_control":intake})
                validate_project(project)
                engine=project["base_engine"];validate(engine)
                native=engine["native_configuration"]
                self.assertEqual(project["result_references"],[])
                self.assertNotEqual(native["geometry_identity"].get("fixture"),"FIXTURE_A_PRIME_V1")
                self.assertEqual(native["geometry_identity"]["gas_exchange_model"]["intake_control"],intake)
                if intake=="piston_port":self.assertEqual(native["reed_petals"],[])
                self.assertEqual(engine["provenance"]["configuration_source"]["classification"],"SYNTHETIC_ASSUMPTION")

    def test_creation_dialog_saves_input_provenance_and_project_recovers(self):
        dialog=NewEngineDialog()
        dialog.project_name.setText("guided-engine")
        dialog.inputs["bore_mm"].setValue(50.0)
        dialog.inputs["stroke_mm"].setValue(54.0)
        dialog.inputs["rod_length_mm"].setValue(110.0)
        dialog.inputs["volume_bdc_cm3"].setValue(100.0)
        dialog.inputs["cylinder_compression_ratio"].setValue(8.0)
        dialog.inputs["reference_rpm"].setValue(5000.0)
        dialog.sources["bore_mm"].setCurrentIndex(0)
        dialog.sources["stroke_mm"].setCurrentIndex(1)
        dialog._create()
        self.assertIsNotNone(dialog.project)
        engine=dialog.project["base_engine"]
        self.assertEqual(engine["provenance"]["design_inputs"]["bore_mm"]["classification"],"MEASURED")
        self.assertEqual(engine["provenance"]["design_inputs"]["stroke_mm"]["classification"],"ESTIMATED")
        self.assertIn("Cilindrada",dialog.derived.text())
        self.assertIn("Volumen de cámara",dialog.derived.text())
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/"guided-engine.dino2t.json"
            save_project(path,dialog.project)
            recovered=load_project(path)
            validate_project(recovered)
        self.assertEqual(recovered,dialog.project)
        self.assertEqual(identity(recovered["base_engine"]),identity(engine))


if __name__=="__main__":unittest.main()
