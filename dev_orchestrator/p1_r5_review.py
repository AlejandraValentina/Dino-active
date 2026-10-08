"""Offline reconstruction and explicit second-order R5 evaluation; never solves."""
import argparse
import copy
import gzip
import hashlib
import json
from pathlib import Path

from motorsim.gas1d.eos import IdealGas
from .p2b_resume import (ROOT, load_reusable, source_hashes, signature,
    expected_signature, test_gate, runtime, digest, write)
from .p2b_campaign import frozen_checks
from .p2_campaign import sha
from .p1_r4_gate import OLD, EVIDENCE, verify_inventory, revised_t11
from motorsim.gas1d import verification as v

PREVIOUS = ROOT / 'results/p2b-gas1d-20260918/resume-remaining-final'

def load_records(acquisition):
    records, origins = load_reusable(PREVIOUS, source_hashes(), retain_timeouts=True)
    acquisition = Path(acquisition).resolve()
    manifest = json.loads((acquisition / 'artifacts/acquisition.json').read_text(encoding='utf-8'))
    if manifest['source_sha256'] != source_hashes():
        raise ValueError('Solver changed')
    for name, item in manifest['cases'].items():
        path = acquisition / item['path']
        if sha(path) != item['sha256']:
            raise ValueError('New artifact hash mismatch')
        record = json.loads(gzip.decompress(path.read_bytes()))
        base, sep, n = name.partition('_N')
        expected = expected_signature(base, int(n) if sep else None)
        if signature(record) != expected or item['input_sha256'] != expected:
            raise ValueError('Canonical input mismatch')
        records[name] = record
        origins[name] = dict(path=path.relative_to(ROOT).as_posix(), sha256=sha(path),
            input_sha256=expected, solver_revision='4620200', role=item['role'])
    for name, record in records.items():
        origins[name]['configuration_sha256'] = digest(record['configuration'])
        origins[name]['initial_mesh_sha256'] = digest({k: record[k] for k in ('mesh','initial')})
    return records, origins

def acoustic_rows(records):
    rows = []
    for n in (400,800,1600):
        for c in (.2,.4,.6):
            name = f'T03_{c}' + (f'_N{n}' if n != 800 else '')
            record = records[name]; result = record['result']
            complete = result['status'] == 'completed' and result['time'] == record['configuration']['final_time']
            eos = IdealGas(record['configuration']['R'], record['configuration']['gamma'])
            ref = [eos.primitive(tuple(qi / volume for qi in q)) for q,volume in zip(record['reference'],record['mesh']['volumes'])]
            exact = max(w[2]-v.P0 for w in ref)
            amplitude = max(w[2]-v.P0 for w in result['primitive']) if complete else None
            error = abs(amplitude-exact) if complete else None
            ledgers = [max(abs(s['normalized'][k]) for s in result['ledger']) for k in range(4)]
            stages = [max(abs(s[field][k]) for s in result['stage_ledger'] for field in ('stage1_normalized','stage2_normalized')) for k in range(4)]
            for w in result['primitive']: eos.validate(w)
            ext = result['extrema']
            admissible = min(ext[k] for k in ('min_rho','min_p','min_T'))>0 and 0<=ext['min_Y']<=ext['max_Y']<=1
            admissible &= all(min(s[field][:3])>0 and 0<=s[field][3]<=s[field][4]<=1 for s in result['stage_ledger'] for field in ('stage1_extrema','stage2_extrema'))
            rows.append(dict(name=name,N=n,CFL=c,complete=complete,amplitude_Pa=amplitude,
                reference_Pa=exact,absolute_error_Pa=error,
                relative_error=error/exact if complete else None,
                E_A=error/10 if complete else None,
                conservation_components=ledgers,stage_conservation_components=stages,
                admissible_recorded_interval=admissible, metrics=record['metrics'],
                runtime=runtime(record)))
    return rows

def candidate_r5(records):
    """Explicit hypothetical R5 branch, never alters the historical R4 evaluator."""
    matrix = {test:test_gate(test,records) for test in ('T10','T11')}
    old = copy.deepcopy(matrix['T11'])
    new = matrix['T11']
    for key, values in new['metrics'].items():
        if key.startswith('sensitivity_'):
            new['checks'][key] = values[2] < values[0]
    rows = acoustic_rows(records)
    new['checks']['all_nine_final'] = len(rows)==9 and all(r['complete'] for r in rows)
    new['checks']['strict_admissibility'] = all(r['admissible_recorded_interval'] for r in rows)
    new['checks']['four_balances_steps_stages'] = all(max(r['conservation_components']+r['stage_conservation_components'])<=1e-10 for r in rows)
    new['checks']['complete_parent_suite'] = new['recorded_subcases'] == new['completed_subcases'] == new['expected_subcases'] == 12
    required = {f'sensitivity_{a}_{b}' for a,b in ((.2,.4),(.4,.6),(.2,.6))}
    required |= {f'analytical_error_{c}' for c in (.2,.4,.6)}
    required |= {f'Sod_{c}_{field}' for c in (.4,.6) for field in ('rho','u','p')}
    required |= {f'pulse_{c}_speed' for c in (.4,.6)}
    new['checks']['comparisons_complete'] = required <= new['checks'].keys()
    new['status'] = 'PASS' if all(new['checks'].values()) else 'FAIL'
    return matrix, old, rows

def report(acquisition, output):
    records, origins = load_records(acquisition)
    matrix, historical, rows = candidate_r5(records)
    # These comparisons diagnose scientific coherence, not new tuned thresholds.
    profiles = {}
    for c in (.2,.4,.6):
        selected = [r for r in rows if r['CFL']==c]
        profiles[str(c)] = {key:[r['metrics'].get(key) for r in selected]
            for key in ('pressure_L1','pressure_L2','speed_relative_error','phase_displacement_error')}
    checks = frozen_checks()
    result = dict(state='EVIDENCE_FOR_INDEPENDENT_R5_REVIEW', R5_adopted=False,
        matrix_under_candidate_R5=matrix, T11_under_R4=historical, rows=rows,
        profile_diagnostics=profiles, provenance=origins, frozen_checks=checks,
        source_sha256=source_hashes(), new_integrations=2,
        runtime_by_case={name:runtime(r) for name,r in records.items()})
    write(output,result)
    return result

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--acquisition',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    report(args.acquisition,args.output)
