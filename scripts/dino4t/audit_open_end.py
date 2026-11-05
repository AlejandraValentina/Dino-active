"""Stage-2 audit E1: steady subsonic flow through a constant-area pipe that
discharges to ambient through an ideal open end (A_eff = A, Cd = 1).

Exact reference (calorically perfect gas, frictionless): the inlet is an
isentropic acceleration from the stagnation reservoir and the exit static
pressure equals the ambient pressure, so
    M^2 = 2/(g-1) [ (p0/p_amb)^((g-1)/g) - 1 ],  mdot = rho w A
with rho, w evaluated at (p_amb, T0/(1+(g-1)/2 M^2)).
A restriction boundary that treats the duct static pressure as the
upstream stagnation pressure predicts p_exit = p_amb + O(M^2) and an mdot deficit.
"""
import json
import math
import sys

import numpy as np

from motorsim.dino4t import verification as v
from motorsim.dino4t.restriction import VolumeGas


def run(p0_over_pamb, n=40, t_end=0.12, gamma=1.4, R=287.0):
    mix = v.air_cp_mixture(gamma, R)
    duct = v._uniform_duct(mix, n, length=0.5, diameter=0.04)
    A = float(duct.area[0])
    p_amb, T0 = 1e5, 300.0
    inlet = VolumeGas.from_mixture(mix, p0_over_pamb * p_amb, T0, np.ones(1), 0.0)
    outlet = VolumeGas.from_mixture(mix, p_amb, T0, np.ones(1), 0.0)
    q = duct.uniform(p_amb * (1 + 0.5 * (p0_over_pamb - 1)), T0, np.ones(1))
    bench = v.DuctBench(duct, (inlet, A, A), (outlet, A, A), cfl=0.8)
    out = bench.run(q, t_end, probe=lambda qq: 0.0)
    tr = np.array([(r[0], r[2], r[3]) for r in out["trace"]])
    late = tr[:, 0] > 0.8 * t_end
    m_num = float(-tr[late, 2].mean())
    w = duct.primitive(out["q"])
    p_end = float(w["p"][-1])
    M2 = 2 / (gamma - 1) * (p0_over_pamb ** ((gamma - 1) / gamma) - 1)
    T = T0 / (1 + (gamma - 1) / 2 * M2)
    m_exact = (p_amb / (R * T)) * math.sqrt(M2 * gamma * R * T) * A
    return dict(p0_over_pamb=p0_over_pamb, mach_exact=math.sqrt(M2), mdot_exact=m_exact, mdot_model=m_num,
                mdot_relative_error=(m_num - m_exact) / m_exact, last_cell_pressure_over_ambient=p_end / p_amb,
                dynamic_head_over_p=0.5 * gamma * M2)


if __name__ == "__main__":
    rows = [run(r) for r in (1.005, 1.02, 1.05, 1.1, 1.2, 1.4)]
    for r in rows:
        print(f"p0/pa={r['p0_over_pamb']:.3f}  M={r['mach_exact']:.3f}  mdot err={r['mdot_relative_error']*100:+.2f}%  "
              f"p_exit/p_amb-1={(r['last_cell_pressure_over_ambient']-1)*100:+.2f}%  (dyn head {r['dynamic_head_over_p']*100:.2f}%)")
    if len(sys.argv) > 1:
        json.dump(rows, open(sys.argv[1], "w"), indent=2)
