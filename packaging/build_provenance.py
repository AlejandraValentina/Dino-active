"""Deterministic provenance for the bytes consumed by the Windows bundle."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import subprocess

from bundle_inputs import (ConsumedInput, bundle_data_inputs, git_input_scope,
                           repository_input_paths)
from motorsim.source_provenance import SOURCE_POLICY_FILES


def packaged_input_paths(root: Path) -> list[Path]:
    """Files copied, source-backed, or required to produce the shipped app."""
    return repository_input_paths(root)


def input_manifest(root: Path, consumed=()) -> dict:
    root = Path(root).resolve()
    files = []
    for path in packaged_input_paths(root):
        data = path.read_bytes()
        relative = path.relative_to(root).as_posix()
        files.append({"path": relative,
                      "role": "GIT_POLICY" if relative in SOURCE_POLICY_FILES else "REPOSITORY_BUILD_INPUT",
                      "size_bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()})
    consumed_files = []
    labels = set()
    destinations = set()
    for item in sorted(consumed, key=lambda x: x.logical_path):
        if item.logical_path.casefold() in labels or (item.bundle_path and item.bundle_path.casefold() in destinations):
            raise ValueError("Duplicate consumed input/destination: " + item.logical_path)
        labels.add(item.logical_path.casefold())
        if item.bundle_path:
            destinations.add(item.bundle_path.casefold())
        path = Path(item.source).resolve()
        if Path(item.source).is_symlink() or not path.is_file():
            raise FileNotFoundError("Missing/nonregular consumed input: " + item.logical_path)
        data = path.read_bytes()
        value = {"logical_path": item.logical_path, "bundle_path": item.bundle_path,
                 "size_bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
        try:
            value.update(origin="EXPLICIT_BYTE_INPUT", git_bound=False,
                         repository_path=path.relative_to(root).as_posix())
        except ValueError:
            value.update(origin="EXPLICIT_BYTE_INPUT", git_bound=False, repository_path=None)
        consumed_files.append(value)
    canonical = json.dumps({"files": files, "consumed_files": consumed_files}, ensure_ascii=False, sort_keys=True,
                           separators=(",", ":")).encode("utf-8")
    return {"schema": "DINO_BUNDLE_INPUT_MANIFEST_V2", "files": files,
            "consumed_files": consumed_files, "byte_policy": "Raw bytes; no EOL normalization",
            "sha256": hashlib.sha256(canonical).hexdigest()}


def git_status(root: Path, paths: list[str] | None = None) -> bytes:
    args = ["git", "status", "--porcelain=v1", "-z", "--untracked-files=all"]
    if paths:
        args += ["--", *paths]
    return subprocess.check_output(args, cwd=root)


def ensure_packaged_inputs_clean(root: Path, consumed=()) -> None:
    """Refuse a package if any app/build input differs from the named commit."""
    status = git_status(root, git_input_scope(root, consumed))
    if status:
        paths = []
        for entry in status.decode("utf-8", errors="replace").split("\0"):
            if len(entry) >= 4:
                paths.append(entry[3:])
        raise RuntimeError("Entradas del paquete/build con cambios locales; commit requerido: " +
                           ", ".join(paths[:12]))
    # git status does not report ignored files, although a recursive data/source
    # inventory can consume them. Every static repository preimage must exist in
    # the index; explicit dynamic byte inputs are identified separately.
    tracked = {p.decode("utf-8") for p in subprocess.check_output(
        ["git", "ls-files", "-z", "--", *git_input_scope(root)], cwd=root).split(b"\0") if p}
    declared = {p.relative_to(Path(root).resolve()).as_posix() for p in packaged_input_paths(root)}
    untracked = sorted(declared - tracked)
    if untracked:
        raise RuntimeError("Entradas declaradas sin vínculo Git: " + ", ".join(untracked[:12]))


def unrelated_dirty_fingerprint(root: Path, consumed=()) -> dict:
    """Summarize unrelated working-tree changes without recording local paths."""
    all_status = git_status(root)
    package_status = git_status(root, git_input_scope(root, consumed))
    unrelated = all_status  # Caller first requires package_status to be empty.
    if package_status:
        ensure_packaged_inputs_clean(root, consumed)
    entries = [item for item in unrelated.split(b"\0") if item]
    return {"source_dirty": bool(entries), "unrelated_dirty_entry_count": len(entries),
            "unrelated_dirty_status_sha256": hashlib.sha256(unrelated).hexdigest()}


def verify_input_snapshot(root: Path, manifest: dict, consumed=()) -> None:
    """Both the Git boundary and exact raw snapshot must survive consumption."""
    ensure_packaged_inputs_clean(root, consumed)
    if input_manifest(root, consumed)["sha256"] != manifest["sha256"]:
        raise RuntimeError("A declared bundle input changed during the build")


def copy_bound_file(source: Path, target: Path, expected_sha256: str) -> dict:
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    if hashlib.sha256(target.read_bytes()).hexdigest() != expected_sha256:
        raise RuntimeError("Copied input does not match its pre-build byte snapshot: " + str(target))
    return {"path": str(target), "sha256": expected_sha256}


def copy_repository_file(root: Path, relative: str, target: Path, manifest: dict) -> dict:
    entry = next((x for x in manifest["files"] if x["path"] == relative), None)
    if entry is None:
        raise RuntimeError("Undeclared repository copy: " + relative)
    return copy_bound_file(Path(root) / relative, target, entry["sha256"])


def copy_consumed_inputs(bundle: Path, consumed, manifest: dict) -> list[dict]:
    entries = {x["logical_path"]: x for x in manifest["consumed_files"]}
    copied = []
    for item in consumed:
        if item.bundle_path is not None:
            if item.logical_path not in entries:
                raise RuntimeError("Undeclared consumed copy: " + item.logical_path)
            copied.append(copy_bound_file(item.source, Path(bundle) / item.bundle_path,
                                          entries[item.logical_path]["sha256"]))
    return copied


def verify_copied_files(copied) -> None:
    for entry in copied:
        path = Path(entry["path"])
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != entry["sha256"]:
            raise RuntimeError("Final copied preimage changed: " + str(path))


def verify_bundle_data(root: Path, generated: Path, bundle: Path, manifest: dict,
                       generated_sha256: str) -> None:
    entries = {x["path"]: x for x in manifest["files"]}
    seen = set()
    for target in ("gui", "dino", "worker"):
        for item in bundle_data_inputs(root, target, generated):
            if item.source == Path(generated) / "build.json":
                expected = generated_sha256
            else:
                try:
                    expected = entries[item.source.relative_to(root).as_posix()]["sha256"]
                except (ValueError, KeyError) as exc:
                    raise RuntimeError("Undeclared bundle input: " + str(item.source)) from exc
            path = Path(bundle) / "_internal" / item.destination / item.source.name
            if path in seen:
                continue
            seen.add(path)
            if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
                raise RuntimeError("Packaged data preimage differs from declared input: " + str(path))


def package_model_metadata(root: Path) -> dict:
    """Keep the native API model family distinct from the legacy reference UI."""
    from motorsim.reference_results import MODEL_VERSION, FOUR_MODEL_VERSION
    from motorsim.dino4t import MODEL_ID
    from motorsim.dino4t.runner import resolved_models
    config = json.loads((Path(root) / "configs/dino4t/example_single_cylinder_500cc.json").read_text(encoding="utf-8"))
    return {"models": {"two_stroke": MODEL_VERSION, "four_stroke": MODEL_ID},
            "legacy_models": {"two_stroke": MODEL_VERSION, "four_stroke": FOUR_MODEL_VERSION},
            "native_engine_models": {"four_stroke": {"model_id": MODEL_ID, "api": "DINO4T_API_V1",
                "example_components": resolved_models(config),
                "component_selection_authority": "each native result.models, not package defaults"}}}
