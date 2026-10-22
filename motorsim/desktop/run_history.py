"""Read-only index of local exploratory run manifests and project references."""
from __future__ import annotations

import json
from datetime import datetime,timezone
from pathlib import Path


def _entry(folder: Path, *, artifact_root: Path, project_id: str, referenced=False):
    manifest_path=folder/"run.json" if folder.is_dir() else folder
    if manifest_path.name!="run.json":manifest_path=manifest_path.parent/"run.json"
    run_dir=manifest_path.parent
    base={"project_id":project_id,"run_id":run_dir.name,"variant":"No informado","rpm":None,
          "updated_at":None,"classification":None,"periodicity":"NOT_REPORTED","audit":"NOT_REPORTED",
          "conservation":"NOT_REPORTED","artifact_root":str(artifact_root),"run_directory":str(run_dir),
          "manifest_path":str(manifest_path),"result_path":str(run_dir/"result.json"),
          "checkpoint_path":str(run_dir/"checkpoint.json"),"identity_sha256":None,
          "configuration_sha256":None,"result_sha256":None,"checkpoint_sha256":None,
          "status":"MANIFEST_MISSING","resumable":False,"referenced":referenced,"details":{}}
    try:
        manifest=json.loads(manifest_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        if (run_dir/"result.json").exists() or (run_dir/"checkpoint.json").exists():
            try:base["updated_at"]=datetime.fromtimestamp(run_dir.stat().st_mtime,timezone.utc).isoformat()
            except OSError:pass
            base["status"]="INCOMPLETE_METADATA"
        return base
    except (OSError,ValueError) as exc:
        base["status"]="MANIFEST_UNREADABLE";base["details"]={"message":str(exc)};return base
    if not isinstance(manifest,dict):
        base["status"]="MANIFEST_INVALID";return base
    bindings=manifest.get("bindings") if isinstance(manifest.get("bindings"),dict) else {}
    preflight=manifest.get("preflight") if isinstance(manifest.get("preflight"),dict) else {}
    # Some existing run manifests intentionally contain only summary/provenance;
    # their result.json carries the original preflight and final periodicity.
    # Read only this metadata for display and leave the independent importer to
    # verify hashes, primaries, and scientific evidence when a run is opened.
    result_path=run_dir/"result.json"
    result_doc={}
    needs_result_metadata=(preflight.get("rpm") is None or manifest.get("periodicity") is None
                           or manifest.get("status") is None or manifest.get("classification") is None
                           or manifest.get("elapsed_seconds") is None
                           or preflight.get("total_finite_volume_cells") is None)
    if needs_result_metadata and result_path.is_file():
        try:
            candidate=json.loads(result_path.read_text(encoding="utf-8"))
            if isinstance(candidate,dict):result_doc=candidate
        except (OSError,ValueError):
            pass
    result_preflight=result_doc.get("preflight") if isinstance(result_doc.get("preflight"),dict) else {}
    if preflight.get("rpm") is None and result_preflight:
        preflight=result_preflight
    cycles=manifest.get("cycles") if isinstance(manifest.get("cycles"),list) else []
    audits=[c.get("audit",{}) for c in cycles if isinstance(c,dict)]
    audit_status="PASS" if audits and all(a.get("status")=="PASS" for a in audits) else ("FAIL" if any(a.get("status")=="FAIL" for a in audits) else "NOT_REPORTED")
    conservation=[c.get("conservation") for c in cycles if isinstance(c,dict) and isinstance(c.get("conservation"),dict)]
    try:updated=datetime.fromtimestamp(manifest_path.stat().st_mtime,timezone.utc).isoformat()
    except OSError:updated=None
    checkpoint_name=manifest.get("checkpoint_artifact","checkpoint.json")
    checkpoint=(run_dir/checkpoint_name if isinstance(checkpoint_name,str) and Path(checkpoint_name).name==checkpoint_name else run_dir/"__invalid_checkpoint_path__")
    if manifest.get("schema")=="DINO_ENGINEERING_RUN_V1" and isinstance(checkpoint_name,str):
        candidate=(run_dir/checkpoint_name).resolve()
        if candidate.is_relative_to(run_dir.resolve()):checkpoint=candidate
    result=result_path
    periodicity=manifest.get("periodicity")
    if manifest.get("schema")=="DINO_ENGINEERING_RUN_V1" and periodicity=="NOT_EVALUATED" and len(cycles)>=2:
        periodicity="NOT_CONVERGED"
    if periodicity is None:periodicity=result_doc.get("periodicity")
    if periodicity is None and isinstance(result_doc.get("cycles"),list) and result_doc["cycles"]:
        periodicity=result_doc["cycles"][-1].get("periodicity")
    base.update({
      "run_id":manifest.get("run_id",run_dir.name),"variant":bindings.get("variant_label","No informado"),
      "rpm":preflight.get("rpm"),"updated_at":updated,
      "classification":manifest.get("classification") or result_doc.get("classification"),
      "periodicity":periodicity or "NOT_REPORTED",
      "audit":audit_status,"audit_recomputed":bool(audits) and all(a.get("recomputed") is True for a in audits),
      "conservation":"REPORTED" if conservation else "NOT_REPORTED","conservation_cycles":len(conservation),
      "identity_sha256":bindings.get("identity_sha256"),"configuration_sha256":bindings.get("configuration_sha256"),
      "result_sha256":manifest.get("result_sha256"),"checkpoint_sha256":manifest.get("checkpoint_sha256"),
      "status":manifest.get("status") or result_doc.get("status","STATUS_NOT_REPORTED"),
      "resumable":manifest.get("status")=="INTERRUPTED_CHECKPOINTED" and checkpoint.is_file()
                  and bool(bindings.get("identity_sha256")) and preflight.get("rpm") is not None,
      "result_path":str(result) if result.is_file() else None,
      "checkpoint_path":str(checkpoint) if checkpoint.is_file() else None,
      "artifact_root":str(artifact_root),"details":{"cycles_completed":manifest.get("cycles_completed"),
        "cycles_requested":preflight.get("max_cycles"),"elapsed_seconds":manifest.get("elapsed_seconds") or result_doc.get("elapsed_seconds"),
        "total_finite_volume_cells":preflight.get("total_finite_volume_cells") or result_preflight.get("total_finite_volume_cells"),"conservation":conservation,
        "source_hashes":bindings.get("source_hashes",{})}})
    return base


def list_project_runs(project: dict, artifact_root: str|Path) -> list[dict]:
    """Read only run.json/result references; primaries are untouched."""
    root=Path(artifact_root).expanduser();project_id=project["project_id"]
    candidates=[]
    local=root/"exploratory-workflow-v1"/project_id
    if local.is_dir():candidates.extend((path,root,False) for path in sorted(local.iterdir()) if path.is_dir())
    for ref in project.get("result_references",[]):
        if not isinstance(ref,dict) or not isinstance(ref.get("path"),str):
            continue
        target=Path(ref["path"]).expanduser()
        if not target.is_absolute():target=root/target
        folder=target if target.is_dir() else target.parent
        detected_root=root
        try:
            parts=folder.parts;index=parts.index("exploratory-workflow-v1")
            detected_root=Path(*parts[:index])
        except ValueError:pass
        candidates.append((folder,detected_root,True))
    entries=[];seen=set()
    for path,entry_root,referenced in candidates:
        manifest=path/"run.json" if path.is_dir() else path
        key=str(manifest.resolve()).casefold()
        if key in seen:continue
        seen.add(key);entries.append(_entry(path,artifact_root=entry_root,project_id=project_id,referenced=referenced))
    entries.sort(key=lambda row:(row.get("updated_at") or "",row["run_id"]),reverse=True)
    return entries
