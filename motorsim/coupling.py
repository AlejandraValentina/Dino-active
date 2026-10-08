"""Isolated P3 interfaces. P3-R1 uses the frozen Euler Riemann kernel.

The old prescribed-reservoir diagnostic remains explicitly named and separate.
"""
from dataclasses import dataclass
from math import isfinite

from .gas1d.boundary import Boundary
from .gas1d.eos import IdealGas, InvalidState
from .gas1d.riemann import hllc_flux


@dataclass(frozen=True)
class ChamberState:
    mass: float
    internal_energy: float
    fresh_mass: float
    volume: float

    def thermodynamics(self, eos: IdealGas):
        if not all(isfinite(x) for x in (self.mass, self.internal_energy, self.fresh_mass, self.volume)):
            raise InvalidState('Nonfinite chamber state')
        if min(self.mass, self.internal_energy, self.volume) <= 0 or not 0 <= self.fresh_mass <= self.mass:
            raise InvalidState('Inadmissible chamber state')
        rho = self.mass / self.volume
        pressure = (eos.gamma - 1) * self.internal_energy / self.volume
        temperature = self.internal_energy / (self.mass * eos.cv)
        fraction = self.fresh_mass / self.mass
        eos.validate((rho, 0., pressure, fraction))
        return rho, pressure, temperature, fraction


@dataclass(frozen=True)
class SharedFlux:
    face_state: tuple
    outward: tuple  # mass, axial momentum, total energy, fresh mass; outside pipe
    donor: str

    def increments(self, dt):
        """One flux integral, opposite signs. Not a time integration scheme."""
        if not isfinite(dt) or dt < 0:
            raise ValueError('Invalid dt')
        transfer = tuple(dt * self.outward[k] for k in (0, 2, 3))
        return dict(chamber=transfer, pipe=tuple(-x for x in transfer),
                    outward_axial_impulse=dt*self.outward[1])


def prescribed_reservoir_flux(chamber, interior, area, normal, *, eos=None):
    eos = eos or IdealGas()
    if normal not in (-1, 1) or not isfinite(area) or area <= 0:
        raise ValueError('Invalid interface area/normal')
    _, pressure, temperature, fraction = chamber.thermodynamics(eos)
    boundary = Boundary('reservoir', p0=pressure, T0=temperature, Y0=fraction)
    face = boundary.face_state(interior, normal, eos)
    # No second Riemann problem or second boundary condition at this face.
    outward = tuple(normal * area * f for f in eos.flux(face))
    donor = 'pipe' if outward[0] > 0 else ('chamber' if outward[0] < 0 else 'none')
    return SharedFlux(face, outward, donor)


@dataclass(frozen=True)
class RiemannExchange:
    flux_x: tuple
    outward: tuple
    wave_speeds: tuple
    fallback_reason: str | None

    def increments(self, dt):
        if not isfinite(dt) or dt < 0:
            raise ValueError('Invalid dt')
        transfer = tuple(dt*self.outward[k] for k in (0, 2, 3))
        return dict(chamber=transfer, pipe=tuple(-x for x in transfer),
                    interface_axial_impulse=dt*self.outward[1])


def interface_flux(chamber, interior, area, normal, *, eos=None):
    """One Riemann problem; direction is an output, never an input branch.

    Flux_x follows the pipe's x axis. Normal points OUT of the pipe.
    The chamber receives normal*area*EulerFlux components mass/energy/species.
    Its macroscopic velocity is zero; the interface force does no wall work.
    """
    eos = eos or IdealGas()
    if normal not in (-1, 1) or not isfinite(area) or area <= 0:
        raise ValueError('Invalid interface area/normal')
    rho, pressure, _, fraction = chamber.thermodynamics(eos)
    stagnant = eos.validate((rho, 0., pressure, fraction))
    left, right = (stagnant, interior) if normal == -1 else (interior, stagnant)
    flux, speeds, reason = hllc_flux(left, right, eos)
    scaled = tuple(area*f for f in flux)
    return RiemannExchange(scaled, tuple(normal*f for f in scaled), speeds, reason)
