"""Frozen P4A bank, conservative ideal port and boundary diagnostics."""
import argparse
from dataclasses import asdict
import gzip,json
from pathlib import Path
from motorsim.coupling import ChamberState
from motorsim.exhaust_port import ExhaustPort
from motorsim.exhaust1d import Bench,solve_exhaust
from motorsim.simulation_case import geometry
from motorsim.gas1d.mesh import uniform_mesh
from motorsim.gas1d.eos import IdealGas
from motorsim.gas1d.boundary import Boundary
from .p2_campaign import ROOT,sha,write


def checks(r):
    e=r['extrema']
    return dict(completed=r['status']=='completed',conservation=r['max_global_residual']<=1e-10,
        stages=r['max_stage_residual']<=1e-10,positive=min(e[k] for k in ('rho','p','T'))>0 and 0<=e['Y_min']<=e['Y_max']<=1,
        events=r['hit_events']==r['events'],CFL=all(x['dt']<=min(x['limits']) for x in r['stages']))


def case(label,n=100,cfl=.4):
    eos=IdealGas();port=ExhaustPort.from_project(geometry());area=3.141592653589793*.02**2/4
    p=100000 if label=='closed' else (80000 if label=='backflow' else 300000)
    temp=300 if label in ('closed','backflow') else 600
    ch=ChamberState(p*.0001/(eos.R*temp),p*.0001/(eos.gamma-1),.8*p*.0001/(eos.R*temp),.0001)
    start=0 if label=='closed' else 80.;finish=40 if label=='closed' else (145 if label=='backflow' else 300)
    system=Bench(ch,port,start_angle=start);mesh=uniform_mesh(n,.6,area)
    initial=[tuple(v*x for x in eos.conservative((100000/(eos.R*300),0.,100000.,.2))) for v in mesh.volumes]
    r=solve_exhaust(mesh,initial,system,(finish-start)/system.rate,cfl=cfl,sensors=(.1,.3,.5))
    c=checks(r);history=r['history'];traces=[s for row in r['stages'] for s in row['traces']]
    if label=='closed':
        c['no_leak']=r['state']==system.initial and all(all(v==0 for v in row['exchange']) for row in history)
        c['equilibrium']=max(abs(w[2]-100000) for w in r['primitive'])/100000<=1e-12
    if label=='blowdown':
        opened=[s for s in traces if s['area']>1e-8]
        c['opening']=bool(opened) and opened[0]['exchange'][0]<0
        c['discharge']=r['state'][0]<system.initial[0] and r['state'][1]<system.initial[1]
        c['wave']=max(row['sensors'][0][0] for row in history)>101000
        c['closing']=all(all(v==0 for v in s['exchange']) for s in traces if s['angle']>port.events(area)[-2]+1.)
    if label=='backflow':
        c['reverse']=r['state'][0]>system.initial[0] and r['state'][1]>system.initial[1]
        c['local_species']=all(abs(s['exchange'][2]-s['exchange'][0]*s['pipe_face'][3])<=1e-12 for s in traces if s['exchange'][0]>0)
    # Arrival threshold is 1% of imposed pressure contrast, fixed before run.
    threshold=100000+.01*abs(p-100000)
    arrival=next((row['time'] for row in history if row['sensors'][0][0]>threshold),None) if label=='blowdown' else None
    metrics=dict(arrival=arrival,pressure_integral=sum(row['dt']*abs(row['sensors'][0][0]-100000) for row in history),mass_exchange=r['port_integral'][0])
    return dict(name=f'{label}_N{n}_CFL{cfl}',inputs=dict(label=label,N=n,CFL=cfl,start=start,finish=finish,chamber=asdict(ch),port=asdict(port),length=.6,area=area),checks=c,status='PASS' if all(c.values()) else 'FAIL',metrics=metrics,result=r)


def campaign(run_dir):
    art=Path(run_dir)/'artifacts';(art/'cases').mkdir(parents=True)
    receipt=json.loads((ROOT/'docs/gasdynamic/p3_human_acceptance.json').read_text(encoding='utf-8'))
    if receipt['state']!='P3_HUMAN_ACCEPTED' or not all(sha(ROOT/p)==h for p,h in receipt['frozen_sha256'].items()):raise ValueError('P3 baseline mismatch')
    records=[];inventory={}
    for label,n,cfl in [('closed',100,.4),('blowdown',100,.4),('backflow',100,.4)]:
        print('START',label,n,cfl,flush=True);row=case(label,n,cfl);records.append(row)
        path=art/'cases'/(row['name']+'.json.gz');path.write_bytes(gzip.compress(json.dumps(row,allow_nan=False,separators=(',',':')).encode(),mtime=0));inventory[path.name]=sha(path);write(art/'inventory.json',inventory)
        print('END',row['name'],row['status'],row['result']['reason'],row['result']['wall_seconds'],flush=True)
        if row['status']!='PASS':break
    passed=len(records)==3 and all(r['status']=='PASS' for r in records)
    write(art/'summary.json',dict(state='P4A_READY_FOR_REVIEW' if passed else 'P4_BLOCKED_PORT_CONTRACT',passed=passed,cases=[{k:v for k,v in r.items() if k!='result'}|dict(runtime=r['result']['wall_seconds'],reason=r['result']['reason'],residual=r['result']['max_global_residual'],counts=r['result']['counts']) for r in records]))
    write(art/'result.json',dict(checks=[dict(id='P4A',passed=passed,kind='numerical',reason='E01-E05 port bank')],metrics=dict(cases=len(records)),scientific_change_required=False))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run-dir',type=Path,required=True);campaign(p.parse_args().run_dir)
