import unittest
from dataclasses import replace
from motorsim.exhaust_port import ExhaustPort, port_flux
from motorsim.simulation_case import geometry
from motorsim.gas1d.eos import IdealGas
from motorsim.gas1d.boundary import Boundary
from motorsim.coupling import ChamberState, interface_flux


class ExhaustPortTests(unittest.TestCase):
    def setUp(self):
        self.eos=IdealGas();self.ch=ChamberState(.0002,80.,.00012,.0001)
        self.pipe=(100000/(287*300),12.,100000.,.2);self.area=.0003
    def test_closed_wall_exact_and_continuous(self):
        closed=port_flux(self.ch,self.pipe,0.,self.area)
        wall,_,_=Boundary('wall').flux(self.pipe,-1,self.eos)
        self.assertEqual(closed['exchange'],(0.,0.,0.))
        self.assertEqual(closed['flux'],tuple(self.area*x for x in wall))
        errors=[]
        for fraction in (1e-2,1e-4,1e-6,1e-8):
            f=port_flux(self.ch,self.pipe,self.area*fraction,self.area)
            errors.append(max(abs(a-b) for a,b in zip(f['flux'],closed['flux'])))
        self.assertTrue(all(b<a for a,b in zip(errors,errors[1:])))
    def test_open_shared_flux_and_local_backflow_species(self):
        for ch in (self.ch,replace(self.ch,internal_energy=10.)):
            for fraction in (.2,1.,2.):
                area=min(self.area*fraction,self.area)
                f=port_flux(ch,self.pipe,self.area*fraction,self.area)
                reference=interface_flux(ch,self.pipe,area,-1)
                self.assertEqual(f['exchange'],tuple(reference.outward[k] for k in (0,2,3)))
                for j,k in enumerate((0,2,3)):self.assertEqual(f['exchange'][j],-f['flux'][k])
    def test_existing_area_and_events(self):
        project=geometry();port=ExhaustPort.from_project(project)
        from motorsim.ports import port_results
        expected=port_results(project.ports[0],project.stroke_mm,project.rod_length_mm)
        self.assertIn(expected.opening,port.events(self.area));self.assertIn(expected.closing,port.events(self.area))
        for angle,value in enumerate(expected.areas):self.assertEqual(port.area(angle),value*1e-6)

    def test_geometry_adapter_existing_segments(self):
        from math import pi,fsum
        from motorsim.exhaust_geometry import exhaust_mesh
        project=geometry();mesh=exhaust_mesh(project.ducts.exhaust,.003)
        expected=fsum(pi*s.length_mm*(s.start_diameter_mm**2+s.start_diameter_mm*s.end_diameter_mm+s.end_diameter_mm**2)/12*1e-9 for s in project.ducts.exhaust)
        self.assertAlmostEqual(fsum(mesh.volumes),expected,places=15)
        self.assertAlmostEqual(mesh.faces[-1],.2)

    def test_geometry_rejects_discontinuous_joint(self):
        from motorsim.exhaust_geometry import exhaust_mesh
        from motorsim.project import DuctSegment
        with self.assertRaises(ValueError):exhaust_mesh((DuctSegment('',100,20,20),DuctSegment('',100,30,30)),.01)
