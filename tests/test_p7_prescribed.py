import pytest
from motorsim.p7_prescribed import (Q_F, burn_fraction, burn_rate, capture_event,
    restore_event, snapshot_event, split_step, ssprk2_source_step)

def run(n):
    e = capture_event(350, (2.0, 1.0, 4.0, 3.0))
    s = (2.0, 1.0, 4.0, 3.0, 0.0)
    for i in range(n): s = ssprk2_source_step(s, 350+40*i/n, 40/n, 1.0, e)
    return s, e

def test_p7_f01_zero_fresh():
    s, e = run(1); z = capture_event(350, (0, 0, 4, 3))
    assert ssprk2_source_step((0, 0, 4, 3, 9), 350, 40, 1, z) == (0, 0, 4, 3, 9)
    assert e.fresh == 3 and z.ledger.heat_added == 0

def test_p7_f02_proportional_and_ledger():
    s, e = run(80)
    assert s[:4] == pytest.approx((0, 0, 4, 6), abs=2e-3)
    assert e.ledger.source_mass_residual == pytest.approx(0, abs=1e-12)
    assert e.ledger.heat_added == pytest.approx(Q_F*3, rel=2e-5)
    assert e.ledger.heat_burn_residual == pytest.approx(0, abs=1e-8)

def test_p7_f03_boundaries():
    assert burn_rate(349.9, 350) == 0 and burn_rate(390, 350) == 0
    assert split_step(349, 42, 350) == ((349, 350), (350, 390), (390, 391))

def test_p7_f04_both_stages_are_stage_angle_dependent():
    e = capture_event(350, (1, 1, 0, 0))
    assert e.source(350, 1)[3] == 0 and e.source(370, 1)[3] > 0

def test_p7_f05_only_captured_fresh():
    s, e = run(40)
    assert s[2] == 4 and e.ledger.residual_unchanged == 0

def test_p7_f06_closed_source_is_mass_conservative():
    s, e = run(100)
    assert sum(s[:4]) == pytest.approx(10, abs=2e-12)

def test_p7_f07_restart_and_f08_determinism():
    s, e = run(20); snap = snapshot_event(e)
    restored = restore_event(snap)
    assert snapshot_event(restored) == snap
    assert run(20)[0] == pytest.approx(s)

def test_p7_resolution_converges_to_analytic_primitive():
    coarse, _ = run(10); fine, _ = run(80)
    expected = 3 + 3*burn_fraction(390, 350)
    assert coarse[3] == pytest.approx(expected, abs=3e-3)
    assert fine[3] == pytest.approx(expected, abs=2e-3)
