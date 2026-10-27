import numpy as np
import pytest
from scripts.diagnostics.material_species_diagnostic_v1 import exact_norms,profile,cell_average_norms


def test_material_comparison_is_exact_for_same_plug_with_subdivided_cells():
    a=(np.array([0.,1.,2.]),np.array([[1.,0,0,0],[0,0,0,1.]]))
    b=(np.array([0.,.25,1.,1.25,2.]),np.array([[1.,0,0,0],[1.,0,0,0],[0,0,0,1.],[0,0,0,1.]]))
    assert all(m['L1']==0 for m in exact_norms(a,b,.1,1.9).values())
    shifted=(b[0]+.5,b[1])
    assert exact_norms(a,shifted,.5,2.)['burned']['L1']==pytest.approx(1/3)


def test_compression_changes_positions_but_not_mass_labels():
    c={'ducts':[{'id':'exhaust','mesh':{'volumes':[1.,1.]}}]}
    a={'ducts':{'exhaust':[[1,0,10,1],[1,0,10,1]]},'species':{'ducts':{'exhaust':[[1,0,0,0],[0,0,0,1]]}}}
    b={'ducts':a['ducts'],'species':a['species']}
    compressed={'ducts':[{'id':'exhaust','mesh':{'volumes':[.5,.5]}}]}
    b={'ducts':{'exhaust':[[2,0,20,2],[2,0,20,2]]},'species':a['species']}
    assert exact_norms(profile(a,c),profile(b,compressed),0.,2.)['burned']['L1']==0
    with pytest.raises(ValueError):exact_norms(profile(a,c),profile(b,compressed),-1.,2.)


def test_exact_cell_average_does_not_require_pointwise_discontinuity_agreement():
    initial=(np.array([0.,1.,2.]),np.array([[1.,0,0,0],[0,0,0,1.]]))
    averaged=(np.array([.5,1.5]),np.array([[.5,0,0,.5]]))
    assert exact_norms(initial,averaged,.5,1.5)['burned']['L1']==.5
    assert cell_average_norms(averaged,initial,.5,1.5)['norms']['burned']['L1']==0
