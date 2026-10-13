from __future__ import annotations

import gzip
import json

from scripts import full_rpm_sweep_v1_impl2_extension_supervisor_v3 as extension


def test_v2_incremental_manifest_sync_verifies_only_new_cycle_links(tmp_path, monkeypatch):
    variant = {"variant_id": "A_PRIME_MESH_0"}
    point_id = "A_PRIME_MESH_0@1000RPM"
    point_dir = tmp_path / variant["variant_id"] / "rpm-01000"
    metrics_dir = point_dir / "cycle-metrics"
    metrics_dir.mkdir(parents=True)
    for cycle in (3, 4):
        primary = {"cycle_index": cycle, "observables": {"value": cycle}}
        primary_bytes = extension.campaign._canonical_bytes(primary)
        path = point_dir / f"cycle-{cycle:03d}.json.gz"
        path.write_bytes(gzip.compress(primary_bytes))
        (metrics_dir / f"cycle-{cycle:03d}.json").write_text(json.dumps({
            "cycle": cycle,
            "primary_sha256": extension.campaign._sha256(primary_bytes),
        }), encoding="utf-8")
    checkpoint_path = point_dir / "checkpoint.json"
    checkpoint_path.write_text("{}", encoding="utf-8")
    (point_dir / "checkpoint-status.json").write_text(json.dumps({
        "classification": "IN_PROGRESS_CHECKPOINTED",
        "cycles_completed": 4,
        "next_cycle": 5,
    }), encoding="utf-8")

    monkeypatch.setattr(extension.campaign, "resolve_mechanical_loss_v1",
                        lambda **kwargs: object())
    monkeypatch.setattr(extension.campaign, "_point_contract_hashes",
                        lambda *args: {"expected": True})
    monkeypatch.setattr(extension.campaign, "_load_checkpoint",
                        lambda *args, **kwargs: {"next_cycle": 5})
    row = {"point_id": point_id, "classification": "IN_PROGRESS_CHECKPOINTED",
           "cycles_completed": 2, "checkpoint_sha256": "old"}
    manifest = {"completed_or_checkpointed_points": [row]}
    changed = extension._refresh_point_rows(
        tmp_path, manifest, {point_id: (variant, 1000)},
        {"rpm_grid": {"points_rpm": [1000]}}, "canonical-prereg")
    assert changed is True
    assert row["cycles_completed"] == 4
    assert row["checkpoint_sha256"] == extension._sha(checkpoint_path.read_bytes())


def test_v2_manifest_accepts_only_explicit_authorization_chain(tmp_path):
    point_ids = ["A_PRIME_MESH_0@1000RPM"]
    initial = extension._validate_extension_manifest(
        tmp_path, point_ids, "a" * 64, "b" * 64, "c" * 64,
        {"supersedes_authorization_sha256": None})
    assert initial["authorization_chain"] == ["b" * 64]
    resumed = extension._validate_extension_manifest(
        tmp_path, point_ids, "a" * 64, "b" * 64, "c" * 64,
        {"supersedes_authorization_sha256": None})
    assert resumed["authorization_chain"] == ["b" * 64]
    chained = extension._validate_extension_manifest(
        tmp_path, point_ids, "a" * 64, "d" * 64, "c" * 64,
        {"supersedes_authorization_sha256": "b" * 64})
    assert chained["authorization_chain"] == ["b" * 64, "d" * 64]
    resumed_chain = extension._validate_extension_manifest(
        tmp_path, point_ids, "a" * 64, "d" * 64, "c" * 64,
        {"supersedes_authorization_sha256": "b" * 64})
    assert resumed_chain["authorization_chain"] == ["b" * 64, "d" * 64]
    try:
        extension._validate_extension_manifest(
            tmp_path, point_ids, "a" * 64, "e" * 64, "c" * 64,
            {"supersedes_authorization_sha256": "x" * 64})
    except RuntimeError as exc:
        assert "authorization chain" in str(exc)
    else:
        raise AssertionError("unlinked authorization must fail closed")

