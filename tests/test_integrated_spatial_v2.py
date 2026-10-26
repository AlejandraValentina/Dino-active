from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest

from motorsim.integrated_2t import IntegratedEngine2T
from motorsim.gas1d.mesh import uniform_mesh
from motorsim.gas1d.spatial_reconstruction_v1 import SCHEMA as V1
from motorsim.gas1d.spatial_reconstruction_v2 import SCHEMA as V2,reconstruct_v2
from motorsim.port_connection_v2 import SCHEMA as PORT
from scripts.diagnostics import boundary_truncation_reference_v1 as reference
from test_integrated_2t import _case


def test_steady_nozzle_reference_meets_preregistered_boundary_order():
    r=reference.sequence(V2)
    assert r['observed_residual_orders']['actual_normalized_L1'][-1][0]>1.8
    assert r['observed_residual_orders']['actual_normalized_L1'][-1][2]>1.8
    for case in r['cases']:
        assert case['analytical_mass_flux_spread']<1e-12
        assert case['analytical_energy_flux_spread']<1e-12
        assert case['port_exact_face_relative_mass_flux_error']<1e-10


def test_both_stages_conserve_and_exact_same_model_restart():
    a,_=reference.fixture(8,V2);b,_=reference.fixture(8,V2)
    for _ in range(3):
        row=a.step(1e-8,.00006)
        for stage in row['stage_face_fluxes']:
            record=stage['exhaust']['port_connection_states']['left']
            assert record['boundary_reconstruction_model']==V2
            assert 'boundary_species_mass_fractions' in record
    report=a.conservation_report()
    assert abs(report['mass']['residual'])<1e-14
    assert abs(report['energy']['residual'])<2e-10
    assert max(abs(s['residual']) for s in report['species'].values())<1e-14
    b.restore(deepcopy(a.snapshot()))
    a.step(1e-8,.00006);b.step(1e-8,.00006)
    assert a.snapshot()==b.snapshot()
    old,_=reference.fixture(8,V1)
    with pytest.raises(ValueError,match='configuration mismatch'):old.restore(a.snapshot())


def test_new_model_is_serialized_and_old_reader_rejects_it(tmp_path):
    root=Path('results/predictive-reliability-v1/spatial-muscl-coarse')
    c=json.loads((root/'configuration.json').read_text())
    c['geometry_identity']['spatial_reconstruction_model']=V2
    e=IntegratedEngine2T.from_configuration_dict(c)
    assert e.configuration_dict()==c
    source=subprocess.run(['git','show','a4f7ceb:motorsim/integrated_2t.py'],capture_output=True,encoding='utf-8',check=True).stdout
    path=tmp_path/'old_integrated.py';path.write_text(source,encoding='utf-8')
    name='motorsim._boundary_v1_reader_reference'
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec)
    sys.modules[name]=module
    try:
        spec.loader.exec_module(module)
        with pytest.raises(ValueError,match='supported reconstruction'):
            module.IntegratedEngine2T.from_configuration_dict(c)
    finally:del sys.modules[name]
    e.spatial_reconstruction_model=V1
    with pytest.raises(ValueError,match='changed after construction'):e.step(1e-8,.00006)


@pytest.mark.parametrize('reverse',[False,True])
def test_boundary_donor_uses_trace_composition_for_signed_duct_outflow(reverse):
    mesh=uniform_mesh(6,.03,1e-4)
    gas=[(1.1768,-20. if reverse else 20.,2e5,1.)]*6
    fractions=[(.2+.05*i,.1,.7-.05*i,0.) for i in range(6)]
    species=[tuple(w[0]*v*y for y in ys) for w,v,ys in zip(gas,mesh.volumes,fractions)]
    e=_case(exhaust_mesh=mesh,exhaust_initial_states=gas,duct_species={'exhaust':species},
        exhaust_area=1e-4,transfer_area=0.,geometry_identity={'fixture':'boundary-donor-v2',
        'spatial_reconstruction_model':V2,'port_connection_model':PORT})
    r=reconstruct_v2(mesh,gas,fractions,eos=e.eos)
    face=e._assemble(e.state,0.,e.reference_rpm)['faces']['exhaust']
    side='left' if reverse else 'right';mf=face[side][0]
    assert mf<0 if reverse else mf>0
    expected=r.species_left[0] if reverse else r.species_right[-1]
    assert [v/mf for v in face[side+'_species']]==pytest.approx(expected,rel=1e-13,abs=1e-15)


def test_closed_port_has_zero_mass_energy_and_species_flux():
    # Separate genuinely closed fixture, without editing a live configuration.
    e=_case(exhaust_mesh=uniform_mesh(8),exhaust_area=0.,transfer_area=0.,
        geometry_identity={'fixture':'closed-boundary-v2','spatial_reconstruction_model':V2,
                           'port_connection_model':PORT})
    row=e.step(1e-8,.00006)
    for stage in row['stage_face_fluxes']:
        face=stage['exhaust']
        assert face['left'][0]==face['left'][2]==0.
        assert face['left_species']==(0.,0.,0.,0.)


@pytest.mark.parametrize('spatial',[None,V1])
@pytest.mark.parametrize('port',[None,PORT])
def test_existing_physical_path_is_bit_identical_to_pre_boundary_source(tmp_path,monkeypatch,spatial,port):
    new,_=reference.fixture(8,spatial,port)
    source=subprocess.run(['git','show','a4f7ceb:motorsim/integrated_2t.py'],capture_output=True,encoding='utf-8',check=True).stdout
    path=tmp_path/'old_integrated.py';path.write_text(source,encoding='utf-8')
    name='motorsim._pre_boundary_physical_reference'
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec)
    sys.modules[name]=module
    try:
        spec.loader.exec_module(module)
        with monkeypatch.context() as m:
            for attr in ('IntegratedEngine2T','EngineGeometry2T','DuctPath2T'):
                m.setattr(reference,attr,getattr(module,attr))
            old,_=reference.fixture(8,spatial,port)
        for _ in range(3):
            new.step(1e-8,.00006);old.step(1e-8,.00006)
            assert new.state==old.state and new.ledger==old.ledger
    finally:del sys.modules[name]


def test_sod_shock_and_stationary_contact_meet_unchanged_reference_limits(monkeypatch):
    from scripts.diagnostics import verify_spatial_reconstruction_v1 as diagnostic
    import test_spatial_shocks_v1 as reference_tests
    monkeypatch.setattr(diagnostic,'reconstruct_v1',reconstruct_v2)
    reference_tests.test_sod_shock_positive_species_conservation_and_exact_shock_speed()
    reference_tests.test_stationary_contact_and_pure_species_do_not_diffuse()


def test_dynamic_reed_and_heat_remain_conservative_with_boundary_capability():
    from motorsim.integrated_2t import DynamicReedBinding2T
    from motorsim.reed import ReedPetal,ReedState
    from motorsim.reed_coupling import HingedFlapGeometryV1
    from motorsim.thermal import ThermalSurface,ThermalSystem
    mesh=uniform_mesh(2,.02,1e-4)
    petal=ReedPetal('boundary-dynamic',.001,.0001,.01,10.,.01,.002,.8,'SYNTHETIC_ASSUMPTION')
    geom=HingedFlapGeometryV1('boundary-dynamic','1','SYNTHETIC_ASSUMPTION',.01,.02,
        mesh.volumes[-1],.00015,.002,.8)
    binding=DynamicReedBinding2T('intake',geom,petal,ReedState(.001,0.))
    wall=ThermalSurface('moving-wall','transfer_walls',.001,50.,'SYNTHETIC_ASSUMPTION',400.)
    e=_case(crankcase_pressure=101325.,cylinder_pressure=101325.,duct_pressure=101325.,
        intake_area=1e-5,transfer_area=0.,exhaust_area=0.,dynamic_reed_binding=binding,
        thermal_system=ThermalSystem((wall,)),thermal_locations={'moving-wall':'intake:1'},
        geometry_identity={'fixture':'boundary-dynamic-thermal-v2','spatial_reconstruction_model':V2,
                           'port_connection_model':PORT})
    for _ in range(3):e.step(1e-7,.0006)
    assert abs(e.conservation_report()['energy']['residual'])<2e-11


@pytest.mark.parametrize('pressure',[90000.,150000.])
def test_network_exchange_conserves_for_both_directions(pressure):
    from test_integrated_2t import _intake_plenum
    e=_case(intake_area=0.,transfer_area=0.,exhaust_area=0.,
        intake_plenum=_intake_plenum(pressure=pressure),
        geometry_identity={'fixture':'boundary-network-v2','spatial_reconstruction_model':V2,
                           'port_connection_model':PORT})
    for _ in range(3):e.step(1e-8,.00006)
    report=e.conservation_report()
    assert abs(report['mass']['residual'])<1e-14
    assert abs(report['energy']['residual'])<2e-11
    assert max(abs(s['residual']) for s in report['species'].values())<1e-14
