"""Puerta de fase A: dominio candidato separado del contrato público."""
import json
from pathlib import Path
import unittest

from motorsim.examples import example_project
from motorsim.performance import indicated_output, sweep_metrics
from motorsim.project import ProjectError
from motorsim.reference_results import project_inputs, validated_model
from motorsim.rpm_domain import validate_rpm, validate_candidate_2t_rpm
from motorsim.sweep import plan_rpms, load_sweep

ROOT = Path(__file__).resolve().parents[1]


class DomainTests(unittest.TestCase):
    def test_candidate_is_not_public(self):
        for rpm in (1000, 15000):
            self.assertEqual(validate_candidate_2t_rpm(rpm), rpm)
            with self.assertRaises(ProjectError): validate_rpm(rpm, '4T')
        with self.assertRaises(ProjectError): validate_rpm(1000, '2T')
        self.assertEqual(validate_rpm(15000, '2T'), 15000)
        for rpm in (999, 15001, True, 1000., '1000', None):
            with self.assertRaises(ProjectError): validate_candidate_2t_rpm(rpm)

    def test_public_contract_and_plans_both_cycles(self):
        for cycle in ('2T', '4T'):
            for rpm in (2500, 3000, 3500): self.assertEqual(validate_rpm(rpm, cycle), rpm)
            for rpm in (2499, 15001 if cycle == '2T' else 3501, True, 3000., '3000'):
                with self.assertRaises(ProjectError): validate_rpm(rpm, cycle)
            self.assertEqual(plan_rpms(2500, 3500, 500, cycle), [2500, 3000, 3500])
            for args in ((1000,15000,500), (2500,3500,100), (2500,3500,300),
                         (2500,3500,0), (2500,3500,-500)):
                with self.assertRaises(ProjectError): plan_rpms(*args, cycle=cycle)
        with self.assertRaises(ProjectError): validate_rpm(3000, '6T')

    def test_project_worker_contract_both_cycles(self):
        for cycle in ('2t', '4t'):
            project=example_project(cycle+'-reference')
            origin=dict(kind='project',project_name=project.name,source_path=None,dirty=True)
            for rpm in (2500,15000 if cycle == '2t' else 3500):
                data=project_inputs(project,origin,rpm=rpm)
                self.assertEqual(validated_model(data)[0].case.rpm,rpm)
            for rpm in (1000,15001 if cycle == '2t' else 3501):
                with self.assertRaises(ProjectError): project_inputs(project,origin,rpm=rpm)

    def test_historical_readers_and_derivatives(self):
        for path in ('results/simulacion-2t/barrido-20260915/gui-sweep/series.json',
                     'results/simulacion-2t/cuatro-tiempos-20260916/R2/gui-sweep/series.json'):
            sweep=load_sweep(ROOT/path)
            self.assertEqual(sweep['index']['rpms'],[2500,3000,3500])
            self.assertEqual(len(sweep_metrics(sweep)),3)

    def test_campaign_3000_exact_scientific_regression(self):
        candidate=json.loads((ROOT/'results/rendimiento-dominio-2t-20260917/3000.json').read_text(encoding='utf-8'))['result']
        historical=json.loads((ROOT/'results/simulacion-2t/barrido-20260915/gui-sweep/point-02/summary.json').read_text(encoding='utf-8'))['result']
        samples=json.loads((ROOT/'results/simulacion-2t/barrido-20260915/gui-sweep/point-02/samples.json').read_text(encoding='utf-8'))
        self.assertEqual(candidate['last_two_cycles'],samples['cycles'])
        for field in ('cycles','converged','stop','actual_substep_deg','rhs_evaluations'):
            self.assertEqual(candidate[field],historical[field],field)
        for result in (candidate,historical):
            last=result['cycles'][-1]
            self.assertEqual(indicated_output(last['W_C_J'],3000,'2T'),
                dict(indicated_power_W=824.525375603044,indicated_torque_Nm=2.624545784638522))
