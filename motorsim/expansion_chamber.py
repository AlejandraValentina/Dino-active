"""Configurable two-stroke exhaust chamber geometry and 1D result adapter.

Geometry is discretized by the existing quasi-1D mesh builder. This module
does not solve gas dynamics: pressure, Mach and flow outputs are mapped from
the actual primitive states produced by the existing gas1d solver.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from bisect import bisect_left
from typing import Any

from .gas1d.eos import IdealGas
from .gas1d.mesh import Mesh, segments_mesh

SCHEMA = "EXPANSION_CHAMBER_GEOMETRY_V1"
KINDS = {"header", "diffuser", "belly", "baffle_cone", "stinger",
         "silencer", "tailpipe", "conical"}


def _number(value: Any, label: str) -> float:
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError(f"{label} must be finite numeric data, excluding booleans")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{label} is outside the supported numeric range")
    return result


@dataclass(frozen=True)
class ChamberSection:
    name: str
    kind: str
    length_mm: float
    inlet_diameter_mm: float
    outlet_diameter_mm: float
    provenance: str = "SYNTHETIC_ASSUMPTION"

    def validate(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("Each expansion section needs a name")
        if not isinstance(self.kind, str) or self.kind not in KINDS:
            raise ValueError(f"Unsupported expansion section kind: {self.kind}")
        for field in ("length_mm", "inlet_diameter_mm", "outlet_diameter_mm"):
            if _number(getattr(self, field), f"{self.name}.{field}") <= 0:
                raise ValueError(f"{self.name}.{field} must be positive")
        if not isinstance(self.provenance, str) or self.provenance not in {"DOCUMENTED", "DERIVED_FROM_DOCUMENTED",
                                   "SYNTHETIC_ASSUMPTION", "UNKNOWN"}:
            raise ValueError(f"{self.name}.provenance is invalid")

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return {"name": self.name, "kind": self.kind, "length_mm": self.length_mm,
                "inlet_diameter_mm": self.inlet_diameter_mm,
                "outlet_diameter_mm": self.outlet_diameter_mm,
                "provenance": self.provenance}

    @classmethod
    def from_dict(cls, value: Any) -> "ChamberSection":
        fields = {"name", "kind", "length_mm", "inlet_diameter_mm",
                  "outlet_diameter_mm", "provenance"}
        if not isinstance(value, dict) or set(value) != fields:
            raise ValueError("Expansion section has missing or unexpected fields")
        result = cls(**value)
        result.validate()
        return result


@dataclass(frozen=True)
class ExpansionChamber:
    sections: tuple[ChamberSection, ...]

    def validate(self) -> None:
        if not isinstance(self.sections, tuple) or not self.sections:
            raise ValueError("An expansion chamber needs one or more sections")
        if any(not isinstance(section, ChamberSection) for section in self.sections):
            raise ValueError("Expansion geometry contains an invalid section")
        for section in self.sections:
            section.validate()
        for left, right in zip(self.sections, self.sections[1:]):
            if not math.isclose(left.outlet_diameter_mm, right.inlet_diameter_mm,
                                rel_tol=1e-12, abs_tol=1e-12):
                raise ValueError(f"Disconnected expansion sections: {left.name}/{right.name}")

    @property
    def length_mm(self) -> float:
        self.validate()
        return math.fsum(section.length_mm for section in self.sections)

    def mesh(self, dx_target_m: float) -> Mesh:
        self.validate()
        return segments_mesh([{"length": section.length_mm,
                               "start_diameter": section.inlet_diameter_mm,
                               "end_diameter": section.outlet_diameter_mm}
                              for section in self.sections], dx_target_m)

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return {"schema": SCHEMA, "sections": [section.to_dict()
                                               for section in self.sections]}

    @classmethod
    def from_dict(cls, value: Any) -> "ExpansionChamber":
        if (not isinstance(value, dict) or set(value) != {"schema", "sections"}
                or value["schema"] != SCHEMA or not isinstance(value["sections"], list)):
            raise ValueError("Expansion chamber schema is invalid")
        result = cls(tuple(ChamberSection.from_dict(row) for row in value["sections"]))
        result.validate()
        return result


def map_solver_state(mesh: Mesh, primitives: tuple, *, eos: IdealGas | None = None,
                     base_primitives: tuple | None = None) -> dict[str, Any]:
    """Map an actual 1D solution to engineering traces and acoustic signals.

    ``pressure_wave_pa`` is the solver pressure trace. Optional ``linear_acoustic``
    values are a small-perturbation isentropic decomposition around explicitly
    supplied base states; they are not used as a nonlinear wave solution.
    """
    gas = eos or IdealGas()
    if len(primitives) != mesh.n:
        raise ValueError("The state count must match the expansion mesh")
    if base_primitives is not None and len(base_primitives) != mesh.n:
        raise ValueError("The base-state count must match the expansion mesh")
    rows = []
    for index, (state, width, volume) in enumerate(zip(primitives, mesh.widths, mesh.volumes)):
        try:
            rho, velocity, pressure, species = gas.validate(tuple(
                _number(value, f"cell[{index}].primitive") for value in state))
        except (TypeError, ValueError) as error:
            raise ValueError(f"Invalid expansion state at cell {index}: {error}") from error
        area = volume / width
        temperature = pressure / (rho * gas.R)
        sound = gas.sound_speed((rho, velocity, pressure, species))
        row = {"x_m": mesh.centers[index], "area_m2": area, "density_kg_m3": rho,
               "velocity_m_s": velocity, "pressure_wave_pa": pressure,
               "temperature_K": temperature, "mach": velocity / sound,
               "mass_flow_kg_s": rho * velocity * area,
               "characteristic_right_m_s": velocity + sound,
               "characteristic_left_m_s": velocity - sound}
        if base_primitives is not None:
            base = gas.validate(tuple(_number(value, f"base[{index}].primitive")
                                      for value in base_primitives[index]))
            rho0, u0, p0, _ = base
            a0 = gas.sound_speed(base)
            dp, du = pressure - p0, velocity - u0
            acoustic = 0.5 * (dp + rho0 * a0 * du)
            row["linear_acoustic"] = {"right_pressure_perturbation_pa": acoustic,
                                      "left_pressure_perturbation_pa": 0.5 * (dp - rho0 * a0 * du),
                                      "base_state_isentropic_small_signal": True}
        rows.append(row)

    right_times = []
    left_times = []
    right_total = left_total = 0.0
    left_reachable = True
    for row, width in zip(rows, mesh.widths):
        right_speed = row["characteristic_right_m_s"]
        left_speed = -row["characteristic_left_m_s"]
        right_total += width / right_speed if right_speed > 0 else math.inf
        right_times.append(right_total if math.isfinite(right_total) else None)
    left_reachable = True
    for row, width in reversed(list(zip(rows, mesh.widths))):
        left_speed = -row["characteristic_left_m_s"]
        if left_speed > 0 and left_reachable:
            left_total += width / left_speed
        else:
            left_reachable = False
            left_total = math.inf
        left_times.append(left_total if math.isfinite(left_total) else None)
    left_times.reverse()
    return {"schema": "EXPANSION_CHAMBER_TRACE_V1", "cells": rows,
            "right_characteristic_travel_time_s": right_times,
            "left_characteristic_travel_time_s": left_times,
            "interpretation": "solver trace; linear decomposition only when a base is supplied"}


def reflection_timing_estimates(mesh: Mesh, trace: dict[str, Any],
                                locations_m: tuple[float, ...]) -> tuple[dict[str, Any], ...]:
    """Estimate acoustic arrival/return times at supplied geometric stations.

    These are characteristic travel times from the actual base flow, not
    predicted reflected amplitudes. The quasi-1D solver supplies those waves.
    """
    cells = trace.get("cells") if isinstance(trace, dict) else None
    if not isinstance(cells, list) or len(cells) != mesh.n:
        raise ValueError("A compatible solver trace is required")
    estimates = []
    for location in locations_m:
        x = _number(location, "reflection_location_m")
        if not mesh.faces[0] < x < mesh.faces[-1]:
            raise ValueError("Reflection stations must be inside the duct")
        face = bisect_left(mesh.faces, x)
        if face == len(mesh.faces) or mesh.faces[face] != x:
            face = max(1, min(mesh.n - 1, bisect_left(mesh.faces, x)))
            x = mesh.faces[face]
        incident = returned = 0.0
        valid = True
        for index in range(face):
            width = mesh.widths[index]
            row = cells[index]
            right_speed = row["characteristic_right_m_s"]
            left_speed = -row["characteristic_left_m_s"]
            if right_speed <= 0 or left_speed <= 0:
                valid = False
                break
            incident += width / right_speed
            returned += width / left_speed
        estimates.append({"location_m": x,
                          "incident_arrival_s": incident if valid else None,
                          "return_to_inlet_s": incident + returned if valid else None,
                          "status": "ESTIMATED_FROM_CHARACTERISTICS" if valid else "NO_UPSTREAM_ACOUSTIC_PATH"})
    return tuple(estimates)
