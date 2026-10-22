"""One 3000 RPM point: existing workflow invocations, one accumulated ledger."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import threading
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import psutil
from scripts.diagnostics.integrated_solver_verification_a3b_v4 import atomic, bounded_process, watch_parent
from motorsim.engine_configuration import implementation_source_hashes, resolve_for_operating_point
from motorsim.exploratory_workflow import run_exploratory, preflight, _run_directory
from motorsim._evidence_io import canonical_digest

GLOBAL_SECONDS = 3000
INVOCATION_SECONDS = 600
CLOSURE_RESERVE = 10
PROJECT = 'periodic-point-3000'
RUN = 'independent-point'


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def digest_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def external(root):
    root = Path(root).resolve()
    if root == ROOT or ROOT in root.parents:
        raise ValueError('external artifact root required')
    return root


def prepare(root, document, *, horizon=10, global_seconds=GLOBAL_SECONDS):
    """Zero-step preparation; CLI supplies only the owner-approved reference."""
    root = external(root)
    check = preflight(document,rpm=3000,max_cycles=horizon,budget_seconds=600,memory_limit_mib=3072)
    sources = implementation_source_hashes()
    definition = {'schema':'DINO_SINGLE_PERIODIC_POINT_V1','rpm':3000,'horizon':horizon,
        'global_seconds':global_seconds,'invocation_seconds':600,'worker_mib':3072,
        'aggregate_mib':4096,'closure_reserve_seconds':CLOSURE_RESERVE,
        'document_sha256':canonical_digest(document),'preflight':check,
        'scientific_sources':{k:v for k,v in sources.items() if k!='motorsim.exploratory_workflow'},
        'operational_sources':{'workflow':sources['motorsim.exploratory_workflow'],
            'executor':digest_file(__file__),
            'supervisor':digest_file(ROOT/'scripts/diagnostics/integrated_solver_verification_a3b_v4.py')},
        'initial_state':'INDEPENDENT; historical standalone snapshot is not a workflow checkpoint',
        'artifact_root':str(root),'scientific_execution_authorized':False}
    if type(global_seconds) not in (int,float) or not math.isfinite(global_seconds) or not 0 < global_seconds <= GLOBAL_SECONDS:
        raise ValueError('invalid total budget')
    root.mkdir(parents=True,exist_ok=False)
    atomic(root/'document.json',document)
    atomic(root/'prepared.json',definition)
    save_ledger(root,{'schema':'DINO_POINT_BUDGET_V1','definition_sha256':canonical_digest(definition),
        'entries':[],'charged_seconds':0.0,'terminal':None})
    return definition


def save_ledger(root, value):
    atomic(root/'ledger.json',{'value':value,'sha256':canonical_digest(value)})


def ledger(root):
    wrapped = read(root/'ledger.json')
    value = wrapped['value']; definition = read(root/'prepared.json')
    if wrapped['sha256'] != canonical_digest(value) or value['definition_sha256'] != canonical_digest(definition):
        raise ValueError('FAIL_CLOSED ledger integrity or identity')
    total = 0.0
    for number, entry in enumerate(value['entries'],1):
        charge, reservation = entry['charged_seconds'],entry['reservation_seconds']
        if (entry['number']!=number or not all(type(x) in (int,float) and math.isfinite(x) for x in (charge,reservation))
                or not 0 <= charge <= reservation <= INVOCATION_SECONDS
                or entry['state'] not in ('ACTIVE','CLOSED','INTERRUPTED_RESERVED')
                or (entry['state'] in ('ACTIVE','INTERRUPTED_RESERVED') and charge!=reservation)):
            raise ValueError('FAIL_CLOSED ledger charge')
        total += charge
    if abs(total-value['charged_seconds'])>1e-8 or total>definition['global_seconds']:
        raise ValueError('FAIL_CLOSED accumulated budget')
    return value


def validate(root):
    definition = read(root/'prepared.json'); document = read(root/'document.json')
    sources = implementation_source_hashes()
    actual = {k:v for k,v in sources.items() if k!='motorsim.exploratory_workflow'}
    if (definition['artifact_root']!=str(root) or definition['scientific_sources']!=actual or
        definition['document_sha256']!=canonical_digest(document) or
        definition['operational_sources']!={'workflow':sources['motorsim.exploratory_workflow'],
            'executor':digest_file(__file__),
            'supervisor':digest_file(ROOT/'scripts/diagnostics/integrated_solver_verification_a3b_v4.py')}):
        raise ValueError('FAIL_CLOSED implementation/configuration identity')
    return definition


def classification(result, horizon):
    if result['status']=='FAILED_CLOSED':
        if any(kind in result.get('classification','') for kind in
               ('RESOURCE_LIMIT_EXCEEDED','ARTIFACT_BUDGET_EXCEEDED')):
            return 'PARTIAL_RESOURCE_OR_TIME'
        return 'NUMERICAL_OR_PHYSICAL_FAILURE'
    if result.get('periodicity') in ('PERIOD_1','PERIOD_2'):
        metrics = result.get('cycles',[])[-1].get('engineering_output',{}).get('cycle_metrics',{})
        required = ('imep_pa','fmep_pa','bmep_pa','brake_power_w','brake_torque_nm')
        if all(metrics.get(k,{}).get('status')=='DEFINED' and
               type(metrics[k].get('value')) in (int,float) and math.isfinite(metrics[k]['value'])
               for k in required):
            return 'PERIODIC_POINT_ACCEPTED'
        return 'PERIODICITY_OBSERVED_ENGINEERING_UNDEFINED'
    if result['cycles_completed']>=horizon:
        return 'PERIODICITY_NOT_IDENTIFIED'
    return 'CONTINUE_AT_CHECKPOINT'


def worker(root, budget):
    parent = psutil.Process(os.getppid())
    threading.Thread(target=watch_parent,args=(parent.pid,parent.create_time()),daemon=True).start()
    definition = validate(root)
    deadline = time.monotonic()+budget
    timings = read(root/'cycle-timing.json') if (root/'cycle-timing.json').exists() else []
    cycle_start = [time.monotonic()]; last_cost = [max([120.0]+[r['wall_s'] for r in timings])]
    def admit(cycle):
        remaining = deadline-time.monotonic()
        allowed = remaining >= max(120.0,last_cost[0]*1.5+30)
        if allowed:
            cycle_start[0] = time.monotonic()
        return allowed
    def complete(cycle, record):
        elapsed = time.monotonic()-cycle_start[0]
        last_cost[0] = max(last_cost[0],elapsed)
        timings.append({'cycle':cycle,'wall_s':elapsed,'rss_bytes':psutil.Process().memory_info().rss})
        atomic(root/'cycle-timing.json',timings)
    path = _run_directory(root,PROJECT,RUN)
    result = run_exploratory(read(root/'document.json'),project_id=PROJECT,run_id=RUN,
        artifact_root=root,rpm=3000,max_cycles=definition['horizon'],budget_seconds=budget,
        memory_limit_mib=3072,resume=(path/'run.json').exists(),
        cycle_admission=admit,cycle_complete=complete,
        progress=lambda row: atomic(root/'progress.json',row),variant_label='reference 48-cell point')
    atomic(root/'worker-result.json',result)


def recover(root):
    """No solver: abandoned invocation consumes its full reservation."""
    value = ledger(root)
    active = value['entries'][-1] if value['entries'] else None
    if not active or active['state']!='ACTIVE':
        raise ValueError('no interrupted reservation')
    for key in ('supervisor','worker'):
        pid = active.get(key+'_pid')
        if pid:
            try:
                if psutil.Process(pid).create_time()==active[key+'_created']:
                    raise ValueError('FAIL_CLOSED process still active')
            except psutil.NoSuchProcess:
                pass
    active['state']='INTERRUPTED_RESERVED'; value['terminal']='PARTIAL_RESOURCE_OR_TIME'
    save_ledger(root,value)
    # Evidence and workflow locks are preserved; no automatic retry or adoption.
    return value


def invoke(root, authorization, *, cap_seconds=600):
    root = external(root)
    started = time.monotonic()
    definition = validate(root); value = ledger(root)
    auth = read(authorization)
    if auth != {'authorized':True,'definition_sha256':canonical_digest(definition)}:
        raise ValueError('separate exact execution authorization required')
    if value['terminal'] or any(e['state']=='ACTIVE' for e in value['entries']):
        raise ValueError('FAIL_CLOSED terminal or unclosed invocation; no automatic retry')
    if psutil.virtual_memory().available < 4096*1024**2:
        raise MemoryError('4096 MiB available host RAM required')
    remaining = definition['global_seconds']-value['charged_seconds']
    if remaining < 150 or not 0 < cap_seconds <= INVOCATION_SECONDS:
        value['terminal']='PARTIAL_RESOURCE_OR_TIME'; save_ledger(root,value)
        return value
    cap = min(cap_seconds,remaining)
    entry = {'number':len(value['entries'])+1,'state':'ACTIVE','reservation_seconds':cap,
        'charged_seconds':cap,'supervisor_pid':os.getpid(),
        'supervisor_created':psutil.Process().create_time(),
        'started_unix':time.time(),'cycles_before':0}
    run_path = _run_directory(root,PROJECT,RUN)
    if (run_path/'run.json').exists():
        entry['cycles_before']=read(run_path/'run.json').get('cycles_completed',0)
    value['entries'].append(entry); value['charged_seconds']+=cap
    save_ledger(root,value)  # reservation durable before spawn
    def launched(pid):
        entry.update(worker_pid=pid,worker_created=psutil.Process(pid).create_time())
        save_ledger(root,value)
    try:
        outcome = bounded_process([sys.executable,str(Path(__file__).resolve()),'_worker',
            '--root',str(root),'--worker-budget',str(max(1,cap-2*CLOSURE_RESERVE))],
            root/f'invocation-{entry["number"]:03d}.log',started+cap-CLOSURE_RESERVE,
            on_start=launched)
        entry['outcome']=outcome
        elapsed=time.monotonic()-started
        charged=min(cap,elapsed+CLOSURE_RESERVE)
        value['charged_seconds']+=charged-cap; entry['charged_seconds']=charged
        entry['elapsed_seconds']=elapsed; entry['state']='CLOSED'
        if outcome['exit_code']!=0 or outcome['stop_reason']:
            value['terminal']=('PARTIAL_RESOURCE_OR_TIME' if outcome['stop_reason'] else
                'FAIL_CLOSED_WORKER_ERROR')
        else:
            result=read(root/'worker-result.json')
            state=classification(result,definition['horizon'])
            entry['cycles_after']=result['cycles_completed']
            if state!='CONTINUE_AT_CHECKPOINT':
                value['terminal']=state
            elif result['cycles_completed']<=entry['cycles_before']:
                value['terminal']='PARTIAL_RESOURCE_OR_TIME'
        save_ledger(root,value)
        return value
    except BaseException:
        # Keep full durable reservation. Recovery cannot reset this charge.
        raise


def execute(root, authorization):
    root=external(root)
    lock=root/'executor.lock'
    fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY)
    try:
        os.close(fd)
        while True:
            result=invoke(root,authorization)
            if result['terminal']:
                return result
    finally:
        lock.unlink(missing_ok=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=['prepare','verify','run','recover','_worker'])
    parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--authorization',type=Path)
    parser.add_argument('--worker-budget',type=float)
    args=parser.parse_args(); root=external(args.root)
    if args.command=='prepare':
        from scripts.diagnostics.integrated_solver_verification_a3b_v3 import _build_configuration
        result=prepare(root,_build_configuration('T1-A')['variant'])
    elif args.command=='verify':
        result={'definition_sha256':canonical_digest(validate(root)),'ledger':ledger(root),'solver_steps':0}
    elif args.command=='run':
        result=execute(root,args.authorization)
    elif args.command=='recover':
        result=recover(root)
    else:
        value=ledger(root); entry=value['entries'][-1]
        if entry['state']!='ACTIVE' or entry['supervisor_pid']!=os.getppid():
            raise ValueError('worker requires live reserved supervisor')
        worker(root,args.worker_budget); return
    print(json.dumps(result))


if __name__=='__main__':
    main()
