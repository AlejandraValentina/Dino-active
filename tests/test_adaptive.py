"""Controles del controlador y regresión acotada de E, 300–300.5°."""
from dataclasses import asdict
import math
import time
import threading
import unittest
from unittest.mock import patch

from motorsim.adaptive import PROFILES, Stepper, error_norm, step_factor, targets, run_adaptive
from motorsim.simulation import Model, SIZE, StopCalculation, rk4, independent_increment, BURN
from motorsim.prototype import Monitor, memory_mib

# Estado sintético exacto de la traza de 783970d, no un proyecto de la usuaria.
SEED = [3.4862426380387404e-05, 8.62974636055665, 3.476407127646083e-05,
        0.00031223643140526337, 78.94597569501214, 0.0003038668806492507,
        7.791017242842931e-05, 37.7620978228464, 4.6956125132095125e-05,
        6.860256320107736e-05, 29.92391776725271, 3.0234053531305144e-05]


def run_interval(profile, reverse=False, model=None):
    model = model or Model()
    state = SEED.copy()+[0.]*(SIZE-12)
    if reverse:
        # Prueba distinta y explícita: entrada físicamente permitida, no ajuste del caso.
        state[10] *= 99986/((model.case.gamma-1)*state[10]/model.geometry(10740.)[0][3])
    initial = state.copy()
    rows = []
    stepper = Stepper(model, profile, rows.append)
    started = time.perf_counter()
    monitor = Monitor(profile.max_step_deg, time.monotonic(), emit=lambda *a, **k: None)
    angle, end = 10740., 10740.5
    snapshot = stepper.evaluate(angle, state, None)[1]
    first_snapshot = snapshot
    independent = [0.]*SIZE
    stop = 'intervalo completado'
    try:
        while angle < end:
            pair = stepper.advance(angle, state, end, None,
                                   lambda: monitor(1, angle, stepper.rhs_count))
            for new_angle, candidate, new_snapshot in pair:
                inc = independent_increment(snapshot, new_snapshot, (new_angle-angle)/18000, 0., 0.)
                independent = [a+b for a, b in zip(independent, inc)]
                state, angle, snapshot = candidate, new_angle, new_snapshot
    except StopCalculation as exc:
        stop = str(exc)
    return dict(profile=asdict(profile), stop=stop, completed=angle == end,
        seconds=time.perf_counter()-started, peak_MiB=memory_mib(),
        initial_state=initial[:12], final_state=state[:12],
        initial_E_p_T_Y=first_snapshot[0][3], final_E_p_T_Y=snapshot[0][3],
        delta_Y_E=snapshot[0][3][2]-first_snapshot[0][3][2],
        outgoing_mass_E_kg=(state[41]+state[27])/2,
        incoming_mass_E_kg=(state[41]-state[27])/2,
        integrator_link_E=state[27:30], independent_link_E=independent[27:30],
        attempts_log=rows, **stepper.statistics())


class AdaptiveTests(unittest.TestCase):
    def test_normalization_all_twelve_components_and_nonfinite(self):
        start = [1e-4, 100., 5e-5]*4
        for j in range(12):
            fine, full = start.copy(), start.copy()
            full[j] += 1e-7 if j % 3 != 1 else .1
            e, label = error_norm(start, full, fine, PROFILES[0])
            atol = 1e-6 if j % 3 == 1 else 1e-12
            self.assertAlmostEqual(e, abs(full[j]-fine[j])/15/(atol+1e-6*abs(start[j])))
            self.assertEqual(label, f'{("I", "K", "C", "E")[j//3]}.{("m", "U", "F")[j%3]}')
        full = start.copy()
        full[11] = math.nan
        self.assertEqual(error_norm(start, full, start, PROFILES[0])[0], math.inf)

    def test_controller_bounds_and_zero(self):
        self.assertEqual(step_factor(0), 2.)
        self.assertEqual(step_factor(math.inf), .2)
        self.assertEqual(step_factor(math.nan), .2)
        self.assertEqual(step_factor(1), .9)
        for e in (.001, .1, 1., 10., 1e12):
            self.assertGreaterEqual(step_factor(e), .2)
            self.assertLessEqual(step_factor(e), 2.)
            self.assertLess(step_factor(e, rejected=True), 1.)

    def test_local_error_rejects_positive_states_and_keeps_only_halves(self):
        model = Model()
        y = SEED.copy()+[0.]*(SIZE-12)
        original = y.copy()
        log = []
        stepper = Stepper(model, PROFILES[0], log.append)
        pair = stepper.advance(10740., y, 10740.5, None)
        self.assertGreater(stepper.rejections['local_error'], 0)
        self.assertEqual(y, original)
        h = log[-1]['proposed_deg']/18000
        expected_mid = rk4(0., original.copy(), h/2,
                          lambda t, s: model.evaluate(10740+t*18000, s)[0])
        expected_end = rk4(h/2, expected_mid, h/2,
                          lambda t, s: model.evaluate(10740+t*18000, s)[0])
        self.assertEqual(pair[0][1], expected_mid)
        self.assertEqual(pair[1][1], expected_end)  # Incluye todos los acumuladores.
        self.assertEqual(stepper.stage_evaluations, 12*stepper.attempts)
        self.assertEqual(stepper.rhs_count, 15*stepper.attempts)
        self.assertEqual(stepper.accepted, 2)

    def test_minimum_applies_to_each_half_step(self):
        model = Model()
        stepper = Stepper(model, PROFILES[0])
        with self.assertRaisesRegex(StopCalculation, 'medio paso'):
            stepper.advance(300., model.initial_state(), 300.0015, None)
        self.assertEqual(stepper.rhs_count, 0)

    def test_all_derivative_evaluations_are_counted_and_limited(self):
        model = Model()
        state = SEED.copy()+[0.]*(SIZE-12)
        stepper = Stepper(model, PROFILES[0])
        with patch.object(model, 'evaluate', wraps=model.evaluate) as observed:
            stepper.advance(10740., state, 10740.5, None)
            self.assertEqual(observed.call_count, stepper.rhs_count)
            self.assertEqual(stepper.rhs_count, stepper.stage_evaluations+stepper.endpoint_evaluations)
            stepper.rhs_count = 1_999_999
            before = observed.call_count
            stepper.evaluate(10740., state, None)
            with self.assertRaisesRegex(StopCalculation, '2000000'):
                stepper.evaluate(10740., state, None)
            self.assertEqual(observed.call_count, before+1)

    def test_event_alignment_and_heat_branches(self):
        model = Model()
        events = targets(180., 540., model.events)
        for e in (270., 350., 360., 390., 540.):
            self.assertIn(e, events)
        y = SEED.copy()+[0.]*(SIZE-12)
        fs = y[8]
        stepper = Stepper(model, PROFILES[0])
        pair = stepper.advance(350., y, 350.1, (350., fs))
        self.assertLessEqual(pair[-1][0], 350.1)
        self.assertEqual(y[BURN], 0.)
        for angle, state, snap in pair:
            self.assertAlmostEqual(state[8]+state[BURN], fs, places=18)
        self.assertEqual(stepper.stage_evaluations, 12*stepper.attempts)
        self.assertEqual(stepper.rhs_count, 15*stepper.attempts)

    def test_recorded_interval_improves_before_formal_series(self):
        for profile in PROFILES:
            with self.subTest(profile=profile.name):
                result = run_interval(profile)
                self.assertTrue(result['completed'], result['stop'])
                self.assertLess(abs(result['delta_Y_E']), .00015287984966599888)
                self.assertGreaterEqual(result['actual_substep_deg']['minimum'], .001)

    def test_physical_return_is_not_blocked(self):
        result = run_interval(PROFILES[0], reverse=True)
        self.assertTrue(result['completed'], result['stop'])
        self.assertGreater(result['incoming_mass_E_kg'], 0)
        self.assertLess(result['integrator_link_E'][0], 0)

    def test_runner_audits_both_accepted_halves(self):
        def stop_after_pair(cycle, angle, count, completed=False):
            if angle > 180:
                raise StopCalculation('par comprobado')
        with patch('motorsim.adaptive.independent_increment', wraps=independent_increment) as audited:
            result = run_adaptive(PROFILES[0], stop_after_pair)
        self.assertEqual(result['accepted_steps'], 2)
        self.assertEqual(audited.call_count, 2)
        self.assertEqual(audited.call_args_list[0].args[1], audited.call_args_list[1].args[0])
        self.assertEqual(result['stop'], 'par comprobado')
        self.assertFalse(result['converged'])

    def test_adaptive_cancellation_latency(self):
        cancelled = threading.Event()
        request_time = []
        def cancel():
            request_time.append(time.monotonic())
            cancelled.set()
        timer = threading.Timer(.05, cancel)
        monitor = Monitor(.5, time.monotonic(), cancelled.is_set, emit=lambda *a, **k: None)
        timer.start()
        try:
            result = run_adaptive(PROFILES[0], monitor)
        finally:
            timer.cancel()
            timer.join()
        self.assertEqual(result['stop'], 'cancelación solicitada')
        self.assertLess(time.monotonic()-request_time[0], 1.)


if __name__ == '__main__':
    unittest.main()
