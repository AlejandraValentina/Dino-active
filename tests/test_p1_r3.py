import math
import unittest
from motorsim.gas1d.eos import IdealGas,InvalidState
from motorsim.gas1d.boundary import Boundary
from motorsim.gas1d.verification import definition,BASE,P0,A0,RHO


class BoundarySemanticsTests(unittest.TestCase):
    def test_pressure_and_outgoing_characteristic_both_normals(self):
        eos=IdealGas();bc=Boundary('ideal_open_pressure_release')
        for normal in (-1,1):
            for dp in (-10.,10.):
                state=(RHO+dp/A0**2,normal*dp/(RHO*A0),P0+dp,.4)
                result=bc.face_state(state,normal,eos)
                self.assertEqual(result[2],P0)
                self.assertNotEqual(result[1],0.)
                jp=lambda w:normal*w[1]+2*eos.sound_speed(w)/(eos.gamma-1)
                self.assertAlmostEqual(jp(state),jp(result),places=10)
                self.assertAlmostEqual(state[2]/state[0]**eos.gamma,result[2]/result[0]**eos.gamma,places=8)
                self.assertEqual(result[3],.4)
                flux,_,reason=bc.flux(state,normal,eos)
                self.assertEqual(flux,eos.flux(result));self.assertIsNone(reason)

    def test_previous_incompatible_states_are_not_zeroed(self):
        eos=IdealGas();bc=Boundary('ideal_open_pressure_release')
        state=(1.161440185780459,1.8959009076787148e-10,99999.99999991049,.3000000000000006)
        result=bc.face_state(state,1,eos)
        self.assertLess(result[1],0.)
        self.assertAlmostEqual(result[1],-3.64578601597e-11,delta=1e-22)
        self.assertEqual(result[2],100000.)

    def test_no_microscopic_sign_switch(self):
        eos=IdealGas();bc=Boundary('ideal_open_pressure_release',T0=999.,Y0=.9)
        for velocity in (-1e-15,0.,1e-15):
            result=bc.face_state((RHO,velocity,P0,.2),1,eos)
            self.assertEqual(result[1],velocity)
            self.assertEqual(result[3],.2)

    def test_scope_and_invalid_pressure(self):
        eos=IdealGas()
        for pressure in (0.,-1.,float('nan')):
            with self.assertRaises(InvalidState):Boundary('ideal_open_pressure_release',p0=pressure).face_state(BASE,1,eos)
        with self.assertRaises(InvalidState):Boundary('ideal_open_pressure_release').face_state((RHO,2*A0,P0,.3),1,eos)

    def test_distinct_characteristic_response(self):
        eos=IdealGas();dp=1.;state=(RHO+dp/A0**2,dp/(RHO*A0),P0+dp,.3)
        opened=Boundary('ideal_open_pressure_release').face_state(state,1,eos)
        nr=Boundary('nonreflecting',state=BASE).face_state(state,1,eos)
        self.assertEqual(opened[2],P0)
        self.assertGreater(nr[2],P0)
        self.assertAlmostEqual(opened[1]/state[1],2.,delta=2e-5)
        self.assertAlmostEqual(nr[1]/state[1],1.,delta=2e-5)

    def test_assignments_and_explicit_exterior(self):
        self.assertEqual(definition('T05')['bc'][1].kind,'ideal_open_pressure_release')
        self.assertEqual(definition('T04')['bc'][1].kind,'wall')
        for name in ('T03','T04','T05'):
            self.assertEqual(definition(name)['bc'][0].state,BASE)
        self.assertEqual(definition('T03')['bc'][1].state,BASE)
