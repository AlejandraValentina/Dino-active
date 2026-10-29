"""Compare bisection and opt-in Brent from the same preserved 176-cell state.

This is a fixed three-cycle performance/equivalence comparison. It does not
evaluate periodicity or alter any physical/numerical acceptance parameter.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import time
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from motorsim.integrated_2t import (
    IntegratedEngine2T,
    _integrated_nominal_step_end,
    _integrated_scheduled_angles,
    _solver_dependency_hashes,
)
from motorsim.port_connection_v2 import NoAdmissiblePortState
from scripts.agents.storage_preflight import check_storage_requirements, default_artifact_root
from scripts.diagnostics.diagnose_integrated_mesh_v1 import write
from scripts.diagnostics.periodicity_extension_v4 import conserved

CONFIG_SHA256 = "4e8c01987424c0dae3b12a3af456dcbb951e43a992b2278f539bafdedf56ad73"
CHECKPOINT_SHA256 = "5a7ae79230c251d5b277238ef79e5e3ee050d59304c186e4d913c6f9a744085a"
MAX_TOTAL_WALL_S = 660.0
ROOT_SOLVERS = ("bisection", "brent")
RETRY_TOKENS = ("CFL limit exceeded", "inadmissible species mass", "rho/p/Y inadmissible")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical(value) -> str:
    return json.dumps(value, ensure_ascii=False, allow_nan=False,
                      sort_keys=True, separators=(",", ":"))


def compare(left, right, path="", diffs=None, limit=100):
    if diffs is None:
        diffs = []
    if len(diffs) >= limit:
        return diffs
    if isinstance(left, dict) and isinstance(right, dict):
        for key in sorted(set(left) | set(right)):
            if key in {"recorded_at", "timing", "root_solver"}:
                continue
            if key not in left or key not in right:
                diffs.append({"path": f"{path}.{key}", "kind": "missing"})
            else:
                compare(left[key], right[key], f"{path}.{key}", diffs, limit)
        return diffs
    if isinstance(left, list) and isinstance(right, list):
        if len(left) != len(right):
            diffs.append({"path": path, "kind": "length", "left": len(left), "right": len(right)})
        else:
            for i, (a, b) in enumerate(zip(left, right)):
                compare(a, b, f"{path}[{i}]", diffs, limit)
        return diffs
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        import math
        if not math.isfinite(float(left)) or not math.isfinite(float(right)):
            if left != right:
                diffs.append({"path": path, "kind": "nonfinite"})
            return diffs
        if abs(float(left) - float(right)) > 1e-10 + 1e-10 * max(abs(float(left)), abs(float(right))):
            diffs.append({"path": path, "kind": "numeric", "left": left, "right": right,
                          "absolute": abs(float(left) - float(right))})
        return diffs
    if left != right:
        diffs.append({"path": path, "kind": "value", "left": left, "right": right})
    return diffs


def resolve_inputs(artifact_root: Path):
    source = artifact_root / "predictive-reliability-v1" / "candidate-periodic-gci-v1" / "window-176-02"
    config_path = source / "configuration.json"
    checkpoint_path = source / "checkpoint-absolute-037.json"
    if sha(config_path) != CONFIG_SHA256 or sha(checkpoint_path) != CHECKPOINT_SHA256:
        raise ValueError("preserved 176 config/checkpoint hash differs")
    config = json.loads(config_path.read_text(encoding="utf-8"))
    checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    return source, config_path, checkpoint_path, config, checkpoint


def _new_engine(config, checkpoint):
    engine = IntegratedEngine2T.from_configuration_dict(config)
    engine.restore(deepcopy(checkpoint))
    expected_cycle = int(checkpoint["cycle"])
    if engine.cycle != expected_cycle or engine.crank_angle_unwrapped_deg != 360.0 * expected_cycle:
        raise ValueError("restored state cycle/angle differs from checkpoint")
    if canonical(engine.snapshot()) != canonical(checkpoint):
        raise ValueError("cycle-37 restore does not round-trip exactly")
    return engine


def _elapsed(total_start: float, prior_consumed_wall_s: float) -> float:
    return prior_consumed_wall_s + time.perf_counter() - total_start


def _run_one(name, config, checkpoint, output: Path, total_start: float,
             prior_consumed_wall_s: float, resume_checkpoint=None,
             resume_cycle_wall_s=0.0, resume_checkpoint_sha256=None):
    if _elapsed(total_start, prior_consumed_wall_s) >= MAX_TOTAL_WALL_S:
        raise TimeoutError("660-second cumulative E2 budget reached before second execution")
    case_start = time.perf_counter()
    engine = _new_engine(config, checkpoint)
    engine.port_root_solver = name
    case_output = output / name
    case_output.mkdir(parents=True, exist_ok=False)
    start_snapshot = engine.snapshot()
    cycles = []
    first_cycle = 38
    if resume_checkpoint is not None:
        engine.restore(deepcopy(resume_checkpoint))
        if engine.cycle != 38 or engine.crank_angle_unwrapped_deg != 13680.0:
            raise ValueError("resumed bisection checkpoint is not absolute cycle 38")
        cycles.append({
            "absolute_cycle": 38,
            "angle_deg": engine.crank_angle_unwrapped_deg,
            "steps_cumulative": None,
            "solver_s": None,
            "cycle_wall_s": resume_cycle_wall_s,
            "checkpoint_sha256": resume_checkpoint_sha256,
            "conservation": engine.conservation_report(),
            "timing_qualification": "completed cycle from preserved interrupted attempt; solver-only timing unavailable",
        })
        write(case_output / "checkpoint-absolute-038.json", resume_checkpoint)
        first_cycle = 39
    target_angle = 40 * 360.0
    schedule = _integrated_scheduled_angles(engine, target_angle)
    solver_s = 0.0
    accepted_steps = 0
    rejected_steps = 0
    for absolute_cycle in range(first_cycle, 41):
        cycle_start = time.perf_counter()
        cycle_solver_s = 0.0
        while engine.crank_angle_unwrapped_deg < 360.0 * absolute_cycle - 1e-9:
            elapsed_total = _elapsed(total_start, prior_consumed_wall_s)
            if elapsed_total >= MAX_TOTAL_WALL_S:
                raise TimeoutError("660-second cumulative E2 budget reached; stopping current execution")
            end = _integrated_nominal_step_end(
                engine, engine.crank_angle_unwrapped_deg, target_angle, schedule)
            delta = min(360.0 * absolute_cycle, end) - engine.crank_angle_unwrapped_deg
            rejected = []
            for _ in range(25):
                step_start = time.perf_counter()
                try:
                    engine.step(delta / (6 * 9000.0), delta, capture_trace=False)
                except NoAdmissiblePortState:
                    raise
                except ValueError as exc:
                    if not any(token in str(exc) for token in RETRY_TOKENS):
                        raise
                    rejected.append(str(exc))
                    delta *= 0.5
                else:
                    elapsed_step = time.perf_counter() - step_start
                    solver_s += elapsed_step
                    cycle_solver_s += elapsed_step
                    accepted_steps += 1
                    rejected_steps += len(rejected)
                    if _elapsed(total_start, prior_consumed_wall_s) >= MAX_TOTAL_WALL_S:
                        raise TimeoutError("660-second cumulative E2 budget reached after solver step")
                    break
            else:
                raise RuntimeError("25 rejected step proposals")
        engine.compact_fast_recipe_cycle()
        snapshot = engine.snapshot()
        balance = engine.conservation_report()
        if not conserved(balance):
            raise ValueError(f"{name} conservation failed at cycle {absolute_cycle}")
        checkpoint_path = case_output / f"checkpoint-absolute-{absolute_cycle:03}.json"
        write(checkpoint_path, snapshot)
        reread = json.loads(checkpoint_path.read_text(encoding="utf-8"))
        restored = _new_engine(config, reread)
        if canonical(restored.snapshot()) != canonical(snapshot):
            raise ValueError(f"{name} checkpoint restore differs at cycle {absolute_cycle}")
        cycles.append({
            "absolute_cycle": absolute_cycle,
            "angle_deg": engine.crank_angle_unwrapped_deg,
            "steps_cumulative": accepted_steps,
            "solver_s": cycle_solver_s,
            "cycle_wall_s": time.perf_counter() - cycle_start,
            "checkpoint_sha256": sha(checkpoint_path),
            "conservation": balance,
        })
        write(case_output / "cycles.json", cycles)
        if _elapsed(total_start, prior_consumed_wall_s) > MAX_TOTAL_WALL_S:
            raise TimeoutError("660-second cumulative E2 budget exceeded after result write")
    final = engine.snapshot()
    final_path = case_output / "final-checkpoint.json"
    write(final_path, final)
    case_wall = time.perf_counter() - case_start + resume_cycle_wall_s
    result = {
        "schema": "DINO_E2B_ROOT_SOLVER_176_COMPARISON_RUN_V1",
        "root_solver": name,
        "source_configuration_sha256": CONFIG_SHA256,
        "source_cycle37_checkpoint_sha256": CHECKPOINT_SHA256,
        "initial_snapshot_sha256": hashlib.sha256(canonical(start_snapshot).encode()).hexdigest(),
        "final_snapshot": final,
        "final_snapshot_sha256": hashlib.sha256(canonical(final).encode()).hexdigest(),
        "final_checkpoint_sha256": sha(final_path),
        "cycles": cycles,
        "accepted_steps": accepted_steps,
        "rejected_steps": rejected_steps,
        "solver_s": solver_s,
        "solver_cycles_measured": sum(row.get("solver_s") is not None for row in cycles),
        "solver_s_per_cycle_measured": solver_s / max(
            1, sum(row.get("solver_s") is not None for row in cycles)),
        "case_wall_s_including_initialization_restore_and_writes": case_wall,
        "conservation": engine.conservation_report(),
        "solver_dependency_sha256": _solver_dependency_hashes(),
    }
    write(case_output / "result.json", result)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-root", type=Path, default=default_artifact_root())
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--preflight", type=Path, required=True)
    parser.add_argument("--prior-consumed-wall-s", type=float, default=0.0)
    parser.add_argument("--resume-bisection-checkpoint", type=Path)
    args = parser.parse_args(argv)
    total_start = time.perf_counter()
    preflight = json.loads(args.preflight.read_text(encoding="utf-8"))
    if (preflight.get("schema") != "DINO_E2B_ROOT_SOLVER_176_PREFLIGHT_V1" or
            preflight.get("solver_steps_executed") != 0 or
            preflight.get("configuration_sha256") != CONFIG_SHA256 or
            preflight.get("checkpoint_sha256") != CHECKPOINT_SHA256 or
            preflight.get("prior_consumed_wall_s") != args.prior_consumed_wall_s):
        raise ValueError("E2 176 preflight is missing or does not bind the preserved inputs")
    if args.output.exists():
        raise FileExistsError("preserve existing comparison output")
    _, config_path, checkpoint_path, config, checkpoint = resolve_inputs(args.artifact_root)
    if config_path.stat().st_size != 131125 or checkpoint_path.stat().st_size != 181258:
        raise ValueError("preserved source artifact size differs")
    if sum(len(duct["mesh"]["volumes"]) for duct in config["ducts"]) != 176:
        raise ValueError("source configuration is not the preserved 176-cell case")
    if not preflight.get("storage_preflight", {}).get("status") == "PASS":
        raise ValueError("storage preflight did not pass")
    resume_checkpoint = None
    resume_cycle_wall_s = 0.0
    resume_checkpoint_sha256 = None
    if args.resume_bisection_checkpoint:
        resume_checkpoint_sha256 = sha(args.resume_bisection_checkpoint)
        if resume_checkpoint_sha256 != preflight.get("resume_checkpoint_sha256"):
            raise ValueError("resumed bisection checkpoint hash differs from preflight")
        resume_checkpoint = json.loads(args.resume_bisection_checkpoint.read_text(encoding="utf-8"))
        if resume_checkpoint.get("cycle") != 38:
            raise ValueError("resume checkpoint must be absolute cycle 38")
        resume_cycle_wall_s = float(preflight["resume_cycle_wall_s"])
    args.output.mkdir(parents=True)
    write(args.output / "source-binding.json", {
        "configuration_sha256": CONFIG_SHA256,
        "checkpoint_sha256": CHECKPOINT_SHA256,
        "checkpoint_cycle": 37,
        "checkpoint_angle_deg": 13320.0,
        "configuration_path": str(config_path),
        "checkpoint_path": str(checkpoint_path),
        "solver_dependency_sha256": _solver_dependency_hashes(),
    })
    results = []
    error = None
    status = "PASS"
    try:
        for mode in ROOT_SOLVERS:
            results.append(_run_one(mode, config, checkpoint, args.output, total_start,
                                    args.prior_consumed_wall_s,
                                    resume_checkpoint if mode == "bisection" else None,
                                    resume_cycle_wall_s if mode == "bisection" else 0.0,
                                    resume_checkpoint_sha256 if mode == "bisection" else None))
    except Exception as exc:
        status = "FAIL" if isinstance(exc, TimeoutError) else "ERROR"
        error = f"{type(exc).__name__}: {exc}"
    differences = compare(results[0]["final_snapshot"], results[1]["final_snapshot"]) if len(results) == 2 else []
    if len(results) == 2 and differences:
        status = "DIVERGENCE"
    initial_states_equal = len(results) == 2 and results[0]["initial_snapshot_sha256"] == results[1]["initial_snapshot_sha256"]
    common_cycles = []
    speedup = None
    if len(results) == 2:
        left = {row["absolute_cycle"]: row.get("solver_s") for row in results[0]["cycles"]}
        right = {row["absolute_cycle"]: row.get("solver_s") for row in results[1]["cycles"]}
        common_cycles = sorted(c for c in set(left) & set(right)
                               if left[c] is not None and right[c] is not None)
        right_total = sum(right[c] for c in common_cycles)
        if common_cycles and right_total > 0:
            speedup = sum(left[c] for c in common_cycles) / right_total
    total_wall = _elapsed(total_start, args.prior_consumed_wall_s)
    if total_wall > MAX_TOTAL_WALL_S:
        status = "FAIL_BUDGET_EXCEEDED"
        error = error or "cumulative execution exceeded 660 seconds"
    final = {
        "schema": "DINO_E2B_ROOT_SOLVER_176_COMPARISON_V1",
        "status": status,
        "error": error,
        "runs_completed": [r["root_solver"] for r in results],
        "equivalent_initial_states": initial_states_equal,
        "final_state_differences": differences,
        "numeric_equivalence_tolerance": "abs(a-b) <= 1e-10 + 1e-10*max(abs(a),abs(b))",
        "solver_speedup_bisection_over_brent": speedup,
        "speedup_common_completed_cycles": common_cycles,
        "total_wall_s_including_initialization_restore_calculation_and_writes": total_wall,
        "authorized_total_wall_s": MAX_TOTAL_WALL_S,
        "prior_failed_attempt_wall_s": args.prior_consumed_wall_s,
        "runs": [{k: v for k, v in r.items() if k != "final_snapshot"} for r in results],
        "periodicity_searched": False,
        "physics_or_tolerances_modified": False,
    }
    if total_wall > MAX_TOTAL_WALL_S:
        final["status"] = "FAIL_BUDGET_EXCEEDED"
        final["error"] = final["error"] or "cumulative execution exceeded 660 seconds including result serialization"
    serialized_write_start = time.perf_counter()
    write(args.output / "comparison.json", final)
    one_write_s = time.perf_counter() - serialized_write_start
    # Conservatively budget one more final-manifest write of approximately the
    # same size; the updated manifest itself records this bound.
    final["total_wall_s_including_initialization_restore_calculation_and_writes"] += one_write_s
    if final["total_wall_s_including_initialization_restore_calculation_and_writes"] > MAX_TOTAL_WALL_S:
        final["status"] = "FAIL_BUDGET_EXCEEDED"
        final["error"] = final["error"] or "cumulative execution plus final manifest write margin exceeded 660 seconds"
    write(args.output / "comparison.json", final)
    print(json.dumps({k: final[k] for k in ("status", "runs_completed", "equivalent_initial_states",
                                             "solver_speedup_bisection_over_brent",
                                             "total_wall_s_including_initialization_restore_calculation_and_writes",
                                             "error")}, ensure_ascii=False))
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
