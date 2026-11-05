"""Stable integration surface of Dino 4T (``DINO4T_API_V1``).

Consumers (Dino Desktop, ``motorsim.engine_platform``, batch tools) should depend on this module and
on the JSON documents it exchanges, never on solver internals (``engine``, ``duct``, ``restriction``...).
Contract text, versioning rules and the list of what is *not* guaranteed:
docs/dino4t/integration_contract.md.

Design rules
  * No function here raises for an expected failure: configuration problems, model-validity
    violations, wall-limit and non-convergence are returned as a structured ``error`` / ``status``.
    Only programming errors (a non-dict config, a bad option type) raise.
  * Everything exchanged is JSON-serialisable; progress callbacks receive plain dicts.
  * Units are SI except where a key suffix says otherwise (``_bar``, ``_kW``, ``_deg``, ``_mg``...).
"""
from __future__ import annotations

import copy
import inspect
import re
from typing import Callable

from . import MODEL_ID
from .config import SCHEMA as CONFIG_SCHEMA, ConfigError, canonical_hash, validate as _validate_config

API_VERSION = "DINO4T_API_V1"
RESULT_SCHEMA = "DINO4T_OPERATING_POINT_RESULT_V1"
RESULT_REQUIRED_KEYS = ("schema", "model_id", "models", "config_sha256", "code_commit", "code_dirty",
                        "thermo_sources", "provenance", "status", "termination", "periodicity", "cycles_run",
                        "operating_point", "final_cycle", "conservation", "evidence_level", "claims")
# run status vocabulary (summary["status"]); "completed" is the only status with a usable final_cycle
# that has also reached the requested end condition.
RUN_STATUSES = ("completed", "incomplete", "failed_numerical")
PERIODICITY_STATUSES = ("PERIODIC_CONVERGED", "NOT_CONVERGED")
ERROR_CODES = {
    "CONFIG_INVALID": "configuration rejected before any computation (fixable by the caller)",
    "OPTION_INVALID": "an option of run() is out of range",
    "MODEL_OUT_OF_VALIDITY": "the model refused a state it cannot represent (fail-closed boundary/thermo)",
    "WALL_LIMIT": "wall-clock limit reached; partial results are returned",
    "NOT_PERIODIC": "ran to the cycle limit without meeting the periodicity criteria",
    "CANCELLED": "user requested cancellation; any returned summary contains completed cycles only",
    "INTERNAL": "unexpected exception; a defect, not a user error",
}
_UNIT_SUFFIXES = (("_g_kWh", "g/kWh"), ("_MJ_kg", "MJ/kg"), ("_Nm", "N*m"), ("_kW", "kW"), ("_bar", "bar"),
                  ("_deg", "deg"), ("_mg", "mg"), ("_K", "K"), ("_J", "J"))
_SOLVER_ERRORS = ("InadmissibleState", "RestrictionError", "ThermoError")


def indicator_unit(key: str) -> str | None:
    """Unit of a ``final_cycle`` indicator, read from its name suffix (None = dimensionless/count)."""
    for suffix, unit in _UNIT_SUFFIXES:
        if key.endswith(suffix):
            return unit
    return None


def capabilities() -> dict:
    """Static description of what this build offers (no computation)."""
    from .restriction import RestrictionError  # noqa: F401  (import check only)
    from .runner import resolved_models
    return {
        "api": API_VERSION, "model_id": MODEL_ID, "cycle": "4T",
        "config_schema": CONFIG_SCHEMA, "result_schema": RESULT_SCHEMA,
        "result_required_keys": list(RESULT_REQUIRED_KEYS),
        "run_statuses": list(RUN_STATUSES), "periodicity_statuses": list(PERIODICITY_STATUSES),
        "error_codes": dict(ERROR_CODES),
        "selectable_models": {
            "combustion.zone_model": ["single_zone", "two_zone_equilibrium"],
            "numerics.restriction_model": ["V1", "V2"],
            "numerics.limiter": ["minmod", "van_leer", "mc", "unlimited_central"],
        },
        "default_models": resolved_models({"combustion": {"zone_model": "two_zone_equilibrium"}}),
        "options": {"out_dir": "path or None", "overrides": "nested dict merged over the config",
                    "max_cycles": "int >= 1", "wall_limit_s": "float > 0", "on_progress": "callable(dict) or None",
                    "cancel_event": "threading.Event-like object; observed after a completed 720-degree cycle",
                    "initial_state": "opaque continuation state from a previous run of the SAME topology",
                    "allow_unknown_keys": "bool; default False = unread config keys (typos) are rejected"},
        "claims": {"calibration": "NOT_PERFORMED", "experimental_validation": "NOT_PERFORMED",
                   "predictive_capability": "NOT_CLAIMED"},
        "scope": ["single cylinder", "4-stroke spark ignition", "0D cylinder + quasi-1D ducts",
                  "prescribed (Wiebe) burn", "synthetic engineering parameters unless provenance says otherwise"],
        "not_supported": ["multi-cylinder", "junctions with loss", "kinetics / NO / knock", "injection and fuel films",
                          "turbocharging", "any claim of experimental agreement"],
        "units_rule": "SI unless a key suffix states otherwise; see indicator_unit()",
    }


def validate(config: dict) -> dict:
    """Check a configuration without running it.  Never raises for a bad configuration.

    Returns ``{"valid": bool, "issues": [{"code","path","message"}], "config_sha256": str|None}``.
    ``valid`` means the configuration builds a runnable engine (the mesh and the valve/port areas are
    checked by building it); it says nothing about physical adequacy of the parameter values.
    """
    from .config import build
    issues = []
    if not isinstance(config, dict):
        raise TypeError("config must be a dict")
    try:
        _validate_config(config)
        build(config)
    except ConfigError as exc:
        issues.append({"code": "CONFIG_INVALID", "path": _path_of(str(exc)), "message": str(exc)})
    except (ValueError, KeyError, TypeError) as exc:  # constructors validate ranges with ValueError
        issues.append({"code": "CONFIG_INVALID", "path": _path_of(str(exc)),
                       "message": f"{type(exc).__name__}: {exc}"})
    unknown = unknown_keys(config) if not issues else []
    return {"valid": not issues, "issues": issues, "unknown_keys": unknown,
            "config_sha256": canonical_hash(config) if not issues else None}


def unknown_keys(config: dict) -> list[str]:
    """Dotted paths of keys the builder never reads (typically typos, which would silently fall back
    to a default model).  Allowed = keys of the reference example configuration plus every key
    literal read by ``config.build`` / the section specs; a key is checked within its section."""
    from . import config as cfgmod
    from .config import EXAMPLE_PATH, load
    read = set(re.findall(r"[\"'](\w+)[\"']", inspect.getsource(cfgmod)))
    ref = load(EXAMPLE_PATH)
    found = []

    def walk(node, ref_node, path):
        if not isinstance(node, dict):
            return
        for key, value in node.items():
            sub = ref_node.get(key) if isinstance(ref_node, dict) else None
            if (not isinstance(ref_node, dict) or key not in ref_node) and key not in read:
                found.append(".".join(path + [key]))
            elif key not in ("segments", "lift", "discharge_coefficient", "periodicity"):
                walk(value, sub, path + [key])

    walk(config, ref, [])
    return found


def _path_of(message: str) -> str | None:
    m = re.search(r"\b([a-z_]+(?:\.[a-z_]+)+)\b", message)
    return m.group(1) if m else None


def run(config: dict, *, out_dir=None, overrides: dict | None = None, max_cycles: int | None = None,
        wall_limit_s: float = 3600.0, on_progress: Callable[[dict], None] | None = None,
        initial_state=None, allow_unknown_keys: bool = False, cancel_event=None) -> dict:
    """Run one operating point to periodicity (or the cycle/wall limit).

    Returns an envelope::

        {"api": "DINO4T_API_V1", "ok": bool, "error": None | {"code","message","detail"},
         "summary": DINO4T_OPERATING_POINT_RESULT_V1 dict | None, "artifacts": {...}, "state": opaque|None}

    ``ok`` is True only when the run completed AND is periodic; a finished-but-not-periodic run is
    ``ok=False`` with ``error.code == "NOT_PERIODIC"`` and the summary still attached, so that a GUI can
    show it with the proper caveat instead of presenting it as a result.
    """
    from .runner import run_operating_point
    if max_cycles is not None and (not isinstance(max_cycles, int) or max_cycles < 1):
        return _fail("OPTION_INVALID", "max_cycles must be an integer >= 1")
    if not (isinstance(wall_limit_s, (int, float)) and wall_limit_s > 0):
        return _fail("OPTION_INVALID", "wall_limit_s must be > 0")
    if cancel_event is not None and not callable(getattr(cancel_event, "is_set", None)):
        return _fail("OPTION_INVALID", "cancel_event must provide is_set()")
    cfg = copy.deepcopy(config)
    if overrides:
        from .config import _deep_update
        _deep_update(cfg, copy.deepcopy(overrides))
    check = validate(cfg)
    if not check["valid"]:
        return _fail("CONFIG_INVALID", check["issues"][0]["message"], detail=check["issues"])
    if check["unknown_keys"] and not allow_unknown_keys:
        # an unread key (typo) would silently fall back to a default model: refuse instead
        return _fail("CONFIG_INVALID", f"unknown configuration keys: {check['unknown_keys']}",
                     detail=[{"code": "UNKNOWN_KEY", "path": k} for k in check["unknown_keys"]])

    def progress(record):
        if on_progress is not None:
            on_progress({"cycle": int(record.index) + 1, "work_net_J": float(record.work_net),
                         "p_max_bar": float(record.p_max) / 1e5})

    try:
        out = run_operating_point(cfg, out_dir=out_dir, max_cycles=max_cycles, wall_limit_s=wall_limit_s,
                                  progress=progress, initial_state=initial_state, cancel_event=cancel_event)
    except Exception as exc:  # noqa: BLE001 - the API boundary converts every failure into data
        code = "MODEL_OUT_OF_VALIDITY" if type(exc).__name__ in _SOLVER_ERRORS else "INTERNAL"
        return _fail(code, f"{type(exc).__name__}: {exc}")
    summary = out["summary"]
    artifacts = {}
    if out_dir is not None:
        artifacts = {"summary": "summary.json", "config_resolved": "config_resolved.json",
                     "trace_last_cycle": "trace_last_cycle.csv", "directory": str(out_dir)}
    error = None
    if summary["status"] == "failed_numerical":
        error = {"code": "MODEL_OUT_OF_VALIDITY", "message": summary["termination"], "detail": None}
    elif summary["status"] == "incomplete":
        code = "CANCELLED" if summary.get("termination") == "cancelled_by_user" else "WALL_LIMIT"
        error = {"code": code, "message": summary["termination"], "detail": None}
    elif summary["periodicity"]["status"] != "PERIODIC_CONVERGED":
        error = {"code": "NOT_PERIODIC", "message": "cycle limit reached without periodicity", "detail": None}
    return {"api": API_VERSION, "ok": error is None, "error": error, "summary": summary,
            "artifacts": artifacts, "state": out["result"].get("state")}


def _fail(code: str, message: str, *, detail=None) -> dict:
    return {"api": API_VERSION, "ok": False, "error": {"code": code, "message": message, "detail": detail},
            "summary": None, "artifacts": {}, "state": None}


def check_summary(summary: dict) -> list[str]:
    """Return the list of contract violations of a result summary (empty = conforming)."""
    problems = [f"missing key {k}" for k in RESULT_REQUIRED_KEYS if k not in summary]
    if summary.get("schema") != RESULT_SCHEMA:
        problems.append(f"schema != {RESULT_SCHEMA}")
    if summary.get("status") not in RUN_STATUSES:
        problems.append(f"status {summary.get('status')!r} not in {RUN_STATUSES}")
    claims = summary.get("claims", {})
    if claims.get("experimental_validation") != "NOT_PERFORMED" and not summary.get("validation_evidence"):
        problems.append("experimental_validation claimed without validation_evidence")
    if claims.get("predictive_capability") not in ("NOT_CLAIMED",) and not summary.get("validation_evidence"):
        problems.append("predictive_capability claimed without validation_evidence")
    return problems
