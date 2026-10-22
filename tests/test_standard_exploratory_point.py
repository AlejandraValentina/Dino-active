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
        "--mechanical-loss","undefined","--memory-mib","128"])
    assert runner.run(args) == 0
    result=json.loads((tmp_path/"point/manifest.json").read_text())
    assert result["status"] == "TIME_LIMIT_NONCONVERGED"
    assert result["terminal_angle_deg"] == 0


def test_explicit_resume_binds_parent_and_restores_without_steps(tmp_path,monkeypatch):
    e=engine(); cfg=e.configuration_dict()
    config=tmp_path/"configuration.json"; config.write_bytes(runner.encode(cfg))
    producer=tmp_path/"old-runner.py";producer.write_bytes(b"frozen parent")
    bindings=dict(configuration_canonical_sha256=runner.digest(cfg),
        configuration_file_sha256=runner.hashlib.sha256(config.read_bytes()).hexdigest(),
        native_configuration_identity=e.configuration_identity,rpm=9000,
        solver_sha256=runner.hashlib.sha256((ROOT/"motorsim/integrated_2t.py").read_bytes()).hexdigest(),
        runner_sha256=runner.hashlib.sha256(producer.read_bytes()).hexdigest())
    cp=dict(bindings=bindings,next_cycle=1,periodicity_history=[],engine_snapshot=e.snapshot())
    cp_hash=runner.atomic(tmp_path/"checkpoint.json",cp)
    parent=dict(schema="DINO_MINIMAL_EXPLORATORY_POINT_V1",status="MAX_CYCLES_NONCONVERGED",
        bindings=bindings,checkpoint_artifact="checkpoint.json",checkpoint_sha256=cp_hash,cycles=[])
    runner.atomic(tmp_path/"manifest.json",parent)
    args=runner.parser().parse_args(["--config",str(config),"--output",str(tmp_path/"new"),
        "--rpm","9000","--mechanical-loss","undefined","--resume-manifest",str(tmp_path/"manifest.json"),
        "--parent-runner",str(producer)])
    monkeypatch.setattr(e,"step",lambda *a,**k:pytest.fail("restore must not execute solver"))
    _,history,streak,receipt=runner.restore_parent(e,cfg,args)
    assert not history and streak==0 and receipt["exact_state_restore"]
    (tmp_path/"checkpoint.json").write_bytes(b"tampered")
    with pytest.raises(ValueError,match="integrity"):
        runner.restore_parent(e,cfg,args)
    parent["bindings"]["rpm"]=3100
    runner.atomic(tmp_path/"manifest.json",parent)
    with pytest.raises(ValueError,match="identity"):
        runner.restore_parent(e,cfg,args)


def test_compacted_restore_preserves_next_physical_step():
    a=engine();a.step(.01/(6*9000),.01);a.compact_cycle_trace()
    b=engine();b.restore(a.snapshot())
    ra=a.step(.01/(6*9000),.01);rb=b.step(.01/(6*9000),.01)
    # Restore normalizes JSON lists/tuples; require exact canonical numbers,
    # not the producer's incidental in-memory sequence container type.
    assert runner.encode(ra)==runner.encode(rb)
    assert runner.encode(a.state)==runner.encode(b.state)
    assert runner.encode(a.ledger)==runner.encode(b.ledger)
