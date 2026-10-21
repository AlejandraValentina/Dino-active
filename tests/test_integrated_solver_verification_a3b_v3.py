from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "diagnostics"))

import integrated_solver_verification_a3b_v3 as a3b


_BUILT: dict[str, dict] = {}


def _built(config_id: str) -> dict:
    if config_id not in _BUILT:
        _BUILT[config_id] = a3b._build_configuration(config_id)
    return _BUILT[config_id]


def _binding() -> dict:
    return a3b._binding(_built("T1-A"))


def _write_parent_fixture(tmp_path: Path, binding: dict) -> dict:
    records = [
        {"cycle": 1, "primary_sha256": "a" * 64, "observables": {}},
        {"cycle": 2, "primary_sha256": "b" * 64, "observables": {}},
    ]
    parent_binding = dict(binding)
    parent_binding["protocol_sha256"] = a3b.PARENT_PROTOCOL_SHA256
    parent_binding["driver_sha256"] = a3b.PARENT_DRIVER_SHA256
    checkpoint = {
        "schema": "DINO_ISV1_A3B_CHECKPOINT_V1",
        "bindings": parent_binding,
        "next_cycle": 3,
        "records": records,
        "engine_snapshot": {"synthetic": True},
        "periodicity_snapshot": {"synthetic": True},
    }
    result = {
        "schema": "DINO_ISV1_A3B_CONFIG_RESULT_V1",
        "config_id": "T1-A",
        "status": "PARTIAL_BUDGET",
        "cycles_completed": 2,
        "records": records,
    }
    ledger = {
        "schema": "DINO_ISV1_A3B_BUDGET_LEDGER_V1",
        "protocol_sha256": a3b.PARENT_PROTOCOL_SHA256,
        "entries": [
            {
                "invocation_id": "T1-A-inv01-e14f03d8a1",
                "config_id": "T1-A",
                "invocation_index": 1,
                "elapsed_seconds": 112.094,
                "reserved_seconds": 0.0,
                "cycles_completed": 0,
                "cycle_indices": [],
                "checkpoint_next_cycle": 1,
                "status": "FAILED_CLOSED",
                "failure": "PRIMARY_CONFIGURATION_HASH_MISMATCH",
            },
            {
                "invocation_id": "T1-A-inv01-a3ebb12d64",
                "config_id": "T1-A",
                "invocation_index": 1,
                "elapsed_seconds": 266.469,
                "reserved_seconds": 0.0,
                "cycles_completed": 2,
                "cycle_indices": [1, 2],
                "checkpoint_next_cycle": 3,
                "status": "PARTIAL_BUDGET",
                "failure": "T1-A cap exceeded",
            },
        ],
    }
    a3b._write_json(tmp_path / "T1-A" / "checkpoint.json", checkpoint)
    a3b._write_json(tmp_path / "T1-A" / "result.json", result)
    a3b._write_json(tmp_path / "a3b-budget-ledger.json", ledger)
    return {
        "checkpoint": checkpoint,
        "result": result,
        "ledger": ledger,
        "parent_binding": parent_binding,
    }


def _patch_parent_hashes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
                         fixture: dict) -> None:
    monkeypatch.setattr(
        a3b, "PARENT_CHECKPOINT_SHA256",
        a3b._file_sha_raw(tmp_path / "T1-A" / "checkpoint.json"))
    monkeypatch.setattr(
        a3b, "PARENT_RESULT_SHA256",
        a3b._file_sha_raw(tmp_path / "T1-A" / "result.json"))
    monkeypatch.setattr(
        a3b, "PARENT_LEDGER_SHA256",
        a3b._file_sha_raw(tmp_path / "a3b-budget-ledger.json"))
    monkeypatch.setattr(
        a3b, "PARENT_BINDING_SHA256",
        a3b._canonical_binding_sha256(fixture["parent_binding"]))
    monkeypatch.setattr(a3b, "PARENT_CYCLE_PRIMARY_SHA256", ("a" * 64, "b" * 64))


def test_v3_protocol_freeze_and_budget() -> None:
    protocol = a3b._load_protocol()
    assert protocol["status"] == "FROZEN_PROTOCOL_EXECUTION_NOT_AUTHORIZED"
    assert protocol["owner_scope_confirmation"]["selected_t1a_cumulative_cap_seconds"] == 600
    assert protocol["owner_scope_confirmation"]["execution_authorization"] == "NOT_GRANTED"
    caps = protocol["budget"]["per_configuration_caps_seconds"]
    assert caps["T1-A"] == 600
    assert sum(caps.values()) == 4270
    assert protocol["budget"]["hard_cap_seconds"] - sum(caps.values()) == 50
    t1a = next(row for row in protocol["budget"]["invocation_plan"]
               if row["id"] == "T1-A")
    assert t1a["start_cycle"] == 3
    assert t1a["cycles_per_invocation"] == [1]
    assert t1a["continuation"] is True
    assert a3b._canonical_binding_sha256(
        protocol["parent_lineage"]["parent_binding"]) == a3b.PARENT_BINDING_SHA256


def test_v3_scientific_binding_equality() -> None:
    protocol = a3b._load_protocol()
    parent = protocol["parent_lineage"]["parent_binding"]
    binding = _binding()
    assert a3b._scientific_binding_diff(parent, binding) == []
    assert parent["protocol_sha256"] != binding["protocol_sha256"]
    assert parent["driver_sha256"] != binding["driver_sha256"]
    changed = dict(parent)
    changed["solver_configuration_sha256"] = "0" * 64
    assert a3b._scientific_binding_diff(changed, binding) == [
        "solver_configuration_sha256"]


def test_v3_binding_preserves_parent_scientific_hashes() -> None:
    protocol = a3b._load_protocol()
    parent = protocol["parent_lineage"]["parent_binding"]
    binding = _binding()
    for key in ("config_id", "configuration_sha256", "solver_configuration_sha256",
                "identity_sha256", "project_sha256", "fuel_id",
                "mechanical_loss_model_sha256", "periodicity_contract",
                "periodicity_source_sha256", "periodicity_thresholds_sha256",
                "cycle_primary_contract", "exploratory_workflow_source_sha256",
                "solver_source_hashes"):
        assert binding[key] == parent[key]


def test_v3_run_scope_is_t1a_cycle3_only() -> None:
    a3b._validate_run_scope("T1-A", 2)
    with pytest.raises(a3b.Refused):
        a3b._validate_run_scope("T1-B", 2)
    with pytest.raises(a3b.Refused):
        a3b._validate_run_scope("T1-A", 1)
    with pytest.raises(a3b.Refused):
        a3b._validate_run_scope("T1-A", 3)


def test_v3_ledger_carries_forward_parent_charges(tmp_path: Path) -> None:
    binding = _binding()
    fixture = _write_parent_fixture(tmp_path, binding)
    # The ledger bootstrap does not need the checkpoint/result hashes.
    a3b._write_json(tmp_path / "T1-A" / "checkpoint.json", fixture["checkpoint"])
    a3b._write_json(tmp_path / "T1-A" / "result.json", fixture["result"])

    # Patch only the ledger hash; _load_ledger validates it.
    old = a3b.PARENT_LEDGER_SHA256
    a3b.PARENT_LEDGER_SHA256 = a3b._file_sha_raw(
        tmp_path / "a3b-budget-ledger.json")
    try:
        ledger = a3b._load_ledger(tmp_path)
    finally:
        a3b.PARENT_LEDGER_SHA256 = old
    assert abs(a3b._ledger_spent(ledger) - 378.563) < 1e-6
    assert abs(a3b._ledger_config_spent(ledger, "T1-A") - 378.563) < 1e-6
    assert [row["lineage"] for row in ledger["entries"]] == [
        "V2_CARRY_FORWARD", "V2_CARRY_FORWARD"]

    entry = {"config_id": "T1-A", "elapsed_seconds": 0.0,
             "reserved_seconds": 0.0}
    ledger["entries"].append(entry)
    reserve = a3b._reserve_next_cycle(ledger, entry, "T1-A", 0.0)
    assert reserve == pytest.approx(164.005)
    projected = a3b._ledger_config_spent(ledger, "T1-A")
    assert projected == pytest.approx(542.568)
    assert projected <= a3b.CONFIG_SPECS["T1-A"]["cap_seconds"]

    # A carried charge cannot be silently reduced or reclassified.
    tampered = json.loads(json.dumps(ledger))
    tampered["entries"][0]["elapsed_seconds"] = 0.0
    old = a3b.PARENT_LEDGER_SHA256
    a3b.PARENT_LEDGER_SHA256 = a3b._file_sha_raw(
        tmp_path / "a3b-budget-ledger.json")
    try:
        with pytest.raises(a3b.Refused):
            a3b._validate_carry_forward(tmp_path, tampered)
    finally:
        a3b.PARENT_LEDGER_SHA256 = old


def test_v3_checkpoint_bootstrap_preserves_parent(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    binding = _binding()
    fixture = _write_parent_fixture(tmp_path, binding)
    _patch_parent_hashes(tmp_path, monkeypatch, fixture)
    before = {
        name: a3b._file_sha_raw(tmp_path / "T1-A" / name)
        for name in ("checkpoint.json", "result.json")
    }
    checkpoint = a3b._bootstrap_v3_checkpoint(tmp_path, binding)
    assert checkpoint["next_cycle"] == 3
    assert [row["origin"] for row in checkpoint["records"]] == [
        "V2_CARRY_FORWARD", "V2_CARRY_FORWARD"]
    assert checkpoint["lineage"]["parent_binding_sha256"] == a3b.PARENT_BINDING_SHA256
    assert before["checkpoint.json"] == a3b._file_sha_raw(
        tmp_path / "T1-A" / "checkpoint.json")
    assert before["result.json"] == a3b._file_sha_raw(
        tmp_path / "T1-A" / "result.json")

    path = tmp_path / "T1-A" / "v3" / "checkpoint.json"
    loaded = a3b._load_checkpoint(path, binding)
    assert loaded is not None
    changed = dict(binding)
    changed["solver_configuration_sha256"] = "0" * 64
    with pytest.raises(a3b.Refused):
        a3b._load_checkpoint(path, changed)

    tampered = json.loads(json.dumps(checkpoint))
    tampered["records"][0]["origin"] = "V3"
    a3b._write_json(path, tampered)
    with pytest.raises(a3b.Refused):
        a3b._load_checkpoint(path, binding)


def test_v3_authorization_binds_caps_and_lineage(tmp_path: Path) -> None:
    driver = a3b._file_sha(Path(a3b.__file__))
    payload = {
        "protocol_sha256": a3b.PROTOCOL_SHA256,
        "parent_protocol_sha256": a3b.PARENT_PROTOCOL_SHA256,
        "driver_sha256": driver,
        "owner_confirmation": "synthetic v3 authorization",
        "execution_authorized": True,
        "global_cap_seconds": a3b.GLOBAL_CAP_SECONDS,
        "t1a_cumulative_cap_seconds": 600,
        "per_invocation_cap_seconds": a3b.PER_INVOCATION_CAP_SECONDS,
        "parent_checkpoint_sha256": a3b.PARENT_CHECKPOINT_SHA256,
        "parent_result_sha256": a3b.PARENT_RESULT_SHA256,
        "parent_ledger_sha256": a3b.PARENT_LEDGER_SHA256,
        "parent_binding_sha256": a3b.PARENT_BINDING_SHA256,
        "config_id": "T1-A",
        "invocation_index": 2,
    }
    path = tmp_path / "authorization.json"
    a3b._write_json(path, payload)
    assert a3b._load_authorization(path)["execution_authorized"] is True

    for key, value in (
        ("execution_authorized", False),
        ("t1a_cumulative_cap_seconds", 601),
        ("parent_checkpoint_sha256", "0" * 64),
        ("driver_sha256", "0" * 64),
    ):
        a3b._write_json(path, {**payload, key: value})
        with pytest.raises(a3b.Refused):
            a3b._load_authorization(path)


def test_v3_addendum_binds_protocol_driver_and_lineage(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(a3b, "ADDENDUM", tmp_path / "addendum.json")
    driver = a3b._file_sha(Path(a3b.__file__))
    preflight = {
        "schema": a3b.PREFLIGHT_SCHEMA,
        "status": "PASS",
        "protocol": {"sha256": a3b.PROTOCOL_SHA256},
        "driver_sha256_lf": driver,
        "configs": [
            {"config_id": config_id,
             "total_finite_volume_cells": a3b.CONFIG_SPECS[config_id]["cells"],
             "max_cfl": a3b.CONFIG_SPECS[config_id]["max_cfl"],
             "solver_steps": 0}
            for config_id in a3b.CONFIG_SPECS
        ],
    }
    lineage = {
        "schema": a3b.LINEAGE_PREFLIGHT_SCHEMA,
        "status": "PASS",
        "protocol": {"sha256": a3b.PROTOCOL_SHA256},
        "driver_sha256_lf": driver,
        "scientific_fields_equal": True,
        "no_solver_steps": True,
        "parent": {
            "protocol_sha256": a3b.PARENT_PROTOCOL_SHA256,
            "driver_sha256": a3b.PARENT_DRIVER_SHA256,
            "checkpoint_sha256": a3b.PARENT_CHECKPOINT_SHA256,
            "result_sha256": a3b.PARENT_RESULT_SHA256,
            "ledger_sha256": a3b.PARENT_LEDGER_SHA256,
            "binding_sha256": a3b.PARENT_BINDING_SHA256,
        },
    }
    preflight_path = tmp_path / "preflight.json"
    lineage_path = tmp_path / "lineage.json"
    a3b._write_json(preflight_path, preflight)
    a3b._write_json(lineage_path, lineage)
    payload = a3b._write_addendum(preflight_path, lineage_path, "PASS")
    assert payload["protocol"]["sha256"] == a3b.PROTOCOL_SHA256
    assert payload["driver"]["sha256_lf"] == driver
    assert payload["lineage"]["parent_checkpoint_sha256"] == a3b.PARENT_CHECKPOINT_SHA256
    assert payload["lineage"]["t1a_cumulative_cap_seconds"] == 600
    assert payload["caps"]["config_caps_seconds"]["T1-A"] == 600
    assert payload["authorization"]["status"] == "NOT_GRANTED"
    assert a3b._load_addendum()["driver"]["sha256_lf"] == driver
    with pytest.raises(a3b.Refused):
        a3b._write_addendum(preflight_path, lineage_path, "PASS")
