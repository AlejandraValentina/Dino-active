"""Run one preregistered periodic mesh window from audited E2B A cycle 30."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from motorsim.integrated_2t import IntegratedEngine2T, _solver_dependency_hashes
from motorsim.reference_harness.convergence import PeriodicDetectorV2
from scripts.agents.storage_preflight import check_storage_requirements, default_artifact_root
from scripts.diagnostics.diagnose_integrated_mesh_v1 import sha
from scripts.diagnostics.periodicity_refined_mesh_pilot_v1 import run as run_window
from scripts.diagnostics.remap_representation_v1 import initialize


CONFIG_REL = Path("results/e2-spatial-waves-v1/preparation/A44.json")
E2B_MANIFEST_REL = Path("results/e2b-periodic-ab-v1/manifest.json")
E2B_INDEX_REL = Path("results/e2b-periodic-ab-v1/artifact-index.json")


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def validate_source(repo_root: Path, artifact_root: Path) -> dict:
    """Verify all inherited inputs before creating any campaign output."""
    repo_root = Path(repo_root)
    artifact_root = Path(artifact_root)
    manifest_path = repo_root / E2B_MANIFEST_REL
    index_path = repo_root / E2B_INDEX_REL
    manifest, index = _load(manifest_path), _load(index_path)
    config_path = repo_root / CONFIG_REL
    if sha(config_path) != manifest["configuration_sha256"]["A"]:
        raise ValueError("E2B A44 configuration hash differs")
    if manifest["solver_dependency_sha256"] != _solver_dependency_hashes():
        raise ValueError("E2B solver dependency hashes differ")
    if index.get("root_relative") != "e2b-periodic-ab-v1-20261028":
        raise ValueError("unexpected E2B artifact root identity")
    files = {row["path"]: row for row in index.get("files", [])}
    e2b_root = artifact_root / index["root_relative"]
    bound = {}
    for relative in ("A/checkpoint-030.json", "A/recipe-030.json", "A/audit-030.json"):
        path = e2b_root / relative
        expected = files.get(relative)
        if expected is None or not path.is_file() or sha(path) != expected["sha256"]:
            raise ValueError(f"E2B artifact integrity mismatch: {relative}")
        if path.stat().st_size != expected["bytes"]:
            raise ValueError(f"E2B artifact size mismatch: {relative}")
        bound[relative] = expected["sha256"]
    audit = _load(e2b_root / "A/audit-030.json")
    if audit.get("cycle") != 30 or audit.get("replay_exact") is not True:
        raise ValueError("E2B A30 primary audit is incomplete")
    if audit.get("periodicity_outcome", {}).get("outcomes", {}).get("lag1", {}).get("status") != "PASS":
        raise ValueError("E2B A30 periodic detector did not pass")
    config = _load(config_path)
    checkpoint = _load(e2b_root / "A/checkpoint-030.json")
    engine = IntegratedEngine2T.from_configuration_dict(config)
    engine.restore(checkpoint)
    if engine.crank_angle_unwrapped_deg != 10800.0 or engine.cycle != 30:
        raise ValueError("E2B native checkpoint is not cycle 30")
    return {"config_path": config_path, "checkpoint_path": e2b_root / "A/checkpoint-030.json",
            "manifest_sha256": sha(manifest_path), "artifact_index_sha256": sha(index_path),
            "configuration_sha256": sha(config_path), "source_artifacts": bound,
            "solver_dependency_sha256": manifest["solver_dependency_sha256"]}


def source_preparer(repo_root: Path, source: dict, level: int):
    config = _load(source["config_path"])
    checkpoint = _load(source["checkpoint_path"])
    engine, fine_config, remap = initialize(config, checkpoint, level, "P0",
                                             source["source_artifacts"]["A/checkpoint-030.json"])
    if engine.cycle != 30 or engine.crank_angle_unwrapped_deg != 10800.0:
        raise ValueError("conservative mesh initialization changed cycle origin")
    provenance = {
        "source_type": "E2B_A_AUDITED_PERIODIC_STATE",
        "source_configuration_sha256": source["configuration_sha256"],
        "source_checkpoint_sha256": source["source_artifacts"]["A/checkpoint-030.json"],
        "source_recipe_sha256": source["source_artifacts"]["A/recipe-030.json"],
        "source_primary_audit_sha256": source["source_artifacts"]["A/audit-030.json"],
        "source_manifest_sha256": source["manifest_sha256"],
        "source_artifact_index_sha256": source["artifact_index_sha256"],
        "solver_dependency_sha256": source["solver_dependency_sha256"],
        "initialization": remap,
        "origin_absolute_cycle": 30,
        "physical_origin_crank_deg": 10800.0,
        "first_detector_cycle_index": 1,
        "detector": "fresh PeriodicDetectorV2 history per grid",
    }
    return engine, fine_config, PeriodicDetectorV2(), provenance


def build_preflight(level: int, protocol_path: Path, *, repo_root: Path = ROOT,
                    artifact_root: Path | None = None) -> dict:
    """Bind one mesh initialization and storage check without solver steps."""
    if level not in (1, 2):
        raise ValueError("mesh level must be 1 (88 cells) or 2 (176 cells)")
    artifact_root = Path(artifact_root) if artifact_root else default_artifact_root()
    source = validate_source(repo_root, artifact_root)
    _, fine_config, _, provenance = source_preparer(repo_root, source, level)
    output_root = artifact_root / "predictive-reliability-v1" / "candidate-periodic-gci-v1"
    storage = check_storage_requirements([(output_root, 1024**3)])
    return {
        "schema": "DINO_CANDIDATE_PERIODIC_GCI_PREFLIGHT_V1",
        "mesh_level": level,
        "total_cells": 44 * (2 ** level),
        "protocol_sha256": sha(protocol_path),
        "runner_sha256": sha(Path(__file__)),
        "source": {key: value for key, value in source.items()
                   if key not in ("config_path", "checkpoint_path")},
        "remap": provenance["initialization"],
        "configuration_identity": fine_config.get("geometry_identity", {}).get(
            "diagnostic_initialization"),
        "storage_preflight": storage,
        "solver_steps_executed": 0,
        "campaign_execution_authorized_by_protocol": level == 1,
        "qualification": "Zero-step lineage/remap/storage preflight only. Window execution is limited to level 1 until its result is reviewed.",
    }


def run_first_window(level: int, output: Path, *, repo_root: Path = ROOT,
                     artifact_root: Path | None = None,
                     preflight_receipt: Path | None = None,
                     protocol_path: Path | None = None) -> int:
    if level not in (1, 2):
        raise ValueError("mesh level must be 1 (88 cells) or 2 (176 cells)")
    if preflight_receipt is None or protocol_path is None:
        raise ValueError("execution requires the committed zero-step preflight receipt and protocol")
    frozen = _load(preflight_receipt)
    if (frozen.get("schema") != "DINO_CANDIDATE_PERIODIC_GCI_PREFLIGHT_V1" or
            frozen.get("mesh_level") != level or frozen.get("solver_steps_executed") != 0 or
            frozen.get("protocol_sha256") != sha(protocol_path)):
        raise ValueError("preflight receipt does not bind this level/protocol")
    if level != 1 or not frozen.get("campaign_execution_authorized_by_protocol"):
        raise ValueError("only the preregistered 88-cell first window is admitted")
    artifact_root = Path(artifact_root) if artifact_root else default_artifact_root()
    source = validate_source(repo_root, artifact_root)
    preflight = check_storage_requirements([(output, 16 * 1024**2),
                                            (artifact_root, 1024**3)])
    prepare = lambda unused_root: source_preparer(repo_root, source, level)
    return run_window(artifact_root, output, source_preparer=prepare,
                      first_absolute=31, last_absolute=36,
                      solver_budget=260, admission_budget=290,
                      schema=f"CANDIDATE_PERIODIC_GCI_LEVEL{level}_WINDOW_V1")


def build_continuation_preregistration(source_output: Path, addendum_path: Path,
                                       *, repo_root: Path = ROOT,
                                       artifact_root: Path | None = None) -> dict:
    """Freeze exact cycle-36 source and trend-based admission for cycles 37-40."""
    source_output = Path(source_output)
    artifact_root = Path(artifact_root) if artifact_root else default_artifact_root()
    receipt = _load(source_output / "receipt.json")
    cycles = _load(source_output / "cycles.json")
    detector_state = _load(source_output / "detector.json")
    if (receipt.get("status") != "TRANSIENT_AT_BUDGET" or
            receipt.get("completed_new_cycles") != 6 or
            receipt.get("absolute_terminal_angle") != 12960.0 or
            len(cycles) != 6 or len(detector_state.get("history", [])) != 6):
        raise ValueError("continuation requires the complete frozen cycle-36 window")
    if receipt.get("source_solver_sha256") != _solver_dependency_hashes():
        raise ValueError("continuation source solver identity differs")
    trend = continuation_trend(cycles)
    source_files = ("configuration.json", "checkpoint-absolute-036.json",
                    "detector.json", "cycles.json", "receipt.json")
    hashes = {name: sha(source_output / name) for name in source_files}
    if _load(source_output / "checkpoint-absolute-036.json").get("cycle") != 36:
        raise ValueError("source checkpoint is not absolute cycle 36")
    preflight = check_storage_requirements([
        (artifact_root / "predictive-reliability-v1" / "candidate-periodic-gci-v1", 1024**3)])
    return {
        "schema": "DINO_CANDIDATE_PERIODIC_GCI_88_CONTINUATION_PREREG_V1",
        "protocol_addendum_sha256": sha(addendum_path),
        "source_window": "DINO_ARTIFACT_ROOT/predictive-reliability-v1/candidate-periodic-gci-v1/window-88-01",
        "source_files_sha256": hashes,
        "source_solver_dependency_sha256": receipt["source_solver_sha256"],
        "continuation_runner_sha256": sha(Path(__file__)),
        "source_detector_history_cycles": 6,
        "source_terminal_cycle": 36,
        "next_absolute_cycles": [37, 38, 39, 40],
        "trend_last_three": trend,
        "projected_solver_seconds": receipt["timing_seconds"]["solver"] / 6.0 * 4.0,
        "projected_with_20_percent_margin_seconds": receipt["timing_seconds"]["solver"] / 6.0 * 4.0 * 1.2,
        "solver_budget_seconds": 180.0,
        "admission_budget_seconds": 205.0,
        "cumulative_grid_solver_budget_seconds": 600.0,
        "storage_preflight": preflight,
        "solver_steps_executed": 0,
        "activation": "ONE_CONTINUATION_WINDOW_ONLY_REVIEW_AFTER_CYCLE_40",
    }


def continuation_trend(cycles: list[dict]) -> list[dict]:
    """Return the last-three statistics only when both registered tails fall."""
    if len(cycles) < 3:
        raise ValueError("three completed cycles are required for trend review")
    trend = [row.get("statistics") for row in cycles[-3:]]
    if any(not isinstance(row, dict) for row in trend):
        raise ValueError("last three detector statistics are incomplete")
    if not all(a["maximum"] > b["maximum"] and a["p90"] > b["p90"]
               for a, b in zip(trend, trend[1:])):
        raise ValueError("last three maximum/p90 trends do not strictly improve")
    return trend


def run_continuation(source_output: Path, preregistration_path: Path,
                     addendum_path: Path, output: Path, *,
                     repo_root: Path = ROOT,
                     artifact_root: Path | None = None) -> int:
    artifact_root = Path(artifact_root) if artifact_root else default_artifact_root()
    prereg = _load(preregistration_path)
    if (prereg.get("schema") != "DINO_CANDIDATE_PERIODIC_GCI_88_CONTINUATION_PREREG_V1" or
            prereg.get("protocol_addendum_sha256") != sha(addendum_path) or
            prereg.get("solver_steps_executed") != 0 or
            prereg.get("continuation_runner_sha256") != sha(Path(__file__)) or
            prereg.get("source_solver_dependency_sha256") != _solver_dependency_hashes()):
        raise ValueError("continuation preregistration/addendum binding mismatch")
    source_output = Path(source_output)
    for relative, expected in prereg["source_files_sha256"].items():
        if sha(source_output / relative) != expected:
            raise ValueError(f"continuation source changed: {relative}")

    def prepare(unused_root):
        config = _load(source_output / "configuration.json")
        checkpoint = _load(source_output / "checkpoint-absolute-036.json")
        detector_state = _load(source_output / "detector.json")
        engine = IntegratedEngine2T.from_configuration_dict(config)
        engine.restore(checkpoint)
        detector = PeriodicDetectorV2(detector_state)
        if engine.cycle != 36 or engine.crank_angle_unwrapped_deg != 12960.0:
            raise ValueError("restored continuation state is not cycle 36")
        return engine, config, detector, {
            "source_type": "EXACT_NATIVE_CHECKPOINT_AND_DETECTOR_CONTINUATION",
            "source_window_hashes": prereg["source_files_sha256"],
            "origin_absolute_cycle": 30,
            "physical_origin_crank_deg": 10800.0,
            "first_detector_cycle_index": 7,
            "detector_history_restored_exactly": True,
        }

    check_storage_requirements([(Path(output), 16 * 1024**2),
                                (artifact_root, 1024**3)])
    return run_window(artifact_root, Path(output), source_preparer=prepare,
                      first_absolute=37, last_absolute=40,
                      solver_budget=180, admission_budget=205,
                      schema="CANDIDATE_PERIODIC_GCI_LEVEL1_WINDOW2_V1")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--level", type=int, choices=(1, 2), required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--artifact-root", type=Path)
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument("--protocol", type=Path)
    parser.add_argument("--preflight-receipt", type=Path)
    parser.add_argument("--continue-from", type=Path)
    parser.add_argument("--protocol-addendum", type=Path)
    args = parser.parse_args()
    if args.preflight_only:
        if args.continue_from:
            if args.protocol_addendum is None or args.output.exists():
                raise ValueError("continuation preflight requires an addendum, new output, and source")
            result = build_continuation_preregistration(
                args.continue_from, args.protocol_addendum,
                artifact_root=args.artifact_root)
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
            print(json.dumps({"preflight": "PASS", "cycles": result["next_absolute_cycles"],
                              "solver_steps": 0}))
            return
        if args.protocol is None or args.output.exists():
            raise ValueError("preflight requires --protocol and a new --output path")
        result = build_preflight(args.level, args.protocol,
                                 artifact_root=args.artifact_root)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"preflight": "PASS", "level": args.level,
                          "cells": result["total_cells"], "solver_steps": 0}))
        return
    if args.continue_from:
        if args.protocol_addendum is None or args.preflight_receipt is None:
            raise ValueError("continuation execution requires its preflight and addendum")
        raise SystemExit(run_continuation(
            args.continue_from, args.preflight_receipt, args.protocol_addendum,
            args.output, artifact_root=args.artifact_root))
    raise SystemExit(run_first_window(args.level, args.output, artifact_root=args.artifact_root,
                                     preflight_receipt=args.preflight_receipt,
                                     protocol_path=args.protocol))


if __name__ == "__main__":
    main()
