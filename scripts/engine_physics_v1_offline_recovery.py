"""Regenerate historical ENGINE_PHYSICS_V1 points with the V2 adapter.

This is an offline derivation only.  It never writes the accepted r3 evidence
tree; corrected records and an explicit old/new comparison live in a new,
versioned recovery directory.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from motorsim.engine_physics_v1 import evaluate_integrated_cycle_v2, synthetic_gasoline_v1


ROOT = Path(__file__).resolve().parents[1]
HISTORICAL = ROOT / "results/engine-physics-v1/campaign-evidence-r3"
DEFAULT_OUT = ROOT / "results/engine-physics-v1/recovery-offline-v2"
POINTS = {
    "engine_a_3000": 3000.0,
    "engine_a_4000": 4000.0,
    "engine_b_3000": 3000.0,
    "engine_b_4000": 4000.0,
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    fuel = synthetic_gasoline_v1()
    differences = []
    for point, rpm in POINTS.items():
        primary_path = HISTORICAL / point / "cycle-012.json.gz"
        old_path = HISTORICAL / point / "engineering-012.json"
        primary = json.load(gzip.open(primary_path, "rt", encoding="utf-8"))
        old = json.load(old_path.open(encoding="utf-8"))
        corrected = evaluate_integrated_cycle_v2(
            primary, rpm=rpm, fuel=fuel,
            periodicity_status="NO_CONVERGENCE_WITHIN_HORIZON")
        corrected["evidence_class"] = "TRANSIENT_CYCLE_12"
        corrected["historical_source"] = {
            "primary": str(primary_path.relative_to(ROOT)).replace("\\", "/"),
            "primary_sha256": sha256(primary_path),
            "historical_output": str(old_path.relative_to(ROOT)).replace("\\", "/"),
            "historical_output_sha256": sha256(old_path),
        }
        point_out = args.out / point
        point_out.mkdir(parents=True, exist_ok=True)
        with (point_out / "engineering-v2-cycle-012.json").open("w", encoding="utf-8") as stream:
            json.dump(corrected, stream, indent=2, sort_keys=True)
            stream.write("\n")
        differences.append({
            "point": point,
            "old_schema": old.get("schema"),
            "new_schema": corrected["schema"],
            "old_periodicity": old.get("periodicity"),
            "new_periodicity": corrected["periodicity"],
            "old_hard_gate": old.get("hard_gate", {}).get("classification"),
            "new_hard_gate": corrected["hard_gate"]["classification"],
            "old_fuel_burned": old.get("fuel", {}).get("fuel_burned_kg_per_cycle"),
            "new_fuel_burned": corrected["outputs"]["fuel_burned"],
            "old_fresh_air": old.get("fuel", {}).get("fresh_air_delivered_kg_per_cycle"),
            "new_fresh_air": corrected["outputs"]["AFR"],
            "new_operating_point_status": corrected["operating_point_status"],
            "new_hard_failures": corrected["hard_gate"]["hard_failures"],
        })
    manifest = {
        "schema": "ENGINE_PHYSICS_V1_OFFLINE_RECOVERY_V2",
        "source_tree": "results/engine-physics-v1/campaign-evidence-r3",
        "source_immutability": "historical tree was read-only for this derivation",
        "periodicity_status": "NO_CONVERGENCE_WITHIN_HORIZON",
        "evidence_class": "TRANSIENT_CYCLE_12",
        "adapter": "motorsim.engine_physics_v1.evaluate_integrated_cycle_v2",
        "fuel_sha256": fuel.content_hash,
        "differences": differences,
    }
    with (args.out / "differences.json").open("w", encoding="utf-8") as stream:
        json.dump(manifest, stream, indent=2, sort_keys=True)
        stream.write("\n")


if __name__ == "__main__":
    main()
