"""E2A observer/preparation tests; no solver time steps outside its budget."""
from copy import deepcopy
import numpy as np
import pytest
from motorsim.gas1d.mesh import uniform_mesh
from scripts.diagnostics.e2a_exhaust_waves_v1 import lag,overlap_weights,variant_b


def test_positive_lag_means_later_b_and_is_offset_invariant():
    t=np.arange(501)*.5
    a=np.exp(-((t-110)/4)**2)
    b=7+2*np.exp(-((t-113)/4)**2)
    x=lag(a,b)
    assert x['valid']
    assert x['lag_deg']==pytest.approx(3.,abs=.01)
    assert x['correlation']==pytest.approx(1.)


def test_flat_signal_cannot_define_wave_phase():
    assert not lag(np.ones(100),np.ones(100))['valid']


def test_physical_sensor_weights_conserve_a_constant_field_on_both_grids():
    for n in (8,16):
        w=overlap_weights(uniform_mesh(n,.1,1e-4).as_dict(),.04)
        assert w.sum()==pytest.approx(1.)
        assert w.dot(np.full(n,101325.))==pytest.approx(101325.)


def test_exact_overlap_integrates_variable_frustum_area():
    # sqrt(area) is linear: integral of (1+x)^2 between .25 and .75.
    mesh=dict(faces=[0.,1.],areas=[1.,4.])
    assert overlap_weights(mesh,.5,.5).tolist()==[1.]
    with pytest.raises(ValueError):overlap_weights(mesh,2.,.1)


def test_header_edit_changes_only_geometry_dependent_inventory_and_surface():
    c=dict(ducts=[dict(id='exhaust',mesh=dict(faces=[0,.083/3,.166/3,.083,.2],
        centers=[.083/6,.083/2,5*.083/6,.15],volumes=[1,1,1,2]))],
        duct_species={'exhaust':[[.1,.2,.3,.4] for _ in range(4)]},
        geometry_identity={'chamber':{'sections':[{'length_mm':83.}]},'pipe_sections_mm':[[83.,37.5,37.5]]},
        thermal_system={'surfaces':[dict(id='h',area_m2=1.,heat_transfer_w_m2k=50.)]},
        thermal_locations={'h':'exhaust:0'})
    saved=deepcopy(c);b=variant_b(c);ratio=103/83
    assert c==saved
    assert b['ducts'][0]['mesh']['faces'][3]==pytest.approx(.103)
    assert b['ducts'][0]['mesh']['faces'][-1]==pytest.approx(.22)
    assert b['duct_species']['exhaust'][0][0]==pytest.approx(.1*ratio)
    assert b['thermal_system']['surfaces'][0]['area_m2']==pytest.approx(ratio)
    assert b['thermal_system']['surfaces'][0]['heat_transfer_w_m2k']==50.
