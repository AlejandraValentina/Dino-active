from copy import deepcopy
import json
from pathlib import Path

import pytest

from motorsim.integrated_2t import IntegratedEngine2T
from motorsim.reference_harness.convergence import compare_cycles_v2,PeriodicDetectorV2
from scripts.diagnostics.checkpoint_periodicity_indicators_v1 import cycle_observations,diagnose

ROOT=Path('results/predictive-reliability-v1/mesh-refined-v1')


def snapshots():
    c=json.loads((ROOT/'configuration.json').read_text())
    e=IntegratedEngine2T.from_configuration_dict(c)
    a,b=[json.loads((ROOT/n).read_text()) for n in ('initial-checkpoint.json','checkpoint-360.json')]
    return e,a,b


def test_unchanged_observations_pass_but_two_cycles_do_not_establish_periodicity():
    e,a,b=snapshots()
    r1=cycle_observations(e,a,b,1);r2=deepcopy(r1);r2['cycle_index']=2
    assert compare_cycles_v2(r1,r2)['status']=='PASS'
    detector=PeriodicDetectorV2();detector.update(r1);detector.update(r2)
    assert detector.classification is None


@pytest.mark.parametrize('fault',['phase','configuration'])
def test_phase_or_identity_mismatch_is_rejected(fault):
    e,a,b=snapshots()
    if fault=='phase':b['crank_angle_unwrapped_deg']+=.1
    else:b['configuration_identity']['configuration_sha256']='0'*64
    with pytest.raises(ValueError):cycle_observations(e,a,b,1)


def test_species_difference_cannot_be_hidden_by_equal_work():
    e,a,b=snapshots();r1=cycle_observations(e,a,b,1)
    r2=deepcopy(r1);r2['cycle_index']=2
    r2['observables']['ducts']['exhaust'][0]['species_mass_fractions']=[0.,0.,1.,0.]
    r1['observables']['ducts']['exhaust'][0]['species_mass_fractions']=[1.,0.,0.,0.]
    assert compare_cycles_v2(r1,r2)['status']=='FAIL'


def test_native_diagnosis_uses_no_engine_steps(monkeypatch):
    def forbidden(*args,**kwargs):raise AssertionError('read-only diagnostic must not step')
    monkeypatch.setattr(IntegratedEngine2T,'step',forbidden)
    r=diagnose(ROOT)
    assert r['solver_steps']==0 and r['failed_count']>0
    assert r['comparison']['status']=='FAIL'
    assert r['periodicity_demonstrated'] is False
