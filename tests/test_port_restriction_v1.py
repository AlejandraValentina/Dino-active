"""Independent thermodynamic references; no target engine power is specified."""
from decimal import Decimal, localcontext
import itertools
import math

import pytest

from motorsim.gas1d.eos import IdealGas, InvalidState
from motorsim.port_restriction_v1 import (
    QuiescentVolumeStateV1 as State, RestrictionGeometryV1 as Geometry,
    reservoir_restriction_v1 as exchange,
)

AIR = (1.0, 0.0, 0.0, 0.0)
BURNED = (0.0, 0.0, 0.0, 1.0)


def independent_mach_reference(p0, t0, pb, area, cd, eos):
    """80-digit EOS + Mach relations applied to actual float input pressures.

    Recovering Mach from quantized pressures avoids interpreting floating-point
    pressure rounding at M=0.001 as a discrepancy of the physical flux law.
    """
    with localcontext() as ctx:
        ctx.prec = 80
        g, gas_r, p, t, back = map(Decimal, (eos.gamma, eos.R, p0, t0, pb))
        if back == p:
            return 0.0
        mach_sq = 2 / (g - 1) * ((back / p) ** (-(g - 1) / g) - 1)
        mach_sq = min(mach_sq, Decimal(1))
        static_t = t / (1 + (g - 1) * mach_sq / 2)
        static_p = p * (static_t / t) ** (g / (g - 1))
        rho = static_p / (gas_r * static_t)
        velocity = (mach_sq * g * gas_r * static_t).sqrt()
        return float(Decimal(area) * Decimal(cd) * rho * velocity)


CASES = list(itertools.product((1.2, 1.35, 1.4), (1e5, 2e5, 5e5),
             (300.0, 900.0), (1e-6, 1e-4), (0.0, 0.5, 0.8, 1.0),
             (0.0, 0.001, 0.01, 0.1, 0.3, 0.8, 1.0)))


@pytest.mark.parametrize("gamma,p0,t0,area,cd,mach", CASES)
def test_mass_against_independent_mach_eos_reference(gamma, p0, t0, area, cd, mach):
    eos = IdealGas(gamma=gamma)
    pb = p0 / (1 + (gamma - 1) * mach * mach / 2) ** (gamma / (gamma - 1))
    result = exchange(State(p0, t0, AIR), State(pb, 500.0, BURNED), Geometry(area, cd, .3), eos=eos)
    expected = independent_mach_reference(p0, t0, pb, area, cd, eos)
    if expected == 0:
        assert result.mass_rate_kg_s == result.energy_rate_w == 0
    else:
        assert result.mass_rate_kg_s == pytest.approx(expected, rel=1e-10, abs=0)
        assert result.energy_rate_w == pytest.approx(expected * eos.cp * t0, rel=1e-10, abs=0)
        assert result.throat_mach <= 1.0 + 1e-14


@pytest.mark.parametrize("backpressure", (1.0, 1e3, 2e4, 5e4))
def test_choking_plateau_and_donor_enthalpy(backpressure):
    a = exchange(State(2e5, 900., BURNED), State(backpressure, 300., AIR), Geometry(1e-4, .8, .4))
    b = exchange(State(2e5, 900., BURNED), State(1., 200., AIR), Geometry(1e-4, .8, .4))
    assert a.mass_rate_kg_s == b.mass_rate_kg_s
    assert a.throat_mach == 1
    assert a.species_rates_kg_s == (0., 0., 0., a.mass_rate_kg_s)
    assert a.energy_rate_w / a.mass_rate_kg_s == IdealGas().cp * 900.


def test_forward_reverse_with_actual_donor_temperature_and_directional_cd():
    a, b = State(2e5, 900., BURNED), State(1e5, 300., AIR)
    f = exchange(a, b, Geometry(1e-4, .8, .4))
    r = exchange(b, a, Geometry(1e-4, .4, .8))
    assert r.mass_rate_kg_s == -f.mass_rate_kg_s
    assert r.energy_rate_w == -f.energy_rate_w
    assert r.species_rates_kg_s == tuple(-x for x in f.species_rates_kg_s)
    assert (f.donor, r.donor) == ("left", "right")


def test_dimensions_and_similarity_scalings():
    eos = IdealGas()
    def flux(area=1e-4, cd=.8, pressure=2e5, temperature=300.):
        return exchange(State(pressure, temperature, AIR), State(pressure/2, 450., BURNED),
                        Geometry(area, cd, cd), eos=eos).mass_rate_kg_s
    base = flux()
    assert flux(area=2e-4) == pytest.approx(2*base, rel=1e-12)
    assert flux(cd=.4) == pytest.approx(.5*base, rel=1e-12)
    assert flux(pressure=4e5) == pytest.approx(2*base, rel=1e-12)
    assert flux(temperature=1200.) == pytest.approx(.5*base, rel=1e-12)


def test_equilibrium_has_no_heat_or_species_diffusion_between_quiescent_volumes():
    x = exchange(State(1e5, 300., AIR), State(1e5, 900., BURNED), Geometry(1e-4, 1., 1.))
    assert x.branch == "EQUILIBRIUM"
    assert x.mass_rate_kg_s == x.energy_rate_w == 0
    assert x.species_rates_kg_s == (0.,)*4


@pytest.mark.parametrize("steps", (1, 2, 16, 1024))
def test_near_equilibrium_has_no_deadband(steps):
    p0 = 1e5
    pb = p0 - steps * math.ulp(p0)
    eos = IdealGas()
    x = exchange(State(p0, 300., AIR), State(pb, 300., AIR), Geometry(1e-4, 1., 1.))
    ref = independent_mach_reference(p0, 300., pb, 1e-4, 1., eos)
    assert x.mass_rate_kg_s > 0
    assert x.mass_rate_kg_s == pytest.approx(ref, rel=1e-10, abs=0)


@pytest.mark.parametrize("bad", (float('nan'), float('inf'), -1., 0., True))
def test_rejects_invalid_reservoir_state(bad):
    with pytest.raises(InvalidState):
        exchange(State(bad, 300., AIR), State(1e5, 300., AIR), Geometry(1e-4, 1., 1.))


@pytest.mark.parametrize("geometry", (Geometry(-1., 1., 1.), Geometry(1e-4, 1.1, 1.),
                         Geometry(1e-4, 1., -1.), Geometry(1e-4, True, 1.)))
def test_rejects_invalid_geometry_or_cd(geometry):
    with pytest.raises(InvalidState):
        exchange(State(2e5, 300., AIR), State(1e5, 300., AIR), geometry)


def test_zero_geometric_area_is_closed_and_does_not_mutate_inputs():
    left, right = State(2e5, 900., BURNED), State(1e5, 300., AIR)
    before = (left, right)
    x = exchange(left, right, Geometry(0., 1., 1.))
    assert x.mass_rate_kg_s == x.energy_rate_w == 0
    assert x.branch == "CLOSED"
    assert before == (left, right)
