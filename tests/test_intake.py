import json
import math
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from motorsim.project import Intake, Project, Port, ProjectError, INTAKE_FIELDS, parse_number
from motorsim.intake import intake_results
from motorsim.storage import load_project, save_project


class IntakeTests(unittest.TestCase):
    def setUp(self):
        self.intake = Intake('piston_port', 64, 10, 20, 42)

    def test_independent_case_crosses_tdc(self):
        r = intake_results(self.intake, 56, 100)
        self.assertAlmostEqual(r.opening, 270, places=9)
        self.assertAlmostEqual(r.closing, 90, places=9)
        self.assertAlmostEqual(r.duration, 180, places=9)
        self.assertEqual(r.maximum, 200)
        for angle in (0, 360): self.assertEqual(r.areas[angle], 200)
        for angle in (90, 180, 270): self.assertAlmostEqual(r.areas[angle], 0, places=9)
        self.assertTrue(all(v == 0 for v in r.areas[91:270]))
        self.assertGreater(r.areas[30], 0); self.assertGreater(r.areas[330], 0)

    def test_partial_and_never_opens(self):
        r = intake_results(replace(self.intake, skirt_mm=70), 56, 100)
        self.assertEqual(r.maximum, 80); self.assertEqual(r.areas[0], 80)
        for skirt in (74, 80):
            r = intake_results(replace(self.intake, skirt_mm=skirt), 56, 100)
            self.assertTrue(r.never_opens)
            self.assertIsNone(r.opening); self.assertIsNone(r.closing)
            self.assertEqual(r.duration, 0); self.assertEqual(r.maximum, 0)
            self.assertEqual(r.areas, (0,)*361)

    def test_domain_and_saveable_incompatibility(self):
        for intake in (replace(self.intake, top_mm=55), replace(self.intake, skirt_mm=18),
                       replace(self.intake, skirt_mm=17)):
            Project(intake=intake).validate()
            r = intake_results(intake, 56, 100)
            self.assertIn('Fuera del modelo', r.event_error)
            self.assertIsNone(r.opening); self.assertIsNone(r.duration)
            self.assertIsNone(r.maximum); self.assertFalse(r.areas)
        self.assertFalse(intake_results(replace(self.intake, top_mm=56), 56, 100).event_error)

    def test_dependencies_and_invalid_inputs(self):
        for width in (None, -1, math.inf, True, '20'):
            r = intake_results(replace(self.intake, width_mm=width), 56, 100)
            self.assertAlmostEqual(r.closing, 90); self.assertTrue(r.area_error)
            self.assertFalse(r.areas); self.assertIsNone(r.maximum)
        for key in ('top_mm', 'height_mm', 'skirt_mm'):
            for value in (None, 0, -1, math.nan, math.inf, True, 'texto'):
                r = intake_results(replace(self.intake, **{key:value}), 56, 100)
                self.assertTrue(r.event_error); self.assertFalse(r.areas)
        for stroke, rod in ((None,100), (56,None), (56,28), (56,20), (0,100)):
            r = intake_results(self.intake, stroke, rod)
            self.assertTrue(r.event_error); self.assertFalse(r.areas)
        r = intake_results(self.intake, 56, 100, {'skirt_mm':'Texto inválido conservado'})
        self.assertEqual(r.event_error, 'Texto inválido conservado')
        self.assertIn('sin definir', intake_results(Intake(),56,100).event_error)

    def test_parse_optional_decimal_and_invalid(self):
        for key in INTAKE_FIELDS:
            self.assertIsNone(parse_number(' ', key))
            self.assertEqual(parse_number('42,125',key), 42.125)
            self.assertEqual(parse_number('42.125',key), 42.125)
            for text in ('0','-1','nan','inf','1,234.5','texto'):
                with self.assertRaises(ProjectError): parse_number(text,key)

    def test_numeric_range_and_cancellation(self):
        r = intake_results(replace(self.intake, width_mm=1e308),56,100)
        self.assertAlmostEqual(r.closing,90); self.assertIn('rango', r.area_error)
        self.assertFalse(r.areas)
        tiny = Intake('piston_port',64,1e-200,1e-200,64)
        r = intake_results(tiny,56,100)
        self.assertFalse(r.event_error); self.assertIn('rango',r.area_error)
        large = Intake('piston_port',1e308,10,20,1e308)
        r = intake_results(large,56,100)
        self.assertFalse(r.event_error); self.assertEqual(r.maximum,200)

    def test_events_not_samples_and_updates(self):
        original = intake_results(self.intake,56,100)
        for intake,stroke,rod in ((self.intake,58,100),(self.intake,56,110),
                                 (replace(self.intake,top_mm=65),56,100),
                                 (replace(self.intake,height_mm=11),56,100),
                                 (replace(self.intake,skirt_mm=43),56,100)):
            r = intake_results(intake,stroke,rod)
            self.assertNotAlmostEqual(original.closing,r.closing)
            self.assertNotEqual(original.areas,r.areas)
            self.assertGreater(abs(r.closing-round(r.closing)), .001)

    def test_roundtrip_complete_incomplete_undefined_and_legacy(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'prueba.json'
            for intake in (self.intake,Intake(),replace(self.intake,mode=None),
                           replace(self.intake,width_mm=None),replace(self.intake,skirt_mm=17)):
                for cycle in ('2T','4T'):
                    p=Project(cycle=cycle,intake=intake,ports=(Port('Escape','escape',32,10,20),),
                              crankcase_volume_bdc_cm3=250.125)
                    save_project(path,p); self.assertEqual(load_project(path),p)
                    data=json.loads(path.read_text(encoding='utf-8'))
                    self.assertEqual(data['format_version'],6)
                    self.assertEqual(set(data['intake']),set(Intake.__dataclass_fields__))
            for version in (1,2,3):
                data=p.to_dict();data.pop('four_stroke');data.pop('ducts');data.pop('intake');data['format_version']=version
                if version<3:
                    for key in ('ports','crankcase_volume_bdc_cm3','two_stroke_reference'):data.pop(key)
                if version==1:data={k:data[k] for k in ('format_version','name','cycle')}
                raw=json.dumps(data).encode();path.write_bytes(raw)
                old=load_project(path);self.assertEqual(old.intake,Intake())
                self.assertEqual(path.read_bytes(),raw)
                for key,value in data.items():
                    if key not in ('format_version','ports','two_stroke_reference'):
                        self.assertEqual(getattr(old,key),value)
                if version==3:self.assertEqual(old.ports,p.ports)
                save_project(path,old)
                self.assertEqual(json.loads(path.read_text(encoding='utf-8'))['format_version'],6)

    def test_malformed_intake_rejected(self):
        data=Project(intake=self.intake).to_dict();valid=data['intake']
        bad=[None,[],{},*({k:v for k,v in valid.items() if k!=key} for key in valid)]
        bad += [{**valid,key:value} for key,value in (('mode','reed'),('mode',True),
                 ('reference','otra'),('skirt_mm',0),('height_mm',float('nan')),('width_mm','20'))]
        for intake in bad:
            with self.subTest(intake=intake), self.assertRaises(ProjectError):
                Project.from_dict({**data,'intake':intake})
