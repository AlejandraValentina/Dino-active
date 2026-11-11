"""Portable project bundles with hash verification and no legacy promotion."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import tempfile
import shutil
import uuid
import zipfile

BUNDLE_SCHEMA = "DINO_PORTABLE_PROJECT_BUNDLE_V2"
LEGACY_BUNDLE_SCHEMA = "DINO_PORTABLE_PROJECT_BUNDLE_V1"
FAMILIES = {"2T", "4T_native", "4T_0D"}
PROJECT_NAME = "project.json"
MANIFEST_NAME = "manifest.json"
README_NAME = "README.txt"


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _file_sha256(path: Path) -> str:
    return _sha256(path.read_bytes())


def _safe_member(name: str) -> str:
    if not isinstance(name, str) or not name or "\\" in name:
        raise ValueError("ruta de bundle inválida")
    path = PurePosixPath(name)
    if path.is_absolute() or not path.parts or any(':' in part or '\x00' in part for part in path.parts) or ".." in path.parts or path.as_posix() in {
            PROJECT_NAME, MANIFEST_NAME, README_NAME}:
        raise ValueError("ruta de bundle inválida")
    return path.as_posix()


def _project_dict(family: str, project) -> dict:
    if family == "4T_0D":
        return project.to_dict() if hasattr(project, "to_dict") else deepcopy(project)
    return deepcopy(project)


def _legacy_count(family: str, project: dict) -> int:
    if family == "2T":
        return sum(1 for ref in project.get("result_references", [])
                   if "LEGACY" in str(ref.get("classification", "")).upper())
    return 0


def _write_project(family: str, project: dict, project_path, files: list[dict],
                   warnings: list[str], sources: dict[str, Path]) -> None:
    if family in {"2T", "4T_native"}:
        from ..engine_project import validate_project
        validate_project(project)
        key = "result_references" if family == "2T" else "run_references"
        for ref in project.get(key, []):
            for path_key in ("path", "run_manifest_path"):
                if path_key not in ref or not ref[path_key]:
                    continue
                source = Path(ref[path_key])
                if not source.is_file():
                    raise FileNotFoundError(f"No se encontró el artifact referenciado: {source}")
                digest = _file_sha256(source)
                relative = f"artifacts/{digest[:12]}-{source.name}"
                if relative not in sources:
                    files.append({"path": relative, "role": "RESULT" if path_key == "path" else "TRACE",
                                  "sha256": digest, "size": source.stat().st_size})
                sources[relative] = source
                ref[path_key] = "./" + relative
    elif family == "4T_0D":
        from ..four_stroke_project import FourStrokeProject
        FourStrokeProject.from_dict(project)
        if not project.get("curve_references"):
            return
        if project_path is None:
            raise ValueError("El proyecto 4T 0D con referencias de curva requiere una ruta guardada")
        base = Path(project_path).resolve().parent
        for reference in project["curve_references"]:
            relative = _safe_member(reference["series_path"])
            source = base / Path(relative)
            if not source.is_file():
                raise FileNotFoundError(f"No se encontró la traza de curva: {source}")
            digest = _file_sha256(source)
            if relative not in sources:
                files.append({"path": relative, "role": "TRACE", "sha256": digest,
                              "size": source.stat().st_size})
            sources[relative] = source
    else:
        raise ValueError("familia de bundle no admitida")


def write_project_bundle(path, project, *, family: str, project_path=None,
                         created_at=None) -> Path:
    """Write a portable bundle containing the project and referenced artifacts."""
    if family not in FAMILIES:
        raise ValueError("familia de bundle no admitida")
    target = Path(path)
    data = _project_dict(family, project)
    files: list[dict] = []
    warnings: list[str] = []
    sources: dict[str, Path] = {}
    from .portable_artifacts import collect_project
    data,files,payloads,warnings,assessments=collect_project(project,family,project_path)
    project_bytes = (json.dumps(data, sort_keys=True, indent=2, ensure_ascii=False,
                                allow_nan=False) + "\n").encode("utf-8")
    manifest = {
        "schema": BUNDLE_SCHEMA,
        "bundle_id": uuid.uuid4().hex,
        "created_at": created_at or datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "family": family,
        "project_schema": data.get("schema"),
        "project_id": data.get("project_id") or data.get("name"),
        "project_sha256": _sha256(project_bytes),
        "files": sorted(files, key=lambda item: item["path"]),
        "legacy_reference_count": sum(bool(a.get('legacy')) for a in assessments),
        "legacy_policy": "PRESERVE_CLASSIFICATION_NEVER_PROMOTE",
        "warnings": warnings,
        "references": assessments,
        "availability": "PARTIAL" if warnings else "COMPLETE",
    }
    readme = _readme(manifest)
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=target.name + ".", suffix=".tmp", dir=target.parent)
    os.close(fd)
    try:
        with zipfile.ZipFile(tmp_name, "w", zipfile.ZIP_DEFLATED) as bundle:
            bundle.writestr(PROJECT_NAME, project_bytes)
            bundle.writestr(MANIFEST_NAME, (json.dumps(manifest, sort_keys=True, indent=2,
                                                       ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8"))
            bundle.writestr(README_NAME, readme.encode("utf-8"))
            for entry in manifest["files"]:
                bundle.writestr(entry['path'],payloads[entry['path']])
        os.replace(tmp_name, target)
    finally:
        try:
            os.unlink(tmp_name)
        except FileNotFoundError:
            pass
    return target


def _readme(manifest: dict) -> str:
    lines = [
        "Dino Desktop - bundle portable de proyecto",
        f"Bundle: {manifest['bundle_id']}",
        f"Familia: {manifest['family']}",
        f"Proyecto: {manifest['project_id']}",
        f"Política legacy: {manifest['legacy_policy']}",
        "Los hashes SHA-256 del proyecto y de cada artifact se verifican al importar.",
        "",
        "Archivos:",
    ]
    for entry in manifest["files"]:
        lines.append(f"- {entry['path']} [{entry['role']}] {entry['sha256']}")
    lines.append("")
    lines.append("La importación conserva la clasificación original; no promueve "
                 "resultados legacy, parciales o no convergentes.")
    return "\n".join(lines) + "\n"


def inspect_bundle(path) -> tuple[dict, bytes]:
    """Validate a bundle without extracting it."""
    with zipfile.ZipFile(path) as bundle:
        from .portable_artifacts import MAX_BYTES
        listing=bundle.infolist()
        if sum(i.file_size for i in listing)>MAX_BYTES:raise ValueError('El bundle supera el límite de 512 MiB sin comprimir')
        if len({i.filename.casefold() for i in listing})!=len(listing):raise ValueError('El bundle contiene rutas duplicadas o ambiguas')
        names = set(bundle.namelist())
        if MANIFEST_NAME not in names or PROJECT_NAME not in names:
            raise ValueError("el bundle no contiene manifest.json y project.json")
        manifest = json.loads(bundle.read(MANIFEST_NAME).decode("utf-8"))
        if manifest.get("schema") not in {BUNDLE_SCHEMA,LEGACY_BUNDLE_SCHEMA} or manifest.get("family") not in FAMILIES:
            raise ValueError("manifest de bundle no admitido")
        expected = {PROJECT_NAME, MANIFEST_NAME, README_NAME}
        if any(_safe_member(item["path"]) in expected for item in manifest.get("files", [])):
            raise ValueError("el manifest no puede sobrescribir archivos reservados")
        project_raw = bundle.read(PROJECT_NAME)
        if _sha256(project_raw) != manifest.get("project_sha256"):
            raise ValueError("hash del proyecto del bundle no coincide")
        seen = set()
        for entry in manifest.get("files", []):
            relative = _safe_member(entry.get("path"))
            if relative in seen:
                raise ValueError("archivo duplicado en el bundle")
            seen.add(relative)
            if relative not in names:
                raise ValueError(f"falta el archivo declarado: {relative}")
            raw = bundle.read(relative)
            if _sha256(raw) != entry.get("sha256"):
                raise ValueError(f"hash de artifact no coincide: {relative}")
        return manifest, project_raw


def _import_new_directory(path, target) -> dict:
    """Validate, extract and load a portable bundle without promoting legacy results."""
    manifest, _project_raw = inspect_bundle(path)
    source = Path(path)
    if target.exists() and any(target.iterdir()):
        raise FileExistsError(f"La carpeta de importación no está vacía: {target}")
    target.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(source) as bundle:
        with (target / PROJECT_NAME).open("wb") as stream:
            stream.write(bundle.read(PROJECT_NAME))
        for entry in manifest["files"]:
            relative = _safe_member(entry["path"])
            output = target / Path(relative)
            output.parent.mkdir(parents=True, exist_ok=True)
            raw = bundle.read(relative)
            if _sha256(raw) != entry.get("sha256"):
                raise ValueError(f"hash de artifact no coincide: {relative}")
            output.write_bytes(raw)
        (target / MANIFEST_NAME).write_bytes(bundle.read(MANIFEST_NAME))
        if README_NAME in bundle.namelist():
            (target / README_NAME).write_bytes(bundle.read(README_NAME))
    project_file = target / PROJECT_NAME
    if manifest["family"] == "4T_0D":
        from ..four_stroke_project import load_project
    else:
        from ..engine_project import load_project
    project = load_project(project_file)
    availability=manifest.get('availability','UNASSESSED_LEGACY_BUNDLE')
    assessments=[]
    if manifest['family']=='4T_native':
        from .four_stroke_artifacts import assess_run_reference
        for ref in project['run_references']:
            assessment=assess_run_reference(ref)
            assessments.append(dict(run_id=ref['run_id'],integrity=assessment.classification,
                execution=ref['status'],periodicity=ref['periodicity_status'],issues=assessment.issues))
        if any(a['integrity'] not in {'VERIFIED','LEGACY_UNVERIFIED'} for a in assessments):availability='PARTIAL'
    return {"manifest": manifest, "project": project, "project_path": project_file,
            "destination": str(target), "legacy_reference_count": manifest.get("legacy_reference_count", 0),
            'availability':availability,'assessments':assessments}


def import_bundle(path, destination=None) -> dict:
    """Prepare a new import atomically; never write into an existing project."""
    source=Path(path)
    target=Path(destination) if destination is not None else source.with_suffix('')
    if target.exists():raise FileExistsError('Elegí una carpeta nueva para importar; no se sobrescriben originales.')
    inspect_bundle(source)
    target.parent.mkdir(parents=True,exist_ok=True)
    staging=Path(tempfile.mkdtemp(prefix='.dino-import-',dir=target.parent))
    try:
        result=_import_new_directory(source,staging)
        if target.exists():raise FileExistsError('La carpeta de destino apareció durante la importación.')
        os.rename(staging,target)
        # Re-resolve only editable outer references, never primary metadata.
        if result['manifest']['family']=='4T_0D':
            from ..four_stroke_project import load_project
        else:from ..engine_project import load_project
        result.update(project=load_project(target/PROJECT_NAME),project_path=target/PROJECT_NAME,destination=str(target))
        if result['manifest']['family']=='4T_native':
            from .four_stroke_artifacts import assess_run_reference
            result['assessments']=[]
            for ref in result['project']['run_references']:
                assessment=assess_run_reference(ref)
                result['assessments'].append(dict(run_id=ref['run_id'],integrity=assessment.classification,
                    execution=ref['status'],periodicity=ref['periodicity_status'],issues=assessment.issues))
        return result
    finally:
        if staging.exists():
            # Delete only this operation's newly created staging directory.
            assert staging.resolve().parent==target.parent.resolve() and staging.name.startswith('.dino-import-')
            shutil.rmtree(staging)
