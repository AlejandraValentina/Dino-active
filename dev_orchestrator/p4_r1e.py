"""P4-R1E: one N800 integration; only its operational wall limit changes."""
import argparse
from dataclasses import asdict
import gzip
import hashlib
import json
import time
from pathlib import Path
from .p4_r1 import EOS,prepare,brackets,measured,compare,frozen,solve_exhaust,checks
from .p2_campaign import ROOT,sha,write

OLD=ROOT/'results/p4-r1-20260921'


def same_json_value(actual,stored):
    """Normalize tuple/list representation only; no numeric rounding/tolerance."""
    return json.dumps(actual,sort_keys=True,allow_nan=False)==json.dumps(stored,sort_keys=True,allow_nan=False)


def verify():
    receipt=json.loads((ROOT/'docs/gasdynamic/p4_r1e_frozen.json').read_text(encoding='utf-8'))
    return frozen() and all(sha(ROOT/p)==h for p,h in receipt['sha256'].items())


def run(run_dir):
    art=Path(run_dir)/'artifacts';(art/'cases').mkdir(parents=True)
    if not verify():raise ValueError('Frozen sources/observables/evidence mismatch')
    prior=[]
    for path in sorted((OLD/'run/artifacts/cases').glob('*.gz')):
        row=json.loads(gzip.decompress(path.read_bytes()))
        if row['complete']:prior.append(row)
        elif row['N']==800:partial=row
    assert len(prior)==8
    mesh,q,system,end=prepare('blowdown',800,.4);lo,hi,alpha=brackets(mesh)
    w0=[EOS.primitive(tuple(v/volume for v in cell)) for cell,volume in zip(q,mesh.volumes)]
    i=mesh.centers.index(lo);pinitial=(1-alpha)*w0[i][2]+alpha*w0[i+1][2]
    assert [lo,hi,alpha]==partial['brackets'] and end==partial['requested_end']
    inputs=dict(mesh=mesh.as_dict(),initial_cells=q,initial_chamber=system.initial,
                port=asdict(system.port),start_angle=system.start_angle,rpm=system.rate/6,CFL=.4,
                requested_end=end,sensors=[lo,hi],initial_pressure=pinitial)
    payload=json.dumps(inputs,sort_keys=True,separators=(',',':')).encode()
    write(art/'inputs.json',inputs)
    write(art/'execution-choice.json',dict(mode='restart_from_t0',new_integrations=1,wall_limit=1500,
        reason='Frozen solver has no resume API for time, events and ledgers. Saved final arrays are not a resumable checkpoint through that API.',
        input_sha256=hashlib.sha256(payload).hexdigest(),geometry_sha256=hashlib.sha256(json.dumps(inputs['port'],sort_keys=True).encode()).hexdigest(),
        partial_source_sha256=sha(OLD/'run/artifacts/cases/blowdown_N800_CFL0.4.json.gz')))
    started=time.monotonic()
    r=solve_exhaust(mesh,q,system,end,cfl=.4,sensors=(lo,hi),wall_limit=1500.)
    row=dict(name='blowdown_N800_CFL0.4',kind='blowdown',N=800,CFL=.4,brackets=[lo,hi,alpha],
             initial_pressure=pinitial,initial_mass=system.initial[0],requested_end=end,result=r,
             observed_wrapper_seconds=time.monotonic()-started)
    row['metrics'],row['signal']=measured(row);row['checks']=checks(r)
    row['checks']['mass_ledger']=row['metrics']['mass_ledger_residual']<=1e-10
    row['complete']=all(row['checks'].values())
    path=art/'cases/blowdown_N800_CFL0.4.json.gz'
    path.write_bytes(gzip.compress(json.dumps(row,allow_nan=False,separators=(',',':')).encode(),mtime=0))
    write(art/'inventory.json',{path.name:sha(path)})
    # Exact prefix verifies restart determinism without altering numerical states.
    length=min(len(partial['result']['history']),len(r['history']))
    prefix=dict(history=same_json_value(r['history'][:length],partial['result']['history'][:length]),
                stages=same_json_value(r['stages'][:length],partial['result']['stages'][:length]))
    data=prior+[row];comp=compare(data)
    nominal=sorted([d for d in data if d['kind']=='blowdown' and d['CFL']==.4 and d['complete']],key=lambda d:d['N'])
    arrivals=[dict(N=d['N'],time=d['metrics']['arrival'],angle=d['metrics']['arrival_angle']) for d in nominal]
    ad=[abs(b['time']-a['time']) if a['time'] is not None and b['time'] is not None else None for a,b in zip(arrivals,arrivals[1:])]
    controls=sorted([d for d in prior if d['kind']=='control'],key=lambda d:d['N'])
    control=len(controls)==3 and all(a['metrics']['linear_reference_L1']>b['metrics']['linear_reference_L1'] for a,b in zip(controls,controls[1:])) and all(d['metrics']['area_range'][0]==d['metrics']['area_range'][1] for d in controls)
    temporal=[v for values in comp['temporal'].values() for v in values.values()]
    gates=dict(pressure=False,mass=False,arrival=False,conservation=row['checks']['conservation'] and row['checks']['stages'] and row['checks']['mass_ledger'],
               admissibility=row['checks']['positive'],CFL=row['checks']['CFL'],control=control,temporal=len(temporal)==4 and all(v['small'] for v in temporal),complete=row['complete'])
    if row['complete']:
        for label,key in (('pressure','Q_pressure'),('mass','Q_mass')):
            ds=comp['differences'][key];gates[label]=len(ds)==3 and ds[-1]['absolute']<ds[-2]['absolute']
        gates['arrival']=len(ad)==3 and all(v is not None for v in ad) and ad[-1]<ad[-2]
    phase_state=None
    if r['reason']=='wall_timeout':state='P4_R2_PERFORMANCE_OPTIMIZATION_REQUIRED'
    elif all(gates.values()):state='P4_R1_PREASYMPTOTIC_REFINEMENT_CONFIRMED'
    else:
        state='P4_R1_SPATIAL_CONVERGENCE_UNRESOLVED'
        if row['complete'] and not gates['arrival']:phase_state='P4_R1_WAVE_PHASE_CONVERGENCE_UNRESOLVED'
    if not verify() or not all(prefix.values()):state='FAILED_INFRASTRUCTURE'
    close=190/18000
    closing=next((h for h in r['history'] if h['time']==close),None)
    post=[p for t,p in zip(row['signal']['times'],row['signal']['pressure']) if t>close]
    balances=dict(final_raw={key:b-a-e for key,a,b,e in zip(('mass_kg','energy_J','species_kg'),r['initial_inventory'],r['final_inventory'],r['external'])},
                  max_normalized={key:max((abs(h['residual'][i]) for h in r['history']),default=None) for i,key in enumerate(('mass','energy','species'))},
                  max_stage=r['max_stage_residual'],extrema=r['extrema'])
    summary=dict(state=state,phase_state=phase_state,gates=gates,frozen=verify(),restart_prefix_exact=prefix,
        comparison=comp,arrivals=arrivals,arrival_differences=ad,metrics=row['metrics'],balances=balances,
        closing_reached=closing is not None,closing_state=closing,postclose_samples=len(post),
        postclose_min=min(post,default=None),postclose_max=max(post,default=None),
        relative_mass_difference=comp['differences']['Q_mass'][-1]['absolute']/abs(row['metrics']['Q_mass']) if row['complete'] else None,
        P4_accepted=False,P4_gate_changed=False,P4C_started=False,P5_started=False,new_integrations=1)
    write(art/'summary.json',summary)
    write(art/'result.json',dict(checks=[dict(id='n800_evidence',passed=True,kind='numerical',reason=state),
          dict(id='frozen_implementation',passed=verify() and all(prefix.values()),kind='numerical',reason='Source/observable hashes and exact prior accepted-step prefix')],
          metrics=dict(new_integrations=1),scientific_change_required=state!='P4_R1_PREASYMPTOTIC_REFINEMENT_CONFIRMED'))
    print(state,flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--run-dir',type=Path,required=True)
    run(parser.parse_args().run_dir)
