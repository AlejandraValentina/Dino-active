"""Dino 4T stage 2: regression tests against independent exact/analytic solutions.

These guard the defects found by the stage-2 audit (see docs/dino4t/stage2_assessment.md):
the stage-1 suite passed while an ideal open end passed 29 % too little flow.
"""
import math

import numpy as np
import pytest

from motorsim.dino4t import config, verification as v, verification_stage2 as s2
from motorsim.dino4t.restriction import EndCell, RestrictionError, VolumeGas, restriction_flux
from motorsim.dino4t.runner import run_operating_point
from motorsim.dino4t.thermo import Mixture, dry_air


def _end_cell(duct, q, index=0):
    return EndCell.from_primitive(duct.primitive(q), index)


def test_v1_boundary_defect_is_a_29_percent_flow_deficit_and_v2_removes_it():
    """Steady flow through an ideal open end vs the exact isentropic nozzle (E1)."""
    mix = s2._air_cp()
    res = {}
    for stagnation in (False, True):
        duct = v._uniform_duct(mix, 20, length=0.5, diameter=0.04)
        A = float(duct.area[0])
        up = VolumeGas.from_mixture(mix, 1.1e5, 300.0, np.ones(1), 0.0)
        dn = VolumeGas.from_mixture(mix, 1.0e5, 300.0, np.ones(1), 0.0)
        bench = v.DuctBench(duct, (up, A, A), (dn, A, A))
        orig = v.restriction_flux
        v.restriction_flux = lambda *a, _o=orig, _s=stagnation, **k: _o(*a, stagnation=_s, **k)
        try:
            out = bench.run(duct.uniform(1.05e5, 300.0, np.ones(1)), 0.08, probe=lambda q: 0.0)
        finally:
            v.restriction_flux = orig
        res[stagnation] = float(-np.mean([r[3] for r in out["trace"] if r[0] > 0.07]))
    M2 = 2 / 0.4 * (1.1 ** (0.4 / 1.4) - 1)
    T = 300.0 / (1 + 0.2 * M2)
    exact = 1e5 / (287.0 * T) * math.sqrt(M2 * 1.4 * 287.0 * T) * A
    assert res[False] / exact - 1 == pytest.approx(-0.2828, abs=0.01)  # the documented V1 defect
    assert abs(res[True] / exact - 1) < 2e-3


@pytest.mark.parametrize("mach_out", [0.1, 0.4, 0.7])
def test_duct_to_volume_branch_uses_stagnation_pressure(mach_out):
    """An ideal open end (sigma = 1) must hold the face static pressure at the ambient value."""
    mix = Mixture.standard()
    air = dry_air(mix)
    duct = v._uniform_duct(mix, 4, length=0.04)
    q = duct.uniform(1.0e5, 300.0, air, u=mach_out * 347.0)
    A = float(duct.area[-1])
    amb = VolumeGas.from_mixture(mix, 1.0e5, 300.0, air, 0.0)
    r = restriction_flux(_end_cell(duct, q, -1), "right", A, A, A, amb, mix.ns)
    assert r.p_face == pytest.approx(1.0e5, rel=1e-9)
    assert r.mdot_into_duct < 0


def test_supersonic_face_roots_are_excluded():
    """The V2 residual has spurious roots with a supersonic face; the physical one must be selected."""
    mix = Mixture.standard()
    air = dry_air(mix)
    duct = v._uniform_duct(mix, 4, length=0.04)
    q = duct.uniform(1.049e5, 706.0, air, u=357.0)
    A = float(duct.area[-1])
    amb = VolumeGas.from_mixture(mix, 1.01325e5, 298.15, air, 1.0)
    r = restriction_flux(_end_cell(duct, q, -1), "right", A, A, A, amb, mix.ns)
    assert r.p_face == pytest.approx(1.01325e5, rel=1e-6) and r.mach_face < 1.0


def test_choked_duct_end_when_orifice_demands_more_than_the_duct_can_deliver():
    mix = Mixture.standard()
    air = dry_air(mix)
    duct = v._uniform_duct(mix, 4, length=0.04)
    q = duct.uniform(1.0e5, 300.0, air, u=250.0)
    A = float(duct.area[-1])
    vac = VolumeGas.from_mixture(mix, 0.2e5, 300.0, air, 0.0)  # strong suction
    r = restriction_flux(_end_cell(duct, q, -1), "right", A, A, A, vac, mix.ns)
    assert r.choked and r.mach_face == pytest.approx(1.0, abs=1e-6)


def test_open_end_steady_flow_vs_exact_nozzle():
    c = s2.open_end_steady_flow()
    assert c["passed"], c["metrics"]["rows"]


def test_strong_unsteady_inflow_matches_shock_contact_solution():
    c = s2.strong_unsteady_inflow_vs_shock_contact_solution()
    assert c["passed"], c["metrics"]["rows"]


def test_shock_reflection_at_open_end_matches_exact():
    c = s2.open_end_shock_reflection()
    assert c["passed"], c["metrics"]["rows"]


def test_helmholtz_frequency_and_compressible_neck_correction():
    c = s2.helmholtz_resonator()
    m = c["metrics"]
    assert c["passed"], m
    # the lumped Helmholtz formula is ~2 % off here; the model must follow the exact compressible result
    assert abs(m["f_model_Hz"] - m["f_exact_Hz"]) < 0.1 * abs(m["f_lumped_Hz"] - m["f_exact_Hz"])


def test_vessel_charge_and_discharge_vs_independent_ode():
    for c in s2.vessel_discharge_and_charge():
        assert c["passed"], c["metrics"]
        assert c["metrics"]["energy_closure"] < 1e-12 and c["metrics"]["mass_closure"] < 1e-12


def test_fanno_and_wall_heat_transfer():
    for c in (s2.fanno_friction(), s2.wall_heat_transfer()):
        assert c["passed"], c["metrics"]


def test_order_rule_monotone_data_recovers_formal_order():
    """Extremum clipping, not a defect, explains sub-2 order of TVD limiters on pulses (control experiment)."""
    c = s2.order_profiles(limiters=("van_leer", "mc"), first_order_grids=(100, 200, 400))
    assert c["passed"], c["metrics"]
    assert c["metrics"]["van_leer"]["monotone"][-1] > c["metrics"]["van_leer"]["pulse"][-1]


def test_plenum_engine_wiring_conserves_and_runs():
    cfg = config.load(config.EXAMPLE_PATH)
    cfg["intake_plenum"] = {"provenance": "SYNTHETIC_ASSUMPTION", "volume_cm3": 3000.0,
                            "feed_duct": {"segments": [{"length_mm": 200.0, "start_diameter_mm": 50.0,
                                                       "end_diameter_mm": 50.0}], "friction": True,
                                          "heat_transfer": True, "wall_temperature_K": 320.0}}
    out = run_operating_point(cfg, max_cycles=3, overrides={"numerics": {"dx_mm": 25.0}})
    s = out["summary"]
    assert s["status"] == "completed"
    assert max(s["conservation"]["max_relative_closure"].values()) < 1e-12
    assert 0.5 < s["final_cycle"]["volumetric_efficiency_intake_valve"] < 1.2


def test_v1_restriction_model_reproduces_stage1_bit_for_bit():
    """Provenance: the stage-1 evidence stays reproducible behind numerics.restriction_model = 'V1'."""
    cfg = config.load(config.EXAMPLE_PATH)
    out = run_operating_point(cfg, max_cycles=8, overrides={"numerics": {"restriction_model": "V1"},
                                                            "combustion": {"zone_model": "single_zone"}})
    f = out["summary"]["final_cycle"]
    assert f["imep_net_bar"] == 12.498382979526601
    assert f["volumetric_efficiency_intake_valve"] == 0.9228879996798574


# ---------------------------------------------------------------- equilibrium and two zones
def test_equilibrium_solver_matches_cantera():
    c = s2.equilibrium_vs_cantera()
    assert c["passed"], c["metrics"]


def test_two_zone_closure_matches_cantera_including_uv_end_state():
    c = s2.two_zone_closure_vs_cantera()
    assert c["passed"], c["metrics"]


def test_two_zone_closure_is_continuous_across_the_regularisation_threshold():
    from motorsim.dino4t.equilibrium import TwoZoneClosure
    mix = Mixture.standard()
    y, b = s2._charge_elements(mix, 1.0)
    cl = TwoZoneClosure(mix)
    kw = dict(U=float(mix.internal_energy(y, 700.0)), s_u=float(mix.entropy(y, 700.0, 22e5)),
              V=float(mix.gas_constant(y)) * 700.0 / 22e5, m=1.0, Y_u=y, b_full=b, fuel_inert_full=0.0)
    below = cl.solve(x_b=cl.x_regular * (1 - 1e-9), **kw)
    above = cl.solve(x_b=cl.x_regular * (1 + 1e-9), **kw)
    assert abs(below.p / above.p - 1) < 3e-5  # documented O(x_reg) regularisation error


@pytest.mark.parametrize("x_b", [1e-9, 1e-6, 1e-4 * 1.0001, 1e-3])
def test_two_zone_closure_survives_truncation_error_in_total_energy(x_b):
    """U carries integrator truncation error (~1e-6 relative); e_b = (U-U_u)/m_b must not blow up."""
    from motorsim.dino4t.equilibrium import TwoZoneClosure
    mix = Mixture.standard()
    y, b = s2._charge_elements(mix, 1.0)
    cl = TwoZoneClosure(mix)
    u0 = float(mix.internal_energy(y, 700.0))
    for err in (0.0, 3e-6, -3e-6):
        z = cl.solve(U=u0 * (1 + err), s_u=float(mix.entropy(y, 700.0, 22e5)),
                     V=float(mix.gas_constant(y)) * 700.0 / 22e5, m=1.0, x_b=x_b, Y_u=y, b_full=b, fuel_inert_full=0.0)
        assert 300.0 < z.T_b < 6000.0 and abs(z.p / 22e5 - 1) < 0.05


def test_two_zone_closed_cylinder_second_order_and_conservative():
    c = s2.two_zone_cylinder_temporal_order(dthetas=(1.0, 0.5, 0.25))
    assert c["passed"], c["metrics"]


def test_two_zone_engine_cycle_reports_zone_temperatures():
    cfg = config.load(config.EXAMPLE_PATH)
    out = run_operating_point(cfg, max_cycles=2, overrides={"numerics": {"dx_mm": 25.0}})
    f = out["summary"]["final_cycle"]
    assert f["T_burned_max_K"] > f["T_unburned_max_K"] > 600.0
    assert max(out["summary"]["conservation"]["max_relative_closure"].values()) < 1e-12


# -------------------------------------------------------------------------- studies
def test_apply_overrides_does_not_mutate_the_base_configuration():
    from motorsim.dino4t import studies
    cfg = config.load(config.EXAMPLE_PATH)
    out = studies.apply_overrides(cfg, {"operating_point.rpm": 7000.0, "intake_valve.lift.close_deg": -120.0})
    assert out["operating_point"]["rpm"] == 7000.0 and cfg["operating_point"]["rpm"] == 6000.0
    scaled = studies.PHYSICAL_PARAMETERS["intake_runner_length"](cfg, 1.1)["intake_duct.segments"]
    assert scaled[0]["length_mm"] == pytest.approx(1.1 * cfg["intake_duct"]["segments"][0]["length_mm"])


def test_sweep_with_continuation_returns_provenance(tmp_path):
    from motorsim.dino4t import studies
    cfg = config.load(config.EXAMPLE_PATH)
    rows = studies.sweep(cfg, studies.linspace_points("operating_point.rpm", 5000.0, 5500.0, 2), max_cycles=2,
                         base_overrides={"numerics": {"dx_mm": 30.0}}, out_dir=tmp_path)
    assert [r["status"] for r in rows] == ["completed", "completed"]
    saved = __import__("json").loads((tmp_path / "sweep.json").read_text(encoding="utf-8"))
    assert saved["claims"]["experimental_validation"] == "NOT_PERFORMED"
    assert (tmp_path / "sweep.csv").exists()


# ------------------------------------------------------------- boundary regime coverage
def test_supersonic_inflow_face_fails_closed_instead_of_returning_mach_above_one():
    mix = Mixture.standard()
    air = dry_air(mix)
    duct = v._uniform_duct(mix, 4, length=0.04)
    q = duct.uniform(0.6e5, 300.0, air, u=-0.9 * 347.0)  # already inflowing at M = 0.9
    A = float(duct.area[-1])
    res = VolumeGas.from_mixture(mix, 8.0e5, 400.0, air, 0.0)
    with pytest.raises(RestrictionError, match="supersonic inflow"):
        restriction_flux(_end_cell(duct, q, -1), "right", A, A, A, res, mix.ns)


def test_restriction_regime_scan_monotone_continuous_and_subsonic(tmp_path):
    """26 460 boundary evaluations over Mach -0.9..0.9, three T, three p, three area ratios and
    volume pressures 0.05-8 bar: a root always exists or the state is declared outside validity,
    |M_face| <= 1, mass flow is monotone in the volume pressure, fluxes follow the donor."""
    import runpy
    import sys
    from pathlib import Path
    out = tmp_path / "scan.json"
    argv = sys.argv
    sys.argv = ["scan", str(out)]
    try:
        runpy.run_path(str(Path(__file__).resolve().parents[1] / "scripts/dino4t/audit_restriction_regimes.py"),
                       run_name="__main__")
    finally:
        sys.argv = argv
    res = __import__("json").loads(out.read_text(encoding="utf-8"))
    assert res["failures"] == 0, res["failure_examples"][:3]
    assert res["cases"] > 20000
