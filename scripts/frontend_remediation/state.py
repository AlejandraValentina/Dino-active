"""Manage the isolated owner-authorized frontend remediation queue."""
import argparse
import datetime as dt
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
STATUS=ROOT/'results/2t-commercial-core-20261002/program-status.json'
OBJECTIVE='DINO_FRONTEND_REMEDIATION_V1'
TASKS=[('FRM-CAUSES','Re-evaluate P0 causes and freeze application integrity invariants'),
 ('FRM-P0-EDIT','Protect native drafts and submitted configuration identity'),
 ('FRM-P0-BUNDLE','Transport complete immutable native artifact closures with honest partial/legacy status'),
 ('FRM-P0-SAVE','Normalize imported project paths and preserve work on save errors'),
 ('FRM-CONTEXT','Persistent active project/model/variant/revision and navigation'),
 ('FRM-EDITORS','Physical-component forms, contextual errors and readable active-context help'),
 ('FRM-FLOWS','Simulation plans, terminal result access and comparison guidance'),
 ('FRM-PORTABILITY-UX','Preview portable contents and report import availability honestly'),
 ('FRM-ARCH-ROADMAP','Independent re-evaluation, incremental architecture and per-finding roadmap'),
 ('FRM-REGRESSION','Negative integrity checks and scoped/protected regressions'),
 ('FRM-LIVE-UAT','Real source GUI workflows and compact/large visual evidence')]


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('task',nargs='?')
    parser.add_argument('--state',default='DONE')
    parser.add_argument('--evidence',action='append',default=[])
    args=parser.parse_args()
    data=json.loads(STATUS.read_text(encoding='utf-8'))
    if args.task:
        task=next(t for t in data['queue'] if t['id']==args.task)
        task.update(state=args.state,evidence=args.evidence,write_scope=[],
                    next_action='Continue authorized remediation objective.')
    else:
        data['frontend_remediation_prior_objective']=data['current_objective']
        data['current_objective']=dict(id=OBJECTIVE,state='IN_PROGRESS',owner_approved=True,
            summary='Owner-authorized P0 structural fixes and coherent source frontend evolution.',
            change='openspec/changes/frontend-remediation-v1',
            spec='openspec/changes/frontend-remediation-v1/specs/frontend-remediation-v1/spec.md',
            plan='results/frontend-remediation-v1/plan.json',gate_tasks=[t[0] for t in TASKS],
            completion_criterion='F0 integrity and F1 coherent workflow source acceptance with tests/live evidence and explicit outstanding Windows/human UAT status.')
        for task_id,description in TASKS:
            if not any(t['id']==task_id for t in data['queue']):
                data['queue'].append(dict(id=task_id,objective=OBJECTIVE,description=description,
                    dependencies=[],state='READY',blocker=None,commits=[],evidence=[],next_action=description,
                    owner_role='implementation',write_scope=[],evidence_level='L0'))
        data['gate_status']=dict(objective=OBJECTIVE,state='OPEN',classification=None,evidence=[],
            gate_tasks_total=len(TASKS),gate_tasks_done=0,gate_task_states={'READY':len(TASKS)},
            remaining=[t[0] for t in TASKS],updated_at=dt.datetime.now(dt.timezone.utc).isoformat())
        output=ROOT/'results/frontend-remediation-v1';output.mkdir(parents=True,exist_ok=True)
        (output/'plan.json').write_text(json.dumps(dict(schema='DINO_FRONTEND_REMEDIATION_V1',
            base='696b8fc1368e7ba6ecf3a2c25ab6359264ec80d9',tasks=TASKS,
            lifecycle=['IMPLEMENTED','SOURCE_ACCEPTED','WINDOWS_ACCEPTED','PENDING_UAT'],
            block_reassessment=[dict(id=t['id'],assessment='Preserved: outside frontend remediation; no later capability resolves missing scientific inputs or deferred owner scope.') for t in data['queue'] if t['state']=='BLOCKED_LOCAL']),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        agents=ROOT/'AGENTS.md';text=agents.read_text(encoding='utf-8')
        start=text.index('CURRENT_OBJECTIVE:',text.index('## 1. CURRENT_OBJECTIVE'))
        end=text.index('durable queue:',start)
        text=text[:start]+'''CURRENT_OBJECTIVE: DINO_FRONTEND_REMEDIATION_V1
change/spec:       openspec/changes/frontend-remediation-v1/
                   specs/frontend-remediation-v1/spec.md
roadmap:          docs/frontend-remediation-v1/architecture-and-roadmap.md
completion:        Owner-authorized F0 structural P0 fixes and F1 coherent source
                   workflows with tests/live GUI evidence. Keep IMPLEMENTED,
                   SOURCE_ACCEPTED, WINDOWS_ACCEPTED and PENDING_UAT distinct.
                   No solver/scientific changes, push or main merge.
'''+text[end:]
        agents.write_text(text,encoding='utf-8')
    STATUS.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(args.task or OBJECTIVE)


if __name__=='__main__':main()
