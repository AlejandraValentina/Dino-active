"""Native artifact commit marker and byte verification, independent of Desktop."""
from __future__ import annotations

import csv
import hashlib
import io
import json
import math
from pathlib import Path, PurePosixPath

SCHEMA = "DINO4T_ARTIFACT_MANIFEST_V1"
BYTE_POLICY = "UTF8_LF_JSON_AND_CSV_V1"


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")


def parse_json(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result: raise ValueError("duplicate JSON key: " + key)
            result[key] = value
        return result
    def constant(value):
        raise ValueError("nonfinite JSON token: " + value)
    def floating(value):
        result = float(value)
        if not math.isfinite(result): raise ValueError("nonfinite JSON number: " + value)
        return result
    value = json.loads(raw, object_pairs_hook=pairs, parse_constant=constant, parse_float=floating)
    if not isinstance(value, dict): raise ValueError("JSON root must be an object")
    return value


def safe_path(base, relative):
    base = Path(base).resolve()
    if not isinstance(relative, str) or not relative or "\\" in relative or ":" in relative:
        raise ValueError("artifact path must be a safe POSIX relative path")
    parts = PurePosixPath(relative)
    if parts.is_absolute() or str(parts) != relative or any(x in ("..", ".") for x in parts.parts):
        raise ValueError("artifact path escapes its bundle")
    path = base.joinpath(*parts.parts)
    for parent in [path, *path.parents]:
        if parent == base: break
        if parent.is_symlink(): raise ValueError("symbolic artifact paths are not allowed")
    if not path.resolve().is_relative_to(base): raise ValueError("artifact path escapes its bundle")
    return path


def require_empty_output(directory):
    path = Path(directory)
    if path.exists() and (not path.is_dir() or any(path.iterdir())):
        raise FileExistsError("artifact output must be new or empty; existing evidence is never overwritten")


def trace_bytes(trace):
    keys = [k for k, v in trace.items() if isinstance(v, list) and k != "pressure_grid" and len(v) == len(trace["theta"])]
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, lineterminator="\n"); writer.writerow(keys)
    for row in zip(*(trace[k] for k in keys)):
        writer.writerow([f"{value:.10g}" for value in row])
    return stream.getvalue().encode("utf-8")


def publish_primary(directory, summary, config, trace=None, *, origin=None, raw_primary=None):
    """Publish new exact preimages, manifest last. Never overwrite old data.

    raw_primary is used only for explicit receipt-backed historical copying;
    its bytes are retained, not normalized to the new producer byte policy.
    """
    from .config import canonical_hash
    require_empty_output(directory)
    directory = Path(directory); directory.mkdir(parents=True, exist_ok=True)
    payloads = raw_primary if raw_primary is not None else {"summary": json_bytes(summary), "config": json_bytes(config),
                               **({"trace": trace_bytes(trace)} if trace is not None else {})}
    names = {"summary": "summary.json", "config": "config_resolved.json", "trace": "trace_last_cycle.csv"}
    if not {"summary", "config"}.issubset(payloads) or set(payloads) - set(names):
        raise ValueError("invalid primary artifact roles")
    entries = {}
    for role, raw in payloads.items():
        path = directory / names[role]
        with path.open("xb") as stream: stream.write(raw)
        entries[role] = {"path": names[role], "size_bytes": len(raw), "sha256": sha256(raw)}
    manifest = {"schema": SCHEMA, "byte_policy": "PRESERVED_IMPORT_PREIMAGES_V1" if raw_primary else BYTE_POLICY,
                "config_identity_sha256": canonical_hash(config), "artifacts": entries,
                "origin": origin or {"kind": "DINO4T_API_PRODUCER"}}
    raw = json_bytes(manifest)
    with (directory / "artifacts.json").open("xb") as stream: stream.write(raw)
    return {"manifest": "artifacts.json", "manifest_sha256": sha256(raw),
            "summary": names["summary"], "config_resolved": names["config"],
            "trace_last_cycle": names["trace"] if "trace" in entries else None, "directory": str(directory)}


def verify_primary(manifest_path, expected_sha256):
    """Return a single verified byte snapshot; no file is reopened for plotting."""
    from .config import canonical_hash
    manifest_path = Path(manifest_path)
    raw_manifest = manifest_path.read_bytes()
    if not isinstance(expected_sha256, str) or sha256(raw_manifest) != expected_sha256:
        raise ValueError("original artifact manifest digest mismatch")
    manifest = parse_json(raw_manifest)
    if manifest.get("schema") != SCHEMA: raise ValueError("unsupported artifact manifest")
    if not isinstance(manifest.get("origin"), dict) or not isinstance(manifest["origin"].get("kind"), str):
        raise ValueError("artifact origin must be explicit")
    entries = manifest.get("artifacts")
    if not isinstance(entries, dict) or not {"summary", "config"}.issubset(entries) or set(entries) - {"summary", "config", "trace"}:
        raise ValueError("invalid artifact roles")
    snapshot, paths, logical_paths = {}, {}, set()
    for role, entry in entries.items():
        if not isinstance(entry, dict) or type(entry.get("size_bytes")) is not int or entry["size_bytes"] < 0:
            raise ValueError("invalid byte preimage descriptor")
        path = safe_path(manifest_path.parent, entry.get("path"))
        logical = entry["path"].casefold()
        if logical in logical_paths: raise ValueError("duplicate/case-aliased artifact preimage path")
        logical_paths.add(logical)
        paths[role] = path
        raw = path.read_bytes()
        if len(raw) != entry.get("size_bytes") or sha256(raw) != entry.get("sha256"):
            raise ValueError(f"{role} original byte identity mismatch")
        snapshot[role] = raw
    summary = parse_json(snapshot["summary"]); config = parse_json(snapshot["config"])
    identity = canonical_hash(config)
    if identity != manifest.get("config_identity_sha256") or identity != summary.get("config_sha256"):
        raise ValueError("manifest/config/result semantic identity mismatch")
    cycles = summary.get("cycles_run")
    if type(cycles) is not int or cycles < 0: raise ValueError("invalid recorded cycle count")
    if cycles > 0 and "trace" not in snapshot:
        raise ValueError("complete cycles require their original trace")
    if "trace" in snapshot:
        stream = io.StringIO(snapshot["trace"].decode("utf-8"))
        reader = csv.DictReader(stream)
        if not reader.fieldnames or len(set(reader.fieldnames)) != len(reader.fieldnames) or not {"theta", "p"}.issubset(reader.fieldnames):
            raise ValueError("trace requires unique theta/p columns")
        rows = list(reader)
        try: values = [(float(row["theta"]), float(row["p"])) for row in rows]
        except (ValueError, TypeError, KeyError) as exc: raise ValueError("invalid trace values") from exc
        if len(values) < 2 or not all(math.isfinite(t) and math.isfinite(p) and p > 0 for t, p in values):
            raise ValueError("complete-cycle pressure trace must be finite and nonempty")
        if any(b[0] <= a[0] for a, b in zip(values, values[1:])):
            raise ValueError("trace crank angles are not strictly increasing")
        def quantum(value):
            return 10 ** (math.floor(math.log10(abs(value))) - 9) if value else 0.0
        # Native traces retain ten significant digits. This is the resulting
        # endpoint serialization bound, not a relaxed physical-cycle criterion.
        start, end = values[0][0], values[-1][0]
        rounding_bound = .5 * (quantum(start) + quantum(end)) + 32 * math.ulp(max(abs(start), abs(end), 720.0))
        if abs((end - start) - 720.0) > rounding_bound:
            raise ValueError("trace does not span one complete native 720-degree cycle")
    return {"manifest": manifest, "manifest_raw": raw_manifest, "raw": snapshot, "paths": paths,
            "summary": summary, "config": config, "manifest_path": manifest_path}
