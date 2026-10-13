"""Compact, replayable cycle recipes for the diagnostic FAST_RECIPE_V1 path."""
from __future__ import annotations

import copy
import hashlib
import json
import math
import os
import tempfile
import time
from pathlib import Path
from typing import Any

from .integrated_2t import (
    IntegratedEngine2T,
    _solver_dependency_hashes,
    audit_integrated_cycle_primary,
    make_integrated_cycle_primary,
    _integrated_nominal_step_end,
    _integrated_scheduled_angles,
)


IMPLEMENTATION_VERSION = "FAST_RECIPE_V1"
RECIPE_SCHEMA = "MOTORSIM_FAST_RECIPE_V1"


class FastRecipeError(ValueError):
    """Invalid, corrupt, or incompatible FAST_RECIPE_V1 input."""


def advance_cycle(engine: IntegratedEngine2T, cycle_index: int, *,
                  capture_trace: bool, profile_capture: bool = False,
                  max_wall_seconds: float = 600.0,
                  timing: dict[str, float] | None = None
                  ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Advance exactly one scheduled cycle, returning accepted recipe steps and retries."""
    if type(cycle_index) is not int or cycle_index != engine.cycle + 1:
        raise FastRecipeError("cycle index must be the engine's next cycle")
    if type(capture_trace) is not bool or type(profile_capture) is not bool:
        raise FastRecipeError("capture mode flags must be bool")
    started = time.monotonic()
    target_angle = float(cycle_index * 360)
    scheduled = _integrated_scheduled_angles(engine, target_angle)
    accepted: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    recipe_capture_seconds = 0.0
    trace_before = engine.trace_capture_seconds
    while engine.crank_angle_unwrapped_deg < target_angle - 1e-10:
        if time.monotonic() - started >= max_wall_seconds:
            raise TimeoutError("FAST_RECIPE_V1 diagnostic cycle exceeded its wall budget")
        angle = engine.crank_angle_unwrapped_deg
        target = _integrated_nominal_step_end(engine, angle, target_angle, scheduled)
        step_angle = target - angle
        for _ in range(25):
            if time.monotonic() - started >= max_wall_seconds:
                raise TimeoutError("FAST_RECIPE_V1 diagnostic cycle exceeded its wall budget")
            dt_s = step_angle / (6.0 * engine.reference_rpm)
            try:
                result = engine.step(dt_s, step_angle, capture_trace=capture_trace,
                                     profile_capture=profile_capture)
                capture_started = time.perf_counter()
                accepted.append({"angle_start_deg": result["angle_start_deg"],
                                 "delta_angle_deg": result["angle_end_deg"] -
                                 result["angle_start_deg"], "dt_s": dt_s})
                recipe_capture_seconds += time.perf_counter() - capture_started
                break
            except ValueError as exc:
                allowed = ("inadmissible species mass", "CFL limit exceeded",
                           "rho/p/Y inadmissible")
                if not any(reason in str(exc) for reason in allowed):
                    raise
                capture_started = time.perf_counter()
                rejected.append({"angle_deg": angle,
                                 "attempted_step_deg": step_angle,
                                 "reason": str(exc)})
                recipe_capture_seconds += time.perf_counter() - capture_started
                step_angle *= 0.5
        else:
            raise RuntimeError(f"no accepted FAST recipe step at {angle:.12g} degrees")
    if engine.crank_angle_unwrapped_deg != target_angle:
        raise FastRecipeError("cycle did not terminate at exact crank-angle boundary")
    if timing is not None:
        elapsed = time.perf_counter() - started
        timing.update({"cycle_wall_seconds": elapsed,
                       "step_trace_capture_seconds": engine.trace_capture_seconds - trace_before,
                       "recipe_schedule_capture_seconds": recipe_capture_seconds,
                       "physical_advance_seconds": max(
                           0.0, elapsed - (engine.trace_capture_seconds - trace_before)
                           - recipe_capture_seconds)})
    return accepted, rejected


def canonical_bytes(value: Any) -> bytes:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=False, allow_nan=False).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise FastRecipeError(f"recipe contains non-canonical data: {exc}") from exc


def sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _is_finite_number(value: Any) -> bool:
    return type(value) in (int, float) and math.isfinite(value)


def _terminal_projection(value: dict[str, Any]) -> dict[str, Any]:
    projection = {
        "engine_schema": value.get("engine_schema", value.get("schema")),
        "configuration_identity": value.get("configuration_identity"),
        "state": value.get("state"),
        "angle_deg": value.get("angle_deg"),
        "crank_angle_unwrapped_deg": value.get("crank_angle_unwrapped_deg"),
        "time_s": value.get("time_s"), "cycle": value.get("cycle"),
        "accepted_steps": value.get("accepted_steps"),
        "rejected_steps": value.get("rejected_steps"),
        "max_cfl": value.get("max_cfl"), "ledger": value.get("ledger"),
        "p7": value.get("p7"), "initial_inventory": value.get("initial_inventory"),
    }
    for key in ("fuel_combustion", "dynamic_reed_state"):
        if key in value:
            projection[key] = value[key]
        elif key == "fuel_combustion":
            projection[key] = None
        elif key == "dynamic_reed_state":
            reed = value.get("state", {}).get("dynamic_reed")
            if reed is not None:
                projection[key] = reed
    return projection


def build_recipe(*, configuration: dict[str, Any], cycle_index: int,
                 cycle_start_snapshot: dict[str, Any],
                 accepted_steps: list[dict[str, Any]],
                 rejected_trials: list[dict[str, Any]],
                 terminal_state: dict[str, Any],
                 next_cycle_checkpoint: dict[str, Any],
                 capture_runner_sha256: str,
                 previous_recipe_sha256: str | None = None) -> dict[str, Any]:
    """Bind one trace-free physical cycle to a deterministic replay schedule."""
    if type(cycle_index) is not int or cycle_index < 1:
        raise FastRecipeError("cycle_index must be a positive integer")
    if not isinstance(configuration, dict) or not isinstance(cycle_start_snapshot, dict):
        raise FastRecipeError("configuration and cycle start checkpoint are required")
    engine = IntegratedEngine2T.from_configuration_dict(configuration)
    if (cycle_start_snapshot.get("schema") != engine.schema or
            cycle_start_snapshot.get("configuration_identity") !=
            engine.configuration_identity or
            not isinstance(cycle_start_snapshot.get("state"), dict)):
        raise FastRecipeError("cycle start checkpoint is invalid")
    if (not isinstance(accepted_steps, list) or not accepted_steps or
            not isinstance(rejected_trials, list)):
        raise FastRecipeError("accepted schedule and rejected trial log are required")
    if (not isinstance(capture_runner_sha256, str) or len(capture_runner_sha256) != 64 or
            any(c not in "0123456789abcdef" for c in capture_runner_sha256)):
        raise FastRecipeError("capture runner hash is invalid")
    if previous_recipe_sha256 is not None and (
            not isinstance(previous_recipe_sha256, str) or len(previous_recipe_sha256) != 64 or
            any(c not in "0123456789abcdef" for c in previous_recipe_sha256)):
        raise FastRecipeError("previous recipe hash is invalid")

    start_angle = float(cycle_start_snapshot["crank_angle_unwrapped_deg"])
    cursor = start_angle
    schedule = []
    for index, row in enumerate(accepted_steps):
        if not isinstance(row, dict):
            raise FastRecipeError(f"accepted step {index} is not an object")
        dt = row.get("dt_s")
        delta = row.get("delta_angle_deg")
        angle = row.get("angle_start_deg")
        if not all(_is_finite_number(value) for value in (dt, delta, angle)) or dt <= 0 or delta <= 0:
            raise FastRecipeError(f"accepted step {index} has invalid time/angle")
        if float(angle) != cursor:
            raise FastRecipeError(f"accepted step {index} schedule is discontinuous")
        schedule.append({"angle_start_deg": float(angle), "delta_angle_deg": float(delta),
                         "dt_s": float(dt)})
        cursor += float(delta)
    expected_end = float(cycle_index * 360)
    if cursor != expected_end:
        raise FastRecipeError("accepted schedule does not terminate at the cycle boundary")
    if (_terminal_projection(terminal_state).get("cycle") != cycle_index or
            _terminal_projection(terminal_state).get("crank_angle_unwrapped_deg") != expected_end):
        raise FastRecipeError("terminal state does not match the recipe cycle boundary")
    for index, rejected in enumerate(rejected_trials):
        if (not isinstance(rejected, dict) or
                not _is_finite_number(rejected.get("angle_deg")) or
                not _is_finite_number(rejected.get("attempted_step_deg")) or
                rejected["attempted_step_deg"] <= 0 or
                not isinstance(rejected.get("reason"), str)):
            raise FastRecipeError(f"rejected trial {index} is invalid")

    recipe = {
        "schema": RECIPE_SCHEMA,
        "implementation_version": IMPLEMENTATION_VERSION,
        "status": "CAPTURED_UNAUDITED",
        "cycle_index": cycle_index,
        "configuration": copy.deepcopy(configuration),
        "configuration_sha256": sha256(canonical_bytes(configuration)),
        "solver_dependency_hashes": _solver_dependency_hashes(),
        "capture_runner_sha256": capture_runner_sha256,
        "cycle_start_snapshot": copy.deepcopy(cycle_start_snapshot),
        "cycle_start_snapshot_sha256": sha256(canonical_bytes(cycle_start_snapshot)),
        "accepted_steps": schedule,
        "rejected_trials": copy.deepcopy(rejected_trials),
        "terminal_state": copy.deepcopy(terminal_state),
        "terminal_state_sha256": sha256(canonical_bytes(terminal_state)),
        "next_cycle_checkpoint": copy.deepcopy(next_cycle_checkpoint),
        "next_cycle_checkpoint_sha256": sha256(canonical_bytes(next_cycle_checkpoint)),
        "previous_recipe_sha256": previous_recipe_sha256,
        "periodicity_source": "CANONICAL_PRIMARY_RECONSTRUCTION_REQUIRED",
        "checkpoint_scope": "COMPLETE_CYCLE_BOUNDARY",
    }
    recipe["recipe_sha256"] = sha256(canonical_bytes(recipe))
    return recipe


def validate_recipe(recipe: dict[str, Any], *, configuration: dict[str, Any] | None = None) -> None:
    if not isinstance(recipe, dict) or recipe.get("schema") != RECIPE_SCHEMA:
        raise FastRecipeError("recipe schema mismatch")
    if recipe.get("implementation_version") != IMPLEMENTATION_VERSION:
        raise FastRecipeError("recipe implementation identity mismatch")
    digest = recipe.get("recipe_sha256")
    payload = {key: value for key, value in recipe.items() if key != "recipe_sha256"}
    if not isinstance(digest, str) or sha256(canonical_bytes(payload)) != digest:
        raise FastRecipeError("recipe digest mismatch")
    if recipe.get("solver_dependency_hashes") != _solver_dependency_hashes():
        raise FastRecipeError("recipe solver dependency hash mismatch")
    config = recipe.get("configuration")
    if (not isinstance(config, dict) or
            sha256(canonical_bytes(config)) != recipe.get("configuration_sha256")):
        raise FastRecipeError("recipe configuration hash mismatch")
    if configuration is not None and canonical_bytes(configuration) != canonical_bytes(config):
        raise FastRecipeError("recipe configuration is incompatible")
    engine_identity = IntegratedEngine2T.from_configuration_dict(config).configuration_identity
    start = recipe.get("cycle_start_snapshot")
    terminal = recipe.get("terminal_state")
    next_checkpoint = recipe.get("next_cycle_checkpoint")
    if (not isinstance(start, dict) or start.get("schema") !=
            IntegratedEngine2T.from_configuration_dict(config).schema or
            start.get("configuration_identity") != engine_identity or
            sha256(canonical_bytes(start)) != recipe.get("cycle_start_snapshot_sha256")):
        raise FastRecipeError("recipe cycle-start checkpoint hash mismatch")
    if (not isinstance(terminal, dict) or
            sha256(canonical_bytes(terminal)) != recipe.get("terminal_state_sha256")):
        raise FastRecipeError("recipe terminal-state hash mismatch")
    if (not isinstance(next_checkpoint, dict) or
            sha256(canonical_bytes(next_checkpoint)) !=
            recipe.get("next_cycle_checkpoint_sha256")):
        raise FastRecipeError("recipe next-cycle checkpoint hash mismatch")
    steps = recipe.get("accepted_steps")
    rejected = recipe.get("rejected_trials")
    if not isinstance(steps, list) or not steps or not isinstance(rejected, list):
        raise FastRecipeError("recipe trajectory or rejection log is missing")
    cursor = float(start.get("crank_angle_unwrapped_deg", float("nan")))
    for index, row in enumerate(steps):
        if (not isinstance(row, dict) or row.get("angle_start_deg") != cursor or
                not _is_finite_number(row.get("delta_angle_deg")) or
                not _is_finite_number(row.get("dt_s")) or
                row["delta_angle_deg"] <= 0 or row["dt_s"] <= 0):
            raise FastRecipeError(f"recipe accepted schedule invalid at step {index}")
        cursor += row["delta_angle_deg"]
    if cursor != float(recipe.get("cycle_index", -1) * 360):
        raise FastRecipeError("recipe accepted schedule does not close its cycle")
    if recipe.get("status") not in {"CAPTURED_UNAUDITED", "AUDITED"}:
        raise FastRecipeError("recipe status is invalid")
    for index, row in enumerate(rejected):
        if (not isinstance(row, dict) or not _is_finite_number(row.get("angle_deg")) or
                not _is_finite_number(row.get("attempted_step_deg")) or
                row["attempted_step_deg"] <= 0 or not isinstance(row.get("reason"), str)):
            raise FastRecipeError(f"recipe rejected trial invalid at row {index}")
    expected_rejections = int(start.get("rejected_steps", -1)) + sum(
        "CFL limit exceeded" in row["reason"] for row in rejected)
    if _terminal_projection(terminal).get("rejected_steps") != expected_rejections:
        raise FastRecipeError("recipe rejection ledger differs from rejected-attempt log")
    if (_terminal_projection(terminal).get("cycle") != recipe.get("cycle_index") or
            _terminal_projection(terminal).get("crank_angle_unwrapped_deg") != cursor):
        raise FastRecipeError("recipe terminal clock does not match accepted schedule")
    checkpoint_engine = IntegratedEngine2T.from_configuration_dict(config)
    try:
        checkpoint_engine.restore(next_checkpoint)
    except (ValueError, TypeError, KeyError) as exc:
        raise FastRecipeError(f"recipe next-cycle checkpoint is not restorable: {exc}") from exc
    checkpoint_state = _terminal_projection(next_checkpoint)
    terminal_state_projection = _terminal_projection(terminal)
    for projection in (checkpoint_state, terminal_state_projection):
        projection.pop("accepted_steps", None)
        projection.pop("rejected_steps", None)
    if (next_checkpoint.get("cycle") != recipe.get("cycle_index") or
            next_checkpoint.get("accepted_steps") != 0 or
            next_checkpoint.get("rejected_steps") != 0 or
            next_checkpoint.get("trace") != [] or
            canonical_bytes(checkpoint_state) != canonical_bytes(terminal_state_projection)):
        raise FastRecipeError("recipe next-cycle checkpoint differs from terminal state")


def reconstruct_primary(recipe: dict[str, Any]) -> dict[str, Any]:
    """Replay a validated recipe and rebuild its canonical V3 primary."""
    validate_recipe(recipe)
    engine = IntegratedEngine2T.from_configuration_dict(recipe["configuration"])
    engine.restore(recipe["cycle_start_snapshot"])
    for index, row in enumerate(recipe["accepted_steps"]):
        result = engine.step(row["dt_s"], row["delta_angle_deg"], capture_trace=True)
        if (result["angle_start_deg"] != row["angle_start_deg"] or
                result["angle_end_deg"] != row["angle_start_deg"] + row["delta_angle_deg"]):
            raise FastRecipeError(f"replay clock mismatch at accepted step {index}")
    # Accepted-step replay does not spend the rejected CFL proposals again;
    # their full schedule is bound here and independently re-exercised by the
    # existing primary auditor before the recipe may become audited.
    engine.rejected_steps += sum(
        "CFL limit exceeded" in row["reason"]
        for row in recipe["rejected_trials"])
    end = engine.snapshot()
    if canonical_bytes(_terminal_projection(end)) != canonical_bytes(
            _terminal_projection(recipe["terminal_state"])):
        raise FastRecipeError("replayed terminal state/ledger differs from captured recipe")
    primary = make_integrated_cycle_primary(
        engine, recipe["cycle_start_snapshot"], end, recipe["cycle_index"],
        rejected_trials=recipe["rejected_trials"],
        runner_sha256=recipe["capture_runner_sha256"])
    return primary


def reconstruct_and_audit(recipe: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Replay a validated recipe, rebuild the canonical primary, then audit it."""
    primary = reconstruct_primary(recipe)
    audit = audit_integrated_cycle_primary(primary)
    if audit.get("recomputed") is not True:
        raise FastRecipeError("canonical primary failed independent replay audit")
    return primary, audit


def write_recipe_atomic(path: str | Path, recipe: dict[str, Any]) -> str:
    """Persist a validated recipe atomically and return its byte hash."""
    validate_recipe(recipe)
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = (json.dumps(recipe, sort_keys=True, indent=2, ensure_ascii=False,
                          allow_nan=False) + "\n").encode("utf-8")
    fd, temp_name = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".tmp",
                                     dir=target.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_name, target)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)
    return sha256(payload)


def read_recipe(path: str | Path, *, expected_file_sha256: str | None = None) -> dict[str, Any]:
    payload = Path(path).read_bytes()
    if expected_file_sha256 is not None and sha256(payload) != expected_file_sha256:
        raise FastRecipeError("recipe artifact hash mismatch")
    try:
        value = json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise FastRecipeError(f"recipe JSON is invalid: {exc}") from exc
    validate_recipe(value)
    return value
