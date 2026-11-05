"""Stage-2 robustness matrix: demanding but physical conditions on the synthetic example engine.
Records status, step rejections, ledger closure, thermodynamic-fit validity and key indicators."""
import json, sys, time
from motorsim.dino4t import config
from motorsim.dino4t.runner import run_operating_point

CASES = {
 "rpm_1500":        {"operating_point": {"rpm": 1500.0}},
 "rpm_10000":       {"operating_point": {"rpm": 10000.0}},
 "rpm_12000":       {"operating_point": {"rpm": 12000.0}},
 "rpm_14000":       {"operating_point": {"rpm": 14000.0}},
 "lean_phi_0.6":    {"operating_point": {"equivalence_ratio": 0.6}},
 "rich_phi_1.5":    {"operating_point": {"equivalence_ratio": 1.5}},
 "large_overlap":   {"intake_valve": {"lift": {"type": "harmonic", "open_deg": 305.0, "close_deg": -130.0, "max_lift_mm": 10.0}},
                     "exhaust_valve": {"lift": {"type": "harmonic", "open_deg": 130.0, "close_deg": -305.0, "max_lift_mm": 9.0}}},
 "coarse_aggressive_numerics": {"numerics": {"dx_mm": 40.0, "cfl": 0.9, "max_dtheta_deg": 2.0}},
 "high_cr_early_spark": {"geometry": {"compression_ratio": 14.0}, "combustion": {"start_deg": -35.0}},
 "hostile_initial_state": {"initial_conditions": {"cylinder_pressure_pa": 500000.0, "cylinder_temperature_K": 1500.0, "exhaust_temperature_K": 1200.0}},
 "choked_exhaust_pipe": {"exhaust_duct": {"segments": [{"length_mm": 700.0, "start_diameter_mm": 34.0, "end_diameter_mm": 34.0}]}},
}

if __name__ == "__main__":
    out = {}
    base = config.load(config.EXAMPLE_PATH)
    for name, ov in CASES.items():
        ov = dict(ov); ov.setdefault("numerics", {}).setdefault("dx_mm", 20.0)
        t = time.time()
        try:
            r = run_operating_point(base, overrides=ov, max_cycles=12, wall_limit_s=420)
            s = r["summary"]; f = s["final_cycle"] or {}
            out[name] = dict(status=s["status"], termination=s["termination"][:160], cycles=s["cycles_run"],
                             periodic=s["periodicity"]["status"], closure=max(s["conservation"]["max_relative_closure"].values()),
                             rejected_steps_last=f.get("rejected_steps"), T_max=f.get("T_max_K"), fit_exceeded=f.get("thermo_fit_range_exceeded"),
                             imep=f.get("imep_net_bar"), eta_v=f.get("volumetric_efficiency_intake_valve"), p_max=f.get("p_max_bar"),
                             wall=round(time.time() - t, 1))
        except Exception as exc:
            out[name] = dict(status="exception", error=f"{type(exc).__name__}: {exc}"[:200], wall=round(time.time() - t, 1))
        print(name, json.dumps(out[name], default=float), flush=True)
    if len(sys.argv) > 1:
        json.dump(out, open(sys.argv[1], "w"), indent=1, default=float)
