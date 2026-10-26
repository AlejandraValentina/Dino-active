from math import sqrt

import pytest

from motorsim.coupling import ChamberState
from motorsim.gas1d.eos import IdealGas
from motorsim.gas1d.exact_riemann_reference_v1 import exact_riemann_v1, VacuumRiemannError
from motorsim.port_connection_v2 import (port_connection_v2, normal_shock,
    nozzle_state, nozzle_mach_roots, area_mach, total_state, NoAdmissiblePortState)


def chamber(p, t, e):
    rho = p/(e.R*t)
    return ChamberState(rho, p/(e.gamma-1), .8*rho, 1.)


def test_exact_sod_reference():
    e = IdealGas(gamma=1.4)
    r = exact_riemann_v1((1.,0.,1.,1.), (.125,0.,.1,0.), eos=e)
    assert r.pressure == pytest.approx(.303130178050647, rel=1e-12)
    assert r.velocity == pytest.approx(.92745262004895, rel=1e-12)
    assert r.sample()[0] == pytest.approx(.4263194281785, rel=1e-11)
    assert r.sample()[3] == 1.
    assert r.sample(-10) == r.left
    assert r.sample(10) == r.right
    # Fan invariant: u+2a/(gamma-1) on the left rarefaction.
    w = r.sample(-.5)
    assert w[1]+2*e.sound_speed(w)/(e.gamma-1) == pytest.approx(
        2*e.sound_speed(r.left)/(e.gamma-1), rel=1e-12)
    assert w[2]/w[0]**e.gamma == pytest.approx(1., rel=1e-12)


def test_exact_contact_symmetry_and_vacuum():
    e = IdealGas(gamma=1.4)
    left, right = (1.,.3,1.,1.), (.2,.3,1.,0.)
    r = exact_riemann_v1(left, right, eos=e)
    assert r.pressure == pytest.approx(1.)
    assert r.sample() == left
    assert r.sample(.5) == right
    reverse = exact_riemann_v1((right[0],-.3,1.,0.), (1.,-.3,1.,1.), eos=e)
    assert reverse.velocity == pytest.approx(-r.velocity)
    assert reverse.pressure == pytest.approx(r.pressure)
    with pytest.raises(VacuumRiemannError):
        exact_riemann_v1((1.,-10.,1.,0.), (1.,10.,1.,0.), eos=e)


@pytest.mark.parametrize('gamma', [1.2,1.35,1.4])
@pytest.mark.parametrize('mach', [1.,1.01,1.5,2.,4.])
def test_independent_normal_shock_rankine_hugoniot(gamma,mach):
    e = IdealGas(gamma=gamma)
    up = (1.2,mach*sqrt(gamma*1e5/1.2),1e5,.7)
    down = normal_shock(up,e)
    assert e.flux(down) == pytest.approx(e.flux(up),rel=1e-12)
    assert down[2]/down[0]**gamma >= up[2]/up[0]**gamma*(1-1e-14)
    r = exact_riemann_v1(up,down,eos=e)
    assert r.pressure == pytest.approx(down[2],rel=1e-12)
    assert r.left_speeds == pytest.approx((0.,0.),abs=1e-10)


@pytest.mark.parametrize('gamma', [1.2,1.35,1.4])
@pytest.mark.parametrize('ratio', [.01,.1,.5,1.])
@pytest.mark.parametrize('temperature', [300.,900.])
@pytest.mark.parametrize('normal', [-1,1])
@pytest.mark.parametrize('regime', ['sub','sup','shock'])
def test_manufactured_nozzle_all_regimes(gamma,ratio,temperature,normal,regime):
    e = IdealGas(gamma=gamma)
    p0, ap = 5e5,1e-4
    sub,sup = nozzle_mach_roots(1/ratio,gamma)
    mach = .6*sub if regime=='sub' else sup
    outward = nozzle_state(p0,temperature,mach,.8,e)
    if regime=='shock':
        outward = normal_shock(outward,e)
    r,w,p,y = outward
    interior = (r,normal*w,p,y)
    x = port_connection_v2(chamber(p0,temperature,e),interior,ratio*ap,ap,normal,eos=e)
    assert x.flux_x == pytest.approx(tuple(ap*f for f in e.flux(interior)),rel=1e-9)
    assert total_state(x.boundary_state,e)[1] == pytest.approx(temperature,rel=1e-11)
    assert x.boundary_total_pressure_pa <= p0*(1+1e-11)
    assert x.outward[0] < 0
    assert x.outward[2]/x.outward[0] == pytest.approx(e.cp*temperature,rel=1e-12)
    if x.causality_rightmost_speed_m_s is not None:
        assert x.causality_rightmost_speed_m_s <= 1e-7
    if x.shock_area_ratio is not None:
        assert 1-1e-10 <= x.shock_area_ratio <= 1/ratio*(1+1e-10)


@pytest.mark.parametrize('normal', [-1,1])
def test_old_minimum_counterexample_has_causal_supersonic_exit(normal):
    e = IdealGas()
    rho = 1e5/(e.R*300)
    w = -.8*sqrt(e.gamma*e.R*300)
    x = port_connection_v2(chamber(5e5,300,e),(rho,normal*w,1e5,.6),5e-5,1e-4,normal,eos=e)
    assert x.branch == 'INFLOW_CHOKED_SUPERSONIC'
    assert abs(x.boundary_state[1])/e.sound_speed(x.boundary_state) == pytest.approx(2.16082960721432)
    assert x.causality_rightmost_speed_m_s == pytest.approx(-150.40047187867,rel=1e-10)
    assert x.outward[0] == pytest.approx(-.05760738925094381,rel=1e-12)
    assert x.acoustic_velocity_residual_m_s is None


def test_closed_wall_reflects_dynamic_pressure_and_vacuum_is_explicit():
    e = IdealGas()
    c = chamber(1e5,300,e)
    x = port_connection_v2(c,(1.2,100.,1e5,.4),0.,1e-4,1,eos=e)
    assert x.outward[0] == x.outward[2] == x.outward[3] == 0
    assert x.boundary_state[2] > 1e5
    assert x.acoustic_velocity_residual_m_s == pytest.approx(0.,abs=1e-12)
    with pytest.raises(NoAdmissiblePortState,match='vacuum'):
        port_connection_v2(c,(1.,-10000.,1e5,.4),0.,1e-4,1,eos=e)


@pytest.mark.parametrize('mach', [1.1,1.5,2.,4.])
@pytest.mark.parametrize('ratio', [.01,.1,.5,1.])
def test_supersonic_outflow_transmission_or_causal_unstart(mach,ratio):
    e = IdealGas()
    state = (1.2,mach*sqrt(e.gamma*1e5/1.2),1e5,.4)
    x = port_connection_v2(chamber(1e4,300,e),state,ratio*1e-4,1e-4,1,eos=e)
    assert x.outward[0] > 0
    if x.branch == 'OUTFLOW_SUPERSONIC_TRANSMITTED':
        assert x.flux_x == pytest.approx(tuple(1e-4*f for f in e.flux(state)),rel=1e-12)
    else:
        assert 'UNSTART_SHOCK' in x.branch
        rp = exact_riemann_v1(state,x.boundary_state,eos=e)
        assert max(rp.left_speeds) <= 1e-7


@pytest.mark.parametrize('gamma', [1.2,1.35,1.4])
@pytest.mark.parametrize('ratio', [.01,.1,.5,.99])
def test_internal_shock_location_from_independent_station_construction(gamma,ratio):
    e = IdealGas(gamma=gamma)
    ap, at, pc, tc = 1e-4, ratio*1e-4, 5e5, 900.
    _, msup = nozzle_mach_roots(1/ratio,gamma)
    mshock = 1+.4*(msup-1)
    ashock = at*area_mach(mshock,gamma)
    shock_up = nozzle_state(pc,tc,mshock,.8,e)
    shock_down = normal_shock(shock_up,e)
    p0down,t0down = total_state(shock_down,e)
    mdown = -shock_down[1]/e.sound_speed(shock_down)
    astar_down = ashock/area_mach(mdown,gamma)
    mexit,_ = nozzle_mach_roots(ap/astar_down,gamma)
    pipe = nozzle_state(p0down,t0down,mexit,.8,e)
    x = port_connection_v2(chamber(pc,tc,e),pipe,at,ap,1,eos=e)
    assert x.branch == 'INFLOW_CHOKED_INTERNAL_SHOCK'
    assert x.shock_area_ratio == pytest.approx(ashock/at,rel=1e-9)
    assert x.flux_x == pytest.approx(tuple(ap*f for f in e.flux(pipe)),rel=1e-9)


@pytest.mark.parametrize('gamma', [1.2,1.35,1.4])
@pytest.mark.parametrize('ratio', [.01,.1,.5,1.])
@pytest.mark.parametrize('transition', ['choking','exit_shock'])
def test_flux_continuity_at_regime_changes(gamma,ratio,transition):
    e = IdealGas(gamma=gamma)
    msub,msup = nozzle_mach_roots(1/ratio,gamma)
    base = nozzle_state(5e5,300,msub if transition=='choking' else msup,.8,e)
    if transition=='exit_shock':
        base = normal_shock(base,e)
    expected = tuple(1e-4*f for f in e.flux(base))
    if transition == 'choking':
        # Matched neighboring solutions, not arbitrary pressure perturbations:
        # at low exit Mach the inverse acoustic mass-flow sensitivity grows
        # like 1/M. The subcritical state approaches the sonic-throat solution.
        for epsilon in [1e-8,1e-10,0.]:
            state = nozzle_state(5e5,300,msub*(1-epsilon),.8,e)
            x = port_connection_v2(chamber(5e5,300,e),state,ratio*1e-4,1e-4,1,eos=e)
            assert x.flux_x == pytest.approx(expected,rel=1e-6)
        return
    for perturbation in [-1e-8,0.,1e-8]:
        rho,u,p,y = base
        state = (rho*(1+perturbation),u,p*(1+perturbation),y)
        x = port_connection_v2(chamber(5e5,300,e),state,ratio*1e-4,1e-4,1,eos=e)
        assert x.flux_x == pytest.approx(expected,rel=1e-6)


@pytest.mark.parametrize('velocity', [-100.,0.,100.,600.])
def test_aperture_limit_is_dynamic_reflecting_wall(velocity):
    e = IdealGas()
    c = chamber(3e5,600,e)
    state = (1.2,velocity,1e5,.2)
    wall = port_connection_v2(c,state,0.,1e-4,1,eos=e)
    near = port_connection_v2(c,state,1e-12,1e-4,1,eos=e)
    assert abs(near.outward[0]) < 1e-8
    assert near.outward[1] == pytest.approx(wall.outward[1],rel=1e-6)


def test_equilibrium_has_no_flow_and_full_area_limit_is_continuous():
    e = IdealGas()
    c = chamber(5e5,300,e)
    state = (1.2,0.,5e5,.2)
    x = port_connection_v2(c,state,1e-5,1e-4,1,eos=e)
    assert x.outward[0] == x.outward[2] == x.outward[3] == 0.
    state = nozzle_state(5e5,300,.3,.8,e)
    a = port_connection_v2(c,state,1e-4,1e-4,1,eos=e)
    b = port_connection_v2(c,state,(1-1e-8)*1e-4,1e-4,1,eos=e)
    assert a.flux_x == pytest.approx(b.flux_x,rel=1e-6)
