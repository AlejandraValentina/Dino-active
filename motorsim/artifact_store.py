"""Resolve and verify artifacts stored outside the source repository."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path, PurePosixPath
from typing import Any


DEFAULT_MANIFEST = (
    Path(__file__).resolve().parents[1] / "artifacts" / "engine-physics-v1-r2.json"
)


class ArtifactStoreError(RuntimeError):
    """A required external artifact is missing or fails its identity check."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _entry(artifact_id: str, manifest_path: Path) -> dict[str, Any]:
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ArtifactStoreError(f"ARTIFACT_MANIFEST_UNAVAILABLE: {manifest_path}: {exc}") from exc
    for item in manifest.get("artifacts", []):
        if item.get("artifact_id") == artifact_id:
            return item
    raise ArtifactStoreError(f"ARTIFACT_ID_NOT_REGISTERED: artifact_id={artifact_id}")


def resolve_external_artifact(
    artifact_id: str,
    *,
    manifest_path: Path = DEFAULT_MANIFEST,
    root: str | os.PathLike[str] | None = None,
) -> Path:
    """Return an artifact path only after checking its registered size and SHA-256.

    ``root`` is injectable for tests. Normal callers use ``DINO_ARTIFACT_ROOT``.
    Manifest paths are POSIX relative paths and may not escape the artifact root.
    """
    item = _entry(artifact_id, Path(manifest_path))
    relative = item.get("expected_external_relative_path")
    expected_hash = item.get("sha256")
    expected_size = item.get("byte_size")
    if not isinstance(relative, str) or not isinstance(expected_hash, str) or not isinstance(expected_size, int):
        raise ArtifactStoreError(f"INVALID_ARTIFACT_MANIFEST_ENTRY: artifact_id={artifact_id}")
    rel = PurePosixPath(relative)
    if rel.is_absolute() or ".." in rel.parts or not rel.parts:
        raise ArtifactStoreError(f"INVALID_ARTIFACT_RELATIVE_PATH: artifact_id={artifact_id} path={relative}")

    configured_root = root if root is not None else os.environ.get("DINO_ARTIFACT_ROOT")
    if not configured_root:
        raise ArtifactStoreError(
            "REQUIRED_EXTERNAL_ARTIFACT_NOT_AVAILABLE: "
            f"artifact_id={artifact_id} expected_relative_path={relative} "
            f"expected_sha256={expected_hash}; set DINO_ARTIFACT_ROOT"
        )
    artifact_root = Path(configured_root).expanduser().resolve()
    path = artifact_root.joinpath(*rel.parts).resolve()
    if not path.is_relative_to(artifact_root):
        raise ArtifactStoreError(f"INVALID_ARTIFACT_RELATIVE_PATH: artifact_id={artifact_id} path={relative}")
    if not path.is_file():
        raise ArtifactStoreError(
            "REQUIRED_EXTERNAL_ARTIFACT_NOT_AVAILABLE: "
            f"artifact_id={artifact_id} expected_relative_path={relative} "
            f"expected_sha256={expected_hash} resolved_path={path}"
        )
    actual_size = path.stat().st_size
    actual_hash = _sha256(path)
    if actual_size != expected_size or actual_hash != expected_hash:
        raise ArtifactStoreError(
            "ARTIFACT_INTEGRITY_FAILURE: "
            f"artifact_id={artifact_id} expected_size={expected_size} actual_size={actual_size} "
            f"expected_sha256={expected_hash} actual_sha256={actual_hash}"
        )
    return path


def resolve_historical_artifact(
    historical_relative_path: str,
    *,
    manifest_path: Path,
    root: str | os.PathLike[str] | None = None,
) -> Path:
    """Resolve a registered artifact by its archival source-relative identity."""
    try:
        manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ArtifactStoreError(f"ARTIFACT_MANIFEST_UNAVAILABLE: {manifest_path}: {exc}") from exc
    for item in manifest.get("artifacts", []):
        if item.get("historical_relative_path") == historical_relative_path:
            return resolve_external_artifact(item.get("artifact_id"), manifest_path=Path(manifest_path), root=root)
    raise ArtifactStoreError(
        f"ARTIFACT_SOURCE_NOT_REGISTERED: historical_relative_path={historical_relative_path}"
    )
