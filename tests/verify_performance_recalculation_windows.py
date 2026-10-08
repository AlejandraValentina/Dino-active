"""Recorrido iterativo Windows solicitado, un ciclo por ejecución, sin repetir campañas."""
import argparse,hashlib,json,os,sys,time
from pathlib import Path
from unittest.mock import patch
parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);parser.add_argument('--cycle',choices=['2T','4T'],required=True);parser.add_argument('--inspect-final',action='store_true');args=parser.parse_args()
os.environ['QT_QPA_PLATFORM']='windows';os.environ['QT_SCALE_FACTOR']='1'
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PySide6.QtCore import QTimer,Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont
from motorsim.window import MainWindow
from motorsim.sweep import load_sweep
if not args.inspect_final:args.output.mkdir(parents=True,exist_ok=False)
app=QApplication([]);app.setFont(QFont('Segoe UI',10));w=MainWindow();w.resize(1350,800);w.move(20,20);w.show();w.raise_();w.activateWindow()
p=w.performance_page;v=w.simulation_view;phase='initial';started=time.monotonic();previous=None;preserved={};runs=[];captures=[];checks=[]

def capture(name,widget=None):
    if widget:p.ensureWidgetVisible(widget)
    else:p.verticalScrollBar().setValue(0)
    QTest.qWait(150);path=args.output/(name+'.png')
    # Capturar solo la ventana Qt visible; excluir notificaciones y otras apps superpuestas.
    assert not path.exists();assert w.grab().save(str(path))
    captures.append(str(path));print('CAPTURE',path,flush=True)

def record():
    (args.output/'evidence.json').write_text(json.dumps(dict(automated=True,manual_acceptance=False,real_worker=True,cycle=args.cycle,
        checks=checks,captures=captures,runs=runs,wall_seconds=time.monotonic()-started,previous_files_verified=len(preserved)),ensure_ascii=False,indent=2),encoding='utf-8')

def configure(end):
    edit=p.rpm_edits[1];p.ensureWidgetVisible(edit);edit.setFocus();edit.selectAll();QTest.keyClicks(edit,str(end));QTest.keyClick(edit,Qt.Key.Key_Tab)
    assert p.setup.isVisible() and p.calculate_button.isEnabled()

def start(name):
    with patch('motorsim.simulation_view.new_output_path',return_value=args.output/name):QTest.mouseClick(p.calculate_button,Qt.MouseButton.LeftButton)
    assert v.active and '--sweep-input' in v.process.arguments()
    assert p.setup.isVisible() and all(not e.isEnabled() for e in p.rpm_edits)
    assert not p.calculate_button.isEnabled()
    if previous is not None:
        assert p.sweep is previous and p.main_plot.isVisible()
        assert 'Resultado anterior' in p.plan_status.text()

def ended(name,cancelled=False):
    global previous
    loaded=load_sweep(args.output/name/'series.json');index=loaded['index']
    runs.append(dict(name=name,state=index['state'],rpms=index['rpms'],integration_seconds=index['integration_seconds'],path=str(loaded['path'])))
    assert all(hashlib.sha256(path.read_bytes()).hexdigest()==value for path,value in preserved.items())
    for f in loaded['path'].parent.rglob('*.json'):preserved[f]=hashlib.sha256(f.read_bytes()).hexdigest()
    assert all(e.isEnabled() for e in p.rpm_edits) and p.calculate_button.isEnabled()
    assert w.navigation.current=='performance' and p.setup.isVisible()
    if cancelled:
        assert index['state']=='cancelled' and p.sweep is previous
        assert 'Nuevo cálculo cancelado' in p.error.text() and p.rpm_edits[1].text()=='3500'
    else:
        assert index['state']=='converged' and p.sweep is v.sweep and p.sweep is not previous
        assert p.plan_matches_sweep(p.sweep) and p.calculate_button.text()=='Recalcular rendimiento'
        assert len(p.rows)==len(index['rpms']);previous=p.sweep
    checks.append(name+': controles disponibles, estado correcto, carpeta exclusiva y datos previos intactos');record()

def tick():
    global phase
    try:
        assert time.monotonic()-started<200,'Límite del recorrido por ciclo'
        if phase=='initial':
            w.load_example(args.cycle.lower()+'-reference');w.navigation.go('performance')
            if args.inspect_final:
                v.sweep=load_sweep(args.output/'run-3/series.json');p.sync_session()
                assert p.plan_matches_sweep(p.sweep) and p.setup.isVisible() and not v.active
                capture('10-final-reabierto-controles');capture('11-final-reabierto-curva',p.main_plot)
                (args.output/'inspection.json').write_text(json.dumps(dict(automated=True,manual_acceptance=False,platform=app.platformName(),capture='QWidget.grab de ventana real Windows; sin overlays ajenos',reopened=str(v.sweep['path']),new_calculations=0,captures=captures),ensure_ascii=False,indent=2),encoding='utf-8')
                w.dirty=False;w.close();app.quit();return
            assert p.sweep is None and p.calculate_button.isEnabled();capture('01-sin-curva')
            start('run-1');phase='first'
        elif phase=='first' and not v.active:
            ended('run-1');capture('02-primera-curva-controles');capture('03-primera-curva',p.main_plot)
            configure(3000);assert p.sweep is previous and not p.plan_matches_sweep(previous)
            capture('04-plan-modificado',p.plan_status);start('run-2');phase='second'
        elif phase=='second' and not v.active:
            ended('run-2');assert [r['rpm'] for r in p.rows]==[2500,3000]
            capture('05-segunda-curva-controles');configure(3500)
            start('cancel-3');phase='cancel-running'
        elif phase=='cancel-running' and v.completed_cycles>0:
            capture('06-recalculando-con-curva-anterior',p.plan_status)
            p.cancel_button.click();phase='cancel-wait'
        elif phase=='cancel-wait' and not v.active:
            ended('cancel-3',True);capture('07-cancelado-con-curva-anterior',p.plan_status)
            start('run-3');phase='third'
        elif phase=='third' and not v.active:
            ended('run-3');capture('08-tercera-curva-controles');capture('09-tercera-curva',p.main_plot)
            assert p.horizontalScrollBar().maximum()==0
            checks.append('Tres cálculos completos y una cancelación en la misma sesión sin cambiar de vista, recargar proyecto ni borrar archivos')
            record();w.dirty=False;w.close();app.quit();return
    except Exception:
        import traceback;error=traceback.format_exc();print(error,flush=True);(args.output/'failure.txt').write_text(error,encoding='utf-8');record()
        if v.active:v.cancel()
        app.exit(1);return
    QTimer.singleShot(200,tick)
QTimer.singleShot(300,tick);sys.exit(app.exec())
