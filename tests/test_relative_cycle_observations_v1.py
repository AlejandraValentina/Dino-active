from copy import deepcopy
import json
from pathlib import Path
import pytest
from motorsim.integrated_2t import IntegratedEngine2T,_json_evidence_equal
from motorsim.reference_harness.convergence import PeriodicDetectorV2
from scripts.diagnostics.relative_cycle_observations_v1 import relative_observations
from scripts.diagnostics.checkpoint_periodicity_indicators_v1 import cycle_observations
from scripts.diagnostics.remap_representation_v1 import initialize
from scripts.diagnostics.diagnose_integrated_mesh_v1 import sha

ROOT=Path(__file__).resolve().parents[1]/'results/predictive-reliability-v1'


def fixture():
    c=json.loads((ROOT/'spatial-boundary-v2-engine/configuration.json').read_text())
    p=ROOT/'periodicity-extension-v4/run'
    cp={i:json.loads((p/f'checkpoint-{i:03}.json').read_text()) for i in (27,28,29)}
    return c,cp


def test_relative_counter_preserves_physics_and_restarts_detector():
    c,cp=fixture();saved=deepcopy(cp);e=IntegratedEngine2T.from_configuration_dict(c);d=PeriodicDetectorV2()
    a,provenance=relative_observations(e,cp[27],cp[28],27)
    native=cycle_observations(e,cp[27],cp[28],28)
    assert a['observables']==native['observables'] and a['configuration_hash']==native['configuration_hash']
    assert a['cycle_index']==1 and provenance['absolute_cycle_index']==28
    d.update(a);restored=PeriodicDetectorV2(d.snapshot())
    b,_=relative_observations(e,cp[28],cp[29],27)
    assert d.update(b)==restored.update(b)
    assert cp==saved
    with pytest.raises(ValueError,match='origin'):relative_observations(e,cp[27],cp[28],28)
    with pytest.raises(ValueError,match='phases'):relative_observations(e,cp[27],cp[29],27)


def test_actual30_refinement_retains_cross_tdc_combustion_and_clock():
    c,_=fixture();path=ROOT/'periodicity-cycle30-control-v1/run/checkpoint-030.json';cp=json.loads(path.read_text())
    e,f,info=initialize(c,cp,1,'P0',sha(path))
    assert e.crank_angle_unwrapped_deg==10800.
    assert info['inventory_max_relative_error']<2e-14
    assert _json_evidence_equal(e.snapshot()['fuel_combustion'],cp['fuel_combustion'])
    for name,rows in cp['state']['ducts'].items():
        for i,q in enumerate(rows):
            assert e._primitive(e.state['ducts'][name][2*i])==e._primitive(q)
