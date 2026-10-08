import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from dev_orchestrator import roadmap_supervisor as sup


class SupervisorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.r = self.root / "roadmap-executor"
        self.r.mkdir()
        (self.r / "state.json").write_text(json.dumps({"current_phase": "TEST", "current_subphase": "T-01", "blockers": []}))
        (self.r / "current_tasks.json").write_text(json.dumps({"phase": "TEST", "active_task": "T-01", "tasks": [{"id": "T-01", "phase": "TEST", "description": "fake", "status": "TODO"}]}))
        self.config = self.root / "config.json"
        self.config.write_text(json.dumps({"agent_command": [sys.executable, "-c", "print('fake')"], "poll_seconds": 0.02, "agent_timeout_seconds": 2, "max_no_progress_attempts": 1, "max_invocations": 0, "live_status_file": str(self.r / "LIVE_STATUS.md")}))
        self.patcher = patch.multiple(sup, ROOT=self.root, R=self.r, CFG=self.config, STATE=self.r / "supervisor_state.json", LOCK=self.r / "supervisor.lock", STOP_REQUEST=self.r / "supervisor.stop", DEFAULT_LIVE_STATUS=self.r / "LIVE_STATUS.md", git_head=lambda: "HEAD-TEST", git_status=lambda: [])
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()
        self.tmp.cleanup()

    def _fake_result(self, progress=False):
        before = sup._roadmap_snapshot(); after = dict(before)
        if progress: after["active_task"] = "T-02"
        return 0, before, after, "inv"

    def test_run_keeps_lock_between_fake_invocations_and_reports_limit(self):
        seen = []
        def fake_invoke():
            seen.append(sup.LOCK.exists())
            return self._fake_result(progress=True)
        self.config.write_text(json.dumps({"max_invocations": 2, "max_no_progress_attempts": 3, "live_status_file": str(self.r / "LIVE_STATUS.md")}))
        with patch.object(sup, "_invoke", side_effect=fake_invoke):
            self.assertEqual(sup._run_loop(), "SUPERVISOR_BLOCKED_INVOCATION_LIMIT")
        self.assertEqual(seen, [True, True])
        self.assertFalse(sup.LOCK.exists())
        self.assertEqual(sup.read(sup.STATE, {})["terminal_reason"], "SUPERVISOR_BLOCKED_INVOCATION_LIMIT")

    def test_stale_lock_is_recovered_but_live_lock_is_not(self):
        sup.write(sup.LOCK, {"pid": 2**30})
        with patch.object(sup, "pid_alive", return_value=False): self.assertTrue(sup.acquire())
        sup.release()
        sup.write(sup.LOCK, {"pid": os.getpid() + 1})
        with patch.object(sup, "pid_alive", return_value=True): self.assertFalse(sup.acquire())

    def test_stop_request_never_replaces_supervisor_pid(self):
        sup.write(sup.STATE, {"pid": 424242, "status": "RUNNING"})
        with patch.object(sup, "live_path", return_value=self.r / "LIVE_STATUS.md"):
            self.assertEqual(sup.main(["supervisor", "stop"]), 0)
        self.assertEqual(sup.read(sup.STATE, {})["pid"], 424242)
        self.assertEqual(sup.read(sup.STOP_REQUEST, {})["requested_by"], os.getpid())

    def test_binary_invalid_output_is_preserved_and_decoded(self):
        code = "import sys; sys.stdout.buffer.write(b'good\\xff\\n'); sys.stdout.flush()"
        self.config.write_text(json.dumps({"agent_command": [sys.executable, "-c", code], "poll_seconds": 0.01, "agent_timeout_seconds": 2, "live_status_file": str(self.r / "LIVE_STATUS.md")}))
        self.assertEqual(sup._invoke()[0], 0)
        invocation = next((self.r / "invocations").iterdir())
        self.assertIn("good", sup._tail(invocation / "stdout.log")[0])
        self.assertTrue((self.r / "LIVE_STATUS.md").exists())

    def test_heartbeat_updates_during_long_child(self):
        code = "import time; print('long'); time.sleep(.25)"
        self.config.write_text(json.dumps({"agent_command": [sys.executable, "-c", code], "poll_seconds": 0.03, "agent_timeout_seconds": 2, "live_status_file": str(self.r / "LIVE_STATUS.md")}))
        result = []
        import threading
        thread = threading.Thread(target=lambda: result.append(sup._invoke()))
        thread.start()
        deadline = time.time() + 1.0
        while time.time() < deadline and not (self.r / "LIVE_STATUS.md").exists(): time.sleep(.02)
        live = (self.r / "LIVE_STATUS.md").read_text(encoding="utf-8")
        thread.join(3)
        self.assertIn("Child PID:", live)
        self.assertTrue(result)

    def test_no_progress_retries_then_blocks(self):
        self.config.write_text(json.dumps({"max_invocations": 0, "max_no_progress_attempts": 1, "live_status_file": str(self.r / "LIVE_STATUS.md")}))
        with patch.object(sup, "_invoke", side_effect=[self._fake_result(), self._fake_result()]):
            self.assertEqual(sup._run_loop(), "SUPERVISOR_BLOCKED_NO_PROGRESS")
        self.assertEqual(sup.read(sup.STATE, {})["invocation_count"], 1)

    def test_live_status_contains_required_fields_and_tail(self):
        invocation = self.r / "invocations" / "abc"; invocation.mkdir(parents=True)
        (invocation / "stdout.log").write_bytes(b"one\xff\ntwo\n")
        sup.write(sup.STATE, {"status": "RUNNING", "pid": os.getpid(), "child_pid": os.getpid(), "current_invocation": "abc", "current_phase": "TEST", "current_task": "T-01", "done": 0, "total": 1, "HEAD": "abc", "last_heartbeat": sup.now(), "terminal_reason": None})
        sup.publish_live()
        text = (self.r / "LIVE_STATUS.md").read_text(encoding="utf-8")
        for field in ("Current UTC", "Current local", "Supervisor", "Child PID", "Phase/task", "DONE/total", "Invocation", "Elapsed agent time", "HEAD", "Terminal reason", "one"):
            self.assertIn(field, text)


if __name__ == "__main__": unittest.main()
