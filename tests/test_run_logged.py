from __future__ import annotations

import sys
import os
import subprocess
from pathlib import Path

from scripts.agents.run_logged import run

ROOT = Path(__file__).resolve().parents[1]


def test_run_logged_child_unicode_is_safe_under_legacy_windows_codepage(tmp_path, monkeypatch):
    monkeypatch.setenv("PYTHONIOENCODING", "cp1252")
    summary = run(
        "unicode-child",
        tmp_path,
        [sys.executable, "-c", "print('integral ∫ and delta Δ')"],
        timeout=10,
        campaign_summary=None,
    )

    assert summary["exit_code"] == 0
    assert not summary["timed_out"]
    assert "integral ∫ and delta Δ" in (tmp_path / "unicode-child.log").read_text(encoding="utf-8")


def test_run_logged_cli_summary_is_safe_under_cp1252(tmp_path):
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "cp1252"
    completed = subprocess.run(
        [sys.executable, str(ROOT / "scripts/agents/run_logged.py"),
         "--name", "unicode-cli", "--out", str(tmp_path), "--",
         sys.executable, "-c", "print('integral ∫ and delta Δ')"],
        cwd=ROOT,
        env=env,
        text=True,
        encoding="cp1252",
        errors="replace",
        capture_output=True,
        timeout=10,
    )

    assert completed.returncode == 0
    assert "exit_code" in completed.stdout
    assert "integral ∫ and delta Δ" in (tmp_path / "unicode-cli.log").read_text(encoding="utf-8")
