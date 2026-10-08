"""Recorrido Windows visible de Rendimiento con históricos, sin solver."""
import argparse,json,os,sys,hashlib
from pathlib import Path
parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True)
parser.add_argument('--width',type=int,default=1366);parser.add_argument('--height',type=int,default=768)
args=parser.parse_args();os.environ['QT_QPA_PLATFORM']='windows'
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont
from PySide6.QtCore import QTimer,Qt
from PySide6.QtTest import QTest
from motorsim.window import MainWindow
from motorsim.sweep import load_sweep
root=Path(__file__).resolve().parents[1];args.output.mkdir(parents=True,exist_ok=True)
app=QApplication([]);app.setFont(QFont('Segoe UI',10));w=MainWindow();w.resize(args.width,args.height);w.show()
files={'2T':root/'results/simulacion-2t/barrido-20260915/gui-sweep/series.json',
       '4T':root/'results/simulacion-2t/cuatro-tiempos-20260916/R2/gui-sweep/series.json'}
captures=[];checks=[]
def capture(name):
    QTest.qWait(100);path=args.output/(name+'.png');assert w.grab().save(str(path));captures.append(str(path));print('CAPTURE',path,flush=True)
def run():
    try:
        w.navigation.go('performance');p=w.performance_page;capture('rendimiento-vacio')
        for cycle,path in files.items():
            before={f:hashlib.sha256(f.read_bytes()).hexdigest() for f in path.parent.rglob('*.json')}
            p.open_sweep(path=path);w.navigation.go('performance');p.verticalScrollBar().setValue(0);capture(cycle+'-resumen')
            p.ensureWidgetVisible(p.main_plot);capture(cycle+'-combinado')
            p.main_plot.setFocus();QTest.keyClick(p.main_plot,Qt.Key.Key_Right)
            assert p.table.currentRow()==1 and '3000 rpm' in p.detail.text()
            capture(cycle+'-seleccion')
            p.ensureWidgetVisible(p.secondary[0]);capture(cycle+'-secundarios')
            p.ensureWidgetVisible(p.table);capture(cycle+'-tabla')
            assert p.horizontalScrollBar().maximum()==0
            p.point_button.click();assert w.navigation.current=='results';capture(cycle+'-resultado')
            assert 'Potencia indicada' in w.simulation_view.summary_label.text()
            w.navigation.go('performance');p.export(folder=args.output/('csv-'+cycle))
            assert (args.output/('csv-'+cycle)/'rendimiento.csv').exists()
            assert before=={f:hashlib.sha256(f.read_bytes()).hexdigest() for f in before}
            checks.append(cycle+': fuente preservada, detalle/teclado, punto, CSV, sin scroll horizontal global')
        w.simulation_view.sweep=load_sweep(files['2T']);w.navigation.go('performance');p.reuse_button.click()
        assert p.rows[0]['metrics']['cycle']=='2T';w.cycle_combo.setCurrentText('4T')
        assert p.sweep is None and not w.simulation_view.active
        checks.append('Consulta histórica explícita e invalidación al cambiar el proyecto; sin proceso')
        (args.output/'evidence.json').write_text(json.dumps(dict(automated=True,manual_acceptance=False,platform=app.platformName(),
            qt_scale=os.environ.get('QT_SCALE_FACTOR','1'),logical_size=[w.width(),w.height()],checks=checks,captures=captures),ensure_ascii=False,indent=2),encoding='utf-8')
    except Exception:
        import traceback;traceback.print_exc();app.exit(1);return
    w.dirty=False;w.close();app.quit()
QTimer.singleShot(300,run);sys.exit(app.exec())
