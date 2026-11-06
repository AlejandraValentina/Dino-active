"""Versioned run-reference boundary for Desktop and other native 4T consumers.

Integrity is relative to the caller's project/reference trust root. It is not
authentication of an external measurement or proof a claimed solver ran.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path

from ..dino4t import api
from ..dino4t.artifacts import json_bytes, parse_json, publish_primary, safe_path, sha256, verify_primary
from ..dino4t.config import canonical_hash

RUN_SCHEMA = "DINO4T_DESKTOP_RUN_V2"
REFERENCE_SCHEMA = "DINO4T_RUN_REFERENCE_V2"


def curve_binding(config):
    value = deepcopy(config); value.get("operating_point", {}).pop("rpm", None)
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                             allow_nan=False).encode("utf-8"))


@dataclass
class RunAssessment:
    classification: str
    issues: list[str] = field(default_factory=list)
    summary: dict | None = None
    config: dict | None = None
    meta: dict = field(default_factory=dict)
    reference: dict = field(default_factory=dict)
    snapshot: dict = field(default_factory=dict, repr=False)

    @property
    def verified(self):
        return self.classification == "VERIFIED"

    def endpoint(self):
        if not self.verified: raise ValueError(self.classification + ": " + "; ".join(self.issues))
        return {"summary": deepcopy(self.summary), "config": deepcopy(self.config), "meta": deepcopy(self.meta),
                "reference": deepcopy(self.reference),
                "trace_sha256": sha256(self.snapshot["raw"]["trace"]) if "trace" in self.snapshot["raw"] else None}


def publish_desktop_run(run_dir, envelope, project_id, variant_id="", *, run_id=None):
    """Anchor the API producer's original manifest in immutable metadata and an outer ref."""
    root = Path(run_dir); root.mkdir(parents=True, exist_ok=True)
    artifacts = envelope.get("artifacts", {})
    manifest_path = safe_path(root, "artifacts/" + artifacts["manifest"])
    primary = verify_primary(manifest_path, artifacts["manifest_sha256"])
    summary, config = primary["summary"], primary["config"]
    if summary != envelope.get("summary"): raise ValueError("API envelope differs from persisted primary")
    entries = primary["manifest"]["artifacts"]
    meta = {"schema": RUN_SCHEMA, "run_id": run_id or root.name, "project_id": project_id,
            "variant_id": variant_id, "api": api.API_VERSION,
            "artifacts_manifest_path": "artifacts/" + artifacts["manifest"],
            "artifacts_manifest_sha256": artifacts["manifest_sha256"],
            "result_sha256": entries["summary"]["sha256"], "config_sha256": summary["config_sha256"],
            "config_identity_sha256": canonical_hash(config), "curve_binding_sha256": curve_binding(config),
            "summary_path": "artifacts/" + entries["summary"]["path"],
            "config_path": "artifacts/" + entries["config"]["path"],
            "trace_path": "artifacts/" + entries["trace"]["path"] if "trace" in entries else None,
            "status": summary["status"], "periodicity_status": summary["periodicity"]["status"],
            "claims": summary["claims"], "result_validation": envelope.get("result_validation")}
    raw = json_bytes(meta)
    with (root / "run.json").open("xb") as stream: stream.write(raw)
    reference = {"schema": REFERENCE_SCHEMA, "run_id": meta["run_id"],
            "path": str((root / meta["summary_path"]).resolve()),
            "run_manifest_path": str((root / "run.json").resolve()), "run_manifest_sha256": sha256(raw),
            "result_sha256": meta["result_sha256"], "config_sha256": summary["config_sha256"],
            "status": meta["status"], "periodicity_status": meta["periodicity_status"], "variant_id": variant_id}
    portable = {**reference, "path": "./" + meta["summary_path"], "run_manifest_path": "./run.json"}
    with (root / "reference.json").open("xb") as stream: stream.write(json_bytes(portable))
    return reference


def assess_run_reference(reference):
    """No silent legacy upgrade. Return raw-data classifications rather than rewrite anything."""
    ref = deepcopy(reference); result = RunAssessment("UNAVAILABLE", reference=ref)
    try:
        path = Path(ref["path"]); raw = path.read_bytes()
        if sha256(raw) != ref["result_sha256"]: raise ValueError("project/result byte identity mismatch")
        summary = parse_json(raw); result.summary = summary
        if ref.get("schema") != REFERENCE_SCHEMA:
            # A legacy summary digest says nothing about the original trace.
            meta_path = path.parent.parent / "run.json"
            meta = parse_json(meta_path.read_bytes()); result.meta = meta
            config = parse_json(Path(meta["config_path"]).read_bytes()); result.config = config
            issues = api.check_summary(summary, config=config)
            result.classification = "LEGACY_INCOMPATIBLE" if issues else "LEGACY_UNVERIFIED"
            result.issues = issues or ["original metadata/trace binding absent; no verified pressure curve or A/B eligibility"]
            return result
        metadata_path = Path(ref["run_manifest_path"])
        metadata_raw = metadata_path.read_bytes()
        if sha256(metadata_raw) != ref["run_manifest_sha256"]: raise ValueError("original run metadata digest mismatch")
        meta = parse_json(metadata_raw)
        if meta.get("schema") != RUN_SCHEMA or meta.get("run_id") != ref["run_id"]:
            raise ValueError("run metadata/reference identity mismatch")
        manifest_path = safe_path(metadata_path.parent, meta["artifacts_manifest_path"])
        primary = verify_primary(manifest_path, meta["artifacts_manifest_sha256"])
        result.summary, result.config = primary["summary"], primary["config"]
        for role, key in (("summary", "summary_path"), ("config", "config_path"), ("trace", "trace_path")):
            if role in primary["paths"] and safe_path(metadata_path.parent, meta[key]) != primary["paths"][role]:
                raise ValueError("metadata redirects original " + role)
        if primary["paths"]["summary"].resolve() != path.resolve() or primary["raw"]["summary"] != raw:
            raise ValueError("outer reference redirects original summary")
        for key, expected in (("result_sha256", sha256(raw)), ("config_sha256", summary["config_sha256"]),
                              ("status", summary["status"]), ("periodicity_status", summary["periodicity"]["status"])):
            if ref.get(key) != expected or meta.get(key) != expected: raise ValueError("reference/metadata contradicts " + key)
        if meta.get("variant_id") != ref.get("variant_id") or meta.get("api") != api.API_VERSION:
            raise ValueError("run context contradicts reference")
        if meta.get("config_identity_sha256") != canonical_hash(result.config) or meta.get("curve_binding_sha256") != curve_binding(result.config):
            raise ValueError("configuration/curve binding mismatch")
        if meta.get("claims") != summary.get("claims"): raise ValueError("claims contradict raw result")
        issues = api.check_summary(result.summary, config=result.config)
        result.classification = ("INELIGIBLE_INTEGRITY" if issues and all(x.startswith("INELIGIBLE_INTEGRITY") for x in issues)
                                 else "INVALID_CONTRACT" if issues else "VERIFIED"); result.issues = issues
        identity = summary.get("source_identity")
        source_qualification = ("COMPLETE_CLEAN_SOURCE_SNAPSHOT" if isinstance(identity, dict) and identity.get("status")=="COMPLETE" and summary.get("code_dirty") is False
                                else "DIRTY_OR_UNKNOWN_SOURCE" if identity else "SOURCE_IDENTITY_UNVERIFIED_LEGACY")
        result.meta = {**meta, "summary_path": str(path), "config_path": str(primary["paths"]["config"]),
                       "trace_path": str(primary["paths"]["trace"]) if "trace" in primary["paths"] else None,
                       "integrity_classification": result.classification,
                       "source_qualification": source_qualification,
                       "artifact_origin": primary["manifest"]["origin"],
                       "artifact_byte_policy": primary["manifest"]["byte_policy"]}
        result.snapshot = {**primary, "metadata_raw": metadata_raw, "metadata_path": metadata_path}
    except (OSError, ValueError, KeyError, TypeError) as exc:
        result.classification = "UNAVAILABLE" if isinstance(exc, OSError) else "CORRUPT_OR_INCOMPATIBLE"
        result.issues = [f"{type(exc).__name__}: {exc}"]
    return result


def require_verified_run(reference):
    result = assess_run_reference(reference)
    if not result.verified: raise ValueError(result.classification + ": " + "; ".join(result.issues))
    return result


def import_reference_bundle(reference_path, destination):
    """Admit a supplied original outer reference, not a hash invented beside a trace."""
    source = Path(reference_path); ref = parse_json(source.read_bytes())
    if ref.get("schema") != REFERENCE_SCHEMA: raise ValueError("an original versioned outer reference is required")
    for key in ("path", "run_manifest_path"):
        if ref[key].startswith("./"):
            ref[key] = str(safe_path(source.parent, ref[key][2:]))
        elif not Path(ref[key]).is_absolute(): raise ValueError("ambiguous outer reference path")
    assessment = require_verified_run(ref)
    destination = Path(destination)
    if destination.exists(): raise FileExistsError("import destination exists")
    metadata = parse_json(assessment.snapshot["metadata_raw"])
    destination.mkdir(parents=True)
    (destination / "run.json").write_bytes(assessment.snapshot["metadata_raw"])
    manifest = safe_path(destination, metadata["artifacts_manifest_path"])
    manifest.parent.mkdir(parents=True, exist_ok=True); manifest.write_bytes(assessment.snapshot["manifest_raw"])
    for role, raw in assessment.snapshot["raw"].items():
        target = safe_path(manifest.parent, assessment.snapshot["manifest"]["artifacts"][role]["path"])
        target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(raw)
    copied = {**ref, "path": str(safe_path(destination, metadata["summary_path"])),
              "run_manifest_path": str(destination / "run.json")}
    require_verified_run(copied)
    return copied


def recover_recorded_text_bytes(raw, expected_sha256, policy):
    """Explicit EOL-only reconstruction to an independently recorded raw digest."""
    if sha256(raw) == expected_sha256: return raw
    if policy != "GIT_TEXT_RECORDED_EOL_V1": raise ValueError("raw preimage mismatch; explicit recorded-EOL policy required")
    raw.decode("utf-8")
    lf = raw.replace(b"\r\n", b"\n")
    if b"\r" in lf: raise ValueError("lone CR is outside the recorded text policy")
    matches = {candidate for candidate in (lf, lf.replace(b"\n", b"\r\n")) if sha256(candidate) == expected_sha256}
    if len(matches) != 1: raise ValueError("recorded raw preimage cannot be reconstructed by declared EOL-only policy")
    return matches.pop()


def reconstruct_from_ab_receipt(summary_path, receipt_path, expected_receipt_sha256, run_id, destination, project_id, *, byte_recovery_policy=None):
    """Explicit original-receipt reconstruction into a NEW bundle, never auto-rebinding legacy data."""
    source = Path(summary_path); receipt_raw = Path(receipt_path).read_bytes()
    if sha256(receipt_raw) != expected_receipt_sha256: raise ValueError("trusted original receipt digest mismatch")
    receipt = parse_json(receipt_raw)
    if receipt.get("schema") != "DINO4T_AB_COMPARISON_V1": raise ValueError("unsupported historical receipt")
    proof = deepcopy(receipt); recorded_id = proof.pop("comparison_id", None)
    for item in proof.get("endpoints", []):
        for key in ("summary_path", "config_path", "trace_path"): item.pop(key, None)
    if sha256(json.dumps(proof, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()) != recorded_id:
        raise ValueError("historical receipt identity does not match its original payload")
    endpoint = next((x for x in receipt["endpoints"] if x["run_id"] == run_id), None)
    if endpoint is None: raise ValueError("receipt does not identify requested original run")
    raw = {"summary": source.read_bytes(), "config": source.with_name("config_resolved.json").read_bytes(),
           "trace": source.with_name("trace_last_cycle.csv").read_bytes()}
    recovered = {}
    for role, key in (("summary", "result_sha256"), ("trace", "trace_sha256")):
        original = sha256(raw[role])
        raw[role] = recover_recorded_text_bytes(raw[role], endpoint[key], byte_recovery_policy)
        if original != sha256(raw[role]): recovered[role] = {"input_sha256": original, "restored_sha256": sha256(raw[role]), "policy": byte_recovery_policy}
    summary, config = parse_json(raw["summary"]), parse_json(raw["config"])
    if sha256(raw["summary"]) != endpoint["result_sha256"] or sha256(raw["trace"]) != endpoint.get("trace_sha256") or canonical_hash(config) != endpoint["config_sha256"]:
        raise ValueError("historical bytes do not match the original receipt; no automatic EOL normalization")
    if api.check_summary(summary, config=config): raise ValueError("historical result/config contract invalid")
    root = Path(destination)
    if root.exists(): raise FileExistsError("reconstruction destination already exists")
    artifacts = publish_primary(root / "artifacts", summary, config, raw_primary=raw,
        origin={"kind": "EXPLICIT_LEGACY_RECEIPT_RECONSTRUCTION", "evidence_sha256": expected_receipt_sha256,
                "evidence_run_id": run_id, "evidence_schema": receipt["schema"],
                "byte_reconstruction": recovered,
                "role_authority": {"summary": "ORIGINAL_RAW_RECEIPT_SHA256", "trace": "ORIGINAL_RAW_RECEIPT_SHA256",
                                   "config": "ORIGINAL_CANONICAL_JSON_IDENTITY_AND_CURRENT_PRESERVED_RAW_PREIMAGE"}})
    return publish_desktop_run(root, {"summary": summary, "artifacts": artifacts}, project_id,
                               endpoint.get("variant_id") or "", run_id=run_id)


def export_project_bundle(project, destination):
    """Byte-copy only verified new references; retain manifest identities after relocation."""
    from ..engine_project import save_project
    destination = Path(destination)
    if destination.exists(): raise FileExistsError("bundle export destination already exists")
    assessments = [require_verified_run(ref) for ref in project["run_references"]]
    result = deepcopy(project); result["run_references"] = []
    destination.mkdir(parents=True)
    for i, assessment in enumerate(assessments):
        root = destination / "runs" / str(i)
        primary = assessment.snapshot; metadata_path = root / "run.json"
        metadata_path.parent.mkdir(parents=True)
        metadata_path.write_bytes(primary["metadata_raw"])
        manifest_path = safe_path(root, parse_json(primary["metadata_raw"])["artifacts_manifest_path"])
        manifest_path.parent.mkdir(parents=True, exist_ok=True); manifest_path.write_bytes(primary["manifest_raw"])
        for role, raw in primary["raw"].items():
            target = safe_path(manifest_path.parent, primary["manifest"]["artifacts"][role]["path"])
            target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(raw)
        ref = deepcopy(assessment.reference)
        ref["path"] = "./" + (root / parse_json(primary["metadata_raw"])["summary_path"]).relative_to(destination).as_posix()
        ref["run_manifest_path"] = "./" + metadata_path.relative_to(destination).as_posix()
        result["run_references"].append(ref)
    save_project(destination / "project.dino.json", result)
    return destination / "project.dino.json"
