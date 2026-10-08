"""Frozen P3B synthetic cases; no engine geometry or production simulation."""
import argparse
from dataclasses import asdict
import gzip
import json
from pathlib import Path
from motorsim.coupled import solve_coupled
from motorsim.gas1d.eos import IdealGas
from motorsim.gas1d.mesh import uniform_mesh
from .p3_r1 import chamber
from .p2_campaign import ROOT, sha, write


def common_checks(r):
    e=r['extrema']
    return dict(completed=r['status']=='completed',
        conservation=max((max(x['normalized']) for x in r['ledger']),default=float('inf'))<=1e-10,
        stages=max((max(v) for x in r['stage_ledger'] for v in x['normalized']),default=float('inf'))<=1e-10,
        CFL=all(x['dt']<=min(x['limits']) for x in r['stage_ledger']),
        positivity=min(e[k] for k in ('rho','p','T','m','U'))>0 and e['F_min']>=0 and e['m_minus_F']>=0 and 0<=e['Y_min']<=e['Y_max']<=1)


def species_audit(r):
    errors=[]
    for row in r['traces']:
        for stage in row['stages']:
            if stage['fallback_reason']:
                # No donor replacement for HLLE. Full vector is retained by interface.
                continue
            m,_,_,f=stage['outward']
            y=stage['pipe_face'][3] if m>=0 else stage['Y_chamber']
            errors.append(abs(f-m*y)/max(1.,abs(m)))
    return max(errors,default=0.)


def run_case(label,method,n=60,cfl=.4):
    eos=IdealGas();mesh=uniform_mesh(n,.3,.0003)
    pressure=100000. if label=='equilibrium' else (80000. if label=='filling' else 120000.)
    ch=chamber(pressure,Y=.3 if label=='equilibrium' else .8,V=.0001)
    w=(100000/(287*300),0.,100000.,.3 if label=='equilibrium' else .2)
    initial=[tuple(x*v for x in eos.conservative(w)) for v in mesh.volumes]
    end=.0015 if label=='equilibrium' else (.004 if label=='reversal' else .0003)
    r=solve_coupled(mesh,initial,ch,end,method=method,eos=eos,cfl=cfl,wall_limit=300.)
    checks=common_checks(r);checks['species']=species_audit(r)<=1e-12
    if label=='equilibrium':
        drift=max(abs(b-a)/scale for row in r['primitive'] for a,b,scale in zip(w,row,(w[0],eos.sound_speed(w),w[2],1.)))
        drift=max(drift,*(abs(b-a)/a for a,b in zip(r['initial_chamber'],r['chamber'])))
        checks['equilibrium']=drift<=1e-12
    if label in ('blowdown','filling'):
        sign=1 if label=='filling' else -1
        checks['mass_energy_direction']=all(sign*(r['chamber'][k]-r['initial_chamber'][k])>0 for k in (0,1))
        checks['wave_sign']=-sign*(r['primitive'][0][2]-100000)>0
    if label=='reversal':checks['natural_reversal']=bool(r['reversals'])
    return dict(name=label+'_'+method,inputs=dict(N=n,CFL=cfl,method=method,final_time=end,chamber=asdict(ch),pipe_state=w,length=.3,area=.0003),
        initial=initial,checks=checks,status='PASS' if all(checks.values()) else 'FAIL',species_error=species_audit(r),result=r)


def campaign(run_dir):
    art=Path(run_dir)/'artifacts';(art/'cases').mkdir(parents=True)
    review=json.loads((ROOT/'results/p3-r1-20260918/r1-reviewed.json').read_text(encoding='utf-8'))
    if review['state']!='P3_R1_PASS_RIEMANN_COUPLING' or review['interface_sha256']!=sha(ROOT/'motorsim/coupling.py'):
        raise ValueError('R1 gate or kernel hash mismatch')
    records=[];inventory={}
    for method in ('FIRST_ORDER','MUSCL_SSPRK2'):
        for label in ('equilibrium','blowdown','filling','reversal'):
            print('START',label,method,flush=True)
            r=run_case(label,method);records.append(r)
            path=art/'cases'/(r['name']+'.json.gz');path.write_bytes(gzip.compress(json.dumps(r,allow_nan=False,separators=(',',':')).encode(),mtime=0));inventory[path.name]=sha(path)
            write(art/'inventory.json',inventory)
            print('END',r['name'],r['status'],r['result']['wall_seconds'],[k for k,v in r['checks'].items() if not v],flush=True)
            if r['status']!='PASS':break
        if records[-1]['status']!='PASS':break
    matrix={}
    for case,labels in {'C01':('equilibrium',),'C02':('blowdown',),'C03':('filling',),'C04':('reversal',),'C05':('blowdown',),'C06':('filling','reversal'),'C07':('equilibrium','blowdown','filling','reversal')}.items():
        selected=[r for r in records if any(r['name'].startswith(label+'_') for label in labels)]
        matrix[case]=dict(status='PASS' if len(selected)==2*len(labels) and all(r['status']=='PASS' for r in selected) else 'FAIL_OR_NOT_RUN',cases=[r['name'] for r in selected])
    passed=len(records)==8 and all(r['status']=='PASS' for r in records)
    write(art/'summary.json',dict(state='P3B_READY_FOR_REVIEW' if passed else 'P3_BLOCKED_COUPLING',matrix=matrix,passed=passed,
        cases=[{k:v for k,v in r.items() if k not in ('result','initial')}|dict(runtime=r['result']['wall_seconds'],counts=r['result']['counts'],reversals=r['result']['reversals'],max_residual=max((max(l['normalized']) for l in r['result']['ledger']),default=None)) for r in records]))
    write(art/'result.json',dict(checks=[dict(id='P3B',passed=passed,kind='numerical',reason='Finite fixed-volume gate')],metrics=dict(cases=len(records)),scientific_change_required=False))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run-dir',type=Path,required=True)
    campaign(p.parse_args().run_dir)
