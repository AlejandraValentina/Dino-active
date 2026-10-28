"""Match all saved exhaust gradient extrema across grids without cutoffs."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.diagnostics.diagnose_integrated_mesh_v1 import write


GRIDS = ("p0-88", "p0-176", "p0-352")
PAIRS = (("88_176", "p0-88", "p0-176"),
         ("176_352", "p0-176", "p0-352"),
         ("88_352", "p0-88", "p0-352"))
FIELDS = ("pressure_Pa", "density_kg_m3", "burned_fraction")
PHASES = (90.0, 120.0, 150.0)


def sha(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def local_peaks(values, centers) -> list[dict]:
    values = np.asarray(values, dtype=float)
    centers = np.asarray(centers, dtype=float)
    if (values.ndim != 1 or len(values) != len(centers) or len(values) < 3 or
            not np.all(np.isfinite(values)) or not np.all(np.diff(centers) > 0)):
        raise ValueError("peak profile must be finite on an ordered mesh")
    magnitude = np.abs(np.gradient(values, centers, edge_order=2))
    indices = []
    if magnitude[0] > magnitude[1]:
        indices.append(0)
    for index in range(1, len(magnitude) - 1):
        if (magnitude[index] >= magnitude[index - 1] and
                magnitude[index] >= magnitude[index + 1] and
                (magnitude[index] > magnitude[index - 1] or
                 magnitude[index] > magnitude[index + 1])):
            indices.append(index)
    if magnitude[-1] > magnitude[-2]:
        indices.append(len(magnitude) - 1)
    return [{"cell_index": int(index), "x_m": float(centers[index]),
             "absolute_gradient": float(magnitude[index])}
            for index in indices]


def match_peaks(peaks_a: list[dict], peaks_b: list[dict]) -> dict:
    """Greedy one-to-one nearest-position pairing; distance is descriptive only."""
    candidates = sorted((abs(a["x_m"] - b["x_m"]), ia, ib)
                        for ia, a in enumerate(peaks_a)
                        for ib, b in enumerate(peaks_b))
    used_a, used_b, matches = set(), set(), []
    for distance, ia, ib in candidates:
        if ia in used_a or ib in used_b:
            continue
        used_a.add(ia); used_b.add(ib)
        a, b = peaks_a[ia], peaks_b[ib]
        matches.append({"peak_a_index": ia, "peak_b_index": ib,
                        "x_a_m": a["x_m"], "x_b_m": b["x_m"],
                        "position_difference_m": b["x_m"] - a["x_m"],
                        "absolute_gradient_a": a["absolute_gradient"],
                        "absolute_gradient_b": b["absolute_gradient"],
                        "absolute_gradient_difference": b["absolute_gradient"] - a["absolute_gradient"]})
    matches.sort(key=lambda row: row["x_a_m"])
    return {"matches": matches,
            "unmatched_a": [row for index, row in enumerate(peaks_a) if index not in used_a],
            "unmatched_b": [row for index, row in enumerate(peaks_b) if index not in used_b],
            "matching_rule": "greedy one-to-one minimum-distance pairing over all peaks; no distance or amplitude acceptance cutoff"}


def analyze(wavefront_path: Path) -> dict:
    wavefront_path = Path(wavefront_path)
    data = json.loads(wavefront_path.read_text(encoding="utf-8"))
    if data.get("schema") != "DINO_POSTOPEN_EXHAUST_WAVEFRONT_TRACKING_V1":
        raise ValueError("wavefront tracking schema differs")
    peak_data = {}
    for grid in GRIDS + ("p0-176-timehalf",):
        if grid not in data.get("cases", {}):
            raise ValueError(f"missing saved grid/time case: {grid}")
        phase_data = data["cases"][grid]["profiles_by_phase"]
        if set(phase_data) != {str(phase) for phase in (60.0, 90.0, 120.0, 150.0)}:
            raise ValueError(f"phase sequence differs for {grid}")
        peak_data[grid] = {}
        for phase in PHASES:
            profile = phase_data[str(phase)]
            centers = profile["fields"].get("centers_m")
            if centers is None:
                raise ValueError(f"cell centers missing for {grid} at {phase}")
            peak_data[grid][str(phase)] = {
                field: local_peaks(profile["fields"][field], centers) for field in FIELDS
            }
    comparisons = {}
    for label, grid_a, grid_b in PAIRS:
        comparisons[label] = {}
        for phase in PHASES:
            comparisons[label][str(phase)] = {
                field: match_peaks(peak_data[grid_a][str(phase)][field],
                                   peak_data[grid_b][str(phase)][field])
                for field in FIELDS
            }
    temporal = {str(phase): {
        field: match_peaks(peak_data["p0-176"][str(phase)][field],
                           peak_data["p0-176-timehalf"][str(phase)][field])
        for field in FIELDS
    } for phase in PHASES}
    return {
        "schema": "DINO_POSTOPEN_GRADIENT_PEAK_MATCHING_V1",
        "source_wavefront_sha256": sha(wavefront_path),
        "phase_degrees": list(PHASES),
        "fields": list(FIELDS),
        "peaks_by_grid_phase_field": peak_data,
        "cross_grid_matches": comparisons,
        "176_timehalf_matches": temporal,
        "interpretation": "Local extrema and their nearest-position matches describe saved numerical profiles only. A match does not identify the same physical wave, and unmatched extrema are retained without threshold filtering.",
        "thresholds_used": False, "wave_speed_fit": False,
        "periodicity": "NOT_TESTED", "gci": None,
        "experimental_validation": False, "predictive_claim": False,
        "candidate_promotion": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wavefront", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(f"preserve prior peak-match output: {args.output}")
    result = analyze(args.wavefront)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    write(args.output, result)
    print(json.dumps({"schema": result["schema"],
                      "grid_pairs": list(result["cross_grid_matches"]),
                      "phases": result["phase_degrees"],
                      "output": str(args.output)}))


if __name__ == "__main__":
    main()
