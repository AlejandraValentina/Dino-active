"""First bounded88-grid periodicity window, independently initialized/detected."""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import sys
import time
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from motorsim.integrated_2t import IntegratedEngine2T,_solver_dependency_hashes,_integrated_scheduled_angles,_integrated_nominal_step_end,_json_evidence_equal
from motorsim.reference_harness.convergence import PeriodicDetectorV2
from motorsim.port_connection_v2 import NoAdmissiblePortState
from scripts.diagnostics.remap_representation_v1 import initialize
from scripts.diagnostics.relative_cycle_observations_v1 import relative_observations
from scripts.diagnostics.periodicity_extension_v4 import conserved
from scripts.diagnostics.diagnose_integrated_mesh_v1 import sha,write
from scripts.agents.storage_preflight import check_storage_requirements


def load(p):return json.loads(p.read_text(encoding='utf-8'))


def prepare(root):
    audit=root/'periodic-primary-audit-v1';manifest=load(audit/'manifest.json')
    def bound(name):
        if sha(audit/name)!=manifest['files'][name]:raise ValueError('periodic audit changed')
        return load(audit/name)
    decision=bound('reconstruction/receipt.json');entry=bound('run/cycle-030-audit.json')
    if decision['status']!='PASS' or decision['periodicity_audited'] is not True or decision['detector']['detected_period']!=1 or decision['detector']['converged_cycle']!=30:
        raise ValueError('audited periodic source required')
    cp_path=root/'periodicity-cycle30-control-v1/run/checkpoint-030.json';config_path=root/'spatial-boundary-v2-engine/configuration.json'
    if sha(cp_path)!=entry['source']['end_sha256'] or entry['audit']['solver_dependency_sha256']!=_solver_dependency_hashes():raise ValueError('source state/dependencies differ')
    config=load(config_path);cp=load(cp_path);coarse=IntegratedEngine2T.from_configuration_dict(config);coarse.restore(cp)
    if coarse.configuration_identity['configuration_sha256']!=entry['audit']['configuration_hash']:raise ValueError('source configuration differs')
    engine,fine,remap=initialize(config,cp,1,'P0',sha(cp_path))
    if not conserved(engine.conservation_report()) or not _json_evidence_equal(engine.snapshot()['fuel_combustion'],cp['fuel_combustion']):raise ValueError('remap/history inconsistency')
    return engine,fine,PeriodicDetectorV2(),dict(source_checkpoint_sha256=sha(cp_path),source_configuration_sha256=sha(config_path),
        source_audited_decision_sha256=sha(audit/'reconstruction/receipt.json'),initialization=remap,origin_absolute_cycle=30,
        physical_origin_crank_deg=engine.crank_angle_unwrapped_deg,first_detector_cycle_index=1)


def statistics(comparison):
    values=sorted(v['value']/v['threshold'] for v in comparison.get('metrics',{}).values())
    if not values:return None
    import numpy as np
    return dict(maximum=max(values),p90=float(np.quantile(values,.9)),median=float(np.median(values)),failed=sum(x>1 for x in values),count=len(values))


def run(root,out,*,source_preparer=None,first_absolute=31,last_absolute=36,solver_budget=260,admission_budget=290,schema='REFINED88_PERIODICITY_PILOT_V1'):
    if not 1<=last_absolute-first_absolute+1<=6 or not 0<solver_budget<=admission_budget<=290:raise ValueError('invalid bounded window')
    preflight=check_storage_requirements([(out,16*1024**2)])
    if out.exists():raise FileExistsError('preserve earlier pilot')
    start=time.perf_counter();timing=dict(restoration=0.,solver=0.,detector=0.,serialization=0.,balances=0.)
    engine,config,detector,provenance=(source_preparer or prepare)(root);timing['restoration']=time.perf_counter()-start
    origin=provenance['origin_absolute_cycle']
    if engine.crank_angle_unwrapped_deg!=360.*(first_absolute-1) or len(detector.history)!=first_absolute-1-origin:raise ValueError('source phase/detector origin differs')
    prefix=[];expected_partial=None;prefix_index=0;replayed=True;prior_cycles=[]
    for path in provenance.get('source_previous_cycles_paths',[]):prior_cycles.extend(load(Path(path)))
    if 'source_partial_path' in provenance:
        partial_path=Path(provenance['source_partial_path']);recipe_path=Path(provenance['source_partial_recipe_path'])
        if sha(partial_path)!=provenance['source_partial_sha256'] or sha(recipe_path)!=provenance['source_partial_recipe_sha256']:raise ValueError('partial source changed')
        expected_partial=load(partial_path);prefix=[r for r in load(recipe_path) if r['angle_start_deg']>=engine.crank_angle_unwrapped_deg]
        if not prefix or prefix[-1]['angle_end_deg']!=expected_partial['crank_angle_unwrapped_deg']:raise ValueError('partial recipe coverage differs')
        prior_cycles=load(Path(provenance['source_previous_cycles_path']));replayed=False
        timing['source_partial_replay_s_subset']=0.
    out.mkdir(parents=True)
    def save(name,value):
        tick=time.perf_counter();write(out/name,value);timing['serialization']+=time.perf_counter()-tick
    save('configuration.json',config);previous=engine.snapshot();save('initial-checkpoint.json',previous)
    save('initialization.json',provenance);cycles=[];recipe=[];status='TRANSIENT_AT_BUDGET';error=None
    end_angle=360.*last_absolute;schedule=_integrated_scheduled_angles(engine,end_angle)
    try:
        for absolute in range(first_absolute,last_absolute+1):
            frames=[dict(angle=engine.crank_angle_unwrapped_deg,state=deepcopy(engine.state),ledger=deepcopy(engine.ledger))]
            while engine.crank_angle_unwrapped_deg<360.*absolute-1e-9:
                if timing['solver']>=solver_budget or time.perf_counter()-start>=admission_budget:raise TimeoutError(f'{solver_budget}s solver/{admission_budget}s admission')
                delta=min(360.*absolute,_integrated_nominal_step_end(engine,engine.crank_angle_unwrapped_deg,end_angle,schedule))-engine.crank_angle_unwrapped_deg
                rejected=[]
                for _ in range(25):
                    tick=time.perf_counter()
                    try:row=engine.step(delta/(6*9000.),delta,capture_trace=False)
                    except NoAdmissiblePortState:raise
                    except ValueError as exc:
                        if not any(s in str(exc) for s in ('CFL limit exceeded','inadmissible species mass','rho/p/Y inadmissible')):raise
                        rejected.append(dict(step_deg=delta,error=str(exc)));delta*=.5
                    else:break
                    finally:
                        elapsed=time.perf_counter()-tick;timing['solver']+=elapsed
                        if not replayed:timing['source_partial_replay_s_subset']+=elapsed
                else:raise RuntimeError('25 rejections')
                accepted=dict(**row,rejected_proposals=rejected);recipe.append(accepted)
                if not replayed:
                    if prefix_index>=len(prefix) or not _json_evidence_equal(accepted,prefix[prefix_index]):raise ValueError('partial accepted/rejected recipe differs')
                    prefix_index+=1
                    if prefix_index==len(prefix):
                        if not _json_evidence_equal(engine.fast_recipe_terminal_state(),expected_partial):raise ValueError('partial FAST replay differs')
                        replayed=True;save('partial-replay-verification.json',dict(status='PASS',accepted_steps=prefix_index,crank_angle_deg=engine.crank_angle_unwrapped_deg,terminal_sha256=provenance['source_partial_sha256']))
                angle=engine.crank_angle_unwrapped_deg
                if abs(angle-round(angle/30)*30)<1e-9:
                    frames.append(dict(angle=angle,state=deepcopy(engine.state),ledger=deepcopy(engine.ledger)))
            engine.compact_fast_recipe_cycle();current=engine.snapshot();save(f'checkpoint-absolute-{absolute:03}.json',current)
            tick=time.perf_counter();record,indices=relative_observations(engine,previous,current,origin);outcome=detector.update(record);timing['detector']+=time.perf_counter()-tick
            tick=time.perf_counter();balance=engine.conservation_report();valid=conserved(balance);timing['balances']+=time.perf_counter()-tick
            comparison=outcome['outcomes'].get('lag1',dict(status='NOT_EVALUATED',metrics={}))
            work=-(current['ledger']['cylinder_work_J']-previous['ledger']['cylinder_work_J'])
            cycles.append(dict(cycle=absolute-origin,absolute_cycle=absolute,indices=indices,comparison=comparison,statistics=statistics(comparison),
                detector_outcome=outcome,work_J=work,imep_bar=work/engine.slider_crank.crankcase.displacement_m3/1e5,inventory=engine.inventory(),conservation=balance))
            save(f'frames-absolute-{absolute:03}.json',frames);save('cycles.json',cycles);save('recipe.json',recipe);save('detector.json',detector.snapshot());previous=current
            if len(frames)!=13:raise ValueError('phase sampling incomplete; no time-step adjustment allowed')
            if not valid:raise ValueError('conservation gate failed')
            if outcome['classification'] is not None:status='PERIOD_CANDIDATE_REQUIRES_AUDIT';break
            valid_stats=[c['statistics'] for c in prior_cycles+cycles if c['statistics'] is not None]
            if len(valid_stats)>=3:
                recent=valid_stats[-3:]
                if all(b['maximum']>=.95*a['maximum'] and b['p90']>=a['p90'] for a,b in zip(recent,recent[1:])):
                    status='STOP_NO_SUFFICIENT_PROGRESS';break
    except TimeoutError as exc:error=str(exc)
    except Exception as exc:status='ERROR';error=f'{type(exc).__name__}: {exc}'
    save('recipe.json',recipe);save('terminal-state.json',engine.snapshot() if engine.accepted_steps==0 else engine.fast_recipe_terminal_state())
    result=dict(schema=schema,status=status,error=error,completed_new_cycles=len(cycles),absolute_terminal_angle=engine.crank_angle_unwrapped_deg,
        execution_bounds=dict(first_absolute_cycle=first_absolute,last_absolute_cycle=last_absolute,solver_budget_s=solver_budget,admission_budget_s=admission_budget),
        source_partial_replay_verified=replayed,source_partial_replayed_steps=prefix_index,
        timing_seconds=timing,wall_s=time.perf_counter()-start,initialization=provenance,configuration_sha256=sha(out/'configuration.json'),
        source_solver_sha256=_solver_dependency_hashes(),runner_sha256=sha(Path(__file__)),conservation=engine.conservation_report(),storage_preflight=preflight,
        terminal_state_kind='NATIVE_CHECKPOINT' if engine.accepted_steps==0 else 'FAST_RECIPE_TERMINAL_STATE',stage_audit_performed=False,
        periodicity_audited=False,mesh_independence=False,experimental_validation=False,review='SELF_REVIEW')
    save('receipt.json',result);print({k:result[k] for k in ('status','error','completed_new_cycles','wall_s','absolute_terminal_angle')})
    return 1 if status=='ERROR' else 0


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();raise SystemExit(run(a.root,a.output))
