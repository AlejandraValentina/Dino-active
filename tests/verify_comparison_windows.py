"""Recorrido visible de comparación/CSV con resultados existentes, nunca integración."""
import argparse
import csv
import ctypes
import hashlib
import os
from pathlib import Path
import sys
from unittest.mock import patch

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output',type=Path,required=True)
parser.add_argument('--suffix',default='')
parser.add_argument('--no-export',action='store_true',help='Solo repetir captura, sin escribir CSV.')
args=parser.parse_args()
os.environ['QT_QPA_PLATFORM']='windows';os.environ['QT_SCALE_FACTOR']='1.2'
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PySide6.QtCore import Qt, QTimer, QProcess
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from motorsim.window import MainWindow

user32=ctypes.WinDLL('user32',use_last_error=True)
user32.OpenInputDesktop.restype=ctypes.c_void_p
desktop=user32.OpenInputDesktop(0,False,1)
if not desktop:raise RuntimeError('Escritorio no accesible; no se espera desbloqueo')
name=ctypes.create_unicode_buffer(256);needed=ctypes.c_ulong()
user32.GetUserObjectInformationW.argtypes=[ctypes.c_void_p,ctypes.c_int,ctypes.c_void_p,ctypes.c_ulong,ctypes.POINTER(ctypes.c_ulong)]
assert user32.GetUserObjectInformationW(desktop,2,name,ctypes.sizeof(name),ctypes.byref(needed))
user32.CloseDesktop.argtypes=[ctypes.c_void_p];user32.CloseDesktop(desktop)
assert name.value=='Default',name.value

root=Path('results/simulacion-2t/editor-20260915')
sources=[p for side in ('A','B','C') for p in (root/side).glob('*.json')]
assert (root/'A/manifest.json').exists() and (root/'B/manifest.json').exists()
hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
app=QApplication([]);app.setApplicationName('MotorSim')
window=MainWindow();window.name_edit.setText('PROYECTO DE PRUEBA — comparación independiente')
before=window.project();window.show();window.tabs.setCurrentWidget(window.simulation_view)
guard=patch.object(QProcess,'start',side_effect=AssertionError('Prohibido iniciar cálculo'))
mock_start=guard.start()
view=None;phase=0


def capture(kind):
    path=Path('docs/images')/f'motorsim-comparacion-{kind}-150{args.suffix}.png'
    assert not path.exists(),str(path)
    frame=view.frameGeometry()
    pixels=view.screen().grabWindow(0,frame.x(),frame.y(),frame.width(),frame.height())
    assert not pixels.isNull() and pixels.save(str(path))
    print('CAPTURE',path.resolve(),pixels.width(),pixels.height(),flush=True)


def tick():
    global phase,view
    try:
        if phase==0:
            QTest.mouseClick(window.simulation_view.compare_button,Qt.MouseButton.LeftButton)
            view=window.simulation_view.comparison_dialog
            assert view is not None
            available=view.screen().availableGeometry()
            view.resize(min(1080,available.width()-40),min(790,available.height()-60))
            view.move(available.x()+20,available.y()+10)
            view.raise_();view.activateWindow()
            for i,side in enumerate(('A','B')):
                with patch('motorsim.comparison_view.QFileDialog.getOpenFileName',return_value=(str(root/side/'manifest.json'),'')):
                    QTest.mouseClick(view.select_buttons[i],Qt.MouseButton.LeftButton)
            assert view.comparison and view.export_button.isEnabled(),view.error_label.text()
            assert view.results[0]['inputs']['profile']['name']==view.results[1]['inputs']['profile']['name']=='B'
            assert len(view.comparison['differences']['geometry'])==1
            assert abs(view.comparison['metrics'][0]['difference']-.14104542998868)<1e-11
            if not args.no_export:
                with patch('motorsim.comparison_view.QFileDialog.getSaveFileName',return_value=(str(args.output),'')):
                    QTest.mouseClick(view.export_button,Qt.MouseButton.LeftButton)
                assert 'CSV exportados' in view.error_label.text(),view.error_label.text()
                with (args.output/'resumen.csv').open(encoding='utf-8',newline='') as f:summary=list(csv.DictReader(f))
                with (args.output/'curvas.csv').open(encoding='utf-8',newline='') as f:curves=list(csv.DictReader(f))
                assert len(summary)==7 and len(curves)==1442
                for i,key in enumerate(('W_C_J','W_K_J','p_max_Pa')):
                    expected=[r['result']['cycles'][-1][key] for r in view.results]
                    assert [float(summary[i][c]) for c in ('value_A','value_B')]==expected
                    assert float(summary[i]['difference_B_minus_A'])==expected[1]-expected[0]
                for i,r in enumerate(view.results):
                    rows=curves[i*721:(i+1)*721]
                    assert rows[0]['run_id']==r['manifest']['run_id']
                    assert float(rows[0]['angle_cycle_deg'])==180 and float(rows[-1]['angle_cycle_deg'])==540
                    assert [float(row['volume_m3']) for row in rows]==[row['V_m3'][2] for row in r['samples']['cycles'][-1]]
                print('CSV_VERIFIED',str(args.output.resolve()),'7 magnitudes, 1442 muestras',flush=True)
                view.error_label.clear();view.error_label.hide()
            view.scroll.verticalScrollBar().setValue(0)
            phase=1
        elif phase==1:
            assert view.table.verticalScrollBar().maximum()==0
            capture('resumen')
            view.tabs.setCurrentIndex(2)
            view.scroll.verticalScrollBar().setValue(view.scroll.verticalScrollBar().maximum())
            phase=2
        elif phase==2:
            capture('entradas')
            view.tabs.setCurrentIndex(1);view.scroll.verticalScrollBar().setValue(0)
            phase=3
        elif phase==3:
            capture('curvas')
            view.scroll.verticalScrollBar().setValue(view.scroll.verticalScrollBar().maximum())
            phase=4
        elif phase==4:
            capture('curvas-inferior')
            view.resize(730,view.height());view.tabs.setCurrentIndex(0);view.scroll.verticalScrollBar().setValue(0)
            phase=5
        elif phase==5:
            view.select_buttons[0].setFocus();QTest.keyClick(view.select_buttons[0],Qt.Key.Key_Tab)
            assert view.select_buttons[1].hasFocus()
            capture('compacta')
            assert window.project()==before and window.dirty
            assert hashes=={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
            mock_start.assert_not_called()
            print('WINDOWS_OK',f'DPR={view.devicePixelRatioF()}', 'sin cálculo; fuentes y proyecto intactos; no aceptación manual',flush=True)
            view.close();window.dirty=False;window.close();app.quit()
    except Exception as exc:
        print('ERROR',repr(exc),flush=True)
        timer.stop()
        if view:view.close()
        window.dirty=False;window.close();app.exit(1)


timer=QTimer();timer.setInterval(500);timer.timeout.connect(tick);timer.start()
code=app.exec();guard.stop();sys.exit(code)
