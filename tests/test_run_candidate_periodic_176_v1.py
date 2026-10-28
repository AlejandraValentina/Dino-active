import pytest

from scripts.diagnostics.run_candidate_periodic_176_v1 import preflight


def test_176_preflight_is_bounded_and_zero_step(tmp_path):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    # Source binding is the first fail-closed operation and must stop before
    # creating the campaign target if source artifacts are absent.
    with pytest.raises((FileNotFoundError, ValueError, KeyError)):
        preflight(repo_root, tmp_path / "artifacts", repo_root / "protocol.md")


def test_protocol_fixes_first_window_and_does_not_claim_gci():
    from pathlib import Path

    text = Path("openspec/changes/predictive-reliability-v1/candidate-periodic-gci-176-first-window-addendum-v1.md").read_text(encoding="utf-8")
    assert "cycles 31–38" in text
    assert "1080 s" in text
    assert "No GCI is calculated until all three grids are independently periodic" in text
