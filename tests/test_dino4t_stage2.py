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
    out = run_operating_point(cfg, overrides={"numerics": {"restriction_model": "V1"}}, max_cycles=8)
    f = out["summary"]["final_cycle"]
    assert f["imep_net_bar"] == 12.498382979526601
    assert f["volumetric_efficiency_intake_valve"] == 0.9228879996798574
