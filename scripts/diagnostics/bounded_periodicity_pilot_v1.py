"""Same-source/same-run continuation, bounded native-cycle L1 indicators only."""
import argparse
import json
from pathlib import Path
import sys
import time
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from motorsim.integrated_2t import IntegratedEngine2T,_solver_dependency_hashes,_integrated_scheduled_angles,_integrated_nominal_step_end
from motorsim.port_connection_v2 import NoAdmissiblePortState
from motorsim.reference_harness.convergence import PeriodicDetectorV2
from scripts.diagnostics.checkpoint_periodicity_indicators_v1 import cycle_observations
from scripts.diagnostics.diagnose_integrated_mesh_v1 import read_bound_reference,sha,write
from scripts.agents.storage_preflight import check_storage_requirements


def run(source,output):
    preflight=check_storage_requirements([(output,16*1024**2)])
    if output.exists():raise FileExistsError('preserve prior pilot')
    receipt,config_path,terminal=read_bound_reference(source)
    audit=source.parent/'spatial-boundary-v2-cycle2-replay-audit.json'
    bound=json.loads(audit.read_text(encoding='utf-8'))
    if bound['status']!='PASS' or bound['evidence_binding']['solver_dependency_sha256']!=_solver_dependency_hashes():raise ValueError('source dependency mismatch')
    if bound['source_receipt_sha256']!=sha(source/'receipt.json'):raise ValueError('source receipt mismatch')
    config=json.loads(config_path.read_text(encoding='utf-8'));engine=IntegratedEngine2T.from_configuration_dict(config)
    detector=PeriodicDetectorV2();previous=None
    for i,name in enumerate(('initial-checkpoint.json','checkpoint-360.json','checkpoint-720.json')):
        current=json.loads((source/name).read_text(encoding='utf-8'));engine.restore(current)
        if previous is not None:detector.update(cycle_observations(engine,previous,current,i))
        previous=current
    engine.restore(terminal);output.mkdir(parents=True)
    recipe=[];cycles=[];start=time.perf_counter();status='TRANSIENT_AT_BUDGET';error=None
    schedule=_integrated_scheduled_angles(engine,4320.)
    try:
        for cycle in range(3,13):
            target=360.*cycle
            while engine.crank_angle_unwrapped_deg<target-1e-9:
                if time.perf_counter()-start>=150:raise TimeoutError('150-second numerical admission budget')
                delta=min(target,_integrated_nominal_step_end(engine,engine.crank_angle_unwrapped_deg,4320.,schedule))-engine.crank_angle_unwrapped_deg
                rejected=[]
                for attempt in range(25):
                    try:row=engine.step(delta/(6*9000.),delta,capture_trace=False)
                    except NoAdmissiblePortState:raise
                    except ValueError as exc:
                        if not any(t in str(exc) for t in ('CFL limit exceeded','inadmissible species mass','rho/p/Y inadmissible')):raise
                        rejected.append(dict(attempted_step_deg=delta,reason=str(exc)));delta*=.5
                    else:break
                else:raise RuntimeError('25 rejected proposals')
                recipe.append(dict(**row,rejected_proposals=rejected))
            engine.compact_fast_recipe_cycle();current=engine.snapshot()
            write(output/f'checkpoint-{cycle:03}.json',current)
            outcome=detector.update(cycle_observations(engine,previous,current,cycle))
            comparison=outcome['outcomes']['lag1'];metrics=comparison.get('metrics',{})
            cycles.append(dict(cycle=cycle,comparison=comparison,detector_outcome=outcome,
                cylinder_work_J=-(current['ledger']['cylinder_work_J']-previous['ledger']['cylinder_work_J']),
                failed_count=sum(not m['passed'] for m in metrics.values())))
            write(output/'cycles.json',cycles);write(output/'detector.json',detector.snapshot())
            previous=current
            if outcome.get('classification') in ('PERIODIC','PERIOD_1','PERIOD_2'):
                status='PERIOD_CANDIDATE_REQUIRES_AUDIT';break
    except TimeoutError as exc:error=str(exc)
    except Exception as exc:status='ERROR';error=f'{type(exc).__name__}: {exc}'
    write(output/'accepted-recipe.json',recipe)
    terminal_state=engine.snapshot() if engine.accepted_steps==0 else engine.fast_recipe_terminal_state()
    write(output/'terminal-state.json',terminal_state)
    result=dict(schema='DINO_BOUNDED_PERIODICITY_PILOT_V1',status=status,error=error,wall_s=time.perf_counter()-start,
        terminal_angle=engine.crank_angle_unwrapped_deg,completed_new_cycles=len(cycles),
        source_configuration_sha256=sha(config_path),source_checkpoint_sha256=sha(source/'checkpoint-720.json'),
        solver_dependency_sha256=_solver_dependency_hashes(),cycles=cycles,conservation=engine.conservation_report(),storage_preflight=preflight,
        evidence_level='L1_NATIVE_CHECKPOINT_DERIVED',periodicity_demonstrated=False,mesh_independence_demonstrated=False,experimental_validation=False)
    write(output/'receipt.json',result);print(json.dumps({k:result[k] for k in ('status','error','wall_s','terminal_angle','completed_new_cycles')}))
    return 1 if status=='ERROR' else 0


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();raise SystemExit(run(a.source,a.output))
