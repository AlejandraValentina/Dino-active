"""Cuadratura independiente: referencias prescritas, sin ejecutar el motor."""
import unittest
from unittest.mock import patch

from motorsim import simulation as sim

from motorsim.simulation import SIZE, independent_increment, audit, balances_ok


def prescribed_snapshot(t, flow):
    return ([(100000., 300., .25)]*4, [.001]*4,
            [flow(t)] + [(0., 0., 0.)]*5)


def integrate_prescribed(nodes, flow):
    ledger = [0.]*SIZE
    for left, right in zip(nodes, nodes[1:]):
        inc = independent_increment(prescribed_snapshot(left, flow),
                                    prescribed_snapshot(right, flow), right-left, 0., 0.)
        ledger = [x+y for x, y in zip(ledger, inc)]
    return ledger


class IndependentQuadratureTests(unittest.TestCase):
    def test_constant_flow_nonuniform_intervals(self):
        ledger = integrate_prescribed([0., .017, .13, .31, 1.], lambda t: (.002, 600., .0005))
        for actual, expected in zip(ledger[12:15], (.002, 600., .0005)):
            self.assertAlmostEqual(actual, expected, places=12)

    def test_linear_sign_change_and_different_donors(self):
        # q=2t-1, cambio en t=.5. Integral q=0; cada semitriángulo=.25.
        # h/Y negativos = 500/.2, positivos = 300/.8.
        def flow(t):
            q = 2*t-1
            h, fresh = (500., .2) if q < 0 else (300., .8)
            return q, q*h, q*fresh
        ledger = integrate_prescribed([0., .03, .2, .5, .57, .9, 1.], flow)
        for actual, expected in zip(ledger[12:15], (0., -50., .15)):
            self.assertAlmostEqual(actual, expected, places=12)
        self.assertAlmostEqual(ledger[36], .5)
        self.assertAlmostEqual(ledger[42], 200.)

    def test_quadratic_refinement_has_known_trapezoid_error(self):
        # Integral t² dt de 0 a 1 = 1/3; error del trapecio uniforme = h²/6.
        for n in (4, 8):
            ledger = integrate_prescribed([i/n for i in range(n+1)], lambda t: (t*t, 0., 0.))
            self.assertAlmostEqual(ledger[12]-1/3, 1/(6*n*n), places=14)

    def test_endpoints_no_duplicate_time_and_seconds_conversion(self):
        angles = [180., 180.125, 180.43, 180.5, 181.]
        times = [(a-180)/18000 for a in angles]
        ledger = integrate_prescribed(times, lambda t: (.003, 900., .001))
        self.assertAlmostEqual(ledger[12], .003/18000, places=18)
        self.assertAlmostEqual(ledger[13], 900./18000, places=14)
        # Un extremo repetido tiene dt=0, no otro intervalo de duración positiva.
        duplicate = integrate_prescribed(times[:3]+[times[2]]+times[3:], lambda t: (.003, 900., .001))
        self.assertEqual(ledger, duplicate)

    def test_wrong_transport_is_not_hidden_by_independent_audit(self):
        ledger = integrate_prescribed([0., .1, .23, 1.], lambda t: (.001, 100., .00025))
        start = [.002, 500., .0005]*4
        end = start.copy()
        end[0] += .001
        end[1] += 100.
        end[2] += .00025
        correct = audit(start, end, ledger)
        self.assertTrue(balances_ok(correct, correct))
        for component in (12, 13, 14):
            wrong = ledger.copy()
            wrong[component] *= -1
            self.assertFalse(balances_ok(correct, audit(start, end, wrong)))

    def test_rejected_attempt_does_not_enter_either_accumulator(self):
        model = sim.Model()
        rk = sim.rk4
        candidates = []
        increments = []
        def forced_rejection(t, state, dt, rhs, project):
            candidate = rk(t, state, dt, rhs, project)
            candidates.append(candidate)
            if len(candidates) == 1:
                raise sim.InvalidStage('rechazo inducido después del cálculo, antes de aceptar')
            return candidate
        def capture(left, right, dt, q, b):
            inc = independent_increment(left, right, dt, q, b)
            increments.append((dt, inc))
            return inc
        def stop_after_accepted(cycle, angle, count, completed=False):
            if angle > 180:
                raise sim.StopCalculation('una aceptación para probar descarte')
        with patch.object(sim, 'rk4', forced_rejection), patch.object(sim, 'independent_increment', capture):
            result = sim.run_resolution(.5, stop_after_accepted, model)
        expected = rk(0., model.initial_state(), .25/18000,
                      lambda t, y: model.evaluate(180+t*18000, y)[0])
        self.assertEqual(result['accepted_steps'], 1)
        self.assertEqual(result['rejected_steps'], 1)
        self.assertEqual(candidates[-1], expected)  # Incluye libro del integrador.
        self.assertEqual(result['partial']['state'], expected[:12])
        self.assertEqual(len(increments), 1)        # Auditoría solo del aceptado.
        self.assertEqual(increments[0][0], .25/18000)


if __name__ == '__main__':
    unittest.main()
