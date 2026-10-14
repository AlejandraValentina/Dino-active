from __future__ import annotations

import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import unittest
from PySide6.QtWidgets import QApplication

from motorsim.desktop.app import DinoDesktopWindow
from motorsim.desktop.context import DesktopContext
from motorsim.desktop.services import new_project
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


if __name__=="__main__":
    unittest.main()
