import gzip, json
from pathlib import Path
from dev_orchestrator.p4_hybrid import prepare
from motorsim.hybrid_fast import run_cycle

# Load checkpoint 28
g1_dir=Path("results/p4-r6-20260921/artifacts/g1_cycles")
cycle28=json.loads(gzip.decompress((g1_dir/"G1-cycle28.json.gz").read_bytes()))
cycle29=json.loads(gzip.decompress((g1_dir/"G1-cycle29.json.gz").read_bytes()))

# Prepare state from cycle28 final
# cycle28 final state and cells are at end of cycle28 (angle 180+28*360? Actually cycle numbers)
# For restart, we need to run cycle 29 from checkpoint 28's final state
# The checkpoint's state is at angle 180+28*360? Wait cycle 1 is 180->540, cycle 28 is 180+27*360 -> 9900? Actually 180+27*360 = 9900, end is 10260
# So next cycle 29 starts at 10260
# Use HybridSystem with begin = 180+28*360 = 10260
from dev_orchestrator.p4_hybrid import prepare as prep
model, mesh, pipe, state0 = prep('straight')
# Instead of using state0, use checkpoint
# Load checkpoint: we have cycle28's final state/cells
state28=cycle28['state']
cells28=cycle28['cells']
# in our generation, cycle29 was run from state28/cells28, so rerunning should reproduce cycle29 exactly
# Run one cycle from that checkpoint
row=run_cycle(mesh, cells28, state28, 180+28*360, backend='NUMBA_FUSED')
# Compare to cycle29
import math
def compare(a,b):
    if isinstance(a,float):
        return abs(a-b) <= 1e-13+1e-10*abs(a)
    if isinstance(a,list):
        return len(a)==len(b) and all(compare(x,y) for x,y in zip(a,b))
    if isinstance(a,dict):
        return a.keys()==b.keys() and all(compare(a[k],b[k]) for k in a)
    return a==b

# Compare key fields
keys=['state','cells','work_indicated_J','port_integral','history']
ok=True
for k in keys:
    # for history etc, compare via json dumps
    import json as js
    a=js.loads(js.dumps(row[k])); b=js.loads(js.dumps(cycle29[k]))
    # for floats, use tolerance
    # simple check: compare via periodic equivalence? Use exact
    if a==b:
        print(f"{k} exact")
    else:
        # check with tolerance for floats
        # Use deep compare with tolerance for floats inside
        def deep_eq(x,y):
            if isinstance(x,float) and isinstance(y,float):
                return abs(x-y) <= 1e-12+1e-10*abs(x)
            if isinstance(x,list) and isinstance(y,list):
                return len(x)==len(y) and all(deep_eq(a,b) for a,b in zip(x,y))
            if isinstance(x,dict) and isinstance(y,dict):
                return x.keys()==y.keys() and all(deep_eq(x[k],y[k]) for k in x)
            return x==y
        eq=deep_eq(a,b)
        print(f"{k} deep_eq {eq}")
        ok=ok and eq

print(f"restart determinism {'PASS' if ok else 'FAIL'}")
# Also compare via equivalence function
from dev_orchestrator.p4_r3_benchmark import equivalent
# Need baseline? Use cycle29 as baseline, row as test
# Build minimal dict for equivalence: need to wrap as run_cycle output vs saved?
# Instead, just check that the rerun's history matches saved cycle29's history exactly with tolerance
# Use periodic equivalence? For now, just check work etc
print(f"work original {cycle29['work_indicated_J']} rerun {row['work_indicated_J']} diff {abs(cycle29['work_indicated_J']-row['work_indicated_J'])}")
