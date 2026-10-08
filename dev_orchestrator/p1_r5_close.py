"""Offline P2 closure under the independently adopted R5 contract."""
import argparse
import gzip
import json
from pathlib import Path

from motorsim.gas1d import verification as v
from motorsim.gas1d.eos import IdealGas
from .p1_r5_review import ROOT, load_records, candidate_r5
from .p2b_resume import test_gate, runtime, source_hashes, write
from .p2b_campaign import frozen_checks
from .p2_campaign import sha
from .p1_r4_gate import OLD, EVIDENCE, verify_inventory, revised_t11
from .p0_campaign import HISTORICAL_RPMS, compare_historical

EVIDENCE_R5 = ROOT / 'results/p1-r5e-20260918'


def close(run_dir):
    review = json.loads((EVIDENCE_R5 / 'scientific-review.json').read_text(encoding='utf-8'))
    contract_path = ROOT / 'docs/gasdynamic/1d_contract_v1_r5.json'
    if review['state'] != 'P1_R5_PASS_CFL_SECOND_ORDER_CONTRACT' or review['contract_sha256'] != sha(contract_path):
        raise ValueError('R5 not independently adopted or contract changed')
    contract = json.loads(contract_path.read_text(encoding='utf-8'))
    if contract['verification_cases'][10]['definition'] != (EVIDENCE_R5 / 'r5-candidate.md').read_text(encoding='utf-8'):
        raise ValueError('Adopted definition differs from reviewed candidate')
    records, provenance = load_records(EVIDENCE_R5 / 'acquisition')
    revised, r4, rows = candidate_r5(records)
    matrix = {f'T{i:02}': test_gate(f'T{i:02}', records) for i in range(1, 13)}
    matrix['T11'] = revised['T11']
    checks = frozen_checks()
    verify_inventory(OLD)
    verify_inventory(EVIDENCE / 'study')
    controls = {p.name[:-8]: json.loads(gzip.decompress(p.read_bytes())) for p in (OLD / 'artifacts/cases').glob('*.json.gz')}
    first_order = v.aggregate(list(controls.values()))
    first_order['T11'] = revised_t11(first_order['T11'], json.loads((EVIDENCE / 'study/artifacts/study.json').read_text(encoding='utf-8')))
    checks['FIRST_ORDER_R4'] = len(controls) == 52 and all(row['status'] == 'PASS' for row in first_order.values())
    regressions = [compare_historical(rpm, json.loads((ROOT / f'results/p0-baseline-0d-20260917/artifacts/points/{rpm}.json').read_text(encoding='utf-8'))) for rpm in HISTORICAL_RPMS]
    checks['P0_regression'] = len(regressions) == 7 and all(r['passed'] for r in regressions)
    checks['P2B'] = all(row['status'] == 'PASS' for row in matrix.values())
    checks['all_final'] = len(records) == 58 and all(r['result']['status'] == 'completed' and r['result']['time'] == r['configuration']['final_time'] for r in records.values())
    checks['T12_ten'] = matrix['T12']['completed_subcases'] == 10 and matrix['T12']['status'] == 'PASS'
    conservation = {}; admissible = True
    for name, record in records.items():
        result = record['result']
        eos = IdealGas(record['configuration']['R'], record['configuration']['gamma'])
        for w in result['primitive']:
            eos.validate(w)
        ext = result['extrema']
        admissible &= min(ext[k] for k in ('min_rho','min_p','min_T')) > 0 and 0 <= ext['min_Y'] <= ext['max_Y'] <= 1
        admissible &= all(min(s[field][:3]) > 0 and 0 <= s[field][3] <= s[field][4] <= 1 for s in result['stage_ledger'] for field in ('stage1_extrema','stage2_extrema'))
        conservation[name] = dict(step=[max(abs(s['normalized'][k]) for s in result['ledger']) for k in range(4)],
            stage=[max(abs(s[field][k]) for s in result['stage_ledger'] for field in ('stage1_normalized','stage2_normalized')) for k in range(4)])
    checks['conservation'] = all(max(r['step'] + r['stage']) <= 1e-10 for r in conservation.values())
    checks['admissibility'] = admissible
    checks['solver_unchanged'] = source_hashes() == json.loads((EVIDENCE_R5 / 'study.json').read_text(encoding='utf-8'))['source_sha256']
    summary = dict(state='P2_READY_FOR_FINAL_INDEPENDENT_REVIEW' if all(checks.values()) else 'P2_BLOCKED_SECOND_ORDER',
        contract='1D_CONTRACT_V1_R5', contract_sha256=sha(contract_path), scientific_review_sha256=sha(EVIDENCE_R5 / 'scientific-review.json'),
        checks=checks, matrix=matrix, historical_T11_R4=r4, first_order_R4=first_order,
        P0_regressions=regressions, provenance=provenance, conservation=conservation,
        runtime_by_case={n:runtime(r) for n,r in records.items()},
        first_order_comparison={n:dict(metrics=r['metrics'],runtime=runtime(r)) for n,r in controls.items()},
        T10_errors={n:r['metrics'] for n,r in records.items() if n.startswith('T10_')},
        performance=dict(current_acquisition_seconds=sum(records[n]['result']['wall_seconds'] for n in ('T10_800','T03_0.2_N1600')),
            maximum_case_seconds=max(r['result']['wall_seconds'] for r in records.values()),
            HLLC=sum(r['result']['hllc_flux_count'] for r in records.values()),
            HLLE=sum(r['result']['hlle_fallback_count'] for r in records.values()),
            RHS=sum(r['result']['rhs_count'] for r in records.values())),
        new_integrations_in_closure=0, P2_HUMAN_ACCEPTED=False, P3='NOT_STARTED')
    art = Path(run_dir) / 'artifacts'
    art.mkdir(parents=True, exist_ok=True)
    write(art / 'closure.json', summary)
    write(art / 'result.json', dict(checks=[dict(id=k, passed=bool(ok), kind='numerical', reason=summary['state']) for k,ok in checks.items()],
        metrics=dict(completed_cases=len(records), new_integrations=0), scientific_change_required=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--run-dir', type=Path, required=True)
    close(parser.parse_args().run_dir)
