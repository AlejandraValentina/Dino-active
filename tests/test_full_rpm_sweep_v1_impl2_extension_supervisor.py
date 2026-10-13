from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts import full_rpm_sweep_v1_impl2_extension_supervisor_v1 as extension


def test_extension_selects_exact_remaining_26_points():
    prereg, _, _ = extension._expected_identity()
    points = extension._extension_points(prereg)
    ids = {extension._point_id(variant, rpm) for variant, rpm in points}
    assert len(ids) == 26
    assert not ids.intersection(extension.PILOT_POINT_IDS)
    assert len(ids | extension.PILOT_POINT_IDS) == 30


def test_user_authorization_scope_is_exact_and_hash_bound(tmp_path):
    prereg, prereg_sha, identity = extension._expected_identity()
    ids = sorted(extension._point_id(v, rpm) for v, rpm in extension._extension_points(prereg))
    auth = {
        "schema": "FULL_RPM_SWEEP_V1_IMPL2_APPEND_ONLY_EXTENSION_AUTHORIZATION_V3",
        "authorization_type": "EXPLICIT_REMAINING_26_POINT_EXTENSION",
        "authorized": True,
        "implementation_version": extension.campaign.IMPLEMENTATION_VERSION,
        "preregistration_sha256": prereg_sha,
        "implementation_identity_sha256": extension._file_sha(
            extension.ROOT / "results/full-rpm-sweep-v1/implementation-v2-campaign-identity.json"),
        "campaign_runner_sha256": extension._file_sha(
            extension.ROOT / identity["source_paths"]["runner"]),
        "execution_supervisor_sha256": extension._file_sha(Path(extension.__file__)),
        "scope": {"point_ids": ids, "maximum_points": 26,
                  "global_budget_seconds": 21600,
                  "maximum_invocation_seconds": 3600,
                  "maximum_workers": 4, "memory_budget_mib": 4096,
                  "worker_reservation_mib": 512},
        "exclusions": ["the four completed pilot points and their artifacts",
                       "all v1 points and artifacts",
                       "any point outside the remaining 26 preregistered IMPL2 points",
                       "new configurations, models, solver/physics changes, and FAST_RECIPE_V1"],
    }
    auth_path = tmp_path / "authorization.json"
    auth_path.write_text(json.dumps(auth), encoding="utf-8")
    assert extension._validate_authorization(auth_path, prereg_sha, identity, ids) == auth
    auth["scope"]["point_ids"].append("A_PRIME_MESH_0@3100RPM")
    auth_path.write_text(json.dumps(auth), encoding="utf-8")
    with pytest.raises(RuntimeError, match="scope"):
        extension._validate_authorization(auth_path, prereg_sha, identity, ids)


def test_extension_manifest_rejects_cross_identity_and_wrong_scope(tmp_path, monkeypatch):
    point_ids = ["A_PRIME_MESH_0@1000RPM"]
    manifest = extension._validate_extension_manifest(
        tmp_path, point_ids, "a" * 64, "b" * 64, "c" * 64)
    assert manifest["campaigns_started"] == 0
    assert manifest["fast_recipe_enabled"] is False
    assert manifest["scope"] == point_ids
    assert len(manifest["completed_or_checkpointed_points"]) == 1

    manifest["implementation_identity_sha256"] = "d" * 64
    (tmp_path / "campaign.json").write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(RuntimeError, match="identity"):
        extension._validate_extension_manifest(
            tmp_path, point_ids, "a" * 64, "b" * 64, "c" * 64)


def test_invocation_ledger_is_append_only_and_capped(tmp_path):
    auth_sha = "a" * 64
    invocation_id, started_path, max_seconds = extension._create_invocation_start(
        tmp_path, auth_sha, 3600)
    assert started_path.is_file()
    assert max_seconds == 3600
    started_bytes = started_path.read_bytes()
    extension._finish_invocation(tmp_path, invocation_id, __import__("time").monotonic(),
                                 {"campaign_status": "PARTIAL_IN_PROGRESS"})
    assert started_path.read_bytes() == started_bytes
    consumed, rows = extension._budget_records(tmp_path)
    assert consumed >= 0
    assert rows[0]["status"] == "COMPLETED"


def test_invocation_ledger_never_grants_more_than_global_budget(tmp_path):
    for index in range(6):
        ledger = tmp_path / f"invocation-old-{index}-STARTED.json"
        ledger.write_text(json.dumps({"invocation_id": f"old-{index}",
                                      "started_at_unix": 1,
                                      "pid": 99999999}), encoding="utf-8")
    consumed, rows = extension._budget_records(tmp_path)
    assert consumed == extension.GLOBAL_BUDGET_SECONDS
    with pytest.raises(RuntimeError, match="exhausted"):
        extension._create_invocation_start(tmp_path, "a" * 64, 3600)


def test_pilot_roots_are_validated_as_distinct_read_only_bundle():
    prereg, prereg_sha, identity = extension._expected_identity()
    manifest = extension._validate_pilot_artifacts(prereg, prereg_sha, identity)
    assert manifest["campaign_status"] == "PARTIAL_IN_PROGRESS"
    rows = {row["point_id"]: row for row in manifest["completed_or_checkpointed_points"]}
    assert set(rows) >= extension.PILOT_POINT_IDS
    assert all(rows[point_id]["classification"] == "PERIOD_1"
               for point_id in extension.PILOT_POINT_IDS)

