"""Small-amplitude reflected Gaussian and direct boundary reversal controls."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys
import time
import numpy as np
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from motorsim.gas1d.mesh import uniform_mesh
from motorsim.gas1d.eos import IdealGas
from motorsim.gas1d.riemann import hllc_flux
from motorsim.gas1d.spatial_reconstruction_v2 import reconstruct_v2
from motorsim.gas1d.open_end_plenum_v2 import OpenEndPlenumV2Boundary
from scripts.agents.storage_preflight import check_storage_requirements
from scripts.diagnostics.outlet_front_control_v1 import norms
from motorsim.integrated_2t import _solver_dependency_hashes


def gaussian_average(a,b,center,sigma=.07):
    f=lambda x:math.erf((x-center)/(math.sqrt(2)*sigma))
    return sigma*math.sqrt(math.pi/2)*(f(b)-f(a))/(b-a)


def acoustic(n,scale,deadline):
    e=IdealGas(gamma=1.4,R=1.);sound=math.sqrt(1.4);eps=1e-5
    mesh=uniform_mesh(n,1.,1.);out=OpenEndPlenumV2Boundary(p0=1.,T0=1.)
    g=np.array([gaussian_average(a,b,.35) for a,b in zip(mesh.faces,mesh.faces[1:])])
    rho=1+eps*g/1.4;u=eps*g/sound;p=1+eps*g
    q=np.column_stack((rho,rho*u,p/.4+.5*rho*u*u));s=np.column_stack((0*rho,0*rho,rho,0*rho))
    initial=np.r_[q.sum(axis=0),s.sum(axis=0)]/n;ledger=np.zeros(7);absolute=np.zeros(7)
    history=[];t=0.;steps=0
    def rhs(q,s):
        w=[e.primitive((*r,r[0])) for r in q];y=[tuple(r/sum(r)) for r in s]
        r=reconstruct_v2(mesh,w,y,eos=e);flux=[]
        for i in range(n+1):
            if i==0:
                f=hllc_flux((1.,0.,1.,1.),r.left[0],e)[0][:3];donor=(1.,0.,0.,0.) if f[0]>=0 else r.species_left[0]
            elif i==n:
                face=out.resolve(r.right[-1],1,e);f=e.flux(face.state)[:3];donor=r.species_right[-1] if f[0]>=0 else (1.,0.,0.,0.)
            else:
                f=hllc_flux(r.right[i-1],r.left[i],e)[0][:3];donor=r.species_right[i-1] if f[0]>=0 else r.species_left[i]
            flux.append((*f,*(f[0]*v/sum(donor) for v in donor)))
        flux=np.array(flux);d=-(flux[1:]-flux[:-1])*n
        return d[:,:3],d[:,3:],flux[0]-flux[-1],flux[-1]
    while t<.8-1e-14:
        if time.perf_counter()>deadline:raise TimeoutError('bounded acoustic budget')
        dt=min(scale*.15/(n*(sound+eps)),.8-t)
        dq,ds,b0,f0=rhs(q,s);q1=q+dt*dq;s1=s+dt*ds
        dq,ds,b1,f1=rhs(q1,s1)
        q=.5*(q+q1+dt*dq);s=.5*(s+s1+dt*ds)
        ledger+=dt*.5*(b0+b1);absolute+=dt*.5*(abs(b0)+abs(b1))
        history.append([t+dt,*((f0+f1)*.5).tolist()]);t+=dt;steps+=1
    incident=np.array([gaussian_average(a,b,.35+sound*t) for a,b in zip(mesh.faces,mesh.faces[1:])])
    reflected=np.array([gaussian_average(a,b,2-.35-sound*t) for a,b in zip(mesh.faces,mesh.faces[1:])])
    pressure=np.array([e.primitive((*r,r[0]))[2] for r in q]);velocity=q[:,1]/q[:,0]
    perturb=(pressure-1)/eps;target=incident-reflected
    weight=np.maximum(0,-perturb);centroid=float(np.dot(mesh.centers,weight)/sum(weight))
    return dict(n=n,time_scale=scale,steps=steps,pressure_error=norms(perturb,target),
        velocity_error=norms(velocity/(eps/sound),incident+reflected),
        reflected_amplitude=float(-min(perturb)),reflected_centroid=centroid,
        exact_centroid=2-.35-sound*.8,centroid_phase_error_s=(centroid-(2-.35-sound*.8))/sound,
        conservation_residual=(np.r_[q.sum(axis=0),s.sum(axis=0)]/n-initial-ledger).tolist(),
        net_boundary_transfer=ledger.tolist(),absolute_boundary_transfer=absolute.tolist(),
        outlet_history=history,pressure_profile=pressure.tolist(),species=s.tolist())


def reversal():
    e=IdealGas(gamma=1.4,R=1.);b=OpenEndPlenumV2Boundary(p0=1.,T0=1.)
    rows=[]
    for u in [0.,-1e-12,1e-12]+[.15*math.sin(2*math.pi*i/100) for i in range(301)]:
        r=b.resolve((.8,u,1.,1.),1,e);f=e.flux(r.state)
        enthalpy=(f[2]/f[0]) if f[0] else None
        rows.append(dict(u=u,mass_flux=f[0],energy_flux=f[2],branch=r.branch,
            reservoir_donor=r.reservoir_donor,total_enthalpy=enthalpy,
            inflow_enthalpy_error=abs(enthalpy-e.cp) if r.reservoir_donor and f[0] else 0.))
    return rows


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    preflight=check_storage_requirements([(args.output,8*1024**2)])
    if args.output.exists():raise FileExistsError('preserve earlier evidence')
    start=time.perf_counter();cases=[acoustic(n,1.,start+120) for n in (32,64,128)]
    cases.append(acoustic(128,.5,start+120))
    rows=reversal();result=dict(schema='DINO_PULSATING_OUTLET_CONTROL_V1',cases=cases,reversals=rows,
        wall_s=time.perf_counter()-start,storage_preflight=preflight,solver_dependency_sha256=_solver_dependency_hashes(),
        runner_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        qualification='Linear acoustic reference valid to small-amplitude truncation; direct reversals are boundary algebra, not full coupled reversal trajectories.',review='SELF_REVIEW',experimental_validation=False)
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(wall_s=result['wall_s'],cases=[dict(n=c['n'],L1=c['pressure_error']['L1'],amplitude=c['reflected_amplitude'],phase=c['centroid_phase_error_s']) for c in cases])))
