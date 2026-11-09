"""Terminal acceptance receipts: PASS only after wait, exit code and resource checks.

This module is maintainer-only.  It is deliberately independent of the GUI and
of the solver so that success, error, timeout and incomplete-close behavior can
be tested with fake process objects.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys


class TerminalAcceptanceError(RuntimeError):
    pass


def default_worker_probe(image: str = "MotorSimWorker.exe"):
    """Return an empty list only when the worker table was actually checked."""
    if sys.platform != "win32":
        return []
    try:
        result = subprocess.run(
            ["tasklist", "/FI", f"IMAGENAME eq {image}", "/FO", "CSV", "/NH"],
            capture_output=True, text=True, timeout=10, check=False)
    except (OSError, subprocess.SubprocessError) as exc:
        return [f"TASKLIST_UNAVAILABLE: {type(exc).__name__}: {exc}"]
    if result.returncode != 0:
        detail = (result.stderr or "").strip()[:200]
        return [f"TASKLIST_FAILED: exit {result.returncode}: {detail}"]
    output = (result.stdout or "").strip()
    if not output:
        return ["TASKLIST_EMPTY_OUTPUT"]
    return [image] if image.lower() in output.lower() else []


def _invalidate_previous_pass(work: Path, acceptance_name: str) -> None:
    target = work / acceptance_name
    if not target.is_file():
        return
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    target.replace(work / f"acceptance-superseded-{stamp}.json")


def _terminate(process, timeout=5):
    try:
        process.terminate()
    except Exception:
        pass
    try:
        process.wait(timeout=timeout)
        return
    except Exception:
        pass
    try:
        process.kill()
    except Exception:
        pass
    try:
        process.wait(timeout=timeout)
    except Exception:
        pass


def _write(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, ensure_ascii=False, indent=2,
                               allow_nan=False) + "\n", encoding="utf-8")


def _record(payload: dict, result: str, *, exit_code, issues: list[str],
            worker_check: str) -> dict:
    record = dict(payload)
    record.update({
        "schema": payload.get("schema", "DINO_TERMINAL_ACCEPTANCE_V1"),
        "result": result,
        "exit_code": exit_code,
        "terminal_verification": {
            "process_wait": True,
            "exit_code_zero": exit_code == 0,
            "worker_check": worker_check,
            "issues": list(issues),
            "verified_at": datetime.now(timezone.utc).isoformat(),
        },
    })
    return record


def finalize_acceptance(work, payload: dict, *, process, timeout: float = 15.0,
                        worker_image: str = "MotorSimWorker.exe",
                        worker_probe=None, shutdown_check=None,
                        acceptance_name: str = "acceptance.json"):
    """Write a terminal receipt only after the process and its resources are closed.

    Returns the written record.  Non-PASS results are written to
    ``acceptance-failure.json`` / ``acceptance-incomplete.json`` so that the
    failed or interrupted evidence is retained without publishing a PASS.
    """
    work = Path(work)
    work.mkdir(parents=True, exist_ok=True)
    _invalidate_previous_pass(work, acceptance_name)
    try:
        exit_code = process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        _terminate(process)
        record = _record(payload, "TIMEOUT", exit_code=None,
                         issues=[f"process did not terminate within {timeout} s"],
                         worker_check="NOT_REACHED")
        _write(work / "acceptance-incomplete.json", record)
        return record
    if exit_code != 0:
        record = _record(payload, "FAIL", exit_code=exit_code,
                         issues=[f"process exit code {exit_code}"],
                         worker_check="NOT_REACHED")
        _write(work / "acceptance-failure.json", record)
        return record
    if shutdown_check is not None:
        try:
            closed = bool(shutdown_check())
        except Exception as exc:
            closed = False
            issue = f"final shutdown check raised {type(exc).__name__}: {exc}"
        else:
            issue = "final shutdown check failed"
        if not closed:
            record = _record(payload, "INCOMPLETE", exit_code=exit_code,
                             issues=[issue], worker_check="NOT_REACHED")
            _write(work / "acceptance-incomplete.json", record)
            return record
    probe = worker_probe or default_worker_probe
    try:
        workers = list(probe(worker_image))
    except Exception as exc:
        workers = [f"WORKER_PROBE_FAILED: {type(exc).__name__}: {exc}"]
    if workers:
        record = _record(payload, "FAIL", exit_code=exit_code,
                         issues=[f"orphan or unverifiable workers: {workers}"],
                         worker_check="FAILED")
        _write(work / "acceptance-failure.json", record)
        return record
    record = _record(payload, "PASS", exit_code=exit_code, issues=[],
                     worker_check="CLEAN")
    _write(work / acceptance_name, record)
    return record
