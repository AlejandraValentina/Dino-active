import unittest
from unittest.mock import patch
from motorsim.coupling import ChamberState, interface_flux
from motorsim.gas1d.eos import IdealGas
from motorsim.gas1d.riemann import hllc_flux


def chamber(p=100000., T=300., Y=.3, V=.01):
    eos=IdealGas();m=p*V/(eos.R*T)
    return ChamberState(m,p*V/(eos.gamma-1),Y*m,V)


class RiemannCouplingTests(unittest.TestCase):
    def test_thermal_contacts(self):
        for T in (299.,300.,301.):
            for n in (-1,1):
                flux=interface_flux(chamber(),(100000/(287*T),0.,100000.,.3),.01,n)
                self.assertEqual(tuple(flux.outward[k] for k in (0,2,3)),(0.,0.,0.))
                self.assertIsNone(flux.fallback_reason)

    def test_exactly_one_riemann_evaluation(self):
        with patch('motorsim.coupling.hllc_flux', wraps=hllc_flux) as kernel:
            result=interface_flux(chamber(120000,Y=.8),(100000/(287*300),0.,100000.,.2),.01,-1)
        self.assertEqual(kernel.call_count,1)
        left,right,eos=kernel.call_args.args
        self.assertEqual(left[1],0.)
        expected=hllc_flux(left,right,eos)[0]
        self.assertEqual(result.flux_x,tuple(.01*f for f in expected))
        increments=result.increments(1e-5)
        self.assertTrue(all(a==-b for a,b in zip(increments['chamber'],increments['pipe'])))

    def test_forward_reverse_species_and_orientation(self):
        for pressure in (80000.,120000.):
            for n in (-1,1):
                flux=interface_flux(chamber(pressure,Y=.8),(100000/(287*300),0.,100000.,.2),.01,n)
                self.assertEqual(flux.outward[0]<0, pressure>100000)
                self.assertAlmostEqual(flux.outward[3]/flux.outward[0],.8 if pressure>100000 else .2)

    def test_fallback_vector_not_replaced(self):
        # Audit plumbing independently of which states trigger contractual HLLE.
        with patch('motorsim.coupling.hllc_flux',return_value=((1.,2.,3.,.4),(-2.,0.,2.),'inadmissible_star')):
            r=interface_flux(chamber(),(1.,0.,100000.,.2),.01,-1)
        self.assertEqual(r.outward,(-.01,-.02,-.03,-.004))
        self.assertEqual(r.fallback_reason,'inadmissible_star')
