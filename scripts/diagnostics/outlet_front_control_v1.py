"""Exact translating-contact controls; isolated duct, no engine power claim."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys
import time
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from motorsim.gas1d.mesh import uniform_mesh
from motorsim.gas1d.eos import IdealGas
from motorsim.gas1d.riemann import hllc_flux
from motorsim.gas1d.boundary import Boundary
from motorsim.gas1d.spatial_reconstruction_v1 import reconstruct_v1
from motorsim.gas1d.spatial_reconstruction_v2 import reconstruct_v2
from motorsim.integrated_2t import _solver_dependency_hashes
from scripts.agents.storage_preflight import check_storage_requirements


def coverage(n,t,periodic):
    return np.array([sum(max(0.,min((i+1)/n,.75+t+k)-max(i/n,.5+t+k))*n
        for k in (range(-2,2) if periodic else (0,))) for i in range(n)])


def exact(n,t,periodic,contact):
    f=coverage(n,t,periodic);rho=1+.2*f if contact else np.ones(n)
    q=np.column_stack((rho,rho,2.5+.5*rho))
    s=np.column_stack(((1.2 if contact else 1)*f,np.zeros(n),1-f,np.zeros(n)))
    return q,s


def norms(a,b):
    d=np.abs(np.array(a)-np.array(b))
    return dict(L1=float(np.mean(d)),L2=float(np.sqrt(np.mean(d*d))),Linf=float(np.max(d)))


def crossing(y,level):
    # Rising front near exact x=.85; exclude the periodic descending front.
    for i in range(len(y)-1):
        if (i+.5)/len(y)<.55:continue
        if y[i]<=level<y[i+1]:return (i+.5+(level-y[i])/(y[i+1]-y[i]))/len(y)
    return None


def run_case(n,periodic,contact,model,scale,deadline):
    mesh=uniform_mesh(n,1.,1.);e=IdealGas(gamma=1.4,R=1.)
    outlet=Boundary('reservoir',p0=1.,T0=1.)
    q,s=exact(n,0.,periodic,contact);initial=np.r_[q.sum(axis=0),s.sum(axis=0)]/n
    budget=np.zeros(7);t=0.;steps=0
    def rhs(q,s):
        w=[e.primitive((*r,r[0])) for r in q]
        y=[tuple(r/math.fsum(r)) for r in s]
        if model=='first':left=right=w;yl=yr=y
        else:
            r=(reconstruct_v2 if model=='v2' else reconstruct_v1)(mesh,w,y,eos=e,periodic=periodic)
            left,right,yl,yr=r.left,r.right,r.species_left,r.species_right
        fs=[]
        for i in range(n+1):
            if periodic:
                l,k=(i-1)%n,i%n;f=hllc_flux(right[l],left[k],e)[0][:3];donor=yr[l] if f[0]>=0 else yl[k]
            elif i==0:
                f=hllc_flux((1.,1.,1.,1.),left[0],e)[0][:3];donor=(0.,0.,1.,0.) if f[0]>=0 else yl[0]
            elif i==n:
                f=outlet.flux(right[-1],1,e)[0][:3];donor=yr[-1] if f[0]>=0 else (0.,0.,1.,0.)
            else:
                f=hllc_flux(right[i-1],left[i],e)[0][:3];donor=yr[i-1] if f[0]>=0 else yl[i]
            fs.append((*f,*(f[0]*v/math.fsum(donor) for v in donor)))
        fs=np.array(fs);d=-(fs[1:]-fs[:-1])*n
        return d[:,:3],d[:,3:],fs[0]-fs[-1]
    while t<.35-1e-14:
        if time.perf_counter()>deadline:raise TimeoutError('120-second global budget')
        dt=min(scale*.15/(n*(1+math.sqrt(1.4))),.35-t)
        dq,ds,f0=rhs(q,s);q1=q+dt*dq;s1=s+dt*ds
        dq1,ds1,f1=rhs(q1,s1)
        q=.5*(q+q1+dt*dq1);s=.5*(s+s1+dt*ds1)
        budget+=.5*dt*(f0+f1);t+=dt;steps+=1
    eq,es=exact(n,.35,periodic,contact);y=s[:,0]/s.sum(axis=1);ey=es[:,0]/es.sum(axis=1)
    crosses=[crossing(y,v) for v in (.1,.5,.9)]
    residual=np.r_[q.sum(axis=0),s.sum(axis=0)]/n-initial-budget
    return dict(n=n,periodic=periodic,contact=contact,model=model,time_scale=scale,steps=steps,
        error_fraction=norms(y,ey),error_species_density=norms(s[:,0],es[:,0]),
        front_position_50=crosses[1],front_width_10_90=(crosses[2]-crosses[0]) if all(v is not None for v in crosses) else None,
        amplitude=[float(min(y)),float(max(y))],conservation_residual=residual.tolist(),
        boundary_transfer=budget.tolist(),profile_species=s.tolist(),profile_gas=q.tolist(),
        max_pressure_error=max(abs(e.primitive((*r,r[0]))[2]-1) for r in q))


def run():
    start=time.perf_counter();cases=[]
    for periodic,contact,model in [(True,False,'v2'),(False,False,'first'),(False,False,'v1'),(False,False,'v2'),(False,True,'v2')]:
        for n in (32,64,128):cases.append(run_case(n,periodic,contact,model,1.,start+120))
    for contact in (False,True):cases.append(run_case(128,False,contact,'v2',.5,start+120))
    projected=[]
    for a,b in zip(cases,cases[1:]):
        if (a['periodic'],a['contact'],a['model'],a['time_scale'])!=(b['periodic'],b['contact'],b['model'],b['time_scale']) or b['n']!=2*a['n']:continue
        sf=np.array(b['profile_species']).reshape(a['n'],2,4).mean(axis=1)
        sc=np.array(a['profile_species'])
        projected.append(dict(n=a['n'],periodic=a['periodic'],contact=a['contact'],model=a['model'],
            species_density=norms(sc[:,0],sf[:,0]),fraction=norms(sc[:,0]/sc.sum(axis=1),sf[:,0]/sf.sum(axis=1))))
    temporal=[]
    for b in cases[-2:]:
        a=next(a for a in cases if a['n']==128 and not a['periodic'] and a['contact']==b['contact'] and a['model']=='v2' and a['time_scale']==1)
        temporal.append(dict(contact=b['contact'],species_density=norms(np.array(a['profile_species'])[:,0],np.array(b['profile_species'])[:,0])))
    return dict(schema='DINO_OUTLET_FRONT_CONTROL_V1',cases=cases,projected_grid_differences=projected,temporal_differences=temporal,
        wall_s=time.perf_counter()-start,solver_dependency_sha256=_solver_dependency_hashes(),runner_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        evidence_level='L1_ISOLATED_CONTROL',review='SELF_REVIEW',experimental_validation=False,
        scope='Actual HLLC/reconstruction/Boundary, diagnostic SSPRK2 harness; not full integrated engine or its exhaust boundary replay.')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    preflight=check_storage_requirements([(a.output,8*1024**2)])
    if a.output.exists():raise FileExistsError('preserve earlier evidence')
    r=run();r['storage_preflight']=preflight
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(r,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    print(json.dumps(dict(cases=len(r['cases']),wall_s=r['wall_s'],max_conservation_residual=max(abs(v) for c in r['cases'] for v in c['conservation_residual']))))
