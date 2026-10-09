"""Lossless segmented representation for IMPL2 diagnostic evidence.

This prototype only changes the on-disk representation of a completed V3
primary. The historical primary builder and its independent replay auditor
remain the authority; readers reconstruct the canonical object before audit.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any


SCHEMA = "FULL_RPM_SWEEP_V1_IMPL2_SEGMENTED_PRIMARY_V1"


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def encode_segmented_primary(primary: dict) -> dict:
    """Transpose trajectory row dictionaries into lossless field columns."""
    if not isinstance(primary, dict) or not isinstance(primary.get("trajectory"), list):
        raise ValueError("segmented primary requires a trajectory list")
    rows = primary["trajectory"]
    if not rows or any(not isinstance(row, dict) for row in rows):
        raise ValueError("segmented primary requires nonempty object rows")
    names = sorted({key for row in rows for key in row})
    columns = {name: [row.get(name) for row in rows] for name in names}
    presence = {name: [name in row for row in rows] for name in names}
    metadata = {key: value for key, value in primary.items() if key != "trajectory"}
    return {
        "schema": SCHEMA,
        "canonical_primary_sha256": canonical_sha256(primary),
        "row_count": len(rows),
        "column_names": names,
        "columns": columns,
        "presence": presence,
        "metadata": metadata,
    }


def decode_segmented_primary(segment: dict) -> dict:
    if not isinstance(segment, dict) or segment.get("schema") != SCHEMA:
        raise ValueError("unsupported segmented primary schema")
    count, names, columns, presence, metadata = (segment.get("row_count"),
                                       segment.get("column_names"),
                                       segment.get("columns"),
                                       segment.get("presence"),
                                       segment.get("metadata"))
    if (type(count) is not int or count <= 0 or not isinstance(names, list) or
            names != sorted(set(names)) or not isinstance(columns, dict) or
            set(columns) != set(names) or not isinstance(presence, dict) or
            set(presence) != set(names) or not isinstance(metadata, dict) or
            any(not isinstance(columns[name], list) or len(columns[name]) != count
                or not isinstance(presence[name], list) or len(presence[name]) != count
                or any(type(bit) is not bool for bit in presence[name])
                for name in names)):
        raise ValueError("invalid segmented primary columns")
    rows = [{name: columns[name][index] for name in names
             if presence[name][index]}
            for index in range(count)]
    primary = dict(metadata)
    primary["trajectory"] = rows
    if canonical_sha256(primary) != segment.get("canonical_primary_sha256"):
        raise ValueError("segmented primary canonical hash mismatch")
    return primary


def write_segment_atomic(path: Path, segment: dict) -> str:
    """Write one process-owned segment atomically and return its file hash."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = canonical_bytes(segment)
    temporary = path.with_name(path.name + f".{os.getpid()}.tmp")
    try:
        with temporary.open("wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()
    return hashlib.sha256(payload).hexdigest()
