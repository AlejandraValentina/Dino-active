"""Protocolo visible 4T: ejecutar UNA vez o reabrir evidencia sin calcular.

No forma parte de unittest discover. --execute autoriza los cuatro puntos GUI
del protocolo R2 (barrido de tres y compresión 8.2); sin él solo se reabre.
"""
import argparse
import ctypes
from dataclasses import replace
import json
import os
from pathlib import Path
import sys
from unittest.mock import patch

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--root',type=Path,required=True)
parser.add_argument('--execute',action='store_true')
args=parser.parse_args()
os.environ['QT_QPA_PLATFORM']='windows';os.environ['QT_SCALE_FACTOR']='1.5'
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PySide6.QtCore import QProcess,QTimer,Qt
from PySide6.QtWidgets import QApplication,QTabWidget
from motorsim.window import MainWindow
from motorsim.four_stroke import geometry
from motorsim.reference_results import load_result
from motorsim.sweep import load_sweep

u=ctypes.WinDLL('user32',use_last_error=True);u.OpenInputDesktop.restype=ctypes.c_void_p
d=u.OpenInputDesktop(0,False,1)
if not d:raise RuntimeError('Escritorio inaccesible; no se espera desbloqueo.')
name=ctypes.create_unicode_buffer(256);needed=ctypes.c_ulong()
u.GetUserObjectInformationW.argtypes=[ctypes.c_void_p,ctypes.c_int,ctypes.c_void_p,ctypes.c_ulong,ctypes.POINTER(ctypes.c_ulong)]
assert u.GetUserObjectInformationW(d,2,name,ctypes.sizeof(name),ctypes.byref(needed))
u.CloseDesktop.argtypes=[ctypes.c_void_p];u.CloseDesktop(d)
assert name.value=='Default',name.value
ledger_path=args.root/'protocol.json'
ledger=json.loads(ledger_path.read_text(encoding='utf-8'))
assert ledger['gate_passed']
if args.execute:
    assert ledger['integration_seconds']+240<=ledger['limit_seconds']
    assert not (args.root/'gui-sweep').exists() and not (args.root/'gui-compression').exists()
guard=None if args.execute else patch.object(QProcess,'start',side_effect=AssertionError('Recaptura sin integrar'))
if guard:guard.start()
app=QApplication([]);app.setApplicationName('MotorSim');w=MainWindow();v=w.simulation_view
base=replace(geometry(),name='EJEMPLO SINTÉTICO S4T — protocolo R2')
w._activate(base,None);w.show();w.tabs.setCurrentWidget(v)
available=w.screen().availableGeometry()
def fit(widget):
    widget.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint,True)
    widget.resize(available.width()-40,available.height()-60);widget.move(20,10)
    widget.show();widget.raise_();widget.activateWindow()
fit(w);assert w.devicePixelRatioF()==1.5
phase=0;captures=[];last_progress=''
def account(label,result):
    ledger['runs'].append(dict(name=label,seconds=result['result']['seconds'],
        converged=result['status']=='converged',stop=result['result']['stop']))
    ledger['integration_seconds']+=result['result']['seconds']
    ledger_path.write_text(json.dumps(ledger,ensure_ascii=False,indent=2),encoding='utf-8')
    assert ledger['integration_seconds']<=720

def capture(widget,kind):
    path=Path('docs/images')/f'motorsim-4t-{kind}-r2-150.png'
    frame=widget.frameGeometry();pixels=widget.screen().grabWindow(0,frame.x(),frame.y(),frame.width(),frame.height())
    assert not pixels.isNull() and pixels.save(str(path))
    captures.append(str(path));print('CAPTURE',path,flush=True)

def tick():
    global phase,last_progress
    try:
        if v.active:
            progress=v.progress_label.text()
            if progress!=last_progress:print(progress,flush=True);last_progress=progress
            return
        if phase==0:
            v.origin_combo.setCurrentIndex(1);v.mode_combo.setCurrentIndex(1)
            if args.execute:v.start(output=args.root/'gui-sweep')
            else:v.open_sweep(path=args.root/'gui-sweep/series.json')
        elif phase==1:
            assert v.sweep is not None,(v.state_label.text(),v.error_label.text())
            if args.execute:
                for point,result in zip(v.sweep['index']['points'],v.sweep['results']):
                    if result:account(f"GUI-B100-{point['rpm']}",result)
            assert v.sweep['index']['state']=='converged',v.sweep['index']['reason']
            fit(v.sweep_dialog)
            if not (args.root/'sweep-csv').exists():v.sweep_dialog.export(folder=args.root/'sweep-csv')
        elif phase==2:
            capture(v.sweep_dialog,'barrido')
            v.sweep_dialog.findChild(QTabWidget).setCurrentIndex(1)
        elif phase==3:
            capture(v.sweep_dialog,'barrido-trabajo');v.sweep_dialog.hide()
            w.numeric_edits['compression_ratio'].setText('8.2')
            assert w.dirty
            v.mode_combo.setCurrentIndex(0);v.rpm_edit.setText('3000')
            if args.execute:v.start(output=args.root/'gui-compression')
            else:v.open_result(path=args.root/'gui-compression/manifest.json')
        elif phase==4:
            assert v.result is not None,(v.state_label.text(),v.error_label.text())
            if args.execute:account('GUI-B100-compression-8.2',v.result)
            assert v.result['status']=='converged',v.result['result']['stop']
            assert v.result['inputs']['project_snapshot']['compression_ratio']==8.2
            assert v.result['inputs']['origin']['dirty']
            fit(w);v.ensureWidgetVisible(v.summary_label,0,0)
        elif phase==5:
            capture(w,'resultado');v.verticalScrollBar().setValue(v.verticalScrollBar().maximum())
        elif phase==6:
            capture(w,'curvas');v.show_comparison();dialog=v.comparison_dialog
            dialog.select_result(0,path=args.root/'gui-sweep/point-02/manifest.json')
            dialog.select_result(1,path=args.root/'gui-compression/manifest.json')
            assert dialog.comparison is not None,dialog.compatibility_label.text()
            fit(dialog);dialog.scroll.ensureWidgetVisible(dialog.table,0,0)
            if not (args.root/'comparison-csv').exists():dialog.export(folder=args.root/'comparison-csv')
        elif phase==7:
            capture(v.comparison_dialog,'comparacion');v.comparison_dialog.tabs.setCurrentIndex(1)
            v.comparison_dialog.scroll.ensureWidgetVisible(v.comparison_dialog.angle_plot,0,0)
        elif phase==8:
            capture(v.comparison_dialog,'comparacion-curvas')
            evidence=dict(automated_visible=True,manual_acceptance=False,desktop=name.value,dpr=w.devicePixelRatioF(),
                captures=captures,executed=args.execute,source='R2/gui-sweep + R2/gui-compression',
                unsaved_compression_snapshot=True,comparison_csv=True,sweep_csv=True)
            (args.root/('windows-execution.json' if args.execute else 'windows-reopen.json')).write_text(json.dumps(evidence,ensure_ascii=False,indent=2),encoding='utf-8')
            v.comparison_dialog.close();w.dirty=False;w.close();app.quit();return
        phase+=1
    except Exception as exc:
        print('VISIBLE_ERROR',repr(exc),flush=True)
        if v.active:v.cancel()
        w.dirty=False;w.close();app.exit(1)
timer=QTimer();timer.setInterval(500);timer.timeout.connect(tick);timer.start()
code=app.exec()
if guard:guard.stop()
sys.exit(code)
