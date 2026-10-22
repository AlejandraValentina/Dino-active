"""Display-format/integrity fixture, not simulated scientific evidence."""
from motorsim.engineering_point import atomic
from motorsim.engineering_workflow import import_desktop_runs,SCHEMA
import pytest


def test_engineering_samples_are_hash_bound_and_transients_do_not_become_curves(tmp_path):
    folder=tmp_path/"invocation-001";folder.mkdir()
    c=dict(cycle=2,mechanical_estimate=None,imep_Pa=100,indicated_power_W=10,indicated_torque_Nm=.1,
        conservation=dict(relative=dict(mass=0,energy=0,species=0)),cylinder_work_J=1,crankcase_work_J=-.1,
        chemical_heat_J=2,fuel_burned_kg=1e-8,afr_trapped=12,
        closure_snapshots=dict(exhaust=dict(cylinder_species_kg=[1e-5,1e-6,0,0])))
    sample=dict(angle_deg=0,pressures_Pa=dict(cylinder=100000,exhaust_entry=101000),mass_flow_kg_s=dict(exhaust=.01))
    c['diagnostic_artifact_sha256']=atomic(folder/"cycle-002-diagnostics.json",dict(summary=c,samples=[sample]))
    diag=dict(cycles=[c],periodicity="NOT_EVALUATED",bindings=dict(rpm=9000,configuration_canonical_sha256='a'*64))
    diag_sha=atomic(folder/"manifest.json",diag)
    result=dict(schema=SCHEMA,attempt="invocation-001",diagnostic_manifest_sha256=diag_sha,
        bindings=dict(run_id='run',variant_label='base'),cycles_completed=2,classification='MAX_CYCLES_NONCONVERGED')
    result_sha=atomic(tmp_path/"result.json",result);atomic(tmp_path/"run.json",dict(result_sha256=result_sha))
    data=import_desktop_runs([tmp_path]);row=data['points'][0]
    assert row['periodicity']=='NOT_CONVERGED' and row['audit_recomputed'] is False
    assert row['indicated_power'] is None and row['transient_estimates']['indicated_power']==.01
    channel=data['traces'][0]['channels']['cylinder_pressure_pa']
    assert channel==dict(unit='Pa',values=[100000])
    (folder/"cycle-002-diagnostics.json").write_text('{}')
    with pytest.raises(ValueError,match='sample hash'):
        import_desktop_runs([tmp_path])
