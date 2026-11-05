"""Operating-point runner: build -> integrate to periodicity -> indicators -> artifacts."""
from __future__ import annotations

import csv
import json
import math
from pathlib import Path
import subprocess
import sys

import numpy as np

from . import MODEL_ID, MODELS
from .config import build
from .cycle_analysis import PeriodicityMonitor
from .thermo_data import ACCESSED, BURCAT_SHA256, GRI30_SHA256

CLAIMS = {
    "numerical_verification": "see docs/dino4t/verification_report.md (separate evidence)",
    "calibration": "NOT_PERFORMED",
    "experimental_validation": "NOT_PERFORMED",
    "predictive_capability": "NOT_CLAIMED",
}


def _packaged_build_metadata(path=None):
    if path is None and not getattr(sys, "frozen", False):
        return None
    path = Path(path) if path is not None else Path(__file__).resolve().parents[1] / "build.json"
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return value if isinstance(value, dict) else None


def resolved_models(config: dict) -> dict:
    """Model identifiers actually selected by the configuration (not the static defaults)."""
    models = dict(MODELS)
    two_zone = config.get("combustion", {}).get("zone_model", "single_zone") == "two_zone_equilibrium"
    models["cylinder"] = "TWO_ZONE_EQUILIBRIUM_V1" if two_zone else "SINGLE_ZONE_0D_V1"
    models["combustion"] = "WIEBE_PRESCRIBED_BURN_TWO_ZONE_EQUILIBRIUM_V1" if two_zone else "WIEBE_SINGLE_ZONE_V1"
    v = config.get("numerics", {}).get("restriction_model", "V2")
    models["valve_boundary"] = f"QUASI_STEADY_RESTRICTION_{v}"
    return models


def _git_dirty():
    """True when tracked files differ from HEAD (the commit alone then does not identify the code)."""
    packaged = _packaged_build_metadata()
    if packaged is not None:
        if not isinstance(packaged.get("source_commit"), str):
            return None
        if packaged.get("packaged_inputs_clean") is not True:
            return True
        return False
    try:
        out = subprocess.run(["git", "status", "--porcelain", "--untracked-files=no", "--", "."],
                             capture_output=True, text=True, cwd=Path(__file__).parent, timeout=10)
        return bool(out.stdout.strip()) if out.returncode == 0 else None
    except (OSError, subprocess.SubprocessError):
        return None


def _git_commit():
    packaged = _packaged_build_metadata()
    if packaged is not None:
        commit = packaged.get("source_commit")
        return commit if isinstance(commit, str) and len(commit) == 40 else None
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True,
                              cwd=Path(__file__).parent, timeout=10).stdout.strip() or None
    except (OSError, subprocess.SubprocessError):
        return None


def _jsonable(value):
    if isinstance(value, dict):
        return {k: _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    if isinstance(value, (np.floating, np.integer)):
        value = value.item()
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, np.ndarray):
        return _jsonable(value.tolist())
    if isinstance(value, np.bool_):
        return bool(value)
    return value


def run_operating_point(config: dict, *, out_dir=None, overrides=None, max_cycles=None,
                        wall_limit_s=3600.0, progress=None, initial_state=None) -> dict:
    """``initial_state``: converged state of a previous run of the same topology (continuation)."""
    engine, state, context = build(config, overrides=overrides)
    warm_start = "none"
    if initial_state is not None:
        compatible = (set(initial_state["ducts"]) == set(state["ducts"])
                      and all(initial_state["ducts"][k].shape == state["ducts"][k].shape for k in state["ducts"])
                      and initial_state["cyl"].shape == state["cyl"].shape
                      and set(initial_state["plen"]) == set(state["plen"]))
        if compatible:
            warm_start = "used"
            state = {"ducts": {k: v.copy() for k, v in initial_state["ducts"].items()},
                     "cyl": initial_state["cyl"].copy(),
                     "plen": {k: v.copy() for k, v in initial_state["plen"].items()}}
        else:  # e.g. a duct length change altered the number of cells: cold start, recorded in the summary
            warm_start = "discarded_incompatible_mesh"
    num = context["config"].get("numerics", {})
    monitor = PeriodicityMonitor(context, num.get("periodicity"))
    cycles = int(max_cycles or num.get("max_cycles", 20))

    def on_cycle(record):
        if progress:
            progress(record)

    result = engine.run(state, cycles, wall_limit_s=wall_limit_s, on_cycle=on_cycle, convergence=monitor)
    records = result["cycles"]
    if len(monitor.indicators) < len(records):  # last cycle when convergence hook did not run
        monitor(records)
    final = monitor.indicators[-1] if monitor.indicators else None
    summary = {
        "schema": "DINO4T_OPERATING_POINT_RESULT_V1",
        "model_id": MODEL_ID, "models": resolved_models(context["config"]),
        "config_identifier": context["config"].get("identifier"),
        "config_sha256": context["config_hash"],
        "code_commit": _git_commit(), "code_dirty": _git_dirty(),
        "thermo_sources": {"gri30_sha256": GRI30_SHA256, "burcat_sha256": BURCAT_SHA256, "accessed": ACCESSED},
        "provenance": {g: context["config"][g]["provenance"] for g in
                       ("geometry", "intake_valve", "exhaust_valve", "intake_duct", "exhaust_duct",
                        "combustion", "heat_transfer", "friction", "ambient")},
        "status": result["status"], "termination": result["reason"],
        "periodicity": {"status": monitor.status, "tolerances": monitor.tol, "history": monitor.metrics},
        "cycles_run": len(records),
        "operating_point": context["config"]["operating_point"],
        "final_cycle": final,
        "cycle_history": [{k: ind[k] for k in ("imep_net_bar", "pmep_bar", "volumetric_efficiency_intake_valve",
                                                "trapped_mass_mg", "residual_gas_fraction_ivc", "p_max_bar")}
                          for ind in monitor.indicators],
        "conservation": {"final_relative_closure": result["closure"], "max_relative_closure": result["max_closure"]},
        "wall_seconds": result["wall_seconds"],
        "warm_start": warm_start,
        "evidence_level": "L1_ENGINEERING_RUN",
        "claims": CLAIMS,
    }
    summary = _jsonable(summary)
    if out_dir is not None:
        out = Path(out_dir)
        out.mkdir(parents=True, exist_ok=True)
        (out / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
        (out / "config_resolved.json").write_text(json.dumps(context["config"], indent=2), encoding="utf-8")
        if records:
            write_trace_csv(records[-1].trace, out / "trace_last_cycle.csv")
    return {"summary": summary, "records": records, "engine": engine, "context": context, "result": result}


def write_trace_csv(trace: dict, path):
    keys = [k for k, v in trace.items() if isinstance(v, list) and k != "pressure_grid" and len(v) == len(trace["theta"])]
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(keys)
        for row in zip(*(trace[k] for k in keys)):
            writer.writerow([f"{v:.10g}" for v in row])
