"""Application queue lifecycle tests; executors here are synthetic test doubles."""
import os,json,threading,time
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import desktop_qsettings_isolation
import pytest
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QThreadPool
from motorsim.desktop.engineering_jobs import EngineeringJobs,snapshot_job

APP=QApplication.instance() or QApplication([])


def job():return snapshot_job('2T',{'fixture':'SYNTHETIC_APPLICATION_TEST'},'project','variant','a'*64,rpm=3000,cycles=1,wall=10)


def wait(predicate):
    deadline=time.monotonic()+5
    while not predicate():
        if time.monotonic()>deadline:raise AssertionError('Synthetic executor did not finish')
        APP.processEvents();time.sleep(.005)
    APP.processEvents()


def test_snapshot_is_immutable_and_serial_queue_can_pause(tmp_path):
    entered=threading.Event();release=threading.Event();calls=[]
    def execute(item,root,cancel,progress):
        calls.append(item['job_id']);entered.set();release.wait(3);return {'classification':'SYNTHETIC_TEST','path':'not-a-result'}
    q=EngineeringJobs(tmp_path/'queue.json',tmp_path,executor=execute);first=job();q.add(first);second=job();q.add(second);first['configuration']='changed after enqueue'
    q.start();wait(entered.is_set);assert q.items[0]['configuration']!='changed after enqueue'
    q.pause();release.set();wait(lambda:not q.running)
    assert q.items[0]['status']=='COMPLETED' and q.items[1]['status']=='PENDING' and len(calls)==1
    q.start();wait(lambda:q.items[1]['status']=='COMPLETED');assert len(calls)==2
    QThreadPool.globalInstance().waitForDone(2000)


def test_cancel_pending_and_active_preserves_qualification(tmp_path):
    entered=threading.Event()
    def execute(item,root,cancel,progress):
        entered.set();cancel.wait(3);return {'classification':'NOT_CONVERGED','path':'synthetic-no-file'}
    q=EngineeringJobs(tmp_path/'queue.json',tmp_path,executor=execute);q.add(job());q.add(job());q.cancel(q.items[1]['job_id']);q.start();wait(entered.is_set)
    q.cancel(q.items[0]['job_id']);wait(lambda:not q.running)
    assert all(i['status']=='CANCELLED' for i in q.items) and q.items[0]['result']['classification']=='NOT_CONVERGED'
    assert q.paused;QThreadPool.globalInstance().waitForDone(2000)


def test_interruption_is_durable_and_never_auto_resumed(tmp_path):
    path=tmp_path/'queue.json';q=EngineeringJobs(path,tmp_path);q.add(job());q.items[0]['status']='RUNNING';q.save();q.close()
    recovered=EngineeringJobs(path,tmp_path)
    assert recovered.paused and not recovered.running and recovered.items[0]['status']=='INTERRUPTED'
    assert json.loads(path.read_text(encoding='utf-8'))['items'][0]['status']=='INTERRUPTED'


def test_corrupt_input_is_rejected_without_rewriting_ledger(tmp_path):
    path=tmp_path/'queue.json';q=EngineeringJobs(path,tmp_path);q.add(job());data=json.loads(path.read_text(encoding='utf-8'));data['items'][0]['configuration']='{}';path.write_text(json.dumps(data));before=path.read_bytes();q.close()
    with pytest.raises(ValueError):EngineeringJobs(path,tmp_path)
    assert path.read_bytes()==before


def test_storage_and_persistence_failure_do_not_launch(tmp_path,monkeypatch):
    q=EngineeringJobs(tmp_path/'queue.json',tmp_path);q.add(job())
    with monkeypatch.context() as m:
        m.setattr('motorsim.storage_preflight.check_storage_requirements',lambda *a,**kw:(_ for _ in ()).throw(OSError('storage denied')))
        with pytest.raises(OSError):q.start()
    assert not q.running and q.items[0]['status']=='PENDING'
    monkeypatch.setattr(q,'save',lambda:(_ for _ in ()).throw(OSError('write denied')))
    with pytest.raises(OSError):q.start()
    assert not q.running and q.items[0]['status']=='PENDING'


def test_stale_callbacks_cannot_update_another_job(tmp_path):
    entered=threading.Event();release=threading.Event()
    def execute(item,root,cancel,progress):entered.set();release.wait(3);return {'classification':'SYNTHETIC_TEST'}
    q=EngineeringJobs(tmp_path/'queue.json',tmp_path,executor=execute);q.add(job());q.start();wait(entered.is_set);before=q.items[0].copy()
    q._progress('not-the-active-id',{'cycle':999});q._terminal('not-the-active-id',{},None)
    assert q.running and q.items[0]==before
    release.set();wait(lambda:not q.running);QThreadPool.globalInstance().waitForDone(2000)


def test_second_writer_is_rejected_until_owner_closes(tmp_path):
    path=tmp_path/'queue.json';q=EngineeringJobs(path,tmp_path);q.add(job());before=path.read_bytes()
    with pytest.raises(ValueError,match='dueño'):EngineeringJobs(path,tmp_path)
    assert path.read_bytes()==before
    q.close();reopened=EngineeringJobs(path,tmp_path);assert len(reopened.items)==1
    with pytest.raises(ValueError):q.save()
    reopened.close()
