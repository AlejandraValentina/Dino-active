import numpy as np
import pytest
from scripts.diagnostics.periodic88_material_reference_v1 import bounded_slopes,average


def test_linear_mass_reconstruction_preserves_means_and_species_closure():
    edges=np.array([0.,.2,.7,1.1,2.]);means=np.array([[.1,.01,0.,.89],[.2,.02,0.,.78],[.7,.07,0.,.23],[.8,.08,0.,.12]])
    slopes=bounded_slopes(edges,means);mid=.5*(edges[:-1]+edges[1:])
    for i in range(len(means)):
        np.testing.assert_allclose(average(edges,means,slopes,edges[i],edges[i+1]),means[i],atol=1e-15)
        for face in (edges[i],edges[i+1]):
            value=means[i]+slopes[i]*(face-mid[i]);assert min(value)>=-1e-15 and max(value)<=1+1e-15
            assert sum(value)==pytest.approx(1.,abs=1e-15)


def test_exact_linear_average_on_arbitrary_material_interval():
    edges=np.arange(5.);mid=.5*(edges[:-1]+edges[1:]);means=np.c_[.1*mid,np.zeros(4),np.zeros(4),1-.1*mid]
    slopes=bounded_slopes(edges,means)
    answer=average(edges,means,slopes,1.2,2.7)
    np.testing.assert_allclose(answer,[.195,0.,0.,.805],atol=1e-15)


def test_pure_markers_and_constant_marker_cannot_overshoot():
    edges=np.arange(6.);means=np.array([[1.,0.,0.,0.],[1.,0.,0.,0.],[0.,0.,0.,1.],[0.,0.,0.,1.],[0.,0.,0.,1.]])
    np.testing.assert_array_equal(bounded_slopes(edges,means),0.)
    with pytest.raises(ValueError,match='outside'):average(edges,means,np.zeros_like(means),-.1,1.)
