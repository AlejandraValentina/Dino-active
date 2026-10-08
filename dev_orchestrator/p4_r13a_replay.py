"""Replay R12 N400 50->54 solely to recover cycle54 angular history."""
import argparse, gzip, json, time
from pathlib import Path
import numpy as np

def run(out):
    from motorsim.checkpoint import load_restart
    from motorsim.exhaust_geometry import exhaust_mesh
    from dev_orchestrator.p4_waves import segments
    from motorsim.hybrid_fast import run_cycle
    from dev_orchestrator.p4_hybrid import checks
    out=Path(out); out.mkdir(parents=True,exist_ok=True)
    src=Path("results/p4-r11-20260922/campaign_stageA/jobs/G1_N400_A/restart_cycle50")
    meta,s0,c0=load_restart(src)
    assert meta["cycle"]==50 and meta["n"]==400 and meta["backend"]=="NUMBA_FUSED" and meta["cfl"]==0.4
    mesh=exhaust_mesh(segments("straight"),0.75/400)
    s=s0.tolist() if isinstance(s0,np.ndarray) else s0; c=c0.tolist() if isinstance(c0,np.ndarray) else c0; begin=float(meta["angle"])
    for cycle in range(51,55):
        row=run_cycle(mesh,c,s,begin,backend="NUMBA_FUSED",cfl=0.4)
        row["initial_cylinder_mass"]=s[6]; row["cycle"]=cycle; row["checks"]=checks(row)
        (out/f"full_cycle{cycle:02}.json.gz").write_bytes(gzip.compress(json.dumps(row,allow_nan=False).encode(),mtime=0))
        if cycle==54: final=row
        s=row["state"];c=row["cells"];begin=row["end"]
    r12=Path("results/p4-r12-20260922/campaign_N400_50_54/jobs/G1_N400_50_54")
    m54=json.loads((r12/"restart_cycle54/metadata.json").read_text())
    om,os,oc=load_restart(r12/"restart_cycle54")
    exact_state=np.array(final["state"]) .tobytes()==np.array(os).tobytes()
    exact_cells=np.array(final["cells"]) .tobytes()==np.array(oc).tobytes()
    eq={"state":exact_state,"cells":exact_cells,"angle":float(final["end"])==float(m54["angle"]),"cycle":int(final["cycle"])==int(m54["cycle"]),"dtype":"float64","exact":bool(exact_state and exact_cells and float(final["end"])==float(m54["angle"]))}
    (out/"cycle54_replay_equivalence.json").write_text(json.dumps(eq,indent=2))
    return eq
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--out",required=True);print(run(p.parse_args().out))
