"""Source adapter checks; no long integration or scientific campaign."""
import unittest
from copy import deepcopy
from math import fsum
from motorsim.hybrid_exhaust import LegacySources, HybridSystem
from motorsim.simulation import Model, burn_fraction
from motorsim.gas1d.eos import IdealGas
from dev_orchestrator.p4_hybrid import periodic,checks


class HybridSourcesTests(unittest.TestCase):
    def setUp(self):
        self.model=LegacySources();self.eos=IdealGas()

    def test_unreplaced_flows_and_geometry_are_legacy(self):
        original=Model(external_band_pa=100);state=original.initial_state()
        for angle in (180,250,350,370,450,540):
            a=original.evaluate(angle,state);b=self.model.evaluate(angle,state)
            self.assertEqual(a[1][2][:4],b[1][2][:4])
            self.assertEqual(original.geometry(angle)[:2],self.model.geometry(angle)[:2])
            self.assertEqual(b[1][2][4:],[(0.,0.,0.),(0.,0.,0.)])

    def test_source_ledger_excludes_internal_transfers_and_dummy_exhaust(self):
        state=self.model.initial_state()[:9]
        for angle in (180,230,310,450):
            system=HybridSystem(self.model,angle,state)
            dy,external,terms=system.source(state,0,self.eos)
            self.assertEqual(len(dy),9)
            for k in range(3):self.assertAlmostEqual(fsum(dy[k::3]),external[k],places=10)
            before=(dy,external,terms)
            system.dummy[1]*=1.1
            self.assertEqual(before,system.source(state,0,self.eos))

    def test_analytic_species_matches_legacy_at_all_heat_stages(self):
        state=self.model.initial_state()[:9];state[8]=.4*state[6]
        system=HybridSystem(self.model,350,state,350)
        for angle in (350,351,370,389.9,390,390.1):
            t=(angle-350)/self.model.rate
            physical=system.physical(state,t)
            self.assertEqual(physical[8],state[8]*(1-burn_fraction(angle,350,40)))
            dy,external,terms=system.source(state,t,self.eos)
            self.assertEqual(dy[8],0.)
            self.assertEqual(system.area(t),0.)
            self.assertEqual(terms['heat'],self.model.case.fresh_energy_j_kg*terms['burn_rate'])
            for k in range(3):self.assertAlmostEqual(fsum(dy[k::3]),external[k],places=9)

    def test_species_transform_is_not_clipping(self):
        state=self.model.initial_state()[:9];state[8]=state[6]*.5
        system=HybridSystem(self.model,350,state,350)
        corrupted=state.copy();corrupted[8]*=.9
        with self.assertRaisesRegex(ValueError,'Transformed'):system.physical(corrupted,0)
        with self.assertRaisesRegex(ValueError,'ports closed'):system.evaluate(state,110/self.model.rate)

    def test_invalid_physical_state_is_rejected(self):
        state=self.model.initial_state()[:9];system=HybridSystem(self.model,180,state)
        state[6]=-1
        with self.assertRaises(ValueError):system.validate(state,0,self.eos)


class HybridGateTests(unittest.TestCase):
    def cycle(self):
        return dict(begin=180.,history=[dict(angle=x,p_cyl=1e5,sensors_p_u_M_Y=[(1e5,0,0,0)]*3) for x in (180.1,360,540)],
            state=[1,10,.2]*3,cells=[(1,0,10,.2)]*2,work_indicated_J=10,port_integral=[.1,1,.01],initial_cylinder_mass=1)

    def test_periodicity_checks_pressure_inventory_and_exchange(self):
        a=self.cycle();self.assertTrue(periodic(a,deepcopy(a))['passed'])
        for mutate in (lambda b:b['history'][1].update(p_cyl=110000),lambda b:b['state'].__setitem__(2,.21),
                       lambda b:b['port_integral'].__setitem__(0,.2),lambda b:b['cells'].__setitem__(0,(1,0,11,.2)),
                       lambda b:b['history'][1].update(sensors_p_u_M_Y=[(120000,0,0,0)]*3)):
            b=deepcopy(a);mutate(b);self.assertFalse(periodic(a,b)['passed'])

    def test_periodicity_rejects_missing_phase_support(self):
        a=self.cycle();b=deepcopy(a);b['history'][-1]['angle']=539
        with self.assertRaises(ValueError):periodic(a,b)

    def test_CFL_uses_stage_bound_and_species_is_strict(self):
        r=dict(max_global_residual=0,max_stage_residual=0,max_CFL=.4000000000000001,
            extrema=dict(rho=1,p=1,T=1,Y_min=0,Y_max=1),stages=[dict(dt=.1,limits=[.1,.2],traces=[])])
        row=dict(complete=True,global_balance=[0]*3,segments=[dict(result=r,physical_balance=[0]*3)])
        self.assertTrue(checks(row)['CFL'])
        r['stages'][0]['dt']=.11;self.assertFalse(checks(row)['CFL'])
        r['extrema']['Y_min']=-1e-16;self.assertFalse(checks(row)['positive'])


if __name__=='__main__':unittest.main()
