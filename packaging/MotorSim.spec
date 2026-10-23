from pathlib import Path
import os

root=Path(SPECPATH).parent
generated=Path(os.environ['MOTORSIM_BUILD_INPUTS'])
common=dict(pathex=[str(root)],excludes=['PySide6.QtNetwork','PySide6.QtQml',
    'PySide6.QtQuick','PySide6.QtWebEngineCore','PySide6.QtTest','pywinauto','comtypes','pytest','dev_orchestrator'],
    noarchive=False)
gui_a=Analysis([str(root/'packaging/gui_entry.py')],datas=[
    (str(root/'motorsim/theme.qss'),'motorsim'),
    (str(root/'motorsim/ayuda.txt'),'motorsim'),
    (str(generated/'build.json'),'motorsim')],**common)
# Solo plugins de la interfaz Widgets usada, sin QML, formatos ni plataformas ajenas.
gui_a.binaries=[item for item in gui_a.binaries if '/plugins/' not in item[0].replace('\\','/')
    or Path(item[0]).name.lower() in ('qwindows.dll','qmodernwindowsstyle.dll')]
gui_a.datas=[item for item in gui_a.datas if '/translations/' not in item[0].replace('\\','/')
    or Path(item[0]).name=='qtbase_es.qm']
dino_a=Analysis([str(root/'packaging/dino_desktop_entry.py')],
    # Source-backed package imports preserve __file__, inspect and producer
    # checkpoint fingerprints. The same source bytes are shipped and executed.
    module_collection_mode={'motorsim':'py'}, datas=[
    (str(generated/'build.json'),'motorsim'),
    (str(root/'results/2t-commercial-core-20261002/fixtures/v1-prime-mesh/fixture_a_prime-mesh-0.json'),
     'results/2t-commercial-core-20261002/fixtures/v1-prime-mesh'),
    # Read-only provenance auditing uses inspect.getsource() for exact producer
    # and solver dependency fingerprints. PyInstaller stores bytecode in PYZ;
    # retain the matching sources as data so frozen replay can perform the same
    # checks instead of failing closed merely because source files are absent.
    *[(str(source),str(source.parent.relative_to(root)).replace('\\','/'))
      for source in sorted((root/'motorsim').rglob('*.py'))]],**common)
dino_a.binaries=[item for item in dino_a.binaries if '/plugins/' not in item[0].replace('\\','/')
    or Path(item[0]).name.lower() in ('qwindows.dll','qmodernwindowsstyle.dll')]
dino_a.datas=[item for item in dino_a.datas if '/translations/' not in item[0].replace('\\','/')
    or Path(item[0]).name=='qtbase_es.qm']
worker_a=Analysis([str(root/'packaging/worker_entry.py')],datas=[],
    pathex=[str(root)],excludes=['PySide6','shiboken6','pywinauto','comtypes','dev_orchestrator'],noarchive=False)
gui=EXE(PYZ(gui_a.pure),gui_a.scripts,[],exclude_binaries=True,name='MotorSim',
    console=False,debug=False,strip=False,upx=False)
worker=EXE(PYZ(worker_a.pure),worker_a.scripts,[],exclude_binaries=True,name='MotorSimWorker',
    console=True,debug=False,strip=False,upx=False)
dino=EXE(PYZ(dino_a.pure),dino_a.scripts,[],exclude_binaries=True,name='Dino2T',
    console=False,debug=False,strip=False,upx=False)
COLLECT(gui,dino,worker,gui_a.binaries,gui_a.datas,dino_a.binaries,dino_a.datas,worker_a.binaries,worker_a.datas,
    strip=False,upx=False,name='MotorSim')
