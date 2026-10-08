"""P4-R8 jobs for multicore execution.

All jobs are top-level functions for pickleability via ProcessPoolExecutor.
Uses frozen science: Euler quasi-1D, HLLC/HLLE, MUSCL/minmod, SSP-RK2, CFL 0.4, coupling, etc.
Backend NUMBA_FUSED, float64, fastmath=False, parallel=False.
"""
import gzip
import json
import math
import time
from pathlib import Path
from math import fsum

def _prepare(label, dx_target):
    from motorsim.exhaust_geometry import exhaust_mesh
    from dev_orchestrator.p4_waves import segments
    from motorsim.hybrid_exhaust import LegacySources
    from motorsim.gas1d.eos import IdealGas
    model = LegacySources()
    mesh = exhaust_mesh(segments(label), dx_target)
    p, T, Y = model.case.initial_pty[3]
    eos = IdealGas()
    U = eos.conservative((p/(eos.R*T), 0., p, Y))
    pipe = [tuple(v*u for u in U) for v in mesh.volumes]
    state = model.initial_state()[:9]
    return model, mesh, pipe, state

def _periodic_metrics(prev, cur):
    """Copied from p4_hybrid.periodic exact definition."""
    from bisect import bisect_right
    def relative(a,b,floor=0.):
        return abs(a-b)/max(abs(a),abs(b),floor)
    def curve(row,key,index=None):
        hs=row['history']; xs=[h['angle']-row['begin'] for h in hs]
        if xs[0]>.5 or xs[-1]!=360.:
            raise ValueError('Incomplete phase support')
        ys=[h[key] if index is None else h[key][index][0] for h in hs]
        out=[]
        for phase in (i*.5 for i in range(1,721)):
            j=bisect_right(xs,phase)
            if j==0 or j==len(xs):
                out.append(ys[0] if j==0 else ys[-1])
            else:
                out.append(ys[j-1]+(ys[j]-ys[j-1])*(phase-xs[j-1])/(xs[j]-xs[j-1]))
        return out
    def pressure(key,index=None):
        a=curve(prev,key,index); b=curve(cur,key,index)
        return max(abs(x-y) for x,y in zip(a,b))/max(map(abs,a+b))
    a,b=prev['state'],cur['state']
    inventories=[]
    for k in (0,3,6):
        inventories.extend((relative(a[k],b[k]),relative(a[k+1],b[k+1]),abs(a[k+2]/a[k]-b[k+2]/b[k]) if a[k]!=0 and b[k]!=0 else 0))
    pa=[fsum(c[j] for c in prev['cells']) for j in (0,2,3)]
    pb=[fsum(c[j] for c in cur['cells']) for j in (0,2,3)]
    inventories.extend((relative(pa[0],pb[0]),relative(pa[1],pb[1]),abs(pa[2]-pb[2])/max(pa[0],pb[0]) if max(pa[0],pb[0]) else 0))
    metrics=dict(
        work=relative(prev['work_indicated_J'],cur['work_indicated_J'],1.),
        cylinder_pressure=pressure('p_cyl'),
        sensor_pressure=[pressure('sensors_p_u_M_Y',i) for i in range(3)],
        port_mass=relative(prev['port_integral'][0],cur['port_integral'][0],cur['initial_cylinder_mass']),
        inventories=inventories,
    )
    metrics['sensor_max']=max(metrics['sensor_pressure'])
    metrics['inv_max']=max(inventories)
    metrics['passed']=metrics['work']<=0.005 and metrics['cylinder_pressure']<=0.005 and metrics['sensor_max']<=0.005 and metrics['port_mass']<=0.002 and metrics['inv_max']<=0.002
    return metrics

def _vector_norm(prev, cur):
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
    import math as _m
    return dict(max_norm=max(comps), l2=_m.sqrt(sum(c*c for c in comps)/len(comps)))

def p4_r8_gas_job(job_id, job_dir, worker_id, N, dx_target, cycles=2, backend='NUMBA_FUSED', cfl=0.4):
    """Deterministic gas job: run `cycles` G1 cycles from canonical initial condition.
    Returns work list, hashes, runtime. Used for multicore equivalence test and for N350/N400 campaigns.
    """
    from motorsim.hybrid_fast import run_cycle
    model, mesh, pipe, state = _prepare('straight', dx_target)
    # verify N matches expectation
    # allow tolerance: mesh.n should equal N for straight
    if mesh.n != N:
        # Still proceed but note
        pass
    begin = 180.0
    s = state
    c = pipe
    works = []
    walls = []
    # store per-cycle files in job_dir for evidence
    job_path = Path(job_dir)
    job_path.mkdir(parents=True, exist_ok=True)
    history = []
    for i in range(cycles):
        row = run_cycle(mesh, c, s, begin + i*360, backend=backend, cfl=cfl)
        row['initial_cylinder_mass'] = s[6]
        works.append(row['work_indicated_J'])
        walls.append(row['cycle_wall_seconds'])
        # save cycle for determinism check (compressed)
        # but keep small for equivalence test
        # save hashes
        import hashlib, json as _js
        state_hash = hashlib.sha256(_js.dumps(row['state']).encode()).hexdigest()[:12]
        cells_hash = hashlib.sha256(_js.dumps(row['cells']).encode()).hexdigest()[:12]
        history.append(dict(cycle=i+1, work=row['work_indicated_J'], state_hash=state_hash, cells_hash=cells_hash, wall=row['cycle_wall_seconds']))
        # conservation check
        # write cycle json for evidence (light)
        # we keep full row for potential reuse
        # compress to job_dir
        # For equivalence test we only need 2 cycles, so store both
        # For campaign we store all
        if cycles <= 5 or i >= cycles-2:
            # save last 2 for comparison
            p = job_path / f"cycle{i+1:02}.json.gz"
            p.write_bytes(gzip.compress(json.dumps(row).encode()))
        s = row['state']
        c = row['cells']
    total_wall = sum(walls)
    result = dict(job_id=job_id, worker_id=worker_id, N=N, dx_target=dx_target, mesh_n=mesh.n, cycles=cycles, backend=backend, cfl=cfl, works=works, walls=walls, total_wall=total_wall, history=history)
    # also write result.json already handled by wrapper, but write explicit for debugging
    (job_path / "gas_result.json").write_text(json.dumps(result, indent=2))
    return result

def p4_r8_continuation_job(job_id, job_dir, worker_id, N, dx_target, start_cycle, start_state, start_cells, start_angle, cycles=10, backend='NUMBA_FUSED', cfl=0.4):
    """Continuation from checkpoint: start_state/cells at start_angle, run `cycles` additional cycles."""
    from motorsim.exhaust_geometry import exhaust_mesh
    from dev_orchestrator.p4_waves import segments
    from motorsim.hybrid_fast import run_cycle
    # Need to reconstruct mesh (same N)
    model, mesh, _, _ = _prepare('straight', dx_target)
    s = start_state
    c = start_cells
    begin = start_angle  # angle at start (end of previous cycle)
    # start_cycle is number of already completed cycles (e.g., 30), next cycle is start_cycle+1
    works = []
    walls = []
    rows = []
    job_path = Path(job_dir)
    job_path.mkdir(parents=True, exist_ok=True)
    for i in range(cycles):
        cycle_num = start_cycle + 1 + i
        row = run_cycle(mesh, c, s, begin + i*360, backend=backend, cfl=cfl)
        row['initial_cylinder_mass'] = s[6]
        works.append(row['work_indicated_J'])
        walls.append(row['cycle_wall_seconds'])
        rows.append(row)
        # save
        p = job_path / f"cycle{cycle_num:02}.json.gz"
        p.write_bytes(gzip.compress(json.dumps(row).encode()))
        s = row['state']
        c = row['cells']
    result = dict(job_id=job_id, worker_id=worker_id, N=N, dx_target=dx_target, start_cycle=start_cycle, start_angle=start_angle, cycles=cycles, works=works, walls=walls, total_wall=sum(walls))
    (job_path / "continuation_result.json").write_text(json.dumps(result, indent=2))
    return result

def p4_r8_N_campaign_job(job_id, job_dir, worker_id, N, dx_target, max_cycles=30, backend='NUMBA_FUSED', cfl=0.4):
    """Full campaign from canonical IC: max_cycles G1, then diagnostic continuation if needed.
    Saves campaign cycles, D1/D2, classification, conservation.
    """
    from motorsim.hybrid_fast import run_cycle
    from dev_orchestrator.p4_hybrid import checks
    model, mesh, pipe, state = _prepare('straight', dx_target)
    if mesh.n != N:
        # still log
        pass
    job_path = Path(job_dir)
    job_path.mkdir(parents=True, exist_ok=True)
    s = state
    c = pipe
    begin = 180.0
    rows = []
    checks_list = []
    walls = []
    works = []
    # For conservation tracking
    for i in range(max_cycles):
        row = run_cycle(mesh, c, s, begin + i*360, backend=backend, cfl=cfl)
        row['initial_cylinder_mass'] = s[6]
        cks = checks(row)
        rows.append(row)
        checks_list.append(cks)
        walls.append(row['cycle_wall_seconds'])
        works.append(row['work_indicated_J'])
        p = job_path / f"G1-cycle{i+1:02}.json.gz"
        p.write_bytes(gzip.compress(json.dumps(row).encode()))
        # update
        s = row['state']
        c = row['cells']
        # check conservation per row must pass, if fails mark regression
        # continue but record
    # compute D1/D2 for classification
    d1 = []
    d2 = []
    for i in range(1, len(rows)):
        try:
            m = _periodic_metrics(rows[i-1], rows[i])
        except Exception as e:
            m = dict(error=str(e))
        d1.append(m)
    for i in range(2, len(rows)):
        try:
            m = _periodic_metrics(rows[i-2], rows[i])
        except Exception as e:
            m = dict(error=str(e))
        d2.append(m)
    # vector lag2
    vec_lag2 = []
    for i in range(2, len(rows)):
        try:
            v = _vector_norm(rows[i-2], rows[i])
        except Exception as e:
            v = dict(error=str(e))
        vec_lag2.append(v)
    # classification per section 8
    # PERIOD1 requires 3 consecutive original passed
    # PERIOD2 diagnostic requires D1 FAIL and D2 3 consecutive passed
    def classify(d1_list, d2_list):
        # check last streaks? Actually need any 3 consecutive after cycle5
        # For our campaign with max_cycles=30, we check from cycle 6 onward (index 5)
        # Find if there exists 3 consecutive passed in D1 (lag1)
        # D1 list corresponds to cycles 2..max, index 0 is 2 vs1
        # Need comparison for cycles >=5: that is D1 index >=4 (since cycle6 vs5 -> i=5 -> d1 idx 4)
        # Simpler: look for streak of 3 passed in tail? Check all windows
        has_period1 = False
        period1_at = None
        for idx in range(len(d1_list)-2):
            # cycles are idx+2, idx+3, idx+4 -> need all >=5
            # need centered? Check that the last of the three is >=5
            # So first window that ends at cycle >=7? Actually need 3 comparisons consecutive starting after cycle5
            # Means cycles 6,7,8 correspond to d1 indices 4,5,6
            window = d1_list[idx:idx+3]
            if all(w.get('passed') for w in window):
                # check that idx+1 >=4 (so first of window corresponds to cycle >=6?)
                # The window's cycles are idx+2, idx+3, idx+4 (1-indexed for D1?)
                # For D1, comparison n vs n-1, n is idx+2 (since d1[0] is 2 vs1)
                # So window covers n = idx+2, idx+3, idx+4
                # Requirement: streak of 3 after cycle5 means n >=6 for all? Actually need 3 consecutive after cycle5: meaning last 3 comparisons all pass and n >=? At least the earliest in streak >=6?
                # We'll require idx >=4 (so first n >=6)
                if idx >=4:
                    has_period1 = True
                    period1_at = idx+4  # cycle number of last in streak
                    break
        has_period2_diag = False
        period2_at = None
        # D2 diagnostic: need D1 still FAIL (materially) and D2 3 consecutive passed
        # For D2, index 0 is 3 vs1, index 1 is 4 vs2 etc. So D2 n is idx+3
        # Need 3 consecutive D2 passed where corresponding D1 for those n is FAIL
        # Check window of 3 in D2
        for idx in range(len(d2_list)-2):
            window = d2_list[idx:idx+3]
            if all(w.get('passed') for w in window):
                # need D1 FAIL for those n? For each n in window, check D1 for same n
                # D1 for n corresponds to d1[n-2] (0-indexed)
                # D2 n = idx+3, idx+4, idx+5
                n_vals = [idx+3, idx+4, idx+5]
                d1_fails = True
                for n in n_vals:
                    # d1 index for n vs n-1 is n-2
                    d1_idx = n-2
                    if d1_idx <0 or d1_idx >= len(d1_list):
                        d1_fails=False
                        break
                    if d1_list[d1_idx].get('passed'):
                        d1_fails=False
                        break
                if d1_fails and idx+2 >=4:  # need tail after early cycles, at least first D2 n >=? Let's require n >=7 (so idx>=4)
                    # For D2 after cycle6? general require window ends at n>=8 maybe
                    if idx >=3:  # first D2 in window n>=6?
                        has_period2_diag = True
                        period2_at = n_vals[-1]
                        break
        # Determine general failure: if neither, check if D2 still decreasing but not crossing
        # We'll return flags
        return dict(has_period1=has_period1, period1_at=period1_at, has_period2_diag=has_period2_diag, period2_at=period2_at)

    classification = classify(d1, d2)
    # Also compute amplitudes for last pair if even count
    # For period-2, last two are A/B (odd/even). For period-1, last is steady.
    # Compute amplitudes per observable for last A/B pair
    amp = {}
    if len(rows)>=2:
        A = rows[-2]; B = rows[-1]
        WA = A['work_indicated_J']; WB = B['work_indicated_J']
        amp['work'] = dict(A=WA, B=WB, mean=(WA+WB)/2, amp=abs(WA-WB)/2)
        # cylinder pressure via metrics already: but we can also compute raw mean pressure? Use history curves? Use state? For now use p_cyl from history? Simpler use mean pressure from cells? But we will compute via periodic metrics amplitude? For amplitude we need |p difference|/2? But we have metrics relative, need absolute. We'll compute pipe integrals externally.
        # For pipe mass etc.
        import math
        for key, j in [('pipe_mass',0),('pipe_mom',1),('pipe_energy',2),('pipe_species',3)]:
            pa = fsum(c[j] for c in A['cells'])
            pb = fsum(c[j] for c in B['cells'])
            amp[key] = dict(A=pa, B=pb, mean=(pa+pb)/2, amp=abs(pa-pb)/2)
        for key, idx in [('port_mass',0),('port_energy',1),('port_species',2)]:
            pa = A['port_integral'][idx]
            pb = B['port_integral'][idx]
            amp[key] = dict(A=pa, B=pb, mean=(pa+pb)/2, amp=abs(pa-pb)/2)
        # cylinder state inventories: mass etc from state vector 9
        for name, k in [('I_mass',0),('K_mass',3),('C_mass',6)]:
            amp[name] = dict(A=A['state'][k], B=B['state'][k], mean=(A['state'][k]+B['state'][k])/2, amp=abs(A['state'][k]-B['state'][k])/2)
        # sensor pressures: need to compute mean pressure at sensor max location? We'll compute sensor max pressure amplitude via periodic metrics not needed here; but compute sensor p at phase 123.5 deg etc offline
    # conservation summary
    cons_pass = all(all(v for v in ck.values()) for ck in checks_list)
    # max residuals
    max_global = max(max(map(abs, r['global_balance'])) if r['global_balance'] else 0 for r in rows)
    # also per segment balances are inside checks, but we record global
    result = dict(
        job_id=job_id, worker_id=worker_id, N=N, dx_target=dx_target, mesh_n=mesh.n, max_cycles=max_cycles,
        works=works, walls=walls, total_wall=sum(walls), avg_wall=sum(walls)/len(walls) if walls else 0,
        d1=d1, d2=d2, vec_lag2=vec_lag2, classification=classification, amp=amp,
        conservation_pass=cons_pass, max_global_balance=max_global,
        checks=checks_list,
    )
    # write campaign summary
    (job_path / "campaign_result.json").write_text(json.dumps(result, indent=2, default=str))
    return result
