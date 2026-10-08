"""First-kernel experiment; tolerances declared before measurement."""
import argparse,json,time,platform,sys,gzip
from pathlib import Path
import numpy as np
import numba,llvmlite
from motorsim import exhaust_batch as ref,exhaust_numba as compiled
from motorsim.gas1d.eos import IdealGas
from .p2_campaign import write

def run(folder):
    art=Path(folder)/'artifacts';art.mkdir(parents=True,exist_ok=True)
    eos=IdealGas();rng=np.random.default_rng(413)
    left=np.column_stack((rng.uniform(.1,5,249),rng.uniform(-500,500,249),rng.uniform(1e4,1e6,249),rng.uniform(0,1,249)))
    right=left[::-1].copy();left[0]=[1,-2000,10000,.2];right[0]=[1,2000,10000,.8]
    start=time.perf_counter();actual=compiled.hllc(left,right,eos);jit=time.perf_counter()-start
    expected=ref.hllc(left,right,eos)
    equivalent=all(np.allclose(a,b,rtol=1e-10,atol=1e-13,equal_nan=True) for a,b in zip(actual[:2],expected[:2])) and actual[2:]==expected[2:]
    branch_equivalence=equivalent
    old=json.loads(gzip.decompress(Path('results/p4-r2-20260921/p4c/artifacts/G1-cycle01.json.gz').read_bytes()))
    shot=min(old['segments'][2]['result']['snapshots'],key=lambda x:abs(x['angle']-480))
    from .p4_hybrid import prepare
    from motorsim.gas1d.boundary import Boundary
    _,mesh,_,_=prepare('straight')
    lo,hi,_=ref.Kernel(mesh,eos).reconstruct(np.array(shot['primitive']),(Boundary('outflow'),Boundary('nonreflecting',state=(100000/(287*500),0.,100000.,0.))))
    left=hi[:-1];right=lo[1:]
    actual=compiled.hllc(left,right,eos);expected=ref.hllc(left,right,eos)
    equivalent=branch_equivalence and all(np.allclose(a,b,rtol=1e-10,atol=1e-13,equal_nan=True) for a,b in zip(actual[:2],expected[:2])) and actual[2:]==expected[2:]
    timings={}
    for name,fn in [('NUMPY_REFERENCE',ref.hllc),('NUMBA_EXPERIMENTAL',compiled.hllc)]:
        start=time.perf_counter()
        for _ in range(2000):fn(left,right,eos)
        timings[name]=time.perf_counter()-start
    ratio=timings['NUMPY_REFERENCE']/timings['NUMBA_EXPERIMENTAL']
    data=dict(python=sys.version,numpy=np.__version__,numba=numba.__version__,llvmlite=llvmlite.__version__,platform=platform.platform(),first_call_seconds=jit,equivalence=bool(equivalent),timings=timings,speedup=ratio,fixture="G1 reopening nearest 480 degrees, frozen R2 snapshot",branch_equivalence=bool(branch_equivalence),faces_per_call=249,repeats=2000,targetoptions=compiled.faces.targetoptions)
    write(art/'micro.json',data)
    write(art/'result.json',dict(checks=[dict(id='micro_equivalence',kind='numerical',passed=bool(equivalent and ratio>1),reason='Predeclared tolerances, same exceptional branches')],metrics={},scientific_change_required=False))
    print(json.dumps(data),flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run-dir',required=True);run(p.parse_args().run_dir)
