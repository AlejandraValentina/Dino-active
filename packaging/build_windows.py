"""Construcción onedir identificada; sin borrar productos ni datos anteriores."""
import argparse
from datetime import datetime,timezone
import hashlib
from importlib import metadata
import json
import os
from pathlib import Path
import platform
import struct
import subprocess
import sys
import tempfile
import uuid
import zipfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from motorsim.runtime import APP_VERSION
from motorsim.examples import PROJECT_FILES, example_file_project
from motorsim.storage import load_project
from motorsim.engine_project import load_project as load_engine_project
from motorsim.engine_configuration import implementation_source_hashes
from motorsim.project_case import execution_errors
from motorsim.source_provenance import capture_source_identity
from scripts.agents.storage_preflight import (
    GIB, check_storage_requirements, default_artifact_root,
)
from build_provenance import (
    ensure_packaged_inputs_clean, input_manifest, unrelated_dirty_fingerprint,
    copy_bound_file, copy_consumed_inputs, copy_repository_file,
    package_model_metadata, verify_bundle_data, verify_input_snapshot,
    verify_copied_files,
)
from bundle_inputs import ConsumedInput, POST_BUILD_FILES, directory_inputs


def periodic_example_plan(path):
    """Enumerate all optional bytes before building; later copies use this plan."""
    if path is None:
        return None, []
    path=Path(path).resolve()
    project=json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(project,dict) or not isinstance(project.get('result_references'),list):
        raise ValueError('El proyecto periódico no declara una lista de referencias.')
    consumed=[ConsumedInput(path,'periodic-example/project.json')]
    refs=[];folders=set()
    for ref in project['result_references']:
        if not isinstance(ref,dict) or not isinstance(ref.get('path'),str):
            raise ValueError('Referencia periódica sin ruta válida.')
        source=Path(ref['path'])
        if not source.is_absolute():source=path.parent/source
        source=source.resolve()
        result=json.loads(source.read_text(encoding='utf-8'))
        if not isinstance(result,dict) or not isinstance(result.get('periodicity',''),str):
            raise ValueError('Resultado periódico con clasificación inválida.')
        if not result.get('periodicity','').startswith('PERIOD_1'):continue
        if hashlib.sha256(source.read_bytes()).hexdigest()!=ref['artifact_sha256']:
            raise RuntimeError('Referencia periódica alterada')
        folder=source.parent.name
        if folder.casefold() in folders:
            raise RuntimeError('Dos referencias periódicas colisionan en el directorio portable: '+folder)
        folders.add(folder.casefold())
        consumed.extend(directory_inputs(source.parent,'periodic-example/data/'+folder,
                                         'Ejemplos/Datos/'+folder))
        refs.append(dict(ref,path='./Datos/'+folder+'/'+source.name))
    if len(refs)!=6:raise RuntimeError('Se requieren seis puntos periódicos existentes')
    project['result_references']=refs
    return project,consumed


def license_input_plan():
    """External licenses are explicit raw inputs, never attributed to Git HEAD."""
    values=[ConsumedInput(Path(sys.base_prefix)/'LICENSE.txt','licenses/python/LICENSE.txt',
                          'Licencias/Python-LICENSE.txt')]
    for name in ('PySide6','PySide6_Essentials','PySide6_Addons','shiboken6','pyinstaller'):
        dist=metadata.distribution(name)
        for file in dist.files or []:
            if '.dist-info/' in str(file) and ('license' in str(file).lower() or Path(file).name in ('METADATA','COPYING.txt')):
                source=Path(dist.locate_file(file))
                if source.is_file():
                    values.append(ConsumedInput(source,'licenses/'+name+'/'+str(file).replace('\\','/'),
                                                'Licencias/'+name+'/'+source.name))
    return values


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--trial',action='store_true',help='Prueba de empaquetado con árbol no limpio, identificada como tal.')
    parser.add_argument('--output-root',type=Path,help='Directorio externo de distribución (por defecto DINO_ARTIFACT_ROOT/Windows o ~/Dino-artifacts/Windows).')
    parser.add_argument('--work-root',type=Path,help='Directorio temporal de PyInstaller (por defecto DINO_BUILD_WORK_ROOT o el temporal del sistema).')
    parser.add_argument('--periodic-example',type=Path,help='Proyecto existente con seis referencias periódicas; copia sin recalcular.')
    args=parser.parse_args()
    if os.name!='nt' or struct.calcsize('P')!=8 or sys.version_info[:3]!=(3,11,0):
        raise RuntimeError('Se requiere Windows x64 y Python 3.11.0 para esta receta fijada.')
    if Path(sys.prefix).resolve()!=(ROOT/'.venv-build').resolve():
        raise RuntimeError('Usá .venv-build; no se altera el entorno operativo.')
    versions={}
    for line in (ROOT/'packaging/requirements-build.txt').read_text(encoding='utf-8').splitlines():
        if not line or line.startswith('#'):continue
        name,version=line.split('==');actual=metadata.version(name)
        if actual!=version:raise RuntimeError(f'{name}: requerido {version}, disponible {actual}')
        versions[name]=actual
    def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT,text=True).strip()
    commit=git('rev-parse','HEAD');dirty=bool(git('status','--porcelain'))
    if dirty and not args.trial:raise RuntimeError('El paquete final requiere Git limpio; registrá primero código y receta.')
    # A trial may coexist with unrelated local work, but every byte consumed by
    # PyInstaller or copied into the product must match the named commit.
    periodic_project,periodic_inputs=periodic_example_plan(args.periodic_example)
    consumed=[*periodic_inputs,*license_input_plan()]
    ensure_packaged_inputs_clean(ROOT,consumed)
    manifest=input_manifest(ROOT,consumed)
    dirty_summary=unrelated_dirty_fingerprint(ROOT,consumed)
    source_identity=capture_source_identity(ROOT)
    if source_identity['status']!='COMPLETE' or source_identity['dirty'] is not False:
        raise RuntimeError('La identidad completa de las fuentes no es limpia/verificable.')
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    name=f'MotorSim-{APP_VERSION}-windows-x64-{commit[:8]}'+('-trial-'+stamp if args.trial else '')
    output_root = args.output_root or (default_artifact_root()/'Windows')
    destination=output_root/name
    if destination.exists() or Path(str(destination)+'.zip').exists():raise RuntimeError('Destino existente; no se sobrescribe.')
    work_base = args.work_root or Path(os.environ.get(
        'DINO_BUILD_WORK_ROOT', str(Path(tempfile.gettempdir())/'Dino-build-work'))).expanduser()
    storage_report=check_storage_requirements(
        [(output_root, int(1.5*GIB)), (work_base, GIB)])
    print(json.dumps(dict(storage_preflight=storage_report),ensure_ascii=False))
    for name in ('LGPL-3.0-only.txt','GPL-3.0-only.txt','SOURCES.txt'):
        if not (ROOT/'packaging/licenses'/name).is_file():raise RuntimeError('Falta aviso requerido: '+name)
    work=work_base/uuid.uuid4().hex;generated=work/'inputs';generated.mkdir(parents=True)
    info=dict(app_version=APP_VERSION,source_commit=commit,trial=args.trial,
        built_utc=stamp,python=sys.version,platform=platform.platform(),architecture=platform.machine(),
        project_format=6,desktop_project_schemas=dict(two_stroke="MOTORSIM_ENGINE_PROJECT_V3",
            four_stroke="DINO_DESKTOP_ENGINE_PROJECT_4T_V1"),
        result_formats=dict(two_stroke=[1,2,3],four_stroke="DINO4T_OPERATING_POINT_RESULT_V1"),
        engine_apis=dict(two_stroke="DINO_ENGINEERING_RUN_V1",four_stroke="DINO4T_API_V1"),
        **package_model_metadata(ROOT),dependencies=versions,
        source_identity=source_identity,
        workflow_source_hashes=implementation_source_hashes(),
        packaged_inputs_clean=True,packaged_input_count=len(manifest['files'])+len(manifest['consumed_files']),
        packaged_inputs_clean_scope='Declared repository inputs; explicit byte inputs are not Git-bound',
        packaged_input_manifest_schema=manifest['schema'],
        packaged_input_byte_policy=manifest['byte_policy'],
        packaged_input_manifest_sha256=manifest['sha256'],
        packaged_inputs=manifest['files'],explicit_consumed_inputs=manifest['consumed_files'],**dirty_summary)
    (generated/'build.json').write_text(json.dumps(info,ensure_ascii=False,indent=2),encoding='utf-8')
    generated_sha256=hashlib.sha256((generated/'build.json').read_bytes()).hexdigest()
    env=os.environ.copy();env['MOTORSIM_BUILD_INPUTS']=str(generated)
    subprocess.run([sys.executable,'-m','PyInstaller','--noconfirm','--distpath',str(destination),
        '--workpath',str(work/'pyinstaller'),str(ROOT/'packaging/MotorSim.spec')],cwd=ROOT,env=env,check=True)
    bundle=destination/'MotorSim'
    copied=[copy_bound_file(generated/'build.json',bundle/'build.json',generated_sha256)]
    for relative,target in POST_BUILD_FILES:
        copied.append(copy_repository_file(ROOT,relative,bundle/target,manifest))
    examples=bundle/'Ejemplos';examples.mkdir()
    for key,filename in PROJECT_FILES.items():
        source=ROOT/'examples/projects'/filename
        project=load_project(source)
        if project!=example_file_project(key):raise RuntimeError('Regenerá el ejemplo canónico: '+filename)
        if execution_errors(project):raise RuntimeError('Ejemplo incompatible: '+str(execution_errors(project)))
        copied.append(copy_repository_file(ROOT,source.relative_to(ROOT).as_posix(),examples/filename,manifest))
    desktop_example=ROOT/'examples/projects/dino-2t-starter.dino2t.json'
    load_engine_project(desktop_example)
    copied.append(copy_repository_file(ROOT,desktop_example.relative_to(ROOT).as_posix(),examples/'desktop-dino-2t-starter.dino2t.json',manifest))
    exhaust_example=ROOT/'examples/projects/dino-2t-exhaust-comparison.dino2t.json'
    load_engine_project(exhaust_example)
    copied.append(copy_repository_file(ROOT,exhaust_example.relative_to(ROOT).as_posix(),examples/'desktop-dino-2t-exhaust-comparison.dino2t.json',manifest))
    copied.extend(copy_consumed_inputs(bundle,consumed,manifest))
    if periodic_project is not None:
        portable=examples/'Curvas-periodicas-125cc.dino.json'
        portable.write_text(json.dumps(periodic_project,ensure_ascii=False,indent=2),encoding='utf-8')
        load_engine_project(portable)
        copied.append({'path':str(portable),'sha256':hashlib.sha256(portable.read_bytes()).hexdigest()})
        copied.append(copy_repository_file(ROOT,'packaging/INICIO-DINO.txt',bundle/'INICIO-DINO.txt',manifest))
    licenses=bundle/'Licencias'
    for source in (ROOT/'packaging/licenses').rglob('*'):
        if source.is_file():
            copied.append(copy_repository_file(ROOT,source.relative_to(ROOT).as_posix(),
                                 licenses/'Qt'/source.relative_to(ROOT/'packaging/licenses'),manifest))
    dependency_file=bundle/'BUILD-DEPENDENCIES.txt'
    dependency_file.write_text('\n'.join(f'{k}=={v}' for k,v in versions.items())+'\n',encoding='utf-8')
    copied.append({'path':str(dependency_file),'sha256':hashlib.sha256(dependency_file.read_bytes()).hexdigest()})
    verify_bundle_data(ROOT,generated,bundle,manifest,generated_sha256)
    verify_copied_files(copied)
    verify_input_snapshot(ROOT,manifest,consumed)
    archive=Path(str(destination)+'.zip')
    if any('dev_orchestrator' in part.lower() for file in bundle.rglob('*') for part in file.relative_to(bundle).parts):
        raise RuntimeError('Infraestructura de desarrollo detectada en el paquete; no se genera ZIP.')
    with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED,compresslevel=6) as zipped:
        for file in sorted(bundle.rglob('*')):
            if file.is_file():zipped.write(file,file.relative_to(destination))
    digest=hashlib.sha256(archive.read_bytes()).hexdigest()
    archive.with_suffix('.zip.sha256').write_text(digest+'  '+archive.name+'\n',encoding='ascii')
    print(json.dumps(dict(folder=str(bundle),zip=str(archive),sha256=digest,
        zip_bytes=archive.stat().st_size,folder_bytes=sum(p.stat().st_size for p in bundle.rglob('*') if p.is_file()),
        build_metadata_sha256=generated_sha256,build=info),indent=2))

if __name__=='__main__':
    try:main()
    except (OSError,ValueError,RuntimeError,subprocess.CalledProcessError) as exc:
        print(f'No se completó la construcción: {exc}',file=sys.stderr);raise SystemExit(1)
