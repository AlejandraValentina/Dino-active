"""Bounded, non-confirmatory 0D application study for the synthetic KT100 fixture."""
import argparse
from dataclasses import asdict
import hashlib
import json
import math
from pathlib import Path
import time

from motorsim.adaptive import PROFILES, run_adaptive
from motorsim.kt100_reference import (
    FIXTURE_ID, SIMULATION_ID, build_fixture_config, canonical_json,
    fixture_case, fixture_project, indicated_power_2t_w,
    indicated_torque_equivalent_nm,
)
from motorsim.prototype import Monitor
from motorsim.simulation import Model

EXPLORATORY_RPM = (5000, 7000, 9000, 11000, 13000)
PROFILE = PROFILES[1]
EXTERNAL_BAND_PA = 100


def _run_once(rpm, *, rod_scale=1.0, exhaust_scale=1.0):
    started = time.monotonic()
    case = fixture_case(rpm, rod_scale=rod_scale, exhaust_scale=exhaust_scale)
    model = Model(case, external_band_pa=EXTERNAL_BAND_PA)
    monitor = Monitor(PROFILE.max_step_deg, started, emit=lambda *a, **k: None)
    result = run_adaptive(PROFILE, monitor, model)
    cycles = result["cycles"]
    cycle = cycles[-1] if cycles else result.get("partial") or {}
    state = cycle.get("state", [])
    state_finite = len(state) == 12 and all(math.isfinite(float(value)) for value in state)
    state_admissible = state_finite and all(
        state[3*i] > 0 and state[3*i+1] > 0 and
        0 <= state[3*i+2] <= state[3*i] for i in range(4))
    work = cycle.get("W_C_J")
    pmax = cycle.get("p_max_Pa")
    geometry = fixture_project(rod_scale=rod_scale, exhaust_scale=exhaust_scale)
    return {
        "run": result,
        "point": {
            "rpm": rpm,
            "configuration": {
                "rod_length_mm": geometry.rod_length_mm,
                "exhaust_segments_length_mm": [s.length_mm for s in geometry.ducts.exhaust],
                "compression_ratio": geometry.compression_ratio,
                "profile": asdict(PROFILE),
                "external_regularization_band_Pa": EXTERNAL_BAND_PA,
            },
            "model_scope": "existing 0D I/K/C/E; lumped transfer and exhaust restrictions; synthetic, non-confirmatory",
            "convergence_status": "PERIOD_1_CONVERGED" if result["converged"] else "NOT_CONVERGED",
            "period": 1 if result["converged"] else None,
            "periodicity_contract": "existing motorsim 0D convergence() plus 3 consecutive passing cycles from cycle 5; period-2 and E13-R1 are not implemented by this path",
            "cycles_completed": len(cycles),
            "stop_reason": result["stop"],
            "indicated_work_last_completed_cycle_J": work,
            "indicated_power_from_work_W": None if work is None else indicated_power_2t_w(work, rpm),
            "torque_equivalent_from_work_Nm": None if work is None else indicated_torque_equivalent_nm(work),
            "peak_pressure_last_completed_cycle_Pa": pmax,
            "fresh_delivery": {"status": "NOT_SEPARATELY_LEDGERED_BY_0D_MODEL", "fresh_charge_at_source_event_kg": cycle.get("F_s_kg")},
            "fresh_short_circuit": {"status": "NOT_RESOLVED_BY_0D_MODEL"},
            "mass_energy_and_passive_marker_balances": {
                "discrete": cycle.get("discrete"),
                "independent": cycle.get("independent"),
                "balances_passed": cycle.get("balances_passed"),
                "marker_is_not_four_species": True,
            },
            "species_balance": "ONE_PASSIVE_FRESH_FRACTION_MARKER_ONLY; FOUR_SPECIES_P6_NOT_MODELED",
            "CFL": "NOT_APPLICABLE_ZERO_D",
            "admissibility": {"terminal_four_cv_state_finite_and_physical": state_admissible,
                "nonphysical_stage_rejections": result.get("rejections_by_cause", {}).get("nonphysical", 0),
                "model_evaluator_rejects_invalid_intermediate_states": True},
            "prescribed_heat_event": {"Q_J_last_cycle": cycle.get("Q_J"), "bookkeeping_converted_mass_kg": cycle.get("converted_kg"),
                "observed": bool(cycle.get("Q_J", 0) > 0 and cycle.get("converted_kg", 0) > 0),
                "chemistry": "NOT_MODELED"},
            "restart": {"status": "NOT_SUPPORTED_BY_EXISTING_0D_ADAPTIVE_API"},
            "deterministic_replay": None,
            "accepted_steps": result.get("accepted_steps"),
            "rejected_steps": result.get("rejected_steps"),
            "RHS_evaluations": result.get("rhs_evaluations"),
            "rejections_by_cause": result.get("rejections_by_cause"),
            "elapsed_wall_seconds": result.get("seconds"),
            "completed_at_wall_seconds": time.monotonic() - started,
            "cycle_summaries": cycles,
        },
    }


def run_point(rpm, *, rod_scale=1.0, exhaust_scale=1.0, replay=True):
    primary = _run_once(rpm, rod_scale=rod_scale, exhaust_scale=exhaust_scale)
    point = primary["point"]
    if replay:
        repeated = _run_once(rpm, rod_scale=rod_scale, exhaust_scale=exhaust_scale)
        # Compare complete recorded cycle summaries and controller counts; wall time is excluded.
        payload_a = {"cycles": primary["run"]["cycles"], "stop": primary["run"]["stop"],
                     "converged": primary["run"]["converged"], "rhs": primary["run"]["rhs_evaluations"],
                     "accepted": primary["run"]["accepted_steps"], "rejected": primary["run"]["rejected_steps"]}
        payload_b = {"cycles": repeated["run"]["cycles"], "stop": repeated["run"]["stop"],
                     "converged": repeated["run"]["converged"], "rhs": repeated["run"]["rhs_evaluations"],
                     "accepted": repeated["run"]["accepted_steps"], "rejected": repeated["run"]["rejected_steps"]}
        digest_a = hashlib.sha256(canonical_json(payload_a).encode()).hexdigest()
        digest_b = hashlib.sha256(canonical_json(payload_b).encode()).hexdigest()
        point["deterministic_replay"] = {"executed_from_same_initial_state": True,
            "terminal_cycle_history_exact": payload_a == payload_b,
            "sha256_first": digest_a, "sha256_replay": digest_b,
            "restart": "NOT_TESTED; this is a same-initial-state replay, not a restart"}
    return point


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--rpm", type=int, action="append")
    parser.add_argument("--rod-scale", type=float, default=1.0)
    parser.add_argument("--exhaust-scale", type=float, default=1.0)
    parser.add_argument("--no-replay", action="store_true")
    args = parser.parse_args()
    rpms = tuple(args.rpm or EXPLORATORY_RPM)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "fixture-config.json").write_text(json.dumps(
        build_fixture_config(), ensure_ascii=False, sort_keys=True, indent=2,
        allow_nan=False)+"\n", encoding="utf-8")
    results = []
    for rpm in rpms:
        try:
            point = run_point(rpm, rod_scale=args.rod_scale,
                              exhaust_scale=args.exhaust_scale,
                              replay=not args.no_replay)
        except Exception as exc:
            point = {"rpm": rpm, "classification": "INCOMPLETE_OR_ERROR",
                     "error": f"{type(exc).__name__}: {exc}"}
        results.append(point)
        (args.output / f"point-{rpm}-rod{args.rod_scale:g}-exh{args.exhaust_scale:g}.json").write_text(
            json.dumps(point, ensure_ascii=False, sort_keys=True, indent=2,
                       allow_nan=False)+"\n", encoding="utf-8")
        campaign = {"schema": "kt100-reference-campaign-v1", "case_id": SIMULATION_ID,
            "fixture_id": FIXTURE_ID, "dataset_kind": "SYNTHETIC_MODEL_EXECUTION",
            "execution_path": "existing 0D adaptive application model",
            "rpm_grid": list(rpms), "rpm_grid_reason": "fixed exploratory grid selected before execution; KT100SP RPM range unknown",
            "experimental_validation": "NOT_PERFORMED", "predictive_validation": "NOT_CLAIMED",
            "results": results}
        (args.output / "campaign.json").write_text(json.dumps(campaign,
            ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)+"\n", encoding="utf-8")
        print(json.dumps({"rpm": rpm, "status": point.get("convergence_status", point.get("classification")),
            "cycles": point.get("cycles_completed"), "work_J": point.get("indicated_work_last_completed_cycle_J"),
            "replay": point.get("deterministic_replay"), "error": point.get("error")}, allow_nan=False), flush=True)


if __name__ == "__main__":
    main()
