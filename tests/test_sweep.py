"""Controles de RPM/serie. Dobles explícitos, sin ejecuciones físicas aceptadas."""
from copy import deepcopy
from dataclasses import asdict, replace
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from PySide6.QtCore import QProcess
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from motorsim.project import ProjectError
from motorsim.simulation_case import SyntheticCase
from motorsim.simulation import Model, sample, HEAT, BURN, burn_rate
from motorsim.project_case import validate_rpm
from motorsim.reference_results import project_inputs, reference_inputs, validated_model, save_result, load_result, ResultError
from motorsim.sweep import plan_rpms, validate_request, execute_sweep, load_sweep, write_index
from motorsim.sweep_view import export_sweep_csv
from motorsim.comparison import compatibility_errors
from motorsim.window import MainWindow
from test_reference_results import edit_payload, diagnostic
from test_project_simulation import project_diagnostic
from test_comparison import fixture


def inputs(rpm=2500):
    project=replace(SyntheticCase().project_geometry,name='DOBLE DE PRUEBA RPM')
    return project_inputs(project,dict(kind='project',project_name=project.name,source_path=None,dirty=True),rpm=rpm)


def request():return dict(common_inputs=inputs(),rpms=[2500,3000,3500])


def diagnostic_point(folder,cancelled,report,*,inputs):
    """Diagnóstico de estado inicial, no integración ni convergencia."""
    folder.mkdir()
    model,profile=validated_model(inputs);y=model.initial_state()
    rows=[sample(a,y,model.evaluate(a,y)[1],rpm=model.case.rpm) for a in (180,180.5)]
    result=dict(profile=asdict(profile),cycles=[],converged=False,seconds=.1,peak_process_MiB=25.,
        stop='diagnóstico de prueba cancelado',last_two_cycles=[],partial=dict(samples=rows,state=y[:12]))
    save_result(folder,result,'cancelled',inputs,{})
    report(dict(event='finished',timings=dict(setup_seconds=.01,writing_seconds=.02,integration_seconds=.1,wall_seconds=.13)))
    return 130


class RpmTests(unittest.TestCase):
    def test_plan_strict_bounds_types_endpoint(self):
        self.assertEqual(plan_rpms(2500,3500,500),[2500,3000,3500])
        self.assertEqual(plan_rpms(2500,3500,250),[2500,2750,3000,3250,3500])
        for rpm in (True,2500.,'3000',None,float('nan'),float('inf'),2499,15001):
            with self.subTest(rpm=rpm),self.assertRaises(ProjectError):validate_rpm(rpm)
        for args in ((2500,3500,300),(3000,2500,500),(2500,2500,1),(2500,3500,0),
                     (2500,3500,100),(2500,3500,True),(2500,3500,500.)):
            with self.subTest(args=args),self.assertRaises(ProjectError):plan_rpms(*args)
        for rpms in ([2500,3500,3000],[2500,2750,3500],[2500,2500],[2500,15001]):
            with self.assertRaises(ValueError):validate_request(dict(common_inputs=inputs(),rpms=rpms))

    def test_angular_temporal_dependencies_and_initial_recipe(self):
        ref=reference_inputs();models=[validated_model(inputs(rpm))[0] for rpm in (2500,3000,3500)]
        for model,rpm in zip(models,(2500,3000,3500)):
            self.assertEqual(model.rate,6*rpm)
            self.assertAlmostEqual(360/model.rate,60/rpm)
            self.assertEqual(model.case.heat_start_deg,350);self.assertEqual(model.case.heat_duration_deg,40)
            self.assertEqual(model.initial_state(),models[1].initial_state())
            self.assertEqual(model.case.initial_pty,SyntheticCase().initial_pty)
            v,dv,_=model.geometry(90);_,base_dv,_=models[1].geometry(90)
            self.assertAlmostEqual(dv[2],base_dv[2]*rpm/3000)
            # Estado admisible a 360°, con inventarios construidos a esa geometría.
            y=model.initial_state();volumes=model.geometry(360)[0];initial=model.geometry(180)[0]
            for i in range(4):
                for j in range(3):y[3*i+j]*=volumes[i]/initial[i]
            heat=(350,1e-5);dy,_=model.evaluate(360,y,heat)
            expected=1e-5*burn_rate(360,350,40)*6*rpm
            self.assertAlmostEqual(dy[BURN],expected)
            self.assertAlmostEqual(dy[HEAT],expected*model.case.fresh_energy_j_kg)
            self.assertEqual(model.analytic(360,y,heat),models[1].analytic(360,y,heat))
            row=sample(540,model.initial_state(),model.evaluate(540,model.initial_state())[1],rpm=rpm)
            self.assertAlmostEqual(row['time_s'],60/rpm)
        self.assertEqual(ref,reference_inputs());self.assertEqual(SyntheticCase().rpm,3000)

    def test_process_reconstructs_rpm_not_arbitrary_conditions(self):
        from motorsim.reference_run import execute
        with tempfile.TemporaryDirectory() as d:
            for mutate in (lambda x:x['operating_point'].update(rpm=3000.),
                           lambda x:x['operating_point'].update(rpm=None),
                           lambda x:x['case'].update(rpm=3000),
                           lambda x:x['case'].update(heat_duration_deg=50)):
                data=inputs();mutate(data)
                with patch('motorsim.reference_run.run_adaptive') as run,self.assertRaises(ValueError):
                    execute(Path(d)/'blocked',threading.Event(),inputs=data)
                run.assert_not_called();self.assertFalse((Path(d)/'blocked').exists())

    def test_v3_time_angle_and_old_versions(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);new=root/'new'
            diagnostic_point(new,threading.Event(),lambda x:None,inputs=inputs(3500))
            loaded=load_result(new/'manifest.json');self.assertEqual(loaded['manifest']['version'],3)
            self.assertAlmostEqual(loaded['samples']['partial'][1]['time_s'],.5/21000)
            edit_payload(new,'samples.json',lambda x:x['partial'][1].update(time_s=.5/18000))
            with self.assertRaisesRegex(ResultError,'Tiempo/ángulo'):load_result(new/'manifest.json')
            for version,writer in ((1,diagnostic),(2,project_diagnostic)):
                folder=root/str(version);folder.mkdir();r=load_result(writer(folder))
                self.assertEqual(r['manifest']['version'],version);self.assertEqual(r['inputs']['case']['rpm'],3000)

    def test_ab_old_and_new_effective_conditions(self):
        a=fixture();b=deepcopy(a);b['inputs']=inputs(3000)
        self.assertFalse(compatibility_errors(a,b))
        a['inputs']=reference_inputs();self.assertFalse(compatibility_errors(a,b))
        b['inputs']=inputs(2500);self.assertTrue(any('Régimen' in e for e in compatibility_errors(a,b)))

    def test_individual_records_separate_times_with_controlled_runner(self):
        from motorsim.reference_run import execute
        from itertools import count
        model,profile=validated_model(inputs())
        result=dict(profile=asdict(profile),cycles=[],converged=False,seconds=0.,
                    stop='doble sin integración',last_two_cycles=[],partial=None)
        with tempfile.TemporaryDirectory() as d,patch('motorsim.reference_run.run_adaptive',return_value=result):
            messages=[];folder=Path(d)/'point'
            # El reloj Windows puede registrar 0 s para una escritura diminuta.
            # Un reloj controlado prueba la separación sin depender de su resolución.
            with patch('motorsim.reference_results.time.monotonic',side_effect=count(100,.01)):
                execute(folder,threading.Event(),messages.append,inputs=inputs())
            loaded=load_result(folder/'manifest.json')
            timing=loaded['manifest']['timings']
            self.assertEqual(timing,messages[-1]['timings'])
            self.assertEqual(timing['integration_seconds'],0)
            self.assertGreater(timing['writing_seconds'],0)
            self.assertGreater(timing['wall_seconds'],timing['writing_seconds'])


class SweepTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)

    def test_diagnostic_reopen_integrity_and_csv(self):
        folder=self.root/'series'
        execute_sweep(folder,threading.Event(),lambda x:None,request(),run_point=diagnostic_point)
        loaded=load_sweep(folder/'series.json')
        self.assertEqual([p['state'] for p in loaded['index']['points']],['cancelled','not_executed','not_executed'])
        self.assertIsNone(loaded['results'][1]);self.assertEqual(loaded['index']['integration_seconds'],.1)
        export_sweep_csv(self.root/'csv',loaded)
        with (self.root/'csv/serie.csv').open(encoding='utf-8',newline='') as f:rows=list(csv.DictReader(f))
        self.assertEqual(len(rows),3)
        for row in rows:
            for key in ('W_C_J_per_cycle','W_K_J_per_cycle','p_max_absolute_Pa'):self.assertEqual(row[key],'')
        self.assertEqual(rows[1]['cycles'],'');self.assertEqual(rows[0]['cycles'],'0')
        self.assertEqual(rows[0]['run_id'],loaded['results'][0]['manifest']['run_id'])
        original=deepcopy(loaded['index'])
        mutations=[lambda x:x['points'][0].update(result='../outside/manifest.json'),
                   lambda x:x.update(series_id='a'*32),
                   lambda x:x['common_inputs']['project_snapshot'].update(compression_ratio=8.2),
                   lambda x:x['points'][0].update(run_id='another'),
                   lambda x:x['points'][1].update(state='running'),
                   lambda x:x.update(integration_seconds=2),
                   lambda x:x.update(state='converged'),
                   lambda x:x.update(interface_wall_seconds=float('nan'))]
        for mutate in mutations:
            index=deepcopy(original);mutate(index)
            (folder/'series.json').write_text(json.dumps(index),encoding='utf-8')
            with self.assertRaises(ResultError):load_sweep(folder/'series.json')
        write_index(folder,original)
        other=self.root/'other';execute_sweep(other,threading.Event(),lambda x:None,request(),run_point=diagnostic_point)
        # Hash y run_id coincidentes no permiten apropiarse de un punto de otra serie.
        for file in (other/'point-01').glob('*.json'):(folder/'point-01'/file.name).write_bytes(file.read_bytes())
        original['points'][0].update(manifest_sha256=hashlib.sha256((folder/'point-01/manifest.json').read_bytes()).hexdigest(),
                                    run_id=load_result(folder/'point-01/manifest.json')['manifest']['run_id'])
        write_index(folder,original)
        with self.assertRaisesRegex(ResultError,'ajeno'):load_sweep(folder/'series.json')

    def controlled(self,stop=None,cancel_between=False,cancel_during=False):
        """load_result doble: estados de control, nunca archivos físicos convergidos."""
        data=request();event=threading.Event();calls=[];stored={};messages=[]
        def run(folder,cancelled,report,*,inputs):
            model,_=validated_model(inputs);calls.append(deepcopy(inputs))
            self.assertEqual(model.initial_state()[:12],inputs['initial_state'])
            self.assertEqual(inputs['project_snapshot']['compression_ratio'],8)
            data['common_inputs']['project_snapshot']['compression_ratio']=9
            data['rpms'][2]=3400
            folder.mkdir();(folder/'manifest.json').write_text('DOBLE CONTROLADO')
            state='error' if len(calls)==stop else 'converged'
            if cancel_during:cancelled.set();state='cancelled'
            stored[str(folder/'manifest.json')]=dict(inputs=inputs,status=state,manifest=dict(run_id='double'),
                result=dict(seconds=.1,stop='control de prueba',cycles=[]))
            report(dict(event='finished',timings=dict(setup_seconds=.01,writing_seconds=.02,integration_seconds=.1,wall_seconds=.13)))
        def progress(message):
            messages.append(message)
            if cancel_between and message['event']=='point_finished':event.set()
        with patch('motorsim.sweep.load_result',side_effect=lambda p:stored[str(p)]):
            execute_sweep(self.root/'control',event,progress,data,run_point=run)
        return calls,json.loads((self.root/'control/series.json').read_text()),messages

    def test_single_copy_independent_starts_all_points(self):
        calls,index,_=self.controlled()
        self.assertEqual([x['case']['rpm'] for x in calls],[2500,3000,3500])
        self.assertEqual(index['rpms'],[2500,3000,3500]);self.assertEqual(index['state'],'converged')
        self.assertEqual(calls[0]['initial_state'],calls[2]['initial_state'])
        self.assertEqual([x['series_context']['point_index'] for x in calls],[0,1,2])

    def test_intermediate_failure_preserves_prefix_no_retry(self):
        calls,index,_=self.controlled(stop=2)
        self.assertEqual(len(calls),2)
        self.assertEqual([p['state'] for p in index['points']],['converged','error','not_executed'])
        self.assertIsNotNone(index['points'][1]['result']);self.assertEqual(index['state'],'stopped')

    def test_cancel_between(self):
        calls,index,_=self.controlled(cancel_between=True)
        self.assertEqual(len(calls),1);self.assertEqual(index['state'],'cancelled')
        self.assertEqual(index['points'][1]['state'],'not_executed')

    def test_cancel_during(self):
        calls,index,_=self.controlled(cancel_during=True)
        self.assertEqual(len(calls),1);self.assertEqual(index['points'][0]['state'],'cancelled')
        self.assertEqual(index['points'][1]['state'],'not_executed')

    def test_cancel_before_and_exclusive_folder(self):
        event=threading.Event();event.set()
        with patch('motorsim.reference_run.execute') as run:
            execute_sweep(self.root/'cancel',event,lambda x:None,request());run.assert_not_called()
            self.assertEqual(load_sweep(self.root/'cancel/series.json')['index']['state'],'cancelled')
            with self.assertRaises(FileExistsError):execute_sweep(self.root/'cancel',event,lambda x:None,request())


class SweepWindowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])

    def setUp(self):
        self.window=MainWindow();self.view=self.window.simulation_view
        self.window._activate(replace(SyntheticCase().project_geometry,name='PRUEBA'),None)
        self.view.origin_combo.setCurrentIndex(1)

    def tearDown(self):
        self.window.dirty=False;self.window.close();self.window.deleteLater();self.app.processEvents()

    def test_ui_strict_plan_and_one_process_snapshot(self):
        self.assertEqual(self.view.rpm_edit.text(),'3000')
        for text in ('','3000.0','nan','3,000','-2500','15001'):
            self.view.rpm_edit.setText(text)
            with patch.object(QProcess,'start') as start:self.view.start();start.assert_not_called()
            self.assertTrue(self.view.error_label.text())
        self.view.mode_combo.setCurrentIndex(1)
        self.assertIn('2500, 3000, 3500',self.view.plan_label.text())
        with tempfile.TemporaryDirectory() as d,patch.object(QProcess,'start') as start:
            self.view.start(output=Path(d)/'series');process=self.view.process
            self.assertIn('--sweep-input',process.arguments())
            captured=json.loads(self.view._request_path.read_text(encoding='utf-8'))
            self.window.numeric_edits['compression_ratio'].setText('8.2')
            self.view.start(output=Path(d)/'second');self.assertEqual(start.call_count,1)
            self.assertIs(self.view.process,process);self.assertIn('configuración anterior',self.view.stale_label.text())
            self.assertEqual(captured['common_inputs']['project_snapshot']['compression_ratio'],8)
            self.assertFalse(self.view.open_sweep_button.isEnabled())
            # Doble de proceso que no arrancó: limpiar, sin escribir cancel en pipe inexistente.
            self.view._finish_cleanup()

    def test_reopen_without_process_preserves_editor_and_stale(self):
        with tempfile.TemporaryDirectory() as d:
            folder=Path(d)/'series'
            execute_sweep(folder,threading.Event(),lambda x:None,request(),run_point=diagnostic_point)
            before=self.window.project()
            with patch.object(QProcess,'start') as start:
                self.view.open_sweep(path=folder/'series.json');start.assert_not_called()
            self.assertEqual(self.window.project(),before)
            self.assertTrue(self.view.stale_label.text())
            dialog=self.view.sweep_dialog
            self.assertEqual(dialog.table.rowCount(),3)
            self.assertEqual(dialog.table.item(0,4).text(),'');self.assertFalse(dialog.point_button.isEnabled())
            previous=self.view.sweep
            self.view.open_sweep(path=folder/'missing.json');self.assertIs(self.view.sweep,previous)
            dialog.close()

    def test_supervision_uses_point_clock_not_series_clock(self):
        import time
        self.view._started=time.monotonic()-120;self.view._point_started=time.monotonic()-10
        with patch.object(self.view,'cancel') as cancel:self.view._tick();cancel.assert_not_called()
        self.view._point_started=time.monotonic()-66
        with patch.object(self.view,'cancel') as cancel:self.view._tick();cancel.assert_called_once()

    def test_existing_destination_and_race_do_not_rewrite_other_series(self):
        with tempfile.TemporaryDirectory() as d:
            folder=Path(d)/'previous'
            execute_sweep(folder,threading.Event(),lambda x:None,request(),run_point=diagnostic_point)
            original=(folder/'series.json').read_bytes()
            self.view.mode_combo.setCurrentIndex(1)
            with patch.object(QProcess,'start') as start:
                self.view.start(output=folder);start.assert_not_called()
            self.assertEqual(original,(folder/'series.json').read_bytes())
            # Simula carrera tras preflight: hijo no emitió sweep_started propio.
            self.view.output=folder;self.view._running_sweep=True;self.view._series_id=None
            self.view._finished(2,QProcess.ExitStatus.NormalExit)
            self.assertEqual(original,(folder/'series.json').read_bytes())
            self.assertIsNone(self.view.sweep)

    def test_close_protects_edits_cancels_series_and_opens_no_dialog(self):
        self.window.show();self.window.name_edit.setText('Edición pendiente')
        self.view.mode_combo.setCurrentIndex(1)
        with tempfile.TemporaryDirectory() as d,patch.object(QProcess,'start'),patch.object(QProcess,'write',return_value=7) as write:
            folder=Path(d)/'close'
            self.view.start(output=folder)
            with patch.object(self.window,'_ask_changes',return_value='cancel'):self.window.close()
            self.assertTrue(self.view.active);self.assertFalse(self.view.cancel_requested)
            with patch.object(self.window,'_ask_changes',return_value='discard'):self.window.close()
            write.assert_called_once_with(b'cancel\n');self.assertTrue(self.view.cancel_requested)
            captured=json.loads(self.view._request_path.read_text(encoding='utf-8'))
            execute_sweep(folder,threading.Event(),lambda x:None,captured,run_point=diagnostic_point)
            self.view._series_id=load_sweep(folder/'series.json')['index']['series_id']
            self.view._finished(130,QProcess.ExitStatus.NormalExit)
            QTest.qWait(20)
            self.assertFalse(self.view.active);self.assertFalse(self.window.isVisible())
            self.assertIsNone(self.view.sweep_dialog)
