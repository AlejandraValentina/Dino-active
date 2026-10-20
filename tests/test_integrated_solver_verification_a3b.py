from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "diagnostics"))

import integrated_solver_verification_a3b as a3b


def _synthetic_result(config_id: str, multipliers: dict[str, float]) -> dict:
    records = []
    for cycle in (1, 2, 3):
        observables = {}
        for name in a3b.OBSERVABLES:
            base = -1.0e-9 if name == "crankcase_gas_work_J" else 1.0
            if name == "crankcase.mass_kg":
                base = 1.0
            observables[name] = {
                "value": base * multipliers[config_id],
                "status": "DEFINED",
                "source": "synthetic",
                "reason": None,
            }
        records.append({
            "cycle": cycle,
            "observables": observables,
            "conservation": {"mass_residual_kg": 1.0e-19},
            "timers": {key: 1.0 for key in a3b.TIMER_KEYS},
            "wall_seconds": 10.0,
        })
    return {
        "schema": a3b.RESULT_SCHEMA,
        "config_id": config_id,
        "status": "COMPLETE",
        "protocol_sha256": a3b.PROTOCOL_SHA256,
        "records": records,
        "cycle_indices": [1, 2, 3],
        "cycles_completed": 3,
        "bindings": {
            "protocol_sha256": a3b.PROTOCOL_SHA256,
            "driver_sha256": a3b._file_sha(Path(a3b.__file__)),
            "configuration_sha256": "a" * 64,
            "identity_sha256": "b" * 64,
        },
        "timers": a3b._aggregate_timers(records),
    }


def _write_test_addendum(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(a3b, "ADDENDUM", tmp_path / "addendum.json")
    a3b._write_json(tmp_path / "addendum.json", {
        "schema": a3b.ADDENDUM_SCHEMA,
        "protocol": {"sha256": a3b.PROTOCOL_SHA256},
        "driver": {"sha256_lf": a3b._file_sha(Path(a3b.__file__))},
    })


def test_protocol_and_zero_step_preflight() -> None:
    protocol = a3b._load_protocol()
    assert protocol["status"] == "FROZEN_PROTOCOL_EXECUTION_NOT_AUTHORIZED"
    assert [row["id"] for row in protocol["scope"]["configuration_set"]] == list(
        a3b.CONFIG_SPECS)
    receipt = a3b._protocol_preflight_receipt(list(a3b.CONFIG_SPECS))
    assert receipt["status"] == "PASS"
    assert receipt["no_solver_steps"] is True
    assert [row["config_id"] for row in receipt["configs"]] == list(a3b.CONFIG_SPECS)
    assert [row["total_finite_volume_cells"] for row in receipt["configs"]] == [
        48, 48, 48, 28, 18]
    assert all(row["solver_steps"] == 0 for row in receipt["configs"])
    assert all(row["status"] == "PASS" for row in receipt["configs"])
    assert receipt["configs"][0]["identity_sha256"] == (
        protocol["scope"]["identity_invariants"]["identity_sha256"])


def test_budget_ledger_closes_stale_and_enforces_caps(tmp_path: Path) -> None:
    ledger = a3b._load_ledger(tmp_path)
    assert ledger["entries"] == []
    ledger["entries"].append({
        "invocation_id": "stale",
        "config_id": "T1-A",
        "elapsed_seconds": 2.0,
        "reserved_seconds": 10.0,
        "status": "RUNNING",
    })
    a3b._close_stale_entries(ledger)
    assert ledger["entries"][0]["elapsed_seconds"] == 10.0
    assert ledger["entries"][0]["reserved_seconds"] == 0.0
    assert ledger["entries"][0]["status"] == "INTERRUPTED_ACCOUNTED"
    a3b._save_ledger(tmp_path, ledger)
    assert a3b._load_ledger(tmp_path)["entries"][0]["elapsed_seconds"] == 10.0

    entry = {"config_id": "T1-A", "elapsed_seconds": 0.0, "reserved_seconds": 0.0}
    ledger = {"entries": [entry]}
    reserve = a3b._reserve_next_cycle(ledger, entry, "T1-A", 0.0)
    assert reserve > 0.0
    assert entry["reserved_seconds"] == reserve

    capped = {"config_id": "T1-A", "elapsed_seconds": 500.0, "reserved_seconds": 0.0}
    ledger = {"entries": [capped]}
    with pytest.raises(a3b.BudgetExhausted):
        a3b._reserve_next_cycle(ledger, capped, "T1-A", 0.0)
    assert capped["reserved_seconds"] == 500.0


def test_every_configuration_can_complete_its_planned_cycles() -> None:
    ledger = {"entries": []}
    for config_id, plan in a3b.INVOCATION_PLAN.items():
        estimate = a3b.CONFIG_SPECS[config_id]["linear_seconds_per_cycle"]
        for invocation_index, cycles in enumerate(plan, start=1):
            entry = {
                "invocation_id": f"{config_id}-inv{invocation_index}",
                "config_id": config_id,
                "invocation_index": invocation_index,
                "elapsed_seconds": 0.0,
                "reserved_seconds": 0.0,
                "status": "RUNNING",
            }
            ledger["entries"].append(entry)
            elapsed = 0.0
            for _ in range(cycles):
                a3b._reserve_next_cycle(ledger, entry, config_id, elapsed)
                elapsed += estimate
                entry["elapsed_seconds"] = elapsed
                entry["reserved_seconds"] = 0.0
            entry["status"] = "INVOCATION_COMPLETE_CHECKPOINTED"
    assert a3b._ledger_spent(ledger) <= a3b.GLOBAL_CAP_SECONDS


def test_observable_extraction_prefers_raw_crankcase_values() -> None:
    primary = {
        "observables": {
            "work_J": 10.0,
            "crankcase_gas_work_J": -3.0e-9,
            "net_piston_gas_work_J": 7.0,
            "chambers": {"crankcase": {"mass_kg": 1.25}},
        }
    }
    metrics = {
        "indicated_power_w": {"status": "DEFINED", "value": 100.0, "reason": None},
        "brake_work_j": {"status": "UNDEFINED", "value": None, "reason": "no loss"},
    }
    assert a3b._observable_record(primary, metrics, "crankcase.mass_kg")["value"] == 1.25
    assert a3b._observable_record(primary, metrics, "crankcase_gas_work_J")["value"] == -3.0e-9
    assert a3b._observable_record(primary, metrics, "indicated_power_w")["value"] == 100.0
    undefined = a3b._observable_record(primary, metrics, "brake_work_j")
    assert undefined["status"] == "UNDEFINED"
    assert undefined["value"] is None
    assert a3b._selected_primary_observables(primary) == {
        "work_J": 10.0,
        "crankcase_gas_work_J": -3.0e-9,
        "net_piston_gas_work_J": 7.0,
        "crankcase_mass_kg": 1.25,
    }


def test_classification_rules() -> None:
    def row(delta: float, passes: bool, sign_crossing: bool = False) -> dict:
        return {"cycle": 1, "delta": delta, "passes_tolerance": passes,
                "sign_crossing": sign_crossing, "status": "PASS" if passes else "FAIL"}

    assert a3b._classify_pair_rows(
        [row(0.1, True)], [row(0.01, True)]) == ["CONVERGING_MONOTONE"]
    assert a3b._classify_pair_rows(
        [row(0.1, True)], [row(0.2, True)]) == ["NON_MONOTONE"]
    assert a3b._classify_pair_rows(
        [row(0.1, True)], [row(0.01, False)]) == ["NOT_CONVERGED"]
    assert a3b._classify_pair_rows(
        [row(0.1, True)], [row(0.01, True, True)]) == ["NOT_CONVERGED"]
    assert a3b._classify_pair_rows(
        [row(0.1, True)], [{"cycle": 1, "delta": None, "passes_tolerance": None,
                           "sign_crossing": None, "status": "NOT_EVALUATED"}]
    ) == ["NOT_EVALUATED"]


def test_freeze_and_analysis_are_ordered_and_bounded(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(a3b, "_artifact_root", lambda: tmp_path)
    monkeypatch.setattr(a3b, "ANALYSIS_FREEZE", tmp_path / "freeze.json")
    monkeypatch.setattr(a3b, "REPORT", tmp_path / "report.json")
    monkeypatch.setattr(a3b, "RECEIPT", tmp_path / "receipt.json")
    _write_test_addendum(tmp_path, monkeypatch)

    # Temporal: A -> B -> C has decreasing deltas.
    # Spatial: E -> D -> A has decreasing deltas.
    multipliers = {
        "T1-A": 1.0,
        "T1-B": 1.001,
        "T1-C": 1.0011,
        "T1-D": 0.9995,
        "T1-E": 0.998,
    }
    for config_id in a3b.CONFIG_SPECS:
        a3b._write_json(tmp_path / config_id / "result.json",
                        _synthetic_result(config_id, multipliers))

    freeze = a3b._freeze_atol()
    assert freeze["status"] == "FROZEN_BEFORE_COMPARISON"
    assert (tmp_path / "freeze.json").is_file()
    assert freeze["observables"]["indicated_power_w"]["cycle_1"]["x_base"] == 1.0
    with pytest.raises(a3b.Refused):
        a3b._freeze_atol()

    assert a3b._analyze() == 0
    report = json.loads((tmp_path / "report.json").read_text(encoding="utf-8"))
    assert report["status"] == "COMPLETE"
    assert report["overall_output"] == "NO_GLOBAL_CONVERGENCE_VERDICT"
    assert report["no_global_verdict"] is True
    assert report["no_predictive_claim"] is True
    assert report["claim_scope"]["periodicity"] == "NOT_EVALUATED_HORIZON_INSUFFICIENT"
    assert all(value == "CONVERGING_MONOTONE"
               for value in report["per_observable_classifications"].values())
    assert "does not establish periodicity" in report["bounded_statement"]
    assert (tmp_path / "receipt.json").is_file()


def test_analysis_refuses_without_freeze(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(a3b, "_artifact_root", lambda: tmp_path)
    monkeypatch.setattr(a3b, "ANALYSIS_FREEZE", tmp_path / "missing-freeze.json")
    monkeypatch.setattr(a3b, "REPORT", tmp_path / "report.json")
    monkeypatch.setattr(a3b, "RECEIPT", tmp_path / "receipt.json")
    _write_test_addendum(tmp_path, monkeypatch)
    with pytest.raises(a3b.Refused):
        a3b._analyze()


def test_addendum_binds_current_driver(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(a3b, "ADDENDUM", tmp_path / "addendum.json")
    driver_sha = a3b._file_sha(Path(a3b.__file__))
    receipt = {
        "schema": a3b.PREFLIGHT_SCHEMA,
        "status": "PASS",
        "protocol": {"sha256": a3b.PROTOCOL_SHA256},
        "driver_sha256_lf": driver_sha,
        "configs": [
            {"config_id": config_id,
             "total_finite_volume_cells": a3b.CONFIG_SPECS[config_id]["cells"],
             "max_cfl": a3b.CONFIG_SPECS[config_id]["max_cfl"],
             "solver_steps": 0}
            for config_id in a3b.CONFIG_SPECS
        ],
    }
    receipt_path = tmp_path / "preflight.json"
    a3b._write_json(receipt_path, receipt)
    payload = a3b._write_addendum(receipt_path, "PASS")
    assert payload["driver"]["sha256_lf"] == driver_sha
    assert payload["protocol"]["sha256"] == a3b.PROTOCOL_SHA256
    assert payload["authorization"]["status"] == "NOT_GRANTED"
    assert a3b._load_addendum()["driver"]["sha256_lf"] == driver_sha
    with pytest.raises(a3b.Refused):
        a3b._write_addendum(receipt_path, "PASS")


def test_completed_config_is_not_rewritten(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(a3b, "_artifact_root", lambda: tmp_path)
    _write_test_addendum(tmp_path, monkeypatch)
    authorization = tmp_path / "authorization.json"
    a3b._write_json(authorization, {
        "protocol_sha256": a3b.PROTOCOL_SHA256,
        "owner_confirmation": "synthetic test authorization",
        "global_cap_seconds": a3b.GLOBAL_CAP_SECONDS,
    })
    result_path = tmp_path / "T1-E" / "result.json"
    a3b._write_json(result_path, _synthetic_result("T1-E", {"T1-E": 1.0}))
    before = a3b._file_sha_raw(result_path)
    assert a3b._run_config("T1-E", 1, authorization) == 0
    assert a3b._file_sha_raw(result_path) == before


def test_checkpoint_rejects_changed_binding(tmp_path: Path) -> None:
    built = a3b._build_configuration("T1-E")
    binding = a3b._binding(built)
    engine = a3b.IntegratedEngine2T.from_configuration_dict(
        built["effective"]["native_configuration"])
    detector = a3b.PeriodicDetectorV2()
    checkpoint = {
        "schema": a3b.CHECKPOINT_SCHEMA,
        "bindings": binding,
        "next_cycle": 1,
        "records": [],
        "engine_snapshot": engine.snapshot(),
        "periodicity_snapshot": detector.snapshot(),
    }
    path = tmp_path / "checkpoint.json"
    a3b._write_json(path, checkpoint)
    loaded = a3b._load_checkpoint(path, binding)
    assert loaded is not None
    changed = dict(binding)
    changed["driver_sha256"] = "0" * 64
    with pytest.raises(a3b.Refused):
        a3b._load_checkpoint(path, changed)
