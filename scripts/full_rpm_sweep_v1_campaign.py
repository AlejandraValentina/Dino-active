"""Opt-in resumable FULL_RPM_SWEEP_V1_IMPL2 campaign runner.

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
import platform
import os
import shutil
from pathlib import Path
import sys
import time
import importlib.metadata
import importlib.util
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
    _integrated_nominal_step_end,
    _integrated_scheduled_angles,
    audit_integrated_cycle_primary,
    make_integrated_cycle_primary,
    _solver_dependency_hashes,
)
from motorsim.mechanical_loss_binding_v1 import (  # noqa: E402
    canonical_sha256,
    resolve_mechanical_loss_v1,
)
from motorsim.scavenging_partition_v1 import evaluate_scavenging_partition_v1  # noqa: E402
from motorsim.reference_harness.convergence import (  # noqa: E402
    CONTRACT,
    CONTRACT_V2,
    PeriodicDetectorV2,
)


PROGRAM_STATUS = ROOT / "results/2t-commercial-core-20261002/program-status.json"
MAX_INVOCATION_SECONDS = 3600
IMPLEMENTATION_VERSION = "FULL_RPM_SWEEP_V1_IMPL2"


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


def _write_primary_gzip(path: Path, value: Any | None = None,
                        *, payload: bytes | None = None) -> None:
    if payload is None:
        payload = _canonical_bytes(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    with temp.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as stream:
            stream.write(payload)
    temp.replace(path)


def _process_rss_bytes() -> int | None:
    try:
        import psutil
        return int(psutil.Process(os.getpid()).memory_info().rss)
    except (ImportError, OSError):
        return None


def _write_cycle_metrics(point_dir: Path, cycle: int, metrics: dict) -> None:
    _write_json_atomic(point_dir / "cycle-metrics" / f"cycle-{cycle:03d}.json", metrics)


def _record_checkpoint_progress(output_root: Path, variant: dict, rpm: int,
                                checkpoint_path: Path,
                                checkpoint_status: dict) -> None:
    manifest_path = output_root / "campaign.json"
    if not manifest_path.is_file():
        raise RuntimeError("campaign manifest must be persisted before solver work")
    manifest = _read_json(manifest_path)
    point_id = f"{variant['variant_id']}@{rpm}RPM"
    for row in manifest.get("completed_or_checkpointed_points", []):
        if row.get("point_id") == point_id:
            row.update({
                "classification": checkpoint_status["classification"],
                "cycles_completed": checkpoint_status["cycles_completed"],
                "next_cycle": checkpoint_status["next_cycle"],
                "checkpoint_path": str(checkpoint_path.relative_to(output_root)),
                "checkpoint_sha256": _sha256(checkpoint_path.read_bytes()),
                "performance_metrics": checkpoint_status.get("performance_metrics"),
            })
            break
    else:
        raise ValueError(f"campaign manifest lacks the registered point: {point_id}")
    manifest["campaigns_started"] = 1
    if checkpoint_status["classification"] != "INTERRUPTED_CHECKPOINTED":
        manifest["campaign_status"] = "IN_PROGRESS"
    _write_json_atomic(manifest_path, manifest)


def _record_point_started(output_root: Path, variant: dict, rpm: int,
                          *, cycles_completed: int, next_cycle: int) -> None:
    manifest_path = output_root / "campaign.json"
    manifest = _read_json(manifest_path)
    point_id = f"{variant['variant_id']}@{rpm}RPM"
    for row in manifest.get("completed_or_checkpointed_points", []):
        if row.get("point_id") == point_id:
            row.update({"classification": "IN_PROGRESS",
                        "cycles_completed": cycles_completed,
                        "next_cycle": next_cycle})
            break
    else:
        raise ValueError(f"campaign manifest lacks the registered point: {point_id}")
    manifest["campaigns_started"] = 1
    manifest["campaign_status"] = "IN_PROGRESS"
    _write_json_atomic(manifest_path, manifest)


def _point_performance_metrics(cycle_metrics: list[dict]) -> dict:
    elapsed = [float(row["cycle_elapsed_s"]) for row in cycle_metrics
               if isinstance(row.get("cycle_elapsed_s"), (int, float))]
    return {
        "measured_cycles": len(elapsed),
        "mean_cycle_seconds": (sum(elapsed) / len(elapsed) if elapsed else None),
        "total_measured_cycle_seconds": sum(elapsed),
        "accepted_steps": sum(int(row.get("accepted_solver_steps", 0))
                               for row in cycle_metrics),
        "rejected_steps": sum(int(row.get("rejected_solver_steps", 0))
                               for row in cycle_metrics),
        "primary_compressed_bytes": sum(int(row.get("primary_compressed_bytes", 0))
                                         for row in cycle_metrics),
        "max_observed_process_rss_bytes": max(
            (int(row["process_rss_bytes"]) for row in cycle_metrics
             if row.get("process_rss_bytes") is not None), default=None),
        "serialization_seconds": sum(float(row.get("primary_serialization_seconds", 0))
                                      for row in cycle_metrics),
        "checkpoint_seconds": sum(float(row.get("checkpoint_write_seconds", 0))
                                   for row in cycle_metrics),
    }


def _r2_compatible_scavenging(primary: dict) -> dict:
    """Retain gross ledgers/conservation; mask non-identifiable retention claims."""
    partition = evaluate_scavenging_partition_v1(primary)
    reason = "CURRENT_CYCLE_FRESH_RETENTION_NOT_IDENTIFIABLE"
    for name in ("trapping_efficiency", "charging_efficiency", "scavenging_efficiency"):
        prior = partition["metrics"]["ratios"].get(name, {})
        partition["metrics"]["ratios"][name] = {
            "value": None, "status": "UNDEFINED", "reason": reason,
            "definition_version": "R2_CURRENT_CYCLE_FRESH_RETENTION_V1",
            "superseded_definition": prior.get("status"),
        }
    for name in ("fresh_retained", "fresh_lost"):
        if name in partition["metrics"].get("masses_kg", {}):
            partition["metrics"]["masses_kg"][name] = {
                "value": None, "status": "NOT_IDENTIFIABLE", "reason": reason,
                "definition_version": "R2_CURRENT_CYCLE_FRESH_RETENTION_V1",
            }
    partition["metrics"]["r2_current_semantics"] = {
        "TE_CE_SE": "UNDEFINED",
        "reason": reason,
        "gross_crossing_and_species_conservation_preserved": True,
    }
    return partition


def _ensure_campaign_provenance(out: Path, prereg: dict,
                                prereg_sha: str) -> dict:
    """Bundle the exact inputs and implementation needed to inspect results."""
    provenance_dir = out / "provenance"
    provenance_dir.mkdir(parents=True, exist_ok=True)
    prereg_path = provenance_dir / "preregistration.json"
    if prereg_path.exists():
        if canonical_sha256(_read_json(prereg_path)) != prereg_sha:
            raise ValueError("external artifact bundle preregistration hash mismatch")
    else:
        _write_json_atomic(prereg_path, prereg)

    source_paths = {
        "motorsim/mechanical_loss_binding_v1.py",
        "motorsim/full_rpm_outputs_v1.py",
        "motorsim/full_rpm_sweep_v1.py",
        "motorsim/reference_harness/convergence.py",
        "motorsim/scavenging_partition_v1.py",
        "motorsim/scavenging.py",
        "scripts/full_rpm_sweep_v1_campaign.py",
        "scripts/summarize_full_rpm_sweep_v1.py",
        "scripts/verify_full_rpm_sweep_v1_contract.py",
        "scripts/verify_full_rpm_sweep_v1_artifacts.py",
        "openspec/changes/full-rpm-sweep-v1/specs/full-rpm-sweep-v1/spec.md",
        "results/full-rpm-sweep-v1/readiness.json",
        "results/full-rpm-sweep-v1/preflight.json",
        "results/full-rpm-sweep-v1/campaign-authorization.json",
    }
    for module_name in prereg["solver_dependency_hashes"]:
        source_paths.add(module_name.replace(".", "/") + ".py")
    for variant in prereg["variants"]:
        source_paths.add(variant["source_fixture_path"])
    files = {}
    expected_fixture_hashes = {
        variant["source_fixture_path"]: variant["fixture_sha256"]
        for variant in prereg["variants"]
    }
    for relative in sorted(source_paths):
        source = ROOT / relative
        payload = source.read_bytes()
        digest = _sha256(payload.replace(b"\r\n", b"\n"))
        raw_digest = _sha256(payload)
        expected_fixture = expected_fixture_hashes.get(relative)
        if expected_fixture is not None and raw_digest != expected_fixture:
            raise ValueError(f"fixture source hash differs from preregistration: {relative}")
        expected = prereg["solver_dependency_hashes"].get(
            relative[:-3].replace("/", "."))
        if expected is not None and digest != expected:
            raise ValueError(f"solver source hash differs from preregistration: {relative}")
        target = provenance_dir / "source" / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            target_digest = _sha256(target.read_bytes().replace(b"\r\n", b"\n"))
            if target_digest != digest:
                raise ValueError(f"external source bundle hash mismatch: {relative}")
        else:
            shutil.copy2(source, target)
        files[relative] = {"sha256": digest,
                           "artifact_path": str(target.relative_to(out))}

    configurations = {}
    for variant in prereg["variants"]:
        fixture = _read_json(ROOT / variant["source_fixture_path"])
        config = fixture["engine_configuration"]
        config_path = provenance_dir / "configurations" / f"{variant['variant_id']}.json"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        _write_json_atomic(config_path, config)
        configurations[variant["variant_id"]] = {
            "fixture_sha256": variant["fixture_sha256"],
            "engine_configuration_sha256": canonical_sha256(config),
            "artifact_path": str(config_path.relative_to(out)),
        }
    receipt = {
        "schema": "FULL_RPM_SWEEP_V1_ARTIFACT_PROVENANCE_V1",
        "campaign_id": f"{IMPLEMENTATION_VERSION}_{prereg_sha[:16]}",
        "preregistration_sha256": prereg_sha,
        "authorization_sha256": _sha256(
            (ROOT / "results/full-rpm-sweep-v1/campaign-authorization.json").read_bytes()),
        "campaign_runner_sha256": _sha256(
            Path(__file__).read_bytes().replace(b"\r\n", b"\n")),
        "python_version": sys.version,
        "platform": platform.platform(),
        "psutil_version": importlib.metadata.version("psutil")
        if importlib.util.find_spec("psutil") else None,
        "solver_dependencies": prereg["solver_dependency_hashes"],
        "source_files": files,
        "variant_configurations": configurations,
        "provenance": "SYNTHETIC_ASSUMPTION_CONDITIONAL_ON_P4; no experimental validation",
    }
    receipt_path = provenance_dir / "manifest.json"
    if receipt_path.exists():
        prior = _read_json(receipt_path)
        if prior != receipt:
            raise ValueError("external artifact provenance manifest mismatch")
    else:
        _write_json_atomic(receipt_path, receipt)
    return receipt


def _selected_points(prereg: dict, *, pilot: bool) -> list[tuple[dict, int]]:
    if not pilot:
        return [(variant, rpm) for variant in prereg["variants"]
                for rpm in rpm_points(prereg)]
    variants = {variant["variant_id"]: variant for variant in prereg["variants"]}
    required = ("A_PRIME_MESH_0", "B_PRIME_MESH_0")
    if not all(name in variants for name in required):
        raise ValueError("registered pilot variants are missing")
    if 4000 not in rpm_points(prereg):
        raise ValueError("registered pilot RPM 4000 is missing")
    return [(variants[name], 4000) for name in required]


def _projection(primary: dict) -> dict:
    return {"cycle_index": primary["cycle_index"],
            "configuration_hash": primary["configuration_hash"],
            "contract": CONTRACT, "observables": primary["observables"]}


class _CampaignDeadlineReached(Exception):
    pass


def _advance_to_bounded(engine: IntegratedEngine2T, target_angle: float,
                        rejected_trials: list[dict], deadline: float) -> None:
    """Advance using the registered stepping schedule with deadline checks."""
    scheduled = _integrated_scheduled_angles(engine, target_angle)
    while engine.crank_angle_unwrapped_deg < target_angle - 1e-10:
        if time.monotonic() >= deadline:
            raise _CampaignDeadlineReached
        angle = engine.crank_angle_unwrapped_deg
        target = _integrated_nominal_step_end(engine, angle, target_angle, scheduled)
        step = target - angle
        for attempt in range(25):
            if time.monotonic() >= deadline:
                raise _CampaignDeadlineReached
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


def _require_readiness_pass() -> None:
    status = _read_json(PROGRAM_STATUS)
    gate = status.get("gate_status", {})
    readiness = status.get("readiness_gate_status", gate)
    if (readiness.get("objective") != "FULL_RPM_SWEEP_V1" or
            readiness.get("state") != "PASS" or
            readiness.get("classification") != "FULL_RPM_SWEEP_V1_READINESS_PASS" or
            status.get("full_rpm_sweep_precondition") != "EXPLICIT_MECHANICAL_LOSS_MODEL_REQUIRED" or
            status.get("full_rpm_sweep_precondition_status") != "RESOLVED" or
            status.get("full_rpm_sweep_executable") is not True or
            status.get("full_rpm_sweep_status") not in {"NOT_STARTED", "IN_PROGRESS", "PARTIAL"}):
        raise RuntimeError("FULL_RPM_SWEEP_V1 readiness PASS is not durably registered")
    if status.get("full_rpm_sweep_execution_authorized") is not True:
        raise RuntimeError("FULL_RPM_SWEEP_V1 campaign execution is not authorized")
    authorization = _read_json(ROOT / "results/full-rpm-sweep-v1/campaign-authorization.json")
    prereg = _read_json(ROOT / PREREGISTRATION)
    expected_variants = [item["variant_id"] for item in prereg["variants"]]
    if (authorization.get("authorized") is not True or
            authorization.get("scope", {}).get("variants") != expected_variants or
            authorization.get("scope", {}).get("maximum_points") != 30 or
            authorization.get("scope", {}).get("rpm_points_per_variant") != 15):
        raise RuntimeError("FULL_RPM_SWEEP_V1 authorization receipt does not match preregistration")


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
        "implementation_version": IMPLEMENTATION_VERSION,
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


def _load_checkpoint(path: Path, expected: dict,
                     expected_file_sha256: str | None = None) -> dict:
    payload = path.read_bytes()
    if (expected_file_sha256 is not None and
            _sha256(payload) != expected_file_sha256):
        raise ValueError("checkpoint artifact hash mismatch")
    value = json.loads(payload)
    if (value.get("schema") != "FULL_RPM_SWEEP_V1_IMPL2_POINT_CHECKPOINT" or
            value.get("implementation_version") != IMPLEMENTATION_VERSION):
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
        campaign_manifest = _read_json(output_root / "campaign.json")
        point_row = next((row for row in campaign_manifest.get(
            "completed_or_checkpointed_points", [])
                          if row.get("point_id") == point_id), None)
        if not isinstance(point_row, dict) or not isinstance(
                point_row.get("checkpoint_sha256"), str):
            raise ValueError("checkpoint artifact hash is missing from campaign manifest")
        checkpoint = _load_checkpoint(
            checkpoint_path, bindings,
            expected_file_sha256=point_row["checkpoint_sha256"])
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
    cycle_metrics = []
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
            prior_sha = _sha256(_canonical_bytes(primary))
            measurement_path = point_dir / "cycle-metrics" / f"cycle-{cycle:03d}.json"
            if not measurement_path.is_file():
                raise ValueError("checkpointed primary lacks its performance measurement receipt")
            measurement = _read_json(measurement_path)
            if (measurement.get("cycle") != cycle or
                    measurement.get("primary_sha256") != prior_sha):
                raise ValueError("cycle measurement receipt does not match its primary")
            cycle_metrics.append(measurement)
            cycle_rows.append({"cycle": cycle, "primary_sha256": prior_sha,
                               "audit": "PASS", "metrics": measurement})

    _record_point_started(output_root, variant, rpm,
                          cycles_completed=first_cycle - 1,
                          next_cycle=first_cycle)
    for cycle in range(first_cycle, prereg["horizon"]["max_complete_cycles_per_point"] + 1):
        rejected: list[dict] = []
        cycle_started = time.monotonic()
        cycle_start_snapshot = engine.snapshot()
        detector_start_snapshot = detector.snapshot()
        try:
            _advance_to_bounded(engine, float(cycle * 360), rejected,
                                started + budget_seconds)
            end_snapshot = engine.snapshot()
            primary = make_integrated_cycle_primary(
                engine, start_snapshot, end_snapshot, cycle,
                rejected_trials=rejected,
                runner_sha256=_sha256(Path(__file__).read_bytes().replace(b"\r\n", b"\n")))
        except _CampaignDeadlineReached:
            # Roll back any partial cycle so resume starts from its last
            # complete, hash-bound state and detector history.
            engine.restore(cycle_start_snapshot)
            detector.restore(detector_start_snapshot)
            checkpoint = {
                "schema": "FULL_RPM_SWEEP_V1_IMPL2_POINT_CHECKPOINT",
                "implementation_version": IMPLEMENTATION_VERSION,
                "bindings": bindings,
                "next_cycle": cycle,
                "engine_snapshot": cycle_start_snapshot,
                "periodicity_snapshot": detector_start_snapshot,
            }
            _write_json_atomic(checkpoint_path, checkpoint)
            interrupted = {
                "schema": "FULL_RPM_SWEEP_V1_POINT_RESULT",
                "point_id": point_id,
                "variant_id": variant["variant_id"],
                "rpm": rpm,
                "classification": "INTERRUPTED_CHECKPOINTED",
                "cycles_completed": cycle - 1,
                "next_cycle": cycle,
                "engineering_outputs": None,
                "cycle_primaries": [row["primary_sha256"] for row in cycle_rows],
                "performance_metrics": _point_performance_metrics(cycle_metrics),
                "bindings": bindings,
            }
            _write_json_atomic(point_dir / "checkpoint-status.json", interrupted)
            return interrupted
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
                "cycle_primaries": [row["primary_sha256"] for row in cycle_rows],
                "performance_metrics": _point_performance_metrics(cycle_metrics),
                "bindings": bindings,
            }
            _write_json_atomic(result_path, failure)
            return failure
        audit = audit_integrated_cycle_primary(primary)
        scavenging_assessment = _r2_compatible_scavenging(primary)
        if (audit.get("recomputed") is not True or primary.get("admissible") is not True or
                scavenging_assessment["hard_gate"]["classification"] != "PASS"):
            failure = {
                "schema": "FULL_RPM_SWEEP_V1_POINT_RESULT",
                "point_id": point_id,
                "rpm": rpm,
                "classification": "PRIMARY_AUDIT_FAIL" if audit.get("recomputed") is not True
                                  else "PHYSICAL_INVALID",
                "audit": audit,
                "scavenging": scavenging_assessment,
                "conservation": primary.get("conservation"),
                "hard_gates": {
                    "primary_admissible": primary.get("admissible") is True,
                    "primary_replay_audit": audit.get("recomputed") is True,
                    "scavenging_partition": scavenging_assessment["hard_gate"],
                    "conservation": scavenging_assessment["species_closure"],
                },
                "cycles_completed": cycle,
                "engineering_outputs": None,
                "primary_sha256": _sha256(_canonical_bytes(primary)),
                "cycle_primaries": [row["primary_sha256"] for row in cycle_rows],
                "performance_metrics": _point_performance_metrics(cycle_metrics),
                "bindings": bindings,
            }
            _write_primary_gzip(point_dir / f"cycle-{cycle:03d}.json.gz", primary)
            _write_json_atomic(result_path, failure)
            return failure

        serialization_started = time.monotonic()
        primary_payload = _canonical_bytes(primary)
        primary_sha = _sha256(primary_payload)
        serialization_seconds = time.monotonic() - serialization_started
        primary_write_started = time.monotonic()
        primary_path = point_dir / f"cycle-{cycle:03d}.json.gz"
        _write_primary_gzip(primary_path, payload=primary_payload)
        primary_write_seconds = time.monotonic() - primary_write_started
        detector_started = time.monotonic()
        update = detector.update(_projection(primary))
        detector_seconds = time.monotonic() - detector_started
        measurement = {
            "cycle": cycle,
            "primary_sha256": primary_sha,
            "cycle_elapsed_s": time.monotonic() - cycle_started,
            "primary_serialization_seconds": serialization_seconds,
            "primary_write_seconds": primary_write_seconds,
            "primary_compressed_bytes": primary_path.stat().st_size,
            "detector_update_seconds": detector_seconds,
            "checkpoint_write_seconds": 0.0,
            "accepted_solver_steps": int(engine.accepted_steps),
            "rejected_solver_steps": len(rejected),
            "process_rss_bytes": _process_rss_bytes(),
            "detector_classification": detector.classification,
            "detector_update": update,
        }
        _write_cycle_metrics(point_dir, cycle, measurement)
        cycle_metrics.append(measurement)
        cycle_rows.append({"cycle": cycle, "primary_sha256": primary_sha,
                           "audit": "PASS", "detector": update,
                           "metrics": measurement})
        classification = detector.classification
        if classification in ("PERIOD_1", "PERIOD_2"):
            observables = primary["observables"]
            scavenging = scavenging_assessment
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
                "scavenging": scavenging,
                "conservation": primary["conservation"],
                "hard_gates": {
                    "primary_admissible": primary.get("admissible") is True,
                    "primary_replay_audit": audit.get("recomputed") is True,
                    "scavenging_partition": scavenging["hard_gate"],
                    "conservation": scavenging["species_closure"],
                },
                "warnings": primary.get("warnings", []),
                "performance_metrics": _point_performance_metrics(cycle_metrics),
                "bindings": bindings,
                "cycle_primaries": [row["primary_sha256"] for row in cycle_rows],
            }
            _write_json_atomic(result_path, terminal)
            return terminal

        # Keep the complete-cycle state but discard trajectory memory before
        # the next cycle. The exact physical state and ledgers are retained.
        engine.compact_cycle_trace()
        start_snapshot = engine.snapshot()
        checkpoint = {
            "schema": "FULL_RPM_SWEEP_V1_IMPL2_POINT_CHECKPOINT",
            "implementation_version": IMPLEMENTATION_VERSION,
            "bindings": bindings,
            "next_cycle": cycle + 1,
            "engine_snapshot": start_snapshot,
            "periodicity_snapshot": detector.snapshot(),
        }
        checkpoint_started = time.monotonic()
        _write_json_atomic(checkpoint_path, checkpoint)
        measurement["checkpoint_write_seconds"] = time.monotonic() - checkpoint_started
        _write_cycle_metrics(point_dir, cycle, measurement)
        in_progress = {
            "classification": "IN_PROGRESS_CHECKPOINTED",
            "cycles_completed": cycle,
            "next_cycle": cycle + 1,
            "performance_metrics": _point_performance_metrics(cycle_metrics),
        }
        _write_json_atomic(point_dir / "checkpoint-status.json", in_progress)
        _record_checkpoint_progress(output_root, variant, rpm, checkpoint_path,
                                    in_progress)
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
                "performance_metrics": _point_performance_metrics(cycle_metrics),
                "bindings": bindings,
            }
            # Do not create result.json: a later --resume must continue this point.
            _write_json_atomic(point_dir / "checkpoint-status.json", interrupted)
            _record_checkpoint_progress(output_root, variant, rpm, checkpoint_path,
                                        interrupted)
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
        "performance_metrics": _point_performance_metrics(cycle_metrics),
        "bindings": bindings,
        "cycle_primaries": [row["primary_sha256"] for row in cycle_rows],
    }
    _write_json_atomic(result_path, terminal)
    return terminal


def execute_campaign(*, output_root: str | Path, resume: bool = False,
                     pilot: bool = False,
                     budget_seconds: int = MAX_INVOCATION_SECONDS) -> dict:
    """Run the preregistered campaign, optionally in two-point pilot mode."""
    started = time.monotonic()
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
    prereg = _read_json(prereg_path)
    prereg_sha = canonical_sha256(prereg)
    output_manifest = out / "campaign.json"
    if output_manifest.exists() and not resume:
        raise FileExistsError("campaign output exists; pass --resume or choose a fresh external directory")
    campaign_id = f"{IMPLEMENTATION_VERSION}_{prereg_sha[:16]}"
    if output_manifest.exists():
        prior_manifest = _read_json(output_manifest)
        if (prior_manifest.get("campaign_id") != campaign_id or
                prior_manifest.get("pre-registration_sha256") != prereg_sha):
            raise ValueError("campaign resume manifest does not match preregistration")
    _ensure_campaign_provenance(out, prereg, prereg_sha)
    selected_points = _selected_points(prereg, pilot=pilot)

    invocation = {
        "id": f"{time.time_ns()}-{('PILOT' if pilot else 'FULL')}" ,
        "started_at_unix": time.time(),
        "phase": "PILOT" if pilot else "FULL_CAMPAIGN",
        "requested_points": [f"{variant['variant_id']}@{rpm}RPM"
                             for variant, rpm in selected_points],
        "results": [],
    }

    def save_summary(campaign_status: str) -> dict:
        catalog = []
        terminal = {"NO_CONVERGENCE_WITHIN_HORIZON", "NUMERICAL_INVALID",
                    "PRIMARY_AUDIT_FAIL", "PHYSICAL_INVALID", "PERIOD_1", "PERIOD_2"}
        for variant in prereg["variants"]:
            for rpm in rpm_points(prereg):
                point_dir = out / variant["variant_id"] / f"rpm-{rpm:05d}"
                result_file = point_dir / "result.json"
                checkpoint_file = point_dir / "checkpoint.json"
                checkpoint_status = point_dir / "checkpoint-status.json"
                result = _read_json(result_file) if result_file.is_file() else None
                checkpoint = _read_json(checkpoint_status) if checkpoint_status.is_file() else None
                classification = (result or checkpoint or {}).get("classification", "NOT_STARTED")
                row = {"point_id": f"{variant['variant_id']}@{rpm}RPM",
                       "variant_id": variant["variant_id"], "rpm": rpm,
                       "classification": classification,
                       "cycles_completed": (result or checkpoint or {}).get("cycles_completed"),
                       "next_cycle": (result or checkpoint or {}).get("next_cycle"),
                       "result_path": str(result_file.relative_to(out)) if result else None,
                       "checkpoint_path": str(checkpoint_file.relative_to(out))
                       if checkpoint_file.is_file() else None}
                if result or checkpoint:
                    point_record = result or checkpoint
                    row["performance_metrics"] = point_record.get("performance_metrics")
                if result:
                    row["result_sha256"] = _sha256(result_file.read_bytes())
                    row["failure_reason"] = result.get("failure_reason")
                    row["hard_gates"] = result.get("hard_gates")
                if checkpoint_file.is_file():
                    row["checkpoint_sha256"] = _sha256(checkpoint_file.read_bytes())
                catalog.append(row)
        unfinished = any(row["classification"] not in terminal for row in catalog)
        previous = _read_json(output_manifest) if output_manifest.is_file() else {}
        invocations = list(previous.get("invocations", []))
        invocation_row = {
            "id": invocation["id"],
            "phase": invocation["phase"],
            "started_at_unix": invocation["started_at_unix"],
            "duration_seconds": time.monotonic() - started,
            "requested_points": invocation["requested_points"],
            "results": invocation["results"],
        }
        invocations = [row for row in invocations if row.get("id") != invocation["id"]]
        if invocation["results"] or not invocations:
            invocations.append(invocation_row)
        pilot_done = (pilot and len(invocation["results"]) == 2 and
                      all(row["classification"] in terminal
                          for row in invocation["results"]))
        campaign_started = bool(previous.get("campaigns_started", 0) or
                                invocation["results"])
        if pilot_done:
            campaign_status = "PILOT_COMPLETE_PENDING_FULL_CAMPAIGN"
        elif unfinished and campaign_status != "INTERRUPTED_CHECKPOINTED":
            campaign_status = "PARTIAL_IN_PROGRESS"
        provenance_path = out / "provenance" / "manifest.json"
        summary = {
            "schema": "FULL_RPM_SWEEP_V1_CAMPAIGN_SUMMARY",
            "campaign_id": campaign_id,
            "pre-registration_sha256": prereg_sha,
            "preflight_status": "PASS",
            "campaigns_started": 1 if campaign_started else 0,
            "campaign_status": campaign_status,
            "campaign_scope": [f"{variant['variant_id']}@{rpm}RPM"
                               for variant in prereg["variants"] for rpm in rpm_points(prereg)],
            "completed_or_checkpointed_points": catalog,
            "invocations": invocations,
            "provenance_manifest": str(provenance_path.relative_to(out)),
            "provenance_manifest_sha256": _sha256(provenance_path.read_bytes()),
            "updated_solver_dependency_hashes": _solver_dependency_hashes(),
        }
        if pilot_done:
            pilot_metrics = [row.get("performance_metrics") or {}
                             for row in catalog
                             if row["rpm"] == 4000 and row["classification"] in terminal]
            measured_cycles = sum(int(row.get("measured_cycles", 0)) for row in pilot_metrics)
            total_cycle_time = sum(float(row.get("total_measured_cycle_seconds", 0))
                                   for row in pilot_metrics)
            total_bytes = sum(int(row.get("primary_compressed_bytes", 0))
                              for row in pilot_metrics)
            mean_cycles_per_point = (measured_cycles / 2) if measured_cycles else None
            mean_bytes_per_cycle = (total_bytes / measured_cycles) if measured_cycles else None
            mean_seconds_per_cycle = (total_cycle_time / measured_cycles) if measured_cycles else None
            summary["pilot_projection"] = {
                "basis": "A4000 and B4000 pilot measurements; rough linear estimate, not a guarantee",
                "pilot_cycles": measured_cycles,
                "mean_seconds_per_cycle": mean_seconds_per_cycle,
                "mean_primary_bytes_per_cycle": mean_bytes_per_cycle,
                "mean_cycles_per_pilot_point": mean_cycles_per_point,
                "estimated_total_campaign_seconds": (
                    mean_seconds_per_cycle * mean_cycles_per_point * 30
                    if None not in (mean_seconds_per_cycle, mean_cycles_per_point) else None),
                "estimated_primary_storage_bytes": (
                    mean_bytes_per_cycle * mean_cycles_per_point * 30
                    if None not in (mean_bytes_per_cycle, mean_cycles_per_point) else None),
                "artifact_root_free_bytes": shutil.disk_usage(out).free,
                "psutil_observations_available": importlib.util.find_spec("psutil") is not None,
            }
        _write_json_atomic(output_manifest, summary)
        return summary

    save_summary("PREPARED")
    for variant, rpm in selected_points:
        point_result = _run_point(
            prereg, prereg_sha, variant, rpm, out,
            resume=resume, started=started, budget_seconds=budget_seconds)
        point_dir = out / variant["variant_id"] / f"rpm-{rpm:05d}"
        invocation["results"].append({
            "point_id": point_result["point_id"],
            "classification": point_result["classification"],
            "result_path": str((point_dir / "result.json").relative_to(out))
            if (point_dir / "result.json").is_file() else None,
            "checkpoint_path": str((point_dir / "checkpoint.json").relative_to(out))
            if (point_dir / "checkpoint.json").is_file() else None,
        })
        summary = save_summary(
            "INTERRUPTED_CHECKPOINTED"
            if point_result["classification"] == "INTERRUPTED_CHECKPOINTED"
            else "IN_PROGRESS")
        if point_result["classification"] == "INTERRUPTED_CHECKPOINTED":
            return summary
    return save_summary("COMPLETE_WITH_POINT_CLASSIFICATIONS")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true",
                        help="start the campaign (requires durable readiness PASS)")
    parser.add_argument("--output-root", type=Path,
                        help="durable external artifact directory; must be outside the repo")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--pilot", action="store_true",
                        help="run only preregistered A4000 and B4000 as the first phase of this campaign")
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
        output_root = Path(artifact_root) / "engine-physics-v1/full-rpm-sweep-v1-impl2"
    if output_root.name != "full-rpm-sweep-v1-impl2":
        parser.error("IMPL2 requires a separate output root named full-rpm-sweep-v1-impl2")
    if output_root.resolve().is_relative_to(ROOT.resolve()):
        parser.error("campaign artifact output must remain outside the repository")
    result = execute_campaign(output_root=output_root, resume=args.resume,
                              pilot=args.pilot,
                              budget_seconds=args.budget_seconds)
    print(json.dumps({"campaign_status": result["campaign_status"],
                      "points": len(result["completed_or_checkpointed_points"]),
                      "campaigns_started": result["campaigns_started"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
