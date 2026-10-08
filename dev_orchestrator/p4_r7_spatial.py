"""Spatial sensitivity N200/N300 from canonical initial conditions"""
import gzip, json
from pathlib import Path
from motorsim.exhaust_geometry import exhaust_mesh
from dev_orchestrator.p4_waves import segments
from motorsim.hybrid_exhaust import LegacySources
from motorsim.gas1d.eos import IdealGas
from motorsim.hybrid_fast import run_cycle
from bisect import bisect_right
from math import fsum

def periodic_detailed(prev, cur):
    def relative(a,b,floor=0.): return abs(a-b)/max(abs(a),abs(b),floor)
    def curve(row,key,index=None):
        hs=row['history']; xs=[h['angle']-row['begin'] for h in hs]
        ys=[h[key] if index is None else h[key][index][0] for h in hs]
        out=[]
        phases=[i*0.5 for i in range(1,721)]
        for phase in phases:
            j=bisect_right(xs,phase)
            if j==0 or j==len(xs):
                out.append(ys[0] if j==0 else ys[-1])
            else:
                out.append(ys[j-1]+(ys[j]-ys[j-1])*(phase-xs[j-1])/(xs[j]-xs[j-1]))
        return out
    work_rel=relative(prev['work_indicated_J'],cur['work_indicated_J'],1.)
    p1=curve(prev,'p_cyl')
    p2=curve(cur,'p_cyl')
    cyl=max(abs(a-b) for a,b in zip(p1,p2))/max(map(abs,p1+p2))
    sens=[]
    for si in range(3):
        a=curve(prev,'sensors_p_u_M_Y',si)
        b=curve(cur,'sensors_p_u_M_Y',si)
        sens.append(max(abs(x-y) for x,y in zip(a,b))/max(map(abs,a+b)))
    sensor_max=max(sens)
    port=relative(prev['port_integral'][0],cur['port_integral'][0],cur['initial_cylinder_mass'])
    return dict(work=work_rel, sensor_max=sensor_max, cyl=cyl)

def prepare_n(label, dx_target):
    model=LegacySources()
    mesh=exhaust_mesh(segments(label), dx_target)
    p,T,Y=model.case.initial_pty[3]
    eos=IdealGas()
    U=eos.conservative((p/(eos.R*T),0.,p,Y))
    return model,mesh,[tuple(v*u for u in U) for v in mesh.volumes],model.initial_state()[:9]

for N, dx in [(200,0.00375),(300,0.0025)]:
    print(f"=== N{N} dx {dx} ===")
    model,mesh,pipe,state=prepare_n('straight', dx)
    print(f"Mesh N={mesh.n}")
    # Run 10 cycles (to stay within budget)
    s=state
    c=pipe
    begin=180
    cycles=[]
    for i in range(10):
        row=run_cycle(mesh, c, s, begin + i*360, backend='NUMBA_FUSED')
        row['initial_cylinder_mass']=s[6]
        print(f" cycle {i+1} work {row['work_indicated_J']:.5f} wall {row['cycle_wall_seconds']:.1f}")
        cycles.append(row)
        s=row['state']; c=row['cells']
    # Check D1 for last 5
    for i in range(5,10):
        if i>=1:
            d=periodic_detailed(cycles[i-1], cycles[i])
            print(f"  D1 {i+1} vs {i}: work {d['work']:.5f} sensor {d['sensor_max']:.5f}")
    # D2
    for i in range(7,10):
        if i>=2:
            d=periodic_detailed(cycles[i-2], cycles[i])
            print(f"  D2 {i+1} vs {i-1}: work {d['work']:.5f} sensor {d['sensor_max']:.5f}")
    # Odd/even work
    works=[c['work_indicated_J'] for c in cycles]
    odd=works[0::2]
    even=works[1::2]
    print(f" odd last 3 {odd[-3:]} even last 3 {even[-3:]}")
    # Save
    import json, pathlib
    out=Path(f"results/p4-r7-20260921/spatial_N{N}.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"N":N, "dx":dx, "works":works, "cycles":len(cycles)}, indent=2))
    print(f"saved N{N}")
