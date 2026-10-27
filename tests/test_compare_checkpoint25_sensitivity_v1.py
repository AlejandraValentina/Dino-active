import pytest
from scripts.diagnostics.compare_checkpoint25_sensitivity_v1 import norms


def test_physical_volume_weighting_differs_from_cell_count_weighting():
    n=norms([0.,1.],[3.,1.])
    assert n==dict(L1=.25,L2=.5,Linf=1.)


def test_constant_error_norms_are_mesh_partition_invariant():
    a=norms([.2,.2],[3.,1.]);b=norms([.2]*4,[1.,2.,.4,.6])
    assert a==pytest.approx(b)
