"""Manual, opt-in update manifest validation; no network or auto-update."""
from __future__ import annotations

import json
import re
from pathlib import Path

SCHEMA = "DINO_UPDATE_MANIFEST_V1"
CHANNELS = {"engineering", "trial", "release"}
REQUIRED = {"schema", "version", "source_commit", "channel", "zip_sha256",
            "dino2t_exe_sha256", "worker_exe_sha256", "released_at"}
_SHA = re.compile(r"^[0-9a-f]{64}$")
_VERSION = re.compile(r"^(\d+)\.(\d+)\.(\d+)(?:-rc(\d+))?$")


def parse_version(value: str) -> tuple:
    match = _VERSION.match(str(value).strip())
    if not match:
        raise ValueError("versión no reconocida")
    major, minor, patch, rc = match.groups()
    return (int(major), int(minor), int(patch), int(rc) if rc else 10**9)


def _sha(value, key):
    if not isinstance(value, str) or not _SHA.match(value):
        raise ValueError(f"hash inválido: {key}")
    return value


def validate_manifest(data: dict) -> dict:
    if not isinstance(data, dict) or data.get("schema") != SCHEMA:
        raise ValueError("manifest de actualización no reconocido")
    missing = REQUIRED - set(data)
    if missing:
        raise ValueError("faltan campos: " + ", ".join(sorted(missing)))
    if data.get("channel") not in CHANNELS:
        raise ValueError("canal de actualización no admitido")
    parse_version(data.get("version"))
    if not isinstance(data.get("source_commit"), str) or not data["source_commit"].strip():
        raise ValueError("commit fuente inválido")
    if not isinstance(data.get("released_at"), str) or not data["released_at"].strip():
        raise ValueError("fecha de release inválida")
    for key in ("zip_sha256", "dino2t_exe_sha256", "worker_exe_sha256"):
        _sha(data.get(key), key)
    return dict(data)


def load_manifest(path) -> dict:
    return validate_manifest(json.loads(Path(path).read_text(encoding="utf-8")))


def check_update(manifest: dict, *, current_version: str, current_commit: str) -> dict:
    """Compare a validated manifest with the running build; no network side effects."""
    validate_manifest(manifest)
    current_tuple = parse_version(current_version)
    candidate_tuple = parse_version(manifest["version"])
    commit = str(current_commit or "").lower()
    candidate_commit = str(manifest["source_commit"]).lower()
    if candidate_commit == commit:
        status = "UP_TO_DATE"
    elif candidate_tuple > current_tuple:
        status = "UPDATE_AVAILABLE"
    elif candidate_tuple < current_tuple:
        status = "OLDER_CANDIDATE"
    else:
        status = "DIFFERENT_BUILD"
    return {"status": status, "current_version": current_version,
            "candidate_version": manifest["version"],
            "current_commit": current_commit,
            "candidate_commit": manifest["source_commit"],
            "channel": manifest["channel"],
            "zip_sha256": manifest["zip_sha256"]}
