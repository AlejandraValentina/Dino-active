"""F03: contexto de reanudación 4T, fase, identidad y compatibilidad de configuración."""
import json
from pathlib import Path

import numpy as np
import pytest

from motorsim.dino4t import api, runner

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "configs/dino4t/example_single_cylinder_500cc.json"


def bounded_config():
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    config["numerics"]["dx_mm"] = 20.0
    config["numerics"]["max_dtheta_deg"] = 2.0
    return config


def context_for(state, config_hash, theta_start=-360.0):
    return {
        "schema": runner.STATE_CONTEXT_SCHEMA,
        "state": state,
        "theta_deg": theta_start,
        "phase_deg": 0.0,
        "cycles_completed": 1,
        "model_id": runner.MODEL_ID,
        "complete_cycle": True,
        "config_sha256": config_hash,
        "topology_sha256": runner.topology_sha256(state),
        "source_status": "completed",
        "source_termination": "requested_cycles",
    }


def raw_state():
    return {"ducts": {}, "cyl": object(), "plen": {}}


def test_raw_and_midcycle_states_are_rejected_without_a_boundary():
    with pytest.raises(ValueError, match="initial_state must"):
        runner.validate_initial_state(raw_state())
    mid = context_for(raw_state(), "a" * 64)
    mid["complete_cycle"] = False
    with pytest.raises(ValueError, match="mid-cycle"):
        runner.validate_initial_state(mid)
    mid["complete_cycle"] = True
    mid["phase_deg"] = 180.0
    with pytest.raises(ValueError, match="boundary"):
        runner.validate_initial_state(mid)
    mid["phase_deg"] = 0.0
    mid["theta_deg"] = -180.0
    with pytest.raises(ValueError, match="phase"):
        runner.validate_initial_state(
            mid, engine=type("Engine", (), {"initial_state": staticmethod(raw_state),
                                            "theta_start": -360.0})())


def test_model_topology_and_config_assessment():
    from motorsim.dino4t.config import build
    config = bounded_config()
    engine, state, context = build(config)
    good = context_for(state, context["config_hash"])
    assessment = runner.initial_state_assessment(config, good)
    assert assessment["valid"] and assessment["kind"] == "continuation"

    wrong_model = dict(good, model_id="OTHER_MODEL")
    assert not runner.initial_state_assessment(config, wrong_model)["valid"]

    wrong_topology = dict(good, topology_sha256="0" * 64)
    result = runner.initial_state_assessment(config, wrong_topology)
    assert not result["valid"] and "topology" in result["error"]

    changed = json.loads(json.dumps(config))
    changed["combustion"]["efficiency"] = 0.99
    warm = runner.initial_state_assessment(changed, good)
    assert warm["valid"] and warm["kind"] == "warm_start"
    assert warm["source_config_sha256"] == context["config_hash"]


def test_api_rejects_a_context_that_cannot_be_verified():
    from motorsim.dino4t.config import build
    config = bounded_config()
    engine, state, context = build(config)
    good = context_for(state, context["config_hash"])
    broken = dict(good, phase_deg=90.0)
    envelope = api.run(config, initial_state=broken, max_cycles=1, wall_limit_s=30.0)
    assert envelope["error"]["code"] == "OPTION_INVALID"
    assert envelope["summary"] is None


def test_same_configuration_is_a_continuation_without_exact_restart_claim():
    config = bounded_config()
    first = runner.run_operating_point(config, max_cycles=1, wall_limit_s=120.0)
    assert first["state_context"]["complete_cycle"] is True
    second = runner.run_operating_point(
        config, max_cycles=1, wall_limit_s=120.0,
        initial_state=first["state_context"])
    summary = second["summary"]
    assert summary["warm_start"] == "continuation"
    assert summary["initial_state_context"]["kind"] == "continuation"
    assert summary["initial_state_context"]["exact_restart_claim"] == "NOT_SUPPORTED"


def test_cycle_boundary_continuation_agrees_with_continuous_run_to_roundoff():
    config = bounded_config()
    continuous = runner.run_operating_point(config, max_cycles=2, wall_limit_s=180.0)
    first = runner.run_operating_point(config, max_cycles=1, wall_limit_s=120.0)
    second = runner.run_operating_point(
        config, max_cycles=1, wall_limit_s=120.0,
        initial_state=first["state_context"])
    assert second["state_context"]["phase_deg"] == continuous["state_context"]["phase_deg"] == 0.0
    assert (float(second["result"]["theta"]) - first["state_context"]["theta_deg"]) % 720.0 == \
        (float(continuous["result"]["theta"]) - first["state_context"]["theta_deg"]) % 720.0
    left = continuous["result"]["state"]
    right = second["result"]["state"]
    # This is a roundoff-level cycle-boundary continuation, not a bitwise exact
    # restart claim.  The API summary says exact_restart_claim=NOT_SUPPORTED.
    assert second["summary"]["initial_state_context"]["exact_restart_claim"] == "NOT_SUPPORTED"
    assert set(left["ducts"]) == set(right["ducts"])
    for key in left["ducts"]:
        np.testing.assert_allclose(left["ducts"][key], right["ducts"][key],
                                   rtol=1e-10, atol=1e-8)
    np.testing.assert_allclose(left["cyl"], right["cyl"], rtol=1e-10, atol=1e-8)
    assert set(left["plen"]) == set(right["plen"])
    for key in left["plen"]:
        np.testing.assert_allclose(left["plen"][key], right["plen"][key],
                                   rtol=1e-10, atol=1e-8)
