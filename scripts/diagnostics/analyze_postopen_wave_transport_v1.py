"""Read-only common-phase comparison of a completed post-opening wave run."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.diagnostics.compare_checkpoint25_sensitivity_v1 import compare_states
from scripts.diagnostics.compare_remap_representation_v1 import restrict_to
from scripts.diagnostics.diagnose_integrated_mesh_v1 import write
from scripts.diagnostics.run_postopen_wave_transport_v1 import (CASES, CASE_GRID,
                                                                source_validation)


PHASES = (60.0, 90.0, 120.0, 150.0)
SPATIAL_PAIRS = (("spatial_88_176", "p0-88", "p0-176"),
                 ("spatial_176_352", "p0-176", "p0-352"),
                 ("spatial_88_352", "p0-88", "p0-352"))


def sha(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _flatten_scalars(value, prefix=""):
    if isinstance(value, dict):
        result = {}
        for key, child in value.items():
            child_prefix = f"{prefix}.{key}" if prefix else str(key)
            result.update(_flatten_scalars(child, child_prefix))
        return result
    if isinstance(value, list):
        result = {}
        for index, child in enumerate(value):
            result.update(_flatten_scalars(child, f"{prefix}[{index}]"))
        return result
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"non-numeric integrated face-flux value at {prefix}")
    return {prefix: float(value)}


def compare_integrated_flux(a: dict, b: dict) -> dict:
    left, right = _flatten_scalars(a), _flatten_scalars(b)
    if set(left) != set(right):
        raise ValueError("integrated face-flux topology differs")
    return {key: {"a": left[key], "b": right[key],
                  "absolute_difference": abs(left[key] - right[key]),
                  "symmetric_relative_difference": abs(left[key] - right[key]) /
                  max(abs(left[key]), abs(right[key]), 1e-30)}
            for key in sorted(left)}


def maximum_normalized_conservation_residual(report: dict) -> float:
    mass = report["mass"]
    energy = report["energy"]
    mass_scale = max(abs(mass["initial"]), abs(mass["final"]))
    energy_scale = max(abs(energy["initial"]), abs(energy["final"]))
    values = [abs(mass["residual"]) / max(mass_scale, 1e-30),
              abs(energy["residual"]) / max(energy_scale, 1e-30)]
    values.extend(abs(item["residual"]) / max(mass_scale, 1e-30)
                  for item in report["species"].values())
    return max(values)


def _load_case(run_root: Path, name: str, expected_runner: str, expected_solver: dict):
    folder = run_root / name
    receipt = json.loads((folder / "receipt.json").read_text(encoding="utf-8"))
    if receipt.get("status") != "COMPLETE" or receipt.get("error") is not None:
        raise ValueError(f"case {name} is incomplete")
    if receipt.get("runner_sha256") != expected_runner or receipt.get("solver_dependency_sha256") != expected_solver:
        raise ValueError(f"case {name} runner/solver identity differs")
    if receipt.get("source_replay", {}).get("fast_terminal_exact") is not True:
        raise ValueError(f"case {name} source replay was not exact")
    if receipt.get("normalized_conservation_pass") is not True:
        raise ValueError(f"case {name} conservation gate failed")
    if receipt.get("phase_degrees") != list(PHASES):
        raise ValueError(f"case {name} target phases differ")
    config = json.loads((folder / "configuration.json").read_text(encoding="utf-8"))
    frames = json.loads((folder / "frames.json").read_text(encoding="utf-8"))
    flux_windows = json.loads((folder / "flux-windows.json").read_text(encoding="utf-8"))
    if [row.get("phase_deg") for row in frames] != list(PHASES):
        raise ValueError(f"case {name} field frame phases differ")
    if [(row.get("phase_start_deg"), row.get("phase_end_deg")) for row in flux_windows] != [
            (60.0, 90.0), (90.0, 120.0), (120.0, 150.0)]:
        raise ValueError(f"case {name} flux-window coverage differs")
    if any(not row.get("conservation", {}).get("mass") or
           not row.get("conservation", {}).get("energy") or
           not row.get("conservation", {}).get("species") for row in flux_windows):
        raise ValueError(f"case {name} flux window lacks conservation evidence")
    return {"receipt": receipt, "config": config, "frames": frames,
            "flux_windows": flux_windows,
            "receipt_sha256": sha(folder / "receipt.json"),
            "frames_sha256": sha(folder / "frames.json"),
            "flux_windows_sha256": sha(folder / "flux-windows.json")}


def analyze(source_root: Path, run_root: Path) -> dict:
    source_root, run_root = Path(source_root), Path(run_root)
    source_binding = source_validation(source_root)
    run_receipt = json.loads((run_root / "receipt.json").read_text(encoding="utf-8"))
    if run_receipt.get("status") != "COMPLETE" or run_receipt.get("error") is not None:
        raise ValueError("post-opening run receipt is not complete")
    solver_hashes = run_receipt.get("solver_dependency_sha256")
    runner_hash = run_receipt.get("runner_sha256")
    if not isinstance(solver_hashes, dict) or not isinstance(runner_hash, str):
        raise ValueError("run runner/solver identities are missing")
    case_names = [row.get("name") for row in run_receipt.get("cases", [])
                  if row.get("status") == "COMPLETE"]
    if set(case_names) != set(CASES) or len(case_names) != len(CASES):
        raise ValueError("all four distinct P0 cases are required")
    cases = {name: _load_case(run_root, name, runner_hash, solver_hashes) for name in CASES}
    phase_index = {name: {row["phase_deg"]: row for row in case["frames"]}
                   for name, case in cases.items()}
    comparisons = {}
    for label, a_name, b_name in SPATIAL_PAIRS + (("temporal_176_halfstep", "p0-176", "p0-176-timehalf"),):
        a, b = cases[a_name], cases[b_name]
        target_name = "p0-88" if label.startswith("spatial_") else a_name
        target = cases[target_name]["config"]
        field_rows = []
        for phase in PHASES:
            state_a = phase_index[a_name][phase]["state"]
            state_b = phase_index[b_name][phase]["state"]
            if label.startswith("spatial_"):
                state_a = restrict_to(state_a, a["config"], target)
                state_b = restrict_to(state_b, b["config"], target)
            field_rows.append({"phase_deg": phase,
                               "fields": compare_states(state_a, state_b, target)})
        flux_rows = []
        for index, (wa, wb) in enumerate(zip(a["flux_windows"], b["flux_windows"])):
            if (wa["phase_start_deg"], wa["phase_end_deg"]) != (wb["phase_start_deg"], wb["phase_end_deg"]):
                raise ValueError(f"{label} flux interval mismatch")
            flux_rows.append({"phase_start_deg": wa["phase_start_deg"],
                              "phase_end_deg": wa["phase_end_deg"],
                              "integrated_face_flux_differences": compare_integrated_flux(
                                  wa["integrated_face_fluxes"], wb["integrated_face_fluxes"])})
        work_a = -(a["frames"][-1]["ledger"]["cylinder_work_J"] -
                   a["frames"][0]["ledger"]["cylinder_work_J"])
        work_b = -(b["frames"][-1]["ledger"]["cylinder_work_J"] -
                   b["frames"][0]["ledger"]["cylinder_work_J"])
        comparisons[label] = {"field_comparisons": field_rows,
                              "integrated_flux_window_comparisons": flux_rows,
                              "work_difference_J": work_b - work_a}
    case_summary = {}
    for name, case in cases.items():
        case_summary[name] = {
            "grid_total_cells": CASE_GRID[name],
            "angular_cap_deg": case["receipt"]["angular_cap_deg"],
            "wall_s": case["receipt"]["wall_s"],
            "accepted_source_steps_replayed": case["receipt"]["source_replay"]["accepted_source_steps_replayed"],
            "rejected_source_proposals_replayed": case["receipt"]["source_replay"]["rejected_source_proposals_replayed"],
            "phase_degrees": case["receipt"]["phase_degrees"],
            "normalized_conservation_pass": case["receipt"]["normalized_conservation_pass"],
            "maximum_normalized_conservation_residual": maximum_normalized_conservation_residual(
                case["receipt"]["global_conservation"]),
            "receipt_sha256": case["receipt_sha256"],
            "frames_sha256": case["frames_sha256"],
            "flux_windows_sha256": case["flux_windows_sha256"],
        }
    return {
        "schema": "DINO_POSTOPEN_WAVE_TRANSPORT_ANALYSIS_V1",
        "classification": "COMPLETE_TRANSIENT_SPATIAL_AND_TEMPORAL_DIAGNOSTIC",
        "source_binding": source_binding,
        "run_receipt_sha256": sha(run_root / "receipt.json"),
        "total_run_wall_s": run_receipt["wall_s"],
        "cases": case_summary,
        "comparisons": comparisons,
        "periodicity": "NOT_TESTED",
        "gci": None,
        "experimental_validation": False,
        "predictive_claim": False,
        "candidate_promotion": False,
        "qualification": "Transient 60–150 degree differences include remapping and unsteady evolution. They localize mesh/time sensitivity only; no periodicity, GCI, experimental validation, predictive claim, or adoption follows.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(f"preserve prior analysis: {args.output}")
    report = analyze(args.source_root, args.run_root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    write(args.output, report)
    print(json.dumps({"classification": report["classification"],
                      "comparisons": list(report["comparisons"]),
                      "run_wall_s": report["total_run_wall_s"],
                      "output": str(args.output)}))


if __name__ == "__main__":
    main()
