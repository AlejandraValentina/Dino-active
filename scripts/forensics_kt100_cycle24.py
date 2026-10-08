"""Reconstruct the consumed KT100 R1 failure from its cycle-20 checkpoint.

This is a bounded forensic replay of cycles 21-24, not a new campaign.  It
does not write to or alter the R1 primary evidence directory.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import sys
import traceback
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from motorsim.gas1d.eos import IdealGas
from motorsim.p5c import IntegratedP5C
from motorsim.reference_harness.checkpoint import restore_checkpoint
from motorsim.reference_harness.convergence import PeriodicDetector
from motorsim.reference_harness.evidence import canonical_bytes
from motorsim.reference_harness.runtime import advance_cycle
from scripts.build_kt100_open_end_plenum_v2 import build

PRIMARY = ROOT / "results/kt100-hybrid-model-fixture-v2-harness-20261002-r6-open-end-plenum-v2-recovery-r1/rpm-5000"
OUTPUT = ROOT / "results/2t-commercial-core-20261002/kt100_cycle24_forensics.json"
FAILURE_EXPECTED = {
    "accepted_steps": 21925, "angle_deg": 142.19487248520613,
    "cycle_index": 24, "exception_type": "InvalidState",
    "message": "Conserved rho/species inadmissible", "status": "NUMERICAL_FAILURE",
}


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_gzip(path: Path):
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        return json.load(stream)


def _jsonable(value):
    if isinstance(value, tuple):
        return [_jsonable(x) for x in value]
    if isinstance(value, list):
        return [_jsonable(x) for x in value]
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if type(value) in (str, int, float, bool) or value is None:
        return value
    raise TypeError(type(value).__name__)


def _thermodynamic_rows(state, eos):
    cc, cy, intake, tr1, tr2, exhaust = state
    rows = []
    for name, chamber in (("crankcase", cc), ("cylinder", cy)):
        mass, momentum, energy, fresh_mass, volume = chamber
        rho = mass / volume
        pressure = (eos.gamma - 1.0) * energy / volume
        velocity = momentum / mass
        sound = (eos.gamma * pressure / rho) ** 0.5
        rows.append({"component": name, "cell": 0, "rho_kg_m3": rho,
                     "pressure_Pa": pressure, "temperature_K": pressure / (rho * eos.R),
                     "velocity_m_s": velocity, "mach": velocity / sound,
                     "legacy_fresh_fraction": fresh_mass / mass})
    for name, path in (("intake", intake), ("tr1", tr1), ("tr2", tr2),
                       ("exhaust", exhaust)):
        for index, q in enumerate(path):
            rho, momentum, energy, rho_y = q
            velocity = momentum / rho
            pressure = (eos.gamma - 1.0) * (energy - 0.5 * momentum * velocity)
            sound = (eos.gamma * pressure / rho) ** 0.5
            rows.append({"component": name, "cell": index, "rho_kg_m3": rho,
                         "rhoY_kg_m3": rho_y,
                         "rhoY_minus_rho_kg_m3": rho_y - rho,
                         "temperature_K": pressure / (rho * eos.R),
                         "pressure_Pa": pressure, "velocity_m_s": velocity,
                         "mach": velocity / sound,
                         "legacy_fresh_fraction_raw": rho_y / rho,
                         "legacy_fresh_fraction_bounded_view": min(1.0, rho_y / rho)})
    return rows


def main():
    if OUTPUT.exists():
        raise FileExistsError(f"refusing to overwrite forensic receipt: {OUTPUT}")
    failure = _read_gzip(PRIMARY / "failure.json.gz")
    if failure != FAILURE_EXPECTED:
        raise RuntimeError("persisted R1 failure no longer matches the forensic target")
    config = build()
    config["operating_point"]["rpm"] = 5000
    checkpoint_path = PRIMARY / "checkpoint-cycle-0020.json.gz"
    system, model, offset = __import__(
        "motorsim.reference_harness.runtime", fromlist=["build_system"]).build_system(config)
    checkpoint = _read_gzip(checkpoint_path)
    restore_checkpoint(system, PeriodicDetector(), checkpoint, config)
    eos = system.gas.eos
    replayed = []
    for cycle in (21, 22, 23):
        record = advance_cycle(system, model, config, offset, cycle)
        expected = _read_gzip(PRIMARY / f"cycle-{cycle:04d}.json.gz")
        equal = canonical_bytes(record) == canonical_bytes(expected)
        replayed.append({"cycle": cycle, "primary_exact_match": equal,
                         "accepted_steps": record["accepted_steps"],
                         "terminal_state": record["terminal_state"]})
        if not equal:
            raise RuntimeError(f"cycle {cycle} replay differs from persisted primary")

    capture = {"stages": [], "candidate": None, "before_attempt": None,
               "invalid_q": None, "invalid_traceback": None, "step": None}
    original_adapter = IdealGas.primitive_with_mass_fraction_roundoff
    original_primitive = IdealGas.primitive
    original_stage_rhs = IntegratedP5C._stage_rhs
    original_install = IntegratedP5C._install
    original_step = type(system).step

    def strict_adapter(self, q, *, ulps=8):
        # Reproduce the pre-fix strict P5 call semantics while preserving the
        # unchanged IdealGas.primitive contract.
        return self.primitive(q)

    def capture_primitive(self, q):
        try:
            return original_primitive(self, q)
        except Exception:
            capture["invalid_q"] = tuple(q)
            capture["invalid_traceback"] = traceback.format_exc()
            raise

    def capture_stage(self, state, **kwargs):
        pending = {"angle_deg": kwargs.get("stage_angle"),
                   "input_state": deepcopy(state), "rhs": None, "trace": None}
        capture["stages"].append(pending)
        if len(capture["stages"]) > 2:
            capture["stages"].pop(0)
        result = original_stage_rhs(self, state, **kwargs)
        pending["rhs"] = deepcopy(result[0])
        pending["trace"] = deepcopy(result[1])
        return result

    def capture_install(self, state):
        capture["candidate"] = deepcopy(state)
        return original_install(self, state)

    def capture_step(self, dt, *, angle=None, **kwargs):
        capture["before_attempt"] = {
            "angle_deg": self.gas.angle,
            "accepted_step_count": len(self.gas.history),
            "gas_state": deepcopy(self.gas._state()),
            "species_mass": deepcopy(self.species_mass),
            "gas_totals": deepcopy(self.gas.totals()),
            "gas_ledger": deepcopy(self.gas.ledger),
            "core_ledger": deepcopy(self.gas.core.ledger),
            "gas_external_cumulative": deepcopy(self.gas._external_cumulative),
            "p6_external_species": deepcopy(self._external),
            "fresh_delivered": self.fresh_delivered,
            "fresh_short_circuit": self.fresh_short_circuit,
            "p7_species_source_delta": deepcopy(self.p7_source_delta),
        }
        capture["step"] = {"dt_s": dt, "requested_end_angle_deg": angle}
        return original_step(self, dt, angle=angle, **kwargs)

    IdealGas.primitive_with_mass_fraction_roundoff = strict_adapter
    IdealGas.primitive = capture_primitive
    IntegratedP5C._stage_rhs = capture_stage
    IntegratedP5C._install = capture_install
    type(system).step = capture_step
    try:
        try:
            advance_cycle(system, model, config, offset, 24)
            raise RuntimeError("forensic replay unexpectedly accepted cycle 24")
        except Exception as error:
            if type(error).__name__ != "InvalidState" or str(error) != FAILURE_EXPECTED["message"]:
                raise
            exception = {"type": type(error).__name__, "message": str(error),
                         "traceback": capture["invalid_traceback"] or traceback.format_exc()}
    finally:
        IdealGas.primitive_with_mass_fraction_roundoff = original_adapter
        IdealGas.primitive = original_primitive
        IntegratedP5C._stage_rhs = original_stage_rhs
        IntegratedP5C._install = original_install
        type(system).step = original_step

    candidate = capture["candidate"] or system.gas._state()
    invalid = capture["invalid_q"]
    if invalid is None:
        invalid = next((q for path in candidate[2:] for q in path if q[3] > q[0]), None)
    if invalid is None:
        raise RuntimeError("no rhoY > rho state found in failed candidate")

    areas = model.geometry(capture["step"]["requested_end_angle_deg"] - offset)[2]
    result = {
        "schema": "KT100_CYCLE24_FORENSIC_REPLAY_V1",
        "classification": "REPRODUCED_FLOAT64_ROUNDOFF_ADMISSIBILITY_FAILURE",
        "campaign_status": "R1_ALLOWANCE_CONSUMED_NO_RERUN_AUTHORIZED",
        "point": {"rpm": 5000, "boundary": "OPEN_END_PLENUM_V2",
                  "boundary_provenance": "SYNTHETIC_ASSUMPTION",
                  "configuration_hash": _read_gzip(PRIMARY / "manifest.json.gz")["configuration_sha256"]},
        "source_primary": {
            "directory": PRIMARY.relative_to(ROOT).as_posix(),
            "failure_sha256": _sha(PRIMARY / "failure.json.gz"),
            "cycle23_sha256": _sha(PRIMARY / "cycle-0023.json.gz"),
            "checkpoint20_sha256": _sha(checkpoint_path),
            "persisted_failure": failure,
        },
        "replay_from_cycle20": {"cycles": replayed,
                                 "cycles24_to_failure_only": True},
        "failure": {**failure, "exception_path": exception,
                    "scheduler_stage": "P5C blended SSPRK2 state qn admissibility after install"},
        "accepted_state_before_failed_step": _jsonable(capture["before_attempt"]),
        "failed_attempt": {
            "step": capture["step"],
            "resolved_port_areas_m2": list(areas),
            "sspRK_stages": _jsonable(capture["stages"]),
            "candidate_full_state": _jsonable(candidate),
            "thermodynamics_by_component_cell": _thermodynamic_rows(candidate, eos),
            "invalid_cell": {"rho_kg_m3": invalid[0], "momentum_kg_m2_s": invalid[1],
                             "total_energy_J_m3": invalid[2], "rhoY_kg_m3": invalid[3],
                             "excess_kg_m3": invalid[3] - invalid[0],
                             "excess_ulp": (invalid[3] - invalid[0]) / __import__("math").ulp(invalid[0])},
            "boundary_configuration": config["boundaries"],
            "intake_reed_configuration": {
                "initial_states": {key: config["initial_states"].get(key)
                                   for key in ("intake", "transfer1", "transfer2", "crankcase")},
                "project_intake_ports": config["engine"]["project"].get("ports"),
                "reed": config["engine"]["project"].get("reed"),
            },
        },
        "root_cause": {
            "immediate": "strict P5 passive-scalar admissibility rejected rhoY one float64 ULP above rho at Y~=1",
            "mechanism": "the legacy rhoY scalar and rho are independently accumulated through SSPRK2; P6's four-species inventory is still valid and is authoritative",
            "scope": "general P5 conservative-to-primitive roundoff handling, not KT100-specific physical behavior",
            "not_indicated": ["no evidence of negative density", "no evidence of negative species mass",
                              "no change to EOS thermodynamic equations, fluxes, geometry, boundary, CFL, or solver scheme",
                              "the P5 primitive-view adapter is an explicit roundoff handling change"],
        },
        "artifacts_written": [OUTPUT.relative_to(ROOT).as_posix()],
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
                      encoding="utf-8", newline="\n")
    print(json.dumps({"output": OUTPUT.relative_to(ROOT).as_posix(),
                      "classification": result["classification"],
                      "failure_angle_deg": failure["angle_deg"],
                      "invalid_cell": result["failed_attempt"]["invalid_cell"]}, indent=2))


if __name__ == "__main__":
    main()
