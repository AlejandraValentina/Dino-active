"""Isolated smooth-wave convergence with exact cell-average references."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from motorsim.gas1d.eos import IdealGas
from motorsim.gas1d.mesh import uniform_mesh
from motorsim.gas1d.riemann import hllc_flux
from motorsim.gas1d.spatial_reconstruction_v1 import reconstruct_v1
from scripts.agents.storage_preflight import check_storage_requirements


def average_wave(a,b,frequency=1,*,cosine=False,shift=0.):
    k=2*math.pi*frequency
    if cosine:
        return (math.sin(k*(b-shift))-math.sin(k*(a-shift)))/(k*(b-a))
    return (math.cos(k*(a-shift))-math.cos(k*(b-shift)))/(k*(b-a))


def entropy_cell(a,b,t=0.):
    s=average_wave(a,b,shift=t)
    c=average_wave(a,b,cosine=True,shift=t)
    s2=average_wave(a,b,2,shift=t)
    rho=1+.2*s
    species=(.4+.08*s+.1*c+.01*s2,.2+.04*s,
             .3+.06*s-.05*c-.005*s2,.1+.02*s-.05*c-.005*s2)
    return rho,species


def initial(mesh,kind,e):
    gas,species=[],[]
    for a,b in zip(mesh.faces,mesh.faces[1:]):
        if kind=='entropy':
            rho,ys=entropy_cell(a,b)
            q=(rho,rho,1/(e.gamma-1)+.5*rho)
        else:
            eps=1e-6; sound=math.sqrt(e.gamma)
            s=average_wave(a,b)
            s2=.5-.5*average_wave(a,b,2,cosine=True)
            s3=(3*s-average_wave(a,b,3))/4
            rho=1+eps*s
            q=(rho,sound*eps*(s+eps*s2),
                (1+e.gamma*eps*s)/(e.gamma-1)+.5*sound**2*eps**2*(s2+eps*s3))
            ys=tuple(rho*y for y in (.4,.2,.3,.1))
        gas.append(q);species.append(ys)
    return gas,species


def spatial_rhs(mesh,gas,species,e,model,*,periodic=True):
    n=mesh.n
    w=[e.primitive((*q,q[0])) for q in gas]
    ys=[tuple(v/math.fsum(row) for v in row) for row in species]
    if model=='muscl':
        r=reconstruct_v1(mesh,w,ys,eos=e,periodic=periodic)
        left,right=r.left,r.right
        yl,yr=r.species_left,r.species_right
    else:
        left=right=w;yl=yr=ys
    fluxes,sfluxes=[],[]
    for i in range(n if periodic else n+1):
        if periodic:
            l,k=i,(i+1)%n
        else:
            l,k=max(0,i-1),min(n-1,i)
        flux,_,_=hllc_flux(right[l],left[k],e)
        donor=yr[l] if flux[0]>=0 else yl[k]
        sf=tuple(flux[0]*v/math.fsum(donor) for v in donor)
        fluxes.append(flux[:3]);sfluxes.append(sf)
    dq,ds=[],[]
    for i,dx in enumerate(mesh.widths):
        l,r=((i-1)%n,i) if periodic else (i,i+1)
        dq.append(tuple(-(fluxes[r][j]-fluxes[l][j])/dx for j in range(3)))
        ds.append(tuple(-(sfluxes[r][j]-sfluxes[l][j])/dx for j in range(4)))
    return dq,ds


def advance(mesh,gas,species,e,model,dt,*,periodic=True):
    dq,ds=spatial_rhs(mesh,gas,species,e,model,periodic=periodic)
    q1=[tuple(v+dt*s for v,s in zip(q,r)) for q,r in zip(gas,dq)]
    s1=[tuple(v+dt*s for v,s in zip(q,r)) for q,r in zip(species,ds)]
    dq,ds=spatial_rhs(mesh,q1,s1,e,model,periodic=periodic)
    q2=[tuple(.5*(v+w+dt*s) for v,w,s in zip(q,r,d)) for q,r,d in zip(gas,q1,dq)]
    s2=[tuple(.5*(v+w+dt*s) for v,w,s in zip(q,r,d)) for q,r,d in zip(species,s1,ds)]
    return q2,s2


def run_case(n,kind,model):
    e=IdealGas(gamma=1.4)
    mesh=uniform_mesh(n,1.,1.)
    gas,species=initial(mesh,kind,e)
    initial_totals=[math.fsum(q[k]/n for q in gas) for k in (0,2)]
    initial_species=[math.fsum(s[k]/n for s in species) for k in range(4)]
    t=0.;steps=0
    while t<.1:
        maximum=max(abs(q[1]/q[0])+e.sound_speed(e.primitive((*q,q[0]))) for q in gas)
        dt=min(.1-t,.2/(n*maximum))
        gas,species=advance(mesh,gas,species,e,model,dt)
        t+=dt;steps+=1
    rho_error=species_error=pressure_error=0.
    for i,(q,s) in enumerate(zip(gas,species)):
        a,b=mesh.faces[i:i+2]
        w=e.primitive((*q,q[0]))
        if kind=='entropy':
            exact,sy=entropy_cell(a,b,t)
            rho_error+=abs(q[0]-exact)/n
            species_error+=sum(abs(v-z) for v,z in zip(s,sy))/(4*n)
            pressure_error+=abs(w[2]-1)/n
        else:
            p=1+e.gamma*1e-6*average_wave(a,b,shift=math.sqrt(e.gamma)*t)
            pressure_error+=abs(w[2]-p)/n
    final_totals=[math.fsum(q[k]/n for q in gas) for k in (0,2)]
    final_species=[math.fsum(s[k]/n for s in species) for k in range(4)]
    residual=max(abs(a-b) for a,b in zip(initial_totals+initial_species,final_totals+final_species))
    return dict(n=n,kind=kind,model=model,steps=steps,rho_L1=rho_error,
        species_L1=species_error,pressure_L1=pressure_error,conservation_abs=residual)


def verify():
    began=time.perf_counter()
    rows=[]
    for kind in ('entropy','acoustic'):
        for model in ('legacy','muscl'):
            for n in (40,80,160):
                if time.perf_counter()-began>60:
                    raise TimeoutError('isolated spatial verification exceeded budget')
                rows.append(run_case(n,kind,model))
    orders={}
    for kind,metric in [('entropy','rho_L1'),('entropy','species_L1'),('acoustic','pressure_L1')]:
        for model in ('legacy','muscl'):
            values=[r[metric] for r in rows if r['kind']==kind and r['model']==model]
            orders[f'{kind}:{model}:{metric}']=math.log2(values[-2]/values[-1])
    passed=(orders['entropy:muscl:rho_L1']>=1.7 and
        orders['entropy:muscl:species_L1']>=1.7 and orders['acoustic:muscl:pressure_L1']>=1.6 and
        max(r['conservation_abs'] for r in rows)<=1e-11)
    return dict(schema='DINO_SPATIAL_RECONSTRUCTION_V1_VERIFICATION',passed=passed,
        cases=rows,observed_final_orders=orders,wall_s=time.perf_counter()-began,
        cfl=.2,gas_gamma=1.4,physical_time=.1,initialization='EXACT_CELL_AVERAGES',
        acoustic_reference='LINEARIZED_AMPLITUDE_1E-6_NONLINEAR_ERROR_O_EPSILON_SQUARED',
        engine_steps=0,review='SELF_REVIEW',experimental_validation=False)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    preflight=check_storage_requirements([(args.output.parent,1024**2)])
    result=verify();result['storage_preflight']=preflight
    result['source_sha256']={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in (
        'motorsim/gas1d/spatial_reconstruction_v1.py','scripts/diagnostics/verify_spatial_reconstruction_v1.py')}
    args.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:result[k] for k in ('passed','observed_final_orders','wall_s')},indent=2))
    raise SystemExit(0 if result['passed'] else 1)
