"""Dino 4T: duct solver, restriction boundary, cylinder integration (L0, < ~1 min)."""
import numpy as np
import pytest

from motorsim.dino4t import verification as v
from motorsim.dino4t.restriction import EndCell, VolumeGas, restriction_flux
from motorsim.dino4t.thermo import Mixture, dry_air


@pytest.fixture(scope="module")
def mix():
    return Mixture.standard()


def test_sod_converges_and_conserves():
    result = v.sod_shock_tube(resolutions=(100, 200, 400))
    assert result["passed"], result["metrics"]


def test_unlimited_scheme_is_second_order():
    result = v.smooth_acoustic_order(resolutions=(100, 200, 400), limiter="unlimited_central")
    assert result["metrics"]["observed_order"][-1] > 1.8, result["metrics"]


def test_well_balanced_quiescent_duct():
    result = v.well_balanced_area_change()
    assert result["passed"], result["metrics"]


def _cell(duct, q):
    return EndCell.from_primitive(duct.primitive(q), 0)


def test_restriction_flux_is_shared_by_duct_and_volume(mix):
    air = dry_air(mix)
    duct = v._uniform_duct(mix, 4, length=0.04)
    q = duct.uniform(1e5, 300.0, air)
    A = float(duct.area[0])
    for p_vol in (0.5e5, 0.99e5, 1.01e5, 3e5):
        vol = VolumeGas.from_mixture(mix, p_vol, 900.0, air, 1.0)
        r = restriction_flux(_cell(duct, q), "left", A, 0.3 * A, 0.25 * A, vol, mix.ns)
        # mass, species, tracer and energy leaving the volume enter the duct (x-flux at a left end)
        assert np.allclose(r.flux_x[:mix.ns], -r.to_volume[:mix.ns], rtol=0, atol=1e-18)
        assert r.flux_x[mix.ns + 2] == pytest.approx(-r.to_volume[mix.ns + 1], rel=1e-15)
        assert (r.mdot_into_duct > 0) == (p_vol > 1e5)


def test_restriction_choked_flow_matches_orifice_law(mix):
    air = dry_air(mix)
    duct = v._uniform_duct(mix, 4, length=0.04)
    q = duct.uniform(1e5, 300.0, air)
    A = float(duct.area[0])
    vol = VolumeGas.from_mixture(mix, 10e5, 1500.0, air, 1.0)
    r = restriction_flux(_cell(duct, q), "left", A, 0.05 * A, 0.05 * A, vol, mix.ns)
    ideal = v.orifice_mass_flow(0.05 * A, 10e5, 1500.0, vol.R, vol.gamma, 1e5)
    assert r.choked and r.mdot_into_duct == pytest.approx(ideal, rel=1e-12)


def test_closed_end_reflects_like_a_wall(mix):
    air = dry_air(mix)
    duct = v._uniform_duct(mix, 4, length=0.04)
    q = duct.uniform(1e5, 300.0, air, u=-20.0)  # gas moving toward the left wall
    r = restriction_flux(_cell(duct, q), "left", float(duct.area[0]), 0.0, 0.0,
                         VolumeGas.from_mixture(mix, 1e5, 300.0, air, 0.0), mix.ns)
    assert r.mdot_into_duct == 0.0 and r.p_face > 1e5  # compression at the wall
    w = duct.primitive(q)
    g, a = float(w["gamma"][0]), float(w["a"][0])
    simple_wave = 1e5 * (1 + (g - 1) / 2 * 20.0 / a) ** (2 * g / (g - 1))
    assert r.p_face == pytest.approx(simple_wave, rel=1e-12)
    assert r.p_face == pytest.approx(1e5 + float(w["rho"][0]) * a * 20.0, rel=5e-3)  # acoustic limit


def test_isentropic_motoring_second_order():
    result = v.isentropic_motoring(dthetas=(1.0, 0.5))
    assert result["metrics"]["observed_order"][-1] > 1.8
    assert max(result["metrics"]["energy_closure"]) < 1e-12


def test_burn_matches_independent_ode():
    result = v.burn_vs_independent_ode(dthetas=(0.5, 0.25))
    assert result["metrics"]["max_rel_pressure_difference"][-1] < 1e-5, result["metrics"]
    assert max(result["metrics"]["energy_closure"]) < 1e-12
