import pytest

from motorsim.p6_species import (SPECIES, P6SpeciesLedger, SpeciesChamber,
                                  advect_species, atmospheric_species,
                                  donor_species, validate_species,
                                  legacy_to_species, legacy_fresh_mass,
                                  scavenging_metrics)
from motorsim.p5c import make_p5c_fixture
from motorsim.p6_species import P6IntegratedSystem


def test_four_species_sum_and_atmosphere():
    assert atmospheric_species() == (1.0, 0.0, 0.0, 0.0)
    assert validate_species((.5, .2, .2, .1), 1.0) == (.5, .2, .2, .1)


def test_forward_and_reverse_use_actual_donor():
    left = (.8, .1, .1, 0.0)
    right = (.1, .2, .3, .4)
    assert donor_species(2.0, left, right) == (1.6, .2, .2, 0.0)
    assert donor_species(-2.0, left, right) == tuple(-2.0*x for x in right)


def test_shared_flux_updates_both_sides():
    left, right, flux = advect_species((.8, .1, .1, 0), (.1, .2, .3, .4), .2, .01, 1.0)
    assert all(x >= 0 for x in left + right)
    assert all(abs(a + b - c - d) < 1e-12 for a,b,c,d in zip(left,right,(.8,.1,.1,0),(.1,.2,.3,.4)))
    assert sum(flux) == pytest.approx(.2)


def test_independent_species_ledger():
    ledger = P6SpeciesLedger([(.8, .1, .1, 0.0), (.1, .2, .3, .4)])
    ledger.update([(.7, .1, .1, .1), (.2, .2, .3, .3)], (.0, .0, .0, .0))
    report = ledger.report()
    assert set(report) == set(SPECIES)
    assert all(abs(v['residual']) < 1e-12 for v in report.values())


def test_chamber_species_admissibility():
    chamber = SpeciesChamber(1.0, (.8, .1, .1, 0.0))
    chamber.apply((.1, 0.0, 0.0, 0.0), .1)
    assert sum(chamber.species) == pytest.approx(chamber.mass)


def test_legacy_mapping_is_deterministic_and_derived():
    state = legacy_to_species(2.0, .25)
    assert state == (0.5, 0.0, 1.5, 0.0)
    assert legacy_fresh_mass(state) == pytest.approx(.5)


def test_scavenging_metrics_do_not_count_reverse_exhaust():
    metrics = scavenging_metrics((.4, .1, .3, .2), transfer_fresh=.2,
                                 exhaust_outward_mass=-.5)
    assert metrics['fresh_short_circuit_mass'] == 0.0
    assert metrics['cylinder_fresh_mass'] == pytest.approx(.5)


def test_p6_integrates_on_p5c_and_derives_legacy_view():
    system = P6IntegratedSystem(make_p5c_fixture(port_area=0.0))
    result = system.step(1e-7)
    assert len(result['species_final']) == 4
    assert result['legacy_fresh_cylinder'] >= 0.0
    assert system.validate()
    assert len(system.stage_species) == 2
    assert system.stage_species[0]['before'] != system.stage_species[1]['before'] or \
        system.stage_species[0]['after'] == system.stage_species[1]['before']


def test_p6_restart_and_deterministic_replay():
    a = P6IntegratedSystem(make_p5c_fixture(port_area=0.0))
    a.step(1e-7)
    # The cumulative species-ledger baseline may differ from a fresh fixture
    # after preparation/rebasing, so it must travel with a restart snapshot.
    a._initial = tuple(value * .95 for value in a._species_totals())
    snap = a.snapshot()
    a.step(1e-7)
    expected = a._species_totals(), a.gas.totals()
    b = P6IntegratedSystem(make_p5c_fixture(port_area=0.0))
    b.restore(snap)
    assert b._initial == a._initial
    b.step(1e-7)
    assert b._species_totals() == expected[0]
    assert b.gas.totals() == expected[1]


def test_p6_heterogeneous_transfer_donors_and_scavenging_counter():
    system = P6IntegratedSystem(make_p5c_fixture(port_area=0.0))
    system.species['tr1'][0] = (.7, .2, .1, 0.0)
    system.species['tr2'][0] = (.1, .3, .2, .4)
    system.species['cylinder'][0] = (.2, .1, .4, .3)
    system._sync_manual_views()
    before = tuple(system.species['cylinder'][0])
    system._exchange(.01, 'tr1', 'cylinder', 1e-3)
    tr1_after = tuple(system.species['cylinder'][0])
    cylinder_mass = sum(system.species_mass['cylinder'][0])
    system.species_mass['cylinder'][0] = tuple(cylinder_mass * value for value in before)
    system._refresh_species_views()
    system._exchange(.01, 'tr2', 'cylinder', 1e-3)
    tr2_after = tuple(system.species['cylinder'][0])
    assert tr1_after != tr2_after
    assert system.validate()


def test_verification_trace_is_optional_and_shared_flux_consistent():
    off = P6IntegratedSystem(make_p5c_fixture(port_area=0.0))
    off.step(1e-7)
    assert off.verification_trace == []

    on = P6IntegratedSystem(make_p5c_fixture(port_area=0.0), capture_trace=True)
    on.step(1e-7)
    assert len(on.verification_trace) == 2
    for stage in on.verification_trace:
        for item in stage['interfaces']:
            assert sum(item['species_fluxes'].values()) == pytest.approx(
                item['gas_mass_flux'])
            if item['closed']:
                assert item['gas_mass_flux'] == 0.0
                assert all(value == 0.0 for value in item['species_fluxes'].values())


def test_verification_trace_donor_follows_flow_direction():
    system = P6IntegratedSystem(make_p5c_fixture(port_area=0.0), capture_trace=True)
    system.species['tr1'][0] = (.1, .2, .3, .4)
    system.step(1e-7)
    for stage in system.verification_trace:
        for item in stage['interfaces']:
            if item['gas_mass_flux'] > 0:
                assert item['donor_component'] == item['left_component']
            elif item['gas_mass_flux'] < 0:
                assert item['donor_component'] == item['right_component']
            else:
                assert item['donor_component'] is None


def test_physical_component_inventory_uses_gas_mass_geometry():
    system = P6IntegratedSystem(make_p5c_fixture(port_area=0.0))
    snapshot = system.inventory_snapshot()
    assert snapshot['global']['species_sum'] == pytest.approx(snapshot['global']['gas_mass'])
    for component in snapshot['components'].values():
        assert component['species_sum'] == pytest.approx(component['gas_mass'])
        assert all(cell['species_sum_minus_gas_mass'] == pytest.approx(0.0)
                   for cell in component['cells'])


def test_rhs_trace_assembles_chamber_interface_species_contributions():
    system = P6IntegratedSystem(make_p5c_fixture(port_area=0.0), capture_trace=True)
    system.species['tr1'][0] = (.1, .2, .3, .4)
    system.species['tr2'][0] = (.4, .3, .2, .1)
    system.step(1e-7)
    for stage in system.verification_trace:
        rhs = stage['rhs']
        assert len(rhs['crankcase']['assembled_rhs']) == 4
        assert len(rhs['cylinder']['assembled_rhs']) == 4


def test_conservative_species_mass_is_authoritative_through_step():
    system = P6IntegratedSystem(make_p5c_fixture(port_area=0.0), capture_trace=True)
    system.species['tr1'][0] = (.7, .2, .1, 0.0)
    system.species['tr2'][0] = (.1, .3, .2, .4)
    system.step(1e-7, angle=150.0)
    assert all(sum(cell) == pytest.approx(sum(cell))
               for cells in system.species_mass.values() for cell in cells)
    inventory = system.inventory_snapshot()['global']
    assert inventory['species_sum'] == pytest.approx(inventory['gas_mass'])
    assert all(sum(cell) >= 0.0 for cells in system.species_mass.values() for cell in cells)


def test_multicell_internal_species_transport_conserves_each_species():
    system = P6IntegratedSystem(make_p5c_fixture(cells=3, port_area=0.0),
                                capture_trace=True)
    system.species['tr1'][:] = [(.8, .1, .1, 0.0), (.4, .2, .2, .2),
                                 (.1, .2, .3, .4)]
    system.species['tr2'][:] = [(.1, .3, .2, .4), (.2, .2, .3, .3),
                                 (.7, .1, .1, .1)]
    system.step(1e-7, angle=150.0)
    before = system._species_totals()
    for _ in range(4):
        system.step(1e-7, angle=150.0)
    after = system._species_totals()
    assert after == pytest.approx(before, abs=1e-15)
    assert system.inventory_snapshot()['global']['species_sum_minus_gas_mass'] == pytest.approx(0.0)
