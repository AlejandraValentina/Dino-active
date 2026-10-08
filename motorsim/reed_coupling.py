"""Preregistered dynamic-reed geometry and conservative 0D coupling V1.

This is a bounded synthetic component foundation. It does not bind into a full
engine or change the historical P5/P6 paths.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
from typing import Any

from .gas1d.eos import IdealGas
from .reed import ReedPetal, ReedState
from .simulation import restriction


GEOMETRY_SCHEMA = "DYNAMIC_REED_HINGED_FLAP_GEOMETRY_V1"
STATE_SCHEMA = "DYNAMIC_REED_COUPLED_TWO_VOLUME_V1"
SPECIES = ("fresh_air", "fuel", "residual", "burned")


def _finite(value: Any, label: str) -> float:
    try:
        valid = type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        valid = False
    if not valid:
        raise ValueError(f"{label} must be finite numeric data")
    return float(value)


@dataclass(frozen=True)
class HingedFlapGeometryV1:
    id: str
    version: str
    provenance: str
    width_m: float
    length_m: float
    left_closed_volume_m3: float
    right_closed_volume_m3: float
    lift_stop_m: float
    discharge_coefficient: float

    def validate(self, petal: ReedPetal | None = None) -> None:
        if (not isinstance(self.id, str) or not isinstance(self.version, str) or
                not self.id.strip() or not self.version.strip()):
            raise ValueError("geometry id and version must be nonempty")
        if self.provenance != "SYNTHETIC_ASSUMPTION":
            raise ValueError("V1 hinged-flap geometry requires synthetic provenance")
        for name in ("width_m", "length_m", "left_closed_volume_m3",
                     "right_closed_volume_m3", "lift_stop_m"):
            if _finite(getattr(self, name), name) <= 0.0:
                raise ValueError(f"{name} must be positive")
        cd = _finite(self.discharge_coefficient, "discharge_coefficient")
        if not 0.0 < cd <= 1.0:
            raise ValueError("discharge_coefficient must be in (0, 1]")
        swept = self.swept_volume_area_m2
        if (self.left_closed_volume_m3 + swept * self.lift_stop_m <= 0.0 or
                self.right_closed_volume_m3 - swept * self.lift_stop_m <= 0.0):
            raise ValueError("adjacent swept control volumes must stay positive")
        if petal is not None:
            petal.validate()
            if not math.isclose(petal.effective_width_m, self.width_m,
                                rel_tol=1e-13, abs_tol=0.0):
                raise ValueError("petal flow width does not match declared geometry")
            if not math.isclose(petal.lift_stop_m, self.lift_stop_m,
                                rel_tol=1e-13, abs_tol=0.0):
                raise ValueError("petal lift stop does not match declared geometry")
            if not math.isclose(petal.discharge_coefficient,
                                self.discharge_coefficient,
                                rel_tol=1e-13, abs_tol=0.0):
                raise ValueError("petal discharge coefficient does not match geometry")
            if not math.isclose(petal.pressure_area_m2, swept,
                                rel_tol=1e-12, abs_tol=0.0):
                raise ValueError("pressure area must equal the declared swept-volume area")

    @property
    def swept_volume_area_m2(self) -> float:
        return self.width_m * self.length_m / 2.0

    def flow_area_m2(self, lift_m: float) -> float:
        lift = _finite(lift_m, "lift_m")
        if not 0.0 <= lift <= self.lift_stop_m:
            raise ValueError("lift is outside the declared geometry")
        return self.discharge_coefficient * self.width_m * lift

    def volumes_m3(self, lift_m: float) -> tuple[float, float]:
        return self.volumes_from_base_m3(self.left_closed_volume_m3,
                                         self.right_closed_volume_m3, lift_m)

    def volumes_from_base_m3(self, left_base_m3: float, right_base_m3: float,
                             lift_m: float) -> tuple[float, float]:
        left_base = _finite(left_base_m3, "left_base_m3")
        right_base = _finite(right_base_m3, "right_base_m3")
        lift = _finite(lift_m, "lift_m")
        if not 0.0 <= lift <= self.lift_stop_m:
            raise ValueError("lift is outside the declared geometry")
        area = self.swept_volume_area_m2
        left = left_base + area * lift
        right = right_base - area * lift
        if left <= 0.0 or right <= 0.0:
            raise ValueError("reed displacement leaves a nonpositive control volume")
        return left, right

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return {"schema": GEOMETRY_SCHEMA, "id": self.id, "version": self.version,
                "provenance": self.provenance, "width_m": self.width_m,
                "length_m": self.length_m,
                "left_closed_volume_m3": self.left_closed_volume_m3,
                "right_closed_volume_m3": self.right_closed_volume_m3,
                "lift_stop_m": self.lift_stop_m,
                "discharge_coefficient": self.discharge_coefficient,
                "flow_area_law": "CD_WIDTH_TIMES_LIFT_V1",
                "swept_volume_law": "LINEAR_HINGED_FLAP_WIDTH_LENGTH_OVER_2_V1"}

    @classmethod
    def from_dict(cls, value: Any) -> "HingedFlapGeometryV1":
        fields = {"schema", "id", "version", "provenance", "width_m", "length_m",
                  "left_closed_volume_m3", "right_closed_volume_m3", "lift_stop_m",
                  "discharge_coefficient", "flow_area_law", "swept_volume_law"}
        if (not isinstance(value, dict) or set(value) != fields or
                value.get("schema") != GEOMETRY_SCHEMA or
                value.get("flow_area_law") != "CD_WIDTH_TIMES_LIFT_V1" or
                value.get("swept_volume_law") != "LINEAR_HINGED_FLAP_WIDTH_LENGTH_OVER_2_V1"):
            raise ValueError("unsupported dynamic reed geometry schema/law")
        result = cls(**{key: value[key] for key in fields - {
            "schema", "flow_area_law", "swept_volume_law"}})
        result.validate()
        return result


@dataclass(frozen=True)
class GasVolumeState4:
    mass_kg: float
    internal_energy_J: float
    species_mass_kg: tuple[float, float, float, float]

    def validate(self) -> None:
        mass = _finite(self.mass_kg, "mass_kg")
        energy = _finite(self.internal_energy_J, "internal_energy_J")
        if mass <= 0.0 or energy <= 0.0:
            raise ValueError("gas volume mass and internal energy must be positive")
        if not isinstance(self.species_mass_kg, tuple) or len(self.species_mass_kg) != 4:
            raise ValueError("exactly four extensive species are required")
        species = tuple(_finite(x, "species_mass_kg") for x in self.species_mass_kg)
        if any(x < 0.0 for x in species):
            raise ValueError("species mass cannot be negative")
        if not math.isclose(math.fsum(species), mass, rel_tol=2e-13,
                            abs_tol=2e-15 * max(1.0, mass)):
            raise ValueError("four-species mass must equal total gas mass")


class DynamicReedTwoVolumeCouplingV1:
    """One SSPRK2 state for two 0D gas volumes and one moving reed petal."""

    def __init__(self, geometry: HingedFlapGeometryV1, petal: ReedPetal,
                 left: GasVolumeState4, right: GasVolumeState4,
                 reed: ReedState, *, eos: IdealGas | None = None):
        if not isinstance(geometry, HingedFlapGeometryV1):
            raise ValueError("geometry must be HingedFlapGeometryV1")
        if not isinstance(petal, ReedPetal):
            raise ValueError("petal must be ReedPetal")
        geometry.validate(petal)
        self.geometry = geometry
        self.petal = petal
        self.eos = eos or IdealGas()
        if not isinstance(self.eos, IdealGas):
            raise ValueError("eos must be IdealGas")
        left.validate()
        right.validate()
        self._validate_reed(reed)
        self._state = (left.mass_kg, left.internal_energy_J, *left.species_mass_kg,
                       right.mass_kg, right.internal_energy_J, *right.species_mass_kg,
                       reed.position_m, reed.velocity_m_s, 0.0)
        self._initial_mass = left.mass_kg + right.mass_kg
        self._initial_species = tuple(a + b for a, b in
                                      zip(left.species_mass_kg, right.species_mass_kg))
        self._initial_energy = self._gas_energy(self._state) + self._reed_energy(self._state)
        self.validate()

    @property
    def state(self) -> tuple:
        return tuple(self._state)

    def _validate_reed(self, reed: ReedState) -> None:
        if not isinstance(reed, ReedState):
            raise ValueError("reed state must use ReedState")
        x = _finite(reed.position_m, "reed.position_m")
        v = _finite(reed.velocity_m_s, "reed.velocity_m_s")
        if not 0.0 <= x <= self.geometry.lift_stop_m:
            raise ValueError("reed lift is outside the registered range")
        if (x == 0.0 and v < 0.0) or (x == self.geometry.lift_stop_m and v > 0.0):
            raise ValueError("reed velocity points outside its registered range")
        self.geometry.volumes_m3(x)

    @staticmethod
    def _unpack(state: tuple):
        return (state[0], state[1], tuple(state[2:6]),
                state[6], state[7], tuple(state[8:12]), state[12], state[13], state[14])

    def _thermo(self, mass: float, energy: float, volume: float):
        if mass <= 0.0 or energy <= 0.0 or volume <= 0.0:
            raise ValueError("inadmissible coupled gas volume")
        pressure = (self.eos.gamma - 1.0) * energy / volume
        temperature = energy / (mass * self.eos.cv)
        if not all(math.isfinite(x) and x > 0.0 for x in (pressure, temperature)):
            raise ValueError("inadmissible coupled gas thermodynamics")
        return pressure, temperature

    def _rhs(self, state: tuple) -> tuple[float, ...]:
        ml, ul, yl, mr, ur, yr, x, v, diss = self._unpack(state)
        if not all(math.isfinite(value) for value in state):
            raise ValueError("nonfinite dynamic reed coupled state")
        left_volume, right_volume = self.geometry.volumes_m3(x)
        pl, tl = self._thermo(ml, ul, left_volume)
        pr, tr = self._thermo(mr, ur, right_volume)
        # The third tuple value is only the legacy restriction helper's passive
        # diagnostic. Four-species fluxes below always use actual donor state.
        fresh_l = (yl[0] + yl[1]) / ml
        fresh_r = (yr[0] + yr[1]) / mr
        mdot, enthalpy_rate, _ = restriction(
            (pl, tl, fresh_l), (pr, tr, fresh_r),
            self.geometry.width_m * x, self.geometry.discharge_coefficient,
            self.eos.R, self.eos.gamma)
        if mdot > 0.0:
            donor, donor_mass = yl, ml
        elif mdot < 0.0:
            donor, donor_mass = yr, mr
        else:
            donor, donor_mass = (0.0,) * 4, 1.0
        species_flux = tuple(mdot * species / donor_mass for species in donor)
        sweep = self.geometry.swept_volume_area_m2
        pressure_force = (pl - pr) * sweep
        reed_accel = (pressure_force - self.petal.stiffness_n_m * x -
                      self.petal.damping_n_s_m * v) / self.petal.mass_kg
        dx = v
        # Contact/impact mechanics are not part of this contract. Reject an
        # outward force at rest on a stop instead of silently constraining it.
        if x == 0.0 and v == 0.0 and reed_accel < 0.0:
            raise ValueError("dynamic reed stop contact requires a versioned event contract")
        elif x == self.geometry.lift_stop_m and v == 0.0 and reed_accel > 0.0:
            raise ValueError("dynamic reed stop contact requires a versioned event contract")
        work_left = -pl * sweep * dx
        work_right = pr * sweep * dx
        return (-mdot, -enthalpy_rate + work_left, *(-q for q in species_flux),
                mdot, enthalpy_rate + work_right, *species_flux,
                dx, reed_accel, self.petal.damping_n_s_m * v * v)

    def _validate_state(self, state: tuple) -> None:
        if not isinstance(state, tuple) or len(state) != 15:
            raise ValueError("invalid dynamic reed coupled state shape")
        for index, value in enumerate(state):
            _finite(value, f"state[{index}]")
        ml, ul, yl, mr, ur, yr, x, v, diss = self._unpack(state)
        GasVolumeState4(ml, ul, yl).validate()
        GasVolumeState4(mr, ur, yr).validate()
        self._validate_reed(ReedState(x, v))
        if _finite(diss, "reed_dissipation_J") < 0.0:
            raise ValueError("reed dissipation ledger cannot decrease")
        lv, rv = self.geometry.volumes_m3(x)
        self._thermo(ml, ul, lv)
        self._thermo(mr, ur, rv)

    def validate(self) -> None:
        self._validate_state(self._state)

    @staticmethod
    def _euler(state: tuple, rhs: tuple[float, ...], dt: float) -> tuple:
        return tuple(value + dt * rate for value, rate in zip(state, rhs))

    def step(self, dt_s: float) -> tuple:
        dt = _finite(dt_s, "dt_s")
        if dt <= 0.0:
            raise ValueError("dt_s must be positive")
        original = self._state
        k1 = self._rhs(original)
        stage = self._euler(original, k1, dt)
        self._validate_state(stage)
        k2 = self._rhs(stage)
        candidate = tuple(0.5 * old + 0.5 * (mid + dt * rate)
                          for old, mid, rate in zip(original, stage, k2))
        self._validate_state(candidate)
        self._state = candidate
        return self._state

    def _gas_energy(self, state: tuple) -> float:
        ml, ul, _, mr, ur, _, _, _, _ = self._unpack(state)
        return ul + ur

    def _reed_energy(self, state: tuple) -> float:
        *_, x, v, _diss = self._unpack(state)
        return 0.5 * self.petal.mass_kg * v * v + 0.5 * self.petal.stiffness_n_m * x * x

    def ledger(self) -> dict[str, Any]:
        self.validate()
        state = self._state
        ml, ul, yl, mr, ur, yr, x, v, diss = self._unpack(state)
        masses = tuple(a + b for a, b in zip(yl, yr))
        return {
            "mass_initial_kg": self._initial_mass,
            "mass_current_kg": ml + mr,
            "mass_residual_kg": ml + mr - self._initial_mass,
            "species_initial_kg": list(self._initial_species),
            "species_current_kg": list(masses),
            "species_residual_kg": [now - initial for now, initial in
                                    zip(masses, self._initial_species)],
            "species_sum_residual_kg": math.fsum(masses) - ml - mr,
            "gas_energy_J": ul + ur,
            "reed_stored_energy_J": self._reed_energy(state),
            "reed_dissipation_J": diss,
            "total_energy_residual_J": (ul + ur + self._reed_energy(state) + diss -
                                         self._initial_energy),
            "lift_m": x, "velocity_m_s": v,
            "left_volume_m3": self.geometry.volumes_m3(x)[0],
            "right_volume_m3": self.geometry.volumes_m3(x)[1],
            "flow_area_m2": self.geometry.flow_area_m2(x),
        }

    def checkpoint(self) -> dict[str, Any]:
        self.validate()
        state_data = list(self._state)
        return {
            "schema": STATE_SCHEMA,
            "geometry": self.geometry.to_dict(),
            "geometry_sha256": hashlib.sha256(_canonical(self.geometry.to_dict())).hexdigest(),
            "petal": self.petal.to_dict(),
            "eos": {"R": self.eos.R, "gamma": self.eos.gamma},
            "state": state_data,
            "state_sha256": hashlib.sha256(_canonical(state_data)).hexdigest(),
            "initial_mass_kg": self._initial_mass,
            "initial_species_kg": list(self._initial_species),
            "initial_energy_J": self._initial_energy,
        }

    def restore(self, checkpoint: Any) -> None:
        if not isinstance(checkpoint, dict) or checkpoint.get("schema") != STATE_SCHEMA:
            raise ValueError("invalid dynamic reed coupled checkpoint schema")
        expected = (self.geometry.to_dict(), self.petal.to_dict(),
                    {"R": self.eos.R, "gamma": self.eos.gamma})
        actual = (checkpoint.get("geometry"), checkpoint.get("petal"), checkpoint.get("eos"))
        if actual != expected:
            raise ValueError("dynamic reed coupled checkpoint configuration mismatch")
        if hashlib.sha256(_canonical(actual[0])).hexdigest() != checkpoint.get("geometry_sha256"):
            raise ValueError("dynamic reed geometry identity hash mismatch")
        state_data = checkpoint.get("state", ())
        if (not isinstance(state_data, list) or
                hashlib.sha256(_canonical(state_data)).hexdigest() !=
                checkpoint.get("state_sha256")):
            raise ValueError("dynamic reed coupled state hash mismatch")
        state = tuple(state_data)
        self._validate_state(state)
        initial_mass = _finite(checkpoint.get("initial_mass_kg"), "initial_mass_kg")
        initial_species = checkpoint.get("initial_species_kg")
        initial_energy = _finite(checkpoint.get("initial_energy_J"), "initial_energy_J")
        if (not isinstance(initial_species, list) or len(initial_species) != 4 or
                any(_finite(x, "initial_species_kg") < 0.0 for x in initial_species)):
            raise ValueError("invalid dynamic reed initial species ledger")
        if initial_mass <= 0.0 or initial_energy <= 0.0:
            raise ValueError("dynamic reed initial totals must be positive")
        if not math.isclose(math.fsum(initial_species), initial_mass,
                            rel_tol=2e-13, abs_tol=2e-15 * max(1.0, initial_mass)):
            raise ValueError("dynamic reed initial species do not sum to initial mass")
        ml, ul, yl, mr, ur, yr, *_ = self._unpack(state)
        current_mass = ml + mr
        current_species = tuple(a + b for a, b in zip(yl, yr))
        if not math.isclose(current_mass, initial_mass, rel_tol=2e-13,
                            abs_tol=2e-15 * max(1.0, initial_mass)):
            raise ValueError("dynamic reed checkpoint global mass mismatch")
        if any(not math.isclose(now, initial, rel_tol=2e-13,
                                abs_tol=2e-15 * max(1.0, initial_mass))
               for now, initial in zip(current_species, initial_species)):
            raise ValueError("dynamic reed checkpoint global species mismatch")
        total_energy = (ul + ur + self._reed_energy(state) + state[-1])
        if not math.isclose(total_energy, initial_energy, rel_tol=2e-12,
                            abs_tol=2e-14 * max(1.0, initial_energy)):
            raise ValueError("dynamic reed checkpoint global energy mismatch")
        self._state = state
        self._initial_mass = initial_mass
        self._initial_species = tuple(initial_species)
        self._initial_energy = initial_energy


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      allow_nan=False).encode("utf-8")
