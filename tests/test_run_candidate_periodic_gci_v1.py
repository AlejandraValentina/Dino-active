import json
from pathlib import Path

import pytest

from scripts.diagnostics.run_candidate_periodic_gci_v1 import continuation_trend, validate_source


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


def test_continuation_requires_declining_maximum_and_p90_for_last_three_cycles():
    cycles = [{"statistics": {"maximum": 4.3, "p90": 1.62}},
              {"statistics": {"maximum": 3.03, "p90": 0.89}},
              {"statistics": {"maximum": 2.69, "p90": 0.53}}]
    assert len(continuation_trend(cycles)) == 3
    cycles[-1]["statistics"]["p90"] = 1.0
    try:
        continuation_trend(cycles)
    except ValueError as exc:
        assert "strictly improve" in str(exc)
    else:
        raise AssertionError("non-improving trend admitted")
