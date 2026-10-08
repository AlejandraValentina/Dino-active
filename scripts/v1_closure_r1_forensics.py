"""Independent offline provenance check for the historical C14/C15 R1 runs."""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from motorsim.reference_harness.convergence import CONTRACT_V2, PeriodicDetectorV2


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def evaluate(directory: Path) -> dict:
    detector = PeriodicDetectorV2()
    statuses = []
    primary_files = sorted(directory.glob("cycle-*.json.gz"))
    for expected, path in enumerate(primary_files, 1):
        with gzip.open(path, "rt", encoding="utf-8") as stream:
            primary = json.load(stream)
        statuses.append(primary.get("periodicity", {}).get("status"))
        projection = {
            "cycle_index": primary["cycle_index"],
            "configuration_hash": primary["configuration_hash"],
            "contract": "REFERENCE_PERIODIC_CONVERGENCE_V1",
            "observables": primary["observables"],
        }
        if projection["cycle_index"] != expected:
            raise ValueError(f"non-contiguous primary cycle: {path.name}")
        detector.update(projection)
    if len(primary_files) != 20:
        raise ValueError("R1 forensic check requires the complete 20-cycle run")
    return {
        "schema": "MOTORSIM_2T_R1_PROVENANCE_FORENSICS_V1",
        "directory": directory.as_posix(),
        "primary_count": len(primary_files),
        "primary_periodicity_statuses": sorted(set(statuses)),
        "runner_executed_detector": False,
        "runner_wrote_periodicity_status_manually": True,
        "offline_detector": "motorsim.reference_harness.convergence.PeriodicDetectorV2",
        "offline_detector_contract": CONTRACT_V2,
        "p1_streak": detector.lag1_streak,
        "p2_branches": detector.branch_streaks,
        "detected_period": detector.detected_period,
        "classification": "R1_NO_CONVERGENCE_CONFIRMED_OFFLINE",
        "primary_files_sha256": {path.name: sha(path) for path in primary_files},
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = evaluate(args.directory)
    args.output.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: result[key] for key in (
        "classification", "p1_streak", "p2_branches", "detected_period")}, sort_keys=True))


if __name__ == "__main__":
    main()
