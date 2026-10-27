"""Finite 2x2 mesh/time diagnostic initialized from a bound physical checkpoint."""
import argparse
from copy import deepcopy
import json
import math
from pathlib import Path
import sys
import time
import numpy as np
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from motorsim.integrated_2t import IntegratedEngine2T,_solver_dependency_hashes,_integrated_scheduled_angles,_integrated_nominal_step_end
from motorsim.port_connection_v2 import NoAdmissiblePortState
from scripts.diagnostics.diagnose_integrated_mesh_v1 import refined_configuration,restrict_state,sha,write
from scripts.agents.storage_preflight import check_storage_requirements


def prolong(state,coarse,fine):
    """Piecewise constant conserved-density prolongation; exact volume split."""
    result=deepcopy(state);meshes={p['id']:p['mesh'] for p in coarse['ducts']}
    for p in fine['ducts']:
        name=p['id'];vc=meshes[name]['volumes'];vf=p['mesh']['volumes']
        result['ducts'][name]=[deepcopy(q) for q in state['ducts'][name] for _ in (0,1)]
        result['species']['ducts'][name]=[tuple(s*vf[j]/vc[j//2] for s in state['species']['ducts'][name][j//2]) for j in range(len(vf))]
    return result


def initialize(config,checkpoint,refine,parent_hash,checkpoint_hash):
    if checkpoint['trace'] or checkpoint['accepted_steps']!=0:raise ValueError('require compacted native complete-cycle checkpoint')
    if not refine:
        e=IntegratedEngine2T.from_configuration_dict(config);e.restore(checkpoint);return e,config,dict(kind='SAME_SIMULATION_RESUME')
    fine=refined_configuration(config,parent_hash)
    fine['geometry_identity']['diagnostic_initialization']=dict(schema='CONSERVATIVE_P0_CHECKPOINT_INITIALIZATION_V1',source_checkpoint_sha256=checkpoint_hash)
    e=IntegratedEngine2T.from_configuration_dict(fine)
    # New diagnostic initialization, not cross-mesh resume: actual new identity
    # is constructor generated; original checkpoint/identity remain untouched.
    template=e.snapshot();mapped=deepcopy(checkpoint)
    mapped['configuration_identity']=template['configuration_identity']
    mapped['initial_inventory']=template['initial_inventory']
    mapped['state']=prolong(checkpoint['state'],config,fine)
    mapped['trace_origin_state']=prolong(checkpoint['trace_origin_state'],config,fine)
    e.restore(mapped)
    coarse_engine=IntegratedEngine2T.from_configuration_dict(config)
    a=coarse_engine.inventory(checkpoint['state']);b=e.inventory()
    pairs=[(a['mass_kg'],b['mass_kg']),(a['energy_J'],b['energy_J'])]+list(zip(a['species_kg'],b['species_kg']))
    error=max(abs(x-y)/max(abs(x),abs(y),1e-30) for x,y in pairs)
    if error>1e-12:raise ValueError('nonconservative diagnostic initialization')
    restricted=restrict_state(e.state,fine,config)
    delta=max(abs(x-y)/max(abs(x),abs(y),1e-30) for name in checkpoint['state']['ducts'] for q,r in zip(checkpoint['state']['ducts'][name],restricted['ducts'][name]) for x,y in zip(q,r))
    return e,fine,dict(kind='NEW_DIAGNOSTIC_CONSERVATIVE_INITIALIZATION',inventory_max_relative_error=error,restriction_max_relative_error=delta,
        qualification='Same piecewise-constant physical field; subcell slopes are not supplied. Initial subcell/reconstruction adjustment is not separable from spatial evolution.')


def run(root,out,refine,step):
    preflight=check_storage_requirements([(out,16*1024**2)])
    if out.exists():raise FileExistsError('preserve earlier diagnostic')
    source=root/'exhaust-composition-plateau-v1/relaxation-check';config_path=root/'spatial-boundary-v2-engine/configuration.json'
    cp_path=source/'checkpoint-025.json';load=lambda p:json.loads(p.read_text(encoding='utf-8'))
    receipt=load(source/'receipt.json')
    if receipt['solver_dependency_sha256']!=_solver_dependency_hashes() or receipt['configuration_sha256']!=sha(config_path):raise ValueError('source/config mismatch')
    manifest=load(source.parent/'manifest.json');hashes={k.replace('\\','/'):v for k,v in manifest['files'].items()}
    if sha(cp_path)!=hashes['relaxation-check/checkpoint-025.json']:raise ValueError('checkpoint hash mismatch')
    cp=load(cp_path);e,config,remap=initialize(load(config_path),cp,refine,sha(config_path),sha(cp_path))
    out.mkdir(parents=True);write(out/'configuration.json',config);write(out/'initial-checkpoint.json',e.snapshot())
    initial_inventory=e.inventory();stages=[];original=e._assemble
    def observer(*args,**kwargs):
        kwargs['capture_trace']=True;r=original(*args,**kwargs)
        stages.append({name:(np.array(f['all_species_faces'][0]),np.array(f['all_species_faces'][-1]),f['all_faces'][0][0],f['all_faces'][-1][0]) for name,f in r['faces'].items()})
        return r
    e._assemble=observer
    totals={p.id:{side:dict(net=np.zeros(4),positive=np.zeros(4),negative=np.zeros(4),positive_mass=0.,negative_mass=0.) for side in ('left','right')} for p in e.ducts}
    frames=[dict(angle=9000.,state=deepcopy(e.state),ledger=deepcopy(e.ledger))];recipe=[];start=time.perf_counter();status='COMPLETE';error=None
    schedule=_integrated_scheduled_angles(e,9360.)
    try:
        for target in range(9030,9361,30):
            while e.crank_angle_unwrapped_deg<target-1e-9:
                if time.perf_counter()-start>=120:raise TimeoutError('120-second case budget')
                angle=e.crank_angle_unwrapped_deg
                delta=min(target,_integrated_nominal_step_end(e,angle,9360.,schedule),(math.floor((angle+1e-9)/step)+1)*step)-angle
                rejected=[]
                for _ in range(25):
                    stages.clear()
                    try:row=e.step(delta/(6*9000.),delta,capture_trace=False)
                    except NoAdmissiblePortState:raise
                    except ValueError as exc:
                        if not any(s in str(exc) for s in ('CFL limit exceeded','inadmissible species mass','rho/p/Y inadmissible')):raise
                        rejected.append(dict(step_deg=delta,error=str(exc)));delta*=.5
                    else:break
                else:raise RuntimeError('25 rejections')
                if len(stages)!=2:raise ValueError('two SSPRK stages required')
                for stage in stages:
                    for name,values in stage.items():
                        for side,s,m in [('left',values[0],values[2]),('right',values[1],values[3])]:
                            t=totals[name][side];t['net']+=.5*delta/(6*9000.)*s;t['positive' if m>=0 else 'negative']+=.5*delta/(6*9000.)*s
                            t['positive_mass' if m>=0 else 'negative_mass']+=.5*delta/(6*9000.)*m
                recipe.append(dict(**row,rejected_proposals=rejected))
            frames.append(dict(angle=float(target),state=deepcopy(e.state),ledger=deepcopy(e.ledger)))
    except Exception as exc:status='STOPPED';error=f'{type(exc).__name__}: {exc}'
    for ends in totals.values():
        for t in ends.values():
            for key in ('net','positive','negative'):t[key]=t[key].tolist()
    write(out/'frames.json',frames);write(out/'recipe.json',recipe)
    if status=='COMPLETE':e.compact_fast_recipe_cycle();write(out/'terminal-checkpoint.json',e.snapshot())
    else:write(out/'terminal-fast.json',e.fast_recipe_terminal_state())
    work=-(e.ledger['cylinder_work_J']-cp['ledger']['cylinder_work_J'])
    result=dict(schema='CHECKPOINT_2X2_DIAGNOSTIC_V1',status=status,error=error,step_cap_deg=step,refined=refine,
        wall_s=time.perf_counter()-start,initialization=remap,interfaces=totals,initial_inventory=initial_inventory,final_inventory=e.inventory(),
        work_J=work,imep_bar=work/e.slider_crank.crankcase.displacement_m3/1e5,conservation=e.conservation_report(),
        source_checkpoint_sha256=sha(cp_path),configuration_sha256=sha(out/'configuration.json'),solver_dependency_sha256=_solver_dependency_hashes(),
        periodicity_demonstrated=False,experimental_validation=False,storage_preflight=preflight,review='SELF_REVIEW')
    write(out/'receipt.json',result);print(json.dumps({k:result[k] for k in ('status','error','wall_s','work_J','initialization')}))
    return 0 if status=='COMPLETE' else 1


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--refine',action='store_true');p.add_argument('--step',type=float,choices=(.5,.25),required=True);a=p.parse_args();raise SystemExit(run(a.root,a.output,a.refine,a.step))
