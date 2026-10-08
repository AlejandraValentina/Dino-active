import unittest
from motorsim.coupling import ChamberState, prescribed_reservoir_flux as interface_flux
from motorsim.gas1d.eos import IdealGas, InvalidState


class InterfaceTests(unittest.TestCase):
    def setUp(self):
        self.eos = IdealGas()
        self.chamber = ChamberState(100000/(287*300)*.01, 100000*.01/(1.35-1),
                                    .8*100000/(287*300)*.01, .01)

    def test_equilibrium_and_pressure_impulse(self):
        state=(100000/(287*300),0.,100000.,.8)
        for normal in (-1,1):
            flux=interface_flux(self.chamber,state,.01,normal)
            self.assertEqual(flux.outward[0],0.)
            self.assertEqual(flux.outward[2],0.)
            self.assertEqual(flux.outward[3],0.)
            self.assertAlmostEqual(flux.outward[1],normal*1000.)

    def test_shared_increment_and_total_enthalpy(self):
        for u,expected in ((-20.,'chamber'),(20.,'pipe')):
            flux=interface_flux(self.chamber,(100000/(287*300),u,100000.,.2),.01,1)
            self.assertEqual(flux.donor,expected)
            self.assertAlmostEqual(flux.outward[3]/flux.outward[0],.8 if u<0 else .2)
            _,velocity,p,y=flux.face_state
            rho=flux.face_state[0]
            self.assertAlmostEqual(flux.outward[2]/flux.outward[0],self.eos.cp*p/(rho*self.eos.R)+velocity**2/2)
            increments=flux.increments(1e-5)
            self.assertEqual(tuple(a+b for a,b in zip(increments['chamber'],increments['pipe'])),(0.,0.,0.))

    def test_invalid_state_not_clipped(self):
        for args in ((0,1,0,1),(1,0,0,1),(1,1,2,1),(1,1,-.1,1)):
            with self.assertRaises(InvalidState):
                ChamberState(*args).thermodynamics(self.eos)

    def test_frozen_boundary_gap_is_not_hidden(self):
        with self.assertRaisesRegex(InvalidState,'No consistent reservoir inflow branch'):
            interface_flux(self.chamber,(100000/(287*301),-.001,100000.,.2),.01,1)


if __name__=='__main__':
    unittest.main()
