"""Analítica independiente y consulta de históricos; sin integrar el solver."""
import csv,gc,json,math,os,tempfile,unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from PySide6.QtCore import QEvent,Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from motorsim.performance import indicated_output,result_metrics,sweep_metrics,export_performance_csv
from motorsim.reference_results import load_result,ResultError
from motorsim.sweep import load_sweep
from motorsim.sweep_view import export_sweep_csv
from motorsim.comparison import compare_results,export_csv,ComparisonError
from motorsim.window import MainWindow

ROOT=Path(__file__).resolve().parents[1]
TWO=ROOT/'results/simulacion-2t/barrido-20260915/gui-sweep/series.json'
FOUR=ROOT/'results/simulacion-2t/cuatro-tiempos-20260916/R2/gui-sweep/series.json'
COMP=FOUR.parent.parent/'gui-compression/manifest.json'

class DerivedTests(unittest.TestCase):
    def test_independent_analytic_two_and_four(self):
        for cycle,work in (('2T',2*math.pi),('4T',4*math.pi)):
            value=indicated_output(work,3000,cycle)
            self.assertAlmostEqual(value['indicated_torque_Nm'],1,places=14)
            self.assertAlmostEqual(value['indicated_power_W'],100*math.pi,places=12)
    def test_invalid_and_signed_finite_work(self):
        for work,rpm,cycle in ((1,0,'2T'),(1,-1,'2T'),(1,True,'2T'),(1,'3000','2T'),(1,float('nan'),'4T'),(1,float('inf'),'4T'),(1,3000,'6T'),(float('nan'),3000,'2T'),(float('inf'),3000,'4T'),(True,3000,'2T'),(1e308,3000,'2T')):
            with self.subTest(args=(work,rpm,cycle)),self.assertRaises(ResultError):indicated_output(work,rpm,cycle)
        self.assertEqual(indicated_output(0,3000,'2T')['indicated_power_W'],0)
        self.assertLess(indicated_output(-2*math.pi,3000,'2T')['indicated_torque_Nm'],0)
    def test_preserved_results_exact_inputs_and_no_mutation(self):
        for path in (TWO,FOUR):
            sweep=load_sweep(path);before=deepcopy(sweep);rows=sweep_metrics(sweep)
            for row,result in zip(rows,sweep['results']):
                if row['metrics'] is None:continue
                last=result['result']['cycles'][-1];m=row['metrics'];four=m['cycle']=='4T'
                self.assertEqual(m['W_C_J'],last['W_C_J']);self.assertEqual(m['p_max_Pa'],last['p_max_Pa'])
                self.assertAlmostEqual(m['indicated_power_W'],last['W_C_J']*m['rpm']/(120 if four else 60),places=11)
                self.assertAlmostEqual(m['indicated_torque_Nm'],last['W_C_J']/(math.pi*(4 if four else 2)),places=12)
            self.assertEqual(sweep,before)
        result=load_result(COMP);value=result_metrics(result)
        self.assertAlmostEqual(value['indicated_power_W']/1000,1.273873,places=6)
        self.assertAlmostEqual(value['indicated_torque_Nm'],4.054862,places=6)
    def test_failed_points_and_mixed_cycle_rejected(self):
        sweep=load_sweep(TWO);sweep['index']['points'][1].update(state='error',reason='DOBLE fallo de prueba')
        sweep['results'][1]=None;rows=sweep_metrics(sweep);self.assertIsNone(rows[1]['metrics'])
        self.assertIsNotNone(rows[0]['metrics']);self.assertIsNotNone(rows[2]['metrics'])
        sweep['results'][0]['inputs']['case']['project_geometry']['cycle']='4T'
        with self.assertRaises(ResultError):sweep_metrics(sweep)
    def test_comparison_swap_and_csv_precision(self):
        a=load_sweep(FOUR)['results'][1];b=load_result(COMP)
        ab,ba=compare_results(a,b),compare_results(b,a)
        for key in ('indicated_power_W','indicated_torque_Nm'):
            left=next(r for r in ab['metrics'] if r['magnitude']==key);right=next(r for r in ba['metrics'] if r['magnitude']==key)
            self.assertEqual(left['a'],result_metrics(a)[key]);self.assertEqual(left['difference'],-right['difference'])
            self.assertEqual(left['relative_percent'],100*(left['b']-left['a'])/abs(left['a']))
        altered=deepcopy(b);altered['inputs']['case']['rpm']=2500
        with self.assertRaises(ComparisonError):compare_results(a,altered)
        with tempfile.TemporaryDirectory() as root:
            export_csv(Path(root)/'compare',ab)
            with (Path(root)/'compare/resumen.csv').open(encoding='utf-8') as f:data=list(csv.DictReader(f))
            for key in ('indicated_power_W','indicated_torque_Nm'):
                row=next(r for r in data if r['magnitude']==key);self.assertEqual(float(row['value_A']),result_metrics(a)[key])
    def test_performance_and_series_exports_no_fake_zeros(self):
        sweep=load_sweep(TWO);sweep['index']['points'][1].update(state='cancelled',reason='DOBLE cancelado');sweep['results'][1]['status']='cancelled'
        with tempfile.TemporaryDirectory() as root:
            for function,name in ((export_performance_csv,'rendimiento.csv'),(export_sweep_csv,'serie.csv')):
                folder=Path(root)/name;function(folder,sweep)
                with (folder/name).open(encoding='utf-8') as f:rows=list(csv.DictReader(f))
                for key in ('indicated_power_W','indicated_torque_Nm'):
                    self.assertEqual(float(rows[0][key]),result_metrics(sweep['results'][0])[key]);self.assertEqual(rows[1][key],'')

class PerformanceUITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
    def setUp(self):self.w=MainWindow();self.w.show();self.app.processEvents()
    def tearDown(self):
        self.w.dirty=False;self.w.close();self.w.deleteLater()
        self.app.sendPostedEvents(None,QEvent.Type.DeferredDelete);self.app.processEvents();gc.collect()
    def test_empty_navigation_and_reuse_no_worker(self):
        w=self.w;p=w.performance_page
        with patch('motorsim.simulation_view.QProcess') as process:
            w.navigation.go('performance');self.assertIsNone(p.sweep);self.assertFalse(p.export_button.isEnabled())
            w.simulation_view.sweep=load_sweep(TWO);w.navigation.go('performance');p.reuse_button.click()
            self.assertEqual(p.table.rowCount(),3);process.assert_not_called()
            w.cycle_combo.setCurrentText('4T');self.assertIsNone(p.sweep);self.assertFalse(p.rows)
    def test_both_cycles_point_selection_detail_results_and_keyboard(self):
        w=self.w;p=w.performance_page
        for path,cycle in ((TWO,'2T'),(FOUR,'4T')):
            w.navigation.go('performance');p.open_sweep(path=path);p.table.selectRow(1)
            self.assertIn('3000 rpm',p.detail.text());self.assertIn('Par indicado equivalente',p.detail.text())
            p.main_plot.setFocus();QTest.keyClick(p.main_plot,Qt.Key.Key_End);self.assertEqual(p.table.currentRow(),2)
            p.point_button.click();self.assertEqual(w.navigation.current,'results')
            v=w.simulation_view;self.assertIn('Potencia indicada',v.summary_label.text());self.assertEqual(v.inputs['case']['project_geometry']['cycle'],cycle)
    def test_failed_gap_cannot_open_and_valid_replacement_preserved_on_error(self):
        p=self.w.performance_page;sweep=load_sweep(TWO)
        sweep['index']['points'][1].update(state='error',reason='DOBLE error');sweep['results'][1]=None;p.set_sweep(sweep)
        p.table.selectRow(1);self.assertFalse(p.point_button.isEnabled());self.assertEqual(p.table.item(1,3).text(),'—')
        segments=p.main_plot.series_segments('indicated_power_W',1000);self.assertEqual([len(s) for s in segments],[1,1])
        p.open_sweep(path=ROOT/'no-existe/series.json');self.assertIs(p.sweep,sweep);self.assertIn('selección anterior',p.error.text())
    def test_compact_layout_and_csv(self):
        w=self.w;p=w.performance_page;w.resize(900,650);w.navigation.go('performance');p.open_sweep(path=FOUR);QTest.qWait(50)
        self.assertEqual(p.horizontalScrollBar().maximum(),0)
        with tempfile.TemporaryDirectory() as root:
            p.export(folder=Path(root)/'export');self.assertTrue((Path(root)/'export/rendimiento.csv').is_file())

if __name__=='__main__':unittest.main()
