"""Bounded, isolated mesh diagnostic for an expansion chamber and transfer duct."""
from __future__ import annotations

import json
from math import exp, fsum
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from motorsim.expansion_chamber import ChamberSection, ExpansionChamber
from motorsim.gas1d.boundary import Boundary
from motorsim.gas1d.eos import IdealGas
from motorsim.gas1d.mesh import uniform_mesh
from motorsim.gas1d.solver import solve


CHAMBER = ExpansionChamber((
    ChamberSection("header", "header", 80.0, 20.0, 20.0),
    ChamberSection("diffuser", "diffuser", 180.0, 20.0, 52.0),
    ChamberSection("belly", "belly", 100.0, 52.0, 52.0),
    ChamberSection("baffle", "baffle_cone", 170.0, 52.0, 16.0),
    ChamberSection("stinger", "stinger", 120.0, 16.0, 16.0),
))
BASE_PRESSURE_PA = 100_000.0
BASE_TEMPERATURE_K = 300.0
PULSE_AMPLITUDE_PA = 500.0


def _case(mesh, eos: IdealGas, *, length: float, final_time: float, cells: int,
          sensor_x: float) -> dict[str, Any]:
    states = []
    for x in mesh.centers:
        pulse = exp(-((x - 0.25 * length) / (0.035 * length)) ** 2)
        pressure = BASE_PRESSURE_PA + PULSE_AMPLITUDE_PA * pulse
        rho = pressure / (eos.R * BASE_TEMPERATURE_K)
        states.append((rho, 0.0, pressure, 0.0))
    initial = [tuple(volume * value for value in eos.conservative(state))
               for volume, state in zip(mesh.volumes, states)]
    sample_interval = final_time / 40.0
    result = solve(mesh, initial, final_time,
                   (Boundary("wall"), Boundary("wall")), eos=eos, cfl=0.4,
                   sample_interval=sample_interval, sensor=sensor_x)
    if result["status"] != "completed":
        raise RuntimeError(f"{cells}-cell mesh failed: {result['status']} {result['reason']}")
    residual_max = [max(abs(row["normalized"][k]) for row in result["ledger"])
                    for k in range(4)]
    signal = result["sensors"]
    pressure_delta = [row[1] - BASE_PRESSURE_PA for row in signal]
    initial_delta = pressure_delta[0]
    arrival = next((row[0] for row, dp in zip(signal, pressure_delta)
                    if dp - initial_delta >= 10.0), None)
    inventory_mass = fsum(mesh.volumes)
    return {
        "cells": cells,
        "dx_min_m": min(mesh.widths),
        "dx_max_m": max(mesh.widths),
        "mesh_volume_m3": inventory_mass,
        "completed_time_s": result["time"],
        "steps": result["steps"],
        "max_cfl": result["max_CFL"],
        "rejected_steps": result["rejected_steps"],
        "sensor_x_m": sensor_x,
        "sensor_initial_pressure_delta_pa": initial_delta,
        "sensor_first_sample_over_10pa_s": arrival,
        "sensor_peak_pressure_delta_pa": max(pressure_delta),
        "sensor_peak_increment_from_initial_pa": max(pressure_delta) - initial_delta,
        "sensor_trace": [[float(t), float(p)] for t, p in signal],
        "max_normalized_ledger_residual": residual_max,
    }


def run_mesh_study() -> dict[str, Any]:
    eos = IdealGas()
    chamber_length = CHAMBER.length_mm / 1000.0
    sound_speed = eos.sound_speed((BASE_PRESSURE_PA / (eos.R * BASE_TEMPERATURE_K),
                                   0.0, BASE_PRESSURE_PA, 0.0))
    cases = []
    chamber_rows = []
    for dx in (0.13, 0.02, 0.01, 0.005):
        mesh = CHAMBER.mesh(dx)
        final_time = 0.35 * chamber_length / sound_speed
        row = _case(mesh, eos, length=chamber_length, final_time=final_time,
                    cells=mesh.n, sensor_x=0.65 * chamber_length)
        row["dx_target_m"] = dx
        chamber_rows.append(row)
    cases.append({"component": "synthetic_expansion_chamber_from_existing_fixture",
                  "geometry": CHAMBER.to_dict(), "mesh_study": chamber_rows})

    transfer_length = 0.05
    transfer_area = 1e-4
    transfer_rows = []
    for count in (2, 4, 8, 16, 32):
        mesh = uniform_mesh(count, length=transfer_length, area=transfer_area)
        final_time = 0.35 * transfer_length / sound_speed
        transfer_rows.append(_case(mesh, eos, length=transfer_length,
                                   final_time=final_time, cells=count,
                                   sensor_x=0.65 * transfer_length))
    cases.append({"component": "straight_synthetic_transfer_duct",
                  "length_m": transfer_length, "area_m2": transfer_area,
                  "mesh_study": transfer_rows})

    return {
        "schema": "AUD13_MESH_DIAGNOSTIC_V1",
        "classification": "DIAGNOSTIC_NO_ACCEPTANCE_THRESHOLD_REGISTERED",
        "solver": "existing gas1d first-order finite-volume Forward Euler / HLLC",
        "boundary": "closed wall at both ends; no reservoir or KT100 data",
        "initial_condition": {
            "base_pressure_pa": BASE_PRESSURE_PA,
            "base_temperature_k": BASE_TEMPERATURE_K,
            "pressure_pulse_amplitude_pa": PULSE_AMPLITUDE_PA,
            "pulse_center_fraction": 0.25,
            "pulse_width_fraction": 0.035,
            "cfl": 0.4,
            "duration_fraction_of_length_over_sound_speed": 0.35,
        },
        "eos": {"R_J_kgK": eos.R, "gamma": eos.gamma},
        "cases": cases,
        "interpretation": (
            "This isolated fixed-time study records resolution sensitivity and "
            "conservation only. It does not validate the integrated engine, "
            "identify a sufficient mesh, or establish physical accuracy."
        ),
    }


def write_mesh_study(path: str | Path) -> dict[str, Any]:
    result = run_mesh_study()
    Path(path).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    write_mesh_study(args.output)
