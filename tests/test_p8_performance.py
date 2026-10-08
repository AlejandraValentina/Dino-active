import math
import unittest
from unittest.mock import patch

from motorsim.p8_performance import (P8_ANCHORS, PREPARATION_CYCLES,
                                      PREPARATION_END_DEG, cycle_duration_s,
                                      indicated_metrics, omega_deg_s,
                                      validate_p8_rpm, work_from_pressure_volume)
from motorsim.project import ProjectError
from motorsim.p5c import make_p5c_fixture
from motorsim.p8_performance import model_geometry_callback
from motorsim.p8_performance import build_event_cuts
from motorsim.simulation_case import SyntheticCase
from motorsim.p8_performance import event_cuts, run_campaign
from motorsim.p8_performance import run_anchor
from motorsim.coupling import ChamberState
from motorsim.exhaust_port import port_flux
from motorsim.gas1d.eos import IdealGas


class P8ContractTests(unittest.TestCase):
    def _replay_anchor(self):
        return {
            "terminal_replay_digest": "a"*64,
            "preparation_state_digest": "b"*64,
            "p7_ledger": {"heat_added": 1.0},
            "W_cycle_J": 1.0, "p_max_Pa": 2.0,
            "global_mass_residual_kg": 0.0,
            "global_energy_residual_J": 0.0,
            "fresh_mass_delivered_kg": 3.0,
            "fresh_short_circuit_mass_kg": 0.5,
            "mass_balance_terms": {"residual": 0.0},
            "energy_balance_terms": {"residual": 0.0},
            "gates": {},
        }

    def test_replay_gate_requires_fresh_delivery_equality(self):
        first = self._replay_anchor()
        second = self._replay_anchor()
        second["fresh_mass_delivered_kg"] += 1.0
        with patch("motorsim.p8_performance._run_once", side_effect=[first, second]):
            result = run_anchor(2500)
        self.assertFalse(result["deterministic_replay"]["fresh_delivery_equal"])
        self.assertFalse(result["gates"]["deterministic_replay"])

    def test_replay_gate_requires_short_circuit_equality(self):
        first = self._replay_anchor()
        second = self._replay_anchor()
        second["fresh_short_circuit_mass_kg"] += 1.0
        with patch("motorsim.p8_performance._run_once", side_effect=[first, second]):
            result = run_anchor(2500)
        self.assertFalse(result["deterministic_replay"]["short_circuit_equal"])
        self.assertFalse(result["gates"]["deterministic_replay"])

    def test_replay_gate_requires_full_terminal_digest(self):
        first = self._replay_anchor()
        second = self._replay_anchor()
        second["terminal_replay_digest"] = "c"*64
        with patch("motorsim.p8_performance._run_once", side_effect=[first, second]):
            result = run_anchor(2500)
        self.assertFalse(result["deterministic_replay"]["state_equal"])
        self.assertFalse(result["gates"]["deterministic_replay"])

    def test_campaign_is_nonvacuous_and_writes_consistent_anchor_evidence(self):
        import json, tempfile
        with tempfile.TemporaryDirectory() as directory:
            result = run_campaign(directory)
            self.assertEqual(result['status'], 'P8_WIDE_RPM_PERFORMANCE_VERIFIED_CONDITIONAL')
            self.assertEqual(result['failures'], [])
            consolidated = json.load(open(directory + '/p8-wide-rpm.json', encoding='utf-8'))
            for anchor in consolidated['anchors']:
                per = json.load(open(f"{directory}/anchor-{anchor['rpm']}.json", encoding='utf-8'))
                self.assertEqual(per, anchor)
                self.assertEqual(anchor['preparation']['cycles'], 2)
                self.assertEqual(anchor['preparation']['start_angle_deg'], 180.0)
                self.assertEqual(anchor['preparation']['end_angle_deg'], 900.0)
                self.assertEqual(anchor['preparation']['prescribed_heat_J'], 0.0)
                self.assertFalse(anchor['preparation']['p7_enabled'])
                self.assertTrue(anchor['gates']['prepared_initial_state'])
                self.assertTrue(anchor['gates']['deterministic_replay'])
            required = {'finite', 'geometry_rebased', 'admissible', 'species',
                        'p7_one_event', 'p7_nonvacuous', 'p7_source_admissible',
                        'p7_heat_consistent', 'cfl', 'source_heat_consistent',
                        'prescribed_heat_matches_ledger', 'global_mass_conservation',
                        'global_energy_conservation', 'prepared_initial_state',
                        'restart', 'deterministic_replay'}
            for anchor in consolidated['anchors']:
                self.assertTrue(required <= set(anchor['gates']))
                self.assertTrue(all(anchor['gates'][name] for name in required))
                self.assertGreater(anchor['prescribed_heat_J'], 0.0)
            self.assertTrue(all(a['gates']['p7_nonvacuous'] for a in consolidated['anchors']))
            self.assertTrue(all(a['gates']['prescribed_heat_matches_ledger'] for a in consolidated['anchors']))
            self.assertTrue(all(a['gates']['source_heat_consistent'] for a in consolidated['anchors']))
    def test_p7_hooks_are_zero_after_the_fixed_event(self):
        from motorsim.p8_performance import _new_system
        from motorsim.p7_prescribed import capture_event
        _, system = _new_system(2500, enable_p7=True)
        system.p7_event = capture_event(350.0, system.species_mass['cylinder'][0])
        system._p7_active_interval = (390.0, 391.0)
        system._p7_mass_rate = None
        assert system._p7_source(390.5, None, {'area': 0.0}) == (0.0, 0.0, 0.0)
        assert system._p7_species_source(390.5) == (0.0, 0.0, 0.0, 0.0, 0.0)

    def test_event_cuts_repeat_mechanics_and_p7_boundaries(self):
        from motorsim.simulation_case import SyntheticCase
        cuts = event_cuts(SyntheticCase(), 180.0, 900.0)
        self.assertIn(350.0, cuts)
        self.assertIn(390.0, cuts)
        for expected in (430.1050607703571, 450.0, 472.2040961002297,
                         477.3344439797084, 514.489936176896):
            self.assertTrue(any(abs(value - expected) < 1e-12 for value in cuts))
        self.assertIn(710.0, cuts)
        self.assertIn(750.0, cuts)
        measured = build_event_cuts(SyntheticCase(), 180.0, 540.0,
                                    p7_enabled=True, restart_probe=True)
        self.assertIn(370.0, measured)

    def test_domain_and_timing(self):
        self.assertEqual(P8_ANCHORS, (2500, 5000, 8000, 11000, 15000))
        self.assertEqual(omega_deg_s(2500), 15000.0)
        self.assertEqual(omega_deg_s(15000), 90000.0)
        self.assertEqual(cycle_duration_s(2500), 60 / 2500)
        for rpm in (2499, 15001, 2500.0, True):
            with self.assertRaises(ProjectError):
                validate_p8_rpm(rpm)

    def test_work_sign_and_formulas(self):
        expansion = work_from_pressure_volume((100000, 100000), (1e-4, 2e-4))
        compression = work_from_pressure_volume((100000, 100000), (2e-4, 1e-4))
        self.assertGreater(expansion, 0)
        self.assertLess(compression, 0)
        m = indicated_metrics(12.0, 6000, 2.5e6)
        self.assertEqual(m["P_indicated_W"], 1200.0)
        self.assertAlmostEqual(m["T_indicated_Nm"], 12 / (2 * math.pi))

    def test_geometry_callback_updates_both_ssprk_stages(self):
        seen = []
        def geometry(angle):
            seen.append(angle)
            volume = 0.01 + angle * 1e-6
            return {'volumes': (0.001, volume, volume, 0.002),
                    'volume_rates': (0.0, 0.0),
                    'areas': (0.0, 0.0, 0.0, 0.0)}
        fixture = make_p5c_fixture(port_area=0.0)
        fixture.geometry_callback = geometry
        fixture.core.geometry_callback = geometry
        fixture.step(0.1, angle=12.0)
        self.assertEqual(seen[:3], [11.9, 11.9, 11.9])
        self.assertIn(12.0, seen)
        self.assertAlmostEqual(fixture.history[-1]['stage_states'][0][1][4], 0.0100119)
        self.assertAlmostEqual(fixture.history[-1]['stage_states'][2][1][4], 0.010012)

    def test_callback_uses_authoritative_crankcase_and_cylinder_slots(self):
        def geometry(angle):
            return {'volumes': (0.11, 0.21 + angle * 1e-6,
                                0.31 + angle * 1e-6, 0.41),
                    'volume_rates': (0.0, 0.0),
                    'areas': (0.0, 0.0, 0.0, 0.0)}
        fixture = make_p5c_fixture(port_area=0.0)
        fixture.geometry_callback = geometry
        fixture.core.geometry_callback = geometry
        fixture.step(0.1, angle=12.0)
        q0, _, qn = fixture.history[-1]['stage_states']
        self.assertAlmostEqual(q0[0][4], 0.21 + 11.9e-6)
        self.assertAlmostEqual(q0[1][4], 0.31 + 11.9e-6)
        self.assertAlmostEqual(qn[0][4], 0.21 + 12e-6)
        self.assertAlmostEqual(qn[1][4], 0.31 + 12e-6)

    def test_model_geometry_area_mapping_is_direct(self):
        class FakeModel:
            case = type('Case', (), {'project_geometry': object()})()
            def geometry(self, angle):
                return ((1, 2, 3, 4), (5, 6, 7, 8),
                        (10, 11, 12, 13, 14, 15))
        callback = model_geometry_callback(FakeModel())
        self.assertEqual(callback(0)['areas'], (11, 12, 13, 14))

    def test_dynamic_exhaust_area_is_capped_by_fixed_pipe(self):
        eos = IdealGas()
        chamber = ChamberState(1e-5, 100.0, 0.0, 1e-4)
        pipe = (1.0, 0.0, 100000.0, 0.0)
        face = port_flux(chamber, pipe, 3e-4, 1e-4, eos=eos)
        self.assertEqual(face['area'], 1e-4)

    def test_absolute_event_cuts_repeat_after_one_turn(self):
        cuts = build_event_cuts(SyntheticCase(), 360.0, 540.0, p7_enabled=True)
        for phase in (430.10506077035714, 450.0, 472.2040961002297,
                      477.3344439797084, 514.489936176896, 540.0):
            self.assertIn(phase, cuts)


if __name__ == "__main__":
    unittest.main()
