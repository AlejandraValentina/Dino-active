"""Mirrored isentropic reference with the reservoir at the right duct end."""
import argparse
import math
from pathlib import Path
import sys
import json

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from motorsim.integrated_2t import IntegratedEngine2T,EngineGeometry2T,DuctPath2T,_solver_dependency_hashes
from motorsim.gas1d.mesh import uniform_mesh
from motorsim.gas1d.boundary import Boundary
from motorsim.gas1d.spatial_reconstruction_v1 import SCHEMA as V1
from motorsim.gas1d.spatial_reconstruction_v2 import SCHEMA as V2
from motorsim.port_connection_v2 import SCHEMA as PORT
from scripts.diagnostics import boundary_truncation_reference_v1 as base
from scripts.diagnostics.diagnose_integrated_mesh_v1 import write,sha
from scripts.agents.storage_preflight import check_storage_requirements


def reversed_state(w):return w[0],-w[1],w[2],w[3]


def diagnose(n,model):
    original,mesh=base.fixture(n,model)
    e=original.eos;aux=uniform_mesh(2,.02,1e-4)
    paths=(DuctPath2T('intake',mesh,'intake'),DuctPath2T('transfer',aux,'transfer'),
           DuctPath2T('exhaust',aux,'exhaust'))
    reservoir=(base.P0/(e.R*base.T0),0.,base.P0,1.)
    states={p.id:([reversed_state(original._primitive(q)) for q in original.state['ducts']['exhaust']]
                 if p.id=='intake' else [reservoir]*p.mesh.n) for p in paths}
    species={p.id:[tuple(w[0]*v*f for f in base.FRACTIONS) for w,v in zip(states[p.id],p.mesh.volumes)] for p in paths}
    species.update({name:tuple(reservoir[0]*v*f for f in base.FRACTIONS)
                    for name,v in [('crankcase',.00015),('cylinder',.00018)]})
    def geometry(angle):return EngineGeometry2T(.00015,.00018,0.,0.,mesh.areas[-1],(0.,),0.)
    engine=IntegratedEngine2T(reservoir,reservoir,paths,states,geometry,eos=e,species=species,
        atmosphere=(base.P0,base.T0),atmosphere_species=base.FRACTIONS,outlet_species=base.FRACTIONS,
        inlet_boundary=Boundary('fixed',state=reversed_state(base.reference(0.,e))),
        geometry_identity={'fixture':'steady-reversed-nozzle-v1','port_connection_model':PORT,
                           'spatial_reconstruction_model':model})
    stage=engine._assemble(engine.state,0.,engine.reference_rpm)
    exact=[tuple(a*f for f in e.flux(reversed_state(base.reference(x,e)))[:3]) for x,a in zip(mesh.faces,mesh.areas)]
    rho=reservoir[0];sound=math.sqrt(e.gamma*e.R*base.T0)
    scales=(rho*sound/base.LENGTH,base.P0/base.LENGTH,base.P0*sound/base.LENGTH)
    rhs=stage['q']['ducts']['intake'];volume=sum(mesh.volumes)
    norms=[math.fsum(abs(row[k])*v for row,v in zip(rhs,mesh.volumes))/(volume*scales[k]) for k in range(3)]
    face=stage['faces']['intake']['right']
    chamber=engine._chamber_state(engine.state['chambers']['crankcase'],engine.state['species']['chambers']['crankcase'])
    exchange=engine._port_exchange(chamber,reversed_state(base.reference(base.LENGTH,e)),mesh.areas[-1],mesh.areas[-1],1)
    return dict(cells=n,spatial_model=model,normalized_L1=norms,
        right_mass_flux_relative_error=abs(face[0]-exact[-1][0])/abs(exact[-1][0]),
        exact_right_face_connection_error=abs(exchange.flux_x[0]-exact[-1][0])/abs(exact[-1][0]))


def run():
    results={}
    for model in (V1,V2):
        cases=[diagnose(n,model) for n in (20,40,80,160)]
        orders=[[math.log(a['normalized_L1'][k]/b['normalized_L1'][k],2) for k in range(3)]
                 for a,b in zip(cases,cases[1:])]
        results[model]=dict(cases=cases,residual_orders=orders)
    return dict(schema='DINO_REVERSED_NOZZLE_TRUNCATION_V1',solver_steps=0,time_integrations=0,
        review='SELF_REVIEW',models=results,solver_dependency_sha256=_solver_dependency_hashes(),
        runner_sha256=sha(Path(__file__)),reference_helper_sha256=sha(Path(base.__file__)),
        experimental_validation=False,physical_equations_modified=False)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();check_storage_requirements([(args.output,1024**2)])
    if args.output.exists():raise FileExistsError('preserve reference artifacts')
    result=run();write(args.output,result)
    print(json.dumps({key:value['residual_orders'][-1] for key,value in result['models'].items()}))
