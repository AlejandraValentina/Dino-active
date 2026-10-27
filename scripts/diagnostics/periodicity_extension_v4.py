"""One declared continuation25->29, unchanged engine and detector."""
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


def load_source(source,config_source):
    load=lambda p:json.loads(p.read_text(encoding='utf-8'))
    manifest=load(source.parent/'manifest.json');hashes={k.replace('\\','/'):v for k,v in manifest['files'].items()}
    for name in ('checkpoint-024.json','checkpoint-025.json','detector.json','receipt.json','cycles.json'):
        if sha(source/name)!=hashes['relaxation-check/'+name]:raise ValueError('source hash mismatch')
    prior=load(source/'receipt.json')
    if prior['solver_dependency_sha256']!=_solver_dependency_hashes():raise ValueError('solver source mismatch')
    if sha(config_source/'configuration.json')!=prior['configuration_sha256']:raise ValueError('configuration mismatch')
    e=IntegratedEngine2T.from_configuration_dict(load(config_source/'configuration.json'));cp=load(source/'checkpoint-025.json');e.restore(cp)
    if not _json_evidence_equal(e.snapshot(),cp):raise ValueError('native roundtrip mismatch')
    saved=load(source/'detector.json');detector=PeriodicDetectorV2(saved)
    if len(detector.history)!=25 or detector.detected_period is not None or not _json_evidence_equal(saved,detector.snapshot()):raise ValueError('wrong detector prefix')
    expected=cycle_observations(e,load(source/'checkpoint-024.json'),cp,25)
    if not _json_evidence_equal(expected,detector.history[-1]):raise ValueError('restored observations mismatch')
    return e,cp,detector,load(source/'cycles.json')


def conserved(report):
    m=report['mass'];energy=report['energy']
    return (abs(m['residual'])<=1e-12*max(abs(m['initial']),abs(m['final'])) and
        abs(energy['residual'])<=1e-12*max(abs(energy['initial']),abs(energy['final'])) and
        all(abs(s['residual'])<=1e-12*max(abs(m['initial']),abs(m['final'])) for s in report['species'].values()))


def run(source,config_source,out):
    preflight=check_storage_requirements([(out,16*1024**2)])
    if out.exists():raise FileExistsError('preserve prior invocation')
    start=time.perf_counter();timing=dict(solver=0.,serialization=0.,detector=0.,restoration=0.,audit=0.)
    e,previous,detector,base=load_source(source,config_source);timing['restoration']=time.perf_counter()-start
    out.mkdir(parents=True);cycles=[];recipe=[];status='TRANSIENT_AT_BUDGET';error=None
    schedule=_integrated_scheduled_angles(e,10440.)
    def save(name,value):
        tick=time.perf_counter();write(out/name,value);timing['serialization']+=time.perf_counter()-tick
    try:
        for cycle in range(26,30):
            while e.crank_angle_unwrapped_deg<360.*cycle-1e-9:
                if timing['solver']>=75 or time.perf_counter()-start>=85:raise TimeoutError('75s solver/85s admission;90s overall budget')
                delta=min(360.*cycle,_integrated_nominal_step_end(e,e.crank_angle_unwrapped_deg,10440.,schedule))-e.crank_angle_unwrapped_deg
                rejected=[]
                for _ in range(25):
                    tick=time.perf_counter()
                    try:row=e.step(delta/(6*9000.),delta,capture_trace=False)
                    except NoAdmissiblePortState:raise
                    except ValueError as exc:
                        if not any(s in str(exc) for s in ('CFL limit exceeded','inadmissible species mass','rho/p/Y inadmissible')):raise
                        rejected.append(dict(step_deg=delta,error=str(exc)));delta*=.5
                    else:break
                    finally:timing['solver']+=time.perf_counter()-tick
                else:raise RuntimeError('25 rejected proposals')
                recipe.append(dict(**row,rejected_proposals=rejected))
            e.compact_fast_recipe_cycle();current=e.snapshot();save(f'checkpoint-{cycle:03}.json',current)
            tick=time.perf_counter();outcome=detector.update(cycle_observations(e,previous,current,cycle));timing['detector']+=time.perf_counter()-tick
            tick=time.perf_counter();balance=e.conservation_report();valid=conserved(balance);timing['audit']+=time.perf_counter()-tick
            cycles.append(dict(cycle=cycle,comparison=outcome['outcomes']['lag1'],detector_outcome=outcome,
                cylinder_work_J=-(current['ledger']['cylinder_work_J']-previous['ledger']['cylinder_work_J']),conservation=balance))
            save('cycles.json',cycles);save('detector.json',detector.snapshot());save('recipe.json',recipe);previous=current
            if not valid:raise ValueError('conservation gate failed')
            if outcome['classification'] is not None:status='PERIOD_CANDIDATE_REQUIRES_AUDIT';break
            if len(cycles)>=3:
                rows=analyze(base+cycles)['cycles'];a,b=rows[-6:-3],rows[-3:]
                median=lambda x,k:float(np.median([r['lags']['lag1']['all'][k] for r in x]))
                if median(b,'maximum')>=.95*median(a,'maximum') and median(b,'p90')>=median(a,'p90'):
                    status='STOP_NO_SUFFICIENT_PROGRESS';break
    except TimeoutError as exc:error=str(exc)
    except Exception as exc:status='ERROR';error=f'{type(exc).__name__}: {exc}'
    save('recipe.json',recipe);save('terminal-state.json',e.snapshot() if e.accepted_steps==0 else e.fast_recipe_terminal_state());save('trends.json',analyze(base+cycles))
    result=dict(schema='DINO_PERIODICITY_EXTENSION_V4',status=status,error=error,completed_new_cycles=len(cycles),terminal_angle=e.crank_angle_unwrapped_deg,
        timing_seconds=timing,wall_s=time.perf_counter()-start,conservation=e.conservation_report(),source_checkpoint_sha256=sha(source/'checkpoint-025.json'),
        source_detector_sha256=sha(source/'detector.json'),configuration_sha256=sha(config_source/'configuration.json'),solver_dependency_sha256=_solver_dependency_hashes(),
        runner_sha256=sha(Path(__file__)),restoration_exact=True,detector_observations_reproduced=True,storage_preflight=preflight,
        terminal_state_kind='NATIVE_CHECKPOINT' if e.accepted_steps==0 else 'FAST_RECIPE_TERMINAL_STATE',
        evidence_level='L1_NATIVE_OBSERVATIONS',audit_performed=False,periodicity_demonstrated=False,experimental_validation=False)
    save('receipt.json',result);print(json.dumps({k:result[k] for k in ('status','error','completed_new_cycles','terminal_angle','wall_s','timing_seconds')}))
    return 1 if status=='ERROR' else 0


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--configuration-source',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    raise SystemExit(run(a.source,a.configuration_source,a.output))
