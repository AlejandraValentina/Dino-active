"""One bounded continuation from native cycle17 with cost attribution."""
import argparse
import json
from pathlib import Path
import sys
import time
import numpy as np
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from motorsim.integrated_2t import IntegratedEngine2T,_solver_dependency_hashes,_integrated_scheduled_angles,_integrated_nominal_step_end,_json_evidence_equal
from motorsim.reference_harness.convergence import PeriodicDetectorV2
from motorsim.port_connection_v2 import NoAdmissiblePortState
from scripts.diagnostics.checkpoint_periodicity_indicators_v1 import cycle_observations
from scripts.diagnostics.diagnose_integrated_mesh_v1 import sha,write
from scripts.diagnostics.periodicity_trends_v1 import analyze
from scripts.agents.storage_preflight import check_storage_requirements


def run(source,config_source,out):
    check_storage_requirements([(out,16*1024**2)])
    if out.exists():raise FileExistsError('preserve prior invocation')
    start=time.perf_counter();timing=dict(solver=0.,serialization=0.,detector=0.,restoration=0.,audit=0.)
    manifest=json.loads((source.parent/'manifest.json').read_text());prior=json.loads((source/'receipt.json').read_text())
    for name in ('checkpoint-017.json','detector.json'):
        if sha(source/name)!=manifest['files']['run/'+name]:raise ValueError('source hash mismatch')
    if prior['solver_dependency_sha256']!=_solver_dependency_hashes():raise ValueError('solver source mismatch')
    if sha(config_source/'configuration.json')!=prior['configuration_sha256']:raise ValueError('configuration mismatch')
    config=json.loads((config_source/'configuration.json').read_text());engine=IntegratedEngine2T.from_configuration_dict(config)
    previous=json.loads((source/'checkpoint-017.json').read_text());engine.restore(previous)
    if not _json_evidence_equal(engine.state,previous['state']):raise ValueError('restoration mismatch')
    detector=PeriodicDetectorV2(json.loads((source/'detector.json').read_text()))
    if len(detector.history)!=17 or detector.detected_period is not None:raise ValueError('wrong detector prefix')
    timing['restoration']=time.perf_counter()-start
    out.mkdir(parents=True);cycles=[];recipe=[];base=json.loads((source/'cycles.json').read_text());status='TRANSIENT_AT_BUDGET';error=None
    schedule=_integrated_scheduled_angles(engine,8280.)
    def save(name,data):
        tick=time.perf_counter();write(out/name,data);timing['serialization']+=time.perf_counter()-tick
    try:
        for cycle in range(18,24):
            while engine.crank_angle_unwrapped_deg<360.*cycle-1e-9:
                if timing['solver']>=120 or time.perf_counter()-start>=145:raise TimeoutError('finite 120s solver/145s admission, 150s overall limit limit')
                delta=min(360.*cycle,_integrated_nominal_step_end(engine,engine.crank_angle_unwrapped_deg,8280.,schedule))-engine.crank_angle_unwrapped_deg
                rejected=[]
                for _ in range(25):
                    tick=time.perf_counter()
                    try:row=engine.step(delta/(6*9000.),delta,capture_trace=False)
                    except NoAdmissiblePortState:raise
                    except ValueError as exc:
                        if not any(s in str(exc) for s in ('CFL limit exceeded','inadmissible species mass','rho/p/Y inadmissible')):raise
                        rejected.append(dict(step_deg=delta,error=str(exc)));delta*=.5
                    else:break
                    finally:timing['solver']+=time.perf_counter()-tick
                else:raise RuntimeError('25 rejected proposals')
                recipe.append(dict(**row,rejected_proposals=rejected))
            tick=time.perf_counter();engine.compact_fast_recipe_cycle();current=engine.snapshot();timing['serialization']+=time.perf_counter()-tick
            save(f'checkpoint-{cycle:03}.json',current)
            tick=time.perf_counter();outcome=detector.update(cycle_observations(engine,previous,current,cycle));timing['detector']+=time.perf_counter()-tick
            comparison=outcome['outcomes']['lag1']
            cycles.append(dict(cycle=cycle,comparison=comparison,detector_outcome=outcome,cylinder_work_J=-(current['ledger']['cylinder_work_J']-previous['ledger']['cylinder_work_J'])))
            save('cycles.json',cycles);save('detector.json',detector.snapshot());save('recipe.json',recipe)
            previous=current
            if outcome['classification'] is not None:status='PERIOD_CANDIDATE_REQUIRES_AUDIT';break
            if len(cycles)>=3:
                rows=analyze(base+cycles)['cycles'];a,b=rows[-6:-3],rows[-3:]
                mx=lambda x,k:float(np.median([r['lags']['lag1']['all'][k] for r in x]))
                if mx(b,'maximum')>=.95*mx(a,'maximum') and mx(b,'p90')>=mx(a,'p90'):
                    status='STOP_NO_SUFFICIENT_PROGRESS';break
    except TimeoutError as exc:error=str(exc)
    except Exception as exc:status='ERROR';error=f'{type(exc).__name__}: {exc}'
    save('recipe.json',recipe);save('terminal-state.json',engine.snapshot() if engine.accepted_steps==0 else engine.fast_recipe_terminal_state())
    save('trends.json',analyze(base+cycles))
    result=dict(schema='DINO_PERIODICITY_EXTENSION_V2',status=status,error=error,completed_new_cycles=len(cycles),terminal_angle=engine.crank_angle_unwrapped_deg,
        timing_seconds=timing,wall_s=time.perf_counter()-start,conservation=engine.conservation_report(),
        source_checkpoint_sha256=sha(source/'checkpoint-017.json'),source_detector_sha256=sha(source/'detector.json'),
        configuration_sha256=sha(config_source/'configuration.json'),solver_dependency_sha256=_solver_dependency_hashes(),
        evidence_level='L1_NATIVE_OBSERVATIONS',audit_performed=False,periodicity_demonstrated=False,experimental_validation=False)
    save('receipt.json',result);print(json.dumps(result|{'conservation':'persisted','solver_dependency_sha256':'persisted'}))
    return 1 if status=='ERROR' else 0


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--configuration-source',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    raise SystemExit(run(a.source,a.configuration_source,a.output))
