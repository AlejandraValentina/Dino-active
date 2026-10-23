"""Offline reduction of existing engineering-point evidence; no solver steps."""
import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from motorsim.reference_harness.convergence import CONTRACT, compare_cycles_v2


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def reduce_cycle(c):
    o = c['observables']
    cells = o['ducts']['exhaust']
    metrics = (c.get('comparison') or {}).get('metrics', {})
    failed = {k: v for k, v in metrics.items() if not v['passed']}
    groups = Counter(k.split('].')[-1] if k.startswith('ducts.exhaust[') else k for k in failed)
    return dict(cycle=c['cycle'], work_J=c['cylinder_work_J'],
        trapped_air_kg=c['closure_snapshots']['exhaust']['cylinder_species_kg'][0],
        brake=c['mechanical_estimate'], exhaust_mass_kg=sum(x['mass_kg'] for x in cells),
        exhaust_energy_J=sum(x['total_energy_J'] for x in cells),
        exhaust_species_kg=[sum(x['mass_kg']*x['species_mass_fractions'][i] for x in cells) for i in range(4)],
        global_species_kg=o['global_species_kg'],
        exhaust_pressure_Pa=[x['pressure_Pa'] for x in cells],
        exhaust_temperature_K=[x['temperature_K'] for x in cells],
        exhaust_residual_fraction=[x['species_mass_fractions'][2] for x in cells],
        failed_groups=dict(groups), failures=len(failed),
        worst_threshold_ratio=max((v['value']/v['threshold'] for v in metrics.values()), default=None),
        streak=c['periodicity_streak'], wall_s=c['wall_s'],
        conservation=c['conservation']['relative'])


def analyze(path, parent_dir=None):
    manifest = json.loads(path.read_bytes())
    directory = path.parent
    cycles = manifest['cycles']
    integrity = []
    max_balance = [0., 0., 0., 0., 0., 0.]
    for n, c in enumerate(cycles):
        record = dict(cycle_index=n+1, configuration_hash=manifest['bindings']['configuration_canonical_sha256'],
                      contract=CONTRACT, observables=c['observables'])
        if n:
            assert compare_cycles_v2(previous, record) == c['comparison'], f'detector mismatch cycle {n+1}'
            older = cycles[n-1]['observables']
            newer = c['observables']
            f = c['flow_integrals']
            # Exhaust is source-free: exact stage-quadrature boundary fluxes.
            for i, name in enumerate(('air', 'fuel', 'residual', 'burned')):
                delta = sum(x['mass_kg']*x['species_mass_fractions'][i] for x in newer['ducts']['exhaust']) - sum(x['mass_kg']*x['species_mass_fractions'][i] for x in older['ducts']['exhaust'])
                boundary = sum(f.get(f'exhaust.left.{name}.out_{sgn}_kg',0)*sign - f.get(f'exhaust.right.{name}.out_{sgn}_kg',0)*sign for sgn,sign in [('positive',1),('negative',-1)])
                max_balance[i] = max(max_balance[i], abs(delta-boundary))
            mass_delta = sum(x['mass_kg'] for x in newer['ducts']['exhaust']) - sum(x['mass_kg'] for x in older['ducts']['exhaust'])
            max_balance[4] = max(max_balance[4],abs(mass_delta-f['exhaust.left.net_kg']+f['exhaust.right.net_kg']))
            for i in range(4):
                source = sum(c['ledger_delta'][k][i] for k in ('external_species_kg','fuel_combustion_source_species_kg','p7_source_species_kg'))
                max_balance[5] = max(max_balance[5],abs(newer['global_species_kg'][i]-older['global_species_kg'][i]-source))
        previous = record
        artifact = directory/f'cycle-{n+1:03d}-diagnostics.json'
        if not artifact.exists() and parent_dir is not None:
            artifact = parent_dir/artifact.name
        assert sha(artifact) == c['diagnostic_artifact_sha256'], artifact
        data = json.loads(artifact.read_bytes())
        assert len(data['samples']) == 720
        assert len({s['angle_deg'] for s in data['samples']}) == 720
        integrity.append(dict(cycle=n+1, sha256=sha(artifact)))
    cp_path = directory/manifest['checkpoint_artifact']
    assert sha(cp_path) == manifest['checkpoint_sha256']
    cp = json.loads(cp_path.read_bytes())
    assert cp['next_cycle'] == len(cycles)+1
    assert cp['bindings'] == manifest['bindings']
    assert len(cp['periodicity_history']) == len(cycles)
    return dict(manifest=str(path), manifest_sha256=sha(path), checkpoint_sha256=sha(cp_path),
        next_cycle=cp['next_cycle'], status=manifest['status'], periodicity=manifest['periodicity'],
        bindings=manifest['bindings'], continuation=manifest['continuation'],
        wall_s=manifest['wall_s'], solver_wall_s=manifest['solver_step_wall_s'],
        processing_wall_s=manifest['processing_wall_s'], peak_rss_mib=manifest['peak_rss_mib'],
        rejected_trials=manifest['rejected_trials'], integrity=integrity,
        detector_recomputed=True, max_abs_exhaust_species_balance_residual_kg=max_balance[:4],
        max_abs_exhaust_mass_balance_residual_kg=max_balance[4],
        max_abs_global_species_balance_residual_kg=max_balance[5],
        cycles=[reduce_cycle(c) for c in cycles])


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('manifest',type=Path)
    p.add_argument('--parent-dir',type=Path)
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    result=analyze(a.manifest,a.parent_dir)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ('cycles','integrity','bindings')},indent=2))
