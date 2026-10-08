"""Bounded initialization diagnostic; this is not an executable V2 fixture."""
from __future__ import annotations

import json
from pathlib import Path

from motorsim.gas1d.eos import IdealGas
from motorsim.kt100_reference import fixture_case
from motorsim.p5c import make_p5c_full_fixture
from motorsim.p6_species import P6IntegratedSystem, legacy_to_species
from motorsim.p8_performance import model_geometry_callback, omega_deg_s
from motorsim.simulation import Model


def diagnose() -> dict:
    case = fixture_case(5000)
    model = Model(case, external_band_pa=100)
    gas = make_p5c_full_fixture(eos=IdealGas(R=287.0, gamma=1.35), cells=2)
    gas.geometry_callback = model_geometry_callback(model)
    gas.core.geometry_callback = gas.geometry_callback
    gas.angle = case.initial_angle_deg

    volumes = model.geometry(case.initial_angle_deg)[0]
    for chamber, pty, volume in (
        (gas.core.crankcase, case.initial_pty[1], volumes[1]),
        (gas.core.cylinder, case.initial_pty[2], volumes[2]),
    ):
        pressure, temperature, fresh_fraction = pty
        chamber.volume = volume
        chamber.primitive = (
            pressure / (gas.eos.R * temperature), 0.0, pressure,
            float(fresh_fraction),
        )
    gas.core._initial = gas.core._totals()
    gas._initial = gas.totals()
    gas._previous_totals = dict(gas._initial)

    def fractions(mass: float, fresh_fraction: float) -> tuple[float, ...]:
        return tuple(value / mass for value in
                     legacy_to_species(mass, float(fresh_fraction)))

    components = {
        "crankcase": [fractions(gas.core.crankcase.inventory(gas.eos)[0], 1.0)],
        "cylinder": [fractions(gas.core.cylinder.inventory(gas.eos)[0], 0.0)],
    }
    for name, path in (
        ("intake", gas.core.intake),
        ("tr1", gas.core.transfers[0]),
        ("tr2", gas.core.transfers[1]),
        ("exhaust", gas.exhaust),
    ):
        components[name] = [
            fractions(q[0] * volume, q[3] / q[0])
            for q, volume in zip(path.conservative(), path.mesh.volumes)
        ]

    system = P6IntegratedSystem(
        gas, component_species=components, capture_trace=True,
        enable_p7=True, angular_rate_deg_s=omega_deg_s(5000),
    )
    valid = system.validate()
    error = system.species_sum_error()
    if not valid or abs(error) > 1e-12:
        raise RuntimeError("KT100 bounded P6 initialization diagnostic failed")
    return {
        "schema": "KT100_HYBRID_V2_BOUNDED_PREFLIGHT_V1",
        "classification": "INITIAL_SPECIES_ADMISSIBLE_ONLY",
        "fixture_source": "KT100_MODEL_FIXTURE_V1",
        "rpm": 5000,
        "uses_p5c_full_topology_constructor": True,
        "uses_default_verification_mesh_not_kt100_duct_mesh": True,
        "gas_or_species_step_executed": False,
        "p7_event_executed": False,
        "species_names": ["fresh_air", "fuel", "residual", "burned"],
        "component_cell_counts": {name: len(cells) for name, cells in components.items()},
        "species_mass_by_component": {
            name: [list(cell) for cell in cells]
            for name, cells in system.species_mass.items()
        },
        "species_sum_error_kg": error,
        "species_admissible": valid,
        "geometry_model_events": len(model.events),
        "not_v2_verification": True,
    }


def main() -> None:
    result = diagnose()
    output = Path("results/kt100-hybrid-model-fixture-v2-20261001")
    output.mkdir(parents=True, exist_ok=True)
    (output / "bounded-preflight.json").write_text(
        json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
