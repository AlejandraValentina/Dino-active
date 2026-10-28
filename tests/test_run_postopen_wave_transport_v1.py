import pytest
import hashlib
import json

from scripts.diagnostics.run_postopen_wave_transport_v1 import (
    CASE_CAP_S,
    CASES,
    MARGIN,
    _replay_source,
    admission_estimates,
    source_validation,
)
from motorsim.integrated_2t import _solver_dependency_hashes
from scripts.diagnostics import run_postopen_wave_transport_v1 as postopen_runner


def test_admission_estimates_apply_margin_and_per_case_cap():
    prep = {"cases": [
        {"name": "p0-88", "projected_replay_plus_extension_s": 48.0},
        {"name": "p0-176-timehalf", "projected_replay_plus_extension_s": 154.0},
    ]}

    rows = admission_estimates(prep)

    assert rows[0]["with_margin_s"] == pytest.approx(48 * MARGIN)
    assert rows[0]["admitted_by_per_case_cap"] is True
    assert rows[1]["with_margin_s"] == pytest.approx(154 * MARGIN)
    assert rows[1]["admitted_by_per_case_cap"] is True
    assert CASE_CAP_S == 210.0
    assert admission_estimates(prep, factor=1.1)[1]["admitted_by_per_case_cap"] is False


class FakeEngine:
    def __init__(self):
        self.crank_angle_unwrapped_deg = 13680.0

    def step(self, dt, delta, capture_trace=False):
        if delta < 1.0:
            raise ValueError("registered rejected trial")
        start = self.crank_angle_unwrapped_deg
        self.crank_angle_unwrapped_deg += delta
        return {"dt_s": dt, "angle_start_deg": start,
                "angle_end_deg": self.crank_angle_unwrapped_deg}

    def fast_recipe_terminal_state(self):
        return {"angle": self.crank_angle_unwrapped_deg}


def test_exact_source_replay_checks_step_and_fast_terminal():
    engine = FakeEngine()
    case = {
        "recipe": [{"dt_s": .01, "angle_start_deg": 13680.0,
                    "angle_end_deg": 13740.0, "rejected_proposals": []}],
        "terminal-state": {"angle": 13740.0},
    }

    replay = _replay_source(engine, case, deadline=10**20)

    assert replay["accepted_source_steps_replayed"] == 1
    assert replay["fast_terminal_exact"] is True
    assert replay["terminal_angle_deg"] == 13740.0


def test_replay_fails_closed_if_recorded_fast_terminal_differs():
    engine = FakeEngine()
    case = {
        "recipe": [{"dt_s": .01, "angle_start_deg": 13680.0,
                    "angle_end_deg": 13740.0, "rejected_proposals": []}],
        "terminal-state": {"angle": 13739.0},
    }

    with pytest.raises(ValueError, match="FAST terminal differs"):
        _replay_source(engine, case, deadline=10**20)


def test_replay_checks_recorded_rejected_proposals():
    engine = FakeEngine()
    case = {
        "recipe": [{"dt_s": .01, "angle_start_deg": 13680.0,
                    "angle_end_deg": 13740.0,
                    "rejected_proposals": [{"step_deg": .5, "error": "registered rejected trial"}]}],
        "terminal-state": {"angle": 13740.0},
    }

    replay = _replay_source(engine, case, deadline=10**20)

    assert replay["rejected_source_proposals_replayed"] == 1


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_source_validation_checks_archived_runner_hashes(tmp_path, monkeypatch):
    source = tmp_path / "source"
    (source / "run").mkdir(parents=True)
    (source / "source.txt").write_text("input", encoding="utf-8")
    (source / "source_runner.py").write_text("runner", encoding="utf-8")
    receipt = {"status": "COMPLETE", "solver_dependency_sha256": _solver_dependency_hashes(),
               "cases": [{"name": name, "status": "COMPLETE"} for name in CASES]}
    (source / "run" / "receipt.json").write_text(json.dumps(receipt), encoding="utf-8")
    input_manifest = {"files": {"source.txt": _sha(source / "source.txt")}}
    (source / "input-manifest.json").write_text(json.dumps(input_manifest), encoding="utf-8")
    manifest = {
        "schema": "PREOPEN_WAVE_TRANSPORT_FINAL_MANIFEST_V1",
        "status": "COMPLETE_BOUNDED_DIAGNOSTIC",
        "files": {"run/receipt.json": _sha(source / "run" / "receipt.json"),
                  "input-manifest.json": _sha(source / "input-manifest.json"),
                  "source.txt": _sha(source / "source.txt")},
        "source_files": {"source_runner.py": _sha(source / "source_runner.py")},
    }
    (source / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    monkeypatch.setattr(postopen_runner, "ROOT", source)

    checked = postopen_runner.source_validation(source)
    assert checked["source_files_sha256"] == manifest["source_files"]

    (source / "source_runner.py").write_text("changed runner", encoding="utf-8")
    with pytest.raises(ValueError, match="runner source changed"):
        postopen_runner.source_validation(source)
