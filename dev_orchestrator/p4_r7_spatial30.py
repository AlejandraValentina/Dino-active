import gzip, json
from pathlib import Path
from motorsim.exhaust_geometry import exhaust_mesh
from dev_orchestrator.p4_waves import segments
from motorsim.hybrid_exhaust import LegacySources
from motorsim.gas1d.eos import IdealGas
from motorsim.hybrid_fast import run_cycle

def prepare_n(label, dx):
    model=LegacySources()
    mesh=exhaust_mesh(segments(label), dx)
    p,T,Y=model.case.initial_pty[3]
    eos=IdealGas()
    U=eos.conservative((p/(eos.R*T),0.,p,Y))
    return model,mesh,[tuple(v*u for u in U) for v in mesh.volumes],model.initial_state()[:9]

for N, dx in [(200,0.00375)]:
    print(f"=== N{N} 30 cycles ===")
    model,mesh,pipe,state=prepare_n('straight', dx)
    print(f"N={mesh.n}")
    s=state
    c=pipe
    begin=180
    for i in range(30):
        row=run_cycle(mesh, c, s, begin + i*360, backend='NUMBA_FUSED')
        row['initial_cylinder_mass']=s[6]
        print(f" cycle {i+1} work {row['work_indicated_J']:.5f} wall {row['cycle_wall_seconds']:.1f}")
        s=row['state']; c=row['cells']
        # save last two for comparison
        if i>=28:
            import gzip, json
            p=Path(f"results/p4-r7-20260921/spatial_N{N}_cycle{i+1}.json.gz")
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(gzip.compress(json.dumps(row).encode()))
    print(f"done N{N}")
