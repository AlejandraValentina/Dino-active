"""Dino 4T: thermochemistry, geometry, valves, closures (fast, L0)."""
import math

import numpy as np
import pytest

from motorsim.dino4t import verification as v
from motorsim.dino4t.closures import ChenFlynnFriction, WoschniHeatTransfer
from motorsim.dino4t.combustion import Wiebe, burned_composition, premixed_charge, products_change
from motorsim.dino4t.kinematics import SliderCrank
from motorsim.dino4t.thermo import Mixture, ThermoError, dry_air
from motorsim.dino4t.thermo_data import RECORDS, parse_nasa7
from motorsim.dino4t.valves import FlowCoefficients, HarmonicLift, TabulatedLift, Valve, wrap


@pytest.fixture(scope="module")
def mix():
    return Mixture.standard()


def test_records_parse_and_share_t_mid():
    for name, (_, _, text) in RECORDS.items():
        rec = parse_nasa7(text)
        assert rec["t_mid"] == 1000.0 and len(rec["low"]) == len(rec["high"]) == 7, name


@pytest.mark.parametrize("case", [v.thermo_reference, v.thermo_inversion, v.stoichiometry,
                                  v.geometry_checks, v.orifice_function, v.hllc_vs_gas1d])
def test_verification_case(case):
    result = case()
    assert result["passed"], result["metrics"]


def test_fit_seam_continuity(mix):
    """NASA fits are continuous at T_mid to a small fraction of cp*dT."""
    for i in range(mix.ns):
        y = np.eye(mix.ns)[i]
        jump = abs(float(mix.enthalpy(y, 1000.0 - 1e-9)) - float(mix.enthalpy(y, 1000.0)))
        assert jump < 1e-3 * float(mix.cp(y, 1000.0)), mix.names[i]


def test_temperature_out_of_range_raises(mix):
    air = dry_air(mix)
    with pytest.raises(ThermoError):
        mix.temperature_from_energy(air, float(mix.internal_energy(air, 50.0)) - 1e6)


@pytest.mark.parametrize("phi", [0.7, 1.0, 1.3])
def test_adiabatic_combustion_conserves_energy_and_heats(mix, phi):
    y = premixed_charge(mix, "IC8H18", phi)
    b = burned_composition(mix, "IC8H18", y)
    e = float(mix.internal_energy(y, 700.0))
    T = mix.temperature_from_energy(b, e)
    assert abs(float(mix.internal_energy(b, T)) - e) < 1e-6
    assert 2200.0 < T < 3400.0


def test_rich_products_contain_co_and_h2(mix):
    y = premixed_charge(mix, "IC8H18", 1.3)
    d = products_change(mix, "IC8H18", y[0], y[1])
    assert d[mix.index("CO")] > 0 and d[mix.index("H2")] > 0
    assert abs(d[mix.index("O2")] + y[1]) < 1e-15  # all oxygen consumed


def test_wiebe_normalization_and_inverse():
    w = Wiebe(-20.0, 55.0, 5.0, 2.0)
    assert w.fraction(0.0) == 0.0 and w.fraction(55.0) == pytest.approx(1.0, abs=1e-15)
    for x in (0.1, 0.5, 0.9):
        assert w.fraction(w.angle_at_fraction(x)) == pytest.approx(x, rel=1e-12)
    grid = np.linspace(0, 55, 20001)
    grid[-1] = 55.0 * (1 - 1e-13)  # left limit: the truncated law has a rate jump at EOC
    integral = np.trapezoid([w.rate_per_deg(t) for t in grid], grid)
    assert integral == pytest.approx(1.0, rel=1e-6)


def test_slider_crank_cycle_symmetry():
    g = SliderCrank(0.086, 0.086, 0.143, 11.0)
    assert g.volume(0) == pytest.approx(g.volume(360))
    assert g.volume(-180) == pytest.approx(g.clearance_volume + g.displacement)
    assert g.volume(90) > g.clearance_volume + g.displacement / 2  # finite rod: piston past mid-stroke


def test_valve_lift_laws_and_area():
    lift = HarmonicLift(350.0, -130.0, 0.010)
    assert lift.duration == pytest.approx(240.0)
    assert lift.lift(350.0) == 0.0 and lift.lift(-130.0) == 0.0
    assert lift.lift(wrap(350.0 + 120.0)) == pytest.approx(0.010)
    table = TabulatedLift([-10.0, 40.0, 110.0, 180.0, 230.0], [0.0, 0.004, 0.009, 0.004, 0.0])
    assert table.lift(110.0) == pytest.approx(0.009) and table.lift(300.0) == 0.0
    assert all(table.lift(t) >= 0.0 for t in np.linspace(-360, 360, 2000))
    cd = FlowCoefficients((0.0, 0.1, 0.3), (0.7, 0.65, 0.45), (0.6, 0.55, 0.38))
    valve = Valve(lift, 0.032, 2, cd)
    L = lift.lift(30.0)
    assert valve.effective_area(30.0, "forward") == pytest.approx(2 * cd.cd(L / 0.032, "forward") * math.pi * 0.032 * L)
    assert valve.effective_area(0.0, "forward") == 0.0


def test_lift_table_rejects_nonzero_ends():
    with pytest.raises(ValueError):
        TabulatedLift([0.0, 10.0, 20.0], [0.001, 0.002, 0.0])


def test_woschni_and_friction_reference_values():
    h = WoschniHeatTransfer().coefficient(bore_m=0.1, p_pa=1e6, T_K=800.0, mean_piston_speed=10.0,
                                          displacement=7.85e-4, gas_exchange=False, combustion_phase=False,
                                          reference=None, volume=1e-4)
    expected = 3.26 * 0.1 ** -0.2 * 1000.0 ** 0.8 * 800.0 ** -0.55 * (2.28 * 10.0) ** 0.8
    assert h == pytest.approx(expected, rel=1e-12)
    f = ChenFlynnFriction(30000.0, 0.005, 9000.0, 90.0)
    assert f.fmep(5e6, 15.0) == pytest.approx(30000 + 25000 + 135000 + 20250)
