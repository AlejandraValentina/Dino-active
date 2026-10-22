"""Focused runner checks; no long runs and no historical artifacts."""
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("minimal_point", ROOT/"scripts/run_standard_exploratory_point.py")
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


def engine():
    return runner.IntegratedEngine2T.from_configuration_dict(json.loads(
        (ROOT/"configs/reference_cases/standard_v1_125cc_blair_cartwright.json").read_text()))


def test_configuration_geometry_and_six_petals():
    e = engine()
    assert len(e.reed_petals) == 6
    assert e.configuration_dict()["port_binding"]["port_set"]["ports"][0]["height_mm"] == 36
    assert runner.closure_events(e,9000)["exhaust"] == pytest.approx(272.084717078)
    assert runner.static_area(e.reed_petals,1000) == pytest.approx(93.988896e-6)


def test_native_step_diagnostics_conservation_and_restore():
    e = engine()
    d = runner.Diagnostics()
    row = e.step(.01/(6*9000),.01)
    d.consume(e,row)
    assert d.samples
    assert d.dt[0] > 0
    assert d.cfl <= .4
    assert max(runner.conservation(e)["relative"].values()) < 1e-8
    initial = e.initial_inventory
    delta = runner.ledger_delta(e.ledger,{k:([0]*len(v) if isinstance(v,list) else 0) for k,v in e.ledger.items()})
    obs = runner.terminal_observables(e,initial,delta)
    a = dict(cycle_index=1,configuration_hash="test",contract=runner.CONTRACT,observables=obs)
    b = dict(a,cycle_index=2)
    assert runner.compare_cycles_v2(a,b)["status"] == "PASS"
    e.compact_cycle_trace()
    snapshot = e.snapshot()
    restored = engine()
    restored.restore(snapshot)
    assert restored.snapshot() == snapshot
    snapshot["configuration_identity"]["initial_state_sha256"] = "0"*64
    with pytest.raises(ValueError):
        restored.restore(snapshot)


def test_atomic_and_explicit_mechanical_selection(tmp_path):
    path = tmp_path/"record.json"
    h = runner.atomic(path,{"a":1})
    assert h == runner.digest({"a":1})
    assert list(tmp_path.glob("*.tmp")) == []
    with pytest.raises(SystemExit):
        runner.parser().parse_args(["--config","a","--output","b","--rpm","9000"])


def test_reject_repository_output():
    args = runner.parser().parse_args(["--config","missing","--output",str(ROOT/"unsafe"),
        "--rpm","9000","--mechanical-loss","undefined"])
    with pytest.raises(ValueError,match="outside repository"):
        runner.run(args)


def test_capture_does_not_change_step():
    a,b = engine(),engine()
    a.step(.01/(6*9000),.01)
    b.step(.01/(6*9000),.01,capture_trace=False)
    assert a.state == b.state
    assert a.ledger == b.ledger


def test_exhausted_deadline_stops_without_physical_step(tmp_path):
    args = runner.parser().parse_args(["--config",str(ROOT/"configs/reference_cases/standard_v1_125cc_blair_cartwright.json"),
        "--output",str(tmp_path/"point"),"--rpm","9000","--wall-seconds","0.001",
        "--mechanical-loss","undefined"])
    assert runner.run(args) == 0
    result=json.loads((tmp_path/"point/manifest.json").read_text())
    assert result["status"] == "TIME_LIMIT_NONCONVERGED"
    assert result["terminal_angle_deg"] == 0
