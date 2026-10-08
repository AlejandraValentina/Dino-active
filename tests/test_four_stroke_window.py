"""Editor 4T sin pantalla; no aceptación manual ni cálculo integrado."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from dataclasses import replace
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from motorsim.window import MainWindow
from motorsim.four_stroke import geometry
from motorsim.simulation_case import geometry as two_geometry
from motorsim.project import ProjectError, FourStroke
from motorsim.storage import load_project


class FourStrokeWindowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)/'motor.json'
        self.window = MainWindow(); self.window._activate(geometry(),None)
        self.window.show(); self.app.processEvents()
        self.error = patch.object(self.window,'_error'); self.error.start(); self.addCleanup(self.error.stop)

    def tearDown(self):
        self.window.dirty=False; self.window.close(); self.window.deleteLater(); self.app.processEvents()

    def test_edit_save_reopen_events_and_missing_clear(self):
        w=self.window; v=w.valves_view
        v.edits['intake']['opening_deg'].setText('700')
        v.edits['intake']['duration_deg'].setText('240')
        v.edits['exhaust']['duration_deg'].setText('240')
        self.assertIn('940° (fase 220°)',v.outputs['intake'].text())
        self.assertIn('total 40°',v.crossing.text()); self.assertTrue(w.dirty)
        with patch.object(w,'_choose_file',return_value=self.path): self.assertTrue(w.save())
        saved=w.project(); w._activate(load_project(self.path),self.path)
        self.assertEqual(w.project(),saved); self.assertFalse(w.dirty)
        v.edits['intake']['lift_mm'].clear()
        self.assertFalse(v.plots['intake'][0].values); self.assertIn('—',v.crossing.text())
        self.assertTrue(w.save()); self.assertIsNone(load_project(self.path).four_stroke.intake.lift_mm)

    def test_cycle_independence_preserves_invalid_drafts_and_common_data(self):
        w=self.window
        original=replace(two_geometry(),four_stroke=geometry().four_stroke)
        w._activate(original,None)
        w.ducts_view.edits['length_mm'].setText('texto inválido')
        w.cycle_combo.setCurrentText('4T')
        self.assertIs(w.motor4_page.tabs.widget(1),w.ducts4_view)
        w.ducts4_view.edits['length_mm'].setText('123,456')
        w.valves_view.edits['intake']['seat_mm'].setText('24,5')
        self.assertEqual(w.numeric_edits['bore_mm'].text(),'54')
        with self.assertRaises(ProjectError): w.project()
        w.cycle_combo.setCurrentText('2T')
        self.assertEqual(w.ducts_view.edits['length_mm'].text(),'texto inválido')
        w.ducts_view.edits['length_mm'].setText('100')
        self.assertEqual(w.project().ports,original.ports)
        self.assertEqual(w.project().intake,original.intake)
        self.assertEqual(w.project().four_stroke.ducts.intake[0].length_mm,123.456)
        self.assertEqual(w.project().four_stroke.intake.seat_mm,24.5)

    def test_invalid_save_cancel_errors_and_incompatible_geometry(self):
        w=self.window
        with patch.object(w,'_choose_file',return_value=self.path): self.assertTrue(w.save())
        raw=self.path.read_bytes()
        edit=w.valves_view.edits['intake']['stem_mm']; edit.setText('NaN')
        self.assertFalse(w.save()); self.assertEqual(self.path.read_bytes(),raw)
        with patch.object(w,'_ask_changes',return_value='cancel'):
            w.new_project(); self.assertFalse(w.close())
        self.assertEqual(edit.text(),'NaN')
        edit.setText('22') # individually valid but incompatible with throat 20
        self.assertTrue(w.save()); self.assertFalse(w.valves_view.plots['intake'][0].values)
        self.assertIn('s < d',w.valves_view.outputs['intake'].text())
        raw=self.path.read_bytes(); edit.setText('5')
        with patch('motorsim.storage.os.replace',side_effect=PermissionError('test')):
            self.assertFalse(w.save())
        self.assertEqual(self.path.read_bytes(),raw); self.assertTrue(w.dirty)
        with patch.object(w,'_choose_file',return_value=self.path),patch.object(w,'_confirm_overwrite',return_value=False):
            self.assertFalse(w.save_as())

    def test_legacy_4t_keeps_historical_ducts_in_2t(self):
        import json
        w=self.window; p=replace(two_geometry(),cycle='4T')
        data=p.to_dict(); data.pop('four_stroke'); data['format_version']=5
        raw=json.dumps(data).encode(); self.path.write_bytes(raw)
        w._activate(load_project(self.path),self.path)
        self.assertEqual(w.project().ducts,p.ducts)
        self.assertEqual(w.project().four_stroke,FourStroke())
        self.assertFalse(w.ducts4_view.drafts['intake']); self.assertFalse(w.dirty)
        self.assertEqual(self.path.read_bytes(),raw)

    def test_keyboard_compact_and_no_stale_curve(self):
        w=self.window; v=w.valves_view; w.tabs.setCurrentWidget(v)
        w.resize(700,500); self.app.processEvents()
        first=v.edits['intake']['seat_mm']; second=v.edits['intake']['throat_mm']
        first.setFocus(); QTest.keyClick(first,Qt.Key.Key_Tab)
        self.assertIs(self.app.focusWidget(),second)
        self.assertEqual(v.horizontalScrollBar().maximum(),0)
        second.setText('no'); self.assertFalse(v.plots['intake'][1].values)
        self.assertTrue(second.property('invalid'))


if __name__=='__main__': unittest.main()
