"""P4-PERF-01 AFTER baseline with new checkpoint architecture"""
import json, gzip, time, hashlib, tempfile, os
from pathlib import Path
import psutil
import numpy as np

RESULTS = Path("results/p4-perf-01-20260922/after")
RESULTS.mkdir(parents=True, exist_ok=True)

from motorsim.exhaust_geometry import exhaust_mesh
from dev_orchestrator.p4_waves import segments
from motorsim.hybrid_fast import run_cycle
from motorsim.hybrid_exhaust import LegacySources
from motorsim.gas1d.eos import IdealGas
from motorsim.checkpoint import save_summary, save_restart, load_restart, should_write_restart

def prepare_straight(dx_target):
    model = LegacySources()
    mesh = exhaust_mesh(segments('straight'), dx_target)
    p,T,Y = model.case.initial_pty[3]
    eos = IdealGas()
    U = eos.conservative((p/(eos.R*T), 0., p, Y))
    pipe = [tuple(v*u for u in U) for v in mesh.volumes]
    state = model.initial_state()[:9]
    return model, mesh, pipe, state, eos

def run_case(N, dx_target, restart_every=5):
    print(f"=== AFTER N{N} dx {dx_target} restart_every={restart_every} ===", flush=True)
    model, mesh, pipe, state, eos = prepare_straight(dx_target)
    print(f"mesh n={mesh.n}", flush=True)
    begin = 180.0
    s = state
    c = pipe
    # Warmup
    print("Warmup cycle (JIT)...", flush=True)
    row_warm = run_cycle(mesh, c, s, begin, backend='NUMBA_FUSED', cfl=0.4)
    s = row_warm['state']
    c = row_warm['cells']
    begin += 360
    cycles = []
    proc = psutil.Process()
    peak_rss = 0
    # Setup dirs for checkpoints
    base_dir = RESULTS / f"G1_N{N}"
    base_dir.mkdir(parents=True, exist_ok=True)
    # For restart, use per-cycle dirs
    for i in range(3):
        cycle_num = i+1
        print(f"Measured cycle {cycle_num}/3 begin {begin:.1f}", flush=True)
        rss_before = proc.memory_info().rss
        t0 = time.perf_counter()
        row = run_cycle(mesh, c, s, begin, backend='NUMBA_FUSED', cfl=0.4)
        t1 = time.perf_counter()
        wall_cycle = row['cycle_wall_seconds']
        solver = row['solver_seconds']
        diagnostics_time = wall_cycle - solver
        # counts
        total_counts = dict(rhs=0, HLLC=0, HLLE=0, characteristic=0, rejected=0, downgrades=0)
        for seg in row['segments']:
            cc = seg['result'].get('counts', {})
            for k in total_counts:
                total_counts[k] += cc.get(k, 0)
        # SUMMARY write
        summary_path = base_dir / f"summary_cycle{cycle_num:02}.json"
        t2 = time.perf_counter()
        summ, summary_bytes = save_summary(row, summary_path)
        t3 = time.perf_counter()
        summary_time = t3-t2
        summary_kb = summary_bytes/1024
        # RESTART write decision per policy
        restart_time = 0
        restart_bytes = 0
        restart_path = None
        do_restart = should_write_restart(cycle_num, restart_every, is_final=(cycle_num==3))
        if do_restart:
            restart_dir = base_dir / f"restart_cycle{cycle_num:02}"
            config = dict(dx_target=dx_target, backend='NUMBA_FUSED', cfl=0.4, config_hash=hashlib.sha256(json.dumps(dict(N=N, dx=dx_target)).encode()).hexdigest()[:12])
            t4 = time.perf_counter()
            meta, raw_bytes, gz_size = save_restart(row['state'], row['cells'], cycle=cycle_num, angle=row['end'], config=config, out_dir=restart_dir, compressed=False)
            t5 = time.perf_counter()
            restart_time = t5-t4
            # size of npz
            restart_bytes = (restart_dir / "state.npz").stat().st_size + (restart_dir / "metadata.json").stat().st_size
            restart_path = str(restart_dir)
            # also measure read
            t6 = time.perf_counter()
            meta2, s2, c2 = load_restart(restart_dir)
            t7 = time.perf_counter()
            restart_read = t7-t6
        else:
            restart_read = 0
        rss_after = proc.memory_info().rss
        peak_rss = max(peak_rss, rss_before, rss_after)
        # For FULL_DEBUG we skip
        cycles.append(dict(
            cycle=cycle_num,
            wall_cycle_seconds=wall_cycle,
            solver_seconds=solver,
            diagnostics_seconds=diagnostics_time,
            counts=total_counts,
            summary_bytes=summary_bytes,
            summary_kb=summary_kb,
            summary_time=summary_time,
            restart_bytes=restart_bytes,
            restart_time=restart_time,
            restart_read=restart_read if do_restart else None,
            restart_written=do_restart,
            work=row['work_indicated_J'],
            rss_before_mb=rss_before/(1024*1024),
            rss_after_mb=rss_after/(1024*1024),
        ))
        print(f"  wall {wall_cycle:.2f} solver {solver:.2f} summary {summary_bytes}B time {summary_time:.4f}s restart {restart_bytes}B time {restart_time:.4f}s", flush=True)
        s = row['state']
        c = row['cells']
        begin += 360
        # save last row for equivalence later
        if cycle_num == 3:
            # also save as legacy for comparison? Not needed
            pass
    avg_wall = sum(c['wall_cycle_seconds'] for c in cycles)/len(cycles)
    avg_solver = sum(c['solver_seconds'] for c in cycles)/len(cycles)
    avg_summary_time = sum(c['summary_time'] for c in cycles)/len(cycles)
    avg_restart_time = sum(c['restart_time'] for c in cycles if c['restart_written'])/ max(1, sum(1 for c in cycles if c['restart_written']))
    avg_summary_kb = sum(c['summary_kb'] for c in cycles)/len(cycles)
    avg_restart_kb = sum(c['restart_bytes'] for c in cycles if c['restart_written'])/ max(1, sum(1 for c in cycles if c['restart_written']))/1024 if any(c['restart_written'] for c in cycles) else 0
    # total checkpoint bytes: summary every cycle + restart every N
    total_summary_bytes = sum(c['summary_bytes'] for c in cycles)
    total_restart_bytes = sum(c['restart_bytes'] for c in cycles)
    mem = psutil.virtual_memory()
    result = dict(
        N=N, dx_target=dx_target, mesh_n=mesh.n, backend='NUMBA_FUSED', cfl=0.4,
        restart_every=restart_every,
        cycles=cycles,
        avg_wall_cycle_seconds=avg_wall,
        avg_solver_seconds=avg_solver,
        avg_summary_seconds=avg_summary_time,
        avg_restart_seconds=avg_restart_time,
        avg_summary_kb=avg_summary_kb,
        avg_restart_kb=avg_restart_kb,
        total_summary_bytes=total_summary_bytes,
        total_restart_bytes=total_restart_bytes,
        total_checkpoint_bytes=total_summary_bytes+total_restart_bytes,
        peak_rss_mb=peak_rss/(1024*1024),
        total_wall_seconds=sum(c['wall_cycle_seconds'] for c in cycles),
        system_memory=dict(total_mb=mem.total/(1024*1024), available_mb=mem.available/(1024*1024)),
        config_hash=hashlib.sha256(json.dumps(dict(N=N, dx=dx_target, backend='NUMBA_FUSED', cfl=0.4)).encode()).hexdigest()[:12],
    )
    out = RESULTS / f"after_N{N}_re{restart_every}.json"
    out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"Saved {out} avg_wall {avg_wall:.2f} avg_summary {avg_summary_kb:.2f}KB restart {avg_restart_kb:.2f}KB", flush=True)
    return result

if __name__ == "__main__":
    # Global warm
    print("Global JIT warm...", flush=True)
    m0, mesh0, pipe0, state0, eos0 = prepare_straight(0.75/100)
    _ = run_cycle(mesh0, pipe0, state0, 180., backend='NUMBA_FUSED', cfl=0.4)
    print("Warm done", flush=True)
    # Test restart_every 1 and 5 for N250 and N400, but for baseline we use 5 (default)
    r250_re5 = run_case(250, 0.75/250, restart_every=5)
    r400_re5 = run_case(400, 0.75/400, restart_every=5)
    # Also test restart_every 1 for comparison
    r250_re1 = run_case(250, 0.75/250, restart_every=1)
    r400_re1 = run_case(400, 0.75/400, restart_every=1)
    # Summary comparison
    summary = dict(
        N250_re5=r250_re5,
        N400_re5=r400_re5,
        N250_re1=r250_re1,
        N400_re1=r400_re1,
    )
    # Load before for comparison
    before_250 = json.loads((Path("results/p4-perf-01-20260922/before/before_N250.json")).read_text())
    before_400 = json.loads((Path("results/p4-perf-01-20260922/before/before_N400.json")).read_text())
    # Compute reductions
    def comp(before, after):
        return dict(
            wall_before=before['avg_wall_cycle_seconds'],
            wall_after=after['avg_wall_cycle_seconds'],
            wall_speedup=before['avg_wall_cycle_seconds']/after['avg_wall_cycle_seconds'] if after['avg_wall_cycle_seconds'] else 0,
            wall_reduction_percent=(1-after['avg_wall_cycle_seconds']/before['avg_wall_cycle_seconds'])*100,
            checkpoint_before_mb=before['avg_checkpoint_gz_mb'],
            checkpoint_after_mb=after['total_checkpoint_bytes']/len(after['cycles'])/(1024*1024),
            checkpoint_reduction_percent=(1 - (after['total_checkpoint_bytes']/len(after['cycles'])/(1024*1024))/before['avg_checkpoint_gz_mb'])*100,
            serialize_before=before['avg_serialize_seconds'],
            serialize_after=after['avg_summary_seconds'],
            serialize_reduction=(1-after['avg_summary_seconds']/before['avg_serialize_seconds'])*100 if before['avg_serialize_seconds'] else 0,
            gzip_before=before['avg_gzip_seconds'],
            gzip_after=0, # no gzip for summary
            raw_before_mb=before['avg_checkpoint_raw_mb'],
            raw_after_mb=after['avg_summary_kb']/1024,
        )
    comparison = dict(
        N250_re5_vs_before=comp(before_250, r250_re5),
        N400_re5_vs_before=comp(before_400, r400_re5),
        N250_re1_vs_before=comp(before_250, r250_re1),
        N400_re1_vs_before=comp(before_400, r400_re1),
    )
    (RESULTS / "after_summary.json").write_text(json.dumps(dict(summary=summary, comparison=comparison), indent=2), encoding="utf-8")
    print("AFTER SUMMARY comparison", json.dumps(comparison, indent=2))
