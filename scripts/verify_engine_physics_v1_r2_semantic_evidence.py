"""Verify persisted R2 corrected outputs against external inputs and fixtures."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from motorsim.artifact_store import resolve_external_artifact


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_sha(value) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def verify() -> dict:
    artifact_manifest = json.loads((ROOT / "artifacts/engine-physics-v1-r2.json").read_text(encoding="utf-8"))
    manifest = json.loads((ROOT / "results/engine-physics-v1/r2-semantic-correction/manifest.json").read_text(encoding="utf-8"))
    old_r2 = json.loads((ROOT / "results/engine-physics-v1/r2-offline/manifest.json").read_text(encoding="utf-8"))
    first_review = json.loads((ROOT / "results/engine-physics-v1/r2-external-review/first-review.json").read_text(encoding="utf-8"))
    artifacts = {item["artifact_id"]: item for item in artifact_manifest["artifacts"]}
    old_points = {item["point_id"]: item for item in old_r2["points"]}
    records = []
    for point in manifest["points"]:
        artifact = artifacts[point["primary"]["artifact_id"]]
        primary_path = resolve_external_artifact(artifact["artifact_id"])
        primary = json.loads(__import__("gzip").open(primary_path, "rt", encoding="utf-8").read())
        fixture_path = (ROOT / "results/2t-commercial-core-20261002/fixtures/v1-prime-mesh" /
                        ("fixture_a_prime-mesh-0.json" if point["point_id"].startswith("A") else
                         "fixture_b_prime-mesh-0.json"))
        fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
        model = fixture["mechanical_loss_model"]
        outputs = point["outputs"]
        expected_fmep = sum(term["mep_pa"] for term in model["terms"])
        obs = primary["observables"]
        combustion = obs["fuel_coupled_combustion"]
        checks = {
            "primary_hash": sha(primary_path) == artifact["sha256"] == point["primary"]["sha256"],
            "primary_size": primary_path.stat().st_size == artifact["byte_size"] == point["primary"]["byte_size"],
            "fixture_config_hash": canonical_sha(fixture["engine_configuration"]) == fixture["engine_configuration_sha256"],
            "fixture_file_hash": sha(fixture_path) == point["fixture_mechanical_loss_provenance"]["fixture_file_sha256"],
            "fixture_model_hash": canonical_sha(model) == point["fixture_mechanical_loss_provenance"]["mechanical_loss_model_sha256"],
            "fmep_from_fixture": outputs["FMEP"]["value"] == expected_fmep,
            "afr_from_same_boundary_ledgers": abs(outputs["AFR"]["value"] - obs["fresh_air_intake_delivery_kg"] / obs["fuel_delivered_kg"]) < 1e-12,
            "fuel_closure": abs(outputs["fuel_burned"]["value"] + outputs["fuel_unburned"]["value"] - outputs["fuel_available"]["value"]) <= 1e-12,
            "undefined_scavenging_semantics": all(outputs[name]["status"] == "UNDEFINED" and outputs[name]["reason"] == "CURRENT_CYCLE_FRESH_RETENTION_NOT_IDENTIFIABLE" for name in ("TE", "CE", "SE")),
            "independent_partition": point["independent_partition_conservation"]["passed"],
            "hard_gate": point["hard_physical_gate"]["classification"] == "PASS",
            "old_new_comparison_uses_persisted_r2": (
                manifest["comparison"][point["point_id"]]["FMEP"]["old"] ==
                old_points[point["point_id"]]["outputs"]["FMEP"]["value"] and
                manifest["comparison"][point["point_id"]]["FMEP"]["new"] ==
                outputs["FMEP"]["value"] and
                manifest["comparison"][point["point_id"]]["AFR"]["old"] ==
                old_points[point["point_id"]]["outputs"]["AFR"]["value"]),
        }
        records.append({"point_id": point["point_id"], "artifact_id": artifact["artifact_id"],
                        "checks": checks, "all_pass": all(checks.values())})
    tracked = subprocess.run(["git", "ls-files"], cwd=ROOT, check=True,
                             capture_output=True, text=True).stdout.splitlines()
    primary_paths_tracked = [path for path in tracked
                             if path.endswith(("cycle-073.json.gz", "cycle-088.json.gz",
                                               "cycle-034.json.gz", "cycle-038.json.gz")) and
                             "engine-physics-v1" in path]
    b4000 = artifacts["R2_B4000"]
    overall = {
        "schema": "ENGINE_PHYSICS_V1_R2_SEMANTIC_EVIDENCE_AUDIT_V1",
        "semantic_correction_result": manifest["semantic_correction_result"],
        "administrative_gate": manifest["status"],
        "campaigns_started": manifest["campaigns_started"],
        "first_review_preserved": first_review["review_id"] == "EP_R2_EXTERNAL_REVIEW_FAIL" and first_review["result"] == "FAIL",
        "b4000_historical_git_status": b4000.get("historical_git_status"),
        "b4000_false_commit_attribution_removed": "relevant_historical_commit" not in b4000,
        "primary_paths_tracked": primary_paths_tracked,
        "all_points_pass": all(item["all_pass"] for item in records),
        "comparison_baseline": "persisted pre-correction R2 offline manifest",
    }
    overall["all_pass"] = (overall["semantic_correction_result"] ==
                            "ENGINE_PHYSICS_V1_R2_SEMANTIC_CORRECTION_READY_FOR_REVIEW" and
                            overall["administrative_gate"] == "REVIEW" and
                            overall["campaigns_started"] == 0 and
                            overall["first_review_preserved"] and
                            overall["b4000_historical_git_status"] == "UNTRACKED_AT_CAPTURE" and
                            overall["b4000_false_commit_attribution_removed"] and
                            not primary_paths_tracked and overall["all_points_pass"])
    result = {**overall, "points": records}
    target = ROOT / "results/engine-physics-v1/r2-semantic-correction/provenance-audit.json"
    target.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    result = verify()
    print(json.dumps({"all_pass": result["all_pass"], "points": len(result["points"]),
                      "semantic_correction_result": result["semantic_correction_result"]},
                     sort_keys=True))
    raise SystemExit(0 if result["all_pass"] else 1)
