"""Strict JSON configuration checks for the independent reference harness."""
from __future__ import annotations

from math import isfinite

from ..project import Project

CONTRACT_ID = "REFERENCE_PERIODIC_CONVERGENCE_V1"
SPECIES = ("fresh_air", "fuel", "residual", "burned")


def _finite_number(value, name, *, positive=False):
    if type(value) not in (int, float) or not isfinite(value):
        raise ValueError(f"{name} must be a finite JSON number")
    if positive and value <= 0:
        raise ValueError(f"{name} must be positive")
    return float(value)


def _state(value, name):
    if not isinstance(value, dict):
        raise ValueError(f"{name} must be an object")
    pressure = _finite_number(value.get("pressure_Pa"), f"{name}.pressure_Pa", positive=True)
    temperature = _finite_number(value.get("temperature_K"), f"{name}.temperature_K", positive=True)
    velocity = _finite_number(value.get("velocity_m_s", 0.0), f"{name}.velocity_m_s")
    composition = value.get("species_mass_fractions")
    if not isinstance(composition, dict) or set(composition) != set(SPECIES):
        raise ValueError(f"{name}.species_mass_fractions must define exactly {SPECIES}")
    fractions = [_finite_number(composition[key], f"{name}.{key}") for key in SPECIES]
    if any(x < 0 for x in fractions) or abs(sum(fractions) - 1.0) > 1e-12:
        raise ValueError(f"{name} species fractions must be nonnegative and sum to one")
    return pressure, temperature, velocity, tuple(fractions)


def validate_config(config):
    """Validate a versioned harness config before creating a solver state."""
    if not isinstance(config, dict) or config.get("schema") != "motorsim-reference-engine-v1":
        raise ValueError("unsupported reference-engine configuration schema")
    def reject_unsupported(value):
        if isinstance(value, dict):
            if any(key.lower() in ("discharge_coefficient", "discharge_coefficients")
                   for key in value):
                raise ValueError("the product P4/P5-C port flux has no configurable discharge coefficient")
            for child in value.values():
                reject_unsupported(child)
        elif isinstance(value, list):
            for child in value:
                reject_unsupported(child)
    reject_unsupported(config)
    engine = config.get("engine")
    if not isinstance(engine, dict):
        raise ValueError("engine must be an object")
    project = Project.from_dict(engine.get("project"))
    if project.cycle != "2T":
        raise ValueError("REFERENCE_ENGINE_HYBRID_HARNESS_V1 currently requires a 2T project")
    if project.cylinder_count != 1:
        raise ValueError("the existing P5-C product topology supports exactly one cylinder")
    if (len(project.ports) != 3 or
            sorted(port.function for port in project.ports) != ["escape", "transfer", "transfer"]):
        raise ValueError("the existing P5-C topology requires one exhaust and two transfer ports")
    for name in ("cylinder_count", "bore_mm", "stroke_mm", "rod_length_mm",
                 "compression_ratio", "crankcase_volume_bdc_cm3"):
        if getattr(project, name) is None:
            raise ValueError(f"engine.project.{name} is required")
    operating = config.get("operating_point")
    if not isinstance(operating, dict):
        raise ValueError("operating_point is required")
    _finite_number(operating.get("rpm"), "operating_point.rpm", positive=True)
    numerics = config.get("numerics")
    if not isinstance(numerics, dict):
        raise ValueError("numerics is required")
    cfl = _finite_number(numerics.get("cfl"), "numerics.cfl", positive=True)
    if cfl > 0.6:
        raise ValueError("numerics.cfl must not exceed the product solver limit 0.6")
    dx = _finite_number(numerics.get("dx_target_m"), "numerics.dx_target_m", positive=True)
    cycles = numerics.get("max_cycles")
    if type(cycles) is not int or not 1 <= cycles <= 400:
        raise ValueError("numerics.max_cycles must be an integer in [1,400]")
    gamma = _finite_number(numerics.get("gamma"), "numerics.gamma", positive=True)
    gas_r = _finite_number(numerics.get("gas_R_J_kgK"), "numerics.gas_R_J_kgK", positive=True)
    if gamma <= 1:
        raise ValueError("numerics.gamma must exceed one")
    comb = config.get("combustion")
    if not isinstance(comb, dict):
        raise ValueError("combustion is required")
    phase = _finite_number(comb.get("physical_event_phase_deg"), "combustion.physical_event_phase_deg")
    if not 30 <= phase <= 350:
        raise ValueError("physical event phase must be in [30,350] degrees")
    if comb.get("duration_deg") != 40.0 or comb.get("heat_per_burned_mass_J_kg") != 800000.0:
        raise ValueError("P7 product duration and heat capability are fixed at 40 deg / 800000 J/kg")
    ducts = config.get("transfer_ducts")
    if not isinstance(ducts, list) or len(ducts) != 2:
        raise ValueError("exactly two explicitly defined transfer_ducts are required")
    from ..gas1d.mesh import segments_mesh
    meshes = []
    for index, duct in enumerate(ducts, 1):
        segments = duct if isinstance(duct, list) else [duct]
        if not segments or not all(isinstance(segment, dict) for segment in segments):
            raise ValueError(f"transfer_ducts[{index}] must contain segment objects")
        meshes.append(segments_mesh(segments, dx))
    boundaries = config.get("boundaries")
    if not isinstance(boundaries, dict):
        raise ValueError("boundaries is required")
    if (boundaries.get("atmosphere_pressure_Pa") != 101325.0 or
            boundaries.get("atmosphere_temperature_K") != 300.0 or
            boundaries.get("atmosphere_species_mass_fractions") != {
                "fresh_air": 1.0, "fuel": 0.0, "residual": 0.0, "burned": 0.0}):
        raise ValueError("the current P5-C/P6 atmospheric boundary is fixed at 101325 Pa, 300 K, fresh_air=1")
    boundary_capability = boundaries.get(
        "external_boundary_capability", "LEGACY_CHARACTERISTIC_V1")
    if boundary_capability not in ("LEGACY_CHARACTERISTIC_V1", "OPEN_END_PLENUM_V2"):
        raise ValueError("unsupported external boundary capability")
    if (boundary_capability == "OPEN_END_PLENUM_V2" and
            boundaries.get("external_boundary_provenance") != "SYNTHETIC_ASSUMPTION"):
        raise ValueError("OPEN_END_PLENUM_V2 requires SYNTHETIC_ASSUMPTION provenance")
    if boundary_capability == "OPEN_END_PLENUM_V2":
        model = config.get("boundary_model")
        if (not isinstance(model, dict) or model.get("id") != boundary_capability or
                model.get("provenance") != "SYNTHETIC_ASSUMPTION" or
                "not calibrated WB40" not in str(model.get("description", ""))):
            raise ValueError("OPEN_END_PLENUM_V2 requires its explicit synthetic boundary-model identity")
    initial = config.get("initial_states")
    if not isinstance(initial, dict):
        raise ValueError("initial_states is required")
    required = ("crankcase", "cylinder", "intake", "transfer1", "transfer2", "exhaust")
    for name in required:
        state = initial.get(name)
        if name in ("intake", "transfer1", "transfer2", "exhaust") and isinstance(state, list):
            if not state:
                raise ValueError(f"initial_states.{name} cannot be empty")
            for index, item in enumerate(state):
                _state(item, f"initial_states.{name}[{index}]")
        else:
            _state(state, f"initial_states.{name}")
    contract = config.get("convergence_contract")
    if contract != CONTRACT_ID:
        raise ValueError(f"convergence_contract must be {CONTRACT_ID}")
    evidence = config.get("evidence")
    if not isinstance(evidence, dict) or type(evidence.get("checkpoint_cadence_cycles")) is not int or evidence["checkpoint_cadence_cycles"] < 1:
        raise ValueError("evidence.checkpoint_cadence_cycles must be a positive integer")
    return {"project": project, "cfl": cfl, "dx_target_m": dx,
            "max_cycles": cycles, "gamma": gamma, "gas_R_J_kgK": gas_r,
            "physical_event_phase_deg": phase, "transfer_meshes": meshes,
            "external_boundary_capability": boundary_capability}
