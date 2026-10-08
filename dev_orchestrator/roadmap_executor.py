"""Reconstruct durable roadmap state from the closed P8 evidence.

This evaluator never authorizes P9. It validates the committed P8 campaign,
including consolidated/anchor/CSV consistency, then records a conservative
terminal P8 state. Missing or inconsistent evidence blocks transition.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

P8_RESULT_DIR = Path("results/p8-wide-rpm-auditable-r4-final-20260930")
P8_RPMS = (2500, 5000, 8000, 11000, 15000)
P8_EVIDENCE_COMMIT = "602035de2c792475a2f102e64b0f3d00b4883b7f"
P8_CLOSED_AT = "2026-09-27T22:34:04-03:00"
P8_GATE_KEYS = (
    "finite", "geometry_rebased", "admissible", "species",
    "p7_one_event", "p7_nonvacuous", "p7_source_admissible",
    "p7_heat_consistent", "cfl", "source_heat_consistent",
    "prescribed_heat_matches_ledger", "global_mass_conservation",
    "global_energy_conservation", "prepared_initial_state",
    "restart", "deterministic_replay",
)


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _csv_matches(csv_path: Path, anchors: dict[int, dict]) -> bool:
    if not csv_path.exists():
        return False
    rows = list(csv.DictReader(csv_path.open(encoding="utf-8", newline="")))
    if [int(row["rpm"]) for row in rows] != list(P8_RPMS):
        return False
    for row in rows:
        a = anchors[int(row["rpm"])]
        capture = a["p7_capture"]
        checks = {
            "prepared_cylinder_fresh_kg": a["prepared_cylinder_fresh_kg"],
            "captured_fresh_kg": capture["captured_fresh_kg"],
            "burned_produced_kg": capture["burned_produced_kg"],
            "prescribed_heat_J": a["prescribed_heat_J"],
            "W_cycle_J": a["W_cycle_J"],
            "P_indicated_W": a["P_indicated_W"],
            "T_indicated_Nm": a["T_indicated_Nm"],
            "p_max_Pa": a["p_max_Pa"],
        }
        if any(float(row[key]) != value for key, value in checks.items()):
            return False
        if row["restart_state_equal"] != str(a["restart"]["state_equal"]):
            return False
        if float(row["checkpoint_angle_deg"]) != a["restart"]["checkpoint_angle_deg"]:
            return False
        if float(row["achieved_CFL_max"]) != a["achieved_CFL_max"]:
            return False
        if float(row["global_mass_residual_kg"]) != a["global_mass_residual_kg"]:
            return False
        if float(row["global_energy_residual_J"]) != a["global_energy_residual_J"]:
            return False
    return True


def _audit_p8(repo: Path) -> tuple[dict, dict]:
    result_dir = repo / P8_RESULT_DIR
    consolidated_path = result_dir / "p8-wide-rpm.json"
    if not consolidated_path.exists():
        return {}, {"evidence_present": False, "closure_ok": False}

    payload = _read_json(consolidated_path)
    from .p8_durable_audit import audit_campaign
    primary_audit = audit_campaign(result_dir)
    anchors_list = payload.get("anchors", [])
    anchors = {int(a["rpm"]): a for a in anchors_list if "rpm" in a}
    anchors_complete = tuple(sorted(anchors)) == P8_RPMS and len(anchors_list) == len(P8_RPMS)
    individual_equal = anchors_complete and all(
        (result_dir / f"anchor-{rpm}.json").exists()
        and _read_json(result_dir / f"anchor-{rpm}.json") == anchors[rpm]
        for rpm in P8_RPMS
    )
    gates_ok = anchors_complete and all(
        all(a.get("gates", {}).get(key) is True for key in P8_GATE_KEYS)
        for a in anchors.values()
    )
    restart_ok = anchors_complete and all(
        a.get("restart", {}).get(key) is True
        for a in anchors.values()
        for key in (
            "executed", "checkpoint_inside_p7", "state_equal", "species_mass_equal",
            "p7_ledger_equal", "external_equal", "fresh_delivery_equal",
            "short_circuit_equal",
        )
    )
    replay_ok = anchors_complete and all(
        a.get("deterministic_replay", {}).get(key) is True
        for a in anchors.values()
        for key in ("executed", "state_equal", "preparation_state_equal", "metrics_equal")
    )
    nonvacuous = anchors_complete and all(
        a["p7_capture"]["captured_fresh_kg"] > 0.0
        and a["p7_capture"]["burned_produced_kg"] > 0.0
        and a["prescribed_heat_J"] > 0.0
        for a in anchors.values()
    )
    csv_equal = anchors_complete and _csv_matches(result_dir / "p8-wide-rpm.csv", anchors)
    flags = {
        "evidence_present": True,
        "anchors_complete": anchors_complete,
        "anchor_files_equal": individual_equal,
        "csv_equal": csv_equal,
        "gates_ok": gates_ok,
        "restart_ok": restart_ok,
        "replay_ok": replay_ok,
        "primary_audit_ok": primary_audit.get("passed") is True,
        "primary_audit": primary_audit,
        "p7_nonvacuous": nonvacuous,
        "p4_blocked": payload.get("p4") == "BLOCKED / NOT_GRANTED",
        "p9_stopped": payload.get("p9") == "STOPPED",
        "status_ok": payload.get("status") == "P8_WIDE_RPM_PERFORMANCE_VERIFIED_CONDITIONAL",
        "no_failures": payload.get("failures") == [],
    }
    flags["closure_ok"] = all(value is True for key, value in flags.items()
                               if key != "primary_audit")
    return payload, flags


def evaluate(repo: str | Path = ".") -> dict:
    repo = Path(repo).resolve()
    out = repo / "results" / "roadmap-executor"
    out.mkdir(parents=True, exist_ok=True)
    payload, audit = _audit_p8(repo)
    closed = audit.get("closure_ok", False)
    state = {
        "current_phase": "P8",
        "current_subphase": None,
        "base_commit": "f782e6bb7fa9dfb7624f10179442da69f53075b5",
        "latest_commit": P8_EVIDENCE_COMMIT,
        "classification": (
            "P8_WIDE_RPM_PERFORMANCE_VERIFIED_CONDITIONAL"
            if closed else "P8_EVIDENCE_INCONSISTENT_BLOCKED"
        ),
        "attempt": 0,
        "gates": {
            "campaign": "PASS" if audit.get("status_ok") and audit.get("no_failures") else "BLOCKED",
            "anchors": "PASS" if audit.get("anchors_complete") else "BLOCKED",
            "anchor_files": "PASS" if audit.get("anchor_files_equal") else "BLOCKED",
            "csv_consistency": "PASS" if audit.get("csv_equal") else "BLOCKED",
            "restart": "PASS" if audit.get("restart_ok") else "BLOCKED",
            "determinism": "PASS" if audit.get("replay_ok") else "BLOCKED",
            "primary_recomputation": "PASS" if audit.get("primary_audit_ok") else "BLOCKED",
            "p7_nonvacuous": "PASS" if audit.get("p7_nonvacuous") else "BLOCKED",
            "measured_gates": "PASS" if audit.get("gates_ok") else "BLOCKED",
            "p4": "NOT_GRANTED" if audit.get("p4_blocked") else "INCONSISTENT",
            "p9": "STOPPED" if audit.get("p9_stopped") else "INCONSISTENT",
            "independent_review": (
                "READY_FOR_FINAL_INDEPENDENT_RATIFICATION"
                if closed else "BLOCKED_PENDING_P8_PRIMARY_EVIDENCE"
            ),
        },
        "blockers": [
            "P4 remains BLOCKED / NOT_GRANTED",
            "Independent review remains pending",
            "P9 is not authorized",
        ],
        "dependencies": {"P4": "UNRESOLVED", "P7": "CONDITIONAL_VERIFIED"},
        "started_at": P8_CLOSED_AT,
        "completed_at": P8_CLOSED_AT,
        "next_action": (
            "Keep P8 closed; require explicit human authorization and a new P9 contract before experimental validation"
            if closed else "Repair P8 evidence inconsistency before any phase transition"
        ),
        "evidence": {
            "consolidated": str(P8_RESULT_DIR / "p8-wide-rpm.json"),
            "csv": str(P8_RESULT_DIR / "p8-wide-rpm.csv"),
            "audit": audit,
            "reported_closure": payload.get("closure"),
        },
    }
    (out / "state.json").write_text(
        json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return state


if __name__ == "__main__":
    print(json.dumps(evaluate(), indent=2, ensure_ascii=False))
