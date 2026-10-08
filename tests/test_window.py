"""Pruebas de widgets sin pantalla; no sustituyen el recorrido manual Windows."""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt, QTimer
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QFileDialog, QLineEdit, QMessageBox, QDialogButtonBox

from motorsim.project import Project, ProjectError
from motorsim.storage import load_project, save_project
from motorsim.window import MainWindow


class WindowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "original.json"
        self.copy = self.path.with_name("copia.json")
        self.window = MainWindow()
        self.window.show()
        self.app.processEvents()
        self.error_patch = patch.object(self.window, "_error")
        self.error = self.error_patch.start()
        self.addCleanup(self.error_patch.stop)

    def tearDown(self):
        self.window.dirty = False
        self.window.close()
        self.window.deleteLater()
        self.app.processEvents()

    def edit(self):
        self.window.name_edit.selectAll()
        QTest.keyClicks(self.window.name_edit, "Motor editado")
        self.window.cycle_combo.setCurrentText("4T")

    def snapshot(self):
        return self.window.project(), self.window.path, self.window.dirty

    def test_initial_window_and_edit(self):
        self.assertEqual(self.snapshot(), (Project(), None, False))
        self.assertEqual([self.window.cycle_combo.itemText(i) for i in range(2)], ["2T", "4T"])
        self.assertIn("2T · INACTIVO", self.window.notice.text())
        self.assertIn("Sin archivo", self.window.file_label.text())
        self.edit()
        self.assertTrue(self.window.dirty)
        self.assertIn("MotorSim — Motor editado · 4T · Cambios pendientes", self.window.windowTitle())
        self.assertEqual(self.window.state_label.text(), "Cambios pendientes")

    def test_cycle_keyboard_and_reopen(self):
        self.window.summary_page.tabs.setCurrentIndex(1)
        combo = self.window.cycle_combo
        self.window.name_edit.setFocus()
        QTest.keyClick(self.window.name_edit, Qt.Key.Key_Tab)
        self.assertTrue(combo.hasFocus())
        QTest.keyClick(combo, Qt.Key.Key_Down)
        self.assertEqual(self.window.project().cycle, "4T")
        self.assertTrue(self.window.dirty)
        QTest.keyClick(combo, Qt.Key.Key_Up)
        self.assertEqual(self.window.project().cycle, "2T")
        with patch.object(self.window, "_choose_file", return_value=self.path):
            self.assertTrue(self.window.save())
        self.window.new_project()
        with patch.object(self.window, "_choose_file", return_value=self.path):
            self.window.open_project()
        self.assertEqual(combo.currentText(), "2T")
        self.assertEqual(self.window.state_label.text(), "Guardado")

    def test_characteristics_roundtrip_cycle_and_dirty(self):
        self.window.text_edits["manufacturer"].setText("Fabricante de prueba")
        self.window.text_edits["model"].setText("Modelo de prueba")
        self.window.notes_edit.setPlainText("Notas\ncon acentos á")
        for field, value in zip(self.window.numeric_edits, ("2", "54,123456789", "54.5", "110", "10,5")):
            self.window.numeric_edits[field].setText(value)
        before = self.window.project()
        self.window.cycle_combo.setCurrentText("4T")
        self.window.cycle_combo.setCurrentText("2T")
        self.assertEqual(self.window.project(), before)
        with patch.object(self.window, "_choose_file", return_value=self.path):
            self.assertTrue(self.window.save())
        self.window.new_project()
        with patch.object(self.window, "_choose_file", return_value=self.path):
            self.window.open_project()
        self.assertEqual(self.window.project(), before)
        for widget in (*self.window.text_edits.values(), *self.window.numeric_edits.values()):
            self.window.dirty = False
            widget.setText(widget.text() + "1")
            self.assertTrue(self.window.dirty)
        self.window.dirty = False
        self.window.notes_edit.insertPlainText("más")
        self.assertTrue(self.window.dirty)

    def test_geometry_dependencies_and_invalid_save(self):
        edits = self.window.numeric_edits
        edits["bore_mm"].setText("80")
        edits["stroke_mm"].setText("90")
        self.assertEqual(self.window.volume_label.text(), "452.39")
        self.assertEqual(self.window.total_volume_label.text(), "—")
        edits["cylinder_count"].setText("4")
        self.assertEqual(self.window.total_volume_label.text(), "1809.56")
        edits["stroke_mm"].setText("45")
        self.assertEqual(self.window.volume_label.text(), "226.19")
        edits["rod_length_mm"].setText("inválido")
        self.assertEqual(self.window.volume_label.text(), "226.19")
        with patch.object(self.window, "_choose_file") as choose:
            self.assertFalse(self.window.save())
            choose.assert_not_called()
        self.assertEqual(edits["rod_length_mm"].text(), "inválido")
        with patch.object(self.window, "_ask_changes", return_value="save"):
            self.window.new_project()
            self.assertFalse(self.window.close())
        self.assertTrue(self.window.dirty)
        edits["bore_mm"].setText("nan")
        self.assertEqual(self.window.volume_label.text(), "—")
        self.assertEqual(self.window.total_volume_label.text(), "—")
        edits["bore_mm"].clear()
        self.assertFalse(edits["bore_mm"].property("invalid"))
        self.assertEqual(self.window.volume_label.text(), "—")

    def test_complete_sheet_survives_close_and_new_window(self):
        self.window.name_edit.setText("Ficha de prueba")
        self.window.text_edits["manufacturer"].setText("Fabricante á")
        self.window.text_edits["model"].setText("Modelo de prueba")
        self.window.notes_edit.setPlainText("Observaciones\nsegunda línea")
        for field, value in zip(self.window.numeric_edits, ("4", "80", "90", "150", "10,5")):
            self.window.numeric_edits[field].setText(value)
        self.window.cycle_combo.setCurrentText("4T")
        expected = self.window.project()
        with patch.object(self.window, "_choose_file", return_value=self.path):
            self.assertTrue(self.window.save())
        self.assertTrue(self.window.close())
        reopened = MainWindow()
        try:
            reopened.show()
            with patch.object(reopened, "_choose_file", return_value=self.path):
                reopened.open_project()
            self.assertEqual(reopened.project(), expected)
            self.assertFalse(reopened.dirty)
            self.assertEqual(reopened.volume_label.text(), "452.39")
            self.assertEqual(reopened.total_volume_label.text(), "1809.56")
        finally:
            reopened.dirty = False
            reopened.close()
            reopened.deleteLater()

    def test_v1_editor_opens_empty_features_without_rewriting(self):
        original = b'{"format_version":1,"name":"Anterior","cycle":"4T"}'
        self.path.write_bytes(original)
        with patch.object(self.window, "_choose_file", return_value=self.path):
            self.window.open_project()
        self.assertEqual(self.window.project(), Project("Anterior", "4T"))
        self.assertFalse(self.window.dirty)
        self.assertEqual(self.path.read_bytes(), original)
        self.assertEqual(self.window.volume_label.text(), "—")
        self.assertEqual(self.window.total_volume_label.text(), "—")
        for edit in self.window.numeric_edits.values():
            self.assertEqual(edit.text(), "")
        self.assertTrue(self.window.save())
        self.assertIn('"format_version": 6', self.path.read_text(encoding="utf-8"))

    def test_responsive_groups(self):
        self.window.navigation.go("geometry")
        self.window.resize(1100, 760)
        self.app.processEvents()
        self.assertTrue(self.window.geometry_view.editor_wide)
        self.window.resize(640, 480)
        self.app.processEvents()
        self.assertFalse(self.window.geometry_view.editor_wide)
        self.assertEqual(self.window.workspace_scroll.horizontalScrollBar().maximum(), 0)

    def test_kinematics_updates_clears_and_preserves_json(self):
        for field, value in zip(self.window.numeric_edits, ("4", "20", "6", "5", "3")):
            self.window.numeric_edits[field].setText(value)
        view = self.window.geometry_view
        self.window.tabs.setCurrentWidget(view)
        self.app.processEvents()
        self.assertAlmostEqual(view.data.positions[90], 4)
        with patch.object(self.window, "_choose_file", return_value=self.path):
            self.assertTrue(self.window.save())
        original = self.path.read_bytes()
        view.angle_slider.setValue(90)
        self.assertFalse(self.window.dirty)
        self.assertEqual(self.path.read_bytes(), original)
        self.assertIn("4.00 mm", view.current.text())
        self.window.numeric_edits["compression_ratio"].clear()
        self.assertTrue(view.position_plot.values)
        self.assertFalse(view.volume_plot.values)
        self.assertIn("Falta", view.volume_plot.error)
        self.window.numeric_edits["rod_length_mm"].setText("3")
        self.assertFalse(view.position_plot.values)
        self.assertFalse(view.mechanism.data.positions)
        self.assertIn("incompatible", view.position_plot.error)
        self.assertTrue(self.window.save())
        self.assertEqual(load_project(self.path).rod_length_mm, 3)
        with patch.object(self.window, "_choose_file", return_value=self.path):
            self.window.open_project()
        self.assertFalse(view.position_plot.values)
        self.window.new_project()
        self.assertFalse(view.volume_plot.values)
        self.assertFalse(view.position_plot.values)

    def test_kinematics_cycle_keyboard_and_compact_layout(self):
        for field, value in zip(self.window.numeric_edits, ("1", "80", "90", "150", "10")):
            self.window.numeric_edits[field].setText(value)
        self.window.cycle_combo.setCurrentText("4T")
        view = self.window.geometry_view
        self.window.tabs.setCurrentWidget(view)
        self.assertEqual(len(view.volume_plot.values), 721)
        view.angle_slider.setValue(540)
        self.assertEqual(view.data.positions[540], 90)
        self.assertIn("2.ª", view.angle_label.text())
        view.angle_slider.setFocus()
        QTest.keyClick(view.angle_slider, Qt.Key.Key_Left)
        self.assertEqual(view.angle_slider.value(), 539)
        self.window.resize(640, 480)
        self.app.processEvents()
        self.assertFalse(view._wide)
        self.assertEqual(view.horizontalScrollBar().maximum(), 0)
        self.window.cycle_combo.setCurrentText("2T")
        self.assertEqual(view.angle_slider.maximum(), 360)
        self.assertEqual(len(view.volume_plot.values), 361)

    def test_large_integer_dimension_survives_open_and_save(self):
        project = Project(bore_mm=9007199254740993)
        save_project(self.path, project)
        with patch.object(self.window, "_choose_file", return_value=self.path):
            self.window.open_project()
        self.assertTrue(self.window.save())
        self.assertEqual(load_project(self.path).bore_mm, project.bore_mm)

    def configure_ducts(self):
        v=self.window.ducts_view
        self.window.tabs.setCurrentWidget(self.window.duct_stack)
        for name,values in (('Tubo sintético',('100','20','20')),('Cono sintético',('100','20','40'))):
            v.add_segment();v.name_edit.setText(name)
            for key,value in zip(v.edits,values):v.edits[key].setText(value)
        return v

    def test_ducts_edit_reorder_delete_and_profile(self):
        v=self.configure_ducts()
        self.assertEqual(v.profile.data.profile,((0,100,10,10),(100,200,10,20)))
        self.assertIn('104.72',v.totals.text())
        with patch.object(self.window,'_choose_file',return_value=self.path):
            self.assertTrue(self.window.save())
        v.list.setCurrentRow(0)
        self.assertFalse(self.window.dirty)
        self.assertEqual(v.profile.selected,0)
        v.down_button.click()
        self.assertTrue(self.window.dirty)
        self.assertEqual(v.profile.data.profile,((0,100,10,20),(100,200,10,10)))
        self.assertIn('discontinua',v.joints.text())
        self.assertIn('104.72',v.totals.text())
        self.assertEqual(v.name_edit.text(),'Tubo sintético')
        v.up_button.click()
        self.assertEqual(v.profile.data.joints,(True,))
        v.edits['length_mm'].setText('150,125')
        self.assertEqual(float(v.profile.data.length),250.125)
        v.remove_button.click()
        self.assertEqual(len(v.profile.data.profile),1)
        self.assertEqual(v.name_edit.text(),'Cono sintético')
        self.assertTrue(self.window.save())
        self.assertEqual(load_project(self.path).ducts.intake[0].name,'Cono sintético')
        v.remove_button.click()
        self.assertIn('Sin tramos',v.totals.text());self.assertFalse(v.profile.data.profile)
        self.assertTrue(self.window.save())
        self.assertFalse(load_project(self.path).ducts.intake)

    def test_ducts_both_routes_cycle_save_close_reopen(self):
        v=self.configure_ducts()
        v.route_combo.setCurrentIndex(1)
        self.assertFalse(v.drafts['exhaust']);v.add_segment()
        v.name_edit.setText('Escape incompleto');v.edits['length_mm'].setText('55.125')
        with patch.object(self.window,'_choose_file',return_value=self.path):
            self.assertTrue(self.window.save())
        original=self.window.project()
        v.route_combo.setCurrentIndex(0);v.list.setCurrentRow(0)
        self.assertFalse(self.window.dirty)
        self.window.cycle_combo.setCurrentText('4T')
        self.assertIs(self.window.motor4_page.tabs.widget(1),self.window.ducts4_view)
        self.assertFalse(self.window.ducts4_view.drafts['intake'])
        self.assertEqual(self.window.project().ducts,original.ducts)
        self.assertTrue(self.window.save());self.assertTrue(self.window.close())
        reopened=MainWindow()
        try:
            with patch.object(reopened,'_choose_file',return_value=self.path):reopened.open_project()
            self.assertEqual(reopened.project().ducts,original.ducts)
            reopened.cycle_combo.setCurrentText('2T')
            self.assertEqual(reopened.ducts_view.profile.data.length,200)
        finally:
            reopened.dirty=False;reopened.close();reopened.deleteLater()

    def test_ducts_invalid_drafts_survive_selection_reorder_and_cancel(self):
        v=self.configure_ducts()
        with patch.object(self.window,'_choose_file',return_value=self.path):self.assertTrue(self.window.save())
        raw=self.path.read_bytes()
        v.edits['start_diameter_mm'].setText('inválido')
        self.assertFalse(v.profile.data.profile);self.assertIsNone(v.profile.data.volume)
        self.assertEqual(v.profile.data.length,200)
        v.up_button.click();v.list.setCurrentRow(1);v.route_combo.setCurrentIndex(1)
        for cycle in ('4T','2T'):
            self.window.cycle_combo.setCurrentText(cycle)
            with patch.object(self.window,'_choose_file') as choose:
                self.assertFalse(self.window.save());choose.assert_not_called()
            with patch.object(self.window,'_ask_changes',return_value='cancel'):
                self.window.new_project();self.assertFalse(self.window.close())
            self.assertEqual(self.path.read_bytes(),raw)
            self.assertEqual(v.drafts['intake'][0]['start_diameter_mm'],'inválido')
        v.route_combo.setCurrentIndex(0);v.list.setCurrentRow(0)
        self.assertEqual(v.edits['start_diameter_mm'].text(),'inválido')
        v.edits['start_diameter_mm'].clear()
        self.assertTrue(self.window.save());self.assertIsNone(load_project(self.path).ducts.intake[0].start_diameter_mm)
        v.edits['start_diameter_mm'].setText('20')
        self.assertTrue(v.profile.data.profile)
        v.edits['length_mm'].clear()
        self.assertFalse(v.profile.data.profile);self.assertIsNone(v.profile.data.length)
        self.assertIn('Área inicial: 314.16',v.piece_results.text())
        self.app.processEvents()

    def test_ducts_file_failures_protect_data_and_v4_open(self):
        import json
        from motorsim.project import Intake, Port, Ducts
        v=self.configure_ducts()
        with patch.object(self.window,'_choose_file',return_value=self.path):self.assertTrue(self.window.save())
        raw=self.path.read_bytes();v.edits['length_mm'].setText('101')
        before=self.snapshot()
        with patch.object(self.window,'_choose_file',return_value=None):self.assertFalse(self.window.save_as())
        with patch.object(self.window,'_choose_file',return_value=self.path), \
             patch.object(self.window,'_confirm_overwrite',return_value=False):self.assertFalse(self.window.save_as())
        with patch('motorsim.storage.os.replace',side_effect=PermissionError('Prueba')):
            self.assertFalse(self.window.save())
        self.assertEqual(self.snapshot(),before);self.assertEqual(self.path.read_bytes(),raw)
        self.copy.write_text('{',encoding='utf-8')
        with patch.object(self.window,'_choose_file',return_value=self.copy):self.window.open_project()
        self.assertEqual(self.snapshot(),before)
        old=Project('Anterior','2T',ports=(Port('Escape','escape',32,10,20),),
                    crankcase_volume_bdc_cm3=250,intake=Intake('piston_port',64,10,20,42))
        data=old.to_dict();data.pop('ducts');data['format_version']=4
        raw=json.dumps(data).encode();self.copy.write_bytes(raw)
        with patch.object(self.window,'_choose_file',return_value=self.copy), \
             patch.object(self.window,'_ask_changes',return_value='discard'):self.window.open_project()
        self.assertEqual(self.window.project(),old);self.assertEqual(self.copy.read_bytes(),raw)
        self.assertEqual(self.window.project().ducts,Ducts())
        self.assertFalse(self.window.dirty)

    def test_ducts_keyboard_and_compact_layout(self):
        v=self.configure_ducts()
        with patch.object(self.window,'_choose_file',return_value=self.path):self.assertTrue(self.window.save())
        v.route_combo.setFocus();QTest.keyClick(v.route_combo,Qt.Key.Key_Down)
        self.assertEqual(v.route,'exhaust');self.assertFalse(self.window.dirty)
        QTest.keyClick(v.route_combo,Qt.Key.Key_Up)
        self.assertEqual(v.route,'intake');self.assertFalse(self.window.dirty)
        v.name_edit.setFocus();QTest.keyClick(v.name_edit,Qt.Key.Key_Tab)
        self.assertIs(self.app.focusWidget(),v.edits['length_mm'])
        self.window.resize(700,480);self.app.processEvents()
        self.assertFalse(v._wide);self.assertEqual(v.horizontalScrollBar().maximum(),0)
        self.assertEqual(v.profile.data.length,200)

    def configure_intake(self):
        w = self.window
        w.name_edit.setText('CASO SINTÉTICO — Admisión')
        w.numeric_edits['stroke_mm'].setText('56')
        w.numeric_edits['rod_length_mm'].setText('100')
        v = w.ports_view.intake
        w.tabs.setCurrentWidget(w.ports_view)
        v.mode_combo.setCurrentIndex(1)
        for key, text in zip(v.edits, ('64', '10', '20', '42')):
            v.edits[key].setText(text)
        return v

    def test_intake_save_reopen_cycles_and_undefined(self):
        v = self.configure_intake()
        self.assertIn('270.00',v.results.text())
        self.assertIn('∪',v.results.text())
        with patch.object(self.window, '_choose_file', return_value=self.path):
            self.assertTrue(self.window.save())
        original = self.window.project()
        self.assertFalse(self.window.dirty)
        self.window.cycle_combo.setCurrentText('4T')
        self.assertEqual(self.window.project().intake,original.intake)
        self.assertFalse(v.plot.values)
        self.assertTrue(self.window.save())
        self.window.new_project()
        self.assertIsNone(v.mode_combo.currentData())
        with patch.object(self.window, '_choose_file', return_value=self.path):
            self.window.open_project()
        self.assertEqual(self.window.project().intake,original.intake)
        self.window.cycle_combo.setCurrentText('2T')
        self.assertEqual(v.plot.values[0],200)
        v.mode_combo.setCurrentIndex(0)
        self.assertFalse(v.plot.values)
        self.assertEqual(v.edits['skirt_mm'].text(),'42')
        self.assertTrue(self.window.save())
        self.assertIsNone(load_project(self.path).intake.mode)
        v.mode_combo.setCurrentIndex(1)
        self.assertEqual(v.plot.values[360],200)

    def test_intake_invalid_draft_cancel_and_file_errors(self):
        v = self.configure_intake()
        with patch.object(self.window, '_choose_file', return_value=self.path):
            self.assertTrue(self.window.save())
        original = self.path.read_bytes()
        v.edits['skirt_mm'].setText('inválido')
        self.assertFalse(v.plot.values)
        for cycle in ('4T','2T'):
            self.window.cycle_combo.setCurrentText(cycle)
            v.mode_combo.setCurrentIndex(0)
            self.window.tabs.setCurrentIndex(0)
            self.window.tabs.setCurrentWidget(self.window.ports_view)
            self.assertEqual(v.edits['skirt_mm'].text(),'inválido')
            self.assertFalse(self.window.save())
            with patch.object(self.window,'_ask_changes',return_value='cancel'):
                self.window.new_project()
                self.assertFalse(self.window.close())
            self.assertEqual(v.edits['skirt_mm'].text(),'inválido')
            self.assertEqual(self.path.read_bytes(),original)
        v.edits['skirt_mm'].setText('43,125')
        v.mode_combo.setCurrentIndex(1)
        before=self.snapshot()
        with patch.object(self.window,'_choose_file',return_value=None):
            self.assertFalse(self.window.save_as())
        with patch.object(self.window,'_choose_file',return_value=self.path), \
             patch.object(self.window,'_confirm_overwrite',return_value=False):
            self.assertFalse(self.window.save_as())
        with patch('motorsim.storage.os.replace',side_effect=PermissionError('Prueba')):
            self.assertFalse(self.window.save())
        self.assertEqual(self.snapshot(),before)
        self.assertEqual(self.path.read_bytes(),original)
        self.assertTrue(self.window.save())
        self.assertEqual(load_project(self.path).intake.skirt_mm,43.125)

    def test_intake_results_update_and_clear_by_dependency(self):
        v=self.configure_intake()
        for edit, text in ((self.window.numeric_edits['stroke_mm'],'58'),
                           (self.window.numeric_edits['rod_length_mm'],'110'),
                           (v.edits['top_mm'],'65'),(v.edits['height_mm'],'11'),
                           (v.edits['skirt_mm'],'43')):
            previous=v.plot.values
            edit.setText(text)
            self.assertTrue(v.plot.values)
            self.assertNotEqual(v.plot.values,previous)
        for text in ('','inválido'):
            v.edits['width_mm'].setText(text)
            self.assertFalse(v.plot.values)
            self.assertNotIn('Apertura: —',v.results.text())
        v.edits['width_mm'].setText('20')
        for text in ('','inválido','1'):
            v.edits['skirt_mm'].setText(text)
            self.assertFalse(v.plot.values)
            self.assertIn('Apertura: —',v.results.text())
        v.edits['skirt_mm'].setText('80')
        self.assertEqual(v.plot.values,(0,)*361)
        self.assertIn('No se abre',v.results.text())
        self.app.processEvents()

    def test_intake_legacy_v3_no_rewrite_and_keyboard(self):
        import json
        from motorsim.project import Intake, Port
        data=Project(ports=(Port('Conservada','transfer',32,10,20),),
                     crankcase_volume_bdc_cm3=200).to_dict()
        data.pop('intake'); data['format_version']=3
        raw=json.dumps(data).encode(); self.path.write_bytes(raw)
        with patch.object(self.window,'_choose_file',return_value=self.path):
            self.window.open_project()
        self.assertEqual(self.path.read_bytes(),raw)
        self.assertEqual(self.window.project().intake,Intake())
        self.assertFalse(self.window.dirty)
        v=self.window.ports_view.intake
        self.window.tabs.setCurrentWidget(self.window.ports_view)
        self.window.motor2_page.tabs.setCurrentIndex(1)
        v.mode_combo.setFocus()
        QTest.keyClick(v.mode_combo,Qt.Key.Key_Down)
        self.assertEqual(v.mode_combo.currentData(),'piston_port')
        QTest.keyClick(v.mode_combo,Qt.Key.Key_Tab)
        self.assertIs(self.app.focusWidget(),v.edits['top_mm'])
        self.assertTrue(self.window.dirty)
        self.window.resize(700,480); self.app.processEvents()
        self.assertFalse(v._wide)
        self.assertEqual(self.window.ports_view.horizontalScrollBar().maximum(),0)
        self.assertTrue(self.window.save())
        self.assertEqual(load_project(self.path).ports[0].name,'Conservada')
        self.assertEqual(load_project(self.path).crankcase_volume_bdc_cm3,200)

    def test_ports_edit_save_switch_delete_reopen(self):
        view=self.window.ports_view
        self.window.tabs.setCurrentWidget(view)
        self.window.numeric_edits['stroke_mm'].setText('56')
        self.window.numeric_edits['rod_length_mm'].setText('100')
        QTest.mouseClick(view.add_button, Qt.MouseButton.LeftButton)
        view.name_edit.setText('Sintético escape')
        view.function_combo.setCurrentIndex(1)
        for key,value in zip(view.edits,('32','10','20')):view.edits[key].setText(value)
        view.crankcase_edit.setText('250,125')
        self.assertEqual(view.plot.values[180],200)
        self.assertIn('90.00',view.results.text())
        QTest.mouseClick(view.add_button, Qt.MouseButton.LeftButton)
        view.name_edit.setText('Transferencia sin dimensiones')
        view.function_combo.setCurrentIndex(2)
        with patch.object(self.window,'_choose_file',return_value=self.path):
            self.assertTrue(self.window.save())
        expected=self.window.project()
        view.list.setCurrentRow(0)
        self.assertFalse(self.window.dirty)
        self.window.cycle_combo.setCurrentText('4T')
        self.assertFalse(view.panel.isVisible())
        self.assertFalse(view.plot.values)
        self.assertEqual(self.window.project().ports,expected.ports)
        self.assertTrue(self.window.save())
        self.window.new_project()
        with patch.object(self.window,'_choose_file',return_value=self.path):self.window.open_project()
        self.window.cycle_combo.setCurrentText('2T')
        self.assertEqual(self.window.project().ports,expected.ports)
        self.assertEqual(self.window.project().crankcase_volume_bdc_cm3,250.125)
        self.assertEqual(view.name_edit.text(),'Sintético escape')
        self.assertEqual(view.plot.values[180],200)
        view.list.setCurrentRow(1)
        QTest.mouseClick(view.remove_button,Qt.MouseButton.LeftButton)
        self.assertTrue(self.window.dirty)
        self.assertTrue(self.window.save())
        self.window.new_project()
        with patch.object(self.window,'_choose_file',return_value=self.path):self.window.open_project()
        self.assertEqual(len(self.window.project().ports),1)

    def test_ports_invalid_draft_survives_selection_and_cancel(self):
        view=self.window.ports_view
        self.window.tabs.setCurrentWidget(view)
        view.add_port();view.edits['width_mm'].setText('inválido')
        view.add_port();view.name_edit.setText('Otra fila')
        with patch.object(self.window,'_choose_file') as choose:
            self.assertFalse(self.window.save());choose.assert_not_called()
        with patch.object(self.window,'_ask_changes',return_value='cancel'):self.window.new_project()
        self.assertEqual(len(view.drafts),2)
        view.list.setCurrentRow(0)
        self.assertEqual(view.edits['width_mm'].text(),'inválido')
        self.window.cycle_combo.setCurrentText('4T')
        self.assertFalse(self.window.save())
        self.window.cycle_combo.setCurrentText('2T')
        view.edits['width_mm'].clear()
        self.assertIsNone(self.window.project().ports[0].width_mm)
        view.crankcase_edit.setText('0')
        self.assertFalse(self.window.save())

    def test_port_curves_update_and_clear(self):
        view=self.window.ports_view
        self.window.tabs.setCurrentWidget(view)
        self.window.numeric_edits['stroke_mm'].setText('56')
        self.window.numeric_edits['rod_length_mm'].setText('100')
        view.add_port()
        for key,value in zip(view.edits,('32','10','20')):view.edits[key].setText(value)
        before=view.plot.values
        self.window.numeric_edits['rod_length_mm'].setText('110')
        self.assertNotEqual(view.plot.values,before)
        before=view.plot.values
        self.window.numeric_edits['stroke_mm'].setText('58')
        self.assertNotEqual(view.plot.values,before)
        view.edits['top_mm'].setText('57')
        self.assertEqual(view.plot.values[180],20)
        view.edits['top_mm'].setText('58')
        self.assertIn('No se abre',view.results.text())
        self.assertTrue(all(v==0 for v in view.plot.values))
        self.app.processEvents()  # También dibuja curva cero sin división por cero.
        view.edits['height_mm'].clear()
        self.assertFalse(view.plot.values)
        self.assertIn('Falta',view.plot.error)
        view.edits['height_mm'].setText('10')
        self.window.numeric_edits['rod_length_mm'].setText('20')
        self.assertFalse(view.plot.values)
        self.assertTrue(view.plot.error)

    def test_visible_toolbar_uses_protected_file_actions(self):
        self.edit()
        save_button = self.window.file_toolbar.widgetForAction(self.window.actions["save"])
        with patch.object(self.window, "_choose_file", return_value=self.path):
            QTest.mouseClick(save_button, Qt.MouseButton.LeftButton)
        self.assertEqual(load_project(self.path), self.window.project())
        self.edit()
        before = self.snapshot()
        new_button = self.window.file_toolbar.widgetForAction(self.window.actions["new"])
        with patch.object(self.window, "_ask_changes", return_value="cancel"):
            QTest.mouseClick(new_button, Qt.MouseButton.LeftButton)
        self.assertEqual(self.snapshot(), before)

    def test_compact_window_keeps_status_and_notice_visible(self):
        self.window.resize(680, 440)
        self.app.processEvents()
        for widget in (self.window.file_label, self.window.notice, self.window.state_label, self.window.statusBar()):
            top_left = widget.mapTo(self.window, widget.rect().topLeft())
            bottom_right = widget.mapTo(self.window, widget.rect().bottomRight())
            self.assertTrue(self.window.rect().contains(top_left))
            self.assertTrue(self.window.rect().contains(bottom_right))

    def test_long_path_remains_available_without_hiding_status(self):
        path = Path("C:/proyectos") / ("carpeta-" * 30) / "motor.json"
        self.window._activate(Project(), path)
        self.window.resize(680, 440)
        self.app.processEvents()
        self.assertEqual(self.window.file_label.toolTip(), str(path))
        self.assertIn("…", self.window.file_label.text())
        self.assertTrue(self.window.file_label.text().endswith("motor.json"))
        self.assertEqual(self.window.state_label.text(), "Guardado")
        self.assertTrue(self.window.notice.isVisible())

    def test_save_as_keeps_original_and_changes_active_path(self):
        self.edit()
        with patch.object(self.window, "_choose_file", return_value=self.path):
            self.assertTrue(self.window.save())
        original = self.path.read_bytes()
        self.window.name_edit.setText("Copia áéíóú")
        with patch.object(self.window, "_choose_file", return_value=self.copy):
            self.assertTrue(self.window.save_as())
        self.assertEqual(self.path.read_bytes(), original)
        self.assertEqual(load_project(self.copy), self.window.project())
        self.assertEqual(self.window.path, self.copy)
        self.assertFalse(self.window.dirty)
        self.window.name_edit.setText("Guardar en la ruta activa")
        with patch.object(self.window, "_choose_file") as choose:
            self.assertTrue(self.window.save())
            choose.assert_not_called()
        self.assertEqual(load_project(self.copy).name, "Guardar en la ruta activa")

    def test_save_cancel_overwrite_reject_and_failure_preserve_state(self):
        save_project(self.path, Project())
        self.window._activate(Project(), self.path)
        self.edit()
        original = self.path.read_bytes()
        before = self.snapshot()
        with patch.object(self.window, "_choose_file", return_value=None):
            self.assertFalse(self.window.save_as())
        self.assertEqual(self.snapshot(), before)
        with patch.object(self.window, "_choose_file", return_value=self.path):
            with patch.object(self.window, "_confirm_overwrite", return_value=False) as confirm:
                self.assertFalse(self.window.save_as())
                confirm.assert_called_once_with(self.path)
        self.assertEqual(self.snapshot(), before)
        with patch("motorsim.storage.os.replace", side_effect=PermissionError("Acceso denegado")):
            self.assertFalse(self.window.save())
            with patch.object(self.window, "_choose_file", return_value=self.copy):
                self.assertFalse(self.window.save_as())
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(self.path.read_bytes(), original)
        self.assertFalse(self.copy.exists())
        self.error.assert_called()

    def test_overwrite_accepted(self):
        save_project(self.path, Project())
        self.edit()
        with patch.object(self.window, "_choose_file", return_value=self.path):
            with patch.object(self.window, "_confirm_overwrite", return_value=True):
                self.assertTrue(self.window.save_as())
        self.assertEqual(load_project(self.path), self.window.project())

    def test_invalid_name_preserves_edit_and_path(self):
        for name in ("", "   "):
            self.window.name_edit.setText(name)
            before = self.snapshot()
            with patch.object(self.window, "_choose_file") as choose:
                self.assertFalse(self.window.save())
                choose.assert_not_called()
            self.assertEqual(self.snapshot(), before)
        self.assertEqual(self.error.call_count, 2)

    def test_open_cancel_invalid_and_unreadable_preserve_pending(self):
        self.edit()
        before = self.snapshot()
        self.path.write_text("malformado", encoding="utf-8")
        for path in (None, self.path, self.copy):
            with self.subTest(path=path):
                with patch.object(self.window, "_choose_file", return_value=path):
                    with patch.object(self.window, "_ask_changes", return_value="discard"):
                        self.window.open_project()
                self.assertEqual(self.snapshot(), before)

    def test_cancel_new_open_exit_and_window_close(self):
        save_project(self.path, Project("Otro", "2T"))
        self.edit()
        before = self.snapshot()
        with patch.object(self.window, "_ask_changes", return_value="cancel"):
            self.window.actions["new"].trigger()
            with patch.object(self.window, "_choose_file", return_value=self.path):
                self.window.actions["open"].trigger()
            self.window.actions["exit"].trigger()
            self.assertFalse(self.window.close())
        self.assertTrue(self.window.isVisible())
        self.assertEqual(self.snapshot(), before)

    def test_discard_new_open_and_close(self):
        self.edit()
        with patch.object(self.window, "_ask_changes", return_value="discard"):
            self.window.new_project()
            self.assertEqual(self.snapshot(), (Project(), None, False))
            self.edit()
            other = Project("Motor á", "4T")
            save_project(self.path, other)
            with patch.object(self.window, "_choose_file", return_value=self.path):
                self.window.open_project()
            self.assertEqual(self.snapshot(), (other, self.path, False))
            self.edit()
            self.assertTrue(self.window.close())

    def test_save_before_new_open_and_close(self):
        for operation in ("new", "open", "close"):
            with self.subTest(operation=operation):
                self.window._activate(Project(), self.path)
                self.edit()
                edited = self.window.project()
                save_project(self.copy, Project("Otro", "2T"))
                with patch.object(self.window, "_ask_changes", return_value="save"):
                    if operation == "new":
                        self.window.new_project()
                        self.assertEqual(self.window.project(), Project())
                    elif operation == "open":
                        with patch.object(self.window, "_choose_file", return_value=self.copy):
                            self.window.open_project()
                        self.assertEqual(self.window.project(), Project("Otro", "2T"))
                    else:
                        self.assertTrue(self.window.close())
                self.assertEqual(load_project(self.path), edited)

    def test_cancelled_or_failed_save_blocks_transitions(self):
        save_project(self.path, Project("Abrir", "2T"))
        self.edit()
        before = self.snapshot()
        for failed in (False, True):
            with patch.object(self.window, "_ask_changes", return_value="save"):
                with patch.object(self.window, "_choose_file", return_value=self.path if failed else None):
                    with patch.object(self.window, "_confirm_overwrite", return_value=True):
                        with patch("motorsim.window.save_project", side_effect=ProjectError("Fallo")):
                            self.window.new_project()
                            self.assertFalse(self.window.close())
                with patch.object(self.window, "_choose_file", side_effect=[self.path, None]):
                    self.window.open_project()
            self.assertEqual(self.snapshot(), before)
            self.assertTrue(self.window.isVisible())

    def test_open_same_file_after_save_uses_saved_data(self):
        save_project(self.path, Project())
        self.window._activate(Project(), self.path)
        self.edit()
        edited = self.window.project()
        with patch.object(self.window, "_choose_file", return_value=self.path):
            with patch.object(self.window, "_ask_changes", return_value="save"):
                self.window.open_project()
        self.assertEqual(self.snapshot(), (edited, self.path, False))

    def test_long_name_is_not_truncated_when_opened(self):
        project = Project("á" * 40000, "4T")
        save_project(self.path, project)
        with patch.object(self.window, "_choose_file", return_value=self.path):
            self.window.open_project()
        self.assertEqual(self.window.project(), project)

    def test_real_pending_dialog_buttons_and_escape(self):
        for caption, expected in (("Guardar", "save"), ("Descartar", "discard"),
                                  ("Cancelar", "cancel"), (None, "cancel")):
            def answer():
                box = self.app.activeModalWidget()
                if isinstance(box, QMessageBox):
                    if caption is None:
                        QTest.keyClick(box, Qt.Key.Key_Escape)
                    else:
                        for button in box.buttons():
                            if button.text() == caption:
                                QTest.mouseClick(button, Qt.MouseButton.LeftButton)
            QTimer.singleShot(0, answer)
            with self.subTest(caption=caption):
                self.assertEqual(self.window._ask_changes(), expected)

    def test_real_file_dialogs_save_open_and_cancel(self):
        failures = []
        timeout = QTimer()
        timeout.setInterval(3000)

        def timed_out():
            failures.append("El diálogo no terminó dentro de 3 segundos")
            dialog = self.app.activeModalWidget()
            if dialog:
                dialog.reject()

        timeout.timeout.connect(timed_out)
        timeout.start()
        self.addCleanup(timeout.stop)

        def choose(path):
            def answer():
                dialog = self.app.activeModalWidget()
                try:
                    self.assertIsInstance(dialog, QFileDialog)
                    if path is None:
                        QTest.keyClick(dialog, Qt.Key.Key_Escape)
                    else:
                        filename = dialog.findChild(QLineEdit, "fileNameEdit")
                        filename.setText(str(path))
                        buttons = dialog.findChild(QDialogButtonBox)
                        choice = (QDialogButtonBox.StandardButton.Save
                                  if dialog.acceptMode() == QFileDialog.AcceptMode.AcceptSave
                                  else QDialogButtonBox.StandardButton.Open)
                        QTest.mouseClick(buttons.button(choice), Qt.MouseButton.LeftButton)
                except Exception as exc:
                    failures.append(exc)
                    if dialog:
                        dialog.reject()
            QTimer.singleShot(100, answer)

        self.edit()
        # Se comprueba también que el diálogo agrega .json al destino.
        choose(self.path.with_suffix(""))
        self.assertTrue(self.window.save())
        self.assertTrue(self.path.exists())
        edited = self.window.project()
        self.window.new_project()
        choose(self.path)
        self.window.open_project()
        self.assertEqual(self.window.project(), edited)
        self.assertTrue(self.window.path.samefile(self.path))
        self.assertFalse(self.window.dirty)
        self.edit()
        before = self.snapshot()
        choose(None)
        self.window.open_project()
        self.assertEqual(self.snapshot(), before)
        choose(None)
        self.assertFalse(self.window.save_as())
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(failures, [])

    def test_real_overwrite_confirmation(self):
        for caption, expected in (("Reemplazar", True), ("Cancelar", False)):
            def answer():
                box = self.app.activeModalWidget()
                if isinstance(box, QMessageBox):
                    for button in box.buttons():
                        if button.text() == caption:
                            QTest.mouseClick(button, Qt.MouseButton.LeftButton)
            QTimer.singleShot(100, answer)
            with self.subTest(caption=caption):
                self.assertEqual(self.window._confirm_overwrite(self.path), expected)
