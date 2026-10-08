"""Generate 30 G1 cycles for R6 diagnosis, saving full histories."""
import gzip, json, time
from pathlib import Path
from dev_orchestrator.p4_hybrid import prepare, checks, periodic
from motorsim.hybrid_fast import run_cycle
from dev_orchestrator.p2_campaign import ROOT, sha, write

out = Path("results/p4-r6-20260921/artifacts/g1_cycles")
out.mkdir(parents=True, exist_ok=True)
meta = Path("results/p4-r6-20260921")
meta.mkdir(parents=True, exist_ok=True)

model, mesh, pipe, state = prepare('straight')
prev=None
history=[]
t0=time.perf_counter()
for cycle in range(1,31):
    init_mass=state[6]
    row=run_cycle(mesh, pipe, state, 180+360*(cycle-1), backend='NUMBA_FUSED')
    row['initial_cylinder_mass']=init_mass
    c=checks(row)
    comp=periodic(prev,row) if prev and row['complete'] else None
    entry=dict(cycle=cycle, work=row['work_indicated_J'], checks=c, periodic=comp, wall=row['cycle_wall_seconds'])
    history.append(entry)
    # save full row
    p=out/f"G1-cycle{cycle:02}.json.gz"
    p.write_bytes(gzip.compress(json.dumps(row,allow_nan=False).encode()))
    print(f"cycle {cycle} work {row['work_indicated_J']:.3f} periodic {comp['passed'] if comp else None} wall {row['cycle_wall_seconds']:.1f}")
    state=row['state']; pipe=row['cells']; prev=row

write(meta/"g1_history.json", history)
print(f"done {time.perf_counter()-t0:.1f}s")

# also generate 15 G2 for diagnostic
out2=Path("results/p4-r6-20260921/artifacts/g2_cycles")
out2.mkdir(parents=True, exist_ok=True)
model2, mesh2, pipe2, state2 = prepare('chain')
prev=None
for cycle in range(1,16):
    init_mass=state2[6]
    row=run_cycle(mesh2, pipe2, state2, 180+360*(cycle-1), backend='NUMBA_FUSED')
    row['initial_cylinder_mass']=init_mass
    p=out2/f"G2-cycle{cycle:02}.json.gz"
    p.write_bytes(gzip.compress(json.dumps(row,allow_nan=False).encode()))
    print(f"G2 cycle {cycle} work {row['work_indicated_J']:.3f}")
    state2=row['state']; pipe2=row['cells']; prev=row
