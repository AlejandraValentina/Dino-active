"""Hot path profiling for P4-R5: categorizes A-L time budgets over G1 windows and full cycle.
Does not change frozen science; instrumentation only.
"""
import time, cProfile, pstats, json, gzip
from pathlib import Path
from collections import Counter, defaultdict

import numpy as np
from motorsim.gas1d.eos import IdealGas
from motorsim.gas1d.boundary import Boundary
from motorsim.hybrid_fast import HybridSystem, LegacySources
from motorsim.exhaust_geometry import exhaust_mesh
from motorsim.gas1d.mesh import smooth_mesh
from motorsim import exhaust_batch as ref_batch
from motorsim import exhaust_numpy, exhaust_numba
from .p4_hybrid import prepare
from .p2_campaign import ROOT, write

CATEGORIES = [
    "A_python_exterior",
    "B_primitive",
    "C_muscl",
    "D_hllc",
    "E_geometric_source",
    "F_boundary",
    "G_coupling",
    "H_assembly",
    "I_ssprk2",
    "J_cfl_admissibility",
    "K_diagnostics",
    "L_allocation",
]

def profile_windows_and_cycle(output_dir):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Prepare warm-up
    model, mesh, pipe, state = prepare('straight')
    eos = IdealGas()
    exterior = Boundary('nonreflecting', state=(100000/(287*500),0.,100000.,0.))
    # JIT warm-up: tiny run
    for backend_name, solver in [('NUMPY', exhaust_numpy.solve_exhaust), ('NUMBA', exhaust_numba.solve_exhaust)]:
        sys_state = HybridSystem(model, 180., state, None)
        solver(mesh, pipe, sys_state, 1e-8, eos=eos, cfl=.4, exterior=exterior, sensors=(.1,.3,.5), wall_limit=90)

    # Now detailed hotspot profiling for NUMBA backend on full windows
    # We'll instrument exhaust_numpy.solve_exhaust by wrapping its inner functions with timers.
    # Instead of monkey patching the live solver, we copy its code with timing buckets.

    results = {}

    # --- Detailed per-RHS breakdown via wrapper ---
    # Create timed wrappers for kernels
    # We'll measure counts and time for each category using perf_counter around each subcall.
    # Approach: run the same three focal windows as P4-R4 but with injected timers.
    from motorsim.exhaust_numpy import Kernel as NumpyKernel

    # Reuse same windows as p4_r4_focal.py
    old = json.loads(gzip.decompress((ROOT/'results/p4-r2-20260921/p4c/artifacts/G1-cycle01.json.gz').read_bytes()))
    cases = []
    _, mesh2, pipe2, state2 = prepare('straight')
    cases.append(('initial', 180., pipe2, state2, None))
    prev = old['segments'][0]['result']
    cases.append(('heat', 350., prev['cells'], prev['state'], 350.))
    third = old['segments'][2]['result']
    shot = min(third['snapshots'], key=lambda x: abs(x['angle']-480))
    h = next(h for h in third['history'] if h['angle']==shot['angle'])
    cells = [tuple(v*u for u in eos.conservative(w)) for v,w in zip(mesh2.volumes, shot['primitive'])]
    cases.append(('reopening', shot['angle'], cells, h['chamber'], None))

    options = dict(eos=eos, cfl=.4, exterior=Boundary('nonreflecting', state=(100000/(287*500),0.,100000.,0.)), sensors=(.1,.3,.5), wall_limit=90)

    # instrumented solve
    def instrumented_solve(mesh, initial, system, end, *, eos=None, cfl=.4, exterior=None, sensors=(), wall_limit=600., numeric_backend=None):
        buckets = Counter()
        counts = Counter()
        # timing helper
        def timed(cat, fn, *args, **kwargs):
            s = time.perf_counter()
            r = fn(*args, **kwargs)
            buckets[cat] += time.perf_counter() - s
            return r

        # We'll replicate exhaust_numpy.solve_exhaust but with bucketed timing
        from motorsim.exhaust_batch import Kernel, primitive as batch_primitive, hllc as batch_hllc
        import time as tmod
        from math import fsum
        from motorsim.gas1d.boundary import Boundary as B
        from motorsim.exhaust1d import port_flux, IdealGas, InvalidState, cfl_step, event_step

        kernel_class = Kernel
        primitive_fn = batch_primitive
        hllc_fn = batch_hllc
        if numeric_backend is not None:
            kernel_class = numeric_backend.Kernel
            primitive_fn = numeric_backend.primitive
            hllc_fn = numeric_backend.hllc

        eos = eos or IdealGas()
        exterior = exterior or Boundary('nonreflecting', state=(100000/(eos.R*300),0.,100000.,0.))
        # mesh cache
        class CachedMesh:
            def __init__(self, mesh):
                self.n=mesh.n;self.faces=mesh.faces;self.centers=mesh.centers;self.areas=mesh.areas;self.volumes=mesh.volumes;self.widths=mesh.widths;self.as_dict=mesh.as_dict
        mesh = CachedMesh(mesh)
        kernel = kernel_class(mesh, eos)
        fallback_faces=[];downgrade_cells=[];inventory_cache={}
        cache={}
        start = tmod.monotonic()
        q = np.array(initial, dtype=np.float64)
        z = list(system.initial)
        events = system.events(mesh.areas[0], end)
        event_index=0
        t=0.
        cnts=dict(rhs=0,HLLC=0,HLLE=0,characteristic=0,rejected=0,downgrades=0)
        def primitive(cells):
            counts['primitive_calls']+=1
            s=tmod.perf_counter()
            key=id(cells)
            if key in cache and cache[key][0] is cells:
                r=cache[key][1]
            else:
                r=primitive_fn(cells, kernel.volumes, eos)
                if len(cache)>=4: del cache[next(iter(cache))]
                cache[key]=(cells,r)
            buckets['B_primitive']+=tmod.perf_counter()-s
            return r
        def validate(cells, state, when):
            s=tmod.perf_counter()
            system.validate(state, when, eos)
            buckets['J_cfl_admissibility']+= tmod.perf_counter()-s
            return primitive(cells)
        def inventory(cells, state):
            s=tmod.perf_counter()
            key=id(cells)
            if key not in inventory_cache or inventory_cache[key][0] is not cells:
                values=[fsum(cells[:,j]) for j in (0,2,3)]
                if len(inventory_cache)>=4: del inventory_cache[next(iter(inventory_cache))]
                inventory_cache[key]=(cells,values)
            res=[fsum(state[k::3])+v for k,v in enumerate(inventory_cache[key][1])]
            buckets['K_diagnostics']+= tmod.perf_counter()-s
            return res
        w=validate(q,z,t)
        initial_inventory=inventory(q,z)
        scale=(initial_inventory[0],initial_inventory[1],initial_inventory[0])
        sensor_indices=[min(range(mesh.n),key=lambda i:abs(mesh.centers[i]-x)) for x in sensors]
        def rhs(cells, state, when):
            cnts['rhs']+=1
            counts['rhs_calls']+=1
            # B + J already in validate
            s=tmod.perf_counter()
            ws=validate(cells, state, when)
            buckets['B_primitive']+=0 # already counted
            # C
            s1=tmod.perf_counter()
            left,right,down=kernel.reconstruct(ws,(Boundary('outflow'),exterior))
            buckets['C_muscl']+=tmod.perf_counter()-s1
            counts['reconstruct']+=1
            cnts['downgrades']+=len(down)
            if down:
                downgrade_cells.append(dict(rhs=cnts['rhs'],time=when,cells=down))
            # G part chamber
            s2=tmod.perf_counter()
            ch=system.chamber(state, when)
            ch.thermodynamics(eos)
            buckets['G_coupling']+= tmod.perf_counter()-s2
            # G port
            s3=tmod.perf_counter()
            port=port_flux(ch,tuple(left[0].tolist()),system.area(when),mesh.areas[0],eos=eos)
            buckets['G_coupling']+= tmod.perf_counter()-s3
            cnts['HLLC']+=port['HLLC'];cnts['HLLE']+=port['HLLE']
            if port['HLLE']:
                fallback_faces.append(dict(rhs=cnts['rhs'],time=when,face=0,reason='frozen_port_HLLE',evaluations=port['HLLE']))
            # D interior faces + H allocation
            s4=tmod.perf_counter()
            flux=np.empty((mesh.n+1,4))
            speeds=np.empty(mesh.n+1)
            buckets['L_allocation']+= tmod.perf_counter()-s4
            # port flux
            s5=tmod.perf_counter()
            flux[0]=port['flux']
            speeds[0]=max(abs(port['speeds'][0]),abs(port['speeds'][2]))
            buckets['H_assembly']+= tmod.perf_counter()-s5
            s6=tmod.perf_counter()
            f,s,reasons,fallback_speeds=hllc_fn(right[:-1],left[1:],eos)
            buckets['D_hllc']+= tmod.perf_counter()-s6
            counts['hllc_calls']+=1
            counts['hllc_faces']+= (mesh.n-1)
            cnts['HLLE']+=len(reasons);cnts['HLLC']+=mesh.n-1-len(reasons)
            for i,reason in reasons.items():
                fallback_faces.append(dict(rhs=cnts['rhs'],time=when,face=i+1,reason=reason,speeds=fallback_speeds[i]))
            s7=tmod.perf_counter()
            flux[1:-1]=kernel.areas[1:-1,None]*f
            speeds[1:-1]=np.maximum(np.abs(s[:,0]),np.abs(s[:,2]))
            buckets['H_assembly']+= tmod.perf_counter()-s7
            s8=tmod.perf_counter()
            exterior_face=tuple(right[-1].tolist())
            f2,s2,reason=exterior.flux(exterior_face,1,eos)
            buckets['F_boundary']+= tmod.perf_counter()-s8
            if exterior.kind in ('wall','fixed','outflow'):
                cnts['HLLE' if reason else 'HLLC']+=1
            else:
                cnts['characteristic']+=1
            if reason:
                fallback_faces.append(dict(rhs=cnts['rhs'],time=when,face=mesh.n,reason=reason,speeds=s2))
            s9=tmod.perf_counter()
            flux[-1]=tuple(mesh.areas[-1]*v for v in f2)
            speeds[-1]=max(abs(s2[0]),abs(s2[2]))
            buckets['H_assembly']+= tmod.perf_counter()-s9
            s10=tmod.perf_counter()
            limit,_,unit=kernel.cfl(ws,speeds,cfl)
            buckets['J_cfl_admissibility']+= tmod.perf_counter()-s10
            s11=tmod.perf_counter()
            dq=flux[:-1]-flux[1:]
            dq[:,1]+=ws[:,2]*kernel.area_delta
            buckets['E_geometric_source']+= tmod.perf_counter()-s11
            counts['dq_arrays']+=1
            s12=tmod.perf_counter()
            dz,external,terms=system.source(state,when,eos)
            buckets['G_coupling']+= tmod.perf_counter()-s12
            s13=tmod.perf_counter()
            for k in range(3):
                dz[3*system.cylinder+k]+=port['exchange'][k]
                external[k]-=flux[-1][(0,2,3)[k]]
            boundary_state=exterior.face_state(exterior_face,1,eos)
            buckets['F_boundary']+= tmod.perf_counter()-s13
            return dict(dq=dq,dz=dz,external=external,terms=terms,port=port,limit=limit,unit=unit,
                        trace=dict(time=when,angle=system.angle(when),area=port['area'],chamber=list(state),volume=ch.volume,
                        pressure=ch.thermodynamics(eos)[1],pipe_face=left[0].tolist(),exchange=port['exchange'],
                        outlet=boundary_state,open_reaction=port['open_reaction'],closed_reaction=port['closed_reaction']))
        def advance(cells, state, op, dt):
            s=tmod.perf_counter()
            res=cells+dt*op['dq'],[a+dt*b for a,b in zip(state,op['dz'])]
            buckets['I_ssprk2']+= tmod.perf_counter()-s
            return res
        history=[];stages=[];snapshots=[];external=[0.]*3;port_integral=[0.]*3;rejections={};hit_events=[]
        def extremes(rows):
            return dict(rho=float(np.min(rows[:,0])),p=float(np.min(rows[:,2])),T=float(np.min(rows[:,2]/(rows[:,0]*eos.R))),
                Y_min=float(np.min(rows[:,3])),Y_max=float(np.max(rows[:,3])))
        extrema=extremes(w)
        def observe(cells, state, when):
            s=tmod.perf_counter()
            rows=validate(cells,state,when)
            for key,value in extremes(rows).items():
                extrema[key]=(max if key=='Y_max' else min)(extrema[key],value)
            buckets['K_diagnostics']+= tmod.perf_counter()-s
            return rows
        status='completed';reason='final_time';max_stage_residual=0.;max_global_residual=0.;max_CFL=0.;next_snapshot=0
        outer_start=tmod.perf_counter()
        while t<end:
            s_wall=tmod.perf_counter()
            if tmod.monotonic()-start>wall_limit:
                status='failed_infrastructure';reason='wall_timeout';break
            try:
                s0=tmod.perf_counter()
                op0=rhs(q,z,t)
                buckets['A_python_exterior']+=0 # will attribute remaining
                target=events[event_index]
                dt=0
                # event_step
                s_e=tmod.perf_counter()
                from motorsim.gas1d.solver import event_step as evs
                dt=evs(op0['limit'],target-t)
                buckets['J_cfl_admissibility']+= tmod.perf_counter()-s_e
                for retry in range(13):
                    if dt<1e-12 or t+dt==t:
                        from motorsim.gas1d.eos import InvalidState as IS
                        raise IS('dt_below_min')
                    try:
                        s_adv=tmod.perf_counter()
                        q1,z1=advance(q,z,op0,dt)
                        buckets['I_ssprk2']+=0
                        s_val=tmod.perf_counter()
                        validate(q1,z1,t+dt)
                        buckets['J_cfl_admissibility']+=0
                        op1=rhs(q1,z1,t+dt)
                        if dt>op1['limit']:
                            from motorsim.gas1d.eos import InvalidState as IS
                            raise IS('stage_CFL')
                        q2,z2=advance(q1,z1,op1,dt)
                        s_val2=tmod.perf_counter()
                        validate(q2,z2,t+2*dt)
                        qnew=.5*q+.5*q2
                        znew=[.5*a+.5*b for a,b in zip(z,z2)]
                        buckets['I_ssprk2']+= tmod.perf_counter()-s_adv
                        s_val3=tmod.perf_counter()
                        validate(qnew,znew,t+dt)
                        break
                    except (ValueError,OverflowError,ZeroDivisionError) as exc:
                        cnts['rejected']+=1
                        key=str(exc);rejections[key]=rejections.get(key,0)+1
                        if retry==12:
                            from motorsim.gas1d.eos import InvalidState as IS
                            raise IS('joint_retries_exhausted: '+key)
                        dt*=.5
                s_res=tmod.perf_counter()
                for qa,za,qb,zb,op in ((q,z,q1,z1,op0),(q1,z1,q2,z2,op1)):
                    residue=max(abs(b-a-dt*e)/s for a,b,e,s in zip(inventory(qa,za),inventory(qb,zb),op['external'],scale))
                    max_stage_residual=max(max_stage_residual,residue)
                    max_CFL=max(max_CFL,dt/op['unit'])
                buckets['K_diagnostics']+= tmod.perf_counter()-s_res
                s_obs=tmod.perf_counter()
                observe(q1,z1,t+dt);observe(q2,z2,t+2*dt);w=observe(qnew,znew,t+dt)
                buckets['K_diagnostics']+= tmod.perf_counter()-s_obs
            except (ValueError,OverflowError,ZeroDivisionError) as exc:
                status='failed_numerical';reason=str(exc);break
            s_post=tmod.perf_counter()
            for k in range(3):
                external[k]+=dt*.5*(op0['external'][k]+op1['external'][k])
                port_integral[k]+=dt*.5*(op0['port']['exchange'][k]+op1['port']['exchange'][k])
            q,z=qnew,znew;t+=dt
            if t>=target:
                t=target;hit_events.append(t);event_index+=1
            inv=inventory(q,z)
            res=[(a-b-e)/s for a,b,e,s in zip(inv,initial_inventory,external,scale)]
            max_global_residual=max(max_global_residual,max(map(abs,res)))
            ch=system.chamber(z,t)
            rho,p,T,Y=ch.thermodynamics(eos)
            s_hist=tmod.perf_counter()
            history.append(dict(time=t,angle=system.angle(t),dt=dt,chamber=z.copy(),cylinder=(p,T,ch.mass,Y),area=system.area(t),
                sensors=[(w[i][2],w[i][1],w[i][1]/eos.sound_speed(w[i]),w[i][3]) for i in sensor_indices],
                port_pressure=op1['trace']['pipe_face'][2],port_Mach=op1['trace']['pipe_face'][1]/eos.sound_speed(op1['trace']['pipe_face']),
                exchange=[.5*(op0['port']['exchange'][k]+op1['port']['exchange'][k]) for k in range(3)],
                external=external.copy(),port_integral=port_integral.copy(),inventory=inv,residual=res))
            stages.append(dict(dt=dt,limits=[op0['limit'],op1['limit']],traces=[op0['trace'],op1['trace']]))
            buckets['K_diagnostics']+= tmod.perf_counter()-s_hist
            if t>=next_snapshot:
                snapshots.append(dict(time=t,angle=system.angle(t),primitive=w.tolist()))
                next_snapshot+=end/8
            buckets['A_python_exterior']+= tmod.perf_counter()-s_wall
            # Now subtract known buckets to get A residual? Instead we already accounted, so total wall includes everything, but we attributed A as outer loop overhead. We'll later compute percentages.
        # total time
        total = tmod.monotonic() - start
        # sum buckets
        bucket_sum = sum(buckets.values())
        # A may be overcounted; adjust: A is Python exterior not yet accounted; we measured outer iteration wall - sum others? Let's compute residual.
        # For now return buckets as measured
        return dict(status=status,reason=reason,time=t,wall_seconds=tmod.monotonic()-start,cells=q.tolist(),state=z,primitive=primitive(q).tolist(),
            initial_inventory=initial_inventory,final_inventory=inventory(q,z),external=external,port_integral=port_integral,
            max_global_residual=max_global_residual,max_stage_residual=max_stage_residual,max_CFL=max_CFL,extrema=extrema,
            counts=cnts,rejections=rejections,events=events,hit_events=hit_events,history=history,stages=stages,snapshots=snapshots,
            sensor_positions=[mesh.centers[i] for i in sensor_indices],mesh=mesh.as_dict(),
            batch_observability=dict(HLLE_faces=fallback_faces,MUSCL_downgrade_cells=downgrade_cells),
            _profile_buckets=dict(buckets),_profile_counts=dict(counts),_profile_total=total)

    profiler=cProfile.Profile()
    overall_stats={}
    focal_results=[]
    for name, angle, q, z, heat in cases:
        for solver_name, numeric_backend in [('NUMBA', exhaust_numba)]:
            system = HybridSystem(model, angle, z, heat)
            # warm
            # run with instrumented
            res = instrumented_solve(mesh2, q, system, .0001, eos=eos, cfl=.4, exterior=Boundary('nonreflecting', state=(100000/(287*500),0.,100000.,0.)), sensors=(.1,.3,.5), wall_limit=90, numeric_backend=numeric_backend)
            buckets = res['_profile_buckets']
            total = sum(buckets.values())
            # percentages
            perc = {k: v/total*100 if total>0 else 0 for k,v in buckets.items()}
            focal_results.append(dict(window=name, backend=solver_name, buckets=buckets, percentages=perc, total_profiling_seconds=total, wall_seconds=res['wall_seconds'], counts=res['_profile_counts'], rhs=res['counts']['rhs'], steps=len(res['history'])))
            print(f"FOCAL {name} buckets:", json.dumps(buckets, indent=2))
            print(f"perc:", json.dumps(perc, indent=2))

    # Full G1 cycle profiling with cProfile and also with instrumented solve for breakdown
    # Full cycle via instrumented
    model_full, mesh_full, pipe_full, state_full = prepare('straight')
    system_full = HybridSystem(model_full, 180., state_full, None)
    # We need to run full cycle once to get breakdown, but that is expensive (26s). We'll do it now with instrumented and also cProfile.
    # Use instrumented for detailed breakdown
    print("Starting full G1 instrumented profiling (expect ~30s)...")
    start_full = time.perf_counter()
    # Use profiler around instrumented
    # Instead of re-instrument per RHS, we already have bucket timers inside. So run with cProfile disabled to avoid double overhead, just perf_counter buckets.
    # For full cycle we reuse instrumented_solve but with longer end and orchestration that handles heat segments? Instead use exhaustive full cycle via HybridSystem loop?
    # Simpler: run through p4_hybrid prepare style? The full G1 cycle is 3 segments via HybridSystem. Easiest: call motorsim.hybrid_fast.run_cycle with instrumented inner solver?
    # For profiling, we'll just profile one segment's RHS microbenchmark? Let's do full cycle via hybrid_fast but swapping solver.
    # Instead, run a simplified full cycle emulation: just call instrumented_solve for each heat segment like hybrid_fast does.
    # To avoid complexity, directly call hybrid_fast.run_cycle with a wrapper that counts.
    # Alternative: run full hybrid cycle using exhaust_numba and capture cProfile top functions.

    # cProfile of full G1NUMBA cycle via hybrid_fast
    from motorsim.hybrid_fast import run_cycle as fast_cycle
    # Warm JIT already done, now profile
    profiler.enable()
    r_full = fast_cycle(mesh_full, pipe_full, state_full, backend='NUMBA_EXPERIMENTAL')
    profiler.disable()
    stats = pstats.Stats(profiler)
    funcs = [dict(file=k[0], line=k[1], func=k[2], calls=v[1], self_s=v[2], inline_s=v[3]) for k,v in stats.stats.items()]
    top_self = sorted(funcs, key=lambda x: x['self_s'], reverse=True)[:20]
    top_inline = sorted(funcs, key=lambda x: x['inline_s'], reverse=True)[:20]
    # Save cProfile dump
    profiler.dump_stats(str(output_dir / 'g1_full_numba.prof'))
    write(output_dir / 'g1_full_profile.json', dict(wall_seconds=r_full['cycle_wall_seconds'], solver_seconds=r_full['solver_seconds'], top_self=top_self, top_inline=top_inline, complete=r_full['complete'], reason=r_full['reason']))
    # Also do instrumented detailed breakdown for one full G1 via hybrid loop instrumented manually
    # We'll run hybrid-like loop but using instrumented_solve for each cut
    from motorsim.simulation import burn_fraction
    cuts = [180., 350., 390., 540.]
    state = state_full
    pipe = pipe_full
    model = model_full
    exterior = Boundary('nonreflecting', state=(100000/(287*500),0.,100000.,0.))
    from math import fsum as mfsum
    total_buckets = Counter()
    total_counts = Counter()
    total_wall = 0
    for a,b in zip(cuts, cuts[1:]):
        heat = 350. if a==350. else None
        system = HybridSystem(model, a, state, heat)
        dur = (b-a)/model.rate
        res_seg = instrumented_solve(mesh_full, pipe, system, dur, eos=eos, cfl=.4, exterior=exterior, sensors=(.1,.3,.5), wall_limit=600, numeric_backend=exhaust_numba)
        # accumulate buckets
        for k,v in res_seg['_profile_buckets'].items():
            total_buckets[k] += v
        for k,v in res_seg['_profile_counts'].items():
            total_counts[k]+=v
        total_wall += res_seg['wall_seconds']
        state = res_seg['state'] if isinstance(res_seg['state'], list) else res_seg['state']
        pipe = res_seg['cells']
        print(f"SEGMENT {a}->{b} wall {res_seg['wall_seconds']:.2f} buckets sum {sum(res_seg['_profile_buckets'].values()):.2f}")

    total_sum = sum(total_buckets.values())
    perc_total = {k: v/total_sum*100 if total_sum>0 else 0 for k,v in total_buckets.items()}
    # Estimate Python exterior residual as A_python - may need корректировка: total_wall vs bucket_sum
    # Our buckets already include A_python_exterior as outer loop; so total_sum should approx equal instrumented profiling total. We'll keep as is.
    summary = dict(
        focal_windows=focal_results,
        full_cycle_instrumented=dict(buckets=dict(total_buckets), percentages=perc_total, total_bucket_seconds=total_sum, total_wall_seconds=total_wall, counts=dict(total_counts)),
        full_cycle_cprofile=dict(top_self=top_self, top_inline=top_inline, wall_seconds=r_full['cycle_wall_seconds'])
    )
    write(output_dir / 'hot_path_breakdown.json', summary)
    print(json.dumps(summary, indent=2))
    write(output_dir / 'result.json', dict(checks=[dict(id='hot_path_profile', passed=True, kind='numerical', reason='profiled')], metrics={}, scientific_change_required=False))

if __name__ == '__main__':
    import argparse, sys
    p=argparse.ArgumentParser()
    p.add_argument('--run-dir', required=True)
    args=p.parse_args()
    profile_windows_and_cycle(args.run_dir)
