"""Recorrido visual Windows nativo; consultas históricas, sin integrar física."""
import argparse,json,os,sys
from pathlib import Path
from dataclasses import replace
p=argparse.ArgumentParser();p.add_argument('--width',type=int,default=1366);p.add_argument('--height',type=int,default=768)
p.add_argument('--output',type=Path,required=True);args=p.parse_args()
os.environ['QT_QPA_PLATFORM']='windows'
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont
from PySide6.QtCore import QTimer
from PySide6.QtTest import QTest
from motorsim.window import MainWindow
from motorsim.simulation_case import geometry
from motorsim.four_stroke import geometry as geometry4
from motorsim.external_data import prepare_import,declarations,DEFINITIONS,save_import
from motorsim.sweep import load_sweep
app=QApplication([]);app.setFont(QFont('Segoe UI',10))
w=MainWindow();w.resize(args.width,args.height);w.show();args.output.mkdir(parents=True,exist_ok=True)
root=Path(__file__).resolve().parents[1];historical=root/'results/simulacion-2t/cuatro-tiempos-20260916/R2'
captures=[]
def capture(name):
    QTest.qWait(100);app.processEvents();w.repaint();app.processEvents()
    path=args.output/(name+'.png');assert w.grab().save(str(path));captures.append(str(path));print('CAPTURE',path,flush=True)
def run():
    try:
        for key in ('summary','simulation','results','compare','external'):
            w.navigation.go(key);capture(key+'-vacio')
        w._activate(replace(geometry(),name='PRUEBA SINTÉTICA 2T — no medida'),None)
        w.navigation.go('summary');capture('resumen-2t')
        w.navigation.go('motor2');capture('motor-2t')
        w.navigation.go('geometry');capture('geometria-2t')
        w._activate(replace(geometry4(),name='PRUEBA SINTÉTICA 4T — no medida'),None)
        w.navigation.go('summary');capture('resumen-4t')
        w.navigation.go('motor4');capture('motor-4t')
        w.navigation.go('simulation');w.simulation_view.origin_combo.setCurrentIndex(1);capture('simulacion')
        w.simulation_view.open_result(path=historical/'gui-sweep/point-02/manifest.json')
        w.navigation.go('simulation');capture('simulacion-convergida')
        w.simulation_view.verticalScrollBar().setValue(w.simulation_view.verticalScrollBar().maximum());capture('simulacion-contexto')
        w.navigation.go('results');capture('resultados')
        w.simulation_view.open_sweep(path=historical/'gui-sweep/series.json');capture('barrido')
        w.navigation.go('compare');w.comparison_page.select_result(0,path=historical/'gui-sweep/point-02/manifest.json')
        w.comparison_page.select_result(1,path=historical/'gui-compression/manifest.json');capture('comparacion')
        raw=b'rpm,value\n2500,52\n3000,50\n'
        data=prepare_import(raw,declarations('W_C_4T_J','J/ciclo',DEFINITIONS['W_C_4T_J'],'Ejemplo sintético',name='PRUEBA SINTÉTICA, no medida'))
        folder=args.output/'externo';ext=save_import(folder,data)
        w.external_page.external=ext;w.external_page.sweep=load_sweep(historical/'gui-sweep/series.json');w.external_page.refresh()
        w.navigation.go('external');capture('externos')
        w.external_page.tabs.setCurrentIndex(1);capture('externos-curvas')
        w.navigation.pages['external'].verticalScrollBar().setValue(w.navigation.pages['external'].verticalScrollBar().maximum());capture('externos-curvas-inferior')
        w.navigation.go('results');w.result_workspace.show_result()
        w.simulation_view.open_result(path=historical/'gui-sweep/point-02/manifest.json')
        w.simulation_view.result_tabs.setCurrentIndex(1);capture('resultados-curvas')
        area=w.result_workspace.tabs.widget(0);area.verticalScrollBar().setValue(area.verticalScrollBar().maximum());capture('resultados-curvas-inferior')
        assert not w.simulation_view.active
        (args.output/'evidence.json').write_text(json.dumps(dict(automated=True,manual_acceptance=False,platform=app.platformName(),
            scale=os.environ.get('QT_SCALE_FACTOR','1'),logical_size=[w.width(),w.height()],screen_pixels=[app.primaryScreen().size().width(),app.primaryScreen().size().height()],
            capture_method='QWidget.grab de ventana Qt Windows real; ancho grande puede exceder escritorio visible',captures=captures),ensure_ascii=False,indent=2),encoding='utf-8')
    except Exception:
        import traceback;traceback.print_exc();app.exit(1);return
    w.dirty=False;w.close();app.quit()
QTimer.singleShot(400,run);sys.exit(app.exec())
