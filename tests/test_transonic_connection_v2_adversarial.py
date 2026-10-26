import itertools
import math

import pytest

from motorsim.coupling import ChamberState
from motorsim.gas1d.eos import IdealGas, InvalidState
from motorsim.gas1d.exact_riemann_reference_v1 import exact_riemann_v1
from motorsim.port_connection_v2 import port_connection_v2


@pytest.mark.parametrize('gamma,pr,ar,mi',itertools.product(
    [1.2,1.35,1.4],[.1,1.,10.],[.01,.5,1.],[-3.,-1.1,1.1,3.]))
def test_supersonic_input_sweep_causality_entropy_and_orientation(gamma,pr,ar,mi):
    e = IdealGas(gamma=gamma)
    c = ChamberState(pr*1e5/(e.R*600),pr*1e5/(gamma-1),0.,1.)
    rho = 1e5/(e.R*300)
    state = (rho,mi*math.sqrt(gamma*e.R*300),1e5,.4)
    x = port_connection_v2(c,state,ar*1e-4,1e-4,1,eos=e)
    r = port_connection_v2(c,(rho,-state[1],1e5,.4),ar*1e-4,1e-4,-1,eos=e)
    assert x.outward[0] == pytest.approx(r.outward[0],rel=1e-11)
    assert x.outward[2] == pytest.approx(r.outward[2],rel=1e-11)
    assert x.flux_x[1] == pytest.approx(r.flux_x[1],rel=1e-11)
    if x.outward[0] < 0:
        assert x.boundary_total_pressure_pa <= pr*1e5*(1+1e-10)
        assert x.outward[2]/x.outward[0] == pytest.approx(e.cp*600,rel=1e-11)
    if x.branch == 'INFLOW_CHOKED_SUPERSONIC':
        wave = exact_riemann_v1(state,x.boundary_state,eos=e)
        assert max(*wave.left_speeds,wave.velocity,*wave.right_speeds) < 1e-7
    if 'UNSTART' in x.branch:
        wave = exact_riemann_v1(state,x.boundary_state,eos=e)
        assert max(wave.left_speeds) < 1e-7


@pytest.mark.parametrize('area,pipe,normal',[
    (-1.,1.,1),(2.,1.,1),(1.,0.,1),(math.nan,1.,1),
    (1.,math.inf,1),(True,1.,1),(1.,1.,True),(1.,1.,0)])
def test_invalid_geometry_has_no_legacy_fallback(area,pipe,normal):
    c = ChamberState(1.,1e5/.35,0.,1.)
    with pytest.raises(InvalidState):
        port_connection_v2(c,(1.,0.,1e5,.4),area,pipe,normal)
