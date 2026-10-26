"""One conservative frustum-grid refinement, existing trace-free integrator."""
import argparse
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from motorsim.integrated_2t import (IntegratedEngine2T,_integrated_scheduled_angles,
    _integrated_nominal_step_end,_json_evidence_equal)
from motorsim.gas1d.eos import IdealGas
from motorsim.port_connection_v2 import NoAdmissiblePortState
from scripts.agents.storage_preflight import check_storage_requirements
from scripts.diagnostics.compare_integrated_port_v2 import terminal_differences


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path,value):
    path.write_text(json.dumps(value,allow_nan=False,separators=(',',':'))+'\n',encoding='utf-8')


def bisect_frustum_mesh(mesh):
    faces=[mesh['faces'][0]];areas=[mesh['areas'][0]]
    volumes=[];centers=[]
    for i,(left,right) in enumerate(zip(mesh['faces'],mesh['faces'][1:])):
        al,ar=mesh['areas'][i:i+2]
        mid=(left+right)/2
        am=((math.sqrt(al)+math.sqrt(ar))/2)**2
        new=[]
        for x0,x1,a0,a1 in ((left,mid,al,am),(mid,right,am,ar)):
            h=x1-x0;ra,rb=math.sqrt(a0),math.sqrt(a1);delta=rb-ra
            section=(a0+ra*rb+a1)/3
            vol=h*section
            centroid=x0+h*(a0/2+2*ra*delta/3+delta*delta/4)/section
            volumes.append(vol);centers.append(centroid);new.append(vol)
            faces.append(x1);areas.append(a1)
        if not math.isclose(sum(new),mesh['volumes'][i],rel_tol=1e-12,abs_tol=0.):
            raise ValueError('parent cell is not the assumed exact linear frustum')
        moment=sum(v*x for v,x in zip(new,centers[-2:]))
        if not math.isclose(moment,mesh['volumes'][i]*mesh['centers'][i],rel_tol=1e-12,abs_tol=1e-30):
            raise ValueError('parent centroid is not that of the assumed frustum')
    return dict(faces=faces,areas=areas,volumes=volumes,centers=centers)


def refined_configuration(config,parent_sha256):
    if config.get('dynamic_reed_binding') is not None:
        raise ValueError('this diagnostic has no verified remapping of moving-cell bindings')
    result=deepcopy(config)
    for path in result['ducts']:
        name=path['id'];original=path['mesh']
        fine=bisect_frustum_mesh(original)
        original_states=result['initial_duct_states'][name]
        original_species=result['duct_species'][name]
        result['initial_duct_states'][name]=[deepcopy(w) for w in original_states for _ in range(2)]
        result['duct_species'][name]=[[value*fine['volumes'][j]/original['volumes'][j//2]
            for value in original_species[j//2]] for j in range(len(fine['volumes']))]
        path['mesh']=fine
    if result.get('thermal_system') is not None:
        meshes={p['id']:p['mesh'] for p in config['ducts']}
        surfaces=[];locations={}
        for surface in config['thermal_system']['surfaces']:
            location=config['thermal_locations'][surface['id']]
            if location in ('cylinder','crankcase'):
                surfaces.append(deepcopy(surface));locations[surface['id']]=location
                continue
            name,index=location.rsplit(':',1)
            if name not in meshes:
                raise ValueError('unsupported thermal location for conservative mesh refinement')
            i=int(index)
            al,ar=meshes[name]['areas'][i:i+2]
            rl,rr=math.sqrt(al),math.sqrt(ar)
            first_fraction=(3*rl+rr)/(4*(rl+rr))
            first_area=surface['area_m2']*first_fraction
            for child,area in enumerate((first_area,surface['area_m2']-first_area)):
                item=deepcopy(surface)
                item['id']=surface['id']+f'~bisect-{child}'
                item['area_m2']=area
                surfaces.append(item);locations[item['id']]=f'{name}:{2*i+child}'
        result['thermal_system']['surfaces']=surfaces
        result['thermal_locations']=locations
    result['geometry_identity']['mesh_refinement_provenance']=dict(
        schema='CONSERVATIVE_EXACT_FRUSTUM_BISECTION_V1',factor=2,
        parent_configuration_sha256=parent_sha256,
        thermal_partition='UNCHANGED_H_AND_TW_SURFACE_AREA_SPLIT_BY_LINEAR_RADIUS')
    return result


def restrict_state(state,fine_config,coarse_config):
    result=deepcopy(state)
    meshes={p['id']:p['mesh'] for p in fine_config['ducts']}
    for p in coarse_config['ducts']:
        name=p['id'];vf=meshes[name]['volumes'];vc=p['mesh']['volumes']
        q=state['ducts'][name];s=state['species']['ducts'][name]
        result['ducts'][name]=[tuple(math.fsum(q[j][k]*vf[j] for j in (2*i,2*i+1))/v
            for k in range(4)) for i,v in enumerate(vc)]
        result['species']['ducts'][name]=[tuple(math.fsum(s[j][k] for j in (2*i,2*i+1))
            for k in range(4)) for i in range(len(vc))]
    return result


def run(source,output):
    preflight=check_storage_requirements([(output,5*1024**2)])
    if output.exists():raise FileExistsError('preserve earlier diagnostic outputs')
    reference=json.loads((source/'receipt.json').read_text(encoding='utf-8'))
    config_path=source/'configuration.json'
    if sha(config_path)!=reference['configuration_sha256']:
        raise ValueError('source configuration hash mismatch')
    checkpoint_path=source/'terminal-checkpoint.json'
    if sha(checkpoint_path)!=reference['terminal_checkpoint_sha256']:
        raise ValueError('source terminal checkpoint hash mismatch')
    checkpoint=json.loads(checkpoint_path.read_text(encoding='utf-8'))
    if (not _json_evidence_equal(checkpoint['state'],reference['final_state']) or
            not _json_evidence_equal(checkpoint['ledger'],reference['final_ledger'])):
        raise ValueError('source summary does not match its bound checkpoint')
    coarse_config=json.loads(config_path.read_text(encoding='utf-8'))
    config=refined_configuration(coarse_config,sha(config_path))
    coarse=IntegratedEngine2T.from_configuration_dict(coarse_config)
    engine=IntegratedEngine2T.from_configuration_dict(config)
    initial_a,initial_b=coarse.inventory(),engine.inventory()
    pairs=[(initial_a['mass_kg'],initial_b['mass_kg']),
           (initial_a['energy_J'],initial_b['energy_J'])]+list(zip(initial_a['species_kg'],initial_b['species_kg']))
    init_error=max(abs(a-b)/max(abs(a),abs(b),1e-30) for a,b in pairs)
    if init_error>1e-12:raise ValueError('refinement does not conserve initial inventories')
    try:engine.restore(coarse.snapshot())
    except ValueError as exc:
        if 'configuration mismatch' not in str(exc):raise
        cross_mesh_rejected=True
    else:raise AssertionError('cross-mesh checkpoint was accepted')
    output.mkdir(parents=True)
    write(output/'configuration.json',engine.configuration_dict())
    write(output/'initial-checkpoint.json',engine.snapshot())
    recipe=[];checkpoints=[];status='COMPLETE';error=None
    scheduled=_integrated_scheduled_angles(engine,720.)
    began=time.perf_counter();compute=0.
    try:
        while engine.crank_angle_unwrapped_deg<720.-1e-9:
            if time.perf_counter()-began>=240 or len(recipe)>=10000:
                raise TimeoutError('declared computation/step budget reached')
            angle=engine.crank_angle_unwrapped_deg
            delta=_integrated_nominal_step_end(engine,angle,720.,scheduled)-angle
            rejected=[]
            for attempt in range(25):
                tick=time.perf_counter()
                try:row=engine.step(delta/(6*9000.),delta,capture_trace=False)
                except NoAdmissiblePortState:raise
                except ValueError as exc:
                    if not any(t in str(exc) for t in ('CFL limit exceeded','inadmissible species mass','rho/p/Y inadmissible')):raise
                    rejected.append(dict(attempted_step_deg=delta,reason=str(exc)))
                    delta*=.5
                else:break
                finally:compute+=time.perf_counter()-tick
            else:raise RuntimeError('25 rejected trials')
            recipe.append(dict(**row,rejected_proposals=rejected))
            if abs(engine.crank_angle_unwrapped_deg%360)<1e-9:
                engine.compact_fast_recipe_cycle()
                snapshot=engine.snapshot()
                path=output/f"checkpoint-{int(engine.crank_angle_unwrapped_deg)}.json"
                write(path,snapshot)
                restored=IntegratedEngine2T.from_configuration_dict(config)
                restored.restore(json.loads(path.read_text(encoding='utf-8')))
                if not _json_evidence_equal(restored.state,engine.state) or not _json_evidence_equal(restored.ledger,engine.ledger):
                    raise AssertionError('native checkpoint state/ledger mismatch')
                checkpoints.append(dict(path=path.name,sha256=sha(path)))
    except Exception as exc:status,error='STOPPED',f'{type(exc).__name__}: {exc}'
    terminal=(engine.snapshot() if engine.accepted_steps==0 else engine.fast_recipe_terminal_state())
    write(output/'terminal-state.json',terminal);write(output/'accepted-recipe.json',recipe)
    report=engine.conservation_report()
    mass_scale=engine.initial_inventory['mass_kg']+abs(engine.ledger['external_mass_kg'])
    energy_scale=engine.initial_inventory['energy_J']+sum(abs(v) for k,v in engine.ledger.items() if isinstance(v,(float,int)) and k.endswith('_J'))
    residuals=dict(mass=abs(report['mass']['residual'])/mass_scale,
        energy=abs(report['energy']['residual'])/energy_scale,
        species=max(abs(v['residual']) for v in report['species'].values())/mass_scale)
    projected=restrict_state(engine.state,config,coarse_config)
    errors=terminal_differences(reference['final_state'],projected,IdealGas(**config['eos'])) if status=='COMPLETE' else None
    result=dict(schema='DINO_INTEGRATED_MESH_SENSITIVITY_V1',status=status,error=error,
        evidence_level='L1_RECIPE_AND_NATIVE_CHECKPOINTS',review='SELF_REVIEW',
        runner_sha256=sha(Path(__file__)),source_directory=str(source.resolve()),
        wall_s=time.perf_counter()-began,compute_s=compute,accepted_steps=len(recipe),
        coarse_cells=sum(len(p['mesh']['volumes']) for p in coarse_config['ducts']),
        fine_cells=sum(len(p['mesh']['volumes']) for p in config['ducts']),
        terminal_angle_deg=engine.crank_angle_unwrapped_deg,initial_inventory_relative_difference=init_error,
        cross_mesh_checkpoint_rejected=cross_mesh_rejected,checkpoints=checkpoints,
        normalized_residuals=residuals,conservation=report,final_state=engine.state,
        final_ledger=engine.ledger,largest_projected_mesh_differences=errors[:12] if errors else [],
        maximum_projected_mesh_difference=errors[0][0] if errors else None,
        mesh_independence_demonstrated=False,experimental_validation=False,
        source_configuration_sha256=sha(config_path),configuration_sha256=sha(output/'configuration.json'),
        accepted_recipe_sha256=sha(output/'accepted-recipe.json'),terminal_state_sha256=sha(output/'terminal-state.json'),
        terminal_state_kind='NATIVE_CHECKPOINT' if engine.accepted_steps==0 else 'FAST_TERMINAL_PLUS_RECIPE',
        storage_preflight=preflight,scientific_state='TRANSIENT_MESH_SENSITIVITY_NOT_VALIDATION')
    result['execution_gate']=bool(status=='COMPLETE' and max(residuals['mass'],residuals['species'])<=1e-9
        and residuals['energy']<=1e-8 and init_error<=1e-12)
    write(output/'receipt.json',result)
    print(json.dumps({k:result[k] for k in ('status','error','execution_gate','coarse_cells','fine_cells',
        'wall_s','compute_s','maximum_projected_mesh_difference','normalized_residuals')},indent=2))
    return 0 if result['execution_gate'] else 1


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    raise SystemExit(run(args.source,args.output))
