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
worker_a=Analysis([str(root/'packaging/worker_entry.py')],datas=[],
    pathex=[str(root)],excludes=['PySide6','shiboken6','pywinauto','comtypes','dev_orchestrator'],noarchive=False)
gui=EXE(PYZ(gui_a.pure),gui_a.scripts,[],exclude_binaries=True,name='MotorSim',
    console=False,debug=False,strip=False,upx=False)
worker=EXE(PYZ(worker_a.pure),worker_a.scripts,[],exclude_binaries=True,name='MotorSimWorker',
    console=True,debug=False,strip=False,upx=False)
COLLECT(gui,worker,gui_a.binaries,gui_a.datas,worker_a.binaries,worker_a.datas,
    strip=False,upx=False,name='MotorSim')
