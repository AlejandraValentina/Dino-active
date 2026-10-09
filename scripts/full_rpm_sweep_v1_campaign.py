"""Opt-in resumable FULL_RPM_SWEEP_V1 campaign runner.

Default invocation is preflight-only. A campaign requires ``--execute``, a
durable readiness PASS, and an output directory outside the Git repository.
This runner is intentionally not invoked as part of readiness verification.
"""
from __future__ import annotations

import argparse
import copy
import gzip
import hashlib
import json
import os
from pathlib import Path
import sys
import time
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from motorsim.full_rpm_outputs_v1 import compute_full_rpm_outputs_v1  # noqa: E402
from motorsim.full_rpm_sweep_v1 import (  # noqa: E402
    PREREGISTRATION,
    preflight_full_rpm_sweep_v1,
    rpm_points,
)
from motorsim.integrated_2t import (  # noqa: E402
    IntegratedEngine2T,
    audit_integrated_cycle_primary,
    make_integrated_cycle_primary,
    _solver_dependency_hashes,
)
from motorsim.mechanical_loss_binding_v1 import (  # noqa: E402
    canonical_sha256,
    resolve_mechanical_loss_v1,
)
from motorsim.reference_harness.convergence import (  # noqa: E402
    CONTRACT,
    CONTRACT_V2,
    PeriodicDetectorV2,
)
from scripts.produce_integrated_cycle_evidence import advance_to  # noqa: E402


PROGRAM_STATUS = ROOT / "results/2t-commercial-core-20261002/program-status.json"
MAX_INVOCATION_SECONDS = 3600


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _read_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object at {path}")
    return value


def _write_json_atomic(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    temp.write_text(json.dumps(value, sort_keys=True, indent=2,
                               ensure_ascii=False, allow_nan=False) + "\n",
                    encoding="utf-8", newline="\n")
    temp.replace(path)


def _write_primary_gzip(path: Path, value: Any) -> None:
    payload = _canonical_bytes(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    with temp.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as stream:
            stream.write(payload)
    temp.replace(path)


def _projection(primary: dict) -> dict:
    return {"cycle_index": primary["cycle_index"],
            "configuration_hash": primary["configuration_hash"],
            "contract": CONTRACT, "observables": primary["observables"]}


def _require_readiness_pass() -> None:
    status = _read_json(PROGRAM_STATUS)
    gate = status.get("gate_status", {})
    if (gate.get("objective") != "FULL_RPM_SWEEP_V1" or
            gate.get("state") != "PASS" or
            gate.get("classification") != "FULL_RPM_SWEEP_V1_READINESS_PASS" or
            status.get("full_rpm_sweep_precondition") != "EXPLICIT_MECHANICAL_LOSS_MODEL_REQUIRED" or
            status.get("full_rpm_sweep_precondition_status") != "RESOLVED" or
            status.get("full_rpm_sweep_executable") is not True or
            status.get("full_rpm_sweep_status") != "NOT_STARTED"):
        raise RuntimeError("FULL_RPM_SWEEP_V1 readiness PASS is not durably registered")
    if status.get("full_rpm_sweep_execution_authorized") is not True:
        raise RuntimeError("FULL_RPM_SWEEP_V1 campaign execution is not authorized")


def _point_contract_hashes(prereg: dict, prereg_sha: str, variant: dict,
                           resolved_loss, rpm: int) -> dict:
    return {
        "preregistration_sha256": prereg_sha,
        "fixture_sha256": variant["fixture_sha256"],
        "engine_configuration_sha256": variant["engine_configuration_sha256"],
        "point_configuration_sha256": _point_configuration_hash(variant, rpm),
        "mechanical_loss_model_sha256": resolved_loss.model_sha256,
        "fuel_sha256": variant.get("fuel", {}).get("sha256"),
        "mixture_ratio_basis": variant.get("mixture_input"),
        "solver_dependency_hashes": _solver_dependency_hashes(),
        "periodicity_contract": prereg["periodicity"]["contract"],
        "periodicity_source_sha256": prereg["periodicity_source_sha256"],
        "campaign_producer_sha256": _sha256(
            Path(__file__).read_bytes().replace(b"\r\n", b"\n")),
        "output_adapter_sha256": _sha256(
            (ROOT / "motorsim/full_rpm_outputs_v1.py").read_bytes().replace(b"\r\n", b"\n")),
    }


def _point_configuration_hash(variant: dict, rpm: int) -> str:
    fixture_path = ROOT / variant["source_fixture_path"]
    fixture = _read_json(fixture_path)
    config = copy.deepcopy(fixture["engine_configuration"])
    config["reference_rpm"] = float(rpm)
    return canonical_sha256(config)


def _configuration_for(variant: dict, rpm: int) -> dict:
    fixture = _read_json(ROOT / variant["source_fixture_path"])
    config = copy.deepcopy(fixture["engine_configuration"])
    config["reference_rpm"] = float(rpm)
    return config


def _load_checkpoint(path: Path, expected: dict) -> dict:
    value = _read_json(path)
    if value.get("schema") != "FULL_RPM_SWEEP_V1_POINT_CHECKPOINT":
        raise ValueError("checkpoint schema mismatch")
    if value.get("bindings") != expected:
        raise ValueError("checkpoint binding hash mismatch")
    if type(value.get("next_cycle")) is not int or value["next_cycle"] < 1:
        raise ValueError("checkpoint next_cycle is invalid")
    if not isinstance(value.get("engine_snapshot"), dict):
        raise ValueError("checkpoint engine state is missing")
    if not isinstance(value.get("periodicity_snapshot"), dict):
        raise ValueError("checkpoint detector state is missing")
    return value


def _run_point(prereg: dict, prereg_sha: str, variant: dict, rpm: int,
               output_root: Path, *, resume: bool,
               started: float, budget_seconds: int) -> dict:
    resolved_loss = resolve_mechanical_loss_v1(
        preregistration_path=ROOT / PREREGISTRATION,
        variant_id=variant["variant_id"], repository_root=ROOT,
        rpm_points=prereg["rpm_grid"]["points_rpm"], load=1.0)
    bindings = _point_contract_hashes(prereg, prereg_sha, variant,
                                      resolved_loss, rpm)
    point_dir = output_root / variant["variant_id"] / f"rpm-{rpm:05d}"
    result_path = point_dir / "result.json"
    checkpoint_path = point_dir / "checkpoint.json"
    if result_path.is_file():
        prior = _read_json(result_path)
        if prior.get("bindings") != bindings:
            raise ValueError(f"persisted result binding mismatch: {point_dir}")
        return prior

    config = _configuration_for(variant, rpm)
    engine = IntegratedEngine2T.from_configuration_dict(config)
    detector = PeriodicDetectorV2()
    if checkpoint_path.is_file():
        if not resume:
            raise FileExistsError(f"incomplete point exists; pass --resume: {point_dir}")
        checkpoint = _load_checkpoint(checkpoint_path, bindings)
        engine.restore(checkpoint["engine_snapshot"])
        detector.restore(checkpoint["periodicity_snapshot"])
        start_snapshot = engine.snapshot()
        first_cycle = checkpoint["next_cycle"]
    else:
        if point_dir.exists() and any(point_dir.iterdir()):
            raise FileExistsError(f"unrecognized partial point state: {point_dir}")
        point_dir.mkdir(parents=True, exist_ok=True)
        start_snapshot = engine.snapshot()
        first_cycle = 1

    point_id = f"{variant['variant_id']}@{rpm}RPM"
    cycle_rows = []
    if first_cycle > 1:
        prior_cycle_path = point_dir / f"cycle-{first_cycle - 1:03d}.json.gz"
        if not prior_cycle_path.is_file():
            raise ValueError("checkpoint exists without its prior primary")
        for cycle in range(1, first_cycle):
            primary_path = point_dir / f"cycle-{cycle:03d}.json.gz"
            if not primary_path.is_file():
                raise ValueError("checkpoint primary history is incomplete")
            primary = json.loads(gzip.decompress(primary_path.read_bytes()))
            audit = audit_integrated_cycle_primary(primary)
            if audit.get("recomputed") is not True:
                raise ValueError("persisted primary failed replay audit")
            cycle_rows.append({"cycle": cycle, "primary_sha256": _sha256(_canonical_bytes(primary)),
                               "audit": "PASS"})

    for cycle in range(first_cycle, prereg["horizon"]["max_complete_cycles_per_point"] + 1):
        rejected: list[dict] = []
        try:
            advance_to(engine, float(cycle * 360), rejected)
            end_snapshot = engine.snapshot()
            primary = make_integrated_cycle_primary(
                engine, start_snapshot, end_snapshot, cycle,
                rejected_trials=rejected,
                runner_sha256=_sha256(Path(__file__).read_bytes().replace(b"\r\n", b"\n")))
        except Exception as exc:  # Persist causal numerical failure and no engineering values.
            failure = {
                "schema": "FULL_RPM_SWEEP_V1_POINT_RESULT",
                "point_id": point_id,
                "rpm": rpm,
                "classification": "NUMERICAL_INVALID",
                "failure_type": type(exc).__name__,
                "failure_reason": str(exc),
                "cycles_completed": cycle - 1,
                "engineering_outputs": None,
                "bindings": bindings,
            }
            _write_json_atomic(result_path, failure)
            return failure
        audit = audit_integrated_cycle_primary(primary)
        if audit.get("recomputed") is not True or primary.get("admissible") is not True:
            failure = {
                "schema": "FULL_RPM_SWEEP_V1_POINT_RESULT",
                "point_id": point_id,
                "rpm": rpm,
                "classification": "PRIMARY_AUDIT_FAIL" if audit.get("recomputed") is not True
                                  else "PHYSICAL_INVALID",
                "audit": audit,
                "cycles_completed": cycle,
                "engineering_outputs": None,
                "bindings": bindings,
            }
            _write_primary_gzip(point_dir / f"cycle-{cycle:03d}.json.gz", primary)
            _write_json_atomic(result_path, failure)
            return failure

        primary_payload = _canonical_bytes(primary)
        primary_sha = _sha256(primary_payload)
        _write_primary_gzip(point_dir / f"cycle-{cycle:03d}.json.gz", primary)
        update = detector.update(_projection(primary))
        cycle_rows.append({"cycle": cycle, "primary_sha256": primary_sha,
                           "audit": "PASS", "detector": update})
        classification = detector.classification
        if classification in ("PERIOD_1", "PERIOD_2"):
            observables = primary["observables"]
            outputs = compute_full_rpm_outputs_v1(
                cylinder_indicated_work_j=observables["cylinder_indicated_work_J"],
                net_piston_gas_work_j=observables["net_piston_gas_work_J"],
                swept_displacement_m3=primary["swept_displacement_m3"],
                rpm=rpm,
                air_delivered_kg=observables["fresh_air_intake_delivery_kg"],
                fuel_delivered_kg=observables["fuel_delivered_kg"],
                stoichiometric_afr=variant["fuel"]["stoichiometric_afr"],
                mechanical_loss=resolved_loss,
                primary_id=point_id,
                primary_sha256=primary_sha,
                cycle_index=cycle,
                load=1.0,
            )
            terminal = {
                "schema": "FULL_RPM_SWEEP_V1_POINT_RESULT",
                "point_id": point_id,
                "variant_id": variant["variant_id"],
                "rpm": rpm,
                "classification": classification,
                "converged_cycle": detector.converged_cycle,
                "periodicity_contract": CONTRACT_V2,
                "cycles_completed": cycle,
                "engineering_outputs": outputs,
                "bindings": bindings,
                "cycle_primaries": [row["primary_sha256"] for row in cycle_rows],
            }
            _write_json_atomic(result_path, terminal)
            return terminal

        # Keep the complete-cycle state but discard trajectory memory before
        # the next cycle. The exact physical state and ledgers are retained.
        engine.trace = []
        engine.accepted_steps = 0
        engine.rejected_steps = 0
        start_snapshot = engine.snapshot()
        checkpoint = {
            "schema": "FULL_RPM_SWEEP_V1_POINT_CHECKPOINT",
            "bindings": bindings,
            "next_cycle": cycle + 1,
            "engine_snapshot": start_snapshot,
            "periodicity_snapshot": detector.snapshot(),
        }
        _write_json_atomic(checkpoint_path, checkpoint)
        if time.monotonic() - started >= budget_seconds:
            interrupted = {
                "schema": "FULL_RPM_SWEEP_V1_POINT_RESULT",
                "point_id": point_id,
                "variant_id": variant["variant_id"],
                "rpm": rpm,
                "classification": "INTERRUPTED_CHECKPOINTED",
                "cycles_completed": cycle,
                "next_cycle": cycle + 1,
                "engineering_outputs": None,
                "bindings": bindings,
            }
            # Do not create result.json: a later --resume must continue this point.
            _write_json_atomic(point_dir / "checkpoint-status.json", interrupted)
            return interrupted

    terminal = {
        "schema": "FULL_RPM_SWEEP_V1_POINT_RESULT",
        "point_id": point_id,
        "variant_id": variant["variant_id"],
        "rpm": rpm,
        "classification": "NO_CONVERGENCE_WITHIN_HORIZON",
        "periodicity_contract": CONTRACT_V2,
        "cycles_completed": prereg["horizon"]["max_complete_cycles_per_point"],
        "engineering_outputs": None,
        "bindings": bindings,
        "cycle_primaries": [row["primary_sha256"] for row in cycle_rows],
    }
    _write_json_atomic(result_path, terminal)
    return terminal


def execute_campaign(*, output_root: str | Path, resume: bool = False,
                     budget_seconds: int = MAX_INVOCATION_SECONDS) -> dict:
    """Run only after a durable readiness PASS; not used by readiness checks."""
    _require_readiness_pass()
    if type(budget_seconds) is not int or not 1 <= budget_seconds <= MAX_INVOCATION_SECONDS:
        raise ValueError("budget_seconds must be an integer in [1, 3600]")
    out = Path(output_root).resolve()
    if out == ROOT or out.is_relative_to(ROOT):
        raise ValueError("sweep outputs must be outside the Git repository")
    prereg_path = ROOT / PREREGISTRATION
    preflight = preflight_full_rpm_sweep_v1(prereg_path, repository_root=ROOT)
    if preflight.get("preflight_status") != "PASS":
        raise RuntimeError("FULL_RPM_SWEEP_V1 preflight failed closed")
    prereg_bytes = prereg_path.read_bytes()
    prereg = json.loads(prereg_bytes)
    prereg_sha = canonical_sha256(prereg)
    output_manifest = out / "campaign.json"
    if output_manifest.exists() and not resume:
        raise FileExistsError("campaign output exists; pass --resume or choose a fresh external directory")
    started = time.monotonic()
    point_results = []
    for variant in prereg["variants"]:
        for rpm in rpm_points(prereg):
            point_result = _run_point(
                prereg, prereg_sha, variant, rpm, out,
                resume=resume, started=started, budget_seconds=budget_seconds)
            point_results.append({"point_id": point_result["point_id"],
                                  "classification": point_result["classification"],
                                  "result_path": str((out / variant["variant_id"] /
                                                       f"rpm-{rpm:05d}" / "result.json"))
                                  if (out / variant["variant_id"] /
                                      f"rpm-{rpm:05d}" / "result.json").is_file() else None})
            summary = {
                "schema": "FULL_RPM_SWEEP_V1_CAMPAIGN_SUMMARY",
                "pre-registration_sha256": prereg_sha,
                "preflight_status": "PASS",
                "campaigns_started": 1,
                "campaign_status": "IN_PROGRESS",
                "completed_or_checkpointed_points": point_results,
                "updated_solver_dependency_hashes": _solver_dependency_hashes(),
            }
            point_dir = out / variant["variant_id"] / f"rpm-{rpm:05d}"
            result_file = point_dir / "result.json"
            checkpoint_status = point_dir / "checkpoint-status.json"
            checkpoint_file = point_dir / "checkpoint.json"
            if result_file.is_file():
                point_results[-1]["result_sha256"] = _sha256(result_file.read_bytes())
            elif checkpoint_status.is_file() and checkpoint_file.is_file():
                point_results[-1]["checkpoint_sha256"] = _sha256(checkpoint_file.read_bytes())
            _write_json_atomic(output_manifest, summary)
            if point_result["classification"] == "INTERRUPTED_CHECKPOINTED":
                summary["campaign_status"] = "INTERRUPTED_CHECKPOINTED"
                _write_json_atomic(output_manifest, summary)
                return summary
    summary = {
        "schema": "FULL_RPM_SWEEP_V1_CAMPAIGN_SUMMARY",
        "pre-registration_sha256": prereg_sha,
        "preflight_status": "PASS",
        "campaigns_started": 1,
        "campaign_status": "COMPLETE_WITH_POINT_CLASSIFICATIONS",
        "completed_or_checkpointed_points": point_results,
        "updated_solver_dependency_hashes": _solver_dependency_hashes(),
    }
    _write_json_atomic(output_manifest, summary)
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true",
                        help="start the campaign (requires durable readiness PASS)")
    parser.add_argument("--output-root", type=Path,
                        help="durable external artifact directory; must be outside the repo")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--budget-seconds", type=int, default=MAX_INVOCATION_SECONDS)
    args = parser.parse_args(argv)
    if not args.execute:
        report = preflight_full_rpm_sweep_v1(repository_root=ROOT)
        print(json.dumps(report, sort_keys=True))
        return 0 if report["preflight_status"] == "PASS" else 1
    output_root = args.output_root
    if output_root is None:
        artifact_root = os.environ.get("DINO_ARTIFACT_ROOT")
        if not artifact_root:
            parser.error("--execute requires --output-root or DINO_ARTIFACT_ROOT")
        output_root = Path(artifact_root) / "engine-physics-v1/full-rpm-sweep-v1"
    result = execute_campaign(output_root=output_root, resume=args.resume,
                              budget_seconds=args.budget_seconds)
    print(json.dumps({"campaign_status": result["campaign_status"],
                      "points": len(result["completed_or_checkpointed_points"]),
                      "campaigns_started": result["campaigns_started"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
