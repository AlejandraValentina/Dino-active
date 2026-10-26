from copy import deepcopy
import math
import json
from pathlib import Path

import pytest

from motorsim.gas1d.mesh import segments_mesh,uniform_mesh
from scripts.diagnostics.diagnose_integrated_mesh_v1 import bisect_frustum_mesh,refined_configuration,restrict_state,read_bound_reference,sha,write
from test_integrated_spatial_v1 import case


def test_refined_native_configuration_roundtrips_without_format_coercion():
    from motorsim.integrated_2t import IntegratedEngine2T
    original=json.loads(Path('results/predictive-reliability-v1/spatial-muscl-coarse/configuration.json').read_text(encoding='utf-8'))
    fine=refined_configuration(original,'a'*64)
    restored=IntegratedEngine2T.from_configuration_dict(fine)
    assert restored.configuration_dict()==fine


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


@pytest.mark.parametrize('name',['spatial-muscl-coarse','mesh-refined-v1'])
def test_hash_bound_native_reference_accepts_both_existing_formats(name):
    r,c,s=read_bound_reference(Path('results/predictive-reliability-v1')/name)
    assert r['terminal_angle_deg']==s['crank_angle_unwrapped_deg']==720.
    assert sha(c)==r['configuration_sha256']


@pytest.mark.parametrize('fault',['config_hash','checkpoint_hash','phase','fast','gate','summary','schema'])
def test_reference_loader_fails_closed_before_writing_or_stepping(tmp_path,fault):
    source=Path('results/predictive-reliability-v1/mesh-refined-v1')
    for name in ('configuration.json','terminal-state.json','receipt.json'):
        (tmp_path/name).write_bytes((source/name).read_bytes())
    r=json.loads((tmp_path/'receipt.json').read_text())
    s=json.loads((tmp_path/'terminal-state.json').read_text())
    if fault=='config_hash':r['configuration_sha256']='0'*64
    elif fault=='checkpoint_hash':r['terminal_state_sha256']='0'*64
    elif fault=='phase':
        s['crank_angle_unwrapped_deg']=360.
        write(tmp_path/'terminal-state.json',s)
        r['terminal_state_sha256']=sha(tmp_path/'terminal-state.json')
    elif fault=='fast':r['terminal_state_kind']='FAST_TERMINAL_PLUS_RECIPE'
    elif fault=='gate':r['execution_gate']=1
    elif fault=='summary':r['final_state']['chambers']['cylinder'][0]*=2.
    elif fault=='schema':r['schema']='unknown'
    write(tmp_path/'receipt.json',r)
    with pytest.raises(ValueError):read_bound_reference(tmp_path)


def test_second_refinement_remains_conservative_and_reconstructible():
    from motorsim.integrated_2t import IntegratedEngine2T
    source=Path('results/predictive-reliability-v1/mesh-refined-v1/configuration.json')
    coarse=json.loads(source.read_text())
    fine=refined_configuration(coarse,sha(source))
    a,b=(IntegratedEngine2T.from_configuration_dict(c) for c in (coarse,fine))
    assert sum(p.mesh.n for p in b.ducts)==176
    for key in ('mass_kg','energy_J'):
        assert a.inventory()[key]==pytest.approx(b.inventory()[key],rel=1e-12)
    assert a.inventory()['species_kg']==pytest.approx(b.inventory()['species_kg'],rel=1e-12)
    assert sum(s.area_m2 for s in a.thermal_system.surfaces)==pytest.approx(
        sum(s.area_m2 for s in b.thermal_system.surfaces),rel=1e-14)
