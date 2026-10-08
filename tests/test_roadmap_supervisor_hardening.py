import json
import os
import subprocess
import sys
import time
from pathlib import Path

import dev_orchestrator.roadmap_supervisor as supervisor


def test_real_windows_self_pid_detection():
    if os.name != "nt":
        return
    assert supervisor.pid_alive(os.getpid()) is True


def test_pid_alive_parses_tasklist_csv(monkeypatch):
    class Result:
        returncode = 0
        stdout = '"python.exe","4242","Console","1","12,345 K"\n'

    monkeypatch.setattr(supervisor.os, "name", "nt")
    monkeypatch.setattr(supervisor.subprocess, "run", lambda *a, **k: Result())
    assert supervisor.pid_alive(4242) is True
    assert supervisor.pid_alive(4243) is False


def test_extension_codex_resolution_without_path(monkeypatch, tmp_path):
    extension = tmp_path / ".vscode" / "extensions" / "openai.chatgpt-1.2.3-win32-x64" / "bin" / "windows-x86_64"
    extension.mkdir(parents=True)
    executable = extension / "codex.exe"
    executable.write_bytes(b"fake")
    monkeypatch.setattr(supervisor.os, "name", "nt")
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    monkeypatch.setattr(supervisor.shutil, "which", lambda _: None)
    assert supervisor.resolve_agent_command(["codex", "exec", "-"])[0] == str(executable)


def test_stale_stop_is_cleared_only_after_lock(monkeypatch, tmp_path):
    monkeypatch.setattr(supervisor, "R", tmp_path)
    monkeypatch.setattr(supervisor, "LOCK", tmp_path / "supervisor.lock")
    monkeypatch.setattr(supervisor, "STOP_REQUEST", tmp_path / "supervisor.stop")
    supervisor.STOP_REQUEST.write_text("stale", encoding="utf-8")
    assert supervisor.acquire() is True
    try:
        supervisor._clear_stale_stop_after_acquire()
        assert not supervisor.STOP_REQUEST.exists()
    finally:
        supervisor.release()


def test_no_progress_blocks_on_nth_attempt():
    before = {"HEAD": "x", "active_task": "T", "done": 0, "phase": "P", "blockers": [], "worktree": []}
    assert supervisor._progressed(before, dict(before)) is False


def test_terminal_detection_for_done_queue(monkeypatch, tmp_path):
    monkeypatch.setattr(supervisor, "R", tmp_path)
    (tmp_path / "state.json").write_text(json.dumps({"current_phase": "TEST"}), encoding="utf-8")
    (tmp_path / "current_tasks.json").write_text(json.dumps({"tasks": [{"id": "T", "status": "DONE"}]}), encoding="utf-8")
    assert supervisor._terminal_reason() == "ROADMAP_NO_ACTIVE_TASKS"


def test_terminate_helper_waits_for_exact_child(monkeypatch):
    calls = []

    class Child:
        pid = 4321
        returncode = None
        def poll(self): return self.returncode
        def wait(self, timeout=None):
            calls.append(("wait", timeout))
            self.returncode = 1
            return self.returncode

    monkeypatch.setattr(supervisor.os, "name", "nt")
    monkeypatch.setattr(supervisor.subprocess, "run", lambda argv, **kwargs: calls.append(argv))
    assert supervisor.terminate_process_tree(Child()) == 1
    assert calls[0] == ["taskkill", "/PID", "4321", "/T", "/F"]


def test_start_refuses_live_owner(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(supervisor, "R", tmp_path)
    monkeypatch.setattr(supervisor, "LOCK", tmp_path / "supervisor.lock")
    supervisor.LOCK.write_text(json.dumps({"pid": 777}), encoding="utf-8")
    monkeypatch.setattr(supervisor, "pid_alive", lambda pid: pid == 777)
    assert supervisor.main(["roadmap_supervisor.py", "start"]) == 1
    assert "ALREADY_RUNNING" in capsys.readouterr().out


def test_real_detached_fake_autonomy_proof(tmp_path):
    """Exercise the detached lifecycle without reading or changing MotorSim state."""
    root = tmp_path / "isolated"
    results = root / "results" / "roadmap-executor"
    results.mkdir(parents=True)
    (results / "state.json").write_text(json.dumps({"current_phase": "TEST", "current_subphase": "A"}), encoding="utf-8")
    (results / "current_tasks.json").write_text(json.dumps({
        "phase": "TEST", "active_task": "A",
        "tasks": [{"id": "A", "phase": "TEST", "status": "TODO"},
                  {"id": "B", "phase": "TEST", "status": "TODO"}]
    }), encoding="utf-8")
    fake_code = (
        "import json, pathlib, sys, time; "
        "p=pathlib.Path('results/roadmap-executor'); c=p/'calls'; "
        "n=int(c.read_text())+1 if c.exists() else 1; c.write_text(str(n)); "
        "print('FAKE_INVOCATION_'+str(n), flush=True); "
        "d=json.loads((p/'current_tasks.json').read_text()); "
        "d['tasks'][n-1]['status']='DONE'; d['active_task']='B' if n == 1 else None; "
        "(p/'current_tasks.json').write_text(json.dumps(d)); "
        "s=json.loads((p/'state.json').read_text()); "
        "s['current_subphase']='B' if n == 1 else None; (p/'state.json').write_text(json.dumps(s)); "
            "time.sleep(2.0)"
    )
    config = {
        "agent_command": [sys.executable, "-c", fake_code],
        "agent_timeout_seconds": 20, "max_no_progress_attempts": 3,
        "max_invocations": 0, "poll_seconds": 0.1,
        "live_status_file": str(results / "LIVE_STATUS.md")
    }
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(config), encoding="utf-8")
    env = os.environ.copy()
    env.update({"MOTORSIM_SUPERVISOR_ROOT": str(root),
                "MOTORSIM_SUPERVISOR_RESULTS": str(results),
                "MOTORSIM_SUPERVISOR_CONFIG": str(config_path)})
    script = str(Path(__file__).resolve().parents[1] / "dev_orchestrator" / "roadmap_supervisor.py")
    start = subprocess.run([sys.executable, script, "start"], env=env, cwd=root,
                           capture_output=True, text=True, timeout=15)
    assert start.returncode == 0, start.stdout + start.stderr
    supervisor_pid = int(start.stdout.strip().splitlines()[0])
    try:
        deadline = time.time() + 10
        first = None
        while time.time() < deadline:
            candidate = supervisor.read(results / "supervisor_state.json", {})
            if candidate.get("child_pid") and supervisor.pid_alive(candidate["child_pid"]):
                first = candidate
                break
            time.sleep(0.1)
        assert first is not None
        first_status = (results / "LIVE_STATUS.md").read_text()
        status_deadline = time.time() + 2
        while time.time() < status_deadline and (results / "LIVE_STATUS.md").read_text() == first_status:
            time.sleep(0.1)
        assert (results / "LIVE_STATUS.md").read_text() != first_status
        second = None
        while time.time() < deadline:
            state = supervisor.read(results / "supervisor_state.json", {})
            if (results / "calls").exists() and (results / "calls").read_text() == "2" and state.get("child_pid"):
                second = state
                break
            time.sleep(0.1)
        assert second is not None
        assert supervisor.pid_alive(supervisor_pid)
        assert "Child PID" in first_status and "alive" in first_status
        stop = subprocess.run([sys.executable, script, "stop"], env=env, cwd=root,
                              capture_output=True, text=True, timeout=10)
        assert stop.returncode == 0
        deadline = time.time() + 10
        while time.time() < deadline and supervisor.pid_alive(supervisor_pid):
            time.sleep(0.1)
        assert not supervisor.pid_alive(supervisor_pid)
        assert not (results / "supervisor.lock").exists()
        assert (results / "calls").read_text() == "2"
        evidence = {"pass": True, "detached": True, "invocations": ["A", "B"],
                    "same_supervisor_pid": supervisor_pid, "clean_stop": True,
                    "lock_removed": True, "live_status_updated_while_child_running": True,
                    "first_status": first_status, "fake_call_count": 2}
        proof = results / "fake-autonomy-proof.json"
        proof.write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    finally:
        if supervisor.pid_alive(supervisor_pid):
            subprocess.run([sys.executable, script, "stop"], env=env, cwd=root, timeout=10)
