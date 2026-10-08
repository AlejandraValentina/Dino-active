"""Operational view and maintenance of the durable MotorSim program status.

``program-status.json`` is the single operational authority (AGENTS.md §5).
This tool only reads/writes process fields (objective, queue states, gate
status, progress log); it never touches physics, fixtures or evidence.

Commands:
  brief        compact session brief (objective, gate, queue, blockers, log)
  check        structural validation; exit 1 on errors
  promote      WAITING -> READY when every dependency is DONE
  log          append one compact progress_log entry
  stop-status  termination decision (AGENTS.md §2); exit 0/10/11/12
  gate         recompute gate counts; optionally set a terminal state
  migrate-v2   idempotent migration from the V1 status layout
"""

from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_STATUS = ROOT / "results/2t-commercial-core-20261002/program-status.json"
P9_SPEC = "openspec/changes/p9-experimental-validation/specs/p9-experimental-validation/spec.md"
P9_SHA256 = "79fbe9b88d26fc4af5083d65d468f59c9208535f0ab389d2f3cb9a7654b88a4d"

SCHEMA_V2 = "MOTORSIM_PROGRAM_STATUS_V2"
STATES = ("READY", "IN_PROGRESS", "WAITING", "BLOCKED_LOCAL", "REVIEW", "DONE")
GATE_TERMINAL = ("PASS", "FAIL_TERMINAL")
GATE_STATES = ("OPEN", "REVIEW") + GATE_TERMINAL
MIN_READY = 3
MAX_SUMMARY = 400

EXIT_CONTINUE = 0
EXIT_STOP_A = 10
EXIT_STOP_B = 11
EXIT_STOP_C = 12


def _now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat()


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def save(path: Path, data: dict) -> None:
    text = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
    tmp.replace(path)


def _queue(data: dict) -> list[dict]:
    return data.get("queue", [])


def _by_state(data: dict, state: str) -> list[dict]:
    return [item for item in _queue(data) if item.get("state") == state]


def _deps_done(data: dict, item: dict) -> bool:
    states = {task.get("id"): task.get("state") for task in _queue(data)}
    return all(states.get(dep) == "DONE" for dep in item.get("dependencies", []))


def _open_owner_decisions(data: dict) -> list[dict]:
    return [d for d in data.get("owner_decisions_pending", []) if d.get("status", "OPEN") == "OPEN"]


def _next_approved_objective(data: dict) -> dict | None:
    current = (data.get("current_objective") or {}).get("id")
    for objective in data.get("objectives", []):
        if objective.get("id") == current:
            continue
        if objective.get("owner_approved") is True and objective.get("state") in ("APPROVED", "PROPOSED"):
            return objective
    return None


def _scope_overlap(a: str, b: str) -> bool:
    a = a.replace("\\", "/").rstrip("/")
    b = b.replace("\\", "/").rstrip("/")
    return a == b or a.startswith(b + "/") or b.startswith(a + "/")


# --------------------------------------------------------------------- gate


def gate_summary(data: dict) -> dict:
    objective = data.get("current_objective") or {}
    gate_ids = objective.get("gate_tasks", [])
    states = {task.get("id"): task.get("state") for task in _queue(data)}
    counts: dict[str, int] = {}
    for task_id in gate_ids:
        state = states.get(task_id, "MISSING")
        counts[state] = counts.get(state, 0) + 1
    previous = data.get("gate_status") or {}
    return {
        "objective": objective.get("id"),
        "state": previous.get("state", "OPEN") if previous.get("objective") == objective.get("id") else "OPEN",
        "classification": previous.get("classification") if previous.get("objective") == objective.get("id") else None,
        "evidence": previous.get("evidence", []) if previous.get("objective") == objective.get("id") else [],
        "gate_tasks_total": len(gate_ids),
        "gate_tasks_done": counts.get("DONE", 0),
        "gate_task_states": counts,
        "remaining": [task_id for task_id in gate_ids if states.get(task_id) != "DONE"],
        "updated_at": _now(),
    }


# --------------------------------------------------------------------- stop


def stop_decision(data: dict) -> dict:
    ready = _by_state(data, "READY")
    active = _by_state(data, "IN_PROGRESS") + _by_state(data, "REVIEW")
    hard = data.get("hard_stop")
    if isinstance(hard, dict) and hard.get("active"):
        return {"decision": "STOP_C_HARD_STOP", "exit": EXIT_STOP_C, "reason": hard.get("reason")}
    gate = data.get("gate_status") or {}
    objective = (data.get("current_objective") or {}).get("id")
    if gate.get("objective") == objective and gate.get("state") in GATE_TERMINAL:
        nxt = _next_approved_objective(data)
        if nxt is None:
            return {"decision": "STOP_A_GATE_REACHED", "exit": EXIT_STOP_A, "reason": f"{objective}: {gate.get('state')}"}
        return {
            "decision": "CONTINUE",
            "exit": EXIT_CONTINUE,
            "reason": f"gate {gate.get('state')}; switch to owner-approved objective {nxt.get('id')}",
            "action": "SWITCH_OBJECTIVE",
        }
    decisions = _open_owner_decisions(data)
    if decisions and not ready and not active:
        return {
            "decision": "STOP_B_OWNER_DECISION",
            "exit": EXIT_STOP_B,
            "reason": ", ".join(str(d.get("id")) for d in decisions),
        }
    result = {"decision": "CONTINUE", "exit": EXIT_CONTINUE, "reason": f"{len(ready)} READY, {len(active)} active"}
    if len(ready) < MIN_READY:
        result["action"] = "REPLAN_REQUIRED"
    return result


# -------------------------------------------------------------------- check


def check(data: dict, root: Path = ROOT) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    objective = data.get("current_objective")
    if not isinstance(objective, dict) or not objective.get("id"):
        errors.append("current_objective missing")
    else:
        for key in ("change", "spec", "completion_criterion", "gate_tasks"):
            if not objective.get(key):
                errors.append(f"current_objective.{key} missing")
    ids = [task.get("id") for task in _queue(data)]
    seen: set = set()
    for task_id in ids:
        if task_id in seen:
            errors.append(f"duplicate task id {task_id}")
        seen.add(task_id)
    known = set(ids)
    for task_id in (objective or {}).get("gate_tasks", []) if isinstance(objective, dict) else []:
        if task_id not in known:
            errors.append(f"gate task {task_id} not in queue")
    for task in _queue(data):
        tid = task.get("id")
        state = task.get("state")
        if state not in STATES:
            errors.append(f"{tid}: unknown state {state!r}")
        for dep in task.get("dependencies", []):
            if dep not in known:
                errors.append(f"{tid}: unknown dependency {dep}")
        if state == "BLOCKED_LOCAL":
            unblock = task.get("unblock_tasks") or []
            if not unblock and not task.get("no_local_unblock_reason"):
                errors.append(f"{tid}: BLOCKED_LOCAL without unblock_tasks or no_local_unblock_reason")
            for ref in unblock:
                if ref not in known:
                    errors.append(f"{tid}: unblock task {ref} not in queue")
            if not task.get("blocker"):
                errors.append(f"{tid}: BLOCKED_LOCAL without blocker")
        if state == "WAITING" and _deps_done(data, task):
            warnings.append(f"{tid}: WAITING with all dependencies DONE (run promote)")
        if state == "READY" and not _deps_done(data, task):
            warnings.append(f"{tid}: READY with unfinished dependencies")
    active = [t for t in _queue(data) if t.get("state") == "IN_PROGRESS"]
    for i, first in enumerate(active):
        for second in active[i + 1:]:
            for a in first.get("write_scope", []):
                for b in second.get("write_scope", []):
                    if _scope_overlap(a, b):
                        errors.append(f"write_scope conflict {first.get('id')}:{a} <-> {second.get('id')}:{b}")
    gate = data.get("gate_status")
    if not isinstance(gate, dict):
        errors.append("gate_status missing")
    elif gate.get("state") not in GATE_STATES:
        errors.append(f"gate_status.state invalid {gate.get('state')!r}")
    if not isinstance(data.get("progress_log"), list):
        errors.append("progress_log missing")
    ready = len(_by_state(data, "READY"))
    if ready < MIN_READY:
        warnings.append(f"only {ready} READY (< {MIN_READY}): replan the queue against CURRENT_OBJECTIVE")
    p9 = root / P9_SPEC
    if p9.exists():
        # Canonical hash is over git (LF) content; Windows checkouts may use CRLF.
        digest = hashlib.sha256(p9.read_bytes().replace(b"\r\n", b"\n")).hexdigest()
        if digest != P9_SHA256:
            errors.append(f"P9 spec hash mismatch {digest}")
    else:
        warnings.append("P9 spec not present in this checkout; hash not verified")
    return errors, warnings


# ------------------------------------------------------------------ migrate

V1_CLOSURE_GATE = [f"C{i}" for i in range(1, 19)]

CURRENT_OBJECTIVE_V2 = {
    "id": "MOTORSIM_2T_V1_CLOSURE",
    "change": "openspec/changes/two-stroke-v1-closure",
    "spec": "openspec/changes/two-stroke-v1-closure/specs/two-stroke-v1-closure/spec.md",
    "completion_criterion": (
        "All gate tasks C1-C18 DONE and a terminal classification recorded in gate_status: "
        "PASS = GENERAL_PURPOSE_2T_SIMULATION_CORE_VERIFIED (synthetic, CONDITIONAL_ON_P4, no experimental "
        "validation) when FIXTURE_A_PRIME and FIXTURE_B_PRIME pass every requirement of the spec; "
        "FAIL_TERMINAL = exact failed/incomplete gates stated without extending a horizon or relaxing a criterion."
    ),
    "gate_tasks": V1_CLOSURE_GATE,
    "durable_queue": "results/2t-commercial-core-20261002/program-status.json#queue",
    "set_by": "owner order 2026-10-06 (AGENTS_V2)",
}

OBJECTIVES_V2 = [
    {"id": "MOTORSIM_2T_V1_CLOSURE", "state": "ACTIVE", "owner_approved": True},
    {
        "id": "ENGINE_PHYSICS_V1",
        "state": "PROPOSED",
        "owner_approved": False,
        "summary": "Single production core plus STANDARD_V1 engine physics (fuel-bound Wiebe, two-zone "
        "scavenging profile, port Cd, cylinder/duct heat transfer, FMEP) and plausibility gates.",
    },
    {
        "id": "FULL_RPM_SWEEP_V1",
        "state": "PROPOSED",
        "owner_approved": False,
        "summary": "ENGINEERING FAST mode, compiled kernels, parallel RPM points with warm start; "
        "12-15 point WOT sweep in minutes with configuration comparison.",
    },
    {
        "id": "TUNING_WORKFLOW_AND_REFERENCE_CORRELATION_V1",
        "state": "PROPOSED",
        "owner_approved": False,
        "summary": "KT100 sanity/calibration tiers, dynamic reed V1, exhaust builder, port time-area, "
        "exhaust-port wave plots.",
    },
]

HELPER_TASKS_V2 = [
    {
        "id": "V2-early-regression",
        "description": "Early L0 drift check on current HEAD: focused integrated/evidence tests and P4-P8 "
        "regression launched through scripts/agents/run_logged.py; record only the summary. Not the C17 "
        "closing run and not gate evidence.",
        "dependencies": [],
        "state": "READY",
        "blocker": None,
        "commits": [],
        "evidence": [],
        "next_action": "Run with run_logged.py, log counts in progress_log, open new tasks for any failure.",
        "objective": "MOTORSIM_2T_V1_CLOSURE",
        "owner_role": "verification",
        "evidence_level": "L0",
        "write_scope": ["results/2t-v1-closure-20261006/early-regression"],
        "classification": "BLOCKS_2T_V1",
    },
    {
        "id": "V2-C13-draft",
        "description": "Non-binding draft of the A'/B' campaign preregistration content (horizon, detectors, "
        "outputs, RPM pair for C16) so C13 can be committed immediately once C11/C12 are DONE. The draft "
        "is not the C13 preregistration and fixes nothing that depends on the mesh study.",
        "dependencies": [],
        "state": "READY",
        "blocker": None,
        "commits": [],
        "evidence": [],
        "next_action": "Write the draft from the closure spec/design; leave mesh-dependent values as explicit placeholders.",
        "objective": "MOTORSIM_2T_V1_CLOSURE",
        "owner_role": "evidence/release reviewer",
        "evidence_level": "L0",
        "write_scope": ["docs/gasdynamic/v1_closure_campaign_preregistration_draft.md"],
        "classification": "BLOCKS_2T_V1",
    },
]

POST_V1_BACKLOG_IDS = {"dynamic-reed-stage-coupling", "fuel-library-combustion-v2"}


def migrate_v2(data: dict) -> list[str]:
    """Return a list of human-readable changes; mutates ``data`` in place."""
    changes: list[str] = []
    if data.get("schema") != SCHEMA_V2:
        history = data.setdefault("schema_history", [])
        if data.get("schema") and data["schema"] not in history:
            history.append(data["schema"])
        data["schema"] = SCHEMA_V2
        changes.append(f"schema -> {SCHEMA_V2}")
    if not data.get("current_objective"):
        data["current_objective"] = json.loads(json.dumps(CURRENT_OBJECTIVE_V2))
        changes.append("current_objective added")
    if not data.get("objectives"):
        data["objectives"] = json.loads(json.dumps(OBJECTIVES_V2))
        changes.append("objectives added")
    for key, default in (("owner_decisions_pending", []), ("hard_stop", None), ("decisions", [])):
        if key not in data:
            data[key] = default
            changes.append(f"{key} added")
    if "progress_log" not in data:
        data["progress_log"] = []
        changes.append("progress_log added")

    states = {task.get("id"): task.get("state") for task in _queue(data)}
    for task in _queue(data):
        tid = task.get("id")
        external = [dep for dep in task.get("dependencies", []) if dep not in states]
        if external:
            task["dependencies"] = [dep for dep in task["dependencies"] if dep in states]
            task.setdefault("external_dependencies", []).extend(external)
            changes.append(f"{tid}: non-task dependencies moved to external_dependencies")
        if task.get("evidence") == [[]]:
            task["evidence"] = []
        if task.get("state") == "DONE_CONDITIONAL":
            task["state"] = "DONE"
            task.setdefault(
                "qualification",
                "Pre-V2 state DONE_CONDITIONAL: scope limited as described in evidence/next_action; "
                "not end-to-end acceptance.",
            )
            if tid in POST_V1_BACKLOG_IDS:
                task.setdefault("classification", "POST_2T_V1_BACKLOG")
            changes.append(f"{tid}: DONE_CONDITIONAL -> DONE + qualification")
        # A BLOCKED_LOCAL without an unblock plan whose dependencies are not all DONE
        # is a dependency wait; the original blocker text is kept for reassessment.
        if (
            task.get("state") == "BLOCKED_LOCAL"
            and not task.get("unblock_tasks")
            and not task.get("no_local_unblock_reason")
            and (
                task.get("blocker") == "Prerequisite gates not yet complete"
                or any(states.get(dep) != "DONE" for dep in task.get("dependencies", []))
            )
        ):
            task["state"] = "WAITING"
            task["previous_blocker"] = task.pop("blocker")
            task["blocker"] = None
            changes.append(f"{tid}: dependency wait BLOCKED_LOCAL -> WAITING")
        if (
            tid == "17d-fuel-properties"
            and task.get("state") == "BLOCKED_LOCAL"
            and str(task.get("blocker", "")).startswith("No approved fuel record")
            and states.get("C4") == "DONE"
        ):
            task["state"] = "DONE"
            task["resolution"] = "SUPERSEDED_BY_LATER_CAPABILITY"
            task["previous_blocker"] = task.get("blocker")
            task["blocker"] = None
            task["qualification"] = (
                "Explicit fuel properties now exist only as SYNTHETIC_FUEL_SURROGATE_V1 (C4, "
                "FUEL_COUPLED_COMBUSTION_V1) and the MODELED_SURROGATE C8H18 profile of FUEL_LIBRARY_V1 "
                "(fuel-library-combustion-v2). ANCAP chemistry remains unknown; no real-fuel claim; P7 Q_F "
                "is still not an LHV."
            )
            task.setdefault("evidence", []).append(
                "Superseded per queue items C4 and fuel-library-combustion-v2 and "
                "openspec/changes/two-stroke-v1-closure/tasks.md (C4, additive capability section)."
            )
            changes.append(f"{tid}: obsolete BLOCKED_LOCAL -> DONE (superseded)")

    known = {task.get("id") for task in _queue(data)}
    ready = len(_by_state(data, "READY"))
    for helper in HELPER_TASKS_V2:
        if ready >= MIN_READY:
            break
        if helper["id"] not in known:
            data["queue"].append(json.loads(json.dumps(helper)))
            known.add(helper["id"])
            ready += 1
            changes.append(f"{helper['id']}: READY helper task added (replan: READY < {MIN_READY})")

    cont = data.get("continuation_status")
    if isinstance(cont, dict) and "superseded_by" not in cont:
        cont["superseded_by"] = "current_objective, gate_status, progress_log (MOTORSIM_PROGRAM_STATUS_V2)"
        changes.append("continuation_status marked superseded")

    gate = gate_summary(data)
    if (data.get("gate_status") or {}).get("objective") != gate["objective"] or "gate_status" not in data:
        changes.append("gate_status initialized")
    data["gate_status"] = gate
    if changes:
        data["progress_log"].append(
            {
                "at": _now(),
                "task": "AGENTS_V2",
                "kind": "process",
                "summary": "Migrated program status to V2: " + "; ".join(changes)[: MAX_SUMMARY - 40],
            }
        )
    return changes


# ---------------------------------------------------------------------- CLI


def _brief(data: dict, as_json: bool) -> str:
    objective = data.get("current_objective") or {}
    gate = data.get("gate_status") or {}
    queue = _queue(data)
    groups = {state: [t.get("id") for t in queue if t.get("state") == state] for state in STATES}
    blocked = [
        {
            "id": t.get("id"),
            "blocker": str(t.get("blocker"))[:200],
            "unblock_tasks": t.get("unblock_tasks", []),
        }
        for t in queue
        if t.get("state") == "BLOCKED_LOCAL"
    ]
    ready = [
        {"id": t.get("id"), "description": str(t.get("description"))[:160], "next_action": str(t.get("next_action"))[:160]}
        for t in queue
        if t.get("state") == "READY"
    ]
    brief = {
        "current_objective": {k: objective.get(k) for k in ("id", "change", "spec", "completion_criterion")},
        "gate": {k: gate.get(k) for k in ("state", "gate_tasks_done", "gate_tasks_total", "remaining")},
        "counts": {state: len(ids) for state, ids in groups.items()},
        "ready": ready,
        "in_progress": groups["IN_PROGRESS"] + groups["REVIEW"],
        "waiting": groups["WAITING"],
        "blocked_local": blocked,
        "owner_decisions_pending": [d.get("id") for d in _open_owner_decisions(data)],
        "recent_progress": data.get("progress_log", [])[-5:],
        "stop_status": stop_decision(data),
    }
    if as_json:
        return json.dumps(brief, indent=2, ensure_ascii=False)
    lines = [
        f"CURRENT_OBJECTIVE: {brief['current_objective']['id']}",
        f"  spec: {brief['current_objective']['spec']}",
        f"  completion: {brief['current_objective']['completion_criterion']}",
        f"GATE: {gate.get('state')} {gate.get('gate_tasks_done')}/{gate.get('gate_tasks_total')} "
        f"remaining={','.join(gate.get('remaining') or [])}",
        "COUNTS: " + " ".join(f"{s}={n}" for s, n in brief["counts"].items()),
        "READY:",
        *[f"  - {t['id']}: {t['description']}" for t in ready],
        "ACTIVE: " + ", ".join(brief["in_progress"]),
        "WAITING: " + ", ".join(brief["waiting"]),
        "BLOCKED_LOCAL:",
        *[f"  - {b['id']}: {b['blocker']} | unblock={b['unblock_tasks']}" for b in blocked],
        "OWNER_DECISIONS: " + ", ".join(map(str, brief["owner_decisions_pending"])),
        "RECENT_PROGRESS:",
        *[f"  - {e.get('at')} {e.get('task')}: {str(e.get('summary'))[:160]}" for e in brief["recent_progress"]],
        f"STOP_STATUS: {brief['stop_status']['decision']} ({brief['stop_status']['reason']})"
        + (f" ACTION={brief['stop_status']['action']}" if brief["stop_status"].get("action") else ""),
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--status", type=Path, default=DEFAULT_STATUS)
    sub = parser.add_subparsers(dest="command", required=True)
    p_brief = sub.add_parser("brief")
    p_brief.add_argument("--json", action="store_true")
    sub.add_parser("check")
    p_promote = sub.add_parser("promote")
    p_promote.add_argument("--dry-run", action="store_true")
    p_log = sub.add_parser("log")
    p_log.add_argument("--task", required=True)
    p_log.add_argument("--summary", required=True)
    p_log.add_argument("--kind", default="task")
    p_log.add_argument("--commit")
    p_stop = sub.add_parser("stop-status")
    p_stop.add_argument("--json", action="store_true")
    p_gate = sub.add_parser("gate")
    p_gate.add_argument("--set", choices=GATE_STATES)
    p_gate.add_argument("--classification")
    p_gate.add_argument("--evidence", action="append", default=[])
    p_migrate = sub.add_parser("migrate-v2")
    p_migrate.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    data = load(args.status)
    if args.command == "brief":
        print(_brief(data, args.json))
        return 0
    if args.command == "check":
        root = args.status.resolve().parents[2] if args.status != DEFAULT_STATUS else ROOT
        errors, warnings = check(data, root)
        for message in errors:
            print(f"ERROR {message}")
        for message in warnings:
            print(f"WARN  {message}")
        print("CHECK " + ("FAIL" if errors else "OK"))
        return 1 if errors else 0
    if args.command == "promote":
        promoted = [t.get("id") for t in _queue(data) if t.get("state") == "WAITING" and _deps_done(data, t)]
        for task in _queue(data):
            if task.get("id") in promoted:
                task["state"] = "READY"
        if promoted:
            data["gate_status"] = gate_summary(data)
            if not args.dry_run:
                save(args.status, data)
        print("PROMOTED " + (", ".join(promoted) if promoted else "none"))
        return 0
    if args.command == "log":
        summary = args.summary.strip()
        if len(summary) > MAX_SUMMARY:
            print(f"ERROR summary longer than {MAX_SUMMARY} chars; keep progress_log compact")
            return 1
        entry = {"at": _now(), "task": args.task, "kind": args.kind, "summary": summary}
        if args.commit:
            entry["commit"] = args.commit
        data.setdefault("progress_log", []).append(entry)
        save(args.status, data)
        print("LOGGED")
        return 0
    if args.command == "stop-status":
        decision = stop_decision(data)
        print(json.dumps(decision, ensure_ascii=False) if args.json else f"{decision['decision']}: {decision['reason']}")
        return decision["exit"]
    if args.command == "gate":
        gate = gate_summary(data)
        if args.set:
            if args.set == "PASS" and gate["remaining"]:
                print(f"ERROR cannot set PASS with remaining gate tasks {gate['remaining']}")
                return 1
            if args.set in GATE_TERMINAL and not (args.classification and args.evidence):
                print("ERROR terminal gate state requires --classification and at least one --evidence")
                return 1
            gate["state"] = args.set
            gate["classification"] = args.classification
            gate["evidence"] = args.evidence
        data["gate_status"] = gate
        save(args.status, data)
        print(json.dumps({k: gate[k] for k in ("objective", "state", "gate_tasks_done", "gate_tasks_total")}))
        return 0
    if args.command == "migrate-v2":
        changes = migrate_v2(data)
        if changes and not args.dry_run:
            save(args.status, data)
        print("\n".join(changes) if changes else "already V2; no changes")
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
