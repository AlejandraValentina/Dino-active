"""Owner-authorized continuation/restart for B′4000 only.

No checkpoint was available, so this runner restarts from the original initial
condition, reproduces the persisted first nine cycles, and continues only to
the already preregistered cycle-47 horizon.
"""
from __future__ import annotations

import argparse
import gzip
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from motorsim.engine_physics_v1 import evaluate_integrated_cycle_v2, synthetic_gasoline_v1  # noqa: E402
from motorsim.integrated_2t import IntegratedEngine2T, audit_integrated_cycle_primary, make_integrated_cycle_primary  # noqa: E402
from motorsim.mechanical import MechanicalLossModel  # noqa: E402
from motorsim.reference_harness.convergence import CONTRACT, CONTRACT_V2, PeriodicDetectorV2  # noqa: E402
from scripts.engine_physics_v1_campaign import (  # noqa: E402
    advance_to, canonical, checkpoint_equivalent, config_for,
    reset_trace, sha,
)
from scripts.engine_physics_v1_recovery_campaign import binding_hashes  # noqa: E402

PREREG = ROOT / "results/engine-physics-v1/recovery-preregistration-v2.json"
HISTORICAL = ROOT / "results/engine-physics-v1/recovery-campaign-data-v2/engine_b_4000"


def run(output: Path) -> dict:
    if output.exists() and any(output.iterdir()):
        raise ValueError(f"continuation output exists: {output}")
    prereg = json.loads(PREREG.read_text())
    point = next(item for item in prereg["points"] if item["id"] == "ENGINE_B_4000")
    if point["horizon_cycles"] != 47:
        raise ValueError("B4000 continuation requires the preregistered 47-cycle horizon")
    wrapper, config, config_hash = config_for(point["fixture"], point["rpm"])
    if config_hash != point["config_sha256"]:
        raise ValueError("B4000 configuration hash is not preregistered")
    engine = IntegratedEngine2T.from_configuration_dict(config)
    fuel = synthetic_gasoline_v1()
    binding = binding_hashes(wrapper, config)
    output.mkdir(parents=True, exist_ok=True)
    detector = PeriodicDetectorV2()
    start = engine.snapshot()
    continuity = []
    summaries = []
    old_primary_sha = {}
    for cycle in range(1, 10):
        old_path = HISTORICAL / f"cycle-{cycle:03d}.json.gz"
        old_primary_sha[cycle] = sha(canonical(json.load(gzip.open(old_path, "rt", encoding="utf-8"))))
    for cycle in range(1, 48):
        rejected: list[dict] = []
        advance_to(engine, float(cycle * 360), rejected)
        end = engine.snapshot()
        primary = make_integrated_cycle_primary(
            engine, start, end, cycle, rejected_trials=rejected,
            runner_sha256=binding["producer"])
        if audit_integrated_cycle_primary(primary).get("recomputed") is not True:
            raise ValueError(f"B4000 primary audit failed at cycle {cycle}")
        current_sha = sha(canonical(primary))
        if cycle <= 9:
            match = current_sha == old_primary_sha[cycle]
            continuity.append({"cycle": cycle, "expected_sha256": old_primary_sha[cycle],
                               "reproduced_sha256": current_sha, "match": match})
            if not match:
                raise RuntimeError(f"B4000 deterministic restart mismatch at cycle {cycle}")
        update = detector.update({
            "cycle_index": primary["cycle_index"],
            "configuration_hash": primary["configuration_hash"],
            "contract": CONTRACT,
            "observables": primary["observables"],
        })
        status = detector.classification or "NOT_EVALUATED"
        record = evaluate_integrated_cycle_v2(
            primary, rpm=point["rpm"], fuel=fuel, periodicity_status=status,
            mechanical_losses=MechanicalLossModel.from_dict(wrapper["mechanical_loss_model"]),
        )
        with gzip.open(output / f"cycle-{cycle:03d}.json.gz", "wb") as stream:
            stream.write(canonical(primary))
        (output / f"engineering-v2-{cycle:03d}.json").write_text(
            json.dumps(record, sort_keys=True, indent=2, allow_nan=False) + "\n")
        summaries.append({"cycle": cycle, "hard_gate": record["hard_gate"]["classification"],
                          "operating_point_status": record["operating_point_status"],
                          "terminal_snapshot_sha256": sha(canonical(end))})
        if cycle >= 10:
            reset_trace(engine)
            start = engine.snapshot()
        else:
            start = end
        if detector.classification is not None:
            break
    result = {
        "schema": "ENGINE_PHYSICS_V1_B4000_OPERATIONAL_CONTINUATION_RESULT",
        "point_id": "ENGINE_B_4000", "fixture": point["fixture"], "rpm": point["rpm"],
        "mode": "B4000_OPERATIONAL_RESTART_AFTER_TIMEOUT",
        "authorization": "OWNER_AUTHORIZED_OPERATIONAL_CONTINUATION",
        "status": detector.classification or "NO_CONVERGENCE_WITHIN_HORIZON",
        "periodicity_contract": CONTRACT_V2,
        "detector": detector.snapshot(), "cycles_completed": len(summaries),
        "horizon_cycles": 47, "continuity": continuity,
        "continuity_verified": all(item["match"] for item in continuity),
        "binding_hashes": binding, "config_sha256": config_hash,
        "fuel_sha256": fuel.content_hash, "cycles": summaries,
        "engineering_output_files": [f"engineering-v2-{item['cycle']:03d}.json" for item in summaries],
        "no_extension_beyond_cycle_47": True,
    }
    (output / "result.json").write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    value = run((ROOT / args.output).resolve())
    print(json.dumps({"status": value["status"], "cycles": value["cycles_completed"],
                      "continuity_verified": value["continuity_verified"]}, sort_keys=True))
