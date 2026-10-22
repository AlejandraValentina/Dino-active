"""Small physical continuity fixtures and deterministic operational failures."""
import copy
import json
from pathlib import Path
import shutil
from types import SimpleNamespace

import pytest
from scripts.diagnostics import periodic_point_executor as point
from motorsim import exploratory_workflow as workflow
from motorsim._evidence_io import canonical_digest, read_primary
from motorsim.reference_harness.convergence import PeriodicDetectorV2
from test_exploratory_workflow import engine_document


@pytest.fixture(scope='module')
def continuity(tmp_path_factory):
    base=tmp_path_factory.mktemp('point-continuity')
    document=engine_document()
    common=dict(project_id='fixture',run_id='point',rpm=3000,max_cycles=2,
                budget_seconds=600,memory_limit_mib=1024)
    continuous=workflow.run_exploratory(document,artifact_root=base/'continuous',**common)
    one=workflow.run_exploratory(document,artifact_root=base/'fragmented',
        cycle_admission=lambda cycle:cycle==1,**common)
    assert one['cycles_completed']==1
    split=workflow.run_exploratory(document,artifact_root=base/'fragmented',resume=True,**common)
    return base,document,common,continuous,split


def test_real_continuous_fragmented_canonical_physics_detector_and_audits(continuity):
    base,document,common,continuous,split=continuity
    assert continuous['cycles_completed']==split['cycles_completed']==2
    assert [r['cycle'] for r in split['cycles']]==[1,2]
    assert [r['primary_sha256'] for r in continuous['cycles']]==[r['primary_sha256'] for r in split['cycles']]
    assert [r['conservation'] for r in continuous['cycles']]==[r['conservation'] for r in split['cycles']]
    cps=[]
    for label,result in [('continuous',continuous),('fragmented',split)]:
        root=base/label/'exploratory-workflow-v1/fixture/point'
        cp=point.read(root/result['checkpoint_artifact']); cps.append(cp)
        detector=PeriodicDetectorV2()
        for row in result['cycles']:
            primary=read_primary(root/row['artifact'],expected_sha256=row['primary_sha256'])
            assert row['audit']['status']=='PASS' and row['audit']['recomputed']
            detector.update({'cycle_index':row['cycle'],'configuration_hash':primary['configuration_hash'],
                'contract':workflow.CYCLE_PRIMARY_CONTRACT,'observables':primary['observables']})
        assert detector.snapshot()==cp['periodicity_snapshot']
    assert canonical_digest(cps[0])==canonical_digest(cps[1])


@pytest.mark.parametrize('damage',['corrupt','incompatible','orphan','detector'])
def test_real_resume_rejects_corrupt_incompatible_partial_or_wrong_detector(continuity,tmp_path,damage):
    base,document,common,_,split=continuity
    source=base/'fragmented/exploratory-workflow-v1/fixture/point'
    target=tmp_path/'exploratory-workflow-v1/fixture/point'
    shutil.copytree(source,target)
    manifest=point.read(target/'run.json'); cp_path=target/manifest['checkpoint_artifact']
    cp=point.read(cp_path)
    if damage=='corrupt':
        cp_path.write_bytes(b'{')
    elif damage=='orphan':
        (target/'cycle-0003.json.gz').write_bytes(b'incomplete')
    else:
        if damage=='incompatible':
            cp['bindings']['identity_sha256']='0'*64
        else:
            history=cp['periodicity_snapshot']['history']
            history[0]['observables']['work_J']+=1.0
            detector=PeriodicDetectorV2()
            for row in history: detector.update(row)
            cp['periodicity_snapshot']=detector.snapshot()
        workflow._atomic_write(cp_path,workflow._json_bytes(cp))
        manifest['checkpoint_sha256']=point.digest_file(cp_path)
        workflow._atomic_write(target/'run.json',workflow._json_bytes(manifest))
    with pytest.raises(ValueError,match='resume rejected'):
        workflow.run_exploratory(document,artifact_root=tmp_path,resume=True,**common)


@pytest.fixture
def prepared(tmp_path):
    root=tmp_path/'point'
    definition=point.prepare(root,engine_document(),horizon=2)
    auth=tmp_path/'authorization.json'
    point.atomic(auth,{'authorized':True,'definition_sha256':canonical_digest(definition)})
    return root,definition,auth


def test_preparation_is_zero_step_and_requires_separate_authorization(prepared,tmp_path):
    root,definition,auth=prepared
    assert definition['scientific_execution_authorized'] is False
    assert definition['preflight']['solver_steps']==0
    assert point.ledger(root)['charged_seconds']==0
    point.atomic(auth,{'authorized':False})
    with pytest.raises(ValueError,match='authorization'):point.invoke(root,auth)
    assert point.ledger(root)['entries']==[]


def test_identity_and_ledger_tamper_fail_closed(prepared):
    root,definition,auth=prepared
    doc=point.read(root/'document.json'); doc['display_name']='tampered'
    point.atomic(root/'document.json',doc)
    with pytest.raises(ValueError,match='identity'):point.validate(root)
    wrapped=point.read(root/'ledger.json'); wrapped['value']['charged_seconds']=0.01
    point.atomic(root/'ledger.json',wrapped)
    with pytest.raises(ValueError,match='ledger'):point.ledger(root)


@pytest.mark.parametrize('remaining',[0,149])
def test_global_budget_exhaustion_never_spawns(prepared,monkeypatch,remaining):
    root,definition,auth=prepared
    value=point.ledger(root)
    for i,charge in enumerate([600]*4+[600-remaining],1):
        value['entries'].append({'number':i,'state':'CLOSED','reservation_seconds':600,'charged_seconds':charge})
    value['charged_seconds']=3000-remaining; point.save_ledger(root,value)
    monkeypatch.setattr(point.psutil,'virtual_memory',lambda:SimpleNamespace(available=8*1024**3))
    monkeypatch.setattr(point,'bounded_process',lambda *a,**k:pytest.fail('spawn forbidden'))
    assert point.invoke(root,auth)['terminal']=='PARTIAL_RESOURCE_OR_TIME'


def test_insufficient_host_memory_does_not_reserve_or_spawn(prepared,monkeypatch):
    root,definition,auth=prepared
    monkeypatch.setattr(point.psutil,'virtual_memory',lambda:SimpleNamespace(available=1024))
    with pytest.raises(MemoryError):point.invoke(root,auth)
    assert point.ledger(root)['charged_seconds']==0


@pytest.mark.parametrize(('reason','code','terminal'),[
    ('TIMEOUT',1,'PARTIAL_RESOURCE_OR_TIME'),('RESOURCE',1,'PARTIAL_RESOURCE_OR_TIME'),
    (None,7,'FAIL_CLOSED_WORKER_ERROR')])
def test_supervised_failure_charged_and_terminal_no_retry(prepared,monkeypatch,reason,code,terminal):
    root,definition,auth=prepared
    monkeypatch.setattr(point.psutil,'virtual_memory',lambda:SimpleNamespace(available=8*1024**3))
    def bounded(*args,**kwargs):
        active=point.ledger(root)
        assert active['charged_seconds']==600 and active['entries'][-1]['state']=='ACTIVE'
        return {'exit_code':code,'stop_reason':reason}
    monkeypatch.setattr(point,'bounded_process',bounded)
    value=point.invoke(root,auth)
    assert value['terminal']==terminal and 10<=value['charged_seconds']<=600
    with pytest.raises(ValueError,match='no automatic retry'):point.invoke(root,auth)


def test_planned_invocations_accumulate_and_preserve_completed_cycle_count(prepared,monkeypatch):
    root,definition,auth=prepared
    monkeypatch.setattr(point.psutil,'virtual_memory',lambda:SimpleNamespace(available=8*1024**3))
    counts=iter((1,2))
    path=workflow._run_directory(root,point.PROJECT,point.RUN)
    path.mkdir(parents=True)
    def bounded(*args,**kwargs):
        cycle=next(counts)
        point.atomic(path/'run.json',{'cycles_completed':cycle})
        point.atomic(root/'worker-result.json',{'status':'COMPLETE','periodicity':'NOT_EVALUATED',
            'cycles_completed':cycle})
        return {'exit_code':0,'stop_reason':None}
    monkeypatch.setattr(point,'bounded_process',bounded)
    first=point.invoke(root,auth)
    assert first['terminal'] is None
    second=point.invoke(root,auth)
    assert second['terminal']=='PERIODICITY_NOT_IDENTIFIED'
    assert second['entries'][1]['cycles_before']==1
    assert second['charged_seconds']>first['charged_seconds']
    assert second['charged_seconds']==sum(e['charged_seconds'] for e in second['entries'])


def test_interrupted_supervisor_retains_full_reservation_and_recovers(prepared,monkeypatch):
    root,definition,auth=prepared
    monkeypatch.setattr(point.psutil,'virtual_memory',lambda:SimpleNamespace(available=8*1024**3))
    def crash(*a,**k):raise OSError('simulated supervisor interruption')
    monkeypatch.setattr(point,'bounded_process',crash)
    with pytest.raises(OSError):point.invoke(root,auth)
    assert point.ledger(root)['charged_seconds']==600
    value=point.ledger(root); value['entries'][-1]['supervisor_pid']=99999999
    point.save_ledger(root,value)
    recovered=point.recover(root)
    assert recovered['charged_seconds']==600 and recovered['terminal']=='PARTIAL_RESOURCE_OR_TIME'


def test_partial_persistence_keeps_reservation_or_old_ledger(prepared,monkeypatch):
    root,definition,auth=prepared
    before=(root/'ledger.json').read_bytes()
    def fail(*a,**k):raise OSError('fsync interrupted')
    monkeypatch.setattr(point,'atomic',fail)
    with pytest.raises(OSError):point.save_ledger(root,{'incomplete':True})
    assert (root/'ledger.json').read_bytes()==before


def test_real_windows_subprocess_worker_small_fixture(tmp_path):
    if point.psutil.virtual_memory().available < 4096*1024**2:
        pytest.skip('host launch guard: 4096 MiB available required')
    root=tmp_path/'real-worker'
    definition=point.prepare(root,engine_document(),horizon=1)
    auth=tmp_path/'auth.json'
    point.atomic(auth,{'authorized':True,'definition_sha256':canonical_digest(definition)})
    value=point.invoke(root,auth)
    assert value['terminal']=='PERIODICITY_NOT_IDENTIFIED'
    assert 0 < value['charged_seconds'] <= 600
    entry=value['entries'][0]
    assert entry['cycles_after']==1 and entry['outcome']['exit_code']==0
    result=point.read(root/'worker-result.json')
    assert result['cycles'][0]['audit']['recomputed'] is True
    assert result['cycles_completed']==1


def test_detector_continuity_includes_accepted_period1_and_period2():
    from test_v1_closure_periodicity import _record
    for periodic in (1,2):
        continuous=PeriodicDetectorV2(); resumed=PeriodicDetectorV2()
        records=[_record(i,0.0 if periodic==1 or i%2 else 1.0)
                 for i in range(1,5 if periodic==1 else 9)]
        for row in records: continuous.update(row)
        for row in records[:3]: resumed.update(row)
        restored=PeriodicDetectorV2(); restored.restore(resumed.snapshot())
        for row in records[3:]: restored.update(row)
        assert restored.snapshot()==continuous.snapshot()
        assert restored.classification==f'PERIOD_{periodic}'


@pytest.mark.parametrize(('status','period','cycles','expected'),[
    ('COMPLETE','NOT_EVALUATED',2,'PERIODICITY_NOT_IDENTIFIED'),
    ('INTERRUPTED_CHECKPOINTED','NOT_EVALUATED',1,'CONTINUE_AT_CHECKPOINT'),
    ('FAILED_CLOSED','NOT_EVALUATED',1,'NUMERICAL_OR_PHYSICAL_FAILURE'),
    ('COMPLETE','PERIOD_2',2,'PERIODICITY_OBSERVED_ENGINEERING_UNDEFINED'),
    ('COMPLETE','PERIOD_1',2,'PERIODIC_POINT_ACCEPTED')])
def test_scientific_classification_never_accepts_missing_metrics(status,period,cycles,expected):
    metrics={k:{'status':'DEFINED','value':1.0} for k in
        ('imep_pa','fmep_pa','bmep_pa','brake_power_w','brake_torque_nm')} if period=='PERIOD_1' else {}
    result={'status':status,'periodicity':period,'cycles_completed':cycles,
        'cycles':[{'engineering_output':{'cycle_metrics':metrics}}]}
    assert point.classification(result,2)==expected


def test_artifact_or_memory_limit_is_not_a_physics_failure():
    for kind in ('ARTIFACT_BUDGET_EXCEEDED','RESOURCE_LIMIT_EXCEEDED'):
        assert point.classification({'status':'FAILED_CLOSED','classification':kind},10)=='PARTIAL_RESOURCE_OR_TIME'
