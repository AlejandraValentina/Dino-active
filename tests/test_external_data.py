"""Fixtures aritméticos declarados; no mediciones ni simulaciones aceptadas."""
from copy import deepcopy
import csv
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from PySide6.QtCore import QProcess
from PySide6.QtWidgets import QApplication, QDialog

from motorsim.external_data import (DEFINITIONS, ExternalDataError, declarations, parse_csv,
    prepare_import, save_import, load_import, contrast, export_contrast)
from motorsim.external_view import ExternalDialog, ImportDialog
from motorsim.comparison import ComparisonError
from motorsim.reference_results import project_inputs
from motorsim.simulation_case import SyntheticCase
from motorsim.sweep import load_sweep
from motorsim.window import MainWindow


RAW=b'rpm,value\n2500,10\n3000,20\n3500,-2\n'


def metadata(key='W_C_J',unit='J/ciclo',**texts):
    return declarations(key,unit,DEFINITIONS[key],**texts)


def fixture_sweep():
    """Valores unitarios 11/18/-1, jamás guardados como convergencia física."""
    project=SyntheticCase().project_geometry
    common=project_inputs(project,dict(kind='project',project_name=project.name,source_path=None,dirty=False),rpm=2500)
    return dict(index=dict(series_id='fixture-sweep-not-physical',common_inputs=common,
        points=[dict(rpm=rpm,state='converged',reason='fixture aritmético',run_id=f'fixture-{rpm}') for rpm in (2500,3000,3500)]),
        results=[dict(result=dict(cycles=[dict(W_C_J=value,p_max_Pa=1350000)])) for value in (11,18,-1)])


class ExternalParserTests(unittest.TestCase):
    def test_work_signs_bom_unsorted_and_outside_solver(self):
        raw=b'\xef\xbb\xbfrpm,value\r\n4000,-2\r\n1250,0\r\n2500,10\r\n'
        result=prepare_import(raw,metadata())
        self.assertEqual(result['raw'],raw)
        self.assertEqual([r['rpm'] for r in result['rows']],[1250,2500,4000])
        self.assertEqual([r['value'] for r in result['rows']],[0,10,-2])
        self.assertEqual([r['source_row'] for r in result['rows']],[3,4,2])

    def test_bar_conversion_and_original_preserved(self):
        rows=parse_csv(b'rpm,value\n3000,13.5\n',metadata('p_max_Pa','bar'))
        self.assertEqual(rows[0]['original'],Decimal('13.5'))
        self.assertEqual(rows[0]['value'],1350000)
        self.assertEqual(metadata('p_max_Pa','bar')['canonical_unit'],'Pa abs.')

    def test_malformed_headers_columns_and_no_data(self):
        for raw,row in ((b'',1),(b'RPM,value\n1,2',1),(b'rpm;value\n1;2',1),
                        (b'rpm,value,x\n1,2,3',1),(b'rpm,value\n',2),
                        (b'rpm,value\n1,2,3',2),(b'rpm,value\n1',2),
                        (b'rpm,value\n\n',2),(b'rpm,value\n"1,2',2)):
            with self.subTest(raw=raw),self.assertRaisesRegex(ExternalDataError,f'Fila {row}.*columna'):
                parse_csv(raw,metadata())
        with self.assertRaisesRegex(ExternalDataError,'UTF-8'):parse_csv(b'rpm,value\n1,\xff',metadata())

    def test_invalid_numbers_report_row_and_column(self):
        for bad in ('','NaN','nan','inf','Infinity','1/2','1+2','1_000','1 000','1e9999','1e-9999','__import__("os")'):
            for index,column in ((0,'rpm'),(1,'value')):
                cells=['2500','10'];cells[index]=bad
                # CSV quoting de la expresión no debe hacerla ejecutable.
                import io
                stream=io.StringIO();csv.writer(stream).writerows([['rpm','value'],cells])
                with self.subTest(bad=bad,column=column),self.assertRaisesRegex(ExternalDataError,f'Fila 2, columna {column}'):
                    parse_csv(stream.getvalue().encode(),metadata())
        for bad in ('0','-1'):
            with self.assertRaisesRegex(ExternalDataError,'rpm'):parse_csv(f'rpm,value\n{bad},10'.encode(),metadata())
        with self.assertRaisesRegex(ExternalDataError,'value'):parse_csv(b'rpm,value\n3000,"1,000"',metadata())

    def test_pressure_rejects_zero_negative_and_overflow(self):
        for value in ('0','-0','-1','1e308'):
            with self.subTest(value=value),self.assertRaisesRegex(ExternalDataError,'Fila 2, columna value'):
                parse_csv(f'rpm,value\n3000,{value}'.encode(),metadata('p_max_Pa','bar'))

    def test_duplicates_numeric_and_exact_decimal_identity(self):
        for other in ('2500','2500.0','2.5e3'):
            with self.assertRaisesRegex(ExternalDataError,'Fila 3, columna rpm.*duplicado'):
                parse_csv(f'rpm,value\n2500,1\n{other},2'.encode(),metadata())
        rows=parse_csv(b'rpm,value\n2500,1\n2500.00000000000000000001,2',metadata())
        self.assertNotEqual(rows[0]['rpm'],rows[1]['rpm'])

    def test_unknown_metadata_and_incompatible_definitions(self):
        meta=metadata()
        self.assertEqual(meta['provenance'],'No determinada')
        for field in ('name','source','engine','configuration','conditions','notes'):self.assertEqual(meta[field],'No informado')
        for key,unit,definition in (('power','kW','potencia'),('W_C_J','kW',DEFINITIONS['W_C_J']),
                ('W_C_J','J/ciclo','trabajo parcial'),('p_max_Pa','Pa','presión manométrica'),
                ('p_max_Pa','psi',DEFINITIONS['p_max_Pa'])):
            with self.assertRaises(ExternalDataError):declarations(key,unit,definition)
        meta['canonical_unit']='bar'
        with self.assertRaises(ExternalDataError):prepare_import(RAW,meta)


class ExternalPersistenceTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)

    def test_roundtrip_without_source_bytes_and_metadata(self):
        source=self.root/'source.csv';source.write_bytes(b'\xef\xbb\xbf'+RAW)
        meta=metadata(provenance='Ejemplo sintético',name='EJEMPLO SINTÉTICO',source='Control, no medición')
        loaded=save_import(self.root/'import',prepare_import(source.read_bytes(),meta))
        source.unlink()
        reopened=load_import(loaded['path'])
        self.assertEqual(reopened['raw'],b'\xef\xbb\xbf'+RAW)
        self.assertEqual(reopened['metadata'],meta);self.assertEqual(reopened['rows'],loaded['rows'])
        self.assertEqual(reopened['manifest']['dataset_id'],loaded['manifest']['dataset_id'])

    def test_revalidation_hash_rules_units_path_id_and_structure(self):
        saved=save_import(self.root/'import',prepare_import(RAW,metadata()))
        original=saved['manifest'];path=saved['path']
        for mutate in (lambda m:m.update(csv_file='../other.csv'),lambda m:m.update(dataset_id='wrong'),
            lambda m:m['metadata'].update(original_unit='kW'),lambda m:m['metadata'].update(definition='parcial'),
            lambda m:m['rules'].update(bar_to_pa=1),lambda m:m['metadata'].update(provenance='Medición verificada'),
            lambda m:m.update(version=True)):
            changed=deepcopy(original);mutate(changed);path.write_text(json.dumps(changed),encoding='utf-8')
            with self.assertRaises(ExternalDataError):load_import(path)
        path.write_text(json.dumps(original),encoding='utf-8')
        (path.parent/'original.csv').write_bytes(b'rpm,value\n2500,NaN\n')
        with self.assertRaisesRegex(ExternalDataError,'hash'):load_import(path)
        original['csv_sha256']=hashlib.sha256((path.parent/'original.csv').read_bytes()).hexdigest()
        path.write_text(json.dumps(original),encoding='utf-8')
        with self.assertRaisesRegex(ExternalDataError,'Fila 2'):load_import(path)

    def test_exclusive_destination_and_failed_metadata_write(self):
        prepared=prepare_import(RAW,metadata());folder=self.root/'exists';folder.mkdir()
        personal=folder/'original.csv';personal.write_bytes(b'NO TOCAR')
        with self.assertRaises(ExternalDataError):save_import(folder,prepared)
        self.assertEqual(personal.read_bytes(),b'NO TOCAR')
        with patch('motorsim.external_data.write_json',side_effect=OSError('fallo de disco')):
            with self.assertRaisesRegex(ExternalDataError,'fallo de disco'):save_import(self.root/'failed',prepared)
        self.assertFalse((self.root/'failed').exists())

    def test_required_independent_arithmetic_and_summary_source(self):
        saved=save_import(self.root/'import',prepare_import(RAW,metadata()))
        data=contrast(saved,fixture_sweep())
        self.assertEqual([r['difference'] for r in data['rows']],[1,-2,1])
        self.assertEqual([r['relative_percent'] for r in data['rows']],[10,-10,50])
        self.assertEqual(data['matches'],3)
        self.assertIn('Equivalencia de condiciones no acreditada',data['notice'])
        # No muestras de gráficos en fixture: usa únicamente resumen.

    def test_zero_unmatched_failure_and_no_interpolation(self):
        raw=b'rpm,value\n3500,0\n2500.00000000000000000001,7\n3000,20\n2000,2\n4000,4'
        saved=save_import(self.root/'import',prepare_import(raw,metadata()))
        sweep=fixture_sweep();sweep['index']['points'][1].update(state='not_converged',reason='presupuesto agotado')
        data=contrast(saved,sweep);rows={r['rpm']:r for r in data['rows']}
        self.assertEqual(data['matches'],1)
        self.assertEqual(rows[3500]['difference'],-1);self.assertIsNone(rows[3500]['relative_percent'])
        self.assertIsNone(rows[2500]['external']);self.assertEqual(rows[2500]['simulated'],11)
        for rpm in (2000,4000,Decimal('2500.00000000000000000001')):
            self.assertIsNone(rows[rpm]['simulated']);self.assertIsNone(rows[rpm]['difference'])
        self.assertIsNone(rows[3000]['simulated']);self.assertIsNone(rows[3000]['difference'])
        self.assertIn('not_converged',rows[3000]['state']);self.assertEqual(rows[3000]['reason'],'presupuesto agotado')

    def test_export_faithful_provenance_blanks_and_no_overwrite(self):
        saved=save_import(self.root/'import',prepare_import(b'rpm,value\n2500,0\n2000,-2',
            metadata(provenance='Ejemplo sintético',source='Fuente, "sintética"\nSin medición')))
        before=(saved['path'].read_bytes(),(saved['path'].parent/'original.csv').read_bytes())
        data=contrast(saved,fixture_sweep());folder=self.root/'csv';export_contrast(folder,data)
        with (folder/'contraste.csv').open(encoding='utf-8',newline='') as f:rows=list(csv.DictReader(f))
        self.assertEqual(len(rows),4)
        self.assertTrue(all(row['provenance']=='Ejemplo sintético' for row in rows))
        self.assertEqual(rows[0]['simulated'],'');self.assertEqual(rows[1]['relative_percent'],'')
        self.assertEqual(rows[1]['simulated_minus_external'],'11')
        self.assertEqual(rows[0]['source'],'Fuente, "sintética"\nSin medición')
        self.assertEqual(rows[0]['dataset_id'],saved['manifest']['dataset_id'])
        original=(folder/'contraste.csv').read_bytes()
        with self.assertRaises(ComparisonError):export_contrast(folder,data)
        self.assertEqual((folder/'contraste.csv').read_bytes(),original)
        self.assertEqual(before,(saved['path'].read_bytes(),(saved['path'].parent/'original.csv').read_bytes()))

    def test_existing_real_sweep_read_only_no_motor(self):
        path=Path('results/simulacion-2t/barrido-20260915/gui-sweep/series.json')
        if not path.exists():self.skipTest('Barrido local ausente; nunca sustituir ni ejecutar')
        sweep=load_sweep(path);before=path.read_bytes()
        saved=save_import(self.root/'import',prepare_import(RAW,metadata(provenance='Ejemplo sintético')))
        data=contrast(saved,sweep)
        self.assertEqual(data['matches'],3)
        self.assertEqual(data['rows'][0]['simulated'],Decimal('16.209291803030894'))
        self.assertEqual(data['rows'][0]['difference'],Decimal('6.209291803030894'))
        self.assertEqual(path.read_bytes(),before)


class ExternalWindowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.guard=patch.object(QProcess,'start',side_effect=AssertionError('No ejecutar motor'))
        self.start=self.guard.start();self.addCleanup(self.guard.stop)
        self.window=MainWindow();self.window.name_edit.setText('Editor con cambios propios')
        self.window.simulation_view.external_button.click();self.dialog=self.window.simulation_view.external_dialog

    def tearDown(self):
        self.start.assert_not_called();self.dialog.close();self.window.dirty=False;self.window.close()
        self.window.deleteLater();self.app.processEvents()

    def test_explicit_declaration_preview_invalidation_and_cancel(self):
        wizard=ImportDialog(RAW,self.dialog)
        self.assertEqual(wizard.provenance.currentText(),'No determinada')
        wizard.preview();self.assertIsNone(wizard.prepared);self.assertFalse(wizard.confirm_button.isEnabled())
        wizard.magnitude.setCurrentIndex(1);wizard.unit.setCurrentIndex(1)
        wizard.preview();self.assertIsNone(wizard.prepared)
        wizard.confirm_definition.setChecked(True);wizard.preview()
        self.assertEqual(wizard.preview_table.rowCount(),3);self.assertTrue(wizard.confirm_button.isEnabled())
        wizard.texts['source'].setText('Cambio posterior');self.assertIsNone(wizard.prepared)
        self.assertFalse(wizard.confirm_button.isEnabled())
        wizard.preview()
        with patch('motorsim.external_view.QFileDialog.getSaveFileName',return_value=('','')):wizard.confirm()
        self.assertIsNone(wizard.imported);wizard.reject()

    def test_import_confirm_roundtrip_unknown_conditions_and_previous_preserved(self):
        wizard=ImportDialog(RAW,self.dialog);wizard.magnitude.setCurrentIndex(1);wizard.unit.setCurrentIndex(1)
        wizard.confirm_definition.setChecked(True);wizard.preview();wizard.confirm(folder=self.root/'import')
        self.assertEqual(wizard.result(),QDialog.DialogCode.Accepted)
        self.dialog.open_import(path=wizard.imported['path']);previous=self.dialog.external
        source=self.root/'draft.csv';source.write_bytes(RAW)
        with patch('motorsim.external_view.ImportDialog.exec',return_value=QDialog.DialogCode.Rejected):
            self.dialog.import_csv(path=source)
        self.assertIs(self.dialog.external,previous)
        self.dialog.open_import(path=self.root/'bad.json');self.assertIs(self.dialog.external,previous)
        bad=ImportDialog(b'rpm,value\n2500,NaN',self.dialog)
        bad.magnitude.setCurrentIndex(1);bad.unit.setCurrentIndex(1);bad.confirm_definition.setChecked(True);bad.preview()
        self.assertIn('Fila 2',bad.error.text());self.assertFalse(bad.confirm_button.isEnabled());bad.reject()
        self.assertIn('No determinada',self.dialog.identity.text())
        self.assertIn('No informado',self.dialog.details.toPlainText())

    def test_contrast_export_preserves_project_and_uses_loaded_inputs(self):
        before=self.window.project();dirty=self.window.dirty
        imported=save_import(self.root/'import',prepare_import(RAW,metadata(provenance='Ejemplo sintético')))
        self.dialog.open_import(path=imported['path'])
        with patch('motorsim.external_view.load_sweep',return_value=fixture_sweep()):self.dialog.open_sweep(path='fixture')
        self.assertEqual(self.dialog.table.item(0,3).text(),'1')
        self.assertIn('3 coincidencias',self.dialog.status.text())
        self.assertIn('Ejemplo sintético',self.dialog.identity.text());self.assertIn('Geometría de la copia',self.dialog.details.toPlainText())
        self.dialog.export(folder=self.root/'export')
        self.assertTrue((self.root/'export/contraste.csv').exists())
        self.assertEqual(self.window.project(),before);self.assertEqual(self.window.dirty,dirty)
        previous=self.dialog.sweep
        self.dialog.open_sweep(path=self.root/'bad-series.json');self.assertIs(self.dialog.sweep,previous)
        self.assertTrue(self.dialog.export_button.isEnabled())
