"""Gates de evidencia: no cambia ciencia, archivos ni ejecución de otras fases."""
from ..contracts import BASE, ContractError, read_json, TERMINAL_STATES


def policies():
    data=read_json(BASE/'gates/policies.json')
    if data['terminal_states']!=list(TERMINAL_STATES): raise ContractError('Estados de política inválidos')
    expected=['FAILED_INFRASTRUCTURE','SCIENTIFIC_CHANGE_REQUIRED','BLOCKED','PASS']
    if data['precedence']!=expected: raise ContractError('Precedencia no implementada')
    p=data['default']
    if p!=dict(require_all_checks=True,require_complete_evidence=True,require_review=True,
               allow_dummy_stub_only_for='dummy',out_of_scope='BLOCKED'):
        raise ContractError('Política no implementada')
    return p


def evaluate(phase, checks, review, *, errors=(), scope_violations=(), evidence_complete=True,
             scientific_change_required=False, exhausted=False, blocked_reasons=()):
    policy=policies()
    if scope_violations: return 'BLOCKED',['scope_violation',*list(errors)]
    if errors: return 'FAILED_INFRASTRUCTURE',list(errors)
    if (scientific_change_required or review['scientific_change_required']) and not phase['scientific_changes_authorized']:
        return 'SCIENTIFIC_CHANGE_REQUIRED',['unauthorized_scientific_change_required']
    reasons=list(blocked_reasons)
    if scope_violations: reasons.append('scope_violation')
    if exhausted: reasons.append('max_repair_attempts_exhausted')
    by_id={c['id']:c for c in checks}
    for name in phase['required_checks']:
        if name not in by_id or not by_id[name]['passed']: reasons.append('required_check_failed:'+name)
    if not evidence_complete: reasons.append('incomplete_evidence')
    accepted_review=(review['kind']=='independent' or
                     review['kind']=='dummy_stub' and phase['phase']==policy['allow_dummy_stub_only_for'])
    if not accepted_review or review['status']!='PASS' or review['blocking_findings']:
        reasons.append('review_not_approved')
    return ('BLOCKED',list(dict.fromkeys(reasons))) if reasons else ('PASS',['all_required_checks_passed'])
