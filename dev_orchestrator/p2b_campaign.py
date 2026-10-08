"""Bounded P2B verification; frozen first-order evidence is the control."""
import argparse
import gzip
import json
import math
import time
from pathlib import Path

from motorsim.gas1d import verification as v
from motorsim.gas1d.methods import solve
from motorsim.gas1d.mesh import uniform_mesh
from motorsim.gas1d.reference import cell_integrals, primitives
from .p2_campaign import ROOT, sha, write, invariants
from .p1_r4_gate import OLD, EVIDENCE, verify_inventory, revised_t11

FROZEN=ROOT/'results/p2b-gas1d-20260918/frozen-p2a.json'


def stage_cfl_valid(result):
    # Same floating-point inequality used by the integrator; no tolerance or altered CFL.
    return all(s['accepted_dt']<=min(s['stage1_dt_limit'],s['stage2_dt_limit']) for s in result['stage_ledger'])


def frozen_checks():
    checks=invariants()
    checks['first_order_contracts_frozen']=all(sha(ROOT/p)==h for p,h in json.loads(FROZEN.read_text(encoding='utf-8')).items())
    for name,status in (('p1_r4','P1_R4_HUMAN_ACCEPTED'),('p2a','P2A_HUMAN_ACCEPTED')):
        receipt=json.loads((ROOT/f'docs/gasdynamic/{name}_human_acceptance.json').read_text(encoding='utf-8'))
        checks[name+'_accepted']=receipt['status']==status and receipt['actor']=='usuaria'
    return checks


def run_case(name, control=None, n=None, *, wall_limit=None):
    case=v.definition(name)
    if n is not None:case['mesh']=uniform_mesh(n)
    mesh=case['mesh'];eos=case['eos']
    initial=cell_integrals(mesh,case['initial'],eos,case['area'],case['breaks'])
    reference=cell_integrals(mesh,case['reference'],eos,case['area'],case['refbreaks'])
    result=solve(mesh,initial,case['end'],case['bc'],method='MUSCL_SSPRK2',eos=eos,cfl=case['cfl'],
                 sensor=case['sensor'],sample_interval=case['interval'],wall_limit=(240. if name=='T10_800' else 120.) if wall_limit is None else wall_limit,
                 progress=lambda step,t:print(f'PROGRESS {name} N={mesh.n} step={step} t={t:.8g}',flush=True) if step%2000==0 else None)
    metrics,checks=v.measure(case,result,reference,initial)
    metrics['worst_stage_ledger']=max((max(s[k]) for s in result['stage_ledger'] for k in ('stage1_normalized','stage2_normalized')),default=0.)
    checks['stage_conservation']=metrics['worst_stage_ledger']<=1e-10
    checks['stage_CFL']=stage_cfl_valid(result)
    if result['status']=='completed':
        if case['test'] in ('T04','T05'):checks['reflection_error']=metrics['reflection_error']<=.15
        if control and case['test'] in ('T02','T06'):
            for field in (('rho','u','p') if case['test']=='T02' else ('rho','Y')):
                checks['no_worse_first_order_'+field]=metrics['errors'][field]['L1']<=control['metrics']['errors'][field]['L1']+1e-10
        if case['test']=='T10':
            for field,k in (('density',0),('fresh',3)):
                metrics[field+'_L2']=v.norms([c[k]/vol for c,vol in zip(result['cells'],mesh.volumes)],
                    [c[k]/vol for c,vol in zip(reference,mesh.volumes)],mesh.volumes,v.RHO)['L2']
        if case['test']=='T03':
            exact_amplitude=max(w[2]-v.P0 for w in primitives(mesh,reference,eos))
            metrics.update(analytical_amplitude=exact_amplitude,
                analytical_amplitude_error=abs(metrics['amplitude']-exact_amplitude)/10.,
                phase_displacement_error=(metrics['speed']-v.A0)*case['end'],
                dissipation=1-metrics['amplitude_ratio'])
    return dict(name=name if n is None else f'{name}_N{n}',status='PASS' if all(checks.values()) else 'FAIL',checks=checks,metrics=metrics,
                configuration=dict(N=mesh.n,CFL=case['cfl'],R=eos.R,gamma=eos.gamma,final_time=case['end'],method='MUSCL_SSPRK2',
                                   boundaries='periodic' if case['bc']=='periodic' else [b.__dict__ for b in case['bc']]),
                mesh=mesh.as_dict(),initial=initial,reference=reference,result=result)


def full_matrix(records, refinement):
    rows=v.aggregate(records)
    for field in ('density_L1','fresh_L1'):
        for n,m in ((100,200),(200,400),(400,800)):
            key=f'order_{n}_{m}_{field}';order=rows['T10']['metrics'][key]
            if n==100:rows['T10']['checks'].pop(key)  # Diagnostic pair, original P1 contractual pairs start at 200.
            else:rows['T10']['checks'][key]=order is not None and order>=1.5
    # R4-only amplitude refinement, explicitly extended to MUSCL by this order.
    t11=rows['T11'];t11['historical_8_percent_diagnostic']={}
    for c in (.4,.6):
        key=f'pulse_{c}_amplitude'
        t11['historical_8_percent_diagnostic'][key]=t11['checks'].pop(key)
    data={(r['configuration']['N'],r['configuration']['CFL']):r for r in refinement}
    t11['checks']['complete_refinement']=set(data)=={(n,c) for n in (400,800,1600) for c in (.2,.4,.6)}
    t11['checks']['refinement_stability']=all(r['result']['status']=='completed' and r['checks']['worst_ledger'] and r['checks']['stage_conservation'] and r['checks']['stage_CFL'] for r in refinement)
    t11['checks']['parent_accuracy_800_1600']=all(r['status']=='PASS' for r in refinement if r['configuration']['N']>=800)
    for a,b in ((.2,.4),(.4,.6),(.2,.6)):
        values=[abs(data[n,a]['metrics']['amplitude']-data[n,b]['metrics']['amplitude'])/10. for n in (400,800,1600)]
        key=f'sensitivity_{a}_{b}';t11['metrics'][key]=values;t11['checks'][key]=values[0]>values[1]>values[2]
    for c in (.2,.4,.6):
        values=[data[n,c]['metrics']['analytical_amplitude_error'] for n in (400,800,1600)]
        key=f'analytical_error_{c}';t11['metrics'][key]=values;t11['checks'][key]=values[0]>values[1]>values[2]
    for row in rows.values():row['status']='PASS' if all(row['checks'].values()) else 'FAIL'
    return rows


def partial_matrix(records):
    rows={f'T{i:02}':dict(status='NOT_RUN',checks={}) for i in range(1,13)}
    for r in records:
        test='T11' if r['name'].startswith(('T02_sod_','T03_')) else r['name'][:3]
        rows[test]['checks'][r['name']]=r['status']=='PASS'
    for test,row in rows.items():
        if row['checks']:row['status']='PARTIAL' if all(row['checks'].values()) else 'FAIL'
        expected={n for n in v.case_names() if ('T11' if n.startswith(('T02_sod_','T03_')) else n[:3])==test}
        if test not in ('T08','T10','T11') and set(row['checks'])==expected and all(row['checks'].values()):row['status']='PASS'
    return rows


def campaign(run_dir):
    started=time.monotonic();art=run_dir/'artifacts';(art/'cases').mkdir()
    checks=frozen_checks()
    if not all(checks.values()):raise ValueError('Frozen dependency failed '+str(checks))
    verify_inventory(OLD);verify_inventory(EVIDENCE/'study')
    controls={p.name[:-8]:json.loads(gzip.decompress(p.read_bytes())) for p in (OLD/'artifacts/cases').glob('*.json.gz')}
    control_rows=v.aggregate(list(controls.values()))
    study=json.loads((EVIDENCE/'study/artifacts/study.json').read_text(encoding='utf-8'))
    control_rows['T11']=revised_t11(control_rows['T11'],study)
    checks['first_order_R4_control']=all(row['status']=='PASS' for row in control_rows.values())
    write(art/'first-order-control.json',dict(matrix=control_rows,evidence=str(OLD.relative_to(ROOT)),mode='offline frozen records; no new first-order campaign'))
    records=[];refinement=[];hashes={}
    # Positivity before expensive smooth/refinement cases. Never continue through an unresolved numerical failure.
    early=['T01_rest','T01_moving','T12_expansion','T12_contact','T12_pure0','T12_pure1']
    names=early+[n for n in v.case_names() if n not in early]
    def save(r):
        target=art/'cases'/(r['name']+'.json.gz')
        target.write_bytes(gzip.compress(json.dumps(r,allow_nan=False,separators=(',',':')).encode(),mtime=0))
        hashes[target.relative_to(run_dir).as_posix()]=sha(target)
        write(art/'checkpoint.json',dict(latest=r['name'],status=r['status'],hashes=hashes))
        print('END '+r['name']+' '+r['status']+' '+str(r['result']['wall_seconds'])+' '+str([k for k,val in r['checks'].items() if not val]),flush=True)
    for name in names:
        print('START '+name,flush=True)
        r=run_case(name,controls.get(name));save(r);records.append(r)
        if name.startswith('T03_'):refinement.append(r)
        if r['status']!='PASS':break
    if len(records)==52 and all(r['status']=='PASS' for r in records):
        for n in (400,1600):
            for c in (.2,.4,.6):
                print(f'START T03_{c}_N{n}',flush=True)
                r=run_case(f'T03_{c}',n=n);save(r);refinement.append(r)
                if r['result']['status']!='completed':break
            if refinement[-1]['result']['status']!='completed':break
    complete=len(records)==52 and len(refinement)==9 and all(r['result']['status']=='completed' for r in refinement)
    matrix=full_matrix(records,refinement) if complete else partial_matrix(records)
    checks.update(frozen_checks());checks['P2B']=complete and all(row['status']=='PASS' for row in matrix.values())
    allrecords=records+[r for r in refinement if r not in records]
    infrastructure=any(r['result']['status']=='failed_infrastructure' for r in allrecords)
    state='P2B_READY_FOR_INDEPENDENT_REVIEW' if checks['P2B'] else 'P2_BLOCKED_SECOND_ORDER'
    if any(r['result']['status']=='failed_numerical' for r in allrecords):state='P2_BLOCKED_POSITIVITY'
    if infrastructure:state='FAILED_INFRASTRUCTURE'
    if not checks['baseline_intact']:state='P2_BLOCKED_REGRESSION'
    def brief(r):
        return {k:r[k] for k in ('name','status','checks','metrics','configuration')} | dict(runtime={k:val for k,val in r['result'].items() if k not in ('cells','primitive','temperature','Mach','face_fluxes','ledger','stage_ledger','sensors')})
    summary=dict(state=state,matrix=matrix,checks=checks,cases=[brief(r) for r in allrecords],
        first_order_comparison=[dict(name=r['name'],first_order_metrics=controls[r['name']]['metrics'],first_order_runtime={k:controls[r['name']]['result'].get(k) for k in ('steps','wall_seconds','extrema','hllc_flux_count','hlle_fallback_count','fallback_reason')}) for r in records],
        wall_seconds=time.monotonic()-started,source_sha256={p.relative_to(ROOT).as_posix():sha(p) for p in (ROOT/'motorsim/gas1d').glob('*.py')},
        contract='1D_CONTRACT_V1_R4',P3='NOT_STARTED',human_acceptance='P2_NOT_ACCEPTED',repair_attempt=json.loads((FROZEN.parent/'repair-budget.json').read_text(encoding='utf-8'))['used'],
        note='STOP at first unresolved failure; partial tests do not constitute a complete gate. Review must classify science versus implementation.')
    write(art/'p2b-summary.json',summary)
    write(art/'result.json',dict(checks=[dict(id=k,passed=value,kind='numerical' if k in ('P2B','first_order_R4_control') else 'infrastructure',reason=state) for k,value in checks.items()],metrics=dict(cases=len(allrecords),wall_seconds=summary['wall_seconds']),scientific_change_required=False))
    write(art/'inventory.json',{p.relative_to(run_dir).as_posix():sha(p) for p in art.rglob('*') if p.is_file() and p.name!='inventory.json'})


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--run-dir',type=Path,required=True)
    campaign(parser.parse_args().run_dir)
