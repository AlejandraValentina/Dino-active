import json
import math
import tempfile
import unittest
from dataclasses import asdict, replace
from pathlib import Path

from motorsim.project import Port, Project, ProjectError, parse_number
from motorsim.ports import port_results
from motorsim.storage import save_project, load_project


class PortTests(unittest.TestCase):
    def setUp(self):
        self.port=Port('Sintético','escape',32,10,20)

    def test_independent_synthetic_case(self):
        # 28 + 100 - sqrt(10000-784) = 32; esperado no llama a función probada.
        result=port_results(self.port,56,100)
        self.assertAlmostEqual(result.opening,90,places=9)
        self.assertAlmostEqual(result.closing,270,places=9)
        self.assertAlmostEqual(result.duration,180,places=9)
        self.assertEqual(result.maximum,200)
        self.assertAlmostEqual(result.areas[90],0,places=9)
        self.assertEqual(result.areas[180],200)
        self.assertEqual(result.areas[0],0)
        self.assertTrue(all(0<=area<=200 for area in result.areas))

    def test_partial_and_never_open(self):
        result=port_results(replace(self.port,top_mm=52),56,100)
        self.assertEqual(result.maximum,80)
        self.assertEqual(result.areas[180],80)
        for top in (56,60):
            result=port_results(replace(self.port,top_mm=top),56,100)
            self.assertTrue(result.never_opens)
            self.assertIsNone(result.opening)
            self.assertIsNone(result.closing)
            self.assertEqual(result.duration,0)
            self.assertEqual(result.maximum,0)
            self.assertEqual(result.areas,(0,)*361)

    def test_events_not_rounded_to_degree(self):
        a=port_results(replace(self.port,top_mm=33),56,100)
        self.assertGreater(abs(a.opening-round(a.opening)),.01)
        self.assertAlmostEqual(a.closing,360-a.opening)
        self.assertNotEqual(a.opening,port_results(self.port,58,100).opening)
        self.assertNotEqual(a.opening,port_results(replace(self.port,top_mm=33),56,110).opening)

    def test_missing_invalid_and_incompatible(self):
        for value in (None,0,-1,math.nan,math.inf,'32',True):
            result=port_results(replace(self.port,top_mm=value),56,100)
            self.assertTrue(result.event_error)
            self.assertFalse(result.areas)
        for key in ('height_mm','width_mm'):
            result=port_results(replace(self.port,**{key:None}),56,100)
            self.assertAlmostEqual(result.opening,90)
            self.assertIsNone(result.maximum)
            self.assertTrue(result.area_error)
        for stroke,rod in ((None,100),(56,None),(56,28),(56,20)):
            result=port_results(self.port,stroke,rod)
            self.assertTrue(result.event_error)
            self.assertFalse(result.areas)
        result=port_results(self.port,56,100,{'top_mm':'Entrada inválida conservada'})
        self.assertEqual(result.event_error,'Entrada inválida conservada')

    def test_new_numeric_validation(self):
        for key in ('top_mm','height_mm','width_mm','crankcase_volume_bdc_cm3'):
            self.assertIsNone(parse_number('',key))
            self.assertEqual(parse_number('12,345',key),12.345)
            self.assertEqual(parse_number('12.345',key),12.345)
            for bad in ('0','-2','nan','inf','1,234.5','texto'):
                with self.assertRaises(ProjectError):parse_number(bad,key)

    def test_area_numeric_range_does_not_turn_into_valid_zero(self):
        for height,width in ((1e-200,1e-200),(10,1e308)):
            result=port_results(replace(self.port,height_mm=height,width_mm=width),56,100)
            self.assertAlmostEqual(result.opening,90)
            self.assertIsNone(result.maximum)
            self.assertFalse(result.areas)
            self.assertIn('rango',result.area_error)

    def test_multiple_incomplete_roundtrip_and_delete(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'motor.json'
            p=Project(ports=(self.port,Port('Transferencia','transfer'),Port()),crankcase_volume_bdc_cm3=250.125)
            for cycle in ('2T','4T'):
                p=replace(p,cycle=cycle);save_project(path,p)
                self.assertEqual(load_project(path),p)
                self.assertEqual(json.loads(path.read_text(encoding='utf-8'))['format_version'],6)
            p=replace(p,ports=p.ports[1:]);save_project(path,p)
            self.assertEqual(load_project(path),p)

    def test_legacy_files_unchanged_until_save(self):
        v2={'format_version':2,'name':'Anterior','cycle':'4T','manufacturer':'Marca',
            'model':'Modelo','notes':'Notas','cylinder_count':1,'bore_mm':54,'stroke_mm':56,
            'rod_length_mm':100,'compression_ratio':10}
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'old.json'
            for data in ({'format_version':1,'name':'v1','cycle':'2T'},v2):
                raw=json.dumps(data).encode();path.write_bytes(raw)
                project=load_project(path)
                self.assertEqual(project.ports,())
                self.assertIsNone(project.crankcase_volume_bdc_cm3)
                self.assertEqual(path.read_bytes(),raw)
                for key,value in data.items():
                    if key!='format_version':self.assertEqual(getattr(project,key),value)
                save_project(path,project)
                self.assertEqual(json.loads(path.read_text(encoding='utf-8'))['format_version'],6)

    def test_malformed_v3_rejected(self):
        valid=Project(ports=(self.port,)).to_dict()
        for data in ({**valid,'ports':None},{**valid,'ports':[{}]},
                     {**valid,'two_stroke_reference':'otra'},
                     {**valid,'crankcase_volume_bdc_cm3':0}):
            with self.assertRaises(ProjectError):Project.from_dict(data)
        for key,value in (('name',None),('function','admission'),('width_mm',0),('height_mm',True)):
            port={**asdict(self.port),key:value}
            with self.assertRaises(ProjectError):Project.from_dict({**valid,'ports':[port]})
