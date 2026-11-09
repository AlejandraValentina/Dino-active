"""Operating-point runner: build -> integrate to periodicity -> indicators -> artifacts."""
from __future__ import annotations

import csv
import hashlib
import json
import math
import platform
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
    combustion_enabled = config.get("combustion", {}).get("enabled", True)
    two_zone = combustion_enabled and config.get("combustion", {}).get("zone_model", "single_zone") == "two_zone_equilibrium"
    models["cylinder"] = "TWO_ZONE_EQUILIBRIUM_V1" if two_zone else "SINGLE_ZONE_0D_V1"
    models["combustion"] = "WIEBE_PRESCRIBED_BURN_TWO_ZONE_EQUILIBRIUM_V1" if two_zone else "WIEBE_SINGLE_ZONE_V1"
    if not combustion_enabled: models["combustion"] = "DISABLED"
    if not config.get("heat_transfer", {}).get("enabled", True): models["heat_transfer"] = "DISABLED"
    if not config.get("numerics", {}).get("second_order", True):
        models["duct"] = "QUASI_1D_HLLC_FIRST_ORDER_MULTISPECIES_V1"
    v = config.get("numerics", {}).get("restriction_model", "V2")
    models["valve_boundary"] = f"QUASI_STEADY_RESTRICTION_{v}"
    return models


def _git_dirty():
    """True when tracked files differ from HEAD (the commit alone then does not identify the code)."""
    return _source_identity()["dirty"]


def _git_commit():
    return _source_identity()["code_commit"]


def _source_identity():
    from ..source_provenance import capture_source_identity
    return capture_source_identity(Path(__file__).resolve().parents[2], build_metadata=_packaged_build_metadata())


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


STATE_CONTEXT_SCHEMA = "DINO4T_STATE_CONTEXT_V1"
STATE_CONTEXT_FIELDS = {"schema", "state", "theta_deg", "phase_deg", "cycles_completed",
                        "model_id", "complete_cycle", "config_sha256", "topology_sha256",
                        "source_status", "source_termination"}


def _finite_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _array_signature(value):
    shape = getattr(value, "shape", None)
    if shape is None:
        return None
    return {"shape": [int(item) for item in shape],
            "dtype": str(getattr(value, "dtype", "unknown"))}


def state_topology(state):
    """Topology only: keys, array shapes and dtypes, never physical values."""
    return {"ducts": {key: _array_signature(value)
                      for key, value in (state.get("ducts") or {}).items()},
            "cyl": _array_signature(state.get("cyl")),
            "plen": {key: _array_signature(value)
                     for key, value in (state.get("plen") or {}).items()}}


def topology_sha256(state):
    payload = json.dumps(state_topology(state), sort_keys=True, separators=(",", ":"),
                         ensure_ascii=True, allow_nan=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _phase_deg(theta, theta_start):
    return float((float(theta) - float(theta_start)) % 720.0)


def _at_cycle_boundary(phase):
    return math.isclose(float(phase) % 720.0, 0.0, abs_tol=1e-9)


def _state_context(result, engine, config_sha256):
    theta = float(result["theta"])
    phase = _phase_deg(theta, engine.theta_start)
    return {
        "schema": STATE_CONTEXT_SCHEMA,
        "state": result["state"],
        "theta_deg": theta,
        "phase_deg": phase,
        "cycles_completed": len(result["cycles"]),
        "model_id": MODEL_ID,
        "complete_cycle": (result["status"] == "completed"
                           and bool(result["cycles"])
                           and _at_cycle_boundary(phase)),
        "config_sha256": config_sha256,
        "topology_sha256": topology_sha256(result["state"]),
        "source_status": result["status"],
        "source_termination": result["reason"],
    }


def validate_initial_state(initial_state, *, engine=None, expected_state=None):
    """Accept only an explicit, completed-cycle state context; never a raw mid-cycle dict.

    A context carries the phase, model, configuration and topology identity needed to
    distinguish a same-configuration continuation from a different-configuration warm
    start.  Exact mid-cycle restart is not representable here.
    """
    if not isinstance(initial_state, dict) or initial_state.get("schema") != STATE_CONTEXT_SCHEMA:
        raise ValueError("initial_state must be a DINO4T_STATE_CONTEXT_V1 from a completed cycle")
    if initial_state.get("complete_cycle") is not True:
        raise ValueError("mid-cycle initial_state is unsafe; resume only from a completed 720-degree cycle")
    if initial_state.get("model_id") != MODEL_ID:
        raise ValueError("initial_state model identity does not match the native 4T model")
    raw = initial_state.get("state")
    if not isinstance(raw, dict) or not {"ducts", "cyl", "plen"} <= set(raw):
        raise ValueError("initial_state state payload is incomplete")
    theta = initial_state.get("theta_deg")
    phase = initial_state.get("phase_deg")
    if not _finite_number(theta) or not _finite_number(phase):
        raise ValueError("initial_state phase context is missing or invalid")
    if not _at_cycle_boundary(phase):
        raise ValueError("initial_state is not at a complete-cycle boundary")
    if engine is not None:
        actual = _phase_deg(theta, engine.theta_start)
        if not _at_cycle_boundary(actual):
            raise ValueError("initial_state phase is incompatible with the configured cycle start")
        recorded = initial_state.get("topology_sha256")
        if not isinstance(recorded, str) or len(recorded) != 64:
            raise ValueError("initial_state topology identity is missing or invalid")
        if expected_state is not None and recorded != topology_sha256(expected_state):
            raise ValueError("initial_state topology does not match the configured mesh")
    return raw


def initial_state_assessment(config: dict, initial_state):
    """Classify an initial state before any solver work.

    ``continuation`` = same exact configuration at a cycle boundary;
    ``warm_start`` = different configuration with an identical state topology.
    There is no exact-restart capability and none is claimed here.
    """
    from .config import build
    engine, state, context = build(config)
    try:
        raw = validate_initial_state(initial_state, engine=engine, expected_state=state)
    except ValueError as exc:
        return {"valid": False, "kind": None, "error": str(exc), "state": None}
    same_config = initial_state.get("config_sha256") == context["config_hash"]
    return {"valid": True, "kind": "continuation" if same_config else "warm_start",
            "error": None, "state": raw, "context": context,
            "same_config": same_config,
            "source_config_sha256": initial_state.get("config_sha256"),
            "theta_deg": initial_state.get("theta_deg"),
            "phase_deg": initial_state.get("phase_deg"),
            "cycles_completed": initial_state.get("cycles_completed")}


def run_operating_point(config: dict, *, out_dir=None, overrides=None, max_cycles=None,
                        wall_limit_s=3600.0, progress=None, initial_state=None,
                        cancel_event=None) -> dict:
    """``initial_state``: explicit cycle-boundary state context from a previous run."""
    from .artifacts import publish_primary, require_empty_output
    if out_dir is not None: require_empty_output(out_dir)
    source_identity = _source_identity()
    engine, state, context = build(config, overrides=overrides)
    warm_start = "none"
    initial_state_context = None
    if initial_state is not None:
        raw_state = validate_initial_state(initial_state, engine=engine, expected_state=state)
        same_config = initial_state.get("config_sha256") == context["config_hash"]
        kind = "continuation" if same_config else "warm_start"
        warm_start = "continuation" if same_config else "warm_start_different_config"
        state = {"ducts": {k: v.copy() for k, v in raw_state["ducts"].items()},
                 "cyl": raw_state["cyl"].copy(),
                 "plen": {k: v.copy() for k, v in raw_state["plen"].items()}}
        initial_state_context = {
            "schema": "DINO4T_INITIAL_STATE_V1",
            "kind": kind,
            "exact_restart_claim": "NOT_SUPPORTED",
            "source_config_sha256": initial_state.get("config_sha256"),
            "theta_deg": initial_state.get("theta_deg"),
            "phase_deg": initial_state.get("phase_deg"),
            "cycles_completed": initial_state.get("cycles_completed"),
            "topology_match": True,
        }
    num = context["config"].get("numerics", {})
    monitor = PeriodicityMonitor(context, num.get("periodicity"))
    cycles = int(max_cycles or num.get("max_cycles", 20))

    def on_cycle(record):
        if progress:
            progress(record)

    result = engine.run(state, cycles, wall_limit_s=wall_limit_s, on_cycle=on_cycle,
                        convergence=monitor, cancel_event=cancel_event)
    ending_identity = _source_identity()
    stable = (source_identity.get("inventory_sha256") == ending_identity.get("inventory_sha256")
              and source_identity.get("code_commit") == ending_identity.get("code_commit"))
    source_identity["stable_during_run"] = stable
    if not stable:
        source_identity["status"] = "INCOMPLETE"; source_identity["dirty"] = True
        source_identity.setdefault("issues", []).append("SOURCE_CHANGED_DURING_RUN")
        source_identity["ending_identity"] = ending_identity
    records = result["cycles"]
    if len(monitor.indicators) < len(records):  # last cycle when convergence hook did not run
        monitor(records)
    final = monitor.indicators[-1] if monitor.indicators else None
    summary = {
        "schema": "DINO4T_OPERATING_POINT_RESULT_V1",
        "model_id": MODEL_ID, "models": resolved_models(context["config"]),
        "config_identifier": context["config"].get("identifier"),
        "config_sha256": context["config_hash"],
        "code_commit": source_identity.get("code_commit"), "code_dirty": source_identity.get("dirty"),
        "source_identity": source_identity,
        "runtime_environment": {"python": platform.python_version(), "implementation": platform.python_implementation(),
                                "platform": platform.platform(), "numpy": np.__version__,
                                "scipy": __import__("scipy").__version__},
        "thermo_sources": {"gri30_sha256": GRI30_SHA256, "burcat_sha256": BURCAT_SHA256, "accessed": ACCESSED},
        "provenance": {g: context["config"][g]["provenance"] for g in
                       ("geometry", "intake_valve", "exhaust_valve", "intake_duct", "exhaust_duct",
                        "combustion", "heat_transfer", "friction", "ambient")},
        "status": result["status"], "termination": result["reason"],
        "periodicity": {"status": monitor.status, "tolerances": monitor.tol, "history": monitor.metrics,
                        "detector": {"schema": "DINO4T_PERIODICITY_DECISION_V2", "min_cycles": monitor.min_cycles}},
        "cycles_run": len(records),
        "operating_point": context["config"]["operating_point"],
        "final_cycle": final,
        "cycle_history": [{k: ind[k] for k in ("imep_net_bar", "pmep_bar", "volumetric_efficiency_intake_valve",
                                                "trapped_mass_mg", "residual_gas_fraction_ivc", "p_max_bar")}
                          for ind in monitor.indicators],
        "conservation": {"final_relative_closure": result["closure"], "max_relative_closure": result["max_closure"]},
        "wall_seconds": result["wall_seconds"],
        "warm_start": warm_start,
        "initial_state_context": initial_state_context,
        "evidence_level": "L1_ENGINEERING_RUN",
        "claims": CLAIMS,
    }
    summary = _jsonable(summary)
    artifacts = publish_primary(out_dir, summary, context["config"], records[-1].trace if records else None) if out_dir is not None else {}
    return {"summary": summary, "records": records, "engine": engine, "context": context, "result": result,
            "artifacts": artifacts, "state_context": _state_context(result, engine, context["config_hash"])}


def write_trace_csv(trace: dict, path):
    keys = [k for k, v in trace.items() if isinstance(v, list) and k != "pressure_grid" and len(v) == len(trace["theta"])]
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(keys)
        for row in zip(*(trace[k] for k in keys)):
            writer.writerow([f"{v:.10g}" for v in row])
