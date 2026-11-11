"""Check audit coverage, links, provenance and findings, not product acceptance."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import subprocess
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'results/frontend-audit-v1'
BASE='d44305c24ec81d9b767305d319a660c0c034e5c9'


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--artifacts',type=Path,required=True)
    args=parser.parse_args()
    checks={}
    payload=json.loads((OUT/'findings.json').read_text(encoding='utf-8'))
    findings=payload['findings']
    ids={f['id'] for f in findings}
    checks['unique_23_findings']=len(ids)==len(findings)==23
    checks['priorities']=dict(Counter(f['priority'] for f in findings))=={
        'P0':3,'P1':11,'P2':7,'P3':2}
    checks['seven_categories']=set(f['category'] for f in findings)=={
        'Confusión o dificultad de uso','Funcionalidad poco visible',
        'Flujo incompleto','Inconsistencia entre módulos','Problema de visualización',
        'Funcionalidad faltante','Defecto funcional'}
    required=['observation','impact','probable_cause','evidence','components',
              'layer','expected_outcome','acceptance','verification']
    checks['all_backlog_fields']=all(all(f.get(k) for k in required) and
        len(f['acceptance'])>=3 and f['implementation_state']=='PROPOSED_NOT_ACTIVATED'
        for f in findings)
    graph={f['id']:f['dependencies'] for f in findings}
    def visit(node,path=()):
        if node in path or node not in ids:return False
        return all(visit(dep,(*path,node)) for dep in graph[node])
    checks['dependency_dag']=all(visit(node) for node in ids)
    checks['component_paths_exist']=all((ROOT/p).is_file()
        for f in findings for p in f['components'])
    checks['primary_evidence_exists']=all(tag.startswith('p') and
        (OUT/'captures'/(tag+'.png')).is_file() and
        (OUT/'captures'/(tag+'.json')).is_file()
        for f in findings for tag in f['evidence'])
    index=json.loads((OUT/'evidence-index.json').read_text(encoding='utf-8'))
    checks['capture_hashes']=all(hashlib.sha256((ROOT/c['path']).read_bytes()).hexdigest()
                                ==c['sha256'] for c in index['captures'])
    checks['actual_windows_captures']=all(c['platform']=='windows'
        for c in index['captures'] if c['id'].startswith('p'))
    broken=[]
    for path in (ROOT/'docs/frontend-audit-v1').glob('*.md'):
        for target in re.findall(r'\]\(([^)]+)\)',path.read_text(encoding='utf-8')):
            if target.startswith(('https://','http://','#')):continue
            if not (path.parent/target.split('#')[0]).is_file():
                broken.append([path.name,target])
    checks['local_document_links']=not broken
    entries=[json.loads(line) for line in (OUT/'evidence/interactions-pinned.jsonl')
             .read_text(encoding='utf-8').splitlines() if line.strip()]
    responses=[e['response'].get('result') for e in entries
               if e['kind']=='response' and e['response'].get('ok')]
    results=[r for r in responses if isinstance(r,dict)]
    checks['p0_unapplied_real_submission']=any(
        r.get('staged',{}).get('table_bore')=='87' and
        r.get('staged',{}).get('active_bore')==86 and r.get('submitted_bore')==86
        for r in results) and any(r.get('draft_after_run')=='86' for r in results)
    checks['p0_bundle_real_import']=any(
        len(r.get('bundle_import_assessments',[]))==2 and
        all(a['classification']=='UNAVAILABLE' for a in r['bundle_import_assessments'])
        for r in results)
    checks['p0_save_real_failure']=any(e['kind']=='native-save-after-import' and
        e['before']['path_type']=='str' and e['after']['dirty'] and
        e['after']['ui_refs']>e['after']['file_refs'] and not e['ui_error_dialog']
        for e in entries) and "'str' object has no attribute 'suffix'" in (
            OUT/'evidence/driver-pinned.stderr.log').read_text(encoding='utf-8')
    checks['recovery_copy_original_intact']=any(e['kind']=='recovery-outcome' and
        e['outcome']['copy_path']=='None' and e['outcome']['copy_bore']==57 and
        e['outcome']['original_sha256_unchanged'] for e in entries)
    checks['real_pdf_export']=any(r.get('pdf_bytes',0)>1000 for r in results)
    runtime=json.loads((OUT/'evidence/runtime-final.json').read_text(encoding='utf-8'))
    checks['no_active_audit_workers_at_end']=runtime['thread_pool_active']==0 and not any(
        runtime[k] for k in ['native_running','reference_running','2t_running'])
    checks['fixed_runtime']=runtime['qt']=='6.11.2' and runtime['platform']=='windows'
    diff=subprocess.check_output(['git','diff',BASE,'--','motorsim','tests',
                                  'packaging','configs','examples'],cwd=ROOT,text=True)
    checks['no_product_test_or_fixture_changes']=not diff.strip()
    p9=ROOT/'openspec/changes/p9-experimental-validation/specs/p9-experimental-validation/spec.md'
    # The repository's existing program_status check defines this digest over
    # LF-normalized worktree bytes. Also bind it to the exact frozen Git blob.
    frozen_p9=subprocess.check_output(['git','show',BASE+':'+p9.relative_to(ROOT).as_posix()],cwd=ROOT)
    normalized_p9=p9.read_bytes().replace(b'\r\n',b'\n')
    checks['frozen_p9_sha256']=hashlib.sha256(normalized_p9).hexdigest()==(
        '79fbe9b88d26fc4af5083d65d468f59c9208535f0ab389d2f3cb9a7654b88a4d')
    checks['frozen_p9_git_blob_sha256']=hashlib.sha256(frozen_p9).hexdigest()==(
        '79fbe9b88d26fc4af5083d65d468f59c9208535f0ab389d2f3cb9a7654b88a4d')
    checks['frozen_p9_worktree_matches_blob']=normalized_p9==frozen_p9
    checks['legacy_original_bytes_intact']=all(
        (ROOT/'results/dino4t-stage2-v1/example/8000rpm'/name).read_bytes()==
        (args.artifacts/'legacy-stage2-copy'/name).read_bytes()
        for name in ['summary.json','config_resolved.json','trace_last_cycle.csv'])
    checks['three_svg_previews']=all(
        ET.parse(ROOT/'docs/frontend-audit-v1/wireframes'/(name+'.svg')) is not None
        and (ROOT/'docs/frontend-audit-v1/wireframes'/(name+'.png')).is_file()
        for name in ['modelo','simulacion','resultados'])
    branch=subprocess.check_output(['git','branch','--show-current'],cwd=ROOT,text=True).strip()
    checks['isolated_audit_branch']=branch=='audit/dino-frontend-ux-v1'
    report=dict(schema='DINO_FRONTEND_AUDIT_DELIVERY_CHECK_V1',
        product_revision=BASE,review_type='SELF_REVIEW',checks=checks,
        broken_links=broken,result='PASS' if all(checks.values()) else 'FAIL',
        qualification='Checks audit artifacts and observed evidence only. Not product acceptance, independent review or scientific validation.',
        prototype_browser_qa='UNAVAILABLE',
        main_reference_at_review=subprocess.check_output(['git','rev-parse','main'],cwd=ROOT,text=True).strip())
    (OUT/'delivery-check.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    files=[]
    for path in sorted(args.artifacts.rglob('*')):
        if path.is_file():
            files.append(dict(path=path.relative_to(args.artifacts).as_posix(),
                size=path.stat().st_size,sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    (OUT/'external-artifacts-manifest.json').write_text(json.dumps(dict(
        schema='DINO_FRONTEND_AUDIT_EXTERNAL_ARTIFACTS_V1',
        root_locator='Set AUDIT_ARTIFACT_ROOT to the retained pinned-session directory; see local receipt.',
        files=files),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(result=report['result'],checks_passed=sum(checks.values()),
                         checks_total=len(checks),failed=[k for k,v in checks.items() if not v],
                         broken_links=broken),ensure_ascii=False))
    return 0 if all(checks.values()) else 1


if __name__=='__main__':raise SystemExit(main())
