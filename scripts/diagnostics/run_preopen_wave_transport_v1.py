"""Bounded recorded39 pre-opening diagnostic; no periodic continuation."""
import argparse
from copy import deepcopy
import math
from pathlib import Path
import sys
import time
import numpy as np
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from motorsim.integrated_2t import IntegratedEngine2T,_solver_dependency_hashes,_json_evidence_equal,_integrated_scheduled_angles,_integrated_nominal_step_end
from motorsim.port_connection_v2 import NoAdmissiblePortState
from scripts.diagnostics.periodicity_refined_mesh_pilot_v1 import load
from scripts.diagnostics.periodic88_front_flux_v1 import empty_totals,accumulate,serial
from scripts.diagnostics.periodicity_extension_v4 import conserved
from scripts.diagnostics.compare_checkpoint25_sensitivity_v1 import compare_states
from scripts.diagnostics.compare_remap_representation_v1 import restrict_to
from scripts.diagnostics.diagnose_integrated_mesh_v1 import sha,write
from scripts.agents.storage_preflight import check_storage_requirements


def prepared(root,name):
    base=root/'preopen-wave-transport-v1';manifest=load(base/'manifest.json');rel='preparation-verified/'+name+'-initial.json'
    for item in (rel,'preparation-verified/receipt.json'):
        if sha(base/item)!=manifest['files'][item]:raise ValueError('prepared input changed')
    proof=load(base/'preparation-verified/receipt.json')
    if proof['solver_dependency_sha256']!=_solver_dependency_hashes() or proof['solver_steps']!=0:raise ValueError('prepared model/source differs')
    initial=load(base/rel);e=IntegratedEngine2T.from_configuration_dict(initial['configuration']);e.restore(initial['checkpoint'])
    if not _json_evidence_equal(e.snapshot(),initial['checkpoint']) or e.crank_angle_unwrapped_deg!=13680.:raise ValueError('prepared native state differs')
    return e,initial,dict(prepared_input_sha256=sha(base/rel),prepared_manifest_sha256=sha(base/'manifest.json'))


def cell_balances(initial,final,volumes,gas_faces,species_faces,wall):
    v=np.asarray(volumes);qa=np.asarray(initial['ducts']['exhaust']);qb=np.asarray(final['ducts']['exhaust'])
    sa=np.asarray(initial['species']['ducts']['exhaust']);sb=np.asarray(final['species']['ducts']['exhaust'])
    change=np.c_[(qb[:,0]-qa[:,0])*v,(qb[:,2]-qa[:,2])*v,sb-sa]
    transport=np.c_[gas_faces[:-1,0]-gas_faces[1:,0],gas_faces[:-1,2]-gas_faces[1:,2],species_faces[:-1]-species_faces[1:]]
    source=np.zeros_like(change);source[:,1]=-wall;residual=change-transport-source
    mass=np.maximum.reduce([qa[:,0]*v,qb[:,0]*v,abs(transport[:,0]),np.full(len(v),1e-30)])
    energy=np.maximum.reduce([abs(qa[:,2]*v),abs(qb[:,2]*v),abs(transport[:,1]),abs(source[:,1]),np.full(len(v),1e-30)])
    scales=np.c_[mass,energy,np.repeat(mass[:,None],4,axis=1)]
    return dict(change=change.tolist(),transport=transport.tolist(),source=source.tolist(),residual=residual.tolist(),
        maximum_normalized_residual=float(np.max(abs(residual/scales))),vector_order=['mass_kg','energy_J','fresh_kg','fuel_kg','residual_kg','burned_kg'])


def run_case(root,out,template,cap,deadline):
    if cap not in (.0625,.03125):raise ValueError('unregistered angular cap')
    if out.exists():raise FileExistsError('preserve existing case')
    start=time.perf_counter();e,initial,binding=prepared(root,template);out.mkdir(parents=True)
    write(out/'configuration.json',initial['configuration']);write(out/'initial-checkpoint.json',initial['checkpoint'])
    path=next(p for p in e.ducts if p.id=='exhaust');n=len(path.mesh.volumes)
    gas_faces=np.zeros((n+1,3));species_faces=np.zeros((n+1,4));wall=np.zeros(n);totals=empty_totals([p.id for p in e.ducts]);stages=[];original=e._assemble
    def observe(*args,**kwargs):
        kwargs['capture_trace']=True;r=original(*args,**kwargs);f=r['faces']['exhaust']
        if f['all_faces'][0][0]!=0. or f['all_faces'][0][2]!=0. or any(f['all_species_faces'][0]):raise ValueError('pre-opening isolation failed: nonzero exhaust-left transport')
        heat=np.zeros(n)
        for surface,rate in r['thermal_rates'].items():
            location=e.thermal_locations[surface]
            if location.startswith('exhaust:'):heat[int(location.split(':')[1])]+=rate
        stages.append(dict(faces=r['faces'],heat=heat));return r
    e._assemble=observe;frames=[dict(angle=e.crank_angle_unwrapped_deg,state=deepcopy(e.state),ledger=deepcopy(e.ledger))]
    recipe=[];status='COMPLETE';error=None;end=13740.;schedule=_integrated_scheduled_angles(e,end)
    try:
        while e.crank_angle_unwrapped_deg<end-1e-9:
            if time.perf_counter()-start>=180. or time.perf_counter()>=deadline:raise TimeoutError('registered case/global admission budget')
            angle=e.crank_angle_unwrapped_deg
            delta=min(end,_integrated_nominal_step_end(e,angle,end,schedule),(math.floor((angle+1e-9)/cap)+1)*cap)-angle
            rejections=[]
            for _ in range(25):
                stages.clear()
                try:row=e.step(delta/(6*9000.),delta,capture_trace=False)
                except NoAdmissiblePortState:raise
                except ValueError as exc:
                    if not any(s in str(exc) for s in ('CFL limit exceeded','inadmissible species mass','rho/p/Y inadmissible')):raise
                    rejections.append(dict(step_deg=delta,error=str(exc)));delta*=.5
                else:break
            else:raise ValueError('25 rejections')
            if len(stages)!=2:raise ValueError('expected two accepted SSPRK2 stages')
            for stage in stages:
                weight=.5*row['dt_s'];f=stage['faces']['exhaust']
                gas_faces+=weight*np.asarray(f['all_faces']);species_faces+=weight*np.asarray(f['all_species_faces']);wall+=weight*stage['heat']
                accumulate(totals,stage['faces'],weight)
            recipe.append(dict(**row,rejected_proposals=rejections));angle=e.crank_angle_unwrapped_deg
            if abs(angle-round(angle/15)*15)<1e-9:
                frames.append(dict(angle=angle,state=deepcopy(e.state),ledger=deepcopy(e.ledger)));write(out/'frames.json',frames)
                write(out/'recipe.json',recipe);write(out/'terminal-state.json',e.fast_recipe_terminal_state())
        if len(frames)!=5:raise ValueError('natural phase sampling incomplete')
    except TimeoutError as exc:status='PARTIAL_AT_BUDGET';error=str(exc)
    except Exception as exc:status='ERROR';error=f'{type(exc).__name__}: {exc}'
    balances=cell_balances(initial['checkpoint']['state'],e.state,path.mesh.volumes,gas_faces,species_faces,wall)
    global_balance=e.conservation_report()
    if status=='COMPLETE' and (not conserved(global_balance) or balances['maximum_normalized_residual']>1e-12):status='ERROR';error='conservation control failed'
    terminal=e.fast_recipe_terminal_state() if e.accepted_steps else initial['checkpoint']
    write(out/'frames.json',frames);write(out/'recipe.json',recipe);write(out/'terminal-state.json',terminal)
    result=dict(schema='PREOPEN_WAVE_TRANSPORT_CASE_V1',status=status,error=error,template=template,angular_cap_deg=cap,wall_s=time.perf_counter()-start,
        phase_start_deg=0.,phase_end_deg=e.crank_angle_unwrapped_deg-13680.,accepted_steps=len(recipe),rejected_proposals=sum(len(r['rejected_proposals']) for r in recipe),
        source=binding,configuration_sha256=sha(out/'configuration.json'),solver_dependency_sha256=_solver_dependency_hashes(),runner_sha256=sha(Path(__file__)),
        interfaces=serial(totals),exhaust_face_integrated_gas=gas_faces.tolist(),exhaust_face_integrated_species=species_faces.tolist(),exhaust_wall_heat_J=wall.tolist(),
        exhaust_cell_balances=balances,global_conservation=global_balance,
        partial_arc_work_J=-(e.ledger['cylinder_work_J']-initial['checkpoint']['ledger']['cylinder_work_J']),
        terminal_kind='FAST_RECIPE_V1_TERMINAL_STATE_REQUIRES_INITIAL_AND_REPLAY' if e.accepted_steps else 'INITIAL_NATIVE_CHECKPOINT',
        qualification='0-60deg diagnostic of recorded39; no new periodic cycle, no IMEP/power or mesh-independence claim.')
    write(out/'receipt.json',result);return result


def needs_p1(root,out):
    a,b=out/'p0-88',out/'p0-176';ca,cb=load(a/'configuration.json'),load(b/'configuration.json')
    fa,fb=load(a/'frames.json')[-1],load(b/'frames.json')[-1]
    spatial=compare_states(fa['state'],restrict_to(fb['state'],cb,ca),ca)['exhaust']['burned_absolute_fraction']['L1']
    half=load(out/'p0-176-timehalf/frames.json')[-1]
    if not fa['angle']==fb['angle']==half['angle']:raise ValueError('admission comparison phases differ')
    temporal=compare_states(restrict_to(fb['state'],cb,ca),restrict_to(half['state'],cb,ca),ca)['exhaust']['burned_absolute_fraction']['L1']
    prep=load(root/'preopen-wave-transport-v1/preparation-verified/receipt.json')
    representation=prep['initialization']['p1-176']['subcell_fields_vs_root_P0']['exhaust']['burned_absolute_fraction']['L1']
    justified=temporal<=spatial and representation>=.1*spatial
    return dict(exhaust_burned_spatial_L1=spatial,temporal_common88_L1=temporal,initial_representation_L1=representation,run=justified,
        reason='Conditional CPU decision: initial P1 contrast >=10% spatial marker signal and temporal does not dominate. No scientific acceptance thresholds changed.')


def admission_estimate(static_estimate,reference_wall,reference_cells,cells,cap):
    if reference_wall is None:return static_estimate
    return max(static_estimate,reference_wall*cells/reference_cells*.0625/cap)


def run(root,out):
    preflight=check_storage_requirements([(out,32*1024**2)])
    if out.exists():raise FileExistsError('preserve diagnostic')
    out.mkdir(parents=True);start=time.perf_counter();cases=[];status='COMPLETE';error=None;reference=None
    specs=[('p0-88','p0-88',.0625,40.),('p0-176','p0-176',.0625,65.),('p0-352','p0-352',.0625,105.),('p0-176-timehalf','p0-176',.03125,130.),('p1-176','p1-176',.0625,65.)]
    try:
        for name,template,cap,estimate in specs:
            if name=='p1-176':
                decision=needs_p1(root,out);write(out/'p1-admission-decision.json',decision)
                if decision['temporal_common88_L1']>decision['exhaust_burned_spatial_L1']:status='STOP_TEMPORAL_DOMINANCE';break
                if not decision['run']:continue
            cells=352 if template=='p0-352' else 88 if template=='p0-88' else 176
            estimate=admission_estimate(estimate,reference,88,cells,cap)
            remaining=480.-(time.perf_counter()-start)
            write(out/(name+'-admission.json'),dict(remaining_s=remaining,projected_s=estimate,required_with_margin_s=1.2*estimate,admitted=remaining>=1.2*estimate))
            if remaining<1.2*estimate:status='STOP_ADMISSION_BUDGET';break
            result=run_case(root,out/name,template,cap,start+480.);cases.append(dict(name=name,status=result['status'],wall_s=result['wall_s']))
            if reference is None:reference=result['wall_s']
            write(out/'progress.json',dict(cases=cases,wall_s=time.perf_counter()-start))
            if result['status']!='COMPLETE':status=result['status'];error=result['error'];break
    except Exception as exc:status='ERROR';error=f'{type(exc).__name__}: {exc}'
    receipt=dict(schema='PREOPEN_WAVE_TRANSPORT_RUN_V1',status=status,error=error,cases=cases,wall_s=time.perf_counter()-start,
        storage_preflight=preflight,runner_sha256=sha(Path(__file__)),solver_dependency_sha256=_solver_dependency_hashes(),
        new_periodic_cycles=0,periodicity_audited=False,mesh_independence=False,experimental_validation=False,review='SELF_REVIEW')
    write(out/'receipt.json',receipt);print({k:receipt[k] for k in ('status','error','wall_s','cases')});return 1 if status=='ERROR' else 0


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();raise SystemExit(run(a.root,a.output))
