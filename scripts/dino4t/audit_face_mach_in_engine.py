"""Records the largest boundary-face Mach number per branch reached inside full-engine runs."""
import json, sys
from motorsim.dino4t import config, engine as eng, restriction
from motorsim.dino4t.runner import run_operating_point
stats = {}
orig = eng.restriction_flux
def spy(*a, **k):
    r = orig(*a, **k)
    s = stats.setdefault(r.branch, {"n": 0, "max_mach": 0.0, "n_over_1": 0})
    s["n"] += 1; s["max_mach"] = float(max(s["max_mach"], r.mach_face)); s["n_over_1"] += int(r.mach_face > 1 + 1e-9)
    return r
eng.restriction_flux = spy
out = {}
for rpm in (4000.0, 6000.0, 8000.0):
    stats.clear()
    run_operating_point(config.load(config.EXAMPLE_PATH), max_cycles=3, overrides={"operating_point": {"rpm": rpm}, "numerics": {"dx_mm": 20.0}})
    out[str(rpm)] = json.loads(json.dumps(stats))
    print(rpm, stats, flush=True)
json.dump(out, open(sys.argv[1], "w"), indent=1)
