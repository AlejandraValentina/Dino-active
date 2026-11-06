"""Engineering studies on top of the operating-point runner: parameter sweeps and local sensitivities.

* ``sweep``: run a list of override dictionaries; each converged state seeds the next point
  (continuation), which cuts the cycles needed per point.  Results carry the provenance of the
  base configuration and the override of every point.
* ``sensitivity``: central finite differences of chosen indicators with respect to chosen physical
  parameters (relative step), reported as elasticities  d ln y / d ln x.  Physical and numerical
  parameters are kept separate: the first say how much a result depends on an input that may be
  uncertain, the second how much it depends on the discretisation.

None of this is calibration or validation.  Elasticities are local, at one operating point of the
configuration given, and inherit every limitation of the model.
"""
from __future__ import annotations

import copy
import csv
import json
import math
from pathlib import Path

from .runner import _jsonable, run_operating_point

DEFAULT_INDICATORS = ("imep_net_bar", "volumetric_efficiency_intake_valve", "p_max_bar", "pmep_bar",
                      "indicated_fuel_conversion_efficiency", "residual_gas_fraction_ivc",
                      "exhaust_valve_mean_enthalpy_temperature_K", "brake_power_kW")


def _set(config: dict, path: str, value):
    node = config
    keys = path.split(".")
    for k in keys[:-1]:
        node = node[int(k)] if isinstance(node, list) else node[k]
    node[int(keys[-1]) if isinstance(node, list) else keys[-1]] = value


def _get(config: dict, path: str):
    node = config
    for k in path.split("."):
        node = node[int(k)] if isinstance(node, list) else node[k]
    return node


def apply_overrides(config: dict, flat: dict) -> dict:
    """Return a deep copy with dotted-path overrides applied (``intake_valve.lift.open_deg``)."""
    out = copy.deepcopy(config)
    for path, value in flat.items():
        _set(out, path, value)
    return out


def _source_qualification(summary: dict) -> str:
    identity = summary.get("source_identity")
    if isinstance(identity, dict) and identity.get("status") == "COMPLETE" and summary.get("code_dirty") is False:
        return "COMPLETE_CLEAN_SOURCE_SNAPSHOT"
    return "DIRTY_OR_UNKNOWN_SOURCE" if isinstance(identity, dict) else "SOURCE_IDENTITY_UNVERIFIED"


def sweep(config: dict, points: list[dict], *, indicators=DEFAULT_INDICATORS, max_cycles=14,
          continuation=True, out_dir=None, base_overrides=None, progress=None) -> list[dict]:
    from . import api
    rows, state, base_summary = [], None, None
    for i, flat in enumerate(points):
        cfg = apply_overrides(config, flat)
        out = run_operating_point(cfg, overrides=base_overrides, max_cycles=max_cycles,
                                  initial_state=state if continuation else None)
        s = out["summary"]
        if base_summary is None:
            base_summary = s
        final = s["final_cycle"] or {}
        issues = api.check_summary(s, config=out["context"]["config"])
        row = dict(point=i, overrides=flat, status=s["status"], periodicity=s["periodicity"]["status"],
                   cycles=s["cycles_run"], closure=max(s["conservation"]["max_relative_closure"].values()),
                   source_qualification=_source_qualification(s),
                   source_identity_status=(s.get("source_identity") or {}).get("status")
                   if isinstance(s.get("source_identity"), dict) else None,
                   contract_issues=issues,
                   **{k: final.get(k) for k in indicators})
        rows.append(row)
        if s["status"] == "completed" and continuation:
            state = out["result"]["state"]
        if progress:
            progress(row)
    if out_dir is not None:
        out = Path(out_dir)
        out.mkdir(parents=True, exist_ok=True)
        (out / "sweep.json").write_text(json.dumps(_jsonable(dict(
            schema="DINO4T_SWEEP_V1", config_identifier=config.get("identifier"),
            provenance={g: config[g]["provenance"] for g in config if isinstance(config[g], dict) and "provenance" in config[g]},
            source_identity=base_summary.get("source_identity") if base_summary else None,
            runtime_environment=base_summary.get("runtime_environment") if base_summary else None,
            claims=dict(calibration="NOT_PERFORMED", experimental_validation="NOT_PERFORMED",
                        predictive_capability="NOT_CLAIMED"), rows=rows)), indent=1), encoding="utf-8")
        cols = ["point", "status", "periodicity", "cycles", "closure", *indicators]
        with open(out / "sweep.csv", "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["overrides", *cols])
            for r in rows:
                w.writerow([json.dumps(r["overrides"]), *(r.get(c) for c in cols)])
    return rows


def linspace_points(path: str, start: float, stop: float, n: int) -> list[dict]:
    return [{path: start + (stop - start) * i / (n - 1)} for i in range(n)]


# --------------------------------------------------------------------------- sensitivity
def _scale_scalar(path):
    def make(config, factor):
        return {path: _get(config, path) * factor}
    return make


def _scale_list(path, key=None):
    def make(config, factor):
        node = _get(config, path)
        return {path: [v * factor for v in node]}
    return make


def _scale_segment_lengths(section):
    def make(config, factor):
        segs = copy.deepcopy(_get(config, f"{section}.segments"))
        for s in segs:
            s["length_mm"] *= factor
        return {f"{section}.segments": segs}
    return make


def _shift_angle(paths):
    def make(config, factor):  # factor is interpreted as a shift of (factor - 1) * 100 degrees
        shift = (factor - 1.0) * 100.0
        return {p: _get(config, p) + shift for p in paths}
    return make


PHYSICAL_PARAMETERS = {
    "intake_Cd_forward": lambda c, f: {"intake_valve.discharge_coefficient.forward": [v * f for v in _get(c, "intake_valve.discharge_coefficient.forward")]},
    "intake_Cd_reverse": lambda c, f: {"intake_valve.discharge_coefficient.reverse": [v * f for v in _get(c, "intake_valve.discharge_coefficient.reverse")]},
    "exhaust_Cd_forward": lambda c, f: {"exhaust_valve.discharge_coefficient.forward": [v * f for v in _get(c, "exhaust_valve.discharge_coefficient.forward")]},
    "intake_max_lift": _scale_scalar("intake_valve.lift.max_lift_mm"),
    "exhaust_max_lift": _scale_scalar("exhaust_valve.lift.max_lift_mm"),
    "intake_timing_shift_deg_per_pct": _shift_angle(["intake_valve.lift.open_deg", "intake_valve.lift.close_deg"]),
    "exhaust_timing_shift_deg_per_pct": _shift_angle(["exhaust_valve.lift.open_deg", "exhaust_valve.lift.close_deg"]),
    "intake_runner_length": _scale_segment_lengths("intake_duct"),
    "exhaust_pipe_length": _scale_segment_lengths("exhaust_duct"),
    "woschni_multiplier": _scale_scalar("heat_transfer.multiplier"),
    "wall_T_liner": _scale_scalar("heat_transfer.t_liner_K"),
    "friction_A": _scale_scalar("friction.a_pa"),
    "wiebe_duration": _scale_scalar("combustion.duration_deg"),
    "combustion_efficiency": _scale_scalar("combustion.efficiency"),
    "intake_air_temperature": _scale_scalar("ambient.intake_temperature_K"),
}

NUMERICAL_PARAMETERS = {
    "dx_mm": _scale_scalar("numerics.dx_mm"),
    "max_dtheta_deg": _scale_scalar("numerics.max_dtheta_deg"),
    "cfl": _scale_scalar("numerics.cfl"),
}


def sensitivity(config: dict, *, parameters=None, indicators=DEFAULT_INDICATORS, rel_step=0.05,
                max_cycles=14, out_dir=None, progress=None, base_overrides=None) -> dict:
    """Central-difference elasticities.  Timing 'parameters' use a degree shift of rel_step * 100 deg
    (so rel_step=0.05 -> 5 deg) and report d y / d(deg) instead of an elasticity."""
    table = {**PHYSICAL_PARAMETERS, **NUMERICAL_PARAMETERS}
    names = list(parameters or PHYSICAL_PARAMETERS)
    from . import api
    base = run_operating_point(config, overrides=base_overrides, max_cycles=max_cycles)
    if base["summary"]["status"] != "completed":
        raise RuntimeError("base case failed: " + base["summary"]["termination"])
    base_summary = base["summary"]
    y0 = {k: base_summary["final_cycle"][k] for k in indicators}
    state0 = base["result"]["state"]
    result = dict(base=y0, rel_step=rel_step, parameters={}, base_periodicity=base_summary["periodicity"]["status"],
                  source_identity=base_summary.get("source_identity"),
                  runtime_environment=base_summary.get("runtime_environment"),
                  source_qualification=_source_qualification(base_summary),
                  contract_issues=api.check_summary(base_summary, config=base["context"]["config"]))
    for name in names:
        maker = table[name]
        ys = {}
        for sign in (+1, -1):
            cfg = apply_overrides(config, maker(config, 1.0 + sign * rel_step))
            o = run_operating_point(cfg, overrides=base_overrides, max_cycles=max_cycles, initial_state=state0)
            ys[sign] = o["summary"]["final_cycle"] if o["summary"]["status"] == "completed" else None
        if ys[1] is None or ys[-1] is None:
            result["parameters"][name] = dict(status="failed")
            continue
        entry = {}
        for k in indicators:
            if "shift" in name:
                entry[k] = (ys[1][k] - ys[-1][k]) / (2 * rel_step * 100.0)
            else:
                entry[k] = ((ys[1][k] - ys[-1][k]) / (2 * rel_step)) / y0[k] if y0[k] else None
        result["parameters"][name] = dict(status="ok", unit=("d y / d deg" if "shift" in name else "elasticity"), **entry)
        if progress:
            progress(name, result["parameters"][name])
    if out_dir is not None:
        out = Path(out_dir)
        out.mkdir(parents=True, exist_ok=True)
        (out / "sensitivity.json").write_text(json.dumps(_jsonable(dict(
            schema="DINO4T_SENSITIVITY_V1", config_identifier=config.get("identifier"),
            note="local central differences at one operating point; not calibration, not validation",
            **result)), indent=1), encoding="utf-8")
    return result
