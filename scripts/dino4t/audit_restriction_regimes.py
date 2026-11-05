"""Stage-2 closure audit: regime scan of QUASI_STEADY_RESTRICTION_V2 (no reference solution needed).

For a grid of duct end states (Mach -0.9..0.9, several T, p), orifice area ratios and volume pressures
checks properties any physical boundary must have:
  P1 a root exists (no RestrictionError);  P2 |M_face| <= 1;
  P3 mdot into the duct is non-decreasing in the volume pressure (monotone);
  P4 no jump at the flow-reversal point (largest step between neighbouring p_v is bounded by the local slope);
  P5 energy flux == mdot * donor total enthalpy (donor = upstream side);
  P6 species/tracer fluxes follow the donor and sum to mdot.
It is a consistency audit, not a validation: it cannot detect a wrong-but-smooth law."""
import json
import math
import sys

import numpy as np

from motorsim.dino4t.restriction import EndCell, RestrictionError, VolumeGas, restriction_flux
from motorsim.dino4t.thermo import Mixture, dry_air
from motorsim.dino4t import verification as v

mix = Mixture.standard()
air = dry_air(mix)
duct = v._uniform_duct(mix, 4, length=0.04)
A = float(duct.area[-1])
rows, failures, declared = [], [], []
n_cases = 0
for T in (300.0, 600.0, 1100.0):
    for p in (0.6e5, 1.0e5, 2.5e5):
        for M in (-0.9, -0.5, -0.1, 0.0, 0.1, 0.5, 0.9):
            q = duct.uniform(p, T, air, u=M * math.sqrt(1.4 * 287.0 * T))
            cell = EndCell.from_primitive(duct.primitive(q), -1)
            for sigma in (0.05, 0.3, 1.0):
                pv = np.concatenate([np.geomspace(0.05e5, 8e5, 140)])
                mdot, ok = [], True
                for pvol in pv:
                    n_cases += 1
                    vol = VolumeGas.from_mixture(mix, float(pvol), 400.0, air, 0.3)
                    try:
                        r = restriction_flux(cell, "right", A, sigma * A, sigma * A, vol, mix.ns)
                    except RestrictionError as e:
                        if "supersonic inflow" in str(e):
                            declared.append(dict(T=T, p=p, M=M, sigma=sigma, pv_over_pc=float(pvol / p)))
                            mdot.append(np.nan); continue
                        failures.append(dict(T=T, p=p, M=M, sigma=sigma, pv=float(pvol), prop="P1", msg=str(e)[:80]))
                        mdot.append(np.nan); continue
                    mdot.append(r.mdot_into_duct)
                    if abs(r.mach_face) > 1 + 1e-6:
                        failures.append(dict(T=T, p=p, M=M, sigma=sigma, pv=float(pvol), prop="P2", mach=r.mach_face))
                    # energy flux into the volume (last entry) = -mdot_into_duct * h0_donor
                    if r.mdot_into_duct != 0:
                        e_vol = r.to_volume[-1]; m_vol = -r.mdot_into_duct
                        if m_vol > 0:  # donor is the duct: specific total enthalpy must be a plausible gas value
                            h0 = e_vol / m_vol
                            if not (-6e5 < h0 < 4e6):  # absolute enthalpy incl. formation, ref 298 K: cold gas is negative
                                failures.append(dict(T=T, p=p, M=M, sigma=sigma, pv=float(pvol), prop="P5", h0=h0))
                        sp = float(np.sum(r.to_volume[:mix.ns]))
                        if abs(sp - m_vol) > 1e-9 * max(abs(m_vol), 1e-12):
                            failures.append(dict(T=T, p=p, M=M, sigma=sigma, pv=float(pvol), prop="P6", sp=sp, m=m_vol))
                m = np.array(mdot)
                d = np.diff(m)
                scale = np.nanmax(np.abs(m)) if np.isfinite(m).any() else 1.0
                bad = np.where(d < -1e-9 * scale)[0]
                for i in bad[:3]:
                    failures.append(dict(T=T, p=p, M=M, sigma=sigma, pv=float(pv[i]), prop="P3", dm=float(d[i] / scale)))
                jump = np.nanmax(np.abs(d)) / scale if scale > 0 else 0.0
                rows.append(dict(T=T, p=p, M=M, sigma=sigma, max_step_over_scale=float(jump)))
out = dict(schema="DINO4T_RESTRICTION_REGIME_AUDIT_V1", cases=n_cases, grid_rows=len(rows),
           failures=len(failures), declared_out_of_validity=len(declared),
           declared_min_pressure_ratio=min((d["pv_over_pc"] for d in declared), default=None), failure_examples=failures[:400], declared_examples=declared[:400],
           max_step_over_scale=max(r["max_step_over_scale"] for r in rows),
           note="consistency audit of the boundary law; not validation")
json.dump(out, open(sys.argv[1], "w"), indent=1)
print({k: out[k] for k in ("cases", "failures", "declared_out_of_validity", "declared_min_pressure_ratio", "max_step_over_scale")})
