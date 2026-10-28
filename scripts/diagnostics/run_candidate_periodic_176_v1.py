"""Run the first bounded 176-cell periodicity window from audited E2B A30."""
from __future__ import annotations

import argparse
from copy import deepcopy
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from motorsim.integrated_2t import (IntegratedEngine2T, _integrated_nominal_step_end,
                                   _integrated_scheduled_angles, _solver_dependency_hashes)
from motorsim.port_connection_v2 import NoAdmissiblePortState
from motorsim.reference_harness.convergence import PeriodicDetectorV2
from scripts.agents.storage_preflight import check_storage_requirements, default_artifact_root
from scripts.diagnostics.diagnose_integrated_mesh_v1 import sha, write
from scripts.diagnostics.periodicity_extension_v4 import conserved
from scripts.diagnostics.relative_cycle_observations_v1 import relative_observations
from scripts.diagnostics.remap_representation_v1 import initialize
from scripts.diagnostics.run_candidate_periodic_gci_v1 import validate_source


def prepare(repo_root: Path, artifact_root: Path):
    source = validate_source(repo_root, artifact_root)
    config = json.loads(source["config_path"].read_text(encoding="utf-8"))
    checkpoint = json.loads(source["checkpoint_path"].read_text(encoding="utf-8"))
    engine, fine_config, remap = initialize(
        config, checkpoint, 2, "P0", source["source_artifacts"]["A/checkpoint-030.json"])
    if engine.cycle != 30 or engine.crank_angle_unwrapped_deg != 10800.0:
        raise ValueError("176-cell conservative remap changed cycle origin")
    binding = {
        "source_type": "E2B_A_AUDITED_PERIODIC_STATE",
        "source_configuration_sha256": source["configuration_sha256"],
        "source_checkpoint_sha256": source["source_artifacts"]["A/checkpoint-030.json"],
        "source_recipe_sha256": source["source_artifacts"]["A/recipe-030.json"],
        "source_primary_audit_sha256": source["source_artifacts"]["A/audit-030.json"],
        "source_manifest_sha256": source["manifest_sha256"],
        "source_artifact_index_sha256": source["artifact_index_sha256"],
        "solver_dependency_sha256": source["solver_dependency_sha256"],
        "initialization": remap,
        "origin_absolute_cycle": 30,
        "physical_origin_crank_deg": 10800.0,
        "first_detector_cycle_index": 1,
    }
    return engine, fine_config, PeriodicDetectorV2(), binding


def preflight(repo_root: Path, artifact_root: Path, protocol_path: Path) -> dict:
    engine, config, _, binding = prepare(repo_root, artifact_root)
    target = artifact_root / "predictive-reliability-v1" / "candidate-periodic-gci-v1"
    storage = check_storage_requirements([(target, 1024**3)])
    return {
        "schema": "DINO_CANDIDATE_PERIODIC_GCI_176_PREFLIGHT_V1",
        "grid_total_cells": 176,
        "protocol_sha256": sha(protocol_path),
        "runner_sha256": sha(Path(__file__)),
        "configuration_identity": config["geometry_identity"]["diagnostic_initialization"],
        "source_binding": binding,
        "configuration_mesh_totals": {p["id"]: len(p["mesh"]["volumes"])
                                       for p in config["ducts"]},
        "storage_preflight": storage,
        "solver_steps_executed": 0,
        "window_cycles": [31, 37],
        "solver_budget_seconds": 900.0,
        "admission_budget_seconds": 1080.0,
        "projected_solver_seconds": 7 * 120.23,
        "projected_with_20_percent_margin_seconds": 7 * 120.23 * 1.2,
        "qualification": "First independent 176-cell window only; review its detector trend before any continuation.",
    }


def run(repo_root: Path, artifact_root: Path, output: Path,
        protocol_path: Path, preflight_path: Path) -> dict:
    frozen = json.loads(preflight_path.read_text(encoding="utf-8"))
    if (frozen.get("schema") != "DINO_CANDIDATE_PERIODIC_GCI_176_PREFLIGHT_V1" or
            frozen.get("protocol_sha256") != sha(protocol_path) or
            frozen.get("runner_sha256") != sha(Path(__file__)) or
            frozen.get("solver_steps_executed") != 0):
        raise ValueError("176-cell preflight/protocol binding differs")
    engine, config, detector, provenance = prepare(repo_root, artifact_root)
    if (frozen.get("grid_total_cells") != 176 or
            frozen.get("source_binding") != provenance or
            frozen.get("configuration_identity") != config["geometry_identity"]["diagnostic_initialization"]):
        raise ValueError("176-cell preflight source/remap identity differs")
    check_storage_requirements([(output, 64 * 1024**2), (artifact_root, 1024**3)])
    if output.exists():
        raise FileExistsError("preserve existing candidate mesh output")
    output.mkdir(parents=True)
    write(output / "configuration.json", config)
    previous = engine.snapshot()
    write(output / "initial-checkpoint.json", previous)
    write(output / "initialization.json", provenance)
    start = time.perf_counter()
    solver_s = 0.0
    recipe, cycles = [], []
    status, error = "TRANSIENT_AT_BUDGET", None
    last_complete_cycle = 30
    end_angle = 360.0 * 37
    schedule = _integrated_scheduled_angles(engine, end_angle)
    try:
        for absolute in range(31, 38):
            frames = [dict(angle=engine.crank_angle_unwrapped_deg,
                           state=deepcopy(engine.state), ledger=deepcopy(engine.ledger))]
            while engine.crank_angle_unwrapped_deg < 360.0 * absolute - 1e-9:
                if solver_s >= 900.0 or time.perf_counter() - start >= 1080.0:
                    raise TimeoutError("first 176-cell window budget")
                angle = engine.crank_angle_unwrapped_deg
                delta = min(360.0 * absolute,
                            _integrated_nominal_step_end(engine, angle, end_angle, schedule)) - angle
                rejected = []
                for attempt in range(25):
                    began = time.perf_counter()
                    try:
                        row = engine.step(delta / (6 * 9000.0), delta, capture_trace=False)
                    except NoAdmissiblePortState:
                        raise
                    except ValueError as exc:
                        if not any(token in str(exc) for token in
                                   ("CFL limit exceeded", "inadmissible species mass",
                                    "rho/p/Y inadmissible")):
                            raise
                        rejected.append(dict(step_deg=delta, error=str(exc)))
                        delta *= 0.5
                    else:
                        break
                    finally:
                        solver_s += time.perf_counter() - began
                else:
                    raise RuntimeError("25 rejected step proposals")
                recipe.append(dict(**row, rejected_proposals=rejected))
                angle = engine.crank_angle_unwrapped_deg
                if abs(angle - round(angle / 30.0) * 30.0) < 1e-9:
                    frames.append(dict(angle=angle, state=deepcopy(engine.state),
                                       ledger=deepcopy(engine.ledger)))
            if len(frames) != 13:
                raise ValueError("cycle phase sampling incomplete")
            engine.compact_fast_recipe_cycle()
            current = engine.snapshot()
            observation, observation_binding = relative_observations(
                engine, previous, current, 30)
            outcome = detector.update(observation)
            balance = engine.conservation_report()
            if not conserved(balance):
                raise ValueError("global conservation check failed")
            work = -(current["ledger"]["cylinder_work_J"] -
                     previous["ledger"]["cylinder_work_J"])
            imep = work / engine.slider_crank.crankcase.displacement_m3 / 1e5
            lag = outcome["outcomes"].get("lag1", {"status": "NOT_EVALUATED", "metrics": {}})
            values = sorted(item["value"] / item["threshold"]
                            for item in lag.get("metrics", {}).values())
            stats = (dict(maximum=max(values), p90=float(__import__("numpy").quantile(values, .9)),
                          median=float(__import__("numpy").median(values)),
                          failed=sum(x > 1 for x in values), count=len(values)) if values else None)
            cycles.append(dict(cycle=absolute, observation_binding=observation_binding,
                               comparison=lag,
                               detector_outcome=outcome, statistics=stats,
                               work_J=work, imep_bar=imep,
                               conservation=balance))
            write(output / f"checkpoint-absolute-{absolute:03}.json", current)
            write(output / f"frames-absolute-{absolute:03}.json", frames)
            write(output / "recipe.json", recipe)
            write(output / "cycles.json", cycles)
            write(output / "detector.json", detector.snapshot())
            write(output / "progress.json", dict(cycles=len(cycles), last_absolute_cycle=absolute,
                                                   solver_s=solver_s, status="RUNNING"))
            previous = current
            last_complete_cycle = absolute
            if outcome["classification"] is not None:
                status = "PERIOD_CANDIDATE_REQUIRES_AUDIT"
                break
            if len(cycles) >= 6 and all(
                    a["statistics"] and b["statistics"] and
                    b["statistics"]["maximum"] >= .95 * a["statistics"]["maximum"] and
                    b["statistics"]["p90"] >= a["statistics"]["p90"]
                    for a, b in zip(cycles[-6:-3], cycles[-3:])):
                status = "STOP_NO_SUFFICIENT_PROGRESS"
                break
    except TimeoutError as exc:
        error = str(exc)
    except Exception as exc:
        status = "ERROR"
        error = f"{type(exc).__name__}: {exc}"
    if engine.accepted_steps:
        write(output / "partial-recipe.json", recipe)
        write(output / "partial-terminal-state.json", engine.fast_recipe_terminal_state())
    result = {
        "schema": "DINO_CANDIDATE_PERIODIC_GCI_176_WINDOW_V1",
        "status": status,
        "error": error,
        "completed_new_cycles": len(cycles),
        "last_complete_absolute_cycle": last_complete_cycle,
        "absolute_terminal_angle": engine.crank_angle_unwrapped_deg,
        "timing_seconds": {"solver": solver_s, "wall": time.perf_counter() - start},
        "source_binding": provenance,
        "runner_sha256": sha(Path(__file__)),
        "solver_dependency_sha256": _solver_dependency_hashes(),
        "conservation": engine.conservation_report(),
        "periodicity_audited": False,
        "mesh_independence": False,
        "experimental_validation": False,
        "candidate_promotion": False,
    }
    write(output / "receipt.json", result)
    write(output / "progress.json", dict(cycles=len(cycles), last_absolute_cycle=last_complete_cycle,
                                          solver_s=solver_s, status=status))
    print(json.dumps({k: result[k] for k in ("status", "error", "completed_new_cycles",
                                               "last_complete_absolute_cycle", "timing_seconds")}))
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--preflight", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--artifact-root", type=Path)
    parser.add_argument("--preflight-only", action="store_true")
    args = parser.parse_args()
    artifact_root = args.artifact_root or default_artifact_root()
    if args.preflight_only:
        if args.output.exists():
            raise FileExistsError("preserve prior preflight")
        result = preflight(ROOT, artifact_root, args.protocol)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        write(args.output, result)
        print(json.dumps({"preflight": "PASS", "cells": 176, "solver_steps": 0}))
    else:
        raise SystemExit(0 if run(ROOT, artifact_root, args.output, args.protocol, args.preflight)
                         ["status"] != "ERROR" else 1)


if __name__ == "__main__":
    main()
