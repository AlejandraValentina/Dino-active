"""Construcción onedir identificada; sin borrar productos ni datos anteriores."""
import argparse
from datetime import datetime,timezone
import hashlib
from importlib import metadata
import json
import os
from pathlib import Path
import platform
import shutil
import struct
import subprocess
import sys
import uuid
import zipfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from motorsim.runtime import APP_VERSION
from motorsim.examples import PROJECT_FILES, example_file_project
from motorsim.storage import load_project
from motorsim.project_case import execution_errors
from motorsim.reference_results import MODEL_VERSION,FOUR_MODEL_VERSION


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--trial',action='store_true',help='Prueba de empaquetado con árbol no limpio, identificada como tal.')
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
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    name=f'MotorSim-{APP_VERSION}-windows-x64-{commit[:8]}'+('-trial-'+stamp if args.trial else '')
    destination=ROOT/'dist'/name
    if destination.exists() or Path(str(destination)+'.zip').exists():raise RuntimeError('Destino existente; no se sobrescribe.')
    for name in ('LGPL-3.0-only.txt','GPL-3.0-only.txt','SOURCES.txt'):
        if not (ROOT/'packaging/licenses'/name).is_file():raise RuntimeError('Falta aviso requerido: '+name)
    work=ROOT/'build/windows'/uuid.uuid4().hex;generated=work/'inputs';generated.mkdir(parents=True)
    info=dict(app_version=APP_VERSION,source_commit=commit,source_dirty=dirty,trial=args.trial,
        built_utc=stamp,python=sys.version,platform=platform.platform(),architecture=platform.machine(),
        project_format=6,result_formats=dict(two_stroke=[1,2,3],four_stroke=4),
        models=dict(two_stroke=MODEL_VERSION,four_stroke=FOUR_MODEL_VERSION),dependencies=versions)
    (generated/'build.json').write_text(json.dumps(info,ensure_ascii=False,indent=2),encoding='utf-8')
    env=os.environ.copy();env['MOTORSIM_BUILD_INPUTS']=str(generated)
    subprocess.run([sys.executable,'-m','PyInstaller','--noconfirm','--distpath',str(destination),
        '--workpath',str(work/'pyinstaller'),str(ROOT/'packaging/MotorSim.spec')],cwd=ROOT,env=env,check=True)
    bundle=destination/'MotorSim'
    shutil.copy2(generated/'build.json',bundle/'build.json')
    shutil.copy2(ROOT/'motorsim/ayuda.txt',bundle/'LEEME.txt')
    shutil.copy2(ROOT/'packaging/AVISOS.txt',bundle/'AVISOS.txt')
    examples=bundle/'Ejemplos';examples.mkdir()
    for key,filename in PROJECT_FILES.items():
        source=ROOT/'examples/projects'/filename
        project=load_project(source)
        if project!=example_file_project(key):raise RuntimeError('Regenerá el ejemplo canónico: '+filename)
        if execution_errors(project):raise RuntimeError('Ejemplo incompatible: '+str(execution_errors(project)))
        shutil.copy2(source,examples/filename)
    licenses=bundle/'Licencias';shutil.copytree(ROOT/'packaging/licenses',licenses/'Qt')
    shutil.copy2(Path(sys.base_prefix)/'LICENSE.txt',licenses/'Python-LICENSE.txt')
    for name in ('PySide6','PySide6_Essentials','PySide6_Addons','shiboken6','pyinstaller'):
        dist=metadata.distribution(name);out=licenses/name;out.mkdir()
        for file in dist.files or []:
            if '.dist-info/' in str(file) and ('license' in str(file).lower() or Path(file).name in ('METADATA','COPYING.txt')):
                source=Path(dist.locate_file(file))
                if source.is_file():shutil.copy2(source,out/source.name)
    (bundle/'BUILD-DEPENDENCIES.txt').write_text('\n'.join(f'{k}=={v}' for k,v in versions.items())+'\n',encoding='utf-8')
    archive=Path(str(destination)+'.zip')
    if any('dev_orchestrator' in part.lower() for file in bundle.rglob('*') for part in file.relative_to(bundle).parts):
        raise RuntimeError('Infraestructura de desarrollo detectada en el paquete; no se genera ZIP.')
    with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED,compresslevel=6) as zipped:
        for file in sorted(bundle.rglob('*')):
            if file.is_file():zipped.write(file,file.relative_to(destination))
    digest=hashlib.sha256(archive.read_bytes()).hexdigest()
    archive.with_suffix('.zip.sha256').write_text(digest+'  '+archive.name+'\n',encoding='ascii')
    print(json.dumps(dict(folder=str(bundle),zip=str(archive),sha256=digest,
        zip_bytes=archive.stat().st_size,folder_bytes=sum(p.stat().st_size for p in bundle.rglob('*') if p.is_file()),build=info),indent=2))

if __name__=='__main__':
    try:main()
    except (OSError,ValueError,RuntimeError,subprocess.CalledProcessError) as exc:
        print(f'No se completó la construcción: {exc}',file=sys.stderr);raise SystemExit(1)
