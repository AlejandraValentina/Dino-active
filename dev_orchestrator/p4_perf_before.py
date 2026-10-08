"""P4-PERF-01 BEFORE baseline: N250/N400 warmup+3 cycles, JIT hot, metrics."""
import json, gzip, time, hashlib, os, sys, tempfile
from pathlib import Path
import psutil

RESULTS = Path("results/p4-perf-01-20260922/before")
RESULTS.mkdir(parents=True, exist_ok=True)

# Ensure JIT warm
from motorsim.exhaust_geometry import exhaust_mesh
from dev_orchestrator.p4_waves import segments
from motorsim.hybrid_fast import run_cycle
from motorsim.hybrid_exhaust import LegacySources
from motorsim.gas1d.eos import IdealGas

def prepare_straight(dx_target):
    model = LegacySources()
    mesh = exhaust_mesh(segments('straight'), dx_target)
    p, T, Y = model.case.initial_pty[3]
    eos = IdealGas()
    U = eos.conservative((p/(eos.R*T), 0., p, Y))
    pipe = [tuple(v*u for u in U) for v in mesh.volumes]
    state = model.initial_state()[:9]
    return model, mesh, pipe, state, eos

def measure_checkpoint(row):
    # measure raw JSON size, gzip size, timings
    import json as js
    t0=time.perf_counter()
    raw = js.dumps(row).encode()
    t1=time.perf_counter()
    ser_time = t1-t0
    raw_size = len(raw)
    t2=time.perf_counter()
    gz = gzip.compress(raw)
    t3=time.perf_counter()
    gz_time = t3-t2
    gz_size = len(gz)
    # write time to temp file (Windows needs close before unlink)
    import tempfile as _tf
    fd, tmp_path = _tf.mkstemp()
    os.close(fd)
    p = Path(tmp_path)
    try:
        t4=time.perf_counter()
        p.write_bytes(gz)
        t5=time.perf_counter()
        write_time = t5-t4
        # read back
        t6=time.perf_counter()
        data = p.read_bytes()
        t7=time.perf_counter()
        read_time = t7-t6
        t8=time.perf_counter()
        ungz = gzip.decompress(data)
        t9=time.perf_counter()
        decomp_time = t9-t8
        t10=time.perf_counter()
        deser = js.loads(ungz.decode())
        t11=time.perf_counter()
        deser_time = t11-t10
    finally:
        try:
            p.unlink()
        except:
            pass
    return dict(
        json_raw_bytes=raw_size,
        json_serialize_seconds=ser_time,
        gzip_bytes=gz_size,
        gzip_compress_seconds=gz_time,
        write_seconds=write_time,
        read_seconds=read_time,
        gzip_decompress_seconds=decomp_time,
        json_deserialize_seconds=deser_time,
        compression_ratio=gz_size/raw_size if raw_size else 0
    )

def run_case(N, dx_target):
    print(f"=== BEFORE N{N} dx {dx_target} ===", flush=True)
    model, mesh, pipe, state, eos = prepare_straight(dx_target)
    print(f"mesh n={mesh.n}", flush=True)
    # JIT warmup: tiny run already? Do one short cycle warmup not counted
    # Warmup cycle
    begin = 180.0
    s = state
    c = pipe
    # Warmup not counted
    print("Warmup cycle (JIT)...", flush=True)
    t_warm_start = time.perf_counter()
    row_warm = run_cycle(mesh, c, s, begin, backend='NUMBA_FUSED', cfl=0.4)
    t_warm_end = time.perf_counter()
    print(f"Warmup done wall {row_warm['cycle_wall_seconds']:.2f}s solver {row_warm['solver_seconds']:.2f}s total {t_warm_end-t_warm_start:.2f}", flush=True)
    s = row_warm['state']
    c = row_warm['cells']
    begin += 360
    # Now 3 measured cycles
    cycles = []
    proc = psutil.Process()
    peak_rss = 0
    for i in range(3):
        print(f"Measured cycle {i+1}/3 begin {begin:.1f}", flush=True)
        rss_before = proc.memory_info().rss
        t0 = time.perf_counter()
        row = run_cycle(mesh, c, s, begin, backend='NUMBA_FUSED', cfl=0.4)
        t1 = time.perf_counter()
        wall_cycle = row['cycle_wall_seconds']
        solver = row['solver_seconds']
        # counts
        # row['segments'] contains per-segment solver results with counts?
        # Aggregate counts from segments
        total_counts = dict(rhs=0, HLLC=0, HLLE=0, characteristic=0, rejected=0, downgrades=0)
        for seg in row['segments']:
            r = seg['result']
            cc = r.get('counts', {})
            for k in total_counts:
                total_counts[k] += cc.get(k, 0)
        # also history length = accepted steps?
        # Each history entry corresponds to a successful SSP step (accepted)
        # Rejected already counted
        accepted = len(row['history'])
        # diagnostics time is not directly available, estimate via solver vs wall?
        # We'll approximate diagnostics as postprocessing part of run_cycle not solver
        diagnostics_time = wall_cycle - solver
        # serialization etc.
        io = measure_checkpoint(row)
        # peak ram
        rss_after = proc.memory_info().rss
        peak_rss = max(peak_rss, rss_before, rss_after)
        # Python↔Numba calls: count RHS calls = counts rhs
        cycles.append(dict(
            cycle=i+1,
            begin=begin,
            wall_cycle_seconds=wall_cycle,
            solver_seconds=solver,
            diagnostics_seconds=diagnostics_time,
            counts=total_counts,
            accepted_steps=len(row['history']),
            rejected_steps=total_counts['rejected'],
            hllc_faces=total_counts['HLLC'],
            hlle_fallbacks=total_counts['HLLE'],
            history_len=len(row['history']),
            stages_len=len(row.get('stages', [])),
            io=io,
            work=row['work_indicated_J'],
            power=row['power_indicated_W'],
            global_balance=row['global_balance'],
            max_global_residual=row['segments'][0]['result'].get('max_global_residual') if row['segments'] else None,
            checkpoint_json_raw_mb=io['json_raw_bytes']/ (1024*1024),
            checkpoint_gz_mb=io['gzip_bytes']/(1024*1024),
            rss_before_mb=rss_before/(1024*1024),
            rss_after_mb=rss_after/(1024*1024),
        ))
        print(f"  wall {wall_cycle:.2f} solver {solver:.2f} diag {diagnostics_time:.2f} RHS {total_counts['rhs']} HLLC {total_counts['HLLC']} HLLE {total_counts['HLLE']} reject {total_counts['rejected']} json {io['json_raw_bytes']/1e6:.2f}MB gz {io['gzip_bytes']/1e6:.2f}MB ser {io['json_serialize_seconds']:.3f} gz {io['gzip_compress_seconds']:.3f} wr {io['write_seconds']:.3f}", flush=True)
        s = row['state']
        c = row['cells']
        begin += 360
        # save row for later analysis (optional)
        gpath = RESULTS / f"G1_N{N}_cycle{i+1:02}.json.gz"
        gpath.write_bytes(gzip.compress(json.dumps(row).encode()))
    # aggregate
    avg_wall = sum(c['wall_cycle_seconds'] for c in cycles)/len(cycles)
    avg_solver = sum(c['solver_seconds'] for c in cycles)/len(cycles)
    avg_ser = sum(c['io']['json_serialize_seconds'] for c in cycles)/len(cycles)
    avg_gz = sum(c['io']['gzip_compress_seconds'] for c in cycles)/len(cycles)
    avg_wr = sum(c['io']['write_seconds'] for c in cycles)/len(cycles)
    avg_raw_mb = sum(c['checkpoint_json_raw_mb'] for c in cycles)/len(cycles)
    avg_gz_mb = sum(c['checkpoint_gz_mb'] for c in cycles)/len(cycles)
    # peak ram overall
    mem = psutil.virtual_memory()
    result = dict(
        N=N,
        dx_target=dx_target,
        mesh_n=mesh.n,
        backend='NUMBA_FUSED',
        cfl=0.4,
        warmup_wall=row_warm['cycle_wall_seconds'],
        cycles=cycles,
        avg_wall_cycle_seconds=avg_wall,
        avg_solver_seconds=avg_solver,
        avg_serialize_seconds=avg_ser,
        avg_gzip_seconds=avg_gz,
        avg_write_seconds=avg_wr,
        avg_checkpoint_raw_mb=avg_raw_mb,
        avg_checkpoint_gz_mb=avg_gz_mb,
        peak_rss_mb=peak_rss/(1024*1024),
        total_wall_seconds=sum(c['wall_cycle_seconds'] for c in cycles),
        python_numba_transitions_estimate=sum(c['counts']['rhs']*2 for c in cycles), # each RHS involves Python->Numba, plus validation
        system_memory=dict(total_mb=mem.total/(1024*1024), available_mb=mem.available/(1024*1024)),
        config_hash=hashlib.sha256(json.dumps(dict(N=N, dx=dx_target, backend='NUMBA_FUSED', cfl=0.4)).encode()).hexdigest()[:12],
    )
    out = RESULTS / f"before_N{N}.json"
    out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"Saved {out} avg_wall {avg_wall:.2f} raw {avg_raw_mb:.2f}MB gz {avg_gz_mb:.2f}MB", flush=True)
    return result

if __name__ == "__main__":
    # Warm JIT for NUMBA_FUSED already done inside run_case first warmup, but do early global warm
    print("Global JIT warm (small N=100)...", flush=True)
    m0, mesh0, pipe0, state0, eos0 = prepare_straight(0.75/100)
    _ = run_cycle(mesh0, pipe0, state0, 180.0, backend='NUMBA_FUSED', cfl=0.4)
    print("Warm done", flush=True)
    # Run both
    r250 = run_case(250, 0.75/250)
    r400 = run_case(400, 0.75/400)
    # Summary
    summary = dict(
        cases=dict(N250=r250, N400=r400),
        before=dict(
            N250_wall_cycle=r250['avg_wall_cycle_seconds'],
            N400_wall_cycle=r400['avg_wall_cycle_seconds'],
            N250_solver=r250['avg_solver_seconds'],
            N400_solver=r400['avg_solver_seconds'],
            N250_raw_mb=r250['avg_checkpoint_raw_mb'],
            N400_raw_mb=r400['avg_checkpoint_raw_mb'],
            N250_gz_mb=r250['avg_checkpoint_gz_mb'],
            N400_gz_mb=r400['avg_checkpoint_gz_mb'],
            N250_serialize=r250['avg_serialize_seconds'],
            N400_serialize=r400['avg_serialize_seconds'],
            N250_gzip=r250['avg_gzip_seconds'],
            N400_gzip=r400['avg_gzip_seconds'],
            N250_write=r250['avg_write_seconds'],
            N400_write=r400['avg_write_seconds'],
        )
    )
    (RESULTS / "before_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print("BEFORE SUMMARY", json.dumps(summary['before'], indent=2))
