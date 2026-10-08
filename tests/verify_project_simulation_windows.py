"""A/B por editor visible + único contraste C de consola. No es aceptación manual."""
import argparse
import ctypes
from dataclasses import replace
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from unittest.mock import patch

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output',type=Path,required=True,help='Directorio nuevo para evidencia A/B/C.')
parser.add_argument('--reopen',type=Path,help='Solo inspeccionar resultado existente, sin calcular A/B/C.')
parser.add_argument('--scale',default='1')
parser.add_argument('--suffix',default='')
args=parser.parse_args()
os.environ['QT_QPA_PLATFORM']='windows'
os.environ['QT_SCALE_FACTOR']=args.scale
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PySide6.QtCore import Qt, QTimer
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from motorsim.window import MainWindow
from motorsim.simulation_case import SyntheticCase
from motorsim.reference_results import load_result, validated_model
from motorsim.simulation import sensitivity
from motorsim.storage import save_project

# No esperar un desbloqueo ni modificar la política del escritorio.
user32=ctypes.WinDLL('user32',use_last_error=True)
user32.OpenInputDesktop.restype=ctypes.c_void_p
desktop=user32.OpenInputDesktop(0,False,0x0001)
if not desktop:raise RuntimeError('Escritorio de entrada no accesible')
name=ctypes.create_unicode_buffer(256)
needed=ctypes.c_ulong()
user32.GetUserObjectInformationW.argtypes=[ctypes.c_void_p,ctypes.c_int,ctypes.c_void_p,ctypes.c_ulong,ctypes.POINTER(ctypes.c_ulong)]
assert user32.GetUserObjectInformationW(desktop,2,name,ctypes.sizeof(name),ctypes.byref(needed))
user32.CloseDesktop.argtypes=[ctypes.c_void_p]
user32.CloseDesktop(desktop)
assert name.value=='Default', f'Escritorio {name.value}; no se ejecuta recorrido visible'

if not args.reopen:args.output.mkdir(parents=True,exist_ok=False)
app=QApplication([])
app.setApplicationName('MotorSim')
window=MainWindow()
view=window.simulation_view
window.show()
available=window.screen().availableGeometry()
window.resize(min(1050,available.width()-40),min(790,available.height()-70))
window.move(available.x()+20,available.y()+20)
window.raise_()
window.activateWindow()
started=time.monotonic()
phase='reopen' if args.reopen else 'A'
current_project=None
current_dirty=False
console=None
console_log=None
results={}


def load_editor(path):
    window.dirty=False  # Solo preparación del recorrido con archivos propios de prueba.
    with patch.object(window,'_choose_file',return_value=path.resolve()):window.open_project()
    assert window.path==path.resolve()


def start_editor(label):
    global current_project,current_dirty
    path=args.output/f'proyecto-prueba-{label}.json'
    save_project(path,replace(SyntheticCase().project_geometry,name='PRUEBA de integración del editor'))
    load_editor(path)
    window.tabs.setCurrentIndex(0)
    if label=='B':
        edit=window.numeric_edits['compression_ratio']
        edit.setFocus();edit.selectAll();QTest.keyClicks(edit,'8,2')
    current_project,current_dirty=window.project(),window.dirty
    assert current_project.compression_ratio==(8.2 if label=='B' else 8)
    window.tabs.setCurrentWidget(view)
    view.origin_combo.setCurrentIndex(1)
    view.verticalScrollBar().setValue(0)
    QTest.mouseClick(view.check_button,Qt.MouseButton.LeftButton)
    assert 'Entradas admitidas' in view.error_label.text(),view.error_label.text()
    with patch('motorsim.simulation_view.new_output_path',return_value=args.output/label):
        QTest.mouseClick(view.run_button,Qt.MouseButton.LeftButton)
    assert view.active,view.error_label.text()
    process=view.process
    view.start(output=args.output/'duplicate')
    assert view.process is process


def capture(suffix):
    frame=window.frameGeometry()
    path=Path('docs/images')/f'motorsim-proyecto-0d-{suffix}{args.suffix}.png'
    assert not path.exists(),f'No sobrescribir {path}'
    pixmap=window.screen().grabWindow(0,frame.x(),frame.y(),frame.width(),frame.height())
    assert not pixmap.isNull() and pixmap.save(str(path))
    print('CAPTURE',str(path.resolve()),pixmap.width(),pixmap.height(),flush=True)


def record_comparison():
    reference=load_result('results/simulacion-2t/integracion-ui-20260915/manifest.json')
    a,b,c=(results[k] for k in 'ABC')
    exact=(a['result']['cycles']==reference['result']['cycles']
           and a['samples']['cycles']==reference['samples']['cycles']
           and a['result']['rhs_evaluations']==reference['result']['rhs_evaluations'])
    mb,_=validated_model(b['inputs']);ma,_=validated_model(a['inputs'])
    comparison=dict(passed=False,reason='No hay dos soluciones convergidas.')
    if b['status']==c['status']=='converged':
        br=dict(b['result'],last_two_cycles=b['samples']['cycles'])
        cr=dict(c['result'],last_two_cycles=c['samples']['cycles'])
        metrics=sensitivity([br,br,cr])
        comparison=dict(passed=metrics['tolerances_passed'],differences=metrics['fine'],
            meaning='Solo contraste B/C; no acredita tendencia de tres perfiles ni todo el dominio.')
    numerical_seconds=sum(r['result']['seconds'] for r in results.values())
    evidence=dict(reference_A_exact=exact,clearance_A_m3=ma.clearance,clearance_B_m3=mb.clearance,
        modified_B_C_same_snapshot=b['inputs']['project_snapshot']==c['inputs']['project_snapshot'],
        contrast_B_C=comparison,numerical_seconds=numerical_seconds,wall_seconds=time.monotonic()-started,
        executions={key:dict(status=r['status'],cycles=len(r['result']['cycles']),stop=r['result']['stop'],
            seconds=r['result']['seconds'],peak_process_MiB=r['result']['peak_process_MiB'],
            rhs=r['result']['rhs_evaluations'],last_cycle=r['result']['cycles'][-1] if r['result']['cycles'] else None)
            for key,r in results.items()},manual_acceptance=False)
    (args.output/'protocol.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2),encoding='utf-8')
    print('PROTOCOL',json.dumps({k:v for k,v in evidence.items() if k!='executions'}),flush=True)
    assert numerical_seconds<=180
    assert exact,'A no reproduce referencia'
    assert ma.clearance!=mb.clearance
    assert evidence['modified_B_C_same_snapshot']


def tick():
    global phase,console,console_log
    try:
        assert time.monotonic()-started<180,'Presupuesto global de recorrido agotado'
        if phase in ('A','B'):
            start_editor(phase)
            phase+=' running'
        elif phase in ('A running','B running') and not view.active:
            label=phase[0]
            assert view.result,view.error_label.text()
            results[label]=view.result
            assert window.project()==current_project and window.dirty==current_dirty
            assert not (args.output/'duplicate').exists()
            print('EDITOR_RESULT',label,view.result['status'],view.result['result']['seconds'],flush=True)
            if label=='A':phase='B'
            else:
                # Reapertura real de lo guardado, sin cambiar proyecto ni volver a calcular.
                path=view.result['path']
                view.open_result(path=path)
                assert view.result['path']==path and window.project()==current_project and window.dirty
                request=args.output/'request-C.json'
                request.write_text(json.dumps(view.result['inputs'],ensure_ascii=False),encoding='utf-8')
                console_log=(args.output/'console-C.log').open('w',encoding='utf-8')
                command=[sys.executable,'-u','-m','motorsim.reference_run','--project-input',str(request),
                    '--profile-c-check','--control-stdin','--output',str(args.output/'C')]
                console=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=console_log,stderr=subprocess.STDOUT,
                    creationflags=subprocess.CREATE_NO_WINDOW)
                phase='C running'
        elif phase=='C running' and console.poll() is not None:
            console.stdin.close();console_log.close()
            results['C']=load_result(args.output/'C/manifest.json')
            record_comparison()
            phase='capture'
        elif phase=='reopen':
            view.open_result(path=args.reopen)
            assert view.result,view.error_label.text()
            # Cargar solo la copia documentada en editor para mostrar correspondencia vigente.
            from motorsim.project import Project
            window._activate(Project.from_dict(view.inputs['project_snapshot']),
                             Path(view.inputs['origin']['source_path']) if view.inputs['origin']['source_path'] else None)
            window.dirty=view.inputs['origin']['dirty'];window._refresh_status()
            window.tabs.setCurrentWidget(view)
            view.origin_combo.setCurrentIndex(1)
            phase='capture'
        elif phase=='capture':
            assert 'PRUEBA' in view.identity_label.text()
            if view.result['status']=='converged':assert len(view.angle_plot.points)==len(view.pv_plot.points)==721
            capture('resultado')
            view.verticalScrollBar().setValue(view.verticalScrollBar().maximum())
            phase='bottom'
        elif phase=='bottom':
            capture('curvas')
            window.resize(700,min(680,available.height()-70))
            view.verticalScrollBar().setValue(0)
            phase='compact'
        elif phase=='compact':
            assert view.horizontalScrollBar().maximum()==0
            view.run_button.setFocus();QTest.keyClick(view.run_button,Qt.Key.Key_Tab)
            assert view.open_button.hasFocus()
            window.tabs.setCurrentIndex(0);window.tabs.setCurrentWidget(view)
            capture('compacto')
            print('WINDOWS_VISIBLE_OK',json.dumps(dict(device_pixel_ratio=window.devicePixelRatioF(),
                result=str(view.result['path']),manual_acceptance=False)),flush=True)
            window.dirty=False;window.close();app.quit()
    except Exception as exc:
        print('VISIBLE_ERROR',repr(exc),flush=True)
        if view.active:view.cancel()
        if console and console.poll() is None:
            console.stdin.write(b'cancel\n');console.stdin.flush()
        window.dirty=False;window.close()
        timer.stop()
        QTimer.singleShot(3500,lambda:app.exit(1))


timer=QTimer();timer.setInterval(350);timer.timeout.connect(tick);timer.start()
sys.exit(app.exec())
