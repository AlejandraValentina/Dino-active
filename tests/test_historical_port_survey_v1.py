import hashlib
import json

import pytest

from scripts.diagnostics.survey_historical_port_states_v1 import endpoint_coverage, read_verified


@pytest.mark.parametrize('samples', [[], [{}], [{'pressures': {'exhaust': 1e5}}],
    [{'duct_endpoint_primitives': {}}], [{'duct_endpoint_primitives': {'exhaust': [1, 2, 3]}}]])
def test_incomplete_diagnostics_cannot_establish_endpoint_coverage(samples):
    assert not endpoint_coverage(samples)


def test_endpoint_coverage_requires_every_sample():
    good = {'duct_endpoint_primitives': {'exhaust:left': [1., 0., 1e5, .3]}}
    assert endpoint_coverage([good])
    assert not endpoint_coverage([good, {}])


def test_verified_artifact_never_accepts_wrong_hash(tmp_path):
    p = tmp_path/'artifact.json'
    p.write_text(json.dumps({'value': 1}), encoding='utf-8')
    digest = hashlib.sha256(p.read_bytes()).hexdigest()
    assert read_verified(p, digest) == {'value': 1}
    p.write_text('{}', encoding='utf-8')
    with pytest.raises(ValueError, match='hash mismatch'):
        read_verified(p, digest)
