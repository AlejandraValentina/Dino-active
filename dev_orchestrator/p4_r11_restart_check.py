import json, gzip, hashlib
from pathlib import Path
import numpy as np
from motorsim.checkpoint import save_restart, load_restart

# Check N300,N350,N400 cycle40 exact conversion
for N, path in [
    (300, "results/p4-r8-20260922/artifacts/N300-continuation-cycle40.json.gz"),
    (350, "results/p4-r8-20260922/campaign_N350_N400/jobs/G1_N350_30cycles/G1-cycle40.json.gz"),
    (400, "results/p4-r8-20260922/campaign_N350_N400/jobs/G1_N400_30cycles/G1-cycle40.json.gz"),
]:
    row = json.loads(gzip.decompress(Path(path).read_bytes()))
    state = row['state']
    cells = row['cells']
    cycle = 40
    angle = row['end']
    config = dict(dx_target=0.75/N, backend='NUMBA_FUSED', cfl=0.4, config_hash=hashlib.sha256(json.dumps(dict(N=N)).encode()).hexdigest()[:12])
    # Save to temp RESTART
    import tempfile
    tmp = Path(tempfile.mkdtemp()) / "restart"
    save_restart(state, cells, cycle=cycle, angle=angle, config=config, out_dir=tmp, compressed=False)
    meta, s2, c2 = load_restart(tmp)
    # Compare
    state_arr = np.array(state, dtype=np.float64)
    cells_arr = np.array(cells, dtype=np.float64)
    ok_state = np.allclose(state_arr, s2) and np.array_equal(state_arr, s2)
    ok_cells = np.allclose(cells_arr, c2) and np.array_equal(cells_arr, c2)
    ok_angle = meta['angle']==angle
    ok_cycle = meta['cycle']==cycle
    # Also check work state: row['work_indicated_J'] etc. should be reproducible? For restart equivalence we need to check that continuing from restart gives same next cycle as direct? That's next step, but for now check state exact
    print(f"N{N} state exact {ok_state} cells exact {ok_cells} angle {ok_angle} cycle {ok_cycle} work {row['work_indicated_J']:.5f}")
    # Cleanup
    import shutil; shutil.rmtree(tmp.parent, ignore_errors=True)

print("P4_R11_RESTART_EQUIVALENCE_PASS if all exact")
