"""Build a deterministic, no-solver preflight for the Scientific Point V1.

This tool only prepares an identity-bound candidate. It never advances the
solver and does not authorize execution or checkpoint reuse.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from motorsim.desktop.preferences import repository_root_containing
from motorsim.engine_configuration import resolve_for_operating_point, sha256
from motorsim.engine_project import load_project
from motorsim.exhaust_mesh_v2 import refine_exhaust_configuration
from motorsim.exploratory_workflow import preflight, run_exploratory

PROJECT_PATH = ROOT / "examples/projects/dino-2t-exhaust-comparison.dino2t.json"
VARIANT = "Escape original"
RPM = 3000
CELLS_PER_SECTION = 8
MAX_CYCLES = 8
PERIODICITY_CONTRACT = "REFERENCE_PERIODIC_CONVERGENCE_V2"
OUTPUT_PATH = ROOT / "results/dino-2t-scientific-point-v1/point-preflight.json"
RUN_ID = "scientific-point-v1-escape-original-3000rpm-mesh8"


def _normalized_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def _artifact_root() -> Path:
    base = Path(os.environ.get("DINO_ARTIFACT_ROOT", Path.home() / "Dino-artifacts")).expanduser().resolve()
    if repository_root_containing(base) is not None:
        raise RuntimeError("FAIL_CLOSED DINO_ARTIFACT_ROOT resolves inside a Git repository")
    root = base / "dino-2t-scientific-point-v1" / "run-01"
    if repository_root_containing(root) is not None:
        raise RuntimeError("FAIL_CLOSED point artifact root resolves inside a Git repository")
    return root


def build_preflight() -> dict:
    _artifact_root()
    project = load_project(PROJECT_PATH)
    selected = project["variants"].get(VARIANT)
    if not isinstance(selected, dict):
        raise RuntimeError(f"FAIL_CLOSED project does not contain variant {VARIANT!r}")
    sections = selected["native_configuration"]["geometry_identity"]["chamber"]["sections"]
    refined = refine_exhaust_configuration(selected, [1] * len(sections))
    refined = refine_exhaust_configuration(refined, [CELLS_PER_SECTION] * len(sections))
    effective = resolve_for_operating_point(refined, rpm=RPM)
    # Candidate limits are explicit in the receipt. The run API itself still
    # requires a separate durable authorization before it can be invoked.
    check = preflight(refined, rpm=RPM, max_cycles=MAX_CYCLES,
                      budget_seconds=600, memory_limit_mib=3072)
    if check.get("solver_steps") != 0:
        raise RuntimeError("FAIL_CLOSED preflight unexpectedly advanced the solver")
    base = refined["native_configuration"]
    cell_counts = {row["id"]: len(row["mesh"]["volumes"]) for row in base["ducts"]}
    protocol_path = ROOT / "results/dino-stage1-scientific-readiness/preregistration/stage1-diagnostic-protocol-v1.json"
    historical_protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    historical_binding = historical_protocol["frozen_binding"]
    runner_hash = _normalized_sha256(Path(__file__))
    project_hash = _normalized_sha256(PROJECT_PATH)
    old_binding_mismatches = []
    if check["identity_sha256"] != historical_binding.get("identity_sha256"):
        old_binding_mismatches.append("identity_sha256")
    if effective["source_hashes"] != historical_binding.get("solver_source_hashes"):
        old_binding_mismatches.append("solver_source_hashes")
    expected_mechanical = check.get("mechanical_loss_model_sha256")
    if expected_mechanical != historical_binding.get("mechanical_loss_model_sha256"):
        old_binding_mismatches.append("mechanical_loss_model_sha256")
    if check.get("fuel_id") != historical_binding.get("fuel_id"):
        old_binding_mismatches.append("fuel_id")
    receipt = {
        "schema": "DINO_SCIENTIFIC_POINT_V1_PREFLIGHT_V1",
        "classification": "PREFLIGHT_ONLY_NO_SOLVER_STEPS",
        "scope": "one integrated operating point; no campaign or sweep",
        "project": {"path": "examples/projects/dino-2t-exhaust-comparison.dino2t.json",
                    "sha256": project_hash, "project_id": project["project_id"]},
        "selected_point": {"variant": VARIANT, "rpm": RPM, "mesh_adapter": "EXHAUST_MESH_V2",
                           "cells_per_section": CELLS_PER_SECTION,
                           "duct_cells_by_id": cell_counts,
                           "total_finite_volume_cells": sum(cell_counts.values()),
                           "configuration_sha256": check["configuration_sha256"],
                           "identity_sha256": check["identity_sha256"]},
        "implementation": {"runner": "scripts/diagnostics/scientific_point_v1_preflight.py",
                           "runner_sha256": runner_hash,
                           "solver_source_hashes": effective["source_hashes"],
                           "periodicity_contract": PERIODICITY_CONTRACT,
                           "periodicity_source_sha256": check["periodicity_source_sha256"],
                           "periodicity_thresholds_sha256": check["periodicity_thresholds_sha256"]},
        "physical_inputs": {"mechanical_loss_model_sha256": check["mechanical_loss_model_sha256"],
                            "mechanical_loss_preflight": check["mechanical_loss_preflight"],
                            "fuel_id": check["fuel_id"], "afr_kg_air_per_kg_fuel": check["afr_kg_air_per_kg_fuel"],
                            "boundary_identity": base["boundaries"],
                            "fuel_provenance": refined.get("fuel_provenance"),
                            "loss_provenance": refined.get("mechanical_loss_model")},
        "execution_contract": {"max_cycles": MAX_CYCLES,
                               "periodicity_initial": "NOT_EVALUATED",
                               "existing_conservation_gates": ["mass", "energy", "four species", "coupled interfaces"],
                               "terminal_classifications": ["PERIOD_1", "PERIOD_2", "NO_CONVERGENCE_WITHIN_HORIZON", "BUDGET_LIMITED_CHECKPOINTED", "NUMERICAL_INVALID", "AUDIT_FAIL"],
                               "checkpoint_policy": "per complete cycle; new run id/root; resume only after all current identity hashes validate",
                               "artifact_root": "${DINO_ARTIFACT_ROOT}/dino-2t-scientific-point-v1/run-01",
                               "artifact_root_configuration": "DINO_ARTIFACT_ROOT or per-user Dino-artifacts default",
                               "artifact_root_resolved_outside_repository": True,
                               "fast_recipe": "DISABLED",
                               "evidence_pipeline": "CONVENTIONAL_PRIMARY_PLUS_INDEPENDENT_AUDIT"},
        "resource_options_not_authorized": [{"wall_seconds": 600, "memory_mib": 3072, "workers": 1,
                                              "interpretation": "bounded diagnostic; likely partial based on historical 4/8-cycle timeout"},
                                             {"wall_seconds": 1200, "memory_mib": 3072, "workers": 1,
                                              "interpretation": "bounded integration fixture; no convergence guarantee"}],
        "resource_basis": {"historical_wall_seconds": 689.359, "historical_solver_seconds": 682.829,
                           "historical_cycles": "4/8", "historical_sampled_peak_rss_bytes": 2151251968,
                           "memory_option_basis": "3072 MiB proposed headroom above observed peak; not a measured requirement",
                           "AGENTS_MAX_FIXTURE_SECONDS": 1800},
        "historical_stage1_compatibility": {"preregistration_sha256": _normalized_sha256(protocol_path),
                                            "expected_identity_sha256": historical_binding.get("identity_sha256"),
                                            "current_identity_sha256": check["identity_sha256"],
                                            "mismatches": old_binding_mismatches,
                                            "legacy_runner_preflight": "FAIL_CLOSED identity_sha256, solver_source_hashes; historical runner remains unchanged",
                                            "old_checkpoint_resume": "REJECTED; no reuse permitted",
                                            "historical_files_modified": False},
        "preflight_check": check,
        "solver_steps": 0,
        "execution_authorized": False,
        "campaign_started": False,
        "scientific_validation": "NOT_CLAIMED",
        "spatial_independence": "NOT_ESTABLISHED",
    }
    return receipt


def validate_authorization(authorization: dict, *, preflight_sha256: str,
                           receipt: dict) -> None:
    """Require a durable owner decision bound to this exact candidate."""
    required = {
        "schema": "DINO_SCIENTIFIC_POINT_V1_EXECUTION_AUTHORIZATION_V1",
        "state": "OWNER_APPROVED",
        "preflight_sha256": preflight_sha256,
        "configuration_sha256": receipt["selected_point"]["configuration_sha256"],
        "identity_sha256": receipt["selected_point"]["identity_sha256"],
        "runner_sha256": receipt["implementation"]["runner_sha256"],
        "workers": 1,
        "max_cycles": MAX_CYCLES,
        "campaign_authorized": False,
    }
    mismatches = [key for key, expected in required.items() if authorization.get(key) != expected]
    budget = authorization.get("budget_seconds")
    memory = authorization.get("memory_limit_mib")
    if type(budget) is not int or not 1 <= budget <= 1800:
        mismatches.append("budget_seconds (must be 1..1800)")
    if type(memory) is not int or not 1 <= memory <= 3072:
        mismatches.append("memory_limit_mib (must be 1..3072)")
    if not isinstance(authorization.get("owner_decision"), str) or not authorization["owner_decision"].strip():
        mismatches.append("owner_decision")
    if mismatches:
        raise RuntimeError("FAIL_CLOSED authorization mismatch: " + ", ".join(mismatches))


def _atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.{os.getpid()}.{time.time_ns()}.tmp")
    try:
        with temp.open("w", encoding="utf-8", newline="\n") as stream:
            stream.write(json.dumps(value, indent=2, ensure_ascii=False) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
    finally:
        try:
            temp.unlink(missing_ok=True)
        except OSError:
            pass


def execute_authorized(*, preflight_path: Path, authorization_path: Path,
                       resume: bool) -> dict:
    receipt = json.loads(preflight_path.read_text(encoding="utf-8"))
    preflight_hash = hashlib.sha256(preflight_path.read_bytes()).hexdigest()
    authorization_bytes = authorization_path.read_bytes()
    authorization = json.loads(authorization_bytes)
    validate_authorization(authorization, preflight_sha256=preflight_hash, receipt=receipt)
    authorization_hash = hashlib.sha256(authorization_bytes).hexdigest()
    project = load_project(PROJECT_PATH)
    selected = project["variants"][VARIANT]
    sections = selected["native_configuration"]["geometry_identity"]["chamber"]["sections"]
    refined = refine_exhaust_configuration(selected, [1] * len(sections))
    refined = refine_exhaust_configuration(refined, [CELLS_PER_SECTION] * len(sections))
    effective = resolve_for_operating_point(refined, rpm=RPM)
    check = preflight(refined, rpm=RPM, max_cycles=MAX_CYCLES,
                      budget_seconds=600, memory_limit_mib=authorization["memory_limit_mib"])
    if (check.get("configuration_sha256") != receipt["selected_point"]["configuration_sha256"] or
            check.get("identity_sha256") != receipt["selected_point"]["identity_sha256"] or
            effective.get("source_hashes") != receipt["implementation"]["solver_source_hashes"] or
            _normalized_sha256(Path(__file__)) != receipt["implementation"]["runner_sha256"]):
        raise RuntimeError("FAIL_CLOSED current source/configuration no longer matches preflight")
    artifact_root = _artifact_root()
    run_directory = artifact_root / "exploratory-workflow-v1" / project["project_id"] / RUN_ID
    report_path = artifact_root / "reports" / f"{RUN_ID}.json"
    previous_wall = 0.0
    if resume:
        if not report_path.is_file() or not (run_directory / "checkpoint.json").is_file():
            raise RuntimeError("FAIL_CLOSED resume requires this run's report and checkpoint")
        previous = json.loads(report_path.read_text(encoding="utf-8"))
        if (previous.get("preflight_sha256") != preflight_hash or
                previous.get("authorization_sha256") != authorization_hash or
                previous.get("identity_sha256") != check["identity_sha256"]):
            raise RuntimeError("FAIL_CLOSED resume report binding mismatch")
        previous_wall = float(previous.get("cumulative_wall_seconds", 0.0))
    elif run_directory.exists() or report_path.exists():
        raise RuntimeError("FAIL_CLOSED run artifacts already exist; explicit compatible resume is required")
    remaining_total = authorization["budget_seconds"] - previous_wall
    if remaining_total <= 0:
        raise RuntimeError("FAIL_CLOSED authorized cumulative wall budget exhausted")
    invocation_budget = min(600, remaining_total)
    started = time.monotonic()
    result = run_exploratory(
        refined, project_id=project["project_id"], run_id=RUN_ID,
        artifact_root=artifact_root, rpm=RPM, max_cycles=MAX_CYCLES,
        budget_seconds=invocation_budget, memory_limit_mib=authorization["memory_limit_mib"],
        resume=resume, variant_label=f"{VARIANT} / {CELLS_PER_SECTION} cells per section")
    invocation_wall = time.monotonic() - started
    output = {"schema": "DINO_SCIENTIFIC_POINT_V1_EXECUTION_RECEIPT_V1",
              "preflight_sha256": preflight_hash,
              "authorization_sha256": authorization_hash,
              "configuration_sha256": check["configuration_sha256"],
              "identity_sha256": check["identity_sha256"],
              "runner_sha256": receipt["implementation"]["runner_sha256"],
              "classification": result["classification"], "status": result["status"],
              "periodicity": result["periodicity"], "cycles_completed": result["cycles_completed"],
              "elapsed_seconds": result["elapsed_seconds"], "invocation_wall_seconds": invocation_wall,
              "cumulative_wall_seconds": previous_wall + invocation_wall,
              "result_sha256": result["result_sha256"], "checkpoint_sha256": result["checkpoint_sha256"],
              "artifact_directory": result["artifact_directory"], "cycles": result["cycles"],
              "resume_requested": resume, "campaign_started": False,
              "scientific_validation": "NOT_CLAIMED", "spatial_independence": "NOT_ESTABLISHED"}
    _atomic_json(report_path, output)
    output["report_path"] = str(report_path)
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH)
    parser.add_argument("--execute-authorized-point", action="store_true",
                        help="advance the solver only with a matching durable owner authorization")
    parser.add_argument("--authorization", type=Path)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    try:
        if args.resume and not args.execute_authorized_point:
            parser.error("--resume requires --execute-authorized-point")
        if args.execute_authorized_point:
            if args.authorization is None:
                parser.error("execution requires --authorization")
            result = execute_authorized(preflight_path=args.output,
                                        authorization_path=args.authorization,
                                        resume=args.resume)
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return 0
        receipt = build_preflight()
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n",
                               encoding="utf-8", newline="\n")
        digest = hashlib.sha256(args.output.read_bytes()).hexdigest()
        print(json.dumps({"status": "PREFLIGHT_ONLY_NO_SOLVER_STEPS", "path": str(args.output),
                          "sha256": digest, "identity_sha256": receipt["selected_point"]["identity_sha256"],
                          "historical_binding_mismatches": receipt["historical_stage1_compatibility"]["mismatches"],
                          "execution_authorized": False}, indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({"status": "FAIL_CLOSED", "error": f"{type(exc).__name__}: {exc}"}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
