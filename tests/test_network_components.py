import math

import pytest

from motorsim.gas1d.eos import IdealGas
from motorsim.network_components import (
    Atmosphere,
    NetworkConnection,
    NetworkTopology,
    VolumeGasState,
    VolumeNode,
    helmholtz_frequency_hz,
    resolve_volume_duct_interface,
)


def node_state(*, fresh_fraction=0.2, pressure=100_000.0, volume=0.001):
    eos = IdealGas()
    mass = pressure * volume / (eos.R * 300.0)
    energy = pressure * volume / (eos.gamma - 1.0)
    return VolumeGasState(mass, energy,
                          (mass * fresh_fraction, 0.0,
                           mass * (1 - fresh_fraction), 0.0))


def test_topology_serialization_and_multiple_network_volumes():
    topology = NetworkTopology(
        (VolumeNode("airbox", "airbox", 0.01, "DOCUMENTED"),
         VolumeNode("bottle", "boost_bottle", 0.0002, "SYNTHETIC_ASSUMPTION")),
        (NetworkConnection("ambient", "atmosphere", "airbox", 0.0004, 0.02, "DOCUMENTED"),
         NetworkConnection("neck", "airbox", "bottle", 0.0001, 0.08, "UNKNOWN"),
         NetworkConnection("case", "bottle", "crankcase", 0.0002, 0.03, "DOCUMENTED")),
    )
    assert NetworkTopology.from_dict(topology.to_dict()) == topology
    with pytest.raises(ValueError, match="Unknown"):
        NetworkTopology(topology.volumes,
                        (NetworkConnection("bad", "missing", "airbox", 1e-4, 0.02,
                                           "DOCUMENTED"),)).validate()


def test_atmosphere_uses_explicit_default_four_species_composition():
    gas = IdealGas()
    state = Atmosphere(101_325.0, 288.15).primitive(gas)
    assert state == pytest.approx((101325 / (gas.R * 288.15), 0, 101325, 1))
    mixed = Atmosphere(101325, 300, (0.9, 0.1, 0, 0)).primitive(gas)
    assert mixed[3] == pytest.approx(1.0)
    with pytest.raises(ValueError):
        Atmosphere(101325, 300, (True, 0, 0, 0)).primitive(gas)


def test_shared_riemann_exchange_uses_actual_species_donor_and_conserves():
    volume = node_state(fresh_fraction=0.2, pressure=100_000)
    duct_in = (1.0, 0.0, 150_000.0, 1.0)
    incoming = resolve_volume_duct_interface(volume, 0.001, duct_in,
        (0.0, 1.0, 0.0, 0.0), 1e-4, -1)
    assert incoming.mass_into_volume_kg_s > 0
    assert sum(incoming.species_into_volume_kg_s) == pytest.approx(incoming.mass_into_volume_kg_s)
    assert incoming.species_into_volume_kg_s[1] == pytest.approx(incoming.mass_into_volume_kg_s)

    updated, pipe = incoming.apply(volume, 1e-6)
    assert updated.mass_kg + pipe["mass_kg"] == pytest.approx(volume.mass_kg)
    assert updated.internal_energy_j + pipe["energy_j"] == pytest.approx(volume.internal_energy_j)
    for initial, after, opposite in zip(volume.species_mass_kg,
                                        updated.species_mass_kg,
                                        pipe["species_mass_kg"]):
        assert after + opposite == pytest.approx(initial)
    assert sum(updated.species_mass_kg) == pytest.approx(updated.mass_kg)


def test_reverse_interface_uses_volume_composition_as_donor():
    volume = node_state(fresh_fraction=0.75, pressure=150_000)
    duct_out = (1.0, 0.0, 100_000.0, 0.1)
    exchange = resolve_volume_duct_interface(volume, 0.001, duct_out,
        (0.1, 0.0, 0.9, 0.0), 1e-4, -1)
    assert exchange.mass_into_volume_kg_s < 0
    assert exchange.species_into_volume_kg_s[0] / exchange.mass_into_volume_kg_s == pytest.approx(0.75)
    assert exchange.species_into_volume_kg_s[2] / exchange.mass_into_volume_kg_s == pytest.approx(0.25)


def test_lumped_helmholtz_estimate_uses_explicit_effective_length():
    gas = IdealGas()
    value = helmholtz_frequency_hz(0.001, 1e-4, 0.1, 300.0, eos=gas)
    expected = math.sqrt(gas.gamma * gas.R * 300) / (2 * math.pi) * math.sqrt(1e-4 / (0.001 * 0.1))
    assert value == pytest.approx(expected)
    with pytest.raises(ValueError):
        helmholtz_frequency_hz(0.001, 1e-4, 0, 300)


@pytest.mark.parametrize("state", [
    VolumeGasState(0, 1, (0, 0, 0, 0)),
    VolumeGasState(1, 1, (True, 0, 0, 0)),
    VolumeGasState(1, math.nan, (1, 0, 0, 0)),
])
def test_invalid_volume_gas_states_are_rejected(state):
    with pytest.raises(ValueError):
        state.validate()
