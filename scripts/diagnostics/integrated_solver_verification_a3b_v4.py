"""Forward A3b executor. Reuses the immutable V2 scientific cycle pipeline.

Only ``run-config`` (and its supervised private worker) can advance the solver.
Preflight, freeze and analysis never call the solver. V2/V3 are read-only inputs.
"""
from __future__ import annotations

import argparse
import copy
import gzip
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import threading
import time
import uuid

import psutil

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
HERE = Path(__file__).resolve()
RESULTS = ROOT / 'results/integrated-solver-verification-v1'
PROTOCOL = RESULTS / 'a3b-preregistration-v4.json'
FREEZE = RESULTS / 'a3b-preregistration-v4-freeze.json'
ATOL = RESULTS / 'a3b-analysis-freeze-v3.json'
EXECUTOR = HERE.with_name('integrated_solver_verification_a3b.py')
GLOBAL_CAP = 4320.0
CAPS = {'T1-B': 1050.0, 'T1-C': 2100.0, 'T1-D': 310.0, 'T1-E': 210.0}
PLAN = {'T1-B': [1, 1, 1], 'T1-C': [1, 1, 1], 'T1-D': [3], 'T1-E': [3]}
INVOCATION_CAPS = {'T1-B': 600.0, 'T1-C': 750.0, 'T1-D': 600.0, 'T1-E': 600.0}
CLOSURE = 10.0
INVOCATION_OVERHEAD = 20.0
HISTORICAL_OVERHEAD = 2.673  # 1.188 s V2 wrapper + 1.485 s V3 wrapper
TERMINAL = {'FAILED_CLOSED', 'PARTIAL_BUDGET', 'INTERRUPTED_CHECKPOINTED',
            'INTERRUPTED_ACCOUNTED', 'PARTIAL_TIMEOUT', 'PARTIAL_RESOURCE',
            'PARTIAL_WORKER_FAILURE', 'PARTIAL_CANCELLED'}


class Refused(RuntimeError):
    pass


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def atomic(path, value, payload=None):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    try:
        with tmp.open('xb') as out:
            out.write(payload if payload is not None else json.dumps(
                value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode())
            out.flush()
            os.fsync(out.fileno())
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


def executor():
    # A fresh module namespace avoids altering the imported historical module.
    spec = importlib.util.spec_from_file_location('_a3b_v4_cycle_executor', EXECUTOR)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def contract(frozen=False):
    p = load(PROTOCOL)
    if (p['caps'] != CAPS or p['invocations'] != PLAN or
            p['invocation_caps'] != INVOCATION_CAPS or
            p['global_cap_seconds'] != GLOBAL_CAP or p['closure_seconds'] != CLOSURE or
            p['planning_overhead_per_invocation_seconds'] != INVOCATION_OVERHEAD):
        raise Refused('operational contract differs from this driver')
    for relative, expected in p['repository_inputs'].items():
        if sha(ROOT / relative) != expected:
            raise Refused('repository dependency changed: ' + relative)
    if frozen:
        f = load(FREEZE)
        if (f['protocol_sha256'] != sha(PROTOCOL) or f['driver_sha256'] != sha(HERE)
                or f['status'] != 'FROZEN_EXECUTION_NOT_AUTHORIZED'):
            raise Refused('frozen protocol/driver identity mismatch')
    return p


def check_roots(source, output):
    source, output = Path(source).resolve(), Path(output).resolve()
    from motorsim.desktop.preferences import repository_root_containing
    if (repository_root_containing(output) is not None or output == source or
            source in output.parents or output in source.parents):
        raise Refused('output must be external and isolated from the V2/V3 source')
    return source, output


def charge(entries):
    total = 0.0
    for row in entries:
        values = [float(row.get(k, 0.0)) for k in ('elapsed_seconds', 'reserved_seconds')]
        if any(not math.isfinite(v) or v < 0 for v in values):
            raise Refused('invalid ledger charge')
        total += max(values)
    return total


def records_integrity(result, directories):
    records = result['records']
    cycles = [r['cycle'] for r in records]
    if cycles != list(range(1, len(records) + 1)) or len(records) > 3:
        raise Refused('missing, duplicated or out-of-order cycles')
    for rec in records:
        if (rec['audit'].get('status') != 'PASS' or
                rec['audit'].get('recomputed') is not True):
            raise Refused('cycle lacks independent recomputed audit PASS')
        name = rec['artifact']
        if Path(name).name != name:
            raise Refused('invalid primary path')
        found = [p for directory in directories for p in directory.glob('inv*/' + name)]
        if len(found) != 1:
            raise Refused('primary missing or duplicated: ' + name)
        if hashlib.sha256(gzip.decompress(found[0].read_bytes())).hexdigest() != rec['primary_sha256']:
            raise Refused('canonical primary hash mismatch')


def reference(source, p):
    for relative, expected in p['source_inputs'].items():
        if sha(source / relative) != expected:
            raise Refused('historical evidence changed: ' + relative)
    result = load(source / 'T1-A/v3/result.json')
    cp = load(source / 'T1-A/v3/checkpoint.json')
    if (result['status'] != 'COMPLETE' or result['cycle_indices'] != [1, 2, 3]
            or cp['next_cycle'] != 4 or cp['bindings'] != result['bindings']
            or [r['cycle'] for r in cp['records']] != [1, 2, 3]):
        raise Refused('V3 reference is not the complete three-cycle base')
    records_integrity(result, [source / 'T1-A', source / 'T1-A/v3'])
    parent = load(source / 'a3b-budget-ledger-v3.json')
    spent = charge(parent['entries'])
    if abs(spent - p['inherited_ledger_seconds']) > 1e-6:
        raise Refused('V3 ledger charge changed')
    freeze = load(ATOL)
    if (freeze['status'] != 'FROZEN_BEFORE_COMPARISON' or
            freeze['t1a_result_sha256'] != sha(source / 'T1-A/v3/result.json')):
        raise Refused('atol freeze does not bind the reference')
    return result, parent


def read_ledger(output, p, parent):
    path = output / 'a3b-budget-ledger.json'
    if path.exists():
        ledger = load(path)
        if (ledger.get('protocol_sha256') != sha(PROTOCOL) or
                ledger.get('schema') != 'DINO_ISV1_A3B_BUDGET_LEDGER_V4'):
            raise Refused('V4 ledger protocol mismatch')
        if ledger.get('inherited_entries') != parent['entries']:
            raise Refused('inherited ledger entries changed')
        if ledger['entries'][:len(parent['entries'])] != parent['entries']:
            raise Refused('V3 charges missing or modified')
    else:
        ledger = {'schema': 'DINO_ISV1_A3B_BUDGET_LEDGER_V4',
                  'protocol_sha256': sha(PROTOCOL),
                  'inherited_entries': copy.deepcopy(parent['entries']),
                  'entries': copy.deepcopy(parent['entries']) + [{
                      'config_id': 'HISTORICAL_SUPERVISION', 'status': 'COMPLETE',
                      'elapsed_seconds': HISTORICAL_OVERHEAD, 'reserved_seconds': 0.0,
                      'invocation_id': 'historical-wrapper-overhead'}]}
    expected_overhead = {'config_id': 'HISTORICAL_SUPERVISION', 'status': 'COMPLETE',
                         'elapsed_seconds': HISTORICAL_OVERHEAD, 'reserved_seconds': 0.0,
                         'invocation_id': 'historical-wrapper-overhead'}
    if ledger['entries'][len(parent['entries'])] != expected_overhead:
        raise Refused('historical supervision charge changed')
    if len({e['invocation_id'] for e in ledger['entries']}) != len(ledger['entries']):
        raise Refused('duplicate ledger entry')
    charge(ledger['entries'])
    if path.exists() and not (output / 'active-invocation.json').exists():
        for entry in ledger['entries'][len(parent['entries']) + 1:]:
            config = entry.get('config_id')
            if config not in CAPS:
                raise Refused('unknown forward ledger configuration')
            if entry.get('status') in TERMINAL:
                continue  # terminal configurations cannot execute again
            if entry.get('status') == 'SUPERVISION_OVERHEAD':
                receipt = load(output / f"{config}-inv{entry['invocation_index']:02d}-supervisor.json")
                if (receipt.get('token') != entry['invocation_id'] or
                        receipt.get('overhead_charged_seconds') != entry['elapsed_seconds']):
                    raise Refused('supervisor budget receipt mismatch')
            else:
                receipts = [load(p) for p in (output / config).glob('inv*/invocation.json')]
                matches = [r for r in receipts if r.get('invocation_id') == entry['invocation_id']]
                if len(matches) != 1 or matches[0].get('ledger_entry') != entry:
                    raise Refused('worker ledger differs from durable invocation receipt')
    return ledger


def configuration_binding(mod, built, p):
    binding = mod._binding(built)
    actual = {k: v for k, v in binding.items() if k not in ('protocol_sha256', 'driver_sha256')}
    if actual != p['scientific_bindings'][built['config_id']]:
        raise Refused('scientific configuration/source binding changed')
    binding.update(protocol_sha256=sha(PROTOCOL), driver_sha256=sha(HERE),
                   executor_sha256=sha(EXECUTOR), reference_result_sha256=p['reference_result_sha256'],
                   analysis_freeze_sha256=sha(ATOL))
    return binding


def validate_existing(output, config, binding, mod):
    folder = output / config
    cp = folder / 'checkpoint.json'
    result_path = folder / 'result.json'
    result = load(result_path) if result_path.exists() else None
    if result:
        if result.get('bindings') != binding or result.get('config_id') != config:
            raise Refused('result identity mismatch')
        records_integrity(result, [folder])
        if result.get('status') in TERMINAL:
            raise Refused('terminal invocation cannot be retried automatically')
    if cp.exists():
        checkpoint = mod._load_checkpoint(cp, binding)
        records_integrity(checkpoint, [folder])
        if not result or [r['primary_sha256'] for r in result['records']] != [
                r['primary_sha256'] for r in checkpoint['records']]:
            raise Refused('result/checkpoint disagree; recovery must preserve both')
        return checkpoint
    if result or (folder.exists() and any(folder.iterdir())):
        raise Refused('partial directory has no validated checkpoint')
    return None


def budget_report(p, ledger, config=None):
    spent = charge(ledger['entries'])
    config_spent = {c: charge([e for e in ledger['entries'] if e.get('config_id') == c]) for c in CAPS}
    envelopes = p['planning_envelope_per_cycle_seconds']
    projected = spent
    for c in CAPS:
        cycles = [v for e in ledger['entries'] if e.get('config_id') == c
                  for v in e.get('cycle_indices', [])]
        if cycles != list(range(1, len(cycles) + 1)) or len(cycles) > 3:
            raise Refused('invalid ledger cycle sequence for ' + c)
        completed = len(cycles)
        remaining = max(0, 3 - completed)
        invocations = remaining if c in ('T1-B', 'T1-C') else int(remaining > 0)
        estimate = remaining * envelopes[c] + invocations * INVOCATION_OVERHEAD
        projected += estimate
        if config_spent[c] + estimate > CAPS[c]:
            raise Refused(c + ' full remaining horizon exceeds configuration budget')
        if envelopes[c] + INVOCATION_OVERHEAD > INVOCATION_CAPS[c]:
            raise Refused(c + ' cycle cannot fit its invocation envelope')
    if projected > GLOBAL_CAP:
        raise Refused('full remaining matrix envelope exceeds accumulated global budget')
    return {'ledger_consumed_seconds': spent, 'remaining_seconds': GLOBAL_CAP - spent,
            'projected_total_seconds': projected, 'projected_margin_seconds': GLOBAL_CAP - projected,
            'per_config_consumed_seconds': config_spent}


def preflight(source, output, frozen=False, structural_only=False):
    p = contract(frozen)
    source, output = check_roots(source, output)
    ref, parent = reference(source, p)
    if (output / 'active-invocation.json').exists():
        raise Refused('unclosed supervisor; run recover without solver first')
    mod = executor()
    mod.CHECKPOINT_SCHEMA = 'DINO_ISV1_A3B_CHECKPOINT_V4'
    configs = []
    for config in CAPS:
        built = mod._build_configuration(config)
        binding = configuration_binding(mod, built, p)
        checkpoint = validate_existing(output, config, binding, mod)
        if checkpoint:
            engine = mod.IntegratedEngine2T.from_configuration_dict(built['effective']['native_configuration'])
            engine.restore(checkpoint['engine_snapshot'])  # restore only, no step
        configs.append({'config': config, 'solver_steps': 0, 'status': 'PASS',
                        'binding': binding, 'next_cycle': checkpoint['next_cycle'] if checkpoint else 1})
    ledger = read_ledger(output, p, parent)
    if ledger.get('last_supervised_status') in TERMINAL:
        raise Refused('terminal campaign status; new authorization required')
    budget = budget_report(p, ledger)
    available = psutil.virtual_memory().available / 1024**2
    if available < 4096 and not structural_only:
        raise Refused('4096 MiB free RAM required before scientific execution')
    return {'status': 'PASS_STRUCTURAL_ONLY' if structural_only else 'PASS',
            'launch_resources_ready': available >= 4096,
            'launch_preflight_required': True, 'solver_steps': 0, 'configs': configs, 'budget': budget,
            'memory': {'available_mib': available, 'aggregate_cap_mib': 4096,
                       'worker_cap_mib': 3072, 'workers': 1},
            'reference': {'status': ref['status'], 'next_cycle': 4},
            'protocol_sha256': sha(PROTOCOL), 'driver_sha256': sha(HERE)}


def authorization(path, source, output):
    contract(True)
    auth = load(path)
    expected = {'execution_authorized': True, 'protocol_sha256': sha(PROTOCOL),
                'driver_sha256': sha(HERE), 'freeze_sha256': sha(FREEZE),
                'configs': list(CAPS), 'caps': CAPS, 'invocations': PLAN,
                'invocation_caps': INVOCATION_CAPS, 'global_cap_seconds': GLOBAL_CAP,
                'source_root': str(Path(source).resolve()), 'artifact_root': str(Path(output).resolve())}
    if any(auth.get(k) != v for k, v in expected.items()) or not auth.get('owner_confirmation'):
        raise Refused('missing exact independent execution authorization')
    status = load(ROOT / 'results/2t-commercial-core-20261002/program-status.json')
    registered = status.get('a3b_v4_execution_authorization', {})
    if registered.get('sha256') != sha(path) or registered.get('execution_authorized') is not True:
        raise Refused('execution authorization not registered in program-status')
    return auth


def terminate_tree(process):
    try:
        parent = psutil.Process(process.pid)
        children = parent.children(recursive=True)
        for child in reversed(children):
            try:
                child.kill()
            except psutil.NoSuchProcess:
                pass
        parent.kill()
        psutil.wait_procs(children + [parent], timeout=3)
    except psutil.NoSuchProcess:
        pass
    process.wait(timeout=5)


def watch_parent(pid, created):
    while True:
        try:
            same_parent = psutil.Process(pid).create_time() == created
        except psutil.NoSuchProcess:
            same_parent = False
        if not same_parent:
            os._exit(125)  # last atomic complete-cycle checkpoint remains authoritative
        time.sleep(0.2)


def bounded_process(command, log, deadline, aggregate_limit=4096 * 1024**2,
                    on_start=None, worker_limit=3072 * 1024**2):
    peak = 0
    worker_peak = 0
    reason = None
    with Path(log).open('w', encoding='utf-8') as stream:
        child = subprocess.Popen(command, stdout=stream, stderr=subprocess.STDOUT)
        try:
            if on_start:
                on_start(child.pid)
            while child.poll() is None:
                try:
                    processes = [psutil.Process(child.pid)]
                    processes += processes[0].children(recursive=True)
                    worker_rss = [proc.memory_info().rss for proc in processes if proc.is_running()]
                    worker_peak = max([worker_peak] + worker_rss)
                    rss = psutil.Process().memory_info().rss + sum(worker_rss)
                    peak = max(peak, rss)
                    if rss > aggregate_limit or worker_peak > worker_limit:
                        reason = 'RESOURCE'
                except psutil.NoSuchProcess:
                    pass
                if time.monotonic() >= deadline:
                    reason = 'TIMEOUT'
                if reason:
                    terminate_tree(child)
                    break
                time.sleep(0.1)
        except KeyboardInterrupt:
            reason = 'CANCELLED'
            terminate_tree(child)
        except BaseException:
            if child.poll() is None:
                terminate_tree(child)
            raise
    return {'exit_code': child.returncode, 'stop_reason': reason,
            'aggregate_peak_bytes': peak, 'worker_peak_bytes': worker_peak}


def configure_worker(source, output, config, invocation, auth_path):
    if config not in CAPS or not 1 <= invocation <= len(PLAN[config]):
        raise Refused('worker outside forward config/invocation plan')
    p = contract(True)
    mod = executor()
    original_binding = mod._binding
    original_checkpoint = mod._load_checkpoint
    mod.PROTOCOL = PROTOCOL
    mod.PROTOCOL_SHA256 = sha(PROTOCOL)
    mod.ADDENDUM = FREEZE
    mod.LEDGER_SCHEMA = 'DINO_ISV1_A3B_BUDGET_LEDGER_V4'
    mod.CHECKPOINT_SCHEMA = 'DINO_ISV1_A3B_CHECKPOINT_V4'
    mod.RESULT_SCHEMA = 'DINO_ISV1_A3B_CONFIG_RESULT_V4'
    mod.INVOCATION_SCHEMA = 'DINO_ISV1_A3B_INVOCATION_V4'
    mod.CONFIG_SPECS = copy.deepcopy(mod.CONFIG_SPECS)
    for c in CAPS:
        mod.CONFIG_SPECS[c]['cap_seconds'] = CAPS[c]
    mod.INVOCATION_PLAN = PLAN
    mod.PER_INVOCATION_CAP_SECONDS = INVOCATION_CAPS[config]
    mod.INTERNAL_INVOCATION_DEADLINE_SECONDS = INVOCATION_CAPS[config] - 2 * CLOSURE
    mod._artifact_root = lambda: output
    mod._load_protocol = lambda: p
    mod._load_addendum = lambda: load(FREEZE)
    mod._load_authorization = lambda path: authorization(path, source, output)
    def binding(built):
        raw = original_binding(built)
        scientific = {k: v for k, v in raw.items() if k not in ('driver_sha256', 'protocol_sha256')}
        if scientific != p['scientific_bindings'][built['config_id']]:
            raise Refused('scientific binding mismatch in worker')
        raw.update(driver_sha256=sha(HERE), protocol_sha256=sha(PROTOCOL),
                   executor_sha256=sha(EXECUTOR), reference_result_sha256=p['reference_result_sha256'],
                   analysis_freeze_sha256=sha(ATOL))
        return raw
    mod._binding = binding
    mod._validate_identity = lambda protocol, built: binding(built)
    def checkpoint(path, expected):
        obj = original_checkpoint(path, expected)
        if obj:
            records_integrity(obj, [Path(path).parent])
        return obj
    mod._load_checkpoint = checkpoint
    def reserve(ledger, entry, cid, elapsed):
        need = p['planning_envelope_per_cycle_seconds'][cid] + CLOSURE
        base = max(elapsed, entry.get('elapsed_seconds', 0))
        if base + need > INVOCATION_CAPS[cid]:
            raise mod.BudgetExhausted('whole audited cycle cannot fit remaining invocation')
        entry['reserved_seconds'] = base + need
        if charge(ledger['entries']) > GLOBAL_CAP or mod._ledger_config_spent(ledger, cid) > CAPS[cid]:
            entry['reserved_seconds'] = base
            raise mod.BudgetExhausted('whole audited cycle exceeds accumulated budget')
        return need
    mod._reserve_next_cycle = reserve
    mod._write_json = lambda path, value: atomic(path, value, mod._json_bytes(value))
    original_audit = mod.audit_integrated_cycle_primary
    def audit(primary, **kwargs):
        evidence = original_audit(primary, **kwargs)
        if evidence.get('status') != 'PASS' or evidence.get('recomputed') is not True:
            raise mod.Refused('independent audit did not recompute PASS')
        return evidence
    mod.audit_integrated_cycle_primary = audit
    return mod


def settle(ledger, inherited_count, config, invocation, token, previous_spent, elapsed, reason):
    """Settle stale child reservations against inclusive supervisor wall time."""
    for row in ledger['entries'][inherited_count + 1:]:
        if row.get('config_id') == config and row.get('status') == 'RUNNING':
            row['reserved_seconds'] = 0.0
            row['status'] = 'PARTIAL_' + (reason or 'WORKER_FAILURE')
    new_charge = charge(ledger['entries']) - previous_spent
    overhead = max(0.0, elapsed + CLOSURE - new_charge)
    ledger['entries'].append({'config_id': config, 'invocation_id': token,
                              'invocation_index': invocation, 'cycle_indices': [],
                              'elapsed_seconds': overhead, 'reserved_seconds': 0.0,
                              'status': 'SUPERVISION_OVERHEAD'})


def run_config(source, output, config, invocation, auth_path):
    started = time.monotonic()
    p = contract(True)
    source, output = check_roots(source, output)
    authorization(auth_path, source, output)  # before any output directory/solver
    if config not in CAPS or not 1 <= invocation <= len(PLAN[config]):
        raise Refused('config/invocation outside authorized forward plan')
    _, parent = reference(source, p)
    if psutil.virtual_memory().available < 4096 * 1024**2:
        raise Refused('4096 MiB free RAM required')
    output.mkdir(parents=True, exist_ok=True)
    lockmod = executor()
    with lockmod._exclusive_run_lock(output / 'supervisor'):
        active_path = output / 'active-invocation.json'
        if active_path.exists():
            raise Refused('unclosed supervisor state: preserve reservation; no automatic retry')
        ledger = read_ledger(output, p, parent)
        if ledger.get('last_supervised_status') in TERMINAL:
            raise Refused('campaign reached terminal status')
        if any(e.get('status') in TERMINAL and e.get('config_id') in CAPS for e in ledger['entries']):
            raise Refused('campaign has a terminal failure; automatic continuation prohibited')
        mod = configure_worker(source, output, config, invocation, auth_path)
        built = mod._build_configuration(config)
        binding = mod._binding(built)
        cp = validate_existing(output, config, binding, mod)
        next_cycle = cp['next_cycle'] if cp else 1
        if next_cycle == 4:
            return {'status': 'COMPLETE_REUSED', 'solver_steps': 0}
        expected_start = 1 + sum(PLAN[config][:invocation - 1])
        if next_cycle != expected_start:
            raise Refused('invocation number does not match checkpoint cycle')
        budget = budget_report(p, ledger)
        remaining_config = CAPS[config] - budget['per_config_consumed_seconds'][config]
        total_cap = min(INVOCATION_CAPS[config], remaining_config, budget['remaining_seconds'])
        setup_elapsed = time.monotonic() - started
        need = p['planning_envelope_per_cycle_seconds'][config] * PLAN[config][invocation - 1] + CLOSURE
        if setup_elapsed + need + CLOSURE > total_cap:
            raise Refused('setup plus complete audited invocation and closure do not fit')
        atomic(output / 'a3b-budget-ledger.json', ledger)
        token = uuid.uuid4().hex
        active = {'token': token, 'config': config, 'invocation': invocation,
                  'supervisor_pid': os.getpid(), 'reservation_seconds': total_cap,
                  'supervisor_created': psutil.Process().create_time(),
                  'ledger_entry_count': len(ledger['entries']),
                  'protocol_sha256': sha(PROTOCOL), 'driver_sha256': sha(HERE),
                  'previous_charge_seconds': budget['ledger_consumed_seconds']}
        atomic(active_path, active)
        command = [sys.executable, str(HERE), '_worker', '--source-root', str(source),
                   '--artifact-root', str(output), '--config', config, '--invocation', str(invocation),
                   '--authorization', str(auth_path.resolve()), '--token', token]
        def launched(pid):
            active['child_pid'] = pid
            active['child_created'] = psutil.Process(pid).create_time()
            atomic(active_path, active)
        outcome = bounded_process(command, output / f'{config}-inv{invocation:02d}.log',
                                  started + total_cap - CLOSURE, on_start=launched)
        ledger = read_ledger(output, p, parent)
        elapsed = time.monotonic() - started
        settle(ledger, len(parent['entries']), config, invocation, token,
               budget['ledger_consumed_seconds'], elapsed, outcome['stop_reason'])
        if outcome['stop_reason'] or outcome['exit_code']:
            status = 'PARTIAL_' + (outcome['stop_reason'] or 'WORKER_FAILURE')
            result_path = output / config / 'result.json'
            if not outcome['stop_reason'] and result_path.exists():
                result = load(result_path)
                if result.get('bindings') == binding and result.get('status') in TERMINAL:
                    status = result['status']
                    outcome['scientific_failure'] = result.get('failure')
        else:
            status = load(output / config / 'result.json')['status']
            if status not in TERMINAL:
                validate_existing(output, config, binding, mod)
        for relative, expected in p['source_inputs'].items():
            if sha(source / relative) != expected:
                status = 'FAILED_CLOSED'
                outcome['source_integrity_error'] = relative
        ledger['last_supervised_status'] = status
        atomic(output / 'a3b-budget-ledger.json', ledger)
        outcome.update(status=status, elapsed_seconds=elapsed,
                       accumulated_seconds=charge(ledger['entries']), token=token,
                       overhead_charged_seconds=ledger['entries'][-1]['elapsed_seconds'])
        atomic(output / f'{config}-inv{invocation:02d}-supervisor.json', outcome)
        active_path.unlink()
        return outcome


def recover(source, output):
    """Account an interrupted supervisor without executing or replaying a cycle."""
    p = contract(True)
    source, output = check_roots(source, output)
    _, parent = reference(source, p)
    mod = executor()
    with mod._exclusive_run_lock(output / 'supervisor'):
        path = output / 'active-invocation.json'
        active = load(path)
        if active.get('protocol_sha256') != sha(PROTOCOL) or active.get('driver_sha256') != sha(HERE):
            raise Refused('interrupted supervisor identity mismatch')
        try:
            if psutil.Process(active['supervisor_pid']).create_time() == active['supervisor_created']:
                raise Refused('supervisor still exists; recovery refused')
        except psutil.NoSuchProcess:
            pass
        pid = active.get('child_pid')
        if pid and psutil.pid_exists(pid):
            if psutil.Process(pid).create_time() == active.get('child_created'):
                raise Refused('worker still exists; stop it before recovery')
        if not pid:
            for process in psutil.process_iter(['cmdline']):
                if active['token'] in (process.info['cmdline'] or []):
                    raise Refused('unrecorded worker still exists; wait for parent watchdog')
        ledger = read_ledger(output, p, parent)
        if abs(charge(ledger['entries'][:active['ledger_entry_count']]) - active['previous_charge_seconds']) > 1e-6:
            raise Refused('interrupted supervisor ledger prefix changed')
        if not 0 < active['reservation_seconds'] <= INVOCATION_CAPS[active['config']]:
            raise Refused('interrupted reservation invalid')
        for entry in ledger['entries'][len(parent['entries']) + 1:]:
            if entry.get('status') == 'RUNNING':
                entry['elapsed_seconds'] = max(entry.get('elapsed_seconds', 0),
                                               entry.get('reserved_seconds', 0))
                entry['reserved_seconds'] = 0.0
                entry['status'] = 'INTERRUPTED_ACCOUNTED'
        target = active['previous_charge_seconds'] + active['reservation_seconds']
        missing = max(0.0, target - charge(ledger['entries']))
        row = next((e for e in ledger['entries'] if e['invocation_id'] == active['token']), None)
        if row is None:
            row = {'config_id': active['config'], 'invocation_id': active['token'],
                   'cycle_indices': [], 'elapsed_seconds': 0.0, 'reserved_seconds': 0.0}
            ledger['entries'].append(row)
        row['elapsed_seconds'] += missing
        row['status'] = 'INTERRUPTED_ACCOUNTED'
        ledger['last_supervised_status'] = 'INTERRUPTED_ACCOUNTED'
        atomic(output / 'a3b-budget-ledger.json', ledger)
        active['recovery'] = 'FULL_RESERVATION_CONSERVATIVELY_CHARGED_NO_RETRY'
        atomic(output / (active['token'] + '-recovery.json'), active)
        path.unlink()
        return {'status': 'INTERRUPTED_ACCOUNTED', 'solver_steps': 0,
                'accumulated_seconds': charge(ledger['entries'])}


def analyze(source, output):
    p = contract(True)
    source, output = check_roots(source, output)
    base, _ = reference(source, p)
    results = {'T1-A': base}
    mod = executor()
    for config in CAPS:
        built = mod._build_configuration(config)
        binding = configuration_binding(mod, built, p)
        m = configure_worker(source, output, config, 1, Path('unused'))
        checkpoint = validate_existing(output, config, binding, m)
        if not checkpoint or checkpoint['next_cycle'] != 4:
            raise Refused('INCOMPLETE_MATRIX: ' + config)
        result = load(output / config / 'result.json')
        if result['status'] != 'COMPLETE':
            raise Refused('INCOMPLETE_MATRIX: ' + config)
        results[config] = result
    freeze = load(ATOL)
    rows = {}
    for name in mod.OBSERVABLES:
        rows[name] = {}
        for arm, ids in {'temporal': ['T1-A', 'T1-B', 'T1-C'],
                         'spatial': ['T1-E', 'T1-D', 'T1-A']}.items():
            first = mod._pair_rows(results[ids[0]], results[ids[1]], name, freeze)
            second = mod._pair_rows(results[ids[1]], results[ids[2]], name, freeze)
            rows[name][arm] = {'pairs': [first, second],
                              'classification': mod._classify_pair_rows(first, second)}
    classifications = [value for observable in rows.values() for arm in observable.values()
                       for value in arm['classification'] if value != 'NOT_EVALUATED']
    if not classifications:
        raise Refused('no evaluable sensitivity comparisons')
    conclusion = ('COMPLETED — TRANSIENT EVIDENCE ACCEPTED'
                  if all(v == 'CONVERGING_MONOTONE' for v in classifications)
                  else 'COMPLETED — NUMERICAL LIMITATION IDENTIFIED')
    report = {'protocol_sha256': sha(PROTOCOL), 'analysis_freeze_sha256': sha(ATOL),
              'status': 'COMPLETE_TRANSIENT_MATRIX', 'observables': rows,
              'conclusion': conclusion,
              'periodicity': 'NOT_EVALUATED', 'predictive_validation': 'NOT_CLAIMED',
              'spatial_temporal_coupling': 'Spatial arm uses fixed nominal CFL; effective dt changes with mesh. Spatial independence cannot be isolated solely from this arm.'}
    atomic(output / 'sensitivity-report-v4.json', report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['preflight', 'freeze', 'run-config', 'analyze', 'recover', '_worker'])
    parser.add_argument('--source-root', type=Path, required=True)
    parser.add_argument('--artifact-root', type=Path, required=True)
    parser.add_argument('--config', choices=list(CAPS))
    parser.add_argument('--invocation', type=int)
    parser.add_argument('--authorization', type=Path)
    parser.add_argument('--token')
    parser.add_argument('--structural-only', action='store_true',
                        help='preflight/freeze only; reports RAM availability, never authorizes launch')
    args = parser.parse_args()
    try:
        if args.structural_only and args.command not in ('preflight', 'freeze'):
            raise Refused('structural-only is unavailable for execution or recovery')
        if args.command in ('preflight', 'freeze'):
            result = preflight(args.source_root, args.artifact_root, structural_only=args.structural_only)
            if args.command == 'freeze':
                if FREEZE.exists():
                    raise Refused('freeze already exists; immutable')
                atomic(FREEZE, {'status': 'FROZEN_EXECUTION_NOT_AUTHORIZED',
                                'protocol_sha256': sha(PROTOCOL), 'driver_sha256': sha(HERE),
                                'preflight': result})
        elif args.command == 'recover':
            result = recover(args.source_root, args.artifact_root)
        elif args.command == '_worker':
            authorization(args.authorization, args.source_root, args.artifact_root)
            active = load(args.artifact_root / 'active-invocation.json')
            if (active['token'] != args.token or active['config'] != args.config
                    or active['invocation'] != args.invocation
                    or active['supervisor_pid'] != os.getppid()):
                raise Refused('worker requires its live supervisor')
            threading.Thread(target=watch_parent,
                             args=(active['supervisor_pid'], active['supervisor_created']),
                             daemon=True).start()
            mod = configure_worker(args.source_root, args.artifact_root, args.config,
                                   args.invocation, args.authorization)
            return mod._run_config(args.config, args.invocation, args.authorization)
        elif args.command == 'run-config':
            result = run_config(args.source_root, args.artifact_root, args.config,
                                args.invocation, args.authorization)
        else:
            result = analyze(args.source_root, args.artifact_root)
        print(json.dumps(result, sort_keys=True))
        return 1 if args.command == 'run-config' and result.get('status') in TERMINAL else 0
    except (RuntimeError, OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({'status': 'FAIL_CLOSED', 'error': str(exc)}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
