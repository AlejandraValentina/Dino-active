from __future__ import annotations

import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import desktop_qsettings_isolation  # noqa: F401
from PySide6.QtWidgets import QApplication

from motorsim.desktop.app import DinoDesktopWindow
from motorsim.desktop.new_engine_dialog import NewEngineDialog
from motorsim.desktop.context import DesktopContext
from motorsim.desktop.engine_page import EnginePage
from motorsim.desktop.execution_page import ExecutionPage
from motorsim.desktop.results_page import ResultsPage
from motorsim.desktop.preferences import repository_root_containing, settings
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

    def test_engine_page_recalculates_derived_geometry_and_applies_intake_choice(self):
        project=new_design_project("editor-engine")
        page=EnginePage(DesktopContext(project))
        self.assertIn("cámara derivada",page.derived.text())
        self.assertIn("compresión primaria",page.derived.text())
        page.intake_control.setCurrentIndex(page.intake_control.findData("piston_port"))
        page.apply()
        native=page.context.engine()["native_configuration"]
        self.assertEqual(native["geometry_identity"]["gas_exchange_model"]["intake_control"],"piston_port")
        self.assertEqual(native["reed_petals"],[])
        page.intake_control.setCurrentIndex(page.intake_control.findData("reed"))
        page.apply()
        native=page.context.engine()["native_configuration"]
        self.assertEqual(native["geometry_identity"]["gas_exchange_model"]["intake_control"],"reed")
        self.assertTrue(native["reed_petals"])


    def test_new_exploratory_run_uses_a_fresh_id_even_after_prior_run(self):
        page=ExecutionPage(DesktopContext(new_design_project("fresh-run-id")))
        with tempfile.TemporaryDirectory() as folder:
            page.artifact_root=Path(folder)
            page.run_id.setText("old-run-id")
            page._preflight=lambda: {"rpm":3000.0}
            seen=[]
            page._confirm_run=lambda run_id,resume: seen.append((run_id,resume)) or False
            with patch("motorsim.exploratory_workflow._run_directory"):
                page.start_run(resume=False)
        self.assertEqual(len(seen),1)
        self.assertFalse(seen[0][1])
        self.assertNotEqual(seen[0][0],"old-run-id")
        self.assertEqual(page.run_id.text(),seen[0][0])

    def test_project_result_references_are_imported_into_analysis(self):
        project=new_design_project("periodic-reference")
        with tempfile.TemporaryDirectory() as folder:
            result=Path(folder)/"result.json";result.write_text("{}",encoding="utf-8")
            project["result_references"]=[{
                "path":str(result),"identity_sha256":"a"*64,
                "artifact_sha256":"b"*64,"classification":"PERIODIC_EXPLORATORY"
            }]
            context=DesktopContext(project)
            with patch.object(ResultsPage,"open_runs",autospec=True) as open_runs:
                ResultsPage(context)
            open_runs.assert_called_once()
            self.assertEqual(open_runs.call_args.args[1],[result])

    def test_new_project_redirects_stale_repository_artifact_setting(self):
        settings().setValue("artifact_root",str(Path.cwd()))
        window=DinoDesktopWindow()
        self.assertIsNone(repository_root_containing(window.pages[3].artifact_root))
        self.assertFalse(window.context.project["result_references"])
        window.close()


if __name__=="__main__":unittest.main()
