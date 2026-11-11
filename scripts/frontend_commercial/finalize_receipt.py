"""Verify source/package provenance and combine independently recorded gates."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import psutil

ROOT=Path(__file__).resolve().parents[2]
COMMERCIAL='f97469ba6705555e73f6624482564d193e43a101'
FRONTEND='9b7392e3073a443c424377bf01cf05563fdc8d34'
P9='openspec/changes/p9-experimental-validation/specs/p9-experimental-validation/spec.md'
P9_SHA='79fbe9b88d26fc4af5083d65d468f59c9208535f0ab389d2f3cb9a7654b88a4d'


def sha(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def read(path):return json.loads(Path(path).read_text(encoding='utf-8'))


def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--artifacts-root',type=Path,required=True)
    parser.add_argument('--build-commit',required=True);args=parser.parse_args()
    root=args.artifacts_root;candidate=read(root/'candidate.json');bundle=Path(candidate['folder'])
    build=read(bundle/'build.json');checks={};evidence={}
    receipts={'source':'source-clean-v2/acceptance.json','packaged':'packaged-qt/acceptance.json',
              'cp1':'packaged-cp1/acceptance.json','cp2':'packaged-cp2/acceptance.json',
              'recovery':'recovery-invoke-v2/acceptance.json','recents':'packaged-recents.json'}
    for name,path in receipts.items():
        data=read(root/path);checks[name+'_acceptance']=data['result']=='PASS'
        evidence[name]=dict(path=path,sha256=sha(root/path),checks=data.get('checks'))
    source=read(root/'source-gate.json');packaged=read(root/receipts['packaged'])
    checks['clean_source_gate']=source['status']=='SOURCE_ACCEPTED' and source['source_commit']==args.build_commit
    checks['actual_frozen_windows_execution']=packaged['frozen'] and packaged['qt_platform']=='windows'
    checks['packaged_commit_and_version']=packaged['product']['source_commit']==args.build_commit and packaged['product']['version']==build['app_version']=='0.1.0-rc13'
    checks['clean_matching_build']=build['source_commit']==args.build_commit and not build['source_dirty'] and build['packaged_inputs_clean']
    for name in ['combined-focused-first','native-curve-callback-contract','integrated-protected']:
        path=ROOT/'results/frontend-commercial-integration-v1/verification'/f'{name}.summary.json'
        data=read(path);checks[name]=data['exit_code']==0 and not data['timed_out']
        evidence[name]=dict(path=str(path.relative_to(ROOT)),sha256=sha(path),tail=data['tail'])
    # Include failed diagnostic attempts in the cleanup check, without treating
    # their outcomes as passing acceptance evidence.
    owned_alive=[]
    for path in root.glob('*-terminal.json'):
        terminal=read(path)
        if terminal.get('remaining_owned_processes'):owned_alive.extend(terminal['remaining_owned_processes'])
        for child in terminal.get('observed_children',[]):
            try:
                p=psutil.Process(child['pid'])
                if p.create_time()==child['created_at'] and p.is_running():owned_alive.append(child)
            except psutil.Error:pass
    for path in ['source-clean-v2-terminal.json','packaged-terminal.json','packaged-cp1-terminal.json','packaged-cp2-terminal.json','recovery-invoke-v2-terminal.json']:
        t=read(root/path);checks[path]=t['result']=='PASS' and t['exit_code']==0 and not t['remaining_owned_processes']
    checks['no_owned_processes_remain']=not owned_alive and read(root/'probe-cleanup.json')['closed']
    checks['no_external_python_worker_in_packaged_walkthrough']=not any(c['name'].casefold().startswith('python') for c in read(root/'packaged-terminal.json')['observed_children'])
    checks['zip_and_executables_unchanged']=sha(candidate['zip'])==candidate['zip_sha256'] and all(sha(bundle/n)==h for n,h in candidate['executables'].items())
    manifest=json.dumps({'files':build['packaged_inputs'],'consumed_files':build['explicit_consumed_inputs']},ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')
    checks['input_manifest_digest']=hashlib.sha256(manifest).hexdigest()==build['packaged_input_manifest_sha256']
    checks['critical_modules_match_source']=all(sha(ROOT/n)==sha(bundle/'_internal'/n) for n in candidate['module_bytes_match'])
    checks['product_source_unchanged_after_build']=not git('diff','--name-only',args.build_commit,'--','motorsim','packaging').strip()
    changed=git('diff','--name-only',COMMERCIAL,args.build_commit,'--','motorsim').decode().splitlines()
    checks['scientific_sources_unchanged']=all(p.startswith('motorsim/desktop/') or p in {'motorsim/runtime.py','motorsim/dino_desktop.py'} for p in changed)
    protected=read(ROOT/'results/platform-integration-audit-v1/checks/contract/contract-integrity.json')['selected_modules']
    checks['protected_tests_unchanged']=not git('diff','--name-only',COMMERCIAL,args.build_commit,'--',*[p.replace('\\','/') for p in protected]).strip()
    checks['p9_git_and_worktree']=hashlib.sha256(git('show',args.build_commit+':'+P9)).hexdigest()==P9_SHA and hashlib.sha256((ROOT/P9).read_bytes().replace(b'\r\n',b'\n')).hexdigest()==P9_SHA
    checks['original_branch_refs_preserved']=git('rev-parse','main').decode().strip()==COMMERCIAL and git('rev-parse','feat/dino-frontend-remediation-v1').decode().strip()==FRONTEND
    checks['no_unresolved_merge']=not git('ls-files','-u').strip()
    checks['no_issued_license_or_private_key_files']=not candidate['private_key_or_license_files']
    general=read(ROOT/'results/frontend-commercial-integration-v1/general-regression.json')
    checks['general_regression_honestly_not_green']=general['classification']=='GENERAL_REGRESSION_NOT_GREEN' and general['baseline_failures']==general['integration_failures']
    accepted=all(checks.values())
    receipt=dict(schema='DINO_FRONTEND_CP2_INTEGRATION_ACCEPTANCE_V1',source_commit=args.build_commit,
        parents=dict(commercial=COMMERCIAL,frontend=FRONTEND),branch=git('branch','--show-current').decode().strip(),
        status='WINDOWS_ACCEPTED' if accepted else 'INCOMPLETE',checks=checks,evidence=evidence,
        states=dict(SOURCE_ACCEPTED=accepted,WINDOWS_ACCEPTED=accepted,GENERAL_REGRESSION_NOT_GREEN=True,PENDING_UAT=True,SCIENTIFIC_VALIDATION_NOT_PERFORMED=True),
        candidate=candidate,owned_processes_remaining=owned_alive,review='SELF_REVIEW',
        external_keyboard_route='NOT_ACCEPTED_LOCAL_HARNESS: Windows foreground/native picker automation unreliable. Failed attempts retained. Packaged Qt workflows, CP1/CP2, persisted recents and external UIA Invoke recovery accepted separately.',
        scope='F0/F1 + CP0-CP2 functional engineering candidate; not full-suite green, human accessibility UAT, CP3/CP4, or numerical/experimental validation.',
        main_recommendation='Suitable for a separately reviewed functional integration preserving general-regression/UAT/scientific pending classifications. No main merge or push performed.')
    path=ROOT/'results/frontend-commercial-integration-v1/acceptance.json'
    path.write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(status=receipt['status'],checks=checks),ensure_ascii=False))
    return 0 if accepted else 1


if __name__=='__main__':raise SystemExit(main())
