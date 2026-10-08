"""Ejecuta UNA fase explícita; sin edición autónoma ni conexión a agentes."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import threading
import time
import uuid

from ..contracts import BASE, ContractError, inside, load_phase, read_json, validate_named
from ..evidence.build_report import artifacts, build_report
from ..gates.evaluate import evaluate
from ..git_state import compare, snapshot
from .run_review import not_run, run_review
from .run_tests import run_command


def utc(): return datetime.now(timezone.utc).isoformat()


def dependency_errors(phase, evidence_paths):
    missing=[]
    for name in phase['depends_on']:
        if name not in evidence_paths: missing.append('missing_dependency:'+name); continue
        data=validate_named(read_json(evidence_paths[name]),'evidence')
        if data['phase_id']!=name or data['gate']!='PASS' or data['execution_status']!='COMPLETED':
            missing.append('dependency_not_approved:'+name)
    return missing


def run_phase(root, phase_id, *, dry_run=False, continue_requested=False,
              retry_failed_checks=False, dependency_evidence=None, cancel=None):
    root=Path(root).resolve(); cancel=cancel or threading.Event()
    dependency_evidence=dependency_evidence or {}
    phase=None; before=None; run_dir=None; current_attempt=0; started=time.monotonic()
    run_id=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')+'-'+re.sub('[^A-Za-z0-9_-]','_',phase_id)[:64]+'-'+uuid.uuid4().hex[:12]
    data=dict(run_id=run_id,phase_id=phase_id,started_at=utc(),finished_at=utc(),git_commit=None,git_dirty=False,
        preexisting_changes=[],preexisting_untracked=[],commands=[],checks=[],tests=[],metrics={},review=not_run(),
        gate='FAILED_INFRASTRUCTURE',gate_reasons=[],execution_status='COMPLETED',attempts=[],files_changed=[],
        scope_violations=[],preexisting_touched=[],errors=[],artifacts=[],phase_definition_sha256=None,
        config={},continue_requested=continue_requested)
    config=dict(default_command_timeout=30,default_phase_timeout=120,default_max_repair_attempts=3,
        runs_directory='dev_orchestrator/runs',python_executable_policy='current_interpreter',reviewer_mode='dummy_local')
    def create_run():
        nonlocal run_dir
        if run_dir is None:
            directory=inside(root,config['runs_directory'])
            if directory!=root/'dev_orchestrator/runs':
                raise ContractError('runs_directory debe estar bajo dev_orchestrator/runs')
            run_dir=directory/run_id
            run_dir.mkdir(parents=True,exist_ok=False)
            (run_dir/'logs').mkdir(); (run_dir/'artifacts').mkdir()
    def observe_changes(final=False):
        if before is not None:
            # Cierre y escritura tienen una reserva acotada, incluso tras timeout.
            after=snapshot(root,deadline=time.monotonic()+15 if final else started+phase['timeout'])
            data['files_changed'],data['scope_violations'],data['preexisting_touched']=compare(before,after,phase)
    try:
        config=validate_named(read_json(root/'dev_orchestrator/config.json'),'config')
        if config['runs_directory']!='dev_orchestrator/runs': raise ContractError('Directorio de runs no admitido en v1')
        roadmap,phase=load_phase(root,phase_id,config)
        data['phase_definition_sha256']=hashlib.sha256(json.dumps(phase,sort_keys=True).encode()).hexdigest()
        data['config']={**config,'dependency_evidence':{k:str(v) for k,v in dependency_evidence.items()}}
        if dry_run:
            return dict(dry_run=True,phase=phase_id,enabled=phase['enabled'],dependencies=phase['depends_on'],
                commands=phase['commands'],allowed_paths=phase['allowed_paths'],forbidden_paths=phase['forbidden_paths'],
                expected_gate='PASS' if phase['enabled'] else 'BLOCKED',human_gate=phase['human_gate'],
                note='Solo previsión; no ejecuta comandos, crea runs ni avanza de fase.',next_phase_executed=False)
        before=snapshot(root,deadline=started+phase['timeout'])
        data.update(git_commit=before['commit'],git_dirty=before['dirty'],preexisting_changes=before['changes'],preexisting_untracked=before['untracked'])
        create_run()
        blocked=[]
        if not phase['enabled']: blocked.append('phase_disabled_not_implemented')
        blocked.extend(dependency_errors(phase,dependency_evidence))
        if blocked:
            data.update(gate='BLOCKED',gate_reasons=blocked)
        else:
            deadline=started+phase['timeout']
            total_attempts=1+(phase['max_repair_attempts'] if retry_failed_checks else 0)
            for attempt in range(1,total_attempts+1):
                current_attempt=attempt
                data['checks']=[]; data['metrics']={}; data['artifacts']=[]; data['review']=not_run(); scientific=False
                # Cada reintento tiene artefactos nuevos, nunca sobrescribe el anterior.
                work=run_dir if attempt==1 else run_dir/f'attempt-{attempt}'
                if attempt>1: (work/'artifacts').mkdir(parents=True)
                attempt_commands=[]
                for command in phase['commands']:
                    remaining=deadline-time.monotonic()
                    if remaining<=0:
                        data['errors'].append('phase_timeout'); break
                    argv=[part.replace('{python}',sys.executable).replace('{run_dir}',str(work)) for part in command['argv']]
                    outcome=run_command(argv,cwd=root,logs=run_dir/'logs',name=f"{attempt}-{command['id']}",
                        timeout=min(command.get('timeout',config['default_command_timeout']),remaining),kind=command['kind'],cancel=cancel)
                    outcome['id']=command['id']
                    for key in ('stdout_log','stderr_log'): outcome[key]=Path(outcome[key]).relative_to(run_dir).as_posix()
                    data['commands'].append(outcome); attempt_commands.append(outcome)
                    if command['kind']=='test': data['tests'].append(outcome)
                    data['checks'].append(dict(id=command['id'],passed=outcome['status']=='passed',kind='test' if command['kind']=='test' else 'infrastructure',reason=outcome['error'] or outcome['status']))
                    # Comparar tras CADA comando, no solo al terminar la fase.
                    observe_changes()
                    if outcome['status'] in ('cancelled','error') or (command['kind']=='command' and outcome['status']!='passed'):
                        data['errors'].append(outcome['error'] or 'command_failed:'+command['id'])
                    if outcome['status']=='passed' and command.get('result_file'):
                        result_path=inside(work,command['result_file'])
                        if result_path.stat().st_size>1024*1024: raise ContractError('Resultado estructurado demasiado grande')
                        result=validate_named(read_json(result_path),'command-result')
                        ids={c['id'] for c in data['checks']}
                        for check in result['checks']:
                            if check['id'] in ids: raise ContractError('Check duplicado: '+check['id'])
                            ids.add(check['id']); data['checks'].append(check)
                        if data['metrics'].keys() & result['metrics'].keys(): raise ContractError('Métrica duplicada')
                        data['metrics'].update(result['metrics']); scientific |= result['scientific_change_required']
                    if data['errors'] or data['scope_violations'] or scientific: break
                complete=False
                if not data['errors'] and not data['scope_violations']:
                    # Archivo faltante es infraestructura, no fracaso numérico.
                    if not scientific and all(c['status']=='passed' for c in attempt_commands) and len(attempt_commands)==len(phase['commands']):
                        records=artifacts(work,phase['required_evidence'])
                        for record in records: record['path']=(work/record['path']).relative_to(run_dir).as_posix()
                        data['artifacts']=records; complete=True
                    if phase['review']=='required':
                        data['review']=run_review(phase=phase,diff=dict(files_changed=data['files_changed']),
                            evidence=json.loads(json.dumps(data)),required_checks=phase['required_checks'])
                missing_tests=[name for name in phase['required_tests'] if not any(c['id']==name and c['status']=='passed' for c in attempt_commands)]
                if time.monotonic()>=deadline and 'phase_timeout' not in data['errors']:
                    data['errors'].append('phase_timeout')
                gate,reasons=evaluate(phase,data['checks'],data['review'],errors=data['errors'],scope_violations=data['scope_violations'],
                    evidence_complete=complete,scientific_change_required=scientific,blocked_reasons=['required_test_failed:'+n for n in missing_tests])
                data.update(gate=gate,gate_reasons=reasons)
                data['attempts'].append(dict(number=attempt,kind='initial' if attempt==1 else 'verification_retry_no_code_repair',
                    cause='; '.join(reasons),state=gate))
                if gate!='BLOCKED' or data['scope_violations'] or not retry_failed_checks: break
                if attempt==total_attempts:
                    data['gate_reasons'].append('max_repair_attempts_exhausted'); break
            if data['gate']=='PASS' and phase['human_gate']: data['execution_status']='WAITING_HUMAN_APPROVAL'
    except KeyboardInterrupt:
        cancel.set(); data['errors'].append('cancelled_by_user')
        data.update(gate='FAILED_INFRASTRUCTURE',gate_reasons=['cancelled_by_user'])
    except Exception as exc:
        data['errors'].append(f'{type(exc).__name__}: {exc}')
        data.update(gate='FAILED_INFRASTRUCTURE',gate_reasons=[data['errors'][-1]])
    if dry_run: return dict(dry_run=True,phase=phase_id,gate=data['gate'],errors=data['errors'])
    if current_attempt and len(data['attempts'])<current_attempt:
        data['attempts'].append(dict(number=current_attempt,kind='initial' if current_attempt==1 else 'verification_retry_no_code_repair',
            cause='; '.join(data['gate_reasons']),state=data['gate']))
    # Metadatos parciales también se guardan si la configuración/fase no pudo cargarse.
    if run_dir is None:
        config['runs_directory']='dev_orchestrator/runs'
        try:
            create_run()
        except (OSError,ValueError) as exc:
            data['errors'].append('evidence_directory_unavailable: '+str(exc))
            data.update(gate='FAILED_INFRASTRUCTURE',gate_reasons=['evidence_directory_unavailable'])
            return dict(gate=data['gate'],execution_status='COMPLETED',run_dir=None,evidence=data,errors=data['errors'])
    if before is not None and phase is not None:
        try:
            observe_changes(final=True)
            if data['scope_violations']:
                data.update(gate='BLOCKED',gate_reasons=list(dict.fromkeys(['scope_violation',*data['gate_reasons']])),execution_status='COMPLETED')
                if data['attempts']:
                    data['attempts'][-1].update(state='BLOCKED',cause='; '.join(data['gate_reasons']))
        except (OSError,ValueError,subprocess.SubprocessError) as exc:
            data['errors'].append(str(exc)); data.update(gate='FAILED_INFRASTRUCTURE',gate_reasons=['git_observation_failed'])
    data['finished_at']=utc()
    build_report(run_dir,data)
    return dict(gate=data['gate'],execution_status=data['execution_status'],run_dir=str(run_dir),evidence=data)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase'); parser.add_argument('--dry-run',action='store_true')
    parser.add_argument('--continue',dest='continue_requested',action='store_true',help='Reservado: registra la intención, nunca ejecuta la fase siguiente.')
    parser.add_argument('--retry-failed-checks',action='store_true',help='Reintentos acotados de verificación, sin reparar código.')
    parser.add_argument('--dependency',action='append',default=[],metavar='PHASE=evidence.json')
    args=parser.parse_args(argv)
    dependencies={}
    for item in args.dependency:
        if '=' not in item: parser.error('--dependency requiere PHASE=ruta')
        name,path=item.split('=',1); dependencies[name]=Path(path)
    result=run_phase(BASE.parent,args.phase,dry_run=args.dry_run,continue_requested=args.continue_requested,
        retry_failed_checks=args.retry_failed_checks,dependency_evidence=dependencies)
    print(json.dumps({k:v for k,v in result.items() if k!='evidence'},ensure_ascii=False,indent=2))
    return 0 if result.get('gate') in (None,'PASS') else 1


if __name__=='__main__': raise SystemExit(main())
