"""Replay one recorded cycle; stream signed species fluxes, preserve solver."""
import argparse
import json
from pathlib import Path
import sys
import time
import numpy as np
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from motorsim.integrated_2t import IntegratedEngine2T,_json_evidence_equal,_solver_dependency_hashes
from scripts.diagnostics.diagnose_integrated_mesh_v1 import sha,write
from scripts.agents.storage_preflight import check_storage_requirements


def run(root,out):
    check_storage_requirements([(out,8*1024**2)])
    if out.exists():raise FileExistsError('preserve audit')
    src=root/'periodicity-extension-v2/run';load=lambda p:json.loads(p.read_text(encoding='utf-8'))
    receipt=load(src/'receipt.json')
    if receipt['solver_dependency_sha256']!=_solver_dependency_hashes():raise ValueError('solver source mismatch')
    config=load(root/'spatial-boundary-v2-engine/configuration.json')
    if sha(root/'spatial-boundary-v2-engine/configuration.json')!=receipt['configuration_sha256']:raise ValueError('config mismatch')
    a,z=load(src/'checkpoint-022.json'),load(src/'checkpoint-023.json')
    manifest=load(root/'periodicity-extension-v2/manifest.json');hashes={k.replace('\\','/'):v for k,v in manifest['files'].items()}
    for name in ('checkpoint-022.json','checkpoint-023.json','recipe.json'):
        if sha(src/name)!=hashes['run/'+name]:raise ValueError('recorded evidence hash mismatch')
    e=IntegratedEngine2T.from_configuration_dict(config);e.restore(a);original=e._assemble;stages=[]
    def observer(*args,**kwargs):
        kwargs['capture_trace']=True;r=original(*args,**kwargs)
        stages.append({name:dict(left=np.array(f['all_species_faces'][0]),right=np.array(f['all_species_faces'][-1]),
            mass_left=f['all_faces'][0][0],mass_right=f['all_faces'][-1][0]) for name,f in r['faces'].items()})
        return r
    e._assemble=observer
    totals={p.id:{side:{'net':np.zeros(4),'positive':np.zeros(4),'negative':np.zeros(4),'positive_mass':0.,'negative_mass':0.} for side in ('left','right')} for p in e.ducts}
    recipe=[r for r in load(src/'recipe.json') if r['angle_start_deg']>=7920.];start=time.perf_counter()
    for row in recipe:
        if time.perf_counter()-start>90:raise TimeoutError('90s replay budget')
        stages.clear();dt=row['dt_s'];e.step(dt,row['angle_end_deg']-row['angle_start_deg'],capture_trace=False)
        if len(stages)!=2:raise ValueError('expected exactly two SSPRK stages')
        for stage in stages:
            for name,f in stage.items():
                for side in ('left','right'):
                    s=f[side];m=f['mass_'+side];t=totals[name][side];t['net']+=.5*dt*s
                    t['positive' if m>=0 else 'negative']+=.5*dt*s
                    t['positive_mass' if m>=0 else 'negative_mass']+=.5*dt*m
    exact=_json_evidence_equal(e.state,z['state']) and _json_evidence_equal(e.ledger,z['ledger'])
    if not exact:raise ValueError('replayed terminal physical state/ledger differs')
    inventories=lambda c:{**{k:np.array(v) for k,v in c['state']['species']['chambers'].items()},**{k:np.sum(v,axis=0) for k,v in c['state']['species']['ducts'].items()}}
    ia,iz=inventories(a),inventories(z);net=lambda name,side:totals[name][side]['net'];transfers=[p.id for p in e.ducts if p.role=='transfer']
    sources=np.array(z['ledger']['fuel_combustion_source_species_kg'])-a['ledger']['fuel_combustion_source_species_kg']
    p7=np.array(z['ledger']['p7_source_species_kg'])-a['ledger']['p7_source_species_kg']
    balances={}
    for name in ia:
        if name=='cylinder':transport=sum((net(p,'right') for p in transfers),np.zeros(4))-net('exhaust','left');source=sources+p7
        elif name=='crankcase':transport=net('intake','right')-sum((net(p,'left') for p in transfers),np.zeros(4));source=np.zeros(4)
        else:transport=net(name,'left')-net(name,'right');source=np.zeros(4)
        change=iz[name]-ia[name]
        balances[name]=dict(start=ia[name].tolist(),end=iz[name].tolist(),change=change.tolist(),transport=transport.tolist(),source=source.tolist(),residual=(change-transport-source).tolist())
    gross_exhaust_out=totals['exhaust']['right']['positive_mass'];gross_in=-totals['exhaust']['right']['negative_mass']
    mean_mass=.5*(sum(ia['exhaust'])+sum(iz['exhaust']))
    for endpoints in totals.values():
        for t in endpoints.values():
            for key in ('net','positive','negative'):t[key]=t[key].tolist()
    result=dict(schema='DINO_SPECIES_INTERFACE_AUDIT_V1',cycle=23,replayed_steps=len(recipe),wall_s=time.perf_counter()-start,
        terminal_state_and_ledger_exact=exact,interfaces=totals,balances=balances,
        exhaust_gross_out_kg=gross_exhaust_out,exhaust_gross_in_kg=gross_in,
        exhaust_turnover_cycles=mean_mass/gross_exhaust_out if gross_exhaust_out else None,
        qualification='Turnover is gross outflow/inventory diagnostic, not an exponential relaxation constant under recirculation.',
        solver_dependency_sha256=_solver_dependency_hashes(),runner_sha256=sha(Path(__file__)),
        source_checkpoint_sha256=sha(src/'checkpoint-022.json'),evidence_level='L1_STREAMED_ACTUAL_STAGE_FLUX_REPLAY',experimental_validation=False)
    out.parent.mkdir(parents=True,exist_ok=True);write(out,result)
    print(json.dumps(dict(wall_s=result['wall_s'],max_subsystem_species_residual=max(abs(x) for b in balances.values() for x in b['residual']),exact=exact,turnover=result['exhaust_turnover_cycles'])))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();run(a.root,a.output)
