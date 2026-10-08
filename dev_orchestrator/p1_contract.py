"""Checks documentales P1 y cierre con revisión externa; nunca ejecuta un solver."""
import argparse
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from .contracts import read_json, validate_named, load_phase, inside
from .git_state import snapshot, compare
from .evidence.build_report import artifacts, build_report
from .gates.evaluate import evaluate

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = 'docs/gasdynamic/1d_contract_v1.json'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


def validate_contract(m, root=ROOT):
    """Valida integridad y decisiones registradas, no prueba la ciencia del futuro solver."""
    required = {'model_version','equations','state_vector','eos','numerical_method','CFL',
                'boundaries','verification_cases','gates','excluded_scope','dependencies',
                'baseline_reference','documents','production_snapshot','decision_log',
                'unresolved_blocking_decisions'}
    if required-m.keys(): raise ValueError('Contrato incompleto')
    if m['unresolved_blocking_decisions']: raise ValueError('SCIENTIFIC_CHANGE_REQUIRED')
    if m['state_vector'] != ['A*rho','A*rho*u','A*rho*E','A*rho*Y']:
        raise ValueError('Estado conservado contradictorio')
    if m['equations']['source'] != ['0','p*d_x A','0','0']:
        raise ValueError('Fuente de área contradictoria')
    eos=m['eos']; r=eos['R_J_kgK']; g=eos['gamma']
    if (r,g)!=(287,1.35) or abs(eos['cv_J_kgK']-r/(g-1))>1e-9 or abs(eos['cp_J_kgK']-g*r/(g-1))>1e-9:
        raise ValueError('EOS inconsistente')
    if m['numerical_method']['baseline'] != ['finite_volume','first_order','HLLC','Forward_Euler']:
        raise ValueError('Método no seleccionado')
    if m['CFL']['initial']!=0.4 or m['CFL']['test_values']!=[0.2,0.4,0.6]:
        raise ValueError('CFL inconsistente')
    cases=m['verification_cases']
    if [c['id'] for c in cases]!=[f'T{i:02}' for i in range(1,13)]:
        raise ValueError('Deben existir exactamente T01–T12')
    plan=inside(root,'docs/gasdynamic/1d_verification_plan_v1.md').read_text(encoding='utf-8')
    for c in cases:
        if not c['purpose'] or not c['definition'] or c['definition'] not in plan or c['status']!='SPECIFIED_NOT_EXECUTED':
            raise ValueError('Caso sin definición trazable o ejecución atribuida')
    decisions=m['decision_log']
    if [d['id'] for d in decisions]!=[f'D{i}' for i in range(1,12)]:
        raise ValueError('Decision log incompleto')
    for d in decisions:
        if any(not d.get(k) for k in ('selected','alternatives','rationale','risks','deferred_issues')):
            raise ValueError('Decisión incompleta')
    for group in ('documents','baseline_reference','production_snapshot'):
        if not m[group]: raise ValueError('Inventario vacío: '+group)
        for p,h in m[group].items():
            if sha(inside(root,p))!=h: raise ValueError('Hash modificado: '+p)
    receipt=read_json(inside(root,m['dependencies']['receipt']))
    original=validate_named(read_json(inside(root,receipt['original_evidence'])),'evidence')
    if receipt['status']!='P0_HUMAN_ACCEPTED' or receipt['actor']!='usuaria' or original['gate']!='PASS':
        raise ValueError('P0 no aceptado')
    if sha(inside(root,receipt['original_evidence']))!=receipt['original_evidence_sha256']:
        raise ValueError('Evidencia P0 alterada')
    if receipt['baseline_sha256']!=m['baseline_reference']: raise ValueError('Baseline divergente')
    dependency=validate_named(read_json(inside(root,m['dependencies']['dependency_evidence'])),'evidence')
    expected=deepcopy(original); expected['execution_status']='COMPLETED'
    approval=dependency['config'].get('human_acceptance',{})
    if (approval.get('status')!='P0_HUMAN_ACCEPTED' or
            approval.get('receipt_sha256')!=sha(inside(root,m['dependencies']['receipt'])) or
            approval.get('derived_from_sha256')!=receipt['original_evidence_sha256']):
        raise ValueError('Aceptación sin vínculo')
    expected['config']['human_acceptance']=approval
    if dependency!=expected: raise ValueError('Dependencia derivada altera evidencia científica')
    for n in range(2,10):
        if read_json(root/f'dev_orchestrator/phases/P{n}.json')['enabled']:
            raise ValueError('Fase posterior habilitada')
    return True


def check(run_dir):
    m=read_json(ROOT/MANIFEST)
    try:
        validate_contract(m)
    except ValueError as exc:
        # Una falta contractual no se disfraza como error de instalación; una
        # decisión científica pendiente detiene el gate sin reparar ni ejecutar P2.
        write(run_dir/'artifacts/result.json',dict(
            checks=[dict(id='contract_complete',passed=False,kind='infrastructure',reason=str(exc))],
            metrics=dict(numerical_tests_executed=0),
            scientific_change_required=str(exc)=='SCIENTIFIC_CHANGE_REQUIRED'))
        write(run_dir/'artifacts/git-before.json',snapshot(ROOT))
        write(run_dir/'artifacts/contract-inventory.json',{})
        return
    write(run_dir/'artifacts/git-before.json',snapshot(ROOT))
    write(run_dir/'artifacts/contract-inventory.json',{
        MANIFEST:sha(ROOT/MANIFEST), **m['documents'],
        m['dependencies']['receipt']:sha(ROOT/m['dependencies']['receipt']),
        m['dependencies']['dependency_evidence']:sha(ROOT/m['dependencies']['dependency_evidence'])})
    write(run_dir/'artifacts/result.json',dict(
        checks=[dict(id='contract_complete',passed=True,kind='infrastructure',reason='Documentos, T01–T12 y D1–D11 íntegros'),
                dict(id='p0_accepted',passed=True,kind='infrastructure',reason='Aceptación usuaria vinculada al P0 PASS original'),
                dict(id='scope_preserved',passed=True,kind='infrastructure',reason='Hashes producción/baseline intactos, P2–P9 deshabilitadas')],
        metrics=dict(verification_cases=12,decisions=11,numerical_tests_executed=0),
        scientific_change_required=False))


def finalize(run_dir, review_path):
    """Reevalúa el gate; no sustituye el reviewer stub ni oculta su resultado."""
    run_dir=run_dir.resolve()
    if run_dir.parent!=ROOT/'dev_orchestrator/runs': raise ValueError('Run original requerido')
    if (run_dir/'artifacts/p1-finalized.json').exists(): raise ValueError('P1 ya finalizado')
    envelope=read_json(review_path)
    original=(run_dir/'evidence.json').read_bytes()
    data=validate_named(json.loads(original),'evidence')
    if data['phase_id']!='P1' or envelope['run_id']!=data['run_id'] or envelope['evidence_sha256']!=sha(run_dir/'evidence.json'):
        raise ValueError('Revisión sin vínculo a P1')
    review=validate_named(envelope['review'],'review')
    if review['kind']!='independent': raise ValueError('Revisión independiente requerida')
    phase=load_phase(ROOT,'P1',read_json(ROOT/'dev_orchestrator/config.json'))[1]
    if hashlib.sha256(json.dumps(phase,sort_keys=True).encode()).hexdigest()!=data['phase_definition_sha256']:
        raise ValueError('Fase cambió durante revisión')
    validate_contract(read_json(ROOT/MANIFEST))
    inventory=read_json(run_dir/'artifacts/contract-inventory.json')
    if envelope['contract_sha256']!=inventory: raise ValueError('Revisión de otro contrato')
    for p,h in inventory.items():
        if sha(inside(ROOT,p))!=h: raise ValueError('Contrato cambió tras ejecución')
    for a in data['artifacts']:
        if sha(inside(run_dir,a['path']))!=a['sha256']: raise ValueError('Artefacto alterado')
    changed,violations,touched=compare(read_json(run_dir/'artifacts/git-before.json'),snapshot(ROOT),phase)
    violations=sorted(set(violations+data['scope_violations']))
    gate,reasons=evaluate(phase,data['checks'],review,errors=data['errors'],scope_violations=violations,evidence_complete=True)
    data.update(review=review,gate=gate,gate_reasons=reasons,scope_violations=violations,
                files_changed=changed,preexisting_touched=touched,
                execution_status='WAITING_HUMAN_APPROVAL' if gate=='PASS' else 'COMPLETED')
    label='P1_PASS_CONTRACT_READY' if gate=='PASS' else ('P1_BLOCKED_CONTRACT_INCOMPLETE' if gate=='BLOCKED' else gate)
    # Preparación antes de reemplazar evidencia; originales quedan preservados.
    for name,body in [('pre-review-evidence.json',original),('pre-review-summary.md',(run_dir/'summary.md').read_bytes())]:
        dest=run_dir/'artifacts'/name
        if dest.exists() and dest.read_bytes()!=body: raise ValueError('Backup previo diferente')
        if not dest.exists(): dest.write_bytes(body)
    write(run_dir/'artifacts/independent-review.json',envelope)
    write(run_dir/'artifacts/p1-decision.json',dict(state=label,gate=gate,execution_status=data['execution_status'],next_phase_executed=False))
    data['artifacts']+=artifacts(run_dir,['artifacts/pre-review-evidence.json','artifacts/pre-review-summary.md',
                                        'artifacts/independent-review.json','artifacts/p1-decision.json'])
    data['finished_at']=datetime.now(timezone.utc).isoformat()
    try:
        build_report(run_dir,data)
        write(run_dir/'artifacts/p1-finalized.json',dict(state=label,evidence_sha256=sha(run_dir/'evidence.json')))
    except Exception:
        (run_dir/'evidence.json').write_bytes(original)
        (run_dir/'summary.md').write_bytes((run_dir/'artifacts/pre-review-summary.md').read_bytes())
        raise
    print(json.dumps(dict(state=label,run_id=data['run_id'],execution_status=data['execution_status'])))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-dir',type=Path,required=True)
    parser.add_argument('--review',type=Path)
    args=parser.parse_args()
    if args.review: finalize(args.run_dir,args.review)
    else: check(args.run_dir)
