import unittest
from motorsim.gas1d.contact import density_contact


class HydroContactTests(unittest.TestCase):
    def test_pure_contact_and_translation(self):
        for offset in (0., 17.):
            d = density_contact([offset+x for x in (0., 1., 2., 3.)],
                                [(1., 2., 1.), (1., 2., 1.), (2., 2., 1.), (2., 2., 1.)], 1.4)
            self.assertEqual(d['status'], 'UNIQUE')
            self.assertEqual(d['position'], offset+1.5)

    def test_no_tracer_argument(self):
        with self.assertRaises(ValueError):
            density_contact([0., 1.], [(1., 0., 1., 0.), (2., 0., 1., 1.)], 1.4)

    def test_uniform_absent_and_ties_ambiguous(self):
        self.assertEqual(density_contact([0., 1.], [(1., 0., 1.)]*2, 1.4)['status'], 'NO_CONTACT')
        self.assertEqual(density_contact([0., 1., 2.], [(1., 0., 1.), (2., 0., 1.), (1., 0., 1.)], 1.4)['status'], 'AMBIGUOUS')

    def test_acoustic_jumps_not_contact(self):
        for sign in (-1., 1.):
            # Small acoustic compression/expansion; pressure-density relation dominates.
            d = density_contact([0., 1.], [(1., 0., 1.), (1.+sign*.001, sign*.001, 1.+sign*.0014)], 1.4)
            self.assertEqual(d['status'], 'NO_CONTACT')

    def test_normal_shock_not_contact(self):
        # Exact stationary normal shock, gamma1.4, upstream Mach2.
        from math import sqrt
        u = 2*sqrt(1.4)
        ratio = 2.4*4/(.4*4+2)
        d = density_contact([0., 1.], [(1., u, 1.), (ratio, u/ratio, 4.5)], 1.4)
        self.assertEqual(d['status'], 'NO_CONTACT')

    def test_reversal_and_galilean_invariance(self):
        ws = [(1., 0., 1.), (1., 0., 1.), (2., 0., 1.), (2., 0., 1.)]
        for rows in (ws, ws[::-1], [(r, u+25, p) for r,u,p in ws]):
            self.assertEqual(density_contact([0., 1., 2., 3.], rows, 1.4)['position'], 1.5)

    def test_invalid(self):
        for xs, rows in (([0., 0.], [(1., 0., 1.)]*2), ([0., 1.], [(0., 0., 1.), (1., 0., 1.)])):
            with self.assertRaises(ValueError):
                density_contact(xs, rows, 1.4)
