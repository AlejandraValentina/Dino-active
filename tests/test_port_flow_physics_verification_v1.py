"""Diagnostic reference checks; no change to frozen physics or thresholds."""
import pytest
from copy import deepcopy

from scripts.diagnostics.verify_port_flow_physics_v1 import (
    matched_case, finite_run, solve_pipe_mach, mass_density)
from motorsim.gas1d.eos import IdealGas
from motorsim.port_connection_v2 import SCHEMA
from scripts.diagnostics.summarize_port_flow_impact_v1 import assert_matched_configurations


@pytest.mark.parametrize('direction', ['chamber_to_pipe','pipe_to_chamber'])
@pytest.mark.parametrize('normal',[-1,1])
def test_independent_nozzle_station_and_donor_enthalpy(direction,normal):
    row = matched_case(.1,.65,.3,normal,direction)
    assert row['candidate_max_relative_error'] <= 1e-9
    assert row['candidate_h0_ratio'] == pytest.approx(1.,rel=1e-12)


def test_legacy_and_exact_riemann_share_the_weak_flow_limitation():
    row = matched_case(1.,1.,.01,-1,'chamber_to_pipe')
    assert .49 < row['legacy_mass_ratio'] < .51
    assert .49 < row['exact_riemann_mass_ratio'] < .51
    assert row['candidate_max_relative_error'] < 1e-9


@pytest.mark.parametrize('supersonic',[False,True])
def test_independent_continuity_inversion(supersonic):
    e = IdealGas()
    m = solve_pipe_mach(.1,1.,e,supersonic=supersonic)
    assert mass_density(2e5,300,m,e) == pytest.approx(.1*mass_density(2e5,300,1,e),rel=1e-12)
    assert (m>1) == supersonic


@pytest.mark.parametrize('model',['legacy','candidate'])
@pytest.mark.parametrize('pc,pi',[(1e5,2e5),(2e5,1e5)])
def test_finite_chamber_species_conservation_and_checkpoint(model,pc,pi):
    result = finite_run(pc,pi,model)
    assert result['gate']
    flux = result['signed_chamber_to_pipe_integrals']
    assert (flux[0]>0) == (pc>pi)
    assert sum(flux[2:]) == pytest.approx(flux[0],rel=1e-12)


def comparison_configs():
    a=dict(schema='MOTORSIM_INTEGRATED_ENGINE_2T_CONFIG_V6',
           geometry_identity={'fixture':'unchanged'},eos={'gamma':1.35})
    b=deepcopy(a)
    b.update(schema='MOTORSIM_INTEGRATED_ENGINE_2T_CONFIG_V7',base_configuration_schema=a['schema'])
    b['geometry_identity']['port_connection_model']=SCHEMA
    return a,b


def test_only_versioned_boundary_change_is_permitted():
    a,b=comparison_configs()
    assert_matched_configurations(a,b)
    assert b['geometry_identity']['port_connection_model']==SCHEMA
    b['eos']['gamma']=1.4
    with pytest.raises(AssertionError,match='additional physics'):
        assert_matched_configurations(a,b)


def test_muscl_is_rejected_even_if_both_inputs_enable_it():
    a,b=comparison_configs()
    for c in (a,b):
        c['geometry_identity']['spatial_reconstruction_model']='muscl'
    with pytest.raises(AssertionError):
        assert_matched_configurations(a,b)
