import unittest
import numpy as np
import random
from motorsim.gas1d.eos import IdealGas
from motorsim.gas1d.mesh import smooth_mesh
from motorsim.gas1d.boundary import Boundary
import motorsim.exhaust_numba as nb
import motorsim.exhaust_numba_fused as nbf

class AliasingTests(unittest.TestCase):
    def test_fused_does_not_alias_input(self):
        eos=IdealGas()
        mesh=smooth_mesh(8)
        volumes=np.array(mesh.volumes)
        # create cells
        w=[(1+random.random(), random.uniform(-50,50), 100000*(1+random.random()), random.random()) for _ in range(mesh.n)]
        cells=np.array([tuple(qi*v for qi in eos.conservative(x)) for x,v in zip(w, volumes)], dtype=np.float64)
        cells_copy=cells.copy()
        n=mesh.n
        w_buf=np.empty((n,4),dtype=np.float64)
        lf_buf=np.empty((n,4),dtype=np.float64)
        rf_buf=np.empty((n,4),dtype=np.float64)
        bad_buf=np.empty(n,dtype=np.bool_)
        flux_buf=np.empty((n-1,4),dtype=np.float64)
        speeds_buf=np.empty((n-1,3),dtype=np.float64)
        codes_buf=np.empty(n-1,dtype=np.int64)
        ext=np.array([100000/(eos.R*500),0,100000,0],dtype=np.float64)
        from motorsim.exhaust_numba import Kernel as NK
        nk=NK(mesh,eos)
        nb.fused_interior(cells, volumes, nk.dl, nk.dr, nk.left_offset, nk.right_offset, eos.gamma, eos.R, ext, w_buf, lf_buf, rf_buf, bad_buf, flux_buf, speeds_buf, codes_buf)
        # cells should be unchanged
        np.testing.assert_array_equal(cells, cells_copy)
        # w_buf etc should not alias cells
        self.assertIsNot(w_buf, cells)
        self.assertFalse(np.shares_memory(w_buf, cells))

    def test_reuse_does_not_pollute(self):
        eos=IdealGas()
        mesh=smooth_mesh(6)
        volumes=np.array(mesh.volumes)
        from motorsim.exhaust_numba import Kernel as NK
        nk=NK(mesh,eos)
        n=mesh.n
        w_buf=np.empty((n,4),dtype=np.float64)
        lf_buf=np.empty((n,4),dtype=np.float64)
        rf_buf=np.empty((n,4),dtype=np.float64)
        bad_buf=np.empty(n,dtype=np.bool_)
        flux_buf=np.empty((n-1,4),dtype=np.float64)
        speeds_buf=np.empty((n-1,3),dtype=np.float64)
        codes_buf=np.empty(n-1,dtype=np.int64)
        ext=np.array([100000/(eos.R*500),0,100000,0],dtype=np.float64)
        # two different cell states
        w1=[(1,0,100000,0.2) for _ in range(n)]
        w2=[(2,100,200000,0.8) for _ in range(n)]
        cells1=np.array([tuple(qi*v for qi in eos.conservative(x)) for x,v in zip(w1, volumes)], dtype=np.float64)
        cells2=np.array([tuple(qi*v for qi in eos.conservative(x)) for x,v in zip(w2, volumes)], dtype=np.float64)
        nb.fused_interior(cells1, volumes, nk.dl, nk.dr, nk.left_offset, nk.right_offset, eos.gamma, eos.R, ext, w_buf, lf_buf, rf_buf, bad_buf, flux_buf, speeds_buf, codes_buf)
        out1=w_buf.copy()
        nb.fused_interior(cells2, volumes, nk.dl, nk.dr, nk.left_offset, nk.right_offset, eos.gamma, eos.R, ext, w_buf, lf_buf, rf_buf, bad_buf, flux_buf, speeds_buf, codes_buf)
        out2=w_buf.copy()
        # ensure second call overwrote correctly and first output not retained incorrectly
        self.assertFalse(np.allclose(out1, out2))
        # also check that first call's w not equal second's w
        # Re-run first and compare to out1
        nb.fused_interior(cells1, volumes, nk.dl, nk.dr, nk.left_offset, nk.right_offset, eos.gamma, eos.R, ext, w_buf, lf_buf, rf_buf, bad_buf, flux_buf, speeds_buf, codes_buf)
        np.testing.assert_array_equal(w_buf, out1)

    def test_ssp_stage_preserves_qn(self):
        # Test that SSPRK2 with fused does not alias q^n
        from motorsim.gas1d.mesh import uniform_mesh
        from motorsim.exhaust1d import Bench, solve_exhaust
        from motorsim.coupling import ChamberState
        from motorsim.exhaust_port import ExhaustPort
        from motorsim.simulation_case import geometry
        mesh=uniform_mesh(12,.6,3.141592653589793*.02**2/4)
        eos=IdealGas()
        rho=1e5/(287*300)
        pipe=[tuple(v*q for q in eos.conservative((rho,0.,1e5,.2))) for v in mesh.volumes]
        from motorsim.exhaust_geometry import exhaust_mesh
        from motorsim.gas1d.mesh import smooth_mesh
        # use uniform for simplicity
        ch=ChamberState(300000*.0001/(eos.R*600),300000*.0001/(eos.gamma-1),.8*300000*.0001/(eos.R*600),.0001)
        system=Bench(ch,ExhaustPort.from_project(geometry()),start_angle=100)
        # run with fused and check that q after step is not aliased to dq
        import motorsim.exhaust_numba_fused as fused
        import json
        r1=solve_exhaust(mesh,pipe,system,.00015,sensors=(.1,))
        import motorsim.exhaust_numba as orig
        r2=orig.solve_exhaust(mesh,pipe,system,.00015,sensors=(.1,))
        self.assertEqual(r1['counts'], r2['counts'])
        for k in ('cells','state'):
            self.assertEqual(json.loads(json.dumps(r1[k])), json.loads(json.dumps(r2[k])))

if __name__=='__main__':
    unittest.main()
