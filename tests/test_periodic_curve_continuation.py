"""Coordinator-only tests with fake workers; not scientific evidence."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil

import pytest
import motorsim.power_curve_sweep as sweep
from test_power_curve_sweep import _patch_sweep,_kwargs


def test_explicit_order_is_bound_and_respected(monkeypatch,tmp_path):
    calls=_patch_sweep(monkeypatch,tmp_path,[])
    result=sweep.run_power_curve({},**_kwargs(tmp_path),execution_order=[4000,3000])
    assert calls==[(4000,False),(3000,False)]
    assert result['bindings']['execution_order']==[4000,3000]
    with pytest.raises(ValueError,match='binding mismatch'):
        sweep.run_power_curve({},**_kwargs(tmp_path),resume=True,execution_order=[3000,4000])


def test_invalid_order_takes_no_steps(monkeypatch,tmp_path):
    calls=_patch_sweep(monkeypatch,tmp_path,[])
    with pytest.raises(ValueError,match='permutation'):
        sweep.run_power_curve({},**_kwargs(tmp_path),execution_order=[3000,3000])
    assert not calls


def test_continuation_budget_excludes_but_preserves_historical_time(monkeypatch,tmp_path):
    _patch_sweep(monkeypatch,tmp_path,[])
    first=sweep.run_power_curve({},**_kwargs(tmp_path))
    source=tmp_path/'immutable-source';shutil.copytree(Path(first['points'][0]['run_directory']),source)
    original=(source/'result.json').read_bytes()
    seed=dict(first['points'][0],run_id='continued-seed',run_directory=str(source),elapsed_seconds=200.)
    monkeypatch.setattr(sweep,'_reused_points',lambda paths,prepared,**kwargs:[deepcopy(seed)] if paths else [])
    fake=sweep.run_exploratory;seen=[]
    def continued(document,**kw):
        seen.append((kw['rpm'],kw['resume'],kw['budget_seconds']))
        r=fake(document,**kw);r['elapsed_seconds']=203.;return r
    monkeypatch.setattr(sweep,'run_exploratory',continued)
    kw=dict(_kwargs(tmp_path),sweep_id='new-envelope')
    result=sweep.run_power_curve({},**kw,continuation_runs=[source])
    row=result['points'][0]
    assert seen[0][0:2]==(3000,True) and seen[0][2]>4
    assert row['historical_elapsed_seconds']==200 and row['elapsed_seconds']==203
    assert row['continuation_elapsed_seconds']==3
    assert (source/'result.json').read_bytes()==original
    assert row['run_directory']!=str(source)


def test_reference_horizon_extension_requires_explicit_continuation_or_periodic_evidence(monkeypatch,tmp_path):
    _patch_sweep(monkeypatch,tmp_path,[])
    kw=_kwargs(tmp_path);kw.pop('sweep_id');kw['max_cycles']=111
    prepared=sweep.prepare_power_curve({},**kw)
    root=tmp_path/'source';root.mkdir()
    r=dict(schema='DINO_ENGINEERING_RUN_V1',status='COMPLETE',classification='MAX_CYCLES_NONCONVERGED',
        bindings=dict(project_id='demo',variant_label='base',run_id='seed',identity_sha256='rpm-3000',configuration_sha256='config-3000'),
        preflight=dict(rpm=3000,max_cycles=30,mechanical_loss_model_sha256='loss-model'),
        checkpoint_sha256='cp',source_hashes={},periodicity='NOT_CONVERGED',cycles_completed=30,elapsed_seconds=200)
    monkeypatch.setattr('motorsim.engineering_workflow.import_desktop_runs',lambda paths:dict(points=[dict(periodicity='NOT_CONVERGED')]))
    def write():(root/'result.json').write_text(json.dumps(r))
    write()
    with pytest.raises(ValueError,match='horizon'):sweep._reused_points([root],prepared)
    assert sweep._reused_points([root],prepared,continuation=True)[0]['cycles_completed']==30
    r.update(classification='PERIODIC_EXPLORATORY',periodicity='PERIOD_1_OBSERVED_EXPLORATORY_UNAUDITED',cycles_completed=104)
    r['preflight']['max_cycles']=110;write()
    with pytest.raises(ValueError,match='diagnostic evidence'):sweep._reused_points([root],prepared)
    monkeypatch.setattr('motorsim.engineering_workflow.import_desktop_runs',lambda paths:dict(points=[dict(periodicity='PERIOD_1_OBSERVED_EXPLORATORY_UNAUDITED')]))
    assert sweep._reused_points([root],prepared)[0]['cycles_completed']==104
