import copy
import pytest

from motorsim.p5c import IntegratedP5C, make_p5c_fixture
from motorsim.gas1d.eos import InvalidState


def test_p5c_closed_ports_and_conditional_ledger():
    s = make_p5c_fixture(port_area=0.0)
    before = s.totals()
    trace = s.step(1.0e-7)
    assert trace["dependency"] == "CONDITIONAL_ON_P4"
    assert trace["exhaust"]["closed"]
    assert trace["exhaust"]["flux"][0] == 0.0
    assert trace["exhaust"]["flux"][2:] == (0.0, 0.0)
    assert s.admissible()
    assert abs(s.totals()["mass"] - before["mass"]) < 1e-9
    assert abs(s.totals()["species"] - before["species"]) < 1e-9
    assert abs(s.totals()["energy"] - before["energy"]) < 1e-4


def test_p5c_restart_replay():
    a = make_p5c_fixture(port_area=1.0e-4)
    a.step(1.0e-7)
    snap = a.snapshot()
    a.step(1.0e-7)
    expected = a.totals()
    b = make_p5c_fixture(port_area=1.0e-4)
    b.restore(snap)
    b.step(1.0e-7)
    assert b.totals() == expected


def test_p5c_full_topology_evolves_exhaust():
    s = make_p5c_fixture(port_area=1.0e-4)
    initial = s.exhaust.cells[0].conservative
    s.step(1.0e-7)
    assert s.history[-1]["exhaust"]["area"] > 0
    # Equal-pressure initial states may only carry wall momentum; the duct is
    # still dynamically included in the unified RHS and remains admissible.
    assert s.admissible()


def test_p5c_single_rhs_contains_two_transfers_and_exhaust():
    s = make_p5c_fixture(port_area=1.0e-4)
    s.step(1.0e-7)
    interfaces = s.history[-1]["stage_interfaces"][0]
    assert len(interfaces) == 3
    assert s.history[-1]["stage_rhs"][0] == s.history[-1]["stage_rhs"][0]


def test_p5c_closed_exhaust_keeps_transfer_interfaces_in_rhs():
    s = make_p5c_fixture(port_area=0.0)
    s.step(1.0e-7)
    interfaces = s.history[-1]["stage_interfaces"][0]
    assert interfaces[2][0] == 0.0 and interfaces[2][2] == 0.0
    assert len(interfaces[:2]) == 2


def test_p5c_full_fixture_uses_compatible_atmospheric_state():
    s = __import__('motorsim.p5c', fromlist=['make_p5c_full_fixture']).make_p5c_full_fixture()
    s.step(1.0e-7, angle=0.0)
    assert s.admissible()


def test_p5c_controlled_internal_backflow_uses_resolved_flux():
    from motorsim.p5c import make_p5c_backflow_fixture
    s = make_p5c_backflow_fixture()
    s.step(1.0e-7, angle=150.0)
    # Interface index 1 is crankcase -> TR1 in the established trace order.
    assert s.history[-1]["core_interfaces"][0][1][0] < 0.0
    assert s.admissible()


def test_p5c_external_ledger_includes_intake_and_exhaust():
    """The global ledger contains both atmospheric boundary traces."""
    s = __import__('motorsim.p5c', fromlist=['make_p5c_full_fixture']).make_p5c_full_fixture()
    before = s.totals()
    record = s.step(1.0e-7, angle=0.0)
    after = s.totals()

    expected = {
        key: 0.5 * sum(
            record["stage_external"][stage][index] -
            record["stage_exhaust_external"][stage][index]
            for stage in (0, 1)) * record["dt"]
        for key, index in (("mass", 0), ("energy", 2), ("species", 3))
    }
    assert s._last_external == expected
    for key in expected:
        assert abs((after[key] - before[key]) - expected[key]) < 1e-10


def test_p5c_external_ledger_closes_global_inventory_with_both_boundaries():
    s = __import__('motorsim.p5c', fromlist=['make_p5c_full_fixture']).make_p5c_full_fixture()
    before = s.totals()
    for angle in (0.0, 30.0, 60.0):
        s.step(1.0e-7, angle=angle)
    after = s.totals()
    for key in ("mass", "energy", "species"):
        assert after[key] - before[key] == pytest.approx(
            s._external_cumulative[key], abs=1e-10)


def test_p5c_legacy_scalar_roundoff_reproducer_is_bounded_and_nonphysical_excess_fails():
    s = __import__('motorsim.p5c', fromlist=['make_p5c_full_fixture']).make_p5c_full_fixture()
    # One-ULP overshoot captured from KT100 R1 cycle 24, reduced to one P5 cell.
    q = (0.7952109571685706, 230.51360083770064,
         204007.64651722068, 0.7952109571685707)
    s.core.intake.cells[0].conservative = q
    with pytest.raises(InvalidState):
        s.eos.primitive(q)  # the shared EOS gate remains strict
    assert s.admissible()  # P5's explicit float64 scalar-view adapter is bounded

    s.core.intake.cells[0].conservative = (
        q[0], q[1], q[2], q[0] + 32 * __import__('math').ulp(q[0]))
    with pytest.raises(InvalidState):
        s.admissible()
