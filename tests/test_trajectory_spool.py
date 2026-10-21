"""Bounded trajectory storage tests. Small fixtures are not A3b evidence."""
import json
import multiprocessing
import os
from pathlib import Path
import sys
import time

import pytest

from motorsim._trajectory_store import TrajectorySpool
from motorsim.integrated_2t import (IntegratedEngine2T, _evidence_sha256,
    audit_integrated_cycle_primary, make_integrated_cycle_primary)
from test_integrated_2t import _internal_cycle_fixture, _advance_cycle_fixture


def test_lossless_records_are_not_retained_and_read_in_order(tmp_path):
    # marshal deliberately accepts built-ins only; the engine supplies dicts.
    spool = TrajectorySpool(tmp_path)
    rows = [{'index': i, 'state': (float(i), [None, True, -0.0])} for i in range(50)]
    for row in rows:
        spool.append(row)
    spool.sync()
    assert list(spool) == rows
    assert isinstance(spool[0]['state'], tuple)
    assert spool.index_bytes == 8 * 50
    assert spool[-1] == rows[-1]
    assert spool[2:4] == rows[2:4]
    assert spool[0] is not spool[0]
    spool.close()
    assert not list(tmp_path.iterdir())


def test_append_does_not_retain_the_state_graph(tmp_path):
    spool = TrajectorySpool(tmp_path)
    row = {'state': ([1.0, 2.0], {'species': [3.0, 4.0]})}
    before = sys.getrefcount(row), sys.getrefcount(row['state'])
    spool.append(row)
    assert (sys.getrefcount(row), sys.getrefcount(row['state'])) == before
    row['state'][0][0] = 100.0
    assert spool[0]['state'][0][0] == 1.0
    spool.close()


def test_short_write_poisoned_store_cannot_be_checkpointed(tmp_path, monkeypatch):
    spool = TrajectorySpool(tmp_path)
    spool.append({'valid': 1})
    real_write = spool._file.write
    def short_write(data):
        return real_write(data[:10])
    monkeypatch.setattr(spool._file, 'write', short_write)
    with pytest.raises(OSError, match='short'):
        spool.append({'partial': 2})
    assert len(spool) == 1
    for action in [spool.sync, lambda: spool[0], lambda: spool.append({'new': 3})]:
        with pytest.raises(OSError):
            action()
    spool.close()
    assert not list(tmp_path.iterdir())


def test_corrupt_and_truncated_record_rejected(tmp_path):
    for truncate in [False, True]:
        spool = TrajectorySpool(tmp_path)
        spool.append({'state': (1.0, 2.0)})
        spool.sync()
        if truncate:
            spool._file.truncate(43)
        else:
            spool._file.seek(40)
            spool._file.write(b'X')
        with pytest.raises(ValueError, match='corrupt|incomplete'):
            spool[0]
        assert spool.failed
        spool.close()


def test_sync_failure_is_explicit_and_prevents_snapshot(tmp_path, monkeypatch):
    engine = _internal_cycle_fixture()
    engine.enable_trajectory_spooling(tmp_path)
    _advance_cycle_fixture(engine, 1.0)
    def fail(_):
        raise OSError('injected disk failure')
    monkeypatch.setattr(os, 'fsync', fail)
    with pytest.raises(OSError, match='disk failure'):
        engine.snapshot()
    with pytest.raises(OSError, match='persistence failed'):
        engine.step(1e-5, .01)
    engine.trace.close()


def test_restore_disk_failure_leaves_previous_engine_intact(tmp_path, monkeypatch):
    engine = _internal_cycle_fixture()
    engine.enable_trajectory_spooling(tmp_path)
    before = engine.snapshot()
    candidate = _internal_cycle_fixture()
    _advance_cycle_fixture(candidate, 1.0)
    cp = candidate.snapshot()
    original = TrajectorySpool.sync
    def fail(self):
        raise OSError('restore disk failure')
    monkeypatch.setattr(TrajectorySpool, 'sync', fail)
    with pytest.raises(OSError, match='restore disk failure'):
        engine.restore(cp)
    monkeypatch.setattr(TrajectorySpool, 'sync', original)
    assert engine.snapshot() == before
    engine.trace.close()


def test_real_cycle_primary_audit_and_restore_are_canonically_identical(tmp_path):
    left = _internal_cycle_fixture(open_end_plenum_v2=True)
    right = IntegratedEngine2T.from_configuration_dict(left.configuration_dict())
    right.enable_trajectory_spooling(tmp_path)
    start_left, start_right = left.snapshot(), right.snapshot()
    _advance_cycle_fixture(left, 90.0)
    _advance_cycle_fixture(right, 90.0)
    checkpoint = right.snapshot()
    assert _evidence_sha256(left.snapshot()) == _evidence_sha256(checkpoint)
    restored = IntegratedEngine2T.from_configuration_dict(right.configuration_dict())
    restored.enable_trajectory_spooling(tmp_path)
    restored.restore(json.loads(json.dumps(checkpoint)))
    with pytest.raises(ValueError, match='configuration mismatch'):
        incompatible = _internal_cycle_fixture(rpm=3100.0, open_end_plenum_v2=True)
        incompatible.restore(checkpoint)
    for engine in [left, right, restored]:
        _advance_cycle_fixture(engine, 360.0)
    primaries = [make_integrated_cycle_primary(e, start_left, e.snapshot(), 1)
                 for e in [left, right, restored]]
    assert len({_evidence_sha256(p) for p in primaries}) == 1
    for primary in primaries:
        audit = audit_integrated_cycle_primary(primary)
        assert audit['status'] == 'PASS' and audit['recomputed'] is True
    assert left.conservation_report() == right.conservation_report() == restored.conservation_report()
    old = right.trace
    right.compact_cycle_trace()
    assert old._file.closed and isinstance(right.trace, TrajectorySpool)
    assert len(right.trace) == 0
    right.trace.close()
    restored.trace.close()


def _interrupted_worker(directory, checkpoint_path, ready, during_write):
    engine = _internal_cycle_fixture()
    engine.enable_trajectory_spooling(directory)
    _advance_cycle_fixture(engine, 10.0)
    checkpoint_path.write_text(json.dumps(engine.snapshot()))
    if during_write:
        # Simulate death with an uncommitted record header. No checkpoint
        # references this tail and it is never treated as audited evidence.
        engine.trace._file.seek(engine.trace._end)
        engine.trace._file.write(b'partial-header')
        engine.trace._file.flush()
    else:
        _advance_cycle_fixture(engine, 20.0)
    ready.set()
    time.sleep(30)


@pytest.mark.parametrize('during_write', [False, True])
def test_spawn_interruption_recovers_only_self_contained_checkpoint(tmp_path, during_write):
    ctx = multiprocessing.get_context('spawn')
    ready = ctx.Event()
    checkpoint_path = tmp_path / 'checkpoint.json'
    spool_dir = tmp_path / 'spool'
    spool_dir.mkdir()
    worker = ctx.Process(target=_interrupted_worker,
        args=(spool_dir, checkpoint_path, ready, during_write))
    worker.start()
    try:
        assert ready.wait(20)
    finally:
        worker.terminate()
        worker.join(10)
    assert not worker.is_alive()
    assert not list(spool_dir.iterdir())
    cp = json.loads(checkpoint_path.read_text())
    recovered = _internal_cycle_fixture()
    recovered.enable_trajectory_spooling(spool_dir)
    recovered.restore(cp)
    baseline = _internal_cycle_fixture()
    _advance_cycle_fixture(baseline, 30.0)
    _advance_cycle_fixture(recovered, 30.0)
    assert _evidence_sha256(baseline.snapshot()) == _evidence_sha256(recovered.snapshot())
    assert recovered.accepted_steps == len(recovered.trace)
    recovered.trace.close()
