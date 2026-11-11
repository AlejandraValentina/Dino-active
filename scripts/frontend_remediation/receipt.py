"""Revision-bound source acceptance; GUI runs and scientific acceptance stay distinct."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[2]
BASE='696b8fc1368e7ba6ecf3a2c25ab6359264ec80d9'
P9='openspec/changes/p9-experimental-validation/specs/p9-experimental-validation/spec.md'
P9_HASH='79fbe9b88d26fc4af5083d65d468f59c9208535f0ab389d2f3cb9a7654b88a4d'
MAIN_AT_START='48b3afe65ce94fc45b8a2974dd7ea64925ed4f1d'


def git(*args):
    return subprocess.check_output(['git',*args],cwd=ROOT)


def sha(raw):return hashlib.sha256(raw).hexdigest()


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--artifacts',type=Path,required=True)
    args=parser.parse_args();out=ROOT/'results/frontend-remediation-v1'
    checks={}
    summaries={}
    for name in ('frm-source-acceptance-final','frm-commercial-regression-final','frm-protected-accepted'):
        path=out/'verification'/f'{name}.summary.json'
        summary=json.loads(path.read_text(encoding='utf-8'));summaries[name]=summary
        checks[name]=summary['exit_code']==0 and not summary['timed_out']
    changed=git('diff','--name-only',BASE,'--','motorsim').decode().splitlines()
    checks['application_only']=all(p.startswith('motorsim/desktop/') for p in changed)
    changed_tests=set(git('diff','--name-only',BASE,'--','tests').decode().splitlines())
    allowed_tests={'tests/test_frontend_integrity_remediation.py','tests/test_frontend_workflow_remediation.py',
                   'tests/test_desktop_four_stroke_shell.py'}
    checks['only_new_frontend_tests_and_explicit_shell_cleanup']=changed_tests<=allowed_tests
    protected=json.loads((ROOT/'results/platform-integration-audit-v1/checks/contract/contract-integrity.json').read_text())['selected_modules']
    checks['protected_test_modules_unchanged']=not changed_tests.intersection(p.replace('\\','/') for p in protected)
    checks['p9_worktree_canonical']=sha((ROOT/P9).read_bytes().replace(b'\r\n',b'\n'))==P9_HASH
    checks['p9_git_blob']=sha(git('show',f'HEAD:{P9}'))==P9_HASH
    main_now=git('rev-parse','main').decode().strip()
    branch=git('branch','--show-current').decode().strip()
    checks['isolated_remediation_branch']=branch=='feat/dino-frontend-remediation-v1'
    checks['source_increment_not_merged_into_main']=subprocess.run(
        ['git','merge-base','--is-ancestor','HEAD','main'],cwd=ROOT).returncode==1
    source={}
    for name in changed:
        source[name]=sha((ROOT/name).read_bytes().replace(b'\r\n',b'\n'))
    captures={str(p.relative_to(ROOT)).replace('\\','/'):sha(p.read_bytes()) for p in sorted((out/'captures').glob('*.png'))}
    checks['live_capture_set']=len(captures)>=35
    journal=args.artifacts/'interaction-journal.jsonl'
    journal_raw=journal.read_bytes();events=[json.loads(line) for line in journal_raw.splitlines()]
    reopened=[e for e in events if e.get('kind')=='final-process-reopen']
    checks['real_native_input_and_reopen']=bool(reopened) and reopened[-1]['bore_sent']==87 and reopened[-1]['integrity']=='VERIFIED'
    checks['live_save_failure_preserves_original']=any(e.get('kind')=='save-failure' and e.get('save_failure_preserved') for e in events)
    checks['eligible_presentation_comparison']=any(e.get('kind')=='synthetic-presentation-comparison' and e.get('not_solver_evidence') for e in events)
    result=dict(schema='DINO_FRONTEND_SOURCE_ACCEPTANCE_V1',base=BASE,
        source_commit=git('rev-parse','HEAD').decode().strip(),checks=checks,
        git_context=dict(branch=branch,main_at_start=MAIN_AT_START,main_at_acceptance=main_now,
            main_advanced_externally=main_now!=MAIN_AT_START,
            main_reflog=git('reflog','show','main','-5','--date=iso').decode().splitlines(),
            task_actions='No push, merge, reset or rebase; other worktrees preserved'),
        status='SOURCE_ACCEPTED' if all(checks.values()) else 'INCOMPLETE',
        lifecycle=dict(IMPLEMENTED=True,SOURCE_ACCEPTED=all(checks.values()),
            WINDOWS_ACCEPTED=False,PENDING_UAT=True),
        packaged_candidate='NOT_BUILT_NOT_ACCEPTED',review='SELF_REVIEW',
        scientific_validation='NOT_PERFORMED',predictive_capability='NOT_CLAIMED',
        scope='F0 integrity + F1 coherent source workflow; not all 23 findings closed',
        comparison_fixture='SYNTHETIC_PRESENTATION_UI_ONLY; not solver evidence',
        source_hashes=source,capture_sha256=captures,journal_sha256=sha(journal_raw),
        verification_summaries={name:dict(exit_code=s['exit_code'],tail=s['tail']) for name,s in summaries.items()})
    (out/'acceptance.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    # Persist a reviewable copy of the interaction record, not original projects.
    (out/'interaction-journal.jsonl').write_bytes(journal_raw)
    print(json.dumps(dict(status=result['status'],checks=checks),ensure_ascii=False))
    return 0 if all(checks.values()) else 1


if __name__=='__main__':raise SystemExit(main())
