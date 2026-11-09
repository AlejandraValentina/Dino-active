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
import re
from typing import Callable

from . import MODEL_ID
from .config import SCHEMA as CONFIG_SCHEMA, ConfigError, canonical_hash, validate as _validate_config
from .validation import CONFIG_VALIDATION, RESULT_VALIDATION, configuration_issues, finite

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
    "RESULT_INVALID": "raw calculated result retained, but semantic/domain checks failed",
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
        "default_models": resolved_models({}),
        "config_validation_contract": CONFIG_VALIDATION, "result_validation_contract": RESULT_VALIDATION,
        "options": {"out_dir": "path or None", "overrides": "nested dict merged over the config",
                    "max_cycles": "int >= 1", "wall_limit_s": "float > 0", "on_progress": "callable(dict) or None",
                    "cancel_event": "threading.Event-like object; observed after a completed 720-degree cycle",
                    "initial_state": "opaque continuation state from a previous run of the SAME topology",
                    "allow_unknown_keys": "legacy option; unread scientific controls are always rejected"},
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
    issues = configuration_issues(config)
    unknown = [issue["path"] for issue in issues if issue["code"] == "UNKNOWN_KEY"]
    if issues:
        return {"valid": False, "issues": issues, "unknown_keys": unknown,
                "config_sha256": None, "validation_contract": CONFIG_VALIDATION}
    try:
        _validate_config(config)
        build(config)
    except ConfigError as exc:
        issues.append({"code": "CONFIG_INVALID", "path": _path_of(str(exc)), "message": str(exc)})
    except (ValueError, KeyError, TypeError, OverflowError) as exc:  # expected construction/domain errors
        issues.append({"code": "CONFIG_INVALID", "path": _path_of(str(exc)),
                       "message": f"{type(exc).__name__}: {exc}"})
    return {"valid": not issues, "issues": issues, "unknown_keys": unknown,
            "config_sha256": canonical_hash(config) if not issues else None,
            "validation_contract": CONFIG_VALIDATION}


def unknown_keys(config: dict) -> list[str]:
    """Section-aware dotted paths, independent of any bundled example file."""
    return [x["path"] for x in configuration_issues(config) if x["code"] == "UNKNOWN_KEY"]


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
    from .runner import (initial_state_assessment, run_operating_point,
                         validate_initial_state)
    if max_cycles is not None and (not isinstance(max_cycles, int) or isinstance(max_cycles, bool) or max_cycles < 1):
        return _fail("OPTION_INVALID", "max_cycles must be an integer >= 1")
    if not (finite(wall_limit_s) and wall_limit_s > 0):
        return _fail("OPTION_INVALID", "wall_limit_s must be > 0")
    if overrides is not None and not isinstance(overrides, dict):
        return _fail("OPTION_INVALID", "overrides must be an object")
    if not isinstance(allow_unknown_keys, bool) or (on_progress is not None and not callable(on_progress)):
        return _fail("OPTION_INVALID", "invalid allow_unknown_keys/on_progress option")
    if not isinstance(config, dict):
        return _fail("CONFIG_INVALID", "config must be an object")
    if out_dir is not None:
        from .artifacts import require_empty_output
        try: require_empty_output(out_dir)
        except (ValueError, OSError, TypeError) as exc: return _fail("OPTION_INVALID", str(exc))
    if cancel_event is not None and not callable(getattr(cancel_event, "is_set", None)):
        return _fail("OPTION_INVALID", "cancel_event must provide is_set()")
    if initial_state is not None:
        try:
            validate_initial_state(initial_state)
        except ValueError as exc:
            return _fail("OPTION_INVALID", str(exc))
    cfg = copy.deepcopy(config)
    if overrides:
        from .config import _deep_update
        _deep_update(cfg, copy.deepcopy(overrides))
    check = validate(cfg)
    if not check["valid"]:
        return _fail("CONFIG_INVALID", check["issues"][0]["message"], detail=check["issues"])
    if check["unknown_keys"]:
        # an unread key (typo) would silently fall back to a default model: refuse instead
        return _fail("CONFIG_INVALID", f"unknown configuration keys: {check['unknown_keys']}",
                     detail=[{"code": "UNKNOWN_KEY", "path": k} for k in check["unknown_keys"]])
    if initial_state is not None:
        assessment = initial_state_assessment(cfg, initial_state)
        if not assessment["valid"]:
            return _fail("OPTION_INVALID", assessment["error"])

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
    semantic_problems = check_summary(summary, config=out["context"]["config"])
    artifacts = out.get("artifacts", {})
    error = None
    if semantic_problems:
        error = {"code": "RESULT_INVALID", "message": "Calculated data retained but not eligible",
                 "detail": semantic_problems}
    elif summary["status"] == "failed_numerical":
        error = {"code": "MODEL_OUT_OF_VALIDITY", "message": summary["termination"], "detail": None}
    elif summary["status"] == "incomplete":
        code = "CANCELLED" if summary.get("termination") == "cancelled_by_user" else "WALL_LIMIT"
        error = {"code": code, "message": summary["termination"], "detail": None}
    elif summary["periodicity"]["status"] != "PERIODIC_CONVERGED":
        error = {"code": "NOT_PERIODIC", "message": "cycle limit reached without periodicity", "detail": None}
    return {"api": API_VERSION, "ok": error is None, "error": error, "summary": summary,
            "artifacts": artifacts, "state": out.get("state_context"),
            "state_context": out.get("state_context"),
            "result_validation": {"contract": RESULT_VALIDATION, "issues": semantic_problems}}


def _fail(code: str, message: str, *, detail=None) -> dict:
    return {"api": API_VERSION, "ok": False, "error": {"code": code, "message": message, "detail": detail},
            "summary": None, "artifacts": {}, "state": None}


def check_summary(summary: dict, *, config: dict | None = None) -> list[str]:
    """Return the list of contract violations of a result summary (empty = conforming)."""
    from .validation import summary_issues
    return summary_issues(summary, config=config)
