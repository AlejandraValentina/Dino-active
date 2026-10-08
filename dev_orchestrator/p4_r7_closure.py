"""R7 closure: A->B* and B->A*"""
import gzip, json, math
from pathlib import Path
from dev_orchestrator.p4_hybrid import prepare, checks, periodic
from motorsim.hybrid_fast import run_cycle
from dev_orchestrator.p4_r1e import verify

# Load A/B from g1_cycles
g1_dir = Path("results/p4-r6-20260921/artifacts/g1_cycles")
A = json.loads(gzip.decompress((g1_dir/"G1-cycle29.json.gz").read_bytes()))
B = json.loads(gzip.decompress((g1_dir/"G1-cycle30.json.gz").read_bytes()))

# Hashes
import hashlib, json as js
def hash_state(state):
    return hashlib.sha256(json.dumps(state).encode()).hexdigest()[:12]

print(f"A cycle29 angle {A['end']} work {A['work_indicated_J']:.5f} state hash {hash_state(A['state'])} cells hash {hash_state(A['cells'])}")
print(f"B cycle30 angle {B['end']} work {B['work_indicated_J']:.5f} state hash {hash_state(B['state'])}")

# Prepare mesh for N250
model, mesh, _, _ = prepare('straight')
print(f"Mesh N={mesh.n} backend NUMBA_FUSED")

# Run A -> B*
# A end angle is 180+29*360? Actually cycle29 is 180+28*360 -> 10260 end, so begin for next is A['end']
begin_A = A['end']
state_A = A['state']
cells_A = A['cells']
# Need to ensure we use same mesh object? For closure we use same mesh
import time
start=time.perf_counter()
B_star = run_cycle(mesh, cells_A, state_A, begin_A, backend='NUMBA_FUSED')
elapsed=time.perf_counter()-start
print(f"A->B* wall {B_star['cycle_wall_seconds']:.2f} work {B_star['work_indicated_J']:.5f} vs B work {B['work_indicated_J']:.5f} diff {abs(B_star['work_indicated_J']-B['work_indicated_J']):.5f}")

# Compare B* vs B using periodic metrics
# B_star starts from A, so its initial mass is mass of A
B_star['initial_cylinder_mass'] = state_A[6]
# B already has correct initial mass (mass at start of cycle 30)
# Ensure B has it (it does from file)
# Define periodic_detailed locally to avoid importing p4_r6_diagnose top-level
from bisect import bisect_right
from math import fsum
def periodic_detailed(prev, cur):
    def relative(a,b,floor=0.): return abs(a-b)/max(abs(a),abs(b),floor)
    def curve(row,key,index=None):
        hs=row['history']; xs=[h['angle']-row['begin'] for h in hs]
        ys=[h[key] if index is None else h[key][index][0] for h in hs]
        if xs[0]>.5 or xs[-1]!=360.:
            raise ValueError(f"Incomplete phase support {xs[0]} {xs[-1]}")
        out=[]
        phases=[i*0.5 for i in range(1,721)]
        for phase in phases:
            j=bisect_right(xs,phase)
            if j==0 or j==len(xs):
                out.append(ys[0] if j==0 else ys[-1])
            else:
                out.append(ys[j-1]+(ys[j]-ys[j-1])*(phase-xs[j-1])/(xs[j]-xs[j-1]))
        return out, phases
    work_rel=relative(prev['work_indicated_J'],cur['work_indicated_J'],1.)
    p_cyl_prev,_=curve(prev,'p_cyl')
    p_cyl_cur,_=curve(cur,'p_cyl')
    cyl_diffs=[abs(a-b) for a,b in zip(p_cyl_prev,p_cyl_cur)]
    cyl_max_diff=max(cyl_diffs)
    cyl_denom=max(map(abs, p_cyl_prev+p_cyl_cur))
    cyl_metric=cyl_max_diff/cyl_denom if cyl_denom else 0
    sensor_metrics=[]
    sensor_details=[]
    for si in range(3):
        a,_=curve(prev,'sensors_p_u_M_Y',si)
        b,_=curve(cur,'sensors_p_u_M_Y',si)
        diffs=[abs(x-y) for x,y in zip(a,b)]
        maxd=max(diffs)
        denom=max(map(abs, a+b))
        metric=maxd/denom if denom else 0
        sensor_metrics.append(metric)
    sensor_max=max(sensor_metrics)
    port_rel=relative(prev['port_integral'][0],cur['port_integral'][0],cur['initial_cylinder_mass'])
    a_state,b_state=prev['state'],cur['state']
    inventories=[]
    for k in (0,3,6):
        inventories.extend((relative(a_state[k],b_state[k]),relative(a_state[k+1],b_state[k+1]),abs(a_state[k+2]/a_state[k]-b_state[k+2]/b_state[k]) if a_state[k] and b_state[k] else 0))
    pa=[fsum(c[j] for c in prev['cells']) for j in (0,2,3)]
    pb=[fsum(c[j] for c in cur['cells']) for j in (0,2,3)]
    inventories.extend((relative(pa[0],pb[0]),relative(pa[1],pb[1]),abs(pa[2]-pb[2])/max(pa[0],pb[0]) if max(pa[0],pb[0]) else 0))
    passed=work_rel<=0.005 and cyl_metric<=0.005 and sensor_max<=0.005 and port_rel<=0.002 and max(inventories)<=0.002
    return dict(work=work_rel, cylinder_pressure=cyl_metric, sensor_pressure=sensor_metrics, sensor_max=sensor_max, port_mass=port_rel, inventories=inventories, passed=passed)

def vector_norm(prev, cur):
    import math
    from math import fsum
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
    return dict(max_norm=max(comps), l2=math.sqrt(sum(c*c for c in comps)/len(comps)))

d_Bstar_B = periodic_detailed(B, B_star)
print(f"B* vs B: work {d_Bstar_B['work']:.5f} cyl {d_Bstar_B['cylinder_pressure']:.5f} sensor_max {d_Bstar_B['sensor_max']:.5f} port {d_Bstar_B['port_mass']:.5f} inv_max {max(d_Bstar_B['inventories']):.5f} passed {d_Bstar_B['passed']}")

# Now B -> A*
begin_B = B['end']
state_B = B['state']
cells_B = B['cells']
A_star = run_cycle(mesh, cells_B, state_B, begin_B, backend='NUMBA_FUSED')
A_star['initial_cylinder_mass'] = state_B[6]
print(f"B->A* wall {A_star['cycle_wall_seconds']:.2f} work {A_star['work_indicated_J']:.5f} vs A work {A['work_indicated_J']:.5f} diff {abs(A_star['work_indicated_J']-A['work_indicated_J']):.5f}")
d_Astar_A = periodic_detailed(A, A_star)
print(f"A* vs A: work {d_Astar_A['work']:.5f} sensor_max {d_Astar_A['sensor_max']:.5f} passed {d_Astar_A['passed']}")

# Vector norms
v_Bstar_B = vector_norm(B, B_star)
v_Astar_A = vector_norm(A, A_star)
print(f"Vector B* vs B max {v_Bstar_B['max_norm']:.6f} l2 {v_Bstar_B['l2']:.6f}")
print(f"Vector A* vs A max {v_Astar_A['max_norm']:.6f} l2 {v_Astar_A['l2']:.6f}")

# Also compare cross: A* vs B should be far (like D1)
d_Astar_B = periodic_detailed(B, A_star)
print(f"A* vs B (cross, should be far like D1): work {d_Astar_B['work']:.5f} sensor_max {d_Astar_B['sensor_max']:.5f}")

# Overall closure verdict: use thresholds 0.005/0.002
closure_pass = d_Bstar_B['passed'] and d_Astar_A['passed'] and v_Bstar_B['max_norm']<0.002 and v_Astar_A['max_norm']<0.002
print(f"CLOSURE PASS: {closure_pass}")
# Also check that cross is not passing (to confirm period-2)
cross_fail = not d_Astar_B['passed']
print(f"Cross (A* vs B) should fail (period-2): {cross_fail}")

# Save results - convert numpy types for JSON
def to_py(o):
    import numpy as np
    if isinstance(o, (np.bool_, np.integer, np.floating)):
        return o.item()
    if isinstance(o, dict):
        return {k: to_py(v) for k,v in o.items()}
    if isinstance(o, list):
        return [to_py(x) for x in o]
    return o

out=Path("results/p4-r7-20260921")
out.mkdir(parents=True, exist_ok=True)
import json
out.joinpath("closure.json").write_text(json.dumps(to_py({
    "A": {"cycle":29, "work":A['work_indicated_J'], "state_hash":hash_state(A['state']), "cells_hash":hash_state(A['cells']), "end_angle":A['end']},
    "B": {"cycle":30, "work":B['work_indicated_J'], "state_hash":hash_state(B['state']), "cells_hash":hash_state(B['cells']), "end_angle":B['end']},
    "B_star": {"work":B_star['work_indicated_J'], "wall":B_star['cycle_wall_seconds'], "detailed":d_Bstar_B, "vector":v_Bstar_B},
    "A_star": {"work":A_star['work_indicated_J'], "wall":A_star['cycle_wall_seconds'], "detailed":d_Astar_A, "vector":v_Astar_A},
    "closure_pass":closure_pass,
    "cross_fail":cross_fail,
    "backend":"NUMBA_FUSED",
    "N":250,
    "CFL":0.4
}), indent=2))
print("closure saved")
