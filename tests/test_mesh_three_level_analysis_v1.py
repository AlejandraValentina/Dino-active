import math
import pytest

from scripts.diagnostics.compare_mesh_three_levels_v1 import scalar_trend


@pytest.mark.parametrize('order',[.5,1.,2.,3.])
@pytest.mark.parametrize('sign',[-1.,1.])
def test_known_power_error_recovers_conditional_order_and_limit(order,sign):
    v=[10.+sign*h**order for h in (1.,.5,.25)]
    r=scalar_trend(*v)
    assert r['classification']=='MONOTONIC_DECREASING'
    assert r['fitted_order']==pytest.approx(order,rel=1e-12)
    assert r['conditional_extrapolation']==pytest.approx(10.,rel=1e-12)
    assert r['certified_uncertainty'] is None


@pytest.mark.parametrize('values,status',[
    ((1.,2.,4.),'MONOTONIC_NONDECREASING'),
    ((1.,2.,3.),'MONOTONIC_NONDECREASING'),
    ((1.,2.,1.5),'OSCILLATORY_DECREASING'),
    ((1.,2.,0.),'OSCILLATORY_NONDECREASING'),
    ((1.,1.,1.),'RESOLUTION_LIMITED_OR_UNRESOLVED'),
    ((1.,2.,2.),'RESOLUTION_LIMITED_OR_UNRESOLVED')])
def test_refuses_to_extrapolate_unjustified_sequences(values,status):
    r=scalar_trend(*values)
    assert r['classification']==status
    assert r['fitted_order'] is r['conditional_extrapolation'] is None


@pytest.mark.parametrize('invalid',[math.nan,math.inf,True,None])
def test_nonphysical_scalars_rejected(invalid):
    with pytest.raises(ValueError):scalar_trend(1.,2.,invalid)
