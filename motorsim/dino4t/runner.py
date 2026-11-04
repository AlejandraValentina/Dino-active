"""Operating-point runner: build -> integrate to periodicity -> indicators -> artifacts."""
from __future__ import annotations

import csv
import json
import math
from pathlib import Path
import subprocess

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


def _git_commit():
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
                        wall_limit_s=3600.0, progress=None) -> dict:
    engine, state, context = build(config, overrides=overrides)
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
        "model_id": MODEL_ID, "models": MODELS,
        "config_identifier": context["config"].get("identifier"),
        "config_sha256": context["config_hash"],
        "code_commit": _git_commit(),
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
