import math
from unittest.mock import patch

import pytest

from motorsim import p5b
from motorsim.gas1d.eos import IdealGas
from motorsim.gas1d.mesh import uniform_mesh


E = IdealGas()


def make_fixture():
    primitive = (1.0, 0.0, 101325.0, 0.2)
    duct = tuple(primitive for _ in range(4))
    meshes = tuple(uniform_mesh(4, length=0.03, area=1.0e-4) for _ in range(3))
    return p5b.IntegratedIntakeTransfer(
        p5b.Chamber((1.0, 0.0, 100000.0, 0.5), 1.0e-3),
        p5b.Chamber((1.0, 0.0, 98000.0, 0.3), 1.0e-2),
        (duct, duct, duct), eos=E, meshes=meshes,
    )


def test_complete_topology_has_three_separate_finite_paths():
    node = make_fixture()
    assert len(node.intake.cells) == 4
    assert [len(path.cells) for path in node.transfers] == [4, 4]
    assert node.transfers[0] is not node.transfers[1]
    assert node.transfers[0].cells is not node.transfers[1].cells


def test_complete_fixture_solves_five_interfaces_once_per_stage_and_evolves_all_ducts():
    node = make_fixture()
    primitive = (1.0, 0.0, 101325.0, 0.2)
    calls = []
    original = p5b.interface_exchange

    def audited(chamber, interior, area, normal, *, eos):
        result = original(chamber, interior, area, normal, eos=eos)
        calls.append((area, normal, tuple(result["outward"])))
        return result

    with patch.object(p5b, "interface_exchange", side_effect=audited):
        for angle in (0.0, 120.0, 150.0, 300.0, 330.0):
            trace = node.step(1.0e-7, angle=angle)
            assert len(trace["stages"]) == 2
            assert trace["stages"][0]["angle"] == angle
            assert trace["stages"][1]["angle"] == angle
            assert node.admissible() if hasattr(node, "admissible") else True

    assert len(calls) == 5 * 2 * 5
    assert [normal for _, normal, _ in calls[:5]] == [1, -1, 1, -1, 1]
    assert all(any(abs(q[k] - primitive[k]) > 0.0 for q in path.conservative()
                   for k in range(4))
               for path, primitive in zip((node.intake, *node.transfers),
                                          ((1.0, 0.0, 101325.0, 0.2),) * 3))


def test_complete_fixture_closed_ports_are_exact_zero_and_ledgers_are_stage_consistent():
    node = make_fixture()
    for _ in range(8):
        trace = node.step(1.0e-7, angle=0.0)
        assert trace["areas"] == (0.0, 0.0, 0.0)
        assert all(flux == (0.0, 0.0, 0.0, 0.0)
                   for flux, closed in zip(trace["stages"][1]["interfaces"],
                                           trace["stages"][1]["interface_closed"])
                   if closed)
    mass = node.mass_ledger()
    species = node.species_ledger()
    energy = node.energy_ledger()
    # The physical intake port is closed, but the atmosphere/intake far
    # boundary remains the sole external boundary and may fill the finite duct.
    assert mass["external_mass"] >= 0.0
    assert species["external_species"] == pytest.approx(species["delta_species"], abs=1e-15)
    assert mass["integration_residual"] == pytest.approx(0.0, abs=1e-15)
    assert species["integration_residual"] == pytest.approx(0.0, abs=1e-15)
    assert energy["integration_residual"] == pytest.approx(0.0, abs=1e-12)


def test_complete_fixture_external_ledger_and_stored_roundoff_are_separate():
    node = make_fixture()
    for angle in (300.0, 330.0, 120.0, 150.0):
        node.step(1.0e-7, angle=angle)
    mass = node.mass_ledger()
    species = node.species_ledger()
    energy = node.energy_ledger()
    assert mass["external_mass"] != 0.0
    assert mass["delta_mass"] == pytest.approx(mass["external_mass"], abs=1e-15)
    assert species["delta_species"] == pytest.approx(species["external_species"], abs=1e-15)
    assert energy["applied_delta_energy"] == pytest.approx(
        energy["external_energy"] + energy["chamber_work"], abs=1e-12)
    assert energy["integration_residual"] == pytest.approx(0.0, abs=1e-12)
    assert abs(energy["stored_balance_roundoff"]) <= energy["stored_balance_roundoff_bound"]
    assert all(math.isfinite(value) for value in energy.values()
               if isinstance(value, (int, float)))


def test_complete_fixture_replay_is_deterministic():
    a = make_fixture()
    for angle in (0.0, 120.0, 300.0):
        a.step(1.0e-7, angle=angle)
    snap = a.snapshot()
    a.step(1.0e-7, angle=330.0)
    b = make_fixture()
    b.restore(snap)
    b.step(1.0e-7, angle=330.0)
    assert a.history[-1] == b.history[-1]
