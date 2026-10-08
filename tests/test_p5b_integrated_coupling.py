import pytest
from unittest.mock import patch

from motorsim.p5b import (
    Chamber,
    IntegratedIntakeTransfer,
    make_single_0d1d_fixture,
    interior_rhs,
    make_closed_volume_work_fixture,
    make_one_transfer_fixture,
    OneTransferFixture,
    make_two_transfer_fixture,
    TwoTransferFixture,
    ssprk2_step,
)
from motorsim.gas1d.mesh import uniform_mesh
from motorsim.gas1d.boundary import Boundary
from motorsim.gas1d.eos import IdealGas
from motorsim import p5b

E=IdealGas()
def make():
    c=Chamber((1.0,0.,100000.,.5),.001); y=Chamber((1.0,0.,100000.,.5),.01)
    duct=(1.0,0.,101325.,0.)
    return IntegratedIntakeTransfer(c,y,(duct,duct,duct),eos=E)

def test_stage_port_events_and_closed_leakage():
    n=make(); h=n.step(.01, angle=0); assert h['areas']==(0.,0.,0.)
    h=n.step(.01, angle=300); assert h['areas'][0]>0

def test_two_transfer_entities_and_restart_determinism():
    a=make(); a.step(.01,angle=120); snap=a.snapshot(); a.step(.01,angle=250)
    b=make(); b.restore(snap); b.step(.01,angle=250)
    assert a.history[-1] == b.history[-1]

def test_complete_subsystem_has_trace_and_no_exhaust():
    n=make(); [n.step(.005, angle=i*30) for i in range(12)]
    assert len(n.history)==12 and all(len(x['fluxes'])==3 for x in n.history)

def test_interior_rhs_uses_gas1d_hllc():
    mesh=uniform_mesh(2, length=1., area=1.)
    states=[(1.,0.,100000.,.2),(1.,10.,100000.,.2)]
    rhs=interior_rhs(mesh,states,E)
    assert len(rhs)==2 and rhs[0][0] != 0


def test_atmospheric_intake_boundary_uses_consistent_left_face_orientation():
    """A uniform stationary state must not acquire a pressure impulse."""
    state = E.validate((101325.0 / (E.R * 300.0), 0.0, 101325.0, 0.0))
    mesh = uniform_mesh(1, length=0.03, area=1.0e-4)
    node = IntegratedIntakeTransfer(
        Chamber(state, 1.0e-3), Chamber(state, 1.0e-2),
        ((state,), (state,), (state,)), eos=E,
        meshes=(mesh, mesh, mesh), external_boundary=True,
        external_boundary_flux_convention="global_x")
    rhs, _ = node._rhs(node._state(), 300.0)
    assert rhs[2][0] == pytest.approx((0.0, 0.0, 0.0, 0.0), abs=1e-10)

def test_global_ssprk2_two_stages():
    out=ssprk2_step((1.,), lambda z:(-z[0],), .1)
    assert 0 < out[0] < 1

def test_chamber_rhs_sums_one_stage_and_includes_volume_work():
    chamber = Chamber((2.0, 0.0, 100000.0, .25), .01)
    rhs = chamber.conservative_rhs(
        ((.2, 0.0, 10.0, .05), (-.1, 0.0, -4.0, -.02)),
        E, volume_rate=.003)
    assert rhs[0] == .1
    assert abs(rhs[1] - (6.0 - 100000.0*.003)) < 1e-12
    assert abs(rhs[2] - .03) < 1e-12

def test_chamber_stage_updates_volume_and_uses_pre_stage_pressure():
    chamber = Chamber((2.0, 0.0, 100000.0, .25), .01)
    initial = chamber.inventory(E)
    rhs = chamber.conservative_rhs(((0.0, 0.0, 0.0, 0.0),), E,
                                   volume_rate=.001)
    chamber.apply_rhs(rhs, .1, E, volume_rate=.001)
    assert chamber.volume == .0101
    assert chamber.inventory(E)[0] == initial[0]
    assert chamber.inventory(E)[2] < initial[2]

def test_integrated_step_applies_each_chamber_once_with_volume_work():
    n = make()
    n.volume_rates = (.001, -.0005)
    n.step(.01, angle=120)
    assert n.crankcase.volume == .00101
    assert n.cylinder.volume == pytest.approx(.009995)
    assert n.ledger['cc_work'] < 0
    assert n.ledger['cyl_work'] > 0

def test_contractual_volume_work_uses_stage_pressure_and_sign():
    chamber = Chamber((2.0, 0.0, 100000.0, .01), .01)
    initial = chamber.inventory(E)
    volume_rate = .001
    dt = .1
    rhs = chamber.conservative_rhs(((0.0, 0.0, 0.0, 0.0),), E,
                                   volume_rate=volume_rate)
    chamber.apply_rhs(rhs, dt, E, volume_rate=volume_rate)

    # The contractual source is -p_stage*dV/dt.  No interface flux means
    # mass/species stay fixed while expansion removes exactly p*dV energy.
    assert chamber.volume == .0101
    assert chamber.inventory(E)[0] == initial[0]
    assert chamber.inventory(E)[1] == initial[1]
    assert chamber.inventory(E)[2] == initial[2] - 100000.0*volume_rate*dt

def test_contractual_volume_work_compression_has_opposite_sign():
    chamber = Chamber((2.0, 0.0, 100000.0, .01), .01)
    initial = chamber.inventory(E)
    volume_rate = -.001
    dt = .1
    rhs = chamber.conservative_rhs(((0.0, 0.0, 0.0, 0.0),), E,
                                   volume_rate=volume_rate)
    chamber.apply_rhs(rhs, dt, E, volume_rate=volume_rate)
    assert chamber.volume == .0099
    assert chamber.inventory(E)[2] == initial[2] + 100000.0*.001*dt

def test_contractual_volume_work_rejects_nonfinite_inputs():
    chamber = Chamber((2.0, 0.0, 100000.0, .01), .01)
    with pytest.raises(ValueError):
        chamber.conservative_rhs(((0.0, 0.0, 0.0, 0.0),), E, volume_rate=float('nan'))
    with pytest.raises(ValueError):
        chamber.apply_rhs((0.0, 0.0, float('inf')), .1, E)

def test_each_interface_is_resolved_once_from_its_own_duct_state():
    node = make()
    calls = []
    expected_interiors = [duct.primitive(E) for duct in node.duct_states]
    from motorsim import p5b
    original = p5b.interface_exchange

    def audited(chamber, interior, area, normal, *, eos):
        result = original(chamber, interior, area, normal, eos=eos)
        calls.append((interior, area, normal, tuple(result['outward'])))
        return result

    with patch.object(p5b, 'interface_exchange', side_effect=audited):
        history = node.step(.01, angle=150)

    assert len(calls) == 10
    assert calls[0][0] == expected_interiors[0]
    assert calls[1][0] == expected_interiors[1]
    assert calls[2][0] == expected_interiors[2]
    assert history['stages'][0]['interfaces'][0] == calls[0][3]
    assert history['stages'][0]['interfaces'][1] == calls[1][3]


def test_mass_global_ledger_balances_external_intake_and_internal_transfers():
    node = make()
    initial = node.mass_ledger()
    assert initial['delta_mass'] == 0.0
    assert initial['external_mass'] == 0.0
    assert initial['residual'] == 0.0

    for angle in (0.0, 120.0, 150.0, 300.0, 330.0):
        node.step(.001, angle=angle)

    audit = node.mass_ledger()
    assert audit['external_mass'] > 0.0
    assert audit['delta_mass'] == pytest.approx(audit['external_mass'], abs=1e-15)
    assert audit['residual'] == pytest.approx(0.0, abs=1e-15)


def test_mass_global_ledger_is_closed_when_all_ports_are_closed():
    node = make()
    for angle in (0.0, 30.0, 60.0, 240.0):
        node.step(.001, angle=angle)

    audit = node.mass_ledger()
    assert audit['delta_mass'] == pytest.approx(audit['external_mass'], abs=1e-12)
    assert audit['integration_residual'] == pytest.approx(0.0, abs=1e-15)

def test_species_global_ledger_balances_external_intake_and_internal_transfers():
    # Use a pressure-high crankcase so the open intake carries the chamber's
    # passive species out through the external boundary.
    node = IntegratedIntakeTransfer(
        Chamber((1.0, 0.0, 110000.0, .5), .001),
        Chamber((1.0, 0.0, 100000.0, .5), .01),
        ((1.0, 0.0, 101325.0, 0.0),) * 3,
        eos=E,
    )
    initial = node.species_ledger()
    assert initial['delta_species'] == 0.0
    assert initial['external_species'] == 0.0
    assert initial['residual'] == 0.0

    for angle in (0.0, 120.0, 150.0, 300.0, 330.0):
        node.step(.001, angle=angle)

    audit = node.species_ledger()
    # The signed boundary convention is shared with the mass ledger; this
    # fixture's prescribed atmosphere has Y=0, so species leaves the chamber
    # during the intake-open interval and the signed value is negative.
    assert abs(audit['external_species']) > 0.0
    assert audit['delta_species'] == pytest.approx(audit['external_species'], abs=1e-15)
    assert audit['residual'] == pytest.approx(0.0, abs=1e-15)

def test_species_global_ledger_is_closed_when_all_ports_are_closed():
    node = make()
    for angle in (0.0, 30.0, 60.0, 240.0):
        node.step(.001, angle=angle)

    audit = node.species_ledger()
    assert audit['external_species'] == 0.0
    assert audit['delta_species'] == pytest.approx(0.0, abs=1e-15)
    assert audit['residual'] == pytest.approx(0.0, abs=1e-15)


def test_species_global_ledger_cancels_internal_transfers_and_tracks_external_port():
    node = make()
    initial = node.species_ledger()
    assert initial['delta_species'] == 0.0
    assert initial['external_species'] == 0.0
    assert initial['residual'] == 0.0

    for angle in (120.0, 150.0, 300.0, 330.0):
        node.step(.001, angle=angle)

    audit = node.species_ledger()
    assert audit['delta_species'] == pytest.approx(audit['external_species'], abs=1e-12)
    assert audit['delta_species'] == pytest.approx(audit['external_species'], abs=1e-15)
    assert audit['residual'] == pytest.approx(0.0, abs=1e-15)


def test_energy_global_ledger_conserves_fixed_volume_closed_internal_system():
    node = make()
    initial = node.energy_ledger()
    assert initial['delta_energy'] == 0.0
    for angle in (0.0, 30.0, 60.0, 240.0):
        node.step(.001, angle=angle)

    audit = node.energy_ledger()
    assert audit['delta_energy'] == pytest.approx(audit['external_energy'], abs=1e-8)
    assert audit['chamber_work'] == 0.0
    assert audit['delta_energy'] == pytest.approx(audit['external_energy'], abs=1e-8)
    assert audit['residual'] == pytest.approx(0.0, abs=1e-12)


def test_energy_global_ledger_tracks_external_boundary_flux_once():
    node = make()
    node.step(.001, angle=300.0)

    audit = node.energy_ledger()
    assert audit['external_energy'] != 0.0
    assert audit['cc_work'] == 0.0
    assert audit['cyl_work'] == 0.0
    assert audit['delta_energy'] == pytest.approx(audit['external_energy'], abs=2e-12)
    assert audit['residual'] == pytest.approx(0.0, abs=2e-12)


def test_energy_global_ledger_preserves_variable_volume_work_signs():
    node = make()
    node.volume_rates = (.001, -.0005)
    node.step(.001, angle=0.0)

    audit = node.energy_ledger()
    assert audit['external_energy'] != 0.0
    assert audit['cc_work'] < 0.0
    assert audit['cyl_work'] > 0.0
    assert audit['delta_energy'] == pytest.approx(audit['external_energy'] + audit['chamber_work'], abs=1e-8)
    assert audit['residual'] == pytest.approx(0.0, abs=1e-12)


def test_closed_volume_work_fixture_conserves_inventories_and_has_no_flux():
    node = make_closed_volume_work_fixture()
    initial_mass = node.mass_ledger()['initial_mass']
    initial_species = node.species_ledger()['initial_species']
    initial_energy = node.energy_ledger()['initial_energy']

    for angle in (0.0, 30.0, 60.0, 240.0) * 5:
        trace = node.step(1.0e-3, angle=angle)
        assert trace['areas'] == (0.0, 0.0, 0.0)
        assert all(all(value == 0.0 for value in flux) for flux in trace['fluxes'])

    mass = node.mass_ledger()
    species = node.species_ledger()
    energy = node.energy_ledger()
    assert mass['final_mass'] == pytest.approx(initial_mass, abs=1e-15)
    assert species['final_species'] == pytest.approx(initial_species, abs=1e-15)
    assert mass['external_mass'] == 0.0 and mass['residual'] == pytest.approx(0.0, abs=1e-15)
    assert species['external_species'] == 0.0 and species['residual'] == pytest.approx(0.0, abs=1e-15)
    assert energy['external_energy'] == 0.0
    assert energy['delta_energy'] == pytest.approx(energy['chamber_work'], abs=1e-12)
    assert energy['residual'] == pytest.approx(0.0, abs=1e-12)
    assert energy['cc_work'] > 0.0
    assert energy['cyl_work'] < 0.0
    assert energy['final_energy'] == pytest.approx(initial_energy + energy['chamber_work'], abs=1e-12)


def test_closed_volume_work_fixture_keeps_chambers_admissible():
    node = make_closed_volume_work_fixture(volume_rates=(-2.0e-4, 2.0e-4))
    for angle in (0.0, 60.0, 240.0) * 4:
        node.step(1.0e-3, angle=angle)
        for chamber in (node.crankcase, node.cylinder):
            rho, pressure, temperature, fraction = chamber.thermodynamics(E)
            assert rho > 0.0 and pressure > 0.0 and temperature > 0.0
            assert 0.0 <= fraction <= 1.0


def test_single_0d1d_fixture_is_finite_and_externally_closed():
    node = make_single_0d1d_fixture(cells=3)
    initial = node.conservation()["initial"]
    for _ in range(8):
        node.step(1.0e-7)
    audit = node.conservation()
    assert audit["final"]["mass"] == pytest.approx(initial["mass"], abs=1.0e-15)
    assert audit["final"]["energy"] == pytest.approx(initial["energy"], abs=1.0e-10)
    assert audit["final"]["species"] == pytest.approx(initial["species"], abs=1.0e-15)
    assert all(abs(value) < 1.0e-10 for value in audit["delta"].values())
    assert node.admissible()


def test_single_0d1d_fixture_reuses_one_shared_flux_with_opposite_signs():
    node = make_single_0d1d_fixture(cells=1)
    trace = node.step(1.0e-7)
    for stage, shared in enumerate(trace["shared_fluxes"]):
        chamber_rhs = trace["chamber_rhs"][stage]
        duct_rhs = trace["duct_rhs"][stage][0]
        assert chamber_rhs[0] == shared[0]
        assert chamber_rhs[2] == shared[2]
        assert chamber_rhs[3] == shared[3]
        assert duct_rhs[0] == pytest.approx(-shared[0] / node.mesh.volumes[0])
        assert duct_rhs[2] == pytest.approx(-shared[2] / node.mesh.volumes[0])
        assert duct_rhs[3] == pytest.approx(-shared[3] / node.mesh.volumes[0])
    assert any(abs(value) > 0.0 for value in trace["shared_fluxes"][0])


def test_single_0d1d_fixture_keeps_chamber_volume_fixed_and_admissible():
    node = make_single_0d1d_fixture()
    volume = node.chamber.volume
    for _ in range(5):
        node.step(1.0e-7)
    rho, pressure, temperature, fraction = node.chamber.thermodynamics(E)
    assert node.chamber.volume == volume
    assert rho > 0.0 and pressure > 0.0 and temperature > 0.0
    assert 0.0 <= fraction <= 1.0
    assert node.admissible()


def test_single_0d1d_fixture_uses_contractual_rigid_wall_momentum_flux():
    node = make_single_0d1d_fixture(cells=1)
    state = node._state()
    (rhs, shared, _) = node._rhs(state)
    wall = Boundary('wall').flux(E.primitive(state[1][0]), 1, E)[0]
    assert wall[0] == 0.0 and wall[2] == 0.0 and wall[3] == 0.0
    assert wall[1] > 0.0
    expected = -(node.mesh.areas[-1] * wall[1] - (-shared[1])) / node.mesh.volumes[0]
    assert rhs[1][0][1] == pytest.approx(expected)


def test_one_transfer_fixture_is_two_chambers_and_one_finite_duct():
    node = make_one_transfer_fixture(cells=3)
    assert isinstance(node, OneTransferFixture)
    assert len(node.duct_states) == 3
    assert node.interface_areas == (node.mesh.areas[0], node.mesh.areas[-1])
    initial = node.conservation()["initial"]
    for _ in range(8):
        trace = node.step(1.0e-7)
        assert len(trace["stages"]) == 2
        assert trace["stage_order"] == (
            "crankcase_interface", "cylinder_interface", "duct_faces")
        assert node.admissible()
    audit = node.conservation()
    for key in ("mass", "energy", "species"):
        assert audit["final"][key] == pytest.approx(initial[key], abs=1.0e-10)


def test_one_transfer_solves_each_physical_interface_once_per_stage():
    node = make_one_transfer_fixture(cells=2)
    calls = []
    original = p5b.interface_exchange

    def audited(chamber, interior, area, normal, *, eos):
        result = original(chamber, interior, area, normal, eos=eos)
        calls.append((area, normal, result["outward"]))
        return result

    with patch.object(p5b, "interface_exchange", side_effect=audited):
        trace = node.step(1.0e-7)
    assert len(calls) == 4
    assert [call[1] for call in calls] == [-1, 1, -1, 1]
    assert trace["stages"][0]["interfaces"] == (calls[0][2], calls[1][2])
    assert trace["stages"][1]["interfaces"] == (calls[2][2], calls[3][2])
    for stage in trace["stages"]:
        left, right = stage["interfaces"]
        assert stage["face_fluxes"][0] == tuple(-x for x in left)
        assert stage["face_fluxes"][-1] == right


def test_one_transfer_closed_interfaces_have_exact_zero_leakage():
    node = make_one_transfer_fixture(cells=2, interface_areas=(0.0, 0.0))
    before = node.conservation()["initial"]
    before_chambers = (node.crankcase.inventory(E), node.cylinder.inventory(E))
    for _ in range(10):
        trace = node.step(1.0e-6)
        for stage in trace["stages"]:
            assert stage["closed"] == (True, True)
            assert stage["interfaces"] == ((0.0, 0.0, 0.0, 0.0),) * 2
        assert node.crankcase.inventory(E) == pytest.approx(before_chambers[0])
        assert node.cylinder.inventory(E) == pytest.approx(before_chambers[1])
    assert node.conservation()["delta"]["mass"] == pytest.approx(0.0, abs=1.0e-15)
    assert node.mass_ledger()["residual"] == pytest.approx(0.0, abs=1.0e-15)
    assert node.species_ledger()["residual"] == pytest.approx(0.0, abs=1.0e-15)


def test_one_transfer_volume_rates_use_contractual_work_without_external_energy():
    """Small opposing work must pass the unchanged 1e-12 ledger gate.

    This deliberately runs several steps so the observed increment is much
    smaller than the stored chamber/duct inventories.  The fixture must audit
    that increment component-wise rather than subtracting two global totals.
    """
    node = make_one_transfer_fixture(
        cells=2, volume_rates=(-1.0e-4, 1.0e-4), interface_areas=(0.0, 0.0))
    initial = node.conservation()["initial"]
    for _ in range(10):
        node.step(1.0e-6)
        assert node.admissible()
    mass = node.mass_ledger()
    species = node.species_ledger()
    energy = node.energy_ledger()
    assert mass["delta_mass"] == pytest.approx(0.0, abs=1.0e-15)
    assert species["delta_species"] == pytest.approx(0.0, abs=1.0e-15)
    assert energy["external_energy"] == 0.0
    # The strict gate applies to the stage quadrature, not to subtracting
    # large stored chamber energies after ten accepted updates.
    assert energy["applied_delta_energy"] == pytest.approx(
        energy["chamber_work"], abs=1.0e-12)
    assert energy["integration_residual"] == pytest.approx(0.0, abs=1.0e-12)
    assert energy["state_delta_energy"] == energy["delta_energy"]
    assert abs(energy["state_roundoff"]) <= energy["state_roundoff_bound"]
    assert abs(energy["stored_balance_roundoff"]) <= energy["stored_balance_roundoff_bound"]
    assert energy["accepted_updates"] == 10
    assert energy["state_roundoff_bound"] > 0.0
    assert mass["applied_delta_mass"] == pytest.approx(0.0, abs=1.0e-15)
    assert mass["integration_residual"] == pytest.approx(0.0, abs=1.0e-15)
    assert species["applied_delta_species"] == pytest.approx(0.0, abs=1.0e-15)
    assert species["integration_residual"] == pytest.approx(0.0, abs=1.0e-15)
    assert energy["stored_balance_roundoff"] == (
        node.conservation()["final"]["energy"] -
        (initial["energy"] + energy["chamber_work"]))


def test_single_0d1d_fixture_validates_chamber_as_extensive_inventory():
    eos = IdealGas()
    node = make_single_0d1d_fixture(eos=eos, cells=1)
    state = node._state()
    calls = []
    chamber_state = p5b.ChamberState

    def record_chamber_state(*args):
        calls.append(args)
        return chamber_state(*args)

    with patch.object(p5b, 'ChamberState', side_effect=record_chamber_state):
        node._validate_state(state)

    assert calls == [(
        state[0][0],
        state[0][2],
        state[0][3],
        node.chamber.volume,
    )]


def test_two_transfer_fixture_resolves_four_interfaces_once_per_stage_and_reuses_flux():
    node = make_two_transfer_fixture(cells=2)
    calls = []
    original = p5b.interface_exchange

    def audited(chamber, interior, area, normal, *, eos):
        result = original(chamber, interior, area, normal, eos=eos)
        calls.append((interior, area, normal, tuple(result["outward"])))
        return result

    with patch.object(p5b, "interface_exchange", side_effect=audited):
        trace = node.step(1.0e-7)
    assert isinstance(node, TwoTransferFixture)
    assert len(calls) == 8
    assert [item[2] for item in calls] == [-1, 1, -1, 1] * 2
    for stage in trace["stages"]:
        for transfer in stage["transfers"]:
            left, right = transfer["interfaces"]
            assert transfer["face_fluxes"][0] == tuple(-x for x in left)
            assert transfer["face_fluxes"][-1] == right


def test_two_transfer_symmetric_paths_match_without_aliasing_and_conserve():
    node = make_two_transfer_fixture(cells=3)
    assert node.transfers[0] is not node.transfers[1]
    assert node.transfers[0].duct_states is not node.transfers[1].duct_states
    assert node.transfers[0].history is not node.transfers[1].history
    initial = node.conservation()["initial"]
    for _ in range(8):
        trace = node.step(1.0e-7)
        for stage in trace["stages"]:
            a, b = stage["transfers"]
            for left, right in zip(a["interfaces"], b["interfaces"]):
                assert left == pytest.approx(right, abs=1.0e-15)
            for faces_a, faces_b in zip(a["face_fluxes"], b["face_fluxes"]):
                assert faces_a == pytest.approx(faces_b, abs=1.0e-15)
        assert node.admissible()
    audit = node.conservation()
    for key in ("mass", "species", "energy"):
        assert audit["final"][key] == pytest.approx(initial[key], abs=2.0e-10)
    assert node.mass_ledger()["integration_residual"] == pytest.approx(0.0, abs=1.0e-15)
    assert node.species_ledger()["integration_residual"] == pytest.approx(0.0, abs=1.0e-15)
    energy = node.energy_ledger()
    assert energy["applied_delta_energy"] == pytest.approx(0.0, abs=1.0e-12)
    assert energy["integration_residual"] == pytest.approx(0.0, abs=1.0e-12)
    assert abs(energy["stored_balance_roundoff"]) <= energy["stored_balance_roundoff_bound"]


def test_two_transfer_asymmetric_paths_remain_independent_and_distinct():
    left = tuple((1.0, 0.0, 104000.0, 0.2) for _ in range(3))
    right = tuple((0.8, 12.0, 92000.0, 0.7) for _ in range(3))
    node = make_two_transfer_fixture(cells=3, transfer_states=(left, right))
    original_right = tuple(cell.conservative for cell in node.transfers[1].duct_states)
    node.step(1.0e-7)
    first = node.history[-1]["stages"][0]["transfers"]
    assert any(left != pytest.approx(right, abs=1.0e-12)
               for left, right in zip(first[0]["interfaces"], first[1]["interfaces"]))
    assert tuple(cell.conservative for cell in node.transfers[1].duct_states) != original_right
    assert node.transfers[0].duct_states[0] is not node.transfers[1].duct_states[0]
    assert node.admissible()


def test_two_transfer_closed_interfaces_are_exact_zero_and_work_is_stage_accounted():
    node = make_two_transfer_fixture(cells=2, volume_rates=(-1.0e-4, 1.0e-4),
                                     interface_areas=((0.0, 0.0), (0.0, 0.0)))
    initial_chambers = (node.crankcase.inventory(E), node.cylinder.inventory(E))
    for _ in range(10):
        trace = node.step(1.0e-6)
        for stage in trace["stages"]:
            for transfer in stage["transfers"]:
                assert transfer["closed"] == (True, True)
                assert transfer["interfaces"] == ((0.0, 0.0, 0.0, 0.0),) * 2
        assert node.admissible()
    assert node.crankcase.inventory(E)[0] == pytest.approx(initial_chambers[0][0])
    assert node.cylinder.inventory(E)[0] == pytest.approx(initial_chambers[1][0])
    mass = node.mass_ledger()
    species = node.species_ledger()
    energy = node.energy_ledger()
    assert mass["integration_residual"] == pytest.approx(0.0, abs=1.0e-15)
    assert species["integration_residual"] == pytest.approx(0.0, abs=1.0e-15)
    assert energy["applied_delta_energy"] == pytest.approx(energy["chamber_work"], abs=1.0e-12)
    assert energy["integration_residual"] == pytest.approx(0.0, abs=1.0e-12)
    assert abs(energy["stored_balance_roundoff"]) <= energy["stored_balance_roundoff_bound"]
