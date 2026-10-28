"""Replay the recorded 0–60 degree cases and measure their 60–150 degree arc."""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from motorsim.integrated_2t import (IntegratedEngine2T, _integrated_nominal_step_end,
                                   _integrated_scheduled_angles, _json_evidence_equal,
                                   _solver_dependency_hashes)
from motorsim.port_connection_v2 import NoAdmissiblePortState
from scripts.agents.storage_preflight import check_storage_requirements, default_artifact_root
from scripts.diagnostics.periodic88_front_flux_v1 import accumulate, empty_totals, serial
from scripts.diagnostics.periodicity_extension_v4 import conserved
from scripts.diagnostics.prepare_postopen_wave_transport_v1 import CASES, prepare
from scripts.diagnostics.diagnose_integrated_mesh_v1 import sha, write


START_ANGLE = 13680.0
CASE_GRID = {"p0-88": 88, "p0-176": 176, "p0-352": 352, "p0-176-timehalf": 176}
CASE_CAP = {"p0-88": .0625, "p0-176": .0625, "p0-352": .0625, "p0-176-timehalf": .03125}
PHASES = (90.0, 120.0, 150.0)
TOTAL_CAP_S = 600.0
CASE_CAP_S = 210.0
MARGIN = 1.30
SCALE_FROM_60_TO_150 = 2.5


def load(path: Path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def file_sha(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def source_validation(source_root: Path) -> dict:
    source_root = Path(source_root)
    manifest_path = source_root / "manifest.json"
    manifest = load(manifest_path)
    if manifest.get("schema") != "PREOPEN_WAVE_TRANSPORT_FINAL_MANIFEST_V1" or manifest.get("status") != "COMPLETE_BOUNDED_DIAGNOSTIC":
        raise ValueError("pre-opening source manifest contract differs")
    for relative, expected in manifest.get("files", {}).items():
        path = source_root / relative
        if not path.is_file() or file_sha(path) != expected:
            raise ValueError(f"pre-opening manifest source changed: {relative}")
    input_manifest_path = source_root / "input-manifest.json"
    input_manifest = load(input_manifest_path)
    for relative, expected in input_manifest.get("files", {}).items():
        path = source_root / relative
        if not path.is_file() or file_sha(path) != expected:
            raise ValueError(f"pre-opening input source changed: {relative}")
    source_scripts = manifest.get("source_files", {})
    for relative, expected in source_scripts.items():
        path = ROOT / relative
        if not path.is_file() or file_sha(path) != expected:
            raise ValueError(f"pre-opening runner source changed: {relative}")
    run = load(source_root / "run" / "receipt.json")
    if run.get("status") != "COMPLETE" or run.get("solver_dependency_sha256") != _solver_dependency_hashes():
        raise ValueError("pre-opening run or solver dependency identity differs")
    completed = {case["name"] for case in run.get("cases", []) if case.get("status") == "COMPLETE"}
    if not set(CASES).issubset(completed):
        raise ValueError("required P0 pre-opening cases are incomplete")
    return {"manifest_sha256": file_sha(manifest_path),
            "input_manifest_sha256": file_sha(input_manifest_path),
            "source_files_sha256": source_scripts,
            "solver_dependency_sha256": run["solver_dependency_sha256"],
            "required_cases": list(CASES)}


def admission_estimates(preparation: dict, factor: float = 1.0) -> list[dict]:
    estimates = []
    for case in preparation["cases"]:
        projected = case["projected_replay_plus_extension_s"] * factor
        estimates.append({"name": case["name"], "projected_s": projected,
                          "with_margin_s": projected * MARGIN,
                          "per_case_cap_s": CASE_CAP_S,
                          "admitted_by_per_case_cap": projected * MARGIN <= CASE_CAP_S})
    return estimates


def preflight(source_root: Path, output: Path, artifact_root: Path,
              protocol_path: Path) -> dict:
    validation = source_validation(source_root)
    prep = prepare(source_root)
    if not prep["cost"]["fits_proposed_caps"]:
        raise ValueError("fresh source projection exceeds frozen activation caps")
    if prep["cost"]["proposed_total_admission_cap_s"] != TOTAL_CAP_S or prep["cost"]["proposed_per_case_cap_s"] != CASE_CAP_S:
        raise ValueError("prepared budget differs from activation caps")
    storage = check_storage_requirements([(Path(output), 1024**3)])
    return {
        "schema": "DINO_POSTOPEN_WAVE_TRANSPORT_PREFLIGHT_V1",
        "activation_protocol_sha256": file_sha(protocol_path),
        "runner_sha256": file_sha(Path(__file__)),
        "source_validation": validation,
        "preparation": prep,
        "initial_admission_estimates": admission_estimates(prep),
        "storage_preflight": storage,
        "output": str(output),
        "total_admission_cap_s": TOTAL_CAP_S,
        "per_case_admission_cap_s": CASE_CAP_S,
        "study_storage_cap_bytes": 1024**3,
        "solver_steps_executed": 0,
        "activation": "USER_ACTIVATED_BOUNDED_TRANSIENT_DIAGNOSTIC",
        "qualification": "Fresh source and cost preflight only; no solver steps.",
    }


def _source_case(source_root: Path, name: str):
    folder = Path(source_root) / "run" / name
    return {key: load(folder / f"{key}.json") for key in
            ("configuration", "initial-checkpoint", "recipe", "terminal-state", "receipt", "frames")}


def _replay_source(engine, case: dict, deadline: float) -> dict:
    recipe = case["recipe"]
    rejected = 0
    for index, row in enumerate(recipe):
        if time.perf_counter() >= deadline:
            raise TimeoutError("per-case admission cap reached during exact source replay")
        for attempt in row.get("rejected_proposals", []):
            delta = attempt["step_deg"]
            try:
                engine.step(delta / (6 * 9000.0), delta, capture_trace=False)
            except NoAdmissiblePortState:
                raise
            except ValueError as exc:
                if str(exc) != attempt.get("error"):
                    raise ValueError(f"source rejected proposal {index} differs") from exc
                rejected += 1
            else:
                raise ValueError(f"source rejected proposal {index} was accepted on replay")
        delta = row["angle_end_deg"] - row["angle_start_deg"]
        actual = engine.step(row["dt_s"], delta, capture_trace=False)
        if not all(_json_evidence_equal(actual.get(key), value)
                   for key, value in row.items() if key != "rejected_proposals"):
            raise ValueError(f"source accepted step {index} differs on replay")
    if engine.crank_angle_unwrapped_deg != START_ANGLE + 60.0:
        raise ValueError("source replay did not end at 60 degrees")
    engine_state = engine.fast_recipe_terminal_state()
    if not _json_evidence_equal(engine_state, case["terminal-state"]):
        raise ValueError("replayed FAST terminal differs from source")
    return {"accepted_source_steps_replayed": len(recipe),
            "rejected_source_proposals_replayed": rejected,
            "fast_terminal_exact": True,
            "terminal_angle_deg": engine.crank_angle_unwrapped_deg}


def run_case(source_root: Path, output: Path, name: str, deadline: float) -> dict:
    if output.exists():
        raise FileExistsError(f"preserve existing post-opening case: {output}")
    case_start = time.perf_counter()
    source = _source_case(source_root, name)
    receipt = source["receipt"]
    if receipt.get("status") != "COMPLETE" or receipt.get("error") is not None:
        raise ValueError(f"pre-opening source case is not complete: {name}")
    if receipt.get("solver_dependency_sha256") != _solver_dependency_hashes():
        raise ValueError(f"solver dependency identity differs: {name}")
    engine = IntegratedEngine2T.from_configuration_dict(source["configuration"])
    engine.restore(source["initial-checkpoint"])
    if not _json_evidence_equal(engine.snapshot(), source["initial-checkpoint"]):
        raise ValueError(f"native source checkpoint restore differs: {name}")
    output.mkdir(parents=True)
    write(output / "configuration.json", source["configuration"])
    write(output / "initial-checkpoint.json", source["initial-checkpoint"])
    write(output / "source-binding.json", {
        "source_case": name,
        "source_configuration_sha256": file_sha(Path(source_root) / "run" / name / "configuration.json"),
        "source_initial_checkpoint_sha256": file_sha(Path(source_root) / "run" / name / "initial-checkpoint.json"),
        "source_recipe_sha256": file_sha(Path(source_root) / "run" / name / "recipe.json"),
        "source_terminal_sha256": file_sha(Path(source_root) / "run" / name / "terminal-state.json"),
        "source_receipt_sha256": file_sha(Path(source_root) / "run" / name / "receipt.json"),
        "source_frames_sha256": file_sha(Path(source_root) / "run" / name / "frames.json"),
        "source_manifest_sha256": file_sha(Path(source_root) / "manifest.json"),
        "solver_dependency_sha256": _solver_dependency_hashes(),
    })
    replay = _replay_source(engine, source, deadline)
    source_replay_s = time.perf_counter() - case_start
    duct_names = [path.id for path in engine.ducts]
    flux_totals = empty_totals(duct_names)
    window_totals = empty_totals(duct_names)
    phases = [dict(phase_deg=60.0, angle=engine.crank_angle_unwrapped_deg,
                   state=deepcopy(engine.state), ledger=deepcopy(engine.ledger))]
    flux_windows = []
    extension_recipe = []
    rejected_extension = 0
    stage_records = []
    original_assemble = engine._assemble

    def observe(*args, **kwargs):
        kwargs["capture_trace"] = True
        result = original_assemble(*args, **kwargs)
        stage_records.append(result["faces"])
        return result

    engine._assemble = observe
    end_angle = START_ANGLE + 150.0
    schedule = _integrated_scheduled_angles(engine, end_angle)
    case_cap = CASE_CAP_S
    target_angles = {START_ANGLE + phase: phase for phase in PHASES}
    while engine.crank_angle_unwrapped_deg < end_angle - 1e-9:
        now = time.perf_counter()
        if now >= deadline or now - case_start >= case_cap:
            raise TimeoutError(f"{name} reached total/per-case admission cap")
        angle = engine.crank_angle_unwrapped_deg
        next_target = min(target for target in target_angles if target > angle + 1e-9)
        delta = min(next_target, _integrated_nominal_step_end(engine, angle, end_angle, schedule),
                    (math.floor((angle + 1e-9) / CASE_CAP[name]) + 1) * CASE_CAP[name]) - angle
        rejected = []
        for _ in range(25):
            stage_records.clear()
            try:
                row = engine.step(delta / (6 * 9000.0), delta, capture_trace=False)
            except NoAdmissiblePortState:
                raise
            except ValueError as exc:
                if not any(token in str(exc) for token in
                           ("CFL limit exceeded", "inadmissible species mass", "rho/p/Y inadmissible")):
                    raise
                rejected.append({"step_deg": delta, "error": str(exc)})
                delta *= .5
            else:
                break
        else:
            raise RuntimeError("25 rejected step proposals")
        if len(stage_records) != 2:
            raise ValueError("expected exactly two SSPRK2 stage face ledgers")
        extension_recipe.append(dict(**row, rejected_proposals=rejected))
        rejected_extension += len(rejected)
        for stage_faces in stage_records:
            accumulate(flux_totals, stage_faces, .5 * row["dt_s"])
            accumulate(window_totals, stage_faces, .5 * row["dt_s"])
        if len(extension_recipe) % 100 == 0:
            write(output / "extension-recipe.json", extension_recipe)
            write(output / "progress.json", {"status": "RUNNING", "phase_end_deg": engine.crank_angle_unwrapped_deg - START_ANGLE,
                                              "accepted_extension_steps": len(extension_recipe),
                                              "source_replay_s": source_replay_s,
                                              "wall_s": time.perf_counter() - case_start})
        angle = engine.crank_angle_unwrapped_deg
        if any(abs(angle - target) < 1e-8 for target in target_angles):
            phase = target_angles[min(target_angles, key=lambda target: abs(angle - target))]
            balance = engine.conservation_report()
            if not conserved(balance):
                raise ValueError(f"global normalized conservation failed at {phase} degrees")
            phases.append(dict(phase_deg=phase, angle=angle,
                               state=deepcopy(engine.state), ledger=deepcopy(engine.ledger)))
            flux_windows.append(dict(phase_start_deg=phase - 30.0, phase_end_deg=phase,
                                     integrated_face_fluxes=serial(window_totals),
                                     conservation=balance))
            write(output / f"checkpoint-phase-{int(phase):03}.json", engine.snapshot())
            window_totals = empty_totals(duct_names)
            write(output / "frames.json", phases)
            write(output / "flux-windows.json", flux_windows)
            write(output / "extension-recipe.json", extension_recipe)
    if [row["phase_deg"] for row in phases] != [60.0, 90.0, 120.0, 150.0]:
        raise ValueError("common target phase coverage is incomplete")
    final_balance = engine.conservation_report()
    if not conserved(final_balance):
        raise ValueError("global normalized conservation failed at 150 degrees")
    result = {
        "schema": "DINO_POSTOPEN_WAVE_TRANSPORT_CASE_V1",
        "status": "COMPLETE", "error": None, "case": name,
        "grid_total_cells": CASE_GRID[name], "angular_cap_deg": CASE_CAP[name],
        "source_replay": replay, "source_replay_wall_s": source_replay_s,
        "wall_s": time.perf_counter() - case_start,
        "accepted_extension_steps": len(extension_recipe),
        "rejected_extension_proposals": rejected_extension,
        "source_configuration_sha256": file_sha(Path(source_root) / "run" / name / "configuration.json"),
        "runner_sha256": file_sha(Path(__file__)),
        "solver_dependency_sha256": _solver_dependency_hashes(),
        "phase_degrees": [row["phase_deg"] for row in phases],
        "flux_windows": len(flux_windows),
        "flux_integrated_60_to_150": serial(flux_totals),
        "global_conservation": final_balance,
        "normalized_conservation_pass": True,
        "periodicity_audited": False, "mesh_independence": False,
        "experimental_validation": False, "predictive_claim": False,
        "candidate_promotion": False,
        "qualification": "Recorded39 finite transient arc only. Exact source replay and extension; no periodicity, GCI, experimental, predictive or adoption claim.",
    }
    write(output / "frames.json", phases)
    write(output / "flux-windows.json", flux_windows)
    write(output / "extension-recipe.json", extension_recipe)
    write(output / "receipt.json", result)
    write(output / "progress.json", {"status": "COMPLETE", "phase_end_deg": 150.0,
                                      "wall_s": result["wall_s"]})
    return result


def run(source_root: Path, output: Path, artifact_root: Path,
        protocol_path: Path, preflight_path: Path) -> dict:
    frozen = load(preflight_path)
    if (frozen.get("schema") != "DINO_POSTOPEN_WAVE_TRANSPORT_PREFLIGHT_V1" or
            frozen.get("activation_protocol_sha256") != file_sha(protocol_path) or
            frozen.get("runner_sha256") != file_sha(Path(__file__)) or
            frozen.get("solver_steps_executed") != 0 or frozen.get("output") != str(output)):
        raise ValueError("post-opening activation/preflight/runner binding differs")
    validation = source_validation(source_root)
    if frozen.get("source_validation") != validation:
        raise ValueError("post-opening source changed after preregistration")
    preflight_storage = frozen["storage_preflight"]
    if not preflight_storage.get("passed", preflight_storage.get("status") == "PASS"):
        raise ValueError("preflight storage reserve did not pass")
    if output.exists():
        raise FileExistsError("preserve existing post-opening output")
    output.mkdir(parents=True)
    start = time.perf_counter()
    results = []
    status, error = "COMPLETE", None
    cost_factor = 1.0
    try:
        for index, estimate in enumerate(frozen["initial_admission_estimates"]):
            remaining = TOTAL_CAP_S - (time.perf_counter() - start)
            projected = estimate["projected_s"] * cost_factor
            projected_margin = projected * MARGIN
            if projected_margin > CASE_CAP_S or projected_margin > remaining:
                status = "STOP_ADMISSION_BUDGET"
                error = f"{estimate['name']} not admitted: projected margin {projected_margin:.3f}s, remaining {remaining:.3f}s"
                break
            try:
                result = run_case(source_root, output / estimate["name"], estimate["name"],
                                  min(start + TOTAL_CAP_S, time.perf_counter() + CASE_CAP_S))
            except TimeoutError as exc:
                status, error = "PARTIAL_AT_BUDGET", str(exc)
                break
            except Exception as exc:
                case_output = output / estimate["name"]
                if case_output.exists() and not (case_output / "receipt.json").exists():
                    write(case_output / "receipt.json", {"schema": "DINO_POSTOPEN_WAVE_TRANSPORT_CASE_V1",
                                                          "status": "ERROR", "error": f"{type(exc).__name__}: {exc}",
                                                          "preserve_partial": True})
                status, error = "ERROR", f"{estimate['name']}: {type(exc).__name__}: {exc}"
                break
            results.append({"name": estimate["name"], "status": result["status"],
                            "wall_s": result["wall_s"], "receipt_sha256": file_sha(output / estimate["name"] / "receipt.json")})
            cost_factor = max(cost_factor, result["wall_s"] / max(estimate["projected_s"], 1e-12))
            write(output / "progress.json", {"status": "RUNNING", "completed_cases": results,
                                               "wall_s": time.perf_counter() - start})
    except Exception as exc:
        status, error = "ERROR", f"{type(exc).__name__}: {exc}"
    final = {
        "schema": "DINO_POSTOPEN_WAVE_TRANSPORT_RUN_V1",
        "status": status, "error": error, "cases": results,
        "wall_s": time.perf_counter() - start,
        "storage_preflight": preflight_storage,
        "activation_preflight_sha256": file_sha(preflight_path),
        "protocol_sha256": file_sha(protocol_path),
        "runner_sha256": file_sha(Path(__file__)),
        "solver_dependency_sha256": _solver_dependency_hashes(),
        "new_periodic_cycles": 0, "periodicity_audited": False,
        "mesh_independence": False, "experimental_validation": False,
        "predictive_claim": False, "candidate_promotion": False,
    }
    write(output / "receipt.json", final)
    write(output / "progress.json", {"status": status, "completed_cases": results,
                                      "wall_s": final["wall_s"], "error": error})
    print(json.dumps({"status": status, "error": error, "cases": results, "wall_s": final["wall_s"]}))
    return final


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--preflight", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--artifact-root", type=Path)
    parser.add_argument("--preflight-only", action="store_true")
    args = parser.parse_args()
    artifact_root = args.artifact_root or default_artifact_root()
    if args.preflight_only:
        if args.output.exists():
            raise FileExistsError("preserve existing post-opening preflight")
        result = preflight(args.source_root, args.output, artifact_root, args.protocol)
        args.preflight.parent.mkdir(parents=True, exist_ok=True)
        write(args.preflight, result)
        print(json.dumps({"preflight": "PASS", "cases": len(CASES),
                          "with_margin_s": result["preparation"]["cost"]["projection_with_margin_s"],
                          "solver_steps": 0}))
    else:
        if not args.preflight.is_file():
            raise FileNotFoundError("frozen preflight is required")
        result = run(args.source_root, args.output, artifact_root, args.protocol, args.preflight)
        raise SystemExit(0 if result["status"] == "COMPLETE" else 1)


if __name__ == "__main__":
    main()
