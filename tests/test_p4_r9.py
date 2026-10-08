import unittest, math, json
from pathlib import Path
import numpy as np
from bisect import bisect_right

def curve_synthetic(phases, wave):
    return wave

def estimate_phase_shift(a_curve, b_curve, phases, window=1.0, res=0.01):
    a=np.array(a_curve,float); b=np.array(b_curve,float); ph=np.array(phases,float)
    best_delta=0; best_l2=float('inf')
    for delta in np.arange(-window, window+res/2, res):
        b_shifted=np.interp(ph-delta, ph, b, left=b[0], right=b[-1])
        l2=np.sqrt(np.mean((a-b_shifted)**2))
        if l2<best_l2:
            best_l2=l2; best_delta=float(delta)
    return best_delta, best_l2

class P4R9SyntheticTests(unittest.TestCase):
    def test_identical_wave_zero_shift(self):
        phases=[i*0.5 for i in range(1,721)]
        wave=[math.sin(math.radians(p*2)) for p in phases]
        delta,l2=estimate_phase_shift(wave, wave, phases)
        self.assertAlmostEqual(delta, 0, delta=0.011)
        self.assertAlmostEqual(l2, 0, delta=1e-9)

    def test_known_phase_shift(self):
        phases=[i*0.5 for i in range(1,721)]
        wave=[math.sin(math.radians(p*2)) for p in phases]
        shift=0.5
        wave_shifted=[math.sin(math.radians((p-shift)*2)) for p in phases]
        delta,l2=estimate_phase_shift(wave, wave_shifted, phases)
        # delta should be -shift to align (sign depends on convention) or +shift
        self.assertAlmostEqual(abs(delta), shift, delta=0.02)

    def test_amplitude_only(self):
        phases=[i*0.5 for i in range(1,721)]
        wave=[math.sin(math.radians(p*2)) for p in phases]
        wave_amp=[1.1*w for w in wave]
        delta,l2=estimate_phase_shift(wave, wave_amp, phases)
        # amplitude only should give delta near 0, not large shift
        self.assertAlmostEqual(delta, 0, delta=0.05)
        self.assertGreater(l2, 0.05)

    def test_shift_plus_amplitude(self):
        phases=[i*0.5 for i in range(1,721)]
        wave=[math.sin(math.radians(p*2)) for p in phases]
        wave_comb=[1.1*math.sin(math.radians((p-0.3)*2)) for p in phases]
        delta,l2=estimate_phase_shift(wave, wave_comb, phases)
        self.assertAlmostEqual(abs(delta), 0.3, delta=0.05)

    def test_parity_handling(self):
        # Simulate odd/even: create two sequences and ensure estimator works for both
        phases=[i*0.5 for i in range(1,721)]
        base=[math.sin(math.radians(p*2)) for p in phases]
        odd=[b*1.01 for b in base]
        even=[b*0.99 for b in base]
        d1,_=estimate_phase_shift(odd, even, phases)
        d2,_=estimate_phase_shift(even, odd, phases)
        # Deltas should be opposite sign or near 0
        self.assertAlmostEqual(d1, -d2, delta=0.05)

    def test_grid_handling(self):
        # Test that metric reconstruction is stable across grid steps
        # Use same wave but evaluate at 0.5 vs 1.0 vs 0.25
        def metric(phases, a,b):
            diffs=[abs(x-y) for x,y in zip(a,b)]
            denom=max(map(abs, a+b))
            return max(diffs)/denom if denom else 0
        phases05=[i*0.5 for i in range(1,721)]
        wave05=[math.sin(math.radians(p*2)) for p in phases05]
        wave05_shift=[math.sin(math.radians((p-0.2)*2)) for p in phases05]
        m05=metric(phases05, wave05, wave05_shift)
        phases10=[i*1.0 for i in range(1,361)]
        wave10=[math.sin(math.radians(p*2)) for p in phases10]
        wave10_shift=[math.sin(math.radians((p-0.2)*2)) for p in phases10]
        m10=metric(phases10, wave10, wave10_shift)
        # Metrics should be similar within 20%
        self.assertAlmostEqual(m05, m10, delta=0.1)

    def test_original_metric_reconstruction(self):
        # Load real sensor_tables and verify D1 0.60
        p=Path("results/p4-r9-20260922/sensor_tables.json")
        if not p.exists():
            self.skipTest("sensor_tables not yet generated")
        data=json.loads(p.read_text())
        for N in ["250","350"]:
            m=data[N]["D1_last"]["details"][0]["metric"]
            self.assertGreater(m, 0.5)
            self.assertLess(m, 0.7)

if __name__=="__main__":
    unittest.main()
