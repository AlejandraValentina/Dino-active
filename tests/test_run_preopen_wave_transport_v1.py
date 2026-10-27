from pathlib import Path
from copy import deepcopy
import numpy as np
import pytest
from scripts.diagnostics import run_preopen_wave_transport_v1 as module

ROOT=Path(__file__).resolve().parents[1]/'results/predictive-reliability-v1'


def test_prepared_source_is_bound_without_integration(monkeypatch):
    monkeypatch.setattr(module.IntegratedEngine2T,'step',lambda *a,**k:pytest.fail('input check cannot integrate'))
    e,initial,binding=module.prepared(ROOT,'p0-176')
    assert e.crank_angle_unwrapped_deg==13680. and len(binding['prepared_input_sha256'])==64


def test_cell_energy_and_species_close_with_actual_wall_source():
    def state(rho,energy,species):return {'ducts':{'exhaust':[[rho,0.,energy,0.]]},'species':{'ducts':{'exhaust':[species]}}}
    a=state(1.,10.,[1.,0.,0.,0.]);b=state(1.5,11.5,[1.,0.,0.,.5])
    gas=np.array([[1.,0.,3.],[.5,0.,1.]]);species=np.array([[0.,0.,0.,1.],[0.,0.,0.,.5]])
    r=module.cell_balances(a,b,[1.],gas,species,np.array([.5]))
    assert r['maximum_normalized_residual']==0.


def test_detects_species_defect_even_if_mass_and_energy_close():
    state={'ducts':{'exhaust':[[1.,0.,1.,0.]]},'species':{'ducts':{'exhaust':[[1.,0.,0.,0.]]}}}
    bad={'ducts':state['ducts'],'species':{'ducts':{'exhaust':[[.9,0.,0.,.1]]}}}
    r=module.cell_balances(state,bad,[1.],np.zeros((2,3)),np.zeros((2,4)),np.zeros(1))
    assert r['maximum_normalized_residual']==pytest.approx(.1)


def test_cost_projection_uses_observed_grid_and_step_scaling():
    assert module.admission_estimate(100.,40.,88,352,.0625)==160.
    assert module.admission_estimate(100.,40.,88,176,.03125)==160.
    assert module.admission_estimate(100.,None,88,352,.0625)==100.


def test_unregistered_temporal_cap_is_rejected_before_writes(tmp_path):
    with pytest.raises(ValueError,match='unregistered'):module.run_case(ROOT,tmp_path/'out','p0-88',1.,float('inf'))
    assert not (tmp_path/'out').exists()


def test_passive_exhaust_markers_do_not_drive_preopening_gas_rhs(monkeypatch):
    monkeypatch.setattr(module.IntegratedEngine2T,'step',lambda *a,**k:pytest.fail('operator probe cannot integrate'))
    e,initial,binding=module.prepared(ROOT,'p0-88');before=e.snapshot();modified=deepcopy(e.state)
    path=next(p for p in e.ducts if p.id=='exhaust')
    modified['species']['ducts']['exhaust']=[(0.,0.,0.,q[0]*v) for q,v in zip(modified['ducts']['exhaust'],path.mesh.volumes)]
    kwargs=dict(angle=13680.,rpm=9000.,dt_s=.0625/(6*9000.),capture_trace=False)
    a=e._assemble(e.state,**kwargs);b=e._assemble(modified,**kwargs)
    assert module._json_evidence_equal(a['q'],b['q'])
    assert not module._json_evidence_equal(a['species']['ducts']['exhaust'],b['species']['ducts']['exhaust'])
    assert module._json_evidence_equal(e.snapshot(),before)
