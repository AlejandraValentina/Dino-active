import math
import unittest
from unittest.mock import patch
from motorsim.gas1d.eos import IdealGas, InvalidState
from motorsim.gas1d.boundary import Boundary
from motorsim.gas1d.mesh import uniform_mesh
from motorsim.gas1d.riemann import hllc_flux
from motorsim.gas1d.solver import solve, event_step


class P2FixTests(unittest.TestCase):
    def test_hllc_near_rest_mass_sign_and_species(self):
        import json
        from pathlib import Path
        example=json.loads((Path(__file__).parent/'gas1d_contact_roundoff.json').read_text())
        eos=IdealGas(1.,1.4);left=tuple(example['left']);right=tuple(example['right'])
        flux,speeds,reason=hllc_flux(left,right,eos)
        self.assertIsNone(reason);self.assertEqual(speeds,tuple(example['speeds']))
        self.assertGreater(speeds[1],0.);self.assertGreater(flux[0],0.)
        self.assertEqual(flux[0],example['stable_mass']);self.assertEqual(flux[3],flux[0]*left[3])
        self.assertGreater(example['old_fresh']+.00023780923036054375*flux[3],0.)
        # General star-region Rankine-Hugoniot identity, without threshold tuning.
        l=(1.,.2,1.,.2);r=(.125,-.1,.1,.8)
        actual,(sl,sm,sr),reason=hllc_flux(l,r,eos)
        w,s=(l,sl) if sm>=0 else (r,sr)
        rho_star=w[0]*(s-w[1])/(s-sm)
        expected=w[0]*w[1]+s*(rho_star-w[0])
        self.assertAlmostEqual(actual[0],expected,places=14)

    def test_event_tail_partition_respects_cfl_and_minimum(self):
        dt=1.4665653203413753e-6;remaining=dt+9.195747462109605e-13
        split=event_step(dt,remaining)
        self.assertEqual(split,remaining/2)
        self.assertGreaterEqual(split,1e-12);self.assertLessEqual(split,dt)
        self.assertEqual(event_step(1e-12,1.5e-12),1e-12)  # No admissible two-way split.
        eos=IdealGas();mesh=uniform_mesh(2);w=(1.2,0.,100000.,.3)
        initial=[tuple(v*q for q in eos.conservative(w)) for v in mesh.volumes]
        cfl_dt=.4*.5/eos.sound_speed(w);end=2*cfl_dt+5e-13
        result=solve(mesh,initial,end,'periodic',eos=eos,sensor=.5,sample_interval=end)
        self.assertEqual(result['status'],'completed')
        self.assertEqual(result['time'],end);self.assertEqual(result['sensors'][-1][0],end)
        self.assertGreaterEqual(result['minimum_dt'],1e-12)
        self.assertLessEqual(result['max_CFL'],.4+1e-15)

    def test_counts_survive_later_boundary_failure(self):
        eos=IdealGas();mesh=uniform_mesh(4);w=(1.2,0.,100000.,.3)
        initial=[tuple(v*q for q in eos.conservative(w)) for v in mesh.volumes]
        boundaries=(Boundary('outflow'),Boundary('nonreflecting',state=(1.2,10000.,100000.,.3)))
        with patch('motorsim.gas1d.solver.hllc_flux',wraps=hllc_flux) as interior, patch('motorsim.gas1d.boundary.hllc_flux',wraps=hllc_flux) as exterior:
            result=solve(mesh,initial,1e-6,boundaries,eos=eos)
            self.assertEqual(result['status'],'failed_numerical')
            self.assertEqual(result['riemann_flux_count'],interior.call_count+exterior.call_count)
            self.assertEqual(result['riemann_flux_count'],4)

    def test_nonreflecting_explicit_base_entropy_and_species(self):
        eos=IdealGas()
        for normal in (-1,1):
            base=(2.,-normal*20.,120000.,.8)
            actual=Boundary('nonreflecting',state=base).face_state(base,normal,eos)
            for a,b in zip(actual,base):self.assertAlmostEqual(a,b,places=8)

    def test_open_incompatible_branches_not_zeroed(self):
        state=(1.161440185780459,1.8959009076787148e-10,99999.99999991049,.3000000000000006)
        with self.assertRaisesRegex(InvalidState,'No consistent open-boundary branch'):
            Boundary('open').face_state(state,1,IdealGas())

    def test_open_real_flow_sign_preserved(self):
        eos=IdealGas();rho=100000/(287*300)
        for normal in (-1,1):
            for velocity in (-1e-7,1e-7):
                actual=Boundary('open').face_state((rho,velocity,100000.,.3),normal,eos)
                self.assertEqual(math.copysign(1,actual[1]),math.copysign(1,velocity))

    def test_flux_counts_actual_calls_and_periodic_shared_face(self):
        eos=IdealGas();mesh=uniform_mesh(4);w=(1.2,0.,100000.,.3)
        initial=[tuple(v*q for q in eos.conservative(w)) for v in mesh.volumes]
        for bc in ('periodic',(Boundary('nonreflecting',state=w),Boundary('nonreflecting',state=w)),(Boundary('wall'),Boundary('wall'))):
            with patch('motorsim.gas1d.solver.hllc_flux',wraps=hllc_flux) as interior, patch('motorsim.gas1d.boundary.hllc_flux',wraps=hllc_flux) as exterior:
                result=solve(mesh,initial,1e-6,bc,eos=eos)
                self.assertEqual(result['status'],'completed')
                self.assertEqual(result['riemann_flux_count'],interior.call_count+exterior.call_count)
                self.assertEqual(result['hllc_flux_count']+result['hlle_fallback_count'],result['riemann_flux_count'])
                expected=2 if bc!='periodic' and bc[0].kind=='nonreflecting' else 0
                self.assertEqual(result['characteristic_flux_count'],expected)

    def test_fallback_records_actual_boundary_states(self):
        eos=IdealGas(1.,1.4);mesh=uniform_mesh(2,area=1.)
        left,right=(1.,-2.,.4,0.),(1.,2.,.4,1.)
        initial=[tuple(v*q for q in eos.conservative(right)) for v in mesh.volumes]
        result=solve(mesh,initial,1e-6,(Boundary('fixed',state=left),Boundary('fixed',state=right)),eos=eos)
        self.assertEqual(result['status'],'completed')
        record=next(r for r in result['fallback_records'] if r['face']==0)
        self.assertEqual(tuple(record['left']),left)
        for a,b in zip(record['right'],right):self.assertAlmostEqual(a,b)
        self.assertEqual(result['riemann_flux_count'],3)
        self.assertEqual(result['hlle_fallback_count'],1)
