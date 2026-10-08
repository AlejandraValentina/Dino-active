"""Reusable 0D network volumes, declared necks and conservative interfaces."""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any

from .coupling import ChamberState, interface_flux
from .gas1d.eos import IdealGas
from .p6_species import donor_species, validate_species

SCHEMA = "MOTORSIM_NETWORK_COMPONENTS_V1"
VOLUME_KINDS = {"plenum", "airbox", "boost_bottle"}
SPECIES = ("fresh_air", "fuel", "residual", "burned")
PROVENANCE = {"DOCUMENTED", "DERIVED_FROM_DOCUMENTED", "SYNTHETIC_ASSUMPTION", "UNKNOWN"}


def _finite(value: Any, label: str) -> float:
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError(f"{label} must be finite numeric data, excluding booleans")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{label} outside supported range")
    return result


def _species(values, mass):
    if (not isinstance(values, (tuple, list)) or len(values) != 4 or
            any(type(value) not in (int, float) or not math.isfinite(value)
                for value in values)):
        raise ValueError("Four finite species values are required; booleans are invalid")
    return validate_species(values, mass)


@dataclass(frozen=True)
class VolumeNode:
    id: str
    kind: str
    volume_m3: float
    provenance: str

    def validate(self):
        if not isinstance(self.id, str) or not self.id.strip() or self.kind not in VOLUME_KINDS:
            raise ValueError("Network volume id/kind is invalid")
        if _finite(self.volume_m3, "volume_m3") <= 0:
            raise ValueError("Network volume must be positive")
        if not isinstance(self.provenance, str) or self.provenance not in PROVENANCE:
            raise ValueError("Network volume provenance is invalid")

    def to_dict(self):
        self.validate()
        return {"id": self.id, "kind": self.kind, "volume_m3": self.volume_m3,
                "provenance": self.provenance}

    @classmethod
    def from_dict(cls, value):
        if not isinstance(value, dict) or set(value) != {"id", "kind", "volume_m3", "provenance"}:
            raise ValueError("Network volume schema is invalid")
        result = cls(**value)
        result.validate()
        return result


@dataclass(frozen=True)
class NetworkConnection:
    id: str
    upstream: str
    downstream: str
    area_m2: float
    effective_length_m: float
    provenance: str

    def validate(self):
        if not isinstance(self.id, str) or not self.id.strip():
            raise ValueError("Network connection id is required")
        if (not isinstance(self.upstream, str) or not self.upstream.strip() or
                not isinstance(self.downstream, str) or not self.downstream.strip() or
                self.upstream == self.downstream):
            raise ValueError("Network connection endpoints are invalid")
        for name in ("area_m2", "effective_length_m"):
            if _finite(getattr(self, name), name) <= 0:
                raise ValueError(f"{name} must be positive")
        if not isinstance(self.provenance, str) or self.provenance not in PROVENANCE:
            raise ValueError("Network connection provenance is invalid")

    def to_dict(self):
        self.validate()
        return {"id": self.id, "upstream": self.upstream, "downstream": self.downstream,
                "area_m2": self.area_m2, "effective_length_m": self.effective_length_m,
                "provenance": self.provenance}

    @classmethod
    def from_dict(cls, value):
        fields = {"id", "upstream", "downstream", "area_m2", "effective_length_m", "provenance"}
        if not isinstance(value, dict) or set(value) != fields:
            raise ValueError("Network connection schema is invalid")
        result = cls(**value)
        result.validate()
        return result


@dataclass(frozen=True)
class NetworkTopology:
    volumes: tuple[VolumeNode, ...]
    connections: tuple[NetworkConnection, ...]

    def validate(self):
        if not isinstance(self.volumes, tuple) or not isinstance(self.connections, tuple):
            raise ValueError("Network topology collections must be tuples")
        if any(not isinstance(item, VolumeNode) for item in self.volumes):
            raise ValueError("Invalid network volume")
        if any(not isinstance(item, NetworkConnection) for item in self.connections):
            raise ValueError("Invalid network connection")
        for item in self.volumes:
            item.validate()
        for item in self.connections:
            item.validate()
        volume_ids = [item.id for item in self.volumes]
        connection_ids = [item.id for item in self.connections]
        if len(set(volume_ids)) != len(volume_ids) or len(set(connection_ids)) != len(connection_ids):
            raise ValueError("Network ids must be unique")
        endpoints = set(volume_ids) | {"atmosphere", "crankcase", "cylinder", "exhaust"}
        for item in self.connections:
            if item.upstream not in endpoints or item.downstream not in endpoints:
                raise ValueError(f"Unknown network connection endpoint in {item.id}")

    def to_dict(self):
        self.validate()
        return {"schema": SCHEMA,
                "volumes": [item.to_dict() for item in self.volumes],
                "connections": [item.to_dict() for item in self.connections]}

    @classmethod
    def from_dict(cls, value):
        if (not isinstance(value, dict) or set(value) != {"schema", "volumes", "connections"}
                or value["schema"] != SCHEMA or not isinstance(value["volumes"], list)
                or not isinstance(value["connections"], list)):
            raise ValueError("Network topology schema is invalid")
        result = cls(tuple(VolumeNode.from_dict(row) for row in value["volumes"]),
                     tuple(NetworkConnection.from_dict(row) for row in value["connections"]))
        result.validate()
        return result


@dataclass(frozen=True)
class Atmosphere:
    pressure_pa: float
    temperature_K: float
    species_fraction: tuple[float, float, float, float] = (1.0, 0.0, 0.0, 0.0)

    def primitive(self, eos: IdealGas | None = None) -> tuple[float, float, float, float]:
        gas = eos or IdealGas()
        pressure = _finite(self.pressure_pa, "atmosphere.pressure_pa")
        temperature = _finite(self.temperature_K, "atmosphere.temperature_K")
        if pressure <= 0 or temperature <= 0:
            raise ValueError("Atmosphere pressure and temperature must be positive")
        fractions = _species(self.species_fraction, 1.0)
        fresh_fraction = fractions[0] + fractions[1]
        state = (pressure / (gas.R * temperature), 0.0, pressure, fresh_fraction)
        return gas.validate(state)


@dataclass(frozen=True)
class VolumeGasState:
    mass_kg: float
    internal_energy_j: float
    species_mass_kg: tuple[float, float, float, float]

    def validate(self):
        mass = _finite(self.mass_kg, "volume.mass_kg")
        energy = _finite(self.internal_energy_j, "volume.internal_energy_j")
        if mass <= 0 or energy <= 0:
            raise ValueError("Network gas volume mass and energy must be positive")
        species = _species(self.species_mass_kg, mass)
        return species

    def chamber(self, volume_m3: float) -> ChamberState:
        species = self.validate()
        volume = _finite(volume_m3, "volume_m3")
        if volume <= 0:
            raise ValueError("Volume must be positive")
        return ChamberState(self.mass_kg, self.internal_energy_j,
                            species[0] + species[1], volume)

    def primitive(self, volume_m3: float, eos: IdealGas | None = None):
        gas = eos or IdealGas()
        chamber = self.chamber(volume_m3)
        rho, pressure, temperature, fresh = chamber.thermodynamics(gas)
        return (rho, 0.0, pressure, fresh)


@dataclass(frozen=True)
class NetworkExchange:
    mass_into_volume_kg_s: float
    energy_into_volume_w: float
    species_into_volume_kg_s: tuple[float, float, float, float]
    axial_impulse_into_volume_n: float
    fallback_reason: str | None
    wave_speeds: tuple[float, float, float]

    def apply(self, state: VolumeGasState, dt_s: float):
        dt = _finite(dt_s, "dt_s")
        if dt <= 0:
            raise ValueError("dt_s must be positive")
        rates = (self.mass_into_volume_kg_s, self.energy_into_volume_w,
                 self.axial_impulse_into_volume_n, *self.species_into_volume_kg_s)
        if len(self.species_into_volume_kg_s) != 4 or any(
                type(value) not in (int, float) or not math.isfinite(value) for value in rates):
            raise ValueError("Network exchange rates must be finite")
        species = state.validate()
        next_mass = state.mass_kg + dt * self.mass_into_volume_kg_s
        next_energy = state.internal_energy_j + dt * self.energy_into_volume_w
        next_species = tuple(value + dt * rate for value, rate in
                             zip(species, self.species_into_volume_kg_s))
        validate_species(next_species, next_mass)
        if (not math.isfinite(next_mass) or not math.isfinite(next_energy) or
                next_mass <= 0 or next_energy <= 0):
            raise ValueError("Network exchange produced inadmissible volume state")
        updated = VolumeGasState(next_mass, next_energy, next_species)
        # Exact opposite increments for the adjacent finite volume.
        pipe = {"mass_kg": -dt * self.mass_into_volume_kg_s,
                "energy_j": -dt * self.energy_into_volume_w,
                "species_mass_kg": tuple(-dt * value for value in self.species_into_volume_kg_s)}
        return updated, pipe


def resolve_volume_duct_interface(volume_state: VolumeGasState, volume_m3: float,
                                  duct_primitive: tuple, duct_species_fraction: tuple,
                                  area_m2: float, normal: int, *,
                                  eos: IdealGas | None = None) -> NetworkExchange:
    """Reuse one P3 Riemann interface and actual four-species donor fractions.

    The returned rates are positive INTO the 0D volume; the finite-volume
    partner must receive their exact negatives at the same SSPRK stage.
    """
    gas = eos or IdealGas()
    area = _finite(area_m2, "area_m2")
    if area <= 0:
        raise ValueError("Interface area must be positive")
    duct = gas.validate(tuple(_finite(value, "duct_primitive") for value in duct_primitive))
    pipe_species = _species(duct_species_fraction, 1.0)
    volume_species = volume_state.validate()
    chamber = volume_state.chamber(volume_m3)
    flux = interface_flux(chamber, duct, area, normal, eos=gas)
    mass_into = flux.outward[0]
    species_into = donor_species(mass_into, pipe_species, volume_species)
    return NetworkExchange(mass_into, flux.outward[2], species_into,
                           flux.outward[1], flux.fallback_reason,
                           flux.wave_speeds)


def helmholtz_frequency_hz(volume_m3: float, neck_area_m2: float,
                           effective_neck_length_m: float,
                           temperature_K: float, *, eos: IdealGas | None = None) -> float:
    """Lumped resonance estimate; caller supplies effective neck length."""
    volume = _finite(volume_m3, "volume_m3")
    area = _finite(neck_area_m2, "neck_area_m2")
    length = _finite(effective_neck_length_m, "effective_neck_length_m")
    temperature = _finite(temperature_K, "temperature_K")
    if min(volume, area, length, temperature) <= 0:
        raise ValueError("Helmholtz geometry and temperature must be positive")
    gas = eos or IdealGas()
    sound_speed = math.sqrt(gas.gamma * gas.R * temperature)
    frequency = sound_speed / (2 * math.pi) * math.sqrt(area / (volume * length))
    if not math.isfinite(frequency) or frequency <= 0:
        raise ValueError("Helmholtz estimate outside supported range")
    return frequency
