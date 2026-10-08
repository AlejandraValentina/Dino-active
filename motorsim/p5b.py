"""Minimal integrated intake/transfer fixture for conditional P5-B.

Composes P5-A interfaces; exhaust and periodic engine operation are absent.
"""
from dataclasses import dataclass
from copy import deepcopy
from math import fsum, isfinite
import sys
from .duct_network import interface_exchange
from .coupling import ChamberState, interface_flux
from .gas1d.boundary import Boundary
from .gas1d.eos import IdealGas
from .gas1d.mesh import uniform_mesh
from .gas1d.riemann import hllc_flux


def interior_rhs(mesh, states, eos=None):
    """Interior finite-volume RHS using the existing HLLC core."""
    eos = eos or IdealGas()
    if len(states) != mesh.n:
        raise ValueError("state/mesh size mismatch")
    fluxes = [hllc_flux(a, b, eos)[0] for a, b in zip(states, states[1:])]
    rhs = []
    for i in range(mesh.n):
        left = fluxes[i-1] if i else (0., 0., 0., 0.)
        right = fluxes[i] if i < len(fluxes) else (0., 0., 0., 0.)
        rhs.append(tuple(-(right[k]-left[k])/mesh.volumes[i] for k in range(4)))
    return tuple(rhs)


def ssprk2_step(state, rhs, dt):
    """Generic two-stage SSPRK2 update for a global tuple state."""
    z1 = tuple(x + dt*r for x, r in zip(state, rhs(state)))
    r1 = rhs(z1)
    return tuple(.5*(x + y + dt*r) for x, y, r in zip(state, z1, r1))


@dataclass
class Chamber:
    primitive: tuple
    volume: float

    def inventory(self, eos):
        rho,u,p,y = eos.validate(self.primitive)
        mass = rho*self.volume
        return (mass, mass*y, p*self.volume/(eos.gamma-1))

    def thermodynamics(self, eos):
        rho,u,p,y = eos.validate(self.primitive)
        return rho, p, p/(rho*eos.R), y

    def conservative_rhs(self, outward_fluxes, eos, volume_rate=0.0):
        """Return the chamber RHS for one common interface stage.

        ``outward_fluxes`` are all expressed with the chamber-outward sign
        convention.  The interface solves therefore happen against the same
        stage state and their conservative contributions are summed before
        changing the chamber.  The only non-flux energy source is the
        contractual closed-system work term ``-p*dV/dt``.
        """
        if not all(len(flux) == 4 and all(isfinite(value) for value in flux)
                   for flux in outward_fluxes):
            raise ValueError("invalid chamber flux")
        _, pressure, _, _ = self.thermodynamics(eos)
        if not isinstance(volume_rate, (int, float)) or not isfinite(volume_rate):
            raise ValueError("invalid volume rate")
        mass = sum(flux[0] for flux in outward_fluxes)
        energy = sum(flux[2] for flux in outward_fluxes) - pressure*volume_rate
        species = sum(flux[3] for flux in outward_fluxes)
        return mass, energy, species

    def apply_rhs(self, rhs, dt, eos, volume_rate=0.0):
        """Apply one already assembled chamber stage and update its volume."""
        if (not isinstance(dt, (int, float)) or not isfinite(dt) or dt <= 0
                or not isinstance(volume_rate, (int, float))
                or not isfinite(volume_rate)):
            raise ValueError("dt must be positive")
        if len(rhs) != 3 or not all(isfinite(value) for value in rhs):
            raise ValueError("invalid chamber rhs")
        old_volume = self.volume
        new_volume = old_volume + dt*volume_rate
        if new_volume <= 0:
            raise ValueError("NUMERICAL_FAILURE: nonpositive chamber volume")
        mass, species, energy = self.inventory(eos)
        mass += dt*rhs[0]
        energy += dt*rhs[1]
        species += dt*rhs[2]
        if mass <= 0 or not 0 <= species <= mass or energy <= 0:
            raise ValueError("NUMERICAL_FAILURE: inadmissible chamber update")
        self.volume = new_volume
        self.primitive = (mass/new_volume, 0.0,
                          (eos.gamma-1)*energy/new_volume, species/mass)

    def apply_exchange(self, flux, dt, eos, work=0.0):
        """Apply one outward chamber flux; mass/energy/species are conserved."""
        if not isinstance(dt, (int, float)) or not isfinite(dt) or dt <= 0:
            raise ValueError("dt must be positive")
        if not isinstance(work, (int, float)) or not isfinite(work):
            raise ValueError("invalid work")
        self.apply_rhs((flux[0], flux[2] + work/dt, flux[3]), dt, eos)

@dataclass
class DuctCell:
    conservative: tuple
    volume: float

    def primitive(self, eos):
        return eos.primitive(self.conservative)

    def apply_flux(self, flux, dt, eos, sign=1.0):
        q = tuple(self.conservative[i] + sign*dt*flux[i]/self.volume for i in range(4))
        eos.primitive(q)
        self.conservative = q


class Single0D1DFixture:
    """Finite, externally closed chamber-to-duct P5-B fixture.

    The chamber is a fixed-volume, stagnant 0-D control volume.  The duct is
    a finite-volume 1-D mesh with a closed wall at its far end.  The chamber
    interface is solved once per SSPRK2 stage; the exact same extensive flux
    is added to the chamber and subtracted from the first duct cell.
    """

    def __init__(self, chamber, duct_states, *, mesh=None, eos=None):
        self.eos = eos or IdealGas()
        self.mesh = mesh or uniform_mesh(len(duct_states), length=0.03, area=1.0e-4)
        if len(duct_states) != self.mesh.n:
            raise ValueError("state/mesh size mismatch")
        if chamber.volume <= 0 or not isfinite(chamber.volume):
            raise ValueError("invalid chamber volume")
        self.chamber = chamber
        self.duct_states = [
            state if isinstance(state, DuctCell)
            else DuctCell(self.eos.conservative(state), volume)
            for state, volume in zip(duct_states, self.mesh.volumes)
        ]
        self.history = []
        self._initial = self._totals()

    def _state(self):
        mass, species, energy = self.chamber.inventory(self.eos)
        return ((mass, 0.0, energy, species),
                tuple(cell.conservative for cell in self.duct_states))

    def _totals(self, state=None):
        if state is None:
            state = self._state()
        chamber, duct = state
        return {
            "mass": chamber[0] + sum(q[0] * v for q, v in zip(duct, self.mesh.volumes)),
            "energy": chamber[2] + sum(q[2] * v for q, v in zip(duct, self.mesh.volumes)),
            "species": chamber[3] + sum(q[3] * v for q, v in zip(duct, self.mesh.volumes)),
        }

    def _rhs(self, state):
        chamber_q, duct_q = state
        chamber = ChamberState(chamber_q[0], chamber_q[2], chamber_q[3], self.chamber.volume)
        duct_primitive = [self.eos.primitive_with_mass_fraction_roundoff(q)
                          for q in duct_q]
        shared = interface_flux(
            chamber, duct_primitive[0], self.mesh.areas[0], -1, eos=self.eos
        ).outward
        face_fluxes = [tuple(-value for value in shared)]
        for left, right, area in zip(duct_primitive, duct_primitive[1:], self.mesh.areas[1:]):
            face_fluxes.append(tuple(area * value for value in hllc_flux(left, right, self.eos)[0]))
        wall_flux = Boundary('wall').flux(duct_primitive[-1], 1, self.eos)[0]
        face_fluxes.append(tuple(self.mesh.areas[-1] * value for value in wall_flux))
        duct_rhs = []
        for index, volume in enumerate(self.mesh.volumes):
            left = face_fluxes[index]
            right = face_fluxes[index + 1]
            duct_rhs.append(tuple(-(right[k] - left[k]) / volume for k in range(4)))
        chamber_rhs = (shared[0], 0.0, shared[2], shared[3])
        return (chamber_rhs, tuple(duct_rhs)), shared, tuple(face_fluxes[1:-1])

    def _validate_state(self, state):
        chamber, duct = state
        ChamberState(chamber[0], chamber[2], chamber[3], self.chamber.volume).thermodynamics(self.eos)
        for q in duct:
            self.eos.primitive_with_mass_fraction_roundoff(q)

    @staticmethod
    def _combine(a, b, scale):
        return tuple(x + scale * y for x, y in zip(a, b))

    def step(self, dt):
        if not isinstance(dt, (int, float)) or not isfinite(dt) or dt <= 0:
            raise ValueError("dt must be positive")
        initial = self._state()
        rhs0, shared0, internal0 = self._rhs(initial)
        stage1 = (
            self._combine(initial[0], rhs0[0], dt),
            tuple(self._combine(q, r, dt) for q, r in zip(initial[1], rhs0[1])),
        )
        self._validate_state(stage1)
        rhs1, shared1, internal1 = self._rhs(stage1)
        final = (
            tuple(0.5 * (x + y + dt * r) for x, y, r in zip(initial[0], stage1[0], rhs1[0])),
            tuple(tuple(0.5 * (x + y + dt * r) for x, y, r in zip(q0, q1, r1))
                  for q0, q1, r1 in zip(initial[1], stage1[1], rhs1[1])),
        )
        self._validate_state(final)
        self.chamber.primitive = (
            final[0][0] / self.chamber.volume, 0.0,
            (self.eos.gamma - 1.0) * final[0][2] / self.chamber.volume,
            final[0][3] / final[0][0],
        )
        for cell, q in zip(self.duct_states, final[1]):
            cell.conservative = q
        trace = {
            "shared_fluxes": (shared0, shared1),
            "chamber_rhs": (rhs0[0], rhs1[0]),
            "duct_rhs": (rhs0[1], rhs1[1]),
            "internal_fluxes": (internal0, internal1),
            "totals": self._totals(),
        }
        self.history.append(trace)
        return trace

    def conservation(self):
        totals = self._totals()
        return {
            "initial": dict(self._initial),
            "final": totals,
            "delta": {key: totals[key] - self._initial[key] for key in totals},
        }

    def admissible(self):
        chamber, duct = self._state()
        ChamberState(chamber[0], chamber[2], chamber[3], self.chamber.volume).thermodynamics(self.eos)
        for q in duct:
            self.eos.primitive_with_mass_fraction_roundoff(q)
        return True


class OneTransferFixture:
    """Closed crankcase/transfer-duct/cylinder SSPRK2 fixture.

    Both ends of the finite duct are physical chamber interfaces.  There is
    deliberately no terminal wall: each interface is solved once from the
    stage state and the resulting extensive flux is used with the opposite
    sign in the adjacent duct cell.  Chamber volume rates use the same
    ``-p*dV/dt`` source as :class:`Chamber` and are evaluated at each stage.
    """

    def __init__(self, crankcase, cylinder, duct_states, *, mesh=None, eos=None,
                 volume_rates=(0.0, 0.0), interface_areas=None):
        self.eos = eos or IdealGas()
        if not isinstance(crankcase, Chamber) or not isinstance(cylinder, Chamber):
            raise TypeError("fixtures require Chamber instances")
        if not duct_states:
            raise ValueError("transfer duct needs at least one cell")
        self.mesh = mesh or uniform_mesh(len(duct_states), length=0.03, area=1.0e-4)
        if len(duct_states) != self.mesh.n:
            raise ValueError("state/mesh size mismatch")
        if (len(volume_rates) != 2 or
                not all(isinstance(x, (int, float)) and isfinite(x)
                        for x in volume_rates)):
            raise ValueError("invalid chamber volume rates")
        areas = (self.mesh.areas[0], self.mesh.areas[-1]) if interface_areas is None else tuple(interface_areas)
        if (len(areas) != 2 or
                not all(isinstance(x, (int, float)) and isfinite(x) and x >= 0 for x in areas)):
            raise ValueError("invalid interface areas")
        if crankcase.volume <= 0 or cylinder.volume <= 0:
            raise ValueError("invalid chamber volume")
        self.crankcase = crankcase
        self.cylinder = cylinder
        self.volume_rates = tuple(float(x) for x in volume_rates)
        self.interface_areas = tuple(float(x) for x in areas)
        self.duct_states = [
            state if isinstance(state, DuctCell) else DuctCell(self.eos.conservative(state), volume)
            for state, volume in zip(duct_states, self.mesh.volumes)
        ]
        self.history = []
        self.ledger = {"external_mass": 0.0, "external_energy": 0.0,
                       "external_species": 0.0, "cc_work": 0.0,
                       "cyl_work": 0.0}
        # These are the increments actually applied by the SSPRK2 algorithm:
        # stage RHS quadrature, before the updated primitive/conservative
        # values are stored in their float64 component fields.  They are kept
        # separately from the inventory subtraction below so stored-state
        # roundoff cannot be mistaken for a failure of the integration.
        self._applied_deltas = {"mass": 0.0, "energy": 0.0, "species": 0.0}
        # Keep the component inventories, rather than only their global sum.
        # The ledger may then observe a small net increment without recovering
        # it by subtracting two much larger system totals.
        self._initial_state = self._state()
        self._initial_components = self._component_values(self._initial_state)
        self._initial = self._totals(self._initial_state)

    def _state(self):
        cc_mass, cc_species, cc_energy = self.crankcase.inventory(self.eos)
        cy_mass, cy_species, cy_energy = self.cylinder.inventory(self.eos)
        return ((cc_mass, 0.0, cc_energy, cc_species, self.crankcase.volume),
                (cy_mass, 0.0, cy_energy, cy_species, self.cylinder.volume),
                tuple(cell.conservative for cell in self.duct_states))

    def _component_values(self, state):
        cc, cy, duct = state
        return {
            "mass": (cc[0], cy[0], *(q[0] * v for q, v in zip(duct, self.mesh.volumes))),
            "energy": (cc[2], cy[2], *(q[2] * v for q, v in zip(duct, self.mesh.volumes))),
            "species": (cc[3], cy[3], *(q[3] * v for q, v in zip(duct, self.mesh.volumes))),
        }

    def _totals(self, state=None):
        state = self._state() if state is None else state
        return {key: fsum(values) for key, values in self._component_values(state).items()}

    def _rhs(self, state):
        cc_q, cy_q, duct_q = state
        cc = ChamberState(cc_q[0], cc_q[2], cc_q[3], cc_q[4])
        cy = ChamberState(cy_q[0], cy_q[2], cy_q[3], cy_q[4])
        duct_primitive = [self.eos.primitive_with_mass_fraction_roundoff(q)
                          for q in duct_q]

        # These are the only two interface solves in a stage.  Zero area is
        # handled by interface_exchange as an exact closed-port zero flux.
        left = interface_exchange(cc, duct_primitive[0], self.interface_areas[0], -1, eos=self.eos)
        right = interface_exchange(cy, duct_primitive[-1], self.interface_areas[1], 1, eos=self.eos)
        left_flux = tuple(left["outward"])
        right_flux = tuple(right["outward"])
        face_fluxes = [tuple(-x for x in left_flux)]
        for a, b, area in zip(duct_primitive, duct_primitive[1:], self.mesh.areas[1:-1]):
            face_fluxes.append(tuple(area * value for value in hllc_flux(a, b, self.eos)[0]))
        face_fluxes.append(right_flux)
        duct_rhs = tuple(
            tuple(-(face_fluxes[i + 1][k] - face_fluxes[i][k]) / volume for k in range(4))
            for i, volume in enumerate(self.mesh.volumes)
        )
        cc_rhs = (left_flux[0], 0.0, left_flux[2] - cc.thermodynamics(self.eos)[1] * self.volume_rates[0], left_flux[3])
        cy_rhs = (right_flux[0], 0.0, right_flux[2] - cy.thermodynamics(self.eos)[1] * self.volume_rates[1], right_flux[3])
        trace = {
            "interfaces": (left_flux, right_flux),
            "closed": (left["closed"], right["closed"]),
            "face_fluxes": tuple(face_fluxes),
            "work_rates": (-cc.thermodynamics(self.eos)[1] * self.volume_rates[0],
                           -cy.thermodynamics(self.eos)[1] * self.volume_rates[1]),
        }
        return (cc_rhs, cy_rhs, duct_rhs), trace

    @staticmethod
    def _combine(a, b, scale):
        return tuple(x + scale * y for x, y in zip(a, b))

    def _algorithmic_increment(self, rhs, dt):
        """Return one SSPRK2 stage contribution to global inventories.

        Chamber RHS values are already extensive.  Duct RHS values are per
        unit volume, so their contribution is multiplied by the same cell
        volume used by the update.  The sum is deliberately formed from the
        stage RHS, rather than reconstructed from stored states.
        """
        return {
            key: dt * fsum((rhs[0][index], rhs[1][index],
                            *(cell[index] * volume
                              for cell, volume in zip(rhs[2], self.mesh.volumes))))
            for key, index in (("mass", 0), ("energy", 2), ("species", 3))
        }

    def _validate_state(self, state):
        cc, cy, duct = state
        ChamberState(cc[0], cc[2], cc[3], cc[4]).thermodynamics(self.eos)
        ChamberState(cy[0], cy[2], cy[3], cy[4]).thermodynamics(self.eos)
        for q in duct:
            self.eos.primitive_with_mass_fraction_roundoff(q)

    def step(self, dt):
        if not isinstance(dt, (int, float)) or not isfinite(dt) or dt <= 0:
            raise ValueError("dt must be positive")
        initial = self._state()
        rhs0, trace0 = self._rhs(initial)
        stage1 = (
            self._combine(initial[0], rhs0[0], dt)[:4] + (initial[0][4] + dt * self.volume_rates[0],),
            self._combine(initial[1], rhs0[1], dt)[:4] + (initial[1][4] + dt * self.volume_rates[1],),
            tuple(self._combine(q, r, dt) for q, r in zip(initial[2], rhs0[2])),
        )
        self._validate_state(stage1)
        rhs1, trace1 = self._rhs(stage1)
        stage_increment0 = self._algorithmic_increment(rhs0, dt)
        stage_increment1 = self._algorithmic_increment(rhs1, dt)
        for key in self._applied_deltas:
            self._applied_deltas[key] += 0.5 * (stage_increment0[key] + stage_increment1[key])
        final = (
            tuple(0.5 * (x + y + dt * r) for x, y, r in zip(initial[0][:4], stage1[0][:4], rhs1[0])) +
            (0.5 * (initial[0][4] + stage1[0][4] + dt * self.volume_rates[0]),),
            tuple(0.5 * (x + y + dt * r) for x, y, r in zip(initial[1][:4], stage1[1][:4], rhs1[1])) +
            (0.5 * (initial[1][4] + stage1[1][4] + dt * self.volume_rates[1]),),
            tuple(tuple(0.5 * (x + y + dt * r) for x, y, r in zip(q0, q1, r1))
                  for q0, q1, r1 in zip(initial[2], stage1[2], rhs1[2])),
        )
        self._validate_state(final)
        self.crankcase.volume, self.cylinder.volume = final[0][4], final[1][4]
        self.crankcase.primitive = (final[0][0] / final[0][4], 0.0,
                                    (self.eos.gamma - 1.0) * final[0][2] / final[0][4],
                                    final[0][3] / final[0][0])
        self.cylinder.primitive = (final[1][0] / final[1][4], 0.0,
                                   (self.eos.gamma - 1.0) * final[1][2] / final[1][4],
                                   final[1][3] / final[1][0])
        for cell, q in zip(self.duct_states, final[2]):
            cell.conservative = q
        self.ledger["cc_work"] += 0.5 * dt * (trace0["work_rates"][0] + trace1["work_rates"][0])
        self.ledger["cyl_work"] += 0.5 * dt * (trace0["work_rates"][1] + trace1["work_rates"][1])
        trace = {"stages": (trace0, trace1), "totals": self._totals(),
                 "applied_stage_increments": (stage_increment0, stage_increment1),
                 "stage_order": ("crankcase_interface", "cylinder_interface", "duct_faces")}
        self.history.append(trace)
        return trace

    def conservation(self):
        final_state = self._state()
        final = self._totals(final_state)
        final_components = self._component_values(final_state)
        return {"initial": dict(self._initial), "final": final,
                "delta": {
                    key: fsum(value - initial for value, initial in zip(
                        final_components[key], self._initial_components[key]))
                    for key in final_components
                }}

    def mass_ledger(self):
        audit = self.conservation()
        integration_residual = (self._applied_deltas["mass"] -
                                self.ledger["external_mass"])
        return {"initial_mass": audit["initial"]["mass"], "final_mass": audit["final"]["mass"],
                "delta_mass": audit["delta"]["mass"], "external_mass": self.ledger["external_mass"],
                "residual": audit["delta"]["mass"] - self.ledger["external_mass"],
                "applied_delta_mass": self._applied_deltas["mass"],
                "state_delta_mass": audit["delta"]["mass"],
                "integration_residual": integration_residual}

    def species_ledger(self):
        audit = self.conservation()
        integration_residual = (self._applied_deltas["species"] -
                                self.ledger["external_species"])
        return {"initial_species": audit["initial"]["species"], "final_species": audit["final"]["species"],
                "delta_species": audit["delta"]["species"], "external_species": self.ledger["external_species"],
                "residual": audit["delta"]["species"] - self.ledger["external_species"],
                "applied_delta_species": self._applied_deltas["species"],
                "state_delta_species": audit["delta"]["species"],
                "integration_residual": integration_residual}

    def energy_ledger(self):
        audit = self.conservation()
        work = self.ledger["cc_work"] + self.ledger["cyl_work"]
        stored_energies = (
            *self._initial_components["energy"],
            *self._component_values(self._state())["energy"])
        component_count = 2 + len(self.duct_states)
        state_scale = fsum(abs(value) for value in stored_energies)
        component_scale = max(abs(value) for value in stored_energies)
        accepted_updates = len(self.history)
        # Conservative bound: each accepted update can round the two chamber
        # and every duct-cell stored energy, and the final inventory subtraction
        # can round once more.  epsilon * (2*n + 2) * component_count * the
        # largest stored component bounds the accumulation without a fitted
        # threshold.  state_scale is also exposed as the total component scale.
        roundoff_bound = (sys.float_info.epsilon *
                          (2 * accepted_updates + 2) * component_count * component_scale)
        state_roundoff = audit["delta"]["energy"] - self._applied_deltas["energy"]
        integration_residual = (self._applied_deltas["energy"] -
                                (self.ledger["external_energy"] + work))
        # This is the independently observable balance obtained by subtracting
        # the stored final and initial totals.  It includes one additional
        # floating-point operation over ``state_roundoff`` (the addition of
        # the accounted work), so expose it separately and check it against
        # the same conservative machine-roundoff bound.
        stored_balance_roundoff = (audit["final"]["energy"] -
                                    (audit["initial"]["energy"] +
                                     self.ledger["external_energy"] + work))
        return {"initial_energy": audit["initial"]["energy"], "final_energy": audit["final"]["energy"],
                "delta_energy": audit["delta"]["energy"], "external_energy": self.ledger["external_energy"],
                "cc_work": self.ledger["cc_work"], "cyl_work": self.ledger["cyl_work"],
                "chamber_work": work, "accounted_energy": work,
                # Legacy state-based semantics retained for existing callers.
                "residual": audit["delta"]["energy"] - work,
                "applied_delta_energy": self._applied_deltas["energy"],
                "state_delta_energy": audit["delta"]["energy"],
                "integration_residual": integration_residual,
                "state_roundoff": state_roundoff,
                "stored_balance_roundoff": stored_balance_roundoff,
                "stored_balance_roundoff_bound": roundoff_bound,
                "state_roundoff_bound": roundoff_bound,
                "stored_energy_scale": state_scale,
                "stored_energy_component_scale": component_scale,
                "stored_energy_component_count": component_count,
                "accepted_updates": accepted_updates}

    def admissible(self):
        self._validate_state(self._state())
        return True


def make_one_transfer_fixture(*, eos=None, cells=3, volume_rates=(0.0, 0.0), interface_areas=None):
    """Build an externally closed crankcase/one-transfer/cylinder fixture."""
    eos = eos or IdealGas()
    mesh = uniform_mesh(cells, length=0.03, area=1.0e-4)
    crankcase = Chamber((1.05, 0.0, 112000.0, 0.65), 1.0e-3)
    cylinder = Chamber((0.95, 0.0, 97000.0, 0.25), 1.0e-2)
    duct = tuple((1.0, 0.0, 100000.0, 0.4) for _ in range(cells))
    return OneTransferFixture(crankcase, cylinder, duct, mesh=mesh, eos=eos,
                              volume_rates=volume_rates, interface_areas=interface_areas)


class _TransferPath:
    """Private independent state for one finite transfer in TwoTransferFixture."""

    def __init__(self, duct_states, mesh, eos, interface_areas):
        if not duct_states or len(duct_states) != mesh.n:
            raise ValueError("transfer duct state/mesh size mismatch")
        self.mesh = mesh
        self.interface_areas = tuple(float(x) for x in interface_areas)
        self.duct_states = [
            state if isinstance(state, DuctCell)
            else DuctCell(eos.conservative(state), volume)
            for state, volume in zip(duct_states, mesh.volumes)
        ]
        self.history = []
        self.ledger = {"mass": 0.0, "energy": 0.0, "species": 0.0}

    def state(self):
        return tuple(cell.conservative for cell in self.duct_states)


class TwoTransferFixture:
    """Closed crankcase/two-transfer/cylinder SSPRK2 fixture.

    Each path owns its mesh, cells, history and ledger.  A stage resolves the
    four physical interfaces exactly once, then assembles both chamber RHSs by
    summing the two path contributions before either chamber is updated.
    """

    def __init__(self, crankcase, cylinder, transfer_states, *, meshes=None,
                 eos=None, volume_rates=(0.0, 0.0), interface_areas=None):
        self.eos = eos or IdealGas()
        if not isinstance(crankcase, Chamber) or not isinstance(cylinder, Chamber):
            raise TypeError("fixtures require Chamber instances")
        if len(transfer_states) != 2:
            raise ValueError("two independent transfer states are required")
        if meshes is None:
            meshes = tuple(uniform_mesh(len(states), length=0.03, area=1.0e-4)
                           for states in transfer_states)
        if len(meshes) != 2:
            raise ValueError("two independent transfer meshes are required")
        if len(volume_rates) != 2 or not all(
                isinstance(x, (int, float)) and isfinite(x) for x in volume_rates):
            raise ValueError("invalid chamber volume rates")
        if interface_areas is None:
            interface_areas = tuple((mesh.areas[0], mesh.areas[-1]) for mesh in meshes)
        if len(interface_areas) != 2 or any(len(areas) != 2 for areas in interface_areas):
            raise ValueError("two pairs of interface areas are required")
        if (any(not isinstance(x, (int, float)) or not isfinite(x) or x < 0
                for areas in interface_areas for x in areas)):
            raise ValueError("invalid interface areas")
        if crankcase.volume <= 0 or cylinder.volume <= 0:
            raise ValueError("invalid chamber volume")
        self.crankcase = crankcase
        self.cylinder = cylinder
        self.volume_rates = tuple(float(x) for x in volume_rates)
        self.transfers = tuple(
            _TransferPath(states, mesh, self.eos, areas)
            for states, mesh, areas in zip(transfer_states, meshes, interface_areas)
        )
        # Public convenience mirrors the one-transfer fixture without sharing
        # either list or cell objects with a path.
        self.duct_states = tuple(path.duct_states for path in self.transfers)
        self.history = []
        self.ledger = {"external_mass": 0.0, "external_energy": 0.0,
                       "external_species": 0.0, "cc_work": 0.0,
                       "cyl_work": 0.0}
        self._applied_deltas = {"mass": 0.0, "energy": 0.0, "species": 0.0}
        self._initial_state = self._state()
        self._initial_components = self._component_values(self._initial_state)
        self._initial = self._totals(self._initial_state)

    def _state(self):
        cc_mass, cc_species, cc_energy = self.crankcase.inventory(self.eos)
        cy_mass, cy_species, cy_energy = self.cylinder.inventory(self.eos)
        return ((cc_mass, 0.0, cc_energy, cc_species, self.crankcase.volume),
                (cy_mass, 0.0, cy_energy, cy_species, self.cylinder.volume),
                tuple(path.state() for path in self.transfers))

    def _component_values(self, state):
        cc, cy, paths = state
        values = {
            "mass": [cc[0], cy[0]],
            "energy": [cc[2], cy[2]],
            "species": [cc[3], cy[3]],
        }
        for path, mesh in zip(paths, (item.mesh for item in self.transfers)):
            for key, index in (("mass", 0), ("energy", 2), ("species", 3)):
                values[key].extend(q[index] * volume
                                   for q, volume in zip(path, mesh.volumes))
        return {key: tuple(items) for key, items in values.items()}

    def _totals(self, state=None):
        state = self._state() if state is None else state
        return {key: fsum(values) for key, values in self._component_values(state).items()}

    def _path_rhs(self, cc, cy, path, duct_q):
        duct_primitive = [self.eos.primitive_with_mass_fraction_roundoff(q)
                          for q in duct_q]
        left = interface_exchange(cc, duct_primitive[0], path.interface_areas[0], -1, eos=self.eos)
        right = interface_exchange(cy, duct_primitive[-1], path.interface_areas[1], 1, eos=self.eos)
        left_flux, right_flux = tuple(left["outward"]), tuple(right["outward"])
        face_fluxes = [tuple(-value for value in left_flux)]
        for a, b, area in zip(duct_primitive, duct_primitive[1:], path.mesh.areas[1:-1]):
            face_fluxes.append(tuple(area * value for value in hllc_flux(a, b, self.eos)[0]))
        face_fluxes.append(right_flux)
        duct_rhs = tuple(
            tuple(-(face_fluxes[i + 1][k] - face_fluxes[i][k]) / volume for k in range(4))
            for i, volume in enumerate(path.mesh.volumes)
        )
        return ((left_flux, right_flux), duct_rhs), {
            "interfaces": (left_flux, right_flux),
            "closed": (left["closed"], right["closed"]),
            "face_fluxes": tuple(face_fluxes),
        }

    def _rhs(self, state):
        cc_q, cy_q, paths_q = state
        cc = ChamberState(cc_q[0], cc_q[2], cc_q[3], cc_q[4])
        cy = ChamberState(cy_q[0], cy_q[2], cy_q[3], cy_q[4])
        path_rhs, traces = [], []
        for path, duct_q in zip(self.transfers, paths_q):
            rhs, trace = self._path_rhs(cc, cy, path, duct_q)
            path_rhs.append(rhs)
            traces.append(trace)
        cc_flux = tuple(sum(rhs[0][0][k] for rhs in path_rhs) for k in range(4))
        cy_flux = tuple(sum(rhs[0][1][k] for rhs in path_rhs) for k in range(4))
        cc_pressure = cc.thermodynamics(self.eos)[1]
        cy_pressure = cy.thermodynamics(self.eos)[1]
        cc_rhs = (cc_flux[0], 0.0, cc_flux[2] - cc_pressure * self.volume_rates[0], cc_flux[3])
        cy_rhs = (cy_flux[0], 0.0, cy_flux[2] - cy_pressure * self.volume_rates[1], cy_flux[3])
        return (cc_rhs, cy_rhs, tuple(item[1] for item in path_rhs)), {
            "transfers": tuple(traces),
            "aggregate_chamber_rhs": (cc_rhs, cy_rhs),
            "work_rates": (-cc_pressure * self.volume_rates[0],
                           -cy_pressure * self.volume_rates[1]),
        }

    @staticmethod
    def _combine(a, b, scale):
        return tuple(x + scale * y for x, y in zip(a, b))

    def _algorithmic_increment(self, rhs, dt):
        return {
            key: dt * fsum((rhs[0][index], rhs[1][index],
                            *(cell[index] * volume
                              for cells, path in zip(rhs[2], self.transfers)
                              for cell, volume in zip(cells, path.mesh.volumes))))
            for key, index in (("mass", 0), ("energy", 2), ("species", 3))
        }

    def _validate_state(self, state):
        cc, cy, paths = state
        ChamberState(cc[0], cc[2], cc[3], cc[4]).thermodynamics(self.eos)
        ChamberState(cy[0], cy[2], cy[3], cy[4]).thermodynamics(self.eos)
        for path in paths:
            for q in path:
                self.eos.primitive_with_mass_fraction_roundoff(q)

    def step(self, dt):
        if not isinstance(dt, (int, float)) or not isfinite(dt) or dt <= 0:
            raise ValueError("dt must be positive")
        initial = self._state()
        rhs0, trace0 = self._rhs(initial)
        stage1 = (
            self._combine(initial[0], rhs0[0], dt)[:4] +
            (initial[0][4] + dt * self.volume_rates[0],),
            self._combine(initial[1], rhs0[1], dt)[:4] +
            (initial[1][4] + dt * self.volume_rates[1],),
            tuple(tuple(self._combine(q, r, dt) for q, r in zip(path, path_rhs))
                  for path, path_rhs in zip(initial[2], rhs0[2])),
        )
        self._validate_state(stage1)
        rhs1, trace1 = self._rhs(stage1)
        stage_increment0 = self._algorithmic_increment(rhs0, dt)
        stage_increment1 = self._algorithmic_increment(rhs1, dt)
        for key in self._applied_deltas:
            self._applied_deltas[key] += 0.5 * (stage_increment0[key] + stage_increment1[key])
        final = (
            tuple(0.5 * (x + y + dt * r) for x, y, r in zip(initial[0][:4], stage1[0][:4], rhs1[0])) +
            (0.5 * (initial[0][4] + stage1[0][4] + dt * self.volume_rates[0]),),
            tuple(0.5 * (x + y + dt * r) for x, y, r in zip(initial[1][:4], stage1[1][:4], rhs1[1])) +
            (0.5 * (initial[1][4] + stage1[1][4] + dt * self.volume_rates[1]),),
            tuple(tuple(tuple(0.5 * (x + y + dt * r) for x, y, r in zip(q0, q1, r1))
                        for q0, q1, r1 in zip(path0, path1, path_rhs))
                  for path0, path1, path_rhs in zip(initial[2], stage1[2], rhs1[2])),
        )
        self._validate_state(final)
        self.crankcase.volume, self.cylinder.volume = final[0][4], final[1][4]
        self.crankcase.primitive = (final[0][0] / final[0][4], 0.0,
                                    (self.eos.gamma - 1.0) * final[0][2] / final[0][4],
                                    final[0][3] / final[0][0])
        self.cylinder.primitive = (final[1][0] / final[1][4], 0.0,
                                   (self.eos.gamma - 1.0) * final[1][2] / final[1][4],
                                   final[1][3] / final[1][0])
        for path, path_final in zip(self.transfers, final[2]):
            for cell, q in zip(path.duct_states, path_final):
                cell.conservative = q
            path.history.append((trace0["transfers"][self.transfers.index(path)],
                                 trace1["transfers"][self.transfers.index(path)]))
        self.ledger["cc_work"] += 0.5 * dt * (trace0["work_rates"][0] + trace1["work_rates"][0])
        self.ledger["cyl_work"] += 0.5 * dt * (trace0["work_rates"][1] + trace1["work_rates"][1])
        trace = {"stages": (trace0, trace1),
                 "totals": self._totals(),
                 "applied_stage_increments": (stage_increment0, stage_increment1),
                 "stage_order": ("transfer_interfaces", "aggregate_chamber_rhs", "duct_faces")}
        self.history.append(trace)
        return trace

    def conservation(self):
        final_state = self._state()
        final = self._totals(final_state)
        final_components = self._component_values(final_state)
        return {"initial": dict(self._initial), "final": final,
                "delta": {key: fsum(value - initial for value, initial in zip(
                    final_components[key], self._initial_components[key]))
                           for key in final_components}}

    def mass_ledger(self):
        audit = self.conservation()
        integration_residual = self._applied_deltas["mass"] - self.ledger["external_mass"]
        return {"initial_mass": audit["initial"]["mass"], "final_mass": audit["final"]["mass"],
                "delta_mass": audit["delta"]["mass"], "external_mass": self.ledger["external_mass"],
                "residual": audit["delta"]["mass"] - self.ledger["external_mass"],
                "applied_delta_mass": self._applied_deltas["mass"],
                "state_delta_mass": audit["delta"]["mass"], "integration_residual": integration_residual}

    def species_ledger(self):
        audit = self.conservation()
        integration_residual = self._applied_deltas["species"] - self.ledger["external_species"]
        return {"initial_species": audit["initial"]["species"], "final_species": audit["final"]["species"],
                "delta_species": audit["delta"]["species"], "external_species": self.ledger["external_species"],
                "residual": audit["delta"]["species"] - self.ledger["external_species"],
                "applied_delta_species": self._applied_deltas["species"],
                "state_delta_species": audit["delta"]["species"], "integration_residual": integration_residual}

    def energy_ledger(self):
        audit = self.conservation()
        work = self.ledger["cc_work"] + self.ledger["cyl_work"]
        stored = (*self._initial_components["energy"],
                  *self._component_values(self._state())["energy"])
        component_count = 2 + sum(len(path.duct_states) for path in self.transfers)
        component_scale = max(abs(value) for value in stored)
        bound = (sys.float_info.epsilon * (2 * len(self.history) + 2) *
                 component_count * component_scale)
        state_roundoff = audit["delta"]["energy"] - self._applied_deltas["energy"]
        integration_residual = self._applied_deltas["energy"] - work
        stored_balance_roundoff = audit["final"]["energy"] - (audit["initial"]["energy"] + work)
        return {"initial_energy": audit["initial"]["energy"], "final_energy": audit["final"]["energy"],
                "delta_energy": audit["delta"]["energy"], "external_energy": self.ledger["external_energy"],
                "cc_work": self.ledger["cc_work"], "cyl_work": self.ledger["cyl_work"],
                "chamber_work": work, "accounted_energy": work,
                "residual": audit["delta"]["energy"] - work,
                "applied_delta_energy": self._applied_deltas["energy"],
                "state_delta_energy": audit["delta"]["energy"], "integration_residual": integration_residual,
                "state_roundoff": state_roundoff, "stored_balance_roundoff": stored_balance_roundoff,
                "stored_balance_roundoff_bound": bound, "state_roundoff_bound": bound,
                "stored_energy_component_count": component_count, "accepted_updates": len(self.history)}

    def admissible(self):
        self._validate_state(self._state())
        return True


def make_two_transfer_fixture(*, eos=None, cells=3, volume_rates=(0.0, 0.0),
                              transfer_states=None, meshes=None, interface_areas=None):
    """Build two independent finite transfer paths between two chambers."""
    eos = eos or IdealGas()
    if transfer_states is None:
        transfer_states = tuple(tuple((1.0, 0.0, 100000.0, 0.4) for _ in range(cells))
                                for _ in range(2))
    if meshes is None:
        meshes = tuple(uniform_mesh(cells, length=0.03, area=1.0e-4) for _ in range(2))
    crankcase = Chamber((1.05, 0.0, 112000.0, 0.65), 1.0e-3)
    cylinder = Chamber((0.95, 0.0, 97000.0, 0.25), 1.0e-2)
    return TwoTransferFixture(crankcase, cylinder, transfer_states, meshes=meshes, eos=eos,
                              volume_rates=volume_rates, interface_areas=interface_areas)


def make_single_0d1d_fixture(*, eos=None, cells=3):
    """Return a fixed-volume, closed chamber/finite-duct verification case."""
    eos = eos or IdealGas()
    mesh = uniform_mesh(cells, length=0.03, area=1.0e-4)
    chamber = Chamber((1.0, 0.0, 110000.0, 0.4), 1.0e-3)
    duct = tuple((1.0, 0.0, 100000.0, 0.2) for _ in range(cells))
    return Single0D1DFixture(chamber, duct, mesh=mesh, eos=eos)


def make_closed_volume_work_fixture(*, eos=None, volume_rates=(-1.0e-4, 1.0e-4)):
    """Build the P5B-10 closed-volume work fixture.

    All physical ports are closed by the caller's closed-angle trajectory;
    this factory only supplies the two chambers, their passive inventories,
    and the existing contractual volume-rate mechanism.  No heat, reaction,
    or external state is introduced here.
    """
    eos = eos or IdealGas()
    crankcase = Chamber((1.0, 0.0, 100000.0, 0.5), 1.0e-3)
    cylinder = Chamber((1.0, 0.0, 100000.0, 0.5), 1.0e-2)
    closed_duct = (1.0, 0.0, 101325.0, 0.0)
    return IntegratedIntakeTransfer(
        crankcase,
        cylinder,
        (closed_duct, closed_duct, closed_duct),
        eos=eos,
        volume_rates=volume_rates,
        external_boundary=False,
    )


class _FinitePath:
    """Private finite-volume path used by the complete P5-B state."""
    def __init__(self, states, mesh, eos):
        # A four-tuple is the historical one-cell primitive shorthand;
        # otherwise the caller supplied a finite sequence of primitives.
        if isinstance(states, tuple) and len(states) == 4 and isinstance(states[0], (int, float)):
            states = (states,)
        if len(states) != mesh.n:
            raise ValueError("state/mesh size mismatch")
        self.mesh = mesh
        self.cells = [state if isinstance(state, DuctCell)
                      else DuctCell(eos.conservative(state), volume)
                      for state, volume in zip(states, mesh.volumes)]

    def conservative(self):
        return tuple(cell.conservative for cell in self.cells)


class IntegratedIntakeTransfer:
    """Complete finite P5-B topology with one global SSPRK2 update.

    The stored state is atmosphere boundary -> finite intake -> crankcase ->
    two independent finite transfers -> cylinder.  The atmosphere is the
    only non-stored component.  All face fluxes and chamber sources are
    assembled from one common stage state before anything is updated.
    """
    def __init__(self, crankcase, cylinder, duct_states, *, eos=None,
                 volume_rates=(0.0, 0.0), meshes=None, external_boundary=True,
                 geometry_callback=None,
                 external_boundary_flux_convention="legacy_contract",
                 external_boundary_model=None):
        if len(duct_states) != 3:
            raise ValueError("expected intake, transfer1 and transfer2 states")
        self.eos = eos or IdealGas()
        self.crankcase = crankcase
        self.cylinder = cylinder
        self.external_boundary = bool(external_boundary)
        self.external_boundary_model = external_boundary_model
        self.geometry_callback = geometry_callback
        if external_boundary_flux_convention not in ("legacy_contract", "global_x"):
            raise ValueError("unsupported external boundary flux convention")
        self.external_boundary_flux_convention = external_boundary_flux_convention
        def normalize(states):
            if isinstance(states, tuple) and len(states) == 4 and isinstance(states[0], (int, float)):
                return (states,)
            return states
        duct_states = tuple(normalize(states) for states in duct_states)
        if meshes is None:
            # The shorthand fixture has one finite cell per family.  Its
            # deliberately long verification duct keeps the historical
            # diagnostic time steps inside the existing explicit CFL scope;
            # callers running physical geometry pass explicit meshes.
            meshes = tuple(uniform_mesh(len(states), length=30.0, area=1e-4)
                           for states in duct_states)
        if len(meshes) != 3:
            raise ValueError("expected intake and two transfer meshes")
        self.intake = _FinitePath(duct_states[0], meshes[0], self.eos)
        self.transfers = tuple(_FinitePath(states, mesh, self.eos)
                               for states, mesh in zip(duct_states[1:], meshes[1:]))
        self.angle = 0.0
        if len(volume_rates) != 2:
            raise ValueError("expected crankcase and cylinder volume rates")
        self.volume_rates = tuple(float(x) for x in volume_rates)
        self.ledger = {'external_mass': 0.0, 'external_energy': 0.0,
                       'external_species': 0.0, 'cc_work': 0.0,
                       'cyl_work': 0.0}
        self._applied = {'mass': 0.0, 'energy': 0.0, 'species': 0.0}
        self._accepted_updates = 0
        self.history = []
        self._initial = self._totals(self._state())

    @property
    def duct_states(self):
        """Compatibility view of the three path entrance cells.

        Full finite paths are exposed as ``intake`` and ``transfers``; this
        view keeps the earlier P5B trace/audit API without aliasing paths.
        """
        return [self.intake.cells[0], self.transfers[0].cells[0],
                self.transfers[1].cells[0]]

    def _state(self):
        return ((self.crankcase.inventory(self.eos)[0], 0.0,
                 self.crankcase.inventory(self.eos)[2],
                 self.crankcase.inventory(self.eos)[1], self.crankcase.volume),
                (self.cylinder.inventory(self.eos)[0], 0.0,
                 self.cylinder.inventory(self.eos)[2],
                 self.cylinder.inventory(self.eos)[1], self.cylinder.volume),
                self.intake.conservative(),
                *(path.conservative() for path in self.transfers))

    def _component_values(self, state):
        cc, cy, intake, tr1, tr2 = state
        paths = ((q, self.intake.mesh.volumes) for q in (intake,))
        paths = (*paths, (tr1, self.transfers[0].mesh.volumes),
                 (tr2, self.transfers[1].mesh.volumes))
        values = {'mass': [cc[0], cy[0]], 'energy': [cc[2], cy[2]],
                  'species': [cc[3], cy[3]]}
        for duct, volumes in paths:
            values['mass'].extend(q[0] * v for q, v in zip(duct, volumes))
            values['energy'].extend(q[2] * v for q, v in zip(duct, volumes))
            values['species'].extend(q[3] * v for q, v in zip(duct, volumes))
        return {key: tuple(items) for key, items in values.items()}

    def _totals(self, state=None):
        return {key: fsum(items) for key, items in
                self._component_values(self._state() if state is None else state).items()}

    def _total_mass(self):
        """Return the mass currently stored in every coupled volume."""
        return self._totals()['mass']

    def _total_species(self):
        """Return the fresh-species inventory in all stored coupled volumes."""
        return self._totals()['species']

    def _total_energy(self):
        """Return total stored conservative energy in the P5-B volumes."""
        return self._totals()['energy']

    def mass_ledger(self):
        """Audit closed-system mass against the external interface integral.

        A positive external flux denotes mass entering the integrated fixture.
        Internal transfer interfaces cancel because each duct receives the
        opposite update of its chamber flux.  The returned residual is
        ``(final - initial) - external`` and is intentionally not normalized.
        """
        final_mass = self._total_mass()
        external_mass = self.ledger['external_mass']
        delta_mass = final_mass - self._initial['mass']
        return {
            'initial_mass': self._initial['mass'],
            'final_mass': final_mass,
            'delta_mass': delta_mass,
            'external_mass': external_mass,
            'applied_delta_mass': self._applied['mass'],
            'integration_residual': self._applied['mass'] - external_mass,
            'residual': delta_mass - external_mass,
        }

    def species_ledger(self):
        """Audit fresh-species inventory against the external interface.

        Species is stored as fresh mass, not as a mass fraction.  The intake
        endpoint is the only external boundary in this fixture; transfer
        interfaces are internal and therefore cancel from the global balance.
        """
        final_species = self._total_species()
        external_species = self.ledger['external_species']
        delta_species = final_species - self._initial['species']
        return {
            'initial_species': self._initial['species'],
            'final_species': final_species,
            'delta_species': delta_species,
            'external_species': external_species,
            'applied_delta_species': self._applied['species'],
            'integration_residual': self._applied['species'] - external_species,
            'residual': delta_species - external_species,
        }

    def energy_ledger(self):
        """Audit global energy against boundary flux and chamber p*dV work.

        The stored energy includes both chambers and the two internal transfer
        duct cells.  Internal interface fluxes are not ledger inputs: the
        same stage flux is applied with opposite signs at its two endpoints,
        so adding it would double count interface pressure work.  ``external_energy``
        and the two chamber work terms remain separate for auditability.
        """
        final_energy = self._total_energy()
        external_energy = self.ledger['external_energy']
        chamber_work = self.ledger['cc_work'] + self.ledger['cyl_work']
        delta_energy = final_energy - self._initial['energy']
        accounted = external_energy + chamber_work
        applied_delta = self._applied['energy']
        integration_residual = applied_delta - accounted
        roundoff_bound = (64.0 * max(1.0, abs(self._initial['energy']), abs(final_energy)) *
                          2.220446049250313e-16 * max(1, self._accepted_updates))
        return {
            'initial_energy': self._initial['energy'],
            'final_energy': final_energy,
            'delta_energy': delta_energy,
            'external_energy': external_energy,
            'cc_work': self.ledger['cc_work'],
            'cyl_work': self.ledger['cyl_work'],
            'chamber_work': chamber_work,
            'accounted_energy': accounted,
            'applied_delta_energy': applied_delta,
            'integration_residual': integration_residual,
            'state_delta_energy': delta_energy,
            'state_roundoff': delta_energy - applied_delta,
            'state_roundoff_bound': roundoff_bound,
            'stored_balance_roundoff': delta_energy - accounted,
            'stored_balance_roundoff_bound': roundoff_bound,
            'accepted_updates': self._accepted_updates,
            'residual': delta_energy - accounted,
        }

    def _areas(self, angle):
        # Contractual 2T timing fixture: intake opens 270..360 and transfers
        # 100..220 degrees. Values are intentionally explicit and deterministic.
        a = angle % 360.0
        intake = 1e-4 if 270.0 <= a < 360.0 else 0.0
        transfer = 1e-4 if 100.0 <= a < 220.0 else 0.0
        return intake, transfer, transfer

    def _rhs(self, state, angle):
        cc_q, cy_q, intake_q, tr1_q, tr2_q = state
        cc = ChamberState(cc_q[0], cc_q[2], cc_q[3], cc_q[4])
        cy = ChamberState(cy_q[0], cy_q[2], cy_q[3], cy_q[4])
        intake_p = [self.eos.primitive_with_mass_fraction_roundoff(q)
                    for q in intake_q]
        tr_p = [[self.eos.primitive_with_mass_fraction_roundoff(q) for q in duct]
                for duct in (tr1_q, tr2_q)]
        if self.geometry_callback is None:
            ai, at1, at2 = self._areas(angle)
            rates = self.volume_rates
        else:
            geometry = self.geometry_callback(float(angle))
            if isinstance(geometry, dict):
                rates, areas = geometry['volume_rates'], geometry['areas']
            else:
                _, rates, areas = geometry
            if len(rates) != 2 or len(areas) < 3:
                raise ValueError('geometry callback requires two rates and three areas')
            ai, at1, at2 = (float(x) for x in areas[:3])
        # The only external boundary. Its face flux is in the duct +x sign.
        if self.external_boundary:
            atmosphere = (self.external_boundary_model or
                          Boundary('reservoir', p0=101325.0, T0=300.0, Y0=0.0))
            ext = atmosphere.flux(intake_p[0], -1, self.eos)
            ext_face = tuple(self.intake.mesh.areas[0] * value for value in ext[0])
        else:
            ext_face = (0.0, 0.0, 0.0, 0.0)
        # The finite-volume left face is outward from the stored subsystem;
        # ledgers use the atmospheric integral into the subsystem.
        # P5-B's historical fixtures use an outward-oriented boundary tuple.
        # Reference-engine P5-C supplies Boundary.flux's global +x tuple and
        # requests the explicitly named adapter convention below.
        consistent_external = self.external_boundary_flux_convention == "global_x"
        external_in = tuple(value if consistent_external else -value
                            for value in ext_face)
        intake_cc = interface_exchange(cc, intake_p[-1], ai, 1, eos=self.eos)
        transfer = []
        for primitive, area in zip(tr_p, (at1, at2)):
            transfer.append((interface_exchange(cc, primitive[0], area, -1, eos=self.eos),
                             interface_exchange(cy, primitive[-1], area, 1, eos=self.eos)))
        # Every duct uses its own interior HLLC face fluxes.  The interface
        # result above is the same extensive flux consumed by both endpoints.
        def duct_rhs(primitive, mesh, left, right):
            faces = [tuple(-x for x in left)]
            faces.extend(tuple(area * value for value in hllc_flux(a, b, self.eos)[0])
                         for a, b, area in zip(primitive, primitive[1:], mesh.areas[1:-1]))
            faces.append(tuple(right))
            return tuple(tuple(-(faces[i + 1][k] - faces[i][k]) / volume
                                for k in range(4))
                         for i, volume in enumerate(mesh.volumes)), tuple(faces)
        left_external = (tuple(-value for value in ext_face)
                         if consistent_external else ext_face)
        intake_rhs, intake_faces = duct_rhs(intake_p, self.intake.mesh,
                                             left_external, intake_cc['outward'])
        transfer_rhs = []
        transfer_faces = []
        for (left, right), primitive, path in zip(transfer, tr_p, self.transfers):
            rhs, faces = duct_rhs(primitive, path.mesh, left['outward'], right['outward'])
            transfer_rhs.append(rhs); transfer_faces.append(faces)
        cc_fluxes = [intake_cc['outward'], transfer[0][0]['outward'], transfer[1][0]['outward']]
        cy_fluxes = [transfer[0][1]['outward'], transfer[1][1]['outward']]
        def chamber_rhs(chamber, fluxes, rate):
            pressure = chamber.thermodynamics(self.eos)[1]
            return (fsum(flux[0] for flux in fluxes),
                    fsum(flux[2] for flux in fluxes) - pressure * rate,
                    fsum(flux[3] for flux in fluxes))
        cc_rhs = chamber_rhs(cc, cc_fluxes, float(rates[0]))
        cy_rhs = chamber_rhs(cy, cy_fluxes, float(rates[1]))
        return ((cc_rhs, cy_rhs, intake_rhs, transfer_rhs[0], transfer_rhs[1]),
                {'angle': angle, 'areas': (ai, at1, at2), 'external': external_in,
                 'interfaces': (intake_cc['outward'], transfer[0][0]['outward'],
                                transfer[1][0]['outward'], transfer[0][1]['outward'],
                                transfer[1][1]['outward']),
                 'interface_closed': (intake_cc['closed'], transfer[0][0]['closed'],
                                      transfer[1][0]['closed'], transfer[0][1]['closed'],
                                      transfer[1][1]['closed']),
                 'face_fluxes': (intake_faces, transfer_faces[0], transfer_faces[1]),
                 'work_rates': (-cc.thermodynamics(self.eos)[1] * float(rates[0]),
                                -cy.thermodynamics(self.eos)[1] * float(rates[1]))})

    @staticmethod
    def _combine(a, rhs, scale):
        return tuple(x + scale * r for x, r in zip(a, rhs))

    def _validate_state(self, state):
        cc, cy, *ducts = state
        ChamberState(cc[0], cc[2], cc[3], cc[4]).thermodynamics(self.eos)
        ChamberState(cy[0], cy[2], cy[3], cy[4]).thermodynamics(self.eos)
        for duct in ducts:
            for q in duct:
                self.eos.primitive_with_mass_fraction_roundoff(q)

    def admissible(self):
        self._validate_state(self._state())
        return True

    def _applied_increment(self, rhs0, rhs1, dt):
        total = {}
        for key, index in (('mass', 0), ('energy', 2), ('species', 3)):
            chamber_index = {0: 0, 2: 1, 3: 2}[index]
            values = []
            for rhs, state in ((rhs0, self._state()), (rhs1, self._state())):
                values.append(rhs[0][chamber_index] + rhs[1][chamber_index])
                for duct_rhs, volumes in zip(rhs[2:], (self.intake.mesh.volumes,
                                                         self.transfers[0].mesh.volumes,
                                                         self.transfers[1].mesh.volumes)):
                    values.append(fsum(x[index] * v for x, v in zip(duct_rhs, volumes)))
            total[key] = 0.5 * dt * fsum(values)
        return total

    def step(self, dt, angle=None):
        if not isinstance(dt, (int, float)) or not isfinite(dt) or dt <= 0:
            raise ValueError("dt must be positive")
        start = self.angle
        self.angle = start + 360.0 * dt if angle is None else float(angle)
        stage_angles = (start if angle is None else self.angle, self.angle)
        def stage_volumes(a):
            if self.geometry_callback is None:
                return None
            g = self.geometry_callback(float(a))
            return tuple(g['volumes'] if isinstance(g, dict) else g[0])
        volumes0, volumes1 = (stage_volumes(stage_angles[0]),
                              stage_volumes(stage_angles[1]))
        initial = self._state()
        # Geometry is authoritative for the chamber storage volumes.  Install
        # the theta0 values before assembling R0; volumes are ordered I,K,C,E.
        if volumes0 is not None:
            initial = ((*initial[0][:4], volumes0[1]),
                       (*initial[1][:4], volumes0[2]), *initial[2:])
        rhs0, trace0 = self._rhs(initial, stage_angles[0])
        def euler_state(state, rhs):
            cc, cy, *ducts = state
            rcc, rcy, *rducts = rhs
            chambers = []
            rates = self.volume_rates
            for q, r, rate in ((cc, rcc, rates[0]), (cy, rcy, rates[1])):
                chambers.append((q[0] + dt * r[0], q[1], q[2] + dt * r[1],
                                q[3] + dt * r[2]) +
                                (q[4] + dt * rate,))
            if volumes1 is not None:
                chambers[0] = (*chambers[0][:4], volumes1[1])
                chambers[1] = (*chambers[1][:4], volumes1[2])
            return tuple(chambers) + tuple(tuple(self._combine(q, r, dt)
                                                  for q, r in zip(duct, rduct))
                                           for duct, rduct in zip(ducts, rducts))
        stage1 = euler_state(initial, rhs0)
        self._validate_state(stage1)
        rhs1, trace1 = self._rhs(stage1, stage_angles[1])
        def heun_state(old, predictor, rhs):
            cc, cy, *ducts = old
            pcc, pcy, *pducts = predictor
            rcc, rcy, *rducts = rhs
            chambers = []
            for q, p, r, rate in ((cc, pcc, rcc, self.volume_rates[0]),
                                  (cy, pcy, rcy, self.volume_rates[1])):
                chambers.append((0.5 * (q[0] + p[0] + dt * r[0]), q[1],
                                0.5 * (q[2] + p[2] + dt * r[1]),
                                0.5 * (q[3] + p[3] + dt * r[2])) +
                                (0.5 * (q[4] + p[4] + dt * rate),))
            if volumes1 is not None:
                chambers[0] = (*chambers[0][:4], volumes1[1])
                chambers[1] = (*chambers[1][:4], volumes1[2])
            return tuple(chambers) + tuple(tuple(tuple(0.5 * (qv + pv + dt * rv)
                                                        for qv, pv, rv in zip(q, p, r))
                                                 for q, p, r in zip(duct, pred, rr))
                                                 for duct, pred, rr in zip(ducts, pducts, rducts))
        final = heun_state(initial, stage1, rhs1)
        self._validate_state(final)
        applied = self._applied_increment(rhs0, rhs1, dt)
        for key in self._applied:
            self._applied[key] += applied[key]
        self._accepted_updates += 1
        self.crankcase.volume, self.cylinder.volume = final[0][4], final[1][4]
        for chamber, q in ((self.crankcase, final[0]), (self.cylinder, final[1])):
            chamber.primitive = (q[0] / q[4], 0.0, (self.eos.gamma - 1) * q[2] / q[4], q[3] / q[0])
        for path, duct in zip((self.intake, *self.transfers), final[2:]):
            for cell, q in zip(path.cells, duct): cell.conservative = q
        ext0, ext1 = trace0['external'], trace1['external']
        for key, index in (('external_mass', 0), ('external_energy', 2), ('external_species', 3)):
            self.ledger[key] += 0.5 * dt * (ext0[index] + ext1[index])
        self.ledger['cc_work'] += 0.5 * dt * (trace0['work_rates'][0] + trace1['work_rates'][0])
        self.ledger['cyl_work'] += 0.5 * dt * (trace0['work_rates'][1] + trace1['work_rates'][1])
        self.history.append({'angle': self.angle, 'areas': trace1['areas'],
                             'fluxes': list(trace1['interfaces'][:3]),
                             'external_flux': (ext0, ext1),
                             'stages': (trace0, trace1),
                             'crankcase': self.crankcase.inventory(self.eos),
                             'cylinder': self.cylinder.inventory(self.eos),
                             'ducts': [[list(q) for q in duct] for duct in final[2:]],
                             'applied_delta': applied})
        return self.history[-1]

    def snapshot(self):
        return {'angle': self.angle, 'crankcase': deepcopy(self.crankcase),
                'cylinder': deepcopy(self.cylinder), 'intake': deepcopy(self.intake),
                'transfers': deepcopy(self.transfers)}

    def restore(self, snap):
        self.angle = snap['angle']; self.crankcase = deepcopy(snap['crankcase'])
        self.cylinder = deepcopy(snap['cylinder']); self.intake = deepcopy(snap['intake'])
        self.transfers = deepcopy(snap['transfers'])
