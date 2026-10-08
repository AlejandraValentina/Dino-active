"""Durable G2-v2 acquisition. The compact-only 2026-09-29 run remains historical."""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
import platform
import sys
import time
from pathlib import Path

import numba
import numpy

from dev_orchestrator.p4_hybrid import checks, prepare
from motorsim.hybrid_fast import run_cycle
from motorsim.periodicity import PeriodicityDetector, compare_cycles

ROOT = Path("results/p4-g2-v2-ledger-recovery-20260929-retry")
HIST = Path("results/p4-g2-periodic-completion-20260923")
EARLY = Path("results/p4-r6-20260921/artifacts/g2_cycles")
MAX_CYCLES = 400
SCHEMA = "G2_V2_DURABLE_V1"
DETECTOR_SCHEMA = "E13_R1_DETECTOR_V1"
CONSERVATION_LEDGER_SCHEMA = "G2_CONSERVATION_LEDGER_V1"
RUNTIME_SOURCES = (
    "motorsim/hybrid_fast.py", "motorsim/exhaust_numba_fused.py",
    "motorsim/periodicity.py", "dev_orchestrator/p4_hybrid.py",
    "dev_orchestrator/p4_g2_v2_recovery.py",
)
EXPECTED = {
    "configuration_hash": "p4-r6-g2-chain", "scientific_contract_id": "E13-R1",
    "solver": "NUMBA_FUSED", "backend": "NUMBA_FUSED", "mesh": 251,
    "geometry": "chain", "rpm": 3000, "operating_point": "G2",
    "cycle_convention": "360", "anchor_cycle": 1,
    "branch_map": {"A": "odd_relative_to_anchor", "B": "even_relative_to_anchor"},
}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def native(value):
    """Convert NumPy scalar wrappers without changing their binary64 values."""
    if isinstance(value, numpy.generic):
        return value.item()
    if isinstance(value, dict):
        return {k: native(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [native(v) for v in value]
    return value


def load(path: Path) -> dict:
    return json.loads(gzip.decompress(path.read_bytes()))


def source_path(cycle: int) -> Path:
    return (EARLY / f"G2-cycle{cycle:02}.json.gz" if cycle <= 15
            else HIST / f"cycle{cycle:02}.json.gz")


def historical_row(cycle: int) -> tuple[dict, str]:
    path = source_path(cycle)
    row = load(path)
    if (row.get("begin"), row.get("end")) != (180.0 + 360.0 * (cycle - 1),
                                               180.0 + 360.0 * cycle):
        raise ValueError(f"historical cycle {cycle}: angular identity mismatch")
    for key, value in EXPECTED.items():
        if key in row and row[key] != value:
            raise ValueError(f"historical cycle {cycle}: {key} mismatch")
        row[key] = value
    row["cycle"] = cycle
    calculated = checks(row)
    if row.get("checks") is not None and row["checks"] != calculated:
        raise ValueError(f"historical cycle {cycle}: physical checks mismatch")
    row["checks"] = calculated
    if physical_gate(calculated):
        raise ValueError(f"historical cycle {cycle}: physical gate failed")
    return row, sha(path.read_bytes())


def gate_inputs(row: dict) -> dict:
    return native({
        "complete": row["complete"], "global_balance": row["global_balance"],
        "segments": [{
            "physical_balance": s["physical_balance"],
            "max_global_residual": s["result"]["max_global_residual"],
            "max_stage_residual": s["result"]["max_stage_residual"],
            "extrema": s["result"]["extrema"],
            "stages": [{"dt": t["dt"], "limits": t["limits"]}
                       for t in s["result"]["stages"]],
        } for s in row["segments"]],
    })


def conservation_ledger(row: dict) -> dict | None:
    """Extract raw inventories and face/source exchanges captured by the solver."""
    segments = row.get("segments", [])
    if not segments or any("conservation_history" not in s["result"]
                           or not s["result"]["conservation_history"]
                           for s in segments):
        return None
    return native({
        "schema": CONSERVATION_LEDGER_SCHEMA,
        "control_volume": EXPECTED["geometry"],
        "topology_path": row["path"],
        "identity": EXPECTED,
        "cycle_interval_deg": [row["begin"], row["end"]],
        "components": ["mass_kg", "energy_J", "fresh_species_mass_kg"],
        "initial_inventory": row["initial_inventory"],
        "final_inventory": row["final_inventory"],
        "external_exchange": row["external"],
        "global_balance": row["global_balance"],
        "analytical_burn_species_correction": [0., 0., row["analytical_burn"]],
        "segments": [{
            "interval_deg": [s["start_angle"], s["end_angle"]],
            "initial_inventory": s["result"]["initial_inventory"],
            "final_inventory": s["result"]["final_inventory"],
            "external_exchange_raw": s["result"]["external"],
            "analytical_burn_species_correction": [0., 0., s["analytical_burn"]],
            "solver_max_stage_residual": s["result"]["max_stage_residual"],
            "solver_max_global_residual": s["result"]["max_global_residual"],
            "steps": s["result"]["conservation_history"],
        } for s in segments],
    })


def audit_inputs(row: dict) -> dict:
    """Persist E13 inputs and, for captured acquisitions, the primary ledger."""
    inputs = native({
        "cycle": row["cycle"], "begin": row["begin"], "end": row["end"],
        "identity": EXPECTED, "state": row["state"], "cells": row["cells"],
        "work_indicated_J": row["work_indicated_J"],
        "port_integral": row["port_integral"],
        "initial_cylinder_mass": row["initial_cylinder_mass"],
        "history": [{"angle": h["angle"], "p_cyl": h["p_cyl"],
                     "sensors_p_u_M_Y": [[s[0]] for s in h["sensors_p_u_M_Y"]]}
                    for h in row["history"]],
        "gate_inputs": gate_inputs(row),
    })
    ledger = conservation_ledger(row)
    if ledger is not None:
        inputs["conservation_ledger"] = ledger
    return inputs


def metric_row(inputs: dict) -> dict:
    return {**inputs, **inputs["identity"]}


def comparison(previous: dict | None, current: dict) -> dict:
    return (compare_cycles(metric_row(previous), metric_row(current)) if previous
            else {"status": "INVALID", "reason": "MISSING_PREVIOUS_CYCLE", "passed": False})


def snapshot(detector: PeriodicityDetector, cycle: int, branch: str,
             lag1: dict, lag2: dict) -> dict:
    return native({"schema": DETECTOR_SCHEMA, "last_cycle": cycle,
            "last_branch": branch, "last_lag1": lag1, "last_lag2": lag2,
            "state": detector.to_json()})


def restore_detector(saved: dict, cycle: int) -> PeriodicityDetector:
    if not isinstance(saved, dict) or saved.get("schema") != DETECTOR_SCHEMA:
        raise ValueError("detector state missing or wrong schema")
    if saved.get("last_cycle") != cycle or saved.get("last_branch") != ("A" if cycle % 2 else "B"):
        raise ValueError("detector cycle/branch mismatch")
    state = saved.get("state")
    required = ("anchor_cycle", "branch_map", "lag1_streak", "branch_A_streak",
                "branch_B_streak", "detected_period", "converged_cycle",
                "history_identity", "last_metrics")
    if not isinstance(state, dict) or any(k not in state for k in required):
        raise ValueError("incomplete detector state")
    if (state["anchor_cycle"] != 1 or state["branch_map"] != EXPECTED["branch_map"]
            or state["history_identity"] != EXPECTED):
        raise ValueError("detector scientific identity mismatch")
    if any(type(state[k]) is not int or state[k] < 0
           for k in ("lag1_streak", "branch_A_streak", "branch_B_streak")):
        raise ValueError("invalid detector streak")
    if state["detected_period"] is not None or state["converged_cycle"] is not None:
        raise ValueError("restart source already converged")
    if (not isinstance(saved.get("last_lag1"), dict)
            or not isinstance(saved.get("last_lag2"), dict)
            or state["last_metrics"] != saved["last_lag1"]):
        raise ValueError("detector comparison history mismatch")
    return PeriodicityDetector.from_json(state)


def physical_gate(gates: dict) -> str | None:
    required = ("complete", "conservation", "positive", "CFL")
    if not isinstance(gates, dict) or any(type(gates.get(k)) is not bool for k in required):
        return "INVALID_PHYSICAL_GATE"
    if not gates["complete"]:
        return "INCOMPLETE_CYCLE"
    if not gates["conservation"] or not gates["positive"]:
        return "NUMERICAL_FAILURE"
    if not gates["CFL"]:
        return "NUMERICAL_FAILURE_CFL"
    return None


def advance_detector(detector: PeriodicityDetector, inputs: dict, lag1: dict,
                     lag2: dict, branch: str, gates: dict) -> str | None:
    """Apply physical gates before any convergence transition."""
    failure = physical_gate(gates)
    if not finite_tree(inputs) or not finite_tree(lag1) or not finite_tree(lag2):
        return "INVALID_NONFINITE_EVIDENCE"
    if lag1.get("status") == "INVALID" or lag2.get("status") == "INVALID":
        return "INVALID_COMPARISON"
    if failure is None:
        detector.update(metric_row(inputs), lag1=lag1, lag2=lag2, branch=branch)
    return failure


def finite_tree(value) -> bool:
    if value is None or isinstance(value, (str, bool)):
        return True
    if isinstance(value, (float, int)):
        return math.isfinite(value)
    if isinstance(value, (list, tuple)):
        return all(finite_tree(x) for x in value)
    if isinstance(value, dict):
        return all(finite_tree(x) for x in value.values())
    return False


def checkpoint_path(root: Path, cycle: int) -> Path:
    return root / f"checkpoint_cycle{cycle:03}.json.gz"


def save_checkpoint(root: Path, cycle: int, inputs: dict, detector: dict,
                    claims: dict, parent_sha: str | None, source_sha: str | None = None) -> str:
    payload = {"schema": SCHEMA, "inputs": inputs, "detector": detector,
               "claims": claims, "parent_sha256": parent_sha,
               "source_sha256": source_sha}
    packed = gzip.compress(json.dumps(payload, allow_nan=False,
                                      separators=(",", ":")).encode(), mtime=0)
    checkpoint_path(root, cycle).write_bytes(packed)
    return sha(packed)


def prepare_seed(root: Path) -> dict:
    """Replay E13 from primary cycles 1..30; no manually assigned streaks."""
    root.mkdir(parents=True, exist_ok=False)
    detector = PeriodicityDetector(1, EXPECTED["branch_map"])
    previous2 = previous = None
    ancestry = []
    parent_sha = None
    for cycle in range(1, 31):
        row, source_sha = historical_row(cycle)
        inputs = audit_inputs(row)
        lag1, lag2 = comparison(previous, inputs), comparison(previous2, inputs)
        branch = "A" if cycle % 2 else "B"
        detector.update(metric_row(inputs), lag1=lag1, lag2=lag2, branch=branch)
        if detector.detected_period is not None:
            raise ValueError(f"historical convergence at cycle {cycle}")
        saved = snapshot(detector, cycle, branch, lag1, lag2)
        parent_sha = save_checkpoint(root, cycle, inputs, saved,
                                     {"lag1": lag1, "lag2": lag2,
                                      "checks": row["checks"]}, parent_sha, source_sha)
        ancestry.append({"cycle": cycle, "source": str(source_path(cycle)),
                         "source_sha256": source_sha, "checkpoint_sha256": parent_sha})
        previous2, previous = previous, inputs
    seed_path = root / "seed-detector-cycle030.json"
    seed_path.write_text(json.dumps(saved, indent=2, allow_nan=False), encoding="utf-8")
    manifest = {"schema": SCHEMA, "contract": "G2-v2", "identity": EXPECTED,
                "max_cycles": MAX_CYCLES,
                "thresholds": {"work": .005, "cylinder": .005, "sensor_max": .005,
                               "port": .002, "inventories": .002},
                "source_cycles": ancestry, "seed_detector_sha256": sha(seed_path.read_bytes()),
                "runtime": {"python": sys.version, "platform": platform.platform(),
                            "numpy": numpy.__version__, "numba": numba.__version__,
                            "float": "binary64", "backend": "NUMBA_FUSED", "cfl": .4,
                            "fastmath": False, "parallel": False, "workers": 1}}
    manifest["runtime"]["source_sha256"] = {
        path: sha(Path(path).read_bytes()) for path in RUNTIME_SOURCES
    }
    (root / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def run(root: Path = ROOT) -> dict:
    started = time.perf_counter()
    manifest = prepare_seed(root)
    seed_file = root / "seed-detector-cycle030.json"
    if sha(seed_file.read_bytes()) != manifest["seed_detector_sha256"]:
        raise ValueError("seed detector hash mismatch")
    detector = restore_detector(json.loads(seed_file.read_text(encoding="utf-8")), 30)
    previous2 = load(checkpoint_path(root, 29))["inputs"]
    previous = load(checkpoint_path(root, 30))["inputs"]
    parent_sha = sha(checkpoint_path(root, 30).read_bytes())
    stop_reason = None
    cycle = 30
    while cycle < MAX_CYCLES:
        cycle += 1
        _, mesh, _, _ = prepare("chain")
        row = run_cycle(mesh, previous["cells"], previous["state"], previous["end"],
                        backend="NUMBA_FUSED", cfl=.4, capture_conservation=True)
        row.update(cycle=cycle, **EXPECTED,
                   initial_cylinder_mass=previous["state"][6])
        row["checks"] = native(checks(row))
        inputs = audit_inputs(row)
        lag1, lag2 = native(comparison(previous, inputs)), native(comparison(previous2, inputs))
        branch = "A" if cycle % 2 else "B"
        gate_failure = advance_detector(detector, inputs, lag1, lag2, branch,
                                        row["checks"])
        saved = snapshot(detector, cycle, branch, lag1, lag2)
        item = {"cycle": cycle, "branch": branch, "lag1": lag1, "lag2": lag2,
                "checks": row["checks"], "detector": saved["state"],
                "gate_failure": gate_failure, "elapsed_seconds": time.perf_counter()-started}
        parent_sha = save_checkpoint(root, cycle, inputs, saved, item, parent_sha)
        with (root / "cycle-trace.jsonl").open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(item, allow_nan=False) + "\n")
        print(json.dumps({"cycle": cycle, "branch": branch,
                          "lag2_sensor_max": lag2.get("sensor_max"),
                          "A": detector.branch_A_streak, "B": detector.branch_B_streak,
                          "CFL": row["checks"].get("CFL"),
                          "gate_failure": gate_failure,
                          "detected_period": detector.detected_period}), flush=True)
        if gate_failure:
            stop_reason = gate_failure
            break
        if detector.detected_period is not None:
            stop_reason = f"CONVERGED_PERIOD{detector.detected_period}"
            break
        previous2, previous = previous, inputs
    if stop_reason is None:
        stop_reason = "MAX_CYCLES_400_WITHOUT_CONVERGENCE"
    status = ("E13_G2_V2_PASS" if stop_reason.startswith("CONVERGED")
              else "E13_G2_V2_FAIL" if stop_reason.startswith("MAX_CYCLES")
              else "E13_G2_V2_INCONCLUSIVE")
    decision = {"contract": "G2-v2", "status": status,
                "stop_reason": stop_reason, "last_cycle": cycle,
                "cycles_executed": cycle-30, "max_cycles": MAX_CYCLES,
                "detector": detector.to_json(),
                "closing_checkpoint_sha256": parent_sha,
                "prior_acquisition": "historical compact-only evidence; not an audit basis"}
    (root / "decision.json").write_text(json.dumps(decision, indent=2), encoding="utf-8")
    (root / "runtime.json").write_text(json.dumps({"wall_seconds": time.perf_counter()-started,
                                                   "new_cycles": cycle-30}, indent=2), encoding="utf-8")
    return decision


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT)
    print(json.dumps(run(parser.parse_args().output), allow_nan=False), flush=True)
