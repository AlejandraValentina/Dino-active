"""Byte-verifiable source identity; no scientific or solver behavior lives here.

The conservative closure includes the whole application package and native 4T
configuration data, rather than guessing which shared numerical imports matter.
Git identifies canonical source revisions; raw hashes identify the bytes actually
present. A manifest is not a signature or a substitute for its source preimages.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys

SCHEMA = "DINO_SOURCE_IDENTITY_V1"
SOURCE_ROOTS = ("motorsim", "configs/dino4t")
SOURCE_POLICY_FILES = (".gitattributes", ".gitignore")
GENERATED_METADATA = "motorsim/build.json"
REQUIRED_SOURCE_FILES = (
    "motorsim/__init__.py", "motorsim/source_provenance.py",
    "motorsim/kinematics.py", "motorsim/gas1d/mesh.py",
    "motorsim/dino4t/validation.py", "motorsim/dino4t/artifacts.py",
    "motorsim/desktop/four_stroke_artifacts.py", "motorsim/desktop/four_stroke_comparison.py",
    "motorsim/desktop/templates/single_cylinder_2t_starter_v1.json",
    "configs/dino4t/example_single_cylinder_500cc.json",
    *tuple("motorsim/dino4t/" + name + ".py" for name in (
        "__init__", "api", "runner", "config", "engine", "duct", "kinematics",
        "thermo", "thermo_data", "valves", "restriction", "closures",
        "combustion", "twozone", "equilibrium", "cycle_analysis")),
)
BYTE_POLICY = {
    "raw": "SHA-256 and byte size of every actual regular-file preimage; no normalization",
    "canonical_code": "Python source bytes only: CRLF and CR become LF; no transcoding",
    "git": "Git revision/dirty state uses Git canonical working-tree semantics",
    "generated_metadata": GENERATED_METADATA + " is excluded to avoid recursive self-hashing",
    "policy_files": "Present Git policy files are raw preimages, not executable code; tracked missing policies are incomplete",
}


def _canonical(value) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":")).encode("utf-8")


def _excluded(relative: str) -> bool:
    p = Path(relative)
    return (relative == GENERATED_METADATA or "__pycache__" in p.parts
            or p.suffix.lower() in {".pyc", ".pyo"})


def _source_relative(relative: str) -> bool:
    return ((relative in SOURCE_POLICY_FILES or any(relative == prefix or relative.startswith(prefix + "/")
                for prefix in SOURCE_ROOTS)) and not _excluded(relative))


def _collect(root: Path, tracked=()):
    paths = {root / rel for rel in REQUIRED_SOURCE_FILES}
    paths.update(root / rel for rel in SOURCE_POLICY_FILES
                 if (root / rel).exists() or (root / rel).is_symlink())
    issues = []
    for prefix in SOURCE_ROOTS:
        base = root / prefix
        if not base.is_dir():
            issues.append("MISSING_SOURCE_ROOT:" + prefix)
            continue
        try:
            for p in base.rglob("*"):
                rel = p.relative_to(root).as_posix()
                if _excluded(rel):
                    continue
                if p.is_symlink():
                    issues.append("SYMLINK_SOURCE_INPUT:" + rel)
                elif p.is_file():
                    paths.add(p)
        except OSError:
            issues.append("UNREADABLE_SOURCE_ROOT:" + prefix)
    paths.update(root / rel for rel in tracked if _source_relative(rel))
    files = []
    for path in sorted(paths, key=lambda p: p.relative_to(root).as_posix()):
        rel = path.relative_to(root).as_posix()
        if path.is_symlink():
            issues.append("SYMLINK_SOURCE_INPUT:" + rel)
            continue
        try:
            data = path.read_bytes()
        except OSError:
            issues.append("MISSING_OR_UNREADABLE_SOURCE_INPUT:" + rel)
            continue
        role = "GIT_POLICY" if rel in SOURCE_POLICY_FILES else ("PYTHON_SOURCE" if path.suffix.lower() == ".py" else "RUNTIME_DATA")
        entry = {"path": rel, "role": role, "size_bytes": len(data),
                 "sha256": hashlib.sha256(data).hexdigest()}
        if path.suffix.lower() == ".py":
            normalized = data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
            entry["canonical_code_sha256"] = hashlib.sha256(normalized).hexdigest()
        files.append(entry)
    return files, sorted(set(issues))


def source_input_paths(root: Path) -> list[Path]:
    """The declared runtime closure, requiring its dependency/data anchors."""
    root = Path(root).resolve()
    files, issues = _collect(root)
    if issues:
        raise FileNotFoundError("Source input inventory incomplete: " + ", ".join(issues))
    return [root / entry["path"] for entry in files]


def _inventory(files):
    code = [{"path": x["path"], "canonical_code_sha256": x["canonical_code_sha256"]}
            for x in files if "canonical_code_sha256" in x]
    return {"files": files, "inventory_sha256": hashlib.sha256(_canonical(files)).hexdigest(),
            "canonical_code_inventory_sha256": hashlib.sha256(_canonical(code)).hexdigest()}


def _git(root: Path, *args) -> bytes:
    return subprocess.check_output(["git", *args], cwd=root, stderr=subprocess.PIPE, timeout=10)


def _commit(value):
    return value if isinstance(value, str) and re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", value) else None


def validate_source_identity(record, *, require_complete: bool = True) -> list[str]:
    """Pure historical-record validation; never substitutes current source files.

    This checks declared closure anchors and internal byte-manifest integrity.
    It is not a signature or an independent proof of the claimed Git ancestry.
    ``require_complete=False`` admits an explicit INCOMPLETE identity so a valid
    numeric result can still be published with an unverified source
    qualification; strict comparison consumers must require complete source.
    """
    if not isinstance(record, dict):
        return ["source_identity must be an object"]
    problems = []
    if record.get("schema") != SCHEMA:
        problems.append("source_identity schema is unsupported")
    if record.get("status") not in {"COMPLETE", "INCOMPLETE"}:
        problems.append("source_identity status is unsupported")
    complete = record.get("status") == "COMPLETE"
    if require_complete and not complete:
        problems.append("source_identity is incomplete")
    if complete:
        if record.get("stable_during_capture") is not True:
            problems.append("source_identity capture was not stable")
        if record.get("origin") not in {"GIT_WORKTREE", "PACKAGED_PREIMAGES"}:
            problems.append("source_identity has no verified source origin")
        if _commit(record.get("code_commit")) is None:
            problems.append("source_identity commit is invalid")
        if type(record.get("dirty")) is not bool:
            problems.append("source_identity dirty state is unknown/invalid")
        if record.get("origin") == "PACKAGED_PREIMAGES" and record.get("dirty") is not False:
            problems.append("packaged source snapshot is not clean")
        if not isinstance(record.get("issues"), list) or record.get("issues"):
            problems.append("source_identity contains unresolved capture issues")
        if "stable_during_run" in record and record["stable_during_run"] is not True:
            problems.append("source_identity changed during execution")
        if record.get("reproducible_by_commit") is not (record.get("dirty") is False):
            problems.append("source_identity commit reproducibility disagrees with dirty state")
    else:
        if not isinstance(record.get("issues"), list):
            problems.append("source_identity issues must be a list")
        if record.get("dirty") is not None and type(record.get("dirty")) is not bool:
            problems.append("source_identity dirty state is invalid")
        if record.get("code_commit") is not None and _commit(record.get("code_commit")) is None:
            problems.append("source_identity commit is invalid")
    if record.get("byte_policy") != BYTE_POLICY:
        problems.append("source_identity byte policy is unsupported")
    if not complete:
        return problems
    files = record.get("files")
    if not isinstance(files, list) or not files:
        return [*problems, "source_identity files are missing"]
    paths = []
    valid_entries = True
    for entry in files:
        if not isinstance(entry, dict):
            valid_entries = False
            continue
        path = entry.get("path")
        if (not isinstance(path, str) or not path or "\\" in path or ":" in path
                or PurePosixPath(path).is_absolute() or ".." in PurePosixPath(path).parts
                or str(PurePosixPath(path)) != path or not _source_relative(path)):
            valid_entries = False
            continue
        paths.append(path)
        role = "GIT_POLICY" if path in SOURCE_POLICY_FILES else ("PYTHON_SOURCE" if PurePosixPath(path).suffix.lower() == ".py" else "RUNTIME_DATA")
        if entry.get("role") != role:
            valid_entries = False
        if type(entry.get("size_bytes")) is not int or entry["size_bytes"] < 0:
            valid_entries = False
        if not isinstance(entry.get("sha256"), str) or not re.fullmatch(r"[0-9a-f]{64}", entry["sha256"]):
            valid_entries = False
        code_digest = entry.get("canonical_code_sha256")
        if PurePosixPath(path).suffix.lower() == ".py":
            if not isinstance(code_digest, str) or not re.fullmatch(r"[0-9a-f]{64}", code_digest):
                valid_entries = False
        elif "canonical_code_sha256" in entry:
            valid_entries = False
    if not valid_entries:
        problems.append("source_identity contains invalid file entries")
    if paths != sorted(set(paths)) or len(paths) != len(files):
        problems.append("source_identity file paths are not unique and canonical")
    if not set(REQUIRED_SOURCE_FILES) <= set(paths):
        problems.append("source_identity omits a required source/data dependency")
    if valid_entries:
        expected = _inventory(files)
        for key in ("inventory_sha256", "canonical_code_inventory_sha256"):
            if record.get(key) != expected[key]:
                problems.append("source_identity " + key + " mismatch")
    return problems


def capture_source_identity(root: Path | None = None, *, build_metadata: dict | None = None) -> dict:
    """Capture complete actual preimages, or explicitly report an unknown identity.

    Packaged mode accepts a clean origin only when the embedded complete snapshot
    and every shipped preimage agree. Sparse historical metadata is insufficient.
    The origin explicitly distinguishes that proof from a live Git inspection.
    """
    root = (Path(root) if root is not None else Path(__file__).resolve().parents[1]).resolve()
    files, issues = _collect(root)
    result = {"schema": SCHEMA, "status": "INCOMPLETE", "origin": "UNVERIFIED",
              "code_commit": None, "dirty": None, "byte_policy": dict(BYTE_POLICY),
              "stable_during_capture": False,
              "preimages": "actual source files named in files; hashes do not embed their contents",
              "reproducible_by_commit": False, **_inventory(files), "issues": issues}
    if build_metadata is None and getattr(sys, "frozen", False):
        try:
            build_metadata = json.loads((root / GENERATED_METADATA).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            result["issues"].append("PACKAGED_BUILD_METADATA_UNAVAILABLE")
            return result
    if build_metadata is not None:
        snapshot = build_metadata.get("source_identity") if isinstance(build_metadata, dict) else None
        valid = (isinstance(snapshot, dict) and not validate_source_identity(snapshot)
                 and snapshot.get("dirty") is False
                 and build_metadata.get("packaged_inputs_clean") is True
                 and _commit(snapshot.get("code_commit")) is not None
                 and snapshot.get("code_commit") == build_metadata.get("source_commit"))
        if not valid:
            result["issues"].append("PACKAGED_SOURCE_SNAPSHOT_UNVERIFIED")
            return result
        final_files, final_issues = _collect(root)
        if (issues or final_issues or final_files != files or snapshot.get("files") != files
                or snapshot.get("inventory_sha256") != result["inventory_sha256"]):
            result["dirty"] = True
            result["issues"].append("PACKAGED_SOURCE_PREIMAGE_MISMATCH")
            return result
        result.update(status="COMPLETE", origin="PACKAGED_PREIMAGES",
                      code_commit=snapshot["code_commit"], dirty=False,
                      stable_during_capture=True, reproducible_by_commit=True)
        return result
    try:
        git_root = Path(_git(root, "rev-parse", "--show-toplevel").decode().strip()).resolve()
        commit = _commit(_git(root, "rev-parse", "--verify", "HEAD").decode().strip())
        if git_root != root or commit is None:
            raise ValueError("unverifiable Git root/commit")
        scopes = (*SOURCE_ROOTS, *SOURCE_POLICY_FILES)
        tracked = [p.decode("utf-8") for p in _git(root, "ls-files", "-z", "--", *scopes).split(b"\0") if p]
        changed = [p.decode("utf-8") for p in _git(root, "diff", "--name-only", "-z", "HEAD", "--", *scopes).split(b"\0") if p]
        initial_files = files
        files, issues = _collect(root, tracked)
        final_changed = [p.decode("utf-8") for p in _git(root, "diff", "--name-only", "-z", "HEAD", "--", *scopes).split(b"\0") if p]
        final_commit = _commit(_git(root, "rev-parse", "--verify", "HEAD").decode().strip())
        stable = files == initial_files and final_commit == commit and changed == final_changed
        if not stable:
            issues.append("SOURCE_CHANGED_DURING_CAPTURE")
        actual = {x["path"] for x in files}
        dirty = (any(_source_relative(p) for p in [*changed, *final_changed])
                 or bool(actual - set(tracked)) or not stable)
        result.update(**_inventory(files), issues=issues, code_commit=commit,
                      dirty=dirty, origin="GIT_WORKTREE", stable_during_capture=stable)
        if not issues:
            result.update(status="COMPLETE", reproducible_by_commit=not dirty)
    except (OSError, UnicodeError, ValueError, subprocess.SubprocessError):
        result["issues"].append("GIT_SOURCE_IDENTITY_UNAVAILABLE")
    return result
