import json
import math
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from motorsim.project import (DUCT_FIELDS, DuctSegment, Ducts, Intake, Port, Project,
                              ProjectError, parse_number)
from motorsim.ducts import route_geometry
from motorsim.storage import load_project, save_project


class DuctTests(unittest.TestCase):
    def setUp(self):
        self.tube=DuctSegment('Tubo sintético',100,20,20)
        self.cone=DuctSegment('Expansión sintética',100,20,40)

    def test_independent_case_and_profile(self):
        r=route_geometry((self.tube,self.cone))
        self.assertAlmostEqual(float(r.segments[0].volume),10*math.pi,places=10)
        self.assertAlmostEqual(float(r.segments[1].volume),70/3*math.pi,places=10)
        self.assertAlmostEqual(float(r.volume),100/3*math.pi,places=10)
        self.assertAlmostEqual(float(r.segments[0].start_area),100*math.pi,places=10)
        self.assertAlmostEqual(float(r.segments[1].end_area),400*math.pi,places=10)
        self.assertEqual(r.length,200);self.assertEqual(r.joints,(True,))
        self.assertEqual(r.profile,((0,100,10,10),(100,200,10,20)))
        self.assertEqual(r.segments[0].kind,'Tubo cilíndrico')
        self.assertIn('expansión',r.segments[1].kind)

    def test_contraction_discontinuity_and_order(self):
        contraction=replace(self.cone,start_diameter_mm=40,end_diameter_mm=20)
        r=route_geometry((self.tube,contraction))
        self.assertEqual(r.joints,(False,))
        self.assertAlmostEqual(float(r.volume),100/3*math.pi,places=10)
        self.assertIn('contracción',r.segments[1].kind)
        self.assertEqual(r.profile[1],(100,200,20,10))
        r=route_geometry((contraction,self.tube))
        self.assertEqual(r.joints,(True,))
        self.assertEqual(r.profile[0],(0,100,20,10))
        self.assertEqual(r.length,200)

    def test_missing_results_have_independent_dependencies(self):
        r=route_geometry((self.tube,replace(self.cone,start_diameter_mm=None)))
        self.assertEqual(r.length,200);self.assertIsNone(r.volume)
        self.assertEqual(r.joints,(None,));self.assertFalse(r.profile)
        self.assertIsNotNone(r.segments[0].volume)
        self.assertIsNotNone(r.segments[1].end_area)
        self.assertIsNone(r.segments[1].start_area)
        self.assertIn('Tramo 2',r.errors['volume'])
        self.assertIn('Falta',r.errors['profile'])
        r=route_geometry((replace(self.tube,length_mm=None),self.cone))
        self.assertIsNone(r.length);self.assertIsNone(r.volume)
        self.assertIsNotNone(r.segments[0].start_area);self.assertEqual(r.joints,(True,))
        empty=route_geometry(())
        self.assertIsNone(empty.length);self.assertIsNone(empty.volume)
        self.assertEqual(empty.errors['profile'],'Sin tramos')

    def test_invalid_is_not_absent_and_parser(self):
        for key in DUCT_FIELDS:
            self.assertIsNone(parse_number(' ',key))
            self.assertEqual(parse_number('20,125',key),20.125)
            self.assertEqual(parse_number('20.125',key),20.125)
            for bad in ('0','-1','nan','inf','1.234,5','texto'):
                with self.assertRaises(ProjectError):parse_number(bad,key)
            for value in (0,-1,math.inf,math.nan,True,'20'):
                r=route_geometry((replace(self.tube,**{key:value}),))
                self.assertFalse(r.profile);self.assertIsNone(r.volume)
                self.assertNotIn('Falta',r.errors['volume'])
        r=route_geometry((self.tube,),[{'length_mm':'Texto inválido conservado'}])
        self.assertIn('Texto inválido',r.errors['length']);self.assertFalse(r.profile)

    def test_extreme_finite_dimensions(self):
        for number in (1e308,1e-300):
            r=route_geometry((DuctSegment('',number,number,number),))
            self.assertTrue(r.volume.is_finite());self.assertGreater(r.volume,0)
            self.assertGreater(r.segments[0].start_area,0)
        r=route_geometry((replace(self.tube,length_mm=1e308),self.cone))
        self.assertIsNotNone(r.length);self.assertIsNotNone(r.volume)
        self.assertFalse(r.profile);self.assertIn('rango',r.errors['profile'])

    def test_roundtrip_both_routes_incomplete_order_without_derived(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'motor.json'
            for cycle in ('2T','4T'):
                ducts=Ducts((self.tube,self.cone,DuctSegment()),(replace(self.tube,name='Escape'),))
                p=Project(name='Sintético',cycle=cycle,ducts=ducts,intake=Intake('piston_port',64,10,20,42),
                          ports=(Port('Escape','escape',32,10,20),),crankcase_volume_bdc_cm3=250)
                save_project(path,p);self.assertEqual(load_project(path),p)
                data=json.loads(path.read_text(encoding='utf-8'))
                self.assertEqual(data['format_version'],6)
                self.assertEqual(set(data['ducts']),{'intake','exhaust','reference'})
                self.assertEqual(set(data['ducts']['intake'][0]),{'name',*DUCT_FIELDS})
                self.assertIsNone(data['ducts']['intake'][2]['length_mm'])
                updated=replace(p,ducts=replace(ducts,intake=(self.cone,self.tube)))
                save_project(path,updated);self.assertEqual(load_project(path),updated)

    def test_versions_one_to_four_preserve_values_and_do_not_write(self):
        p=Project('Anterior','4T',manufacturer='Marca',notes='Notas',bore_mm=54,stroke_mm=56,
                  ports=(Port('Escape','escape',32,10,20),),crankcase_volume_bdc_cm3=250,
                  intake=Intake('piston_port',64,10,20,42))
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'anterior.json'
            for version in (1,2,3,4):
                data=p.to_dict();data.pop('four_stroke');data.pop('ducts');data['format_version']=version
                if version<4:data.pop('intake')
                if version<3:
                    for key in ('ports','crankcase_volume_bdc_cm3','two_stroke_reference'):data.pop(key)
                if version==1:data={key:data[key] for key in ('format_version','name','cycle')}
                raw=json.dumps(data).encode();path.write_bytes(raw)
                loaded=load_project(path);self.assertEqual(path.read_bytes(),raw)
                self.assertEqual(loaded.ducts,Ducts())
                for key,value in data.items():
                    if key not in ('format_version','ports','intake','two_stroke_reference'):
                        self.assertEqual(getattr(loaded,key),value)
                if version>=3:self.assertEqual(loaded.ports,p.ports)
                if version==4:self.assertEqual(loaded.intake,p.intake)
                save_project(path,loaded)
                self.assertEqual(load_project(path),loaded)
                self.assertEqual(json.loads(path.read_text(encoding='utf-8'))['format_version'],6)

    def test_malformed_v5_rejected(self):
        data=Project(ducts=Ducts((self.tube,),())).to_dict();valid=data['ducts']
        bad=[None,[],{}, {**valid,'reference':'otra'}, {**valid,'intake':None},
             {**valid,'exhaust':[{}]}, {**valid,'intake':[{'name':'incompleto'}]}]
        for key,value in (('name',None),('length_mm',0),('start_diameter_mm',True),('end_diameter_mm','20')):
            bad.append({**valid,'intake':[{**valid['intake'][0],key:value}]})
        for ducts in bad:
            with self.subTest(ducts=ducts),self.assertRaises(ProjectError):
                Project.from_dict({**data,'ducts':ducts})
