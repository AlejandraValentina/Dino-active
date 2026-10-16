import json
from pathlib import Path

import pytest

from scripts.diagnostics.stage1 import run_stage1_periodicity_focal_v1 as runner


@pytest.fixture(scope="module")
def frozen_point():
    return runner._load_configuration()


def test_bound_preflight_passes_without_solver_steps(monkeypatch, tmp_path, frozen_point):
    project, config, effective, preflight = frozen_point
    monkeypatch.setattr(runner, "_load_configuration", lambda: frozen_point)
    monkeypatch.setenv("DINO_ARTIFACT_ROOT", str(tmp_path / "artifacts"))
    result = runner.run(execute=False, preregistration_sha256=None, resume=False)
    assert result["classification"] == "PREFLIGHT_ONLY_NO_SOLVER_STEPS"
    assert result["preflight"]["status"] == "PASS"
    assert result["preflight"]["solver_steps"] == 0
    assert result["configuration_sha256"] == preflight["configuration_sha256"]
    assert result["identity_sha256"] == preflight["identity_sha256"]
    assert not Path(result["artifact_root"]).exists()


def test_repository_artifact_root_fails_closed(monkeypatch):
    monkeypatch.setenv("DINO_ARTIFACT_ROOT", str(runner.ROOT))
    with pytest.raises(RuntimeError, match="inside a Git repository"):
        runner.artifact_root()


def test_preregistered_hash_mismatch_fails_closed_before_solver(monkeypatch, tmp_path, frozen_point):
    monkeypatch.setattr(runner, "_load_configuration", lambda: frozen_point)
    monkeypatch.setenv("DINO_ARTIFACT_ROOT", str(tmp_path / "artifacts"))
    def unexpected(*args, **kwargs):
        raise AssertionError("solver must not be called for a mismatched preregistration")
    monkeypatch.setattr(runner, "run_exploratory", unexpected)
    with pytest.raises(RuntimeError, match="exact preregistration SHA-256"):
        runner.run(execute=True, preregistration_sha256="0" * 64, resume=False)


def test_missing_resume_checkpoint_fails_closed(monkeypatch, tmp_path, frozen_point):
    monkeypatch.setattr(runner, "_load_configuration", lambda: frozen_point)
    monkeypatch.setenv("DINO_ARTIFACT_ROOT", str(tmp_path / "artifacts"))
    protocol_sha = runner._sha(runner.PROTOCOL)
    with pytest.raises(RuntimeError, match="prior report and point checkpoint"):
        runner.run(execute=True, preregistration_sha256=protocol_sha, resume=True)


def test_solver_source_identity_mismatch_fails_closed(frozen_point):
    _, _, effective, preflight = frozen_point
    protocol = json.loads(runner.PROTOCOL.read_text(encoding="utf-8"))
    changed = dict(effective)
    changed["source_hashes"] = dict(effective["source_hashes"])
    changed["source_hashes"]["motorsim.integrated_2t"] = "0" * 64
    with pytest.raises(RuntimeError, match="solver_source_hashes"):
        runner.validate_binding(
            protocol,
            changed,
            preflight,
            runner_sha256=runner._sha(Path(runner.__file__)),
            project_sha256=runner._sha(runner.PROJECT),
        )


def test_invalid_preflight_is_rejected_before_execution(monkeypatch, frozen_point):
    project, config, effective, preflight = frozen_point
    invalid_preflight = dict(preflight, status="FAIL_CLOSED")
    monkeypatch.setattr(runner, "_load_configuration", lambda: (project, config, effective, invalid_preflight))
    with pytest.raises(RuntimeError, match="preflight did not PASS with zero steps"):
        runner.run(execute=False, preregistration_sha256=None, resume=False)
