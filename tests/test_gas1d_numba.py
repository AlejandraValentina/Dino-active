import unittest
import random
import json
import numpy as np
from motorsim.exhaust_numba import hllc,primitive,Kernel
from motorsim.gas1d.eos import IdealGas,InvalidState
from motorsim.gas1d.riemann import hllc_flux
from motorsim.gas1d.second_order import reconstruct
from motorsim.gas1d.boundary import Boundary
from motorsim.gas1d.mesh import smooth_mesh
from motorsim.gas1d.solver import cfl_step
from motorsim.exhaust1d import Bench,solve_exhaust
from motorsim.exhaust_numba import solve_exhaust as numpy_solve
from motorsim.coupling import ChamberState
from motorsim.exhaust_port import ExhaustPort
from motorsim.simulation_case import geometry


class NumbaTests(unittest.TestCase):
    def test_flux_branches_and_fallback_match_scalar(self):
        rng=random.Random(348);eos=IdealGas()
        def w():return (10**rng.uniform(-2,2),rng.uniform(-1500,1500),10**rng.uniform(3,7),rng.random())
        pairs=[(w(),w()) for _ in range(400)]
        pairs += [((1.,-1000.,10000.,.2),(1.,1000.,10000.,.8))]
        pairs += [(x,x) for x in [w() for _ in range(10)]]
        left=np.array([p[0] for p in pairs]);right=np.array([p[1] for p in pairs])
        f,s,reasons,_=hllc(left,right,eos)
        for i,(a,b) in enumerate(pairs):
            want,speed,reason=hllc_flux(a,b,eos)
            np.testing.assert_array_equal(f[i],want)
            np.testing.assert_array_equal(s[i],speed)
            self.assertEqual(reasons.get(i),reason)
        self.assertTrue(reasons)

    def test_primitive_and_invalid_species(self):
        eos=IdealGas();v=np.array([.1,.2,.3]);states=[(1.,4.,1e5,.2),(2.,-10.,2e5,.7),(.5,0.,1e4,0.)]
        cells=np.array([eos.conservative(s) for s in states])*v[:,None]
        want=[eos.primitive(tuple(x/a for x in row)) for row,a in zip(cells.tolist(),v.tolist())]
        np.testing.assert_array_equal(primitive(cells,v,eos),want)
        cells[0,3]=-1e-20
        with self.assertRaises(InvalidState):primitive(cells,v,eos)

    def test_reconstruction_and_cfl_nonuniform(self):
        rng=random.Random(2);mesh=smooth_mesh(31);eos=IdealGas();kernel=Kernel(mesh,eos)
        w=np.array([(1+rng.random(),rng.uniform(-100,100),100000*(1+rng.random()),rng.random()) for _ in range(mesh.n)])
        bc=(Boundary('outflow'),Boundary('nonreflecting',state=(1.,0.,1e5,.2)))
        a,b,d=reconstruct(mesh,w.tolist(),bc,eos);x,y,z=kernel.reconstruct(w,bc)
        np.testing.assert_array_equal(x,a);np.testing.assert_array_equal(y,b);self.assertEqual(z,d)
        speeds=np.array([400.+i for i in range(mesh.n+1)])
        self.assertEqual(kernel.cfl(w,speeds,.4),cfl_step(mesh,w.tolist(),speeds.tolist(),eos,.4))

    def test_joint_steps_match_scalar(self):
        from motorsim.gas1d.mesh import uniform_mesh
        from math import pi
        mesh=uniform_mesh(12,.6,pi*.02**2/4);eos=IdealGas();rho=1e5/(287*300)
        pipe=[tuple(v*q for q in eos.conservative((rho,0.,1e5,.2))) for v in mesh.volumes]
        for pressure in (80000.,300000.):
            ch=ChamberState(pressure*.0001/(287*600),pressure*.0001/(eos.gamma-1),.8*pressure*.0001/(287*600),.0001)
            system=Bench(ch,ExhaustPort.from_project(geometry()),start_angle=100)
            a=solve_exhaust(mesh,pipe,system,.00015,sensors=(.1,));b=numpy_solve(mesh,pipe,system,.00015,sensors=(.1,))
            for key in ('cells','state','history','stages','events','counts','extrema','external','port_integral'):
                self.assertEqual(json.loads(json.dumps(a[key])),json.loads(json.dumps(b[key])),key)

    def test_all_component_downgrade_is_observable(self):
        from motorsim.gas1d.mesh import uniform_mesh
        mesh=uniform_mesh(3,.001);eos=IdealGas();kernel=Kernel(mesh,eos)
        states=[(1e300,0.,p,.2) for p in (3e307,6e307,9e307)]
        bc=(Boundary('outflow'),Boundary('outflow'))
        a,b,d=reconstruct(mesh,states,bc,eos)
        with np.errstate(all='ignore'):x,y,z=kernel.reconstruct(np.array(states),bc)
        self.assertEqual(d,[1]);self.assertEqual(z,d)
        np.testing.assert_array_equal(x,a);np.testing.assert_array_equal(y,b)


if __name__=='__main__':unittest.main()
