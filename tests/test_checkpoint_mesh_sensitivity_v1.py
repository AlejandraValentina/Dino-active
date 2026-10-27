from copy import deepcopy
import json
from pathlib import Path
import pytest
from scripts.diagnostics.checkpoint_mesh_sensitivity_v1 import initialize
from scripts.diagnostics.diagnose_integrated_mesh_v1 import sha,restrict_state
from motorsim.integrated_2t import IntegratedEngine2T,_json_evidence_equal

BASE=Path(__file__).resolve().parents[1]/'results/predictive-reliability-v1'


def fixture():
    c=BASE/'spatial-boundary-v2-engine/configuration.json'
    p=BASE/'exhaust-composition-plateau-v1/relaxation-check/checkpoint-025.json'
    return json.loads(c.read_text()),json.loads(p.read_text()),sha(c),sha(p)


def test_new_diagnostic_initialization_is_conservative_and_preserves_thermodynamics():
    config,cp,ch,ph=fixture();saved=deepcopy(cp)
    e,fine,info=initialize(config,cp,True,ch,ph)
    assert cp==saved
    assert info['inventory_max_relative_error']<2e-14
    assert info['restriction_max_relative_error']<2e-14
    assert _json_evidence_equal(e.snapshot()['fuel_combustion'],cp['fuel_combustion'])
    for name,rows in cp['state']['ducts'].items():
        for i,q in enumerate(rows):
            for j in (2*i,2*i+1):assert e._primitive(e.state['ducts'][name][j])==e._primitive(q)
    assert e.crank_angle_unwrapped_deg==9000.


def test_native_cross_mesh_restore_remains_rejected():
    config,cp,ch,ph=fixture();e,fine,_=initialize(config,cp,True,ch,ph)
    with pytest.raises(ValueError,match='configuration mismatch'):e.restore(cp)


def test_original_mesh_is_exact_native_resume():
    config,cp,ch,ph=fixture();e,c,_=initialize(config,cp,False,ch,ph)
    assert c==config and _json_evidence_equal(e.state,cp['state'])
