"""Microbenchmark RHS 1000 reps: R4 (3 crossings) vs R5 fused (1 crossing)."""
import time, json, gzip, numpy as np
from pathlib import Path
from motorsim.gas1d.eos import IdealGas
from motorsim.gas1d.boundary import Boundary
from dev_orchestrator.p4_hybrid import prepare
from dev_orchestrator.p2_campaign import write
import motorsim.exhaust_numba as r4
import motorsim.exhaust_numba_fused as r5

def run(run_dir):
    run_dir=Path(run_dir)
    art=run_dir/'artifacts'
    art.mkdir(parents=True, exist_ok=True)
    eos=IdealGas()
    _, mesh, pipe, state = prepare('straight')
    # need kernel for volumes etc
    from motorsim.exhaust_numba import Kernel as K4
    k4=K4(mesh,eos)
    from motorsim.exhaust_numba_fused import FUSED_ENABLED  # noqa
    # Prepare 1000 distinct RHS states: use G1 cycle snapshots or generate random
    # Use 1000 random primitive states around typical operating point
    rng=np.random.default_rng(12345)
    n=mesh.n
    # generate 1000 cells snapshots: each is n x 4 conserved
    # Use typical rho ~0.7-1.5, p 90k-150k, etc
    reps=1000
    cells_list=[]
    for _ in range(reps):
        # generate primitive around 100kPa, 500K
        rho=rng.uniform(0.5,1.5, n)
        u=rng.uniform(-200,200, n)
        p=rng.uniform(90000,150000, n)
        Y=rng.uniform(0,0.5, n)
        w=np.column_stack((rho,u,p,Y))
        # conservative
        vols=np.array(mesh.volumes)
        cells=np.empty((n,4), dtype=np.float64)
        for i in range(n):
            r,u_,p_,y=w[i]
            q=eos.conservative((r,u_,p_,y))
            cells[i]=[qi*vols[i] for qi in q]
        cells_list.append(cells)
    # Prepare buffers for fused
    w_buf=np.empty((n,4),dtype=np.float64)
    lf_buf=np.empty((n,4),dtype=np.float64)
    rf_buf=np.empty((n,4),dtype=np.float64)
    bad_buf=np.empty(n,dtype=np.bool_)
    flux_buf=np.empty((n-1,4),dtype=np.float64)
    speeds_buf=np.empty((n-1,3),dtype=np.float64)
    codes_buf=np.empty(n-1,dtype=np.int64)
    ext_state=np.array([100000/(eos.R*500),0,100000,0],dtype=np.float64)
    volumes=np.array(mesh.volumes, dtype=np.float64)
    dl=k4.dl; dr=k4.dr; loff=k4.left_offset; roff=k4.right_offset
    # warm JIT
    r4.fused_interior(cells_list[0], volumes, dl, dr, loff, roff, eos.gamma, eos.R, ext_state, w_buf, lf_buf, rf_buf, bad_buf, flux_buf, speeds_buf, codes_buf)
    # also warm separate
    r4.primitive_numeric(cells_list[0], volumes, eos.gamma, eos.R)
    r4.reconstruct_numeric(np.empty((n,4)), np.array([1,0,100000,0.2]), np.array([1,0,100000,0.2]), dl, dr, loff, roff, eos.R)
    from motorsim.exhaust_batch import Kernel as KB
    kb=KB(mesh,eos)
    # warm hllc
    # use first w
    w0=r4.primitive_numeric(cells_list[0], volumes, eos.gamma, eos.R)
    lo=Boundary('outflow').face_state(tuple(w0[0].tolist()),-1,eos)
    hi=Boundary('nonreflecting', state=(100000/(eos.R*500),0,100000,0)).face_state(tuple(w0[-1].tolist()),1,eos)
    lf,rf,_=r4.reconstruct_numeric(w0, np.array(lo), np.array(hi), dl, dr, loff, roff, eos.R)
    r4.faces(lf[:-1], rf[1:], eos.gamma, eos.R) if False else None  # warm via hllc

    # Actually warm via full path
    # Use time for R4: primitive + reconstruct + faces
    import time as t
    # R4 timing: 3 separate calls per RHS
    start=t.perf_counter()
    for cells in cells_list:
        w=r4.primitive_numeric(cells, volumes, eos.gamma, eos.R)
        lo=Boundary('outflow').face_state(tuple(w[0].tolist()),-1,eos)
        hi=Boundary('nonreflecting', state=(100000/(eos.R*500),0,100000,0)).face_state(tuple(w[-1].tolist()),1,eos)
        lf,rf,_=r4.reconstruct_numeric(w, np.array(lo), np.array(hi), dl, dr, loff, roff, eos.R)
        # interior HLLC
        # need left=rf[:-1], right=lf[1:]
        # use faces
        r4.faces(rf[:-1], lf[1:], eos.gamma, eos.R)
    r4_time=t.perf_counter()-start

    start=t.perf_counter()
    for cells in cells_list:
        r5.fused_interior(cells, volumes, dl, dr, loff, roff, eos.gamma, eos.R, ext_state, w_buf, lf_buf, rf_buf, bad_buf, flux_buf, speeds_buf, codes_buf)
        # also need to handle fallback? For microbenchmark we just measure fused core, not fallback reference. For fairness, R4 also didn't include fallback reference (only HLLE). So comparable.
        # To be fair, we already measured R4 without fallback loop; fused also without fallback reference loop. So we keep.
        pass
    r5_time=t.perf_counter()-start

    speedup=r4_time/r5_time if r5_time>0 else 0
    data=dict(reps=reps, n=n, r4_seconds=r4_time, r5_seconds=r5_time, speedup=speedup, passed=speedup>=1.15, description="1000 RHS primitive+reconstruct+HLLC fused vs separate")
    print(json.dumps(data, indent=2))
    write(art/'micro_rhs.json', data)
    write(art/'result.json', dict(checks=[dict(id='micro_rhs_gate', kind='numerical', passed=speedup>=1.15, reason=f'speedup {speedup:.3f} >=1.15')], metrics=dict(speedup=speedup), scientific_change_required=False))

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(); p.add_argument('--run-dir', required=True); a=p.parse_args(); run(a.run_dir)
