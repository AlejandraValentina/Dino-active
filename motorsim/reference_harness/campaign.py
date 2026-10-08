"""Fixed-horizon reference campaigns with durable primary evidence."""
from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

from .checkpoint import checkpoint_payload, restore_checkpoint, replay_comparison
from .config import validate_config
from .convergence import PeriodicDetector, compare_cycles
from .evidence import (audit_cycles, canonical_bytes, configuration_hash,
                       audit_campaign_directory, manifest, read_json_gzip,
                       verify_source_binding, write_json_gzip)
from .runtime import advance_cycle, build_system


def _record_for_detector(record):
    return {key: record[key] for key in
            ("cycle_index", "configuration_hash", "contract", "observables")}


def run_point(config, output_dir, *, restart_probe=True):
    """Run one fixed preregistered operating point to closure or cycle cap."""
    parsed = validate_config(config)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    run_manifest = manifest(config)
    verify_source_binding(run_manifest["source_sha256"])
    write_json_gzip(output_dir / "manifest.json.gz", run_manifest)
    system, model, offset = build_system(config)
    detector = PeriodicDetector()
    cycles = []
    cycle_s = 1.0 / (float(config["operating_point"]["rpm"]) / 60.0)
    elapsed_s = 0.0
    first_replay = None
    restart_data = None
    failure = None
    for index in range(1, parsed["max_cycles"] + 1):
        try:
            record = advance_cycle(system, model, config, offset, index)
        except Exception as exc:
            failure = {"status": "NUMERICAL_FAILURE", "cycle_index": index,
                       "angle_deg": system.gas.angle, "accepted_steps": len(system.gas.history),
                       "exception_type": type(exc).__name__, "message": str(exc)}
            write_json_gzip(output_dir / "failure.json.gz", failure)
            break
        elapsed_s += cycle_s
        write_json_gzip(output_dir / f"cycle-{index:04d}.json.gz", record)
        cycles.append(record)
        update = detector.update(_record_for_detector(record))
        if index == 1:
            replay_system, replay_model, replay_offset = build_system(config)
            replay_record = advance_cycle(replay_system, replay_model, config,
                                          replay_offset, 1)
            first_replay = {"schema": "REFERENCE_ENGINE_REPLAY_PRIMARY_V1",
                            "passed": canonical_bytes(record) == canonical_bytes(replay_record),
                            "cycle_index": 1,
                            "terminal_state_equal": record["terminal_state"] == replay_record["terminal_state"],
                            "observables_equal": record["observables"] == replay_record["observables"],
                            "continuous_primary": record,
                            "replayed_primary": replay_record}
            write_json_gzip(output_dir / "initial-replay.json.gz", first_replay)
            if not first_replay["passed"]:
                failure = {"status": "DETERMINISTIC_REPLAY_MISMATCH", "cycle_index": 1}
                break
            checkpoint = checkpoint_payload(system, detector, config,
                                            cycle_index=index, elapsed_time_s=elapsed_s)
            write_json_gzip(output_dir / "checkpoint-cycle-0001.json.gz", checkpoint)
            restored_system, restored_model, restored_offset = build_system(config)
            restored_detector = PeriodicDetector()
            restart_info = restore_checkpoint(restored_system, restored_detector,
                                              checkpoint, config)
            restart_data = (restored_system, restored_model, restored_offset,
                            restored_detector, restart_info)
        if index == 2 and restart_probe and restart_data:
            restored_system, restored_model, restored_offset, restored_detector, restart_info = restart_data
            restarted = advance_cycle(restored_system, restored_model, config,
                                      restored_offset, index)
            restored_detector.update(_record_for_detector(restarted))
            restart_pass = canonical_bytes(record) == canonical_bytes(restarted)
            restart_report = {"passed": restart_pass,
                              "schema": "REFERENCE_ENGINE_RESTART_REPLAY_PRIMARY_V1",
                              "checkpoint_cycle": restart_info["cycle_index"],
                              "continued_cycle": index,
                              "state_equal": record["terminal_state"] == restarted["terminal_state"],
                              "observables_equal": record["observables"] == restarted["observables"],
                              "detector_state_equal": detector.snapshot() == restored_detector.snapshot(),
                              "continuous_primary": record,
                              "restarted_primary": restarted,
                              "continuous_detector": detector.snapshot(),
                              "restarted_detector": restored_detector.snapshot()}
            write_json_gzip(output_dir / "restart-replay.json.gz", restart_report)
            if not restart_pass:
                failure = {"status": "RESTART_REPLAY_MISMATCH", "cycle_index": index}
                break
            restart_data = None
        if index % config["evidence"]["checkpoint_cadence_cycles"] == 0:
            checkpoint = checkpoint_payload(system, detector, config,
                                            cycle_index=index, elapsed_time_s=elapsed_s)
            write_json_gzip(output_dir / f"checkpoint-cycle-{index:04d}.json.gz", checkpoint)
        if detector.classification is not None:
            break
    audit = audit_cycles(cycles, run_manifest["configuration_sha256"]) if cycles else {
        "classification": None, "converged_cycle": None,
        "detector_state": PeriodicDetector().snapshot(), "cycle_reports": []}
    if failure and failure["status"] not in ("NUMERICAL_FAILURE",):
        classification = failure["status"]
    elif failure:
        classification = "NUMERICAL_FAILURE"
    elif audit["classification"]:
        classification = audit["classification"]
    else:
        classification = "NO_CONVERGENCE_MAX_CYCLES"
    summary = {"schema": "REFERENCE_ENGINE_HYBRID_CAMPAIGN_SUMMARY_V1",
               "fixture_id": config.get("fixture_id"),
               "rpm": config["operating_point"]["rpm"],
               "classification": classification,
               "detected_period": audit["classification"],
               "converged_cycle": audit["converged_cycle"],
               "complete_cycles": len(cycles), "elapsed_simulated_time_s": elapsed_s,
               "initial_replay": first_replay, "failure": failure,
               "independent_audit": audit}
    write_json_gzip(output_dir / "summary.json.gz", summary)
    try:
        summary["offline_audit"] = audit_campaign_directory(output_dir)
    except Exception as exc:
        summary["offline_audit"] = {"evidence_audit": "FAIL",
                                    "exception_type": type(exc).__name__,
                                    "message": str(exc)}
        if not failure:
            summary["classification"] = "PRIMARY_AUDIT_FAILED"
    write_json_gzip(output_dir / "summary.json.gz", summary)
    return summary


def run_fixed_points(config, root, rpms=(5000, 7000, 9000, 11000, 13000)):
    """Run the five preregistered exploratory points sequentially."""
    results = []
    root = Path(root)
    for rpm in rpms:
        point = deepcopy(config)
        point["operating_point"]["rpm"] = rpm
        output_dir = root / f"rpm-{rpm}"
        summary_path = output_dir / "summary.json.gz"
        failure_path = output_dir / "failure.json.gz"
        if summary_path.exists():
            result = read_json_gzip(summary_path)
            result["offline_audit"] = audit_campaign_directory(output_dir)
            results.append(result)
            continue
        if failure_path.exists():
            run_manifest = read_json_gzip(output_dir / "manifest.json.gz")
            if run_manifest.get("configuration_sha256") != configuration_hash(point):
                raise ValueError(f"saved partial point {rpm} RPM has a different configuration")
            failure = read_json_gzip(failure_path)
            result = {"schema": "REFERENCE_ENGINE_HYBRID_CAMPAIGN_SUMMARY_V1",
                      "fixture_id": point.get("fixture_id"), "rpm": rpm,
                      "classification": failure.get("status"), "detected_period": None,
                      "converged_cycle": None, "complete_cycles": 0,
                      "elapsed_simulated_time_s": 0.0,
                      "initial_replay": None, "failure": failure,
                      "independent_audit": {"classification": None,
                                            "complete_cycles": 0,
                                            "cycle_reports": []}}
            write_json_gzip(summary_path, result)
            result["offline_audit"] = audit_campaign_directory(output_dir)
            write_json_gzip(summary_path, result)
            results.append(result)
            continue
        results.append(run_point(point, output_dir, restart_probe=True))
    return results
