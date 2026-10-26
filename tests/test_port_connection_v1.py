"""Manufactured physical states and conservation checks for the new candidate."""
import itertools
import math

import pytest

from motorsim.coupling import ChamberState, interface_flux
from motorsim.gas1d.eos import IdealGas
from motorsim.port_connection_v1 import port_connection_v1, PortDomainError


def chamber(p, t, eos):
    rho = p/(eos.R*t)
    return ChamberState(rho, p/(eos.gamma-1), rho*.8, 1.)


@pytest.mark.parametrize("mach,gamma,normal", itertools.product(
    (.001,.01,.1,.3,.8), (1.2,1.35,1.4), (-1,1)))
def test_full_area_inflow_is_consistent_with_isentropic_nozzle(mach, gamma, normal):
    eos = IdealGas(gamma=gamma)
    p0, t0, ap = 2e5, 900., 1e-4
    k = 1+(gamma-1)*mach*mach/2
    p, t = p0/k**(gamma/(gamma-1)), t0/k
    rho, v = p/(eos.R*t), mach*math.sqrt(gamma*eos.R*t)
    state = (rho, -normal*v, p, .8)
    x = port_connection_v1(chamber(p0,t0,eos), state, ap, ap, normal, eos=eos)
    expected = tuple(ap*q for q in eos.flux(state))
    for a,b in zip(x.flux_x,expected):
        assert a == pytest.approx(b, rel=1e-8, abs=0)
    assert abs(x.acoustic_velocity_residual_m_s) < 1e-8
    old = interface_flux(chamber(p0,t0,eos), state, ap, normal, eos=eos)
    if mach <= .1:
        assert abs(old.flux_x[0]/expected[0]) < .51


def manufactured_inflow(eos, area_ratio, mt, normal=1):
    """Solve the expansion momentum equation by bisection, not the code quadratic."""
    pc, tc, ap = 2e5, 900., 1e-4
    tt = tc/(1+(eos.gamma-1)*mt*mt/2)
    pt = pc*(tt/tc)**(eos.gamma/(eos.gamma-1))
    vt = mt*math.sqrt(eos.gamma*eos.R*tt)
    q = area_ratio*ap*pt/(eos.R*tt)*vt
    lo, hi = 0., vt
    # pb = q*R*Tb/(Ap*vb); balance pb*Ap+q*vb = pt*Ap+q*vt.
    for _ in range(100):
        v = (lo+hi)/2
        tb = tc-v*v/(2*eos.cp)
        pb = q*eos.R*tb/(ap*v)
        residual = ap*pb+q*v-ap*pt-q*vt
        if residual > 0: lo=v
        else: hi=v
    v=(lo+hi)/2
    tb=tc-v*v/(2*eos.cp)
    pb=q*eos.R*tb/(ap*v)
    return chamber(pc,tc,eos), (pb/(eos.R*tb), -normal*v, pb, .8), ap, q, pt


@pytest.mark.parametrize("ratio,mt,gamma", itertools.product(
    (.01,.1,.5,1.), (.001,.1,.5,.99), (1.2,1.35,1.4)))
def test_restricted_inflow_conserves_throat_and_duct_fluxes(ratio, mt, gamma):
    eos=IdealGas(gamma=gamma)
    c,w,ap,q,pt=manufactured_inflow(eos,ratio,mt)
    x=port_connection_v1(c,w,ratio*ap,ap,1,eos=eos)
    assert -x.flux_x[0] == pytest.approx(q,rel=1e-9)
    assert x.throat_mach == pytest.approx(mt,rel=1e-8)
    assert x.throat_pressure_pa == pytest.approx(pt,rel=1e-9)
    assert x.flux_x[2]/x.flux_x[0] == pytest.approx(eos.cp*900.,rel=1e-12)
    assert x.boundary_total_pressure_pa <= 2e5*(1+1e-10)
    assert abs(x.acoustic_velocity_residual_m_s)<1e-7


@pytest.mark.parametrize("ratio,mt,gamma", itertools.product(
    (.01,.1,.5,1.), (.1,.5,1.), (1.2,1.35,1.4)))
def test_outflow_throat_pipe_mass_and_total_energy(ratio,mt,gamma):
    eos=IdealGas(gamma=gamma)
    p0,t0,ap=2e5,300.,1e-4
    def flux(m):
        t=t0/(1+(gamma-1)*m*m/2)
        p=p0*(t/t0)**(gamma/(gamma-1))
        return p/(eos.R*t)*m*math.sqrt(gamma*eos.R*t)
    q=ratio*ap*flux(mt)
    lo,hi=0.,1.
    for _ in range(100):
        mid=(lo+hi)/2
        if ap*flux(mid)>q:hi=mid
        else:lo=mid
    mb=(lo+hi)/2
    if mb >= 1-1e-12:
        pytest.skip('sonic interior outside the candidate subsonic-interior domain')
    tb=t0/(1+(gamma-1)*mb*mb/2)
    pb=p0*(tb/t0)**(gamma/(gamma-1))
    pc=p0/(1+(gamma-1)*mt*mt/2)**(gamma/(gamma-1))
    if mt==1:pc*=.5
    w=(pb/(eos.R*tb),mb*math.sqrt(gamma*eos.R*tb),pb,.6)
    x=port_connection_v1(chamber(pc,900.,eos),w,ratio*ap,ap,1,eos=eos)
    assert x.flux_x[0]==pytest.approx(q,rel=1e-9)
    assert x.flux_x[2]/x.flux_x[0]==pytest.approx(eos.cp*t0,rel=1e-9)
    assert x.throat_mach==pytest.approx(mt,rel=1e-8)


def test_normal_reversal_retains_momentum_and_reverses_mass_energy():
    e=IdealGas();c,w,ap,_,_=manufactured_inflow(e,.5,.5)
    a=port_connection_v1(c,w,.5*ap,ap,1,eos=e)
    b=port_connection_v1(c,(w[0],-w[1],w[2],w[3]),.5*ap,ap,-1,eos=e)
    assert b.flux_x == (-a.flux_x[0],a.flux_x[1],-a.flux_x[2],-a.flux_x[3])
    assert a.outward[0]==b.outward[0]


def test_equilibrium_and_closed_area_have_exact_zero_exchange():
    e=IdealGas();c=chamber(1e5,900.,e);w=(1e5/(e.R*300.),0.,1e5,.3)
    for area in (0.,1e-4):
        x=port_connection_v1(c,w,area,1e-4,1,eos=e)
        assert x.flux_x==(0.,10.,0.,0.)


@pytest.mark.parametrize('ratio',(.01,.1,.5,1.))
def test_subsonic_to_sonic_throat_has_continuous_mass_flux(ratio):
    e=IdealGas();results=[]
    for mt in (.9999999,1.):
        c,w,ap,q,_=manufactured_inflow(e,ratio,mt)
        if ratio==1 and mt==1:continue
        x=port_connection_v1(c,w,ratio*ap,ap,1,eos=e)
        assert abs(x.flux_x[0])==pytest.approx(q,rel=1e-9)
        results.append(x)
    if len(results)==2:
        assert results[0].flux_x[0]==pytest.approx(results[1].flux_x[0],rel=1e-6)


def test_unsupported_supersonic_interior_is_explicit_not_silent_fallback():
    e=IdealGas();w=(1.,1000.,1e5,1.)
    with pytest.raises(PortDomainError,match='subsonic'):
        port_connection_v1(chamber(2e5,300.,e),w,1e-5,1e-4,1,eos=e)


def test_valid_subsonic_interior_exposes_missing_transonic_boundary_regime():
    # This passing negative test is NOT an adoption pass: the domain receipt
    # counts this physically admissible input as an unsupported engine case.
    e=IdealGas(gamma=1.35)
    rho=1e5/(e.R*300.)
    u=-.8*math.sqrt(e.gamma*e.R*300.)
    with pytest.raises(PortDomainError,match='supersonic duct face'):
        port_connection_v1(chamber(5e5,300.,e),(rho,u,1e5,.6),5e-5,1e-4,1,eos=e)
