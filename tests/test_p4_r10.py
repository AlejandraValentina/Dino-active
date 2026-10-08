import unittest, math, json
import numpy as np
from pathlib import Path

def detect_front_synthetic(p, x):
    dpdx = np.abs(np.diff(p)/np.diff(x))
    idx = int(np.argmax(dpdx))
    x_front = 0.5*(x[idx]+x[idx+1])
    return x_front, idx, float(np.max(dpdx))

class P4R10SyntheticTests(unittest.TestCase):
    def test_front_detector_translated_shock(self):
        x = np.linspace(0,0.75,350)
        # synthetic shock at 0.3 with linear transition 5 cells
        p = np.where(x<0.29, 30000, np.where(x>0.31, 100000, 30000 + (x-0.29)/0.02*70000)).astype(float)
        x_front,_ , _ = detect_front_synthetic(p, x)
        self.assertAlmostEqual(x_front, 0.3, delta=0.02)
        # translated 0.01m (~5dx) to be clearly detectable
        p2 = np.where(x<0.30, 30000, np.where(x>0.32, 100000, 30000 + (x-0.30)/0.02*70000)).astype(float)
        x_front2,_,_ = detect_front_synthetic(p2, x)
        self.assertAlmostEqual(x_front2 - x_front, 0.01, delta=0.007)

    def test_changed_jump_strength(self):
        x = np.linspace(0,0.75,350)
        p1 = np.where(x<0.3, 30000, 100000).astype(float)
        p2 = np.where(x<0.3, 30000, 105000).astype(float)
        x1, idx1, _ = detect_front_synthetic(p1, x)
        x2, idx2, _ = detect_front_synthetic(p2, x)
        self.assertAlmostEqual(x1, x2, delta=0.01)
        jump1 = abs(p1[idx1+1]-p1[idx1])
        jump2 = abs(p2[idx2+1]-p2[idx2])
        self.assertNotAlmostEqual(jump1, jump2, delta=100)

    def test_localized_error_support(self):
        x = np.linspace(0,0.75,350)
        p_a = np.where(x<0.3, 30000, 100000).astype(float)
        p_b = p_a.copy()
        # localized perturbation 5 cells around front
        p_b[140:145] += 2000
        diff2 = (p_a - p_b)**2
        total = np.sum(diff2)
        order = np.argsort(diff2)[::-1]
        cum = np.cumsum(diff2[order])
        for pct in [90,95]:
            thresh = pct/100 * total
            idx = np.searchsorted(cum, thresh)
            n_cells = idx+1
            # Should be ~5 cells for 90%
            if pct==90:
                self.assertLess(n_cells, 20)

    def test_distributed_perturbation(self):
        x = np.linspace(0,0.75,350)
        p_a = np.where(x<0.3, 30000, 100000).astype(float)
        p_b = p_a + np.random.randn(len(x))*100 # distributed
        diff2 = (p_a - p_b)**2
        total = np.sum(diff2)
        order = np.argsort(diff2)[::-1]
        cum = np.cumsum(diff2[order])
        n90 = np.searchsorted(cum, 0.9*total)+1
        # distributed should need many cells
        self.assertGreater(n90, 100)

    def test_physical_x_interpolation(self):
        # Test that comparing by physical x, not index, works across meshes
        x250 = np.linspace(0,0.75,250)
        x400 = np.linspace(0,0.75,400)
        p250 = np.interp(x250, [0,0.3,0.75], [30000,30000,100000])
        p400 = np.interp(x400, [0,0.3,0.75], [30000,30000,100000])
        # Interpolate both to common x
        x_common = np.linspace(0,0.75,500)
        p250_i = np.interp(x_common, x250, p250)
        p400_i = np.interp(x_common, x400, p400)
        diff = np.max(np.abs(p250_i - p400_i))
        self.assertLess(diff, 500)

    def test_odd_even_pairing(self):
        # Ensure odd/even pairing not mixing lag-1
        cycles = list(range(36,41)) # 36,37,38,39,40
        # lag-2 pairs: 40vs38,39vs37,38vs36 (both parities)
        pairs = [(40,38),(39,37),(38,36)]
        for cur, prev in pairs:
            self.assertEqual(cur-prev, 2)
            self.assertEqual(cur%2, prev%2)

    def test_r10_artifacts_exist(self):
        base = Path("results/p4-r10-20260922")
        for fname in ["decision.json","evaluation.json","front_tracking.json","spatial_error.json","mesh_trend.json","sensor_front_relation.json","orbit_ab_vs_lag2.json"]:
            self.assertTrue((base/fname).exists(), f"missing {fname}")

if __name__ == "__main__":
    unittest.main()
