import json
from pathlib import Path

import pytest

from scripts.diagnostics.run_candidate_periodic_gci_v1 import validate_source


def test_refuses_missing_e2b_artifact_root(tmp_path):
    (tmp_path / "results/e2b-periodic-ab-v1").mkdir(parents=True)
    with pytest.raises(FileNotFoundError):
        validate_source(tmp_path, tmp_path / "artifacts")


def test_window_levels_are_explicit():
    source = Path("scripts/diagnostics/run_candidate_periodic_gci_v1.py").read_text(encoding="utf-8")
    assert "if level not in (1, 2)" in source
    assert "first_absolute=31, last_absolute=36" in source
    assert "solver_budget=260, admission_budget=290" in source


def test_preflight_is_zero_step_and_execution_limited_to_level_one():
    source = Path("scripts/diagnostics/run_candidate_periodic_gci_v1.py").read_text(encoding="utf-8")
    assert '"solver_steps_executed": 0' in source
    assert '"campaign_execution_authorized_by_protocol": level == 1' in source
