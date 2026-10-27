"""Replay existing27-30 recipes, audit full stages, rebuild the original detector."""
import argparse
import gc
import json
from pathlib import Path
import sys
import tempfile
import time
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from motorsim.integrated_2t import IntegratedEngine2T,_solver_dependency_hashes,_json_evidence_equal,make_integrated_cycle_primary,audit_integrated_cycle_primary
from motorsim.reference_harness.convergence import PeriodicDetectorV2,CONTRACT
from motorsim._evidence_io import write_primary_atomic
from scripts.agents.storage_preflight import check_storage_requirements,default_artifact_root
from scripts.diagnostics.diagnose_integrated_mesh_v1 import sha,write


def load(path):return json.loads(path.read_text(encoding='utf-8'))


def primary_observation_record(primary):
    # V2 versions detector semantics; cycle-data records retain V1 identity.
    # Preserve the source contract, never relabel a record to bypass checking.
    if primary.get('contract')!=CONTRACT:raise ValueError('unsupported primary data contract')
    return dict(contract=primary['contract'],cycle_index=primary['cycle_index'],
        configuration_hash=primary['configuration_hash'],observables=primary['observables'])


def bound_file(directory,name):
    manifest=load(directory.parent/'manifest.json');hashes={k.replace('\\','/'):v for k,v in manifest['files'].items()}
    path=directory/name
    if sha(path)!=hashes['run/'+name]:raise ValueError('source hash mismatch: '+name)
    return path


def read_bound_cycle(root,cycle):
    if cycle not in (27,28,29,30):raise ValueError('only existing27-30 cycles')
    old=root/'periodicity-extension-v4/run';new=root/'periodicity-cycle30-control-v1/run'
    source=new if cycle==30 else old
    start_path=bound_file(old,f'checkpoint-{cycle-1:03}.json');end_path=bound_file(source,f'checkpoint-{cycle:03}.json')
    receipt=load(bound_file(source,'receipt.json'));recipe_path=bound_file(source,'recipe.json')
    config_path=root/'spatial-boundary-v2-engine/configuration.json'
    if receipt['solver_dependency_sha256']!=_solver_dependency_hashes() or receipt['configuration_sha256']!=sha(config_path):raise ValueError('source/config mismatch')
    rows=[r for r in load(recipe_path) if r['angle_start_deg']>=360.*(cycle-1) and r['angle_end_deg']<=360.*cycle]
    if not rows or rows[0]['angle_start_deg']!=360.*(cycle-1) or rows[-1]['angle_end_deg']!=360.*cycle:raise ValueError('incomplete recipe')
    if any(a['angle_end_deg']!=b['angle_start_deg'] for a,b in zip(rows,rows[1:])):raise ValueError('recipe gap')
    return load(config_path),load(start_path),load(end_path),rows,dict(start_sha256=sha(start_path),end_sha256=sha(end_path),recipe_sha256=sha(recipe_path))


def run(root,out,artifacts):
    preflight=check_storage_requirements([(out,4*1024**2),(artifacts,512*1024**2),(Path(tempfile.gettempdir()),256*1024**2)])
    if out.exists() or artifacts.exists():raise FileExistsError('preserve earlier audit')
    # Verify all inputs before making any output directory.
    sources={i:read_bound_cycle(root,i) for i in (27,28,29,30)}
    history=load(bound_file(root/'periodicity-cycle30-control-v1/run','detector.json'))['history']
    detector=PeriodicDetectorV2()
    for record in history[:26]:detector.update(record)
    out.mkdir(parents=True);artifacts.mkdir(parents=True)
    start=time.perf_counter();records=[];status='STOPPED';error=None
    try:
        for cycle in (27,28,29,30):
            if time.perf_counter()-start>=360:raise TimeoutError('no admission after360s;480s invocation limit')
            began=time.perf_counter();config,cp,expected,recipe,binding=sources[cycle]
            engine=IntegratedEngine2T.from_configuration_dict(config);engine.restore(cp);engine.enable_trajectory_spooling(artifacts)
            rejections=[]
            for row in recipe:
                if time.perf_counter()-began>=120:raise TimeoutError('cycle replay admission120s')
                for attempt in row['rejected_proposals']:
                    delta=attempt['step_deg']
                    try:engine.step(delta/(6*9000.),delta,capture_trace=True)
                    except ValueError as exc:
                        if str(exc)!=attempt['error']:raise ValueError('rejection differs from recipe') from exc
                        rejections.append(dict(angle_deg=row['angle_start_deg'],attempted_step_deg=delta,reason=str(exc)))
                    else:raise ValueError('recorded rejected proposal accepted')
                actual=engine.step(row['dt_s'],row['angle_end_deg']-row['angle_start_deg'],capture_trace=True)
                if not all(_json_evidence_equal(actual[k],v) for k,v in row.items() if k!='rejected_proposals'):raise ValueError('accepted recipe mismatch')
            end=engine.snapshot(streaming=True)
            if not _json_evidence_equal(engine.state,expected['state']) or not _json_evidence_equal(engine.ledger,expected['ledger']):raise ValueError('terminal physical state/ledger differs')
            for key in ('time_s','angle_deg','fuel_combustion','p7'):
                if not _json_evidence_equal(end.get(key),expected.get(key)):raise ValueError('terminal clock/event differs')
            primary=make_integrated_cycle_primary(engine,cp,end,cycle,rejected_trials=rejections,runner_sha256=sha(Path(__file__)))
            path=artifacts/f'cycle-{cycle:03}.json.gz'
            exported=write_primary_atomic(path,primary,maximum_bytes=128*1024**2)
            audit=audit_integrated_cycle_primary(primary,preserve_precycle_p7_baseline=True)
            if audit['status']!='PASS':raise ValueError('primary audit failed')
            record=primary_observation_record(primary)
            outcome=detector.update(record)
            entry=dict(cycle=cycle,status='PASS',wall_s=time.perf_counter()-began,accepted_steps=len(recipe),source=binding,
                artifact_name=path.name,compressed_sha256=sha(path),**exported,audit=audit,periodicity_outcome=outcome,conservation=primary['conservation'])
            records.append(entry);write(out/f'cycle-{cycle:03}-audit.json',entry);write(out/'progress.json',dict(completed=[r['cycle'] for r in records],wall_s=time.perf_counter()-start))
            del primary,end,engine;gc.collect()
            if entry['wall_s']>120:raise TimeoutError('completed cycle exceeded120s; no further admission')
        if detector.detected_period!=1 or detector.converged_cycle!=30:raise ValueError('primary detector decision differs')
        status='PASS'
    except Exception as exc:error=f'{type(exc).__name__}: {exc}'
    result=dict(schema='AUDITED_PERIODIC_PRIMARY_RECONSTRUCTION_V1',status=status,error=error,wall_s=time.perf_counter()-start,
        cycles=[r['cycle'] for r in records],durable_artifact_root=str(artifacts.resolve()),storage_preflight=preflight,
        detector=detector.snapshot(),source_solver_sha256=_solver_dependency_hashes(),runner_sha256=sha(Path(__file__)),
        periodicity_audited=(status=='PASS'),mesh_independence=False,experimental_validation=False,review='SELF_REVIEW')
    write(out/'receipt.json',result);print(json.dumps({k:result[k] for k in ('status','error','wall_s','cycles','periodicity_audited')}))
    return 0 if status=='PASS' else 1


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    raise SystemExit(run(a.root,a.output,default_artifact_root()/'predictive-reliability-v1'/'periodic-primary-audit-v1'))
