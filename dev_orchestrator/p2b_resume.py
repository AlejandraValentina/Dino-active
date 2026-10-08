"""P2B infrastructure-only resume: 300 s/case, T04 first, durable checkpoints."""
import argparse
import gzip
import hashlib
import json
import math
import subprocess
import time
from pathlib import Path

from motorsim.gas1d import verification as v
from motorsim.gas1d.reference import cell_integrals
from motorsim.gas1d.mesh import uniform_mesh
from .p2_campaign import ROOT,sha
from .p2b_campaign import run_case,frozen_checks,partial_matrix,full_matrix
from .p1_r4_gate import OLD,EVIDENCE,verify_inventory,revised_t11

PREVIOUS=ROOT/'results/p2b-gas1d-20260918/attempt-2'
WALL_LIMIT=300.


def read(path):return json.loads(Path(path).read_text(encoding='utf-8'))


def write(path,value):
    path=Path(path);temp=path.with_suffix(path.suffix+'.tmp')
    temp.write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    temp.replace(path)


def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def source_hashes():return {p.relative_to(ROOT).as_posix():sha(p) for p in (ROOT/'motorsim/gas1d').glob('*.py')}


def signature(record):
    return digest({k:record[k] for k in ('configuration','mesh','initial','reference')})


def expected_signature(name,n=None):
    case=v.definition(name)
    if n is not None:case['mesh']=uniform_mesh(n)
    mesh=case['mesh'];eos=case['eos']
    return signature(dict(configuration=dict(N=mesh.n,CFL=case['cfl'],R=eos.R,gamma=eos.gamma,final_time=case['end'],method='MUSCL_SSPRK2',
            boundaries='periodic' if case['bc']=='periodic' else [b.__dict__ for b in case['bc']]),mesh=mesh.as_dict(),
        initial=cell_integrals(mesh,case['initial'],eos,case['area'],case['breaks']),
        reference=cell_integrals(mesh,case['reference'],eos,case['area'],case['refbreaks'])))


def load_reusable(folder,expected_source,*,retain_timeouts=False):
    folder=Path(folder)
    folder=(folder if folder.is_absolute() else ROOT/folder).resolve()
    checkpoint=folder/'artifacts/resume-checkpoint.json'
    if checkpoint.exists():
        manifest=read(checkpoint);sources=manifest['source_sha256'];entries=manifest['cases']
    else:
        manifest=read(folder/'artifacts/p2b-summary.json');sources=manifest['source_sha256']
        entries={Path(p).name[:-8]:dict(path=p,sha256=h) for p,h in read(folder/'artifacts/inventory.json').items() if p.startswith('artifacts/cases/')}
    if sources!=expected_source:raise ValueError('Resume solver/source hashes differ; reuse refused')
    records={};origins={}
    for name,item in entries.items():
        path=folder/item['path']
        if sha(path)!=item['sha256']:raise ValueError('Resume artifact hash mismatch: '+name)
        record=json.loads(gzip.decompress(path.read_bytes()))
        if record['name']!=name:raise ValueError('Resume case identity mismatch')
        passed=record['status']=='PASS' and record['result']['status']=='completed'
        retained=(retain_timeouts and name!='T04' and record['result']['status']=='failed_infrastructure'
            and record['result']['reason']=='wall_timeout' and all(record['checks'].get(k,False) for k in ('worst_ledger','stage_conservation','stage_CFL')))
        if not passed and not retained:continue
        base,sep,n=name.partition('_N')
        expected=expected_signature(base,int(n) if sep else None)
        if signature(record)!=expected:raise ValueError('Resume inputs/configuration differ: '+name)
        records[name]=record;origins[name]=dict(path=path.relative_to(ROOT).as_posix(),sha256=item['sha256'],input_sha256=expected,
            solver_revision='4620200',accepted=passed,
            reason='Identical solver files, inputs, configuration and evidence hash; no reintegration' if passed else 'Retained timeout, NOT credited as PASS; no reintegration')
    return records,origins


def test_id(name):return 'T11' if name.startswith(('T02_sod_','T03_')) else name[:3]


def test_gate(test,records):
    names=[n for n in v.case_names() if test_id(n)==test]
    if test=='T11':names += [f'T03_{c}_N{n}' for n in (400,1600) for c in (.2,.4,.6)]
    selected={n:records[n] for n in names if n in records}
    checks={n:r['status']=='PASS' for n,r in selected.items()};metrics={}
    if test=='T11':
        for name,r in selected.items():
            if name.endswith('_N400'):
                checks[name]=r['result']['status']=='completed' and all(r['checks'][k] for k in ('worst_ledger','stage_conservation','stage_CFL'))
    complete=len(selected)==len(names)
    # A missing independent case must not hide a comparison whose inputs are complete.
    if selected:
        if test=='T08':
            for geom in ('constant','smooth','frustum'):
                for n,m in ((100,200),(200,400)):
                    if not all(selected.get(f'T08_{geom}_flow_{size}',{}).get('status')=='PASS' for size in (n,m)):continue
                    for field in ('rho','u','p'):
                        a=selected[f'T08_{geom}_flow_{n}']['metrics']['errors'][field]['L1'];b=selected[f'T08_{geom}_flow_{m}']['metrics']['errors'][field]['L1']
                        key=f'{geom}_{n}_{m}_{field}';checks[key]=b<=a+1e-12;metrics[key]=dict(coarse=a,fine=b)
        if test=='T10':
            for n,m in ((100,200),(200,400),(400,800)):
                if not all(selected.get(f'T10_{size}',{}).get('status')=='PASS' for size in (n,m)):continue
                for field in ('density_L1','fresh_L1'):
                    a=selected[f'T10_{n}']['metrics'][field];b=selected[f'T10_{m}']['metrics'][field]
                    order=math.log2(a/b) if a>0 and b>0 else None
                    key=f'order_{n}_{m}_{field}';metrics[key]=order
                    if n!=100:checks[key]=order is not None and order>=1.5
        if test=='T11':
            for c in (.4,.6):
                if all(selected.get(name,{}).get('status')=='PASS' for name in ('T02_sod_0.2',f'T02_sod_{c}')):
                    a=selected['T02_sod_0.2'];b=selected[f'T02_sod_{c}']
                    for k,field in enumerate(('rho','u','p')):
                        error=v.norms([w[k] for w in a['result']['primitive']],[w[k] for w in b['result']['primitive']],a['mesh']['volumes'],1.)['L1']
                        key=f'Sod_{c}_{field}';metrics[key]=error;checks[key]=error<=.015
                if all(selected.get(name,{}).get('status')=='PASS' for name in ('T03_0.2',f'T03_{c}')):
                    error=abs(selected['T03_0.2']['metrics']['speed']-selected[f'T03_{c}']['metrics']['speed'])/v.A0
                    key=f'pulse_{c}_speed';metrics[key]=error;checks[key]=error<=.005
            data={(r['configuration']['N'],r['configuration']['CFL']):r for name,r in selected.items() if name.startswith('T03_') and r['result']['status']=='completed'}
            for a,b in ((.2,.4),(.4,.6),(.2,.6)):
                if not all((n,c) in data for n in (400,800,1600) for c in (a,b)):continue
                vals=[abs(data[n,a]['metrics']['amplitude']-data[n,b]['metrics']['amplitude'])/10 for n in (400,800,1600)]
                key=f'sensitivity_{a}_{b}';metrics[key]=vals;checks[key]=vals[0]>vals[1]>vals[2]
            for c in (.2,.4,.6):
                if not all((n,c) in data for n in (400,800,1600)):continue
                vals=[data[n,c]['metrics']['analytical_amplitude_error'] for n in (400,800,1600)]
                key=f'analytical_error_{c}';metrics[key]=vals;checks[key]=vals[0]>vals[1]>vals[2]
    status='PASS' if complete and all(checks.values()) else ('FAIL' if checks and not all(checks.values()) else ('PARTIAL' if checks else 'NOT_RUN'))
    return dict(status=status,checks=checks,metrics=metrics,recorded_subcases=len(selected),
                completed_subcases=sum(r.get('result',{}).get('status','completed' if r['status']=='PASS' else '')=='completed' for r in selected.values()),expected_subcases=len(names))


def runtime(r):
    keys=('status','reason','time','steps','rhs_count','wall_seconds','minimum_dt','maximum_dt','max_CFL','rejected_steps','rejection_reasons','extrema',
          'hllc_flux_count','hlle_fallback_count','characteristic_flux_count','riemann_flux_count','fallback_reason','downgrade_count')
    return {k:r['result'].get(k) for k in keys}


def classify_state(checks,stop,failures):
    if not checks['baseline_intact'] or not checks['solver_unchanged']:return 'P2_BLOCKED_REGRESSION'
    if stop:
        if stop.get('solver_status')=='failed_numerical':return 'P2_BLOCKED_POSITIVITY'
        if stop.get('solver_status')=='completed' or stop.get('reason')=='contractual aggregate failure':return 'P2_BLOCKED_SECOND_ORDER'
    if any(f.get('solver_status')=='failed_infrastructure' for f in failures):return 'FAILED_INFRASTRUCTURE'
    return 'P2B_READY_FOR_INDEPENDENT_REVIEW' if all(checks.values()) else 'P2_BLOCKED_SECOND_ORDER'


def only_infrastructure_failure(gate,failures,test):
    failed={key for key,passed in gate['checks'].items() if not passed}
    timed_out={f['case'] for f in failures if f['test']==test and f.get('solver_status')=='failed_infrastructure'}
    return bool(failed) and failed<=timed_out


def campaign(run_dir,resume=None,start_at=4):
    started=time.monotonic();art=run_dir/'artifacts';(art/'cases').mkdir()
    sources=source_hashes();checks=frozen_checks()
    if not all(checks.values()):raise ValueError('Frozen checks failed')
    available,origins=load_reusable(PREVIOUS,sources)
    if start_at!=4 and resume is None:raise ValueError('Starting later requires explicit checkpoint')
    if resume:
        extra,provenance=load_reusable(resume,sources,retain_timeouts=start_at>4);available.update(extra);origins.update(provenance)
    verify_inventory(OLD);verify_inventory(EVIDENCE/'study')
    controls={p.name[:-8]:json.loads(gzip.decompress(p.read_bytes())) for p in (OLD/'artifacts/cases').glob('*.json.gz')}
    control=v.aggregate(list(controls.values()));control['T11']=revised_t11(control['T11'],read(EVIDENCE/'study/artifacts/study.json'))
    checks['first_order_R4_control']=all(r['status']=='PASS' for r in control.values())
    write(art/'first-order-control.json',dict(matrix=control,reused_evidence=OLD.relative_to(ROOT).as_posix(),new_integrations=0))
    records={};entries={};reused={};retained={};fresh=[];matrix={};stop=None;failures=[]
    def checkpoint():
        write(art/'resume-checkpoint.json',dict(source_sha256=sources,solver_revision='4620200',cases=entries,reused=reused,retained_incomplete=retained,fresh=fresh,matrix=matrix,
            timeout=dict(old_timeout=120,new_timeout=300,previous_T10_800_exception=240,reason='infrastructure/runtime only'),solver_inputs_unchanged=True))
        write(art/'inventory.json',{p.relative_to(run_dir).as_posix():sha(p) for p in art.rglob('*') if p.is_file() and p.name!='inventory.json'})
    def obtain(name,n=None):
        key=name if n is None else f'{name}_N{n}'
        if key in available:
            r=available[key]
            if r['status']=='PASS':reused[key]=origins[key]
            else:retained[key]=origins[key]
            print(('REUSE ' if r['status']=='PASS' else 'RETAIN_INCOMPLETE ')+key+' '+origins[key]['sha256'],flush=True)
            target=art/'cases'/(key+'.json.gz');target.write_bytes((ROOT/origins[key]['path']).read_bytes())
        else:
            print('START '+key+' timeout=300',flush=True)
            r=run_case(name,controls.get(name),n,wall_limit=WALL_LIMIT)
            target=art/'cases'/(key+'.json.gz');temp=target.with_suffix('.tmp')
            temp.write_bytes(gzip.compress(json.dumps(r,allow_nan=False,separators=(',',':')).encode(),mtime=0));temp.replace(target)
            fresh.append(key)
            print('END '+key+' '+r['status']+' '+str(r['result']['wall_seconds'])+' '+str([k for k,x in r['checks'].items() if not x]),flush=True)
        records[key]=r;entries[key]=dict(path=target.relative_to(run_dir).as_posix(),sha256=sha(target),input_sha256=signature(r))
        checkpoint()
        return r
    for name in ('T01_rest','T01_moving','T02_sod','T03'):
        if name not in available:raise ValueError('Missing required baseline passed record: '+name)
        obtain(name)
    for i in range(1,4):matrix[f'T{i:02}']=test_gate(f'T{i:02}',records)
    for i in range(4,start_at):
        test=f'T{i:02}'
        for name in (n for n in v.case_names() if test_id(n)==test):
            if name not in available:raise ValueError('Cannot skip unverified earlier case: '+name)
            r=obtain(name)
            if r['status']!='PASS':failures.append(dict(test=test,case=name,solver_status=r['result']['status'],reason=r['result']['reason']))
        matrix[test]=test_gate(test,records)
        if i==4 and matrix[test]['status']!='PASS':raise ValueError('T04 must PASS before later verification')
        if matrix[test]['status']!='PASS' and not only_infrastructure_failure(matrix[test],failures,test):raise ValueError('Cannot skip scientific aggregate failure: '+test)
    # T04 must PASS before any later integration.
    # An explicitly retained later timeout is incomplete, not a scientific gate; independent tests may proceed.
    for i in range(start_at,13):
        test=f'T{i:02}';names=[(name,None) for name in v.case_names() if test_id(name)==test]
        if test=='T11':names += [(f'T03_{c}',n) for n in (400,1600) for c in (.2,.4,.6)]
        for name,n in names:
            r=obtain(name,n)
            diagnostic_coarse=test=='T11' and n==400 and r['result']['status']=='completed' and all(r['checks'][k] for k in ('worst_ledger','stage_conservation','stage_CFL'))
            if r['status']!='PASS' and not diagnostic_coarse:
                failure=dict(test=test,case=r['name'],solver_status=r['result']['status'],reason=r['result']['reason']);failures.append(failure)
                timeout_only=(start_at>4 and test!='T04' and r['result']['status']=='failed_infrastructure' and r['result']['reason']=='wall_timeout'
                    and all(r['checks'].get(k,False) for k in ('worst_ledger','stage_conservation','stage_CFL')))
                if not timeout_only:stop=failure;break
        matrix[test]=test_gate(test,records);checkpoint()
        if stop or matrix[test]['status']!='PASS':
            if stop is None and start_at>4 and only_infrastructure_failure(matrix[test],failures,test):continue
            if stop is None:stop=dict(test=test,reason='contractual aggregate failure')
            break
    for i in range(1,13):matrix.setdefault(f'T{i:02}',test_gate(f'T{i:02}',records))
    # Preserve existing T12 evidence even if an earlier gate blocks this resume.
    for name in ('T12_expansion','T12_contact','T12_pure0','T12_pure1'):
        if name not in records and name in available:obtain(name)
    matrix['T12']=test_gate('T12',records)
    checks.update(frozen_checks());checks['solver_unchanged']=source_hashes()==sources
    checks['P2B']=len(matrix)==12 and all(r['status']=='PASS' for r in matrix.values())
    if checks['P2B']:
        base=[records[n] for n in v.case_names()];ref=[r for n,r in records.items() if n.startswith('T03_')]
        original=full_matrix(base,ref)
        checks['aggregate_equivalence']=all(original[k]['status']==matrix[k]['status'] for k in matrix)
    state=classify_state(checks,stop,failures)
    summary=dict(state=state,checks=checks,matrix=matrix,stop=stop,failures=failures,source_sha256=sources,solver_revision='4620200',fresh=fresh,reused=reused,retained_incomplete=retained,
        cases=[{k:r[k] for k in ('name','status','checks','metrics','configuration')} | dict(runtime=runtime(r)) for r in records.values()],
        wall_seconds=time.monotonic()-started,P3='NOT_STARTED',P2_HUMAN_ACCEPTED=False,
        first_order_comparison=[dict(name=n,metrics=controls[n]['metrics'],runtime=runtime(controls[n])) for n in records if n in controls],
        timeout=dict(old_timeout=120,new_timeout=300,previous_T10_800_exception=240,reason='infrastructure/runtime only'))
    write(art/'p2b-summary.json',summary)
    write(art/'result.json',dict(checks=[dict(id=k,passed=ok,kind='numerical' if k in ('P2B','first_order_R4_control','aggregate_equivalence') else 'infrastructure',reason=state) for k,ok in checks.items()],
        metrics=dict(fresh_cases=len(fresh),reused_cases=len(reused),wall_seconds=summary['wall_seconds']),scientific_change_required=False))
    checkpoint()


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--run-dir',type=Path,required=True);parser.add_argument('--resume',type=Path)
    parser.add_argument('--start-at',type=int,choices=range(4,13),default=4)
    args=parser.parse_args();campaign(args.run_dir,args.resume,args.start_at)
