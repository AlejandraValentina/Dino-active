"""Persistent lightweight engine projects; cycle primaries stay external."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import tempfile
from typing import Any

from .engine_configuration import identity, validate
from .engine_variants import compare_configurations

SCHEMA = "MOTORSIM_ENGINE_PROJECT_V2"
LEGACY_SCHEMA = "MOTORSIM_ENGINE_PROJECT_V1"


def create_project(project_id: str, base_engine: dict, *, simulation_recipes: dict | None = None,
                   variants: dict | None = None, result_references: list | None = None,
                   scientific_validation_status: str = "NOT_RUN") -> dict:
    validate(base_engine)
    variants = variants or {}
    for name, item in variants.items():
        if not isinstance(name, str) or not name: raise ValueError("variant name required")
        validate(item)
    refs = result_references or []
    for ref in refs:
        if not isinstance(ref, dict) or set(ref) != {"path", "identity_sha256", "artifact_sha256", "classification"}:
            raise ValueError("result reference must contain path, identities, hash and classification only")
        if any(not isinstance(ref[k], str) or not ref[k] for k in ref): raise ValueError("result reference values must be nonempty strings")
    return {"schema": SCHEMA, "project_id": project_id, "base_engine": deepcopy(base_engine),
            "base_identity_sha256": identity(base_engine),
            "variants": deepcopy(variants), "simulation_recipes": deepcopy(simulation_recipes or {}),
            "result_references": deepcopy(refs),
            "measurement_references": [],
            "scientific_validation_status": scientific_validation_status}


def validate_project(project: dict) -> None:
    fields = {"schema", "project_id", "base_engine", "base_identity_sha256", "variants",
              "simulation_recipes", "result_references", "scientific_validation_status"}
    v2_fields = fields | {"measurement_references"}
    if (not isinstance(project, dict) or
            (project.get("schema") == SCHEMA and set(project) != v2_fields) or
            (project.get("schema") == LEGACY_SCHEMA and set(project) != fields) or
            project.get("schema") not in {SCHEMA, LEGACY_SCHEMA}):
        raise ValueError("engine project schema/fields invalid")
    validate(project["base_engine"])
    if identity(project["base_engine"]) != project["base_identity_sha256"]:
        raise ValueError("base engine identity mismatch")
    if not isinstance(project["project_id"], str) or not project["project_id"].strip():
        raise ValueError("project_id must be nonempty")
    if not isinstance(project["variants"], dict) or not isinstance(project["simulation_recipes"], dict):
        raise ValueError("variants and simulation_recipes must be objects")
    for item in project["variants"].values(): validate(item)
    if not isinstance(project["result_references"], list): raise ValueError("result_references must be a list")
    for ref in project["result_references"]:
        if not isinstance(ref, dict) or set(ref) != {"path", "identity_sha256", "artifact_sha256", "classification"}:
            raise ValueError("invalid external result reference")
        for key in ("identity_sha256", "artifact_sha256"):
            value = ref[key]
            if not isinstance(value, str) or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
                raise ValueError(f"invalid external result reference {key}")
    for ref in project.get("measurement_references", []):
        if not isinstance(ref, dict) or set(ref) != {
                "path", "dataset_id", "metadata_sha256", "csv_sha256", "classification"}:
            raise ValueError("invalid measurement reference")
        if (not isinstance(ref["path"], str) or not ref["path"] or
                not isinstance(ref["dataset_id"], str) or len(ref["dataset_id"]) != 32 or
                any(c not in "0123456789abcdef" for c in ref["dataset_id"]) or
                ref["classification"] not in {"MEASURED", "DOCUMENTED", "SYNTHETIC", "UNKNOWN"}):
            raise ValueError("invalid measurement reference identity or classification")
        for key in ("metadata_sha256", "csv_sha256"):
            value = ref[key]
            if not isinstance(value, str) or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
                raise ValueError(f"invalid measurement reference {key}")
    # Explicitly prevent accidentally embedding primary/checkpoint payloads.
    forbidden = {"primaries", "primary_evidence", "checkpoint_payload", "cycle_primaries", "cycle_data"}
    def walk(value, path="project"):
        if isinstance(value, dict):
            if forbidden.intersection(value): raise ValueError(f"bulk evidence is forbidden in editable project at {path}")
            for k, v in value.items(): walk(v, path+"."+k)
        elif isinstance(value, list):
            for i, v in enumerate(value): walk(v, f"{path}[{i}]")
    walk(project)


def save_project(path: str | Path, project: dict) -> str:
    validate_project(project)
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = (json.dumps(project, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")
    fd, tmp_name = tempfile.mkstemp(prefix=target.name + ".", suffix=".tmp", dir=target.parent)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(payload); f.flush(); os.fsync(f.fileno())
        os.replace(tmp_name, target)
    finally:
        try: os.unlink(tmp_name)
        except FileNotFoundError: pass
    return hashlib.sha256(payload).hexdigest()


def load_project(path: str | Path) -> dict:
    path = Path(path)
    project = json.loads(path.read_text(encoding="utf-8"))
    if project.get("schema") == LEGACY_SCHEMA:
        project["schema"] = SCHEMA
        project["measurement_references"] = []
    validate_project(project)
    # Explicit ./ references travel with packaged examples. Legacy relative
    # paths retain their artifact-root semantics; evidence bytes are untouched.
    for ref in project["result_references"]:
        if ref["path"].startswith(("./", ".\\")):
            ref["path"] = str((path.resolve().parent / ref["path"]).resolve())
    for ref in project["measurement_references"]:
        if ref["path"].startswith(("./", ".\\")):
            ref["path"] = str((path.resolve().parent / ref["path"]).resolve())
    return project


def duplicate_project(project: dict, *, project_id: str, display_name: str | None = None) -> dict:
    validate_project(project)
    result = deepcopy(project); result["project_id"] = project_id
    if display_name is not None: result["base_engine"]["display_name"] = display_name
    result["base_identity_sha256"] = identity(result["base_engine"])
    return result


def compare_project_engines(project: dict, variant_name: str) -> list[dict[str, Any]]:
    validate_project(project)
    if variant_name not in project["variants"]: raise KeyError(variant_name)
    return compare_configurations(project["base_engine"], project["variants"][variant_name])
