"""Frozen G1 windows, JIT excluded; no full-cycle authorization on failure."""
import argparse,gzip,json,time
from pathlib import Path
import numpy as np
from motorsim import exhaust_numpy,exhaust_numba
from motorsim.hybrid_fast import HybridSystem,LegacySources
from motorsim.gas1d.eos import IdealGas
from motorsim.gas1d.boundary import Boundary
from .p4_hybrid import prepare
from .p2_campaign import ROOT,write

def compare(a,b):
    if isinstance(a,dict):return a.keys()==b.keys() and all(compare(a[k],b[k]) for k in a if k not in ('wall_seconds',))
    if isinstance(a,(list,tuple)):return len(a)==len(b) and all(compare(x,y) for x,y in zip(a,b))
    if isinstance(a,float):return abs(a-b)<=1e-13+1e-10*abs(a)
    return a==b

def run(folder):
    art=Path(folder)/'artifacts';art.mkdir(parents=True,exist_ok=True)
    _,mesh,pipe,state=prepare('straight');eos=IdealGas();model=LegacySources()
    old=json.loads(gzip.decompress((ROOT/'results/p4-r2-20260921/p4c/artifacts/G1-cycle01.json.gz').read_bytes()))
    cases=[('initial',180.,pipe,state,None)]
    prev=old['segments'][0]['result'];cases.append(('heat',350.,prev['cells'],prev['state'],350.))
    third=old['segments'][2]['result'];shot=min(third['snapshots'],key=lambda x:abs(x['angle']-480));h=next(h for h in third['history'] if h['angle']==shot['angle'])
    cells=[tuple(v*u for u in eos.conservative(w)) for v,w in zip(mesh.volumes,shot['primitive'])]
    cases.append(('reopening',shot['angle'],cells,h['chamber'],None))
    options=dict(eos=eos,cfl=.4,exterior=Boundary('nonreflecting',state=(100000/(287*500),0.,100000.,0.)),sensors=(.1,.3,.5),wall_limit=90)
    start=time.perf_counter()
    exhaust_numba.solve_exhaust(mesh,pipe,HybridSystem(model,180.,state,None),1e-8,**options)
    warmup=time.perf_counter()-start;rows=[]
    for name,angle,q,z,heat in cases:
        outputs=[];times=[]
        for solver in (exhaust_numpy.solve_exhaust,exhaust_numba.solve_exhaust):
            system=HybridSystem(model,angle,z,heat);start=time.perf_counter();r=solver(mesh,q,system,.0001,**options);times.append(time.perf_counter()-start);outputs.append(r)
        keys=('cells','state','history','stages','events','hit_events','counts','extrema','external','port_integral','batch_observability')
        eq={k:compare(outputs[0][k],outputs[1][k]) for k in keys}
        rows.append(dict(name=name,times=times,speedup=times[0]/times[1],equivalence=eq,steps=len(outputs[1]['history']),counts=outputs[1]['counts'],completed=all(r['status']=='completed' for r in outputs)))
        print(rows[-1],flush=True)
    ratio=sum(r['times'][0] for r in rows)/sum(r['times'][1] for r in rows)
    passed=all(all(r['equivalence'].values()) and r['completed'] for r in rows) and ratio>=1.2
    write(art/'focal.json',dict(warmup_seconds=warmup,cases=rows,aggregate_speedup=ratio,passed=passed))
    write(art/'result.json',dict(checks=[dict(id='focal_gate',kind='numerical',passed=passed,reason='Equivalence and >=1.2x before full cycle')],metrics={},scientific_change_required=False))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run-dir',required=True);run(p.parse_args().run_dir)
