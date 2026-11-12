"""Common project experience; engine contracts and result eligibility stay native."""
import hashlib
import json
from PySide6.QtCore import Qt,QTimer
from PySide6.QtWidgets import (QWidget,QLabel,QHBoxLayout,QVBoxLayout,QPushButton,
    QDialog,QTableWidget,QTableWidgetItem,QHeaderView,QMessageBox,QLineEdit,QFileDialog,QToolButton,QMenu)


def descriptor(window):
    context=window._active_context()
    if context is window.four_stroke_context:
        doc=context.project.to_dict();doc.pop('curve_references',None)
        identity=hashlib.sha256(json.dumps(doc,sort_keys=True).encode()).hexdigest()
        return dict(project=context.name,model='4T 0D · referencia sintética',variant='Referencia',
            engine=context.name,revision=identity,dirty=context.dirty,path=context.path)
    from ..engine_platform import identity
    engine=context.engine();native=context.engine_family=='4T'
    # Rendering must not reconstruct/validate a 2T solver on each UI signal.
    # Reuse only identities already checked for these exact document bytes.
    key=(context.engine_family,json.dumps(engine,sort_keys=True,allow_nan=False))
    cache=getattr(window,'_frontend_identity_cache',{})
    if key not in cache:
        if len(cache)>=16:cache.clear()
        cache[key]=identity(context.engine_family,engine)
    window._frontend_identity_cache=cache
    return dict(project=context.project['project_id'],model='4T nativo' if native else '2T integrado',
        variant=context.selected_variant or 'Motor base',
        engine=engine.get('identifier') if native else engine.get('display_name','Motor 2T'),
        revision=cache[key],dirty=context.dirty,path=context.path)


def resolve_draft(parent,operation,apply,discard):
    box=QMessageBox(QMessageBox.Icon.Question,'Cambios sin aplicar',
        f'{operation}: hay cambios del motor sin aplicar.',QMessageBox.StandardButton.NoButton,parent)
    yes=box.addButton('Aplicar y continuar',QMessageBox.ButtonRole.AcceptRole)
    no=box.addButton('Descartar borrador',QMessageBox.ButtonRole.DestructiveRole)
    cancel=box.addButton('Cancelar',QMessageBox.ButtonRole.RejectRole)
    box.setDefaultButton(cancel);box.exec()
    if box.clickedButton() is yes:return bool(apply())
    if box.clickedButton() is no:discard();return True
    return False


class WorkspaceExperience:
    def __init__(self,window):
        self.window=window;self._applying_reference=False
        self.reference_fields=window.four_stroke_workspace.findChildren(QLineEdit)
        self.reference_tables=window.four_stroke_workspace.findChildren(QTableWidget)
        self.reference_snapshot=self.reference_values()
        layout=window.centralWidget().layout()
        actions=layout.itemAt(2).layout()
        self.runs_button=QPushButton('Corridas y cola…')
        self.runs_button.setAccessibleName('Corridas del proyecto y alcance de colas')
        self.runs_button.clicked.connect(self.show_runs)
        actions.insertWidget(max(0,actions.count()-1),self.runs_button)
        self.bundle_button=QPushButton('Contenido portable…')
        self.bundle_button.clicked.connect(self.show_portable_contents)
        actions.insertWidget(max(0,actions.count()-1),self.bundle_button)
        self.header=QWidget();self.header.setObjectName('projectIdentityHeader')
        row=QHBoxLayout(self.header);row.setContentsMargins(14,5,14,5)
        self.project=QLabel();self.project.setWordWrap(True);self.project.setTextFormat(Qt.TextFormat.PlainText)
        self.identity=QLabel();self.identity.setWordWrap(True);self.identity.setTextFormat(Qt.TextFormat.PlainText)
        self.saved=QLabel();self.saved.setWordWrap(True)
        row.addWidget(self.project,3);row.addWidget(self.identity,3);row.addWidget(self.saved,2)
        layout.insertWidget(0,self.header)
        window.project_header=self.header
        # Keep the established 2T variant/baseline controls, without a second
        # competing project/saved label.
        window.context_bar.project.hide();window.context_bar.saved.hide()
        window.four_stroke_tabs.tabBar().hide()
        for button in window.project_mode_stack.widget(1).findChildren(QPushButton):
            if button.text() in ('Volver a 2T','Nuevo 4T…','Abrir 4T…','Guardar 4T'):button.hide()
        for context in (window.context,window.native_four_stroke.context,window.four_stroke_context):
            context.changed.connect(self.refresh)
        window.context.set_edit_guard(self.ensure_two_stroke)
        window.native_four_stroke.context.draft_changed.connect(self.refresh)
        window.pages[0].component_state_changed.connect(self.refresh)
        window.pages[1].component_state_changed.connect(self.refresh)
        window.engine_family_changed.connect(self.refresh)
        window.four_stroke_context.project_changed.connect(self.reference_loaded)
        window.four_stroke_workspace.applied.connect(self.reference_loaded)
        for field in self.reference_fields:field.textEdited.connect(self.refresh)
        for table in self.reference_tables:table.itemChanged.connect(self.refresh)
        for page in (window.four_stroke_workspace.geometry,window.four_stroke_workspace.valves,window.four_stroke_workspace.ducts):
            if hasattr(page,'apply_button'):page.apply_button.clicked.connect(lambda *_,p=page:self.reference_page_applied(p))
        for button in (window.design_mode,window.simulate_mode,window.analysis_mode):button.clicked.connect(self.refresh)
        for signal in (window.native_four_stroke.simulation.runningChanged,
                       window.native_four_stroke.curve.runningChanged,
                       window.four_stroke_context.execution_changed,window.pages[3].state_changed):
            signal.connect(self.refresh)
        from .component_map import ComponentNavigator
        self.components=ComponentNavigator(window)
        from PySide6.QtGui import QAction
        for text,shortcut,callback in (('Modelo','Ctrl+1',lambda:window.set_workspace_mode(0)),('Simular','Ctrl+2',lambda:window.set_workspace_mode(2)),('Resultados','Ctrl+3',lambda:window.set_workspace_mode(1)),('Corridas del proyecto','Ctrl+Shift+R',self.show_runs),('Diferencias de variante','Ctrl+Shift+D',self.show_variant_diff),('Recuperar borrador…','Ctrl+Shift+O',window._offer_recoveries)):
            action=QAction(text,window);action.setShortcut(shortcut);action.triggered.connect(callback);window.addAction(action)
        self.diff_button=QPushButton('Diferencias…');self.diff_button.setToolTip('Comparar la configuración aplicada con el motor base (Ctrl+Shift+D)')
        self.diff_button.clicked.connect(self.show_variant_diff);actions.insertWidget(max(0,actions.count()-1),self.diff_button)
        # Keep primary commands visible; secondary tools share a compact menu.
        self.tool_actions=[];tools=QToolButton();tools.setText('Herramientas');tools.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup);menu=QMenu(tools);tools.setMenu(menu)
        primary={actions.itemAt(i).widget() for i in range(3)}|{self.runs_button}
        for i in range(actions.count()):
            button=actions.itemAt(i).widget()
            if button is None or button in primary:continue
            button.hide()
            if button is window.four_stroke_button:continue
            action=menu.addAction(button.text());action.triggered.connect(button.click);self.tool_actions.append((action,button))
        components=QToolButton();components.setDefaultAction(self.components.action);components.setText('Componentes')
        actions.insertWidget(max(0,actions.count()-1),components);actions.insertWidget(max(0,actions.count()-1),tools)
        from .job_coordinator import JobCoordinator
        self.jobs=JobCoordinator(window)
        self.install_plan_previews()
        self.refresh()

    def install_plan_previews(self):
        from .native_four_stroke_curve import plan_native_rpms
        native=self.window.native_four_stroke.curve
        native.plan_preview=QLabel();native.plan_preview.setWordWrap(True)
        native.layout().insertWidget(1,native.plan_preview)
        def native_plan(*_):
            try:
                rpms=plan_native_rpms(native.start_rpm.value(),native.end_rpm.value(),native.step_rpm.value())
                native.plan_preview.setText(f'{len(rpms)} puntos · {rpms[0]:g}–{rpms[-1]:g} RPM · hasta {len(rpms)*native.wall.value()} s de presupuesto por puntos, más preparación y escritura. La duración real es desconocida; sólo se grafican prestaciones admitidas por el detector.')
            except ValueError as exc:native.plan_preview.setText('Revisá el rango: '+str(exc))
        for field in (native.start_rpm,native.end_rpm,native.step_rpm,native.wall):field.valueChanged.connect(native_plan)
        native_plan()
        reference=self.window.four_stroke_curve
        reference.plan_preview=QLabel();reference.plan_preview.setWordWrap(True)
        reference.layout().insertWidget(1,reference.plan_preview)
        def reference_plan(*_):
            try:
                rpms=reference._rpms()
                reference.plan_preview.setText(f'{len(rpms)} puntos de referencia sintética: {rpms} RPM. No sustituye al motor nativo ni acredita validación experimental.')
            except Exception as exc:reference.plan_preview.setText('Revisá el rango: '+str(exc))
        for field in (reference.start_edit,reference.end_edit,reference.step_edit):field.textChanged.connect(reference_plan)
        reference_plan()

    def reference_loaded(self,*_):
        self.reference_snapshot=self.reference_values()
        self.refresh()

    def reference_values(self):
        values={id(w):w.text() for w in self.reference_fields}
        values.update({id(t):tuple(tuple(t.item(r,c).text() if t.item(r,c) else '' for c in range(t.columnCount())) for r in range(t.rowCount())) for t in self.reference_tables})
        return values

    def reference_page_applied(self,page):
        if hasattr(page,'error') and page.error.text():return
        current=self.reference_values()
        for widget in [*self.reference_fields,*self.reference_tables]:
            if page.isAncestorOf(widget):self.reference_snapshot[id(widget)]=current[id(widget)]
        self.refresh()

    def reference_pending(self):
        return self.reference_values()!=self.reference_snapshot

    def ensure_reference(self,operation):
        if not self.reference_pending():return True
        def apply():
            self._applying_reference=True
            try:ok=self.window.four_stroke_workspace.apply_all()
            finally:self._applying_reference=False
            if ok:self.reference_loaded()
            return ok
        def discard():
            self.window.four_stroke_workspace.refresh(self.window.four_stroke_context.project)
            self.reference_loaded()
        return resolve_draft(self.window,operation,apply,discard)

    def ensure_two_stroke(self,operation):
        if getattr(self.window.context,'queued_execution_active',False):
            QMessageBox.information(self.window,'Cola activa','Pausá o cancelá la cola de puntos antes de iniciar otra operación 2T.');return False
        editor=self.window.pages[0]
        def apply():
            editor.apply()
            return editor._last_edited_component is None
        if editor._last_edited_component is not None and not resolve_draft(self.window,operation,apply,editor.discard_draft):return False
        exhaust=self.window.pages[1]
        if exhaust.edit_state in {'modified','invalid'} and not exhaust._applying and not exhaust._preparing:
            def apply_exhaust():return exhaust.save_current() if self.window.context.selected_variant is not None else exhaust.save_as_new()
            return resolve_draft(self.window,operation,apply_exhaust,exhaust.discard_draft)
        return True

    def refresh(self,*_):
        w=self.window;info=descriptor(w)
        pending=(w.native_four_stroke.editor.has_pending_changes if w._native_four_stroke_active()
                 else self.reference_pending() if w._four_stroke_active()
                 else w.pages[0]._last_edited_component is not None or w.pages[1].edit_state in {'modified','invalid'})
        self.project.setText(f"Proyecto: {info['project']}\n{info['model']} · {info['engine']}")
        self.identity.setText(f"Variante: {info['variant']}\nConfiguración aplicada: {info['revision'][:12]}")
        self.identity.setToolTip('Identidad completa de la configuración aplicada:\n'+info['revision'])
        state='Borrador sin aplicar' if pending else 'Cambios sin guardar' if info['dirty'] else 'Guardado' if info['path'] else 'Sin archivo guardado'
        self.saved.setText(state+'\nValidación experimental no realizada')
        if w._native_four_stroke_active() and w.native_four_stroke.running:
            task=w.native_four_stroke.simulation.task
            running='Punto nativo en ejecución' if task is not None else 'Barrido nativo en ejecución'
            self.saved.setText(state+'\n'+running)
        elif w._four_stroke_active() and w.four_stroke_context.execution_active:
            self.saved.setText(state+'\nReferencia 0D en ejecución')
        elif not w._four_stroke_active() and not w._native_four_stroke_active() and w.pages[3].task is not None:
            self.saved.setText(state+'\nSimulación 2T en ejecución')
        if hasattr(self,'jobs') and self.jobs.running:
            job=self.jobs.manager.task.job
            self.saved.setText(state+f"\nCola: {job['family']} · {job['rpm']:g} RPM · entrada {job['configuration_sha256'][:12]}")
        self.saved.setToolTip(str(info['path'] or 'Elegí Guardar como para conservar el proyecto.'))
        self.diff_button.setEnabled(not w._four_stroke_active())
        for action,button in self.tool_actions:action.setEnabled(button.isEnabled())
        reference=w._four_stroke_active()
        simulate=reference and w.simulate_mode.isChecked()
        w.four_stroke_run_button.setVisible(simulate);w.four_stroke_cancel_button.setVisible(simulate)
        w.four_stroke_status.setVisible(reference and (simulate or w.four_stroke_execution.running))

    def show_portable_contents(self):
        from .portable_artifacts import collect_project
        w=self.window;context=w._active_context()
        family='4T_native' if w._native_four_stroke_active() else '4T_0D' if w._four_stroke_active() else '2T'
        try:
            _,entries,payloads,warnings,assessments=collect_project(context.project,family,context.path)
            text=(f'{len(entries)} archivos vinculados · {sum(len(raw) for raw in payloads.values())/1048576:.2f} MiB\n'
                +('Disponibilidad parcial' if warnings else 'Dependencias vinculadas disponibles')
                +'\nSe exporta la configuración aplicada. Los borradores se resuelven al exportar.\n'
                +'Los resultados abiertos externamente y no vinculados al proyecto quedan fuera.\n'
                +'Transportar archivos no acredita validación experimental.\n\n'
                +'\n'.join(warnings[:8])+ '\n'+ '\n'.join(str(e['path']) for e in entries[:16]))
            QMessageBox.information(w,'Contenido del bundle portable',text)
        except (OSError,ValueError,KeyError,TypeError) as exc:
            QMessageBox.warning(w,'No se pudo revisar el contenido',str(exc))

    def show_runs(self):
        w=self.window;dialog=QDialog(w);dialog.setWindowTitle('Corridas del proyecto')
        dialog.resize(1020,560);root=QVBoxLayout(dialog)
        info=descriptor(w)
        label=QLabel(f"{info['project']} · {info['model']}\nEjecución, periodicidad e integridad son estados distintos; no acreditan validación experimental.")
        label.setWordWrap(True);root.addWidget(label)
        table=QTableWidget(0,5);table.setHorizontalHeaderLabels(['Variante / corrida','RPM','Ejecución','Periodicidad / integridad','Abrir'])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch);root.addWidget(table,1)
        def add(values,callback):
            row=table.rowCount();table.insertRow(row)
            for col,value in enumerate(values):table.setItem(row,col,QTableWidgetItem(str(value)))
            button=QPushButton('Ver resultado');table.setCellWidget(row,4,button)
            button.clicked.connect(lambda *_:(dialog.accept(),callback()))
        if w._native_four_stroke_active():
            results=w.native_four_stroke.results
            if w.native_four_stroke.running:add(['Trabajo nativo activo','Ver preparación','En ejecución','Pendiente de evaluación'],lambda:w.set_workspace_mode(2))
            for index,ref in enumerate(w.native_four_stroke.context.project['run_references']):
                assessment=results.assessments.get(index)
                def open_native(i=index):
                    w.set_workspace_mode(1);results.result_tabs.setCurrentIndex(0);results.history.setCurrentRow(i)
                add([ref.get('variant_id') or 'Motor base','—',ref['status'],assessment.classification if assessment else 'Sin evaluar'],open_native)
        elif w._four_stroke_active():
            if w.four_stroke_context.execution_active:add(['Trabajo 0D activo',w.four_stroke_context.rpm,'En ejecución','Referencia sintética'],lambda:w.set_workspace_mode(2))
            if w.four_stroke_results.result:
                add(['Último punto 0D de esta sesión',w.four_stroke_context.rpm,w.four_stroke_status.text(),'Referencia sintética'],lambda:w.set_workspace_mode(1))
            for ref in w.four_stroke_context.project.curve_references:
                add(['Curva de referencia',str(ref['rpms']),ref['status'],'Consultar curva y archivos'],lambda:w.set_workspace_mode(2))
            queue=QPushButton('Cola de curvas 4T 0D…');queue.clicked.connect(lambda *_:(dialog.accept(),w.set_workspace_mode(2),w.four_stroke_curve.open_batch_queue()));root.addWidget(queue)
        else:
            w.analysis_history.activate()
            history=QPushButton('Explorar historial completo 2T…')
            history.clicked.connect(lambda *_:(dialog.accept(),w.set_workspace_mode(1),w.explorer_dock.show(),w.explorer_tabs.setCurrentWidget(w.analysis_history)))
            root.addWidget(history)
            if w.pages[3].task is not None:add(['Trabajo 2T activo',w.pages[3].rpm.value(),'En ejecución','Pendiente de evaluación'],lambda:w.set_workspace_mode(2))
            for ref in w.context.project['result_references']:
                if ref.get('path'):
                    def open_link(p=ref['path']):
                        from pathlib import Path
                        w.set_workspace_mode(1)
                        if Path(p).name=='result.json':w.results.open_runs([p])
                        else:w.results.load(p)
                    add(['Corrida vinculada al proyecto','—','Consultar resultado',ref['classification']],open_link)
        if not w._native_four_stroke_active() and not w._four_stroke_active():
            bind=QPushButton('Vincular resultado externo verificado…');bind.clicked.connect(lambda *_:(dialog.accept(),self.bind_external_result()));root.addWidget(bind)
        jobs=QPushButton('Cola persistente de puntos 2T / 4T nativo…');jobs.clicked.connect(lambda *_:(dialog.accept(),self.jobs.show()));root.addWidget(jobs)
        if not table.rowCount():root.addWidget(QLabel('Todavía no hay corridas disponibles. Prepará un punto o abrí resultados existentes.'))
        root.addWidget(QLabel('Puntos 2T/nativos: cola persistente con entradas congeladas. Curvas0D: cola de referencia. Los barridos y la reanudación conservan sus capacidades propias.'))
        close=QPushButton('Cerrar');close.clicked.connect(dialog.reject);root.addWidget(close)
        dialog.exec()

    def show_variant_diff(self):
        w=self.window
        if w._four_stroke_active():return
        context=w._active_context()
        from .variant_explorer import show_variant_diff
        show_variant_diff(w,context.project['base_engine'],context.engine(),context.selected_variant or 'Motor base')

    def bind_external_result(self):
        w=self.window
        if w._native_four_stroke_active() or w._four_stroke_active():return
        paths,_=QFileDialog.getOpenFileNames(w,'Vincular resultados 2T · no modifica los originales','','Resultados (result.json)')
        if not paths:return
        if not self.ensure_two_stroke('Vincular resultados externos'):return
        from .result_binding import verified_references
        from .services import run_background
        context=w.context;project_id=context.project['project_id'];project_snapshot=context.project
        def complete(payload):
            if context.project is not project_snapshot or context.project['project_id']!=project_id:
                QMessageBox.warning(w,'Proyecto cambiado','La verificación terminó para otro proyecto; no se vinculó ningún resultado.');return
            refs,_=payload
            from copy import deepcopy
            from ..engine_project import validate_project
            candidate=deepcopy(context.project)
            known={r['path'] for r in candidate['result_references']}
            candidate['result_references'].extend(r for r in refs if r['path'] not in known)
            try:validate_project(candidate)
            except (ValueError,KeyError) as exc:QMessageBox.warning(w,'No se pudo vincular',str(exc));return
            for ref in refs:context.add_result_reference(ref)
            w.statusBar().showMessage(f'{len(refs)} resultados verificados y vinculados; su clasificación se conserva.',7000)
        run_background(verified_references,paths,on_done=complete,on_error=lambda exc:QMessageBox.warning(w,'Resultado no vinculable',str(exc)))
