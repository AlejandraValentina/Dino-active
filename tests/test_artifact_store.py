import hashlib
import json
from pathlib import Path

import pytest

from motorsim.artifact_store import ArtifactStoreError, resolve_external_artifact


def _fixture(tmp_path: Path, payload: bytes = b"small test artifact"):
    root = tmp_path / "store"
    relative = "example/primary.bin"
    artifact = root / relative
    artifact.parent.mkdir(parents=True)
    artifact.write_bytes(payload)
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({
        "artifacts": [{
            "artifact_id": "TEST_PRIMARY",
            "expected_external_relative_path": relative,
            "byte_size": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest(),
        }]
    }), encoding="utf-8")
    return root, manifest, artifact


def test_resolves_relative_path_and_verifies_registered_identity(tmp_path, monkeypatch):
    root, manifest, artifact = _fixture(tmp_path)
    monkeypatch.setenv("DINO_ARTIFACT_ROOT", str(root))
    resolved = resolve_external_artifact("TEST_PRIMARY", manifest_path=manifest)
    assert resolved == artifact.resolve()


def test_missing_artifact_has_actionable_error(tmp_path):
    root, manifest, artifact = _fixture(tmp_path)
    artifact.unlink()
    with pytest.raises(ArtifactStoreError, match="REQUIRED_EXTERNAL_ARTIFACT_NOT_AVAILABLE") as exc:
        resolve_external_artifact("TEST_PRIMARY", manifest_path=manifest, root=root)
    assert "TEST_PRIMARY" in str(exc.value)
    assert "example/primary.bin" in str(exc.value)
    assert hashlib.sha256(b"small test artifact").hexdigest() in str(exc.value)


def test_integrity_mismatch_stops_resolution(tmp_path):
    root, manifest, artifact = _fixture(tmp_path)
    artifact.write_bytes(b"changed")
    with pytest.raises(ArtifactStoreError, match="ARTIFACT_INTEGRITY_FAILURE"):
        resolve_external_artifact("TEST_PRIMARY", manifest_path=manifest, root=root)


def test_missing_root_has_actionable_error(tmp_path, monkeypatch):
    _, manifest, _ = _fixture(tmp_path)
    monkeypatch.delenv("DINO_ARTIFACT_ROOT", raising=False)
    with pytest.raises(ArtifactStoreError, match="REQUIRED_EXTERNAL_ARTIFACT_NOT_AVAILABLE"):
        resolve_external_artifact("TEST_PRIMARY", manifest_path=manifest)


def test_production_code_has_no_local_store_or_historical_path_hardcodes():
    root = Path(__file__).resolve().parents[1]
    production_files = [root / "motorsim" / "artifact_store.py",
                        root / "scripts" / "engine_physics_v1_r2_offline_replay.py"]
    forbidden = (b"E:\\dino\\Dino", b"E:/dino/Dino", b"U:\\", b"U:/")
    for path in production_files:
        source = path.read_bytes()
        assert all(value.lower() not in source.lower() for value in forbidden), path
