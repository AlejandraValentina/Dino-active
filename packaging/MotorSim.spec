from pathlib import Path
import os
import sys

root=Path(SPECPATH).parent
generated=Path(os.environ['MOTORSIM_BUILD_INPUTS'])
sys.path.insert(0,str(root))
sys.path.insert(0,str(root/'packaging'))
from bundle_inputs import ENTRY_POINTS, bundle_data_inputs

def declared_datas(target):
    return [(str(item.source),item.destination)
            for item in bundle_data_inputs(root,target,generated)]
common=dict(pathex=[str(root)],excludes=['PySide6.QtNetwork','PySide6.QtQml',
    'PySide6.QtQuick','PySide6.QtWebEngineCore','PySide6.QtTest','pywinauto','comtypes','pytest','dev_orchestrator'],
    noarchive=False)
gui_a=Analysis([str(root/ENTRY_POINTS['gui'])],datas=declared_datas('gui'),**common)
# Solo plugins de la interfaz Widgets usada, sin QML, formatos ni plataformas ajenas.
gui_a.binaries=[item for item in gui_a.binaries if '/plugins/' not in item[0].replace('\\','/')
    or Path(item[0]).name.lower() in ('qwindows.dll','qmodernwindowsstyle.dll')]
gui_a.datas=[item for item in gui_a.datas if '/translations/' not in item[0].replace('\\','/')
    or Path(item[0]).name=='qtbase_es.qm']
dino_a=Analysis([str(root/ENTRY_POINTS['dino'])],
    # Source-backed package imports preserve __file__, inspect and producer
    # checkpoint fingerprints. The same source bytes are shipped and executed.
    module_collection_mode={'motorsim':'py'}, datas=declared_datas('dino'),
    hiddenimports=['unittest.mock','numpy','scipy.optimize','motorsim.dino4t.api','motorsim.dino4t.config','motorsim.dino4t.runner',
        'motorsim.dino4t.engine','motorsim.dino4t.duct','motorsim.dino4t.valves',
        'motorsim.dino4t.restriction','motorsim.dino4t.thermo','motorsim.dino4t.thermo_data',
        'motorsim.dino4t.combustion','motorsim.dino4t.twozone','motorsim.dino4t.equilibrium',
        'motorsim.dino4t.closures','motorsim.dino4t.kinematics','motorsim.dino4t.cycle_analysis'],**common)
dino_a.binaries=[item for item in dino_a.binaries if '/plugins/' not in item[0].replace('\\','/')
    or Path(item[0]).name.lower() in ('qwindows.dll','qmodernwindowsstyle.dll')]
dino_a.datas=[item for item in dino_a.datas if '/translations/' not in item[0].replace('\\','/')
    or Path(item[0]).name=='qtbase_es.qm']
worker_a=Analysis([str(root/ENTRY_POINTS['worker'])],datas=declared_datas('worker'),
    pathex=[str(root)],excludes=['PySide6','shiboken6','pywinauto','comtypes','dev_orchestrator'],noarchive=False)
gui=EXE(PYZ(gui_a.pure),gui_a.scripts,[],exclude_binaries=True,name='MotorSim',
    console=False,debug=False,strip=False,upx=False)
worker=EXE(PYZ(worker_a.pure),worker_a.scripts,[],exclude_binaries=True,name='MotorSimWorker',
    console=True,debug=False,strip=False,upx=False)
dino=EXE(PYZ(dino_a.pure),dino_a.scripts,[],exclude_binaries=True,name='Dino2T',
    console=False,debug=False,strip=False,upx=False)
COLLECT(gui,dino,worker,gui_a.binaries,gui_a.datas,dino_a.binaries,dino_a.datas,worker_a.binaries,worker_a.datas,
    strip=False,upx=False,name='MotorSim')
