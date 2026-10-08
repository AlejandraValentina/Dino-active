import json, time
from pathlib import Path
from dev_orchestrator.multicore import Campaign, Job

# For R12, continue N350 even branch and N400 even branch
# N350: from 45 to 52 (need 48,50,52)
# N400: from 50 to 54 (need 50,52,54)

RESULT = Path("results/p4-r12-20260922")
RESULT.mkdir(parents=True, exist_ok=True)

def run_one(N, start_cycle, max_cycle):
    # Use p4_r11_jobs but need to handle start 45 and 50
    from dev_orchestrator.p4_r11_jobs import p4_r11_cycle_job
    import tempfile
    from dev_orchestrator.multicore import Campaign as Camp, Job as J
    camp_dir = RESULT / f"campaign_N{N}_{start_cycle}_{max_cycle}"
    camp_dir.mkdir(parents=True, exist_ok=True)
    camp = Camp(camp_dir, workers=1, estimated_per_job_mb=100)
    job_id = f"G1_N{N}_{start_cycle}_{max_cycle}"
    dx = 0.75/N
    camp.add_job(J(job_id=job_id, func=p4_r11_cycle_job, kwargs=dict(N=N, dx_target=dx, start_cycle=start_cycle, max_cycle=max_cycle, backend='NUMBA_FUSED', cfl=0.4), estimated_memory_mb=100))
    res = camp.run(timeout=1800)
    print(f"N{N} {start_cycle}->{max_cycle} wall {res.wall_seconds:.1f} passed {res.passed} failed {res.failed}")
    # Collect result
    job_path = camp_dir / "jobs" / job_id
    res_path = job_path / "r11_result.json"
    if res_path.exists():
        data = json.loads(res_path.read_text())
        (RESULT / f"r12_continuation_N{N}_{start_cycle}_{max_cycle}.json").write_text(json.dumps(data, indent=2))
        return data
    else:
        print(f"Missing result for N{N}")
        return None

if __name__ == "__main__":
    # Warm
    print("Warm...")
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
    print("Warm done")
    # Run N350 45->52 (covers even 48,50,52)
    r350 = run_one(350, 45, 52)
    # Run N400 50->54 (covers even 50,52,54) - but 50 already exists as even PASS, need 52,54
    r400 = run_one(400, 50, 54)
    print("Done", r350.get("first_3x_cycle") if r350 else None, r400.get("first_3x_cycle") if r400 else None)
