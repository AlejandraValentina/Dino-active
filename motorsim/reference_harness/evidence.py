"""Primary evidence, binding, JSON-safe checkpoints, and offline audit."""
from __future__ import annotations

import gzip
import hashlib
import json
import math
from pathlib import Path

from .convergence import PeriodicDetector, CONTRACT, compare_cycles

ROOT = Path(__file__).resolve().parents[2]
BOUND_SOURCES = (
    "motorsim/exhaust_port.py", "motorsim/p5b.py", "motorsim/p5c.py",
    "motorsim/p6_species.py", "motorsim/p7_prescribed.py",
    "motorsim/project.py", "motorsim/ducts.py", "motorsim/simulation.py",
    "motorsim/simulation_case.py", "motorsim/kt100_reference.py",
    "motorsim/gas1d/eos.py", "motorsim/gas1d/mesh.py",
    "motorsim/gas1d/solver.py", "motorsim/gas1d/riemann.py",
    "motorsim/gas1d/boundary.py", "motorsim/reference_harness/config.py",
    "motorsim/reference_harness/convergence.py",
    "motorsim/reference_harness/runtime.py",
    "motorsim/reference_harness/evidence.py",
    "motorsim/reference_harness/checkpoint.py",
    "motorsim/reference_harness/campaign.py",
)


def canonical_bytes(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def sha256_bytes(value):
    return hashlib.sha256(value).hexdigest()


def configuration_hash(config):
    return sha256_bytes(canonical_bytes(config))


def source_binding():
    return {relative: sha256_bytes((ROOT / relative).read_bytes())
            for relative in BOUND_SOURCES}


def manifest(config):
    return {"schema": "REFERENCE_ENGINE_HYBRID_HARNESS_V1_MANIFEST",
            "convergence_contract": CONTRACT,
            "configuration_sha256": configuration_hash(config),
            "configuration": config,
            "source_sha256": source_binding(),
            "historical_campaign_contracts_imported": [],
            "p4_dependency": "CONDITIONAL_ON_P4"}


def _safe(value):
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if type(value) is float:
        if not math.isfinite(value):
            raise ValueError("non-finite value cannot enter primary evidence")
        return value
    if isinstance(value, (tuple, list)):
        return [_safe(x) for x in value]
    if isinstance(value, dict):
        return {str(k): _safe(v) for k, v in value.items()}
    raise TypeError(f"non-JSON evidence type: {type(value).__name__}")


def write_json_gzip(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = canonical_bytes(_safe(value))
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as stream:
            stream.write(payload)
    return sha256_bytes(path.read_bytes())


def read_json_gzip(path):
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        return json.load(stream, parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)))


def _primitive_and_inventory(system, name):
    gas, eos = system.gas, system.gas.eos
    chamber = getattr(gas.core, name)
    mass, marker, energy = chamber.inventory(eos)
    rho, pressure, temperature, _ = chamber.thermodynamics(eos)
    return {"mass_kg": mass, "total_energy_J": energy, "pressure_Pa": pressure,
            "temperature_K": temperature}


def _duct_observables(system, name, path):
    eos = system.gas.eos
    # Product-facing output labels differ from the P6 state keys for the two
    # transfer paths. Keep that translation at the evidence boundary.
    species_name = {"transfer1": "tr1", "transfer2": "tr2"}.get(name, name)
    mass_cells = system.species_mass[species_name]
    records = []
    for cell, volume, species in zip(path.cells, path.mesh.volumes, mass_cells):
        q = cell.conservative
        rho, velocity, pressure, _ = eos.primitive(q)
        total_mass = sum(species)
        records.append({"mass_kg": rho * volume,
                        "total_energy_J": q[2] * volume,
                        "pressure_Pa": pressure,
                        "temperature_K": pressure / (rho * eos.R),
                        "velocity_over_sound_speed": velocity / eos.sound_speed((rho, velocity, pressure, q[3]/rho)),
                        "species_mass_fractions": ([x / total_mass for x in species]
                                                    if total_mass else [0.0] * 4)})
    return records


def make_cycle_record(system, cycle_index, config, work, cfl_min, cfl_max,
                      start_species, start_mass, start_energy, before_delivery,
                      before_short, before_burned, before_heat, before_totals,
                      before_external, before_source, before_species_external,
                      peak_pressure):
    gas, eos = system.gas, system.gas.eos
    paths = {"intake": gas.core.intake, "transfer1": gas.core.transfers[0],
             "transfer2": gas.core.transfers[1], "exhaust": gas.exhaust}
    current_species = system._species_totals()
    species_external = tuple(system._external[i] for i in range(4))
    source = tuple(system.p7_source_delta)
    p7_heat = source[3] * 800000.0
    total = gas.totals()
    ext = gas._external_cumulative
    ext_delta = {key: ext[key] - before_external[key] for key in ext}
    mass_residual = total["mass"] - before_totals["mass"] - ext_delta["mass"]
    heat_increment = p7_heat - before_heat
    energy_residual = total["energy"] - before_totals["energy"] - ext_delta["energy"] - heat_increment + work
    source_delta = tuple(source[i] - before_source[i] for i in range(4))
    species_delta = tuple(current_species[i] - start_species[i] -
                          (system._external[i] - before_species_external[i]) -
                          source_delta[i] for i in range(4))
    if system.p7_event is not None:
        p7_ledger = vars(system.p7_event.ledger).copy()
    else:
        p7_ledger = {"burned_produced": 0.0, "heat_added": 0.0}
    chambers = {name: _primitive_and_inventory(system, name)
                for name in ("cylinder", "crankcase")}
    ducts = {name: _duct_observables(system, name, path) for name, path in paths.items()}
    observable = {"chambers": chambers, "ducts": ducts,
                  "global_species_kg": list(current_species),
                  "cycle_start_total_mass_kg": start_mass,
                  "cycle_start_total_energy_J": start_energy,
                  "work_J": work,
                  "fresh_delivery_kg": system.fresh_delivered - before_delivery,
                  "fresh_short_circuit_kg": system.fresh_short_circuit - before_short,
                  "p7_burned_produced_kg": source_delta[3],
                  "p7_heat_J": heat_increment}
    return {"schema": "REFERENCE_ENGINE_HYBRID_CYCLE_PRIMARY_V1",
            "contract": CONTRACT, "cycle_index": cycle_index,
            "rpm": config["operating_point"]["rpm"],
            "configuration_hash": configuration_hash(config),
            "scheduler_angle_deg": gas.angle,
            "terminal_state": {"gas_conservative": gas._state(),
                               "species_mass": system.species_mass},
            "observables": observable,
            "p7_ledger": p7_ledger,
            "conservation": {"mass_residual_kg": mass_residual,
                             "energy_residual_J": energy_residual,
                             "species_residual_kg_by_component": list(species_delta),
                             "mass_terms": {"start_kg": before_totals["mass"],
                                            "end_kg": total["mass"],
                                            "external_delta_kg": ext_delta["mass"]},
                             "energy_terms": {"start_J": before_totals["energy"],
                                              "end_J": total["energy"],
                                              "external_delta_J": ext_delta["energy"],
                                              "p7_heat_J": heat_increment,
                                              "indicated_work_J": work},
                             "species_terms": {"start_kg": list(start_species),
                                               "end_kg": list(current_species),
                                               "external_delta_kg": [system._external[i] - before_species_external[i] for i in range(4)],
                                               "p7_delta_kg": list(source_delta)},
                             "external_species_kg_cumulative": list(species_external),
                             "p7_species_increment_kg": list(source_delta)},
            "admissible": True, "species_sum_error_kg": system.species_sum_error(),
            "CFL": {"min": cfl_min, "max": cfl_max},
            "performance": {"indicated_work_J": work,
                            "indicated_power_W": work * config["operating_point"]["rpm"] / 60.0,
                            "equivalent_indicated_torque_Nm": work / (2.0 * math.pi),
                            "peak_pressure_Pa": peak_pressure}}


def _validate_finite(value, path="$", *, allow_bool=True):
    if type(value) is bool:
        if allow_bool:
            return
        raise ValueError(f"boolean is not numeric evidence at {path}")
    if type(value) in (int, float):
        if not math.isfinite(value):
            raise ValueError(f"non-finite evidence at {path}")
        return
    if isinstance(value, list):
        for i, child in enumerate(value):
            _validate_finite(child, f"{path}[{i}]", allow_bool=allow_bool)
    elif isinstance(value, dict):
        for key, child in value.items():
            _validate_finite(child, f"{path}.{key}", allow_bool=allow_bool)


def audit_cycles(cycles, config_hash):
    """Offline recomputation from saved PRIMARY cycle records."""
    if not isinstance(cycles, list) or not cycles:
        raise ValueError("primary cycle records are missing")
    detector = PeriodicDetector()
    reports = []
    for index, record in enumerate(cycles, 1):
        _validate_finite(record)
        _validate_finite(record.get("observables"), "$.observables", allow_bool=False)
        _validate_finite(record.get("conservation"), "$.conservation", allow_bool=False)
        _validate_finite(record.get("terminal_state"), "$.terminal_state", allow_bool=False)
        _validate_finite(record.get("trajectory"), "$.trajectory", allow_bool=False)
        _validate_finite(record.get("p7_ledger"), "$.p7_ledger", allow_bool=False)
        if record.get("cycle_index") != index or record.get("configuration_hash") != config_hash:
            raise ValueError("cycle identity/configuration hash mismatch")
        if record.get("contract") != CONTRACT or record.get("schema") != "REFERENCE_ENGINE_HYBRID_CYCLE_PRIMARY_V1":
            raise ValueError("cycle primary schema/contract mismatch")
        terminal = record.get("terminal_state")
        if (record.get("trajectory_last_state") != terminal.get("gas_conservative") or
                not record.get("trajectory") or
                record["trajectory"][-1].get("state") != terminal.get("gas_conservative")):
            raise ValueError("trajectory terminal gas state mismatch")
        if (record.get("trajectory_last_species_mass") != terminal.get("species_mass") or
                record["trajectory"][-1].get("species_mass") != terminal.get("species_mass")):
            raise ValueError("trajectory terminal species state mismatch")
        if record.get("admissible") is not True:
            raise ValueError("cycle not admissible")
        terms = record["conservation"]
        start = record["cycle_start_cumulative"]
        first, last = record["trajectory"][0], record["trajectory"][-1]
        if (first["angle_deg"] <= start["angle_deg"] or
                record["scheduler_angle_deg"] <= first["angle_deg"]):
            raise ValueError("trajectory angle range is incomplete")
        mass = terms["mass_terms"]
        mass_delta = last["gas_totals"]["mass"] - start["gas_totals"]["mass"]
        external_mass = (last["gas_external_cumulative"]["mass"] -
                         start["gas_external"]["mass"])
        mass_residual = mass_delta - external_mass
        energy = terms["energy_terms"]
        external_energy = (last["gas_external_cumulative"]["energy"] -
                           start["gas_external"]["energy"])
        heat_delta = last["p7_heat_cumulative_J"] - start["p7_species_source"][3] * 800000.0
        work_delta = last["work_cumulative_J"]
        energy_residual = (last["gas_totals"]["energy"] - start["gas_totals"]["energy"] -
                           external_energy - heat_delta + work_delta)
        species = terms["species_terms"]
        ext_delta = [last["species_external_cumulative"][i] - start["species_external"][i]
                     for i in range(4)]
        source_delta = [last["p7_species_source_cumulative"][i] - start["p7_species_source"][i]
                        for i in range(4)]
        species_residuals = [last["species_inventory"][i] - start["species_inventory"][i] -
                             ext_delta[i] - source_delta[i] for i in range(4)]
        if (mass_residual != terms["mass_residual_kg"] or
                energy_residual != terms["energy_residual_J"] or
                species_residuals != terms["species_residual_kg_by_component"] or
                abs(mass["start_kg"] - start["gas_totals"]["mass"]) > 0 or
                abs(energy["start_J"] - start["gas_totals"]["energy"]) > 0 or
                abs(energy["indicated_work_J"] - work_delta) > 0 or
                abs(energy["p7_heat_J"] - heat_delta) > 0):
            raise ValueError("stored conservation summary differs from primary terms")
        if abs(record["species_sum_error_kg"]) > 1e-12 * max(1.0, mass["end_kg"]):
            raise ValueError("four species do not sum to total mass")
        work = record["observables"]["work_J"]
        performance = record["performance"]
        if (performance["indicated_work_J"] != work or
                performance["indicated_power_W"] != work * record["rpm"] / 60.0 or
                performance["equivalent_indicated_torque_Nm"] != work / (2.0 * math.pi)):
            raise ValueError("stored performance outputs differ from primary work/RPM")
        peak = max(max(step["cylinder_stage_pressure_Pa"])
                   for step in record["trajectory"])
        if performance["peak_pressure_Pa"] != peak:
            raise ValueError("stored peak pressure differs from accepted stage states")
        result = detector.update({k: record[k] for k in
                                  ("cycle_index", "configuration_hash", "contract", "observables")})
        reports.append(result)
    return {"classification": detector.classification,
            "converged_cycle": detector.converged_cycle,
            "detector_state": detector.snapshot(), "cycle_reports": reports}


def verify_source_binding(binding):
    if not isinstance(binding, dict) or set(binding) != set(BOUND_SOURCES):
        raise ValueError("source binding is missing or has unexpected product files")
    actual = source_binding()
    if binding != actual:
        changed = sorted(k for k in actual if binding.get(k) != actual[k])
        raise ValueError(f"product component source hash mismatch: {changed}")
    return True


def audit_campaign_directory(directory):
    """Rebuild a completed (or explicitly failed) campaign from saved files."""
    directory = Path(directory)
    manifest_data = read_json_gzip(directory / "manifest.json.gz")
    if manifest_data.get("schema") != "REFERENCE_ENGINE_HYBRID_HARNESS_V1_MANIFEST":
        raise ValueError("campaign manifest schema mismatch")
    verify_source_binding(manifest_data.get("source_sha256"))
    config = manifest_data.get("configuration")
    expected_hash = configuration_hash(config)
    if manifest_data.get("configuration_sha256") != expected_hash:
        raise ValueError("campaign configuration hash mismatch")
    cycles = [read_json_gzip(path) for path in sorted(directory.glob("cycle-*.json.gz"))]
    if not cycles:
        failure_path = directory / "failure.json.gz"
        if not failure_path.exists():
            raise ValueError("campaign has neither PRIMARY cycles nor a failure record")
        failure = read_json_gzip(failure_path)
        summary = read_json_gzip(directory / "summary.json.gz")
        if summary.get("failure") != failure or summary.get("complete_cycles") != 0:
            raise ValueError("empty-run summary does not match its failure evidence")
        return {"evidence_audit": "PASS", "run_classification": failure.get("status"), "complete_cycles": 0,
                "failure": failure, "source_binding": "PASS"}

    recomputed = audit_cycles(cycles, expected_hash)
    replay_path = directory / "initial-replay.json.gz"
    if not replay_path.exists():
        raise ValueError("independent initial replay evidence is missing")
    replay = read_json_gzip(replay_path)
    if (replay.get("schema") != "REFERENCE_ENGINE_REPLAY_PRIMARY_V1" or
            replay.get("continuous_primary") != replay.get("replayed_primary") or
            replay.get("continuous_primary") != cycles[0]):
        raise ValueError("independent replay PRIMARY states differ")
    restart_path = directory / "restart-replay.json.gz"
    if restart_path.exists():
        restart = read_json_gzip(restart_path)
        if (restart.get("schema") != "REFERENCE_ENGINE_RESTART_REPLAY_PRIMARY_V1" or
                restart.get("continuous_primary") != restart.get("restarted_primary") or
                restart.get("continuous_detector") != restart.get("restarted_detector")):
            raise ValueError("restart continuation PRIMARY or detector differs")
    checkpoint_paths = sorted(directory.glob("checkpoint-cycle-*.json.gz"))
    for checkpoint_path in checkpoint_paths:
        checkpoint = read_json_gzip(checkpoint_path)
        payload = checkpoint.get("payload")
        serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"),
                                 allow_nan=False).encode("utf-8")
        if hashlib.sha256(serialized).hexdigest() != checkpoint.get("payload_sha256"):
            raise ValueError(f"checkpoint hash mismatch: {checkpoint_path.name}")
        if (payload.get("configuration_hash") != expected_hash or
                payload.get("schema") != "REFERENCE_ENGINE_CHECKPOINT_V1"):
            raise ValueError(f"checkpoint identity mismatch: {checkpoint_path.name}")
    summary = read_json_gzip(directory / "summary.json.gz")
    expected_classification = (summary.get("failure", {}).get("status")
                               if summary.get("failure") else
                               recomputed["classification"] or "NO_CONVERGENCE_MAX_CYCLES")
    if (summary.get("complete_cycles") != len(cycles) or
            summary.get("detected_period") != recomputed["classification"] or
            summary.get("converged_cycle") != recomputed["converged_cycle"] or
            summary.get("classification") != expected_classification):
        raise ValueError("campaign summary disagrees with recomputed PRIMARY evidence")
    return {"evidence_audit": "PASS", "run_classification": expected_classification,
            "complete_cycles": len(cycles),
            "classification": recomputed["classification"],
            "converged_cycle": recomputed["converged_cycle"],
            "source_binding": "PASS", "initial_replay": "PASS",
            "restart_replay": "PASS" if restart_path.exists() else "NOT_PRESENT",
            "recomputed": recomputed}
