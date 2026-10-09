"""Verify a FULL_RPM_SWEEP_V1 campaign from its external bundle alone."""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from pathlib import Path
from typing import Any


def _canonical_sha(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"),
                         ensure_ascii=False, allow_nan=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _file_sha(path: Path, *, normalize_newlines: bool = False) -> str:
    payload = path.read_bytes()
    if normalize_newlines:
        payload = payload.replace(b"\r\n", b"\n")
    return hashlib.sha256(payload).hexdigest()


def _inside(root: Path, relative: str) -> Path:
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError(f"artifact path escapes campaign root: {relative}")
    return path


def _read_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def verify_campaign(campaign_root: str | Path) -> dict:
    root = Path(campaign_root).resolve()
    errors: list[str] = []
    manifest = _read_json(root / "campaign.json")
    bundle = _read_json(_inside(root, manifest["provenance_manifest"]))
    prereg = _read_json(_inside(root, "provenance/preregistration.json"))
    prereg_sha = _canonical_sha(prereg)
    if manifest.get("pre-registration_sha256") != prereg_sha:
        errors.append("PREREGISTRATION_HASH_MISMATCH")
    if bundle.get("preregistration_sha256") != prereg_sha:
        errors.append("BUNDLE_PREREGISTRATION_HASH_MISMATCH")
    if _file_sha(_inside(root, manifest["provenance_manifest"])) != manifest.get(
            "provenance_manifest_sha256"):
        errors.append("PROVENANCE_MANIFEST_HASH_MISMATCH")

    for relative, record in bundle.get("source_files", {}).items():
        source = _inside(root, record["artifact_path"])
        if not source.is_file() or _file_sha(source, normalize_newlines=True) != record["sha256"]:
            errors.append(f"BUNDLED_SOURCE_HASH_MISMATCH:{relative}")
    authorization_record = bundle.get("source_files", {}).get(
        "results/full-rpm-sweep-v1/campaign-authorization.json")
    if authorization_record is None:
        errors.append("CAMPAIGN_AUTHORIZATION_RECEIPT_MISSING")
    else:
        authorization_path = _inside(root, authorization_record["artifact_path"])
        authorization = _read_json(authorization_path)
        if (not authorization.get("authorized") or
                len(authorization.get("scope", {}).get("variants", [])) != 2 or
                authorization.get("scope", {}).get("maximum_points") != 30 or
                _file_sha(authorization_path) != bundle.get("authorization_sha256")):
            errors.append("CAMPAIGN_AUTHORIZATION_SCOPE_OR_HASH_INVALID")
    fixture_hashes = {item["source_fixture_path"]: item["fixture_sha256"]
                      for item in prereg["variants"]}
    for relative, expected in fixture_hashes.items():
        record = bundle.get("source_files", {}).get(relative)
        if record is None:
            errors.append(f"FIXTURE_MISSING_FROM_BUNDLE:{relative}")
        elif _file_sha(_inside(root, record["artifact_path"])) != expected:
            errors.append(f"FIXTURE_HASH_MISMATCH:{relative}")

    configurations = bundle.get("variant_configurations", {})
    for variant in prereg["variants"]:
        config_record = configurations.get(variant["variant_id"])
        if not config_record:
            errors.append(f"CONFIGURATION_MISSING:{variant['variant_id']}")
            continue
        config = _read_json(_inside(root, config_record["artifact_path"]))
        if _canonical_sha(config) != variant["engine_configuration_sha256"]:
            errors.append(f"CONFIGURATION_HASH_MISMATCH:{variant['variant_id']}")
        config_record["configuration"] = config

    expected_ids = {f"{variant['variant_id']}@{rpm}RPM"
                    for variant in prereg["variants"]
                    for rpm in prereg["rpm_grid"]["points_rpm"]}
    catalog = manifest.get("completed_or_checkpointed_points", [])
    actual_ids = {item.get("point_id") for item in catalog}
    if len(catalog) != 30 or actual_ids != expected_ids:
        errors.append("POINT_CATALOG_DOES_NOT_MATCH_30_POINT_PREREGISTRATION")

    checked_results = checked_checkpoints = checked_primaries = checked_metrics = 0
    for item in catalog:
        point_id = item["point_id"]
        variant = next(v for v in prereg["variants"]
                       if v["variant_id"] == item["variant_id"])
        config = configurations[item["variant_id"]]["configuration"]
        point_config = dict(config)
        point_config["reference_rpm"] = float(item["rpm"])
        expected_bindings = {
            "preregistration_sha256": prereg_sha,
            "fixture_sha256": variant["fixture_sha256"],
            "engine_configuration_sha256": variant["engine_configuration_sha256"],
            "point_configuration_sha256": _canonical_sha(point_config),
            "mechanical_loss_model_sha256": variant["mechanical_loss_model_sha256"],
            "fuel_sha256": variant["fuel"]["sha256"],
            "solver_dependency_hashes": prereg["solver_dependency_hashes"],
            "periodicity_contract": prereg["periodicity"]["contract"],
            "periodicity_source_sha256": prereg["periodicity_source_sha256"],
            "campaign_producer_sha256": bundle["campaign_runner_sha256"],
        }
        result = None
        if item.get("result_path"):
            result_path = _inside(root, item["result_path"])
            if _file_sha(result_path) != item.get("result_sha256"):
                errors.append(f"RESULT_HASH_MISMATCH:{point_id}")
                continue
            result = _read_json(result_path)
            bindings = result.get("bindings", {})
            if (bindings.get("preregistration_sha256") != prereg_sha or
                    bindings.get("fixture_sha256") != variant["fixture_sha256"] or
                    bindings.get("engine_configuration_sha256") != variant[
                        "engine_configuration_sha256"]):
                errors.append(f"RESULT_BINDING_MISMATCH:{point_id}")
            classification = result.get("classification")
            valid = classification in {"PERIOD_1", "PERIOD_2"}
            if valid != (result.get("engineering_outputs") is not None):
                errors.append(f"ENGINEERING_OUTPUT_CLASSIFICATION_MISMATCH:{point_id}")
            if not valid and result.get("engineering_outputs") is not None:
                errors.append(f"NONCONVERGED_POINT_HAS_ENGINEERING_OUTPUTS:{point_id}")
            checked_results += 1

        checkpoint = None
        if item.get("checkpoint_path"):
            checkpoint_path = _inside(root, item["checkpoint_path"])
            if _file_sha(checkpoint_path) != item.get("checkpoint_sha256"):
                errors.append(f"CHECKPOINT_HASH_MISMATCH:{point_id}")
            else:
                checkpoint = _read_json(checkpoint_path)
                checkpoint_bindings = checkpoint.get("bindings", {})
                for key, expected in expected_bindings.items():
                    if checkpoint_bindings.get(key) != expected:
                        errors.append(f"CHECKPOINT_BINDING_MISMATCH:{point_id}:{key}")
                adapter = bundle["source_files"].get("motorsim/full_rpm_outputs_v1.py", {})
                if checkpoint_bindings.get("output_adapter_sha256") != adapter.get("sha256"):
                    errors.append(f"CHECKPOINT_BINDING_MISMATCH:{point_id}:output_adapter_sha256")
                checked_checkpoints += 1

        if result is not None:
            primary_hashes = result.get("cycle_primaries", [])
            bindings = result.get("bindings", {})
            for key, expected in expected_bindings.items():
                if bindings.get(key) != expected:
                    errors.append(f"RESULT_BINDING_MISMATCH:{point_id}:{key}")
            adapter = bundle["source_files"].get("motorsim/full_rpm_outputs_v1.py", {})
            if bindings.get("output_adapter_sha256") != adapter.get("sha256"):
                errors.append(f"RESULT_BINDING_MISMATCH:{point_id}:output_adapter_sha256")
            for cycle, expected_hash in enumerate(primary_hashes, 1):
                primary_path = _inside(root, f"{item['variant_id']}/rpm-{item['rpm']:05d}/cycle-{cycle:03d}.json.gz")
                if not primary_path.is_file():
                    errors.append(f"PRIMARY_MISSING:{point_id}:cycle-{cycle}")
                    continue
                primary = json.loads(gzip.decompress(primary_path.read_bytes()))
                if _canonical_sha(primary) != expected_hash:
                    errors.append(f"PRIMARY_HASH_MISMATCH:{point_id}:cycle-{cycle}")
                checked_primaries += 1
                metrics_path = _inside(root, f"{item['variant_id']}/rpm-{item['rpm']:05d}/cycle-metrics/cycle-{cycle:03d}.json")
                if not metrics_path.is_file():
                    errors.append(f"CYCLE_METRICS_MISSING:{point_id}:cycle-{cycle}")
                    continue
                metrics = _read_json(metrics_path)
                if metrics.get("primary_sha256") != expected_hash:
                    errors.append(f"CYCLE_METRICS_PRIMARY_MISMATCH:{point_id}:cycle-{cycle}")
                checked_metrics += 1
            if result.get("primary_sha256") is not None:
                cycle = int(result.get("cycles_completed", 0))
                primary_path = _inside(root, f"{item['variant_id']}/rpm-{item['rpm']:05d}/cycle-{cycle:03d}.json.gz")
                if not primary_path.is_file():
                    errors.append(f"FAILED_CYCLE_PRIMARY_MISSING:{point_id}:cycle-{cycle}")
                else:
                    primary = json.loads(gzip.decompress(primary_path.read_bytes()))
                    if _canonical_sha(primary) != result["primary_sha256"]:
                        errors.append(f"FAILED_CYCLE_PRIMARY_HASH_MISMATCH:{point_id}:cycle-{cycle}")
                    checked_primaries += 1
        elif checkpoint is not None:
            completed = checkpoint["next_cycle"] - 1
            for cycle in range(1, completed + 1):
                primary_path = _inside(root, f"{item['variant_id']}/rpm-{item['rpm']:05d}/cycle-{cycle:03d}.json.gz")
                metrics_path = _inside(root, f"{item['variant_id']}/rpm-{item['rpm']:05d}/cycle-metrics/cycle-{cycle:03d}.json")
                if not primary_path.is_file() or not metrics_path.is_file():
                    errors.append(f"CHECKPOINT_CYCLE_EVIDENCE_MISSING:{point_id}:cycle-{cycle}")
                    continue
                primary = json.loads(gzip.decompress(primary_path.read_bytes()))
                expected_hash = _canonical_sha(primary)
                if _read_json(metrics_path).get("primary_sha256") != expected_hash:
                    errors.append(f"CHECKPOINT_METRICS_PRIMARY_MISMATCH:{point_id}:cycle-{cycle}")
                checked_primaries += 1
                checked_metrics += 1

    return {
        "schema": "FULL_RPM_SWEEP_V1_ARTIFACT_INTEGRITY_REPORT",
        "campaign_id": manifest.get("campaign_id"),
        "campaign_status": manifest.get("campaign_status"),
        "campaign_points": len(catalog),
        "results_checked": checked_results,
        "checkpoints_checked": checked_checkpoints,
        "primaries_checked": checked_primaries,
        "cycle_metrics_checked": checked_metrics,
        "errors": errors,
        "all_pass": not errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("campaign_root", type=Path)
    args = parser.parse_args()
    report = verify_campaign(args.campaign_root)
    print(json.dumps(report, sort_keys=True))
    return 0 if report["all_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
