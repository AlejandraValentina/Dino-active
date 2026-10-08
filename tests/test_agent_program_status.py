"""Tests for the autonomous-agent process tooling in scripts/agents (no physics)."""

from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "agents"))

import launcher  # noqa: E402
import program_status as ps  # noqa: E402
import run_logged  # noqa: E402


def _task(tid: str, state: str, deps: list[str] | None = None, **extra) -> dict:
    return {"id": tid, "state": state, "dependencies": deps or [], **extra}


def _status(queue: list[dict], gate_tasks: list[str] | None = None) -> dict:
    gate_tasks = gate_tasks if gate_tasks is not None else [t["id"] for t in queue]
    return {
        "schema": ps.SCHEMA_V2,
        "current_objective": {
            "id": "OBJ",
            "change": "openspec/changes/obj",
            "spec": "openspec/changes/obj/specs/obj/spec.md",
            "completion_criterion": "all gate tasks DONE",
            "gate_tasks": gate_tasks,
        },
        "objectives": [{"id": "OBJ", "state": "ACTIVE", "owner_approved": True}],
        "queue": queue,
        "gate_status": {"objective": "OBJ", "state": "OPEN"},
        "progress_log": [],
        "owner_decisions_pending": [],
        "hard_stop": {"active": False},
    }


def _ready3() -> list[dict]:
    return [_task(f"R{i}", "READY") for i in range(3)]


class StopDecisionTests(unittest.TestCase):
    def test_continue_with_ready_work(self):
        decision = ps.stop_decision(_status(_ready3()))
        self.assertEqual(decision["exit"], ps.EXIT_CONTINUE)
        self.assertNotIn("action", decision)

    def test_replan_when_ready_below_minimum(self):
        decision = ps.stop_decision(_status([_task("R0", "READY"), _task("W", "WAITING", ["R0"])]))
        self.assertEqual(decision["exit"], ps.EXIT_CONTINUE)
        self.assertEqual(decision["action"], "REPLAN_REQUIRED")

    def test_stop_a_on_terminal_gate_without_next_objective(self):
        data = _status([_task("C1", "DONE")])
        data["gate_status"] = {"objective": "OBJ", "state": "PASS"}
        self.assertEqual(ps.stop_decision(data)["exit"], ps.EXIT_STOP_A)

    def test_switch_objective_when_next_is_owner_approved(self):
        data = _status([_task("C1", "DONE")])
        data["gate_status"] = {"objective": "OBJ", "state": "FAIL_TERMINAL"}
        data["objectives"].append({"id": "NEXT", "state": "PROPOSED", "owner_approved": True})
        decision = ps.stop_decision(data)
        self.assertEqual(decision["exit"], ps.EXIT_CONTINUE)
        self.assertEqual(decision["action"], "SWITCH_OBJECTIVE")

    def test_unapproved_next_objective_does_not_switch(self):
        data = _status([_task("C1", "DONE")])
        data["gate_status"] = {"objective": "OBJ", "state": "PASS"}
        data["objectives"].append({"id": "NEXT", "state": "PROPOSED", "owner_approved": False})
        self.assertEqual(ps.stop_decision(data)["exit"], ps.EXIT_STOP_A)

    def test_stop_b_only_without_ready_or_active_work(self):
        data = _status([_task("B", "BLOCKED_LOCAL", no_local_unblock_reason="owner choice")])
        data["owner_decisions_pending"] = [{"id": "D1", "status": "OPEN"}]
        self.assertEqual(ps.stop_decision(data)["exit"], ps.EXIT_STOP_B)
        data["queue"].append(_task("R", "READY"))
        self.assertEqual(ps.stop_decision(data)["exit"], ps.EXIT_CONTINUE)

    def test_stop_c_hard_stop_has_priority(self):
        data = _status(_ready3())
        data["hard_stop"] = {"active": True, "reason": "repo corrupt"}
        self.assertEqual(ps.stop_decision(data)["exit"], ps.EXIT_STOP_C)

    def test_blocked_local_alone_is_not_a_stop(self):
        data = _status([_task("B", "BLOCKED_LOCAL", unblock_tasks=["U"]), _task("U", "READY")])
        self.assertEqual(ps.stop_decision(data)["exit"], ps.EXIT_CONTINUE)


class CheckTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())

    def test_valid_status_passes(self):
        errors, _ = ps.check(_status(_ready3()), self.root)
        self.assertEqual(errors, [])

    def test_blocked_local_requires_unblock_plan(self):
        errors, _ = ps.check(_status(_ready3() + [_task("B", "BLOCKED_LOCAL")]), self.root)
        self.assertTrue(any("BLOCKED_LOCAL without" in e for e in errors))

    def test_unknown_dependency_and_state(self):
        errors, _ = ps.check(_status(_ready3() + [_task("X", "DONE_CONDITIONAL", ["missing"])]), self.root)
        self.assertTrue(any("unknown state" in e for e in errors))
        self.assertTrue(any("unknown dependency" in e for e in errors))

    def test_write_scope_conflict_between_in_progress_tasks(self):
        queue = _ready3() + [
            _task("A", "IN_PROGRESS", write_scope=["motorsim/"]),
            _task("B", "IN_PROGRESS", write_scope=["motorsim/integrated_2t.py"]),
        ]
        errors, _ = ps.check(_status(queue), self.root)
        self.assertTrue(any("write_scope conflict" in e for e in errors))

    def test_ready_below_minimum_is_warning(self):
        errors, warnings = ps.check(_status([_task("R", "READY")]), self.root)
        self.assertEqual(errors, [])
        self.assertTrue(any("READY" in w for w in warnings))

    def test_p9_hash_is_line_ending_independent(self):
        real = ROOT / ps.P9_SPEC
        if not real.exists():
            self.skipTest("P9 spec not in this checkout")
        lf = real.read_bytes().replace(b"\r\n", b"\n")
        for content in (lf, lf.replace(b"\n", b"\r\n")):
            target = self.root / ps.P9_SPEC
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
            errors, _ = ps.check(_status(_ready3()), self.root)
            self.assertEqual(errors, [], content[:0])
        target.write_bytes(lf + b"tamper\n")
        errors, _ = ps.check(_status(_ready3()), self.root)
        self.assertTrue(any("P9 spec hash mismatch" in e for e in errors))


class MigrationTests(unittest.TestCase):
    def _v1(self) -> dict:
        return {
            "schema": "MOTORSIM_PROGRAM_STATUS_V1",
            "queue": [
                _task("C1", "DONE"),
                _task("C2", "BLOCKED_LOCAL", ["C1", "free text provenance"], blocker="Prerequisite gates not yet complete"),
                _task("dynamic-reed-stage-coupling", "DONE_CONDITIONAL"),
            ],
        }

    def test_migration_is_idempotent_and_valid(self):
        data = self._v1()
        self.assertTrue(ps.migrate_v2(data))
        snapshot = copy.deepcopy(data)
        self.assertEqual(ps.migrate_v2(data), [])
        self.assertEqual(data, snapshot)
        states = {t["id"]: t for t in data["queue"]}
        self.assertEqual(states["dynamic-reed-stage-coupling"]["state"], "DONE")
        self.assertIn("qualification", states["dynamic-reed-stage-coupling"])
        self.assertNotEqual(states["C2"]["state"], "BLOCKED_LOCAL")
        self.assertEqual(states["C2"]["external_dependencies"], ["free text provenance"])
        self.assertEqual(states["C2"]["dependencies"], ["C1"])
        self.assertEqual(data["schema"], ps.SCHEMA_V2)

    def test_dependency_wait_with_any_blocker_text_becomes_waiting(self):
        data = self._v1()
        data["queue"] += [
            _task("C3", "READY"),
            _task("C4", "BLOCKED_LOCAL", ["C3"], blocker="C3 gate remains incomplete"),
            _task("C5", "BLOCKED_LOCAL", ["C1"], blocker="real local blocker"),
        ]
        ps.migrate_v2(data)
        states = {t["id"]: t for t in data["queue"]}
        self.assertEqual(states["C4"]["state"], "WAITING")
        self.assertEqual(states["C4"]["previous_blocker"], "C3 gate remains incomplete")
        # Dependencies all DONE: a genuine blocker stays BLOCKED_LOCAL for check() to flag.
        self.assertEqual(states["C5"]["state"], "BLOCKED_LOCAL")


class CliTests(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.path = self.dir / "program-status.json"
        data = _status([_task("C1", "DONE"), _task("C2", "WAITING", ["C1"]), _task("C3", "WAITING", ["C2"])])
        ps.save(self.path, data)

    def _run(self, *args: str) -> int:
        return ps.main(["--status", str(self.path), *args])

    def test_promote_moves_only_satisfied_waiting_tasks(self):
        self.assertEqual(self._run("promote"), 0)
        states = {t["id"]: t["state"] for t in ps.load(self.path)["queue"]}
        self.assertEqual(states, {"C1": "DONE", "C2": "READY", "C3": "WAITING"})

    def test_log_rejects_long_summary(self):
        self.assertEqual(self._run("log", "--task", "C2", "--summary", "x" * (ps.MAX_SUMMARY + 1)), 1)
        self.assertEqual(self._run("log", "--task", "C2", "--summary", "ok"), 0)
        self.assertEqual(len(ps.load(self.path)["progress_log"]), 1)

    def test_gate_pass_requires_all_gate_tasks_done(self):
        self.assertEqual(self._run("gate", "--set", "PASS", "--classification", "X", "--evidence", "e"), 1)
        self.assertEqual(ps.load(self.path)["gate_status"]["state"], "OPEN")

    def test_saved_json_uses_lf(self):
        self._run("log", "--task", "C2", "--summary", "ok")
        raw = self.path.read_bytes()
        self.assertNotIn(b"\r\n", raw)
        self.assertTrue(raw.endswith(b"\n"))


class RunLoggedTests(unittest.TestCase):
    def test_summary_captures_exit_tail_and_errors(self):
        out = Path(tempfile.mkdtemp())
        code = "import sys; print('step 1'); print('Traceback: boom'); sys.exit(3)"
        summary = run_logged.run("job", out, [sys.executable, "-c", code], 60, None)
        self.assertEqual(summary["exit_code"], 3)
        self.assertFalse(summary["timed_out"])
        self.assertIn("step 1", summary["tail"])
        self.assertTrue(any("Traceback" in line for line in summary["error_lines"]))
        self.assertTrue((out / "job.log").exists())
        self.assertEqual(json.loads((out / "job.summary.json").read_text(encoding="utf-8"))["exit_code"], 3)

    def test_timeout_kills_silent_process(self):
        out = Path(tempfile.mkdtemp())
        summary = run_logged.run("slow", out, [sys.executable, "-c", "import time; time.sleep(30)"], 1, None)
        self.assertTrue(summary["timed_out"])
        self.assertEqual(summary["exit_code"], 124)
        self.assertLess(summary["duration_s"], 20)

    def test_embeds_campaign_summary(self):
        out = Path(tempfile.mkdtemp())
        campaign = out / "campaign.json"
        campaign.write_text('{"classification": "PASS"}', encoding="utf-8")
        summary = run_logged.run("c", out, [sys.executable, "-c", "pass"], 60, campaign)
        self.assertEqual(summary["campaign_summary"], {"classification": "PASS"})


class LauncherTests(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.status = self.dir / "status.json"
        ps.save(self.status, _status(_ready3()))

    def _config(self, agent_command: list[str], **overrides) -> dict:
        config = dict(launcher.DEFAULTS)
        config.update(
            {
                "repo": ROOT,
                "status": self.status,
                "log_dir": self.dir / "sessions",
                "agent_command": agent_command,
                "cooldown_s": 0,
                "session_timeout_s": 60,
                **overrides,
            }
        )
        return config

    def _events(self) -> list[dict]:
        lines = (self.dir / "sessions" / "launcher.jsonl").read_text(encoding="utf-8").splitlines()
        return [json.loads(line) for line in lines]

    def test_dry_run_renders_prompt_without_running(self):
        code = launcher.run_loop(self._config(["false-agent", "{prompt_file}"]), dry_run=True)
        self.assertEqual(code, ps.EXIT_CONTINUE)
        self.assertEqual(self._events()[-1]["event"], "DRY_RUN")
        prompts = list((self.dir / "sessions").glob("*/prompt.md"))
        self.assertEqual(len(prompts), 1)
        self.assertIn("AGENTS.md", prompts[0].read_text(encoding="utf-8"))

    def test_no_progress_safeguard(self):
        code = launcher.run_loop(self._config([sys.executable, "-c", "pass"], max_no_progress_sessions=2))
        self.assertEqual(code, launcher.EXIT_NO_PROGRESS)
        self.assertFalse((self.dir / "sessions" / "launcher.lock").exists())

    def test_progressing_agent_runs_until_gate_stop(self):
        # Fake agent: logs progress each session and closes the gate on the third.
        script = (
            "import json,sys\n"
            "p=sys.argv[1]\n"
            "d=json.load(open(p,encoding='utf-8'))\n"
            "d['progress_log'].append({'task':'R','summary':'step'})\n"
            "if len(d['progress_log'])>=3: d['gate_status']['state']='PASS'\n"
            "open(p,'w',encoding='utf-8').write(json.dumps(d))\n"
        )
        code = launcher.run_loop(self._config([sys.executable, "-c", script, str(self.status)], max_sessions=10))
        self.assertEqual(code, ps.EXIT_STOP_A)
        self.assertEqual(len(ps.load(self.status)["progress_log"]), 3)

    def test_existing_lock_blocks_second_launcher(self):
        (self.dir / "sessions").mkdir()
        (self.dir / "sessions" / "launcher.lock").write_text("{}", encoding="utf-8")
        code = launcher.run_loop(self._config([sys.executable, "-c", "pass"]))
        self.assertEqual(code, launcher.EXIT_LOCKED)


if __name__ == "__main__":
    unittest.main()
