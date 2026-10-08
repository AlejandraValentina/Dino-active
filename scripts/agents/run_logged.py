"""Run a long command with full output to disk and a compact JSON summary.

Usage:
  python scripts/agents/run_logged.py --name NAME --out DIR [--timeout S]
      [--campaign-summary PATH] -- <command> [args...]

Writes DIR/NAME.log (stdout+stderr) and DIR/NAME.summary.json, and prints only
the summary. The agent reads the summary first and opens the log only to
diagnose (AGENTS.md §7). Exit code mirrors the command (124 on timeout).
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import re
import subprocess
import sys
import threading
import time
from collections import deque
from pathlib import Path

TAIL_LINES = 30
MAX_ERROR_LINES = 20
MAX_LINE = 300
ERROR_PATTERN = re.compile(r"Traceback|Error\b|FAILED|\bFAIL\b|Exception|AssertionError|ERROR")


def _now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat()


def run(name: str, out: Path, command: list[str], timeout: float | None, campaign_summary: Path | None) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    log_path = out / f"{name}.log"
    summary_path = out / f"{name}.summary.json"
    tail: deque[str] = deque(maxlen=TAIL_LINES)
    errors: deque[str] = deque(maxlen=MAX_ERROR_LINES)
    started = _now()
    start = time.monotonic()
    timed_out = False
    counter = [0]
    with open(log_path, "w", encoding="utf-8", newline="\n") as log:
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        assert process.stdout is not None

        def _pump() -> None:
            for line in process.stdout:
                log.write(line)
                counter[0] += 1
                short = line.rstrip("\n")[:MAX_LINE]
                tail.append(short)
                if ERROR_PATTERN.search(line):
                    errors.append(f"{counter[0]}: {short}")

        reader = threading.Thread(target=_pump, daemon=True)
        reader.start()
        try:
            process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            process.kill()
            process.wait()
        reader.join(timeout=10)
    line_count = counter[0]
    duration = time.monotonic() - start
    exit_code = 124 if timed_out else process.returncode
    summary: dict = {
        "name": name,
        "command": command,
        "started_at": started,
        "finished_at": _now(),
        "duration_s": round(duration, 3),
        "exit_code": exit_code,
        "timed_out": timed_out,
        "log_path": str(log_path),
        "log_lines": line_count,
        "log_bytes": log_path.stat().st_size,
        "error_lines": list(errors),
        "tail": list(tail),
    }
    if campaign_summary is not None:
        if campaign_summary.exists():
            try:
                summary["campaign_summary"] = json.loads(campaign_summary.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                summary["campaign_summary_error"] = f"invalid JSON: {exc}"
        else:
            summary["campaign_summary_error"] = f"missing: {campaign_summary}"
    with open(summary_path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(summary, indent=2, ensure_ascii=False) + "\n")
    summary["summary_path"] = str(summary_path)
    return summary


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--" not in argv:
        print("usage: run_logged.py --name N --out DIR [--timeout S] [--campaign-summary P] -- command ...")
        return 2
    split = argv.index("--")
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--timeout", type=float)
    parser.add_argument("--campaign-summary", type=Path)
    args = parser.parse_args(argv[:split])
    command = argv[split + 1:]
    if not command:
        print("ERROR empty command")
        return 2
    summary = run(args.name, args.out, command, args.timeout, args.campaign_summary)
    compact = {k: summary[k] for k in ("name", "exit_code", "timed_out", "duration_s", "log_lines", "summary_path")}
    compact["error_lines"] = summary["error_lines"][-5:]
    compact["tail"] = summary["tail"][-8:]
    print(json.dumps(compact, indent=2, ensure_ascii=False))
    return summary["exit_code"]


if __name__ == "__main__":
    sys.exit(main())
