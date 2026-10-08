"""Offline cost profile of a saved P4-R1 state. Never advances the solution."""
import argparse
import cProfile
import gzip
import io
import json
import pstats
import time
from pathlib import Path
from .p4_r1 import EOS, P0, prepare
from .p2_campaign import write
from motorsim.gas1d.boundary import Boundary
from motorsim.gas1d.second_order import reconstruct
from motorsim.gas1d.riemann import hllc_flux
from motorsim.exhaust_port import port_flux


def profile(path, output):
    row=json.loads(gzip.decompress(path.read_bytes()))
    r=row['result']; n=row['N']; counts=r['counts']
    assert r['reason']=='wall_timeout'
    assert counts['characteristic']==counts['rhs']
    mesh,_,system,_=prepare(row['kind'],n,row['CFL'])
    ws=r['primitive']; ch=system.chamber(r['state'],r['time'])
    area=system.area(r['time'])
    exterior=Boundary('nonreflecting',state=(P0/(EOS.R*300),0.,P0,0.))
    costs=dict(reconstruction=0.,internal_Riemann=0.,port_and_coupling=0.,exterior=0.)
    repeats=20
    def snapshot():
        started=time.perf_counter()
        left,right,_=reconstruct(mesh,ws,(Boundary('outflow'),exterior),EOS)
        costs['reconstruction']+=time.perf_counter()-started
        started=time.perf_counter()
        port_flux(ch,left[0],area,mesh.areas[0],eos=EOS)
        costs['port_and_coupling']+=time.perf_counter()-started
        started=time.perf_counter()
        for i in range(n-1):hllc_flux(right[i],left[i+1],EOS)
        costs['internal_Riemann']+=time.perf_counter()-started
        started=time.perf_counter();exterior.flux(right[-1],1,EOS)
        costs['exterior']+=time.perf_counter()-started
    # Timing without profiler, then a separate bounded call profile, no new time step.
    for _ in range(repeats):snapshot()
    timings=costs.copy()
    profiler=cProfile.Profile();profiler.enable();snapshot();profiler.disable()
    stream=io.StringIO();pstats.Stats(profiler,stream=stream).sort_stats('cumulative').print_stats(30)
    output.mkdir(parents=True,exist_ok=True)
    (output/'snapshot-profile.txt').write_text(stream.getvalue().rstrip()+'\n',encoding='utf-8')
    data=dict(kind='offline snapshot microprofile; not full-run timing attribution',
        new_integrations=0,solver_modified=False,physical_time=r['time'],requested_end=row['requested_end'],
        accepted_steps=len(r['history']),wall_seconds=r['wall_seconds'],
        wall_seconds_per_accepted_step=r['wall_seconds']/len(r['history']),
        RHS=counts['rhs'],reconstruction_calls=counts['rhs'],
        port_evaluations=counts['rhs'],coupling_evaluations=counts['HLLC']+counts['HLLE']-n*counts['rhs'],
        internal_Riemann_calls=(n-1)*counts['rhs'],wall_Riemann_calls=counts['rhs'],
        total_Riemann_calls=counts['HLLC']+counts['HLLE'],HLLC=counts['HLLC'],HLLE=counts['HLLE'],
        characteristic=counts['characteristic'],rejections=r['rejections'],
        count_derivation='One reconstruction/port/wall and N-1 internal Riemann per completed RHS; remaining Riemann calls are open-port P3 coupling. characteristic == rhs verifies completion.',
        microprofile_repeats=repeats,microprofile_seconds=timings,
        microprofile_seconds_per_snapshot={k:v/repeats for k,v in timings.items()},
        limitation='Final frozen snapshot only; excludes validation, advances, ledgers, logging and varied states. Do not extrapolate component percentages to the whole integration.')
    write(output/'performance.json',data)
    print(json.dumps(data,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('case',type=Path);parser.add_argument('output',type=Path)
    args=parser.parse_args();profile(args.case,args.output)
