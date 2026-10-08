import pytest
from motorsim.p5c import make_p5c_full_fixture
from motorsim.p6_species import P6IntegratedSystem
from motorsim.p7_prescribed import Q_F

def full_system(port_area=0.0):
    return P6IntegratedSystem(make_p5c_full_fixture(cells=2, port_area=port_area),
                              enable_p7=True, angular_rate_deg_s=18000.0)

def test_f06_real_full_topology_same_ssprk2_source_and_energy_ledger():
    system = full_system()
    captured = tuple(system.species_mass['cylinder'][0])
    captured_fresh = captured[0] + captured[1]
    before = system.inventory_snapshot()['global']
    dt = 1e-7
    result = system.step(dt, angle=350.0 + dt * 18000.0)
    after = system.inventory_snapshot()['global']
    assert system.p7_event is not None
    assert system.p7_event.fresh == pytest.approx(captured_fresh)
    assert len(result['gas']['stage_rhs']) == 2
    assert result['gas']['prescribed_heat'] > 0.0
    assert result['gas']['ledger']['prescribed_heat'] == result['gas']['prescribed_heat']
    assert result['gas']['exhaust']['closed']
    assert after['species_sum'] == pytest.approx(after['gas_mass'], abs=1e-12)
    assert after['gas_mass'] > before['gas_mass']
    assert system.p7_event.ledger.burned_produced == pytest.approx(
        -system.p7_source_delta[0] - system.p7_source_delta[1])
    assert system.p7_event.ledger.heat_added == pytest.approx(
        Q_F * system.p7_event.ledger.burned_produced)
    assert result['gas']['prescribed_heat'] == pytest.approx(
        Q_F * system.p7_event.ledger.burned_produced)

def test_f06_restart_inside_active_event_and_deterministic_replay():
    a = full_system(); a.step(1e-7, angle=350.0 + 1e-7 * 18000.0); snap = a.snapshot()
    a.step(1e-7, angle=350.0 + 2e-7 * 18000.0)
    expected = (a.inventory_snapshot(), a.gas.totals(), a.p7_event.ledger.heat_added)
    b = full_system(); b.restore(snap); assert b.p7_event is not None
    b.step(1e-7, angle=350.0 + 2e-7 * 18000.0)
    assert b.inventory_snapshot() == expected[0]
    assert b.gas.totals() == expected[1]
    assert b.p7_event.ledger.heat_added == expected[2]

def test_f06_pre_post_transport_conservative_and_ports_guarded():
    system = full_system()
    system.step(1e-7, angle=349.0); system.step(1e-7, angle=350.0 + 1e-7 * 18000.0); system.step(1e-7, angle=391.0)
    assert system.inventory_snapshot()['global']['species_sum_minus_gas_mass'] == pytest.approx(0.0)
    leaking = full_system(1e-4)
    with pytest.raises(ValueError, match='closed cylinder ports'):
        leaking.step(1e-7, angle=350.0 + 1e-7 * 18000.0)

def test_p6_default_does_not_react_at_heat_angle():
    system = P6IntegratedSystem(make_p5c_full_fixture(cells=2, port_area=0.0))
    system.step(1e-7, angle=350.0 + 1e-7 * 18000.0)
    assert system.p7_event is None
    assert system.p7_enabled is False

def test_p7_continuous_time_angle_progression_capture_and_restart():
    system = full_system()
    system.gas.angle = 349.99
    dt = 1e-7
    system.step(dt)
    assert system.gas.angle == pytest.approx(349.99 + dt * 18000.0)
    assert system.p7_event is None
    before = system.p7_source_delta[:]
    for _ in range(4):
        system.step(dt)
    assert system.p7_event is None
    system.step(dt)
    assert system.gas.angle == pytest.approx(349.99 + 6.0 * dt * 18000.0)
    assert system.p7_event is not None
    assert len(system.p7_events) == 1
    assert system.p7_source_delta != before
    snap = system.snapshot()
    angle = system.gas.angle
    system.step(dt)
    replay_angle = system.gas.angle
    replay_event = system.p7_event.ledger.heat_added
    restored = full_system()
    restored.restore(snap)
    assert restored.gas.angle == pytest.approx(angle)
    assert restored.p7_event is not None
    restored.step(dt)
    assert restored.gas.angle == pytest.approx(replay_angle)
    assert restored.p7_event.ledger.heat_added == pytest.approx(replay_event)

def test_p7_full_window_3000rpm_authoritative_species_and_energy_closure():
    system = full_system()
    system.gas.angle = 350.0
    dt = 1e-7
    initial = tuple(system.species_mass['cylinder'][0])
    steps = 0
    while system.gas.angle < 390.0:
        system.step(dt)
        steps += 1
        assert steps < 23000
    event = system.p7_event
    assert event is not None
    assert system.gas.angle == pytest.approx(350.0 + steps * dt * 18000.0)
    assert event.fresh == pytest.approx(initial[0] + initial[1])
    assert event.ledger.burned_produced == pytest.approx(event.fresh, abs=2e-7)
    assert event.ledger.fresh_air_converted == pytest.approx(initial[0], abs=2e-7)
    assert event.ledger.fuel_converted == pytest.approx(initial[1], abs=2e-12)
    assert event.ledger.heat_added == pytest.approx(Q_F * event.ledger.burned_produced, rel=2e-7)
    cumulative_heat = sum(h['prescribed_heat'] for h in system.gas.history)
    assert cumulative_heat == pytest.approx(event.ledger.heat_added, abs=1e-12)
    assert cumulative_heat == pytest.approx(Q_F * event.ledger.burned_produced, abs=1e-12)
    assert system.species_mass['cylinder'][0][0] == pytest.approx(0.0, abs=2e-7)
    assert system.species_mass['cylinder'][0][3] == pytest.approx(initial[3] + event.fresh, abs=2e-7)
    assert system.species_mass['cylinder'][0][2] == pytest.approx(initial[2], abs=2e-12)
    assert system.inventory_snapshot()['global']['species_sum_minus_gas_mass'] == pytest.approx(0.0, abs=1e-12)
    ledger = system.gas.history[-1]['ledger']
    assert ledger['residual']['energy_without_prescribed_heat'] == pytest.approx(
        ledger['residual']['energy'] - ledger['prescribed_heat'], abs=1e-12)

def test_p7_source_has_no_heat_support_after_fixed_event():
    system = full_system()
    system.gas.angle = 350.0
    system.step(1.0e-7, angle=350.0 + 1.0e-7 * 18000.0)
    assert system.p7_event is not None
    before = system.p7_event.ledger.heat_added
    system.step(1.0e-7, angle=391.0)
    assert system.gas.history[-1]['prescribed_heat'] == pytest.approx(0.0, abs=1e-15)
    assert system.p7_event.ledger.heat_added == pytest.approx(before, abs=1e-15)
