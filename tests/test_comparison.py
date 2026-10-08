"""Fixtures declarados para comparar datos, no ejecuciones ni evidencia física."""
from copy import deepcopy
from dataclasses import replace
import csv
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QProcess
from PySide6.QtTest import QTest
from motorsim.comparison import (compare_results,compatibility_errors,input_differences,export_csv,ComparisonError)
from motorsim.reference_results import reference_inputs,project_inputs,load_result,ResultError
from motorsim.simulation_case import SyntheticCase
from motorsim.window import MainWindow


def fixture(modified=False):
    """Solo contrato en memoria para aritmética/Qt; no se atribuye convergencia física."""
    project=replace(SyntheticCase().project_geometry,name='FIXTURE de comparación',compression_ratio=8.2 if modified else 8)
    inputs=project_inputs(project,dict(kind='project',project_name=project.name,source_path=None,dirty=modified))
    cycle=9 if modified else 10
    result=dict(W_C_J=12. if modified else 10.,W_K_J=-1. if modified else -2.,
                p_max_Pa=120000. if modified else 100000.,Y=[.2,.15,.5,.4] if modified else [.1,.2,.3,.4],
                balances_passed=True,cycle=cycle)
    rows=[dict(angle_deg=angle+360*(cycle-1),p_T_Y=[[0,0,0]]*2+[[pressure,300,0]],V_m3=[0,0,volume])
          for angle,pressure,volume in ((180,100000,3e-5),(360,120000,1e-5),(540,110000,3e-5))]
    return dict(inputs=inputs,manifest=dict(run_id='fixture-B' if modified else 'fixture-A'),status='converged',
                result=dict(cycles=[deepcopy(result) for _ in range(3)]),samples=dict(cycles=[rows]),path=Path('fixture/manifest.json'))


class ComparisonTests(unittest.TestCase):
    def setUp(self):self.a,self.b=fixture(),fixture(True)

    def test_identity_and_values_from_summary_not_curve(self):
        same=compare_results(self.a,self.a)
        self.assertTrue(all(r['difference']==0 for r in same['metrics']))
        self.assertFalse(same['differences']['geometry'])
        comparison=compare_results(self.a,self.b)
        expected=[(10,12,2,20),(-2,-1,1,50),(100000,120000,20000,20)]
        for row,(a,b,d,p) in zip(comparison['metrics'],expected):
            self.assertEqual((row['a'],row['b'],row['difference'],row['relative_percent']),(a,b,d,p))
        for row,delta in zip(comparison['metrics'][3:],[.1,-.05,.2,0]):
            self.assertAlmostEqual(row['difference'],delta)
            self.assertIsNone(row['relative_percent'])
        # A tiene máximo dibujado 120000 y máximo de resumen fixture 100000.
        self.assertEqual(comparison['metrics'][2]['a'],100000)

    def test_swap_rebases_relative_and_zero_has_no_denominator(self):
        one,two=compare_results(self.a,self.b),compare_results(self.b,self.a)
        for left,right in zip(one['metrics'],two['metrics']):self.assertEqual(left['difference'],-right['difference'])
        self.assertAlmostEqual(two['metrics'][0]['relative_percent'],-100/6)
        self.a['result']['cycles'][-1]['W_C_J']=0
        self.assertIsNone(compare_results(self.a,self.b)['metrics'][0]['relative_percent'])

    def test_all_geometric_and_descriptive_changes(self):
        diff=input_differences(self.a,self.b)
        self.assertEqual(len(diff['geometry']),1)
        self.assertEqual((diff['geometry'][0]['field'],diff['geometry'][0]['a'],diff['geometry'][0]['b']),
                         ('Relación de compresión geométrica',8,8.2))
        p=replace(SyntheticCase().project_geometry,name='Otro nombre',bore_mm=54.0)
        # Nombre, identidad, ruta, dirty, inventarios derivados y referencia/proyecto no son condiciones.
        left=deepcopy(self.a);left['inputs']=reference_inputs()
        right=deepcopy(self.a);right['inputs']=project_inputs(p,dict(kind='project',project_name=p.name,source_path='otra.json',dirty=True))
        self.assertFalse(compatibility_errors(left,right))
        self.assertFalse(input_differences(left,right)['geometry'])
        self.assertTrue(input_differences(left,right)['descriptive'])
        reordered=replace(p,ports=(p.ports[2],p.ports[0],p.ports[1]))
        right['inputs']=project_inputs(reordered,dict(kind='project',project_name=p.name,source_path=None,dirty=False))
        self.assertFalse(input_differences(left,right)['geometry'])
        self.assertFalse(any(r['section'].startswith('Transfer') for r in input_differences(left,right)['descriptive']))
        changed=replace(p,bore_mm=55,crankcase_volume_bdc_cm3=260,
            ports=(replace(p.ports[0],width_mm=21),*p.ports[1:]),intake=replace(p.intake,width_mm=21),
            ducts=replace(p.ducts,intake=(replace(p.ducts.intake[0],length_mm=110),)))
        right['inputs']=project_inputs(changed,dict(kind='project',project_name=p.name,source_path=None,dirty=False))
        sections={r['section'] for r in input_differences(left,right)['geometry']}
        self.assertEqual(sections,{'Ficha','Cárter','Escape 1','Admisión','Conducto admisión · tramo 1'})

    def test_each_condition_difference_and_missing_metadata_blocks(self):
        from motorsim.comparison import CONDITIONS
        for key in CONDITIONS:
            with self.subTest(key=key):
                other=deepcopy(self.b);other['inputs']['case'][key]='diferente'
                with self.assertRaises(ComparisonError):compare_results(self.a,other)
                other=deepcopy(self.b);del other['inputs']['case'][key]
                self.assertIn('Falta','\n'.join(compatibility_errors(self.a,other)))
        for key in ('model_version','variant','profile'):
            other=deepcopy(self.b);other['inputs'][key]='diferente'
            with self.assertRaises(ComparisonError):compare_results(self.a,other)
        for state in ('cancelled','error','not_converged'):
            other=deepcopy(self.b);other['status']=state
            with self.assertRaises(ComparisonError):compare_results(self.a,other)
        other=deepcopy(self.b);other['result']['cycles'][-1]['balances_passed']=False
        with self.assertRaises(ComparisonError):compare_results(self.a,other)

    def test_phase_and_pv_order_preserve_sources(self):
        before=deepcopy((self.a,self.b))
        comparison=compare_results(self.a,self.b)
        for rows in comparison['curves']:
            self.assertEqual([r['angle_cycle_deg'] for r in rows],[180,360,540])
            self.assertEqual([r['volume_m3'] for r in rows],[3e-5,1e-5,3e-5])
        self.assertEqual(comparison['curves'][0][0]['angle_original_deg'],3420)
        self.assertEqual(comparison['curves'][1][0]['angle_original_deg'],3060)
        self.assertEqual((self.a,self.b),before)

    def test_csv_exact_numbers_units_ids_and_escaping(self):
        self.a['manifest']['run_id']='fixture,"A"\nidentificador'
        data=compare_results(self.a,self.b)
        with tempfile.TemporaryDirectory() as d:
            paths=export_csv(Path(d)/'csv',data)
            with paths[0].open(encoding='utf-8',newline='') as f:summary=list(csv.DictReader(f))
            self.assertEqual(summary[0]['run_id_A'],'fixture,"A"\nidentificador')
            self.assertEqual(summary[0]['run_id_B'],'fixture-B')
            self.assertEqual(summary[0]['unit'],'J/ciclo')
            self.assertEqual(float(summary[0]['difference_B_minus_A']),2)
            self.assertEqual(summary[3]['relative_difference_percent'],'')
            with paths[1].open(encoding='utf-8',newline='') as f:curves=list(csv.DictReader(f))
            self.assertEqual(len(curves),6)
            self.assertEqual([r['configuration'] for r in curves],['A']*3+['B']*3)
            self.assertEqual(float(curves[1]['volume_m3']),1e-5)
            self.assertEqual(float(curves[1]['pressure_absolute_Pa']),120000)
            self.assertEqual(float(curves[3]['angle_cycle_deg']),180)

    def test_export_existing_or_second_write_failure_preserves_data(self):
        data=compare_results(self.a,self.b);before=deepcopy(data)
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);existing=root/'existente';existing.mkdir();(existing/'resumen.csv').write_text('no tocar')
            with self.assertRaises(ComparisonError):export_csv(existing,data)
            self.assertEqual((existing/'resumen.csv').read_text(),'no tocar')
            original=Path.open
            def broken(path,*a,**kw):
                if path.name=='curvas.csv':raise OSError('disco de prueba lleno')
                return original(path,*a,**kw)
            with patch.object(Path,'open',broken),self.assertRaisesRegex(ComparisonError,'No se exportó'):
                export_csv(root/'fallido',data)
            self.assertFalse((root/'fallido').exists())
            self.assertEqual(data,before)


class ComparisonWindowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])

    def setUp(self):
        self.window=MainWindow();self.window.name_edit.setText('Trabajo sin guardar')
        self.before=self.window.project()
        self.block=patch.object(QProcess,'start',side_effect=AssertionError('No debe calcular'))
        self.start=self.block.start();self.addCleanup(self.block.stop)
        self.window.simulation_view.show_comparison();self.view=self.window.simulation_view.comparison_dialog

    def tearDown(self):
        self.start.assert_not_called();self.assertEqual(self.window.project(),self.before);self.assertTrue(self.window.dirty)
        self.view.close();self.window.dirty=False;self.window.close();self.window.deleteLater();QTest.qWait(10)

    def choose(self,index,data):
        with patch('motorsim.comparison_view.load_result',return_value=data) as load:
            self.view.select_result(index,path=Path('fixture/manifest.json'))
            load.assert_called_once_with(Path('fixture/manifest.json'))

    def test_selection_invalid_preserves_then_incompatible_clears(self):
        self.choose(0,fixture());self.choose(1,fixture(True))
        self.assertTrue(self.view.export_button.isEnabled())
        prior=self.view.comparison
        with tempfile.TemporaryDirectory() as d:
            self.view.select_result(1,path=Path(d)/'manifest.json')
            self.assertIs(self.view.comparison,prior)
            self.assertIn('conserva',self.view.error_label.text())
        incompatible=fixture(True);incompatible['inputs']['profile']['name']='C'
        self.choose(1,incompatible)
        self.assertFalse(self.view.export_button.isEnabled())
        self.assertIn('Perfil',self.view.compatibility_label.text())
        self.assertEqual(self.view.table.rowCount(),0)
        self.assertFalse(self.view.angle_plot.series)

    def test_ui_values_curves_and_export_failure_do_not_calculate(self):
        self.choose(0,fixture());self.choose(1,fixture(True))
        self.assertEqual(self.view.table.item(0,4).text(),'2')
        self.assertIn('8 → 8.2',self.view.differences.toPlainText())
        self.assertEqual([p[0] for p in self.view.pv_plot.series[0]],[30,10,30])
        with tempfile.TemporaryDirectory() as d:
            files=self.view.export(folder=Path(d)/'export')
            self.assertEqual(len(files),2)
            self.view.export(folder=Path(d)/'export')
            self.assertIn('No se exportó',self.view.error_label.text())
            self.assertTrue(self.view.export_button.isEnabled())


class ExistingComparisonTests(unittest.TestCase):
    def test_existing_results_without_new_simulations(self):
        root=Path(__file__).resolve().parents[1]/'results/simulacion-2t/editor-20260915'
        if not (root/'B/manifest.json').exists():self.skipTest('Resultados reales locales no disponibles; no se recrean')
        files=[p for name in ('A','B','C') for p in (root/name).glob('*.json')]
        before={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
        with patch('motorsim.adaptive.run_adaptive',side_effect=AssertionError('No integrar')):
            a,b,c=[load_result(root/name/'manifest.json') for name in ('A','B','C')]
            comparison=compare_results(a,b)
            self.assertAlmostEqual(comparison['metrics'][0]['difference'],.14104542998868,places=11)
            self.assertEqual(len(comparison['curves'][0]),721)
            self.assertEqual(len(comparison['differences']['geometry']),1)
            with self.assertRaisesRegex(ComparisonError,'Perfil'):compare_results(b,c)
        self.assertEqual({str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in files},before)
