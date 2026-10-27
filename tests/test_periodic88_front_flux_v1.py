import numpy as np
from scripts.diagnostics.periodic88_front_flux_v1 import accumulate,empty_totals,balance_rows,front_delta


def test_signed_stage_flux_reversal_does_not_cancel_gross_transport():
    t=empty_totals(['exhaust'])
    for sign in (1.,-1.):
        f=dict(all_faces=[[sign,0.,sign*300.]]*2,all_species_faces=[[sign*.7,sign*.1,0.,sign*.2]]*2)
        accumulate(t,{'exhaust':f},.5)
    right=t['exhaust']['right']
    np.testing.assert_array_equal(right['gas_net'],[0.,0.,0.])
    assert right['gas_positive'][0]==.5 and right['gas_negative'][0]==-.5
    np.testing.assert_allclose(right['species_positive'],[.35,.05,0.,.1])


def test_energy_uses_work_on_gas_and_subtracts_wall_heat():
    a={'cylinder':dict(mass_kg=1.,energy_J=100.,species_kg=np.array([1.,0.,0.,0.]))}
    b={'cylinder':dict(mass_kg=1.,energy_J=107.,species_kg=np.array([.8,0.,0.,.2]))}
    chemical=dict(heat=10.,species=np.array([-.2,0.,0.,.2]));p7=dict(heat=0.,species=np.zeros(4))
    r=balance_rows(a,b,empty_totals(['exhaust']),[],{'cylinder':-2.},{'cylinder':1.},chemical,p7)
    np.testing.assert_allclose(r['cylinder']['residual'],0.,atol=1e-15)
    assert r['cylinder']['source'][1]==7.


def test_species_normalization_uses_subsystem_mass_not_near_zero_marker():
    a={'exhaust':dict(mass_kg=1.,energy_J=1.,species_kg=np.array([1.,0.,0.,0.]))}
    b={'exhaust':dict(mass_kg=1.,energy_J=1.,species_kg=np.array([1.,0.,1e-18,0.]))}
    r=balance_rows(a,b,empty_totals(['exhaust']),[],{},{},dict(heat=0.,species=np.zeros(4)),dict(heat=0.,species=np.zeros(4)))
    assert r['exhaust']['normalized_residual'][4]==1e-18


def test_equal_pressure_translated_contact_localizes_without_acoustic_change():
    def state(y):
        return dict(ducts={'exhaust':[[1.,0.,10.]]*3},species={'ducts':{'exhaust':[[v,0.,0.,1-v] for v in y]}})
    r=front_delta(state([1.,0.,0.]),state([1.,1.,0.]),[.1,.2,.3],[1.,1.,1.],1.4)
    assert r['pressure_relative_L1']==0.
    assert r['species']['burned']['max_x_m']==.2
    assert r['species']['burned']['discrepancy_width_std_m']==0.
    assert r['species']['burned']['fraction_deltaY_weight_with_abs_dp_over_p_below_1e3']==1.
