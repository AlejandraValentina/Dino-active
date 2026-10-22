import json
from copy import deepcopy
from pathlib import Path

import pytest
from motorsim.gas_exchange_v2 import validate,outlet_species_rate
from motorsim.integrated_2t import IntegratedEngine2T

ROOT=Path(__file__).resolve().parents[1]
MODEL=dict(schema="GAS_EXCHANGE_V2",intake_control="reed",transfer_crankcase_connection="open_duct_face",
    mixed_outflow_fraction=.5,provenance="SYNTHETIC_ASSUMPTION")


def configuration():
    c=json.loads((ROOT/"configs/reference_cases/standard_v1_125cc_blair_cartwright.json").read_text())
    c["geometry_identity"]["gas_exchange_model"]=deepcopy(MODEL)
    return c


def test_closure_is_bounded_conservative_and_actually_changes_outlet():
    assert validate(MODEL)==MODEL
    state=(.4,.1,.2,.3)
    mixed=outlet_species_rate(.1,state,.01,1)
    biased=outlet_species_rate(.1,state,.01,.5)
    assert sum(biased)==pytest.approx(.1)
    assert biased[0]<mixed[0] and biased[3]>mixed[3]
    for x,y in zip(outlet_species_rate(.9,state,1,0),state):assert 0<=x<=y+1e-15
    with pytest.raises(ValueError):validate(dict(MODEL,mixed_outflow_fraction=2))


def test_reed_has_no_piston_gate_and_roundtrip_is_exact():
    cfg=configuration();e=IntegratedEngine2T.from_configuration_dict(cfg)
    assert e.configuration_dict()==cfg
    assert e._geometry(180).intake_area_m2==e.intake.mesh.areas[-1]
    old=deepcopy(cfg);del old["geometry_identity"]["gas_exchange_model"]
    legacy=IntegratedEngine2T.from_configuration_dict(old)
    assert legacy._geometry(180).intake_area_m2==0
    assert e.configuration_identity!=legacy.configuration_identity


def test_transfers_connected_to_crankcase_with_closed_cylinder_end():
    e=IntegratedEngine2T.from_configuration_dict(configuration())
    e.state["chambers"]["crankcase"]=(e.state["chambers"]["crankcase"][0],
        e.state["chambers"]["crankcase"][1]*1.2,e.state["chambers"]["crankcase"][2])
    rhs=e._assemble(e.state,0,9000,dt_s=1e-7)
    assert rhs["faces"][e.transfers[0].id]["left"][0]!=0
    assert rhs["faces"][e.transfers[0].id]["right"][0]==0
    m,u,v=e.state["chambers"]["crankcase"]
    e.state["chambers"]["crankcase"]=(m,u*.5,v)
    reverse=e._assemble(e.state,0,9000,dt_s=1e-7)
    assert reverse["faces"][e.transfers[0].id]["left"][0]<0


def test_reed_pressure_sign_and_native_step_conservation():
    e=IntegratedEngine2T.from_configuration_dict(configuration())
    for _ in range(20):e.step(.01/(6*9000),.01)
    report=e.conservation_report()
    assert abs(report["mass"]["residual"])<1e-12
    assert abs(report["energy"]["residual"])<1e-8
    assert max(abs(s["residual"]) for s in report["species"].values())<1e-12
    e.compact_cycle_trace();snapshot=e.snapshot()
    restored=IntegratedEngine2T.from_configuration_dict(configuration());restored.restore(snapshot)
    assert restored.snapshot()==snapshot


def test_scavenging_changes_actual_stage_outflow_not_only_postprocessing():
    e=IntegratedEngine2T.from_configuration_dict(configuration())
    m,u,v=e.state["chambers"]["cylinder"]
    e.state["chambers"]["cylinder"]=(m,u*2,v)
    rhs=e._assemble(e.state,140,9000,dt_s=1e-7)
    face=rhs["faces"][e.exhaust.id]
    assert face["left"][0]>0
    assert sum(face["left_species"])==pytest.approx(face["left"][0])
    assert sum(face["left_species"][:2])/face["left"][0] < .5
    before=e._assemble(e.state,90,9000,dt_s=1e-7)["faces"][e.exhaust.id]
    assert sum(before["left_species"][:2])/before["left"][0]==pytest.approx(.5)
