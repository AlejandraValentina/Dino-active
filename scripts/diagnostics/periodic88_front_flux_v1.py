"""Saved-state front localization and exact existing39 interface-flux replay.

Diagnostic only: no new cycles, changes to physics, or periodicity criteria.
"""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import sys
import time
import numpy as np
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from motorsim.integrated_2t import IntegratedEngine2T,_json_evidence_equal,_solver_dependency_hashes
from scripts.agents.storage_preflight import check_storage_requirements
from scripts.diagnostics.diagnose_integrated_mesh_v1 import sha,write
from scripts.diagnostics.periodicity_refined_mesh_pilot_v1 import load


def front_delta(previous,current,x,volumes,gamma):
    """Same physical cells and phase; acoustic/contact split is linearized only."""
    a,b=previous,current;x=np.asarray(x);v=np.asarray(volumes)
    qa,qb=np.asarray(a['ducts']['exhaust']),np.asarray(b['ducts']['exhaust'])
    sa,sb=np.asarray(a['species']['ducts']['exhaust']),np.asarray(b['species']['ducts']['exhaust'])
    ya,yb=sa/sa.sum(axis=1)[:,None],sb/sb.sum(axis=1)[:,None]
    pressure=lambda q:(gamma-1)*(q[:,2]-.5*q[:,1]**2/q[:,0])
    pa,pb=pressure(qa),pressure(qb);drho=qb[:,0]-qa[:,0];dp=pb-pa
    rho=.5*(qa[:,0]+qb[:,0]);p=.5*(pa+pb);acoustic=dp/(gamma*p/rho)
    result={}
    for k,name in enumerate(('fresh_air','fuel','residual','burned')):
        dy=yb[:,k]-ya[:,k];w=abs(dy)*v;total=float(sum(w))
        center=float(np.dot(w,x)/total) if total else None
        result[name]=dict(L1=float(total/sum(v)),L2=float(np.sqrt(np.dot(v,dy**2)/sum(v))),Linf=float(max(abs(dy))),
            max_cell=int(np.argmax(abs(dy))),max_x_m=float(x[np.argmax(abs(dy))]),
            discrepancy_centroid_m=center,discrepancy_width_std_m=float(np.sqrt(np.dot(w,(x-center)**2)/total)) if total else None,
            inventory_start_kg=float(sum(sa[:,k])),inventory_end_kg=float(sum(sb[:,k])),
            absolute_inventory_change_kg=float(sum(sb[:,k]-sa[:,k])),
            cellwise_absolute_species_change_kg=float(sum(abs(sb[:,k]-sa[:,k]))),
            fraction_deltaY_weight_with_abs_dp_over_p_below_1e3=float(sum(w[abs(dp)/p<1e-3])/total) if total else None)
    return dict(species=result,pressure_relative_L1=float(np.dot(v,abs(dp))/np.dot(v,p)),
        density_relative_L1=float(np.dot(v,abs(drho))/np.dot(v,rho)),
        density_change_L1_kg=float(np.dot(v,abs(drho))),
        linearized_acoustic_density_L1_kg=float(np.dot(v,abs(acoustic))),
        linearized_contact_density_L1_kg=float(np.dot(v,abs(drho-acoustic))),
        qualification='Absolute weighted terms can cancel; linearized acoustic/contact split is an indicator, not an exact nonlinear mode decomposition.')


def saved_fronts(root):
    first=root/'periodic88-pilot-v1/run';second=root/'periodic88-window2-v1/run'
    config=load(second/'configuration.json');mesh=next(p['mesh'] for p in config['ducts'] if p['id']=='exhaust')
    previous=None;rows=[]
    for absolute in range(31,40):
        source=first if absolute<=35 else second
        frames=load(source/f'frames-absolute-{absolute:03}.json')
        if previous is not None:
            phases=[]
            for a,b in zip(previous,frames):
                phase=b['angle']-360*(absolute-1)
                if phase!=a['angle']-360*(absolute-2):raise ValueError('physical phases differ')
                phases.append(dict(phase_deg=phase,**front_delta(a['state'],b['state'],mesh['centers'],mesh['volumes'],config['eos']['gamma'])))
            rows.append(dict(absolute_cycle=absolute,relative_cycle=absolute-30,phases=phases))
        previous=frames
    return dict(schema='SAVED88_FRONT_DIFFERENCES_V1',cycles=rows,units='SI; composition fractions dimensionless',new_solver_steps=0)


def empty_totals(names):
    return {name:{side:{key:np.zeros(n) for key,n in (('gas_net',3),('species_net',4),('gas_positive',3),('gas_negative',3),('species_positive',4),('species_negative',4))} for side in ('left','right')} for name in names}


def accumulate(totals,faces,weight):
    for name,f in faces.items():
        for side,index in (('left',0),('right',-1)):
            gas=np.asarray(f['all_faces'][index]);species=np.asarray(f['all_species_faces'][index]);t=totals[name][side]
            sign='positive' if gas[0]>=0 else 'negative'
            t['gas_net']+=weight*gas;t['species_net']+=weight*species
            t['gas_'+sign]+=weight*gas;t['species_'+sign]+=weight*species


def inventories(engine,state):
    result={name:dict(mass_kg=q[0],energy_J=q[1],species_kg=np.asarray(state['species']['chambers'][name])) for name,q in state['chambers'].items()}
    for path in engine.ducts:
        q=np.asarray(state['ducts'][path.id]);v=np.asarray(path.mesh.volumes)
        result[path.id]=dict(mass_kg=float(np.dot(v,q[:,0])),energy_J=float(np.dot(v,q[:,2])),species_kg=np.sum(state['species']['ducts'][path.id],axis=0))
    return result


def balance_rows(initial,final,totals,transfers,work,wall,chemical,p7):
    answer={}
    def flux(name,side):
        t=totals[name][side];return np.r_[t['gas_net'][0],t['gas_net'][2],t['species_net']]
    for name,a in initial.items():
        b=final[name];source=np.zeros(6)
        if name=='cylinder':transport=sum((flux(t,'right') for t in transfers),np.zeros(6))-flux('exhaust','left');source[2:]=chemical['species']+p7['species'];source[1]=chemical['heat']+p7['heat']
        elif name=='crankcase':transport=flux('intake','right')-sum((flux(t,'left') for t in transfers),np.zeros(6))
        else:transport=flux(name,'left')-flux(name,'right')
        source[1]+=work.get(name,0.)-wall.get(name,0.)
        va=np.r_[a['mass_kg'],a['energy_J'],a['species_kg']];vb=np.r_[b['mass_kg'],b['energy_J'],b['species_kg']]
        residual=vb-va-transport-source
        mass_scale=max(a['mass_kg'],b['mass_kg'],abs(transport[0]),1e-30)
        energy_scale=max(abs(a['energy_J']),abs(b['energy_J']),abs(transport[1]),abs(source[1]),1e-30)
        species_scale=max(mass_scale,float(max(abs(transport[2:]))),float(max(abs(source[2:]))))
        normalized=residual/np.r_[mass_scale,energy_scale,[species_scale]*4]
        answer[name]=dict(start=va.tolist(),end=vb.tolist(),change=(vb-va).tolist(),transport=transport.tolist(),source=source.tolist(),residual=residual.tolist(),normalized_residual=normalized.tolist())
    return answer


def serial(value):
    if isinstance(value,np.ndarray):return value.tolist()
    if isinstance(value,dict):return {k:serial(v) for k,v in value.items()}
    if isinstance(value,list):return [serial(v) for v in value]
    return value


def run(root,out):
    preflight=check_storage_requirements([(out,8*1024**2)])
    if out.exists():raise FileExistsError('preserve previous diagnosis')
    start=time.perf_counter();src=root/'periodic88-window2-v1';manifest=load(src/'manifest.json')
    def bound(name):
        if sha(src/name)!=manifest['files'][name]:raise ValueError('source evidence hash differs: '+name)
        return load(src/name)
    config=bound('run/configuration.json');a=bound('run/checkpoint-absolute-038.json');z=bound('run/checkpoint-absolute-039.json');receipt=bound('run/receipt.json')
    if receipt['source_solver_sha256']!=_solver_dependency_hashes():raise ValueError('solver dependencies differ')
    recipe=[r for r in bound('run/recipe.json') if r['angle_start_deg']>=13680.]
    e=IntegratedEngine2T.from_configuration_dict(config);e.restore(a)
    if e.dynamic_reed_binding is not None or e.state['network_volumes']:raise ValueError('diagnostic supports fixed duct volumes/no network only')
    if not _json_evidence_equal(e.snapshot(),a):raise ValueError('native source roundtrip differs')
    out.mkdir(parents=True);write(out/'saved-fronts.json',saved_fronts(root))
    stages=[];original=e._assemble
    def observer(*args,**kwargs):
        kwargs['capture_trace']=True;r=original(*args,**kwargs)
        stages.append(dict(faces=r['faces'],work=r['work_rates'],thermal=r['thermal_rates']))
        return r
    e._assemble=observer;totals=empty_totals([p.id for p in e.ducts]);windows=[];window=empty_totals(totals)
    work={n:0. for n in ('cylinder','crankcase')};wall={n:0. for n in totals|work};rejected=0
    for row in recipe:
        if time.perf_counter()-start>120:raise TimeoutError('120s exact existing39 replay budget')
        for attempt in row['rejected_proposals']:
            try:e.step(attempt['step_deg']/(6*9000.),attempt['step_deg'],capture_trace=False)
            except ValueError as exc:
                if str(exc)!=attempt['error']:raise ValueError('rejection differs') from exc
                rejected+=1
            else:raise ValueError('recorded rejection accepted')
        stages.clear();actual=e.step(row['dt_s'],row['angle_end_deg']-row['angle_start_deg'],capture_trace=False)
        if not all(_json_evidence_equal(actual[k],v) for k,v in row.items() if k!='rejected_proposals'):raise ValueError('accepted recipe differs')
        if len(stages)!=2:raise ValueError('expected two SSPRK2 stages')
        for stage in stages:
            weight=.5*row['dt_s'];accumulate(totals,stage['faces'],weight);accumulate(window,stage['faces'],weight)
            for name,rate in stage['work'].items():work[name]+=weight*rate
            for surface,rate in stage['thermal'].items():wall[e.thermal_locations[surface].split(':')[0]]+=weight*rate
        phase=row['angle_end_deg']-13680.
        if abs(phase-round(phase/30)*30)<1e-9:
            windows.append(dict(phase_end_deg=phase,interfaces=serial(window)));window=empty_totals(totals)
    if e.crank_angle_unwrapped_deg!=14040. or not _json_evidence_equal(e.state,z['state']) or not _json_evidence_equal(e.ledger,z['ledger']):raise ValueError('terminal physical state/ledger differs')
    e.compact_fast_recipe_cycle()
    if not _json_evidence_equal(e.snapshot(),z):raise ValueError('terminal native checkpoint differs')
    led=a['ledger'];end=z['ledger'];chemical=dict(species=np.asarray(end['fuel_combustion_source_species_kg'])-led['fuel_combustion_source_species_kg'],heat=end['fuel_combustion_heat_added_J']-led['fuel_combustion_heat_added_J'])
    p7=dict(species=np.asarray(end['p7_source_species_kg'])-led['p7_source_species_kg'],heat=end['p7_heat_added_J']-led['p7_heat_added_J'])
    ia,iz=inventories(e,a['state']),inventories(e,z['state'])
    balances=balance_rows(ia,iz,totals,[p.id for p in e.ducts if p.role=='transfer'],work,wall,chemical,p7)
    maximum=max(abs(v) for b in balances.values() for v in b['normalized_residual'])
    gross_out=totals['exhaust']['right']['gas_positive'][0];gross_in=-totals['exhaust']['right']['gas_negative'][0]
    result=dict(schema='PERIODIC88_EXISTING39_FRONT_FLUX_V1',status='PASS' if maximum<=1e-12 else 'FAIL',wall_s=time.perf_counter()-start,
        replayed_accepted_steps=len(recipe),replayed_rejected_proposals=rejected,terminal_native_checkpoint_exact=True,new_cycles=0,
        balance_vector_order=['mass_kg','energy_J','fresh_air_kg','fuel_kg','residual_kg','burned_kg'],balances=balances,
        maximum_normalized_balance_residual=maximum,interfaces=serial(totals),phase_windows=windows,work_on_gas_J=work,heat_to_wall_J=wall,
        chemical=serial(chemical),p7=serial(p7),exhaust_gross_out_kg=float(gross_out),exhaust_gross_in_kg=float(gross_in),
        exhaust_turnover_cycles=float(.5*(ia['exhaust']['mass_kg']+iz['exhaust']['mass_kg'])/gross_out) if gross_out else None,
        qualification='Gross inventory/outflow ratio is not a relaxation eigenvalue. All face fluxes already include area. Sign groups use stage mass-flow sign; energy is transported total enthalpy.',
        configuration_sha256=sha(src/'run/configuration.json'),source_manifest_sha256=sha(src/'manifest.json'),source_checkpoint_sha256=sha(src/'run/checkpoint-absolute-038.json'),
        solver_dependency_sha256=_solver_dependency_hashes(),runner_sha256=sha(Path(__file__)),storage_preflight=preflight,
        evidence_level='L1_STREAMED_ACTUAL_STAGE_FLUX_EXACT_REPLAY',review='SELF_REVIEW',periodicity_audited=False,mesh_independence=False,experimental_validation=False)
    write(out/'receipt.json',result);print(json.dumps({k:result[k] for k in ('status','wall_s','maximum_normalized_balance_residual','replayed_accepted_steps','exhaust_gross_out_kg','exhaust_gross_in_kg')}))
    return 0 if result['status']=='PASS' else 1


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);args=p.parse_args();raise SystemExit(run(args.root,args.output))
