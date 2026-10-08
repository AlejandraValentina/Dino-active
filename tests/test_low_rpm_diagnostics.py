"""Evidencia y observabilidad; sin nuevas integraciones ni expected científicos nuevos."""
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import unittest

from motorsim.examples import example_project
from motorsim.project_case import build_project_case
from motorsim.reference_results import BAND_PA
from motorsim.simulation import Model
from motorsim.artifact_store import resolve_external_artifact
from tools.analyze_low_rpm import replay_attempt, negative_analysis

ROOT=Path(__file__).resolve().parents[1]
EVIDENCE=ROOT/'results/frontera-baja-2t-20260917'
ARTIFACT_MANIFEST=ROOT/'artifacts/low-rpm-test-evidence.json'
EXTERNAL_EVIDENCE={
    '1000-observation.json':'LOWRPM_OBSERVATION_1000',
    **{f'{rpm}-observation.json':f'LOWRPM_OBSERVATION_{rpm}'
       for rpm in (1500,1750,2000,2250,2500,2750,3000)},
    **{f'{rpm}.json':f'LOWRPM_EVIDENCE_{rpm}' for rpm in (1000,2000,2500,3000)},
}


def read(name):
    artifact_id=EXTERNAL_EVIDENCE.get(name)
    path=(resolve_external_artifact(artifact_id,manifest_path=ARTIFACT_MANIFEST)
          if artifact_id else EVIDENCE/name)
    return json.loads(path.read_text(encoding='utf-8'))


def source_sha256(raw):
    """Hash source text identically for LF and CRLF checkouts."""
    return hashlib.sha256(raw.replace(b'\r\n',b'\n')).hexdigest()


class LowRpmDiagnosticsTests(unittest.TestCase):
    def test_core_hashes_and_contract_preserved(self):
        campaign=read('campaign.json')
        self.assertEqual(set(campaign['source_sha256']),set(campaign['source_sha256_lf']))
        for name,expected in campaign['source_sha256_lf'].items():
            source=(ROOT/'motorsim'/name).read_bytes()
            source=source.replace(b'\r\n',b'\n')
            if name == 'rpm_domain.py':
                # Authorization after P0 changes only the public 2T upper bound.
                # Reconstruct the historical bytes, preserving its recorded hash.
                source=source.replace(b"'2T': (2500, 15000)", b"'2T': (2500, 3500)")
            self.assertEqual(source_sha256(source),expected,name)
        from motorsim.rpm_domain import PUBLIC_DOMAINS
        self.assertEqual(PUBLIC_DOMAINS,{'2T':(2500,15000),'4T':(2500,3500)})

    def test_observation_does_not_change_original_scientific_trajectory(self):
        for rpm in (1000,2000,3000):
            previous=json.loads(resolve_external_artifact(
                f'LOWRPM_REFERENCE_{rpm}',manifest_path=ARTIFACT_MANIFEST).read_text(encoding='utf-8'))
            current=read(f'{rpm}.json')
            self.assertEqual(current['case'],previous['case'])
            for key,value in previous['result'].items():
                if key!='seconds': self.assertEqual(current['result'][key],value,(rpm,key))

    def test_source_hash_is_line_ending_independent(self):
        self.assertEqual(source_sha256(b'alpha\nbeta\n'),
                         source_sha256(b'alpha\r\nbeta\r\n'))

    def test_boundary_records_and_counts(self):
        campaign=read('campaign.json')
        self.assertEqual(campaign['boundary_rpms'],[1500,1750,2000,2250,2500,2750,3000])
        for row in campaign['rows']:
            observation=read(str(row['rpm'])+'-observation.json')
            self.assertEqual(row['rejected_attempts'],len(observation['rejections']))
            self.assertEqual(row['max_consecutive_rejections'],max(r['consecutive_rejections'] for r in observation['rejections']))
            self.assertEqual(row['first_physical_violation'],observation['physical_failures'][0])
            self.assertEqual(row['minimum_accepted_dt_s'],row['minimum_accepted_half_deg']/(6*row['rpm']))
            self.assertGreaterEqual(row['minimum_accepted_half_deg'],.001)
            if row['converged']:
                self.assertTrue(row['last_complete_cycle']['balances_passed'])
                self.assertEqual(row['metrics_kind'],'accepted')

    def test_1000_rejection_components_and_exact_offline_replay(self):
        d=read('1000-diagnostic.json'); rejection=d['rejection']
        base,_=build_project_case(example_project('2t-reference'),rpm=3000)
        model=Model(replace(base,rpm=1000),external_band_pa=BAND_PA)
        replay=replay_attempt(model,rejection['context']['advance'])
        self.assertEqual(replay,d['replay'])
        self.assertEqual(replay['normalized_error'],rejection['error'])
        self.assertEqual(replay['dominant'],'C.F')
        self.assertEqual(max(e['normalized'] for e in rejection['component_errors']),rejection['error'])
        self.assertLess(rejection['next_requested_half_deg'],.001)
        self.assertTrue(all(e['distance_deg']>1 for e in d['events']))

    def test_2000_stage_conservation_and_signs(self):
        observation=read('2000-observation.json'); d=read('2000-diagnostic.json')
        negatives=[r for r in observation['physical_failures'] if r['state'][8]<0]
        base,_=build_project_case(example_project('2t-reference'),rpm=3000)
        model=Model(replace(base,rpm=2000),external_band_pa=BAND_PA)
        for key,record in (('first_negative',negatives[0]),('terminal_negative',negatives[-1])):
            e=negative_analysis(model,record)
            self.assertEqual(e,d[key])
            self.assertEqual(e['F_rk_base_kg']+e['F_increment_kg'],e['F_candidate_kg'])
            self.assertEqual(e['F_rk_base_kg'],0)
            self.assertTrue(e['exceeds_rk_base_inventory'])
            self.assertFalse(e['exceeds_K3_inventory'])
            self.assertEqual(e['stage3_fresh_rhs_kg_s'],e['transport_sum_kg_s'])
            self.assertLess(abs(e['global_fresh_rate_residual']),1e-20)
            self.assertTrue(all(l['fresh_donor_consistent'] for l in e['stage3_snapshot']['links']))
            self.assertTrue(e['only_F_invalid'])
            self.assertIn('error',e['replay'])
        self.assertEqual([r['cause'] for r in d['terminal_attempts']],['local_error']*6+['nonphysical']*2)
        self.assertFalse(d['reduction_executed'])
        self.assertFalse(d['final_step_evaluated_after_negative'])

    def test_repeated_stage_on_halving_and_distinct_1750_mechanism(self):
        failures=read('2000-observation.json')['physical_failures']
        a,b=failures[-2:]
        self.assertEqual(a['state'],b['state'])
        self.assertEqual(a['context']['rk4'],b['context']['rk4'])
        self.assertEqual(a['context']['advance']['h']/2,b['context']['advance']['h'])
        upper=read('1750-diagnostic.json')['replay']['groups'][-1]['stages'][-1]['thermo_only']['cv']['I']
        self.assertGreater(upper['F_kg'],upper['m_kg'])
        self.assertLessEqual(upper['F_kg']-upper['m_kg'],1e-20)
