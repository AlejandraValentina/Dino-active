"""Recorrido visible de configuración 4T, sin ejecutar el solver."""
import argparse
import ctypes
from dataclasses import replace
import json
import os
from pathlib import Path
import sys
from unittest.mock import patch

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output',type=Path,required=True)
parser.add_argument('--suffix',default='')
args=parser.parse_args()
os.environ['QT_QPA_PLATFORM']='windows'; os.environ['QT_SCALE_FACTOR']='1.5'
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PySide6.QtCore import QProcess,QTimer,Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from motorsim.window import MainWindow
from motorsim.four_stroke import geometry
from motorsim.simulation_case import geometry as two_geometry
from motorsim.storage import load_project

user32=ctypes.WinDLL('user32',use_last_error=True); user32.OpenInputDesktop.restype=ctypes.c_void_p
desktop=user32.OpenInputDesktop(0,False,1)
if not desktop: raise RuntimeError('Escritorio inaccesible; no se espera desbloqueo.')
name=ctypes.create_unicode_buffer(256); needed=ctypes.c_ulong()
user32.GetUserObjectInformationW.argtypes=[ctypes.c_void_p,ctypes.c_int,ctypes.c_void_p,ctypes.c_ulong,ctypes.POINTER(ctypes.c_ulong)]
assert user32.GetUserObjectInformationW(desktop,2,name,ctypes.sizeof(name),ctypes.byref(needed))
user32.CloseDesktop.argtypes=[ctypes.c_void_p]; user32.CloseDesktop(desktop)
assert name.value=='Default',name.value
args.output.mkdir(parents=True,exist_ok=False)
guard=patch.object(QProcess,'start',side_effect=AssertionError('No calcular para capturar')); start=guard.start()
app=QApplication([]); app.setApplicationName('MotorSim'); window=MainWindow()
base=replace(two_geometry(),name='EJEMPLO SINTÉTICO — configuración 4T',cycle='4T',four_stroke=geometry().four_stroke)
window._activate(base,None);window.show()
available=window.screen().availableGeometry()
window.resize(available.width()-40,available.height()-60);window.move(20,10)
window.raise_();window.activateWindow()
assert window.devicePixelRatioF()==1.5
window.tabs.setCurrentWidget(window.valves_view)
phase=0; captures=[]


def capture(kind):
    path=Path('docs/images')/f'motorsim-4t-{kind}-150{args.suffix}.png'
    assert not path.exists(),path
    frame=window.frameGeometry()
    pixels=window.screen().grabWindow(0,frame.x(),frame.y(),frame.width(),frame.height())
    assert not pixels.isNull() and pixels.save(str(path))
    captures.append(str(path));print('CAPTURE',path.resolve(),flush=True)


def tick():
    global phase
    try:
        w=window;v=w.valves_view
        if phase==0:
            # Modificar desde controles; snapshot esperado independiente del disco.
            v.edits['intake']['opening_deg'].setText('700')
            v.edits['intake']['duration_deg'].setText('240')
            v.edits['exhaust']['duration_deg'].setText('240')
            assert 'total 40°' in v.crossing.text()
            w.ducts4_view.edits['length_mm'].setText('110,5')
            expected=w.project(); assert w.dirty
            path=args.output/'EJEMPLO_SINTETICO_4T.json'
            with patch.object(w,'_choose_file',return_value=path): assert w.save()
            assert load_project(path)==expected and not w.dirty
            assert w.close()
            # Reabrir después del cierre, conservando configuración 2T independiente.
            w._activate(load_project(path),path);w.show();w.raise_();w.activateWindow()
            w.cycle_combo.setCurrentText('2T');assert w.project().ducts==base.ducts
            w.cycle_combo.setCurrentText('4T');assert w.project().four_stroke==expected.four_stroke
            assert w.save()
            v.edits['intake']['seat_mm'].setText('inválido')
            with patch.object(w,'_error') as err:
                assert not w.save();err.assert_called_once()
            assert not v.plots['intake'][0].values
            with patch.object(w,'_ask_changes',return_value='cancel'): assert not w.close()
            v.edits['intake']['seat_mm'].setText('24');assert w.save()
            v.edits['intake']['seat_mm'].setFocus()
            QTest.keyClick(v.edits['intake']['seat_mm'],Qt.Key.Key_Tab)
            assert v.edits['intake']['throat_mm'].hasFocus()
            v.verticalScrollBar().setValue(0)
        elif phase==1:
            capture('editor');v.verticalScrollBar().setValue(v.verticalScrollBar().maximum())
        elif phase==2:
            capture('alzada-cruce')
            for plot in v.plots.values():plot[1].parentWidget().parentWidget().setCurrentIndex(1)
        elif phase==3:
            capture('area-cruce');w.tabs.setCurrentWidget(w.duct_stack)
            w.ducts4_view.route_combo.setCurrentIndex(1)
            w.ducts4_view.verticalScrollBar().setValue(w.ducts4_view.verticalScrollBar().maximum())
        elif phase==4:
            capture('conductos');w.resize(700,500);w.tabs.setCurrentWidget(v)
            v.verticalScrollBar().setValue(0)
        elif phase==5:
            assert v.horizontalScrollBar().maximum()==0
            capture('compacto')
            evidence=dict(automated_visible=True,manual_acceptance=False,dpr=w.devicePixelRatioF(),
                desktop=name.value,solver_started=False,save_close_reopen=True,
                cycle_data_independent=True,invalid_save_protected=True,close_cancel_protected=True,
                keyboard=True,compact_width=700,captures=captures,
                solver_gate='Solo configuración: este recorrido no evalúa el solver ni su aceptación numérica.')
            (args.output/'recorrido.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2),encoding='utf-8')
            start.assert_not_called();w.dirty=False;w.close();app.quit();return
        phase+=1
    except Exception as exc:
        print('VISIBLE_ERROR',repr(exc),flush=True);window.dirty=False;window.close();app.exit(1)


timer=QTimer();timer.setInterval(500);timer.timeout.connect(tick);timer.start()
exit_code=app.exec();guard.stop();sys.exit(exit_code)
