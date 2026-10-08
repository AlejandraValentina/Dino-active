import json, math, unittest
from pathlib import Path
from motorsim.gas1d.eos import IdealGas
from dev_orchestrator.reference.exact_riemann import ExactRiemann
from motorsim.gas1d.riemann import hllc_flux
from motorsim.coupling import ChamberState, interface_flux
from dev_orchestrator.p4_sci_04a import CHARACTERISTIC_DOC, EPS, SIGMA, SENSOR, X0, L_TRUNC, L_EXT, C0, Z0, P0

OUT = Path("results/p4-sci-04a-foundational-benchmarks-20260923")

class P4Sci04aTests(unittest.TestCase):
    def setUp(self):
        self.eos = IdealGas(R=287.0, gamma=1.35)

    def test_exact_riemann_sanity(self):
        # Sod-like normalized and F1 near-equal
        e = IdealGas(R=287, gamma=1.4)
        left = (1.0, 0.0, 1.0, 1.0)
        right = (0.125, 0.0, 0.1, 0.0)
        ref = ExactRiemann(left, right, e)
        self.assertAlmostEqual(ref.pstar, 0.30313017805, places=5)
        self.assertAlmostEqual(ref.ustar, 0.92745262, places=5)
        self.assertLess(ref.residual, 1e-12)
        # symmetry equal state
        w = (1.2, 30.0, 100000.0, 0.3)
        ref2 = ExactRiemann(w, w, self.eos)
        self.assertAlmostEqual(ref2.pstar, w[2], places=7)
        self.assertAlmostEqual(ref2.ustar, w[1], places=7)

    def test_sod_fixture_gamma135(self):
        eos = self.eos
        left = (1.0, 0.0, 100000.0, 1.0)
        right = (0.125, 0.0, 10000.0, 0.0)
        ref = ExactRiemann(left, right, eos)
        # p_star approx 30526 for gamma1.35
        self.assertAlmostEqual(ref.pstar, 30526.39914644, delta=1.0)
        self.assertAlmostEqual(ref.ustar, 299.334597, delta=1.0)
        # HLLC should have correct direction
        flux, speeds, reason = hllc_flux(left, right, eos)
        self.assertIsNone(reason)
        self.assertGreater(speeds[1], 0)  # u_star positive

    def test_symmetry_equal_state(self):
        w = (1.2, -10.0, 100000.0, 0.5)
        flux, speeds, reason = hllc_flux(w, w, self.eos)
        for a,b in zip(flux, self.eos.flux(w)):
            self.assertAlmostEqual(a,b, places=9)
        self.assertIsNone(reason)
        ref = ExactRiemann(w, w, self.eos)
        self.assertAlmostEqual(ref.pstar, w[2], places=7)

    def test_backflow_sign(self):
        # chamber lower than pipe => outward positive? Test both orientations
        eos = self.eos
        ch = ChamberState(mass=0.000116, internal_energy= 0.000116*eos.cv*300, fresh_mass=0.0000348, volume=0.0001) # 80kPa
        # Actually construct 80kPa chamber
        p_low = 80000
        V=0.0001
        m_low = p_low*V/(eos.R*300)
        ch_low = ChamberState(mass=m_low, internal_energy=m_low*eos.cv*300, fresh_mass=0.3*m_low, volume=V)
        pipe = (100000/(eos.R*300), -40.0, 100000, 0.2) # pipe toward chamber
        # normal -1 chamber left, pipe right, flow should be outward positive if pipe pushes into chamber? Check sign: outward is normal*area*flux; for normal -1 outward negative means into chamber? From coupling doc: outward is outside pipe; for normal -1 left side, outward negative means flow enters pipe? Let's just test direction consistency
        flux = interface_flux(ch_low, pipe, 0.000314, -1, eos=eos)
        # exact reference
        rho_c = p_low/(eos.R*300)
        left = (rho_c, 0.0, p_low, 0.3)
        right = pipe
        ref = ExactRiemann(left, right, eos)
        # mass flux sign should match direction of u_star
        exact_iface = ref.sample(0.0)
        exact_mass_flux = eos.flux(exact_iface)[0]
        # product mass outward = normal*area*flux; sign should reflect same direction as exact mass*normal?
        prod_mass_outward = flux.outward[0]
        exact_mass_outward = -1 * 0.000314 * exact_mass_flux  # normal -1 => outward = -1*area*flux ?
        # Actually flux[0] is per area, outward = normal*area*flux
        # For normal -1, outward = -area*flux. So compare signs
        self.assertEqual((prod_mass_outward>0), (exact_mass_outward>0))
        # also species donor check
        self.assertAlmostEqual(flux.outward[3] / flux.outward[0], left[3] if ref.ustar>=0 else right[3], places=9)

    def test_characteristic_decomposition(self):
        # pure right-going wave: dp=Z*du => L_in=0
        p_prime = 50.0
        du = p_prime / Z0
        dp = p_prime
        L_out = du + dp / Z0
        L_in = du - dp / Z0
        self.assertAlmostEqual(L_in, 0.0, places=12)
        self.assertAlmostEqual(L_out, 2*du, places=12)
        # left-going
        du2 = -p_prime / Z0
        L_out2 = du2 + dp / Z0
        L_in2 = du2 - dp / Z0
        self.assertAlmostEqual(L_out2, 0.0, places=12)
        # doc string contains variables
        self.assertIn("L_out", CHARACTERISTIC_DOC["variables"])
        self.assertIn("Z0", CHARACTERISTIC_DOC["variables"])

    def test_extended_domain_time_window_validity(self):
        c0 = C0
        t_out = (SENSOR - X0)/c0
        t_ref_trunc = ((L_TRUNC - X0)+(L_TRUNC - SENSOR))/c0
        t_ref_ext = ((L_EXT - X0)+(L_EXT - SENSOR))/c0
        window_refl = (t_ref_trunc-3*SIGMA/c0, t_ref_trunc+3*SIGMA/c0)
        valid_end = t_ref_ext -3*SIGMA/c0 -2*(L_TRUNC/50)/c0
        self.assertGreater(t_ref_ext, t_ref_trunc + 3*SIGMA/c0 + 0.001)
        self.assertGreater(valid_end, window_refl[1])
        # ensure truncated reflection window before valid_end
        self.assertLess(window_refl[1], valid_end)
        # also ensure outgoing window before refl window
        window_out = (t_out-3*SIGMA/c0, t_out+3*SIGMA/c0)
        self.assertLess(window_out[1], window_refl[0])

    def test_json_artifact_completeness(self):
        required = [
            OUT/"decision.json",
            OUT/"runtime.json",
            OUT/"b1"/"configuration.json",
            OUT/"b1"/"characteristic_reference.json",
            OUT/"b1"/"extended_domain_reference.json",
            OUT/"b1"/"refinement.json",
            OUT/"b1"/"metrics.json",
            OUT/"b1"/"decision.json",
            OUT/"c1"/"fixtures.json",
            OUT/"c1"/"exact_reference.json",
            OUT/"c1"/"productive_interface.json",
            OUT/"c1"/"errors.json",
            OUT/"c1"/"decision.json",
        ]
        for p in required:
            self.assertTrue(p.exists(), f"missing {p}")
            data = json.loads(p.read_text())
            self.assertIsInstance(data, dict)
        # check top decision classification allowed
        dec = json.loads((OUT/"decision.json").read_text())
        self.assertIn(dec["classification"], ["P4_SCI_FOUNDATIONAL_BENCHMARKS_VERIFIED","P4_SCI_FOUNDATIONAL_BENCHMARKS_INCONCLUSIVE","P4_SCI_CONCRETE_BOUNDARY_DEFECT_IDENTIFIED","P4_SCI_CONCRETE_COUPLING_INTERFACE_DEFECT_IDENTIFIED"])
        self.assertFalse(dec["p4_pass"])
        # b1 decision
        b1d = json.loads((OUT/"b1"/"decision.json").read_text())
        self.assertIn(b1d["classification"], ["P4_SCI_B1_BOUNDARY_LINEAR_VERIFIED","P4_SCI_B1_BOUNDARY_DEFECT_IDENTIFIED","P4_SCI_B1_INCONCLUSIVE"])
        # c1 decision
        c1d = json.loads((OUT/"c1"/"decision.json").read_text())
        self.assertIn(c1d["classification"], ["P4_SCI_C1_INTERFACE_RIEMANN_VERIFIED","P4_SCI_C1_INTERFACE_DEFECT_IDENTIFIED","P4_SCI_C1_INCONCLUSIVE"])
        # runtime cheap check
        rt = json.loads((OUT/"runtime.json").read_text())
        self.assertLess(rt["total_wall_seconds"], 600)
        # b1 metrics check: three levels
        ref = json.loads((OUT/"b1"/"refinement.json").read_text())
        self.assertEqual(len(ref["levels"]), 3)
        # c1 fixtures at least 7
        fix = json.loads((OUT/"c1"/"fixtures.json").read_text())
        self.assertGreaterEqual(len(fix["fixtures"]), 7)

    def test_c1_fixture_coverage(self):
        fixtures = json.loads((OUT/"c1"/"fixtures.json").read_text())["fixtures"]
        ids = {f["id"] for f in fixtures}
        for required in ["F1_NEAR_EQUAL","F2_SHOCK_DOMINATED","F3_RAREFACTION_DOMINATED","F5_BACKFLOW","F7_TYPICAL_P4"]:
            self.assertIn(required, ids)
        # backflow must have correct direction outward vs inward check via errors
        errors = json.loads((OUT/"c1"/"errors.json").read_text())["errors"]
        # find backflow
        bf = next(e for e in errors if e["id"]=="F5_BACKFLOW")
        self.assertTrue(bf["errors"]["correct_direction"])

if __name__ == "__main__":
    unittest.main()
