import numpy as np
import pytest
from scripts.diagnostics.outlet_front_control_v1 import exact,coverage,crossing,norms


def test_periodic_exact_translation_preserves_species_mass_at_wrapping():
    for n in (32,64,128):
        q,s=exact(n,.35,True,True)
        assert np.sum(s[:,0])/n==pytest.approx(.3,abs=1e-14)
        assert np.sum(q[:,0])/n==pytest.approx(1.05,abs=1e-14)
        assert np.max(np.abs(q[:,0]-s.sum(axis=1)))<1e-14


def test_outgoing_exact_species_mass_uses_only_remaining_physical_overlap():
    q,s=exact(64,.35,False,True)
    assert np.sum(s[:,0])/64==pytest.approx(.18,abs=1e-14)
    assert np.sum(q[:,0])/64==pytest.approx(1.03,abs=1e-14)


def test_norms_distinguish_local_peak_from_integral_error():
    r=norms([0.,0.,0.,1.],[0.,0.,0.,0.])
    assert r=={'L1':.25,'L2':.5,'Linf':1.}


def test_position_and_width_have_physical_coordinates():
    x=(np.arange(100)+.5)/100
    y=np.clip((x-.7)/.2,0,1)
    assert crossing(y,.5)==pytest.approx(.8)
    assert crossing(y,.9)-crossing(y,.1)==pytest.approx(.16)
