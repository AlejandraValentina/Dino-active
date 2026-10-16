import pytest

from scripts.diagnostics.scientific_point_v1_preflight import build_preflight, validate_authorization


def test_scientific_point_preflight_is_zero_step_and_fail_closed_for_old_binding():
    receipt = build_preflight()

    assert receipt["preflight_check"]["status"] == "PASS"
    assert receipt["solver_steps"] == 0
    assert receipt["execution_authorized"] is False
    assert receipt["campaign_started"] is False
    assert receipt["selected_point"]["total_finite_volume_cells"] == 48
    assert receipt["selected_point"]["rpm"] == 3000
    assert receipt["historical_stage1_compatibility"]["mismatches"] == [
        "identity_sha256", "solver_source_hashes"
    ]
    assert receipt["historical_stage1_compatibility"]["old_checkpoint_resume"] == "REJECTED; no reuse permitted"
    assert receipt["execution_contract"]["artifact_root_resolved_outside_repository"] is True


def test_point_authorization_must_bind_identity_and_preflight():
    receipt = build_preflight()
    preflight_sha = "a" * 64
    authorization = {
        "schema": "DINO_SCIENTIFIC_POINT_V1_EXECUTION_AUTHORIZATION_V1",
        "state": "OWNER_APPROVED",
        "preflight_sha256": preflight_sha,
        "configuration_sha256": receipt["selected_point"]["configuration_sha256"],
        "identity_sha256": receipt["selected_point"]["identity_sha256"],
        "runner_sha256": receipt["implementation"]["runner_sha256"],
        "workers": 1,
        "max_cycles": 8,
        "campaign_authorized": False,
        "budget_seconds": 1200,
        "memory_limit_mib": 3072,
        "owner_decision": "One point only under the stated resource cap.",
    }

    validate_authorization(authorization, preflight_sha256=preflight_sha, receipt=receipt)
    authorization["identity_sha256"] = "0" * 64
    with pytest.raises(RuntimeError, match="identity_sha256"):
        validate_authorization(authorization, preflight_sha256=preflight_sha, receipt=receipt)
