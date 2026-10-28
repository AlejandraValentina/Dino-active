"""Locate saved post-opening spatial differences by duct, phase and field."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.diagnostics.compare_remap_representation_v1 import restrict_to
from scripts.diagnostics.diagnose_integrated_mesh_v1 import sha, write


PHASES = (60.0, 90.0, 120.0, 150.0)
PAIRS = (("88_176", "p0-88", "p0-176"),
         ("176_352", "p0-176", "p0-352"),
         ("88_352", "p0-88", "p0-352"))
REGIONS = ((0.0, .25), (.25, .5), (.5, .75), (.75, 1.0))


def _norms(values: np.ndarray, weights: np.ndarray) -> dict:
    weights = np.asarray(weights, dtype=float)
    if len(values) != len(weights) or len(values) == 0 or np.any(weights <= 0):
        raise ValueError("field values and positive cell volumes must match")
    normalized = weights / weights.sum()
    absolute = np.abs(values)
    maximum_index = int(np.argmax(absolute))
    return {"L1": float(np.dot(absolute, normalized)),
            "L2": float(np.sqrt(np.dot(values * values, normalized))),
            "Linf": float(absolute[maximum_index]),
            "maximum_cell_local_index": maximum_index}


def field_profiles(state_a: dict, state_b: dict, duct: dict, gamma: float) -> dict:
    """Return cellwise relative rho/p and absolute species fraction differences."""
    name = duct["id"]
    q_a = np.asarray(state_a["ducts"][name], dtype=float)
    q_b = np.asarray(state_b["ducts"][name], dtype=float)
    species_a = np.asarray(state_a["species"]["ducts"][name], dtype=float)
    species_b = np.asarray(state_b["species"]["ducts"][name], dtype=float)
    centers = np.asarray(duct["mesh"]["centers"], dtype=float)
    volumes = np.asarray(duct["mesh"]["volumes"], dtype=float)
    faces = np.asarray(duct["mesh"]["faces"], dtype=float)
    if (q_a.shape != q_b.shape or q_a.shape[0] != len(centers) or
            species_a.shape != species_b.shape or species_a.shape[0] != len(centers) or
            len(volumes) != len(centers) or len(faces) != len(centers) + 1 or
            np.any(q_a[:, 0] <= 0) or np.any(q_b[:, 0] <= 0) or
            np.any(species_a.sum(axis=1) <= 0) or np.any(species_b.sum(axis=1) <= 0)):
        raise ValueError(f"invalid common-grid field arrays for {name}")
    pressure_a = (gamma - 1.0) * (q_a[:, 2] - .5 * q_a[:, 1] ** 2 / q_a[:, 0])
    pressure_b = (gamma - 1.0) * (q_b[:, 2] - .5 * q_b[:, 1] ** 2 / q_b[:, 0])
    metrics = {
        "density_relative": (q_a[:, 0] - q_b[:, 0]) /
                            np.maximum(np.abs(q_a[:, 0]), np.abs(q_b[:, 0])),
        "pressure_relative": (pressure_a - pressure_b) /
                             np.maximum(np.abs(pressure_a), np.abs(pressure_b)),
    }
    fractions_a = species_a / species_a.sum(axis=1)[:, None]
    fractions_b = species_b / species_b.sum(axis=1)[:, None]
    for index, species in enumerate(("fresh", "fuel", "residual", "burned")):
        metrics[species + "_absolute_fraction"] = fractions_a[:, index] - fractions_b[:, index]
    normalized_position = (centers - faces[0]) / (faces[-1] - faces[0])
    result = {}
    for metric, values in metrics.items():
        overall = _norms(values, volumes)
        overall["maximum_center_m"] = float(centers[overall.pop("maximum_cell_local_index")])
        bins = []
        for lower, upper in REGIONS:
            mask = ((normalized_position >= lower) &
                    ((normalized_position < upper) if upper < 1.0 else (normalized_position <= upper)))
            indices = np.flatnonzero(mask)
            if len(indices):
                region = _norms(values[mask], volumes[mask])
                region["maximum_center_m"] = float(centers[indices[region.pop("maximum_cell_local_index")]])
            else:
                region = None
            bins.append({"normalized_duct_interval": [lower, upper],
                         "cells": int(len(indices)), "norms": region})
        result[metric] = {"overall": overall, "quarter_duct_bins": bins}
    result["cell_centers_m"] = centers.tolist()
    result["normalized_position"] = normalized_position.tolist()
    result["volumes_m3"] = volumes.tolist()
    return result


def analyze(report_path: Path, run_root: Path) -> dict:
    report_path, run_root = Path(report_path), Path(run_root)
    base_report = json.loads(report_path.read_text(encoding="utf-8"))
    if base_report.get("schema") != "DINO_POSTOPEN_WAVE_TRANSPORT_ANALYSIS_V1":
        raise ValueError("post-opening common-phase analysis contract differs")
    run_receipt = json.loads((run_root / "receipt.json").read_text(encoding="utf-8"))
    if (run_receipt.get("status") != "COMPLETE" or
            sha(run_root / "receipt.json") != base_report.get("run_receipt_sha256")):
        raise ValueError("post-opening run receipt differs from the analyzed source")
    cases = {}
    for name in ("p0-88", "p0-176", "p0-352"):
        folder = run_root / name
        config = json.loads((folder / "configuration.json").read_text(encoding="utf-8"))
        frames = json.loads((folder / "frames.json").read_text(encoding="utf-8"))
        receipt = json.loads((folder / "receipt.json").read_text(encoding="utf-8"))
        if receipt.get("status") != "COMPLETE" or receipt.get("source_replay", {}).get("fast_terminal_exact") is not True:
            raise ValueError(f"saved case is incomplete: {name}")
        if [row.get("phase_deg") for row in frames] != list(PHASES):
            raise ValueError(f"saved phase sequence differs: {name}")
        cases[name] = {"config": config, "frames": {row["phase_deg"]: row for row in frames}}
    target_config = cases["p0-88"]["config"]
    localized = {}
    for label, a_name, b_name in PAIRS:
        pair = {"coarse_common_grid": "p0-88", "ducts": {}}
        for target_duct in target_config["ducts"]:
            duct_name = target_duct["id"]
            phase_rows = []
            for phase in PHASES:
                state_a = restrict_to(cases[a_name]["frames"][phase]["state"],
                                      cases[a_name]["config"], target_config)
                state_b = restrict_to(cases[b_name]["frames"][phase]["state"],
                                      cases[b_name]["config"], target_config)
                phase_rows.append({"phase_deg": phase,
                                   "metrics": field_profiles(state_a, state_b, target_duct,
                                                             target_config["eos"]["gamma"])})
            trends = {}
            for metric in phase_rows[0]["metrics"]:
                if metric in ("cell_centers_m", "normalized_position", "volumes_m3"):
                    continue
                values = [row["metrics"][metric]["overall"]["L1"] for row in phase_rows]
                trends[metric] = {"L1_by_phase": dict(zip(PHASES, values)),
                                  "change_from_60deg": {phase: value - values[0]
                                                        for phase, value in zip(PHASES, values)}}
            pair["ducts"][duct_name] = {"phase_profiles": phase_rows,
                                        "difference_trends": trends}
        localized[label] = pair
    return {
        "schema": "DINO_POSTOPEN_WAVE_FIELD_LOCALIZATION_V1",
        "source_analysis_sha256": sha(report_path),
        "source_run_receipt_sha256": sha(run_root / "receipt.json"),
        "phase_degrees": list(PHASES),
        "pairs": localized,
        "interpretation": "The profiles locate and quantify saved cross-grid differences only. Changes from the 60-degree baseline mix transient evolution and numerical effects; they do not identify a physical cause or imply acceptance thresholds.",
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
        raise FileExistsError(f"preserve prior localization output: {args.output}")
    report = analyze(args.analysis, args.run_root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    write(args.output, report)
    print(json.dumps({"schema": report["schema"], "pairs": list(report["pairs"]),
                      "ducts_per_pair": len(next(iter(report["pairs"].values()))["ducts"]),
                      "output": str(args.output)}))


if __name__ == "__main__":
    main()
