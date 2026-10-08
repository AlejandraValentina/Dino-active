"""6-cycle continuation from A"""
import gzip, json
from pathlib import Path
from dev_orchestrator.p4_hybrid import prepare
from motorsim.hybrid_fast import run_cycle
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

g1_dir = Path("results/p4-r6-20260921/artifacts/g1_cycles")
A = json.loads(gzip.decompress((g1_dir/"G1-cycle29.json.gz").read_bytes()))
# Use A as start
model, mesh, _, _ = prepare('straight')
state = A['state']
cells = A['cells']
begin = A['end']
# Run 6 cycles
cycles=[]
prev=None
for i in range(6):
    # i=0 is cycle 30 from A, which should be B* (we already have B*), but we will run 6 new cycles
    row = run_cycle(mesh, cells, state, begin + i*360, backend='NUMBA_FUSED')
    # set initial mass for periodic
    row['initial_cylinder_mass'] = state[6]
    cycles.append(row)
    if prev:
        d1 = periodic_detailed(prev, row)
        print(f"Continuation cycle {i+1} vs {i} (from A): work {d1['work']:.5f} sensor_max {d1['sensor_max']:.5f} passed {d1['passed']}")
        # also lag2 vs prev-1
        if len(cycles) >=3:
            prev2 = cycles[-3]
            d2 = periodic_detailed(prev2, row)
            print(f"  lag2 vs {len(cycles)-2}: work {d2['work']:.5f} sensor_max {d2['sensor_max']:.5f} passed {d2['passed']}")
    else:
        print(f"Continuation cycle 1 work {row['work_indicated_J']:.5f}")
    state = row['state']
    cells = row['cells']
    prev = row

# Also check D2 maintains 3 consecutive passes
d1_list=[]
d2_list=[]
for i in range(1,len(cycles)):
    d1_list.append(periodic_detailed(cycles[i-1], cycles[i]))
for i in range(2,len(cycles)):
    d2_list.append(periodic_detailed(cycles[i-2], cycles[i]))
print("D1 passed:", [d['passed'] for d in d1_list])
print("D2 passed:", [d['passed'] for d in d2_list])
# Check 3 consecutive D2 pass
consec=0
for d in d2_list:
    if d['passed']:
        consec+=1
        if consec>=3:
            break
    else:
        consec=0
print(f"D2 3 consecutive pass: {consec>=3}")

# Save
out=Path("results/p4-r7-20260921")
out.mkdir(parents=True, exist_ok=True)
import json as js
def to_py(o):
    import numpy as np
    if isinstance(o, (np.bool_, np.integer, np.floating)):
        return o.item()
    if isinstance(o, dict):
        return {k: to_py(v) for k,v in o.items()}
    if isinstance(o, list):
        return [to_py(x) for x in o]
    return o
out.joinpath("continuation.json").write_text(js.dumps(to_py({"cycles": [{"work": c['work_indicated_J'], "angle": c['end']} for c in cycles], "d1": d1_list, "d2": d2_list}), indent=2))
print("continuation saved")
