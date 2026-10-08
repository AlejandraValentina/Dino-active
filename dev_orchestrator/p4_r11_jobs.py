"""P4-R11 long horizon jobs"""
import json, gzip, time, hashlib
from pathlib import Path
import numpy as np

def _periodic_metrics(prev, cur):
    """Copy of p4_r8 _periodic_detailed but also returns passed"""
    from bisect import bisect_right
    def rel(a,b,floor=0.):
        return abs(a-b)/max(abs(a),abs(b),floor)
    def curve(row, key, idx=None):
        hs=row['history']
        xs=[h['angle']-row['begin'] for h in hs]
        if xs[0]>0.5 or xs[-1]!=360.:
            raise ValueError(f"Incomplete {xs[0]} {xs[-1]}")
        ys=[h[key] if idx is None else h[key][idx][0] for h in hs]
        out=[]
        phases=[]
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
    work_rel=rel(prev['work_indicated_J'], cur['work_indicated_J'],1.)
    p_cyl_prev, _phases = curve(prev,'p_cyl')
    p_cyl_cur, _phases2 = curve(cur,'p_cyl')
    cyl_diffs=[abs(a-b) for a,b in zip(p_cyl_prev,p_cyl_cur)]
    cyl_max=max(cyl_diffs)
    cyl_denom=max(map(abs, p_cyl_prev+p_cyl_cur))
    cyl_metric=cyl_max/cyl_denom if cyl_denom else 0
    sensor_metrics=[]
    sensor_details=[]
    for si in range(3):
        a,_=curve(prev,'sensors_p_u_M_Y',si)
        b,_=curve(cur,'sensors_p_u_M_Y',si)
        diffs=[abs(x-y) for x,y in zip(a,b)]
        maxd=max(diffs)
        denom=max(map(abs, a+b))
        metric=maxd/denom if denom else 0
        idx=diffs.index(maxd)
        phases=[i*0.5 for i in range(1,721)]
        grad_a=0; grad_b=0
        if 0<idx<len(a)-1:
            grad_a=(a[idx+1]-a[idx-1])/1.0
            grad_b=(b[idx+1]-b[idx-1])/1.0
        sensor_metrics.append(metric)
        sensor_details.append(dict(sensor_index=si, phase=phases[idx], p_prev=a[idx], p_cur=b[idx], diff=maxd, denom=denom, metric=metric, grad_prev=grad_a, grad_cur=grad_b))
    sensor_max=max(sensor_metrics)
    sensor_max_idx=sensor_metrics.index(sensor_max)
    # port
    port_rel=rel(prev['port_integral'][0], cur['port_integral'][0], cur['initial_cylinder_mass'])
    a_state,b_state=prev['state'],cur['state']
    inventories=[]
    for k in (0,3,6):
        inventories.append(rel(a_state[k],b_state[k]))
        inventories.append(rel(a_state[k+1],b_state[k+1]))
        if a_state[k]!=0 and b_state[k]!=0:
            inventories.append(abs(a_state[k+2]/a_state[k]-b_state[k+2]/b_state[k]))
        else:
            inventories.append(0)
    from math import fsum
    pa=[fsum(c[j] for c in prev['cells']) for j in (0,2,3)]
    pb=[fsum(c[j] for c in cur['cells']) for j in (0,2,3)]
    inventories.append(rel(pa[0],pb[0]))
    inventories.append(rel(pa[1],pb[1]))
    inventories.append(abs(pa[2]-pb[2])/max(pa[0],pb[0]) if max(pa[0],pb[0]) else 0)
    passed = work_rel<=0.005 and cyl_metric<=0.005 and sensor_max<=0.005 and port_rel<=0.002 and max(inventories)<=0.002
    return dict(work=work_rel, cylinder=cyl_metric, sensor_pressure=sensor_metrics, sensor_max=sensor_max, sensor_max_idx=sensor_max_idx, sensor_details=sensor_details, port_mass=port_rel, inventories=inventories, inv_max=max(inventories), passed=passed)

def _vector_norm(prev, cur):
    import math
    from math import fsum
    def norm(a,b,scale):
        return abs(a-b)/max(abs(a),abs(b),scale) if max(abs(a),abs(b),scale)!=0 else 0
    a=prev['state']; b=cur['state']
    pa=[fsum(c[j] for c in prev['cells']) for j in range(4)]
    pb=[fsum(c[j] for c in cur['cells']) for j in range(4)]
    comps=[]
    for i in range(9):
        comps.append(norm(a[i],b[i], 1.0 if i%3==1 else 0.001))
    for j in range(4):
        comps.append(norm(pa[j],pb[j], 1e-6 if j==0 else 1.0))
    return dict(max_norm=max(comps), l2=math.sqrt(sum(c*c for c in comps)/len(comps)))

def p4_r11_cycle_job(job_id, job_dir, worker_id, N, dx_target, start_cycle, max_cycle, backend='NUMBA_FUSED', cfl=0.4):
    """Continue from cycle start_cycle (40) to max_cycle (60 or 80), with early stop 3x lag-2 PASS"""
    import json, gzip, time, hashlib
    from pathlib import Path
    from motorsim.exhaust_geometry import exhaust_mesh
    from dev_orchestrator.p4_waves import segments
    from motorsim.hybrid_fast import run_cycle
    from motorsim.checkpoint import save_summary, save_restart
    from dev_orchestrator.p4_hybrid import checks

    # Load start state: try R11 stageA restart for any start >40, then R8
    import gzip as gz, json as js
    row0 = None
    state = None
    cells = None
    begin = None
    # Try R11 stageA for start >=41
    if start_cycle >= 41:
        # Try restart first
        candidates = [
            Path(f"results/p4-r12-20260922/campaign_N{N}_45_52/jobs/G1_N{N}_45_52/restart_cycle{start_cycle:02}/state.npz"),
            Path(f"results/p4-r12-20260922/campaign_N{N}_50_54/jobs/G1_N{N}_50_54/restart_cycle{start_cycle:02}/state.npz"),
            Path(f"results/p4-r11-20260922/campaign_stageA/jobs/G1_N{N}_A/restart_cycle{start_cycle:02}/state.npz"),
        ]
        cand = next((p for p in candidates if p.exists()), candidates[-1])
        if cand.exists():
            from motorsim.checkpoint import load_restart
            meta, s_arr, c_arr = load_restart(cand.parent)
            # Try to load full for history
            full_path = cand.parent.parent / f"full_cycle{start_cycle:02}.json.gz"
            if full_path.exists():
                try:
                    row0 = js.loads(gz.decompress(full_path.read_bytes()))
                except:
                    row0 = None
            if row0 is None:
                # Create minimal row from restart (history will be duplicated)
                row0 = dict(state=s_arr.tolist(), cells=c_arr.tolist(), end=meta['angle'], begin=meta['angle']-360, history=[], initial_cylinder_mass=float(s_arr[6]) if len(s_arr)>6 else 0.0001)
            state = s_arr.tolist() if isinstance(s_arr, np.ndarray) else s_arr
            cells = c_arr.tolist() if isinstance(c_arr, np.ndarray) else c_arr
            begin = float(meta['angle'])
        else:
            # Try summary? For 45 we have summary but need state/cells from restart 45? Actually restart 45 exists, so above should have found it
            # If not, try loading from summary's state? But summary doesn't have state/cells full?
            # Fallback to try full_cycle directly
            full_path = Path(f"results/p4-r11-20260922/campaign_stageA/jobs/G1_N{N}_A/full_cycle{start_cycle:02}.json.gz")
            if full_path.exists():
                row0 = js.loads(gz.decompress(full_path.read_bytes()))
                state = row0['state']
                cells = row0['cells']
                begin = row0['end']
    if row0 is None:
        # Fallback to R8
        if N==300:
            src = Path(f"results/p4-r8-20260922/artifacts/N300-continuation-cycle{start_cycle:02}.json.gz")
            if not src.exists():
                src = Path(f"results/p4-r7-20260921/spatial_N300_cycle{start_cycle:02}.json.gz")
                if not src.exists():
                    src = Path(f"results/p4-r8-20260922/artifacts/N300-continuation-cycle40.json.gz")
        elif N==350:
            src = Path(f"results/p4-r8-20260922/campaign_N350_N400/jobs/G1_N350_30cycles/G1-cycle{start_cycle:02}.json.gz")
        elif N==400:
            src = Path(f"results/p4-r8-20260922/campaign_N350_N400/jobs/G1_N400_30cycles/G1-cycle{start_cycle:02}.json.gz")
        else:
            raise ValueError(N)
        if src.exists():
            row0 = js.loads(gz.decompress(src.read_bytes()))
            state = row0['state']
            cells = row0['cells']
            begin = row0['end']
        else:
            raise FileNotFoundError(f"No source for N{N} cycle {start_cycle}")
    # Prepare mesh
    from motorsim.exhaust_geometry import exhaust_mesh
    from dev_orchestrator.p4_waves import segments
    mesh = exhaust_mesh(segments('straight'), dx_target)
    # Keep history for metrics: need last 2 cycles before start for lag-2
    # For start 40, need 38,39,40; for start 60, need 58,59,60
    history_rows = []
    for cyc in [start_cycle-2, start_cycle-1, start_cycle]:
        # Try to load full row for cyc
        p = None
        if N==300:
            # First try R11 stageA if cyc 58-60
            if cyc >= 41:
                p = Path(f"results/p4-r11-20260922/campaign_stageA/jobs/G1_N{N}_A/full_cycle{cyc:02}.json.gz")
                if not p.exists():
                    p = Path(f"results/p4-r8-20260922/artifacts/N300-continuation-cycle{cyc:02}.json.gz")
                    if not p.exists():
                        p = Path(f"results/p4-r7-20260921/spatial_N300_cycle{cyc:02}.json.gz")
            else:
                p = Path(f"results/p4-r8-20260922/artifacts/N300-continuation-cycle{cyc:02}.json.gz")
                if not p.exists():
                    p = Path(f"results/p4-r7-20260921/spatial_N300_cycle{cyc:02}.json.gz")
        elif N==350:
            if cyc >= 41:
                p = Path(f"results/p4-r11-20260922/campaign_stageA/jobs/G1_N{N}_A/full_cycle{cyc:02}.json.gz")
                if not p.exists():
                    p = Path(f"results/p4-r8-20260922/campaign_N350_N400/jobs/G1_N350_30cycles/G1-cycle{cyc:02}.json.gz")
            else:
                p = Path(f"results/p4-r8-20260922/campaign_N350_N400/jobs/G1_N350_30cycles/G1-cycle{cyc:02}.json.gz")
        else:
            if cyc >= 41:
                p = Path(f"results/p4-r11-20260922/campaign_stageA/jobs/G1_N{N}_A/full_cycle{cyc:02}.json.gz")
                if not p.exists():
                    p = Path(f"results/p4-r8-20260922/campaign_N350_N400/jobs/G1_N400_30cycles/G1-cycle{cyc:02}.json.gz")
            else:
                p = Path(f"results/p4-r8-20260922/campaign_N350_N400/jobs/G1_N400_30cycles/G1-cycle{cyc:02}.json.gz")
        if p and p.exists():
            try:
                history_rows.append(js.loads(gz.decompress(p.read_bytes())))
            except:
                history_rows.append(row0)
        else:
            history_rows.append(row0)
    while len(history_rows) < 3:
        history_rows.insert(0, row0)

    job_path = Path(job_dir)
    job_path.mkdir(parents=True, exist_ok=True)
    # For metrics
    temporal = []
    # For early stop tracking lag-2 streak
    lag2_streak = 0
    first_streak_cycle = None
    # Also need to keep all rows for final analysis (41..)
    all_rows = history_rows.copy() # includes 38,39,40

    s = state
    c = cells
    cur_begin = begin
    start_time = time.perf_counter()
    cycles_executed = 0
    for cycle in range(start_cycle+1, max_cycle+1):
        # Run one cycle
        row = run_cycle(mesh, c, s, cur_begin, backend=backend, cfl=cfl)
        row['initial_cylinder_mass'] = s[6]
        # checks
        ck = checks(row)
        # Compute D1 (n vs n-1) and D2 (n vs n-2)
        prev1 = all_rows[-1] # n-1
        prev2 = all_rows[-2] # n-2
        try:
            d1 = _periodic_metrics(prev1, row)
            d2 = _periodic_metrics(prev2, row)
            vec1 = _vector_norm(prev1, row)
            vec2 = _vector_norm(prev2, row)
        except Exception as e:
            d1 = dict(passed=False, error=str(e))
            d2 = dict(passed=False, error=str(e))
            vec1 = dict(max_norm=1)
            vec2 = dict(max_norm=1)
        # Record temporal
        # Normalize bool to Python bool for JSON (avoid np.bool_ -> "False" via default=str)
        def _to_py_bool(v):
            if isinstance(v, (bool,)):
                return bool(v)
            try:
                import numpy as np
                if isinstance(v, np.bool_):
                    return bool(v)
            except:
                pass
            return bool(v) if isinstance(v, (int, float)) and v in (0,1) else v
        temporal.append(dict(
            cycle=cycle,
            work=row['work_indicated_J'],
            d1_work=d1.get('work'), d1_sensor_max=d1.get('sensor_max'), d1_cyl=d1.get('cylinder'), d1_passed=bool(d1.get('passed')),
            d2_work=d2.get('work'), d2_sensor_max=d2.get('sensor_max'), d2_cyl=d2.get('cylinder'), d2_passed=bool(d2.get('passed')),
            d2_details=d2.get('sensor_details'),
            vec1=vec1, vec2=vec2,
            port_exchange=row['port_integral'][0],
            pipe_mass=sum(c2[0] for c2 in row['cells']),
            pipe_energy=sum(c2[2] for c2 in row['cells']),
            pipe_species=sum(c2[3] for c2 in row['cells']),
            global_balance=row['global_balance'],
            admissibility=all(ck.values()),
            conservation_pass=all(ck.values()),
            wall=row['cycle_wall_seconds']
        ))
        # Check early stop: D2 3 consecutive PASS
        if d2.get('passed'):
            lag2_streak += 1
            if lag2_streak == 1:
                first_streak_start = cycle
            if lag2_streak >= 3:
                # Check D1 FAIL for those 3? For diagnostic, we need D1 FAIL to confirm period-2, but early stop valid if D2 3x PASS regardless per spec (not requiring D1)
                # Record first 3x
                if first_streak_cycle is None:
                    first_streak_cycle = cycle
                # If we have 3 consecutive, we can stop this job
                # But per spec, job may stop early, we break
                # Save and break
                # Still need to save checkpoint for this cycle
                pass
        else:
            lag2_streak = 0
            first_streak_start = None

        # Save SUMMARY each cycle
        from motorsim.checkpoint import save_summary, save_restart
        summary_path = job_path / f"summary_cycle{cycle:02}.json"
        save_summary(row, summary_path)
        # RESTART every 5
        if cycle % 5 == 0 or cycle == max_cycle:
            restart_dir = job_path / f"restart_cycle{cycle:02}"
            config = dict(dx_target=dx_target, backend=backend, cfl=cfl, config_hash=hashlib.sha256(json.dumps(dict(N=N)).encode()).hexdigest()[:12])
            save_restart(row['state'], row['cells'], cycle=cycle, angle=row['end'], config=config, out_dir=restart_dir, compressed=False)
        # FULL_DEBUG at 50,60,70,80
        if cycle in [50,60,70,80]:
            full_path = job_path / f"full_cycle{cycle:02}.json.gz"
            full_path.write_bytes(gz.compress(json.dumps(row).encode()))

        # Update for next
        all_rows.append(row)
        s = row['state']
        c = row['cells']
        cur_begin = row['end']
        cycles_executed += 1

        # Check early stop after saving
        if lag2_streak >= 3:
            # Need to ensure we have 3 consecutive, so if we just reached 3, we break after this cycle
            # But spec says job may stop after 3x, we break
            # However we should only break if we have just achieved 3x and this is the third
            # Our lag2_streak counts consecutive, so when it reaches 3 we have 3 in a row ending at this cycle
            print(f"N{N} early stop at cycle {cycle} 3x lag2 PASS", flush=True)
            break

        # Also check conservation/admissibility failure -> stop
        if not all(ck.values()):
            print(f"N{N} stop due to conservation/admissibility fail at cycle {cycle}", flush=True)
            break

    total_wall = time.perf_counter() - start_time
    # Determine streak max and first
    # Compute max streak in temporal
    max_streak = 0
    cur_streak = 0
    first_3 = None
    for t in temporal:
        if t['d2_passed']:
            cur_streak+=1
            if cur_streak==3 and first_3 is None:
                first_3=t['cycle']
            max_streak=max(max_streak, cur_streak)
        else:
            cur_streak=0

    result = dict(
        job_id=job_id, N=N, dx_target=dx_target,
        start_cycle=start_cycle, max_cycle=max_cycle,
        cycles_executed=cycles_executed,
        temporal=temporal,
        max_streak=max_streak,
        first_3x_cycle=first_3,
        lag2_streak_final=lag2_streak,
        total_wall=total_wall,
        avg_wall=total_wall/cycles_executed if cycles_executed else 0,
        # For orbit AB: need to characterize A/B difference from last cycles
        # Use last two cycles work diff
        work_last_two=[t['work'] for t in temporal[-2:]] if len(temporal)>=2 else [],
        # Also need to know D1 final
        d1_final=temporal[-1]['d1_passed'] if temporal else None,
        d2_final=temporal[-1]['d2_passed'] if temporal else None,
    )
    (job_path / "r11_result.json").write_text(json.dumps(result, indent=2, default=str))
    return result
