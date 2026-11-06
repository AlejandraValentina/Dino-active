"""F08/F09 boundary falsifications fixed before provenance remediation."""
from __future__ import annotations

from pathlib import Path
import subprocess
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "packaging"))
import build_provenance as provenance


def _git(root, *args):
    return subprocess.check_output(["git", *args], cwd=root)


def _committed_tree(root):
    required = [
        "motorsim/main.py", "motorsim/kinematics.py", "motorsim/dino4t/runner.py",
        "examples/projects/desktop.json", "configs/dino4t/example_single_cylinder_500cc.json",
        "packaging/MotorSim.spec", "packaging/gui_entry.py",
        "packaging/dino_desktop_entry.py", "packaging/worker_entry.py",
        "packaging/requirements-build.txt", "packaging/AVISOS.txt",
        "packaging/INICIO-DINO.txt", "packaging/build_windows.py",
        "packaging/build_provenance.py", "packaging/licenses/license.txt",
        "scripts/agents/storage_preflight.py",
        "results/2t-commercial-core-20261002/fixtures/v1-prime-mesh/fixture_a_prime-mesh-0.json",
    ]
    for rel in required:
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(rel + "\n", encoding="utf-8")
    _git(root, "init", "-q")
    _git(root, "add", ".")
    _git(root, "-c", "user.name=Provenance test", "-c", "user.email=test@example.invalid",
         "commit", "-qm", "initial source")


def test_native_four_stroke_example_is_manifest_bound():
    root = Path(__file__).resolve().parents[1]
    paths = {item["path"] for item in provenance.input_manifest(root)["files"]}
    assert "configs/dino4t/example_single_cylinder_500cc.json" in paths


def test_dirty_consumed_four_stroke_example_fails_clean_guard(tmp_path):
    _committed_tree(tmp_path)
    (tmp_path / "configs/dino4t/example_single_cylinder_500cc.json").write_text(
        "uncommitted consumed geometry\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="example_single_cylinder_500cc"):
        provenance.ensure_packaged_inputs_clean(tmp_path)


def test_four_stroke_runner_cannot_call_modified_shared_dependency_clean(monkeypatch, tmp_path):
    from motorsim.dino4t import runner
    _committed_tree(tmp_path)
    monkeypatch.setattr(runner, "__file__", str(tmp_path / "motorsim/dino4t/runner.py"))
    monkeypatch.setattr(runner, "_packaged_build_metadata", lambda: None)
    (tmp_path / "motorsim/kinematics.py").write_text("modified shared numerical dependency\n", encoding="utf-8")
    assert runner._git_dirty() is True
