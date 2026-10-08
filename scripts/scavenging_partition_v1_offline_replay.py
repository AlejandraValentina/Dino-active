"""Offline replay of the four periodic primaries for the new partition gate."""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from motorsim.scavenging_partition_v1 import evaluate_scavenging_partition_v1  # noqa: E402

POINTS = {
    "A3000": ("results/engine-physics-v1/recovery-campaign-data-v2/engine_a_3000", 73),
    "A4000": ("results/engine-physics-v1/recovery-campaign-data-v2/engine_a_4000", 88),
    "B3000": ("results/engine-physics-v1/recovery-campaign-data-v2/engine_b_3000", 34),
    "B4000": ("results/engine-physics-v1/b4000-continuation-data-v2", 38),
}


def file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path,
                        default=ROOT / "results/engine-physics-v1/scavenging-partition-replay-v1")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    rows = []
    for name, (directory, cycle) in POINTS.items():
        source = ROOT / directory / f"cycle-{cycle:03d}.json.gz"
        old_path = ROOT / directory / f"engineering-v2-{cycle:03d}.json"
        primary = json.load(gzip.open(source, "rt", encoding="utf-8"))
        old = json.loads(old_path.read_text(encoding="utf-8"))
        corrected = evaluate_scavenging_partition_v1(primary)
        target = args.out / name
        target.mkdir(parents=True, exist_ok=True)
        (target / "corrected-partition.json").write_text(
            json.dumps(corrected, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        old_residual = old["scavenging"]["conservation"]["partition_residual_kg"]
        new_residual = corrected["species_closure"]["max_abs_residual_kg"]
        rows.append({
            "point": name, "cycle": cycle,
            "primary_sha256": file_sha(source), "old_output_sha256": file_sha(old_path),
            "old_gate": old["hard_gate"]["classification"],
            "old_partition_residual_kg": old_residual,
            "new_gate": corrected["classification"],
            "new_species_closure_max_abs_residual_kg": new_residual,
            "new_partition_status": corrected["gross_partition"]["status"],
            "new_metrics": corrected["metrics"]["ratios"],
            "periodicity": old.get("periodicity", {}).get("status", "PERIODIC_PRIMARY"),
        })
    manifest = {
        "schema": "SCAVENGING_PARTITION_CONSERVATION_V1_OFFLINE_REPLAY",
        "objective": "SCAVENGING_PARTITION_CONSERVATION_V1",
        "historical_gate_unchanged": "ENGINE_PHYSICS_V1_FAIL_TERMINAL @ 1ceaa86",
        "solver_rerun": False,
        "physics_changed": False,
        "identity": "terminal_inventory_species = initial_inventory_species + external_species_exchange + internal_species_sources + residual",
        "gross_partition_policy": "NOT_APPLICABLE_AS_UNIQUE_MASS; no clipping or normalization",
        "points": rows,
    }
    (args.out / "differences.json").write_text(
        json.dumps(manifest, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"points": len(rows), "classification": [row["new_gate"] for row in rows]}, sort_keys=True))


if __name__ == "__main__":
    main()
