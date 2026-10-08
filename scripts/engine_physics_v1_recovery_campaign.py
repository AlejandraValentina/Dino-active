"""The single preregistered ENGINE_PHYSICS_V1 recovery campaign.

This producer is versioned separately from the historical 12-cycle producer.
It uses the same IntegratedEngine2T configuration and detector contract, but
derives engineering output only through the corrected V2 adapter.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import inspect
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from motorsim.engine_physics_v1 import evaluate_integrated_cycle_v2, synthetic_gasoline_v1  # noqa: E402
from motorsim.integrated_2t import (  # noqa: E402
    IntegratedEngine2T, _solver_dependency_hashes, audit_integrated_cycle_primary,
    make_integrated_cycle_primary,
)
from motorsim.mechanical import MechanicalLossModel  # noqa: E402
from motorsim.reference_harness.convergence import (  # noqa: E402
    CONTRACT, CONTRACT_V2, PeriodicDetectorV2, THRESHOLDS,
)
from scripts.engine_physics_v1_campaign import (  # noqa: E402
    advance_to, canonical, checkpoint_equivalent, config_for, reset_trace, sha,
    source_sha,
)

PREREG = ROOT / "results/engine-physics-v1/recovery-preregistration-v2.json"


def binding_hashes(wrapper: dict, config: dict) -> dict[str, str]:
    return {
        "solver": sha(canonical(_solver_dependency_hashes())),
        "detector": source_sha(ROOT / "motorsim/reference_harness/convergence.py"),
        "auditor": sha(inspect.getsource(audit_integrated_cycle_primary).encode()),
        "producer": source_sha(Path(__file__).resolve()),
        "config": sha(canonical(config)),
        "fixture": sha(canonical(wrapper)),
        "fuel": config["fuel_coupled_combustion"]["fuel_snapshot"]["content_hash"],
        "thresholds": sha(canonical(THRESHOLDS)),
    }


def run_point(point: dict, output_root: Path) -> dict:
    wrapper, config, config_hash = config_for(point["fixture"], point["rpm"])
    if config_hash != point["config_sha256"]:
        raise ValueError(f"{point['id']}: config hash is not preregistered")
    engine = IntegratedEngine2T.from_configuration_dict(config)
    fuel = synthetic_gasoline_v1()
    binding = binding_hashes(wrapper, config)
    point_dir = output_root / point["id"].lower()
    point_dir.mkdir(parents=True, exist_ok=False)
    detector = PeriodicDetectorV2()
    start = engine.snapshot()
    checkpoint_cycle = min(10, max(1, point["horizon_cycles"] // 2))
    restart_engine = None
    restart_snapshot = None
    summaries = []
    detector_updates = []
    for cycle in range(1, point["horizon_cycles"] + 1):
        rejected: list[dict] = []
        advance_to(engine, float(cycle * 360), rejected)
        end = engine.snapshot()
        primary = make_integrated_cycle_primary(
            engine, start, end, cycle, rejected_trials=rejected,
            runner_sha256=binding["producer"])
        audit = audit_integrated_cycle_primary(primary)
        if audit.get("recomputed") is not True:
            raise ValueError(f"{point['id']}: primary audit failed at cycle {cycle}")
        update = detector.update({
            "cycle_index": primary["cycle_index"],
            "configuration_hash": primary["configuration_hash"],
            "contract": CONTRACT,
            "observables": primary["observables"],
        })
        detector_updates.append({"cycle": cycle, **update})
        status = detector.classification or "NOT_EVALUATED"
        record = evaluate_integrated_cycle_v2(
            primary, rpm=point["rpm"], fuel=fuel, periodicity_status=status,
            mechanical_losses=MechanicalLossModel.from_dict(wrapper["mechanical_loss_model"]),
        )
        with gzip.open(point_dir / f"cycle-{cycle:03d}.json.gz", "wb") as stream:
            stream.write(canonical(primary))
        (point_dir / f"engineering-v2-{cycle:03d}.json").write_text(
            json.dumps(record, sort_keys=True, indent=2, allow_nan=False) + "\n")
        summaries.append({"cycle": cycle, "audit": "PASS",
                          "hard_gate": record["hard_gate"]["classification"],
                          "operating_point_status": record["operating_point_status"],
                          "terminal_snapshot_sha256": sha(canonical(end))})
        if cycle == checkpoint_cycle:
            restart_engine = IntegratedEngine2T.from_configuration_dict(config)
            restart_engine.restore(end)
            restart_snapshot = restart_engine.snapshot()
            if not checkpoint_equivalent(restart_snapshot, end):
                raise ValueError(f"{point['id']}: checkpoint restore mismatch")
            reset_trace(engine)
            reset_trace(restart_engine)
            start = engine.snapshot()
        elif cycle == checkpoint_cycle + 1 and restart_engine is not None:
            replay_rejections: list[dict] = []
            advance_to(restart_engine, float(cycle * 360), replay_rejections)
            if not checkpoint_equivalent(restart_engine.snapshot(), end):
                raise ValueError(f"{point['id']}: checkpoint/restart replay mismatch")
            reset_trace(restart_engine)
        if cycle >= checkpoint_cycle:
            reset_trace(engine)
            start = engine.snapshot()
        else:
            start = end
        if detector.classification is not None:
            break
    final_status = detector.classification or "NO_CONVERGENCE_WITHIN_HORIZON"
    result = {
        "schema": "ENGINE_PHYSICS_V1_RECOVERY_POINT_RESULT",
        "point_id": point["id"], "fixture": point["fixture"], "rpm": point["rpm"],
        "status": final_status, "periodicity_contract": CONTRACT_V2,
        "detector": detector.snapshot(), "detector_updates": detector_updates,
        "cycles_completed": len(summaries), "horizon_cycles": point["horizon_cycles"],
        "checkpoint_cycle": checkpoint_cycle,
        "checkpoint_restore_exact": restart_snapshot is not None,
        "binding_hashes": binding, "config_sha256": config_hash,
        "fuel_sha256": fuel.content_hash, "cycles": summaries,
        "engineering_output_files": [f"engineering-v2-{i:03d}.json" for i in range(1, len(summaries) + 1)],
        "regime_output_policy": "only PERIOD_1/PERIOD_2 are usable; otherwise TRANSIENT_DIAGNOSTIC",
    }
    (point_dir / "result.json").write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    return result


def run(output: Path) -> dict:
    if output.exists() and any(output.iterdir()):
        raise ValueError(f"recovery output exists: {output}")
    prereg = json.loads(PREREG.read_text())
    if prereg["status"] != "PREREGISTERED_BEFORE_RECOVERY_CAMPAIGN":
        raise ValueError("recovery preregistration is not runnable")
    output.mkdir(parents=True, exist_ok=True)
    points = [run_point(point, output) for point in prereg["points"]]
    result = {"schema": "ENGINE_PHYSICS_V1_RECOVERY_CAMPAIGN_RESULT",
              "status": "COMPLETE", "preregistration_sha256": sha(PREREG.read_bytes()),
              "producer_sha256": source_sha(Path(__file__).resolve()), "points": points}
    (output / "result.json").write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    value = run((ROOT / args.output).resolve())
    print(json.dumps({"status": value["status"], "points": [
        {"id": item["point_id"], "status": item["status"]} for item in value["points"]
    ]}, sort_keys=True))
