"""Fixed-horizon N400 continuation from the durable R12 cycle54 restart."""
import argparse, gzip, json, time
from pathlib import Path
import numpy as np

def run(out):
    from motorsim.checkpoint import load_restart, save_restart, save_summary
    from motorsim.exhaust_geometry import exhaust_mesh
    from dev_orchestrator.p4_waves import segments
    from motorsim.hybrid_fast import run_cycle
    from dev_orchestrator.p4_hybrid import checks
    out=Path(out); out.mkdir(parents=True, exist_ok=True)
    src=Path("results/p4-r12-20260922/campaign_N400_50_54/jobs/G1_N400_50_54/restart_cycle54")
    meta,state,cells=load_restart(src)
    assert meta["cycle"]==54 and meta["n"]==400 and meta["backend"]=="NUMBA_FUSED" and meta["cfl"]==0.4
    mesh=exhaust_mesh(segments("straight"),0.75/400)
    rows=[]; started=time.perf_counter(); begin=float(meta["angle"])
    s=state.tolist() if isinstance(state,np.ndarray) else state
    c=cells.tolist() if isinstance(cells,np.ndarray) else cells
    for cycle in range(55,61):
        row=run_cycle(mesh,c,s,begin,backend="NUMBA_FUSED",cfl=0.4)
        row["initial_cylinder_mass"]=s[6]
        row["cycle"]=cycle
        row["checks"]=checks(row)
        save_summary(row,out/f"summary_cycle{cycle:02}.json")
        (out/f"full_cycle{cycle:02}.json.gz").write_bytes(gzip.compress(json.dumps(row,allow_nan=False).encode(),mtime=0))
        if cycle==60:
            save_restart(row["state"],row["cells"],cycle=cycle,angle=row["end"],config=dict(dx_target=.75/400,backend="NUMBA_FUSED",cfl=.4),out_dir=out/"restart_cycle60",compressed=False)
        rows.append(row); s=row["state"]; c=row["cells"]; begin=row["end"]
    json.dump({"restart54_equivalence":True,"cycles_executed":[55,56,57,58,59,60],"runtime":time.perf_counter()-started,"rows":[{"cycle":r["cycle"],"work":r["work_indicated_J"],"checks":r["checks"],"counts":r.get("counts",{})} for r in rows]},open(out/"runtime.json","w"),indent=2)

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--out",required=True);run(p.parse_args().out)
