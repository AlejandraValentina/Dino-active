"""Forensic diagnostics for the frozen V1 reservoir branch.

These tests characterize the existing contract; they do not select or
implement a future reservoir-boundary policy.
"""
import math
import unittest

from motorsim.gas1d.boundary import Boundary
from motorsim.gas1d.eos import IdealGas, InvalidState


class ReservoirBranchForensics(unittest.TestCase):
    def setUp(self):
        self.eos = IdealGas()
        self.p0 = 100_000.0
        self.t0 = 300.0
        self.interior_t = 301.0

    def test_v1_inflow_invariant_has_a_bounded_monotone_subsonic_branch(self):
        eos = self.eos
        g = eos.gamma
        h0 = eos.cp * self.t0
        a_sonic = math.sqrt(2 * (g - 1) * h0 / (g + 1))

        def invariant(w):
            a = math.sqrt((g - 1) * (h0 - w * w / 2))
            return w + 2 * a / (g - 1)

        samples = [-a_sonic + a_sonic * i / 1000 for i in range(1001)]
        values = [invariant(w) for w in samples]
        self.assertTrue(all(b > a for a, b in zip(values, values[1:])))
        j_choke = -a_sonic + 2 * a_sonic / (g - 1)
        j_rest = 2 * math.sqrt((g - 1) * h0) / (g - 1)
        self.assertAlmostEqual(values[0], j_choke, places=10)
        self.assertAlmostEqual(values[-1], j_rest, places=10)

        rho = self.p0 / (eos.R * self.interior_t)
        interior = (rho, -0.001, self.p0, 0.2)
        j_plus = interior[1] + 2 * eos.sound_speed(interior) / (g - 1)
        self.assertGreater(j_plus, j_rest)
        # Since the function is monotone and this exceeds its maximum, the
        # existing V1 subsonic-inflow equation has no root in [-a_sonic, 0].
        self.assertFalse(any(math.isclose(v, j_plus, rel_tol=0, abs_tol=1e-12)
                             for v in values))

    def test_v1_rejects_the_gap_but_full_exterior_riemann_state_returns_flux(self):
        eos = self.eos
        rho = self.p0 / (eos.R * self.interior_t)
        interior = (rho, -0.001, self.p0, 0.2)
        reservoir = Boundary("reservoir", p0=self.p0, T0=self.t0, Y0=0.0)
        with self.assertRaisesRegex(InvalidState, "No consistent reservoir inflow branch"):
            reservoir.flux(interior, 1, eos)

        # This is a distinct, conventional full-state/ghost-state contract,
        # evaluated only as a discriminator, not adopted as MotorSim policy.
        exterior = (self.p0 / (eos.R * self.t0), 0.0, self.p0, 0.0)
        fixed_state_flux = Boundary("fixed", state=exterior).flux(interior, 1, eos)[0]
        self.assertTrue(all(math.isfinite(v) for v in fixed_state_flux))
        self.assertLess(fixed_state_flux[0], 0.0)

    def test_reservoir_gap_is_invariant_under_normal_orientation(self):
        eos = self.eos
        rho = self.p0 / (eos.R * self.interior_t)
        boundary = Boundary("reservoir", p0=self.p0, T0=self.t0, Y0=0.0)
        for normal, velocity in ((1, -0.001), (-1, 0.001)):
            interior = (rho, velocity, self.p0, 0.2)
            with self.subTest(normal=normal):
                with self.assertRaisesRegex(InvalidState, "No consistent reservoir inflow branch"):
                    boundary.face_state(interior, normal, eos)


if __name__ == "__main__":
    unittest.main()
