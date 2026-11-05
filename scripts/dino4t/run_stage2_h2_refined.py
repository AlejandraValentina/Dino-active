"""S2b: refined test of H2 (closure of stage 2).  Usage: run_stage2_h2_refined.py OUT SCALE
Why: the original S2 used a 1000 rpm grid; the 'peak' was a 3-point parabola on that grid, so the
quoted shifts (+3 %, -7 %) were below the grid resolution and H2 was not testable in magnitude.
Pre-declared (before running) H2b: the position of the lobe of eta_v(rpm) is ordered
L x0.7 > L x1.0 > L x1.4 and consecutive lobes differ by at least one grid step (500 rpm) only if
the model resolves it; magnitudes are NOT asserted.  A dx control (L x1.0, dx 20 vs 10 mm) bounds
the numerical noise that comes from the cell count ceil(L/dx)."""
import copy, json, sys
from pathlib import Path
from motorsim.dino4t import config, studies

out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
scale = float(sys.argv[2]); dx = float(sys.argv[3]) if len(sys.argv) > 3 else 20.0
cfg = config.load(config.EXAMPLE_PATH)
for s in cfg["intake_duct"]["segments"]:
    s["length_mm"] *= scale
rpms = [float(r) for r in range(3000, 9001, 500)]
rows = studies.sweep(cfg, [{"operating_point.rpm": r} for r in rpms], base_overrides={"numerics": {"dx_mm": dx}},
                     out_dir=out / f"L{scale}_dx{dx}",
                     progress=lambda r: print(json.dumps({k: r[k] for k in ("overrides", "status", "cycles", "volumetric_efficiency_intake_valve")}, default=float), flush=True))
json.dump([(r["overrides"]["operating_point.rpm"], r["status"], r["periodicity"], r["volumetric_efficiency_intake_valve"], r["imep_net_bar"]) for r in rows],
          open(out / f"S2b_L{scale}_dx{dx}.json", "w"), indent=1)
