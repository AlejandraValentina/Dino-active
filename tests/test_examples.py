"""Ejemplos sintéticos; comparación con fixtures, sin integrar física."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from dataclasses import replace
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from PySide6.QtWidgets import QApplication
from motorsim.examples import EXAMPLES, NOTICE, example_project
from motorsim.simulation_case import geometry as geometry2
from motorsim.four_stroke import geometry as geometry4
from motorsim.project_case import execution_errors
from motorsim.reference_results import project_inputs, validated_model
from motorsim.storage import load_project
from motorsim.comparison import compare_results
from motorsim.window import MainWindow
from motorsim.project import ProjectError
from test_comparison import fixture


class ExampleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
    def setUp(self):
        self.w=MainWindow();self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
    def tearDown(self):
        self.w.dirty=False;self.w.close();self.w.deleteLater();self.app.processEvents()
    def test_canonical_fields_variants_and_identification(self):
        for prefix,factory in (('2t',geometry2),('4t',geometry4)):
            original=factory();a=example_project(prefix+'-reference');b=example_project(prefix+'-compression')
            self.assertEqual(replace(a,name=original.name,notes=original.notes),original)
            self.assertEqual(replace(b,name=a.name,compression_ratio=a.compression_ratio),a)
            self.assertEqual(b.compression_ratio,8.2);self.assertEqual(a.compression_ratio,8)
            self.assertEqual(original,factory())
            for p in (a,b):
                self.assertIn(NOTICE,p.name);self.assertIn(NOTICE,p.notes)
                p.validate();self.assertEqual(execution_errors(p),[])
    def test_each_action_loads_editable_project_and_actual_simulation_inputs(self):
        w=self.w
        for key in EXAMPLES:
            with patch.object(w,'_ask_changes',return_value='discard'):w.example_actions[key].trigger()
            p=example_project(key);self.assertEqual(w.project(),p)
            self.assertTrue(w.dirty);self.assertIsNone(w.path)
            self.assertEqual(w.navigation.current,'summary')
            active='motor2' if p.cycle=='2T' else 'motor4'
            self.assertFalse(w.navigation.items[active].isHidden())
            self.assertTrue(w.navigation.items['motor4' if active=='motor2' else 'motor2'].isHidden())
            self.assertEqual(w.simulation_view.origin_combo.currentIndex(),1)
            inputs=w.simulation_view._capture();model,_=validated_model(inputs)
            self.assertEqual(inputs['case']['project_geometry']['compression_ratio'],p.compression_ratio)
            self.assertEqual(w.simulation_view.inputs,inputs)
            self.assertEqual(model.case.project_geometry,p)
        w.numeric_edits['compression_ratio'].setText('8.3')
        self.assertEqual(w.simulation_view._capture()['case']['project_geometry']['compression_ratio'],8.3)
    def test_save_asks_new_path_and_roundtrips(self):
        w=self.w;w.load_example('2t-compression');p=w.project();target=Path(self.tmp.name)/'nuevo.json'
        with patch.object(w,'_choose_file',return_value=target) as choose:
            self.assertTrue(w.save());choose.assert_called_once_with(True)
        self.assertEqual(load_project(target),p);self.assertEqual(w.path,target);self.assertFalse(w.dirty)
    def test_cancel_and_cancelled_save_preserve_everything(self):
        w=self.w;w.load_example('2t-reference');before=w.project()
        for choice in ('cancel','save'):
            with patch.object(w,'_ask_changes',return_value=choice),patch.object(w,'_choose_file',return_value=None):
                w.load_example('4t-compression')
            self.assertEqual(w.project(),before);self.assertTrue(w.dirty);self.assertIsNone(w.path)
            self.assertEqual(w.cycle_combo.currentText(),'2T')
    def test_save_previous_then_load_and_discard(self):
        w=self.w;w.load_example('2t-reference');previous=w.project();target=Path(self.tmp.name)/'anterior.json'
        with patch.object(w,'_ask_changes',return_value='save'),patch.object(w,'_choose_file',return_value=target):
            w.load_example('4t-reference')
        self.assertEqual(load_project(target),previous);self.assertIsNone(w.path);self.assertTrue(w.dirty)
        with patch.object(w,'_ask_changes',return_value='discard'):w.load_example('4t-compression')
        self.assertEqual(w.project(),example_project('4t-compression'))
        self.assertEqual(load_project(target),previous)
    def test_failed_save_blocks_loading_and_keeps_path(self):
        w=self.w;w.load_example('2t-reference');before=w.project();w.path=Path(self.tmp.name)/'existing.json'
        with patch.object(w,'_ask_changes',return_value='save'),patch('motorsim.window.save_project',side_effect=ProjectError('Fallo de escritura')), patch.object(w,'_error'):
            w.load_example('4t-reference')
        self.assertEqual(w.project(),before);self.assertTrue(w.dirty)
        self.assertEqual(w.path,Path(self.tmp.name)/'existing.json')
    def test_comparison_reference_and_variant_fixtures(self):
        for prefix in ('2t','4t'):
            a,b=fixture(),fixture(True)
            for result,key in ((a,prefix+'-reference'),(b,prefix+'-compression')):
                p=example_project(key)
                result['inputs']=project_inputs(p,dict(kind='project',project_name=p.name,source_path=None,dirty=True))
                if prefix=='4t':
                    result['samples']['cycles']=[[dict(angle_deg=x,p_T_Y=[[0,0,0],[100000,300,0]],V_m3=[0,1e-5]) for x in (0,360,720)]]
                    for c in result['result']['cycles']:
                        c['Y']=c['Y'][:3];c.pop('W_K_J')
            comparison=compare_results(a,b)
            self.assertEqual(len(comparison['differences']['geometry']),1)
            self.assertEqual(comparison['differences']['geometry'][0]['field'],'Relación de compresión geométrica')

if __name__=='__main__':unittest.main()
