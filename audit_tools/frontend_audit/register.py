"""Register the owner's isolated UX research objective, preserving prior state."""
import datetime as dt
import json
from pathlib import Path

root = Path(__file__).resolve().parents[2]
path = root/'results/2t-commercial-core-20261002/program-status.json'
data = json.loads(path.read_text(encoding='utf-8'))
objective = 'DINO_FRONTEND_UX_AUDIT_V1'
tasks = [
    ('UXA-SCOPE', 'Freeze integrated source, audit scope and isolated environment'),
    ('UXA-WALKTHROUGHS', 'Observe real 2T/native4T/reference4T routes with durable evidence'),
    ('UXA-DIAGNOSIS', 'Build evidence-backed seven-category UX/UI diagnosis'),
    ('UXA-DESIGN', 'Propose coherent information architecture and visual wireframes'),
    ('UXA-BACKLOG', 'Prioritize scoped improvements, dependencies and acceptance'),
    ('UXA-REVIEW', 'Self-review coverage, limitations, compatibility and delivery integrity'),
]
data.setdefault('frontend_audit_prior_operational_snapshot', {
    'current_objective': data['current_objective'], 'gate_status': data['gate_status']})
data['current_objective'] = dict(id=objective, state='IN_PROGRESS',owner_approved=True,
    summary='Owner-authorized isolated frontend UX/UI audit and redesign, no product implementation.',
    change='openspec/changes/frontend-ux-audit-v1',
    spec='openspec/changes/frontend-ux-audit-v1/specs/frontend-ux-audit-v1/spec.md',
    plan='results/frontend-audit-v1/plan.json', gate_tasks=[t[0] for t in tasks],
    completion_criterion='Deliver diagnosis, observed routes, wireframes, prioritized backlog and critical evaluation.')
for task_id, description in tasks:
    if not any(t['id']==task_id for t in data['queue']):
        data['queue'].append(dict(id=task_id,objective=objective,description=description,
            dependencies=[],state='READY',blocker=None,commits=[],evidence=[],
            next_action=description,owner_role='orchestrator',write_scope=[],evidence_level='L0'))
data['gate_status']=dict(objective=objective,state='OPEN',classification=None,evidence=[],
    gate_tasks_total=len(tasks),gate_tasks_done=0,gate_task_states={'READY':len(tasks)},
    remaining=[t[0] for t in tasks], updated_at=dt.datetime.now(dt.timezone.utc).isoformat())
path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
agents=root/'AGENTS.md'
text=agents.read_text(encoding='utf-8')
start=text.index('CURRENT_OBJECTIVE:',text.index('## 1. CURRENT_OBJECTIVE'))
end=text.index('durable queue:',start)
text=text[:start]+'''CURRENT_OBJECTIVE: DINO_FRONTEND_UX_AUDIT_V1
change/spec:       openspec/changes/frontend-ux-audit-v1/
                   specs/frontend-ux-audit-v1/spec.md
roadmap:          docs/frontend-audit-v1/backlog.md
completion:        Owner-authorized research/design audit of frozen integrated
                   CP0+CP1+unified UI revision d44305c. Real GUI evidence,
                   diagnosis, wireframes, prioritized backlog and critical review.
                   No product/scientific changes or Windows build.
'''+text[end:]
agents.write_text(text,encoding='utf-8')
output=root/'results/frontend-audit-v1'
output.mkdir(parents=True,exist_ok=True)
(output/'plan.json').write_text(json.dumps(dict(schema='DINO_FRONTEND_UX_AUDIT_V1',
    product_revision='d44305c24ec81d9b767305d319a660c0c034e5c9',
    review_type='SELF_REVIEW', tasks=[dict(id=a,description=b) for a,b in tasks],
    scope='Research/evaluation/design, no product implementation'),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(objective)
