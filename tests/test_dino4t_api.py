"""Dino 4T integration surface (DINO4T_API_V1): the contract Dino Desktop / engine_platform rely on."""
import copy
import json

import pytest

from motorsim import engine_platform
from motorsim.dino4t import api, config


def _cfg():
    return config.load(config.EXAMPLE_PATH)


def test_capabilities_is_json_serialisable_and_declares_no_validation():
    cap = json.loads(json.dumps(api.capabilities()))
    assert cap["api"] == "DINO4T_API_V1" and cap["cycle"] == "4T"
    assert cap["claims"]["experimental_validation"] == "NOT_PERFORMED"
    assert cap["claims"]["predictive_capability"] == "NOT_CLAIMED"
    assert set(api.ERROR_CODES) >= {"CONFIG_INVALID", "MODEL_OUT_OF_VALIDITY", "WALL_LIMIT", "NOT_PERIODIC", "CANCELLED"}


def test_validate_accepts_example_and_returns_hash():
    r = api.validate(_cfg())
    assert r["valid"] and r["issues"] == [] and len(r["config_sha256"]) == 64


@pytest.mark.parametrize("mutate,fragment", [
    (lambda c: c["geometry"].pop("provenance"), "provenance"),
    (lambda c: c.__setitem__("schema", "OTHER"), "schema"),
    (lambda c: c["numerics"].__setitem__("restriction_model", "V9"), "restriction_model"),
    (lambda c: c["combustion"].__setitem__("zone_model", "three_zone"), "combustion"),
    (lambda c: c.pop("intake_duct"), "intake_duct"),
])
def test_validate_reports_bad_configurations_without_raising(mutate, fragment):
    c = _cfg()
    mutate(c)
    r = api.validate(c)
    assert not r["valid"] and r["config_sha256"] is None
    assert r["issues"][0]["code"] == "CONFIG_INVALID" and fragment in r["issues"][0]["message"]


def test_run_returns_error_envelope_for_bad_input_instead_of_raising():
    c = _cfg()
    c["numerics"]["restriction_model"] = "V9"
    out = api.run(c, max_cycles=1)
    assert out["ok"] is False and out["summary"] is None and out["error"]["code"] == "CONFIG_INVALID"
    assert api.run(_cfg(), max_cycles=0)["error"]["code"] == "OPTION_INVALID"
    assert api.run(_cfg(), wall_limit_s=-1)["error"]["code"] == "OPTION_INVALID"


def test_run_envelope_summary_conforms_and_is_not_presented_as_ok_when_not_periodic(tmp_path):
    seen = []
    base = _cfg()
    snapshot = copy.deepcopy(base)
    out = api.run(base, out_dir=tmp_path, max_cycles=2, overrides={"numerics": {"dx_mm": 30.0}},
                  on_progress=seen.append)
    assert base == snapshot  # the caller's configuration is never mutated
    assert out["api"] == "DINO4T_API_V1" and out["summary"] is not None
    assert api.check_summary(out["summary"]) == []
    assert seen and set(seen[0]) == {"cycle", "work_net_J", "p_max_bar"}
    assert out["ok"] == (out["error"] is None)
    if out["summary"]["periodicity"]["status"] != "PERIODIC_CONVERGED":
        assert out["error"]["code"] == "NOT_PERIODIC"  # 2 cycles cannot be periodic: must not read as success
    json.dumps(out["summary"])  # fully JSON serialisable
    assert (tmp_path / "summary.json").exists() and out["artifacts"]["summary"] == "summary.json"


def test_summary_states_the_models_actually_used_and_whether_code_was_dirty():
    out = api.run(_cfg(), max_cycles=1, overrides={"numerics": {"dx_mm": 30.0, "restriction_model": "V1"},
                                                    "combustion": {"zone_model": "single_zone"}})
    s = out["summary"]
    assert s["models"]["valve_boundary"] == "QUASI_STEADY_RESTRICTION_V1"
    assert s["models"]["cylinder"] == "SINGLE_ZONE_0D_V1"
    assert isinstance(s["code_dirty"], (bool, type(None)))
    out2 = api.run(_cfg(), max_cycles=1, overrides={"numerics": {"dx_mm": 30.0}})
    assert out2["summary"]["models"]["valve_boundary"] == "QUASI_STEADY_RESTRICTION_V2"
    assert out2["summary"]["models"]["cylinder"] == "TWO_ZONE_EQUILIBRIUM_V1"


def test_check_summary_rejects_unsupported_claims():
    out = api.run(_cfg(), max_cycles=1, overrides={"numerics": {"dx_mm": 30.0}})
    s = copy.deepcopy(out["summary"])
    s["claims"]["experimental_validation"] = "PERFORMED"
    s["claims"]["predictive_capability"] = "CLAIMED"
    assert len(api.check_summary(s)) == 2


def test_indicator_units_follow_the_name_suffix_for_every_reported_indicator():
    out = api.run(_cfg(), max_cycles=1, overrides={"numerics": {"dx_mm": 30.0}})
    units = {k: api.indicator_unit(k) for k in out["summary"]["final_cycle"]}
    assert units["imep_net_bar"] == "bar" and units["brake_power_kW"] == "kW" and units["T_burned_max_K"] == "K"
    assert units["bsfc_g_kWh"] == "g/kWh" and units["volumetric_efficiency_intake_valve"] is None


def test_engine_platform_still_runs_4t_through_the_shared_contract():
    s = engine_platform.run_operating_point("4T", _cfg(), max_cycles=1, overrides={"numerics": {"dx_mm": 30.0}})
    assert s["claims"]["experimental_validation"] == "NOT_PERFORMED"
    assert engine_platform.families() == ("4T",)


def test_unknown_configuration_keys_are_rejected_because_they_silently_select_defaults():
    c = _cfg()
    c["numerics"]["restricton_model"] = "V1"  # typo: would silently run V2
    c["combustion"]["effciency"] = 0.5
    r = api.validate(c)
    assert not r["valid"] and set(r["unknown_keys"]) == {"numerics.restricton_model", "combustion.effciency"}
    out = api.run(c, max_cycles=1)
    assert out["error"]["code"] == "CONFIG_INVALID" and "restricton_model" in out["error"]["message"]
    assert api.validate(_cfg())["unknown_keys"] == []


def test_user_cancellation_stops_after_complete_cycle_and_persists_partial_primary(tmp_path):
    import threading

    cancel=threading.Event();output=tmp_path/"cancelled-run"
    result=api.run(_cfg(),out_dir=output,max_cycles=20,wall_limit_s=30.0,
        overrides={"numerics":{"dx_mm":30.0}},cancel_event=cancel,
        on_progress=lambda record:cancel.set())
    assert result["error"]["code"]=="CANCELLED"
    assert result["summary"]["status"]=="incomplete"
    assert result["summary"]["termination"]=="cancelled_by_user"
    assert result["summary"]["cycles_run"]==1
    assert result["summary"]["periodicity"]["status"]=="NOT_CONVERGED"
    assert result["state"] is not None and api.check_summary(result["summary"])==[]
    assert (output/"summary.json").is_file()
    assert (output/"config_resolved.json").is_file()
    assert (output/"trace_last_cycle.csv").is_file()
    assert not (output/"checkpoint.json").exists()


def test_cancel_event_option_must_be_event_like():
    assert api.run(_cfg(),max_cycles=1,cancel_event=object())["error"]["code"]=="OPTION_INVALID"
