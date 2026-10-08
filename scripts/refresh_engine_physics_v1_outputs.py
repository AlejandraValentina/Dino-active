"""Refresh only derived ENGINE_PHYSICS_V1 output serialization offline.

No solver step is performed.  The accepted primary cycle files remain the
authority; this utility is used when a derived-field schema bug is corrected.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from motorsim.engine_physics_v1 import evaluate_integrated_cycle_v1, synthetic_gasoline_v1  # noqa: E402
from motorsim.mechanical import MechanicalLossModel  # noqa: E402
from scripts.engine_physics_v1_campaign import config_for  # noqa: E402


def canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode()


def file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def refresh(root: Path) -> dict:
    campaign = json.loads((root / "result.json").read_text())
    fuel = synthetic_gasoline_v1()
    refreshed = []
    for point in campaign["points"]:
        point_dir = root / point["point_id"].lower()
        wrapper, _, _ = config_for(point["fixture"], point["rpm"])
        loss_model = MechanicalLossModel.from_dict(wrapper["mechanical_loss_model"])
        updates = {item["cycle"]: item for item in point["detector_updates"]}
        for primary_path in sorted(point_dir.glob("cycle-*.json.gz")):
            with gzip.open(primary_path, "rt", encoding="utf-8") as stream:
                primary = json.load(stream)
            record = evaluate_integrated_cycle_v1(
                primary, rpm=point["rpm"], fuel=fuel,
                mechanical_losses=loss_model)
            record["periodicity"] = {"detector": "PeriodicDetectorV2",
                                     "update": updates[primary["cycle_index"]]}
            target = point_dir / f"engineering-{primary['cycle_index']:03d}.json"
            target.write_text(json.dumps(record, sort_keys=True, indent=2,
                                         allow_nan=False) + "\n")
            last_record = record
        point["final_hard_gate"] = last_record["hard_gate"]
        point["warnings"] = last_record["hard_gate"]["warnings"]
        point["derived_output_refresh"] = "offline_from_accepted_primaries"
        point["derived_output_module"] = "motorsim.engine_physics_v1"
        refreshed.append(point["point_id"])
    campaign["engineering_output_refresh"] = {
        "reason": "correct fuel_burned field from ratio record to scalar value/status",
        "module": "motorsim.engine_physics_v1",
        "fuel_sha256": fuel.content_hash,
        "points": refreshed,
    }
    (root / "result.json").write_text(json.dumps(campaign, sort_keys=True,
                                                   indent=2) + "\n")
    return {"points": refreshed, "result_sha256": file_sha(root / "result.json")}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(refresh((ROOT / args.root).resolve()), sort_keys=True))
