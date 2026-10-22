"""Compare streaming evidence against ordinary JSON and real solver replay."""
from copy import deepcopy
import gzip
import hashlib
import json
import os
import multiprocessing
import random
import time

import pytest

from motorsim._trajectory_store import TrajectorySpool, EvidenceList
from motorsim._evidence_io import (canonical_chunks, canonical_digest,
    read_primary, write_primary_atomic)
from motorsim.integrated_2t import (IntegratedEngine2T, _evidence_sha256,
    make_integrated_cycle_primary, audit_integrated_cycle_primary)
from test_integrated_2t import _internal_cycle_fixture, _advance_cycle_fixture


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def test_workflow_identity_binds_each_streaming_helper(tmp_path, monkeypatch):
    from motorsim import engine_configuration as config
    before = config.implementation_source_hashes()
    assert {'motorsim._evidence_io', 'motorsim._trajectory_store'} <= before.keys()
    original = config.inspect.getsourcefile
    changed = tmp_path/'changed-helper.py'
    changed.write_text('# deliberately incompatible implementation\n')
    def source_file(module):
        if module.__name__ == 'motorsim._evidence_io':
            return str(changed)
        return original(module)
    monkeypatch.setattr(config.inspect, 'getsourcefile', source_file)
    after = config.implementation_source_hashes()
    assert after['motorsim._evidence_io'] != before['motorsim._evidence_io']
    assert {k:v for k,v in after.items() if k != 'motorsim._evidence_io'} == {
        k:v for k,v in before.items() if k != 'motorsim._evidence_io'}


def test_sealed_snapshot_is_stable_after_append_compact_and_close(tmp_path):
    store = TrajectorySpool(tmp_path)
    store.append({'state': (1.0, 2.0)})
    sealed = store.freeze()
    store.append({'state': (3.0, 4.0)})
    assert len(sealed) == 1
    assert list(sealed) == [{'state': [1.0, 2.0]}]
    store.close()
    assert not store._file.closed
    assert list(sealed[:]) == list(sealed)
    del sealed
    assert store._file.closed
    assert not list(tmp_path.iterdir())


def test_sealed_prefix_survives_a_failed_later_write(tmp_path, monkeypatch):
    store = TrajectorySpool(tmp_path)
    store.append({'state': [1.0]})
    sealed = store.freeze()
    monkeypatch.setattr(store._file, 'write', lambda _: 0)
    with pytest.raises(OSError):
        store.append({'state': [2.0]})
    assert list(sealed) == [{'state': [1.0]}]
    store.close()


def test_analysis_clone_isolates_metadata_without_expanding_sealed_rows(tmp_path):
    from motorsim.exploratory_workflow import _copy_primary_for_analysis
    store = TrajectorySpool(tmp_path)
    store.append({'state': [1.0]})
    primary = {'trajectory': store.freeze(), 'checkpoint_binding': {'ledger': [2.0]}}
    clone = _copy_primary_for_analysis(primary)
    assert clone['trajectory'] is primary['trajectory']
    clone['checkpoint_binding']['ledger'][0] = 3.0
    assert primary['checkpoint_binding']['ledger'][0] == 2.0
    assert list(primary['trajectory']) == [{'state': [1.0]}]
    store.close()


@pytest.mark.parametrize('rows', [0, 1, 50])
def test_stream_roundtrip_matches_standard_canonical_and_gzip_bytes(tmp_path, rows):
    store = TrajectorySpool(tmp_path)
    expected = [{'x': i, 'values': [1.25, -0.0, '\u00f1', None, True]} for i in range(rows)]
    for row in expected:
        store.append(row)
    value = {'trajectory': store.freeze(), 'configuration': {'a': 1.2e-200}}
    ordinary = {'trajectory': expected, 'configuration': {'a': 1.2e-200}}
    assert b''.join(canonical_chunks(value)) == canonical(ordinary)
    path = tmp_path/'primary.gz'
    result = write_primary_atomic(path, value, maximum_bytes=1_000_000)
    payload = canonical(ordinary)+b'\n'
    assert path.read_bytes() == gzip.compress(payload, compresslevel=6, mtime=0)
    assert result['primary_sha256'] == hashlib.sha256(payload).hexdigest()
    loaded = read_primary(path, expected_sha256=result['primary_sha256'])
    assert isinstance(loaded['trajectory'], EvidenceList)
    assert canonical_digest(loaded, newline=True) == result['primary_sha256']
    assert deepcopy(loaded) == ordinary
    store.close()


def test_large_record_and_chunk_boundary_numbers(tmp_path):
    value = {'large': 'a'*65500, 'number': 1.2345678901234567e-200,
             'trajectory': [{'record': 'b'*100000, 'n': -2.3e200}]}
    path = tmp_path/'primary.gz'
    result = write_primary_atomic(path, value, maximum_bytes=1_000_000)
    assert deepcopy(read_primary(path, expected_sha256=result['primary_sha256'])) == value
    with pytest.raises(ValueError, match='oversized'):
        read_primary(path, maximum_record_bytes=500)


def test_noncanonical_truncated_corrupt_and_wrong_hash_fail_closed(tmp_path):
    path = tmp_path/'primary.gz'
    for payload in [b'{"x":1,"trajectory":[{}]}\n',
                    b'{"trajectory":[{},]}\n', b'{"trajectory":[{',
                    b'{"trajectory":[],"trajectory":[]}\n']:
        path.write_bytes(gzip.compress(payload, mtime=0))
        with pytest.raises(ValueError):
            read_primary(path)
    result = write_primary_atomic(path, {'trajectory': []}, maximum_bytes=1000)
    with pytest.raises(ValueError, match='hash mismatch'):
        read_primary(path, expected_sha256='0'*64)
    path.write_bytes(path.read_bytes()[:-3])
    with pytest.raises((EOFError, OSError)):
        read_primary(path)


def test_atomic_stream_failure_preserves_old_file_and_cleans_temporary(tmp_path, monkeypatch):
    path = tmp_path/'primary.gz'
    path.write_bytes(b'old-valid-artifact')
    def fail(*_):
        raise OSError('injected interruption')
    monkeypatch.setattr(os, 'replace', fail)
    with pytest.raises(OSError, match='interruption'):
        write_primary_atomic(path, {'trajectory': []}, maximum_bytes=1000)
    assert path.read_bytes() == b'old-valid-artifact'
    assert not list(tmp_path.glob('*.tmp'))


def _interrupted_primary_writer(path, ready):
    class Rows(EvidenceList):
        def __len__(self):
            return 2
        def _get(self, index):
            if index:
                ready.set()
                time.sleep(30)
            rng = random.Random(0)
            return {'data': ''.join(rng.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=100000))}
    write_primary_atomic(path, {'trajectory': Rows()}, maximum_bytes=1_000_000)


def test_spawn_kill_primary_writer_preserves_checkpoint_target_and_quarantines_tail(tmp_path):
    path = tmp_path/'primary.gz'
    previous = write_primary_atomic(path, {'trajectory': []}, maximum_bytes=1_000_000)
    before = path.read_bytes()
    ctx = multiprocessing.get_context('spawn')
    ready = ctx.Event()
    worker = ctx.Process(target=_interrupted_primary_writer, args=(path, ready))
    worker.start()
    try:
        assert ready.wait(20)
        assert list(tmp_path.glob('*.tmp'))
        with pytest.raises(RuntimeError, match='live'):
            write_primary_atomic(path, {'trajectory': []}, maximum_bytes=1_000_000)
    finally:
        worker.terminate()
        worker.join(10)
    assert not worker.is_alive()
    assert path.read_bytes() == before
    read_primary(path, expected_sha256=previous['primary_sha256'])
    write_primary_atomic(path, {'trajectory': [{'x': 1}]}, maximum_bytes=1_000_000)
    assert not list(tmp_path.glob('*.tmp'))
    assert len(list((tmp_path/'_incomplete_evidence').iterdir())) == 1


def test_real_streaming_primary_replay_persistence_and_checkpoint(tmp_path):
    ordinary = _internal_cycle_fixture(open_end_plenum_v2=True)
    streaming = IntegratedEngine2T.from_configuration_dict(ordinary.configuration_dict())
    streaming.enable_trajectory_spooling(tmp_path)
    start = ordinary.snapshot()
    sealed_start = streaming.snapshot(streaming=True)
    for engine in [ordinary, streaming]:
        _advance_cycle_fixture(engine, 90.0)
    cp = streaming.snapshot(streaming=True)
    assert _evidence_sha256(cp) == _evidence_sha256(ordinary.snapshot())
    restored = IntegratedEngine2T.from_configuration_dict(streaming.configuration_dict())
    restored.enable_trajectory_spooling(tmp_path)
    restored.restore(cp)
    for engine in [ordinary, streaming, restored]:
        _advance_cycle_fixture(engine, 360.0)
    materialized = make_integrated_cycle_primary(ordinary, start, ordinary.snapshot(), 1)
    primary = make_integrated_cycle_primary(streaming, sealed_start,
        streaming.snapshot(streaming=True), 1)
    assert isinstance(primary['trajectory'], EvidenceList)
    assert _evidence_sha256(primary) == _evidence_sha256(materialized)
    audit = audit_integrated_cycle_primary(primary)
    assert audit['status'] == 'PASS' and audit['recomputed'] is True
    path = tmp_path/'primary.gz'
    persisted = write_primary_atomic(path, primary, maximum_bytes=10_000_000)
    loaded = read_primary(path, expected_sha256=persisted['primary_sha256'])
    audited = audit_integrated_cycle_primary(loaded)
    assert audited['status'] == 'PASS' and audited['recomputed'] is True
    assert loaded['conservation'] == materialized['conservation']
    restored_primary = make_integrated_cycle_primary(restored, start,
        restored.snapshot(streaming=True), 1)
    assert _evidence_sha256(restored_primary) == _evidence_sha256(primary)
    for engine in [streaming, restored]:
        engine.compact_cycle_trace()
    assert _evidence_sha256(primary) == _evidence_sha256(materialized)
