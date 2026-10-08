"""Fixed G1 comparison; every measurement retained, no periodic campaign."""
import argparse,cProfile,gzip,json,pstats,time
from pathlib import Path
from .p4_hybrid import prepare,checks
from .p4_r1e import verify
from .p4_r3_profile import peak_memory
from .p2_campaign import ROOT,write,sha


def equivalent(a,b):
    out={}
    def compare(name,x,y,atol=1e-13):
        def flat(v):
            if isinstance(v,(list,tuple)):
                for k in v:yield from flat(k)
            else:yield v
        u=list(flat(x));v=list(flat(y))
        same=len(u)==len(v);pairs=list(zip(u,v))
        out[name]=dict(count=len(u),same_count=same,exact=same and u==v,
            max_abs=max((abs(i-j) for i,j in pairs),default=0),
            max_scaled=max((abs(i-j)/(atol+1e-10*abs(i)) for i,j in pairs),default=0))
        out[name]['passed']=bool(same and out[name]['max_scaled']<=1)
    compare('final_0D',a['state'],b['state']);compare('final_1D',a['cells'],b['cells'])
    for key,atol in [('p_cyl',1e-8),('p_port',1e-8),('mass_flux_port',1e-13),('energy_flux_port',1e-13),('species_flux_port',1e-13),('W_indicated',1e-13),('sensors_p_u_M_Y',1e-13)]:
        compare(key,[h[key] for h in a['history']],[h[key] for h in b['history']],atol)
    for key in ('external','port_integral','final_inventory','global_balance'):compare(key,a[key],b[key])
    discrete=dict(complete=a['complete']==b['complete']==True,
        steps=[len(s['result']['stages']) for s in a['segments']]==[len(s['result']['stages']) for s in b['segments']],
        events=[s['result']['hit_events'] for s in a['segments']]==[s['result']['hit_events'] for s in b['segments']],
        counts=[s['result']['counts'] for s in a['segments']]==[s['result']['counts'] for s in b['segments']],
        scientific_checks=checks(a)==checks(b) and all(checks(b).values()))
    return dict(fields=out,discrete=discrete,passed=all(x['passed'] for x in out.values()) and all(discrete.values()))


def run(folder,repeats=1,backend='STRUCTURAL',profile=False):
    from motorsim.hybrid_fast import run_cycle
    art=Path(folder)/'artifacts';art.mkdir(parents=True,exist_ok=True);assert verify()
    baseline=json.loads(gzip.decompress((ROOT/'results/p4-r2-20260921/p4c/artifacts/G1-cycle01.json.gz').read_bytes()))
    rows=[]
    for i in range(repeats):
        model,mesh,pipe,state=prepare('straight');start=time.perf_counter();cpu=time.process_time()
        profiler=cProfile.Profile() if profile else None
        if profiler:profiler.enable()
        r=run_cycle(mesh,pipe,state,backend=backend)
        if profiler:profiler.disable()
        wall=time.perf_counter()-start;cpu=time.process_time()-cpu
        if profiler:
            profiler.dump_stats(str(art/'full-cycle.prof'))
            stats=pstats.Stats(profiler)
            functions=[dict(file=k[0],line=k[1],function=k[2],primitive_calls=v[0],calls=v[1],self_seconds=v[2],inclusive_seconds=v[3]) for k,v in stats.stats.items()]
            write(art/'full-profile.json',dict(wall_seconds=wall,cpu_seconds=cpu,functions=functions,
                top_inclusive=sorted(functions,key=lambda x:x['inclusive_seconds'],reverse=True)[:40],
                top_self=sorted(functions,key=lambda x:x['self_seconds'],reverse=True)[:40]))
        comparison=equivalent(baseline,r)
        p=art/f'G1-{i+1}.json.gz';p.write_bytes(gzip.compress(json.dumps(r,allow_nan=False,separators=(',',':')).encode(),mtime=0))
        entry=dict(backend=backend,profiled=profile,measurement=i+1,wall_seconds=wall,cpu_seconds=cpu,peak_process_working_set_bytes=peak_memory(),
            cycle_wall_seconds=r['cycle_wall_seconds'],projection_30_seconds=None if profile else 30*wall,speedup=None if profile else baseline['cycle_wall_seconds']/wall,
            baseline_wall_seconds=baseline['cycle_wall_seconds'],equivalence=comparison,artifact_sha256=sha(p))
        rows.append(entry);write(art/'benchmark.json',dict(measurements=rows,frozen=verify()))
        print('G1',i+1,'wall',wall,'equivalent',comparison['passed'],flush=True)
        if not comparison['passed']:break
    write(art/'result.json',dict(checks=[dict(id='benchmark_equivalence',kind='numerical',passed=all(r['equivalence']['passed'] for r in rows),reason='Fixed G1 vs frozen R2')],metrics=dict(measurements=len(rows)),scientific_change_required=False))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run-dir',type=Path,required=True);p.add_argument('--repeats',type=int,default=1);p.add_argument('--backend',default='STRUCTURAL');p.add_argument('--profile',action='store_true');a=p.parse_args();run(a.run_dir,a.repeats,a.backend,a.profile)
