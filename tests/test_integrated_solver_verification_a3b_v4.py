"""V4 orchestration tests. Synthetic fixtures never represent scientific results.

The real engine is constructed/restored in zero-step tests only. The integration
fixture replaces advancement, producer and auditor to test the reused cycle loop.
"""
import contextlib
import copy
import gzip
import hashlib
import json
from pathlib import Path
import sys
import time
import subprocess
import psutil

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts/diagnostics'))
import integrated_solver_verification_a3b_v4 as v4


@pytest.fixture(scope='module')
def protocol():
    return v4.contract()


@pytest.fixture(scope='module')
def built():
    return v4.executor()._build_configuration('T1-B')


def parent():
    return {'entries': [{'invocation_id': 'historical', 'config_id': 'T1-A',
                         'elapsed_seconds': 530.469, 'reserved_seconds': 0,
                         'cycle_indices': [1, 2, 3], 'status': 'COMPLETE'}]}


def test_budget_includes_inherited_and_supervisor_overhead(protocol, tmp_path):
    ledger = v4.read_ledger(tmp_path, protocol, parent())
    result = v4.budget_report(protocol, ledger)
    assert result['ledger_consumed_seconds'] == pytest.approx(533.142)
    assert result['remaining_seconds'] == pytest.approx(3786.858)
    assert result['projected_total_seconds'] < 4320
    assert sum(v4.CAPS.values()) + result['ledger_consumed_seconds'] < 4320
    assert v4.PLAN['T1-B'] == [1, 1, 1]
    assert v4.INVOCATION_CAPS['T1-C'] == 750


@pytest.mark.parametrize('config', list(v4.CAPS))
def test_impossible_cycle_refused_before_solver(protocol, config, tmp_path):
    bad = copy.deepcopy(protocol)
    bad['planning_envelope_per_cycle_seconds'][config] = 5000
    with pytest.raises(v4.Refused, match='budget|envelope'):
        v4.budget_report(bad, v4.read_ledger(tmp_path, bad, parent()))


def test_negative_nan_duplicate_and_forged_inherited_charge(protocol, tmp_path):
    for value in [-1, float('nan'), float('inf')]:
        with pytest.raises(v4.Refused):
            v4.charge([{'elapsed_seconds': value}])
    ledger = v4.read_ledger(tmp_path, protocol, parent())
    ledger['entries'][0]['elapsed_seconds'] = 0
    v4.atomic(tmp_path / 'a3b-budget-ledger.json', ledger)
    with pytest.raises(v4.Refused, match='V3 charges'):
        v4.read_ledger(tmp_path, protocol, parent())


def test_duplicate_ledger_cycles_refused(protocol, tmp_path):
    ledger = v4.read_ledger(tmp_path, protocol, parent())
    ledger['entries'].append({'config_id': 'T1-B', 'cycle_indices': [1, 1], 'elapsed_seconds': 2})
    with pytest.raises(v4.Refused, match='cycle sequence'):
        v4.budget_report(protocol, ledger)


def primary_fixture(tmp_path):
    path = tmp_path / 'inv01-fixture/cycle-0001.json.gz'
    path.parent.mkdir()
    payload = b'{"synthetic":true}'
    path.write_bytes(gzip.compress(payload))
    row = {'cycle': 1, 'artifact': path.name,
           'primary_sha256': hashlib.sha256(payload).hexdigest(),
           'audit': {'status': 'PASS', 'recomputed': True}}
    return path, row


def test_primary_canonical_integrity_and_duplicates(tmp_path):
    path, row = primary_fixture(tmp_path)
    v4.records_integrity({'records': [row]}, [tmp_path])
    row['audit']['recomputed'] = False
    with pytest.raises(v4.Refused, match='audit'):
        v4.records_integrity({'records': [row]}, [tmp_path])
    row['audit']['recomputed'] = True
    path.write_bytes(gzip.compress(b'altered'))
    with pytest.raises(v4.Refused, match='hash mismatch'):
        v4.records_integrity({'records': [row]}, [tmp_path])
    other = tmp_path / 'inv02-fixture'
    other.mkdir()
    (other / path.name).write_bytes(path.read_bytes())
    with pytest.raises(v4.Refused, match='duplicated'):
        v4.records_integrity({'records': [row]}, [tmp_path])


def test_v4_binding_and_real_zero_step_restore(protocol, built, tmp_path, monkeypatch):
    monkeypatch.setattr(v4, "contract", lambda frozen=False: protocol)
    mod = v4.executor()
    binding = v4.configuration_binding(mod, built, protocol)
    assert binding['driver_sha256'] == v4.sha(v4.HERE)
    assert binding['executor_sha256'] == v4.sha(v4.EXECUTOR)
    worker = v4.configure_worker(tmp_path / 'source', tmp_path / 'output', 'T1-B', 1, tmp_path / 'auth')
    assert worker._binding(built) == binding
    engine = worker.IntegratedEngine2T.from_configuration_dict(built['effective']['native_configuration'])
    snapshot = engine.snapshot()
    engine.restore(copy.deepcopy(snapshot))
    assert worker._json_bytes(engine.snapshot()) == worker._json_bytes(snapshot)
    cp = {'schema': 'DINO_ISV1_A3B_CHECKPOINT_V4', 'bindings': binding,
          'next_cycle': 1, 'records': [], 'engine_snapshot': snapshot,
          'periodicity_snapshot': worker.PeriodicDetectorV2().snapshot()}
    path = tmp_path / 'checkpoint.json'
    v4.atomic(path, cp)
    assert worker._load_checkpoint(path, binding)['next_cycle'] == 1
    bad = copy.deepcopy(binding)
    bad['solver_configuration_sha256'] = '0' * 64
    with pytest.raises(RuntimeError, match='bindings differ'):
        worker._load_checkpoint(path, bad)


@pytest.mark.parametrize('kind,code,reason', [('normal', 0, None), ('failure', 7, None),
                                             ('timeout', None, 'TIMEOUT'),
                                             ('memory', None, 'RESOURCE'),
                                             ('worker_memory', None, 'RESOURCE')])
def test_real_subprocess_supervision_no_solver(tmp_path, kind, code, reason):
    script = ('import time; time.sleep(2)' if kind in ('timeout', 'memory', 'worker_memory')
              else f'import time; time.sleep(1.2); raise SystemExit({code})')
    outcome = v4.bounded_process([sys.executable, '-c', script], tmp_path / 'child.log',
                                time.monotonic() + (0.25 if kind == 'timeout' else 5),
                                aggregate_limit=0 if kind == 'memory' else 4096 * 1024**2,
                                worker_limit=0 if kind == 'worker_memory' else 3072 * 1024**2)
    assert outcome['stop_reason'] == reason
    if code is not None:
        assert outcome['exit_code'] == code


def test_absent_authorization_refuses_before_output_or_process(monkeypatch, tmp_path):
    monkeypatch.setattr(v4, 'contract', lambda frozen=False: {})
    monkeypatch.setattr(v4, 'bounded_process', lambda *a, **k: pytest.fail('must not launch'))
    with pytest.raises(FileNotFoundError):
        v4.run_config(tmp_path / 'source', tmp_path / 'output', 'T1-B', 1, tmp_path / 'absent-auth')
    assert not (tmp_path / 'output').exists()


def test_authorization_exact_scope_and_program_registration(monkeypatch, tmp_path):
    monkeypatch.setattr(v4, 'contract', lambda frozen=False: {})
    monkeypatch.setattr(v4, 'ROOT', tmp_path)
    freeze = tmp_path / 'freeze.json'
    freeze.write_text('{}')
    monkeypatch.setattr(v4, 'FREEZE', freeze)
    source, output = tmp_path / 'source', tmp_path / 'output'
    auth = {'execution_authorized': True, 'protocol_sha256': v4.sha(v4.PROTOCOL),
            'driver_sha256': v4.sha(v4.HERE), 'freeze_sha256': v4.sha(freeze),
            'configs': list(v4.CAPS), 'caps': v4.CAPS, 'invocations': v4.PLAN,
            'invocation_caps': v4.INVOCATION_CAPS, 'global_cap_seconds': 4320.0,
            'source_root': str(source.resolve()), 'artifact_root': str(output.resolve()),
            'owner_confirmation': 'SYNTHETIC TEST ONLY'}
    path = tmp_path / 'auth.json'
    status = tmp_path / 'results/2t-commercial-core-20261002/program-status.json'
    for key in ['protocol_sha256', 'driver_sha256', 'configs', 'caps', 'invocations', 'invocation_caps', 'global_cap_seconds']:
        bad = copy.deepcopy(auth)
        bad[key] = None
        v4.atomic(path, bad)
        with pytest.raises(v4.Refused, match='exact independent'):
            v4.authorization(path, source, output)
    v4.atomic(path, auth)
    v4.atomic(status, {'a3b_v4_execution_authorization': {'sha256': 'wrong', 'execution_authorized': True}})
    with pytest.raises(v4.Refused, match='not registered'):
        v4.authorization(path, source, output)
    v4.atomic(status, {'a3b_v4_execution_authorization': {'sha256': v4.sha(path), 'execution_authorized': True}})
    assert v4.authorization(path, source, output)['execution_authorized'] is True


def test_output_isolation(tmp_path):
    source = tmp_path / 'source'
    for output in [source, source / 'v4', tmp_path]:
        with pytest.raises(v4.Refused):
            v4.check_roots(source, output)
    with pytest.raises(v4.Refused):
        v4.check_roots(source, ROOT / 'results/invalid-runtime-output')


def test_frozen_not_evaluated_cannot_become_converged():
    mod = v4.executor()
    freeze = v4.load(v4.ATOL)
    result = {'config_id': 'SYNTHETIC', 'records': [
        {'cycle': c, 'observables': {'brake_power_w': {'status': 'DEFINED', 'value': 1.0}}}
        for c in [1, 2, 3]]}
    rows = mod._pair_rows(result, result, 'brake_power_w', freeze)
    assert all(r['status'] == 'NOT_EVALUATED' for r in rows)


@pytest.mark.parametrize('failure', [None, 'worker_cycle_2', 'audit_cycle_2'])
def test_reused_cycle_executor_resume_ledger_continuity_no_solver(monkeypatch, tmp_path, protocol, built, failure):
    output = tmp_path / 'output'
    output.mkdir()
    auth = tmp_path / 'auth.json'
    auth.write_text('{}')
    monkeypatch.setattr(v4, 'contract', lambda frozen=False: protocol)
    mod = v4.configure_worker(tmp_path / 'source', output, 'T1-B', 1, auth)
    binding = mod._binding(built)
    monkeypatch.setattr(mod, '_binding', lambda b: binding)
    monkeypatch.setattr(mod, '_build_configuration', lambda c: built)
    monkeypatch.setattr(mod, '_load_authorization', lambda a: {})
    monkeypatch.setattr(mod, '_load_addendum', lambda: {})
    monkeypatch.setattr(mod, 'ADDENDUM', auth)
    monkeypatch.setattr(mod, '_rss_bytes', lambda: 100)
    class Engine:
        def __init__(self):
            self.state = {'cycles': 0, 'combustion_ledger': 0}
        @classmethod
        def from_configuration_dict(cls, native):
            return cls()
        def snapshot(self):
            return copy.deepcopy(self.state)
        def restore(self, state):
            self.state = copy.deepcopy(state)
        def compact_cycle_trace(self):
            pass
    class Detector:
        classification = None
        def snapshot(self):
            return {'synthetic': True}
        def restore(self, snapshot):
            assert snapshot == {'synthetic': True}
        def update(self, value):
            return {}
    def advance(engine, cycle, **kwargs):
        assert engine.state['cycles'] == cycle - 1
        assert engine.state['combustion_ledger'] == cycle - 1
        if failure == 'worker_cycle_2' and cycle == 2:
            raise RuntimeError('synthetic worker failure')
        engine.state['cycles'] = cycle
        engine.state['combustion_ledger'] = cycle
        return []
    @contextlib.contextmanager
    def instrument():
        stats = {}
        mod._reset_stats(stats)
        yield stats, {'seconds': 0.0, 'calls': 0}
    monkeypatch.setattr(mod, 'IntegratedEngine2T', Engine)
    monkeypatch.setattr(mod, 'PeriodicDetectorV2', Detector)
    monkeypatch.setattr(mod, '_advance_cycle', advance)
    monkeypatch.setattr(mod, '_instrumented_engine', instrument)
    monkeypatch.setattr(mod, 'make_integrated_cycle_primary', lambda *a, **k: {
        'configuration_hash': binding['solver_configuration_sha256'], 'admissible': True,
        'observables': {}, 'conservation': {}, 'swept_displacement_m3': 1.0,
        'synthetic_cycle': a[3]})
    monkeypatch.setattr(mod, 'audit_integrated_cycle_primary', lambda primary, **k: {
        'status': 'PASS', 'recomputed': not (failure == 'audit_cycle_2' and primary['synthetic_cycle'] == 2)})
    monkeypatch.setattr(mod, '_prepare_engineering_output_record', lambda p, e: p)
    monkeypatch.setattr(mod, 'make_integrated_engineering_output', lambda *a, **k: {
        'configuration_sha256': binding['solver_configuration_sha256'],
        'schema': 'SYNTHETIC', 'claims': {}, 'cycle_metrics': {}})
    monkeypatch.setattr(mod, '_observable_record', lambda *a: {'status': 'NOT_EVALUATED', 'value': None})
    monkeypatch.setattr(mod, '_selected_primary_observables', lambda p: {})
    for invocation in [1, 2, 3]:
        code = mod._run_config('T1-B', invocation, auth)
        cp = v4.load(output / 'T1-B/checkpoint.json')
        if failure and invocation == 2:
            assert code == 1
            assert cp['next_cycle'] == 2
            assert [r['cycle'] for r in cp['records']] == [1]
            assert cp['engine_snapshot']['combustion_ledger'] == 1
            with pytest.raises(v4.Refused, match='terminal'):
                v4.validate_existing(output, 'T1-B', binding, mod)
            return
        assert code == 0
        assert cp['next_cycle'] == invocation + 1
        assert cp['engine_snapshot']['combustion_ledger'] == invocation
        assert [r['cycle'] for r in cp['records']] == list(range(1, invocation + 1))
    result = v4.load(output / 'T1-B/result.json')
    v4.records_integrity(result, [output / 'T1-B'])
    assert result['status'] == 'COMPLETE'
    hashes_before = [r['primary_sha256'] for r in result['records']]
    assert mod._run_config('T1-B', 3, auth) == 0
    assert [r['primary_sha256'] for r in v4.load(output / 'T1-B/result.json')['records']] == hashes_before
    assert len(v4.load(output / 'a3b-budget-ledger.json')['entries']) == 3


def test_timeout_settlement_does_not_lose_reserved_work(protocol, tmp_path):
    ledger = v4.read_ledger(tmp_path, protocol, parent())
    previous = v4.charge(ledger['entries'])
    ledger['entries'].append({'invocation_id': 'worker', 'config_id': 'T1-C',
                              'elapsed_seconds': 100, 'reserved_seconds': 660,
                              'status': 'RUNNING', 'cycle_indices': []})
    v4.settle(ledger, len(parent()['entries']), 'T1-C', 1, 'supervisor', previous, 730, 'TIMEOUT')
    assert v4.charge(ledger['entries']) == pytest.approx(previous + 740)
    assert ledger['entries'][-2]['status'] == 'PARTIAL_TIMEOUT'
    assert ledger['entries'][-2]['reserved_seconds'] == 0


def test_recover_abrupt_supervisor_preserves_checkpoint_and_full_charge(monkeypatch, protocol, tmp_path):
    monkeypatch.setattr(v4, 'contract', lambda frozen=False: protocol)
    monkeypatch.setattr(v4, 'reference', lambda source, p: ({}, parent()))
    source, output = tmp_path / 'source', tmp_path / 'output'
    ledger = v4.read_ledger(output, protocol, parent())
    previous = v4.charge(ledger['entries'])
    count = len(ledger['entries'])
    ledger['entries'].append({'invocation_id': 'synthetic-worker', 'config_id': 'T1-C',
                              'elapsed_seconds': 100, 'reserved_seconds': 660,
                              'cycle_indices': [], 'status': 'RUNNING'})
    v4.atomic(output / 'a3b-budget-ledger.json', ledger)
    checkpoint = output / 'T1-C/checkpoint.json'
    v4.atomic(checkpoint, {'synthetic': 'do not rewrite'})
    before = v4.sha(checkpoint)
    v4.atomic(output / 'active-invocation.json', {
        'token': 'synthetic-supervisor-not-a-command-token', 'config': 'T1-C',
        'supervisor_pid': 2147483647, 'supervisor_created': 0,
        'protocol_sha256': v4.sha(v4.PROTOCOL), 'driver_sha256': v4.sha(v4.HERE),
        'reservation_seconds': 750, 'previous_charge_seconds': previous,
        'ledger_entry_count': count})
    result = v4.recover(source, output)
    assert result['solver_steps'] == 0
    assert result['accumulated_seconds'] == pytest.approx(previous + 750)
    assert v4.sha(checkpoint) == before
    assert not (output / 'active-invocation.json').exists()


def test_frozen_identity_detects_source_and_driver_changes(protocol, monkeypatch, tmp_path):
    p = copy.deepcopy(protocol)
    dependency = tmp_path / 'dependency.py'
    dependency.write_text('frozen')
    p['repository_inputs'] = {'dependency.py': v4.sha(dependency)}
    protocol_file = tmp_path / 'protocol.json'
    driver = tmp_path / 'driver.py'
    driver.write_text('frozen-driver')
    freeze = tmp_path / 'freeze.json'
    v4.atomic(protocol_file, p)
    v4.atomic(freeze, {'protocol_sha256': v4.sha(protocol_file), 'driver_sha256': v4.sha(driver),
                       'status': 'FROZEN_EXECUTION_NOT_AUTHORIZED'})
    monkeypatch.setattr(v4, 'PROTOCOL', protocol_file)
    monkeypatch.setattr(v4, 'HERE', driver)
    monkeypatch.setattr(v4, 'ROOT', tmp_path)
    monkeypatch.setattr(v4, 'FREEZE', freeze)
    v4.contract(True)
    driver.write_text('altered')
    with pytest.raises(v4.Refused, match='identity mismatch'):
        v4.contract(True)
    dependency.write_text('altered')
    with pytest.raises(v4.Refused, match='dependency changed'):
        v4.contract()


def test_atomic_write_failure_preserves_old_evidence_and_cleans_temp(monkeypatch, tmp_path):
    path = tmp_path / 'checkpoint.json'
    v4.atomic(path, {'original': True})
    before = path.read_bytes()
    def fail(*args):
        raise OSError('synthetic interruption before replace')
    monkeypatch.setattr(v4.os, 'replace', fail)
    with pytest.raises(OSError):
        v4.atomic(path, {'original': False})
    assert path.read_bytes() == before
    assert list(tmp_path.glob('*.tmp')) == []


def test_resource_guard_can_be_inspected_without_authorizing_execution(monkeypatch, tmp_path, protocol):
    from types import SimpleNamespace
    monkeypatch.setattr(v4, 'contract', lambda frozen=False: protocol)
    monkeypatch.setattr(v4, 'reference', lambda source, p: ({'status': 'COMPLETE'}, parent()))
    monkeypatch.setattr(v4, 'executor', lambda: SimpleNamespace(_build_configuration=lambda config: {}))
    monkeypatch.setattr(v4, 'configuration_binding', lambda *a: {})
    monkeypatch.setattr(v4, 'validate_existing', lambda *a: None)
    monkeypatch.setattr(v4.psutil, 'virtual_memory', lambda: SimpleNamespace(available=2000 * 1024**2))
    with pytest.raises(v4.Refused, match='RAM'):
        v4.preflight(tmp_path / 'source', tmp_path / 'output')
    result = v4.preflight(tmp_path / 'source', tmp_path / 'output', structural_only=True)
    assert result['status'] == 'PASS_STRUCTURAL_ONLY'
    assert result['launch_resources_ready'] is False
    assert result['solver_steps'] == 0


@pytest.mark.parametrize('stop_reason', [None, 'TIMEOUT'])
def test_supervisor_complete_lifecycle_and_budget_receipts_no_solver(monkeypatch, tmp_path, protocol, built, stop_reason):
    from types import SimpleNamespace
    p = copy.deepcopy(protocol)
    p['source_inputs'] = {}
    monkeypatch.setattr(v4, 'contract', lambda frozen=False: p)
    monkeypatch.setattr(v4, 'reference', lambda source, p: ({}, parent()))
    monkeypatch.setattr(v4, 'authorization', lambda *a: {'synthetic': True})
    monkeypatch.setattr(v4.psutil, 'virtual_memory', lambda: SimpleNamespace(available=8192 * 1024**2))
    output = tmp_path / 'output'
    source = tmp_path / 'source'
    mod = v4.configure_worker(source, output, 'T1-B', 1, tmp_path / 'auth')
    monkeypatch.setattr(mod, '_build_configuration', lambda c: built)
    monkeypatch.setattr(v4, 'configure_worker', lambda *a: mod)
    binding = mod._binding(built)
    def child(command, log, deadline, **kwargs):
        ledger = v4.load(output / 'a3b-budget-ledger.json')
        entry = {'config_id': 'T1-B', 'invocation_id': 'synthetic-child',
                 'invocation_index': 1, 'elapsed_seconds': 0.01,
                 'reserved_seconds': 330 if stop_reason else 0,
                 'status': 'RUNNING' if stop_reason else 'INVOCATION_COMPLETE_CHECKPOINTED',
                 'cycle_indices': [] if stop_reason else [1]}
        ledger['entries'].append(entry)
        v4.atomic(output / 'a3b-budget-ledger.json', ledger)
        if stop_reason is None:
            folder = output / 'T1-B'
            payload = b'{"synthetic":true}'
            invocation = folder / 'inv01-synthetic'
            invocation.mkdir(parents=True)
            (invocation / 'cycle-0001.json.gz').write_bytes(gzip.compress(payload))
            record = {'cycle': 1, 'artifact': 'cycle-0001.json.gz',
                      'primary_sha256': hashlib.sha256(payload).hexdigest(),
                      'audit': {'status': 'PASS', 'recomputed': True}}
            v4.atomic(invocation / 'invocation.json', {'invocation_id': entry['invocation_id'], 'ledger_entry': entry})
            v4.atomic(folder / 'result.json', {'config_id': 'T1-B', 'bindings': binding,
                                              'records': [record], 'status': entry['status']})
            v4.atomic(folder / 'checkpoint.json', {'schema': 'DINO_ISV1_A3B_CHECKPOINT_V4',
                      'bindings': binding, 'next_cycle': 2, 'records': [record],
                      'engine_snapshot': {'synthetic': True}, 'periodicity_snapshot': {'synthetic': True}})
        return {'exit_code': 124 if stop_reason else 0, 'stop_reason': stop_reason, 'aggregate_peak_bytes': 100}
    monkeypatch.setattr(v4, 'bounded_process', child)
    result = v4.run_config(source, output, 'T1-B', 1, tmp_path / 'auth')
    assert not (output / 'active-invocation.json').exists()
    ledger = v4.read_ledger(output, p, parent())
    assert v4.charge(ledger['entries']) >= 533.142 + 10
    assert result['status'] == ('PARTIAL_TIMEOUT' if stop_reason else 'INVOCATION_COMPLETE_CHECKPOINTED')
    if stop_reason:
        with pytest.raises(v4.Refused, match='terminal'):
            v4.run_config(source, output, 'T1-B', 1, tmp_path / 'auth')
    else:
        ledger['entries'][2]['elapsed_seconds'] = 0
        v4.atomic(output / 'a3b-budget-ledger.json', ledger)
        with pytest.raises(v4.Refused, match='durable invocation receipt'):
            v4.read_ledger(output, p, parent())


def test_real_worker_exits_after_abrupt_parent_death_without_solver(tmp_path):
    pid_file = tmp_path / 'worker.pid'
    # Two fresh Python interpreters on Windows; neither constructs or steps an engine.
    code = """
import subprocess,sys,os,psutil,time
from pathlib import Path
child_code = "import sys; sys.path.insert(0, sys.argv[1]); import integrated_solver_verification_a3b_v4 as v; v.watch_parent(int(sys.argv[2]),float(sys.argv[3]))"
child = subprocess.Popen([sys.executable,'-c',child_code,sys.argv[1],str(os.getpid()),str(psutil.Process().create_time())])
Path(sys.argv[2]).write_text(str(child.pid))
time.sleep(30)
"""
    supervisor = subprocess.Popen([sys.executable, '-c', code,
                                   str(ROOT / 'scripts/diagnostics'), str(pid_file)])
    worker = None
    try:
        deadline = time.monotonic() + 10
        while not pid_file.exists() and time.monotonic() < deadline:
            time.sleep(0.05)
        assert pid_file.exists()
        worker = psutil.Process(int(pid_file.read_text()))
        supervisor.kill()
        supervisor.wait(timeout=5)
        worker.wait(timeout=10)
        assert not worker.is_running()
    finally:
        if supervisor.poll() is None:
            supervisor.kill()
            supervisor.wait(timeout=5)
        if worker is not None and worker.is_running():
            worker.kill()
