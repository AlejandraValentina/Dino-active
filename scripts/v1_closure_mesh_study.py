"""Preregistered one-cycle mesh study for MotorSim's synthetic 2T v1 gate.

The fixture builder is an existing test-only reference constructor. Its exact
source is hash-bound in the preregistration; all campaign inputs are frozen
JSON configurations and the integrated primary auditor rebuilds each cycle.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import inspect
import json
import math
from pathlib import Path
import runpy
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from motorsim.combustion import WiebeComponent  # noqa: E402
from motorsim.fuel_combustion import FuelCoupledCombustionV1  # noqa: E402
from motorsim.integrated_2t import (  # noqa: E402
    IntegratedEngine2T, _solver_dependency_hashes, audit_integrated_cycle_primary,
    make_integrated_cycle_primary, make_integrated_engineering_output,
)
from motorsim.mechanical import MechanicalLossModel  # noqa: E402
from scripts.produce_integrated_cycle_evidence import advance_to  # noqa: E402

PROGRAM = Path("results/2t-commercial-core-20261002")
FIXTURE_DIR = PROGRAM / "fixtures" / "v1-prime-mesh"
RUN_DIR = Path("results/2t-v1-closure-20261006/mesh-study")
RECOVERY_R1_DIR = RUN_DIR.with_name("mesh-study-r1")
RECOVERY_R2_DIR = RUN_DIR.with_name("mesh-study-r2")
SCHEMA = "MOTORSIM_2T_V1_MESH_STUDY_PREREGISTRATION_V1"
MESH_LEVELS = ((2, .2), (4, .1), (8, .05), (16, .025))
MESH_TOLERANCE = .02


def canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def fixture_builder():
    namespace = runpy.run_path(str(ROOT / "tests/test_integrated_2t.py"))
    return namespace["_internal_cycle_fixture"]


def fixture_specs():
    combustion = FuelCoupledCombustionV1(
        (WiebeComponent(1.0, 45.0, 5.0, 2.0),), 300.0, .82)
    common = {"open_end_plenum_v2": True,
              "fuel_coupled_combustion": combustion}
    return {
        "FIXTURE_A_PRIME": {**common, "with_reed": True,
            "chamber_length_scale": 1.0, "fixture_name": "FIXTURE_A_PRIME_V1",
            "transfer_ids": ("primary", "secondary", "boost"),
            "rpm": 3000.0},
        "FIXTURE_B_PRIME": {**common, "with_reed": False,
            "chamber_length_scale": 1.45, "fixture_name": "FIXTURE_B_PRIME_V1",
            "transfer_ids": ("primary", "secondary"), "rpm": 4000.0},
    }


def mechanical_loss_model() -> dict:
    from motorsim.mechanical import LossTerm
    return MechanicalLossModel((
        LossTerm("synthetic-piston-ring", "piston_ring",
                 "SYNTHETIC_ASSUMPTION", mep_pa=1000.0),
        LossTerm("synthetic-bearing-accessory", "bearing_accessory",
                 "SYNTHETIC_ASSUMPTION", mep_pa=500.0),
    )).to_dict()


def prepare(run_dir: Path = RUN_DIR, *, amendment: dict | None = None) -> dict:
    builder = fixture_builder()
    builder_source = inspect.getsource(builder).encode("utf-8")
    run_source = Path(__file__).read_bytes()
    engine_sources = _solver_dependency_hashes()
    combustion = next(iter(fixture_specs().values()))["fuel_coupled_combustion"]
    fixture_hashes = {}
    FIXTURE_DIR.mkdir(parents=True, exist_ok=True)
    for fixture_id, base in fixture_specs().items():
        fixture_hashes[fixture_id] = []
        for level, (transfer_cells, exhaust_dx) in enumerate(MESH_LEVELS):
            engine = builder(**base, transfer_cells=transfer_cells,
                             exhaust_cell_length_m=exhaust_dx)
            config = engine.configuration_dict()
            rebuilt = IntegratedEngine2T.from_configuration_dict(config)
            if rebuilt.configuration_dict() != config:
                raise ValueError(f"{fixture_id} mesh {level} config roundtrip failed")
            config_sha = sha(canonical(config))
            doc = {
                "schema": "MOTORSIM_2T_V1_MESH_STUDY_FIXTURE_V1",
                "fixture_id": fixture_id,
                "mesh_level": level,
                "classification": "SYNTHETIC_ASSUMPTION_CONDITIONAL_ON_P4",
                "engine_configuration": config,
                "engine_configuration_sha256": config_sha,
                "mechanical_loss_model": mechanical_loss_model(),
                "fuel_surrogate_snapshot": combustion.fuel.snapshot(),
                "mesh": {"transfer_cells_each": transfer_cells,
                         "exhaust_target_cell_length_m": exhaust_dx,
                         "intake_mesh_held_fixed": True},
            }
            relative = FIXTURE_DIR / f"{fixture_id.lower()}-mesh-{level}.json"
            (ROOT / relative).write_bytes(json.dumps(
                doc, sort_keys=True, indent=2, ensure_ascii=False,
                allow_nan=False).encode("utf-8") + b"\n")
            fixture_hashes[fixture_id].append({
                "mesh_level": level,
                "fixture_config_path": relative.as_posix(),
                "fixture_config_sha256": sha(canonical(doc)),
                "engine_configuration_sha256": config_sha,
                "geometry_sha256": engine.configuration_identity["geometry_sha256"],
                "rpm": config["reference_rpm"],
                "transfer_cells_each": transfer_cells,
                "exhaust_target_cell_length_m": exhaust_dx,
                "transfer_routes": [row["id"] for row in config["ducts"]
                                    if row["role"] == "transfer"],
                "exhaust_cells": len(next(
                    row["mesh"]["volumes"] for row in config["ducts"]
                    if row["role"] == "exhaust")),
            })
    prereg = {
        "schema": SCHEMA,
        "classification": "SYNTHETIC_ASSUMPTION_CONDITIONAL_ON_P4",
        "purpose": "C12 integrated transfer/exhaust mesh sufficiency; one cycle per mesh only",
        "campaigns": False,
        "horizon_cycles_per_mesh": 1,
        "levels": [
            {"mesh_level": i, "transfer_cells_each": n,
             "exhaust_target_cell_length_m": dx}
            for i, (n, dx) in enumerate(MESH_LEVELS)],
        "fixtures": fixture_hashes,
        "fixed_physics": {
            "A_prime": "quasi-static reed, 3 transfers, expansion chamber, 3000 RPM",
            "B_prime": "piston-port, no reed, 2 transfers, chamber length scale 1.45, 4000 RPM",
            "external_boundary": "OPEN_END_PLENUM_V2 / SYNTHETIC_ASSUMPTION",
            "inlet_reservoir_donor": {
                "species_mass_fractions": {
                    "fresh_air": .98, "fuel": .02, "residual": 0.0, "burned": 0.0},
                "provenance": "SYNTHETIC_ASSUMPTION",
                "interpretation": "premixed intake charge; not ambient-air composition or measured carburetor setting",
            },
            "outlet_reservoir_donor": {
                "species_mass_fractions": {
                    "fresh_air": 1.0, "fuel": 0.0, "residual": 0.0, "burned": 0.0},
                "provenance": "SYNTHETIC_ASSUMPTION",
            },
            "fuel": combustion.fuel.snapshot(),
            "combustion_efficiency": .82,
            "thermal": "CONSTANT_H_V1 fixture cylinder wall, SYNTHETIC_ASSUMPTION",
            "mechanical_losses": mechanical_loss_model(),
            "cfl": .4,
            "nominal_proposal_deg": .5,
            "integrator": "existing IntegratedEngine2T SSPRK2",
        },
        "observables": {
            "peak_cylinder_pressure_Pa": "maximum EOS pressure over every accepted cylinder stage state",
            "retained_fresh_air_kg": "fresh_air species mass at exact last transfer-close snapshot",
            "trapped_fuel_kg": "fuel at the exact configured ignition snapshot",
            "cylinder_indicated_work_J": "accepted-cycle integral(p_cyl dV_cyl)",
            "mass_residual_fraction": "signed residual / (residual bound mass_abs_kg / gamma_n)",
            "energy_residual_fraction": "signed residual / (residual bound energy_abs_j / gamma_n)",
        },
        "pairwise_sufficiency": {
            "observables": ["peak_cylinder_pressure_Pa", "retained_fresh_air_kg",
                            "trapped_fuel_kg", "cylinder_indicated_work_J"],
            "positive_or_signed_physical_metric": "abs(a-b)/max(abs(a),abs(b)) <= 0.02; two exact zeros compare equal; one zero uses the nonzero magnitude",
            "signed_ledger_residual": "abs(r_fine/S_fine-r_coarse/S_coarse) <= 0.02, with S=absolute primary ledger-term scale",
            "mesh_tolerance": MESH_TOLERANCE,
            "ledger_gate": "each mesh separately passes gamma_n float64 conservation and primary offline audit",
            "selection": "coarsest level whose pair with its next finer level satisfies every observable; if none, C12 fails and campaigns remain blocked",
        },
        "no_tuning": "No solver, EOS, boundary, initial state, geometry, RPM, CFL, physics, or tolerance changes across each fixture's levels.",
        "source_binding": {
            "fixture_builder_source_sha256": sha(builder_source),
            "mesh_study_runner_sha256": sha(run_source),
            "campaign_stepper_source_sha256": sha(
                inspect.getsource(advance_to).encode("utf-8")),
            "integrated_solver_dependency_sha256": sha(canonical(engine_sources)),
            "campaign_producer_source_sha256": sha(
                inspect.getsource(make_integrated_cycle_primary).encode("utf-8")),
        },
        "status": "PREREGISTERED_NOT_RUN",
    }
    prereg_path = run_dir / "preregistration.json"
    if prereg_path.exists():
        raise ValueError("C12 preregistration already exists; preserve it and use a new amendment path")
    if amendment is not None:
        prereg["amendment"] = amendment
    prereg_path.parent.mkdir(parents=True, exist_ok=True)
    prereg_path.write_bytes(json.dumps(prereg, sort_keys=True, indent=2,
                                       ensure_ascii=False, allow_nan=False).encode("utf-8") + b"\n")
    return prereg


def committed_json(relative: str) -> object:
    payload = subprocess.run(["git", "show", f"HEAD:{relative}"], cwd=ROOT,
                             capture_output=True, check=True).stdout
    return json.loads(payload.decode("utf-8-sig"))


def _pressure_max(primary: dict) -> float:
    gamma = float(primary["configuration"]["eos"]["gamma"])
    peak = 0.0
    for row in primary["trajectory"]:
        for stage in row["stage_states"]:
            _mass, energy, volume = stage["chambers"]["cylinder"]
            peak = max(peak, (gamma - 1.0) * energy / volume)
    return peak


def _mesh_observables(primary: dict, output: dict) -> dict:
    snapshots = primary["port_closure_snapshots"]["snapshots"]
    transfer = snapshots["transfer"]
    fresh = float(transfer["cylinder_species_kg"][0])
    chemistry = primary["observables"]["fuel_coupled_combustion"]
    trapped_fuel = chemistry["fuel_trapped_at_ignition_snapshot_kg"]
    metrics = output["cycle_metrics"]
    indicated = metrics["cylinder_indicated_work_j"]
    if type(trapped_fuel) not in (int, float) or type(indicated["value"]) not in (int, float):
        raise ValueError("C12 required trapped-fuel or indicated-work observable is undefined")
    bounds = primary["evidence_binding"]["residual_bounds"]
    gamma_n = float(bounds["gamma_n"])
    if gamma_n <= 0.0:
        raise ValueError("C12 primary residual bound is invalid")
    mass_scale = float(bounds["mass_abs_kg"]) / gamma_n
    energy_scale = float(bounds["energy_abs_j"]) / gamma_n
    if mass_scale <= 0.0 or energy_scale <= 0.0:
        raise ValueError("C12 residual scale must be positive")
    return {
        "peak_cylinder_pressure_Pa": _pressure_max(primary),
        "retained_fresh_air_kg": fresh,
        "trapped_fuel_kg": float(trapped_fuel),
        "cylinder_indicated_work_J": float(indicated["value"]),
        "mass_residual_kg": float(primary["conservation"]["mass_residual_kg"]),
        "mass_residual_scale_kg": mass_scale,
        "mass_residual_fraction": float(primary["conservation"]["mass_residual_kg"]) / mass_scale,
        "energy_residual_J": float(primary["conservation"]["energy_residual_J"]),
        "energy_residual_scale_J": energy_scale,
        "energy_residual_fraction": float(primary["conservation"]["energy_residual_J"]) / energy_scale,
        "gamma_n": gamma_n,
        "mass_abs_bound_kg": float(bounds["mass_abs_kg"]),
        "energy_abs_bound_J": float(bounds["energy_abs_j"]),
        "accepted_steps": len(primary["trajectory"]),
        "rejected_trials": len(primary["rejected_trials"]),
        "offline_audit": "PASS",
    }


def _pairwise(coarse: dict, fine: dict) -> dict:
    rows = {}
    for name in ("peak_cylinder_pressure_Pa", "retained_fresh_air_kg",
                 "trapped_fuel_kg", "cylinder_indicated_work_J"):
        a, b = float(coarse[name]), float(fine[name])
        denom = max(abs(a), abs(b))
        delta = 0.0 if denom == 0.0 else abs(a - b) / denom
        rows[name] = {"coarse": a, "fine": b,
                      "relative_difference": delta,
                      "pass": delta <= MESH_TOLERANCE}
    for name in ("mass_residual_fraction", "energy_residual_fraction"):
        a, b = float(coarse[name]), float(fine[name])
        delta = abs(a - b)
        rows[name] = {"coarse": a, "fine": b,
                      "absolute_ledger_scale_fraction_difference": delta,
                      "pass": delta <= MESH_TOLERANCE}
    return {"observables": rows,
            "pass": all(item["pass"] for item in rows.values())}


def run(run_dir: Path = RUN_DIR) -> dict:
    prereg_path = run_dir / "preregistration.json"
    prereg = committed_json(prereg_path.as_posix())
    if prereg.get("schema") != SCHEMA or prereg.get("status") != "PREREGISTERED_NOT_RUN":
        raise ValueError("C12 preregistration is absent, changed, or already consumed")
    builder = fixture_builder()
    if sha(inspect.getsource(builder).encode("utf-8")) != prereg["source_binding"]["fixture_builder_source_sha256"]:
        raise ValueError("C12 fixture builder differs from preregistration")
    if sha(Path(__file__).read_bytes()) != prereg["source_binding"]["mesh_study_runner_sha256"]:
        raise ValueError("C12 runner differs from preregistration")
    if sha(inspect.getsource(advance_to).encode("utf-8")) != prereg["source_binding"]["campaign_stepper_source_sha256"]:
        raise ValueError("C12 accepted-step scheduler differs from preregistration")
    if sha(canonical(_solver_dependency_hashes())) != prereg["source_binding"]["integrated_solver_dependency_sha256"]:
        raise ValueError("C12 integrated solver dependencies differ from preregistration")
    if sha(inspect.getsource(make_integrated_cycle_primary).encode("utf-8")) != prereg["source_binding"]["campaign_producer_source_sha256"]:
        raise ValueError("C12 cycle-primary producer differs from preregistration")
    records = {}
    for fixture_id, configs in prereg["fixtures"].items():
        records[fixture_id] = []
        for entry in configs:
            wrapper = committed_json(entry["fixture_config_path"])
            if sha(canonical(wrapper)) != entry["fixture_config_sha256"]:
                raise ValueError("C12 fixture config differs from preregistered hash")
            fixture_dir = ROOT / run_dir / fixture_id.lower()
            fixture_dir.mkdir(parents=True, exist_ok=True)
            marker = fixture_dir / f"mesh-{entry['mesh_level']}-run-started.json"
            dest = fixture_dir / f"mesh-{entry['mesh_level']}-cycle-1.json.gz"
            if marker.exists() or dest.exists():
                raise ValueError(
                    f"C12 mesh run already started for {fixture_id} level {entry['mesh_level']}; no automatic rerun")
            marker.write_bytes(json.dumps({
                "fixture_id": fixture_id,
                "mesh_level": entry["mesh_level"],
                "configuration_sha256": entry["engine_configuration_sha256"],
                "preregistration_sha256": sha(canonical(prereg)),
                "status": "RUN_STARTED",
            }, sort_keys=True, indent=2).encode() + b"\n")
            engine = IntegratedEngine2T.from_configuration_dict(
                wrapper["engine_configuration"])
            if sha(canonical(engine.configuration_dict())) != entry["engine_configuration_sha256"]:
                raise ValueError("C12 engine configuration identity mismatch")
            start = engine.snapshot()
            rejected = []
            advance_to(engine, 360.0, rejected)
            terminal = engine.snapshot()
            primary = make_integrated_cycle_primary(
                engine, start, terminal, 1, rejected_trials=rejected,
                runner_sha256=sha(Path(__file__).read_bytes()))
            audit = audit_integrated_cycle_primary(primary)
            if audit.get("recomputed") is not True:
                raise ValueError("C12 offline primary audit failed")
            model = MechanicalLossModel.from_dict(wrapper["mechanical_loss_model"])
            output = make_integrated_engineering_output(
                primary, mechanical_loss_model=model)
            record = _mesh_observables(primary, output)
            record.update({"fixture_id": fixture_id,
                           "mesh_level": entry["mesh_level"],
                           "configuration_sha256": entry["engine_configuration_sha256"],
                           "audit_sha256": sha(canonical(audit))})
            records[fixture_id].append(record)
            with dest.open("wb") as raw:
                with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as gz:
                    gz.write(canonical(primary))
            (fixture_dir / f"mesh-{entry['mesh_level']}-summary.json").write_bytes(
                json.dumps(record, sort_keys=True, indent=2, allow_nan=False).encode()+b"\n")
            print(f"{fixture_id} mesh {entry['mesh_level']}: {record['accepted_steps']} accepted steps; audit PASS", flush=True)
    decisions = {}
    for fixture_id, rows in records.items():
        comparisons = [_pairwise(left, right) for left, right in zip(rows, rows[1:])]
        adequate = next((i for i, row in enumerate(comparisons) if row["pass"]), None)
        decisions[fixture_id] = {
            "comparisons": comparisons,
            "sufficient_mesh_level": adequate,
            "status": "PASS" if adequate is not None else "MESH_UNRESOLVED",
        }
    result = {"schema": "MOTORSIM_2T_V1_MESH_STUDY_RESULT_V1",
              "preregistration_sha256": sha(canonical(prereg)),
              "preregistration_commit": subprocess.run(
                  ["git", "log", "-1", "--format=%H", "--", prereg_path.as_posix()],
                  cwd=ROOT, capture_output=True, check=True, text=True).stdout.strip(),
              "classification": "SYNTHETIC_ASSUMPTION_CONDITIONAL_ON_P4",
              "fixtures": records, "decisions": decisions,
              "overall_status": ("PASS" if all(
                  value["status"] == "PASS" for value in decisions.values())
                  else "C12_MESH_UNRESOLVED")}
    result_path = ROOT / run_dir / "result.json"
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_bytes(json.dumps(result, sort_keys=True, indent=2,
                                       allow_nan=False).encode()+b"\n")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("prepare", "run", "prepare-r1", "run-r1",
                                         "prepare-r2", "run-r2"))
    args = parser.parse_args()
    if args.mode.startswith("prepare"):
        run_dir = (RECOVERY_R2_DIR if args.mode.endswith("-r2") else
                   RECOVERY_R1_DIR if args.mode.endswith("-r1") else RUN_DIR)
        amendment = None
        if args.mode == "prepare-r1":
            amendment = {
                "schema": "MOTORSIM_2T_V1_MESH_STUDY_AMENDMENT_R1",
                "supersedes": RUN_DIR.as_posix() + "/preregistration.json",
                "reason": (
                    "The first C12 run completed and audited A mesh 0, then the "
                    "C10 offline auditor rejected A mesh 1 because replay used "
                    "angle_end-angle_start instead of the nominal/retry step "
                    "actually passed to SSPRK2. Coordinate subtraction changed "
                    "derived RPM and volume rates by roundoff. The solver, "
                    "physics, meshes, fixture inputs, horizon, thresholds, and "
                    "decision rules are unchanged; only replay uses the step "
                    "frozen by the scheduler and rejection log."
                ),
                "prior_run_disposition": "INVALIDATED_AS_INCOMPLETE_EVIDENCE; artifacts_preserved",
                "diagnostic_replays": (
                    "A mesh 1 was executed twice in-memory only to isolate the "
                    "auditor mismatch; those unpersisted records are discarded "
                    "and are not campaign evidence. R1 reruns the complete fixed "
                    "mesh set under its new source binding."
                ),
                "campaign_changes": [],
            }
        elif args.mode == "prepare-r2":
            amendment = {
                "schema": "MOTORSIM_2T_V1_MESH_STUDY_AMENDMENT_R2",
                "supersedes": RECOVERY_R1_DIR.as_posix() + "/preregistration.json",
                "reason": (
                    "The frozen R1 B-prime finest-mesh run stopped before a "
                    "primary record when fuel combustion rejected a species "
                    "value that the integrated state validator already admits "
                    "within its 1e-14 kg roundoff tolerance. Combustion now "
                    "uses that same admissibility tolerance; reactant "
                    "availability remains clamped at zero and cannot burn a "
                    "negative amount. Inputs, physics, meshes, horizon, "
                    "thresholds, and selection criteria are unchanged."
                ),
                "prior_run_disposition": "INCOMPLETE_ADMISSIBILITY_FAILURE; artifacts_preserved",
                "campaign_changes": [],
                "diagnostic_replays": "none",
            }
        result = prepare(run_dir, amendment=amendment)
        print(json.dumps({"status": result["status"],
                          "levels": len(MESH_LEVELS),
                          "fixtures": list(result["fixtures"]),
                          "preregistration": (run_dir / "preregistration.json").as_posix()},
                         sort_keys=True))
    else:
        run_dir = (RECOVERY_R2_DIR if args.mode.endswith("-r2") else
                   RECOVERY_R1_DIR if args.mode.endswith("-r1") else RUN_DIR)
        result = run(run_dir)
        print(json.dumps({"overall_status": result["overall_status"],
                          "decisions": result["decisions"]}, sort_keys=True))
        return 0 if result["overall_status"] == "PASS" else 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
