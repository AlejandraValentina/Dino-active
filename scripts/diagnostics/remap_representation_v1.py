"""Diagnostic initial-field uncertainty, not a production remapper or warm start.

P0 and limited P1 conserve the *original* cell averages on every grid. P1 is
one possible unresolved field, not recovered information or measured truth.
"""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
import numpy as np

ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from motorsim.integrated_2t import IntegratedEngine2T
from scripts.diagnostics.diagnose_integrated_mesh_v1 import refined_configuration,restrict_state
from scripts.diagnostics.checkpoint_mesh_sensitivity_v1 import run


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def configurations(config,level):
    chain=[config]
    for _ in range(level):chain.append(refined_configuration(chain[-1],digest(chain[-1])))
    return chain


def project(state,coarse,fine,family):
    if family not in ('P0','P1'):raise ValueError('unknown representation')
    result=deepcopy(state);original={p['id']:p['mesh'] for p in coarse['ducts']};limited=0
    for path in fine['ducts']:
        name=path['id'];mesh=original[name];target=path['mesh']
        v=np.array(mesh['volumes']);x=np.array(mesh['centers'])
        q=np.array(state['ducts'][name]);s=np.array(state['species']['ducts'][name])/v[:,None]
        values=np.column_stack((q,s));slopes=np.zeros_like(values)
        if family=='P1' and len(x)>2:
            left=np.diff(values,axis=0)/np.diff(x)[:,None]
            slopes[1:-1]=np.where(left[:-1]*left[1:]>0,
                np.sign(left[:-1])*np.minimum(abs(left[:-1]),abs(left[1:])),0.)
            # Preserve mass/species closure and legacy marker offsets.
            slopes[:,0]=slopes[:,4:].sum(axis=1);slopes[:,3]=slopes[:,0]
        factor=len(target['volumes'])//len(v)
        if factor*len(v)!=len(target['volumes']):raise ValueError('nested mesh required')
        for i in range(len(v)):
            offsets=np.array([mesh['faces'][i]-x[i],mesh['faces'][i+1]-x[i]])
            theta=1.
            for _ in range(60):
                endpoints=values[i]+offsets[:,None]*slopes[i]*theta
                rho,mom,energy=endpoints[:,0],endpoints[:,1],endpoints[:,2]
                if np.all(rho>0) and np.all(energy-.5*mom*mom/rho>0) and np.all(endpoints[:,4:]>=0):break
                theta*=.5
            else:raise ValueError('no admissible conservative reconstruction')
            if theta<1:limited+=1
            slopes[i]*=theta
        mapped=[];species=[]
        for j,(xc,vol) in enumerate(zip(target['centers'],target['volumes'])):
            i=j//factor;row=values[i]+(xc-x[i])*slopes[i]
            mapped.append(row[:4].tolist());species.append((row[4:]*vol).tolist())
        result['ducts'][name]=mapped;result['species']['ducts'][name]=species
    return result,limited


def initialize(config,checkpoint,level,family,checkpoint_hash):
    if checkpoint['trace'] or checkpoint['accepted_steps']!=0:raise ValueError('native compact checkpoint required')
    if level not in (0,1,2):raise ValueError('only three declared grids')
    if level==0:
        engine=IntegratedEngine2T.from_configuration_dict(config);engine.restore(checkpoint)
        return engine,config,dict(kind='SAME_SIMULATION_RESUME',representation=family,level=0)
    chain=configurations(config,level);fine=chain[-1]
    fine['geometry_identity']['diagnostic_initialization']=dict(schema='CONSERVATIVE_SUBCELL_REPRESENTATION_V1',
        representation=family,root_checkpoint_sha256=checkpoint_hash,root_configuration_sha256=digest(config),level=level)
    engine=IntegratedEngine2T.from_configuration_dict(fine);template=engine.snapshot();mapped=deepcopy(checkpoint)
    mapped['configuration_identity']=template['configuration_identity'];mapped['initial_inventory']=template['initial_inventory']
    mapped['state'],limited=project(checkpoint['state'],config,fine,family)
    mapped['trace_origin_state'],_=project(checkpoint['trace_origin_state'],config,fine,family)
    engine.restore(mapped)
    old=IntegratedEngine2T.from_configuration_dict(config).inventory(checkpoint['state']);new=engine.inventory()
    pairs=[(old['mass_kg'],new['mass_kg']),(old['energy_J'],new['energy_J'])]+list(zip(old['species_kg'],new['species_kg']))
    error=max(abs(a-b)/max(abs(a),abs(b),1e-30) for a,b in pairs)
    restricted=engine.state
    for k in range(level,0,-1):restricted=restrict_state(restricted,chain[k],chain[k-1])
    max_error=max(abs(a-b)/max(abs(a),abs(b),1e-30) for n in checkpoint['state']['ducts']
        for qa,qb in zip(checkpoint['state']['ducts'][n],restricted['ducts'][n]) for a,b in zip(qa,qb))
    if error>1e-12 or max_error>1e-12:raise ValueError('nonconservative initial projection')
    return engine,fine,dict(kind='NEW_DIAGNOSTIC_INITIAL_FIELD',representation=family,level=level,
        inventory_max_relative_error=error,restriction_max_relative_error=max_error,positivity_limited_cells=limited,
        qualification='P1 is an admissible unresolved-field hypothesis, not reconstructed experimental information.')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--level',type=int,choices=(0,1,2),required=True);p.add_argument('--family',choices=('P0','P1'),required=True)
    p.add_argument('--step',type=float,choices=(.125,.0625),default=.125);p.add_argument('--budget',type=float,default=240)
    a=p.parse_args()
    def initializer(config,checkpoint,unused,parent_hash,cp_hash):return initialize(config,checkpoint,a.level,a.family,cp_hash)
    raise SystemExit(run(a.root,a.output,bool(a.level),a.step,initializer=initializer,budget_seconds=a.budget))
