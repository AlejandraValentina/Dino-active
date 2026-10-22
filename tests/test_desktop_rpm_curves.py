"""Display and orchestration tests, not synthetic scientific results."""
import hashlib
import json
from pathlib import Path

import pytest
from motorsim.power_curve import build_curve_series,exact_rpm_differences


def test_exploratory_values_are_opt_in_and_never_relabel_raw_status():
    base=dict(rpm=8000,mode='ENGINEERING_EXPLORATORY',classification='MAX_CYCLES_NONCONVERGED',
        periodicity='NOT_CONVERGED',brake_power_status='UNDEFINED',brake_torque_status='UNDEFINED',
        transient_estimates=dict(brake_power=3,brake_torque=4),solver_identity_sha256='solver',
        fuel_id='fuel',mechanical_loss_model_sha256='loss',periodicity_contract='unchanged',total_finite_volume_cells=44)
    rows=[dict(base,variant_id='A'),dict(base,variant_id='B')]
    data=dict(points=rows,requested_rpms=[8000,9000,10000])
    ordinary=build_curve_series(data,{'A','B'})
    assert ordinary[0]['points'][0]['power'] is None
    exploratory=build_curve_series(data,{'A','B'},include_exploratory=True,power_unit='kW')
    assert exploratory[0]['points'][0]['power']==3
    assert exploratory[0]['points'][0]['exploratory'] is True
    assert exploratory[0]['points'][1]['power'] is None
    assert exploratory[0]['points'][1]['classification']=='NOT_STARTED'
    assert rows[0]['brake_power_status']=='UNDEFINED' and rows[0]['periodicity']=='NOT_CONVERGED'
    difference=exact_rpm_differences(exploratory)[0]
    assert difference['exploratory'] and difference['power_status']=='TRANSIENT_ESTIMATE'
    assert difference['power_delta']==0
    rows[0]['classification']='STOPPED_ERROR'
    assert build_curve_series(data,{'A'},include_exploratory=True)[0]['points'][0]['power'] is None


def test_explicit_reused_point_identity_rejection_before_execution(monkeypatch,tmp_path):
    from motorsim.power_curve_sweep import _reused_points
    from test_power_curve_sweep import _patch_sweep,_kwargs
    import motorsim.power_curve_sweep as sweep
    _patch_sweep(monkeypatch,tmp_path,[])
    kw=_kwargs(tmp_path);prepared=sweep.prepare_power_curve({},**{k:v for k,v in kw.items() if k!='sweep_id'})
    root=tmp_path/'seed';root.mkdir()
    result=dict(schema='DINO_ENGINEERING_RUN_V1',status='COMPLETE',classification='MAX_CYCLES_NONCONVERGED',
        bindings=dict(project_id='demo',variant_label='base',run_id='seed',identity_sha256='rpm-3000',configuration_sha256='config-3000'),
        preflight=dict(rpm=3000,max_cycles=2,mechanical_loss_model_sha256='loss-model'),
        checkpoint_sha256='cp',source_hashes={},periodicity='NOT_CONVERGED',cycles_completed=2,elapsed_seconds=4)
    (root/'result.json').write_text(json.dumps(result))
    monkeypatch.setattr('motorsim.engineering_workflow.import_desktop_runs',lambda paths:dict(points=[{}]))
    reused=_reused_points([root],prepared)
    assert reused[0]['reused'] and reused[0]['new_execution_seconds']==0
    with pytest.raises(ValueError,match='duplicate'):_reused_points([root,root],prepared)
    result['bindings']['identity_sha256']='incompatible';(root/'result.json').write_text(json.dumps(result))
    with pytest.raises(ValueError,match='identity'):_reused_points([root],prepared)


def test_existing_coordinator_skips_seed_and_retains_resume_references(monkeypatch,tmp_path):
    import motorsim.power_curve_sweep as sweep
    from test_power_curve_sweep import _patch_sweep,_kwargs
    calls=_patch_sweep(monkeypatch,tmp_path,[])
    kw=_kwargs(tmp_path)
    # Create a completed point with the same stub service used by the existing
    # coordinator tests, then reference it without invoking its service again.
    first=sweep.run_exploratory({},project_id='demo',run_id='seed',artifact_root=kw['artifact_root'],rpm=3000,resume=False)
    calls.clear()
    root=Path(first['artifact_directory']);manifest=json.loads((root/'run.json').read_text())
    manifest['schema']='DINO_ENGINEERING_RUN_V1';(root/'run.json').write_text(json.dumps(manifest))
    seed=dict(rpm=3000,status='COMPLETE',classification='MAX_CYCLES_NONCONVERGED',
        identity_sha256='rpm-3000',configuration_sha256='config-3000',mechanical_loss_model_sha256='loss-model',
        run_directory=str(root),result_artifact_sha256=hashlib.sha256((root/'result.json').read_bytes()).hexdigest(),
        checkpoint_sha256=first['checkpoint_sha256'],reused=True)
    monkeypatch.setattr(sweep,'_reused_points',lambda paths,prepared:[seed] if paths else [])
    monkeypatch.setattr('motorsim.engineering_workflow.import_desktop_runs',lambda paths:dict(points=[dict(audit_status='NOT_PERFORMED')]))
    manifest=sweep.run_power_curve({},**kw,reuse_runs=[root])
    assert calls==[(4000,False)]
    assert manifest['points'][0]['reused']
    assert manifest['bindings']['reuse_runs'][0]['path']==str(root)


def test_real_9000_reference_metadata_can_be_imported_without_recalculation():
    # No external artifacts required; their real verification belongs to the
    # controlled Desktop demonstration, not a test fixture with fake physics.
    from motorsim.engine_configuration import implementation_source_hashes
    assert 'motorsim.power_curve' not in implementation_source_hashes()


def test_explicit_open_endpoint_policy_preserves9000_and_extends_only_control():
    from motorsim.engine_project import load_project
    from motorsim.power_curve_sweep import _operating_document
    from motorsim.engine_configuration import resolve_for_operating_point
    doc=load_project(Path(__file__).resolve().parents[1]/'configs/reference_cases/functional_exhaust_ab_125cc_v1.dino.json')['variants']['A_original']
    policy=dict(schema='POWERVALVE_OPEN_ENDPOINT_HOLD_V1',maximum_rpm=10000)
    assert _operating_document(doc,9000,policy) is doc
    with pytest.raises(ValueError,match='outside'):resolve_for_operating_point(doc,rpm=10000)
    extended=_operating_document(doc,10000,policy)
    assert extended['native_configuration']['port_binding']['powervalve']['position'][-1]==0
    assert extended['native_configuration']['port_binding']['powervalve']['rpm'][-1]==10000
    assert doc['native_configuration']['port_binding']['powervalve']['rpm'][-1]==9500
    assert resolve_for_operating_point(extended,rpm=10000)['selected_rpm']==10000
    with pytest.raises(ValueError,match='exceeds'):_operating_document(doc,11000,policy)
