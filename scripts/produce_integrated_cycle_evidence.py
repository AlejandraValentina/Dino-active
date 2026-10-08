"""Reproducible, preregistration-gated producer for synthetic integrated cycles.

The fixture input is a committed JSON engine configuration. This script does
not select thresholds or fixtures and refuses to integrate without a committed
preregistration matching the exact config and requested horizon.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from motorsim.integrated_2t import (  # noqa: E402
    IntegratedEngine2T, _integrated_nominal_step_end,
    _integrated_scheduled_angles, make_integrated_cycle_primary,
)
from motorsim.powervalve import PowerValve  # noqa: E402

FIXTURES = ROOT / "results/2t-commercial-core-20261002/fixtures"
PERIODICITY_CONTRACT = ROOT / "motorsim/reference_harness/convergence.py"


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      allow_nan=False).encode("utf-8")


def _decode_json_document(payload: bytes) -> object:
    return json.loads(payload.decode("utf-8-sig"))


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_engine(fixture_id: str) -> tuple[IntegratedEngine2T, dict, str]:
    path = FIXTURES / f"fixture-{fixture_id.lower()}-engine-config-v2.json"
    wrapper = json.loads(path.read_text(encoding="utf-8"))
    expected_status = ("AUDIT_REMEDIATION_FIXTURE" if fixture_id in {"C", "D"} else
                       "HISTORICAL_SUPERSEDED_BY_POSTHOC_AUDIT")
    if (wrapper.get("schema") != "MOTORSIM_COMMERCIAL_SYNTHETIC_FIXTURE_CONFIG_V1" or
            wrapper.get("fixture_id") != fixture_id or
            wrapper.get("selection_status") != expected_status):
        raise ValueError("fixture wrapper schema/identity is invalid")
    config = wrapper.get("engine_configuration")
    engine = IntegratedEngine2T.from_configuration_dict(config)
    if engine.configuration_dict() != config:
        raise ValueError("fixture configuration did not round-trip canonically")
    return engine, wrapper, _sha256(_canonical_bytes(config))


def _require_preregistration(path: Path, fixture_id: str,
                             config_sha256: str, horizon: int,
                             restart_cycle: int,
                             recorded_commit: str) -> tuple[dict, str]:
    prereg = _decode_json_document(path.read_bytes())
    required = {
        "schema": "MOTORSIM_COMMERCIAL_CYCLE_PREREGISTRATION_V1",
        "fixture_id": fixture_id,
        "engine_configuration_sha256": config_sha256,
        "horizon_cycles": horizon,
        "restart_cycle": restart_cycle,
        "cycle_convergence_contract_sha256": _sha256(PERIODICITY_CONTRACT.read_bytes()),
    }
    if any(prereg.get(key) != value for key, value in required.items()):
        raise ValueError("preregistration does not match fixture, horizon or contract")
    if not prereg.get("selection_rationale"):
        raise ValueError("preregistration requires selection_rationale")
    relative = path.resolve().relative_to(ROOT).as_posix()
    commit = str(recorded_commit)
    blob = subprocess.run(["git", "show", f"{commit}:{relative}"], cwd=ROOT,
                          check=True, capture_output=True).stdout
    try:
        committed_document = _decode_json_document(blob)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("committed preregistration is not valid UTF-8 JSON") from exc
    if committed_document != prereg:
        raise ValueError("preregistration content differs from its recorded commit")
    subprocess.run(["git", "merge-base", "--is-ancestor", commit, "HEAD"],
                   cwd=ROOT, check=True, capture_output=True)
    producer_commit = prereg.get("producer_commit")
    if producer_commit is not None:
        producer_path = Path(__file__).resolve().relative_to(ROOT).as_posix()
        producer_blob = subprocess.run(
            ["git", "show", f"{producer_commit}:{producer_path}"], cwd=ROOT,
            check=True, capture_output=True).stdout
        producer_source = Path(__file__).read_bytes().replace(b"\r\n", b"\n")
        if producer_blob.replace(b"\r\n", b"\n") != producer_source:
            raise ValueError("producer source differs from its preregistered commit")
        subprocess.run(["git", "merge-base", "--is-ancestor", producer_commit, "HEAD"],
                       cwd=ROOT, check=True, capture_output=True)
    return prereg, _sha256(_canonical_bytes(committed_document))


def advance_to(engine: IntegratedEngine2T, target_angle: float,
               rejected_trials: list[dict]) -> None:
    scheduled_angles = _integrated_scheduled_angles(engine, target_angle)
    while engine.crank_angle_unwrapped_deg < target_angle - 1e-10:
        angle = engine.crank_angle_unwrapped_deg
        target = _integrated_nominal_step_end(
            engine, angle, target_angle, scheduled_angles)
        step = target - angle
        for attempt in range(25):
            try:
                engine.step(step / (6.0 * engine.reference_rpm), step)
                break
            except ValueError as exc:
                allowed = ("inadmissible species mass", "CFL limit exceeded",
                           "rho/p/Y inadmissible")
                if not any(reason in str(exc) for reason in allowed):
                    raise
                rejected_trials.append({"angle_deg": angle,
                                        "attempted_step_deg": step,
                                        "reason": str(exc)})
                step *= .5
        else:
            raise RuntimeError(f"no accepted step at {angle:.12g} degrees")


def _write_gzip_json(path: Path, value: object) -> None:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"),
                         allow_nan=False).encode("utf-8")
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as stream:
            stream.write(payload)


def _write_failure_receipt(output: Path, fixture_id: str, cycle_index: int,
                           target_angle: float, engine: IntegratedEngine2T,
                           config_hash: str, prereg_hash: str,
                           rejected_trials: list[dict], error: Exception) -> None:
    receipt = {
        "schema": "MOTORSIM_COMMERCIAL_CYCLE_FAILURE_V1",
        "fixture_id": fixture_id,
        "engine_configuration_sha256": config_hash,
        "preregistration_sha256": prereg_hash,
        "cycle_index": cycle_index,
        "target_angle_deg": target_angle,
        "reached_angle_deg": engine.crank_angle_unwrapped_deg,
        "accepted_step_count": engine.accepted_steps,
        "failure_type": type(error).__name__,
        "failure_reason": str(error),
        "completed_cycle_files": sorted(path.name for path in output.glob("cycle-*.json.gz")),
        "current_state": engine.state,
        "current_inventory": engine.inventory(),
        "ledger": engine.ledger,
        "rejected_trials": rejected_trials,
    }
    (output / "failure.json").write_text(
        json.dumps(receipt, sort_keys=True, indent=2, allow_nan=False) + "\n",
        encoding="utf-8")


def produce(fixture_id: str, horizon: int, restart_cycle: int,
            preregistration_path: Path, preregistration_commit: str,
            output: Path) -> None:
    engine, wrapper, config_hash = load_engine(fixture_id)
    prereg, prereg_hash = _require_preregistration(
        preregistration_path, fixture_id, config_hash, horizon, restart_cycle,
        preregistration_commit)
    output.mkdir(parents=True, exist_ok=False)
    start = engine.snapshot()
    rejected: list[dict] = []
    runner_sha256 = _sha256(
        Path(__file__).read_bytes().replace(b"\r\n", b"\n"))
    restart_snapshot = None
    restart_engine = None
    for cycle in range(1, horizon + 1):
        rejection_start = len(rejected)
        try:
            advance_to(engine, float(cycle * 360), rejected)
        except Exception as exc:
            _write_failure_receipt(output, fixture_id, cycle, float(cycle * 360),
                                   engine, config_hash, prereg_hash, rejected, exc)
            raise
        end = engine.snapshot()
        record = make_integrated_cycle_primary(
            engine, start, end, cycle,
            rejected_trials=rejected[rejection_start:],
            runner_sha256=runner_sha256)
        _write_gzip_json(output / f"cycle-{cycle:03d}.json.gz", record)
        if cycle == restart_cycle:
            restart_snapshot = end
            restart_engine = IntegratedEngine2T.from_configuration_dict(
                wrapper["engine_configuration"])
            restart_engine.restore(restart_snapshot)
        if restart_cycle < cycle <= restart_cycle + 1 and restart_engine is not None:
            replay_rejections: list[dict] = []
            try:
                advance_to(restart_engine, float(cycle * 360), replay_rejections)
            except Exception as exc:
                _write_failure_receipt(output, fixture_id, cycle, float(cycle * 360),
                                       engine, config_hash, prereg_hash, rejected, exc)
                raise
            if restart_engine.snapshot() != end:
                error = ValueError("restart replay differs from continuous trajectory")
                _write_failure_receipt(output, fixture_id, cycle, float(cycle * 360),
                                       engine, config_hash, prereg_hash, rejected, error)
                raise error
            if cycle == restart_cycle + 1:
                (output / "restart-audit.json").write_text(json.dumps({
                    "status": "EXACT_REPLAY_PASS",
                    "restart_cycle": restart_cycle,
                    "compared_terminal_cycle": cycle,
                    "snapshot_equal": True,
                    "continuous_rejected_trials": rejected,
                    "replay_rejected_trials": replay_rejections,
                }, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        start = end
    manifest = {
        "schema": "MOTORSIM_COMMERCIAL_CYCLE_PRODUCER_MANIFEST_V1",
        "fixture_id": fixture_id,
        "fixture_status": wrapper["selection_status"],
        "engine_configuration_sha256": config_hash,
        "preregistration_sha256": prereg_hash,
        "preregistration_commit": preregistration_commit,
        "producer_commit": prereg.get("producer_commit"),
        "producer_source_sha256": _sha256(
            Path(__file__).read_bytes().replace(b"\r\n", b"\n")),
        "detector_source_sha256": _sha256(
            PERIODICITY_CONTRACT.read_bytes().replace(b"\r\n", b"\n")),
        "horizon_cycles": horizon,
        "restart_cycle": restart_cycle,
        "continuous_rejected_trials": rejected,
        "output_cycle_count": horizon,
    }
    (output / "manifest.json").write_text(json.dumps(
        manifest, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", choices=("A", "B", "C", "D"), required=True)
    parser.add_argument("--validate-only", action="store_true",
                        help="load and round-trip the committed fixture; do not integrate")
    parser.add_argument("--horizon", type=int)
    parser.add_argument("--restart-cycle", type=int)
    parser.add_argument("--preregistration", type=Path)
    parser.add_argument("--preregistration-commit")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        engine, wrapper, config_hash = load_engine(args.fixture)
        if args.validate_only:
            print(json.dumps({"fixture_id": args.fixture,
                              "fixture_status": wrapper["selection_status"],
                              "configuration_schema": engine.configuration_schema,
                              "engine_configuration_sha256": config_hash},
                             sort_keys=True))
            return 0
        if (args.horizon is None or args.horizon < 2 or
                args.restart_cycle is None or
                not 1 <= args.restart_cycle < args.horizon or
                args.preregistration is None or
                args.preregistration_commit is None or args.output is None):
            parser.error("integration requires horizon >= 2, restart cycle, committed preregistration and output")
        produce(args.fixture, args.horizon, args.restart_cycle,
                args.preregistration.resolve(), args.preregistration_commit,
                args.output.resolve())
        return 0
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        parser.exit(2, f"producer blocked: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
