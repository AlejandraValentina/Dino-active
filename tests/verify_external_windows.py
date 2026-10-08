"""Importación visible con CSV sintético y barrido existente. Prohibido calcular."""
import argparse
import csv
import ctypes
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import sys
from unittest.mock import patch

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output',type=Path,required=True)
parser.add_argument('--reopen',action='store_true',help='Solo reabrir y capturar, sin importar/exportar de nuevo.')
parser.add_argument('--suffix',default='')
parser.add_argument('--scale',default='1.5',help='Factor Qt del proceso; comprobar DPR efectivo 1.5.')
args=parser.parse_args()
os.environ['QT_QPA_PLATFORM']='windows';os.environ['QT_SCALE_FACTOR']=args.scale
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PySide6.QtCore import Qt, QTimer, QProcess
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from motorsim.window import MainWindow
from motorsim.external_view import ImportDialog

user32=ctypes.WinDLL('user32',use_last_error=True);user32.OpenInputDesktop.restype=ctypes.c_void_p
desktop=user32.OpenInputDesktop(0,False,1)
if not desktop:raise RuntimeError('Escritorio inaccesible; no esperar desbloqueo')
name=ctypes.create_unicode_buffer(256);needed=ctypes.c_ulong()
user32.GetUserObjectInformationW.argtypes=[ctypes.c_void_p,ctypes.c_int,ctypes.c_void_p,ctypes.c_ulong,ctypes.POINTER(ctypes.c_ulong)]
assert user32.GetUserObjectInformationW(desktop,2,name,ctypes.sizeof(name),ctypes.byref(needed))
user32.CloseDesktop.argtypes=[ctypes.c_void_p];user32.CloseDesktop(desktop)
assert name.value=='Default',name.value
sweep=Path('results/simulacion-2t/barrido-20260915/gui-sweep/series.json')
if not sweep.exists():raise RuntimeError('Barrido local no disponible. No se calcula ni se sustituye.')
source=Path('examples/EJEMPLO_SINTETICO_contraste.csv')
sources=[source,*sweep.parent.rglob('*.json')]
hashes={str(path):hashlib.sha256(path.read_bytes()).hexdigest() for path in sources}
if not args.reopen:args.output.mkdir(parents=True,exist_ok=False)
guard=patch.object(QProcess,'start',side_effect=AssertionError('Ninguna operación debe iniciar el motor'))
start=guard.start()
app=QApplication([]);app.setApplicationName('MotorSim')
window=MainWindow();window.name_edit.setText('Proyecto propio sin guardar — no usado para contraste')
before=window.project();dirty=window.dirty;window.show();view=window.simulation_view
window.tabs.setCurrentWidget(view)
available=window.screen().availableGeometry()
window.resize(min(1080,available.width()-40),available.height()-60);window.move(20,10)
window.raise_();window.activateWindow()
assert window.devicePixelRatioF()==1.5,window.devicePixelRatioF()
dialog=None;phase='start';error=None


def capture(kind,widget=None):
    widget=widget or dialog
    path=Path('docs/images')/f'motorsim-datos-externos-{kind}-150{args.suffix}.png'
    assert not path.exists(),str(path)
    frame=widget.frameGeometry();pixels=widget.screen().grabWindow(0,frame.x(),frame.y(),frame.width(),frame.height())
    assert not pixels.isNull() and pixels.save(str(path))
    print('CAPTURE',str(path.resolve()),pixels.width(),pixels.height(),flush=True)


def fill_declaration():
    global error
    try:
        wizard=app.activeModalWidget();assert isinstance(wizard,ImportDialog)
        wizard.resize(min(780,available.width()-60),available.height()-80);wizard.move(35,15)
        assert wizard.provenance.currentText()=='No determinada'
        wizard.magnitude.setCurrentIndex(1);wizard.unit.setCurrentIndex(1)
        wizard.provenance.setCurrentText('Ejemplo sintético')
        wizard.texts['name'].setText('EJEMPLO SINTÉTICO — control de importación')
        wizard.texts['source'].setText('Valores de prueba definidos independientemente; no derivados del barrido ni medidos.')
        wizard.texts['notes'].setText('10, 20 y −2 J/ciclo son un control aritmético; 2000/4000 rpm prueban puntos sin pareja.')
        wizard.confirm_definition.setChecked(True)
        QTest.mouseClick(wizard.preview_button,Qt.MouseButton.LeftButton)
        assert wizard.prepared and wizard.preview_table.rowCount()==5,wizard.error.text()
        assert 'Ejemplo sintético' in wizard.preview_info.text()
        # Dejar pintar antes de confirmar la importación persistente.
        def confirm():
            try:
                capture('vista-previa',wizard)
                with patch('motorsim.external_view.QFileDialog.getSaveFileName',return_value=(str(args.output/'importacion'),'')):
                    QTest.mouseClick(wizard.confirm_button,Qt.MouseButton.LeftButton)
                assert wizard.imported,wizard.error.text()
            except Exception as exc:
                global error
                error=exc;wizard.reject()
        QTimer.singleShot(400,confirm)
    except Exception as exc:
        error=exc
        if app.activeModalWidget():app.activeModalWidget().reject()


def tick():
    global phase,dialog
    try:
        if phase=='start':
            phase='busy'
            view.ensureWidgetVisible(view.external_button)
            QTest.mouseClick(view.external_button,Qt.MouseButton.LeftButton)
            dialog=view.external_dialog;assert dialog
            dialog.resize(min(1150,available.width()-40),available.height()-60);dialog.move(20,10)
            dialog.raise_();dialog.activateWindow()
            if args.reopen:
                dialog.open_import(path=args.output/'importacion/metadata.json')
            else:
                with patch('motorsim.external_view.QFileDialog.getOpenFileName',return_value=(str(source),'')):
                    QTimer.singleShot(200,fill_declaration)
                    QTest.mouseClick(dialog.import_button,Qt.MouseButton.LeftButton)
                if error:raise error
            assert dialog.external,dialog.error.text()
            with patch('motorsim.external_view.QFileDialog.getOpenFileName',return_value=(str(sweep),'')):
                QTest.mouseClick(dialog.sweep_button,Qt.MouseButton.LeftButton)
            assert dialog.data and dialog.data['matches']==3,dialog.error.text()
            assert dialog.data['external_count']==5 and len(dialog.data['rows'])==5
            assert dialog.external['metadata']['provenance']=='Ejemplo sintético'
            assert 'Equivalencia de condiciones no acreditada' in dialog.status.text()
            if not args.reopen:
                with patch('motorsim.external_view.QFileDialog.getSaveFileName',return_value=(str(args.output/'exportacion'),'')):
                    QTest.mouseClick(dialog.export_button,Qt.MouseButton.LeftButton)
                with (args.output/'exportacion/contraste.csv').open(encoding='utf-8',newline='') as stream:rows=list(csv.DictReader(stream))
                assert len(rows)==5
                for csv_row,row in zip(rows,dialog.data['rows']):
                    assert csv_row['provenance']=='Ejemplo sintético'
                    for column,key in (('external','external'),('simulated','simulated'),('simulated_minus_external','difference'),('relative_percent','relative_percent')):
                        assert (csv_row[column]=='' if row[key] is None else Decimal(csv_row[column])==row[key])
                # Reabrir solo la copia: no se consulta el CSV fuente.
                with patch('motorsim.external_view.QFileDialog.getOpenFileName',return_value=(str(args.output/'importacion/metadata.json'),'')):
                    QTest.mouseClick(dialog.open_button,Qt.MouseButton.LeftButton)
            phase='table'
        elif phase=='table':
            capture('tabla');dialog.tabs.setCurrentIndex(1);phase='plot'
        elif phase=='plot':
            capture('puntos');dialog.tabs.setCurrentIndex(2);phase='metadata'
        elif phase=='metadata':
            capture('procedencia');dialog.tabs.setCurrentIndex(0)
            dialog.resize(780,available.height()-90);dialog.import_button.setFocus()
            QTest.keyClick(dialog.import_button,Qt.Key.Key_Tab);assert dialog.open_button.hasFocus()
            phase='compact'
        elif phase=='compact':
            capture('compacto')
            assert window.project()==before and window.dirty==dirty
            assert all(hashlib.sha256(Path(path).read_bytes()).hexdigest()==value for path,value in hashes.items())
            start.assert_not_called()
            evidence=dict(dpr=window.devicePixelRatioF(),automated_visible=True,manual_acceptance=False,
                solver_started=False,source_hashes_unchanged=True,project_and_dirty_unchanged=True,
                dataset_id=dialog.external['manifest']['dataset_id'],series_id=dialog.data['series_id'],
                provenance=dialog.external['metadata']['provenance'],external_points=5,matched_points=3,
                real_measurements=False,experimental_validation=False)
            if not args.reopen:(args.output/'recorrido.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2),encoding='utf-8')
            print('WINDOWS_VISIBLE_OK',json.dumps(evidence),flush=True)
            dialog.close();window.dirty=False;window.close();app.quit()
    except Exception as exc:
        print('VISIBLE_ERROR',repr(exc),flush=True)
        if dialog:dialog.close()
        window.dirty=False;window.close();timer.stop();app.exit(1)


timer=QTimer();timer.setInterval(400);timer.timeout.connect(tick);timer.start()
exit_code=app.exec();guard.stop();sys.exit(exit_code)
