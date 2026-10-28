"""E2B planning and loss bookkeeping; no large numerical executions."""
from copy import deepcopy
import math
from pathlib import Path
import pytest
from motorsim.integrated_2t import IntegratedEngine2T
from motorsim.mechanical import MechanicalLossModel
from scripts.diagnostics.e2b_periodic_ab_v1 import estimate,performance,load,OUT


def test_output_binding_hashes_actual_detector_without_mutating_primary(monkeypatch):
    import hashlib,json
    import scripts.diagnostics.e2b_periodic_ab_v1 as driver
    class Detector:
        classification='PERIOD_1'
        def snapshot(self):return {'history':[{'cycle_index':30}],'classification':'PERIOD_1'}
    primary={'configuration_hash':'a'*64,'cycle_index':30,'trajectory':[]}
    before=deepcopy(primary)
    monkeypatch.setattr(driver,'make_integrated_engineering_output',lambda record,**kwargs:record)
    record=driver.bound_periodic_output(primary,Detector(),None)
    assert primary==before and record['trajectory'] is primary['trajectory']
    evidence=record['periodicity_evidence']
    assert evidence['terminal_cycle']==30 and evidence['configuration_hash']==primary['configuration_hash']
    assert evidence['detector_sha256']==hashlib.sha256(json.dumps(Detector().snapshot(),
        sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def test_viability_counts_both_variants_audits_and_reserves():
    p=estimate([13.3,13.5,14.])
    assert p['nominal_AB_solver_s']==1350
    assert p['conservative_total_s']==5400
    assert p['feasible'] and not p['B_cycles_known']
    assert not estimate([16.])['feasible']


def test_brake_work_uses_crankcase_and_friction_once():
    model=MechanicalLossModel.from_dict(load('configs/reference_cases/functional_exhaust_ab_125cc_v1.dino.json')['base_engine']['mechanical_loss_model'])
    start={'ledger':dict(cylinder_work_J=-500.,crankcase_work_J=50.)}
    end={'ledger':dict(cylinder_work_J=-630.,crankcase_work_J=53.)}
    r=performance(start,end,.000125,model)
    assert r['cylinder_indicated_work_j']==130
    assert r['crankcase_gas_work_j']==-3
    assert r['net_piston_gas_work_j']==127
    assert r['brake_work_j']==pytest.approx(127-.000125*85000)
    assert r['brake_power_w']==pytest.approx(r['brake_work_j']*150)
    assert r['brake_torque_nm']==pytest.approx(r['brake_work_j']/(2*math.pi))


@pytest.mark.parametrize('variant',['A','B'])
def test_independent_frozen_e2a_config_and_original_thresholds(variant):
    m=load(OUT/'manifest.json');c=load(m['configurations'][variant])
    e=IntegratedEngine2T.from_configuration_dict(c)
    assert e.crank_angle_unwrapped_deg==0
    assert e.configuration_dict()==c
    assert c['reference_rpm']==9000 and c['max_cfl']==.4
    assert sum(len(d['mesh']['volumes']) for d in c['ducts'])==44
    assert c['geometry_identity']['pipe_sections_mm'][0][0]==(83 if variant=='A' else 103)
    assert m['streak']==3
    assert m['thresholds']['duct_cell_species_mass_fraction_absolute']==.002
