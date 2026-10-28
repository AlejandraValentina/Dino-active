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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--level", type=int, choices=(1, 2), required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--artifact-root", type=Path)
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument("--protocol", type=Path)
    parser.add_argument("--preflight-receipt", type=Path)
    args = parser.parse_args()
    if args.preflight_only:
        if args.protocol is None or args.output.exists():
            raise ValueError("preflight requires --protocol and a new --output path")
        result = build_preflight(args.level, args.protocol,
                                 artifact_root=args.artifact_root)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"preflight": "PASS", "level": args.level,
                          "cells": result["total_cells"], "solver_steps": 0}))
        return
    raise SystemExit(run_first_window(args.level, args.output, artifact_root=args.artifact_root,
                                     preflight_receipt=args.preflight_receipt,
                                     protocol_path=args.protocol))


if __name__ == "__main__":
    main()
