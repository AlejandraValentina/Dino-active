"""Bounded P4C measurement; no automatic extension of the P4 budget."""
import argparse
import gzip
import json
import time
from bisect import bisect_right
from math import fsum
from pathlib import Path
from motorsim.hybrid_exhaust import LegacySources,run_cycle
from motorsim.exhaust_geometry import exhaust_mesh
from motorsim.gas1d.eos import IdealGas
from .p4_waves import segments
from .p4_r1e import verify
from .p2_campaign import ROOT,sha,write
from motorsim.periodicity import compare_cycles

BUDGET=600.
MAX_CYCLES=30


def prepare(label):
    model=LegacySources();mesh=exhaust_mesh(segments(label),.003)
    p,T,Y=model.case.initial_pty[3];eos=IdealGas()
    U=eos.conservative((p/(eos.R*T),0.,p,Y))
    return model,mesh,[tuple(v*u for u in U) for v in mesh.volumes],model.initial_state()[:9]


def checks(row):
    results=[s['result'] for s in row['segments']]
    traces=[t for r in results for s in r['stages'] for t in s['traces']]
    back=[t for t in traces if t['exchange'][0]>0]
    return dict(complete=row['complete'],
        conservation=row['global_balance'] is not None and max(map(abs,row['global_balance']))<=1e-10
            and all(max(map(abs,s['physical_balance']))<=1e-10 and s['result']['max_global_residual']<=1e-10
                    and s['result']['max_stage_residual']<=1e-10 for s in row['segments']),
        positive=all(min(r['extrema'][k] for k in ('rho','p','T'))>0 and r['extrema']['Y_min']>=0
            and r['extrema']['Y_max']<=1 for r in results),
        CFL=all(s['dt']<=min(s['limits']) for r in results for s in r['stages']),
        closed_zero=all(t['exchange']==[0.,0.,0.] or tuple(t['exchange'])==(0.,0.,0.) for t in traces if t['area']==0),
        backflow_local=all(abs(t['exchange'][2]-t['exchange'][0]*t['pipe_face'][3])<=1e-12 for t in back))


def periodic(previous,current):
    result = compare_cycles(previous, current)
    if result.get('status') == 'INVALID' and result.get('reason') == 'INCOMPLETE_ANGULAR_HISTORY':
        raise ValueError(result['reason'])
    return result
    def relative(a,b,floor=0.):return abs(a-b)/max(abs(a),abs(b),floor)
    def curve(row,key,index=None):
        hs=row['history'];xs=[h['angle']-row['begin'] for h in hs]
        if xs[0]>.5 or xs[-1]!=360.:raise ValueError('Incomplete phase support for periodic comparison')
        ys=[h[key] if index is None else h[key][index][0] for h in hs]
        out=[]
        # Accepted samples are used only within their shared phase support.
        for phase in (i*.5 for i in range(1,721)):
            j=bisect_right(xs,phase)
            if j==0 or j==len(xs):out.append(ys[0] if j==0 else ys[-1])
            else:out.append(ys[j-1]+(ys[j]-ys[j-1])*(phase-xs[j-1])/(xs[j]-xs[j-1]))
        return out
    def pressure(key,index=None):
        a=curve(previous,key,index);b=curve(current,key,index)
        return max(abs(x-y) for x,y in zip(a,b))/max(map(abs,a+b))
    a,b=previous['state'],current['state']
    inventories=[]
    for k in (0,3,6):
        inventories.extend((relative(a[k],b[k]),relative(a[k+1],b[k+1]),abs(a[k+2]/a[k]-b[k+2]/b[k])))
    pa=[fsum(c[j] for c in previous['cells']) for j in (0,2,3)]
    pb=[fsum(c[j] for c in current['cells']) for j in (0,2,3)]
    inventories.extend((relative(pa[0],pb[0]),relative(pa[1],pb[1]),abs(pa[2]-pb[2])/max(pa[0],pb[0])))
    metrics=dict(work=relative(previous['work_indicated_J'],current['work_indicated_J'],1.),
        cylinder_pressure=pressure('p_cyl'),sensor_pressure=[pressure('sensors_p_u_M_Y',i) for i in range(3)],
        port_mass=relative(previous['port_integral'][0],current['port_integral'][0],current['initial_cylinder_mass']),
        inventories=inventories)
    metrics['passed']=metrics['work']<=.005 and metrics['cylinder_pressure']<=.005 and max(metrics['sensor_pressure'])<=.005 and metrics['port_mass']<=.002 and max(inventories)<=.002
    return metrics


def run(run_dir):
    art=Path(run_dir)/'artifacts';art.mkdir(parents=True,exist_ok=True)
    gate=json.loads((ROOT/'results/p4-r2-20260921/gate-review.json').read_text(encoding='utf-8'))
    if not verify() or gate['P4B']!='P4B_PASS_EXHAUST_WAVE_PHYSICS':raise ValueError('Frozen inputs or R2 prerequisite failed')
    configs={}
    for name,label in (('G1','straight'),('G2','chain')):
        model,mesh,pipe,state=prepare(label)
        configs[name]=dict(label=label,N=mesh.n,mesh=mesh.as_dict(),initial_cells=pipe,initial_0D=state,
            case=model.case.manifest(),CFL=.4,dx_target=.003)
    write(art/'inputs.json',dict(configurations=configs,budget_seconds=BUDGET,max_cycles=MAX_CYCLES,
        definition_sha256=sha(ROOT/'docs/gasdynamic/p4c_hybrid.md'),R2_receipt_sha256=sha(ROOT/'results/p4-r2-20260921/gate-review.json')))
    history=[];terminal=None;inventory={}
    for name,label in (('G1','straight'),('G2','chain')):
        model,mesh,pipe,state=prepare(label);elapsed=0.;previous=None;streak=0
        for cycle in range(1,MAX_CYCLES+1):
            print(f'START {name} cycle={cycle} N={mesh.n} remaining={BUDGET-elapsed:.3f}s',flush=True)
            initial_cylinder_mass=state[6]
            row=run_cycle(mesh,pipe,state,180.+360*(cycle-1),wall_limit=BUDGET-elapsed)
            row['initial_cylinder_mass']=initial_cylinder_mass
            elapsed+=row['cycle_wall_seconds'];c=checks(row)
            comparison=None if previous is None or not row['complete'] else periodic(previous,row)
            entry=dict(configuration=name,cycle=cycle,N=mesh.n,checks=c,complete=row['complete'],reason=row['reason'],
                end_angle=row['end'],wall_seconds=row['cycle_wall_seconds'],solver_seconds=row['solver_seconds'],
                projected_30_cycles_seconds=MAX_CYCLES*row['cycle_wall_seconds'] if cycle==1 and row['complete'] else None,
                global_balance=row['global_balance'],work_J=row['work_indicated_J'],power_W=row['power_indicated_W'],
                torque_Nm=row['torque_indicated_Nm'],periodicity=comparison,
                counts={k:sum(s['result']['counts'][k] for s in row['segments']) for k in ('rhs','HLLC','HLLE','rejected')})
            path=art/f'{name}-cycle{cycle:02}.json.gz'
            path.write_bytes(gzip.compress(json.dumps(row,allow_nan=False,separators=(',',':')).encode(),mtime=0))
            inventory[path.name]=sha(path);history.append(entry)
            write(art/'cycles.json',history);write(art/'inventory.json',inventory)
            print(json.dumps(entry),flush=True)
            if not all(c.values()):
                terminal='P4_BLOCKED_PERFORMANCE' if row['reason']=='wall_timeout' else 'P4_BLOCKED_HYBRID_NUMERICAL';break
            if cycle==1 and MAX_CYCLES*row['cycle_wall_seconds']>BUDGET:
                terminal='P4_BLOCKED_PERFORMANCE';break
            streak=streak+1 if cycle>=5 and comparison and comparison['passed'] else 0
            if streak>=3:break
            if elapsed>=BUDGET:terminal='P4_BLOCKED_PERFORMANCE';break
            if cycle==MAX_CYCLES:terminal='P4_BLOCKED_PERIODIC_CONVERGENCE';break
            state=row['state'];pipe=row['cells'];previous=row
        if terminal:break
    terminal=terminal or 'P4C_REQUIRES_WAVE_RETURN_REVIEW'
    write(art/'summary.json',dict(state=terminal,cycles=history,frozen=verify(),
        G2_executed=any(r['configuration']=='G2' for r in history),P4_PASS=False,P5_started=False))
    write(art/'result.json',dict(checks=[dict(id='hybrid_evidence',passed=True,kind='numerical',reason=terminal),
        dict(id='frozen_implementation',passed=verify(),kind='numerical',reason='151 historical hashes')],
        metrics=dict(cycles=len(history)),scientific_change_required=False))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run-dir',type=Path,required=True);run(p.parse_args().run_dir)
