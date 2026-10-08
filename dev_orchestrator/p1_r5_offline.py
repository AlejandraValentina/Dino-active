"""Read-only scientific reproduction of existing T11 evidence; never integrates."""
import gzip
import hashlib
import json
from pathlib import Path

from motorsim.gas1d.eos import IdealGas
from .p2b_resume import source_hashes, signature, expected_signature

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'results/p2b-gas1d-20260918/resume-remaining-final/artifacts'


def reproduce():
    manifest = json.loads((SOURCE / 'resume-checkpoint.json').read_text(encoding='utf-8'))
    assert manifest['source_sha256'] == source_hashes()
    rows = []
    for n in (400, 800, 1600):
        for c in (.2, .4, .6):
            name = f'T03_{c}' + (f'_N{n}' if n != 800 else '')
            path = SOURCE / 'cases' / (name + '.json.gz')
            evidence_hash = hashlib.sha256(path.read_bytes()).hexdigest()
            assert evidence_hash == manifest['cases'][name]['sha256']
            record = json.loads(gzip.decompress(path.read_bytes()))
            assert signature(record) == expected_signature(f'T03_{c}', n)
            result = record['result']
            complete = result['status'] == 'completed' and result['time'] == record['configuration']['final_time']
            eos = IdealGas(R=record['configuration']['R'], gamma=record['configuration']['gamma'])
            reference = [eos.primitive([x / volume for x in cell]) for cell, volume in zip(record['reference'], record['mesh']['volumes'])]
            analytical = max(w[2] - 100000 for w in reference)
            amplitude = max(w[2] - 100000 for w in result['primitive']) if complete else None
            error = abs(amplitude - analytical) if complete else None
            residuals = [max(abs(step['normalized'][k]) for step in result['ledger']) for k in range(4)]
            stages = [max(abs(step[field][k]) for step in result['stage_ledger'] for field in ('stage1_normalized', 'stage2_normalized')) for k in range(4)]
            for w in result['primitive']:
                eos.validate(w)
            ext = result['extrema']
            admissible = min(ext[k] for k in ('min_rho', 'min_p', 'min_T')) > 0 and 0 <= ext['min_Y'] <= ext['max_Y'] <= 1
            stage_admissible = all(min(s[field][:3]) > 0 and 0 <= s[field][3] <= s[field][4] <= 1 for s in result['stage_ledger'] for field in ('stage1_extrema', 'stage2_extrema'))
            rows.append(dict(N=n, CFL=c, complete=complete, amplitude_Pa=amplitude, reference_Pa=analytical,
                absolute_error_Pa=error, relative_error_to_reference=error / analytical if complete else None,
                normalized_error_to_10Pa=error / 10 if complete else None,
                residual_components=residuals, stage_residual_components=stages,
                admissible_recorded_interval=admissible and stage_admissible,
                runtime=result['wall_seconds'], steps=result['steps'], RHS=result['rhs_count'],
                HLLC=result['hllc_flux_count'], HLLE=result['hlle_fallback_count'],
                fallback_reasons=result['fallback_reason'], checks=record['checks'], metrics=record['metrics'],
                evidence_sha256=evidence_hash, input_configuration_reference_sha256=signature(record)))
    pairs = []
    for a, b in ((.2, .4), (.4, .6), (.2, .6)):
        values = []
        for n in (400, 800, 1600):
            pair = [r for r in rows if r['N'] == n and r['CFL'] in (a, b)]
            values.append(abs(pair[0]['amplitude_Pa'] - pair[1]['amplitude_Pa']) / 10 if all(r['complete'] for r in pair) else None)
        pairs.append(dict(CFL_pair=[a, b], S400_S800_S1600=values))
    return dict(state='P1_R5_CFL_SECOND_ORDER_UNRESOLVED', P2='P2_BLOCKED_SECOND_ORDER',
                source_sha256=source_hashes(), rows=rows, pairs=pairs,
                new_integrations=0, R5_adopted=False, phase_B_authorized_by_gate=False)


if __name__ == '__main__':
    print(json.dumps(reproduce(), ensure_ascii=False, indent=2, allow_nan=False))
