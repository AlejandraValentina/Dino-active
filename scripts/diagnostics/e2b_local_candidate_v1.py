"""Bounded E2B local-candidate benchmark and equivalence harness.

Runs the frozen A44/B44 configurations with the exact E2B step loop
(capture_trace=False, 0.5 deg nominal, 25 retries), measures solver/wall time,
and records a canonical final snapshot for numeric equivalence. It does not
audit primaries, detect periodicity, or promote a candidate.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from motorsim.integrated_2t import (
    IntegratedEngine2T,
    _integrated_nominal_step_end,
    _integrated_scheduled_angles,
)
from motorsim.port_connection_v2 import NoAdmissiblePortState

CONFIGURATIONS = {
    "A": "results/e2-spatial-waves-v1/preparation/A44.json",
    "B": "results/e2-spatial-waves-v1/preparation/B44.json",
}
SOURCE_FILES = (
    "motorsim/integrated_2t.py",
    "motorsim/port_connection_v2.py",
    "motorsim/gas1d/eos.py",
    "motorsim/gas1d/exact_riemann_reference_v1.py",
    "motorsim/gas1d/spatial_reconstruction_v1.py",
    "motorsim/gas1d/spatial_reconstruction_v2.py",
)
RETRY_LIMIT = 25
RETRY_TOKENS = (
    "CFL limit exceeded",
    "inadmissible species mass",
    "rho/p/Y inadmissible",
)
OUT = ROOT / "results/predictive-reliability-v1/e2b-local-candidate-v1"


def _sha_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _source_sha(path: Path) -> str:
    return _sha_bytes(path.read_bytes().replace(b"\r\n", b"\n"))


def _canonical(value) -> str:
    return json.dumps(value, allow_nan=False, sort_keys=True, separators=(",", ":"))


def _write(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".partial")
    temporary.write_text(
        json.dumps(value, allow_nan=False, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _run(variant: str, cycles: int, mode: str) -> dict:
    import psutil

    config_path = ROOT / CONFIGURATIONS[variant]
    config = json.loads(config_path.read_text(encoding="utf-8"))
    engine = IntegratedEngine2T.from_configuration_dict(config)
    root_solver = "brent" if mode == "candidate" else "bisection"
    engine.port_root_solver = root_solver
    target = 360.0 * cycles
    schedule = _integrated_scheduled_angles(engine, target)
    process = psutil.Process()
    peak_rss = 0.0
    cycle_rows = []
    accepted = 0
    rejected_trials = 0
    rejected_reasons = []
    solver_s = 0.0
    wall_start = time.perf_counter()
    for cycle in range(1, cycles + 1):
        cycle_start = time.perf_counter()
        cycle_solver = 0.0
        while engine.crank_angle_unwrapped_deg < 360.0 * cycle - 1e-9:
            peak_rss = max(peak_rss, process.memory_info().rss / 1024**2)
            nominal_end = _integrated_nominal_step_end(
                engine, engine.crank_angle_unwrapped_deg, target, schedule)
            delta = min(360.0 * cycle, nominal_end) - engine.crank_angle_unwrapped_deg
            if delta <= 0.0:
                raise RuntimeError("non-positive step increment")
            rejected = []
            for _ in range(RETRY_LIMIT):
                start = time.perf_counter()
                try:
                    engine.step(delta / 54000.0, delta, capture_trace=False)
                except NoAdmissiblePortState:
                    raise
                except ValueError as exc:
                    if not any(token in str(exc) for token in RETRY_TOKENS):
                        raise
                    rejected.append({"step_deg": delta, "error": str(exc)})
                    delta *= 0.5
                else:
                    accepted += 1
                    rejected_trials += len(rejected)
                    rejected_reasons.extend(item["error"] for item in rejected)
                    elapsed = time.perf_counter() - start
                    solver_s += elapsed
                    cycle_solver += elapsed
                    break
                finally:
                    pass
            else:
                raise RuntimeError("25 rejected proposals in bounded candidate run")
        engine.compact_fast_recipe_cycle()
        snapshot = engine.snapshot()
        cycle_rows.append({
            "cycle": cycle,
            "wall_s": time.perf_counter() - cycle_start,
            "solver_s": cycle_solver,
            "accepted_steps": accepted,
            "snapshot_sha256": _sha_bytes(_canonical(snapshot).encode("utf-8")),
        })
    wall_s = time.perf_counter() - wall_start
    snapshot = engine.snapshot()
    return {
        "schema": "DINO_E2B_LOCAL_CANDIDATE_RUN_V1",
        "recorded_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "variant": variant,
        "cycles": cycles,
        "port_root_solver": root_solver,
        "configuration": CONFIGURATIONS[variant],
        "configuration_sha256_raw": _sha_bytes(config_path.read_bytes()),
        "source_sha256_normalized_lf": {
            name: _source_sha(ROOT / name) for name in SOURCE_FILES
        },
        "accepted_steps": accepted,
        "rejected_trials": rejected_trials,
        "rejected_reasons": rejected_reasons,
        "solver_s": solver_s,
        "wall_s": wall_s,
        "seconds_per_cycle_solver": solver_s / cycles,
        "seconds_per_cycle_wall": wall_s / cycles,
        "peak_rss_mib": peak_rss,
        "cycles_detail": cycle_rows,
        "conservation": engine.conservation_report(),
        "ledger": dict(engine.ledger),
        "initial_inventory": engine.initial_inventory,
        "snapshot": snapshot,
        "snapshot_sha256": _sha_bytes(_canonical(snapshot).encode("utf-8")),
    }


def _replay(variant: str) -> dict:
    candidate_path = OUT / f"candidate-{variant}.json"
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    config_path = ROOT / CONFIGURATIONS[variant]
    config = json.loads(config_path.read_text(encoding="utf-8"))

    def run(root_solver):
        engine = IntegratedEngine2T.from_configuration_dict(config)
        engine.port_root_solver = root_solver
        engine.restore(json.loads(json.dumps(candidate["snapshot"])))
        before = engine.snapshot()
        engine.step(1e-8, .00006, capture_trace=False)
        engine.compact_fast_recipe_cycle()
        return before, engine.snapshot()

    before_fast, fast_a = run("brent")
    _, fast_b = run("brent")
    _, bisection = run("bisection")
    fast_hash = _sha_bytes(_canonical(fast_a).encode("utf-8"))
    bisection_hash = _sha_bytes(_canonical(bisection).encode("utf-8"))
    return {
        "schema": "DINO_E2B_LOCAL_CANDIDATE_REPLAY_V1",
        "recorded_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "variant": variant,
        "candidate": str(candidate_path.relative_to(ROOT)),
        "configuration": CONFIGURATIONS[variant],
        "configuration_sha256_raw": _sha_bytes(config_path.read_bytes()),
        "source_sha256_normalized_lf": {
            name: _source_sha(ROOT / name) for name in SOURCE_FILES
        },
        "restore_exact": _canonical(before_fast) == _canonical(candidate["snapshot"]),
        "fast_replay_exact": _canonical(fast_a) == _canonical(fast_b),
        "bisection_replay_exact": _canonical(fast_a) == _canonical(bisection),
        "fast_snapshot_sha256": fast_hash,
        "bisection_snapshot_sha256": bisection_hash,
    }


def _compare(left, right, path="", diffs=None, limit=20) -> list[dict]:
    if diffs is None:
        diffs = []
    if len(diffs) >= limit:
        return diffs
    if isinstance(left, dict) and isinstance(right, dict):
        for key in sorted(set(left) | set(right)):
            if key in ("recorded_at_utc", "source_sha256_normalized_lf", "solver_s",
                       "wall_s", "seconds_per_cycle_solver", "seconds_per_cycle_wall",
                       "cycles_detail", "peak_rss_mib", "configuration_sha256_raw",
                       "snapshot_sha256", "port_root_solver"):
                continue
            if key not in left or key not in right:
                diffs.append({"path": f"{path}.{key}", "kind": "missing"})
                continue
            _compare(left[key], right[key], f"{path}.{key}", diffs, limit)
        return diffs
    if isinstance(left, list) and isinstance(right, list):
        if len(left) != len(right):
            diffs.append({"path": path, "kind": "length", "left": len(left), "right": len(right)})
            return diffs
        for index, (a, b) in enumerate(zip(left, right)):
            _compare(a, b, f"{path}[{index}]", diffs, limit)
        return diffs
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        if not math.isfinite(float(left)) or not math.isfinite(float(right)):
            if left != right:
                diffs.append({"path": path, "kind": "nonfinite", "left": left, "right": right})
            return diffs
        absolute = abs(float(left) - float(right))
        scale = max(1.0, abs(float(left)), abs(float(right)))
        relative = absolute / scale
        if absolute > 1e-10 + 1e-10*max(abs(float(left)), abs(float(right))):
            diffs.append({
                "path": path,
                "kind": "numeric",
                "left": left,
                "right": right,
                "absolute": absolute,
                "relative": relative,
            })
        return diffs
    if left != right:
        diffs.append({"path": path, "kind": "value", "left": left, "right": right})
    return diffs


def _numeric_extrema(left, right, path="", acc=None) -> dict:
    if acc is None:
        acc = {"max_absolute": 0.0, "max_absolute_path": None,
               "max_relative": 0.0, "max_relative_path": None}
    ignored = {
        "recorded_at_utc", "source_sha256_normalized_lf", "solver_s", "wall_s",
        "seconds_per_cycle_solver", "seconds_per_cycle_wall", "cycles_detail",
        "peak_rss_mib", "configuration_sha256_raw", "snapshot_sha256",
        "port_root_solver",
    }
    if isinstance(left, dict) and isinstance(right, dict):
        for key in sorted(set(left) & set(right)):
            if key not in ignored:
                _numeric_extrema(left[key], right[key], f"{path}.{key}", acc)
        return acc
    if isinstance(left, list) and isinstance(right, list) and len(left) == len(right):
        for index, (a, b) in enumerate(zip(left, right)):
            _numeric_extrema(a, b, f"{path}[{index}]", acc)
        return acc
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        absolute = abs(float(left) - float(right))
        relative = absolute / max(1.0, abs(float(left)), abs(float(right)))
        if absolute > acc["max_absolute"]:
            acc["max_absolute"] = absolute
            acc["max_absolute_path"] = path
        if relative > acc["max_relative"]:
            acc["max_relative"] = relative
            acc["max_relative_path"] = path
    return acc


def _compare_files(baseline_path: Path, candidate_path: Path) -> dict:
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    diffs = _compare(baseline, candidate)
    extrema = _numeric_extrema(baseline, candidate)
    return {
        "schema": "DINO_E2B_LOCAL_CANDIDATE_COMPARISON_V1",
        "baseline": str(baseline_path.resolve().relative_to(ROOT)),
        "candidate": str(candidate_path.resolve().relative_to(ROOT)),
        "snapshot_exact": baseline["snapshot_sha256"] == candidate["snapshot_sha256"],
        "comparison_tolerance": "abs <= 1e-10 + 1e-10*max(|a|,|b|) for numeric fields",
        "max_numeric_difference": extrema,
        "max_differences": diffs,
        "equivalent_at_tolerance": not diffs,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("baseline", "candidate", "compare", "replay"))
    parser.add_argument("--variant", choices=("A", "B", "both"), default="both")
    parser.add_argument("--cycles", type=int, default=2)
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--candidate", type=Path)
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args()
    if args.mode == "compare":
        if not args.baseline or not args.candidate:
            parser.error("compare requires --baseline and --candidate")
        result = _compare_files(args.baseline, args.candidate)
        _write(args.out / "comparison.json", result)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    variants = ("A", "B") if args.variant == "both" else (args.variant,)
    if args.cycles <= 0:
        parser.error("--cycles must be positive")
    for variant in variants:
        if args.mode == "replay":
            result = _replay(variant)
            path = args.out / f"replay-{variant}.json"
            _write(path, result)
            print(json.dumps({
                "mode": args.mode,
                "variant": variant,
                "restore_exact": result["restore_exact"],
                "fast_replay_exact": result["fast_replay_exact"],
                "bisection_replay_exact": result["bisection_replay_exact"],
                "fast_snapshot_sha256": result["fast_snapshot_sha256"],
                "path": str(path.relative_to(ROOT)),
            }, ensure_ascii=False))
            continue
        result = _run(variant, args.cycles, args.mode)
        path = args.out / f"{args.mode}-{variant}.json"
        _write(path, result)
        print(json.dumps({
            "mode": args.mode,
            "variant": variant,
            "cycles": args.cycles,
            "solver_s": result["solver_s"],
            "wall_s": result["wall_s"],
            "seconds_per_cycle_solver": result["seconds_per_cycle_solver"],
            "accepted_steps": result["accepted_steps"],
            "rejected_trials": result["rejected_trials"],
            "peak_rss_mib": result["peak_rss_mib"],
            "snapshot_sha256": result["snapshot_sha256"],
            "path": str(path.relative_to(ROOT)),
        }, ensure_ascii=False))
    print("PASS")


if __name__ == "__main__":
    main()
