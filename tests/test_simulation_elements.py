"""Controles analíticos previos del diseño; no ejecutan el motor integrado."""
import math
import unittest

from motorsim.simulation import (Model, add_transport, restriction, rk4,
                                 burn_fraction, burn_rate)


class ElementaryControls(unittest.TestCase):
    def test_geometry_and_work_sign(self):
        model = Model()
        self.assertLess(abs(model.duct_volumes[0]/(10*math.pi*1e-6)-1), 1e-9)
        self.assertLess(abs(model.duct_volumes[1]/(100/3*math.pi*1e-6)-1), 1e-9)
        for area in model.throats:
            self.assertLess(abs(area/(100*math.pi*1e-6)-1), 1e-9)
        expected = (250+46.656*math.pi)*1e-6
        for angle in (0, 17.3, 90, 180, 270, 359.9):
            volumes, dv, _ = model.geometry(angle)
            self.assertLess(abs((volumes[1]+volumes[2])/expected-1), 1e-9)
            self.assertEqual(dv[1], -dv[2])
        self.assertGreater(model.geometry(90)[1][2], 0)
        self.assertLess(model.geometry(270)[1][2], 0)

    def test_compressible_reference_and_reversal(self):
        hot, cold = (200000, 300, .25), (100000, 500, .8)
        q, h, fresh = restriction(hot, cold, 1e-4, 1, gamma=1.4)
        self.assertLess(abs(q/.04667117-1), 1e-5)
        self.assertAlmostEqual(h/q, 1004.5*300)
        self.assertEqual(fresh/q, .25)
        self.assertEqual(restriction(cold, hot, 1e-4, 1, gamma=1.4), (-q, -h, -fresh))
        reverse = restriction((100000, 300, .25), (200000, 500, .8), 1e-4, 1, gamma=1.4)
        self.assertLess(reverse[0], 0)
        self.assertAlmostEqual(reverse[1]/reverse[0], 1004.5*500)
        self.assertEqual(reverse[2]/reverse[0], .8)
        sub = restriction(hot, (160000, 500, .8), 1e-4, 1, gamma=1.4)[0]
        self.assertLess(abs(sub/.03821455284-1), 1e-5)
        for area, right in ((0, cold), (1e-4, (200000, 500, .8))):
            self.assertEqual(restriction(hot, right, area, 1, gamma=1.4), (0., 0., 0.))
        near = [restriction(hot, (200000*(.5282817877+d), 500, .8), 1e-4, 1, gamma=1.4)[0]
                for d in (-1e-6, 1e-6)]
        self.assertLess(abs(near[0]-near[1])/near[0], 1e-5)

    def test_connected_isolated_tanks(self):
        # Deux volumes fixes; référence = inventaires initiaux, pas le RHS.
        initial = [.002, .002*820*350, .0015, .001, .001*820*300, .0001]
        def rhs(t, y):
            nodes = [(y[3*i+1]*.35/.001, y[3*i+1]/(820*y[3*i]), y[3*i+2]/y[3*i]) for i in range(2)]
            dy = [0.]*6
            add_transport(dy, 0, 1, restriction(*nodes, 1e-5, .7))
            for i in range(3):
                self.assertEqual(dy[i], -dy[i+3])
            return dy
        y = initial[:]
        for i in range(1000):
            y = rk4(i*1e-5, y, 1e-5, rhs)
        for k in range(3):
            expected = initial[k]+initial[k+3]
            self.assertLess(abs((y[k]+y[k+3]-expected)/expected), 1e-7)

    def test_closed_adiabatic_compression(self):
        gamma, v1, v2, p1 = 1.35, .001, .0002, 100000
        duration = .01
        dv = (v2-v1)/duration
        def rhs(t, y):
            pressure = (gamma-1)*y[0]/(v1+dv*t)
            return [-pressure*dv, pressure*dv]
        y = [p1*v1/(gamma-1), 0.]
        for i in range(1000):
            y = rk4(i*duration/1000, y, duration/1000, rhs)
        p2 = p1*(v1/v2)**gamma
        w = (p1*v1-p2*v2)/(gamma-1)
        self.assertLess(abs(((gamma-1)*y[0]/v2)/p2-1), 1e-4)
        self.assertLess(abs(y[1]-w)/max(abs(w), 1), 1e-4)

    def test_prescribed_heat_and_analytic_marker(self):
        mass, fs, qf, u0 = .001, .0004, 800000, 246.
        visited = []
        def project(t, y):
            visited.append(t)
            return [y[0], fs*(1-burn_fraction(350+t*18000, 350)), mass]
        def rhs(t, y):
            self.assertGreaterEqual(y[1], 0)
            self.assertEqual(y[1], fs*(1-burn_fraction(350+t*18000, 350)))
            return [qf*fs*burn_rate(350+t*18000, 350)*18000, 0., 0.]
        y = [u0, fs, mass]
        dt = 40/18000/80
        for i in range(80):
            y = rk4(i*dt, y, dt, rhs, project)
        self.assertLess(abs((y[0]-u0)/(qf*fs)-1), 1e-5)
        self.assertLess(abs(y[1])/mass, 1e-7)
        self.assertEqual(y[2], mass)
        self.assertEqual(len(visited), 5*80)

    def test_homogeneous_marker_analytic_reference(self):
        mass, q = .01, .001
        def rhs(t, y):
            dy = [0., 0., 0.]
            add_transport(dy, None, 0, (q, 0., q))
            add_transport(dy, 0, None, (q, 0., q*y[2]/y[0]))
            return dy
        y = [mass, 1., 0.]
        for i in range(100):
            y = rk4(i*.1, y, .1, rhs)
        self.assertLess(abs(y[2]/mass-.6321205588), 1e-4)


if __name__ == '__main__':
    unittest.main()
