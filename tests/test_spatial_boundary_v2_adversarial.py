import math

import pytest

from motorsim.gas1d.eos import IdealGas
from motorsim.gas1d.mesh import Mesh,uniform_mesh
from motorsim.gas1d.spatial_reconstruction_v2 import reconstruct_v2,SCHEMA
from motorsim.port_connection_v2 import SCHEMA as PORT
from motorsim.integrated_2t import IntegratedNetworkVolume2T
from motorsim.network_components import VolumeNode,NetworkConnection,VolumeGasState
from test_integrated_2t import _case


def test_extrapolation_that_would_reach_zero_density_remains_strictly_positive():
    m=uniform_mesh(4)
    # Exact one-sided linear extrapolation rho=0 at x=0. Cell mean remains >0.
    w=[(x,0.,1e5*x,1.) for x in m.centers]
    r=reconstruct_v2(m,w,[(1.,0.,0.,0.)]*4,eos=IdealGas())
    assert r.left[0][0]>0 and r.left[0][2]>0
    assert r.species_left[0]==(1.,0.,0.,0.)


def test_unequal_cells_and_near_zero_species_remain_admissible():
    faces=(0.,1e-5,.001,.1,1.)
    m=Mesh(faces,(1.,)*5,tuple(b-a for a,b in zip(faces,faces[1:])),
           tuple((a+b)/2 for a,b in zip(faces,faces[1:])))
    w=[(1.+x,10*x,1e5+100*x,1.) for x in m.centers]
    y=[(1.-2e-15,1e-15,1e-15,0.),(.8,.1,.1,0.),(.5,.2,.3,0.),(.2,.3,.5,0.)]
    r=reconstruct_v2(m,w,y,eos=IdealGas())
    for row in (*r.species_left,*r.species_right):
        assert min(row)>=0 and max(row)<=1
        assert abs(math.fsum(row)-1)<4e-15
        assert row[3]==0.


@pytest.mark.parametrize('pressure',[90000.,150000.])
def test_nonconstant_exhaust_composition_uses_actual_reconstructed_network_donor(pressure):
    m=uniform_mesh(6,.03,1e-4);eos=IdealGas();mass=pressure*.001/(eos.R*300.)
    ys=[(.2+.05*i,.1,.7-.05*i,0.) for i in range(6)]
    species=[tuple(1.1768*v*y for y in row) for row,v in zip(ys,m.volumes)]
    node=VolumeNode('outlet','plenum',.001,'SYNTHETIC_ASSUMPTION')
    binding=IntegratedNetworkVolume2T(node,NetworkConnection('neck','exhaust','outlet',
        1e-5,.05,'SYNTHETIC_ASSUMPTION'),'exhaust','right',
        VolumeGasState(mass,pressure*.001/(eos.gamma-1),tuple(mass*y for y in (.3,.1,.4,.2))))
    e=_case(exhaust_mesh=m,network_volumes=(binding,),duct_species={'exhaust':species},
        transfer_area=0.,exhaust_area=0.,geometry_identity={'fixture':'network-boundary-trace',
        'spatial_reconstruction_model':SCHEMA,'port_connection_model':PORT})
    row=e._assemble(e.state,0.,e.reference_rpm)['faces']['exhaust']
    flux=row['right'][0]
    primitive=[e._primitive(q) for q in e.state['ducts']['exhaust']]
    r=reconstruct_v2(m,primitive,ys,eos=eos)
    expected=r.species_right[-1] if pressure<101325. else (.3,.1,.4,.2)
    assert flux>0 if pressure<101325. else flux<0
    assert tuple(v/flux for v in row['right_species'])==pytest.approx(expected,rel=1e-12,abs=1e-14)
