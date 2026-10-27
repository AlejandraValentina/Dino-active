import json
from pathlib import Path
import pytest
from motorsim.integrated_2t import IntegratedEngine2T,_json_evidence_equal
from motorsim.reference_harness.convergence import PeriodicDetectorV2
from scripts.diagnostics.periodicity_extension_v2 import run

BASE=Path(__file__).resolve().parents[1]/'results/predictive-reliability-v1'


def test_cycle17_checkpoint_and_detector_recover_identical_physical_prefix():
    source=BASE/'periodicity-extension-v1/run'
    e=IntegratedEngine2T.from_configuration_dict(json.loads((BASE/'spatial-boundary-v2-engine/configuration.json').read_text()))
    cp=json.loads((source/'checkpoint-017.json').read_text());e.restore(cp)
    assert _json_evidence_equal(e.state,cp['state']) and _json_evidence_equal(e.ledger,cp['ledger'])
    d=PeriodicDetectorV2(json.loads((source/'detector.json').read_text()))
    assert len(d.history)==17 and d.detected_period is None
    assert e.crank_angle_unwrapped_deg==6120.


def test_bad_checkpoint_digest_stops_before_new_output(tmp_path):
    source=tmp_path/'run';source.mkdir()
    (source/'checkpoint-017.json').write_text('{}')
    (source/'receipt.json').write_text('{}')
    (tmp_path/'manifest.json').write_text(json.dumps({'files':{'run\\checkpoint-017.json':'incorrect'}}))
    output=tmp_path/'new'
    with pytest.raises(ValueError,match='source hash mismatch'):run(source,BASE/'spatial-boundary-v2-engine',output)
    assert not output.exists()
