"""P4-R11 Stage A (41-60) and B (61-80)"""
import json, time
from pathlib import Path
from dev_orchestrator.multicore import Campaign, Job
from dev_orchestrator.p4_r11_jobs import p4_r11_cycle_job

RESULT = Path("results/p4-r11-20260922")
RESULT.mkdir(parents=True, exist_ok=True)

def run_stage(stage, Ns, max_cycle, workers):
    print(f"=== Stage {stage} Ns {Ns} max_cycle {max_cycle} workers {workers} ===", flush=True)
    camp_dir = RESULT / f"campaign_stage{stage}"
    camp_dir.mkdir(parents=True, exist_ok=True)
    camp = Campaign(camp_dir, workers=workers, estimated_per_job_mb=100)
    for N in Ns:
        dx = 0.75/N
        job_id = f"G1_N{N}_{stage}"
        camp.add_job(Job(job_id=job_id, func=p4_r11_cycle_job, kwargs=dict(N=N, dx_target=dx, start_cycle=40, max_cycle=max_cycle, backend='NUMBA_FUSED', cfl=0.4), estimated_memory_mb=100))
    start = time.perf_counter()
    res = camp.run(timeout=1800)
    wall = res.wall_seconds
    seq = res.sequential_estimated_seconds
    print(f"Stage {stage} wall {wall:.1f} seq {seq:.1f} speedup {res.speedup:.2f} passed {res.passed} failed {res.failed}", flush=True)
    # Collect results
    results = {}
    for N in Ns:
        job_id = f"G1_N{N}_{stage}"
        job_path = camp_dir / "jobs" / job_id
        res_path = job_path / "r11_result.json"
        if res_path.exists():
            results[str(N)] = json.loads(res_path.read_text())
        else:
            results[str(N)] = None
            print(f"Missing result for N{N}", flush=True)
    # Save multicore runtime
    runtime = dict(stage=stage, Ns=Ns, max_cycle=max_cycle, workers=workers, wall=wall, sequential=seq, speedup=res.speedup, efficiency=res.efficiency, passed=res.passed, failed=res.failed)
    (RESULT / f"multicore_runtime_stage{stage}.json").write_text(json.dumps(runtime, indent=2))
    return results, runtime

if __name__ == "__main__":
    # Warm JIT
    print("Warm JIT N250...", flush=True)
    from motorsim.exhaust_geometry import exhaust_mesh
    from dev_orchestrator.p4_waves import segments
    from motorsim.hybrid_fast import run_cycle
    from motorsim.hybrid_exhaust import LegacySources
    from motorsim.gas1d.eos import IdealGas
    model = LegacySources()
    mesh = exhaust_mesh(segments('straight'), 0.003)
    p,T,Y = model.case.initial_pty[3]
    eos = IdealGas()
    U = eos.conservative((p/(eos.R*T),0.,p,Y))
    pipe = [tuple(v*u for u in U) for v in mesh.volumes]
    state = model.initial_state()[:9]
    _ = run_cycle(mesh, pipe, state, 180., backend='NUMBA_FUSED', cfl=0.4)
    print("Warm done", flush=True)

    # Stage A 41-60 workers 3, early stop 3x lag-2 PASS
    results, runtime = run_stage("A", [300,350,400], 60, workers=3)
    for N in [300,350,400]:
        key=str(N)
        if results[key]:
            (RESULT / f"temporal_metrics_N{N}.json").write_text(json.dumps(results[key], indent=2))
    # Determine need for separate B reporting: check which achieved 3x before 60 vs after
    for N in [350,400]:
        r = results[str(N)]
        if r:
            print(f"N{N} first_3x {r.get('first_3x_cycle')} max_streak {r.get('max_streak')} cycles {r.get('cycles_executed')}", flush=True)
    (RESULT / "multicore_runtime.json").write_text(json.dumps(runtime, indent=2))
    # Check need for Stage B (61-80) if N350/N400 not yet 3x
    need_B = []
    for N in [350,400]:
        r = results[str(N)]
        if r is None or r.get("first_3x_cycle") is None:
            need_B.append(N)
    print(f"Need B for {need_B}", flush=True)
    if need_B:
        workers_B = len(need_B)
        print(f"Running Stage B 61-80 for {need_B} workers {workers_B}", flush=True)
        # For B, need to start from 60, so we need to run jobs from 60 to 80
        # Reuse same job but with start_cycle 60
        from dev_orchestrator.multicore import Campaign as Camp2, Job as Job2
        from dev_orchestrator.p4_r11_jobs import p4_r11_cycle_job as job2
        camp_dir = RESULT / "campaign_stageB"
        camp_dir.mkdir(parents=True, exist_ok=True)
        camp = Camp2(camp_dir, workers=workers_B, estimated_per_job_mb=100)
        for N in need_B:
            dx = 0.75/N
            job_id = f"G1_N{N}_B"
            camp.add_job(Job2(job_id=job_id, func=job2, kwargs=dict(N=N, dx_target=dx, start_cycle=60, max_cycle=80, backend='NUMBA_FUSED', cfl=0.4), estimated_memory_mb=100))
        import time as _t
        start=_t.perf_counter()
        res=camp.run(timeout=1800)
        wall=res.wall_seconds
        print(f"Stage B wall {wall:.1f} passed {res.passed}", flush=True)
        for N in need_B:
            job_id=f"G1_N{N}_B"
            job_path=camp_dir / "jobs" / job_id
            res_path=job_path / "r11_result.json"
            if res_path.exists():
                import json as _js
                data=_js.loads(res_path.read_text())
                (RESULT / f"temporal_metrics_N{N}_B.json").write_text(_js.dumps(data, indent=2))
                print(f"N{N} B first_3x {data.get('first_3x_cycle')} cycles {data.get('cycles_executed')}", flush=True)
        (RESULT / "multicore_runtime_stageB.json").write_text(json.dumps(dict(stage="B", Ns=need_B, workers=workers_B, wall=wall, sequential=res.sequential_estimated_seconds, speedup=res.speedup), indent=2))
    else:
        print("No B needed", flush=True)
    print("Done long horizon")
