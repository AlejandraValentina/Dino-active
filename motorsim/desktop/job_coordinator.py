"""Qt application adapter for durable point jobs; model contracts stay separate."""
from copy import deepcopy
from pathlib import Path
import json
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QTableWidget,QTableWidgetItem,QHeaderView,QPlainTextEdit,QMessageBox,QFileDialog
from .engineering_jobs import EngineeringJobs,snapshot_job
from .preferences import artifact_root,settings


class JobCoordinator:
    def __init__(self,window):
        self.window=window;self.error='';self.manager=None
        root=artifact_root()
        try:self.manager=EngineeringJobs(settings().value('frontend_queue_path') or root/'frontend-engineering-jobs-v1'/'queue.json',root,window)
        except (OSError,ValueError,KeyError,TypeError) as exc:self.error='Cola conservada sin modificar; no se pudo abrir: '+str(exc)
        if self.manager:
            self.manager.resultReady.connect(self.attach_result);self.manager.runningChanged.connect(self.lock_execution)
    def choose_queue(self,new=False):
        if self.running:raise ValueError('Terminá o cancelá el trabajo actual antes de cambiar la cola')
        picker=QFileDialog.getSaveFileName if new else QFileDialog.getOpenFileName
        path,_=picker(self.window,'Nueva cola' if new else 'Abrir cola','','Cola de puntos (*.json)')
        if not path:return
        target=Path(path)
        if new and target.exists():raise ValueError('El archivo ya existe; usá Abrir cola. No se sobrescribió.')
        if self.manager and target.resolve()==self.manager.path.resolve():return
        manager=EngineeringJobs(target,artifact_root(),self.window)
        if self.manager:self.manager.close()
        self.manager=manager;self.error='';manager.resultReady.connect(self.attach_result);manager.runningChanged.connect(self.lock_execution)
        settings().setValue('frontend_queue_path',str(target))

    @property
    def running(self):return bool(self.manager and self.manager.running)
    def lock_execution(self,running):
        w=self.window
        running=bool(self.manager and (self.manager.running or (not self.manager.paused and any(i['status']=='PENDING' for i in self.manager.items))))
        for context in (w.context,w.native_four_stroke.context,w.four_stroke_context):context.queued_execution_active=running
        for widget in (w.pages[3].start,w.native_four_stroke.simulation.start,w.native_four_stroke.curve.start_button,w.four_stroke_run_button):widget.setEnabled(not running)
        w.experience.refresh()
    def other_running(self):
        w=self.window
        return w.pages[3].task is not None or w.native_four_stroke.running or w.four_stroke_context.execution_active or w.four_stroke_execution.running or w.four_stroke_curve.execution.running
    def enqueue_current(self):
        w=self.window
        if self.manager is None:raise ValueError(self.error)
        if self.other_running() or self.running:raise ValueError('Terminá o cancelá la ejecución activa antes de preparar la cola')
        if w._four_stroke_active():raise ValueError('La referencia 0D conserva su cola de curvas, disponible desde esta ventana')
        context=w._active_context()
        if not context.prepare_operation('Congelar entrada para la cola'):return False
        native=w._native_four_stroke_active();config=deepcopy(context.engine());page=w.native_four_stroke.simulation if native else w.pages[3]
        rpm=page.rpm.value();cycles=page.cycles.value();wall=page.wall.value() if native else page.budget.value();memory=1024 if native else page.memory.value()
        if native:config['operating_point']['rpm']=float(rpm)
        from .. import engine_platform
        checked=engine_platform.validate_config('4T' if native else '2T',config)
        if not checked['valid'] or checked.get('unknown_keys'):raise ValueError('Configuración no válida para ejecutar: '+str(checked.get('issues')))
        self.manager.add(snapshot_job('4T' if native else '2T',config,context.project['project_id'],context.selected_variant,context.project['base_identity_sha256'],rpm=rpm,cycles=int(cycles),wall=wall,memory=memory))
        return True
    def start(self):
        if self.other_running():raise ValueError('Hay una ejecución interactiva activa; la cola permanece pendiente')
        if self.manager is None:raise ValueError(self.error)
        self.manager.start()
    def attach_result(self,job,result):
        w=self.window;context=w.native_four_stroke.context if job['family']=='4T' else w.context
        if context.project['project_id']!=job['project_id'] or context.project['base_identity_sha256']!=job['base_identity']:
            w.statusBar().showMessage('Resultado de cola conservado; el proyecto de origen no está abierto. Consultá Corridas y cola.',9000);return
        try:
            if job['family']=='4T':context.add_run_reference(result['reference'])
            else:context.add_result_reference(result['reference'])
        except (ValueError,KeyError,OSError) as exc:w.statusBar().showMessage('Resultado conservado; asociación pendiente: '+str(exc),9000)
    def open_result(self,item):
        result=item.get('result')
        if not result:return
        w=self.window
        if item['family']=='2T':
            w.show_two_stroke_mode();w.set_workspace_mode(1);w.results.open_runs([result['path']])
        else:
            context=w.native_four_stroke.context
            if context.project['project_id']!=item['project_id'] or context.project['base_identity_sha256']!=item['base_identity']:
                QMessageBox.information(w,'Resultado conservado','Abrí el proyecto de origen para asociar esta referencia. Archivo: '+result['path']);return
            w.show_native_four_stroke_mode();w.set_workspace_mode(1)
            refs=context.project['run_references'];index=next((i for i,r in enumerate(refs) if r.get('run_id')==item['job_id']),None)
            if index is not None:w.native_four_stroke.results.history.setCurrentRow(index)
    def show(self):
        w=self.window;dialog=QDialog(w);dialog.setWindowTitle('Cola de puntos de ingeniería');dialog.resize(1000,650);layout=QVBoxLayout(dialog)
        info=QLabel('Puntos 2T y 4T nativo con entradas congeladas. Ejecución serial; terminar un trabajo no demuestra periodicidad ni validación. Los interrumpidos no se reanudan automáticamente. La cola de curvas0D conserva su contrato propio.');info.setWordWrap(True);layout.addWidget(info)
        def choose(new):
            try:self.choose_queue(new);dialog.accept()
            except (ValueError,OSError,KeyError) as exc:QMessageBox.warning(dialog,'No se pudo abrir la cola',str(exc))
        selection=QHBoxLayout();layout.addLayout(selection)
        for text,new in (('Nueva cola…',True),('Abrir cola…',False)):
            button=QPushButton(text);button.clicked.connect(lambda _,n=new:choose(n));selection.addWidget(button)
        if self.manager is None:layout.addWidget(QLabel(self.error));dialog.exec();return
        manager=self.manager;summary=QLabel();summary.setWordWrap(True);layout.addWidget(summary)
        table=QTableWidget(0,7);table.setHorizontalHeaderLabels(['Modelo / proyecto','Variante','RPM','Ciclos / límite','Ejecución','Resultado','Entrada'])
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows);table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection);table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers);table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents);layout.addWidget(table,1)
        preview=QPlainTextEdit();preview.setReadOnly(True);preview.setMaximumHeight(145);preview.setAccessibleName('Entrada congelada y detalle del trabajo');layout.addWidget(preview)
        def selected():return manager.items[table.currentRow()] if 0<=table.currentRow()<len(manager.items) else None
        def refresh():
            row=table.currentRow();table.setRowCount(len(manager.items))
            for r,item in enumerate(manager.items):
                values=(item['family']+' · '+item['project_id'],item['variant'] or 'Base',item['rpm'],f"{item['cycles']} / {item['wall']:g}s",item['status'],(item.get('result') or {}).get('classification') or item.get('error') or item.get('progress'),item['configuration_sha256'][:12])
                for c,value in enumerate(values):table.setItem(r,c,QTableWidgetItem(str(value or '—')))
            if row>=0:table.selectRow(row)
            pending=[i for i in manager.items if i['status']=='PENDING'];summary.setText((manager.error+'\n' if manager.error else '')+f"{len(pending)} pendientes · suma de límites por punto: {sum(i['wall'] for i in pending):g}s, más preparación/escritura; duración real desconocida. Cola {'pausada' if manager.paused else 'activa'}.")
        def inspect():
            item=selected();preview.setPlainText(json.dumps(item,ensure_ascii=False,indent=2) if item else '')
        def call(function):
            try:function();refresh()
            except (ValueError,OSError,KeyError,RuntimeError) as exc:QMessageBox.warning(dialog,'Cola sin cambios de ejecución',str(exc))
        row=QHBoxLayout();layout.addLayout(row)
        for text,callback in (('Agregar punto preparado',self.enqueue_current),('Ejecutar pendientes',self.start),('Pausar después del actual',manager.pause),('Cancelar seleccionado',lambda:manager.cancel(selected()['job_id']) if selected() else None),('Ver resultado',lambda:self.open_result(selected()) if selected() else None)):
            button=QPushButton(text);button.clicked.connect(lambda _,f=callback:call(f));row.addWidget(button)
        reference=QPushButton('Cola de curvas4T0D…');reference.clicked.connect(lambda *_:(dialog.accept(),w.show_four_stroke_mode(),w.set_workspace_mode(2),w.four_stroke_curve.open_batch_queue()));layout.addWidget(reference)
        table.itemSelectionChanged.connect(inspect);manager.changed.connect(refresh);refresh()
        try:dialog.exec()
        finally:manager.changed.disconnect(refresh)
