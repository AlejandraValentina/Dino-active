from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from motorsim.full_rpm_outputs_v1 import compute_full_rpm_outputs_v1
from motorsim.full_rpm_sweep_v1 import preflight_full_rpm_sweep_v1
from motorsim.mechanical_loss_binding_v1 import (
    MechanicalLossBindingError,
    resolve_mechanical_loss_v1,
)
from scripts import full_rpm_sweep_v1_campaign as campaign
from scripts.full_rpm_sweep_v1_campaign import execute_campaign


ROOT = Path(__file__).resolve().parents[1]
PREREG = ROOT / "results/full-rpm-sweep-v1/preregistration.json"
R2_A3000 = ROOT / "results/engine-physics-v1/r2-semantic-correction/A3000/engineering-r2-073.json"


def _contract(tmp_path, mutate):
    value = json.loads(PREREG.read_text(encoding="utf-8"))
    mutate(value)
    path = tmp_path / "preregistration.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def _resolved_a():
    return resolve_mechanical_loss_v1(
        preregistration_path=PREREG,
        variant_id="A_PRIME_MESH_0",
        repository_root=ROOT,
    )


def test_explicit_mechanical_loss_provenance_is_bound_to_fixture_and_config():
    loss = _resolved_a()
    assert loss.model_sha256 == "18f4f692ae9716fbee21f16b4b0bf4fbeb17c4b21a08133dcc7bc36bf75cc76e"
    assert loss.fixture_id == "FIXTURE_A_PRIME"
    assert loss.provenance["fixture_sha256"] == loss.fixture_sha256
    assert loss.provenance["engine_configuration_sha256"] == loss.engine_configuration_sha256
    assert loss.provenance["model_sha256"] == loss.model_sha256
    assert loss.provenance["fallback_used"] is False
    assert len(loss.provenance["evaluated_mep_pa_by_term_and_rpm"]) == 30


def test_missing_model_fails_closed_without_default(tmp_path):
    path = _contract(tmp_path, lambda p: p["variants"][0].pop("mechanical_loss_model"))
    with pytest.raises(MechanicalLossBindingError, match="MISSING_EXPLICIT_MECHANICAL_LOSS_MODEL"):
        resolve_mechanical_loss_v1(
            preregistration_path=path, variant_id="A_PRIME_MESH_0",
            repository_root=ROOT)


def test_implicit_fallback_is_not_reachable(monkeypatch):
    import motorsim.engine_physics_v1 as legacy_engine_physics

    def forbidden():
        raise AssertionError("legacy standard FMEP fallback was called")

    monkeypatch.setattr(legacy_engine_physics, "standard_fmep_model_v1", forbidden)
    report = preflight_full_rpm_sweep_v1(repository_root=ROOT)
    assert report["preflight_status"] == "PASS"
    loss = _resolved_a()
    out = compute_full_rpm_outputs_v1(
        cylinder_indicated_work_j=0.1,
        net_piston_gas_work_j=0.2,
        swept_displacement_m3=1e-4,
        rpm=3000,
        air_delivered_kg=4.9e-6,
        fuel_delivered_kg=1e-7,
        stoichiometric_afr=14.712643678160918,
        mechanical_loss=loss,
        primary_id="test-primary",
        primary_sha256="a" * 64,
        cycle_index=1,
    )
    assert out["outputs"]["FMEP"]["value"] == pytest.approx(1500.0)
    with pytest.raises(ValueError, match="MISSING_EXPLICIT_MECHANICAL_LOSS_MODEL"):
        compute_full_rpm_outputs_v1(
            cylinder_indicated_work_j=0.1, net_piston_gas_work_j=0.2,
            swept_displacement_m3=1e-4, rpm=3000, fuel_delivered_kg=1e-7,
            air_delivered_kg=1e-6, stoichiometric_afr=14.7,
            mechanical_loss=None, primary_id="test-primary",
            primary_sha256="a" * 64, cycle_index=1)


def test_invalid_loss_schema_and_map_domain_fail_closed(tmp_path):
    invalid_schema = _contract(
        tmp_path / "schema",
        lambda p: p["variants"][0]["mechanical_loss_model"].update(schema="UNKNOWN"))
    with pytest.raises(MechanicalLossBindingError):
        resolve_mechanical_loss_v1(
            preregistration_path=invalid_schema, variant_id="A_PRIME_MESH_0",
            repository_root=ROOT)


def test_brake_outputs_satisfy_bmep_power_and_torque_relations():
    loss = _resolved_a()
    work = 0.35
    displacement = 1.2e-4
    rpm = 3000.0
    out = compute_full_rpm_outputs_v1(
        cylinder_indicated_work_j=0.2,
        net_piston_gas_work_j=work,
        swept_displacement_m3=displacement,
        rpm=rpm,
        air_delivered_kg=4.9e-6,
        fuel_delivered_kg=1e-7,
        stoichiometric_afr=14.712643678160918,
        mechanical_loss=loss,
        primary_id="sample",
        primary_sha256="b" * 64,
        cycle_index=4,
    )
    perf = out["performance"]
    assert out["outputs"]["BMEP"]["value"] == pytest.approx(
        work / displacement - perf["friction_mep_pa"])
    assert out["outputs"]["brake_power"]["value"] == pytest.approx(
        perf["brake_work_j"] * rpm / 60.0)
    assert out["outputs"]["brake_power"]["value"] == pytest.approx(
        out["outputs"]["brake_torque"]["value"] * 2 * 3.141592653589793 * rpm / 60.0)


def test_r2_corrected_outputs_remain_compatible():
    point = json.loads(R2_A3000.read_text(encoding="utf-8"))
    outputs = point["outputs"]
    result = compute_full_rpm_outputs_v1(
        cylinder_indicated_work_j=outputs["cylinder_indicated_work"]["value"],
        net_piston_gas_work_j=outputs["net_piston_gas_work"]["value"],
        swept_displacement_m3=point["swept_displacement_m3"],
        rpm=point["rpm"],
        air_delivered_kg=outputs["delivered_air"]["value"],
        fuel_delivered_kg=outputs["delivered_fuel"]["value"],
        stoichiometric_afr=outputs["stoichiometric_AFR"]["value"],
        mechanical_loss=_resolved_a(),
        primary_id=point["primary"]["artifact_id"],
        primary_sha256=point["primary"]["sha256"],
        cycle_index=point["cycle"],
    )["outputs"]
    for name, r2_name in (("IMEP", "IMEP"), ("FMEP", "FMEP"),
                          ("BMEP", "BMEP"), ("brake_power", "brake_power"),
                          ("brake_torque", "brake_torque"),
                          ("ISFC", "ISFC"), ("BSFC", "BSFC")):
        assert result[name]["status"] == outputs[r2_name]["status"]
        assert result[name]["value"] == pytest.approx(outputs[r2_name]["value"], rel=1e-12, abs=1e-12)
    for name in ("AFR", "lambda", "phi"):
        assert result[name]["status"] == outputs[name]["status"]
        assert result[name]["value"] == pytest.approx(outputs[name]["value"], rel=1e-12, abs=1e-12)


def test_preflight_accepts_all_preregistered_points_without_solver_steps():
    report = preflight_full_rpm_sweep_v1(repository_root=ROOT)
    assert report["preflight_status"] == "PASS"
    assert report["readiness_claim"] == "PRECONDITION_RESOLVED"
    assert report["campaigns_started"] == 0
    assert report["solver_steps_started"] == 0
    assert report["points_preflighted"] == 30
    assert all(all(variant["checks"].values()) for variant in report["variants"])


def test_invalid_wot_configuration_fails_before_solver(tmp_path):
    path = _contract(tmp_path, lambda p: p["operation"].update(throttle_fraction=0.5))
    report = preflight_full_rpm_sweep_v1(path, repository_root=ROOT)
    assert report["preflight_status"] == "FAIL_CLOSED"
    assert report["readiness_claim"] == "EXPLICIT_MECHANICAL_LOSS_MODEL_REQUIRED"
    assert report["campaigns_started"] == 0
    assert report["solver_steps_started"] == 0
    assert report["errors"] == ["SWEEP_WOT_CONTRACT_INVALID"]


def test_out_of_domain_power_valve_config_fails_preflight(tmp_path):
    def change_grid(p):
        p["rpm_grid"].update(start_rpm=9000, stop_rpm=9000,
                              increment_rpm=100, points_rpm=[9000])
    path = _contract(tmp_path, change_grid)
    report = preflight_full_rpm_sweep_v1(path, repository_root=ROOT)
    assert report["preflight_status"] == "FAIL_CLOSED"
    assert any("SWEEP_POWERVALVE_DOMAIN_INVALID" in error
               for row in report["variants"] for error in row["errors"])


def test_nonpositive_brake_power_has_causal_bsfc_reason():
    result = compute_full_rpm_outputs_v1(
        cylinder_indicated_work_j=0.1,
        net_piston_gas_work_j=0.01,
        swept_displacement_m3=1e-4,
        rpm=3000,
        air_delivered_kg=1e-6,
        fuel_delivered_kg=1e-7,
        stoichiometric_afr=14.7,
        mechanical_loss=_resolved_a(),
        primary_id="sample",
        primary_sha256="c" * 64,
        cycle_index=2,
    )["outputs"]
    assert result["BSFC"]["status"] == "UNDEFINED"
    assert result["BSFC"]["reason"] == "NONPOSITIVE_BRAKE_POWER"


def test_campaign_runner_refuses_execution_without_explicit_authorization(tmp_path, monkeypatch):
    target = tmp_path / "external-output"
    status = json.loads(campaign.PROGRAM_STATUS.read_text(encoding="utf-8"))
    status["full_rpm_sweep_execution_authorized"] = False
    status_path = tmp_path / "program-status.json"
    status_path.write_text(json.dumps(status), encoding="utf-8")
    monkeypatch.setattr(campaign, "PROGRAM_STATUS", status_path)
    with pytest.raises(RuntimeError, match="campaign execution is not authorized"):
        execute_campaign(output_root=target)
    assert not target.exists()


def test_campaign_cycle_stepper_honors_expired_deadline_before_advancing(monkeypatch):
    engine = SimpleNamespace(crank_angle_unwrapped_deg=0.0,
                             reference_rpm=3000.0,
                             step=lambda *_: pytest.fail("solver step must not start"))
    monkeypatch.setattr(campaign, "_integrated_scheduled_angles",
                        lambda *_: set())
    with pytest.raises(campaign._CampaignDeadlineReached):
        campaign._advance_to_bounded(engine, 360.0, [], deadline=0.0)
    assert engine.crank_angle_unwrapped_deg == 0.0


def test_pilot_is_exactly_the_two_preregistered_4000_rpm_points():
    prereg = json.loads(PREREG.read_text(encoding="utf-8"))
    selected = campaign._selected_points(prereg, pilot=True)
    assert [(variant["variant_id"], rpm) for variant, rpm in selected] == [
        ("A_PRIME_MESH_0", 4000), ("B_PRIME_MESH_0", 4000)]
    assert len(campaign._selected_points(prereg, pilot=False)) == 30


def test_checkpoint_resume_requires_matching_bindings(tmp_path):
    path = tmp_path / "checkpoint.json"
    expected = {"preregistration_sha256": "a" * 64,
                "point_configuration_sha256": "b" * 64}
    checkpoint = {
        "schema": "FULL_RPM_SWEEP_V1_POINT_CHECKPOINT",
        "bindings": expected,
        "next_cycle": 8,
        "engine_snapshot": {"angle": 2520.0},
        "periodicity_snapshot": {"streak": 2},
    }
    path.write_text(json.dumps(checkpoint), encoding="utf-8")
    assert campaign._load_checkpoint(path, expected)["next_cycle"] == 8
    with pytest.raises(ValueError, match="binding hash mismatch"):
        campaign._load_checkpoint(path, {**expected, "point_configuration_sha256": "c" * 64})


def test_campaign_manifest_records_point_start_and_cycle_checkpoint(tmp_path):
    prereg = json.loads(PREREG.read_text(encoding="utf-8"))
    variant = prereg["variants"][0]
    root = tmp_path / "campaign"
    root.mkdir()
    points = [{"point_id": f"{item['variant_id']}@{rpm}RPM",
               "variant_id": item["variant_id"], "rpm": rpm,
               "classification": "NOT_STARTED"}
              for item in prereg["variants"] for rpm in prereg["rpm_grid"]["points_rpm"]]
    (root / "campaign.json").write_text(json.dumps({
        "campaigns_started": 0, "campaign_status": "PREPARED",
        "completed_or_checkpointed_points": points,
    }), encoding="utf-8")
    campaign._record_point_started(root, variant, 4000, cycles_completed=0, next_cycle=1)
    checkpoint = root / variant["variant_id"] / "rpm-04000" / "checkpoint.json"
    checkpoint.parent.mkdir(parents=True)
    checkpoint.write_text("{}", encoding="utf-8")
    campaign._record_checkpoint_progress(
        root, variant, 4000, checkpoint,
        {"classification": "IN_PROGRESS_CHECKPOINTED", "cycles_completed": 1,
         "next_cycle": 2, "performance_metrics": {"measured_cycles": 1}})
    manifest = json.loads((root / "campaign.json").read_text(encoding="utf-8"))
    row = next(item for item in manifest["completed_or_checkpointed_points"]
               if item["point_id"] == "A_PRIME_MESH_0@4000RPM")
    assert manifest["campaigns_started"] == 1
    assert row["classification"] == "IN_PROGRESS_CHECKPOINTED"
    assert row["checkpoint_sha256"] == campaign._sha256(checkpoint.read_bytes())


def test_campaign_provenance_bundle_is_self_contained_and_hash_bound(tmp_path):
    prereg = json.loads(PREREG.read_text(encoding="utf-8"))
    receipt = campaign._ensure_campaign_provenance(
        tmp_path / "campaign", prereg, campaign.canonical_sha256(prereg))
    assert receipt["campaign_id"].startswith("FULL_RPM_SWEEP_V1_")
    assert receipt["source_files"][prereg["variants"][0]["source_fixture_path"]]
    assert receipt["variant_configurations"]["A_PRIME_MESH_0"]["engine_configuration_sha256"] == prereg["variants"][0]["engine_configuration_sha256"]
