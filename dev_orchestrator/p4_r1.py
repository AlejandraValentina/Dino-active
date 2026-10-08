"""P4-R1 read-only observables around the byte-frozen P4 solver."""
import argparse
from bisect import bisect_right
import gzip,json,time
from math import exp,fsum,pi,sqrt,log
from pathlib import Path
from motorsim.exhaust1d import Bench,solve_exhaust
from motorsim.exhaust_port import ExhaustPort
from motorsim.coupling import ChamberState
from motorsim.simulation_case import geometry
from motorsim.gas1d.eos import IdealGas
from motorsim.gas1d.mesh import uniform_mesh
from motorsim.gas1d.reference import cell_integrals
from .p4_bench import checks
from .p4_waves import crossing
from .p2_campaign import ROOT,sha,write

EOS=IdealGas();X=.1;P0=100000.;AREA=pi*.02**2/4
END=220/18000;SPEED=sqrt(EOS.gamma*EOS.R*300)


def brackets(mesh,x=X):
    i=bisect_right(mesh.centers,x)-1
    if not 0<=i<mesh.n-1:raise ValueError('Sensor outside interpolation domain')
    lo,hi=mesh.centers[i:i+2]
    return lo,hi,(x-lo)/(hi-lo)


def absolute_integral(times,values):
    """Exact integral of absolute piecewise-linear samples, including zero crossings."""
    parts=[]
    for ta,tb,a,b in zip(times,times[1:],values,values[1:]):
        if tb<=ta:raise ValueError('Non-increasing physical time')
        value=(abs(a)+abs(b))/2 if a*b>=0 else (a*a+b*b)/(2*(abs(a)+abs(b)))
        parts.append((tb-ta)*value)
    return fsum(parts)


def prepare(kind,n,cfl):
    control=kind=='control';mesh=uniform_mesh(n,.75 if control else .6,AREA)
    pressure=100000. if control else 300000.;temperature=300. if control else 600.;y=.2 if control else .8
    mass=pressure*.0001/(EOS.R*temperature)
    ch=ChamberState(mass,pressure*.0001/(EOS.gamma-1),y*mass,.0001)
    system=Bench(ch,ExhaustPort.from_project(geometry()),start_angle=180 if control else 80)
    if control:
        def initial(x):
            dp=100*exp(-((x-.08)/.015)**2);rho=P0/(EOS.R*300)
            return rho+dp/SPEED**2,dp/(rho*SPEED),P0+dp,.2
        q=cell_integrals(mesh,initial,EOS,lambda x:AREA)
    else:q=[tuple(v*x for x in EOS.conservative((P0/(EOS.R*300),0.,P0,.2))) for v in mesh.volumes]
    return mesh,q,system,.003 if control else END


def measured(row):
    r=row['result'];lo,hi,alpha=row['brackets'];initial=row['initial_pressure']
    if r['sensor_positions'][:2]!=[lo,hi]:raise ValueError('Sensor bracket mismatch')
    times=[0.]+[h['time'] for h in r['history']]
    p=[initial]+[(1-alpha)*h['sensors'][0][0]+alpha*h['sensors'][1][0] for h in r['history']]
    integral=absolute_integral(times,[v-P0 for v in p])
    signed=fsum((b-a)*(pa+pb-2*P0)/2 for a,b,pa,pb in zip(times,times[1:],p,p[1:]))
    mass=r['port_integral'][0]
    stage_mass=fsum(s['dt']*.5*fsum(t['exchange'][0] for t in s['traces']) for s in r['stages'])
    delta=r['state'][0]-row['initial_mass']
    arrival=crossing(times,p,P0+(50. if row['kind']=='control' else 2000.))
    metrics=dict(interval=[0.,r['time']],Q_pressure=integral,Q_pressure_signed=signed,Q_mass=mass,
        mass_from_stages=stage_mass,mass_from_inventory=delta,
        mass_ledger_residual=abs(mass-delta)/r['initial_inventory'][0],arrival=arrival,
        arrival_angle=(180 if row['kind']=='control' else 80)+18000*arrival if arrival is not None else None,
        peak=max(p),minimum=min(p),steps=len(r['history']),dt_min=min((h['dt'] for h in r['history']),default=None),dt_max=max((h['dt'] for h in r['history']),default=None),
        CFL_max=r['max_CFL'],runtime=r['wall_seconds'],counts=r['counts'],conservation=r['max_global_residual'],admissibility=checks(r)['positive'])
    if row['kind']=='control':
        reference=[P0+100*exp(-((X-SPEED*t-.08)/.015)**2) for t in times]
        metrics['linear_reference_L1']=absolute_integral(times,[a-b for a,b in zip(p,reference)])/(100*.003)
        metrics['arrival_exact_linear']=(X-.08-.015*sqrt(log(2)))/SPEED
        areas=[t['area'] for s in r['stages'] for t in s['traces']]
        metrics['area_range']=[min(areas,default=None),max(areas,default=None)]
    else:
        metrics['opening']=dict(time=10/18000,angle=90.)
        metrics['closing']=dict(time=190/18000,angle=270.)
        # Post-closing candidate diagnostic: first local pressure maximum after closing,
        # prominence >= 1% imposed contrast (2kPa). No window movement or gate.
        after=[i for i,t in enumerate(times) if t>=190/18000]
        candidates=[i for i in after[1:-1] if p[i-1]<p[i]>=p[i+1] and p[i]-min(p[after[0]:i+1])>=2000]
        metrics['candidate_postclosing_peak']=times[candidates[0]] if candidates else None
        metrics['reflection_definition']='First post-closing local maximum with >=2000Pa prominence; candidate only, not causal identification of reflection. Null does not imply absence of waves.'
    return metrics,dict(x=X,times=times,pressure=p)


def execute(kind,n,cfl):
    mesh,q,system,end=prepare(kind,n,cfl);lo,hi,alpha=brackets(mesh)
    w0=[EOS.primitive(tuple(v/volume for v in cell)) for cell,volume in zip(q,mesh.volumes)]
    i=mesh.centers.index(lo);pinitial=(1-alpha)*w0[i][2]+alpha*w0[i+1][2]
    # Only output locations change. Every numerical argument/operator is frozen.
    started=time.monotonic()
    r=solve_exhaust(mesh,q,system,end,cfl=cfl,sensors=(lo,hi),wall_limit=900. if n==800 else 600.)
    row=dict(name=f'{kind}_N{n}_CFL{cfl}',kind=kind,N=n,CFL=cfl,brackets=[lo,hi,alpha],initial_pressure=pinitial,
        initial_mass=system.initial[0],requested_end=end,result=r,observed_wrapper_seconds=time.monotonic()-started)
    row['metrics'],row['signal']=measured(row);row['checks']=checks(r)
    row['checks']['mass_ledger']=row['metrics']['mass_ledger_residual']<=1e-10
    row['complete']=all(row['checks'].values())
    return row


def audit():
    rows=[]
    for n,section in ((100,'p4a'),(200,'p4b'),(400,'p4b')):
        path=ROOT/f'results/p4-exhaust-20260918/{section}/artifacts/cases/blowdown_N{n}_CFL0.4.json.gz'
        d=json.loads(gzip.decompress(path.read_bytes()));r=d['result'];h=r['history']
        t=[0.]+[v['time'] for v in h];p=[P0]+[v['sensors'][0][0] for v in h]
        reconstructed=sum(v['dt']*abs(v['sensors'][0][0]-P0) for v in h)
        by_stage=fsum(v['dt']*.5*fsum(s['exchange'][0] for s in v['traces']) for v in r['stages'])
        delta=r['state'][0]-d['inputs']['chamber']['mass']
        rows.append(dict(N=n,path=str(path.relative_to(ROOT)),sha256=sha(path),sensor=r['sensor_positions'][0],
            interval=[0,r['time']],samples=len(h),Q_pressure=d['metrics']['pressure_integral'],reconstructed_right_rule=reconstructed,
            trapezoid_same_displaced_sensor=absolute_integral(t,[v-P0 for v in p]),
            Q_mass=r['port_integral'][0],mass_stage=by_stage,mass_inventory=delta,
            mass_residual=abs(delta-r['port_integral'][0])/r['initial_inventory'][0],events=r['hit_events']))
    return dict(state='P4_R1_METRIC_IMPLEMENTATION_DEFECT',historical=rows,
        reason='Nearest-centre sensor changes physical position; right endpoint pressure quadrature also has dt-dependent first-order bias. Mass comes from conservative stage ledger and is correct.',
        can_recover_fixed_sensor_offline=False,missing='Neighbour-cell time series absent; sparse snapshots cannot reconstruct every accepted endpoint.')


def compare(rows):
    data={(r['kind'],r['N'],r['CFL']):r for r in rows if r['complete']}
    values={};differences={};temporal={}
    for key in ('Q_pressure','Q_mass'):
        seq=[(n,data['blowdown',n,.4]['metrics'][key]) for n in (100,200,400,800) if ('blowdown',n,.4) in data]
        values[key]=seq;differences[key]=[dict(meshes=[a[0],b[0]],signed=b[1]-a[1],absolute=abs(b[1]-a[1])) for a,b in zip(seq,seq[1:])]
        if len(seq)>=3:
            spatial=abs(seq[2][1]-seq[1][1]);temporal[key]={}
            for n in (200,400):
                if ('blowdown',n,.2) in data:
                    nominal=data['blowdown',n,.4]['metrics'][key];low=data['blowdown',n,.2]['metrics'][key];d=abs(low-nominal)
                    temporal[key][str(n)]=dict(nominal=nominal,half_CFL=low,absolute=d,spatial_D200_400=spatial,ratio=d/spatial if spatial else None,
                        small=d<=.1*spatial,comparable=d>=.5*spatial and d>0,temporal_class='small' if d<=.1*spatial else ('comparable' if d>=.5*spatial else 'inconclusive'))
    return dict(values=values,differences=differences,temporal=temporal)


def frozen():
    receipt=json.loads((ROOT/'docs/gasdynamic/p4_r1_frozen.json').read_text(encoding='utf-8'))
    return all(sha(ROOT/p)==h for p,h in receipt['sha256'].items())


def campaign(run_dir):
    art=Path(run_dir)/'artifacts';(art/'cases').mkdir(parents=True)
    if not frozen():raise ValueError('Frozen implementation mismatch')
    write(art/'historical-audit.json',audit());rows=[];inventory={};state=None
    def run(kind,n,cfl):
        print('START',kind,n,cfl,flush=True);row=execute(kind,n,cfl);rows.append(row)
        p=art/'cases'/(row['name']+'.json.gz');p.write_bytes(gzip.compress(json.dumps(row,allow_nan=False,separators=(',',':')).encode(),mtime=0));inventory[p.name]=sha(p);write(art/'inventory.json',inventory)
        write(art/'partial.json',dict(cases=[{k:v for k,v in r.items() if k not in ('result','signal')} for r in rows],comparison=compare(rows)))
        print('END',row['name'],row['complete'],row['result']['reason'],row['metrics'],flush=True)
        return row
    for n,cfl in ((100,.4),(200,.4),(400,.4),(200,.2),(400,.2)):
        row=run('blowdown',n,cfl)
        if not row['complete']:
            state='FAILED_INFRASTRUCTURE' if row['result']['reason']=='wall_timeout' else 'P4_R1_SPATIAL_CONVERGENCE_UNRESOLVED'
            break
    if state is None:
        temporal=compare(rows)['temporal'];items=[v for d in temporal.values() for v in d.values()]
        if len(items)!=4 or not all(v['small'] for v in items):state='P4_R1_SPACE_TIME_COUPLING_UNRESOLVED'
    # Independent control is useful even when temporal contamination blocks N800.
    if state!='FAILED_INFRASTRUCTURE':
        for n in (100,200,400):
            row=run('control',n,.4)
            if not row['complete']:
                state='FAILED_INFRASTRUCTURE' if row['result']['reason']=='wall_timeout' else 'P4_R1_SPATIAL_CONVERGENCE_UNRESOLVED'
                break
    controls=[r for r in rows if r['kind']=='control' and r['complete']]
    control_converges=len(controls)==3 and all(a['metrics']['linear_reference_L1']>b['metrics']['linear_reference_L1'] for a,b in zip(controls,controls[1:])) and all(r['metrics']['area_range'][0]==r['metrics']['area_range'][1] for r in controls)
    if state is None and not control_converges:state='P4_R1_SPATIAL_CONVERGENCE_UNRESOLVED'
    if state is None:
        n800=run('blowdown',800,.4)
        if n800['result']['reason']=='wall_timeout':state='P4_R1_PERFORMANCE_DIAGNOSTIC_REQUIRED'
        elif not n800['complete']:state='P4_R1_SPATIAL_CONVERGENCE_UNRESOLVED'
        else:
            comp=compare(rows);reduces=all(v[-1]['absolute']<v[-2]['absolute'] for v in comp['differences'].values())
            arrivals=[r['metrics']['arrival'] for r in rows if r['kind']=='blowdown' and r['CFL']==.4]
            arrival_converges=all(v is not None for v in arrivals) and abs(arrivals[-1]-arrivals[-2])<abs(arrivals[-2]-arrivals[-3])
            state='P4_R1_PREASYMPTOTIC_REFINEMENT_CONFIRMED' if reduces and arrival_converges and control_converges else 'P4_R1_SPATIAL_CONVERGENCE_UNRESOLVED'
    summary=dict(state=state,metric_defect_confirmed=True,solver_frozen=frozen(),comparison=compare(rows),control_converges=control_converges,
        cases=[{k:v for k,v in r.items() if k not in ('result','signal')} for r in rows],P4_gate_changed=False,P4C_started=False)
    write(art/'summary.json',summary)
    write(art/'result.json',dict(checks=[dict(id='diagnostic_evidence',passed=state!='FAILED_INFRASTRUCTURE',kind='numerical',reason=state),dict(id='frozen_implementation',passed=frozen(),kind='numerical',reason='Source and historical evidence hashes')],metrics=dict(new_integrations=len(rows)),scientific_change_required=state!='P4_R1_PREASYMPTOTIC_REFINEMENT_CONFIRMED'))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run-dir',type=Path,required=True);campaign(p.parse_args().run_dir)
