import math
import unittest
from unittest.mock import patch
from motorsim.gas1d.eos import IdealGas,InvalidState
from motorsim.gas1d.mesh import uniform_mesh,segments_mesh
from motorsim.gas1d.boundary import Boundary
from motorsim.gas1d.methods import solve
from motorsim.gas1d.solver import solve as frozen_solve,cfl_step
from motorsim.gas1d.second_order import minmod,reconstruct


class P2BTests(unittest.TestCase):
    def setUp(self):self.eos=IdealGas()
    def initial(self,mesh,states):
        return [tuple(v*q for q in self.eos.conservative(w)) for v,w in zip(mesh.volumes,states)]

    def test_minmod_not_mc(self):
        self.assertEqual(minmod(1.,3.),1.)
        self.assertEqual(minmod(-4.,-2.),-2.)
        self.assertEqual(minmod(-1.,2.),0.)
        self.assertEqual(minmod(0.,2.),0.)

    def test_stage_cfl_gate_uses_actual_step_inequality(self):
        from dev_orchestrator.p2b_campaign import stage_cfl_valid
        dt=.4*9e-8
        self.assertGreater(dt/9e-8,.4)
        result=dict(max_CFL=dt/9e-8,stage_ledger=[dict(accepted_dt=dt,stage1_dt_limit=dt,stage2_dt_limit=dt)])
        self.assertTrue(stage_cfl_valid(result))
        result['stage_ledger'][0]['accepted_dt']=math.nextafter(dt,math.inf)
        self.assertFalse(stage_cfl_valid(result))

    def test_nonuniform_linear_reconstruction(self):
        mesh=segments_mesh([dict(length=1000,start_diameter=100,end_diameter=180)],.2)
        states=[(1.2+x,.1*x,100000+100*x,.2+.1*x) for x in mesh.centers]
        left,right,down=reconstruct(mesh,states,(Boundary('outflow'),Boundary('outflow')),self.eos)
        self.assertFalse(down)
        for i in range(1,mesh.n-1):
            for face,actual in ((mesh.faces[i],left[i]),(mesh.faces[i+1],right[i])):
                expected=(1.2+face,.1*face,100000+100*face,.2+.1*face)
                for a,b in zip(actual,expected):self.assertAlmostEqual(a,b,places=10)

    def test_local_downgrade_all_components_without_changing_average(self):
        mesh=uniform_mesh(3);states=[(1.2,2.,100000.,.3)]*3
        with patch('motorsim.gas1d.second_order.minmod',return_value=100.):
            left,right,down=reconstruct(mesh,states,'periodic',self.eos)
        self.assertEqual(down,[0,1,2]);self.assertEqual(left,states);self.assertEqual(right,states)

    def test_first_order_dispatch_exact(self):
        mesh=uniform_mesh(4);initial=self.initial(mesh,[(1.2,0.,100000.,.3)]*4)
        a=frozen_solve(mesh,initial,1e-5,'periodic',eos=self.eos)
        b=solve(mesh,initial,1e-5,'periodic',eos=self.eos,method='FIRST_ORDER')
        a.pop('wall_seconds');b.pop('wall_seconds');self.assertEqual(a,b)
        with self.assertRaises(ValueError):solve(mesh,initial,1e-5,'periodic',method='RK4')

    def test_uniform_state_shared_periodic_flux_and_stages(self):
        mesh=uniform_mesh(6);initial=self.initial(mesh,[(1.2,20.,100000.,.3)]*6)
        r=solve(mesh,initial,1e-5,'periodic',eos=self.eos,method='MUSCL_SSPRK2')
        self.assertEqual(r['status'],'completed');self.assertEqual(r['cells'],initial)
        self.assertEqual(r['riemann_flux_count'],mesh.n*r['rhs_count'])
        self.assertEqual(r['rhs_count'],2*r['steps'])
        self.assertEqual(len(r['stage_ledger']),r['steps'])
        self.assertLessEqual(max(max(x['normalized']) for x in r['ledger']),1e-10)

    def test_stage_cfl_rejection_rolls_back_ledger(self):
        mesh=uniform_mesh(4);initial=self.initial(mesh,[(1.2,0.,100000.,.3)]*4)
        calls=0
        def limited(*args):
            nonlocal calls
            calls+=1;limit,index,unit=cfl_step(*args)
            return (limit*.1 if calls==2 else limit),index,unit
        with patch('motorsim.gas1d.second_order.cfl_step',side_effect=limited):
            r=solve(mesh,initial,.0001,'periodic',eos=self.eos,method='MUSCL_SSPRK2')
        self.assertEqual(r['status'],'completed');self.assertEqual(r['cells'],initial)
        self.assertGreater(r['rejection_reasons'].get('stage_CFL_exceeded',0),0)
        self.assertEqual(len(r['ledger']),r['steps'])
        self.assertEqual(r['boundary_flux_integral'],[0.]*4)
        self.assertEqual(r['source_integral'],[0.]*4)
        self.assertAlmostEqual(sum(x['dt'] for x in r['ledger']),.0001)

    def test_variable_area_static_ledger(self):
        mesh=segments_mesh([dict(length=1000,start_diameter=100,end_diameter=120)],.125)
        initial=self.initial(mesh,[(1.2,0.,100000.,.3)]*mesh.n)
        r=solve(mesh,initial,1e-4,(Boundary('wall'),Boundary('wall')),eos=self.eos,method='MUSCL_SSPRK2')
        self.assertEqual(r['status'],'completed')
        self.assertLess(max(abs(w[1]) for w in r['primitive']),1e-10)
        self.assertLess(max(max(x['normalized']) for x in r['ledger']),1e-10)

    def test_invalid_input_rejected_without_clipping(self):
        mesh=uniform_mesh(2)
        with self.assertRaises(InvalidState):
            solve(mesh,[(1.,0.,1.,1.01)]*2,1e-5,'periodic',eos=self.eos,method='MUSCL_SSPRK2')


if __name__=='__main__':unittest.main()
