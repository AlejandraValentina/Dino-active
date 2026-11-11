"""Application bundle closure. Preserve preimages; never promote evidence."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

SCHEMA='DINO_PORTABLE_PROJECT_BUNDLE_V2'
MAX_BYTES=512*1024**2


def collect_project(project, family, project_path=None):
    from .project_bundles import _safe_member
    data=deepcopy(project.to_dict() if hasattr(project,'to_dict') else project)
    base=Path(project_path).resolve().parent if project_path is not None else None
    payloads={};entries=[];warnings=[];assessments=[]

    def resolve(value):
        p=Path(value)
        return (base/p).resolve() if not p.is_absolute() and base is not None else p.resolve()

    def add(source, relative, role='ARTIFACT'):
        relative=_safe_member(relative)
        if not source.is_file():
            warnings.append(f'Archivo no disponible: {relative}')
            return False
        if source.is_symlink():raise ValueError('No se exportan enlaces simbólicos de artifacts')
        size=source.stat().st_size
        if size>MAX_BYTES or sum(len(v) for v in payloads.values())+size>MAX_BYTES:
            raise ValueError('El bundle supera 512 MiB sin comprimir; exportá una selección menor.')
        raw=source.read_bytes()
        if relative in payloads:
            if payloads[relative]!=raw:raise ValueError('Colisión de rutas de artifacts')
            return True
        if relative.casefold() in {p.casefold() for p in payloads}:raise ValueError('Rutas de artifacts ambiguas por mayúsculas')
        payloads[relative]=raw
        entries.append(dict(path=relative,role=role,sha256=hashlib.sha256(raw).hexdigest(),size=len(raw)))
        return True

    def tree(source, prefix):
        for path in sorted(source.rglob('*')):
            if path.is_symlink():raise ValueError('No se exportan enlaces simbólicos de artifacts')
            if path.is_file():add(path,prefix+'/'+path.relative_to(source).as_posix())

    if family=='4T_native':
        from ..engine_project import validate_project
        from .four_stroke_artifacts import assess_run_reference,REFERENCE_SCHEMA
        from ..dino4t.artifacts import safe_path
        validate_project(data)
        for index,ref in enumerate(data['run_references']):
            normalized=deepcopy(ref)
            for key in ('path','run_manifest_path'):
                if key in normalized:normalized[key]=str(resolve(normalized[key]))
            before=assess_run_reference(normalized)
            prefix=f'artifacts/native/{index:04d}-{hashlib.sha256(ref["run_id"].encode()).hexdigest()[:12]}'
            start=len(warnings)
            source=resolve(ref['path'])
            versioned=ref.get('schema')==REFERENCE_SCHEMA
            meta_source=resolve(ref['run_manifest_path']) if versioned else source.parent.parent/'run.json'
            run_root=meta_source.parent
            def relative(source_path):
                if not source_path.resolve().is_relative_to(run_root.resolve()):
                    raise ValueError('Una dependencia nativa escapa de su raíz de corrida')
                return prefix+'/'+source_path.resolve().relative_to(run_root.resolve()).as_posix()
            summary_target=relative(source)
            add(source,summary_target,'SUMMARY')
            add(meta_source,prefix+'/'+meta_source.name,'RUN_METADATA')
            ref['path']='./'+summary_target
            if versioned:
                ref['run_manifest_path']='./'+prefix+'/'+meta_source.name
                try:
                    meta=json.loads(meta_source.read_bytes())
                    manifest_path=safe_path(run_root,meta['artifacts_manifest_path'])
                    if add(manifest_path,relative(manifest_path),'PRIMARY_MANIFEST'):
                        manifest=json.loads(manifest_path.read_bytes())
                        for role,entry in manifest['artifacts'].items():
                            child=safe_path(manifest_path.parent,entry['path'])
                            add(child,relative(child),role.upper())
                except (OSError,ValueError,KeyError,TypeError) as exc:
                    warnings.append(f'Corrida {index+1}: cadena incompleta ({type(exc).__name__})')
            else:
                # Legacy metadata remain original. A local companion resolver
                # supports relocation, always with LEGACY_UNVERIFIED status.
                try:
                    meta=json.loads(meta_source.read_bytes())
                except (OSError,ValueError):meta={}
                config=source.parent/'config_resolved.json'
                if not config.is_file() and meta.get('config_path'):config=resolve(meta['config_path'])
                add(config,prefix+'/'+source.parent.name+'/config_resolved.json','LEGACY_CONFIG')
                trace=source.parent/'trace_last_cycle.csv'
                if trace.is_file():add(trace,prefix+'/'+source.parent.name+'/trace_last_cycle.csv','LEGACY_TRACE')
            if not before.verified and not before.classification.startswith('LEGACY_'):
                warnings.append(f'Corrida {index+1}: {before.classification}; no se declara integridad verificada.')
            assessments.append(dict(index=index,run_id=ref['run_id'],integrity=before.classification,
                execution=ref['status'],periodicity=ref['periodicity_status'],
                legacy=not versioned,availability='COMPLETE' if len(warnings)==start else 'PARTIAL',issues=before.issues))
    elif family=='4T_0D':
        from ..four_stroke_project import FourStrokeProject
        FourStrokeProject.from_dict(data)
        for index,ref in enumerate(data.get('curve_references',[])):
            if base is None:raise ValueError('Guardá el proyecto 4T 0D antes de exportar sus curvas')
            relative=_safe_member(ref['series_path']);source=base/relative
            if source.is_file():tree(source.parent,Path(relative).parent.as_posix())
            else:warnings.append(f'Curva no disponible: {relative}')
            assessments.append(dict(index=index,legacy=False,execution=ref['status'],
                integrity='HASHES_PRESERVED',availability='COMPLETE' if source.is_file() else 'PARTIAL'))
    elif family=='2T':
        from ..engine_project import validate_project
        validate_project(data)
        for collection in ('result_references','measurement_references','study_references'):
            for index,ref in enumerate(data.get(collection,[])):
                source=resolve(ref['path'])
                prefix=f'artifacts/{collection}/{index:04d}'
                start=len(warnings)
                doc={}
                if source.is_file():
                    try:doc=json.loads(source.read_bytes())
                    except (ValueError,OSError):pass
                # Recognized run/dataset directories use relative dependencies.
                # Unknown historical reports are preserved without upgrading them.
                if source.is_file() and (doc.get('schema') in {'DINO_ENGINEERING_RUN_V1','DINO_EXPLORATORY_RUN_V1'} or collection=='measurement_references'):
                    tree(source.parent,prefix)
                else:add(source,prefix+'/'+source.name,'RESULT')
                ref['path']='./'+prefix+'/'+source.name
                if collection=='study_references':warnings.append('Estudio conservado: dependencias externas requieren revisión explícita.')
                assessments.append(dict(index=index,collection=collection,
                    integrity=ref.get('classification','PRESERVED_NOT_PROMOTED'),
                    legacy='LEGACY' in ref.get('classification',''),
                    availability='COMPLETE' if len(warnings)==start else 'PARTIAL'))
    else:raise ValueError('Familia de bundle no admitida')
    return data,entries,payloads,warnings,assessments
