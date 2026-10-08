"""Frozen 20-cycle producer for the two-stroke v1 prime campaigns."""
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

from motorsim.integrated_2t import (  # noqa: E402
    IntegratedEngine2T, _solver_dependency_hashes, audit_integrated_cycle_primary,
    make_integrated_cycle_primary,
)
from motorsim.reference_harness.convergence import (  # noqa: E402
    CONTRACT, CONTRACT_V2, PeriodicDetectorV2, THRESHOLDS as DETECTOR_THRESHOLDS,
)
from scripts.produce_integrated_cycle_evidence import advance_to  # noqa: E402

PREREG = ROOT / "results/2t-v1-closure-20261006/campaign-preregistration-r2.json"
CONFIG_ROOT = ROOT / "results/2t-commercial-core-20261002/fixtures/v1-prime-mesh"


def canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode()


def sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def source_sha(path: Path) -> str:
    return sha(path.read_bytes().replace(b"\r\n", b"\n"))


def detector_projection(primary: dict) -> dict:
    """Build the only record accepted by the preregistered V2 detector."""
    return {
        "cycle_index": primary["cycle_index"],
        "configuration_hash": primary["configuration_hash"],
        "contract": CONTRACT,
        "observables": primary["observables"],
    }


def detector_status(detector: PeriodicDetectorV2, *, exhausted: bool) -> str:
    if detector.classification in {"PERIOD_1", "PERIOD_2"}:
        return detector.classification
    if exhausted:
        return "NO_CONVERGENCE_WITHIN_HORIZON"
    return "RUNNING"


def reset_cycle_trace(engine: IntegratedEngine2T) -> None:
    """Discard prior-cycle trace after its primary has been persisted."""
    engine.trace = []
    engine.accepted_steps = 0
    engine.rejected_steps = 0


def binding_hashes(wrapper: dict, config: dict) -> dict:
    fuel = config["fuel_coupled_combustion"]["fuel_snapshot"]
    return {
        "solver": sha(canonical(_solver_dependency_hashes())),
        "detector": source_sha(ROOT / "motorsim/reference_harness/convergence.py"),
        "auditor": sha(inspect.getsource(audit_integrated_cycle_primary).encode()),
        "producer": source_sha(Path(__file__).resolve()),
        "fixture": sha(canonical(wrapper)),
        "config": sha(canonical(config)),
        "fuel": sha(canonical(fuel)),
        "thresholds": sha(canonical(DETECTOR_THRESHOLDS)),
    }


def load(fixture_id: str) -> dict:
    path = CONFIG_ROOT / f"{fixture_id.lower()}-mesh-0.json"
    wrapper = json.loads(path.read_text(encoding="utf-8"))
    engine = IntegratedEngine2T.from_configuration_dict(wrapper["engine_configuration"])
    if engine.configuration_dict() != wrapper["engine_configuration"]:
        raise ValueError(f"{fixture_id}: configuration roundtrip failed")
    return {"path": path, "wrapper": wrapper, "engine": engine}


def run(fixture_id: str, output: Path) -> dict:
    prereg = json.loads(PREREG.read_text(encoding="utf-8"))
    spec = prereg["fixtures"][fixture_id]
    loaded = load(fixture_id)
    wrapper = loaded["wrapper"]
    config = wrapper["engine_configuration"]
    config_hash = sha(canonical(config))
    if config_hash != spec["engine_configuration_sha256"]:
        raise ValueError(f"{fixture_id}: configuration hash is not preregistered")
    binding = binding_hashes(wrapper, config)
    if binding != spec["binding_hashes"]:
        raise ValueError(f"{fixture_id}: source/configuration binding differs from R2 preregistration")
    if output.exists():
        raise ValueError(f"output exists: {output}")
    output.mkdir(parents=True)
    engine = loaded["engine"]
    runner_sha = binding["producer"]
    rejected: list[dict] = []
    start = engine.snapshot()
    cycle_summaries = []
    detector = PeriodicDetectorV2()
    detector_updates = []
    restart_engine = None
    max_cycles = spec["max_cycles"]
    restart_cycle = spec["restart_cycle"]
    for cycle in range(1, max_cycles + 1):
        first_rejection = len(rejected)
        advance_to(engine, float(cycle * 360), rejected)
        end = engine.snapshot()
        primary = make_integrated_cycle_primary(
            engine, start, end, cycle,
            rejected_trials=rejected[first_rejection:], runner_sha256=runner_sha)
        audit = audit_integrated_cycle_primary(primary)
        if audit.get("recomputed") is not True:
            raise ValueError(f"{fixture_id}: cycle {cycle} offline audit failed")
        update = detector.update(detector_projection(primary))
        detector_updates.append({"cycle": cycle, **update})
        with (output / f"cycle-{cycle:03d}.json.gz").open("wb") as raw:
            with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as stream:
                stream.write(canonical(primary))
        cycle_summaries.append({
            "cycle": cycle, "accepted_steps": len(primary["trajectory"]),
            "rejected_trials": len(primary["rejected_trials"]),
            "audit": "PASS",
            "terminal_snapshot_sha256": sha(canonical(end)),
        })
        if cycle == restart_cycle:
            restart_engine = IntegratedEngine2T.from_configuration_dict(config)
            restart_engine.restore(end)
            # The exact restore is performed while the complete pre-restart
            # history is still present.  After that checkpoint is validated,
            # both continuous and restarted engines can discard persisted
            # prior-cycle traces; the physical state, cumulative ledgers and
            # event histories remain unchanged.
            reset_cycle_trace(engine)
            reset_cycle_trace(restart_engine)
            start = engine.snapshot()
        if cycle == restart_cycle + 1 and restart_engine is not None:
            replay_rejections: list[dict] = []
            advance_to(restart_engine, float(cycle * 360), replay_rejections)
            if canonical(restart_engine.snapshot()) != canonical(end):
                raise ValueError(f"{fixture_id}: restart cycle 11 mismatch")
            reset_cycle_trace(restart_engine)
        if cycle >= restart_cycle:
            reset_cycle_trace(engine)
            start = engine.snapshot()
        else:
            start = end
        if detector.classification is not None:
            break
    exhausted = detector.classification is None and cycle == max_cycles
    final_status = detector_status(detector, exhausted=exhausted)
    if final_status == "RUNNING":
        raise RuntimeError("campaign ended before detector classification or horizon exhaustion")
    result = {
        "schema": "MOTORSIM_2T_V1_CAMPAIGN_RESULT_V1",
        "status": final_status,
        "classification": "SYNTHETIC_ASSUMPTION_CONDITIONAL_ON_P4",
        "fixture_id": fixture_id, "mesh_level": 0, "rpm": config["reference_rpm"],
        "horizon_cycles": max_cycles, "cycles_completed": cycle,
        "restart_cycle": restart_cycle,
        "periodicity_detector": "motorsim.reference_harness.convergence.PeriodicDetectorV2",
        "periodicity_contract": CONTRACT_V2,
        "periodicity_thresholds": DETECTOR_THRESHOLDS,
        "periodicity_status": final_status,
        "detector": detector.snapshot(),
        "detector_updates": detector_updates,
        "binding_hashes": binding,
        "engine_configuration_sha256": config_hash,
        "preregistration_sha256": sha(PREREG.read_bytes()),
        "runner_sha256": runner_sha,
        "restart_cycle_next_exact": True,
        "cycles": cycle_summaries,
    }
    (output / "result.json").write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", choices=("FIXTURE_A_PRIME", "FIXTURE_B_PRIME"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.fixture, (ROOT / args.output).resolve())
    print(json.dumps({"fixture_id": result["fixture_id"], "status": result["status"],
                      "horizon_cycles": result["horizon_cycles"],
                      "periodicity_status": result["periodicity_status"]}, sort_keys=True))


if __name__ == "__main__":
    main()
