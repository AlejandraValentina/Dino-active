import unittest
from dev_orchestrator.p1_r1_study import half_crossing, estimators


class ContactObservableTests(unittest.TestCase):
    def test_linear_crossing_both_directions(self):
        self.assertEqual(half_crossing([0., 1.], [.9, .1]), (.5, 'unique'))
        self.assertEqual(half_crossing([0., 1.], [.1, .9]), (.5, 'unique'))

    def test_exact_center_not_double_counted(self):
        self.assertEqual(half_crossing([0., 1., 2.], [1., .5, 0.]), (1., 'unique'))

    def test_ambiguous_and_absent(self):
        for ys in ([0., 1., 0.], [1., 1., 1.], [.5, .5, 0.]):
            self.assertIsNone(half_crossing([0., 1., 2.], ys)[0])

    def test_invalid_profile(self):
        for xs, ys in (([1., 0.], [1., 0.]), ([0., 1.], [float('nan'), 0.])):
            with self.assertRaises(ValueError):
                half_crossing(xs, ys)

    def test_no_exact_location_oracle_for_b_c_d(self):
        xs = [.45, .47, .49, .51, .53, .55]
        ws = [(1+y, 1., 1., y) for y in [1., 1., .8, .2, 0., 0.]]
        a, b = estimators(xs, ws, .48), estimators(xs, ws, .52)
        for k in 'BCD':
            self.assertEqual(a[k], b[k])
        self.assertAlmostEqual(a['B'], .5)
        self.assertAlmostEqual(a['C'], .5)
        self.assertTrue(a['local_monotone'])

    def test_nonmonotone_not_hidden(self):
        xs = [.47, .49, .51, .53]
        ws = [(1., 1., 1., y) for y in [.8, .9, .1, 0.]]
        self.assertFalse(estimators(xs, ws, .5)['local_monotone'])
