import math
import unittest
from motorsim.gas1d.eos import IdealGas,InvalidState
from motorsim.gas1d.mesh import uniform_mesh,segments_mesh,smooth_mesh
from motorsim.gas1d.riemann import hllc_flux,hlle_flux,estimate_wave_speeds
from motorsim.gas1d.boundary import Boundary
from motorsim.gas1d.solver import solve,cfl_step
from motorsim.gas1d.reference import ExactRiemann,cell_integrals


class GasTests(unittest.TestCase):
    def setUp(self):self.e=IdealGas();self.w=(1.2,30.,100000.,.3)

    def test_eos_roundtrip_sound_pressure(self):
        for w in (self.w,(1.,-150.,1200.,0.),(2.,0.,200000.,1.)):
            recovered=self.e.primitive(self.e.conservative(w))
            for a,b in zip(w,recovered):self.assertAlmostEqual(a,b,places=9)
        self.assertAlmostEqual(self.e.cv,820);self.assertAlmostEqual(self.e.cp,1107)
        self.assertAlmostEqual(self.e.sound_speed(self.w)**2,1.35*100000/1.2)

    def test_invalid_states(self):
        for w in ((0.,0.,1.,0.),(1.,0.,0.,0.),(1.,0.,1.,-1e-16),(1.,0.,1.,1.0000000000000002),(1.,math.nan,1.,0.)):
            with self.assertRaises(InvalidState):self.e.conservative(w)
        with self.assertRaises(InvalidState):self.e.primitive((1.,100.,1.,.5))

    def test_p5_mass_fraction_view_accepts_only_the_bounded_rho_y_roundoff(self):
        # Captured from the accepted P5-CYCLE-24 attempt: independently
        # updated float64 rho and rho*Y differ by one ULP near Y=1.
        rho = 0.7952109571685706
        rho_y = 0.7952109571685707
        q = (rho, 230.51360083770064, 204007.64651722068, rho_y)
        assert self.e.primitive_with_mass_fraction_roundoff(q)[3] == 1.0
        with self.assertRaises(InvalidState):
            self.e.primitive(q)  # general EOS validation remains strict

        far_outside = (rho, q[1], q[2], rho + 32 * math.ulp(rho))
        with self.assertRaises(InvalidState):
            self.e.primitive_with_mass_fraction_roundoff(far_outside)

    def test_equal_hllc_hlle(self):
        for w in (self.w,(1.,0.,1.,1.),(1.,-1000.,10000.,.7)):
            f,s,reason=hllc_flux(w,w,self.e);self.assertIsNone(reason)
            for actual,expected in zip(f,self.e.flux(w)):self.assertAlmostEqual(actual,expected)
            for actual,expected in zip(hlle_flux(w,w,self.e),self.e.flux(w)):self.assertAlmostEqual(actual,expected,places=7)

    def test_stationary_contact(self):
        f,s,reason=hllc_flux((1.,0.,100000.,0.),(2.,0.,100000.,1.),self.e)
        self.assertEqual(f,(0.,100000.,0.,0.));self.assertIsNone(reason)

    def test_scalar_donor_both_directions(self):
        for u in (50.,-50.):
            f,_,_=hllc_flux((1.,u,100000.,.8),(2.,u,100000.,.1),self.e)
            self.assertAlmostEqual(f[3],f[0]*(.8 if u>0 else .1))

    def test_fallback_expansion(self):
        e=IdealGas(1.,1.4);l=(1.,-2.,.4,0.);r=(1.,2.,.4,1.)
        f,s,reason=hllc_flux(l,r,e)
        self.assertEqual(reason,'inadmissible_star');self.assertEqual(f,hlle_flux(l,r,e))

    def test_frustum_volume_centroid_and_join(self):
        m=segments_mesh([dict(length=1000,start_diameter=100,end_diameter=120)],.01)
        self.assertAlmostEqual(sum(m.volumes),math.pi*(.1**2+.1*.12+.12**2)/12,places=15)
        self.assertGreater(sum(v*x for v,x in zip(m.volumes,m.centers))/sum(m.volumes),.5)
        joined=segments_mesh([dict(length=500,start_diameter=100,end_diameter=120),dict(length=500,start_diameter=120,end_diameter=100)],.07)
        self.assertEqual(joined.faces.count(.5),1)
        with self.assertRaises(ValueError):segments_mesh([dict(length=1,start_diameter=1,end_diameter=2),dict(length=1,start_diameter=3,end_diameter=4)],.001)

    def test_boundary_generation(self):
        wall=Boundary('wall');self.assertEqual(wall.face_state(self.w,1,self.e),(1.2,-30.,100000.,.3))
        base=(100000/(287*300),0.,100000.,.3)
        for kind in ('open','nonreflecting','reservoir'):
            w=Boundary(kind).face_state(base,1,self.e)
            for a,b in zip(w,base):self.assertAlmostEqual(a,b,places=8)
        with self.assertRaises(InvalidState):Boundary('reservoir').face_state((1.,-1000.,100000.,.3),1,self.e)

    def test_cfl_uniform(self):
        mesh=uniform_mesh(10);states=[self.w]*10;s=abs(self.w[1])+self.e.sound_speed(self.w)
        dt,_,_=cfl_step(mesh,states,[s]*11,self.e,.4)
        self.assertAlmostEqual(dt,.4*.1/s)

    def test_VARIABLE_AREA_STATIC_EQUILIBRIUM_and_ledger(self):
        base=(100000/(287*300),0.,100000.,.3)
        for mesh in (smooth_mesh(20),segments_mesh([dict(length=1000,start_diameter=100,end_diameter=120)],.05)):
            initial=[tuple(v*q for q in self.e.conservative(base)) for v in mesh.volumes]
            out=solve(mesh,initial,.0001,(Boundary('wall'),Boundary('wall')),eos=self.e)
            self.assertEqual(out['status'],'completed')
            self.assertLess(max(abs(w[1])/self.e.sound_speed(base) for w in out['primitive']),1e-12)
            self.assertLess(max(max(row['normalized']) for row in out['ledger']),1e-10)

    def test_exact_sod_independent_reference(self):
        e=IdealGas(1.,1.4);ref=ExactRiemann((1.,0.,1.,1.),(.125,0.,.1,0.),e)
        self.assertAlmostEqual(ref.pstar,.30313017805064685,places=11)
        self.assertAlmostEqual(ref.ustar,.9274526200489499,places=11)
        self.assertLess(ref.residual,1e-12)
        m=uniform_mesh(20,area=1.)
        cells=cell_integrals(m,lambda x:ref.sample((x-.5)/.2),e,lambda x:1.,ref.breaks(.2))
        self.assertAlmostEqual(sum(c[0] for c in cells),.5625,places=10)


if __name__=='__main__':unittest.main()
