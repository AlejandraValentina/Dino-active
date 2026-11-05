"""Stage-2 engineering studies (S2 intake length x rpm, S3 intake phasing x rpm, S4 sensitivities).
Hypotheses are stated BEFORE running (see docs/dino4t/stage2_assessment.md):
  H2  rpm of maximum eta_v scales approximately as 1/L_runner (wave transit time ~ L/a)
  H3  the best intake phasing moves toward later closing (retard) as rpm rises
  H4  elasticities: eta_v most sensitive to intake Cd/lift and runner length; IMEP to eta_v-driving inputs
These are consistency checks of wave timing and trends, not validation."""
import copy, json, sys
from pathlib import Path
from motorsim.dino4t import config, studies

OUT = Path(sys.argv[1]); OUT.mkdir(parents=True, exist_ok=True)
cfg = config.load(config.EXAMPLE_PATH)
base = {"numerics": {"dx_mm": 20.0}}
which = sys.argv[2:] or ["S2", "S3", "S4"]

def show(r): print(json.dumps({k: r[k] for k in ("overrides", "status", "cycles", "imep_net_bar", "volumetric_efficiency_intake_valve")}, default=float), flush=True)

if "S2" in which:
    rpms = [3500.0, 4500.0, 5500.0, 6500.0, 7500.0, 8500.0, 9500.0]
    res = {}
    for scale in (0.7, 1.0, 1.4):
        c = copy.deepcopy(cfg)
        for s in c["intake_duct"]["segments"]:
            s["length_mm"] *= scale
        rows = studies.sweep(c, [{"operating_point.rpm": r} for r in rpms], base_overrides=base, out_dir=OUT / f"S2_L{scale}", progress=show)
        res[scale] = [(r["overrides"]["operating_point.rpm"], r["volumetric_efficiency_intake_valve"], r["imep_net_bar"]) for r in rows]
    json.dump(res, open(OUT / "S2_summary.json", "w"), indent=1)
if "S3" in which:
    res = {}
    for rpm in (4000.0, 8000.0):
        pts = [{"operating_point.rpm": rpm, "intake_valve.lift.open_deg": 350.0 + d, "intake_valve.lift.close_deg": -130.0 + d} for d in (-20.0, -10.0, 0.0, 10.0, 20.0)]
        rows = studies.sweep(cfg, pts, base_overrides=base, out_dir=OUT / f"S3_rpm{int(rpm)}", progress=show, continuation=False)
        res[rpm] = [(r["overrides"]["intake_valve.lift.close_deg"], r["volumetric_efficiency_intake_valve"], r["imep_net_bar"]) for r in rows]
    json.dump(res, open(OUT / "S3_summary.json", "w"), indent=1)
if "S4" in which:
    names = ["intake_Cd_forward", "intake_Cd_reverse", "exhaust_Cd_forward", "intake_max_lift", "exhaust_max_lift",
             "intake_timing_shift_deg_per_pct", "exhaust_timing_shift_deg_per_pct", "intake_runner_length", "exhaust_pipe_length",
             "woschni_multiplier", "friction_A", "wiebe_duration", "intake_air_temperature"]
    studies.sensitivity(cfg, parameters=names, rel_step=0.05, base_overrides=base, out_dir=OUT / "S4", progress=lambda n, e: print("sens", n, flush=True))
