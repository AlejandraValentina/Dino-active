from __future__ import annotations

import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import tempfile
import unittest
from PySide6.QtWidgets import QApplication
from unittest.mock import patch
from PySide6.QtCore import QSettings

from motorsim.desktop.app import DinoDesktopWindow
from motorsim.desktop.context import DesktopContext
from motorsim.desktop.services import new_project
from motorsim.desktop.execution_page import ExecutionPage
from motorsim.desktop.results_page import ResultsPage
from motorsim.desktop.preferences import artifact_root,set_artifact_root
from motorsim.desktop.exhaust_page import ExhaustPage
from motorsim.engine_configuration import identity


APP=QApplication.instance() or QApplication([])


class DesktopContextV2Tests(unittest.TestCase):
    def test_variant_selection_stays_visible_across_pages(self):
        project=new_project("ux-v2-context-test")
        context=DesktopContext(project)
        name=context.duplicate_variant(None,"Escape prueba")
        window=DinoDesktopWindow(context.project)
        window.context.select_variant(name)
        for page in range(window.stack.count()):
            window.nav.setCurrentRow(page)
            self.assertEqual(window.context.selected_variant,name)
            self.assertEqual(window.context_bar.variant.currentData(),name)
            self.assertEqual(window.inspector_variant.text(),"Escape prueba")
        self.assertIn("no demostraron independencia espacial",window.inspector_science.text())
        window.close()

    def test_variant_lifecycle_is_named_and_does_not_propagate_base_changes(self):
        context=DesktopContext(new_project("ux-v2-variant-test"))
        context.duplicate_variant(None,"Primera")
        variant_identity=identity(context.engine())
        changed=context.project["base_engine"]
        changed["display_name"]="Motor base renombrado"
        self.assertEqual(identity(context.engine("Primera")),variant_identity)
        self.assertEqual(context.engine("Primera")["display_name"],"Primera")
        context.rename_variant("Primera","Escape A")
        self.assertEqual(context.selected_variant,"Escape A")
        context.delete_variant("Escape A")
        self.assertIsNone(context.selected_variant)

    def test_variant_delete_fails_closed_when_external_run_references_exist(self):
        context=DesktopContext(new_project("ux-v2-referenced-test"))
        context.duplicate_variant(None,"Con corrida")
        context.project["result_references"]=[{"path":"run.json","identity_sha256":"a"*64,
            "artifact_sha256":"b"*64,"classification":"EXPLORATORY"}]
        with self.assertRaisesRegex(ValueError,"referencias externas"):
            context.delete_variant("Con corrida")
        self.assertIn("Con corrida",context.project["variants"])

    def test_artifact_root_preference_is_shared_by_simulation_and_results(self):
        prefs=QSettings("Dino2T","DinoDesktop");old=prefs.value("artifact_root")
        try:
            with tempfile.TemporaryDirectory() as temp:
                root=set_artifact_root(temp)
                self.assertEqual(artifact_root(),root)
                execution=ExecutionPage(DesktopContext(new_project("ux-v2-root")))
                results=ResultsPage(DesktopContext(new_project("ux-v2-root")))
                self.assertEqual(execution.artifact_root,root)
                with patch("motorsim.desktop.results_page.QFileDialog.getOpenFileName",return_value=("","")) as dialog:
                    results.choose()
                self.assertEqual(dialog.call_args.args[2],str(root))
        finally:
            if old is None:prefs.remove("artifact_root")
            else:set_artifact_root(old)

    def test_escape_editor_uses_each_shared_station_once_and_rebuilds_widgets_safely(self):
        page=ExhaustPage(DesktopContext(new_project("ux-v2-stations")))
        count=page.table.rowCount()
        self.assertEqual(page.stations.rowCount(),count+1)
        page.refresh();page.refresh()
        combos=[page.mesh_table.cellWidget(i,1) for i in range(count)]
        self.assertEqual(sum(widget is not None for widget in combos),count)
        # One station diameter feeds both adjoining segments without duplicate fields.
        page.stations.item(1,2).setText("21,5")
        rows=page._rows()
        self.assertEqual(rows[0]["outlet_diameter_mm"],21.5)
        self.assertEqual(rows[1]["inlet_diameter_mm"],21.5)
        self.assertEqual(sum(1 for i in range(count) if page.mesh_table.cellWidget(i,1) is not None),count)

    def test_escape_variant_save_is_named_and_current_variant_is_updated_in_place(self):
        context=DesktopContext(new_project("ux-v2-escape-save"));page=ExhaustPage(context)
        self.assertTrue(page.save_as_new(name="Resonador B"))
        self.assertEqual(context.selected_variant,"Resonador B")
        variant_count=len(context.project["variants"])
        page.table.item(1,2).setText("185,5")
        self.assertTrue(page.save_current())
        self.assertEqual(len(context.project["variants"]),variant_count)
        self.assertEqual(context.engine()["native_configuration"]["geometry_identity"]["chamber"]["sections"][1]["length_mm"],185.5)


if __name__=="__main__":
    unittest.main()
