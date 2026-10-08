"""Referencias locales para la variante exterior, sin ejecutar series formales."""
import math
from pathlib import Path
import tempfile
import unittest

from motorsim.simulation import Model, regularized_restriction, restriction
from motorsim.adaptive import PROFILES
from motorsim.regularized_trial import execute
from test_adaptive import SEED, run_interval


class RegularizationTests(unittest.TestCase):
    def test_zero_sign_donor_and_transport(self):
        for band in (100, 50):
            for dp in (0., 1e-7, -1e-7, 25., -25., 200., -200.):
                left, right = (100000+dp, 300., .9), (100000., 600., .2)
                q, h, f = regularized_restriction(left, right, .001, .7, band)
                self.assertEqual(math.copysign(1, q), math.copysign(1, dp))
                if dp:
                    donor = left if dp > 0 else right
                    self.assertAlmostEqual(h/q, 1.35*287/.35*donor[1])
                    self.assertAlmostEqual(f/q, donor[2])
                else:
                    self.assertEqual((q, h, f), (0., 0., 0.))
                self.assertEqual(regularized_restriction(left, right, 0, .7, band), (0., 0., 0.))

    def test_finite_one_sided_slopes_and_band_join(self):
        for band in (100, 50):
            def q(dp):
                return regularized_restriction((100000+dp, 300., .9),
                                              (100000., 600., .2), .001, .7, band)[0]
            for direction, temperature in ((1, 300.), (-1, 600.)):
                # Analytic one-sided slope from the small pressure-drop limit.
                expected = .7*.001*math.sqrt(2*100000/(287*temperature))*1.5/math.sqrt(band)
                for eps in (1e-2, 1e-4, 1e-6):
                    actual_dp = (100000+direction*eps)-100000
                    self.assertAlmostEqual(q(direction*eps)/actual_dp/expected, 1., delta=2e-4)
                edge = direction*band
                original = restriction((100000+edge, 300., .9), (100000., 600., .2), .001, .7)[0]
                self.assertEqual(q(edge), original)
                self.assertAlmostEqual(q(edge*(1-1e-7))/original, 1., delta=1e-6)
                left_slope = (q(edge)-q(edge-.001))/.001
                right_slope = (q(edge+.001)-q(edge))/.001
                self.assertAlmostEqual(left_slope/right_slope, 1., delta=2e-4)
                for dp in (direction*band, direction*200, direction*100000):
                    # Positive absolute pressures in both endpoints.
                    l, r = (200000+dp, 300., .9), (200000., 600., .2)
                    self.assertEqual(regularized_restriction(l, r, .001, .7, band),
                                     restriction(l, r, .001, .7))

    def test_only_external_links_change_and_auditor_sees_them(self):
        original = Model()
        state = SEED.copy()+[0.]*36
        original_flows = original.evaluate(10740., state)[1][2]
        for band in (100, 50):
            candidate = Model(external_band_pa=band)
            self.assertEqual(candidate.initial_state(), original.initial_state())
            dy, snapshot = candidate.evaluate(10740., state)
            flows = snapshot[2]
            self.assertEqual(flows[1:5], original_flows[1:5])
            self.assertNotEqual(flows[5], original_flows[5])
            self.assertEqual(dy[27:30], list(flows[5]))

    def test_local_discharge_and_physical_fill(self):
        for band in (100, 50):
            for reverse in (False, True):
                result = run_interval(PROFILES[0], reverse, Model(external_band_pa=band))
                self.assertTrue(result['completed'], result['stop'])
                pi, _, yi = result['initial_E_p_T_Y']
                pf, _, yf = result['final_E_p_T_Y']
                self.assertLess(abs(pf-100000), abs(pi-100000))
                if reverse:
                    self.assertGreater(result['incoming_mass_E_kg'], 0)
                    self.assertLess(yf, yi)
                else:
                    self.assertLess(abs(result['delta_Y_E']), 1e-8)
                    self.assertGreater(result['outgoing_mass_E_kg'], 0)

    def test_failed_A_stops_series_and_omits_band_comparison(self):
        calls = []
        def failed(profile, monitor, model, trace):
            calls.append((profile.name, model.external_band_pa))
            return dict(profile={'name': profile.name}, converged=False, cycles=[],
                        last_two_cycles=[], partial=None, stop='test budget')
        with tempfile.TemporaryDirectory() as folder:
            result = execute(Path(folder)/'new', runner=failed)
        self.assertEqual(calls, [('A', 100)])
        self.assertEqual(result['profiles_omitted'], ['B', 'C'])
        self.assertFalse(result['comparison_50_Pa_executed'])


if __name__ == '__main__':
    unittest.main()
