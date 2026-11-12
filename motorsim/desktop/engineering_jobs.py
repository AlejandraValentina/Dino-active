"""Durable application jobs over existing public execution APIs. No physics here."""
from __future__ import annotations
from copy import deepcopy
import hashlib,json,math,os,tempfile,threading,uuid
from pathlib import Path
from PySide6.QtCore import QObject,Signal,QRunnable,QThreadPool,QTimer,QElapsedTimer,QLockFile
from PySide6.QtWidgets import QApplication
from .preferences import repository_root_containing

SCHEMA='DINO_ENGINEERING_POINT_QUEUE_V1'
STATES={'PENDING','RUNNING','COMPLETED','FAILED','CANCELLED','INTERRUPTED'}


def canonical(value):return json.dumps(value,sort_keys=True,ensure_ascii=False,allow_nan=False,separators=(',',':'))


def snapshot_job(family,config,project_id,variant,base_identity,*,rpm,cycles,wall,memory=1024):
    if family not in ('2T','4T'):raise ValueError('Esta cola admite puntos 2T y 4T nativo; la referencia 0D conserva su cola de curvas')
    if not isinstance(project_id,str) or not project_id:raise ValueError('Proyecto requerido')
    if not math.isfinite(float(rpm)) or rpm<=0 or type(cycles) is not int or not 1<=cycles<=100:raise ValueError('RPM/ciclos inválidos')
    if not math.isfinite(float(wall)) or not 1<=wall<=600 or not 128<=memory<=32768:raise ValueError('Presupuesto inválido')
    raw=canonical(config)
    return dict(job_id=uuid.uuid4().hex,family=family,project_id=project_id,variant=variant or '',base_identity=base_identity,configuration=raw,configuration_sha256=hashlib.sha256(raw.encode()).hexdigest(),rpm=float(rpm),cycles=cycles,wall=float(wall),memory=int(memory),status='PENDING',result=None,error='',progress='')


def execute_job(job,root,cancel,progress):
    """New attempt only. Checkpoint resume is not inferred by the application."""
    config=json.loads(job['configuration'])
    if hashlib.sha256(job['configuration'].encode()).hexdigest()!=job['configuration_sha256']:raise ValueError('La entrada congelada cambió')
    if job['family']=='2T':
        from ..exploratory_workflow import run_exploratory
        result=run_exploratory(config,project_id=job['project_id'],run_id=job['job_id'],artifact_root=root,rpm=job['rpm'],max_cycles=job['cycles'],budget_seconds=job['wall'],memory_limit_mib=job['memory'],resume=False,cancel_event=cancel,variant_label=job['variant'] or 'base',progress=progress)
        directory=Path(result['artifact_directory']);path=directory/'result.json';raw=path.read_bytes();stored=json.loads(raw)
        return dict(path=str(path),classification=stored['classification'],reference=dict(path=str(path),identity_sha256=stored['bindings']['identity_sha256'],artifact_sha256=hashlib.sha256(raw).hexdigest(),classification=stored['classification']))
    from .. import engine_platform
    from .four_stroke_artifacts import publish_desktop_run
    folder=Path(root)/'frontend-engineering-jobs-v1'/job['job_id'];out=folder/'artifacts';out.mkdir(parents=True,exist_ok=False)
    result=engine_platform.run_api('4T',config,out_dir=out,max_cycles=job['cycles'],wall_limit_s=job['wall'],on_progress=progress,cancel_event=cancel)
    engine_platform.check_result('4T',result)
    if result.get('summary') is None:raise ValueError('El API nativo no devolvió un resultado: '+str(result.get('error')))
    reference=publish_desktop_run(folder,result,job['project_id'],job['variant'],run_id=job['job_id'])
    return dict(path=reference['path'],classification=reference['periodicity_status'],reference=reference)


class _Signals(QObject):
    progress=Signal(dict);finished=Signal(object);failed=Signal(str)


class _Task(QRunnable):
    def __init__(self,job,root,executor):
        super().__init__();self.setAutoDelete(False);self.job=deepcopy(job);self.root=root;self.executor=executor;self.cancel=threading.Event();self.signals=_Signals()
    def run(self):
        try:self.signals.finished.emit(self.executor(self.job,self.root,self.cancel,self.signals.progress.emit))
        except Exception as exc:self.signals.failed.emit(f'{type(exc).__name__}: {exc}')


class EngineeringJobs(QObject):
    changed=Signal();runningChanged=Signal(bool);resultReady=Signal(dict,dict)
    def __init__(self,path,artifact_root,parent=None,executor=execute_job):
        super().__init__(parent);self.path=Path(path);self.root=Path(artifact_root);self.items=[];self.task=None;self.active_id=None;self.paused=True;self.executor=executor;self.error='';self._retired=[]
        if repository_root_containing(self.path) is not None or repository_root_containing(self.root) is not None:raise ValueError('La cola y sus resultados deben quedar fuera del repositorio')
        self.path.parent.mkdir(parents=True,exist_ok=True)
        self._lock=QLockFile(str(self.path)+'.lock');self._lock.setStaleLockTime(0)
        if not self._lock.tryLock(0):raise ValueError('Otra ventana o proceso es dueño de esta cola; elegí otra cola o cerrá esa instancia')
        try:
            if self.path.exists():self.load()
        except Exception:
            self._lock.unlock();raise
    @property
    def running(self):return self.task is not None
    def load(self):
        payload=json.loads(self.path.read_text(encoding='utf-8'))
        if payload.get('schema')!=SCHEMA or not isinstance(payload.get('items'),list) or len(payload['items'])>100:raise ValueError('Cola no reconocida')
        checked=deepcopy(payload['items']);recovered=False
        for item in checked:
            if item.get('status') not in STATES:raise ValueError('Estado de cola inválido')
            checked_job=snapshot_job(item['family'],json.loads(item['configuration']),item['project_id'],item['variant'],item['base_identity'],rpm=item['rpm'],cycles=item['cycles'],wall=item['wall'],memory=item['memory'])
            if checked_job['configuration_sha256']!=item['configuration_sha256']:raise ValueError('Identidad de entrada de cola inválida')
            if not isinstance(item.get('job_id'),str) or len(item['job_id'])!=32 or any(c not in '0123456789abcdef' for c in item['job_id']):raise ValueError('ID de trabajo inválido')
            if item['status']=='RUNNING':item['status']='INTERRUPTED';item['error']='La aplicación se interrumpió. No se reanuda automáticamente; los artifacts se conservan.';recovered=True
        if len({i['job_id'] for i in checked})!=len(checked):raise ValueError('ID de trabajo duplicado')
        self.items=checked;self.paused=True
        if recovered:self.save()
    def close(self):
        if self.running:raise RuntimeError('La cola sigue ejecutando; no se puede liberar su autoridad')
        self._lock.unlock()
    def save(self):
        if not self._lock.isLocked():raise ValueError('La cola ya está cerrada; volvé a abrirla antes de modificarla')
        self.path.parent.mkdir(parents=True,exist_ok=True)
        fd,temp=tempfile.mkstemp(prefix=self.path.name+'.',suffix='.tmp',dir=self.path.parent)
        try:
            with os.fdopen(fd,'w',encoding='utf-8',newline='\n') as stream:stream.write(json.dumps(dict(schema=SCHEMA,items=self.items),ensure_ascii=False,allow_nan=False,indent=2)+'\n');stream.flush();os.fsync(stream.fileno())
            os.replace(temp,self.path)
        finally:
            try:Path(temp).unlink(missing_ok=True)
            except OSError:pass
        self.changed.emit()
    def add(self,job):
        if len(self.items)>=100:raise ValueError('La cola conserva hasta100 trabajos; elegí otro archivo de cola sin borrar los anteriores')
        if self.running:raise ValueError('Pausá la cola antes de agregar configuraciones')
        if job['status']!='PENDING':raise ValueError('Sólo se agregan trabajos nuevos')
        self.items.append(deepcopy(job));self.save()
    def start(self):
        if self.running:return
        from ..storage_preflight import check_storage_requirements
        pending=sum(i['status']=='PENDING' for i in self.items)
        check_storage_requirements([(self.root,pending*256*1024*1024)])
        self.paused=False;self._next()
    def pause(self):self.paused=True;self.changed.emit()
    def cancel(self,job_id):
        item=next(i for i in self.items if i['job_id']==job_id)
        if item['status']=='RUNNING' and self.task:self.paused=True;self.task.cancel.set();item['progress']='Cancelación solicitada; se esperan ciclos completos'
        elif item['status']=='PENDING':item['status']='CANCELLED'
        self.save()
    def _next(self):
        if self.paused or self.running:return
        item=next((i for i in self.items if i['status']=='PENDING'),None)
        if item is None:self.paused=True;self.changed.emit();return
        item['status']='RUNNING';self.active_id=item['job_id'];task=_Task(item,self.root,self.executor);self.task=task
        job_id=item['job_id']
        task.signals.progress.connect(lambda event,j=job_id:self._progress(j,event));task.signals.finished.connect(lambda result,j=job_id:self._terminal(j,result,None));task.signals.failed.connect(lambda error,j=job_id:self._terminal(j,None,error))
        try:self.save()
        except Exception:
            item['status']='PENDING';self.task=None;self.active_id=None;self.paused=True;raise
        self.runningChanged.emit(True);QThreadPool.globalInstance().start(task)
    def _progress(self,job_id,event):
        if not self.running or job_id!=self.active_id:return
        item=next(i for i in self.items if i['job_id']==self.active_id);item['progress']=str(event)[:600];self.changed.emit()
    def _terminal(self,job_id,result,error):
        task=self.task
        if task is None or job_id!=self.active_id:return
        item=next(i for i in self.items if i['job_id']==self.active_id)
        item['status']='CANCELLED' if task.cancel.is_set() else 'FAILED' if error else 'COMPLETED';item['result']=result;item['error']=error or '';item['progress']=''
        self._retired.append(task);self.task=None;self.active_id=None
        try:self.save()
        except OSError as exc:self.error='No se pudo guardar la cola: '+str(exc);self.paused=True;self.changed.emit()
        self.runningChanged.emit(False)
        if result:self.resultReady.emit(deepcopy(item),deepcopy(result))
        # Retain wrapper through signal delivery. The native call has returned.
        QTimer.singleShot(0,self._next)
    def shutdown(self,milliseconds=10000):
        self.paused=True
        if self.task:self.task.cancel.set()
        timer=QElapsedTimer();timer.start()
        while self.task and timer.elapsed()<milliseconds:QApplication.processEvents();time_sleep(.01)
        return self.task is None


def time_sleep(seconds):
    import time
    time.sleep(seconds)
