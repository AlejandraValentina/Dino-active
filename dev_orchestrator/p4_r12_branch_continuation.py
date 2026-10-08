import json, time
from pathlib import Path
from dev_orchestrator.multicore import Campaign, Job

def p4_r12_branch_job(job_id, job_dir, worker_id, N, dx_target, start_cycle, max_cycle):
    import json, gzip, time, hashlib
    from pathlib import Path
    import numpy as np
    from motorsim.exhaust_geometry import exhaust_mesh
    from dev_orchestrator.p4_waves import segments
    from motorsim.hybrid_fast import run_cycle
    from motorsim.checkpoint import save_summary, save_restart
    from dev_orchestrator.p4_hybrid import checks
    from bisect import bisect_right

    def rel(a,b,floor=0.):
        return abs(a-b)/max(abs(a),abs(b),floor)
    def curve(row, key, idx=None):
        hs=row['history']
        xs=[h['angle']-row['begin'] for h in hs]
        if xs[0]>0.5 or xs[-1]!=360.:
            raise ValueError(f"Incomplete {xs[0]} {xs[-1]}")
        ys=[h[key] if idx is None else h[key][idx][0] for h in hs]
        out=[]; phases=[]
        for phase in (i*0.5 for i in range(1,721)):
            phases.append(phase)
            j=bisect_right(xs, phase)
            if j==0:
                out.append(ys[0])
            elif j==len(xs):
                out.append(ys[-1])
            else:
                out.append(ys[j-1]+(ys[j]-ys[j-1])*(phase-xs[j-1])/(xs[j]-xs[j-1]))
        return out, phases
    def periodic(prev, cur):
        work_rel=rel(prev['work_indicated_J'], cur['work_indicated_J'],1.)
        p_prev,_=curve(prev,'p_cyl')
        p_cur,_=curve(cur,'p_cyl')
        cyl_max=max(abs(a-b) for a,b in zip(p_prev,p_cur))
        cyl_denom=max(map(abs, p_prev+p_cur))
        cyl=cyl_max/cyl_denom if cyl_denom else 0
        sensor=[]
        for si in range(3):
            a,_=curve(prev,'sensors_p_u_M_Y',si)
            b,_=curve(cur,'sensors_p_u_M_Y',si)
            diffs=[abs(x-y) for x,y in zip(a,b)]
            maxd=max(diffs)
            denom=max(map(abs, a+b))
            sensor.append(maxd/denom if denom else 0)
        sensor_max=max(sensor)
        port=rel(prev['port_integral'][0], cur['port_integral'][0], cur['initial_cylinder_mass'])
        a_state,b_state=prev['state'],cur['state']
        inv=[]
        for k in (0,3,6):
            inv.append(rel(a_state[k],b_state[k]))
            inv.append(rel(a_state[k+1],b_state[k+1]))
            inv.append(abs(a_state[k+2]/a_state[k]-b_state[k+2]/b_state[k]) if a_state[k] and b_state[k] else 0)
        from math import fsum
        pa=[fsum(c[j] for c in prev['cells']) for j in (0,2,3)]
        pb=[fsum(c[j] for c in cur['cells']) for j in (0,2,3)]
        inv.append(rel(pa[0],pb[0])); inv.append(rel(pa[1],pb[1])); inv.append(abs(pa[2]-pb[2])/max(pa[0],pb[0]) if max(pa[0],pb[0]) else 0)
        passed = work_rel<=0.005 and cyl<=0.005 and sensor_max<=0.005 and port<=0.002 and max(inv)<=0.002
        return dict(work=work_rel, cylinder=cyl, sensor_max=sensor_max, port=port, inv_max=max(inv), passed=bool(passed))

    # Load start state
    import gzip as gz, json as js
    row0=None; state=None; cells=None; begin=None
    # Try R11 stageA restart for start >=41
    cand = Path(f"results/p4-r11-20260922/campaign_stageA/jobs/G1_N{N}_A/restart_cycle{start_cycle:02}/state.npz")
    if cand.exists():
        from motorsim.checkpoint import load_restart
        meta, s_arr, c_arr = load_restart(cand.parent)
        full_path = cand.parent.parent / f"full_cycle{start_cycle:02}.json.gz"
        if full_path.exists():
            try:
                row0 = js.loads(gz.decompress(full_path.read_bytes()))
            except:
                row0=None
        if row0 is None:
            row0 = dict(state=s_arr.tolist(), cells=c_arr.tolist(), end=float(meta['angle']), begin=float(meta['angle'])-360, history=[], initial_cylinder_mass=float(s_arr[6]) if len(s_arr)>6 else 0.0001)
        state = s_arr.tolist() if isinstance(s_arr, np.ndarray) else s_arr
        cells = c_arr.tolist() if isinstance(c_arr, np.ndarray) else c_arr
        begin = float(meta['angle'])
    if row0 is None:
        # Fallback R8
        if N==350:
            src=Path(f"results/p4-r8-20260922/campaign_N350_N400/jobs/G1_N350_30cycles/G1-cycle{start_cycle:02}.json.gz")
        elif N==400:
            src=Path(f"results/p4-r8-20260922/campaign_N350_N400/jobs/G1_N400_30cycles/G1-cycle{start_cycle:02}.json.gz")
        else:
            src=Path(f"results/p4-r8-20260922/artifacts/N300-continuation-cycle{start_cycle:02}.json.gz")
        row0 = js.loads(gz.decompress(src.read_bytes()))
        state=row0['state']; cells=row0['cells']; begin=row0['end']
    from motorsim.exhaust_geometry import exhaust_mesh
    from dev_orchestrator.p4_waves import segments
    mesh = exhaust_mesh(segments('straight'), 0.75/N)
    # History for lag-2: need last 2 cycles before start
    history_rows=[]
    for cyc in [start_cycle-2, start_cycle-1, start_cycle]:
        p=None
        if cyc >= 41:
            # Try R11 stageA
            cand2 = Path(f"results/p4-r11-20260922/campaign_stageA/jobs/G1_N{N}_A/full_cycle{cyc:02}.json.gz")
            if cand2.exists():
                p=cand2
            else:
                # Try summary? Use row0 for 45 etc.
                p=None
        else:
            # R8
            if N==350:
                p=Path(f"results/p4-r8-20260922/campaign_N350_N400/jobs/G1_N350_30cycles/G1-cycle{cyc:02}.json.gz")
            elif N==400:
                p=Path(f"results/p4-r8-20260922/campaign_N350_N400/jobs/G1_N400_30cycles/G1-cycle{cyc:02}.json.gz")
            else:
                p=Path(f"results/p4-r8-20260922/artifacts/N300-continuation-cycle{cyc:02}.json.gz")
        if p and p.exists():
            try:
                history_rows.append(js.loads(gz.decompress(p.read_bytes())))
            except:
                history_rows.append(row0)
        else:
            history_rows.append(row0)
    while len(history_rows)<3:
        history_rows.insert(0,row0)
    job_path=Path(job_dir); job_path.mkdir(parents=True, exist_ok=True)
    temporal=[]
    # Track branch streaks
    odd_streak=0; even_streak=0
    odd_first=None; even_first=None
    all_rows=history_rows.copy()
    s=state; c=cells; cur_begin=begin
    import time as tm
    start_tm=tm.perf_counter()
    for cycle in range(start_cycle+1, max_cycle+1):
        row=run_cycle(mesh, c, s, cur_begin, backend='NUMBA_FUSED', cfl=0.4)
        row['initial_cylinder_mass']=s[6]
        ck=checks(row)
        prev1=all_rows[-1]; prev2=all_rows[-2]
        try:
            d1=periodic(prev1, row)
            d2=periodic(prev2, row)
        except Exception as e:
            d1=dict(passed=False); d2=dict(passed=False)
        # Branch
        is_even = (cycle%2==0)
        if d2['passed']:
            if is_even:
                even_streak+=1
                if even_streak==3 and even_first is None:
                    even_first=cycle-2
                # Keep odd streak separate
                # We need separate counters, not resetting to 0 for other branch
                # So we need to keep odd_streak as is, not reset
                # Instead, we should track separately
                pass
            else:
                odd_streak+=1
                if odd_streak==3 and odd_first is None:
                    odd_first=cycle-2
        else:
            if is_even:
                even_streak=0
            else:
                odd_streak=0
        # Our current code resets odd_streak to 0 when even passes (because we set odd_streak=0 in even branch). That's wrong.
        # Fix: track separately, don't reset other
        # We need to fix this logic: even_streak should only reset when even fails, odd when odd fails
        # So we need to restructure
        # For now, we will recompute after loop
        temporal.append(dict(cycle=cycle, d1_passed=bool(d1['passed']), d2_passed=bool(d2['passed']), d2_sensor_max=d2.get('sensor_max'), d1_sensor_max=d1.get('sensor_max'), work=row['work_indicated_J'], is_even=is_even, even_streak=even_streak, odd_streak=odd_streak, admissibility=all(ck.values())))
        # Save summary/restart
        from motorsim.checkpoint import save_summary, save_restart
        save_summary(row, job_path/f"summary_cycle{cycle:02}.json")
        if cycle%5==0 or cycle==max_cycle:
            save_restart(row['state'], row['cells'], cycle=cycle, angle=row['end'], config=dict(dx_target=0.75/N, backend='NUMBA_FUSED', cfl=0.4), out_dir=job_path/f"restart_cycle{cycle:02}", compressed=False)
        if cycle in [50,60,70,80]:
            (job_path/f"full_cycle{cycle:02}.json.gz").write_bytes(gz.compress(json.dumps(row).encode()))
        all_rows.append(row)
        s=row['state']; c=row['cells']; cur_begin=row['end']
        # Check if both branches have 3x
        # Recompute even/odd streaks correctly from temporal
        # Even streak: last 3 even cycles all pass?
        # Find last 3 even cycles
        even_cycles = [t for t in temporal if t['is_even']]
        odd_cycles = [t for t in temporal if not t['is_even']]
        # Check last 3 of each
        even_3 = len(even_cycles)>=3 and all(e['d2_passed'] for e in even_cycles[-3:])
        odd_3 = len(odd_cycles)>=3 and all(o['d2_passed'] for o in odd_cycles[-3:])
        if even_3 and odd_3:
            print(f"N{N} both branches 3x at cycle {cycle} even {even_cycles[-3]['cycle']},{even_cycles[-2]['cycle']},{even_cycles[-1]['cycle']} odd {odd_cycles[-3]['cycle']},{odd_cycles[-2]['cycle']},{odd_cycles[-1]['cycle']}", flush=True)
            break
        if not all(ck.values()):
            print(f"N{N} stop conservation fail at {cycle}", flush=True)
            break
    total_wall=tm.perf_counter()-start_tm
    # Recompute final even/odd streaks correctly
    even_cycles = [t for t in temporal if t['is_even']]
    odd_cycles = [t for t in temporal if not t['is_even']]
    def max_streak(cycles):
        max_s=0; cur=0; first=None
        for i,c in enumerate(cycles):
            if c['d2_passed']:
                cur+=1
                if cur==3 and first is None:
                    first=cycles[i-2]['cycle']
                max_s=max(max_s,cur)
            else:
                cur=0
        return max_s, first
    even_max, even_first = max_streak(even_cycles)
    odd_max, odd_first = max_streak(odd_cycles)
    result=dict(N=N, start_cycle=start_cycle, max_cycle=max_cycle, cycles_executed=len(temporal), temporal=temporal, even_max=even_max, even_first=even_first, odd_max=odd_max, odd_first=odd_first, both_closed=(even_max>=3 and odd_max>=3), total_wall=total_wall)
    (job_path/"r12_result.json").write_text(json.dumps(result, indent=2, default=str))
    return result

if __name__=="__main__":
    # Test
    pass
