import pytest
import numpy as np
from scripts.diagnostics import analyze_preopen_wave_transport_v1 as module


def test_phase_mismatch_rejected_before_projection():
    with pytest.raises(ValueError,match='phase differs'):module.matched_phases([{'angle':0.}],[{'angle':1.}],{},{},{})


def test_phase_count_mismatch_rejected_before_projection():
    with pytest.raises(ValueError,match='count'):module.matched_phases([], [{'angle':1.}],{},{},{})


def test_pressure_average_excludes_unresolved_subcell_kinetic_energy():
    source={'eos':{'gamma':1.4},'ducts':[{'id':'exhaust','mesh':{'faces':[0.,.5,1.],'volumes':[.5,.5]}}]}
    target={'ducts':[{'id':'exhaust','mesh':{'faces':[0.,1.],'volumes':[1.]}}]}
    state={'ducts':{'exhaust':[[1.,1.,3.,1.],[1.,-1.,3.,1.]]}}
    mean,bias=module.pressure_averages(state,source,target)['exhaust']
    np.testing.assert_allclose(mean,[1.],atol=1e-15);np.testing.assert_allclose(bias,[.2],atol=1e-15)


def test_common_material_bins_do_not_interpret_roundoff_contact_shift_as_large_state_change():
    a=(np.array([0.,1.,2.]),np.array([[1.,0.,0.,0.],[0.,0.,0.,1.]]))
    b=(np.array([0.,1.+1e-14,2.]),a[1].copy())
    r=module.common_material_bins(a,b,a[0],0.,2.)
    assert r['norms']['burned']['Linf']<1e-13
    assert r['covered_interval_kg']==[0.,2.]


def test_common_material_bins_integrate_all_mass_without_dropping_contact():
    a=(np.array([0.,1.,2.]),np.array([[1.,0.,0.,0.],[0.,0.,0.,1.]]))
    b=(np.array([0.,1.2,2.]),a[1].copy())
    r=module.common_material_bins(a,b,a[0],0.,2.)
    assert r['norms']['burned']['L1']==pytest.approx(.1)
    assert r['norms']['burned']['Linf']==pytest.approx(.2)


def test_plot_is_standalone_png_and_preserves_existing_output(tmp_path):
    from pathlib import Path
    from scripts.diagnostics.plot_preopen_wave_transport_v1 import plot
    root=Path(__file__).resolve().parents[1]/'results/predictive-reliability-v1';output=tmp_path/'diagnostic.png'
    plot(root,output)
    assert output.read_bytes().startswith(b'\x89PNG\r\n\x1a\n')
    with pytest.raises(FileExistsError):plot(root,output)
