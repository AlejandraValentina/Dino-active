"""Single preregistered four-point ENGINE_PHYSICS_V1 engineering campaign."""
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

from motorsim.engine_physics_v1 import (  # noqa: E402
    PortDischargeCoefficientsV1,
    evaluate_integrated_cycle_v1,
    synthetic_gasoline_v1,
)
from motorsim.integrated_2t import (  # noqa: E402
    IntegratedEngine2T, _solver_dependency_hashes, audit_integrated_cycle_primary,
    make_integrated_cycle_primary,
)
from motorsim.mechanical import MechanicalLossModel  # noqa: E402
from motorsim.reference_harness.convergence import (  # noqa: E402
    CONTRACT, CONTRACT_V2, PeriodicDetectorV2, THRESHOLDS,
)
from scripts.produce_integrated_cycle_evidence import advance_to  # noqa: E402


PREREG = ROOT / "results/engine-physics-v1/preregistration.json"
CONFIG_ROOT = ROOT / "results/2t-commercial-core-20261002/fixtures/v1-prime-mesh"


def canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode()


def sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def source_sha(path: Path) -> str:
    return sha(path.read_bytes().replace(b"\r\n", b"\n"))


def config_for(fixture: str, rpm: float) -> tuple[dict, dict, str]:
    wrapper = json.loads((CONFIG_ROOT / f"{fixture.lower()}-mesh-0.json").read_text())
    config = json.loads(json.dumps(wrapper["engine_configuration"]))
    config["reference_rpm"] = float(rpm)
    config["schema"] = "MOTORSIM_INTEGRATED_ENGINE_2T_CONFIG_V6"
    fuel = synthetic_gasoline_v1()
    combustion = config["fuel_coupled_combustion"]
    combustion["schema"] = "FUEL_COUPLED_COMBUSTION_V2"
    combustion["combustion_efficiency_provenance"] = "SYNTHETIC_ASSUMPTION"
    combustion["fuel_snapshot"] = fuel.to_dict()
    combustion["fuel_sha256"] = fuel.content_hash
    config_hash = sha(canonical(config))
    return wrapper, config, config_hash


def projection(primary: dict) -> dict:
    return {"cycle_index": primary["cycle_index"],
            "configuration_hash": primary["configuration_hash"],
            "contract": CONTRACT, "observables": primary["observables"]}


def reset_trace(engine: IntegratedEngine2T) -> None:
    engine.trace = []
    engine.accepted_steps = 0
    engine.rejected_steps = 0


def checkpoint_equivalent(left: dict, right: dict) -> bool:
    """Compare the physical checkpoint; wrapped angle is a representation detail.

    ``restore`` validates the complete trace before assignment.  The next
    cycle replay below is the stronger end-to-end equality check, so this
    checkpoint comparison intentionally focuses on state, ledgers, clocks and
    event histories rather than the serialized trace container.
    """
    fields = ("schema", "configuration_identity", "state", "crank_angle_unwrapped_deg",
              "time_s", "cycle", "accepted_steps", "rejected_steps", "max_cfl",
              "ledger", "p7", "initial_inventory", "fuel_combustion")
    a = {key: left.get(key) for key in fields}
    b = {key: right.get(key) for key in fields}
    return canonical(a) == canonical(b)


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
    binding = binding_hashes(wrapper, config)
    fuel = synthetic_gasoline_v1()
    ports = PortDischargeCoefficientsV1({
        "primary_transfer": {"forward": 0.72, "reverse": 0.68},
        "secondary_transfer": {"forward": 0.70, "reverse": 0.66},
        "exhaust": {"forward": 0.75, "reverse": 0.70},
    })
    point_dir = output_root / point["id"].lower()
    point_dir.mkdir(parents=True, exist_ok=False)
    detector = PeriodicDetectorV2()
    start = engine.snapshot()
    checkpoint_cycle = min(10, max(1, point["horizon_cycles"] // 2))
    restart_engine = None
    restart_snapshot = None
    summaries = []
    engineering = []
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
        update = detector.update(projection(primary))
        detector_updates.append({"cycle": cycle, **update})
        record = evaluate_integrated_cycle_v1(
            primary, rpm=point["rpm"], fuel=fuel,
            mechanical_losses=MechanicalLossModel.from_dict(wrapper["mechanical_loss_model"]),
            port_coefficients=ports)
        record["periodicity"] = {"detector": "PeriodicDetectorV2", "update": update}
        with gzip.open(point_dir / f"cycle-{cycle:03d}.json.gz", "wb") as stream:
            stream.write(canonical(primary))
        (point_dir / f"engineering-{cycle:03d}.json").write_text(
            json.dumps(record, sort_keys=True, indent=2, allow_nan=False) + "\n")
        engineering.append(record)
        summaries.append({"cycle": cycle, "audit": "PASS",
                          "accepted_steps": len(primary["trajectory"]),
                          "hard_gate": record["hard_gate"]["classification"],
                          "terminal_snapshot_sha256": sha(canonical(end))})
        if cycle == checkpoint_cycle:
            restart_engine = IntegratedEngine2T.from_configuration_dict(config)
            restart_engine.restore(end)
            restart_snapshot = restart_engine.snapshot()
            if not checkpoint_equivalent(restart_snapshot, end):
                raise ValueError(f"{point['id']}: checkpoint restore mismatch")
            reset_trace(engine); reset_trace(restart_engine)
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
    status = detector.classification or "NO_CONVERGENCE_WITHIN_HORIZON"
    result = {
        "schema": "ENGINE_PHYSICS_V1_POINT_RESULT",
        "point_id": point["id"], "fixture": point["fixture"], "rpm": point["rpm"],
        "status": status, "periodicity_contract": CONTRACT_V2,
        "detector": detector.snapshot(), "detector_updates": detector_updates,
        "cycles_completed": len(summaries), "horizon_cycles": point["horizon_cycles"],
        "checkpoint_cycle": checkpoint_cycle,
        "checkpoint_restore_exact": restart_snapshot is not None,
        "binding_hashes": binding, "config_sha256": config_hash,
        "fuel_sha256": fuel.content_hash, "cycles": summaries,
        "engineering_output_files": [f"engineering-{i:03d}.json" for i in range(1, len(engineering) + 1)],
        "final_hard_gate": engineering[-1]["hard_gate"],
        "warnings": [warning for item in engineering for warning in item["hard_gate"]["warnings"]],
    }
    (point_dir / "result.json").write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    return result


def run(output: Path) -> dict:
    if output.exists() and any(output.iterdir()):
        raise ValueError(f"campaign output exists: {output}")
    prereg = json.loads(PREREG.read_text())
    if prereg["status"] != "PREREGISTERED_NOT_RUN":
        raise ValueError("phase preregistration is not runnable")
    output.mkdir(parents=True, exist_ok=True)
    points = [run_point(point, output) for point in prereg["points"]]
    result = {"schema": "ENGINE_PHYSICS_V1_CAMPAIGN_RESULT",
              "status": "COMPLETE", "preregistration_sha256": sha(PREREG.read_bytes()),
              "producer_sha256": source_sha(Path(__file__).resolve()),
              "points": points,
              "all_hard_gates_pass": all(point["final_hard_gate"]["classification"] == "PASS" for point in points)}
    (output / "result.json").write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    value = run((ROOT / args.output).resolve())
    print(json.dumps({"status": value["status"], "points": [
        {"id": item["point_id"], "status": item["status"],
         "hard_gate": item["final_hard_gate"]["classification"]}
        for item in value["points"]]}, sort_keys=True))
