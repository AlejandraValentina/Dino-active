"""Deterministic analytical P9 pipeline fixtures; never MotorSim predictions."""

from __future__ import annotations

import csv
import gzip
import hashlib
import json
import math
import argparse
from pathlib import Path

from .p9_pipeline import SCHEMA, SYNTHETIC_FLAGS, SYNTHETIC_LABEL, geometry_volumes_m3

RPM_POINTS = (3000, 4500, 6000, 7500, 9000, 10500, 12000)
CYCLES = 50
swept_cm3 = math.pi * 50.0**2 * 50.0 / 4000.0
clearance_cm3 = swept_cm3 / (8.0 - 1.0)
GEOMETRY = {
    "bore_mm": 50.0, "stroke_mm": 50.0, "rod_length_mm": 100.0,
    "displacement_cm3": math.pi * 50.0**2 * 50.0 / 4000.0,
    "compression_ratio": 8.0, "cylinders": 1,
    "reference_volumes_cm3": {"tdc": clearance_cm3,
                               "bdc": clearance_cm3 + swept_cm3,
                               "swept": swept_cm3},
    "reference_volume": "cylinder volume from slider-crank geometry",
    "geometry_origin": SYNTHETIC_LABEL,
}
_PROFILE = (0.72, 0.85, 0.96, 1.00, 0.97, 0.87, 0.70)
_PASS_SCALE = (1.04, 1.06, 0.97, 1.03, 1.08, 0.96, 0.98)
_FAIL_SCALE = (1.04, 1.06, 1.26, 1.03, 1.08, 0.96, 0.98)


def _canonical(value) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()


def _pressures(rpm: int, cycle: int, series: str, scale: float) -> list[float]:
    index = RPM_POINTS.index(rpm)
    profile = _PROFILE[index]
    amplitude = 3_400_000.0 * profile * (scale if series == "simulation" else 1.0)
    angles = list(range(361))
    volume = geometry_volumes_m3(GEOMETRY, [float(x) for x in angles])
    v_bdc = max(volume)
    phase = cycle * 0.17
    cycle_factor = 1.0 + 0.00035 * math.sin(phase) + 0.00008 * math.cos(phase * 0.37)
    values = []
    for angle, vol in zip(angles, volume):
        base = 101_325.0 * (v_bdc / vol) ** 1.25
        # Smooth low-pressure scavenging/exhaust interval, deliberately simple.
        scavenging = 1.0 - 0.31 * math.exp(-0.5 * ((angle - 180.0) / 48.0) ** 4)
        combustion = amplitude * math.exp(-0.5 * ((angle - 12.0) / 10.0) ** 2)
        # Small deterministic acquisition variation; endpoints remain periodic.
        ripple = 1.0 + 0.00015 * math.sin(math.radians(angle * 4) + phase)
        values.append((base * scavenging + combustion) * cycle_factor * ripple)
    values[-1] = values[0]
    return values


def _write_series(path: Path, series: str, scales: tuple[float, ...]) -> dict:
    with path.open("wb") as binary:
        with gzip.GzipFile(fileobj=binary, mode="wb", filename="", mtime=0) as zipped:
            import io
            text = io.TextIOWrapper(zipped, encoding="utf-8", newline="")
            writer = csv.writer(text, lineterminator="\n")
            writer.writerow(("rpm", "cycle", "angle_deg", "pressure_pa"))
            for rpm, scale in zip(RPM_POINTS, scales):
                for cycle in range(CYCLES):
                    for angle, pressure in enumerate(_pressures(rpm, cycle, series, scale)):
                        writer.writerow((rpm, cycle, angle, format(pressure, ".12g")))
            text.flush()
            # Detach so the caller can close the gzip stream only once.
            text.detach()
    content = path.read_bytes()
    return {"path": path.name, "size_bytes": len(content),
            "sha256": hashlib.sha256(content).hexdigest(),
            "role": "experiment_raw" if series == "experiment" else "simulation_primary",
            "media_type": "text/csv+gzip",
            "units": {"rpm": "rev/min", "angle": "degCA", "pressure": "Pa",
                      "pressure_reference": "ABSOLUTE"}}


def generate_fixture(directory: str | Path, scenario: str) -> Path:
    """Generate one PASS/FAIL/INCONCLUSIVE fixture reproducibly, without MotorSim."""
    if scenario not in {"pass", "fail", "inconclusive"}:
        raise ValueError("scenario must be pass, fail, or inconclusive")
    root = Path(directory)
    root.mkdir(parents=True, exist_ok=True)
    exp_file = _write_series(root / "experiment.csv.gz", "experiment", (1.0,) * len(RPM_POINTS))
    scales = _FAIL_SCALE if scenario == "fail" else _PASS_SCALE
    sim_file = _write_series(root / "simulation_primary.csv.gz", "simulation", scales)
    gates = {key: True for key in (
        "periodic_state", "finite_state", "geometry", "admissibility", "species",
        "cfl", "mass_conservation", "energy_conservation", "species_conservation",
        "p7_nonvacuous", "p7_source_admissibility", "restart", "deterministic_replay")}
    points = [{
        "rpm": rpm, "simulation_rpm": rpm, "p9a": {"period": 1, "cycles": CYCLES, "gates": dict(gates)},
        # Deliberately untrusted claims prove the auditor recomputes from raw.
        "claimed_work_exp_j": -999.0, "claimed_relative_error": 0.0,
    } for rpm in RPM_POINTS]
    manifest = {
        "schema": SCHEMA, "dataset_kind": "SYNTHETIC", "experimental_dataset_required": True,
        "configuration_kind": "FIXED_2T",
        "synthetic_label": SYNTHETIC_LABEL, "synthetic_flags": dict(SYNTHETIC_FLAGS),
        "scenario": scenario, "generator": "motorsim.p9_synthetic.generate_fixture",
        "seed": "deterministic-analytic-no-randomness-v1",
        "provenance": {"source_type": "SYNTHETIC_ANALYTIC", "authorized": False,
                       "description": "independent analytical virtual experiment; no MotorSim run"},
        "geometry": dict(GEOMETRY),
        "angle_convention": {"cycle_deg": 360, "zero": "TDC", "direction": "forward"},
        "channels": {"pressure": "cylinder pressure", "rpm": "operating speed", "angle": "crank angle"},
        "cycles_per_point": CYCLES,
        "uncertainty": {"label": SYNTHETIC_LABEL, "pressure_standard_uncertainty_pa": 4500.0,
                        "crank_angle_standard_uncertainty_deg": 0.08,
                        "cycle_variation_fraction": 0.0004, "cycle_count": CYCLES},
        "operating_points": points,
        "raw_files": [exp_file, sim_file],
        "untrusted_claimed_summary": {"mape": 0.0, "status": "P9_PASS"},
    }
    if scenario == "inconclusive":
        manifest["geometry"] = None
    (root / "manifest.json").write_bytes(_canonical(manifest))
    return root


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Generate deterministic P9 synthetic qualification fixtures")
    parser.add_argument("output", type=Path, help="directory receiving pass/fail/inconclusive fixture folders")
    args = parser.parse_args(argv)
    for scenario in ("pass", "fail", "inconclusive"):
        print(generate_fixture(args.output / f"synthetic_{scenario}", scenario))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
