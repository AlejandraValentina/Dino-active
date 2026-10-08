import unittest
from dev_orchestrator.p4_r1 import absolute_integral,brackets,prepare,measured
from motorsim.exhaust1d import solve_exhaust


class ObservableTests(unittest.TestCase):
    def test_absolute_linear_quadrature(self):
        self.assertEqual(absolute_integral([0.,1.],[-2.,2.]),1.)
        self.assertAlmostEqual(absolute_integral([0.,3.],[-2.,1.]),2.5)
        self.assertEqual(absolute_integral([0.,1.,2.],[1.,2.,3.]),4.)
        self.assertEqual(absolute_integral([0.,.5,1.],[-2.,0.,2.]),1.)
    def test_sensor_at_same_physical_point(self):
        for n in (100,200,400,800):
            mesh,_,_,_=prepare('blowdown',n,.4);lo,hi,a=brackets(mesh)
            self.assertAlmostEqual((1-a)*lo+a*hi,.1,places=16)
            self.assertAlmostEqual((1-a)*(3*lo+7)+a*(3*hi+7),7.3)
    def test_logging_does_not_change_solution(self):
        mesh,q,system,_=prepare('blowdown',12,.4);lo,hi,a=brackets(mesh)
        old=solve_exhaust(mesh,q,system,.001,sensors=(.1,.3,.5))
        new=solve_exhaust(mesh,q,system,.001,sensors=(lo,hi))
        for key in ('cells','state','port_integral','external','counts','events','hit_events','stages'):
            self.assertEqual(old[key],new[key],key)
        self.assertEqual([h['dt'] for h in old['history']],[h['dt'] for h in new['history']])
