"""Protocolo autorizado: GUI B 2500/3000/3500 y, condicionalmente, C extremos.

Ventanas reales automatizadas, no aceptación manual. --reopen solo consulta/captura.
"""
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
parser.add_argument('--output',type=Path,required=True)
parser.add_argument('--reopen',action='store_true')
parser.add_argument('--suffix',default='')
args=parser.parse_args()
os.environ['QT_QPA_PLATFORM']='windows';os.environ['QT_SCALE_FACTOR']='1.2'
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PySide6.QtCore import Qt, QTimer, QProcess
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QTabWidget
from motorsim.window import MainWindow
from motorsim.simulation_case import SyntheticCase
from motorsim.reference_results import load_result
from motorsim.sweep import load_sweep
from motorsim.simulation import sensitivity
from motorsim.comparison import compatibility_errors

user32=ctypes.WinDLL('user32',use_last_error=True)
user32.OpenInputDesktop.restype=ctypes.c_void_p
desktop=user32.OpenInputDesktop(0,False,1)
if not desktop:raise RuntimeError('Escritorio inaccesible; no esperar desbloqueo')
name=ctypes.create_unicode_buffer(256);needed=ctypes.c_ulong()
user32.GetUserObjectInformationW.argtypes=[ctypes.c_void_p,ctypes.c_int,ctypes.c_void_p,ctypes.c_ulong,ctypes.POINTER(ctypes.c_ulong)]
assert user32.GetUserObjectInformationW(desktop,2,name,ctypes.sizeof(name),ctypes.byref(needed))
user32.CloseDesktop.argtypes=[ctypes.c_void_p];user32.CloseDesktop(desktop)
assert name.value=='Default',name.value
if not args.reopen:args.output.mkdir(parents=True,exist_ok=False)
app=QApplication([]);app.setApplicationName('MotorSim')
window=MainWindow();view=window.simulation_view;window.show()
available=window.screen().availableGeometry()
window.resize(min(1050,available.width()-40),available.height()-60);window.move(20,10)
window.raise_();window.activateWindow()
assert window.devicePixelRatioF()==1.5,window.devicePixelRatioF()
phase='reopen' if args.reopen else 'start'
started=time.monotonic();console=None;console_log=None;results={};contrasts={};checks={};current_rpm=None


def capture(kind):
    dialog=view.sweep_dialog
    path=Path('docs/images')/f'motorsim-barrido-{kind}-150{args.suffix}.png'
    assert not path.exists(),str(path)
    frame=dialog.frameGeometry()
    pixmap=dialog.screen().grabWindow(0,frame.x(),frame.y(),frame.width(),frame.height())
    assert not pixmap.isNull() and pixmap.save(str(path))
    print('CAPTURE',str(path.resolve()),pixmap.width(),pixmap.height(),flush=True)


def start_console(rpm):
    global console,console_log,current_rpm
    assert not view.active
    current_rpm=rpm
    request=args.output/f'input-C-{rpm}.json'
    request.write_text(json.dumps(results[f'B{rpm}']['inputs'],ensure_ascii=False),encoding='utf-8')
    console_log=(args.output/f'C-{rpm}.log').open('x',encoding='utf-8')
    console=subprocess.Popen([sys.executable,'-u','-m','motorsim.reference_run',
        '--project-input',str(request),'--profile-c-check','--control-stdin','--output',str(args.output/f'C-{rpm}')],
        stdin=subprocess.PIPE,stdout=console_log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)


def record():
    integration=sum(r['result']['seconds'] for r in results.values())
    evidence=dict(checks=checks,contrasts=contrasts,integration_seconds=integration,
        protocol_wall_seconds=time.monotonic()-started,manual_acceptance=False,windows_dpr=window.devicePixelRatioF(),
        executions={key:dict(status=r['status'],run_id=r['manifest']['run_id'],cycles=len(r['result']['cycles']),
            stop=r['result']['stop'],seconds=r['result']['seconds'],peak_process_MiB=r['result']['peak_process_MiB'],
            rhs=r['result'].get('rhs_evaluations'),last_cycle=r['result']['cycles'][-1] if r['result']['cycles'] else None)
            for key,r in results.items()})
    (args.output/'protocol.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2),encoding='utf-8')
    print('PROTOCOL',json.dumps({k:v for k,v in evidence.items() if k!='executions'}),flush=True)
    assert integration<=300 and len(results)<=5


def tick():
    global phase,console,console_log
    try:
        assert time.monotonic()-started<370,'Tiempo de supervisión del recorrido agotado'
        if phase=='start':
            window._activate(replace(SyntheticCase().project_geometry,name='PRUEBA SINTÉTICA'),None)
            window.name_edit.setText('PRUEBA SINTÉTICA — barrido 8:1 sin guardar')
            window.tabs.setCurrentWidget(view);view.origin_combo.setCurrentIndex(1);view.mode_combo.setCurrentIndex(1)
            assert view._rpms()==[2500,3000,3500] and window.dirty
            view.ensureWidgetVisible(view.run_button)
            QTest.mouseClick(view.check_button,Qt.MouseButton.LeftButton)
            assert 'Entradas admitidas' in view.error_label.text(),view.error_label.text()
            with patch('motorsim.simulation_view.new_output_path',return_value=args.output/'gui-sweep'):
                QTest.mouseClick(view.run_button,Qt.MouseButton.LeftButton)
            assert view.active,view.error_label.text()
            process=view.process;view.start(output=args.output/'duplicate');assert view.process is process
            window.numeric_edits['compression_ratio'].setText('8.2')
            assert view.stale_label.text()
            phase='B running'
        elif phase=='B running' and not view.active:
            assert view.sweep,view.error_label.text()
            for rpm,r in zip(view.sweep['index']['rpms'],view.sweep['results']):
                if r:results[f'B{rpm}']=r
            checks['all_B_converged']=view.sweep['index']['state']=='converged'
            checks['copy_geometry_8_and_dirty']=all(r['inputs']['project_snapshot']['compression_ratio']==8 and r['inputs']['origin']['dirty'] for r in results.values())
            checks['editor_remains_8_2']=window.project().compression_ratio==8.2 and window.dirty
            checks['no_duplicate']=not (args.output/'duplicate').exists()
            if 'B3000' in results:
                reference=load_result('results/simulacion-2t/integracion-ui-20260915/manifest.json')
                actual=results['B3000']
                checks['3000_exact_reference']=(actual['result']['cycles']==reference['result']['cycles'] and
                    actual['samples']['cycles']==reference['samples']['cycles'] and
                    actual['result']['rhs_evaluations']==reference['result']['rhs_evaluations'])
                checks['AB_historical_3000_compatible']=not compatibility_errors(reference,actual)
            for key,r in results.items():print('REAL_POINT',key,r['status'],r['result']['seconds'],flush=True)
            assert checks['copy_geometry_8_and_dirty'] and checks['editor_remains_8_2'] and checks['no_duplicate']
            if checks['all_B_converged'] and checks.get('3000_exact_reference'):
                start_console(2500);phase='C running'
            else:
                checks['C_omitted']='Barrido no aprobado; no se amplía protocolo'
                record();phase='reopen'
        elif phase=='C running' and console.poll() is not None:
            console.stdin.close();console_log.close()
            r=load_result(args.output/f'C-{current_rpm}/manifest.json');results[f'C{current_rpm}']=r
            b=results[f'B{current_rpm}']
            if r['status']==b['status']=='converged':
                br=dict(b['result'],last_two_cycles=b['samples']['cycles'])
                cr=dict(r['result'],last_two_cycles=r['samples']['cycles'])
                metrics=sensitivity([br,br,cr])
                contrasts[str(current_rpm)]=dict(passed=metrics['tolerances_passed'],differences=metrics['fine'],
                    scope='Contraste B/C, no tendencia de tres perfiles ni validación de dominio')
            else:contrasts[str(current_rpm)]=dict(passed=False,reason=r['result']['stop'])
            print('REAL_POINT',f'C{current_rpm}',r['status'],r['result']['seconds'],flush=True)
            console=None
            if current_rpm==2500:start_console(3500)
            else:record();phase='reopen'
        elif phase=='reopen':
            before=window.project();dirty=window.dirty
            with patch.object(QProcess,'start',side_effect=AssertionError('Reapertura no debe calcular')):
                view.open_sweep(path=args.output/'gui-sweep/series.json')
            assert view.sweep and window.project()==before and window.dirty==dirty
            dialog=view.sweep_dialog
            dialog.resize(min(1100,available.width()-40),min(640,available.height()-60));dialog.move(20,10)
            dialog.raise_();dialog.activateWindow()
            if not args.reopen:
                dialog.export(folder=args.output/'csv')
                assert (args.output/'csv/serie.csv').exists(),dialog.error.text()
            phase='capture'
        elif phase=='capture':
            capture('resumen')
            view.sweep_dialog.findChild(QTabWidget).setCurrentIndex(1);phase='plots'
        elif phase=='plots':
            capture('trabajo')
            view.sweep_dialog.findChild(QTabWidget).setCurrentIndex(2);phase='pressure'
        elif phase=='pressure':
            capture('presion')
            dialog=view.sweep_dialog;dialog.findChild(QTabWidget).setCurrentIndex(0)
            dialog.table.selectRow(0)
            if dialog.point_button.isEnabled():
                QTest.mouseClick(dialog.point_button,Qt.MouseButton.LeftButton)
                assert view.result and len(view.angle_plot.points)==721 and len(view.pv_plot.points)==721
                view.show_sweep()
            dialog.resize(740,min(590,available.height()-60));dialog.point_button.setFocus()
            QTest.keyClick(dialog.point_button,Qt.Key.Key_Tab);assert dialog.export_button.hasFocus()
            phase='compact'
        elif phase=='compact':
            capture('compacto')
            print('WINDOWS_VISIBLE_OK',json.dumps(dict(dpr=window.devicePixelRatioF(),manual_acceptance=False)),flush=True)
            window.dirty=False;window.close();app.quit()
    except Exception as exc:
        print('PROTOCOL_ERROR',repr(exc),flush=True)
        if view.active:view.cancel()
        if console and console.poll() is None:
            console.stdin.write(b'cancel\n');console.stdin.flush()
        window.dirty=False;window.close();timer.stop();QTimer.singleShot(3500,lambda:app.exit(1))


timer=QTimer();timer.setInterval(350);timer.timeout.connect(tick);timer.start()
sys.exit(app.exec())
