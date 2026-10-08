"""Windows visible: dos barridos UX reales y una cancelación breve; no campaña científica."""
import argparse,json,os,sys,time
from pathlib import Path
from unittest.mock import patch
parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);parser.add_argument('--cancel-only',action='store_true');args=parser.parse_args()
os.environ['QT_QPA_PLATFORM']='windows';os.environ['QT_SCALE_FACTOR']='1'
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PySide6.QtCore import QTimer,Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont
from motorsim.window import MainWindow
from motorsim.examples import example_project
from motorsim.sweep import load_sweep
args.output.mkdir(parents=True,exist_ok=False)
app=QApplication([]);app.setFont(QFont('Segoe UI',10));w=MainWindow();w.resize(1350,800);w.move(20,20);w.show();w.raise_();w.activateWindow()
p=w.performance_page;v=w.simulation_view;phase='cancel-start' if args.cancel_only else '2T-start';started=time.monotonic();captures=[];checks=[];runs={};during=False

def capture(name):
    QTest.qWait(150);frame=w.frameGeometry();path=args.output/(name+'.png')
    assert w.screen().grabWindow(0,frame.x(),frame.y(),frame.width(),frame.height()).save(str(path))
    captures.append(str(path));print('CAPTURE',path,flush=True)

def record():
    (args.output/'evidence.json').write_text(json.dumps(dict(automated=True,manual_acceptance=False,real_worker=True,
        checks=checks,captures=captures,runs=runs,wall_seconds=time.monotonic()-started),ensure_ascii=False,indent=2),encoding='utf-8')

def tick():
    global phase,during
    try:
        assert time.monotonic()-started<390,'Límite del recorrido UX'
        if phase in ('2T-start','4T-start'):
            cycle=phase[:2];w._activate(example_project(cycle.lower()+'-reference'),None);w.navigation.go('performance')
            assert p.sweep is None and p.calculate_button.isVisible() and not v.active
            p.verticalScrollBar().setValue(0);capture(cycle+'-sin-calcular')
            target=args.output/('barrido-'+cycle)
            with patch('motorsim.simulation_view.new_output_path',return_value=target):
                if cycle=='2T':QTest.mouseClick(p.calculate_button,Qt.MouseButton.LeftButton)
                else:
                    w.navigation.go('simulation');v.origin_combo.setCurrentIndex(1);v.mode_combo.setCurrentIndex(1)
                    QTest.mouseClick(v.run_button,Qt.MouseButton.LeftButton);w.navigation.go('performance')
            assert v.active and '--sweep-input' in v.process.arguments()
            phase=cycle+'-running';during=False
        elif phase.endswith('-running'):
            cycle=phase[:2]
            if v.active and v.completed_cycles>0 and not during:
                capture(cycle+'-calculando');during=True
            if not v.active:
                assert v.sweep is not None,v.error_label.text()
                result=load_sweep(args.output/('barrido-'+cycle)/'series.json')
                runs[cycle]=dict(state=result['index']['state'],integration_seconds=result['index']['integration_seconds'],path=str(result['path']))
                assert result['index']['state']=='converged',runs[cycle]
                if cycle=='2T':assert w.navigation.current=='performance'
                w.navigation.go('performance');assert p.sweep is v.sweep and len(p.rows)==3
                p.verticalScrollBar().setValue(0);capture(cycle+'-terminado')
                p.ensureWidgetVisible(p.main_plot);capture(cycle+'-curva')
                assert p.horizontalScrollBar().maximum()==0
                checks.append(cycle+': barrido real persistido, progreso, carga automática, sin diálogo; origen '+('Rendimiento' if cycle=='2T' else 'Simulación'))
                record();phase='4T-start' if cycle=='2T' else 'cancel-start'
        elif phase=='cancel-start':
            w._activate(example_project('2t-compression'),None);w.navigation.go('performance')
            assert p.sweep is None and not p.main_plot.rows
            p.calculate(output=args.output/'cancelado');assert v.active
            p.cancel_button.click();phase='cancel-wait'
        elif phase=='cancel-wait' and not v.active:
            assert v.cancel_requested and not v.forced
            assert p.calculate_button.isVisible() and p.calculate_button.isEnabled()
            checks.append('Cambiar ejemplo retira curvas incompatibles; cancelación cooperativa real')
            runs['cancel']=dict(state=v.state_label.text(),error=v.error_label.text())
            capture('cancelado');record();w.dirty=False;w.close();app.quit();return
    except Exception:
        import traceback;error=traceback.format_exc();print(error,flush=True);(args.output/'failure.txt').write_text(error,encoding='utf-8');record()
        if v.active:v.cancel()
        app.exit(1);return
    QTimer.singleShot(200,tick)
QTimer.singleShot(300,tick);sys.exit(app.exec())
