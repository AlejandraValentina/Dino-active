"""Desktop project contract for Dino 4T, separate from the frozen 2T schema."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json

SCHEMA = "DINO_DESKTOP_ENGINE_PROJECT_4T_V1"


def create_project(project_id: str, engine: dict, *, variants=None, run_references=None,
                   scientific_validation_status="SYNTHETIC_UNVALIDATED") -> dict:
    from .. import engine_platform
    if not isinstance(project_id, str) or not project_id.strip():
        raise ValueError("project_id must be non-empty")
    checked = engine_platform.validate_config("4T", engine)
    if not checked["valid"] or checked["unknown_keys"]:
        raise ValueError(f"invalid 4T configuration: {checked['issues']} {checked['unknown_keys']}")
    project = {"schema": SCHEMA, "project_id": project_id, "engine_family": "4T",
        "base_engine": deepcopy(engine), "base_identity_sha256": checked["config_sha256"],
        "variants": deepcopy(variants or {}), "run_references": deepcopy(run_references or []),
        "scientific_validation_status": scientific_validation_status}
    validate_project(project)
    return project


def config_identity(config: dict) -> str:
    from .. import engine_platform
    return engine_platform.identity("4T", config)


def validate_project(project: dict) -> None:
    from .. import engine_platform
    fields = {"schema", "project_id", "engine_family", "base_engine", "base_identity_sha256",
              "variants", "run_references", "scientific_validation_status"}
    if not isinstance(project, dict) or project.get("schema") != SCHEMA or set(project) != fields:
        raise ValueError("4T desktop project schema/fields invalid")
    if project.get("engine_family") != "4T" or not isinstance(project.get("project_id"), str) or not project["project_id"].strip():
        raise ValueError("4T project identity invalid")
    for engine in [project["base_engine"], *project["variants"].values()]:
        check = engine_platform.validate_config("4T", engine)
        if not check["valid"] or check["unknown_keys"]:
            raise ValueError(f"invalid 4T engine configuration: {check['issues']} {check['unknown_keys']}")
    if project["base_identity_sha256"] != config_identity(project["base_engine"]):
        raise ValueError("4T project base configuration identity mismatch")
    if not isinstance(project["variants"], dict) or not isinstance(project["run_references"], list):
        raise ValueError("4T variants and run references must be collections")
    for name, config in project["variants"].items():
        if not isinstance(name, str) or not name.strip() or config.get("identifier") != name:
            raise ValueError("4T variant identifier mismatch")
    required = {"run_id", "path", "result_sha256", "config_sha256", "status", "periodicity_status", "variant_id"}
    run_ids=set()
    for ref in project["run_references"]:
        from .four_stroke_artifacts import REFERENCE_SCHEMA
        fields = required | {"schema", "run_manifest_path", "run_manifest_sha256"} if isinstance(ref, dict) and ref.get("schema") == REFERENCE_SCHEMA else required
        if not isinstance(ref, dict) or set(ref) != fields or not isinstance(ref["path"], str) or not ref["path"]:
            raise ValueError("4T run reference fields invalid")
        if "schema" in ref and (not isinstance(ref["run_manifest_path"], str) or not ref["run_manifest_path"]):
            raise ValueError("4T run manifest path invalid")
        for key in ("result_sha256", "config_sha256", *(("run_manifest_sha256",) if "schema" in ref else ())):
            value = ref[key]
            if not isinstance(value, str) or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
                raise ValueError(f"invalid 4T run reference {key}")
        if ref["periodicity_status"] not in {"PERIODIC_CONVERGED", "NOT_CONVERGED", "NOT_REPORTED"}:
            raise ValueError("invalid 4T periodicity status")
        if ref["run_id"] in run_ids:
            raise ValueError("duplicate 4T run reference")
        run_ids.add(ref["run_id"])


def load_example() -> dict:
    from ..dino4t.config import EXAMPLE_PATH, load
    config=load(EXAMPLE_PATH)
    # Resolve all optional model selections explicitly so a future default
    # change cannot silently change the Desktop's chosen solver configuration.
    config.setdefault("combustion",{}).setdefault("zone_model","two_zone_equilibrium")
    config.setdefault("numerics",{}).setdefault("restriction_model","V2")
    config.setdefault("numerics",{}).setdefault("limiter","minmod")
    return config


def project_from_example(project_id="dino-4t-nuevo") -> dict:
    config = load_example()
    config["identifier"] = f"{project_id}-motor"
    return create_project(project_id, config)
