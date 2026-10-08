"""Controles independientes previos al caso completo, sin campañas implícitas."""
from dataclasses import replace
import json
import math
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from motorsim.project import Project, FourStroke, Valve, ProjectError, parse_number
from motorsim.valves import lift, area_at_lift, overlap, errors, closed_during_heat
from motorsim.four_stroke import FourStrokeCase, FourStrokeModel, geometry, execution_errors
from motorsim.simulation import (FOUR_LAYOUT, audit, sample, rk4, StopCalculation,
                                burn_fraction, independent_increment)
from motorsim.adaptive import PROFILES, error_norm, targets, Stepper, run_adaptive
from motorsim.storage import save_project, load_project


class FourStrokeTests(unittest.TestCase):
    def test_lift_area_and_periodic_overlap_independent(self):
        v = Valve(24,20,5,5,0,220)
        self.assertEqual([lift(v,a) for a in (0,110,220,720,830,940)], [0,5,0,0,5,0])
        self.assertAlmostEqual(area_at_lift(v,1),24*math.pi)
        self.assertAlmostEqual(area_at_lift(v,5),93.75*math.pi)
        intervals = overlap(replace(v,opening_deg=700,duration_deg=240),
                            replace(v,opening_deg=500,duration_deg=240))
        self.assertEqual(intervals,[(0,20),(700,720)])
        self.assertEqual(sum(b-a for a,b in intervals),40)
        fractional = replace(v,opening_deg=700.1,duration_deg=240.2)
        for turn in range(-1,8):
            self.assertEqual(lift(fractional,700.1+720*turn),0)
            self.assertEqual(lift(fractional,700.1+240.2+720*turn),0)

    def test_domains_missing_invalid_and_incompatible(self):
        for key in Valve.__dataclass_fields__:
            self.assertIsNone(parse_number('',key))
            for text in ('nan','inf','texto','1,2.3','-1'):
                with self.assertRaises(ProjectError): parse_number(text,key)
        self.assertEqual(parse_number('0','opening_deg'),0)
        self.assertEqual(parse_number('0','stem_mm'),0)
        self.assertEqual(parse_number('1,25','lift_mm'),1.25)
        self.assertEqual(parse_number('1.25','lift_mm'),1.25)
        for key in ('opening_deg','duration_deg'):
            with self.assertRaises(ProjectError): parse_number('720',key)
        bad = Valve(20,24,5,5,0,220)
        bad.validate(); self.assertTrue(errors(bad))
        self.assertTrue(errors(Valve()))
        self.assertFalse(closed_during_heat(replace(bad,opening_deg=350)))

    def test_v6_roundtrip_incomplete_and_legacy_no_rewrite(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'motor.json'
            for project in (Project(cycle='4T'),geometry()):
                save_project(path,project); self.assertEqual(load_project(path),project)
                self.assertEqual(json.loads(path.read_text(encoding='utf-8'))['format_version'],6)
            for version in range(1,6):
                data = geometry().to_dict(); data['format_version'] = version; data.pop('four_stroke')
                if version < 5: data.pop('ducts')
                if version < 4: data.pop('intake')
                if version < 3: data.pop('ports'); data.pop('crankcase_volume_bdc_cm3')
                if version == 1: data = {k:data[k] for k in ('format_version','name','cycle')}
                raw = json.dumps(data).encode(); path.write_bytes(raw)
                loaded = load_project(path)
                self.assertEqual(path.read_bytes(),raw)
                self.assertEqual(loaded.four_stroke,FourStroke())
                self.assertEqual(loaded.cycle,'4T')

    def test_three_real_volumes_initial_inventory_and_periods(self):
        model = FourStrokeModel(); y = model.initial_state()
        self.assertEqual(len(y),34); self.assertEqual(model.layout.physical,9)
        volumes = model.geometry(0)[0]
        expected = (10*math.pi*1e-6, (math.pi*.054**2/4*.056)/7, 100/3*math.pi*1e-6)
        for i,(actual,v) in enumerate(zip(volumes,expected)):
            self.assertAlmostEqual(actual,v,14)
            t = 300 if i == 0 else 500
            self.assertAlmostEqual(y[3*i],100000*v/(287*t),14)
            self.assertAlmostEqual(y[3*i+1],100000*v/.35,10)
        for angle in (0,90,180,220,350,500,710):
            self.assertEqual(model.geometry(angle)[0],model.geometry(angle+360)[0])
            self.assertEqual(model.geometry(angle)[2],model.geometry(angle+720)[2])
        self.assertNotEqual(model.geometry(110)[2],model.geometry(470)[2])
        row = sample(720,y,model.evaluate(720,y)[1],initial_angle=0,layout=FOUR_LAYOUT)
        self.assertEqual(row['time_s'],.04); self.assertNotIn('W_K_J',row)
        self.assertEqual(len(targets(0,720,[] ,720)),1440)

    def test_norm_covers_nine_real_components_not_accumulators(self):
        start = [1e-4,10.,5e-5]*3+[0.]*25
        for i in range(9):
            fine = start.copy(); fine[i] *= 1.01
            err, where = error_norm(start,start,fine,PROFILES[0],FOUR_LAYOUT)
            self.assertGreater(err,1); self.assertTrue(where.startswith(('I','C','E')[i//3]))
        fine = start.copy(); fine[9:] = [1e20]*25
        self.assertEqual(error_norm(start,start,fine,PROFILES[0],FOUR_LAYOUT)[0],0)

    def test_closed_actual_model_adiabatic_heat_and_full_cycle_work(self):
        model = FourStrokeModel(); original = model.geometry
        # Isolate the actual 4T balances: prescribed valve and exterior areas zero.
        def closed(a):
            v,dv,_ = original(a); return v,dv,(0.,)*4
        model.geometry = closed
        y = model.initial_state(); initial = y.copy(); y[5] = y[3]*.4
        v0 = original(0)[0][1]; p0 = 100000
        # Two mechanical turns, no heat: p V^gamma invariant and net work zero.
        for i in range(1440):
            a = i*.5
            y = rk4(0,y,.5/model.rate,lambda t,s:model.evaluate(a+t*model.rate,s)[0])
            v = original(a+.5)[0][1]; pressure = model.evaluate(a+.5,y)[1][0][1][0]
            self.assertAlmostEqual(pressure/(p0*(v0/v)**1.35),1,places=7)
        self.assertAlmostEqual(y[model.layout.work+1],0,places=6)
        self.assertAlmostEqual(y[3],initial[3],places=15)
        # Heat in closed moving cylinder: energy + work = Q, all fresh converted.
        y = model.initial_state(); y[5] = y[3]*.4; fs = y[5]; u0 = y[4]
        heat = (350,fs)
        # Place inventories at 350 with the initial energy explicitly retained.
        for i in range(80):
            a = 350+i*.5
            y = rk4(0,y,.5/model.rate,lambda t,s:model.evaluate(a+t*model.rate,s,heat)[0],
                    lambda t,s:model.analytic(a+t*model.rate,s,heat))
        self.assertAlmostEqual(y[4]-u0+y[22],800000*fs,places=8)
        self.assertEqual(y[5],0)

    def test_shared_runner_one_heat_capture_in_720(self):
        model = FourStrokeModel(); heats = []; endpoints = []
        # Sequencing double, no integrated cycle hidden in tests.
        def advance(stepper,angle,state,event,heat,check):
            check(); heats.append(heat); endpoints.append(event)
            return [(event,state.copy(),model.evaluate(0,state)[1])]
        def monitor(cycle,angle,rhs,completed=False):
            if completed: raise StopCalculation('test terminado')
        with patch.object(Stepper,'advance',advance):
            result = run_adaptive(PROFILES[0],monitor,model)
        self.assertEqual(len(result['cycles']),1)
        self.assertEqual(len(result['last_two_cycles'][0]),1441)
        self.assertEqual({h[0] for h in heats if h is not None},{350})
        self.assertEqual(endpoints[-1],720)
        self.assertNotIn('W_K_J',result['cycles'][0])

    def test_preflight_open_heat_and_absence_no_fallback(self):
        self.assertFalse(execution_errors(geometry()))
        self.assertTrue(execution_errors(Project(cycle='4T')))
        p = geometry(); config = replace(p.four_stroke,intake=replace(p.four_stroke.intake,opening_deg=340))
        self.assertTrue(any('aporte' in s for s in execution_errors(replace(p,four_stroke=config))))


if __name__ == '__main__': unittest.main()
