"""Track strongest saved pressure/density/marker gradients without thresholding."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.diagnostics.diagnose_integrated_mesh_v1 import sha, write


CASES = ("p0-88", "p0-176", "p0-352", "p0-176-timehalf")
PHASES = (60.0, 90.0, 120.0, 150.0)


def gradient_summary(values, centers, faces) -> dict:
    values = np.asarray(values, dtype=float)
    centers = np.asarray(centers, dtype=float)
    faces = np.asarray(faces, dtype=float)
    if (values.ndim != 1 or len(values) < 3 or len(values) != len(centers) or
            len(faces) != len(values) + 1 or not np.all(np.isfinite(values)) or
            not np.all(np.diff(centers) > 0) or not np.all(np.diff(faces) > 0)):
        raise ValueError("gradient profile requires finite values on an ordered mesh")
    gradient = np.gradient(values, centers, edge_order=2)
    widths = np.diff(faces)
    weights = np.abs(gradient) * widths
    total_variation = float(weights.sum())
    maximum_index = int(np.argmax(np.abs(gradient)))
    if total_variation > 0:
        centroid = float(np.dot(weights, centers) / total_variation)
        width = float(np.sqrt(np.dot(weights, (centers - centroid) ** 2) / total_variation))
    else:
        centroid = width = None
    return {
        "maximum_absolute_gradient_per_m": float(abs(gradient[maximum_index])),
        "maximum_gradient_location_m": float(centers[maximum_index]) if total_variation else None,
        "integrated_absolute_gradient": total_variation,
        "absolute_gradient_centroid_m": centroid,
        "absolute_gradient_width_std_m": width,
        "gradient_units": "1/m for ln(pressure), ln(density); fraction/m for burned fraction",
    }


def profiles(state: dict, config: dict) -> dict:
    path = next((item for item in config["ducts"] if item["id"] == "exhaust"), None)
    if path is None:
        raise ValueError("exhaust duct is required")
    name = path["id"]
    q = np.asarray(state["ducts"][name], dtype=float)
    species = np.asarray(state["species"]["ducts"][name], dtype=float)
    rho = q[:, 0]
    pressure = (config["eos"]["gamma"] - 1.0) * (q[:, 2] - .5 * q[:, 1] ** 2 / rho)
    if np.any(rho <= 0) or np.any(pressure <= 0) or np.any(species.sum(axis=1) <= 0):
        raise ValueError("saved exhaust profile contains inadmissible states")
    burned = species[:, 3] / species.sum(axis=1)
    centers = np.asarray(path["mesh"]["centers"], dtype=float)
    faces = np.asarray(path["mesh"]["faces"], dtype=float)
    return {
        "pressure_Pa": gradient_summary(np.log(pressure), centers, faces),
        "density_kg_m3": gradient_summary(np.log(rho), centers, faces),
        "burned_fraction": gradient_summary(burned, centers, faces),
        "mesh": {"cells": int(len(centers)), "x_start_m": float(faces[0]),
                 "x_end_m": float(faces[-1])},
        "fields": {"centers_m": centers.tolist(), "pressure_Pa": pressure.tolist(),
                   "density_kg_m3": rho.tolist(), "burned_fraction": burned.tolist()},
    }


def analyze(analysis_path: Path, run_root: Path) -> dict:
    analysis_path, run_root = Path(analysis_path), Path(run_root)
    source_analysis = json.loads(analysis_path.read_text(encoding="utf-8"))
    if source_analysis.get("schema") != "DINO_POSTOPEN_WAVE_TRANSPORT_ANALYSIS_V1":
        raise ValueError("post-opening analysis schema mismatch")
    run_receipt_path = run_root / "receipt.json"
    run_receipt = json.loads(run_receipt_path.read_text(encoding="utf-8"))
    if (run_receipt.get("status") != "COMPLETE" or
            sha(run_receipt_path) != source_analysis.get("run_receipt_sha256")):
        raise ValueError("source run receipt differs from accepted field analysis")
    result_cases = {}
    for case_name in CASES:
        folder = run_root / case_name
        receipt = json.loads((folder / "receipt.json").read_text(encoding="utf-8"))
        config = json.loads((folder / "configuration.json").read_text(encoding="utf-8"))
        frames = json.loads((folder / "frames.json").read_text(encoding="utf-8"))
        if (receipt.get("status") != "COMPLETE" or
                receipt.get("source_replay", {}).get("fast_terminal_exact") is not True or
                [row.get("phase_deg") for row in frames] != list(PHASES)):
            raise ValueError(f"incomplete source case: {case_name}")
        result_cases[case_name] = {
            "angular_cap_deg": receipt["angular_cap_deg"],
            "profiles_by_phase": {str(row["phase_deg"]): profiles(row["state"], config)
                                  for row in frames},
            "receipt_sha256": sha(folder / "receipt.json"),
        }
    temporal = {}
    for phase in PHASES:
        standard = result_cases["p0-176"]["profiles_by_phase"][str(phase)]
        half = result_cases["p0-176-timehalf"]["profiles_by_phase"][str(phase)]
        temporal[str(phase)] = {
            field: {
                "maximum_gradient_location_difference_m": (
                    None if standard[field]["maximum_gradient_location_m"] is None or
                    half[field]["maximum_gradient_location_m"] is None else
                    half[field]["maximum_gradient_location_m"] - standard[field]["maximum_gradient_location_m"]),
                "integrated_absolute_gradient_difference": (
                    half[field]["integrated_absolute_gradient"] -
                    standard[field]["integrated_absolute_gradient"]),
            } for field in ("pressure_Pa", "density_kg_m3", "burned_fraction")
        }
    return {
        "schema": "DINO_POSTOPEN_EXHAUST_WAVEFRONT_TRACKING_V1",
        "source_analysis_sha256": sha(analysis_path),
        "source_run_receipt_sha256": sha(run_receipt_path),
        "phase_degrees": list(PHASES),
        "cases": result_cases,
        "same_grid_timehalf_control_differences": temporal,
        "method": "Native-grid centered gradients; report strongest gradient, total variation, and absolute-gradient centroid/width. No threshold-defined front, wave-speed fit, solver rerun, or acceptance claim.",
        "interpretation": "Gradient peaks/centroids are descriptors of saved transient profiles and can combine multiple waves or contacts. They do not identify a physical cause.",
        "periodicity": "NOT_TESTED", "gci": None,
        "experimental_validation": False, "predictive_claim": False,
        "candidate_promotion": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--analysis", type=Path, required=True)
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(f"preserve existing wavefront report: {args.output}")
    report = analyze(args.analysis, args.run_root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    write(args.output, report)
    print(json.dumps({"schema": report["schema"], "cases": list(report["cases"]),
                      "phases": report["phase_degrees"], "output": str(args.output)}))


if __name__ == "__main__":
    main()
