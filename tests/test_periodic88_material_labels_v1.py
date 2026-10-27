import numpy as np
import pytest
from scripts.diagnostics.periodic88_material_labels_v1 import retained_interval,matched_cell_comparison


def test_safe_interval_covers_both_boundary_reversals():
    assert retained_interval(10.,-2.,3.)==(2.,7.)
    # Arbitrary cumulative paths bounded by those gross discharges.
    for fleft,fright in ((0.,0.),(-2.,1.),(5.,3.),(4.,2.)):
        assert -fleft<=2. and 10.-fright>=7.


def test_rejects_absent_retained_material_and_wrong_sign():
    with pytest.raises(ValueError,match='retained'):retained_interval(1.,-.7,.5)
    with pytest.raises(ValueError,match='signed'):retained_interval(1.,.1,.2)


def test_exact_material_cell_average_under_translation_and_resampling():
    initial=(np.array([0.,1.,2.,3.]),np.array([[1.,0.,0.,0.],[0.,0.,0.,1.],[0.,0.,0.,1.]]))
    # Final cell crosses initial marker discontinuity in mass label.
    final=(np.array([-.5,.5,1.5,2.5]),np.array([[1.,0.,0.,0.],[.5,0.,0.,.5],[0.,0.,0.,1.]]))
    r=matched_cell_comparison(initial,final,.5,2.5)
    assert r['material_aligned_cell_means']['norms']['burned']['L1']==0.
    assert r['same_physical_cell_unaligned_marker_difference']['burned']['L1']==.25


def test_uniform_marker_unchanged_under_compression_of_mass_cells():
    marker=np.tile([.5,.1,.05,.35],(3,1));initial=(np.array([0.,1.,2.,3.]),marker)
    final=(np.array([.1,.8,1.9,2.9]),marker.copy())
    r=matched_cell_comparison(initial,final,.1,2.9)
    assert r['material_aligned_cell_means']['norms']['burned']['L1']<1e-15
