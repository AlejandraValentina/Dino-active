"""Evidence allocation regressions; synthetic containers are not engine results."""
from copy import deepcopy
import hashlib
import json
import tracemalloc
import weakref

import pytest

from motorsim.integrated_2t import _evidence_sha256, _json_evidence_equal, _jsonify


@pytest.mark.parametrize('value', [[], (), [1, -0.0, '\u00f1', None, True],
    [{'b': (2.0, 3.0), 'a': [False, {'x': 1e-250}]}] * 3])
def test_chunked_hash_is_exact_canonical_json(value):
    expected = hashlib.sha256(json.dumps(value, sort_keys=True,
        separators=(',', ':'), allow_nan=False).encode('utf-8')).hexdigest()
    assert _evidence_sha256(value) == expected


def test_hash_rejects_nonfinite_evidence():
    with pytest.raises(ValueError):
        _evidence_sha256([{'x': float('nan')}])


def test_evidence_helpers_do_not_retain_inputs_after_return():
    class Record(dict):
        pass
    value = Record(state=[1.0, 2.0], species=[.1, .2, .3, .4])
    reference = weakref.ref(value)
    assert _json_evidence_equal(value, deepcopy(value))
    _evidence_sha256([value])
    del value
    # Immediate reference-count release, without gc.collect or a global cache.
    assert reference() is None


def test_comparison_preserves_every_nested_stage_and_species():
    left = {'trajectory': [{'stage': (1.0, 2.0), 'species': [3.0, 4.0]}]}
    right = _jsonify(left)
    assert _json_evidence_equal(left, right)
    assert left == deepcopy(left)
    for candidate in [None, [], {}, {'trajectory': []},
                      {'trajectory': [{'stage': [1.0, 2.0], 'species': [3.0, 4.1]}]}]:
        assert _json_evidence_equal(left, candidate) == (_jsonify(left) == _jsonify(candidate))
        assert _json_evidence_equal(candidate, left) == (_jsonify(candidate) == _jsonify(left))


def _peak(operation):
    tracemalloc.start()
    try:
        result = operation()
        return result, tracemalloc.get_traced_memory()[1]
    finally:
        tracemalloc.stop()


def test_evidence_operations_do_not_allocate_full_trajectory_copies():
    # Unique nested objects, not repeated aliases which could hide allocation.
    rows = [{'state': [[float(i), float(j)] for j in range(32)]} for i in range(400)]
    other = deepcopy(rows)
    old_hash, old_peak = _peak(lambda: hashlib.sha256(json.dumps(rows,
        sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest())
    new_hash, new_peak = _peak(lambda: _evidence_sha256(rows))
    assert new_hash == old_hash
    assert new_peak < old_peak / 4
    old_equal, old_peak = _peak(lambda: _jsonify(rows) == _jsonify(other))
    new_equal, new_peak = _peak(lambda: _json_evidence_equal(rows, other))
    assert old_equal is new_equal is True
    assert new_peak < old_peak / 4
