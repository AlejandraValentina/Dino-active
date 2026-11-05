"""Stage-2 audit E3: is the sub-2 order of TVD limiters caused by extremum clipping?
Same acoustic problem, two initial profiles: a Gaussian pulse (has extrema) and a smooth
monotone step (no extremum).  Self-convergence order (Richardson, finest pair)."""
import math, sys, numpy as np
from motorsim.dino4t import verification as v
from motorsim.dino4t.thermo import Mixture, dry_air

def order(profile, limiter, ns=(100, 200, 400, 800)):
    mix = Mixture.standard(); air = dry_air(mix); sols = []
    for n in ns:
        so = limiter != "first_order"
        d = v._uniform_duct(mix, n, second_order=so, limiter=limiter if so else "minmod")
        x = d.centers
        shape = np.exp(-((x - 0.5) / 0.05) ** 2) if profile == "pulse" else 0.5 * (1 + np.tanh((x - 0.5) / 0.05))
        p = 1e5 * (1 + 0.01 * shape); T = 300.0 * (p / 1e5) ** (0.4 / 1.4)
        q = np.vstack([d.uniform(pi, Ti, air)[0] for pi, Ti in zip(p, T)])
        out = v.DuctBench(d, v._closed(), v._closed(), cfl=0.6).run(q, 8e-4)
        sols.append((d, d.primitive(out["q"])["p"]))
    errs = []
    for (dc, pc), (df, pf) in zip(sols, sols[1:]):
        r = (pf[0::2] * df.volume[0::2] + pf[1::2] * df.volume[1::2]) / (df.volume[0::2] + df.volume[1::2])
        errs.append(float(np.sum(np.abs(pc - r) * dc.dx)))
    return [round(math.log2(a / b), 2) for a, b in zip(errs, errs[1:])]

if __name__ == "__main__":
    for prof in ("pulse", "monotone_step"):
        for lim in ("first_order", "minmod", "van_leer", "mc", "unlimited_central"):
            print(f"{prof:14s} {lim:18s} orders {order(prof, lim)}", flush=True)
