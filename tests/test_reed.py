import copy
import math

import pytest

from motorsim.reed import (
    ReedBank,
    ReedPetal,
    ReedState,
    advance_petal,
    dynamic_reed_flow,
    static_area,
    static_lift,
    static_reed_flow,
)


def petal(**changes):
    values = dict(
        id="p1", mass_kg=1.0, pressure_area_m2=0.01,
        effective_width_m=0.02, stiffness_n_m=100.0,
        damping_n_s_m=4.0, lift_stop_m=0.01,
        discharge_coefficient=0.8, provenance="SYNTHETIC_ASSUMPTION",
        restitution=0.0,
    )
    values.update(changes)
    return ReedPetal(**values)


def test_static_equilibrium_and_multi_petal_area():
    first, second = petal(), petal(id="p2", effective_width_m=0.01)
    assert static_lift(first, 50.0) == pytest.approx(0.005)
    assert static_lift(first, -50.0) == 0.0
    assert static_lift(first, 200.0) == first.lift_stop_m
    assert static_area((first, second), 50.0) == pytest.approx(0.00012)


def test_exact_critical_and_overdamped_free_response():
    critical = petal(mass_kg=1.0, stiffness_n_m=4.0,
                     damping_n_s_m=4.0, lift_stop_m=10.0,
                     pressure_area_m2=1.0)
    result = advance_petal(critical, ReedState(0.0, 0.0), 4.0, 0.5)
    expected = 1.0 - 2.0 * math.exp(-1.0)
    assert result.position_m == pytest.approx(expected)
    assert result.velocity_m_s == pytest.approx(2.0 * math.exp(-1.0))

    overdamped = petal(mass_kg=1.0, stiffness_n_m=3.0,
                       damping_n_s_m=4.0, lift_stop_m=10.0,
                       pressure_area_m2=1.0)
    result = advance_petal(overdamped, ReedState(0.0, 0.0), 2.0, 0.5)
    expected = 2.0 / 3.0 - math.exp(-0.5) + math.exp(-1.5) / 3.0
    assert result.position_m == pytest.approx(expected)


def test_underdamped_stop_and_reverse_pressure_closure():
    model = petal(damping_n_s_m=0.2)
    opened = advance_petal(model, ReedState(0.0, 0.0), 1000.0, 0.5)
    assert opened.position_m == model.lift_stop_m
    assert opened.velocity_m_s == 0.0
    closed = advance_petal(model, opened, -1000.0, 0.05)
    assert 0.0 <= closed.position_m < opened.position_m


def test_contact_exactly_at_step_end_cannot_leave_outward_velocity():
    model = petal(mass_kg=1.0, pressure_area_m2=1.0,
                  stiffness_n_m=1.0, damping_n_s_m=0.0,
                  lift_stop_m=1.0, restitution=0.0)
    # x(t)=1-cos(t), so t=pi/2 reaches x=1 with outward velocity exactly
    # at the integration boundary.
    result = advance_petal(model, ReedState(0.0, 0.0), 1.0, math.pi / 2)
    assert result.position_m == pytest.approx(1.0)
    assert result.velocity_m_s == 0.0


def test_bank_roundtrip_multi_petal_and_deterministic_replay():
    petals = (petal(), petal(id="p2", mass_kg=0.5, stiffness_n_m=150.0))
    bank = ReedBank(petals, {item.id: ReedState(0.0, 0.0) for item in petals})
    bank.advance(2000.0, 0.01)
    snapshot = bank.snapshot()
    restored = ReedBank.restore(snapshot)
    assert restored.snapshot() == snapshot
    bank.advance(-1000.0, 0.003)
    restored.advance(-1000.0, 0.003)
    assert restored.snapshot() == bank.snapshot()
    assert set(bank.states) == {"p1", "p2"}


def test_static_and_dynamic_flow_reuse_restriction_and_reverse_behavior():
    item = petal()
    high, low = (150_000.0, 300.0, 1.0), (100_000.0, 300.0, 0.0)
    static_reverse = static_reed_flow((item,), low, high)
    assert static_reverse == (0.0, 0.0, 0.0)
    static_forward = static_reed_flow((item,), high, low)
    assert static_forward[0] > 0.0

    bank = ReedBank((item,), {item.id: ReedState(0.005, 0.0)})
    dynamic_reverse = dynamic_reed_flow(bank, low, high)
    assert dynamic_reverse[0] < 0.0
    bank.advance(-100_000.0, 0.0001)
    assert bank.dynamic_area_m2() > 0.0


@pytest.mark.parametrize("field,value", [
    ("mass_kg", 0), ("pressure_area_m2", math.inf),
    ("effective_width_m", True), ("stiffness_n_m", math.nan),
    ("damping_n_s_m", -1), ("lift_stop_m", 0),
    ("discharge_coefficient", 1.1), ("restitution", -0.1),
    ("provenance", "MEASURED"),
])
def test_invalid_petal_parameters_are_rejected(field, value):
    with pytest.raises(ValueError):
        petal(**{field: value}).validate()


def test_malformed_checkpoint_and_state_are_rejected():
    item = petal()
    bank = ReedBank((item,), {item.id: ReedState(0.0, 0.0)})
    snapshot = bank.snapshot()
    bad = copy.deepcopy(snapshot)
    bad["states"]["p1"]["position_m"] = float("nan")
    with pytest.raises(ValueError):
        ReedBank.restore(bad)
    bad = copy.deepcopy(snapshot)
    bad["schema"] = "future"
    with pytest.raises(ValueError):
        ReedBank.restore(bad)
    with pytest.raises(ValueError):
        advance_petal(item, ReedState(item.lift_stop_m + 1e-6, 0.0), 0, 0.01)


def test_bank_advance_is_transactional_on_bad_timestep():
    petals = (petal(), petal(id="p2"))
    bank = ReedBank(petals, {item.id: ReedState(0.0, 0.0) for item in petals})
    before = bank.snapshot()
    with pytest.raises(ValueError):
        bank.advance(1000.0, float("inf"))
    assert bank.snapshot() == before
