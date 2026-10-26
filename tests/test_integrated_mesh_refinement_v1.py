from copy import deepcopy
import math

import pytest

from motorsim.gas1d.mesh import segments_mesh,uniform_mesh
from scripts.diagnostics.diagnose_integrated_mesh_v1 import bisect_frustum_mesh,refined_configuration,restrict_state
from test_integrated_spatial_v1 import case


def test_trace_free_and_full_trace_preserve_identical_muscl_physical_steps():
    full,fast=case(),case()
    for _ in range(5):
        full.step(1e-8,.00006)
        fast.step(1e-8,.00006,capture_trace=False)
        assert full.state==fast.state
        assert full.ledger==fast.ledger


@pytest.mark.parametrize('mesh',[
    uniform_mesh(4),segments_mesh([{'length':100.,'start_diameter':10.,'end_diameter':20.}],.03)])
def test_frustum_bisection_preserves_volume_moments_and_end_areas(mesh):
    fine=bisect_frustum_mesh(mesh.as_dict())
    assert len(fine['volumes'])==2*mesh.n
    assert fine['areas'][0]==mesh.areas[0] and fine['areas'][-1]==mesh.areas[-1]
    for i,v in enumerate(mesh.volumes):
        assert sum(fine['volumes'][2*i:2*i+2])==pytest.approx(v,rel=1e-12)
        moment=sum(a*b for a,b in zip(fine['volumes'][2*i:2*i+2],fine['centers'][2*i:2*i+2]))
        assert moment==pytest.approx(v*mesh.centers[i],rel=1e-12)


def test_unjustified_volume_is_rejected_instead_of_forced_to_fit():
    mesh=uniform_mesh(4).as_dict();mesh['volumes'][0]*=1.01
    with pytest.raises(ValueError,match='not the assumed exact linear frustum'):
        bisect_frustum_mesh(mesh)


def test_initial_species_prolongation_and_field_restriction_are_conservative():
    m=uniform_mesh(3).as_dict();states=[(1.,.2,1e5,1.)]*3
    species=[tuple(v*x for x in (.4,.2,.3,.1)) for v in m['volumes']]
    coarse={'geometry_identity':{},'ducts':[{'id':'pipe','mesh':m}],
        'initial_duct_states':{'pipe':states},'duct_species':{'pipe':species}}
    before=deepcopy(coarse)
    fine=refined_configuration(coarse,'a'*64)
    assert coarse==before
    state={'chambers':{},'ducts':{'pipe':[(1.,.2,3e5,1.)]*6},
        'species':{'chambers':{},'ducts':fine['duct_species']}}
    projected=restrict_state(state,fine,coarse)
    for i,row in enumerate(projected['species']['ducts']['pipe']):
        assert row==pytest.approx(species[i],rel=1e-12)
    for q in projected['ducts']['pipe']:
        assert q==pytest.approx((1.,.2,3e5,1.),rel=1e-12)


def test_wall_source_remapping_conserves_area_h_and_uniform_heat_transfer():
    from motorsim.thermal import ThermalSurface,ThermalSystem
    m=uniform_mesh(3).as_dict()
    wall=ThermalSurface('wall','exhaust_walls',.02,50.,'SYNTHETIC_ASSUMPTION',400.)
    system=ThermalSystem((wall,))
    c={'geometry_identity':{},'ducts':[{'id':'pipe','mesh':m}],
        'initial_duct_states':{'pipe':[(1.,0.,1e5,1.)]*3},
        'duct_species':{'pipe':[(v,0.,0.,0.) for v in m['volumes']]},
        'thermal_system':system.to_dict(),'thermal_locations':{'wall':'pipe:1'}}
    fine=refined_configuration(c,'a'*64)
    surfaces=fine['thermal_system']['surfaces']
    assert sum(s['area_m2'] for s in surfaces)==pytest.approx(.02,rel=1e-15)
    assert {s['heat_transfer_w_m2k'] for s in surfaces}=={50.}
    assert {s['wall_temperature_K'] for s in surfaces}=={400.}
    assert set(fine['thermal_locations'].values())=={'pipe:2','pipe:3'}
    refined=ThermalSystem.from_dict(fine['thermal_system'])
    heat=sum(refined.heat_rate_w(s.id,300.,9000.,1.) for s in refined.surfaces)
    assert heat==pytest.approx(system.heat_rate_w('wall',300.,9000.,1.),rel=1e-14)
