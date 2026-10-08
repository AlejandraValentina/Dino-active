"""Adaptador y Qt sin pantalla. No son ejecuciones completas A/B/C."""
from copy import deepcopy
from dataclasses import asdict, replace
import json
import os
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest

from motorsim.project import Project, ProjectError, Port, Intake, Ducts, DuctSegment, PORT_FIELDS, INTAKE_FIELDS, DUCT_FIELDS
from motorsim.project_case import build_project_case, execution_errors, configuration_key
from motorsim.reference_results import (project_inputs, reference_inputs, validated_model, save_result, load_result, ResultError)
from motorsim.reference_run import execute, main
from motorsim.simulation_case import SyntheticCase
from motorsim.simulation import Model, sample
from motorsim.window import MainWindow
from test_reference_results import edit_payload


def inputs_for(project=None):
    project = project or replace(SyntheticCase().project_geometry, name='PRUEBA de integración')
    return project_inputs(project, dict(kind='project', project_name=project.name, source_path='inexistente.json', dirty=True))


def project_diagnostic(folder, inputs=None):
    inputs = inputs or inputs_for()
    model, profile = validated_model(inputs)
    y = model.initial_state()
    row = sample(180, y, model.evaluate(180, y)[1])
    result = dict(profile=asdict(profile), cycles=[], converged=False, seconds=.1, peak_process_MiB=25.,
        stop='cancelación solicitada', last_two_cycles=[], partial=dict(samples=[row], state=y[:12]))
    save_result(folder, result, 'cancelled', inputs, {})
    return folder/'manifest.json'


class ProjectAdapterTests(unittest.TestCase):
    def setUp(self):
        self.project = SyntheticCase().project_geometry

    def test_reference_unchanged_and_equal_geometry(self):
        before = reference_inputs()
        model, profile = validated_model(inputs_for())
        ref = Model(external_band_pa=100)
        self.assertEqual(model.initial_state(), ref.initial_state())
        for angle in (0, 45, 90, 180, 350, 360, 390):
            self.assertEqual(model.geometry(angle), ref.geometry(angle))
        self.assertNotEqual(model.case.identifier, ref.case.identifier)
        self.assertNotIn('synthetic_not_experimental', model.case.manifest())
        self.assertEqual(reference_inputs(), before)
        self.assertEqual(profile.name, 'B')

    def test_missing_and_invalid_aggregate(self):
        errors = '\n'.join(execution_errors(Project(cycle='2T')))
        for word in ('cilindros', 'Diámetro', 'Carrera', 'biela', 'compresión', 'cárter', 'Admisión', 'Lumbreras', 'Conducto'):
            self.assertIn(word.lower(), errors.lower())
        for project in (replace(self.project, cylinder_count=2), replace(self.project, rod_length_mm=28),
                        replace(self.project, intake=Intake()), replace(self.project, ports=self.project.ports*2),
                        replace(self.project, ports=self.project.ports[:2]), replace(self.project, ducts=Ducts()),
                        replace(self.project, bore_mm=1e300), replace(self.project, compression_ratio=1)):
            with self.subTest(project=project), self.assertRaises(ProjectError):
                build_project_case(project)

    def test_port_mapping_by_function_not_names_or_order(self):
        ports = (replace(self.project.ports[0], name='Transfer falsa'),
                 replace(self.project.ports[1], name='Escape falso', width_mm=11), self.project.ports[2])
        one = replace(self.project, ports=ports)
        two = replace(one, ports=(ports[2], ports[0], ports[1]))
        a, mapping_a = build_project_case(one)
        b, mapping_b = build_project_case(two)
        self.assertEqual(a, b)
        self.assertEqual(configuration_key(one), configuration_key(two))
        self.assertEqual([m['link_index'] for m in mapping_b], [4,2,3])
        self.assertEqual([m['source_row'] for m in mapping_b], [2,3,1])
        self.assertEqual(a.project_geometry.ports[0].function, 'escape')

    def test_closure_uses_events_across_360(self):
        self.assertFalse(execution_errors(self.project))
        # Apertura 20 grados: el tramo 360–390 se solapa, aunque 350 y 360 estén cerrados.
        from motorsim.kinematics import piston_position
        port = replace(self.project.ports[0], top_mm=piston_position(56,100,20))
        with self.assertRaisesRegex(ProjectError, '350 a 390'):
            build_project_case(replace(self.project, ports=(port,*self.project.ports[1:])))
        port = replace(port, top_mm=56)
        with self.assertRaisesRegex(ProjectError, 'apertura efectiva'):
            build_project_case(replace(self.project, ports=(port,*self.project.ports[1:])))

    def test_duct_discontinuity_and_intake_domain(self):
        bad = replace(self.project.ducts.exhaust[1], start_diameter_mm=21)
        with self.assertRaisesRegex(ProjectError, 'continuos'):
            build_project_case(replace(self.project, ducts=replace(self.project.ducts, exhaust=(self.project.ducts.exhaust[0],bad))))
        for intake in (replace(self.project.intake, top_mm=1), replace(self.project.intake, skirt_mm=1000)):
            with self.assertRaises(ProjectError):
                build_project_case(replace(self.project,intake=intake))

    def test_each_geometry_entry_reaches_model(self):
        ref = Model(external_band_pa=100)
        def signature(model):
            return ([model.geometry(a) for a in (0, 25, 80, 100, 135, 180)], model.events)
        changes = []
        for key in ('bore_mm','stroke_mm','rod_length_mm','compression_ratio','crankcase_volume_bdc_cm3'):
            changes.append((key,replace(self.project,**{key:getattr(self.project,key)+1})))
        for i,p in enumerate(self.project.ports):
            for key in PORT_FIELDS:
                ports=list(self.project.ports)
                ports[i]=replace(p,**{key:getattr(p,key)+1})
                changes.append((f'port{i}.{key}',replace(self.project,ports=tuple(ports))))
        for key in INTAKE_FIELDS:
            changes.append((f'intake.{key}',replace(self.project,intake=replace(self.project.intake,**{key:getattr(self.project.intake,key)+1}))))
        for route in ('intake','exhaust'):
            segments=getattr(self.project.ducts,route)
            for i,segment in enumerate(segments):
                for key in DUCT_FIELDS:
                    changed=list(segments)
                    changed[i]=replace(segment,**{key:getattr(segment,key)+1})
                    if key=='start_diameter_mm' and i:
                        changed[i-1]=replace(changed[i-1],end_diameter_mm=changed[i].start_diameter_mm)
                    if key=='end_diameter_mm' and i+1<len(changed):
                        changed[i+1]=replace(changed[i+1],start_diameter_mm=changed[i].end_diameter_mm)
                    changes.append((f'{route}{i}.{key}',replace(self.project,ducts=replace(self.project.ducts,**{route:tuple(changed)}))))
        for key,project in changes:
            with self.subTest(field=key):
                case,_=build_project_case(project)
                self.assertNotEqual(signature(Model(case,external_band_pa=100)),signature(ref))

    def test_initial_inventories_scale_with_project_volumes(self):
        p=replace(self.project,compression_ratio=8.2,crankcase_volume_bdc_cm3=275,
                  ducts=replace(self.project.ducts,intake=(replace(self.project.ducts.intake[0],length_mm=120),)))
        model,_=validated_model(inputs_for(p))
        ref=Model(external_band_pa=100)
        for i in range(4):
            ratio=model.geometry(180)[0][i]/ref.geometry(180)[0][i]
            for j in range(3):
                self.assertAlmostEqual(model.initial_state()[3*i+j],ref.initial_state()[3*i+j]*ratio)
        self.assertNotEqual(model.clearance,ref.clearance)

    def test_child_revalidates_before_process_work_and_c_requires_snapshot(self):
        with tempfile.TemporaryDirectory() as d:
            inputs=inputs_for()
            inputs['project_snapshot']['cycle']='4T'
            with patch('motorsim.reference_run.run_adaptive') as run, self.assertRaises(ProjectError):
                execute(Path(d)/'blocked',threading.Event(),inputs=inputs)
            run.assert_not_called()
            self.assertFalse((Path(d)/'blocked').exists())
            with patch('motorsim.reference_run.emit'):
                self.assertEqual(main(['--profile-c-check']),2)

    def test_results_reopen_without_original_file_and_validate_contract(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            path=project_diagnostic(root)
            loaded=load_result(path)
            self.assertEqual(loaded['manifest']['version'],2)
            self.assertTrue(loaded['inputs']['origin']['dirty'])
            for mutate in (lambda x:x['inputs']['case'].update(rpm=3100),
                           lambda x:x['inputs']['initial_state'].__setitem__(0,1),
                           lambda x:x['inputs']['port_mapping'][0].update(link_index=2),
                           lambda x:x['inputs']['origin'].update(project_name='otro')):
                project_diagnostic(root)
                edit_payload(root,'case.json',mutate)
                with self.assertRaises(ResultError):load_result(path)
            # Geometría alterada con contrato coherente, pero muestras de la anterior.
            project_diagnostic(root)
            changed=inputs_for(replace(self.project,compression_ratio=8.2))
            edit_payload(root,'case.json',lambda d:d.update(inputs=changed))
            with self.assertRaisesRegex(ResultError,'Volúmenes'):load_result(path)
            project_diagnostic(root)
            edit_payload(root,'samples.json',lambda d:d['partial'][0]['flows_kg_s_W_kg_s'][1].__setitem__(0,42))
            with self.assertRaisesRegex(ResultError,'Flujos'):load_result(path)


from process_double import DiagnosticProcess


class ProjectSimulationWindowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app=QApplication.instance() or QApplication([])

    def setUp(self):
        self.window=MainWindow()
        self.view=self.window.simulation_view
        self.window._activate(replace(SyntheticCase().project_geometry,name='PRUEBA'),None)
        self.view.origin_combo.setCurrentIndex(1)

    def tearDown(self):
        if self.view.active:
            self.view.cancel()
            deadline=time.monotonic()+5
            while self.view.active and time.monotonic()<deadline:QTest.qWait(20)
            self.assertFalse(self.view.active)
        self.window.dirty=False
        self.window.close()
        self.window.deleteLater()
        QTest.qWait(10)

    def test_unsaved_snapshot_independent_and_invalid_drafts_aggregated(self):
        self.window.numeric_edits['compression_ratio'].setText('8,2')
        captured=self.view._capture()
        self.assertEqual(captured['project_snapshot']['compression_ratio'],8.2)
        self.assertTrue(captured['origin']['dirty'])
        self.window.numeric_edits['compression_ratio'].setText('oops')
        self.window.numeric_edits['bore_mm'].setText('NaN')
        self.window.ports_view.drafts[0]['height_mm']='mal'
        self.window.ducts_view.drafts['intake'][0]['length_mm']='mal'
        self.window.ports_view.intake.edits['skirt_mm'].setText('mal')
        self.view.start()
        self.assertFalse(self.view.active)
        for label in ('compresión','Diámetro','Lumbrera 1','Conducto admisión','falda'):
            self.assertIn(label,self.view.error_label.text())
        self.assertEqual(captured['project_snapshot']['compression_ratio'],8.2)

    def test_result_provenance_stale_and_reopen_never_modify_editor(self):
        with tempfile.TemporaryDirectory() as d:
            inputs=self.view._capture()
            path=project_diagnostic(Path(d),inputs)
            self.view.open_result(path=path)
            before=self.window.project()
            self.assertFalse(self.view.stale_label.text())
            self.window.numeric_edits['compression_ratio'].setText('8.2')
            self.assertIn('configuración anterior',self.view.stale_label.text())
            self.view.origin_combo.setCurrentIndex(0)
            self.assertEqual(self.view.inputs,inputs)
            self.view.open_result(path=path)
            self.assertEqual(self.window.project().compression_ratio,8.2)
            self.assertTrue(self.window.dirty)
            self.window._activate(replace(before,name='Otro motor'),None)
            self.assertIn('configuración anterior',self.view.stale_label.text())
            self.assertIn('PRUEBA',self.view.identity_label.text())

    @patch('motorsim.simulation_view.QProcess', DiagnosticProcess)
    def test_double_child_uses_snapshot_then_cooperative_cancel(self):
        with tempfile.TemporaryDirectory() as d:
            self.window.numeric_edits['compression_ratio'].setText('8.2')
            self.view.start(output=Path(d)/'run')
            self.assertTrue(self.view.active)
            request=self.view._request_path
            self.window.numeric_edits['compression_ratio'].setText('9')
            self.assertIn('configuración anterior',self.view.stale_label.text())
            deadline=time.monotonic()+6
            while 'RHS:' not in self.view.progress_label.text() and self.view.active and time.monotonic()<deadline:QTest.qWait(20)
            self.view.cancel()
            while self.view.active and time.monotonic()<deadline:QTest.qWait(20)
            self.assertFalse(self.view.active)
            self.assertFalse(self.view.forced)
            result=load_result(Path(d)/'run/manifest.json')
            self.assertEqual(result['status'],'cancelled')
            self.assertEqual(result['inputs']['project_snapshot']['compression_ratio'],8.2)
            self.assertFalse(request.exists())
            self.assertEqual(self.window.project().compression_ratio,9)
            self.assertTrue(self.window.dirty)
