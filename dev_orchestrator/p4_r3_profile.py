"""Bounded standard-library profiling, isolated from application runtime."""
import argparse,cProfile,ctypes,gzip,json,pstats,time
from pathlib import Path
from motorsim.hybrid_exhaust import HybridSystem
from motorsim.exhaust1d import solve_exhaust
from motorsim.gas1d.boundary import Boundary
from motorsim.gas1d.eos import IdealGas
from .p4_hybrid import prepare
from .p4_r1e import verify
from .p2_campaign import ROOT,write


def peak_memory():
    class Counters(ctypes.Structure):
        _fields_=[('cb',ctypes.c_ulong),('PageFaultCount',ctypes.c_ulong)]+[(k,ctypes.c_size_t) for k in
            ('PeakWorkingSetSize','WorkingSetSize','QuotaPeakPagedPoolUsage','QuotaPagedPoolUsage','QuotaPeakNonPagedPoolUsage','QuotaNonPagedPoolUsage','PagefileUsage','PeakPagefileUsage')]
    p=Counters();p.cb=ctypes.sizeof(p)
    k=ctypes.WinDLL('kernel32');k.GetCurrentProcess.restype=ctypes.c_void_p
    fn=ctypes.WinDLL('psapi').GetProcessMemoryInfo;fn.argtypes=[ctypes.c_void_p,ctypes.POINTER(Counters),ctypes.c_ulong]
    if not fn(k.GetCurrentProcess(),ctypes.byref(p),p.cb):raise ctypes.WinError()
    return p.PeakWorkingSetSize


def run(folder,backend='SCALAR_REFERENCE'):
    art=Path(folder)/'artifacts';art.mkdir(parents=True,exist_ok=True)
    assert verify()
    model,mesh,pipe,state=prepare('straight');eos=IdealGas()
    old=json.loads(gzip.decompress((ROOT/'results/p4-r2-20260921/p4c/artifacts/G1-cycle01.json.gz').read_bytes()))
    cases=[('initial_open',180.,pipe,state,None)]
    previous=old['segments'][0]['result'];cases.append(('heat',350.,previous['cells'],previous['state'],350.))
    third=old['segments'][2]['result'];shot=min(third['snapshots'],key=lambda x:abs(x['angle']-480))
    h=next(h for h in third['history'] if h['angle']==shot['angle'])
    cells=[tuple(v*u for u in eos.conservative(w)) for v,w in zip(mesh.volumes,shot['primitive'])]
    cases.append(('reopening',shot['angle'],cells,h['chamber'],None))
    solver=solve_exhaust
    if backend!='SCALAR_REFERENCE':
        from motorsim.exhaust_fast import solve_exhaust as optimized
        from motorsim.hybrid_fast import HybridSystem as FastSystem,LegacySources
        model=LegacySources();system_class=FastSystem
        solver=optimized
        if backend=='NUMPY':
            from motorsim.exhaust_numpy import solve_exhaust as solver
    else:system_class=HybridSystem
    output=[]
    for name,angle,cells,z,heat in cases:
        system=system_class(model,angle,z,heat);profile=cProfile.Profile()
        start=time.perf_counter();cpu=time.process_time();profile.enable()
        r=solver(mesh,cells,system,.0001,eos=eos,cfl=.4,
            exterior=Boundary('nonreflecting',state=(100000/(287*500),0.,100000.,0.)),sensors=(.1,.3,.5),wall_limit=90)
        profile.disable();cpu=time.process_time()-cpu;wall=time.perf_counter()-start
        profile.dump_stats(str(art/f'{name}.prof'));stats=pstats.Stats(profile)
        rows=[dict(file=k[0],line=k[1],function=k[2],primitive_calls=v[0],calls=v[1],self_seconds=v[2],inclusive_seconds=v[3]) for k,v in stats.stats.items()]
        data=dict(name=name,start_angle=angle,physical_seconds=.0001,status=r['status'],wall_seconds=wall,cpu_seconds=cpu,
            peak_process_working_set_bytes=peak_memory(),steps=len(r['history']),counts=r['counts'],
            top_inclusive=sorted(rows,key=lambda x:x['inclusive_seconds'],reverse=True)[:35],
            top_self=sorted(rows,key=lambda x:x['self_seconds'],reverse=True)[:35],functions=rows)
        write(art/f'{name}.json',data);output.append({k:v for k,v in data.items() if k not in ('functions','top_self','top_inclusive')})
        print(name,r['status'],wall,flush=True)
    write(art/'profile-summary.json',dict(backend=backend,cases=output,baseline_full_wall_seconds=old['cycle_wall_seconds'],
        baseline_counts={k:sum(s['result']['counts'][k] for s in old['segments']) for k in ('rhs','HLLC','HLLE','rejected','characteristic')},
        notes='Profiled times include cProfile overhead, not comparable to unprofiled full-cycle benchmark. Reopening snapshot reconstructs conserved cells solely for profiling; not a restart checkpoint. Allocation counts unavailable; peak process working set includes loaded baseline.',frozen=verify()))
    write(art/'result.json',dict(checks=[dict(id='profile_complete',kind='numerical',passed=all(c['status']=='completed' for c in output),reason='Three representative bounded windows')],metrics={},scientific_change_required=False))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run-dir',type=Path,required=True);p.add_argument('--backend',default='SCALAR_REFERENCE');a=p.parse_args();run(a.run_dir,a.backend)
