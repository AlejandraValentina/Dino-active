import gzip
import json
from pathlib import Path

import pytest

from motorsim.artifact_store import resolve_external_artifact
from motorsim.engine_physics_v1_r2_semantics import (
    load_fixture_model, output_hard_checks, recompute_partition_conservation,
    scavenging_identity_check, metering_ratios,
)
import scripts.engine_physics_v1_r2_offline_replay as replay
from scripts.verify_engine_physics_v1_r2_semantic_evidence import verify as verify_evidence
from scripts.engine_physics_v1_r2_offline_replay import POINTS, build_point

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def corrected_points():
    return [build_point(point) for point in POINTS]


def test_four_accepted_primaries_use_fixture_loss_and_metering_contract(corrected_points):
    assert len(corrected_points) == 4
    for point in corrected_points:
        out = point["outputs"]
        assert out["FMEP"]["value"] == pytest.approx(1500.0)
        assert out["FMEP"]["provenance_details"]["fields_used"]
        assert "fixture_sha256:" in out["FMEP"]["source"]
        assert "model:MECHANICAL_LOSS_MODEL_V1" in out["FMEP"]["source"]
        assert "air_ledger:observables.fresh_air_intake_delivery_kg" in out["AFR"]["source"]
        assert "fuel_ledger:observables.fuel_delivered_kg" in out["AFR"]["source"]
        assert out["AFR"]["value"] == pytest.approx(49.0)
        assert out["lambda"]["value"] == pytest.approx(
            out["AFR"]["value"] / out["stoichiometric_AFR"]["value"])
        assert out["phi"]["value"] == pytest.approx(1.0 / out["lambda"]["value"])
        assert out["fuel_burned"]["value"] + out["fuel_unburned"]["value"] == pytest.approx(
            out["fuel_available"]["value"], abs=1e-12)
        assert out["fuel_burned"]["value"] <= out["fuel_available"]["value"] + 1e-12
        for name in ("TE", "CE", "SE"):
            assert out[name]["status"] == "UNDEFINED"
            assert out[name]["reason"] == "CURRENT_CYCLE_FRESH_RETENTION_NOT_IDENTIFIABLE"
        assert point["hard_physical_gate"]["classification"] == "PASS"
        assert point["hard_physical_gate"]["checks"]["partition_conservation_independent"]
        assert out["BMEP"]["value"] == pytest.approx(
            (out["net_piston_gas_work"]["value"] - out["FMEP"]["value"] *
             point["swept_displacement_m3"]) / point["swept_displacement_m3"])
        assert out["brake_power"]["value"] == pytest.approx(
            out["brake_torque"]["value"] * 2 * 3.141592653589793 * point["rpm"] / 60)
        assert out["fuel_unburned"]["value"] == pytest.approx(
            out["fuel_available"]["value"] - out["fuel_burned"]["value"])


def test_zero_fuel_and_missing_stoichiometry_have_causal_reasons():
    zero_fuel = metering_ratios(0.01, 0.0, 14.7)
    assert zero_fuel["AFR"]["status"] == "UNDEFINED"
    assert zero_fuel["AFR"]["reason"] == "ZERO_FUEL_DELIVERY"
    assert zero_fuel["lambda"]["reason"] == "AFR_UNDEFINED"
    missing_stoich = metering_ratios(0.01, 0.001, None)
    assert missing_stoich["AFR"]["value"] == pytest.approx(10.0)
    assert missing_stoich["lambda"]["status"] == "UNDEFINED"
    assert missing_stoich["lambda"]["reason"] == "MISSING_STOICHIOMETRIC_AFR"


def test_fixture_model_is_loaded_from_configuration_matching_primary():
    primary = json.load(gzip.open(resolve_external_artifact("R2_A3000"), "rt", encoding="utf-8"))
    fixture_path = ROOT / "results/2t-commercial-core-20261002/fixtures/v1-prime-mesh/fixture_a_prime-mesh-0.json"
    model, provenance = load_fixture_model(primary, fixture_path, "FIXTURE_A_PRIME")
    assert sum(term.mep_pa for term in model.terms) == pytest.approx(1500.0)
    assert provenance["primary_configuration_binding_sha256"] == primary["evidence_binding"]["fixture_sha256"]
    assert provenance["mechanical_loss_model_sha256"]


def test_unresolvable_fixture_is_undefined_and_fails_without_fallback(monkeypatch):
    def unavailable(*args, **kwargs):
        raise ValueError("fixture mismatch")
    monkeypatch.setattr(replay, "load_fixture_model", unavailable)
    point = build_point(POINTS[0])
    assert point["outputs"]["FMEP"]["status"] == "UNDEFINED"
    assert point["outputs"]["FMEP"]["reason"] == "FIXTURE_MECHANICAL_LOSS_UNRESOLVED"
    assert point["outputs"]["BMEP"]["status"] == "UNDEFINED"
    assert point["hard_physical_gate"]["classification"] == "HARD_PHYSICAL_INVALID"
    assert not point["hard_physical_gate"]["checks"]["fixture_mechanical_loss_consistency"]


def _gate_inputs():
    from motorsim.mechanical import LossTerm, MechanicalLossModel

    model = MechanicalLossModel((
        LossTerm("ring", "piston_ring", "SYNTHETIC_ASSUMPTION", mep_pa=1000.0),
        LossTerm("bearing", "bearing_accessory", "SYNTHETIC_ASSUMPTION", mep_pa=500.0),
    ))
    prefix = "primary:R2_A3000;sha256:" + "a" * 64 + ";"
    outputs = {name: {"value": 0.5, "status": "DEFINED", "source": prefix + name,
                      "definition_version": "TEST_V1", "provenance": "SYNTHETIC_ASSUMPTION"}
               for name in ("DR", "TE", "CE", "SE", "AFR", "FMEP", "stoichiometric_AFR")}
    for name in ("TE", "CE", "SE"):
        outputs[name] = {"value": None, "status": "UNDEFINED",
                         "reason": "CURRENT_CYCLE_FRESH_RETENTION_NOT_IDENTIFIABLE",
                         "source": prefix + name, "definition_version": "TEST_V1",
                         "provenance": "SYNTHETIC_ASSUMPTION"}
    outputs["AFR"]["source"] += ";air_ledger:observables.fresh_air_intake_delivery_kg;fuel_ledger:observables.fuel_delivered_kg"
    outputs["FMEP"]["source"] += ";fixture:test.json;fixture_sha256:" + "b" * 64 + ";model:MECHANICAL_LOSS_MODEL_V1"
    outputs["stoichiometric_AFR"]["source"] += ";fuel_snapshot_sha256:" + "c" * 64 + ";method:ELEMENTAL_MASS_BALANCE_DRY_AIR_V1"
    identity = {"status": "NOT_APPLICABLE", "passed": None}
    partition = {"passed": True}
    args = dict(fmep_used_pa=1500.0, fixture_model=model, rpm=3000.0,
                afr={"status": "DEFINED", "value": 49.0}, air_kg=49.0e-6,
                metered_fuel_kg=1.0e-6, available_fuel_kg=1.0e-6,
                burned_fuel_kg=0.8e-6, unburned_fuel_kg=0.2e-6,
                fuel_snapshot_bound=True,
                outputs=outputs, partition=partition, scavenging_identity=identity,
                expected_source_prefix=prefix)
    return args


@pytest.mark.parametrize("gate,mutation", [
    ("fixture_mechanical_loss_consistency", {"fmep_used_pa": 85000.0}),
    ("metering_afr_consistency", {"afr": {"status": "DEFINED", "value": 68.0}}),
    ("fuel_accounting_closure", {"unburned_fuel_kg": 0.3e-6}),
    ("fuel_burned_le_available", {"burned_fuel_kg": 1.2e-6}),
    ("fuel_property_source_consistency", {"fuel_snapshot_bound": False}),
    ("scavenging_metric_dependency_validity", {"defined_te": True}),
    ("scavenging_metric_identity", {"identity_fail": True}),
    ("partition_conservation_independent", {"partition_fail": True}),
    ("no_placeholders", {"placeholder_source": True}),
])
def test_each_corrected_hard_gate_fails_its_mutation(gate, mutation):
    args = _gate_inputs()
    if "defined_te" in mutation:
        args["outputs"]["TE"].update(value=0.5, status="DEFINED", reason=None)
    if "identity_fail" in mutation:
        args["scavenging_identity"] = {"status": "DEFINED", "passed": False}
    if "partition_fail" in mutation:
        args["partition"] = {"passed": False}
    if "placeholder_source" in mutation:
        args["outputs"]["AFR"]["source"] = "fallback: hardcoded"
    for key, value in mutation.items():
        if key not in {"defined_te", "identity_fail", "partition_fail", "placeholder_source"}:
            args[key] = value
    assert output_hard_checks(**args)[gate] is False


def test_independent_partition_recomputation_detects_corrupt_external_ledger():
    primary = json.load(gzip.open(resolve_external_artifact("R2_A3000"), "rt", encoding="utf-8"))
    assert recompute_partition_conservation(primary)["passed"]
    primary["cycle_ledgers"]["external_species_kg"][0] += 1e-6
    mutated = recompute_partition_conservation(primary)
    assert not mutated["passed"]
    assert mutated["max_abs_species_residual_kg"] > 1e-12


def test_valid_synthetic_scavenging_inputs_enforce_ce_identity():
    result = scavenging_identity_check(
        {"status": "DEFINED", "value": 0.8},
        {"status": "DEFINED", "value": 0.75},
        {"status": "DEFINED", "value": 0.6},
    )
    assert result["passed"]
    bad = scavenging_identity_check(
        {"status": "DEFINED", "value": 0.8},
        {"status": "DEFINED", "value": 0.75},
        {"status": "DEFINED", "value": 0.7},
    )
    assert not bad["passed"]


def test_nonpositive_brake_power_has_causal_bsfc_reason(corrected_points):
    point = next(item for item in corrected_points if item["point_id"] == "A4000")
    assert point["outputs"]["brake_power"]["value"] <= 0
    assert point["outputs"]["BSFC"]["status"] == "UNDEFINED"
    assert point["outputs"]["BSFC"]["reason"] == "NONPOSITIVE_BRAKE_POWER"


def test_persisted_semantic_evidence_audit_passes():
    result = verify_evidence()
    assert result["all_pass"]
    assert result["comparison_baseline"] == "persisted pre-correction R2 offline manifest"


def test_old_new_comparison_uses_defective_r2_manifest():
    path = ROOT / "results/engine-physics-v1/r2-semantic-correction/comparison.json"
    comparison = json.loads(path.read_text(encoding="utf-8"))
    assert comparison["A3000"]["FMEP"]["old"] == pytest.approx(85000.0)
    assert comparison["A3000"]["FMEP"]["new"] == pytest.approx(1500.0)
    assert comparison["A3000"]["AFR"]["old"] == pytest.approx(67.76299433555442)
    assert comparison["A3000"]["AFR"]["new"] == pytest.approx(49.0)
