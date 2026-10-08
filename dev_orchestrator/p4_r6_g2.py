import gzip, json
from pathlib import Path
from dev_orchestrator.p4_hybrid import prepare
from motorsim.hybrid_fast import run_cycle
out=Path("results/p4-r6-20260921/artifacts/g2_cycles")
out.mkdir(parents=True, exist_ok=True)
model, mesh, pipe, state = prepare('chain')
for cycle in range(1,16):
    init_mass=state[6]
    row=run_cycle(mesh, pipe, state, 180+360*(cycle-1), backend='NUMBA_FUSED')
    row['initial_cylinder_mass']=init_mass
    p=out/f"G2-cycle{cycle:02}.json.gz"
    p.write_bytes(gzip.compress(json.dumps(row,allow_nan=False).encode()))
    print(f"G2 {cycle} work {row['work_indicated_J']:.3f} wall {row['cycle_wall_seconds']:.1f}")
    state=row['state']; pipe=row['cells']
