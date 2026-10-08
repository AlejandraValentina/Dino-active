import unittest
from motorsim.coupled import solve_coupled
from motorsim.gas1d.eos import IdealGas, InvalidState
from motorsim.gas1d.mesh import uniform_mesh
from dev_orchestrator.p3_r1 import chamber


class CoupledStageTests(unittest.TestCase):
    def test_shared_stage_and_ledger(self):
        eos=IdealGas();mesh=uniform_mesh(8,.3,.0003)
        initial=[tuple(v*x for x in eos.conservative((100000/(287*300),0.,100000.,.2))) for v in mesh.volumes]
        r=solve_coupled(mesh,initial,chamber(120000,V=.0001),.00002)
        self.assertEqual(r['status'],'completed')
        self.assertEqual(len(r['traces'][0]['stages']),2)
        a,b=r['traces'][0]['stages']
        self.assertNotEqual(a['chamber'],b['chamber'])
        self.assertNotEqual(a['outward'],b['outward'])
        self.assertLess(max(max(l['normalized']) for l in r['ledger']),1e-10)
        self.assertTrue(all(l['external']==[0.,0.,0.] for l in r['ledger']))

    def test_invalid_chamber_rejected(self):
        from motorsim.coupling import ChamberState
        eos=IdealGas();mesh=uniform_mesh(2)
        q=[tuple(v*x for x in eos.conservative((1.,0.,100000.,.2))) for v in mesh.volumes]
        with self.assertRaises(InvalidState):solve_coupled(mesh,q,ChamberState(1.,-1.,.2,1.),.001)

    def test_isolated_adiabatic_work_source(self):
        # Isolate the work term with a sealed-face test double, not an R1 case.
        from unittest.mock import patch
        from motorsim.coupling import RiemannExchange
        from dev_orchestrator.p3_acoustic import volume
        eos=IdealGas();ch=chamber(100000,Y=.3,V=.0001);end=.00075
        expected=ch.internal_energy*(ch.volume/volume(end)[0])**(eos.gamma-1)
        def sealed(chamber,pipe,area,normal,*,eos):
            a=eos.sound_speed(pipe);flux=(0.,area*pipe[2],0.,0.)
            return RiemannExchange(flux,tuple(normal*x for x in flux),(-a,0.,a),None)
        errors=[]
        with patch('motorsim.coupled.interface_flux',side_effect=sealed):
            for n in (20,40,80):
                mesh=uniform_mesh(n,.3,.0003)
                q=[tuple(v*x for x in eos.conservative((100000/(287*300),0.,100000.,.3))) for v in mesh.volumes]
                r=solve_coupled(mesh,q,ch,end,volume=volume)
                self.assertEqual(r['status'],'completed')
                self.assertEqual(r['chamber'][0],ch.mass)
                self.assertEqual(r['chamber'][2],ch.fresh_mass)
                errors.append(abs(r['chamber'][1]-expected)/expected)
        self.assertTrue(all(b<a for a,b in zip(errors,errors[1:])),errors)
        self.assertLess(errors[-1],1e-5)
