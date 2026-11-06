from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "packaging"))
import build_provenance as provenance
from bundle_inputs import REQUIRED_BUILD_FILES
from motorsim.source_provenance import REQUIRED_SOURCE_FILES


def _minimal_tree(root: Path):
    required = [
        "motorsim/main.py", "examples/projects/desktop.json",
        "packaging/MotorSim.spec", "packaging/gui_entry.py",
        "packaging/dino_desktop_entry.py", "packaging/worker_entry.py",
        "packaging/requirements-build.txt", "packaging/AVISOS.txt",
        "packaging/INICIO-DINO.txt", "packaging/build_windows.py",
        "packaging/build_provenance.py", "packaging/licenses/license.txt",
        "scripts/agents/storage_preflight.py",
        "results/2t-commercial-core-20261002/fixtures/v1-prime-mesh/fixture_a_prime-mesh-0.json",
    ]
    required += [*REQUIRED_BUILD_FILES, *REQUIRED_SOURCE_FILES,
                 "motorsim/theme.qss", "motorsim/ayuda.txt"]
    for relative in set(required):
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(relative, encoding="utf-8")


def test_packaged_input_manifest_is_relative_complete_and_content_sensitive(tmp_path):
    _minimal_tree(tmp_path)
    before = provenance.input_manifest(tmp_path)
    assert "motorsim/main.py" in {entry["path"] for entry in before["files"]}
    assert all(not Path(entry["path"]).is_absolute() for entry in before["files"])
    (tmp_path / "motorsim/main.py").write_text("changed source", encoding="utf-8")
    after = provenance.input_manifest(tmp_path)
    assert before["sha256"] != after["sha256"]


def test_missing_packaged_input_is_rejected(tmp_path):
    _minimal_tree(tmp_path)
    (tmp_path / "packaging/MotorSim.spec").unlink()
    with pytest.raises(FileNotFoundError, match="MotorSim.spec"):
        provenance.input_manifest(tmp_path)


def test_build_rejects_dirty_app_inputs_but_records_unrelated_changes(monkeypatch, tmp_path):
    statuses = iter([b" M motorsim/main.py\0"])
    monkeypatch.setattr(provenance, "git_status", lambda root, paths=None: next(statuses))
    with pytest.raises(RuntimeError, match="motorsim/main.py"):
        provenance.ensure_packaged_inputs_clean(tmp_path)

    responses = iter([b" M notes/local.txt\0", b""])
    monkeypatch.setattr(provenance, "git_status", lambda root, paths=None: next(responses))
    result = provenance.unrelated_dirty_fingerprint(tmp_path)
    assert result["source_dirty"] is True
    assert result["unrelated_dirty_entry_count"] == 1
    assert len(result["unrelated_dirty_status_sha256"]) == 64
