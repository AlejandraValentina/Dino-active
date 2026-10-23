"""Owner-scoped delivery demonstration using the existing RPM coordinator.

No solver implementation or alternative sweep engine. Historical inputs stay
read-only; coordinator-owned copies receive conservative continuations.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys
import threading
import time

sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from motorsim import engineering_point as point
from motorsim.engine_configuration import implementation_source_hashes
from motorsim.engine_project import load_project,save_project
from motorsim.engineering_workflow import import_desktop_runs
from motorsim.integrated_2t import IntegratedEngine2T
from motorsim.power_curve_sweep import prepare_power_curve,run_power_curve

ORDER=[('B_header_plus20',9000),('A_original',8000),('B_header_plus20',8000),('A_original',10000),('B_header_plus20',10000)]
POLICY=dict(schema='POWERVALVE_OPEN_ENDPOINT_HOLD_V1',maximum_rpm=10000)
CAPS={'A_original':1300,'B_header_plus20':1900}


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path,data):point.atomic(path,data)


def prepare(a):
    from motorsim.desktop.preferences import repository_root_containing
    if repository_root_containing(a.artifacts.resolve()) is not None:
        raise ValueError('artifacts must be external')
    a.artifacts.mkdir(parents=True,exist_ok=False)
    project=load_project(a.source_project)
    sources=[]
    for ref in project['result_references']:
        path=Path(ref['path']);path=path/'result.json' if path.is_dir() else path
        assert sha(path)==ref['artifact_sha256']
        r=json.loads(path.read_bytes());root=path.parent
        assert r['source_hashes']==implementation_source_hashes()
        import_desktop_runs([root])
        m=json.loads((root/r['attempt']/'manifest.json').read_bytes())
        cfg=json.loads((root/'native-configuration.json').read_bytes())
        args=argparse.Namespace(config=root/'native-configuration.json',rpm=r['preflight']['rpm'],
            resume_manifest=root/r['attempt']/'manifest.json',parent_runner=root/r['attempt']/'producer.py')
        engine=IntegratedEngine2T.from_configuration_dict(cfg)
        _,_,_,restored=point.restore_parent(engine,cfg,args)
        sources.append(dict(variant=r['bindings']['variant_label'],rpm=r['preflight']['rpm'],
            result=str(path),result_sha256=sha(path),checkpoint_sha256=r['checkpoint_sha256'],
            elapsed_seconds=r['elapsed_seconds'],zero_step_restore=restored))
    assert len(sources)==6 and {(s['variant'],s['rpm']) for s in sources}=={(v,r) for v in CAPS for r in (8000,9000,10000)}
    # Package the already-computed A9000 manifest in the existing Desktop schema.
    # This is derived metadata, not a rerun or a change to scientific evidence.
    original=Path(next(s['result'] for s in sources if s['variant']=='A_original' and s['rpm']==9000)).parent
    target=a.artifacts/'exploratory-workflow-v1'/project['project_id']/original.name
    shutil.copytree(original,target)
    shutil.copytree(a.periodic_a,target/'invocation-002')
    m=json.loads((target/'invocation-002/manifest.json').read_bytes())
    assert m['status']=='PERIODIC_EXPLORATORY' and m['cycles_completed']==104
    assert m['continuation']['manifest_sha256']==sha(original/'invocation-001/manifest.json')
    from motorsim.exploratory_workflow import preflight
    check=preflight(project['variants']['A_original'],rpm=9000,max_cycles=110,budget_seconds=600,memory_limit_mib=512)
    r=json.loads((original/'result.json').read_bytes())
    assert check['identity_sha256']==r['bindings']['identity_sha256']
    r.update(status='COMPLETE',classification=m['status'],periodicity=m['periodicity'],
        attempt='invocation-002',invocations=2,preflight=check,cycles=m['cycles'],cycles_completed=104,
        diagnostic_manifest_sha256=sha(target/'invocation-002/manifest.json'),
        elapsed_seconds=r['elapsed_seconds']+m['wall_s'],artifact_directory=str(target),
        checkpoint_artifact='invocation-002/'+m['checkpoint_artifact'],checkpoint_sha256=m['checkpoint_sha256'])
    shutil.copyfile(target/r['checkpoint_artifact'],target/'checkpoint.json')
    result_hash=point.atomic(target/'result.json',r);save(target/'run.json',dict(r,result_sha256=result_hash))
    import_desktop_runs([target])
    project['result_references'].append(dict(path=str(target/'result.json'),artifact_sha256=result_hash,
        identity_sha256=r['bindings']['identity_sha256'],classification=r['classification']))
    save_project(a.artifacts/'periodic-rpm-curves.dino.json',project)
    checks={v:prepare_power_curve(project['variants'][v],project_id=project['project_id'],variant_label=v,
        artifact_root=a.artifacts,start_rpm=8000,stop_rpm=10000,step_rpm=1000,max_cycles=111,
        point_budget_seconds=600,total_budget_seconds=CAPS[v],memory_limit_mib=512,control_policy=POLICY) for v in CAPS}
    save(a.artifacts/'preflight.json',dict(solver_steps=0,sources=sources,checks=checks,periodic_a=str(target),
        global_new_wall_cap_s=3300,point_new_wall_cap_s=600,order=ORDER,source_hashes=implementation_source_hashes()))
    print(json.dumps(dict(preflight='PASS',solver_steps=0,sources=len(sources),periodic_a_reused=True)),flush=True)


def execute(a):
    pre=json.loads((a.artifacts/'preflight.json').read_bytes())
    assert pre['source_hashes']==implementation_source_hashes()
    for s in pre['sources']:assert sha(Path(s['result']))==s['result_sha256']
    # Exclusive marker prevents accidentally repeating this demonstration/resetting its budget.
    with (a.artifacts/'execution-started.json').open('x',encoding='utf-8') as f:
        json.dump(dict(started_unix=time.time(),global_new_wall_cap_s=3300),f)
    project=load_project(a.artifacts/'periodic-rpm-curves.dino.json');start=time.monotonic()
    receipt=dict(schema='DINO_PERIODIC_RPM_CURVES_DEMO_V1',status='RUNNING',completed=[],new_wall_s=0.,global_cap_s=3300)
    for variant,rpm in ORDER:
        cancel=threading.Event();remaining=3300-(time.monotonic()-start)
        if remaining<1:receipt['status']='GLOBAL_BUDGET_EXHAUSTED';break
        timer=threading.Timer(remaining,cancel.set);timer.daemon=True;timer.start()
        expected=next(s for s in pre['sources'] if s['variant']==variant and s['rpm']==rpm)
        def progress(row):
            if row.get('point') is not None:
                assert row['rpm']==rpm,'coordinator executed out of authorized order'
                cancel.set()
        sid='periodic-'+('A' if variant=='A_original' else 'B')
        series_path=a.artifacts/'dino-power-curve-v1'/project['project_id']/sid/'series.json'
        try:
            series=run_power_curve(project['variants'][variant],project_id=project['project_id'],variant_label=variant,
                artifact_root=a.artifacts,start_rpm=8000,stop_rpm=10000,step_rpm=1000,max_cycles=111,
                point_budget_seconds=600,total_budget_seconds=CAPS[variant],memory_limit_mib=512,
                sweep_id=sid,resume=series_path.exists(),cancel_event=cancel,progress=progress,
                continuation_runs=[Path(s['result']).parent for s in pre['sources'] if s['variant']==variant and not (variant=='A_original' and s['rpm']==9000)],
                reuse_runs=[pre['periodic_a']] if variant=='A_original' else [],control_policy=POLICY,
                execution_order=[9000,8000,10000] if variant=='B_header_plus20' else [8000,9000,10000])
            row=next(p for p in series['points'] if p['rpm']==rpm)
            path=Path(row['run_directory'])/'result.json';r=json.loads(path.read_bytes())
            assert r['cycles_completed']>30 and row['continuation_source']['result_sha256']==expected['result_sha256']
            receipt['completed'].append(dict(variant=variant,rpm=rpm,result=str(path),sha256=sha(path),
                classification=r['classification'],periodicity=r['periodicity'],cycles=r['cycles_completed'],
                new_wall_s=row['continuation_elapsed_seconds'],total_point_wall_s=r['elapsed_seconds']))
            project['result_references'].append(dict(path=str(path),artifact_sha256=sha(path),
                identity_sha256=r['bindings']['identity_sha256'],classification=r['classification']))
            save_project(a.artifacts/'periodic-rpm-curves.dino.json',project)
            if r['classification']=='STOPPED_ERROR':raise RuntimeError(r['failure'])
        except BaseException as exc:
            receipt.update(status='STOPPED_ERROR',failure=repr(exc));raise
        finally:
            timer.cancel();receipt['new_wall_s']=time.monotonic()-start;save(a.artifacts/'execution-receipt.json',receipt)
        print(json.dumps(receipt['completed'][-1]),flush=True)
    else:receipt['status']='AUTHORIZED_POINTS_FINISHED'
    receipt['new_wall_s']=time.monotonic()-start;save(a.artifacts/'execution-receipt.json',receipt)
    print(json.dumps(receipt),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--artifacts',type=Path,required=True)
    p.add_argument('--source-project',type=Path)
    p.add_argument('--periodic-a',type=Path)
    p.add_argument('--execute',action='store_true')
    a=p.parse_args()
    execute(a) if a.execute else prepare(a)
