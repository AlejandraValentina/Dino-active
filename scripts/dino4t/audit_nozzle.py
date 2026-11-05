"""Stage-2 audit E2: steady subsonic isentropic flow in a converging-diverging duct
(area source term WITH flow).  Exact: area-Mach relation of a calorically perfect gas."""
import math, sys, numpy as np
from scipy.optimize import brentq
from motorsim.dino4t import verification as v
from motorsim.dino4t.duct import Duct
from motorsim.dino4t.restriction import VolumeGas

G, R = 1.4, 287.0

def area_ratio(M): return (1 / M) * (2 / (G + 1) * (1 + (G - 1) / 2 * M * M)) ** ((G + 1) / (2 * (G - 1)))

def run(n, mach_throat=0.5, t_end=0.08, second_order=True, limiter="minmod"):
    mix = v.air_cp_mixture(G, R)
    segs = [{"length": 150, "start_diameter": 60, "end_diameter": 40}, {"length": 150, "start_diameter": 40, "end_diameter": 60}]
    duct = Duct("noz", mix, segs, 0.3 / n, second_order=second_order, limiter=limiter)
    A = duct.area; At = A.min()
    Astar = At / area_ratio(mach_throat)
    p0, T0 = 1.5e5, 300.0
    iso = lambda M: (1 + (G - 1) / 2 * M * M)
    def mach_at(a):  # subsonic root
        return brentq(lambda M: area_ratio(M) - a / Astar, 1e-4, 1.0)
    Mc = np.array([mach_at(a) for a in 0.5 * (A[:-1] + A[1:])])  # cell-mean area approximation
    # exact at cell centers: use area at centers (linear interpolation of faces)
    Ac = np.interp(duct.centers, duct.faces, A)
    Mc = np.array([mach_at(a) for a in Ac])
    pex = p0 * iso(Mc) ** (-G / (G - 1))
    Mexit = mach_at(A[-1])
    p_b = p0 * iso(Mexit) ** (-G / (G - 1))
    inlet = VolumeGas.from_mixture(mix, p0, T0, np.ones(1), 0.0)
    outlet = VolumeGas.from_mixture(mix, p_b, T0, np.ones(1), 0.0)
    q = duct.uniform(0.5 * (p0 + p_b), T0, np.ones(1))
    out = v.DuctBench(duct, (inlet, A[0], A[0]), (outlet, A[-1], A[-1]), cfl=0.8).run(q, t_end)
    w = duct.primitive(out["q"])
    err = np.sum(np.abs(w["p"] - pex) * duct.dx) / (np.sum(pex * duct.dx))
    return err, float(np.max(np.abs(w["p"] - pex) / pex)), mach_throat

if __name__ == "__main__":
    for so, lim in ((True, "minmod"), (True, "van_leer"), (False, "minmod")):
        errs = []
        for n in (30, 60, 120):
            e, einf, _ = run(n, second_order=so, limiter=lim); errs.append(e)
        print(so, lim, ["%.2e" % e for e in errs], [round(math.log2(a / b), 2) for a, b in zip(errs, errs[1:])])
