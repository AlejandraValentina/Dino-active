"""Regressions for durable G2-v2 evidence, restart and explicit physical gates."""
from __future__ import annotations

import copy
import gzip
import json
import math
import shutil
from pathlib import Path

import pytest
import numpy as np

from dev_orchestrator.p4_g2_v2_recovery import (
    EXPECTED, ROOT, SCHEMA, advance_detector, audit_inputs, metric_row,
    restore_detector, snapshot, native, save_checkpoint, sha,
)
from dev_orchestrator.p4_g2_v2_offline_audit import (
    EvidenceError, audit, check_claim, compare, gates, read_checkpoint,
    recompute_conservation, terminal_inventory,
    validate_detector_snapshot, validate_metric_inputs,
)
from motorsim.periodicity import PeriodicityDetector, compare_cycles


def _inputs(cycle: int, sensor_pressure: float = 1.) -> dict:
    begin = 180. + 360. * (cycle-1)
    return {
        "cycle": cycle, "begin": begin, "end": begin+360., "identity": EXPECTED,
        "state": [1., 1., 0.] * 3, "cells": [[1., 1., 1., 1.]],
        "work_indicated_J": 1., "port_integral": [1., 0., 0.],
        "initial_cylinder_mass": 1.,
        "history": [
            {"angle": angle, "p_cyl": 1.,
             "sensors_p_u_M_Y": [[sensor_pressure]] * 3}
            for angle in (begin, begin+360.)
        ],
        "gate_inputs": {},
    }


def _synthetic_ledger(inputs):
    inventory = terminal_inventory(inputs["state"], inputs["cells"])
    begin, end = inputs["begin"], inputs["end"]
    segments = []
    for i in range(3):
        a = begin+(end-begin)*i/3
        b = begin+(end-begin)*(i+1)/3
        step = {"time_start": 0., "time_end": 1., "dt": 1.,
                "inventory_start": inventory, "inventory_stage1": inventory,
                "inventory_stage2": inventory, "inventory_accepted": inventory,
                "external_rate_stage_a": [0., 0., 0.],
                "external_rate_stage_b": [0., 0., 0.],
                "cumulative_external": [0., 0., 0.],
                "stage_residuals": [0., 0.], "global_residual": [0., 0., 0.]}
        segments.append({"interval_deg": [a, b], "initial_inventory": inventory,
                         "final_inventory": inventory,
                         "external_exchange_raw": [0., 0., 0.],
                         "analytical_burn_species_correction": [0., 0., 0.],
                         "solver_max_stage_residual": 0.,
                         "solver_max_global_residual": 0., "steps": [step]})
    return {"schema": "G2_CONSERVATION_LEDGER_V1", "control_volume": "chain",
            "identity": EXPECTED, "cycle_interval_deg": [begin, end],
            "components": ["mass_kg", "energy_J", "fresh_species_mass_kg"],
            "initial_inventory": inventory, "final_inventory": inventory,
            "external_exchange": [0., 0., 0.], "global_balance": [0., 0., 0.],
            "analytical_burn_species_correction": [0., 0., 0.],
            "segments": segments}


def _gates(cfl=True):
    return {"complete": True, "conservation": True, "positive": True,
            "CFL": cfl}


def test_persisted_inputs_support_product_and_independent_contract():
    raw = {**_inputs(2), **EXPECTED,
           "segments": [{"physical_balance": [0., 0., 0.],
                         "result": {"max_global_residual": 0.,
                                    "max_stage_residual": 0.,
                                    "extrema": {"rho": 1., "p": 1., "T": 1.,
                                                "Y_min": 0., "Y_max": 1.},
                                    "stages": [{"dt": .1, "limits": [.2]}]}}],
           "complete": True, "global_balance": [0., 0., 0.]}
    current = audit_inputs(raw)
    old = _inputs(1)
    assert {"history", "work_indicated_J", "port_integral",
            "initial_cylinder_mass", "gate_inputs"} <= current.keys()
    assert compare_cycles(metric_row(old), metric_row(current))["passed"] is True
    assert compare(old, current)["passed"] is True
    assert current["history"][-1]["sensors_p_u_M_Y"] == [[1.], [1.], [1.]]


def test_offline_metric_is_not_a_stored_pass_claim():
    old, current = _inputs(1), _inputs(2)
    assert compare(old, current)["passed"] is True
    current["history"][1]["sensors_p_u_M_Y"][0][0] = 1.02
    recalculated = compare(old, current)
    assert recalculated["passed"] is False
    with pytest.raises(EvidenceError, match="PASS_CLAIM_MISMATCH"):
        check_claim({"passed": True}, recalculated, "LAG2")


def test_offline_cfl_is_recalculated_from_stage_data():
    segment = {"physical_balance": [0., 0., 0.],
               "max_global_residual": 0., "max_stage_residual": 0.,
               "extrema": {"rho": 1., "p": 1., "T": 1.,
                           "Y_min": 0., "Y_max": 1.},
               "stages": [{"dt": .1, "limits": [.2]}]}
    row = {"gate_inputs": {"complete": True, "global_balance": [0., 0., 0.],
                           "segments": [copy.deepcopy(segment) for _ in range(3)]}}
    assert all(gates(row).values())
    row["gate_inputs"]["segments"][2]["stages"][0]["dt"] = .3
    assert gates(row)["CFL"] is False
    del row["gate_inputs"]["segments"][2]["stages"]
    with pytest.raises(KeyError):
        gates(row)


def _gate_row():
    segment = {"physical_balance": [0., 0., 0.],
               "max_global_residual": 0., "max_stage_residual": 0.,
               "extrema": {"rho": 1., "p": 1., "T": 1.,
                           "Y_min": 0., "Y_max": 1.},
               "stages": [{"dt": .1, "limits": [.2, .25]}]}
    return {"gate_inputs": {"complete": True, "global_balance": [0., 0., 0.],
                            "segments": [copy.deepcopy(segment) for _ in range(3)]}}


@pytest.mark.parametrize("dt", [False, True, None, "0.001", [0.001], 0, -.1,
                                      math.nan, math.inf, -math.inf])
def test_malformed_dt_is_invalid_evidence_not_a_physical_fail(dt):
    row = _gate_row()
    row["gate_inputs"]["segments"][0]["stages"][0]["dt"] = dt
    with pytest.raises(EvidenceError, match="MALFORMED_CFL_DT"):
        gates(row)


def test_positive_finite_dt_passes_type_validation():
    assert all(gates(_gate_row()).values())


@pytest.mark.parametrize("limit", [False, True, None, "0.2", 0, -.2,
                                         math.nan, math.inf, -math.inf])
def test_malformed_cfl_limit_is_invalid_evidence(limit):
    row = _gate_row()
    row["gate_inputs"]["segments"][0]["stages"][0]["limits"][0] = limit
    with pytest.raises(EvidenceError, match="MALFORMED_CFL_LIMIT"):
        gates(row)


@pytest.mark.parametrize("field,malformed,label", [
    ("global_balance", False, "GLOBAL_BALANCE"),
    ("physical_balance", False, "PHYSICAL_BALANCE"),
    ("max_global_residual", False, "GLOBAL_RESIDUAL"),
    ("rho", False, "EXTREMA_rho"),
])
def test_boolean_cannot_be_a_conservation_or_admissibility_number(field, malformed, label):
    row = _gate_row()
    segment = row["gate_inputs"]["segments"][0]
    if field == "global_balance":
        row["gate_inputs"][field][0] = malformed
    elif field == "physical_balance":
        segment[field][0] = malformed
    elif field == "rho":
        segment["extrema"][field] = malformed
    else:
        segment[field] = malformed
    with pytest.raises(EvidenceError, match=f"MALFORMED_{label}"):
        gates(row)


def test_boolean_metric_claim_cannot_match_numeric_zero():
    metric = compare(_inputs(1), _inputs(2))
    assert metric["sensor_max"] == 0.
    claim = copy.deepcopy(metric)
    claim["sensor_max"] = False
    with pytest.raises(EvidenceError, match="MALFORMED_CLAIM_METRIC"):
        check_claim(claim, metric, "LAG2")


@pytest.mark.parametrize("field", ["cycle", "begin", "sample_angle", "sample_pressure"])
def test_boolean_cycle_or_angular_input_is_invalid(field):
    row = _inputs(1)
    if field == "cycle":
        row["cycle"] = True
    elif field == "begin":
        row["begin"] = False
    elif field == "sample_angle":
        row["history"][0]["angle"] = False
    else:
        row["history"][0]["sensors_p_u_M_Y"][0][0] = False
    with pytest.raises(EvidenceError, match="MALFORMED_"):
        validate_metric_inputs(row, 1)


def test_boolean_detector_streak_is_invalid_even_when_equal_to_one():
    detector = PeriodicityDetector(1, EXPECTED["branch_map"])
    detector.update(metric_row(_inputs(1)), lag1={"passed": False},
                    lag2={"passed": False}, branch="A")
    saved = snapshot(detector, 1, "A", {"passed": False}, {"passed": False})
    saved["state"]["branch_A_streak"] = True
    with pytest.raises(EvidenceError, match="MALFORMED_DETECTOR_BRANCH_A_STREAK"):
        validate_detector_snapshot(saved, 1)


def test_numpy_scalar_serialization_preserves_values_and_boolean_gate():
    converted = native({"cfl": np.bool_(True), "pressure": [np.float64(1.25)]})
    assert converted == {"cfl": True, "pressure": [1.25]}
    assert type(converted["cfl"]) is bool
    json.dumps(converted, allow_nan=False)


def test_missing_persisted_input_is_invalid_not_pass(tmp_path):
    row = _inputs(1)
    del row["work_indicated_J"]
    payload = {"schema": SCHEMA, "inputs": row, "parent_sha256": None}
    path = tmp_path/"checkpoint_cycle001.json.gz"
    path.write_bytes(gzip.compress(json.dumps(payload).encode(), mtime=0))
    with pytest.raises(EvidenceError, match="MISSING_CONTRACT_INPUT"):
        read_checkpoint(tmp_path, 1, None, EXPECTED)


def test_continuous_and_restored_detector_have_identical_evolution():
    lag1 = {"passed": False}
    active = PeriodicityDetector(1, EXPECTED["branch_map"])
    restored = None
    continuous_trace = []
    resumed_trace = []
    for cycle in range(1, 13):
        branch = "A" if cycle % 2 else "B"
        lag2 = {"passed": branch == "A" or cycle >= 8}
        row = _inputs(cycle)
        active.update(metric_row(row), lag1=lag1, lag2=lag2, branch=branch)
        continuous_trace.append(copy.deepcopy(active.to_json()))
        if cycle == 8:
            saved = json.loads(json.dumps(snapshot(active, cycle, branch, lag1, lag2)))
            restored = restore_detector(saved, 8)
            assert restored.to_json() == active.to_json()
        elif cycle > 8:
            restored.update(metric_row(row), lag1=lag1, lag2=lag2, branch=branch)
            resumed_trace.append(copy.deepcopy(restored.to_json()))
    assert resumed_trace == continuous_trace[8:]
    assert active.detected_period == restored.detected_period == 2
    assert active.converged_cycle == restored.converged_cycle == 12
    assert (active.branch_A_streak, active.branch_B_streak) == (6, 3)


@pytest.mark.parametrize("damage", ["missing", "identity", "branch", "schema"])
def test_corrupt_detector_state_cannot_resume(damage):
    detector = PeriodicityDetector(1, EXPECTED["branch_map"])
    detector.update(metric_row(_inputs(30)), lag1={"passed": False},
                    lag2={"passed": False}, branch="B")
    saved = snapshot(detector, 30, "B", {"passed": False}, {"passed": False})
    if damage == "missing":
        del saved["state"]["last_metrics"]
    elif damage == "identity":
        saved["state"]["history_identity"]["rpm"] = 4000
    elif damage == "branch":
        saved["last_branch"] = "A"
    else:
        saved["schema"] = "unknown"
    with pytest.raises(ValueError):
        restore_detector(saved, 30)


@pytest.mark.parametrize("cfl", [False, None])
def test_periodic_metrics_cannot_override_failed_or_missing_cfl(cfl):
    detector = PeriodicityDetector(1, EXPECTED["branch_map"])
    detector.update(metric_row(_inputs(49)), lag1={"passed": False},
                    lag2={"passed": True}, branch="A")
    detector.branch_A_streak = 3
    detector.branch_B_streak = 2
    gate = _gates(cfl)
    failure = advance_detector(detector, _inputs(50), {"passed": False},
                               {"passed": True}, "B", gate)
    assert failure is not None
    assert detector.detected_period is None
    assert detector.branch_B_streak == 2


def test_periodic_metrics_with_cfl_pass_can_close():
    detector = PeriodicityDetector(1, EXPECTED["branch_map"])
    detector.update(metric_row(_inputs(49)), lag1={"passed": False},
                    lag2={"passed": True}, branch="A")
    detector.branch_A_streak = 3
    detector.branch_B_streak = 2
    assert advance_detector(detector, _inputs(50), {"passed": False},
                            {"passed": True}, "B", _gates()) is None
    assert detector.detected_period == 2


def _synthetic_durable_campaign(root: Path):
    root.mkdir()
    detector = PeriodicityDetector(1, EXPECTED["branch_map"])
    before2 = before = None
    parent_sha = None
    ancestry = []
    for cycle in range(1, 39):
        pressure = 1.+.01*cycle if cycle <= 30 else (2. if cycle % 2 else 3.)
        row = _inputs(cycle, pressure)
        row["cells"] = [[1., 1., 1., 1.] for _ in range(251)]
        segment = {"physical_balance": [0., 0., 0.],
                   "max_global_residual": 0., "max_stage_residual": 0.,
                   "extrema": {"rho": 1., "p": 1., "T": 1.,
                               "Y_min": 0., "Y_max": 1.},
                   "stages": [{"dt": .1, "limits": [.2]}]}
        row["gate_inputs"] = {"complete": True, "global_balance": [0., 0., 0.],
                              "segments": [copy.deepcopy(segment) for _ in range(3)]}
        row["conservation_ledger"] = _synthetic_ledger(row)
        lag1 = (compare_cycles(metric_row(before), metric_row(row)) if before else
                {"status": "INVALID", "reason": "MISSING_PREVIOUS_CYCLE", "passed": False})
        lag2 = (compare_cycles(metric_row(before2), metric_row(row)) if before2 else
                {"status": "INVALID", "reason": "MISSING_PREVIOUS_CYCLE", "passed": False})
        branch = "A" if cycle % 2 else "B"
        detector.update(metric_row(row), lag1=lag1, lag2=lag2, branch=branch)
        saved = snapshot(detector, cycle, branch, lag1, lag2)
        source_sha = sha(f"synthetic source {cycle}".encode()) if cycle <= 30 else None
        claims = {"lag1": lag1, "lag2": lag2, "checks": _gates()}
        if cycle >= 31:
            claims.update(cycle=cycle, branch=branch, elapsed_seconds=1.,
                          detector=saved["state"])
        parent_sha = save_checkpoint(root, cycle, row, saved,
                                     claims,
                                     parent_sha, source_sha)
        if cycle <= 30:
            ancestry.append({"cycle": cycle, "source_sha256": source_sha,
                             "checkpoint_sha256": parent_sha})
        if cycle == 30:
            seed = root/"seed-detector-cycle030.json"
            seed.write_text(json.dumps(saved), encoding="utf8")
        before2, before = before, row
    assert detector.detected_period == 2 and detector.converged_cycle == 38
    manifest = {"schema": SCHEMA, "contract": "G2-v2", "identity": EXPECTED,
                "max_cycles": 400,
                "thresholds": {"work": .005, "cylinder": .005,
                               "sensor_max": .005, "port": .002, "inventories": .002},
                "source_cycles": ancestry, "seed_detector_sha256": sha(seed.read_bytes()),
                "runtime": {"cfl": .4, "fastmath": False,
                            "parallel": False, "workers": 1}}
    (root/"manifest.json").write_text(json.dumps(manifest), encoding="utf8")
    (root/"decision.json").write_text(json.dumps({
        "status": "E13_G2_V2_PASS", "stop_reason": "CONVERGED_PERIOD2",
        "last_cycle": 38, "cycles_executed": 8, "max_cycles": 400,
        "closing_checkpoint_sha256": parent_sha,
    }), encoding="utf8")


def _alter_closing_checkpoint(root: Path, mutate):
    path = root/"checkpoint_cycle038.json.gz"
    payload = json.loads(gzip.decompress(path.read_bytes()))
    mutate(payload)
    path.write_bytes(gzip.compress(json.dumps(payload).encode(), mtime=0))
    decision_path = root/"decision.json"
    decision = json.loads(decision_path.read_text(encoding="utf8"))
    decision["closing_checkpoint_sha256"] = sha(path.read_bytes())
    decision_path.write_text(json.dumps(decision), encoding="utf8")


def test_offline_auditor_derives_known_synthetic_period2_without_claim_authority(tmp_path):
    root = tmp_path/"durable"
    _synthetic_durable_campaign(root)
    result = audit(root)
    assert result["classification"] == "E13_G2_V2_PASS", result
    assert result["last_cycle"] == 38
    assert result["branch_A_streak"] >= 3 and result["branch_B_streak"] == 3
    assert result["trace"][-1]["lag2_passed"] is True


def test_conservation_ledger_recomputes_synthetic_global_balance():
    row = _inputs(31)
    row["cells"] = [[1., 1., 1., 1.] for _ in range(251)]
    row["conservation_ledger"] = _synthetic_ledger(row)
    row["gate_inputs"] = {"complete": True, "global_balance": [0., 0., 0.],
                          "segments": [{"physical_balance": [0., 0., 0.],
                                        "max_global_residual": 0.,
                                        "max_stage_residual": 0.,
                                        "extrema": {"rho": 1., "p": 1., "T": 1.,
                                                    "Y_min": 0., "Y_max": 1.},
                                        "stages": [{"dt": .1, "limits": [.2]}]}
                                       for _ in range(3)]}
    recomputed = recompute_conservation(row)
    assert recomputed["global_balance"] == [0., 0., 0.]
    assert recomputed["max_global_residual"] == 0.
    assert recomputed["max_stage_residual"] == 0.


@pytest.mark.parametrize("damage,expected", [
    ("initial", "CONSERVATION_DIAGNOSTIC_MISMATCH"),
    ("final", "CONSERVATION_DIAGNOSTIC_MISMATCH"),
    ("external", "CONSERVATION_DIAGNOSTIC_MISMATCH"),
    ("missing", "MISSING_CONSERVATION_TERM"),
    ("nonfinite", "INVALID_CHECKPOINT_SCHEMA_OR_NONFINITE"),
    ("stored_residual", "CONSERVATION_DIAGNOSTIC_MISMATCH"),
])
def test_offline_conservation_auditor_rejects_mutated_primary_ledger(
        tmp_path, damage, expected):
    root = tmp_path/"durable"
    _synthetic_durable_campaign(root)
    def mutate(payload):
        ledger = payload["inputs"]["conservation_ledger"]
        if damage == "initial":
            ledger["segments"][0]["initial_inventory"][0] += .1
        elif damage == "final":
            ledger["segments"][0]["final_inventory"][0] += .1
        elif damage == "external":
            ledger["segments"][0]["external_exchange_raw"][0] += .1
        elif damage == "missing":
            del ledger["segments"][0]["steps"]
        elif damage == "nonfinite":
            ledger["segments"][0]["steps"][0]["dt"] = math.inf
        else:
            payload["inputs"]["gate_inputs"]["global_balance"][0] = .1
    _alter_closing_checkpoint(root, mutate)
    result = audit(root)
    assert result["classification"] == "E13_G2_V2_INCONCLUSIVE", result
    assert expected in result["reason"], result


@pytest.mark.parametrize("damage,expected", [
    ("metric", "LAG2_sensor_max_CLAIM_MISMATCH"),
    ("missing", "MISSING_CONTRACT_INPUT"),
    ("cfl", "PHYSICAL_GATE_FAILED"),
    ("detector", "DETECTOR_STATE_MISMATCH"),
])
def test_offline_auditor_rejects_tampered_closing_evidence(tmp_path, damage, expected):
    root = tmp_path/"durable"
    _synthetic_durable_campaign(root)
    def mutate(payload):
        if damage == "metric":
            payload["claims"]["lag2"]["sensor_max"] = .1
        elif damage == "missing":
            del payload["inputs"]["work_indicated_J"]
        elif damage == "cfl":
            payload["inputs"]["gate_inputs"]["segments"][0]["stages"][0]["dt"] = .3
            payload["claims"]["checks"]["CFL"] = False
        else:
            payload["detector"]["state"]["branch_B_streak"] = 2
    _alter_closing_checkpoint(root, mutate)
    result = audit(root)
    assert result["classification"] == "E13_G2_V2_INCONCLUSIVE"
    assert expected in result["reason"], result


def test_new_durable_acquisition_reaudits_without_producer_pass():
    assert ROOT.exists(), "Committed G2-v2 recovery evidence is required"
    result = audit(ROOT)
    assert result["classification"] == "E13_G2_V2_PASS", result
    assert result["detected_period"] == 2
    assert result["trace"][-1]["lag2_passed"] is True
    assert result["trace"][-1]["CFL"] is True


def test_reacquired_terminal_states_match_historical_run_exactly():
    historical = Path("results/p4-g2-v2-20260929")
    assert ROOT.exists() and historical.exists()
    for cycle in range(31, 51):
        old = json.loads(gzip.decompress(
            (historical/f"checkpoint_cycle{cycle:03}.json.gz").read_bytes()))
        new = json.loads(gzip.decompress(
            (ROOT/f"checkpoint_cycle{cycle:03}.json.gz").read_bytes()))["inputs"]
        assert (old["begin"], old["end"], old["state"], old["cells"]) == (
            new["begin"], new["end"], new["state"], new["cells"])


def test_r2_real_closing_checkpoint_false_dt_cannot_pass_after_hash_update(tmp_path):
    """Replay the R2 finding without relying on the R2 report as an oracle."""
    target = tmp_path/"mutated-real-evidence"
    target.mkdir()
    for checkpoint in ROOT.glob("checkpoint_cycle*.json.gz"):
        shutil.copyfile(checkpoint, target/checkpoint.name)
    for name in ("manifest.json", "seed-detector-cycle030.json", "decision.json"):
        shutil.copyfile(ROOT/name, target/name)
    path = target/"checkpoint_cycle050.json.gz"
    payload = json.loads(gzip.decompress(path.read_bytes()))
    payload["inputs"]["gate_inputs"]["segments"][0]["stages"][0]["dt"] = False
    path.write_bytes(gzip.compress(json.dumps(payload, separators=(",", ":")).encode(),
                                   mtime=0))
    decision_path = target/"decision.json"
    decision = json.loads(decision_path.read_text(encoding="utf-8"))
    decision["closing_checkpoint_sha256"] = sha(path.read_bytes())
    decision_path.write_text(json.dumps(decision), encoding="utf-8")
    result = audit(target)
    assert result["classification"] == "E13_G2_V2_INCONCLUSIVE", result
    assert result["reason"] == "MALFORMED_CFL_DT"
