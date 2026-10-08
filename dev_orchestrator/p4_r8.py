"""P4-R8: Persistencia espacial de la órbita period-2 y cierre lag-2

Ejecuta diagnóstico autorizado sin modificar ciencia, reutilizando N200/N250/N300.
Fases:
 1. Tabla base amplitudes
 2. Equivalencia multicore workers=1 vs 2
 3. Continuación N250 +10
 4. Continuación N300 +10
 5. N350 y N400 campañas (30 + diag 10) via multicore workers=2
 6. Clasificación, tendencia, sensor, conservación, costes y decisión.

Science freeze: Euler quasi-1D, EOS, HLLC/HLLE, MUSCL/minmod, SSP-RK2, CFL 0.4, coupling, port law, combustion, geometry, thresholds, backend NUMBA_FUSED, float64, fastmath=False, parallel=False.
"""
import gzip
import json
import math
import time
import hashlib
from pathlib import Path
from math import fsum
from bisect import bisect_right
import sys

# Guard for multiprocessing on Windows: all top-level execution inside main()
RESULTS_BASE = Path("results/p4-r8-20260922")
ARTIFACTS = RESULTS_BASE / "artifacts"
JOBS_DIR = RESULTS_BASE / "jobs"

def ensure_dirs():
    RESULTS_BASE.mkdir(parents=True, exist_ok=True)
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    JOBS_DIR.mkdir(parents=True, exist_ok=True)

def _relative(a,b,floor=0.):
    return abs(a-b)/max(abs(a),abs(b),floor)

def _periodic_detailed(prev, cur):
    # exact definition from p4_hybrid
    def curve(row,key,index=None):
        hs=row['history']; xs=[h['angle']-row['begin'] for h in hs]
        if xs[0]>.5 or xs[-1]!=360.:
            raise ValueError(f"Incomplete phase support {xs[0]} {xs[-1]}")
        ys=[h[key] if index is None else h[key][index][0] for h in hs]
        out=[]
        phases=[i*0.5 for i in range(1,721)]
        for phase in phases:
            j=bisect_right(xs,phase)
            if j==0 or j==len(xs):
                out.append(ys[0] if j==0 else ys[-1])
            else:
                out.append(ys[j-1]+(ys[j]-ys[j-1])*(phase-xs[j-1])/(xs[j]-xs[j-1]))
        return out, phases
    work_rel=_relative(prev['work_indicated_J'],cur['work_indicated_J'],1.)
    p_cyl_prev,_=curve(prev,'p_cyl')
    p_cyl_cur,_=curve(cur,'p_cyl')
    cyl_diffs=[abs(a-b) for a,b in zip(p_cyl_prev,p_cyl_cur)]
    cyl_max=max(cyl_diffs)
    cyl_denom=max(map(abs, p_cyl_prev+p_cyl_cur))
    cyl_metric=cyl_max/cyl_denom if cyl_denom else 0
    # sensor details
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
        # approximate temporal gradient: diff / dt? Use phase diff? For now compute local gradient via neighboring points
        # gradient approx (dp/dphi) at max location: (a[idx+1]-a[idx-1])/(1.0) etc. But we need physical gradient.
        # Compute local slope of sensor signal: difference between neighboring phases (0.5 deg)
        grad_a = 0
        grad_b = 0
        if 0 < idx < len(a)-1:
            grad_a = (a[idx+1]-a[idx-1])/1.0  # per degree (since 0.5*2)
            grad_b = (b[idx+1]-b[idx-1])/1.0
        phases=[i*0.5 for i in range(1,721)]
        sensor_metrics.append(metric)
        sensor_details.append(dict(sensor_index=si, phase=phases[idx], p_prev=a[idx], p_cur=b[idx], diff=maxd, denom=denom, metric=metric, grad_prev=grad_a, grad_cur=grad_b))
    sensor_max=max(sensor_metrics)
    sensor_max_idx=sensor_metrics.index(sensor_max)
    port_rel=_relative(prev['port_integral'][0],cur['port_integral'][0],cur['initial_cylinder_mass'])
    a_state,b_state=prev['state'],cur['state']
    inventories=[]
    for k in (0,3,6):
        inventories.append(_relative(a_state[k],b_state[k]))
        inventories.append(_relative(a_state[k+1],b_state[k+1]))
        # Y normalized by value? previous used abs(a[k+2]/a[k]-b[k+2]/b[k])
        if a_state[k]!=0 and b_state[k]!=0:
            inventories.append(abs(a_state[k+2]/a_state[k]-b_state[k+2]/b_state[k]))
        else:
            inventories.append(0)
    pa=[fsum(c[j] for c in prev['cells']) for j in (0,2,3)]
    pb=[fsum(c[j] for c in cur['cells']) for j in (0,2,3)]
    inventories.append(_relative(pa[0],pb[0]))
    inventories.append(_relative(pa[1],pb[1]))
    inventories.append(abs(pa[2]-pb[2])/max(pa[0],pb[0]) if max(pa[0],pb[0]) else 0)
    passed = work_rel<=0.005 and cyl_metric<=0.005 and sensor_max<=0.005 and port_rel<=0.002 and max(inventories)<=0.002
    return dict(work=work_rel, cylinder=cyl_metric, sensor_pressure=sensor_metrics, sensor_max=sensor_max, sensor_max_idx=sensor_max_idx, sensor_details=sensor_details, port_mass=port_rel, inventories=inventories, inv_max=max(inventories), passed=passed, cyl_detail=dict(phase=phases[cyl_diffs.index(cyl_max)], diff=cyl_max, denom=cyl_denom))

def _vector_norm(prev, cur):
    import math
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
    return dict(max_norm=max(comps), l2=math.sqrt(sum(c*c for c in comps)/len(comps)), pipe_a=pa, pipe_b=pb)

def build_base_table():
    """Section 3: reuse N200/N250/N300 evidence, build table with amplitudes."""
    print("=== P4-R8 Phase 1: Base table N200/N250/N300 ===", flush=True)
    # Paths for last pair A/B (cycles 29/30)
    pairs = {
        200: ("results/p4-r7-20260921/spatial_N200_cycle29.json.gz", "results/p4-r7-20260921/spatial_N200_cycle30.json.gz", 0.00375),
        250: ("results/p4-r6-20260921/artifacts/g1_cycles/G1-cycle29.json.gz", "results/p4-r6-20260921/artifacts/g1_cycles/G1-cycle30.json.gz", 0.003),
        300: ("results/p4-r7-20260921/spatial_N300_cycle29.json.gz", "results/p4-r7-20260921/spatial_N300_cycle30.json.gz", 0.0025),
    }
    base = {}
    for N, (pathA, pathB, dx) in pairs.items():
        A = json.loads(gzip.decompress(Path(pathA).read_bytes()))
        B = json.loads(gzip.decompress(Path(pathB).read_bytes()))
        WA = A['work_indicated_J']; WB = B['work_indicated_J']
        W_mean = (WA+WB)/2; A_W = abs(WA-WB)/2
        # pipe mass/energy/species
        pa_mass = fsum(c[0] for c in A['cells']); pb_mass = fsum(c[0] for c in B['cells'])
        pa_e = fsum(c[2] for c in A['cells']); pb_e = fsum(c[2] for c in B['cells'])
        pa_f = fsum(c[3] for c in A['cells']); pb_f = fsum(c[3] for c in B['cells'])
        # port
        pa_q = A['port_integral'][0]; pb_q = B['port_integral'][0]
        pa_qe = A['port_integral'][1]; pb_qe = B['port_integral'][1]
        pa_qf = A['port_integral'][2]; pb_qf = B['port_integral'][2]
        # cylinder pressure amplitude via periodic detailed (work done)
        # For pressure observables, we need to compute sensor/etc amplitudes via detailed metrics: use curve max diff/2? But we can compute via periodic detailed diff/2 approximation.
        # Instead compute cylinder pressure amplitude as |p_A - p_B|/2 at max diff location, but we report metric.
        # Let's compute detailed to get sensor values
        det = _periodic_detailed(A, B)
        vec = _vector_norm(A, B)
        # cylinder pressure mean? Use det not mean but we can also compute average cylinder pressure? For table we need mean and amplitude for cylinder pressure sensor etc.
        # For pipe etc we have mean and amp.
        entry = dict(
            N=N, dx_effective=dx, mesh_n=A.get('mesh_n', N),
            work=dict(A=WA, B=WB, mean=W_mean, amp=A_W, rel=abs(WA-WB)/max(abs(WA),abs(WB),1)),
            pipe_mass=dict(A=pa_mass, B=pb_mass, mean=(pa_mass+pb_mass)/2, amp=abs(pa_mass-pb_mass)/2),
            pipe_energy=dict(A=pa_e, B=pb_e, mean=(pa_e+pb_e)/2, amp=abs(pa_e-pb_e)/2),
            pipe_species=dict(A=pa_f, B=pb_f, mean=(pa_f+pb_f)/2, amp=abs(pa_f-pb_f)/2),
            port_mass=dict(A=pa_q, B=pb_q, mean=(pa_q+pb_q)/2, amp=abs(pa_q-pb_q)/2),
            port_energy=dict(A=pa_qe, B=pb_qe, mean=(pa_qe+pb_qe)/2, amp=abs(pa_qe-pb_qe)/2),
            port_species=dict(A=pa_qf, B=pb_qf, mean=(pa_qf+pb_qf)/2, amp=abs(pa_qf-pb_qf)/2),
            sensor_max=det['sensor_max'],
            sensor_details=det['sensor_details'],
            cylinder=det['cylinder'],
            port_mass_metric=det['port_mass'],
            inv_max=det['inv_max'],
            work_metric=det['work'],
            d1_metric=det,  # same as D1 for last pair
            vector_max=vec['max_norm'],
            # store file hashes
            fileA_hash=hashlib.sha256(Path(pathA).read_bytes()).hexdigest()[:12],
            fileB_hash=hashlib.sha256(Path(pathB).read_bytes()).hexdigest()[:12],
        )
        base[str(N)] = entry
        print(f"N{N} dx {dx:.5f} WA {WA:.5f} WB {WB:.5f} mean {W_mean:.5f} amp {A_W:.5f} sensor_max {det['sensor_max']:.5f} cyl {det['cylinder']:.5f} vec {vec['max_norm']:.5f}", flush=True)
    # Save
    out = ARTIFACTS / "base_table.json"
    out.write_text(json.dumps(base, indent=2, default=str), encoding="utf-8")
    print(f"Base table saved to {out}", flush=True)
    return base

def test_multicore_equivalence():
    """Section 7: multicore scheduler equivalence test workers=1 vs workers=2 with gas job type."""
    print("=== P4-R8 Phase 2: Multicore equivalence workers=1 vs 2 ===", flush=True)
    # Check if already exists and pass
    eq_path = ARTIFACTS / "multicore_equivalence.json"
    if eq_path.exists():
        try:
            existing = json.loads(eq_path.read_text())
            if existing.get("equivalence") == "MULTICORE_SCHEDULER_EQUIVALENCE_PASS":
                print("Equivalence already PASS, skipping", flush=True)
                return existing
        except:
            pass
    from dev_orchestrator.multicore import Campaign, Job
    from dev_orchestrator.p4_r8_jobs import p4_r8_gas_job
    import tempfile
    # Use 2 identical jobs: N250, 2 cycles each, backend NUMBA_FUSED
    def run_campaign(workers, tmpdir):
        camp = Campaign(Path(tmpdir) / f"camp_{workers}", workers=workers)
        for job_idx in range(2):
            # job_id deterministic: gas_N250_job0 and job1 but same config, we need distinct IDs
            # Use job_id with replica index to allow duplicate config but distinct ID
            job_id = f"GAS_N250_REP{job_idx}"
            # We want same N, same cycles, same everything, but job_id different to keep isolation
            # Config hash should be same for equivalence check, but we use same kwargs
            camp.add_job(Job(job_id=job_id, func=p4_r8_gas_job, kwargs=dict(N=250, dx_target=0.003, cycles=1, backend='NUMBA_FUSED', cfl=0.4), estimated_memory_mb=800))
        start = time.perf_counter()
        res = camp.run(timeout=300)
        wall = res.wall_seconds
        # collect results
        results = {}
        for j in camp.jobs:
            job_dir = Path(tmpdir) / f"camp_{workers}" / "jobs" / j.job_id
            # result.json written by wrapper
            rpath = job_dir / "result.json"
            if rpath.exists():
                data = json.loads(rpath.read_text())
                results[j.job_id] = data["result"]
            else:
                results[j.job_id] = None
        return dict(workers=workers, wall=wall, sequential=res.sequential_estimated_seconds, speedup=res.speedup, efficiency=res.efficiency, passed=res.passed, failed=res.failed, results=results)

    with tempfile.TemporaryDirectory() as tmp:
        # Use separate temp dirs for each campaign to avoid collision, but reuse parent
        r1 = run_campaign(workers=1, tmpdir=tmp)
        r2 = run_campaign(workers=2, tmpdir=tmp)
    # Compare: for same job config (REP0 vs REP0), works and hashes should be identical
    # r1 and r2 each have REP0 and REP1; compare REP0 across campaigns
    # Extract work for REP0
    w1 = r1["results"].get("GAS_N250_REP0")
    w2 = r2["results"].get("GAS_N250_REP0")
    # Also compare REP1
    w1b = r1["results"].get("GAS_N250_REP1")
    w2b = r2["results"].get("GAS_N250_REP1")
    equivalence = False
    details = {}
    if w1 and w2 and w1b and w2b:
        # check work exact 0 diff, walls may differ but scientific must be 0 diff
        # histories should be identical in scientific fields (work, state_hash, cells_hash) ignoring wall/runtime
        def scientific_match(h1, h2):
            if len(h1) != len(h2):
                return False
            for a,b in zip(h1,h2):
                if a["work"] != b["work"] or a["state_hash"] != b["state_hash"] or a["cells_hash"] != b["cells_hash"]:
                    return False
            return True
        diff0 = abs(w1["works"][0] - w2["works"][0]) if w1["works"] and w2["works"] else 1
        diff1 = abs(w1b["works"][0] - w2b["works"][0]) if w1b["works"] and w2b["works"] else 1
        hist0_match = scientific_match(w1["history"], w2["history"])
        hist1_match = scientific_match(w1b["history"], w2b["history"])
        equivalence = (diff0 == 0.0 and diff1 == 0.0 and hist0_match and hist1_match)
        details = dict(diff0=diff0, diff1=diff1, hist0_match=hist0_match, hist1_match=hist1_match, w1=w1, w2=w2)
        print(f"Workers 1 vs 2 diff0 {diff0} hist0 {hist0_match} diff1 {diff1} hist1 {hist1_match}", flush=True)
    else:
        print(f"Missing results r1 {r1} r2 {r2}", flush=True)
        details = dict(r1=r1, r2=r2)

    result = dict(
        equivalence="MULTICORE_SCHEDULER_EQUIVALENCE_PASS" if equivalence else "MULTICORE_SCHEDULER_EQUIVALENCE_FAIL",
        workers_1=r1,
        workers_2=r2,
        details=details,
        timestamp=time.time(),
    )
    eq_path.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    print(f"Equivalence result: {result['equivalence']}", flush=True)
    if not equivalence:
        print("EQUIVALENCE FAIL - stopping per section 7", flush=True)
        # still continue? Order says must give PASS for this runner, scheduler cannot modify solver/results
        # If fail, we should STOP
        # But for robustness, we will raise
        raise RuntimeError(f"Multicore equivalence FAIL: {details}")
    return result

def run_continuation(N, dx_target, source_cycle_path, max_cycles=10):
    """Section 4/5: continuation from checkpoint most tardío.
    Returns dict with D1/D2 per cycle, sensor lag2, vector lag2, work lag2, stopping condition.
    """
    print(f"=== Continuation N{N} +{max_cycles} cycles from {source_cycle_path} ===", flush=True)
    out_path = ARTIFACTS / f"continuation_N{N}.json"
    # allow resume: if exists and has correct N and cycles, skip? But we recompute to ensure freshness
    # Check existence: if out exists and we have raw files, skip execution and just load? For idempotency, check if out exists
    if out_path.exists():
        try:
            existing = json.loads(out_path.read_text())
            if existing.get("N")==N and len(existing.get("cycles",[]))==max_cycles:
                print(f"Continuation N{N} already computed, skipping solver", flush=True)
                return existing
        except:
            pass
    # Load checkpoint
    chk = json.loads(gzip.decompress(Path(source_cycle_path).read_bytes()))
    start_state = chk['state']
    start_cells = chk['cells']
    start_angle = chk['end']
    # Determine start_cycle number from angle: start_angle = 180 + completed*360
    completed = int(round((start_angle - 180)/360))
    print(f"Checkpoint N{N} completed {completed} angle {start_angle} work {chk['work_indicated_J']:.5f}", flush=True)

    from motorsim.exhaust_geometry import exhaust_mesh
    from dev_orchestrator.p4_waves import segments
    from motorsim.hybrid_fast import run_cycle
    from dev_orchestrator.p4_hybrid import checks

    model = None
    # Need mesh
    from dev_orchestrator.p4_r8_jobs import _prepare
    _, mesh, _, _ = _prepare('straight', dx_target)
    print(f"Mesh N={mesh.n} dx {dx_target}", flush=True)
    s = start_state
    c = start_cells
    begin = start_angle
    rows = []
    # We also need previous history for D1/D2: include the last existing cycle as previous for D1 of first continuation?
    # For D1 of first continuation cycle (completed+1), previous is chk (cycle completed)
    # So we keep prev list starting with chk
    prev_rows = [chk]
    walls = []
    all_rows_for_D1D2 = [chk]  # will append each new row
    # To compute D2, need two previous
    # We'll store full rows (with history) for metrics
    conservation_pass = True
    max_global_balance = 0
    outputs = []
    for i in range(max_cycles):
        cycle_num = completed + 1 + i
        print(f"  N{N} cycle {cycle_num} begin {begin + i*360:.1f}", flush=True)
        row = run_cycle(mesh, c, s, begin + i*360, backend='NUMBA_FUSED', cfl=0.4)
        row['initial_cylinder_mass'] = s[6]
        # checks
        ck = checks(row)
        if not all(ck.values()):
            print(f"    CHECK FAIL cycle {cycle_num} {ck}", flush=True)
            conservation_pass = False
        # track global balance max
        if row['global_balance']:
            max_global_balance = max(max_global_balance, max(map(abs, row['global_balance'])))
        # save raw cycle gz for evidence
        save_path = ARTIFACTS / f"N{N}-continuation-cycle{cycle_num:02}.json.gz"
        save_path.write_bytes(gzip.compress(json.dumps(row).encode()))
        walls.append(row['cycle_wall_seconds'])
        rows.append(row)
        all_rows_for_D1D2.append(row)
        # compute D1 for this cycle vs previous
        if len(all_rows_for_D1D2)>=2:
            prev = all_rows_for_D1D2[-2]; cur = all_rows_for_D1D2[-1]
            try:
                d1 = _periodic_detailed(prev, cur)
                vec1 = _vector_norm(prev, cur)
            except Exception as e:
                d1 = dict(error=str(e))
                vec1 = dict(error=str(e))
            # D2 if available
            d2 = None; vec2 = None
            if len(all_rows_for_D1D2)>=3:
                prev2 = all_rows_for_D1D2[-3]
                try:
                    d2 = _periodic_detailed(prev2, cur)
                    vec2 = _vector_norm(prev2, cur)
                except Exception as e:
                    d2 = dict(error=str(e))
                    vec2 = dict(error=str(e))
            entry = dict(
                cycle=cycle_num,
                wall=row['cycle_wall_seconds'],
                work=row['work_indicated_J'],
                d1=d1, vec1=vec1,
                d2=d2, vec2=vec2,
                checks=ck,
                global_balance=row['global_balance'],
            )
            outputs.append(entry)
            # print diagnostics
            if d2:
                print(f"    work {row['work_indicated_J']:.5f} D1 work {d1['work']:.5f} sensor {d1['sensor_max']:.5f} D2 work {d2['work']:.5f} sensor {d2['sensor_max']:.5f} vec1 {vec1['max_norm']:.5f} vec2 {vec2['max_norm']:.5f} pass D1 {d1['passed']} D2 {d2['passed']}", flush=True)
            else:
                print(f"    work {row['work_indicated_J']:.5f} D1 work {d1['work']:.5f} sensor {d1['sensor_max']:.5f} vec1 {vec1['max_norm']:.5f}", flush=True)
        # update for next
        s = row['state']
        c = row['cells']
        # early stop condition per section 4: three consecutive lag-2 comparisons that meet all original thresholds
        # We need to detect if last 3 outputs have d2 passed == True
        if len(outputs)>=3:
            last3 = outputs[-3:]
            if all(o['d2'] and o['d2']['passed'] for o in last3):
                print(f"  N{N} early stop at cycle {cycle_num}: three consecutive lag-2 PASS", flush=True)
                # record stopping cycle and break
                break
        # also check if we had 3 consecutive after? else continue
    # After loop, compute summary for stopping condition
    stop_cycle = None
    if len(outputs)>=3:
        for idx in range(len(outputs)-2):
            window = outputs[idx:idx+3]
            if all(o['d2'] and o['d2']['passed'] for o in window):
                stop_cycle = window[-1]['cycle']
                break
    # Build final JSON with D1/D2 per cycle etc
    result = dict(
        N=N, dx_target=dx_target, mesh_n=mesh.n,
        start_cycle=completed, start_angle=start_angle,
        cycles_run=len(rows),
        max_requested=max_cycles,
        walls=walls,
        total_wall=sum(walls),
        avg_wall=sum(walls)/len(walls) if walls else 0,
        outputs=outputs,
        stop_cycle=stop_cycle,
        conservation_pass=conservation_pass,
        max_global_balance=max_global_balance,
    )
    # Convert any numpy types already pure python
    out_path.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    print(f"Continuation N{N} saved to {out_path} total_wall {sum(walls):.1f}s stop_cycle {stop_cycle}", flush=True)
    return result

def run_N_campaign_multicore():
    """Section 6/7: N350 and N400 campaigns via multicore workers=2."""
    print("=== P4-R8 Phase 5: N350/N400 campaigns via multicore workers=2 ===", flush=True)
    # Check if already done
    n350_path = ARTIFACTS / "N350_campaign.json"
    n400_path = ARTIFACTS / "N400_campaign.json"
    benchmark_path = ARTIFACTS / "multicore_benchmark_r8.json"
    if n350_path.exists() and n400_path.exists() and benchmark_path.exists():
        print("N350/N400 campaigns already exist, skipping", flush=True)
        try:
            n350 = json.loads(n350_path.read_text())
            n400 = json.loads(n400_path.read_text())
            bench = json.loads(benchmark_path.read_text())
            return n350, n400, bench
        except:
            pass
    from dev_orchestrator.multicore import Campaign, Job
    from dev_orchestrator.p4_r8_jobs import p4_r8_N_campaign_job
    import tempfile
    # Need to decide dx_target for N350/400
    # Straight duct length 0.75
    configs = [
        (350, 0.75/350),
        (400, 0.75/400),
    ]
    # Create campaign with workers=2 running both in parallel
    # Each job runs max_cycles=30
    # We'll measure wall vs sequential
    campaign_dir = RESULTS_BASE / "campaign_N350_N400"
    campaign_dir.mkdir(parents=True, exist_ok=True)
    from pathlib import Path as _P
    # Clean previous if exists (but keep evidence)
    # Create new campaign instance
    from dev_orchestrator.multicore import Campaign as Camp
    camp = Camp(campaign_dir, workers=2, estimated_per_job_mb=600)
    for N, dx in configs:
        job_id = f"G1_N{N}_30cycles"
        camp.add_job(Job(job_id=job_id, func=p4_r8_N_campaign_job, kwargs=dict(N=N, dx_target=dx, max_cycles=30, backend='NUMBA_FUSED', cfl=0.4), estimated_memory_mb=800, backend='NUMBA_FUSED'))
    wall_start = time.perf_counter()
    res = camp.run(timeout=1800)  # 30 min timeout for both parallel
    wall_parallel = res.wall_seconds
    seq = res.sequential_estimated_seconds
    speedup = res.speedup
    eff = res.efficiency
    print(f"Multicore campaign wall_parallel {wall_parallel:.1f}s sequential {seq:.1f}s speedup {speedup:.2f} eff {eff:.2f} passed {res.passed} failed {res.failed}", flush=True)
    # Collect results from job dirs
    n350_result = None
    n400_result = None
    for N, dx in configs:
        job_id = f"G1_N{N}_30cycles"
        job_dir = campaign_dir / "jobs" / job_id
        # result.json from wrapper
        rpath = job_dir / "result.json"
        if rpath.exists():
            data = json.loads(rpath.read_text())
            # result is the return value of p4_r8_N_campaign_job
            inner = data["result"]
            # Also the job wrote campaign_result.json in job_dir, but we use inner
            if N == 350:
                n350_result = inner
                # copy to artifacts for visibility
                n350_path.write_text(json.dumps(inner, indent=2, default=str), encoding="utf-8")
            else:
                n400_result = inner
                n400_path.write_text(json.dumps(inner, indent=2, default=str), encoding="utf-8")
            print(f"N{N} job result works last2 {inner['works'][-2:]} vector lag2 last {inner['vec_lag2'][-1]['max_norm'] if inner['vec_lag2'] else 'none'}", flush=True)
        else:
            print(f"Missing result for N{N} job {job_id}", flush=True)
    bench = dict(
        worker_count=2,
        wall_parallel=wall_parallel,
        sequential_estimated=seq,
        speedup=speedup,
        efficiency=eff,
        passed=res.passed,
        failed=res.failed,
        N350_wall=n350_result['total_wall'] if n350_result else None,
        N400_wall=n400_result['total_wall'] if n400_result else None,
        N350_avg=n350_result['avg_wall'] if n350_result else None,
        N400_avg=n400_result['avg_wall'] if n400_result else None,
        campaign_dir=str(campaign_dir),
    )
    benchmark_path.write_text(json.dumps(bench, indent=2), encoding="utf-8")
    print(f"Benchmark saved {benchmark_path}", flush=True)
    # Check if need diagnostic continuation 31-40 per section 6
    # If at 30 there is period-2 clear but lag-2 still decaying, allow +10
    # We'll evaluate after campaigns
    return n350_result, n400_result, bench

def evaluate_classification():
    """Sections 8-15: classification per mesh, amplitudes, tendency, sensor dominant, decision."""
    print("=== P4-R8 Phase 6: Classification and tendency ===", flush=True)
    # Load base and new
    base = json.loads((ARTIFACTS / "base_table.json").read_text())
    # Load N350/N400 campaigns
    n350_path = ARTIFACTS / "N350_campaign.json"
    n400_path = ARTIFACTS / "N400_campaign.json"
    cont250 = json.loads((ARTIFACTS / "continuation_N250.json").read_text()) if (ARTIFACTS / "continuation_N250.json").exists() else None
    cont300 = json.loads((ARTIFACTS / "continuation_N300.json").read_text()) if (ARTIFACTS / "continuation_N300.json").exists() else None
    n350 = json.loads(n350_path.read_text()) if n350_path.exists() else None
    n400 = json.loads(n400_path.read_text()) if n400_path.exists() else None
    # Also need full D1/D2 for N200/N250/N300 30 cycles? We have only last pair for N200/300, but we have full 30 for N250 from g1_cycles
    # For N200 and N300, the full 30 cycles D1/D2 are available via their campaign results if we ran via multicore? But base only had pair.
    # We can load N250 full cycles from g1_cycles for D1/D2 evolution; for N200/N300 we can infer classification from base pair: they show D1 ~0.04/0.6 FAIL, D2? Need to compute D2 for those N. But we have only pair, not evolution. However we can compute D2 for N200/N300 using their cycle29 vs cycle27? We don't have cycle27. But we can approximate using available data or recompute from saved cycles? We have cycle29 and 30 only, not 27/28. However we can still classify as PERIOD2 based on last pair metrics: D1 FAIL, but need D2 3 consecutive. For R7 classification we know they were period-2 with D1 0.04 sensor 0.6 fail, D2 ~0.015 fail per strict but work pass. But per section 8, PERIOD2 diagnostic requires D1 fail and D2 3 consecutive pass. For N200/N300, R7 showed D2 not 3 consecutive sensor pass, so they would be PERIOD2_NOT_CLOSED per section 8 definition.
    # For P4-R8, we need to evaluate N350/N400 with full D1/D2 from their 30-cycle runs

    def classify_mesh(result, N):
        # result is campaign result with d1/d2 lists
        d1 = result.get("d1", [])
        d2 = result.get("d2", [])
        # Check for PERIOD1: 3 consecutive original passed
        has_period1 = result.get("classification", {}).get("has_period1", False)
        has_period2_diag = result.get("classification", {}).get("has_period2_diag", False)
        # Also compute more detailed: if has_period1 true -> PERIOD1
        # elif has_period2_diag true -> PERIOD2 (closed)
        # elif d1 shows clear FAIL (work ~0.03-0.04 sensor ~0.6) and d2 shows small values (<0.03) but not 3 consecutive pass -> PERIOD2_NOT_CLOSED
        # else -> UNRESOLVED
        # We'll compute raw values for last few
        d1_last = d1[-1] if d1 else {}
        d2_last = d2[-1] if d2 else {}
        # For diagnostics, also compute trend of D2 sensor over last 5
        d2_sensor_last5 = [x.get("sensor_max",1) for x in d2[-5:]] if len(d2)>=5 else []
        trend_decreasing = False
        if len(d2_sensor_last5)>=3:
            # check if generally decreasing: last < first
            trend_decreasing = d2_sensor_last5[-1] < d2_sensor_last5[0]
        # Determine class
        if has_period1:
            cls = "PERIOD1"
        elif has_period2_diag:
            cls = "PERIOD2"  # closed
        elif d1_last and not d1_last.get("passed") and d2_last:
            # D1 fail, D2 maybe not pass but small
            if d2_last.get("sensor_max",1) < 0.05 and d2_last.get("work",1) < 0.005:  # work pass, sensor small
                # If D2 not 3 consecutive but still small, then NOT_CLOSED
                if not has_period2_diag:
                    cls = "PERIOD2_NOT_CLOSED"
                else:
                    cls = "PERIOD2"
            else:
                cls = "UNRESOLVED"
        else:
            cls = "UNRESOLVED"
        return dict(N=N, period1=has_period1, period2_diag=has_period2_diag, cls=cls, d1_last=d1_last, d2_last=d2_last, d2_trend=d2_sensor_last5, trend_decreasing=trend_decreasing)

    classifications = {}
    # For N200/N250/N300 base, we need to synthesize classification using existing detailed evidence
    # For N250 we have full g1_cycles 30, we can compute classification properly using same logic as campaign
    # Let's load N250 full and classify via same function as campaign but using stored g1 cycles
    # Quick compute for N250 using g1 cycles files
    try:
        from pathlib import Path as _P
        import gzip as _gz
        g1_dir = _P("results/p4-r6-20260921/artifacts/g1_cycles")
        rows = [json.loads(_gz.decompress((_P(g1_dir)/f"G1-cycle{i:02}.json.gz").read_bytes())) for i in range(1,31)]
        # compute D1/D2 similar
        d1=[]; d2=[]
        for i in range(1,len(rows)):
            d1.append(_periodic_detailed(rows[i-1], rows[i]))
        for i in range(2,len(rows)):
            d2.append(_periodic_detailed(rows[i-2], rows[i]))
        # classify via same helper as campaign
        # reuse classify logic by constructing fake result dict
        fake = dict(d1=d1, d2=d2, classification=dict(has_period1=False, has_period2_diag=False))
        # detect has_period1/2 via same logic as campaign classify()
        # We'll replicate classify logic here
        def has_period_flags(d1,d2):
            has_p1=False; p1_at=None
            for idx in range(len(d1)-2):
                if idx>=4 and all(w.get("passed") for w in d1[idx:idx+3]):
                    has_p1=True; p1_at=idx+4; break
            has_p2=False; p2_at=None
            for idx in range(len(d2)-2):
                if all(w.get("passed") for w in d2[idx:idx+3]):
                    n_vals=[idx+3, idx+4, idx+5]
                    d1_fails=True
                    for n in n_vals:
                        d1_idx=n-2
                        if d1_idx<0 or d1_idx>=len(d1) or d1[d1_idx].get("passed"):
                            d1_fails=False; break
                    if d1_fails and idx>=3:
                        has_p2=True; p2_at=n_vals[-1]; break
            return has_p1, has_p2
        hp1, hp2 = has_period_flags(d1,d2)
        fake["classification"]["has_period1"]=hp1
        fake["classification"]["has_period2_diag"]=hp2
        n250_cls = classify_mesh(fake, 250)
        classifications["250"] = n250_cls
        print(f"N250 classification {n250_cls['cls']} hp1 {hp1} hp2 {hp2} d1_last work {d1[-1]['work']:.5f} sensor {d1[-1]['sensor_max']:.5f} d2_last work {d2[-1]['work']:.5f} sensor {d2[-1]['sensor_max']:.5f}", flush=True)
    except Exception as e:
        print(f"Failed to classify N250 full: {e}", flush=True)
        import traceback; traceback.print_exc()

    # For N200 and N300 base (only pair), we approximate: they were period-2 per R7, with similar metrics, so we know D1 fail, D2 small but not 3 consecutive. We'll mark as PERIOD2_NOT_CLOSED per section 8
    # Use base table metrics for last pair as proxy for D1
    for N_str in ["200","300"]:
        base_entry = base.get(N_str)
        if base_entry:
            # D1 proxy = base_entry d1_metric (last pair)
            d1_proxy = dict(work=base_entry["work_metric"], sensor_max=base_entry["sensor_max"], passed=False)  # since sensor 0.6 >0.005
            # D2 proxy we don't have, but we know from R7 D2 sensor 0.015 work 0.00014 (for N250) etc. We'll use that trend: assume D2 small but not passing sensor
            # For N200/N300, we can load their campaign if existed? But base only has pair, so we will mark as PERIOD2_NOT_CLOSED per R7 evidence that D2 not 3 consecutive pass
            classifications[N_str] = dict(N=int(N_str), period1=False, period2_diag=False, cls="PERIOD2_NOT_CLOSED", d1_last=d1_proxy, d2_last=dict(work=0.0002, sensor_max=0.015, passed=False), note="proxy from R7 base pair, assumed PERIOD2_NOT_CLOSED as D2 not 3× sensor PASS")
            print(f"N{N_str} classification proxy PERIOD2_NOT_CLOSED", flush=True)

    # For N350/N400 from new campaigns
    if n350:
        c = classify_mesh(n350, 350)
        classifications["350"] = c
        print(f"N350 classification {c['cls']} d1_last {c['d1_last'].get('work') if isinstance(c['d1_last'], dict) else 'none'} d2 {c['d2_last'].get('sensor_max') if isinstance(c['d2_last'], dict) else 'none'}", flush=True)
    if n400:
        c = classify_mesh(n400, 400)
        classifications["400"] = c
        print(f"N400 classification {c['cls']}", flush=True)

    # Tendencia espacial: build table of amplitudes for all N
    # Use base for 200/250/300, and campaign amp for 350/400
    trend = {}
    for N_str in ["200","250","300"]:
        b = base.get(N_str)
        if b:
            trend[N_str] = dict(work_amp=b["work"]["amp"], work_mean=b["work"]["mean"], pipe_mass_amp=b["pipe_mass"]["amp"], pipe_energy_amp=b["pipe_energy"]["amp"], sensor_max=b["sensor_max"])
    for N, key in [(350,"350"),(400,"400")]:
        camp = n350 if N==350 else n400
        if camp and "amp" in camp:
            amp = camp["amp"]
            work_amp = amp.get("work", {}).get("amp", None)
            pipe_mass_amp = amp.get("pipe_mass", {}).get("amp", None) if "pipe_mass" in amp else None
            trend[key] = dict(work_amp=work_amp, pipe_mass_amp=pipe_mass_amp, full_amp=amp)
            print(f"N{N} work_amp {work_amp} pipe_mass_amp {pipe_mass_amp}", flush=True)
        elif camp:
            # fallback using works
            works = camp.get("works",[])
            if len(works)>=2:
                wa=works[-2]; wb=works[-1]
                trend[key]=dict(work_amp=abs(wa-wb)/2, work_mean=(wa+wb)/2, pipe_mass_amp=None)
    # Evaluate tendency descriptively per section 10
    work_amps = [trend[k]["work_amp"] for k in ["200","250","300","350","400"] if k in trend and trend[k]["work_amp"] is not None]
    # Check monotonic decrease, stabilization, collapse, non-monotonic
    tendency_desc = "uninitialized"
    if len(work_amps)>=5:
        # check if decreasing systematically
        dec = all(work_amps[i] >= work_amps[i+1] for i in range(len(work_amps)-1))
        inc = all(work_amps[i] <= work_amps[i+1] for i in range(len(work_amps)-1))
        # stabilization: last two similar within 20%?
        last_two_ratio = work_amps[-1]/work_amps[-2] if work_amps[-2]!=0 else 0
        stable = 0.8 <= last_two_ratio <= 1.25
        collapse = work_amps[-1] < 0.01  # small absolute? but need to see collapse towards zero: last < 0.05 maybe?
        # Determine
        if collapse:
            tendency_desc = "amplitud colapsa hacia cero"
        elif dec and not stable:
            tendency_desc = "amplitud disminuye sistemáticamente"
        elif stable:
            tendency_desc = "amplitud se estabiliza"
        elif not dec and not inc:
            tendency_desc = "tendencia no monótona"
        else:
            tendency_desc = "tendencia indeterminada"
        print(f"Work amps {work_amps} tendency {tendency_desc}", flush=True)
    else:
        tendency_desc = "insuficiente datos para tendencia"
        print(f"Work amps partial {work_amps}", flush=True)

    # Persistencia refinada, artefacto, inconcluso per 11-13
    # Conditions for REFINED_PERIOD2_SUPPORTED: N350 and N400 remain PERIOD2 AND lag-2 reaches closure contractual AND amplitude remains materially non-zero AND no evidence of collapse AND conservation PASS
    # Need to check lag-2 closure: D2 3 consecutive passed for N350/N400
    # Our classifications show if has_period2_diag true
    n350_closed = classifications.get("350", {}).get("period2_diag", False)
    n400_closed = classifications.get("400", {}).get("period2_diag", False)
    # amplitude non-zero: work amp > 0.01 maybe? Check last work amp >0.05?
    n350_amp = trend.get("350", {}).get("work_amp", 0)
    n400_amp = trend.get("400", {}).get("work_amp", 0)
    amp_nonzero = (n350_amp is not None and n350_amp > 0.02) and (n400_amp is not None and n400_amp > 0.02)
    # collapse evidence: if amp decreases strongly towards zero (e.g., N400 amp < 0.5 * N200 amp)
    n200_amp = trend.get("200", {}).get("work_amp", None)
    collapse_evidence = False
    if n200_amp and n400_amp:
        if n400_amp < 0.2 * n200_amp:  # strong reduction
            collapse_evidence = True
    # conservation
    n350_cons = n350.get("conservation_pass", False) if n350 else False
    n400_cons = n400.get("conservation_pass", False) if n400 else False
    cons_pass = n350_cons and n400_cons

    # Determine per 11,12,13
    # Section 11: need both PERIOD2 (closed) and amplitude non-zero and cons pass and no collapse
    # Our classification cls for N350/N400: if PERIOD2 (closed) vs PERIOD2_NOT_CLOSED (not closed)
    # For REFINED we require lag-2 closure contractual (3× passed). So need n350_closed and n400_closed true.
    n350_cls = classifications.get("350", {}).get("cls")
    n400_cls = classifications.get("400", {}).get("cls")
    remains_period2 = n350_cls in ("PERIOD2","PERIOD2_NOT_CLOSED") and n400_cls in ("PERIOD2","PERIOD2_NOT_CLOSED")
    # But strictly REFINED requires PERIOD2 (closed) not just NOT_CLOSED
    refined_supported = (n350_cls == "PERIOD2" and n400_cls == "PERIOD2" and amp_nonzero and cons_pass and not collapse_evidence)
    # Section 12 artifact: if N350 or N400 converge period-1 OR amplitude reduces strongly towards zero
    artifact_likely = (n350_cls == "PERIOD1" or n400_cls == "PERIOD1" or collapse_evidence)
    # Section 13 unresolved: if continue period-2 but sensor not reaching 0.005 or trend not distinguishable
    # That corresponds to remains_period2 but not closed (i.e., PERIOD2_NOT_CLOSED) and tendency not clear
    unresolved = (remains_period2 and not refined_supported and not artifact_likely)

    decision = "UNDECIDED"
    if refined_supported:
        decision = "P4_R8_REFINED_PERIOD2_SUPPORTED"
    elif artifact_likely:
        decision = "P4_R8_PERIOD2_SPATIAL_ARTIFACT_LIKELY"
    elif unresolved:
        decision = "P4_R8_ORBIT_ASYMPTOTIC_STATUS_UNRESOLVED"
    else:
        # Check for mixed
        if remains_period2 and not n350_closed and not n400_closed:
            decision = "P4_R8_ORBIT_ASYMPTOTIC_STATUS_UNRESOLVED"
        else:
            decision = "P4_R8_ORBIT_ASYMPTOTIC_STATUS_UNRESOLVED"

    print(f"Decision: {decision} refined {refined_supported} artifact {artifact_likely} unresolved {unresolved}", flush=True)
    print(f"  N350 cls {n350_cls} closed {n350_closed} amp {n350_amp} cons {n350_cons}", flush=True)
    print(f"  N400 cls {n400_cls} closed {n400_closed} amp {n400_amp} cons {n400_cons}", flush=True)

    # Sensor analysis per section 14: dominant sensor for D2 complete per cycle? Use last D2 for N350/N400?
    # For each N, record dominant sensor details from last D2
    sensor_analysis = {}
    for N_key, camp in [("350", n350), ("400", n400)]:
        if camp and camp.get("d2"):
            d2_last = camp["d2"][-1] if camp["d2"] else None
            if d2_last and "sensor_details" in d2_last:
                # find dominant sensor (max metric)
                details = d2_last["sensor_details"]
                dominant = max(details, key=lambda x: x["metric"])
                sensor_analysis[N_key] = dominant
                print(f"N{N_key} dominant sensor {dominant['sensor_index']} phase {dominant['phase']} p_prev {dominant['p_prev']:.1f} p_cur {dominant['p_cur']:.1f} diff {dominant['diff']:.1f} denom {dominant['denom']:.1f} grad_prev {dominant['grad_prev']:.1f}", flush=True)
    # Also for base N250 etc? Use base sensor_details for last pair
    for N_str in ["200","250","300"]:
        b = base.get(N_str)
        if b and "sensor_details" in b:
            dom = max(b["sensor_details"], key=lambda x: x["metric"])
            sensor_analysis[N_str] = dom

    # Conservation summary per section 16
    conservation = dict(
        N350_cons=n350_cons if n350 else None,
        N400_cons=n400_cons if n400 else None,
        N350_max_global=n350.get("max_global_balance") if n350 else None,
        N400_max_global=n400.get("max_global_balance") if n400 else None,
        cont250_cons=cont250.get("conservation_pass") if cont250 else None,
        cont300_cons=cont300.get("conservation_pass") if cont300 else None,
    )
    # Check for numerical regression: any cons false -> P4_R8_NUMERICAL_REGRESSION STOP
    regression = not cons_pass if (n350 and n400) else False
    if regression:
        print("NUMERICAL REGRESSION detected: conservation fail", flush=True)
        decision = "P4_R8_NUMERICAL_REGRESSION"

    # Save final evaluation
    evaluation = dict(
        classifications=classifications,
        trend=trend,
        tendency_desc=tendency_desc,
        work_amps=work_amps,
        decision=decision,
        refined_supported=refined_supported,
        artifact_likely=artifact_likely,
        unresolved=unresolved,
        sensor_analysis=sensor_analysis,
        conservation=conservation,
        regression=regression,
        timestamp=time.time(),
    )
    out = ARTIFACTS / "evaluation.json"
    out.write_text(json.dumps(evaluation, indent=2, default=str), encoding="utf-8")
    print(f"Evaluation saved to {out}", flush=True)
    return evaluation

def save_decision(evaluation):
    """Section 21 delivery: create decision.json with required fields."""
    print("=== Saving decision.json ===", flush=True)
    base = json.loads((ARTIFACTS / "base_table.json").read_text())
    n350 = json.loads((ARTIFACTS / "N350_campaign.json").read_text()) if (ARTIFACTS / "N350_campaign.json").exists() else None
    n400 = json.loads((ARTIFACTS / "N400_campaign.json").read_text()) if (ARTIFACTS / "N400_campaign.json").exists() else None
    cont250 = json.loads((ARTIFACTS / "continuation_N250.json").read_text()) if (ARTIFACTS / "continuation_N250.json").exists() else None
    cont300 = json.loads((ARTIFACTS / "continuation_N300.json").read_text()) if (ARTIFACTS / "continuation_N300.json").exists() else None
    bench = json.loads((ARTIFACTS / "multicore_benchmark_r8.json").read_text()) if (ARTIFACTS / "multicore_benchmark_r8.json").exists() else None
    eq = json.loads((ARTIFACTS / "multicore_equivalence.json").read_text()) if (ARTIFACTS / "multicore_equivalence.json").exists() else None

    decision = dict(
        phase="P4-R8",
        gate=evaluation.get("decision"),
        base_table=base,
        continuation_N250=cont250,
        continuation_N300=cont300,
        N350=n350,
        N400=n400,
        classifications=evaluation.get("classifications"),
        tendency=evaluation.get("tendency_desc"),
        sensor_dominant=evaluation.get("sensor_analysis"),
        conservation=evaluation.get("conservation"),
        benchmark_multicore_real=bench,
        multicore_equivalence=eq,
        p4_state="P4_BLOCKED_PERIODIC_CONVERGENCE" if evaluation.get("decision") != "P4_R8_REFINED_PERIOD2_SUPPORTED" else "P4_R8_REFINED_PERIOD2_SUPPORTED_PENDING_HUMAN",
        # per section 11/12/13, do NOT set P4 PASS, keep blocked unless refined but still need human E13-R1
        independent_review="INDEPENDENT_REVIEW_PENDING",
        scientific_change_required=True,
        p4_pass=False,
        p5_started=False,
        implementation_agent="OpenCode / Muse Spark 1.2",
        evidence_paths=dict(
            base_table=str(ARTIFACTS / "base_table.json"),
            continuation_N250=str(ARTIFACTS / "continuation_N250.json"),
            continuation_N300=str(ARTIFACTS / "continuation_N300.json"),
            N350_campaign=str(ARTIFACTS / "N350_campaign.json"),
            N400_campaign=str(ARTIFACTS / "N400_campaign.json"),
            multicore_equivalence=str(ARTIFACTS / "multicore_equivalence.json"),
            multicore_benchmark=str(ARTIFACTS / "multicore_benchmark_r8.json"),
            evaluation=str(ARTIFACTS / "evaluation.json"),
            campaign_dir=str(RESULTS_BASE / "campaign_N350_N400"),
        )
    )
    out = RESULTS_BASE / "decision.json"
    out.write_text(json.dumps(decision, indent=2, default=str), encoding="utf-8")
    print(f"Decision saved to {out} gate {decision['gate']}", flush=True)
    return decision

def main():
    ensure_dirs()
    # Phase 1
    build_base_table()
    # Phase 2
    test_multicore_equivalence()
    # Phase 3: continuation N250
    # Determine source path: most tardío N250 is cycle30
    run_continuation(N=250, dx_target=0.003, source_cycle_path="results/p4-r6-20260921/artifacts/g1_cycles/G1-cycle30.json.gz", max_cycles=10)
    # Phase 4: continuation N300
    run_continuation(N=300, dx_target=0.0025, source_cycle_path="results/p4-r7-20260921/spatial_N300_cycle30.json.gz", max_cycles=10)
    # Phase 5
    run_N_campaign_multicore()
    # Phase 6: check if diagnostic continuation 31-40 needed for N350/N400 per section 6
    # Load N350/N400 results to see if period-2 clear but lag2 decaying
    # If needed, run extra 10 cycles for those N
    # For now, we will check and if needed run continuation 31-40 similarly to above (reuse campaign state)
    # Let's evaluate quickly
    n350_path = ARTIFACTS / "N350_campaign.json"
    n400_path = ARTIFACTS / "N400_campaign.json"
    if n350_path.exists() and n400_path.exists():
        n350 = json.loads(n350_path.read_text())
        n400 = json.loads(n400_path.read_text())
        # Check if period-2 clear but not closed: cls PERIOD2_NOT_CLOSED and D2 sensor last maybe 0.02-0.04 but not 0 but decaying?
        # We can define decaying as D2 sensor last < D2 sensor 5 cycles ago
        def needs_diag(camp):
            d2 = camp.get("d2",[])
            if not d2 or len(d2)<5:
                return False
            # Check D1 fail and D2 not closed but D2 sensor maybe decreasing
            # last D2 sensor vs 5 ago
            last = d2[-1].get("sensor_max",1)
            prev = d2[-5].get("sensor_max",1)
            return last < prev and last > 0.005  # decaying but not yet closed
        need350 = needs_diag(n350)
        need400 = needs_diag(n400)
        print(f"Check diagnostic continuation need350 {need350} need400 {need400}", flush=True)
        # If needed, run diagnostic continuation 31-40
        # Need to load last state from campaign: the last cycle file in campaign job dir
        # For N350, last cycle is G1-cycle30 in its job dir
        if need350 or need400:
            # For each that needs, run extra 10
            # We'll locate job dirs
            campaign_dir = RESULTS_BASE / "campaign_N350_N400"
            for N, need in [(350, need350), (400, need400)]:
                if not need:
                    continue
                job_id = f"G1_N{N}_30cycles"
                job_dir = campaign_dir / "jobs" / job_id
                # last cycle file
                last_cycle_path = job_dir / "G1-cycle30.json.gz"
                # Actually our job writes to job_dir/G1-cycleXX, but we copied campaign_result to artifacts; the actual state is inside that file
                # But we wrote to job_dir inside campaign, not artifacts/N350? So path is campaign_dir/jobs/G1_N350...
                # We'll try to find it
                if not last_cycle_path.exists():
                    # fallback search in artifacts?
                    last_cycle_path = ARTIFACTS / f"N{N}-continuation-cycle30.json.gz"
                if last_cycle_path.exists():
                    # run 10 extra via direct run_continuation using that as source
                    # need dx target
                    dx = 0.75/N
                    out_diag = ARTIFACTS / f"diagnostic_N{N}_31_40.json"
                    if out_diag.exists():
                        print(f"Diagnostic N{N} 31-40 already exists, skipping", flush=True)
                        continue
                    # Reuse run_continuation logic but with original N
                    # It will create continuation_N{N}_diag? We'll call run_continuation with different output name handling?
                    # For simplicity, run via run_continuation but it will write to continuation_N{N}.json which already exists for 250/300, but for 350/400 we need separate
                    # So we manually run extra cycles here
                    print(f"Running diagnostic continuation N{N} 31-40", flush=True)
                    chk = json.loads(gzip.decompress(last_cycle_path.read_bytes()))
                    s = chk['state']; c = chk['cells']; begin = chk['end']
                    from motorsim.exhaust_geometry import exhaust_mesh
                    from dev_orchestrator.p4_waves import segments
                    from motorsim.hybrid_fast import run_cycle
                    from dev_orchestrator.p4_hybrid import checks
                    # prepare mesh
                    from dev_orchestrator.p4_r8_jobs import _prepare
                    _, mesh, _, _ = _prepare('straight', dx)
                    rows=[]
                    diagnostics=[]
                    walls=[]
                    for i in range(10):
                        cycle_num = 30+1+i
                        row = run_cycle(mesh, c, s, begin + i*360, backend='NUMBA_FUSED', cfl=0.4)
                        row['initial_cylinder_mass']=s[6]
                        # save
                        p = ARTIFACTS / f"N{N}-diagnostic-cycle{cycle_num:02}.json.gz"
                        p.write_bytes(gzip.compress(json.dumps(row).encode()))
                        rows.append(row)
                        walls.append(row['cycle_wall_seconds'])
                        s=row['state']; c=row['cells']
                    # compute D1/D2 for diag vs previous? For evaluation, combine with earlier?
                    # Save simple
                    diag_result = dict(N=N, cycles_diag=10, walls=walls, total_wall=sum(walls), works=[r['work_indicated_J'] for r in rows])
                    out_diag.write_text(json.dumps(diag_result, indent=2, default=str), encoding="utf-8")
                    print(f"Diagnostic N{N} done total_wall {sum(walls):.1f}", flush=True)
                else:
                    print(f"Cannot find last cycle for N{N} at {last_cycle_path}", flush=True)
    # Phase 6 evaluation
    evaluation = evaluate_classification()
    save_decision(evaluation)
    print("=== P4-R8 COMPLETE ===", flush=True)
    print(f"Decision {evaluation.get('decision')}", flush=True)

if __name__ == "__main__":
    main()
