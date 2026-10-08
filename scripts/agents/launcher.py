"""Minimal external relauncher for autonomous MotorSim sessions.

Loop:
  stop-status (program_status.py)  -> STOP_A/B/C: exit
  else start a fresh agent session with scripts/agents/session_prompt.md,
       full output to <log_dir>/<session>/session.log, compact summary JSON
  measure progress (HEAD, progress_log length, queue states)
  repeat

Stops only on the AGENTS.md §2 conditions A/B/C plus operational safeguards
(max sessions, consecutive sessions without progress, git unavailable,
concurrent launcher lock). The launcher never edits program-status.json: the
agent session is the only writer.

Usage:
  python scripts/agents/launcher.py --config scripts/agents/launcher.example.json
  python scripts/agents/launcher.py --config cfg.json --dry-run
"""

from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import program_status  # noqa: E402
import run_logged  # noqa: E402

DEFAULTS = {
    "agent_command": ["codex", "exec", "{prompt}"],
    "repo": None,
    "status": None,
    "prompt_template": str(HERE / "session_prompt.md"),
    "log_dir": ".agent-sessions",
    "max_sessions": 20,
    "session_timeout_s": 4 * 3600,
    "max_no_progress_sessions": 2,
    "cooldown_s": 30,
    "stale_lock_s": 12 * 3600,
}

EXIT_NO_PROGRESS = 20
EXIT_MAX_SESSIONS = 21
EXIT_LOCKED = 22
EXIT_GIT = program_status.EXIT_STOP_C


def _now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat()


def load_config(path: Path | None) -> dict:
    config = dict(DEFAULTS)
    if path is not None:
        config.update(json.loads(path.read_text(encoding="utf-8")))
    repo = Path(config["repo"]).resolve() if config["repo"] else program_status.ROOT
    config["repo"] = repo
    status = Path(config["status"]) if config["status"] else program_status.DEFAULT_STATUS.relative_to(program_status.ROOT)
    config["status"] = status if status.is_absolute() else repo / status
    log_dir = Path(config["log_dir"])
    config["log_dir"] = log_dir if log_dir.is_absolute() else repo / log_dir
    return config


def git_head(repo: Path) -> str | None:
    result = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True, text=True)
    return result.stdout.strip() if result.returncode == 0 else None


def fingerprint(repo: Path, status: Path) -> dict:
    data = program_status.load(status)
    states = json.dumps([[t.get("id"), t.get("state")] for t in data.get("queue", [])])
    return {
        "head": git_head(repo),
        "progress_entries": len(data.get("progress_log", [])),
        "queue_digest": hashlib.sha256(states.encode()).hexdigest()[:16],
    }


class Lock:
    def __init__(self, path: Path, stale_s: float):
        self.path = path
        self.stale_s = stale_s

    def acquire(self) -> bool:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.exists():
            age = time.time() - self.path.stat().st_mtime
            if age < self.stale_s:
                return False
        self.path.write_text(json.dumps({"created_at": _now()}), encoding="utf-8")
        return True

    def touch(self) -> None:
        self.path.touch()

    def release(self) -> None:
        if self.path.exists():
            self.path.unlink()


def _event(log_dir: Path, **fields) -> None:
    fields = {"at": _now(), **fields}
    with open(log_dir / "launcher.jsonl", "a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(fields, ensure_ascii=False) + "\n")
    print(json.dumps(fields, ensure_ascii=False))


def render_prompt(template: Path, session_index: int, stop: dict) -> str:
    text = template.read_text(encoding="utf-8")
    return text.replace("{session_index}", str(session_index)).replace(
        "{stop_status}", f"{stop['decision']} ({stop['reason']})" + (f" ACTION={stop['action']}" if stop.get("action") else "")
    )


def build_command(template: list[str], prompt: str, prompt_file: Path) -> list[str]:
    return [part.replace("{prompt_file}", str(prompt_file)).replace("{prompt}", prompt) for part in template]


def run_loop(config: dict, dry_run: bool = False) -> int:
    repo, status, log_dir = config["repo"], config["status"], config["log_dir"]
    log_dir.mkdir(parents=True, exist_ok=True)
    lock = Lock(log_dir / "launcher.lock", config["stale_lock_s"])
    if not dry_run and not lock.acquire():
        _event(log_dir, event="LOCKED", reason="another launcher holds the lock")
        return EXIT_LOCKED
    try:
        no_progress = 0
        for index in range(1, int(config["max_sessions"]) + 1):
            if git_head(repo) is None:
                _event(log_dir, event="STOP", decision="STOP_C_HARD_STOP", reason="git unavailable or repo corrupt")
                return EXIT_GIT
            stop = program_status.stop_decision(program_status.load(status))
            if stop["exit"] != program_status.EXIT_CONTINUE:
                _event(log_dir, event="STOP", decision=stop["decision"], reason=stop["reason"], sessions=index - 1)
                return stop["exit"]
            session_dir = log_dir / f"{_dt.datetime.now().strftime('%Y%m%dT%H%M%S')}-s{index:03d}"
            session_dir.mkdir(parents=True, exist_ok=True)
            prompt = render_prompt(Path(config["prompt_template"]), index, stop)
            prompt_file = session_dir / "prompt.md"
            prompt_file.write_text(prompt, encoding="utf-8")
            command = build_command(config["agent_command"], prompt, prompt_file)
            before = fingerprint(repo, status)
            _event(log_dir, event="SESSION_START", session=index, dir=str(session_dir), stop_status=stop, before=before)
            if dry_run:
                _event(log_dir, event="DRY_RUN", command=[c if len(c) < 120 else c[:117] + "..." for c in command])
                return program_status.EXIT_CONTINUE
            lock.touch()
            summary = run_logged.run("session", session_dir, command, float(config["session_timeout_s"]), None)
            after = fingerprint(repo, status)
            progressed = after != before
            no_progress = 0 if progressed else no_progress + 1
            _event(
                log_dir,
                event="SESSION_END",
                session=index,
                exit_code=summary["exit_code"],
                timed_out=summary["timed_out"],
                duration_s=summary["duration_s"],
                progressed=progressed,
                after=after,
                error_lines=summary["error_lines"][-3:],
            )
            if no_progress >= int(config["max_no_progress_sessions"]):
                _event(
                    log_dir,
                    event="STOP",
                    decision="NO_PROGRESS_SAFEGUARD",
                    reason=f"{no_progress} consecutive sessions without commit/progress/queue change; human check required",
                )
                return EXIT_NO_PROGRESS
            time.sleep(float(config["cooldown_s"]))
        _event(log_dir, event="STOP", decision="MAX_SESSIONS", reason=f"{config['max_sessions']} sessions run")
        return EXIT_MAX_SESSIONS
    finally:
        if not dry_run:
            lock.release()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    return run_loop(load_config(args.config), args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
