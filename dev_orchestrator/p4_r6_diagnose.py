"""R6 diagnosis: D1, sensor_max location, lag2/3/4, X_n, 360 invariance, handoff, odd/even, G2."""
import gzip, json, math
from pathlib import Path
from bisect import bisect_right
from math import fsum
import numpy as np
from dev_orchestrator.p4_hybrid import prepare, checks
from dev_orchestrator.p2_campaign import ROOT

def periodic_detailed(prev, cur):
    # returns detailed metrics including per-sensor breakdown and exact max location
    def relative(a,b,floor=0.): return abs(a-b)/max(abs(a),abs(b),floor)
    def curve(row,key,index=None):
        hs=row['history']; xs=[h['angle']-row['begin'] for h in hs]
        ys=[h[key] if index is None else h[key][index][0] for h in hs]
        # check support
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
        return out, phases, xs, ys
    # work
    work_rel=relative(prev['work_indicated_J'],cur['work_indicated_J'],1.)
    # pressures
    # cylinder
    p_cyl_prev, phases, _, _ = curve(prev,'p_cyl')
    p_cyl_cur,_ ,_,_ = curve(cur,'p_cyl')
    cyl_diffs=[abs(a-b) for a,b in zip(p_cyl_prev,p_cyl_cur)]
    cyl_max_diff=max(cyl_diffs)
    cyl_denom=max(map(abs, p_cyl_prev+p_cyl_cur))
    cyl_metric=cyl_max_diff/cyl_denom if cyl_denom else 0
    cyl_idx=cyl_diffs.index(cyl_max_diff)
    cyl_phase=phases[cyl_idx]
    # sensors
    sensor_metrics=[]
    sensor_details=[]
    for si in range(3):
        a,_ ,_,_ = curve(prev,'sensors_p_u_M_Y',si)
        b,_ ,_,_ = curve(cur,'sensors_p_u_M_Y',si)
        # note: sensors_p_u_M_Y is list of 4-tuples per history: (p,u,M,Y) ??? Actually history sensors are list of 4-tuples (p,u,M,Y)
        # But our curve extracts h[key][index][0] -> first element p
        diffs=[abs(x-y) for x,y in zip(a,b)]
        maxd=max(diffs)
        denom=max(map(abs, a+b))
        metric=maxd/denom if denom else 0
        idx=diffs.index(maxd)
        sensor_metrics.append(metric)
        sensor_details.append(dict(sensor_index=si, phase=phases[idx], p_prev=a[idx], p_cur=b[idx], diff=maxd, denom=denom, metric=metric, angle_prev=prev['begin']+phases[idx], angle_cur=cur['begin']+phases[idx]))
    sensor_max=max(sensor_metrics)
    sensor_max_idx=sensor_metrics.index(sensor_max)
    # port mass
    port_rel=relative(prev['port_integral'][0],cur['port_integral'][0],cur['initial_cylinder_mass'])
    # inventories
    a_state, b_state = prev['state'], cur['state']
    inventories=[]
    for k in (0,3,6):
        inventories.extend((relative(a_state[k],b_state[k]),relative(a_state[k+1],b_state[k+1]),abs(a_state[k+2]/a_state[k]-b_state[k+2]/b_state[k]) if a_state[k]!=0 and b_state[k]!=0 else 0))
    pa=[fsum(c[j] for c in prev['cells']) for j in (0,2,3)]
    pb=[fsum(c[j] for c in cur['cells']) for j in (0,2,3)]
    inventories.extend((relative(pa[0],pb[0]),relative(pa[1],pb[1]),abs(pa[2]-pb[2])/max(pa[0],pb[0]) if max(pa[0],pb[0]) else 0))
    # overall passed per P4C thresholds
    passed = work_rel<=0.005 and cyl_metric<=0.005 and sensor_max<=0.005 and port_rel<=0.002 and max(inventories)<=0.002
    return dict(work=work_rel, cylinder_pressure=cyl_metric, sensor_pressure=sensor_metrics, sensor_max=sensor_max, sensor_max_sensor=sensor_max_idx, sensor_details=sensor_details, port_mass=port_rel, inventories=inventories, passed=passed, cyl_detail=dict(phase=cyl_phase, diff=cyl_max_diff, denom=cyl_denom), work_details=dict(prev=prev['work_indicated_J'], cur=cur['work_indicated_J']))

def vector_norm(prev, cur):
    # X_n as defined: I/K/C m,U,F + pipe integrals
    # For pipe, use conserved integrals: mass, momentum? Actually pipe cells are conserved per volume: (rho*vol, rho*u*vol, E*vol, rhoY*vol)
    # We'll compute pipe mass = sum cells[:,0], momentum = sum cells[:,1], energy = sum cells[:,2], species = sum cells[:,3]
    # For state 0D: I/K/C each has m,U,F? Actually state is 9 values: I m,U,F ; K m,U,F ; C m,U,F ?
    # We'll just use the 9 state values as is, plus pipe integrals
    def norm(a,b,scale):
        return abs(a-b)/max(abs(a),abs(b),scale) if max(abs(a),abs(b),scale)!=0 else 0
    # 0D inventories: state vector 9
    a=prev['state']; b=cur['state']
    # pipe
    pa=[fsum(c[j] for c in prev['cells']) for j in range(4)]
    pb=[fsum(c[j] for c in cur['cells']) for j in range(4)]
    # compute per-component relative
    comps=[]
    for i in range(9):
        comps.append(norm(a[i],b[i], 1.0 if i%3==1 else (0.001 if i%3==0 else 1.0))) # rough
    # pipe
    for j in range(4):
        comps.append(norm(pa[j],pb[j], 1e-6 if j==0 else 1.0))
    # overall norm as max or L2
    max_norm=max(comps)
    l2=math.sqrt(sum(c*c for c in comps)/len(comps))
    return dict(max_norm=max_norm, l2=l2, components=comps, pipe_a=pa, pipe_b=pb, state_a=a, state_b=b)

# Load G1 cycles
g1_dir=Path("results/p4-r6-20260921/artifacts/g1_cycles")
cycles=[]
for i in range(1,31):
    p=g1_dir/f"G1-cycle{i:02}.json.gz"
    cycles.append(json.loads(gzip.decompress(p.read_bytes())))

# D1
d1=[]
for n in range(1, len(cycles)):
    prev=cycles[n-1]; cur=cycles[n]
    detailed=periodic_detailed(prev,cur)
    d1.append(dict(n=n+1, n_prev=n, **detailed))
    # also record sensor_max location
    print(f"D1 cycle {n+1} vs {n}: work {detailed['work']:.5f} cyl {detailed['cylinder_pressure']:.5f} sensor_max {detailed['sensor_max']:.5f} (sensor {detailed['sensor_max_sensor']} phase {detailed['sensor_details'][detailed['sensor_max_sensor']]['phase']:.1f} p_prev {detailed['sensor_details'][detailed['sensor_max_sensor']]['p_prev']:.1f} p_cur {detailed['sensor_details'][detailed['sensor_max_sensor']]['p_cur']:.1f}) port {detailed['port_mass']:.5f} inv_max {max(detailed['inventories']):.5f} passed {detailed['passed']}")

# D2 lag2
d2=[]
for n in range(2, len(cycles)):
    prev=cycles[n-2]; cur=cycles[n]
    detailed=periodic_detailed(prev,cur)
    d2.append(dict(n=n+1, lag=2, prev=n-1, **detailed))
    print(f"D2 cycle {n+1} vs {n-1}: work {detailed['work']:.5f} sensor_max {detailed['sensor_max']:.5f} passed {detailed['passed']}")

# D3, D4
d3=[]
for n in range(3, len(cycles)):
    prev=cycles[n-3]; cur=cycles[n]
    detailed=periodic_detailed(prev,cur)
    d3.append(dict(n=n+1, lag=3, **detailed))
d4=[]
for n in range(4, len(cycles)):
    prev=cycles[n-4]; cur=cycles[n]
    detailed=periodic_detailed(prev,cur)
    d4.append(dict(n=n+1, lag=4, **detailed))

# vector norms
vec_lag1=[]
vec_lag2=[]
for n in range(1, len(cycles)):
    v=vector_norm(cycles[n-1], cycles[n])
    vec_lag1.append(dict(n=n+1, **v))
for n in range(2, len(cycles)):
    v=vector_norm(cycles[n-2], cycles[n])
    vec_lag2.append(dict(n=n+1, **v))

for i in range(22,30):
    print(f"vec lag1 cycle {i+1} max {vec_lag1[i-1]['max_norm']:.5f} l2 {vec_lag1[i-1]['l2']:.5f} lag2 max {vec_lag2[i-2]['max_norm']:.5f} l2 {vec_lag2[i-2]['l2']:.5f}")

# odd/even work
works=[c['work_indicated_J'] for c in cycles]
odd=works[0::2]  # cycles 1,3,5...
even=works[1::2]
print(f"odd works {odd[12:15]} even {even[12:15]}")
# compute differences within subseq
for seq, name in [(odd,"odd"),(even,"even")]:
    diffs=[abs(seq[i]-seq[i-1])/max(abs(seq[i]),abs(seq[i-1]),1) for i in range(1,len(seq))]
    print(f"{name} diffs last 5 {diffs[-5:]} max {max(diffs):.5f}")

# inventories odd/even
# For brevity, just check pipe mass odd/even
for j, name in [(0,"pipe_mass"),(2,"pipe_energy")]:
    vals=[fsum(c['cells'][k][j] for k in range(len(c['cells']))) for c in cycles]  # careful
# Instead use pipe integrals already computed in vector
pipe_masses=[vec_lag1[i]['pipe_a'][0] if i==0 else None]  # not needed

# Save detailed
out=Path("results/p4-r6-20260921/artifacts/diagnosis.json")
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(dict(d1=d1, d2=d2, d3=d3, d4=d4, vec_lag1=vec_lag1, vec_lag2=vec_lag2, works=works, odd=odd, even=even), indent=2))
print("diagnosis saved")
