"""One-shot A9000 -> A10000 warm-initialization pilot.

This is an owner-bounded diagnostic, not an RPM coordinator or campaign.
The run identity is intentionally fixed so an interrupted pilot cannot be
silently resumed or repeated into the same evidence directory.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from motorsim.engine_configuration import resolve_for_operating_point, sha256
from motorsim.exploratory_workflow import run_exploratory
from motorsim.periodic_initialization_v1 import initialize_from_periodic_run
from motorsim.power_curve_sweep import _operating_document

RUN_ID = "perfv3-warm-A10000-from-A9000-20261026"
PROJECT_ID = "functional-reed-125cc-v1"
VARIANT = "A_original"
SOURCE_RPM = 9000
TARGET_RPM = 10000


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--max-cycles", type=int, default=40)
    parser.add_argument("--budget-seconds", type=float, default=240.0)
    args = parser.parse_args()
    if args.max_cycles != 40 or args.budget_seconds != 240.0:
        raise SystemExit("pilot caps are fixed at 40 cycles and 240 seconds")

    receipt_path = ROOT / "results/periodic-rpm-curves-v1/receipt.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    row = next(p for p in receipt["points"]
               if p["variant"] == VARIANT and p["rpm"] == SOURCE_RPM)
    result_path = Path(row["result"]).resolve(strict=True)
    source_run = result_path.parent
    expected = {
        "manifest_sha256": row["manifest_sha256"],
        "checkpoint_sha256": row["checkpoint_sha256"],
        "result_sha256": row["result_sha256"],
        "source_run_id": "ab-A-9000",
        "source_variant_label": VARIANT,
        "source_rpm": SOURCE_RPM,
    }
    project = json.loads((ROOT / "configs/reference_cases/functional_reed_125cc_v1.dino.json")
                         .read_text(encoding="utf-8"))
    base = project["base_engine"]
    target = _operating_document(
        base, TARGET_RPM,
        {"schema": "POWERVALVE_OPEN_ENDPOINT_HOLD_V1", "maximum_rpm": TARGET_RPM})
    target_document, initialization = initialize_from_periodic_run(
        target, source_run, expected_source=expected, target_rpm=TARGET_RPM,
        target_variant_label=VARIANT)
    provenance = initialization["provenance"]
    effective = resolve_for_operating_point(target_document, rpm=TARGET_RPM)
    if effective["native_configuration_sha256"] != sha256(target_document["native_configuration"]):
        raise RuntimeError("target configuration digest did not survive operating-point resolution")

    artifact_root = args.artifact_root.expanduser().resolve()
    if artifact_root == ROOT or ROOT in artifact_root.parents:
        raise RuntimeError("pilot artifacts must stay outside the Git working tree")
    output = (artifact_root / "exploratory-workflow-v1" / PROJECT_ID / RUN_ID).resolve()
    if output.exists():
        raise RuntimeError(f"one-shot pilot output already exists; preserving it: {output}")
    result = run_exploratory(
        target_document, project_id=PROJECT_ID, run_id=RUN_ID,
        artifact_root=artifact_root, rpm=TARGET_RPM,
        max_cycles=args.max_cycles, budget_seconds=args.budget_seconds,
        memory_limit_mib=512, resume=False, variant_label=VARIANT,
        initial_state_provenance=provenance)
    last_cycle = result.get("cycles", [])[-1] if result.get("cycles") else {}
    compact = {
        "status": result.get("status"),
        "classification": result.get("classification"),
        "periodicity": result.get("periodicity"),
        "cycles_completed": result.get("cycles_completed"),
        "elapsed_seconds": result.get("elapsed_seconds"),
        "peak_rss_mib": last_cycle.get("peak_rss_mib"),
        "last_cycle": {key: last_cycle.get(key) for key in (
            "cycle", "cylinder_work_J", "chemical_heat_J", "afr_trapped",
            "fuel_burned_kg", "mechanical_estimate", "pressure_min_max_Pa",
            "closure_snapshots", "conservation", "comparison",
            "periodicity_streak", "wall_s", "peak_rss_mib")},
        "artifact_directory": result.get("artifact_directory"),
        "checkpoint_artifact": result.get("checkpoint_artifact"),
        "checkpoint_sha256": result.get("checkpoint_sha256"),
        "initial_state_provenance": result.get("initial_state_provenance"),
        "initialization_inventory_check": {
            "inventory_equal": initialization["inventory_equal"],
            "source_inventory": initialization["source_inventory"],
            "target_initial_inventory": initialization["target_initial_inventory"],
            "source_total_cycle": initialization["source_total_cycle"],
            "new_run_start_cycle": initialization["new_run_start_cycle"],
        },
        "target_configuration_sha256": effective["native_configuration_sha256"],
    }
    print(json.dumps(compact, sort_keys=True, ensure_ascii=False))
    return 0 if result.get("status") in {
        "COMPLETE", "INTERRUPTED_CHECKPOINTED"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
