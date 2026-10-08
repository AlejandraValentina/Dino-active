"""R4-only verification overlay: frozen product code and original evidence preserved."""
import argparse
import copy
import gzip
import json
from pathlib import Path

from motorsim.gas1d.verification import run_case, definition, measure, aggregate
from .p1_r4_cfl import frozen_checks, differences, numerical_result
from .p2_campaign import ROOT, sha, write

EVIDENCE = ROOT/'results/p1-r4-cfl-20260918'
OLD = ROOT/'results/p1-r3-fronteras-20260918/p2a-attempt-2'


def refinement_checks(study):
    rows={(r['N'],r['CFL']):r for r in study['rows']}
    expected={(n,c) for n in (400,800,1600) for c in (.1,.2,.4,.6)}
    checks={'complete_refinement':set(rows)==expected and len(study['rows'])==12}
    if not checks['complete_refinement']:return checks
    checks['stability_and_ledger']=all(rows[n,c]['stability'] for n in (400,800,1600) for c in (.2,.4,.6))
    checks['parent_accuracy_800_1600']=all(all(rows[n,c]['parent_checks'].values()) for n in (800,1600) for c in (.2,.4,.6))
    for a,b in ((.2,.4),(.4,.6),(.2,.6)):
        s=[differences(rows[n,a]['amplitude_Pa'],rows[n,b]['amplitude_Pa'])['normalized'] for n in (400,800,1600)]
        checks[f'sensitivity_decreases_{a}_{b}']=s[0]>s[1]>s[2]
    for c in (.2,.4,.6):
        error=[rows[n,c]['analytical_amplitude_error'] for n in (400,800,1600)]
        checks[f'analytical_error_decreases_{c}']=error[0]>error[1]>error[2]
    return checks


def revised_t11(original, study):
    checks=copy.deepcopy(original['checks'])
    # Only these two comparisons were superseded, not parent tests or Sod/speed.
    superseded={k:checks.pop(k) for k in ('pulse_0.4_amplitude','pulse_0.6_amplitude')}
    checks.update(refinement_checks(study))
    return dict(status='PASS' if all(checks.values()) else 'FAIL',checks=checks,
                original_metrics=original['metrics'],superseded_diagnostics=superseded,
                contract='1D_CONTRACT_V1_R4')


def verify_inventory(folder):
    inventory=json.loads((folder/'artifacts/inventory.json').read_text(encoding='utf-8'))
    if not all(sha(folder/p)==h for p,h in inventory.items()):raise ValueError('Evidence inventory mismatch')


def verify(run_dir):
    art=run_dir/'artifacts';(art/'cases').mkdir()
    checks=frozen_checks()
    review=json.loads((EVIDENCE/'reviewed-evidence.json').read_text(encoding='utf-8'))
    checks['r4_scientific_review']=review['gate']=='PASS' and review['review']['kind']=='independent'
    if not all(checks.values()):raise ValueError('Frozen source/review failed')
    verify_inventory(OLD);verify_inventory(EVIDENCE/'study')
    study=json.loads((EVIDENCE/'study/artifacts/study.json').read_text(encoding='utf-8'))
    old_summary=json.loads((OLD/'artifacts/p2a-summary.json').read_text(encoding='utf-8'))
    checks['previous_campaign_source_identical']=all(sha(ROOT/p)==h for p,h in old_summary['source_sha256'].items())
    if not checks['previous_campaign_source_identical']:raise ValueError('Previous campaign source mismatch')
    records={}
    for p in (OLD/'artifacts/cases').glob('*.json.gz'):
        record=json.loads(gzip.decompress(p.read_bytes()));records[record['name']]=record
    fresh=[];determinism={}
    for name in [f'T02_sod_{c}' for c in (.2,.4,.6)]+[f'T03_{c}' for c in (.2,.4,.6)]:
        print('START_T11 '+name,flush=True)
        record=run_case(name)
        raw=json.dumps(record,allow_nan=False,separators=(',',':')).encode()
        (art/'cases'/f'{name}.json.gz').write_bytes(gzip.compress(raw,mtime=0))
        old=records[name]
        deterministic=(json.loads(json.dumps(numerical_result(record['result'])))==numerical_result(old['result'])
                       and record['metrics']==old['metrics'] and record['checks']==old['checks'])
        determinism[name]=deterministic;records[name]=record;fresh.append(name)
        write(art/'checkpoint.json',dict(fresh=fresh,determinism=determinism))
        print('END_T11 '+name+' '+record['status']+' deterministic='+str(deterministic),flush=True)
        if record['status']!='PASS' or not deterministic:break
    checks['six_fresh_t11']=len(fresh)==6 and all(determinism.values())
    # Aggregate comparisons use unchanged original routines first.
    original=aggregate(list(records.values()))
    t11=revised_t11(original['T11'],study)
    checks['T11_R4']=checks['six_fresh_t11'] and t11['status']=='PASS'
    write(art/'t11-r4.json',dict(original=original['T11'],revised=t11,fresh=fresh,determinism=determinism,
                              state='T11_R4_PASS' if checks['T11_R4'] else 'T11_R4_BLOCKED'))
    print('T11_R4_PASS' if checks['T11_R4'] else 'T11_R4_BLOCKED',flush=True)
    matrix=None;remeasured={}
    if checks['T11_R4']:
        print('START_OFFLINE_P2A_REGRESSION',flush=True)
        # Re-evaluate all 52 records, without claiming 52 new integrations.
        for name,r in records.items():
            metrics,criteria=measure(definition(name),r['result'],r['reference'],r['initial'])
            remeasured[name]=metrics==r['metrics'] and criteria==r['checks']
            r['metrics']=metrics;r['checks']=criteria;r['status']='PASS' if all(criteria.values()) else 'FAIL'
        matrix=aggregate(list(records.values()));matrix['T11']=revised_t11(matrix['T11'],study)
    checks['offline_52_remeasured']=len(remeasured)==52 and all(remeasured.values())
    checks['P2A_R4']=matrix is not None and all(r['status']=='PASS' for r in matrix.values()) and checks['offline_52_remeasured']
    checks.update(frozen_checks())
    summary=dict(state='P2A_READY_FOR_INDEPENDENT_REVIEW' if all(checks.values()) else 'P2A_BLOCKED',
                 checks=checks,matrix=matrix,t11=t11,determinism=determinism,offline_remeasurement=remeasured,
                 newly_integrated_cases=fresh,reused_case_count=52-len(fresh),
                 previous_evidence=OLD.relative_to(ROOT).as_posix(),previous_inventory_sha256=sha(OLD/'artifacts/inventory.json'),
                 study_evidence=EVIDENCE.relative_to(ROOT).as_posix()+'/study',
                 study_inventory_sha256=sha(EVIDENCE/'study/artifacts/inventory.json'),
                 contract_sha256=sha(ROOT/'docs/gasdynamic/1d_contract_v1_r4.json'),
                 P2B='NOT_STARTED',P3='NOT_STARTED',human_acceptance='NOT_ATTRIBUTED')
    write(art/'p2a-r4.json',summary)
    write(art/'result.json',dict(checks=[dict(id=k,passed=v,kind='numerical',reason='R4 overlay; previous evidence preserved') for k,v in checks.items()],
                               metrics=dict(new_integrations=len(fresh),reevaluated_records=len(remeasured)),scientific_change_required=False))
    write(art/'inventory.json',{p.relative_to(run_dir).as_posix():sha(p) for p in art.rglob('*') if p.is_file() and p.name!='inventory.json'})


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--run-dir',type=Path,required=True)
    verify(parser.parse_args().run_dir)
