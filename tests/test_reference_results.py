"""Archivos del caso de referencia: validación y conservación de diagnóstico."""
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from motorsim.reference_results import (PROFILE, ResultError, load_result, reference_inputs, save_result)
from motorsim.simulation import Model, sample, audit, CV


def diagnostic(folder):
    model = Model(external_band_pa=100)
    y = model.initial_state()
    row = sample(180., y, model.evaluate(180., y)[1])
    result = dict(profile=asdict(PROFILE), cycles=[], converged=False, seconds=.1,
        peak_process_MiB=25., stop='cancelación solicitada', last_two_cycles=[],
        partial=dict(samples=[row], state=y[:12]))
    save_result(folder, result, 'cancelled', reference_inputs(), {})
    return folder/'manifest.json'


def edit_payload(folder, name, mutate):
    path = folder/name
    data = json.loads(path.read_text(encoding='utf-8'))
    mutate(data)
    path.write_text(json.dumps(data), encoding='utf-8')
    manifest = folder/'manifest.json'
    m = json.loads(manifest.read_text(encoding='utf-8'))
    m['files'][name] = hashlib.sha256(path.read_bytes()).hexdigest()
    manifest.write_text(json.dumps(m), encoding='utf-8')


class ReferenceResultTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.folder = Path(self.directory.name)
        self.path = diagnostic(self.folder)

    def test_reopens_cancelled_diagnostic_without_computing(self):
        result = load_result(self.path)
        self.assertEqual(result['status'], 'cancelled')
        self.assertFalse(result['result']['converged'])
        self.assertEqual(len(result['samples']['partial']), 1)

    def test_rejects_wrong_units_and_cross_linked_files(self):
        data = json.loads(self.path.read_text())
        data['units']['pressure'] = 'bar'
        self.path.write_text(json.dumps(data))
        with self.assertRaises(ResultError):
            load_result(self.path)
        diagnostic(self.folder)
        data = json.loads(self.path.read_text())
        data['version'] = True
        self.path.write_text(json.dumps(data))
        with self.assertRaises(ResultError):
            load_result(self.path)
        diagnostic(self.folder)
        edit_payload(self.folder, 'samples.json', lambda d: d.update(run_id='otro'))
        with self.assertRaises(ResultError):
            load_result(self.path)

    def test_rejects_nonfinite_and_incoherent_inventory(self):
        for value in (float('nan'), -1, '100', True):
            with self.subTest(value=value):
                diagnostic(self.folder)
                edit_payload(self.folder, 'samples.json', lambda d: d['partial'][0]['state'].__setitem__(0, value))
                with self.assertRaises(ResultError):
                    load_result(self.path)

    def test_rejects_false_success_wrong_case_and_file_names(self):
        edit_payload(self.folder, 'summary.json', lambda d: d.update(status='converged'))
        with self.assertRaises(ResultError):
            load_result(self.path)
        diagnostic(self.folder)
        edit_payload(self.folder, 'case.json', lambda d: d['inputs']['case']['project_geometry'].update(cylinder_count=True))
        with self.assertRaises(ResultError):
            load_result(self.path)
        diagnostic(self.folder)
        edit_payload(self.folder, 'case.json', lambda d: d['inputs']['variant'].update(delta_p_Pa=50))
        with self.assertRaises(ResultError):
            load_result(self.path)
        diagnostic(self.folder)
        m = json.loads(self.path.read_text())
        m['files']['../otro.json'] = m['files'].pop('case.json')
        self.path.write_text(json.dumps(m))
        with self.assertRaises(ResultError):
            load_result(self.path)

    def test_hash_and_missing_files(self):
        (self.folder/'case.json').write_text('{}')
        with self.assertRaises(ResultError):
            load_result(self.path)
        (self.folder/'case.json').unlink()
        with self.assertRaises(ResultError):
            load_result(self.path)

    def test_rejects_malformed_balances_and_negative_peak(self):
        from motorsim.reference_results import _cycle, _samples
        model = Model(external_band_pa=100)
        y = model.initial_state()
        snapshot = model.evaluate(180, y)[1]
        cycle = dict(cycle=1, state=y[:12], Y=[n[2] for n in snapshot[0]], net_link_mass_kg=[0]*6,
            W_C_J=0, W_K_J=0, p_max_Pa=140000, F_s_kg=0, Q_J=0, converted_kg=0,
            discrete=audit(y,y,y), independent=audit(y,y,y), balances_passed=True,
            convergence={'passed': False})
        cycle['independent'] = list(CV)+['global']
        with self.assertRaises(ResultError):
            _cycle(cycle, 1)
        cycle['independent'] = cycle['discrete']
        cycle['p_max_Pa'] = -1
        with self.assertRaises(ResultError):
            _cycle(cycle, 1)
        cycle['p_max_Pa'] = 100000
        rows=[]
        for i in range(721):
            angle=180+i*.5
            state=[]
            for (pressure, temperature, fresh), volume in zip(model.case.initial_pty, model.geometry(angle)[0]):
                mass=pressure*volume/(model.case.gas_r*temperature)
                state.extend((mass, mass*model.cv*temperature, mass*fresh))
            state += [0.] * (len(y)-12)
            rows.append(sample(angle,state,model.evaluate(angle,state)[1]))
        rows=json.loads(json.dumps(rows))
        with self.assertRaisesRegex(ResultError, 'inferior a las muestras'):
            _samples(rows, True, cycle)


if __name__ == '__main__':
    unittest.main()
