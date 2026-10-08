"""Contratos/Qt 4T, sin nuevas integraciones completas."""
from dataclasses import replace,asdict
from copy import deepcopy
import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
from motorsim.four_stroke import geometry,FourStrokeModel,FourStrokeCase
from motorsim.project import Project,ProjectError
from motorsim.reference_results import (project_inputs,reference_inputs,validated_model,save_result,load_result,ResultError)
from motorsim.simulation import sample
from motorsim.comparison import compare_results,ComparisonError,export_csv
from motorsim.external_data import declarations,DEFINITIONS,prepare_import,save_import,load_import,contrast,ExternalDataError
from motorsim.sweep import point_inputs,execute_sweep,load_sweep
from motorsim.window import MainWindow
from process_double import DiagnosticProcess
from test_reference_results import edit_payload


def inputs4(rpm=3000):
    p=geometry()
    return project_inputs(p,dict(kind='project',project_name=p.name,source_path=None,dirty=True),rpm=rpm)


def diagnostic(folder,inputs):
    model,profile=validated_model(inputs);y=model.initial_state();a=model.case.initial_angle_deg
    row=sample(a,y,model.evaluate(a,y)[1],rpm=model.case.rpm,initial_angle=a,layout=model.layout)
    result=dict(profile=asdict(profile),converged=False,cycles=[],last_two_cycles=[],
        partial=dict(angle_deg=a,state=y[:9],samples=[row]),seconds=0.,peak_process_MiB=20.,stop='cancelación de prueba sin integrar')
    folder.mkdir();save_result(folder,result,'cancelled',inputs,{})
    return folder/'manifest.json'


class FourIntegrationTests(unittest.TestCase):
    def test_valves_timing_ducts_and_geometry_reach_model(self):
        p=geometry();base,_=validated_model(inputs4())
        variants=[replace(p,bore_mm=55),
            replace(p,four_stroke=replace(p.four_stroke,intake=replace(p.four_stroke.intake,lift_mm=3))),
            replace(p,four_stroke=replace(p.four_stroke,intake=replace(p.four_stroke.intake,opening_deg=5))),
            replace(p,four_stroke=replace(p.four_stroke,ducts=replace(p.four_stroke.ducts,
                intake=(replace(p.four_stroke.ducts.intake[0],length_mm=110),))))]
        for project in variants:
            inputs=project_inputs(project,dict(kind='project',project_name=project.name,source_path=None,dirty=True),rpm=3000)
            model,_=validated_model(inputs)
            self.assertNotEqual(model.evaluate(60,model.initial_state()),base.evaluate(60,base.initial_state()))

    def test_four_comparison_phase_no_carter_and_cross_cycle_rejected(self):
        from test_comparison import fixture
        a=fixture();a['inputs']=inputs4();a['samples']['cycles']=[[
            dict(angle_deg=720*9+x,p_T_Y=[[100000,300,1],[100000+x,300,0],[100000,300,0]],V_m3=[1e-5,2e-5,1e-5]) for x in (0,360,720)]]
        for cycle in a['result']['cycles']:
            cycle.pop('W_K_J');cycle['Y']=[1,0,0];cycle['cycle']=10
        b=deepcopy(a)
        p=replace(geometry(),compression_ratio=8.2)
        b['inputs']=project_inputs(p,dict(kind='project',project_name=p.name,source_path=None,dirty=True),rpm=3000)
        for cycle in b['result']['cycles']:cycle['cycle']=7
        for row in b['samples']['cycles'][-1]:row['angle_deg']-=720*3
        compared=compare_results(a,b)
        self.assertEqual([r['angle_cycle_deg'] for r in compared['curves'][1]],[0,360,720])
        self.assertEqual(len(compared['metrics']),7)
        self.assertEqual(compared['metrics'][0]['unit'],'J/720°')
        self.assertEqual(len(compared['differences']['geometry']),1)
        with self.assertRaises(ComparisonError):compare_results(a,fixture())
        with tempfile.TemporaryDirectory() as root:
            paths=export_csv(Path(root)/'csv',compared)
            self.assertIn('J/720°',paths[0].read_text(encoding='utf-8'))
            self.assertNotIn('W_K',paths[0].read_text(encoding='utf-8'))

    def test_rpm_time_derivative_and_heat(self):
        a=FourStrokeModel(FourStrokeCase(rpm=2500));b=FourStrokeModel(FourStrokeCase(rpm=3500))
        y=a.initial_state();y[5]=y[3]*.5
        self.assertEqual(y,b.initial_state()[:5]+[y[5]]+b.initial_state()[6:])
        self.assertAlmostEqual(b.geometry(90)[1][1]/a.geometry(90)[1][1],1.4)
        heat=(350,y[5]);da=a.evaluate(370,y,heat)[0];db=b.evaluate(370,y,heat)[0]
        self.assertAlmostEqual(db[a.layout.heat]/da[a.layout.heat],1.4)
        for model in (a,b):
            row=sample(720,y,model.evaluate(720,y)[1],rpm=model.case.rpm,initial_angle=0,layout=model.layout)
            self.assertAlmostEqual(row['time_s'],120/model.case.rpm)

    def test_reference_project_identical_numeric_inputs(self):
        a,_=validated_model(reference_inputs('4T'));b,_=validated_model(inputs4())
        self.assertEqual(a.initial_state(),b.initial_state())
        for angle in (0,110,220,350,360,390,500,610,720):self.assertEqual(a.geometry(angle),b.geometry(angle))
        altered=inputs4();altered['project_snapshot']['compression_ratio']=8.2
        with self.assertRaises(ResultError):validated_model(altered)

    def test_diagnostic_reopen_strict_dimensions_phase_and_no_carter(self):
        with tempfile.TemporaryDirectory() as root:
            folder=Path(root)/'r';path=diagnostic(folder,inputs4());r=load_result(path)
            self.assertEqual(r['manifest']['version'],4);self.assertEqual(len(r['samples']['partial'][0]['state']),9)
            for change in (lambda d:d['partial'][0]['state'].append(0),
                           lambda d:d['partial'][0].update(W_K_J=0),
                           lambda d:d['partial'][0].update(time_s=1),
                           lambda d:d['partial'][0]['flows_kg_s_W_kg_s'].append([0,0,0])):
                original=(folder/'samples.json').read_bytes();manifest=(folder/'manifest.json').read_bytes()
                edit_payload(folder,'samples.json',change)
                with self.assertRaises(ResultError):load_result(path)
                (folder/'samples.json').write_bytes(original);(folder/'manifest.json').write_bytes(manifest)

    def test_sweep_fresh_copies_and_stop_without_integrating(self):
        common=inputs4(2500)
        copies=[point_inputs(common,'a'*32,i,rpm) for i,rpm in enumerate((2500,3000,3500))]
        models=[validated_model(p)[0] for p in copies]
        self.assertEqual(models[0].initial_state(),models[2].initial_state())
        calls=[]
        def run_point(folder,cancel,report,*,inputs):
            calls.append(inputs['case']['rpm']);path=diagnostic(folder,inputs)
            report(dict(event='finished',timings=dict(integration_seconds=0,setup_seconds=0,writing_seconds=0,wall_seconds=0)))
        with tempfile.TemporaryDirectory() as root:
            folder=Path(root)/'series'
            execute_sweep(folder,threading.Event(),lambda data:None,dict(common_inputs=common,rpms=[2500,3000,3500]),run_point=run_point)
            data=load_sweep(folder/'series.json')
            self.assertEqual(calls,[2500]);self.assertEqual([p['state'] for p in data['index']['points']],['cancelled','not_executed','not_executed'])

    def test_external_cycle_explicit_and_history_not_reinterpreted(self):
        with tempfile.TemporaryDirectory() as root:
            raw=b'rpm,value\n3000,50\n';key='W_C_4T_J'
            ext=save_import(Path(root)/'4t',prepare_import(raw,declarations(key,'J/ciclo',DEFINITIONS[key],provenance='Ejemplo sintético')))
            sweep=dict(index=dict(common_inputs=inputs4(),series_id='unit',points=[dict(rpm=3000,state='converged',reason='unit',run_id='unit')]),results=[dict(result=dict(cycles=[dict(W_C_J=51.)]))])
            self.assertEqual(contrast(ext,sweep)['rows'][0]['difference'],1)
            for key in ('W_C_J','p_max_Pa'):
                unit='J/ciclo' if key=='W_C_J' else 'Pa'
                old=save_import(Path(root)/key,prepare_import(raw,declarations(key,unit,DEFINITIONS[key])))
                with self.assertRaises(ExternalDataError):contrast(old,sweep)

    def test_external_pressure_declares_cycle_and_preserves_bar_conversion(self):
        with tempfile.TemporaryDirectory() as root:
            key='p_max_4T_Pa'
            ext=save_import(Path(root)/'4t',prepare_import(b'rpm,value\n3000,2\n',declarations(key,'bar',DEFINITIONS[key],provenance='Ejemplo sintético')))
            reopened=load_import(Path(root)/'4t/metadata.json')
            self.assertEqual(reopened['metadata'],ext['metadata'])
            sweep=dict(index=dict(common_inputs=inputs4(),series_id='unit',points=[dict(rpm=3000,state='converged',reason='unit',run_id='unit')]),results=[dict(result=dict(cycles=[dict(p_max_Pa=210000.)]))])
            self.assertEqual(contrast(reopened,sweep)['rows'][0]['difference'],10000)
            sweep['index']['common_inputs']=reference_inputs('2T')
            with self.assertRaises(ExternalDataError):contrast(reopened,sweep)


class FourWindowIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
    def setUp(self):
        self.w=MainWindow();self.w._activate(geometry(),None);self.v=self.w.simulation_view
        self.v.origin_combo.setCurrentIndex(1)
    def tearDown(self):
        if self.v.active:
            self.v.cancel()
            for _ in range(200):
                if not self.v.active:break
                QTest.qWait(20)
        self.w.dirty=False;self.w.close();self.w.deleteLater();QTest.qWait(10)
    def test_snapshot_ignores_inactive_2t_and_aggregates_active_errors(self):
        self.w.ports_view.crankcase_edit.setText('invalid')
        self.w.ports_view.intake.edits['skirt_mm'].setText('invalid')
        self.w.numeric_edits['compression_ratio'].setText('8,2')
        captured=self.v._capture();self.assertEqual(captured['project_snapshot']['compression_ratio'],8.2)
        self.assertTrue(captured['origin']['dirty']);self.assertIsNone(captured['project_snapshot']['crankcase_volume_bdc_cm3'])
        self.w.valves_view.edits['intake']['lift_mm'].setText('no')
        self.w.valves_view.edits['exhaust']['stem_mm'].setText('no')
        with self.assertRaises(ProjectError) as context:self.v._capture()
        self.assertIn('intake',str(context.exception));self.assertIn('exhaust',str(context.exception))
    @patch('motorsim.simulation_view.QProcess',DiagnosticProcess)
    def test_snapshot_process_single_cancel_close_and_stale(self):
        with tempfile.TemporaryDirectory() as root:
            self.w.show();self.v.start(output=Path(root)/'r');proc=self.v.process
            self.v.start(output=Path(root)/'duplicate');self.assertIs(proc,self.v.process)
            self.w.numeric_edits['compression_ratio'].setText('8.2')
            self.assertIn('anterior',self.v.stale_label.text())
            for _ in range(200):
                if 'RHS:' in self.v.progress_label.text():break
                QTest.qWait(20)
            with patch.object(self.w,'_ask_changes',return_value='cancel'):self.assertFalse(self.w.close())
            with patch.object(self.w,'_ask_changes',return_value='discard'):self.w.close()
            for _ in range(200):
                if not self.v.active:break
                QTest.qWait(20)
            self.assertFalse(self.v.active);self.assertFalse(self.v.forced)
            r=load_result(Path(root)/'r/manifest.json');self.assertEqual(r['inputs']['project_snapshot']['compression_ratio'],8)
            self.assertEqual(r['status'],'cancelled');self.assertFalse(self.v.angle_plot.points)


if __name__=='__main__':unittest.main()
