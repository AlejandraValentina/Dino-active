"""Controles focalizados de diagnóstico y ejecución; no repiten la serie."""
import csv
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from motorsim.prototype import Monitor, memory_mib, write_samples
from motorsim.simulation import (Model, SIZE, HEAT, BURN, InvalidStage, StopCalculation,
    restriction, independent_increment, audit, balances_ok, convergence,
    run_resolution, sensitivity, sample, burn_fraction)


class ProtocolControls(unittest.TestCase):
    def test_no_qt_dependency(self):
        result = subprocess.run([sys.executable, '-c',
            'import motorsim.prototype,sys; assert not any(k.startswith("PySide6") for k in sys.modules)'],
            capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_initial_reverse_transfer_and_single_evaluation(self):
        model = Model()
        with patch('motorsim.simulation.restriction', wraps=restriction) as flow:
            _, snapshot = model.evaluate(180, model.initial_state())
        self.assertEqual(flow.call_count, 6)
        for q, h, fresh in snapshot[2][2:4]:
            self.assertLess(q, 0)
            self.assertAlmostEqual(h/q, 1107*700)
            self.assertEqual(fresh, 0)
        self.assertEqual(snapshot[2][1], (0., 0., 0.))

    def test_analytic_fresh_each_heat_stage_and_no_clipping(self):
        model = Model()
        y = model.initial_state()
        fs = y[6]/2
        for angle in (350, 350.125, 360, 375, 389.999, 390):
            z = model.analytic(angle, y, (350, fs))
            self.assertEqual(z[8], fs*(1-burn_fraction(angle, 350)))
            dy, state = model.evaluate(angle, z, (350, fs))
            self.assertEqual(dy[8], 0)
            self.assertAlmostEqual(dy[HEAT], 800000*dy[BURN])
            self.assertTrue(all(q == (0., 0., 0.) for q in state[2][2:5]))
        y[8] = -1e-20
        with self.assertRaisesRegex(InvalidStage, 'F fuera'):
            model.evaluate(180, y)
        self.assertEqual(y[8], -1e-20)
        y = model.initial_state()
        y[7] *= 10
        with self.assertRaisesRegex(StopCalculation, 'fuera del dominio'):
            model.evaluate(180, y)

    def test_independent_quadrature_and_inventory_fault_detection(self):
        # Compresión ficticia de un paso: p_media=150 kPa, Delta V=-0.1 L,
        # por tanto W=-15 J y Delta U=+15 J. Sin usar RHS ni sus acumuladores.
        nodes1, nodes2 = [(100000, 300, .2)]*4, [(100000, 300, .2)]*4
        nodes2[2] = (200000, 300, .2)
        volumes1, volumes2 = [.001]*4, [.001]*4
        volumes2[2] = .0009
        flows = [(0., 0., 0.)]*6
        ledger = independent_increment((nodes1, volumes1, flows), (nodes2, volumes2, flows), .001, 0, 0)
        self.assertAlmostEqual(ledger[32], -15.)
        start = [.001, 100., .0002]*4
        end = start.copy()
        end[7] += 15
        clean = audit(start, end, ledger)
        self.assertTrue(balances_ok(clean, clean))
        end[7] += 1
        faulty = audit(start, end, ledger)
        self.assertFalse(balances_ok(clean, faulty))
        self.assertGreater(faulty['global']['normalized_m_u_f'][1], .001)

    def test_monitor_caps_progress_and_cancellation(self):
        now = [0.]
        lines = []
        monitor = Monitor(.5, 0., clock=lambda: now[0], memory=lambda: 20,
                          emit=lambda s, **kw: lines.append(s))
        now[0] = .5
        monitor(1, 200, 100)
        self.assertEqual(len(lines), 1)
        now[0] = 60
        with self.assertRaisesRegex(StopCalculation, '60 segundos'):
            monitor(1, 200, 100)
        series = Monitor(.5, -180, clock=lambda: 0., memory=lambda: 20)
        with self.assertRaisesRegex(StopCalculation, '180 segundos'):
            series(1, 180, 0)
        ram = Monitor(.5, 0., clock=lambda: 0., memory=lambda: 513)
        with self.assertRaisesRegex(StopCalculation, '512 MiB'):
            ram(1, 180, 0)
        self.assertGreater(memory_mib(), 0)

    def test_actual_cancellation_latency_and_cold_start(self):
        signal = threading.Event()
        requested = []
        def cancel():
            requested.append(time.monotonic())
            signal.set()
        timer = threading.Timer(.05, cancel)
        monitor = Monitor(.125, time.monotonic(), signal.is_set, emit=lambda *a, **k: None)
        timer.start()
        try:
            result = run_resolution(.125, monitor)
        finally:
            timer.cancel()
            timer.join()
        self.assertEqual(result['stop'], 'cancelación solicitada')
        self.assertFalse(result['converged'])
        self.assertLess(time.monotonic()-requested[0], 1.)
        self.assertIsNotNone(result['partial'])
        cancelled = Monitor(.5, time.monotonic(), lambda: True)
        untouched = run_resolution(.5, cancelled)
        self.assertEqual(untouched['partial']['state'], Model().initial_state()[:12])

    def test_output_contains_states_signed_flows_and_pv(self):
        model = Model()
        y = model.initial_state()
        row = sample(180, y, model.evaluate(180, y)[1])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'samples.csv'
            write_samples(path, [[row]])
            with path.open(encoding='utf-8') as stream:
                saved = list(csv.DictReader(stream))[0]
        self.assertEqual(saved['link2_direction'], 'reverse')
        self.assertAlmostEqual(float(saved['C_p_Pa']), 140000)
        self.assertAlmostEqual(float(saved['C_V_m3']), 46.656*3.141592653589793*1e-6)
        self.assertEqual(float(saved['C_Y']), 0)

    def test_convergence_requires_all_states_heat_and_balances(self):
        record = dict(state=[.001, 100., .0005]*4, Y=[.5]*4, W_C_J=-2,
                      p_max_Pa=200000, balances_passed=True, F_s_kg=.0001, Q_J=80)
        self.assertTrue(convergence(record, record, [100000]*721, [100000]*721)['passed'])
        for change in ({'F_s_kg': 0}, {'Q_J': 0}, {'balances_passed': False}, {'Y': [.6]*4}):
            self.assertFalse(convergence(record, record | change, [100000]*721, [100000]*721)['passed'])
        self.assertFalse(sensitivity([{'converged': False}]*3)['passed'])

    def test_sensitivity_does_not_require_trend_below_approved_floors(self):
        runs = []
        for work, mass in ((10., .0001), (10.+1e-12, .0001+1e-15), (10.+3e-12, .0001+3e-15)):
            record = dict(W_C_J=work, p_max_Pa=200000, Y=[.5]*4,
                          net_link_mass_kg=[mass]*6)
            rows = [{'p_T_Y': [(100000, 300, .5)]*4}]*721
            runs.append(dict(converged=True, cycles=[record], last_two_cycles=[rows]))
        self.assertTrue(sensitivity(runs)['passed'])


if __name__ == '__main__':
    unittest.main()
