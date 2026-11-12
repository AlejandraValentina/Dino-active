"""Revision/tree-bound frontend acceptance; does not alter product artifacts."""
import argparse,hashlib,json,os,subprocess
from pathlib import Path
import psutil
ROOT=Path(os.environ.get('DINO_FRONTEND_SOURCE_ROOT',Path(__file__).resolve().parents[2]))
BASE='97e40bd8e272943cb6818b7ba9f9e8bac60f837c'
P9='openspec/changes/p9-experimental-validation/specs/p9-experimental-validation/spec.md'
P9_SHA='79fbe9b88d26fc4af5083d65d468f59c9208535f0ab389d2f3cb9a7654b88a4d'


def read(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def sha(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--artifacts-root',type=Path,required=True);parser.add_argument('--round',default='v2');parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    root=args.artifacts_root;candidate=read(root/'candidate.json');folder=Path(candidate['folder']);build=read(folder/'build.json');source=read(root/'source-gate.json');commit=candidate['source_commit'];checks={};evidence={}
    for key in ('source-base','source-f23','windows-base','windows-f23','windows-cp1','windows-cp2','windows-recovery-uia'):
        name=key+'-'+args.round;path=root/name/'acceptance.json';data=read(path);terminal=read(root/(name+'-terminal.json'))
        checks[name]=data['result']=='PASS' and all(data['checks'].values()) and terminal['result']=='PASS' and not terminal['remaining_owned_processes']
        evidence[key]=dict(path=str(path.relative_to(root)),sha256=sha(path),checks=len(data['checks']),captures=len(data.get('captures',{})))
        if key in ('windows-base','windows-f23'):
            checks[key+'_actual_frozen']=data.get('frozen') is True and data['product']['version']=='0.1.0-rc14' and data['product']['source_commit']==commit
            checks[key+'_no_python_worker']=not any(p['name'].casefold().startswith('python') for p in terminal.get('observed_children',[]))
    advanced=read(root/('windows-f23-'+args.round)/'acceptance.json')
    checks['reference_recovery_isolation_in_actual_candidate']=all(advanced['checks'].get(k) for k in ('reference_projects_have_distinct_recovery_paths','reference_recovery_keeps_names'))
    checks['source_gate']=source['status']=='SOURCE_ACCEPTED' and all(source['checks'].values())
    checks['source_product_trees_match_build']=all(git('rev-parse',commit+':'+name).decode().strip()==tree for name,tree in source['product_trees'].items())
    checks['clean_build']=build['source_commit']==commit and not build['source_dirty'] and not build['trial'] and build['packaged_inputs_clean']
    checks['module_bytes_match']=all(sha(ROOT/name)==sha(folder/'_internal'/name) for name in candidate['module_bytes_match'])
    checks['product_source_unchanged_since_build']=not git('diff',commit,'--','motorsim','packaging').strip()
    checks['zip_executables_unchanged']=sha(candidate['zip'])==candidate['zip_sha256'] and all(sha(folder/name)==digest for name,digest in candidate['executables'].items())
    manifest=json.dumps(dict(files=build['packaged_inputs'],consumed_files=build['explicit_consumed_inputs']),ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')
    checks['packaged_input_manifest_digest']=hashlib.sha256(manifest).hexdigest()==build['packaged_input_manifest_sha256']
    checks['no_issued_licenses_or_private_keys']=not [p for p in folder.rglob('*') if p.is_file() and (p.suffix.casefold()=='.dinolicense' or 'private_key' in p.name.casefold() or 'private-key' in p.name.casefold())]
    checks['rc13_zip_unchanged']=sha(root.parent/'frontend-commercial-integration-v1/Windows/MotorSim-0.1.0-rc13-windows-x64-8712f290.zip')=='5c5b24e4960be4b27e4cce6a62142fecba8e246bee533242763aff9fb30ceac9'
    prior=read(root/'candidate-552a5673.json');checks['superseded_rc14_preserved']=sha(prior['zip'])==prior['zip_sha256'] and all(sha(Path(prior['folder'])/name)==digest for name,digest in prior['executables'].items())
    changed=git('diff','--name-only',BASE,commit,'--','motorsim').decode().splitlines()
    checks['scientific_sources_unchanged']=all(p.startswith('motorsim/desktop/') or p in {'motorsim/runtime.py','motorsim/dino_desktop.py'} for p in changed)
    checks['licensing_implementation_unchanged']=not git('diff',BASE,commit,'--','motorsim/licensing','motorsim/desktop/license_dialog.py','packaging/licenses').strip()
    protected=read(ROOT/'results/platform-integration-audit-v1/checks/contract/contract-integrity.json')['selected_modules']
    checks['protected_tests_unchanged']=not git('diff',BASE,commit,'--',*[p.replace('\\','/') for p in protected]).strip()
    checks['p9_frozen']=hashlib.sha256(git('show',commit+':'+P9)).hexdigest()==P9_SHA and hashlib.sha256((ROOT/P9).read_bytes().replace(b'\r\n',b'\n')).hexdigest()==P9_SHA
    checks['main_contains_consolidated_rc13']=subprocess.run(['git','merge-base','--is-ancestor',BASE,'main'],cwd=ROOT).returncode==0
    checks['prior_branches_preserved']=git('rev-parse','integration/dino-frontend-commercial-v1').decode().strip()==BASE and git('rev-parse','feat/dino-frontend-remediation-v1').decode().strip()=='9b7392e3073a443c424377bf01cf05563fdc8d34'
    checks['no_unresolved_merge']=not git('ls-files','-u').strip()
    for name in ('final-combined-source','protected-regression','reference-key-v2'):
        path=ROOT/'results/frontend-f2-f3-v1/verification'/(name+'.summary.json');data=read(path);checks[name]=data['exit_code']==0 and not data['timed_out'];evidence[name]=dict(path=str(path.relative_to(ROOT)),sha256=sha(path),tail=data['tail'])
    findings=read(ROOT/'results/frontend-f2-f3-v1/findings.json');checks['all23_findings_explicit']=len(findings['findings'])==23 and all(f.get('status') in ('CLOSED','PARTIAL','PENDING_UAT') for f in findings['findings'])
    visual=read(root/'visual-evidence.json');checks['visual_artifacts_verified']=all(sha(root/item['file'])==item['sha256'] for item in visual['artifacts'])
    general=read(ROOT/'results/frontend-commercial-integration-v1/general-regression.json');checks['general_debt_preserved']=general['classification']=='GENERAL_REGRESSION_NOT_GREEN' and general['baseline_failures']==general['integration_failures']
    alive=[]
    for path in root.glob('*-terminal.json'):
        terminal=read(path)
        for child in terminal.get('observed_children',[]):
            try:
                process=psutil.Process(child['pid'])
                if process.create_time()==child['created_at'] and process.is_running():alive.append(child)
            except psutil.Error:pass
        alive.extend(terminal.get('remaining_owned_processes',[]))
    checks['owned_processes_terminal']=not alive
    accepted=all(checks.values())
    result=dict(schema='DINO_FRONTEND_F23_ACCEPTANCE_V1',status='WINDOWS_ACCEPTED' if accepted else 'INCOMPLETE',source_commit=commit,validated_implementation_commit=source['source_commit'],branch=git('branch','--show-current').decode().strip(),checks=checks,evidence=evidence,candidate=candidate,states=dict(IMPLEMENTED=True,SOURCE_ACCEPTED=accepted,WINDOWS_ACCEPTED=accepted,PENDING_UAT=True,SCIENTIFIC_VALIDATION_NOT_PERFORMED=True,GENERAL_REGRESSION_NOT_GREEN=True),review='SELF_REVIEW',owned_processes_remaining=alive,findings_counts=findings['counts'],main_consolidation=read(ROOT/'results/frontend-f2-f3-v1/consolidation.json'),scope='Frontend/application engineering acceptance; native/reference remain separate. Real bounded runs are integration evidence, synthetic A/B fixtures remain synthetic. No full general-suite, human accessibility, CP3/CP4 or scientific validation claim.',push_performed=False)
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(status=result['status'],checks=checks,failed=[k for k,v in checks.items() if not v]),ensure_ascii=False));return 0 if accepted else 1


if __name__=='__main__':raise SystemExit(main())
