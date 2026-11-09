"""F16: receipt PASS sólo después de terminación, exit code y recursos cerrados."""
from pathlib import Path
from types import SimpleNamespace
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from motorsim.desktop.acceptance_terminal import (default_worker_probe,
                                                   finalize_acceptance)


class FakeProcess:
    def __init__(self, code=0, *, timeout=False):
        self.code = code
        self.timeout = timeout
        self.terminated = False
        self.killed = False
        self.calls = []

    def wait(self, timeout=None):
        self.calls.append(("wait", timeout))
        if self.timeout:
            raise subprocess.TimeoutExpired("fake", timeout)
        return self.code

    def terminate(self):
        self.terminated = True
        self.calls.append(("terminate", None))

    def kill(self):
        self.killed = True
        self.calls.append(("kill", None))


PAYLOAD = {"schema": "TEST_ACCEPTANCE_V1", "exe": "Dino2T.exe", "checks": ["one"]}


class TerminalAcceptanceTests(unittest.TestCase):
    def test_success_writes_pass_only_after_probes(self):
        process = FakeProcess(0)
        calls = []

        def probe(image):
            calls.append(("probe", image))
            self.assertFalse((Path(self.work) / "acceptance.json").exists())
            return []

        def shutdown():
            calls.append(("shutdown", None))
            self.assertFalse((Path(self.work) / "acceptance.json").exists())
            return True

        self.work = tempfile.mkdtemp()
        record = finalize_acceptance(self.work, PAYLOAD, process=process,
                                     worker_probe=probe, shutdown_check=shutdown)
        self.assertEqual(record["result"], "PASS")
        self.assertTrue((Path(self.work) / "acceptance.json").is_file())
        self.assertEqual(process.calls[0][0], "wait")
        self.assertEqual([name for name, _ in calls], ["shutdown", "probe"])
        self.assertEqual(record["terminal_verification"]["worker_check"], "CLEAN")

    def test_nonzero_exit_never_writes_pass(self):
        process = FakeProcess(2)
        self.work = tempfile.mkdtemp()
        record = finalize_acceptance(self.work, PAYLOAD, process=process,
                                     worker_probe=lambda image: [])
        self.assertEqual(record["result"], "FAIL")
        self.assertFalse((Path(self.work) / "acceptance.json").exists())
        self.assertTrue((Path(self.work) / "acceptance-failure.json").is_file())

    def test_timeout_terminates_and_never_writes_pass(self):
        process = FakeProcess(timeout=True)
        self.work = tempfile.mkdtemp()
        record = finalize_acceptance(self.work, PAYLOAD, process=process,
                                     timeout=1.0, worker_probe=lambda image: [])
        self.assertEqual(record["result"], "TIMEOUT")
        self.assertTrue(process.terminated)
        self.assertFalse((Path(self.work) / "acceptance.json").exists())
        self.assertTrue((Path(self.work) / "acceptance-incomplete.json").is_file())

    def test_incomplete_closure_never_writes_pass(self):
        process = FakeProcess(0)
        self.work = tempfile.mkdtemp()
        record = finalize_acceptance(self.work, PAYLOAD, process=process,
                                     worker_probe=lambda image: [],
                                     shutdown_check=lambda: False)
        self.assertEqual(record["result"], "INCOMPLETE")
        self.assertFalse((Path(self.work) / "acceptance.json").exists())
        self.assertTrue((Path(self.work) / "acceptance-incomplete.json").is_file())

    def test_orphan_worker_never_writes_pass(self):
        process = FakeProcess(0)
        self.work = tempfile.mkdtemp()
        record = finalize_acceptance(self.work, PAYLOAD, process=process,
                                     worker_probe=lambda image: ["MotorSimWorker.exe"])
        self.assertEqual(record["result"], "FAIL")
        self.assertFalse((Path(self.work) / "acceptance.json").exists())
        self.assertTrue((Path(self.work) / "acceptance-failure.json").is_file())

    def test_unverifiable_worker_table_never_writes_pass(self):
        process = FakeProcess(0)
        self.work = tempfile.mkdtemp()
        record = finalize_acceptance(
            self.work, PAYLOAD, process=process,
            worker_probe=lambda image: ["TASKLIST_UNAVAILABLE: test"])
        self.assertEqual(record["result"], "FAIL")
        self.assertFalse((Path(self.work) / "acceptance.json").exists())

    def test_previous_pass_is_invalidated_by_a_non_pass_run(self):
        process = FakeProcess(1)
        self.work = tempfile.mkdtemp()
        old = Path(self.work) / "acceptance.json"
        old.write_text('{"result":"PASS"}', encoding="utf-8")
        record = finalize_acceptance(self.work, PAYLOAD, process=process,
                                     worker_probe=lambda image: [])
        self.assertEqual(record["result"], "FAIL")
        self.assertFalse(old.exists())
        self.assertTrue(list(Path(self.work).glob("acceptance-superseded-*.json")))

    def test_worker_probe_rejects_tasklist_error_and_empty_output(self):
        with patch("motorsim.desktop.acceptance_terminal.sys.platform", "win32"):
            with patch("motorsim.desktop.acceptance_terminal.subprocess.run",
                       return_value=SimpleNamespace(returncode=1, stdout="", stderr="boom")):
                self.assertTrue(default_worker_probe("MotorSimWorker.exe"))
            with patch("motorsim.desktop.acceptance_terminal.subprocess.run",
                       return_value=SimpleNamespace(returncode=0, stdout="", stderr="")):
                self.assertTrue(default_worker_probe("MotorSimWorker.exe"))

    def test_windows_scripts_use_the_terminal_helper(self):
        root = Path(__file__).resolve().parents[1]
        for name in ("verify_dino4t_ab_windows.py",
                     "verify_dino_2t_4t_route_windows.py"):
            source = (root / "tests" / name).read_text(encoding="utf-8")
            self.assertIn("finalize_acceptance", source)
            self.assertNotIn('(work/"acceptance.json").write_text', source)


if __name__ == "__main__":
    unittest.main()
