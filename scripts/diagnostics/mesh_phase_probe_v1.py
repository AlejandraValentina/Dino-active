"""Bounded same-simulation cycle-2 probe, no solver/model modification."""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from motorsim.integrated_2t import IntegratedEngine2T,_integrated_scheduled_angles,_integrated_nominal_step_end,_solver_dependency_hashes
from motorsim.port_connection_v2 import NoAdmissiblePortState
from scripts.agents.storage_preflight import check_storage_requirements
from scripts.diagnostics.diagnose_integrated_mesh_v1 import sha,write


def run(source,output):
    preflight=check_storage_requirements([(output,10*1024**2)])
    if output.exists():raise FileExistsError('preserve earlier evidence')
    config=json.loads((source/'configuration.json').read_text(encoding='utf-8'))
    checkpoint=json.loads((source/'checkpoint-360.json').read_text(encoding='utf-8'))
    receipt=json.loads((source/'receipt.json').read_text(encoding='utf-8'))
    if sha(source/'configuration.json')!=receipt['configuration_sha256']:raise ValueError('configuration hash mismatch')
    bound=next(c for c in receipt['checkpoints'] if c['path']=='checkpoint-360.json')
    if sha(source/'checkpoint-360.json')!=bound['sha256']:raise ValueError('checkpoint hash mismatch')
    if checkpoint['crank_angle_unwrapped_deg']!=360:raise ValueError('wrong initial phase')
    engine=IntegratedEngine2T.from_configuration_dict(config);engine.restore(checkpoint)
    output.mkdir(parents=True)
    frames=[dict(angle=360.,state=deepcopy(engine.state),ledger=deepcopy(engine.ledger))]
    recipe=[];start=time.perf_counter();status='COMPLETE';error=None
    scheduled=_integrated_scheduled_angles(engine,720.)
    try:
        for target in range(375,721,15):
            while engine.crank_angle_unwrapped_deg<target-1e-9:
                if time.perf_counter()-start>=240 or len(recipe)>=10000:raise TimeoutError('finite probe budget reached')
                delta=min(target,_integrated_nominal_step_end(engine,engine.crank_angle_unwrapped_deg,720.,scheduled))-engine.crank_angle_unwrapped_deg
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
            frames.append(dict(angle=float(target),state=deepcopy(engine.state),ledger=deepcopy(engine.ledger)))
    except Exception as exc:status='STOPPED';error=f'{type(exc).__name__}: {exc}'
    write(output/'frames.json',frames);write(output/'recipe.json',recipe)
    write(output/'terminal-fast-state.json',engine.fast_recipe_terminal_state())
    result=dict(schema='DINO_MESH_PHASE_PROBE_V1',status=status,error=error,wall_s=time.perf_counter()-start,
        source_configuration_sha256=sha(source/'configuration.json'),source_checkpoint_sha256=sha(source/'checkpoint-360.json'),
        solver_dependency_sha256=_solver_dependency_hashes(),runner_sha256=sha(Path(__file__)),
        frames_sha256=sha(output/'frames.json'),recipe_sha256=sha(output/'recipe.json'),
        terminal_phase=engine.crank_angle_unwrapped_deg,conservation=engine.conservation_report(),storage_preflight=preflight,
        qualification='Same-simulation continuation; extra output-phase cuts may change temporal truncation; verify original terminal agreement.',
        experimental_validation=False,evidence_level='L1',review='SELF_REVIEW')
    write(output/'receipt.json',result)
    print(json.dumps({k:result[k] for k in ('status','error','wall_s','terminal_phase')}))
    return 0 if status=='COMPLETE' else 1


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();raise SystemExit(run(a.source,a.output))
