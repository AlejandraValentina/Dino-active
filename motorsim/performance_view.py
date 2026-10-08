"""Consulta de rendimiento indicado de barridos validados; nunca crea procesos."""
import math
from PySide6.QtCore import QPointF,QRectF,Qt,Signal
from PySide6.QtGui import QColor,QPainter,QPen
from PySide6.QtWidgets import (QWidget,QScrollArea,QVBoxLayout,QGridLayout,QPushButton,QFileDialog,
    QTableWidget,QTableWidgetItem,QHeaderView,QAbstractItemView,QLayout,QFormLayout,QLineEdit)
from .ui import Header,Panel,Columns,text,ValidationMessage,visual_state
from .performance import sweep_metrics,export_performance_csv,NOTICE
from .reference_results import ResultError
from .sweep import load_sweep
from .sweep_view import STATES
from .comparison import ComparisonError
from .project import Project,ProjectError
from .project_case import configuration_key
from .sweep import plan_rpms


class PerformancePlot(QWidget):
    selected=Signal(int)
    def __init__(self,fields):
        super().__init__();self.fields=fields;self.rows=[];self.current=-1;self.hits=[]
        self.setMinimumHeight(290 if len(fields)==2 else 250);self.setMinimumWidth(0)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAccessibleName(' / '.join(field[1] for field in fields)+' frente a RPM')
        self.setAccessibleDescription('Seleccionar punto con clic o flechas izquierda/derecha. Datos disponibles también en tabla.')
    def set_rows(self,rows):self.rows=rows;self.current=-1;self.update()
    def set_current(self,index):self.current=index;self.update()
    def series_segments(self,key,factor):
        segments=[];segment=[]
        for i,row in enumerate(self.rows):
            if row['metrics'] is None:
                if segment:segments.append(segment);segment=[]
            else:segment.append((i,row['rpm'],row['metrics'][key]/factor))
        if segment:segments.append(segment)
        return segments
    def paintEvent(self,event):
        p=QPainter(self);p.setRenderHint(QPainter.RenderHint.Antialiasing)
        fm=p.fontMetrics();line=fm.height()+5;self.hits=[]
        for i,(_,title,unit,color,_) in enumerate(self.fields):
            p.setPen(QColor(color));suffix=(' · eje izquierdo' if i==0 else ' · eje derecho') if len(self.fields)>1 else ''
            p.drawText(QRectF(12,8+i*line*2,self.width()-24,line*2),Qt.TextFlag.TextWordWrap,title+' ['+unit+']'+suffix)
        box=QRectF(64,12+len(self.fields)*line*2,max(1,self.width()-128),max(1,self.height()-(len(self.fields)*2+3)*line-24))
        p.setPen(QColor('#324762'));p.drawRect(box)
        valid=[r for r in self.rows if r['metrics'] is not None]
        if not valid:
            p.setPen(QColor('#8ba2be'));p.drawText(box.adjusted(8,0,-8,0),Qt.AlignmentFlag.AlignCenter|Qt.TextFlag.TextWordWrap,'Sin puntos convergidos para graficar')
        if self.rows:
            lo,hi=min(r['rpm'] for r in self.rows),max(r['rpm'] for r in self.rows)
            span=hi-lo or 1
            for rpm in sorted(set(r['rpm'] for r in self.rows)):
                x=box.left()+(rpm-lo)/span*box.width()
                p.setPen(QColor('#8ba2be'));p.drawText(QRectF(x-30,box.bottom()+5,60,line),Qt.AlignmentFlag.AlignHCenter,str(rpm))
            for axis,(key,_,_,color,factor) in enumerate(self.fields):
                values=[r['metrics'][key]/factor for r in valid]
                if not values:continue
                bottom,top=min(0,min(values)),max(0,max(values))
                spread=top-bottom or 1
                if bottom<0:bottom-=spread*.08
                top+=spread*.08
                def mapped(rpm,value):return QPointF(box.left()+(rpm-lo)/span*box.width(),box.bottom()-(value-bottom)/(top-bottom)*box.height())
                p.setPen(QColor(color))
                for fraction in (0,.5,1):
                    y=box.bottom()-box.height()*fraction
                    x=box.right()+5 if axis else 0
                    p.drawText(QRectF(x,y-line/2,58,line),Qt.AlignmentFlag.AlignLeft if axis else Qt.AlignmentFlag.AlignRight,f'{bottom+(top-bottom)*fraction:.4g}')
                p.setPen(QPen(QColor(color),1.6))
                for segment in self.series_segments(key,factor):
                    previous=None
                    for index,rpm,value in segment:
                        position=mapped(rpm,value)
                        if previous is not None:p.drawLine(previous,position)
                        p.setBrush(QColor(color));p.drawEllipse(position,4,4)
                        if index==self.current:
                            p.setBrush(Qt.BrushStyle.NoBrush);p.drawEllipse(position,7,7)
                        previous=position;self.hits.append((index,position))
        p.setPen(QColor('#8ba2be'));p.drawText(QRectF(0,self.height()-line-3,self.width(),line),Qt.AlignmentFlag.AlignCenter,'RPM · puntos calculados; segmentos rectos')
        if self.hasFocus():p.setPen(QPen(QColor('#0284c7'),2));p.setBrush(Qt.BrushStyle.NoBrush);p.drawRect(self.rect().adjusted(1,1,-2,-2))
    def mousePressEvent(self,event):
        self.setFocus()
        if self.hits:
            index,point=min(self.hits,key=lambda item:math.hypot(item[1].x()-event.position().x(),item[1].y()-event.position().y()))
            if math.hypot(point.x()-event.position().x(),point.y()-event.position().y())<=18:self.selected.emit(index)
        super().mousePressEvent(event)
    def keyPressEvent(self,event):
        choices=[i for i,r in enumerate(self.rows) if r['metrics'] is not None]
        if choices and event.key() in (Qt.Key.Key_Left,Qt.Key.Key_Right,Qt.Key.Key_Home,Qt.Key.Key_End):
            if event.key()==Qt.Key.Key_Home:index=0
            elif event.key()==Qt.Key.Key_End:index=len(choices)-1
            elif self.current not in choices:index=0
            else:index=max(0,min(len(choices)-1,choices.index(self.current)+(1 if event.key()==Qt.Key.Key_Right else -1)))
            self.selected.emit(choices[index]);event.accept();return
        super().keyPressEvent(event)


class PerformanceSummary(QWidget):
    def __init__(self,names):
        super().__init__();self.values={};parts=[]
        for name in names:
            part=QWidget();layout=QVBoxLayout(part);layout.setContentsMargins(0,0,0,0);layout.setSpacing(5)
            layout.setVerticalSizeConstraint(QLayout.SizeConstraint.SetMinimumSize)
            layout.addWidget(text(name,'unit'));value=text('—','propertyValue');layout.addWidget(value)
            self.values[name]=value;parts.append(part)
        layout=QVBoxLayout(self);layout.setContentsMargins(0,0,0,0)
        layout.setVerticalSizeConstraint(QLayout.SizeConstraint.SetMinimumSize)
        layout.addWidget(Columns(Columns(*parts[:2],400),Columns(*parts[2:],400),850))
    def set_value(self,name,value):self.values[name].setText(str(value))


class PerformanceView(QScrollArea):
    def __init__(self,controller):
        super().__init__();self.controller=controller;self.sweep=None;self.rows=[]
        self._historical_context=None;self._session_seen=None;self._cancelled_sweep=None
        self.setWidgetResizable(True);self.setFrameShape(QScrollArea.Shape.NoFrame)
        body=QWidget();self.setWidget(body);box=QVBoxLayout(body);box.setContentsMargins(20,16,20,16);box.setSpacing(12)
        box.addWidget(Header('Rendimiento','Curvas derivadas de los puntos simulados del barrido seleccionado.',
            'Potencia/par indicados · sin pérdidas mecánicas · no representan valores al eje.'))
        self.empty_label=text('Todavía no hay una curva de rendimiento calculada para este proyecto.');box.addWidget(self.empty_label)
        self.setup=Panel('CURVA DE RENDIMIENTO');box.addWidget(self.setup)
        form=QFormLayout();form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows);self.setup.content.addLayout(form)
        self.rpm_edits=[]
        for title,original in zip(('Inicio [rpm]','Final [rpm]','Incremento [rpm]'),(controller.start_rpm_edit,controller.end_rpm_edit,controller.step_rpm_edit)):
            edit=QLineEdit(original.text());edit.setMaximumWidth(150);edit.setAccessibleName('Rendimiento · '+title)
            form.addRow(title,edit);self.rpm_edits.append(edit)
            edit.textChanged.connect(lambda value,target=original:self.copy_text(target,value))
            original.textChanged.connect(lambda value,target=edit:self.copy_text(target,value))
            edit.textChanged.connect(self.update_plan)
        self.plan_label=text();self.setup.content.addWidget(self.plan_label)
        self.calculate_button=QPushButton('Calcular rendimiento');self.calculate_button.setObjectName('primaryAction');self.setup.content.addWidget(self.calculate_button)
        self.progress_panel=Panel('CALCULANDO RENDIMIENTO');box.addWidget(self.progress_panel)
        self.progress_text=text();self.progress_panel.content.addWidget(self.progress_text)
        self.cancel_button=QPushButton('Cancelar');self.progress_panel.content.addWidget(self.cancel_button)
        self.cancel_button.clicked.connect(controller.cancel);self.calculate_button.clicked.connect(self.calculate)
        source=Panel('BARRIDO SELECCIONADO');box.addWidget(source);self.source_panel=source
        actions=QGridLayout();source.content.addLayout(actions)
        self.open_button=QPushButton('Abrir barrido existente…')
        self.reuse_button=QPushButton('Usar barrido actual');self.export_button=QPushButton('Exportar rendimiento CSV…')
        actions.addWidget(self.open_button,0,0);actions.addWidget(self.reuse_button,0,1);actions.addWidget(self.export_button,1,0,1,2)
        self.identity=text('No hay barrido seleccionado. Abrí uno guardado o usá el barrido actual.');source.content.addWidget(self.identity)
        self.error=ValidationMessage();source.content.addWidget(self.error)
        self.plan_status=text('','unit');box.addWidget(self.plan_status)
        self.summary=PerformanceSummary(('Mayor potencia entre puntos calculados','Mayor par entre puntos calculados','Puntos convergidos','Rango RPM del barrido'))
        panel=Panel('RESUMEN DE LOS PUNTOS');panel.content.addWidget(self.summary);box.addWidget(panel)
        self.result_panels=[panel]
        self.main_plot=PerformancePlot((('indicated_power_W','Potencia indicada','kW','#38bdf8',1000),('indicated_torque_Nm','Par indicado equivalente','N·m','#f59e0b',1)))
        plot_panel=Panel('POTENCIA Y PAR INDICADOS');plot_panel.content.addWidget(self.main_plot);box.addWidget(plot_panel)
        self.result_panels.append(plot_panel)
        self.detail=text('Seleccioná un punto en el gráfico o una fila en la tabla.');plot_panel.content.addWidget(self.detail)
        self.point_button=QPushButton('Abrir resultado del punto');plot_panel.content.addWidget(self.point_button)
        plot_panel.content.addWidget(text(NOTICE,'unit'))
        self.secondary=[];panels=[]
        for key,title,unit,factor in (('W_C_J','Trabajo indicado','J/ciclo',1),('p_max_Pa','Presión máxima absoluta','kPa',1000)):
            plot=PerformancePlot(((key,title,unit,'#38bdf8',factor),));self.secondary.append(plot)
            panel=Panel(title.upper());panel.content.addWidget(plot);panels.append(panel)
        secondary=Columns(*panels,850);box.addWidget(secondary);self.result_panels.append(secondary)
        panel=Panel('PUNTOS DEL BARRIDO');box.addWidget(panel)
        self.result_panels.append(panel)
        self.table=QTableWidget(0,6);self.table.setAccessibleName('Puntos de rendimiento indicado')
        self.table.setStyleSheet('QTableWidget::item:selected { color: #e5edf7; background: #213a52; }')
        self.table.setHorizontalHeaderLabels(['RPM','Estado','W_C [J/ciclo]','Potencia indicada [kW]','Par indicado equivalente [N·m]','pmax [kPa abs]'])
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers);self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection);self.table.verticalHeader().hide()
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.setMinimumHeight(220);panel.content.addWidget(self.table)
        self.open_button.clicked.connect(self.open_sweep);self.reuse_button.clicked.connect(self.reuse_current)
        self.export_button.clicked.connect(self.export);self.point_button.clicked.connect(self.open_point)
        self.table.itemSelectionChanged.connect(self.selection_changed)
        for plot in (self.main_plot,*self.secondary):plot.selected.connect(self.table.selectRow)
        self.controller.idle.connect(self.calculation_finished)
        self.controller.context_changed.connect(self.refresh_context)
        self.controller.activity_changed.connect(self.refresh_available)
        self.update_plan();self.refresh_available();self.selection_changed();box.addStretch()

    def project_context(self):
        try:
            project,origin=self.controller.project_snapshot()
            return configuration_key(project),origin['source_path']
        except (ProjectError,TypeError):return None

    def compatible(self,sweep):
        if sweep is None:return False
        inputs=sweep['index']['common_inputs'];origin=inputs.get('origin')
        return bool(origin and self.project_context()==(configuration_key(Project.from_dict(inputs['project_snapshot'])),origin['source_path']))

    def refresh_context(self):
        # Cambiar RPM notifica contexto también; solo un cambio de motor retira datos.
        if self.sweep is not None and not self.compatible(self.sweep):
            if self._historical_context is None or self._historical_context!=(self.project_context(),):
                self.clear_sweep()
        self.refresh_available()

    def sync_session(self):
        self.refresh_context()
        current=self.controller.sweep
        if not self.controller.active and current is not None and current is not self._session_seen:
            self._session_seen=current
            if current is not self._cancelled_sweep and self.compatible(current) and current['index']['state']!='cancelled':
                complete=current['index']['state']=='converged'
                # Un diagnóstico no sustituye una curva previa; sin ella se admiten
                # los puntos válidos de un barrido parcial, con sus huecos y estado.
                if complete or (not any(r['metrics'] for r in self.rows) and any(r['metrics'] for r in sweep_metrics(current))):
                    self.set_sweep(current);self._historical_context=None
        self.refresh_available()

    def calculation_finished(self):
        # Cancelar puede llegar después de cerrar el índice, antes de finished Qt.
        if self.controller.cancel_requested:self._cancelled_sweep=self.controller.sweep
        self.sync_session()
        c=self.controller;message=c.error_label.text()
        if c._running_sweep:
            if c.cancel_requested or (c.sweep and c.sweep['index']['state']=='cancelled'):
                message='Nuevo cálculo cancelado.'
                if any(r['metrics'] for r in self.rows):
                    message+=(' Se conserva la última curva completa disponible.' if self.sweep['index']['state']=='converged' else ' Se conserva la curva anterior disponible.')
            elif c.sweep and c.sweep['index']['state']!='converged':message=message or c.sweep['index']['reason']
        self.error.setText(message)

    def clear_sweep(self):
        self.sweep=None;self.rows=[];self._historical_context=None;self._session_seen=None;self.table.setRowCount(0)
        for plot in (self.main_plot,*self.secondary):plot.set_rows([])
        self.identity.setText('');self.error.clear();self.selection_changed()

    @staticmethod
    def copy_text(target,value):
        if target.text()!=value:target.setText(value)

    def configured_plan(self):
        values=[edit.text().strip() for edit in self.rpm_edits]
        if any(not value.isascii() or not value.isdigit() for value in values):raise ProjectError('RPM e incremento: ingresá enteros, sin separadores ni unidades.')
        cycle=self.controller.project_cycle() if self.controller.project_cycle else '2T'
        return plan_rpms(*map(int,values),cycle=cycle)

    def plan_matches_sweep(self,sweep):
        try:return sweep is not None and self.configured_plan()==sweep['index']['rpms']
        except (ProjectError,ValueError):return False

    def update_plan(self):
        if hasattr(self,'plan_status'):self.refresh_available()

    def refresh_plan(self,running,has_curve):
        try:
            planned=' · '.join(map(str,self.configured_plan()))+' rpm';valid=True
            self.plan_label.setText('Puntos: '+planned)
        except (ProjectError,ValueError) as exc:
            planned='Plan inválido';valid=False;self.plan_label.setText(str(exc))
        self.calculate_button.setText('Recalcular rendimiento' if has_curve else 'Calcular rendimiento')
        self.calculate_button.setEnabled(not running and valid and self.project_context() is not None)
        for edit in self.rpm_edits:edit.setEnabled(not running)
        self.plan_status.setVisible(has_curve)
        if not has_curve:return
        previous=' · '.join(map(str,self.sweep['index']['rpms']))+' rpm'
        if running:
            message='Resultado anterior · Calculando nueva curva…\nLa curva visible corresponde al cálculo anterior.\nCurva anterior: '+previous
        elif self.plan_matches_sweep(self.sweep):
            message=('✓ Curva actualizada' if self.compatible(self.sweep) else 'Análisis histórico · plan RPM coincidente')+'\n'+previous
        else:
            message='! Curva pendiente de actualización\nLa curva visible corresponde al barrido anterior. Recalculá para aplicar las RPM configuradas.\nCurva anterior: '+previous+'\nNuevo cálculo: '+planned
        self.plan_status.setText(message)

    def calculate(self,checked=False,*,output=None):
        if self.controller.active:return
        self.controller.start_performance(output=output)
        self.error.setText(self.controller.error_label.text())
        self.refresh_available()

    def refresh_available(self):
        running=self.controller.active
        has_curve=any(row['metrics'] is not None for row in self.rows)
        self.setup.setVisible(True);self.empty_label.setVisible(not has_curve and not running)
        self.refresh_plan(running,has_curve)
        self.progress_panel.setVisible(running)
        self.progress_panel.heading.setText('CALCULANDO RENDIMIENTO' if self.controller._running_sweep else 'CÁLCULO EN CURSO')
        self.open_button.setEnabled(not running)
        self.cancel_button.setEnabled(running and not self.controller.cancel_requested)
        self.identity.setVisible(self.sweep is not None)
        self.source_panel.heading.setText('ANÁLISIS HISTÓRICO' if self.sweep is None else 'BARRIDO SELECCIONADO')
        self.reuse_button.setVisible(False)
        self.export_button.setVisible(self.sweep is not None and not running)
        for panel in self.result_panels:panel.setVisible(self.sweep is not None)
        if running:
            c=self.controller;finished=c.finished_points;total=len(c._captured_rpms)
            count=sum(state=='converged' for state in finished.values())
            self.progress_text.setText(c.state_label.text()+'\n'+c.progress_label.text()+'\n'+c.memory_label.text()+f'\nPuntos convergidos: {count} · Pendientes: {total-len(finished)}')
        self.reuse_button.setEnabled(self.controller.sweep is not None and not self.controller.active)
        self.export_button.setEnabled(self.sweep is not None)
        self.selection_changed()
    def open_sweep(self,checked=False,*,path=None):
        if path is None:path,_=QFileDialog.getOpenFileName(self,'Abrir barrido para Rendimiento','','Barrido (series.json)')
        if not path:return
        try:
            self.set_sweep(load_sweep(path));self._historical_context=(self.project_context(),);self._session_seen=self.controller.sweep
            if not self.compatible(self.sweep):self.identity.setText('Análisis histórico · no es la curva del proyecto actual\n'+self.identity.text())
        except (ResultError,ValueError) as exc:self.error.setText(str(exc)+' Se conserva la selección anterior.')
    def reuse_current(self):
        if self.controller.sweep is not None and not self.controller.active:
            self.set_sweep(self.controller.sweep);self._historical_context=(self.project_context(),);self._session_seen=self.controller.sweep
            if not self.compatible(self.sweep):self.identity.setText('Análisis histórico · no es la curva del proyecto actual\n'+self.identity.text())
    def set_sweep(self,sweep):
        rows=sweep_metrics(sweep)  # Validar antes de sustituir la selección.
        self.sweep,self.rows=sweep,rows;index=sweep['index'];inputs=index['common_inputs'];case=inputs['case']
        origin=inputs.get('origin');name=origin['project_name'] if origin else case['identifier']
        cycle=case['project_geometry']['cycle']
        self.identity.setText(f"{name} · {cycle} · {STATES[index['state']]}\nRPM: "+', '.join(str(r['rpm']) for r in rows)+f"\n{str(sweep['path'])}")
        self.identity.setToolTip(str(sweep['path']));self.error.clear()
        valid=[row['metrics'] for row in rows if row['metrics'] is not None]
        for key,caption,factor,unit in (('indicated_power_W','Mayor potencia entre puntos calculados',1000,'kW'),('indicated_torque_Nm','Mayor par entre puntos calculados',1,'N·m')):
            best=max(valid,key=lambda r:r[key]) if valid else None
            self.summary.set_value(caption,f"{best[key]/factor:.6f} {unit} · {best['rpm']} rpm" if best else '—')
        self.summary.set_value('Puntos convergidos',f'{len(valid)} / {len(rows)}')
        self.summary.set_value('Rango RPM del barrido',f"{min(r['rpm'] for r in rows)}–{max(r['rpm'] for r in rows)} rpm")
        self.table.setRowCount(len(rows))
        for i,row in enumerate(rows):
            metrics=row['metrics']
            values=[str(row['rpm']),STATES[row['state']]]+[f'{metrics[key]/factor:.9g}' if metrics else '—' for key,factor in (('W_C_J',1),('indicated_power_W',1000),('indicated_torque_Nm',1),('p_max_Pa',1000))]
            for col,value in enumerate(values):
                item=QTableWidgetItem(value);item.setToolTip(row['reason']);self.table.setItem(i,col,item)
        for plot in (self.main_plot,*self.secondary):plot.set_rows(rows)
        self.table.resizeRowsToContents();self.table.selectRow(0);self.selection_changed();self.refresh_available()
    def selection_changed(self):
        index=self.table.currentRow();row=self.rows[index] if 0<=index<len(self.rows) else None
        metrics=row['metrics'] if row else None;self.point_button.setEnabled(metrics is not None and not self.controller.active)
        for plot in (self.main_plot,*self.secondary):plot.set_current(index)
        if row is None:self.detail.setText('Seleccioná un punto en el gráfico o una fila en la tabla.');return
        if metrics:
            self.detail.setText(f"{row['rpm']} rpm · {STATES[row['state']]}\nPotencia indicada: {metrics['indicated_power_W']/1000:.6f} kW · Par indicado equivalente: {metrics['indicated_torque_Nm']:.6f} N·m\nW_C: {metrics['W_C_J']:.9g} J/ciclo · pmax: {metrics['p_max_Pa']/1000:.9g} kPa abs")
        else:self.detail.setText(f"{row['rpm']} rpm · {STATES[row['state']]} · {row['reason']}\nSin magnitudes indicadas disponibles.")
    def open_point(self):
        index=self.table.currentRow()
        if self.controller.active:return
        if 0<=index<len(self.rows) and self.rows[index]['metrics'] is not None:
            self.controller._show_series_point(self.sweep['results'][index])
    def export(self,checked=False,*,folder=None):
        if self.sweep is None:return
        if folder is None:folder,_=QFileDialog.getSaveFileName(self,'Carpeta nueva para rendimiento.csv','','Carpeta (*)')
        if not folder:return
        try:
            export_performance_csv(folder,self.sweep);self.error.setText('CSV guardado en '+str(folder));visual_state(self.error,'success')
        except (ComparisonError,ResultError) as exc:self.error.setText(str(exc))
