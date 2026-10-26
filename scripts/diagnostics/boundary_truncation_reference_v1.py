"""Instantaneous steady-nozzle spatial residuals; no engine time integration.

Independent isentropic reference, exact frustum cell averages by Gauss quadrature.
The chamber is frozen only for this duct-operator check, not a steady finite 0D
engine. Oracle fluxes below are diagnostics, never installed in the solver.
"""
import argparse
import json
import math
from pathlib import Path
import sys
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from motorsim.integrated_2t import DuctPath2T,EngineGeometry2T,IntegratedEngine2T,_solver_dependency_hashes
from motorsim.gas1d.eos import IdealGas
from motorsim.gas1d.mesh import segments_mesh,uniform_mesh
from motorsim.gas1d.boundary import Boundary
from motorsim.gas1d.spatial_reconstruction_v1 import SCHEMA as SPATIAL
from motorsim.gas1d.spatial_reconstruction_v2 import SCHEMA as SPATIAL_V2
from motorsim.port_connection_v2 import SCHEMA as PORT
from scripts.agents.storage_preflight import check_storage_requirements
from scripts.diagnostics.diagnose_integrated_mesh_v1 import write,sha

LENGTH=.3
P0,T0=200000.,300.
FRACTIONS=(.7,.03,.27,0.)


def area(x):return math.pi/4*(.03-.005*x/LENGTH)**2


def reference(x,eos):
    # A*M*(1+(gamma-1)*M^2/2)^(-(gamma+1)/(2*(gamma-1))) = constant.
    # This reference does not call the candidate's area/Mach inversion.
    g=eos.gamma
    phi=lambda m:m*(1+(g-1)*m*m/2)**(-(g+1)/(2*(g-1)))
    target=area(0)*phi(.2)/area(x)
    lo,hi=0.,1.
    if not 0<target<phi(1.):raise ValueError('reference leaves subsonic branch')
    for _ in range(65):
        m=(lo+hi)/2
        if phi(m)<target:lo=m
        else:hi=m
    m=(lo+hi)/2;t=T0/(1+(g-1)*m*m/2)
    p=P0*(t/T0)**(g/(g-1));rho=p/(eos.R*t)
    return (rho,m*math.sqrt(g*eos.R*t),p,1.)


def cell_means(mesh,eos,quadrature_order=8):
    nodes,weights=np.polynomial.legendre.leggauss(quadrature_order)
    means=[]
    for i,(a,b) in enumerate(zip(mesh.faces,mesh.faces[1:])):
        sums=[[] for _ in range(3)]
        for node,weight in zip(nodes,weights):
            x=(a+b)/2+(b-a)*node/2
            q=eos.conservative(reference(float(x),eos))
            for k in range(3):sums[k].append(float(weight)*area(x)*q[k]*(b-a)/2)
        means.append(tuple(math.fsum(s)/mesh.volumes[i] for s in sums))
    return means


def fixture(n,spatial=SPATIAL,port=PORT):
    eos=IdealGas(gamma=1.35)
    mesh=segments_mesh([dict(length=300.,start_diameter=30.,end_diameter=25.)],LENGTH/n)
    assert mesh.n==n
    means=cell_means(mesh,eos)
    auxiliary=uniform_mesh(2,.02,1e-4)
    paths=(DuctPath2T('intake',auxiliary,'intake'),
           DuctPath2T('transfer',auxiliary,'transfer'),DuctPath2T('exhaust',mesh,'exhaust'))
    reservoir=(P0/(eos.R*T0),0.,P0,1.)
    states={p.id:([eos.primitive((*q,q[0])) for q in means] if p.id=='exhaust'
                 else [reservoir]*p.mesh.n) for p in paths}
    species={p.id:[tuple(w[0]*v*f for f in FRACTIONS)
                   for w,v in zip(states[p.id],p.mesh.volumes)] for p in paths}
    species.update({name:tuple(reservoir[0]*volume*f for f in FRACTIONS)
                    for name,volume in [('crankcase',.00015),('cylinder',.00018)]})
    geometry_type=EngineGeometry2T
    def geometry(angle):
        return geometry_type(.00015,.00018,0.,0.,0.,(0.,),area(0.))
    engine=IntegratedEngine2T(reservoir,reservoir,paths,states,geometry,eos=eos,
        species=species,atmosphere=(P0,T0),atmosphere_species=FRACTIONS,
        outlet_species=FRACTIONS,outlet_boundary=Boundary('fixed',state=reference(LENGTH,eos)),
        geometry_identity=dict(fixture='steady-nozzle-spatial-residual-v1',
            port_connection_model=port,spatial_reconstruction_model=spatial))
    return engine,mesh


def diagnose(n,spatial=SPATIAL):
    engine,mesh=fixture(n,spatial);eos=engine.eos
    assembled=engine._assemble(engine.state,0.,engine.reference_rpm)
    actual=assembled['q']['ducts']['exhaust']
    exact=[tuple(a*f for f in eos.flux(reference(x,eos))[:3]) for x,a in zip(mesh.faces,mesh.areas)]
    trace=assembled['faces']['exhaust']
    boundary_errors={side:{'relative_mass_flux_error':abs(trace[side][0]-exact[i][0])/abs(exact[i][0]),
        'relative_energy_flux_error':abs(trace[side][2]-exact[i][2])/abs(exact[i][2])}
        for side,i in [('left',0),('right',-1)]}
    # Re-evaluate the connection with exact face data to separate boundary
    # input sampling error from the connection equation itself.
    chamber=engine._chamber_state(engine.state['chambers']['cylinder'],
                                engine.state['species']['chambers']['cylinder'])
    face_exchange=engine._port_exchange(chamber,reference(0.,eos),area(0.),area(0.),-1)
    port_face_error=abs(face_exchange.flux_x[0]-exact[0][0])/abs(exact[0][0])
    # Same pressure-area source as production, all face fluxes analytically exact.
    oracle=[]
    for i,v in enumerate(mesh.volumes):
        row=[-(exact[i+1][k]-exact[i][k])/v for k in range(3)]
        p=engine._primitive(engine.state['ducts']['exhaust'][i])[2]
        row[1]+=p*(mesh.areas[i+1]-mesh.areas[i])/v
        oracle.append(row)
    sound=math.sqrt(eos.gamma*eos.R*T0)
    scales=(P0/(eos.R*T0)*sound/LENGTH,P0/LENGTH,P0*sound/LENGTH)
    def norms(rows,indices):
        volume=math.fsum(mesh.volumes[i] for i in indices)
        return [math.fsum(abs(rows[i][k])*mesh.volumes[i] for i in indices)/(volume*scales[k]) for k in range(3)]
    indices=list(range(n));interior=list(range(2,n-2))
    return dict(cells=n,boundary_flux_errors=boundary_errors,
        port_exact_face_relative_mass_flux_error=port_face_error,
        actual_normalized_L1=norms(actual,indices),
        interior_normalized_L1=norms(actual,interior),
        exact_all_face_flux_source_oracle_L1=norms(oracle,indices),
        analytical_mass_flux_spread=max(abs(f[0]-exact[0][0]) for f in exact)/abs(exact[0][0]),
        analytical_energy_flux_spread=max(abs(f[2]-exact[0][2]) for f in exact)/abs(exact[0][2]))


def sequence(spatial=SPATIAL):
    cases=[diagnose(n,spatial) for n in (20,40,80,160)]
    orders={}
    for key in ('actual_normalized_L1','interior_normalized_L1','exact_all_face_flux_source_oracle_L1'):
        orders[key]=[[math.log(a[key][k]/b[key][k],2) if a[key][k]>1e-12 and b[key][k]>1e-12 else None
                      for k in range(3)] for a,b in zip(cases,cases[1:])]
    return dict(schema='DINO_STEADY_NOZZLE_TRUNCATION_REFERENCE_V1',review='SELF_REVIEW',
        solver_steps=0,time_integrations=0,spatial_model=spatial,cases=cases,observed_residual_orders=orders,
        components=['mass','momentum','energy'],runner_sha256=sha(Path(__file__)),
        solver_dependency_sha256=_solver_dependency_hashes(),
        source='NASA isentropic area-Mach/mass/total-state relations; independent bisection and volume quadrature',
        scientific_scope='Instantaneous duct spatial operator with frozen reservoir; not a steady complete finite-volume engine or periodic motor.',
        physical_equations_modified=False,experimental_validation=False)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--model',choices=['muscl-v1','boundary-v2'],default='muscl-v1')
    args=p.parse_args();check_storage_requirements([(args.output,1024**2)])
    if args.output.exists():raise FileExistsError('preserve previous reference')
    r=sequence(SPATIAL_V2 if args.model=='boundary-v2' else SPATIAL);write(args.output,r)
    print(json.dumps(r,indent=2))
