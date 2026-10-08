"""Simulación de referencia o copia del editor mediante QProcess asíncrono."""
import json
import math
from pathlib import Path
import sys
import tempfile
import time

from PySide6.QtCore import QPointF, QProcess, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (QDialog, QDialogButtonBox, QFileDialog, QGridLayout,
    QComboBox, QTabWidget, QLineEdit, QFormLayout, QHBoxLayout, QLabel, QPlainTextEdit, QPushButton, QScrollArea, QVBoxLayout, QWidget)

from .prototype import memory_mib, write_json
from .reference_results import ResultError, load_result, new_output_path, reference_inputs, project_inputs
from .project import Project, ProjectError
from .simulation import TWO_LAYOUT, FOUR_LAYOUT
from .project_case import configuration_key, validate_rpm
from .sweep import plan_rpms, load_sweep, write_index
from .sweep_view import SweepDialog
from .comparison_view import ComparisonDialog
from .external_view import ExternalDialog
from .runtime import worker_command, diagnostic
from .ui import Header, Panel, ContextPanel, SimulationColumns, PropertyTable, Badge, Message, ValidationMessage, visual_state
from .kinematics import calculate_geometry
from .performance import result_metrics, NOTICE


class PressurePlot(QWidget):
    def __init__(self, pv=False):
        super().__init__()
        self.pv, self.points = pv, []
        self.layout = TWO_LAYOUT
        self.volume_range=None
        self.mirror=None
        self.setMinimumHeight(205)
        self.setMinimumWidth(260)
        self.setAccessibleName('Presión-volumen en orden temporal' if pv else 'Presión absoluta frente al ángulo continuo')

    def set_rows(self, rows, layout=None):
        layout=layout or self.layout
        self.layout=layout
        # No ordenar V ni aplicar módulo a ángulos: preservar la trayectoria.
        origin = rows[0]['angle_deg']-(0 if layout.period==720 else 180) if rows else 0
        self.points = [(r['V_m3'][layout.cylinder]*1e6 if self.pv else r['angle_deg']-origin,
                        r['p_T_Y'][layout.cylinder][0]/1000) for r in rows]
        self.update()
        if self.mirror:
            self.mirror.layout=self.layout;self.mirror.points=self.points;self.mirror.volume_range=self.volume_range;self.mirror.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(QColor('#b4d9f5'))
        fm = p.fontMetrics()
        line = fm.height()+5
        title = 'Presión–volumen · orden temporal' if self.pv else f'Presión–ángulo · ciclo {self.layout.period}°'
        p.drawText(QRectF(8, 4, self.width()-16, line), title)
        p.drawText(QRectF(8, line+4, self.width()-16, line), 'Presión absoluta [kPa]')
        xs,ys=zip(*self.points) if self.points else ((),())
        lo,hi=((0.,max(xs)*1.05) if xs else self.volume_range or (0.,1.)) if self.pv else ((0.,720.) if self.layout.period==720 else (180.,540.))
        top=max(ys)*1.05 if ys else 1.
        margin = max(55, fm.horizontalAdvance(f'{top:.0f}')+12)
        box = QRectF(margin, 2*line+12, max(1, self.width()-margin-24), max(1, self.height()-5*line-20))
        p.setPen(QColor('#61758f'))
        p.drawLine(box.topLeft(), box.bottomLeft())
        p.drawLine(box.bottomLeft(), box.bottomRight())
        for fraction in (0, .5, 1):
            y = box.bottom()-box.height()*fraction
            if self.points:p.drawText(QRectF(0, y-line/2, margin-7, line), Qt.AlignmentFlag.AlignRight, f'{top*fraction:.0f}')
            x = box.left()+box.width()*fraction
            caption = f'{lo+(hi-lo)*fraction:.0f}'
            if not self.pv:
                caption += '\n'+('PMS' if self.layout.period==720 or fraction == .5 else 'PMI')
            if not self.pv or self.points or self.volume_range:
                p.drawText(QRectF(x-28, box.bottom()+5, 56, line*2), Qt.AlignmentFlag.AlignHCenter, caption)
        if not self.points:
            p.drawText(box.adjusted(8,0,-8,0), Qt.AlignmentFlag.AlignCenter|Qt.TextFlag.TextWordWrap,
                       'Sin datos de ciclo para graficar')
        path = QPainterPath()
        for i, (x, y) in enumerate(self.points):
            point = QPointF(box.left()+(x-lo)/(hi-lo)*box.width(), box.bottom()-y/top*box.height())
            path.moveTo(point) if i == 0 else path.lineTo(point)
        p.setPen(QPen(QColor('#69baf0'), 2))
        p.drawPath(path)
        p.drawText(QRectF(margin, self.height()-line, box.width(), line), Qt.AlignmentFlag.AlignCenter,
                   'Volumen del cilindro [cm³]' if self.pv else 'Ángulo continuo del ciclo [°]')


class SimulationView(QScrollArea):
    idle = Signal()
    context_changed = Signal()
    activity_changed = Signal()

    def __init__(self, project_snapshot=None, project_cycle=None):
        super().__init__()
        self.setWidgetResizable(True)
        self.setFrameShape(QScrollArea.Shape.NoFrame)
        self.process = None
        self.result = None
        self.output = None
        self.cancel_requested = False
        self.forced = False
        self._buffer = b''
        self._stderr = b''
        self._started = 0.
        self.completed_cycles = 0
        self.inputs = reference_inputs()
        self.project_snapshot = project_snapshot
        self.project_cycle = project_cycle
        self._request_path = None
        self.sweep = None
        self.sweep_dialog = None
        self._running_sweep = False
        self._completion_workspace = 'sweep'
        self.finished_points = {}
        self._point_started = 0.
        self._point_caption = ""
        self._captured_rpms = [3000]
        self._series_id = None
        self._finished_manifest = None
        self.workspace_router=None
        body=QWidget();layout=QVBoxLayout(body);layout.setContentsMargins(20,16,20,16);layout.setSpacing(12)
        def label(text='',style=''):
            w=QLabel(text);w.setTextFormat(Qt.TextFormat.PlainText);w.setWordWrap(True);w.setObjectName(style);return w
        layout.addWidget(Header('Simulación','Prepará las entradas y seguí el cálculo del caso seleccionado.','Modelo 0D · Energía prescrita · Sin ondas ni validación experimental.'))
        preparation=Panel('01 · PREPARACIÓN');self.run_workspace=QWidget();run_layout=QVBoxLayout(self.run_workspace);run_layout.setContentsMargins(0,0,0,0);run_layout.setSpacing(16)
        self.context_panel=ContextPanel()
        self.context_table=PropertyTable(('Caso / proyecto','Ciclo','Geometría','Compresión','Modelo','Integración','Perfil','Regularización','Aporte térmico','Procedencia'))
        self.context_panel.content.addWidget(self.context_table)
        self.context_stale=label('','fieldError')
        self.columns=SimulationColumns(preparation,self.run_workspace,self.context_panel);layout.addWidget(self.columns)
        self.title_label=label('','sectionTitle');self.description_label=label('','unit');self.parameters_label=label()
        for w in (self.title_label,self.description_label,self.parameters_label):w.hide()
        preparation.content.addWidget(label('Origen de las entradas','panelTitle'))
        self.origin_combo=QComboBox();self.origin_combo.addItems(['Referencia 2T','Proyecto actual','Referencia 4T'])
        self.origin_combo.setAccessibleName('Origen de la próxima ejecución');preparation.content.addWidget(self.origin_combo)
        self.origin_combo.setMinimumWidth(0)
        self.origin_combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon);self.origin_combo.setMinimumContentsLength(16)
        self.options=QWidget();form=QFormLayout(self.options);form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
        self.mode_combo=QComboBox();self.mode_combo.addItems(['Punto individual','Barrido corto']);form.addRow('Ejecución',self.mode_combo)
        self.rpm_edit=QLineEdit('3000');self.start_rpm_edit,self.end_rpm_edit,self.step_rpm_edit=QLineEdit('2500'),QLineEdit('3500'),QLineEdit('500')
        for title,edit in [('Punto [rpm]',self.rpm_edit),('Inicio [rpm]',self.start_rpm_edit),('Final [rpm]',self.end_rpm_edit),('Incremento [rpm]',self.step_rpm_edit)]:
            edit.setMaximumWidth(150);edit.setAccessibleName(title);form.addRow(title,edit)
        self.plan_label=label();form.addRow(self.plan_label);preparation.content.addWidget(self.options);self.options.hide()
        self.run_button=QPushButton('&Ejecutar cálculo');self.cancel_button=QPushButton('&Cancelar');self.cancel_button.setEnabled(False)
        self.check_button=QPushButton('Compro&bar');self.details_button=QPushButton('&Detalles')
        self.run_button.setObjectName('primaryAction')
        actions=QGridLayout()
        actions.addWidget(self.check_button,0,0);actions.addWidget(self.details_button,0,1)
        actions.addWidget(self.run_button,1,0,1,2);actions.addWidget(self.cancel_button,2,0,1,2)
        preparation.content.addWidget(label('Validación y ejecución','panelTitle'));preparation.content.addLayout(actions)
        preparation.content.addStretch()
        progress=Panel('02 · ESTADO DEL CÁLCULO');run_layout.addWidget(progress)
        self.state_badge=Badge('INACTIVO');progress.content.addWidget(self.state_badge)
        self.state_label=Message('Esperando inicio de cálculo.','sectionTitle');self.progress_label=label('','unit')
        self.state_label.changed.connect(self._state_changed)
        self.error_label=ValidationMessage()
        for w in (self.state_label,self.progress_label,self.context_stale):progress.content.addWidget(w)
        self.context_stale.hide()
        self.message_host=QVBoxLayout();self.message_host.addWidget(self.error_label);preparation.content.addLayout(self.message_host)
        self.open_button=QPushButton('&Abrir resultado…');self.open_sweep_button=QPushButton('Abrir barrido…');self.sweep_button=QPushButton('Ver barrido…');self.sweep_button.setEnabled(False)
        self.compare_button=QPushButton('Comparar resultados…');self.external_button=QPushButton('Datos externos…')
        self.compare_button.hide();self.external_button.hide();self.comparison_dialog=None;self.external_dialog=None
        self.external_button.clicked.connect(self.show_external)
        self.result_panel=Panel('RESULTADO ACTUAL');result_layout=self.result_panel.content
        self.result_status_label=label('No hay resultado abierto','sectionTitle');result_layout.addWidget(self.result_status_label)
        self.identity_label=label();self.stale_label=label('','fieldError')
        result_layout.addWidget(self.identity_label);result_layout.addWidget(self.stale_label)
        self.result_tabs=QTabWidget();result_layout.addWidget(self.result_tabs)
        summary=QWidget();summary_layout=QVBoxLayout(summary)
        self.summary_label=Message('Abrí un resultado o un barrido en Resultados para consultar datos, o ejecutá un caso admitido.');self.summary_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.memory_label=Message('','unit');self.path_label=label('Cada ejecución se guarda en una carpeta nueva de MotorSim/Resultados.','unit')
        for w in (self.summary_label,self.memory_label,self.path_label):summary_layout.addWidget(w)
        summary_layout.addStretch();self.result_tabs.addTab(summary,'Resumen')
        plots=QWidget();self.plots_grid=QGridLayout(plots);self.angle_plot,self.pv_plot=PressurePlot(),PressurePlot(True)
        self.result_tabs.addTab(plots,'Curvas')
        self.monitor_summary=label();self.monitor_timing=label('','unit')
        self.summary_label.changed.connect(self.monitor_summary.setText);self.memory_label.changed.connect(self.monitor_timing.setText)
        self.summary_label.changed.connect(lambda value:self.monitor_summary.setVisible(bool(value)))
        self.memory_label.changed.connect(lambda value:self.monitor_timing.setVisible(bool(value)))
        self.monitor_summary.hide();self.monitor_timing.hide()
        progress.content.addWidget(self.monitor_summary);progress.content.addWidget(self.monitor_timing)
        self.preview_angle,self.preview_pv=PressurePlot(),PressurePlot(True)
        self.angle_plot.mirror=self.preview_angle;self.pv_plot.mirror=self.preview_pv
        progress.content.addWidget(self.preview_angle);progress.content.addWidget(self.preview_pv)
        self.parameters_text=QPlainTextEdit();self.parameters_text.setReadOnly(True);self.result_tabs.addTab(self.parameters_text,'Parámetros')
        self.balances_text=QPlainTextEdit();self.balances_text.setReadOnly(True);self.result_tabs.addTab(self.balances_text,'Balances')
        self.result_host=QVBoxLayout();self.result_host.addWidget(self.result_panel);run_layout.addLayout(self.result_host)
        layout.addStretch();self.setWidget(body)
        self.timer = QTimer(self)
        self.timer.setInterval(200)
        self.timer.timeout.connect(self._tick)
        self.run_button.clicked.connect(self.start)
        self.cancel_button.clicked.connect(self.cancel)
        self.open_button.clicked.connect(self.open_result)
        self.details_button.clicked.connect(self.show_details)
        self.check_button.clicked.connect(self.check_inputs)
        self.compare_button.clicked.connect(self.show_comparison)
        self.origin_combo.currentIndexChanged.connect(self._origin_changed)
        self.sweep_button.clicked.connect(self.show_sweep)
        self.open_sweep_button.clicked.connect(self.open_sweep)
        self.mode_combo.currentIndexChanged.connect(self._options_changed)
        for edit in (self.rpm_edit,self.start_rpm_edit,self.end_rpm_edit,self.step_rpm_edit):
            edit.textChanged.connect(self._options_changed)
        self._options_changed()
        self._describe_inputs()
        self._arrange()

    def _state_changed(self,value):
        if value=='En ejecución':caption,tone='EJECUTANDO','warning'
        elif value.startswith('Convergencia numérica'):caption,tone='CONVERGIDO','success'
        elif value.startswith('Sin convergencia'):caption,tone='NO CONVERGIDO','warning'
        elif value.startswith('Cancelando'):caption,tone='CANCELANDO','warning'
        elif value.startswith('Cancelado'):caption,tone='CANCELADO','warning'
        elif value.startswith('Error'):caption,tone='ERROR','error'
        elif value.startswith('Barrido:'):caption,tone='BARRIDO','neutral'
        else:caption,tone='INACTIVO','neutral'
        self.state_badge.set_state(caption,tone)

    def _empty_axes(self,geometry):
        cycle=geometry['cycle'] if geometry else ('4T' if self.origin_combo.currentIndex()==2 else '2T')
        if geometry is None and self.project_cycle:cycle=self.project_cycle()
        layout=FOUR_LAYOUT if cycle=='4T' else TWO_LAYOUT
        derived=calculate_geometry(geometry or {},cycle)
        for plot in (self.angle_plot,self.pv_plot):
            plot.volume_range=(derived.chamber,derived.maximum) if derived.chamber is not None and derived.maximum is not None else None
            plot.set_rows([],layout)

    def _rpms(self):
        def integer(edit):
            value=edit.text().strip()
            if not value or not value.isascii() or not value.isdigit():
                raise ProjectError('RPM e incremento: ingresá enteros, sin separadores ni unidades.')
            return int(value)
        cycle=self.project_cycle() if self.project_cycle else '2T'
        if self.mode_combo.currentIndex()==0:
            return [validate_rpm(integer(self.rpm_edit),cycle)]
        return plan_rpms(integer(self.start_rpm_edit),integer(self.end_rpm_edit),integer(self.step_rpm_edit),cycle)

    def _options_changed(self):
        sweep=self.mode_combo.currentIndex()==1
        self.rpm_edit.setEnabled(not sweep)
        self.options.layout().setRowVisible(self.rpm_edit,not sweep)
        for edit in (self.start_rpm_edit,self.end_rpm_edit,self.step_rpm_edit):
            edit.setEnabled(sweep)
            self.options.layout().setRowVisible(edit,sweep)
        invalid=False
        try:self.plan_label.setText('Lista exacta: '+', '.join(map(str,self._rpms()))+' rpm')
        except ProjectError as exc:self.plan_label.setText(str(exc));invalid=True
        for edit in (self.rpm_edit,self.start_rpm_edit,self.end_rpm_edit,self.step_rpm_edit):
            visual_state(edit,'error' if invalid and (edit is self.rpm_edit)!=sweep else 'neutral')
        self.project_changed()

    def show_sweep(self):
        if not self.sweep or self.active:return
        if self.sweep_dialog is None:self.sweep_dialog=SweepDialog(self,self._show_series_point)
        self.sweep_dialog.set_sweep(self.sweep)
        if self.workspace_router:self.workspace_router('sweep')
        else:self.sweep_dialog.show();self.sweep_dialog.raise_();self.sweep_dialog.activateWindow()

    def _show_series_point(self,result):
        self._display(result)
        if self.workspace_router:self.workspace_router('results')

    def open_sweep(self,checked=False,*,path=None):
        if self.active:return
        if path is None:
            path,_=QFileDialog.getOpenFileName(self,'Abrir barrido','','Índice (series.json)')
        if not path:return
        try:loaded=load_sweep(path)
        except ResultError as exc:self.error_label.setText(str(exc));return
        self.sweep=loaded;self.result=None;self.inputs=loaded['index']['common_inputs']
        self._describe_inputs();self.angle_plot.set_rows([]);self.pv_plot.set_rows([])
        self.summary_label.clear();self.error_label.clear()
        self.result_status_label.setText('Seleccioná un punto del barrido para consultar su resultado.')
        self.balances_text.clear();self.memory_label.clear()
        self.state_label.setText('Barrido: '+loaded['index']['reason'])
        self.progress_label.setText(f"Integración de la serie: {loaded['index']['integration_seconds']:.3f} s")
        self.path_label.setText(str(loaded['path']));self.sweep_button.setEnabled(True)
        self.show_sweep()

    def show_external(self):
        if self.workspace_router:
            self.workspace_router('external');return
        if self.external_dialog is None:self.external_dialog=ExternalDialog(self)
        self.external_dialog.show();self.external_dialog.raise_();self.external_dialog.activateWindow()

    def show_comparison(self):
        if self.workspace_router:
            self.workspace_router('compare');return
        if self.comparison_dialog is None:
            self.comparison_dialog = ComparisonDialog(self)
        self.comparison_dialog.show()
        self.comparison_dialog.raise_()
        self.comparison_dialog.activateWindow()

    def _capture(self):
        if self.origin_combo.currentIndex() != 1:
            return reference_inputs('4T' if self.origin_combo.currentIndex()==2 else '2T')
        if self.project_snapshot is None:
            raise ProjectError('No hay editor de proyecto disponible.')
        project, origin = self.project_snapshot()
        return project_inputs(project, origin, rpm=self._rpms()[0])

    def check_inputs(self):
        try:
            inputs = self._capture()
        except (ProjectError, ResultError) as exc:
            self.error_label.setText(str(exc))
            return
        self.error_label.setText('Entradas admitidas para este modelo. La convergencia no está garantizada.')
        if self.result is None and self.sweep is None and not self.active:
            self.inputs = inputs
            self._describe_inputs()

    def _origin_changed(self):
        self.options.setVisible(self.origin_combo.currentIndex()==1)
        # La selección prepara la próxima ejecución; no cambia la procedencia de evidencia abierta.
        if self.result is None and self.sweep is None and not self.active:
            try:
                self.inputs = self._capture()
                self.error_label.clear()
                self._describe_inputs()
            except (ProjectError, ResultError) as exc:
                self.error_label.setText(str(exc))
                self.title_label.setText('Geometría del proyecto · ensayo 0D')
                self.description_label.setText('Las condiciones son supuestos de referencia, no mediciones ni una calibración del motor ingresado.')
                self.parameters_label.clear()
                self.identity_label.clear()
                for value in self.context_table.values.values():value.setText('—')
                self.context_panel.set_summary('Entradas incompletas · revisar proyecto')
                self._empty_axes(None)

    def _describe_inputs(self):
        origin = self.inputs.get('origin')
        self.title_label.setText('Geometría del proyecto · ensayo 0D' if origin else 'Caso de referencia '+self.inputs['case']['identifier'])
        self.description_label.setText('Las condiciones son supuestos de referencia, no mediciones ni una calibración del motor ingresado.'
            if origin else 'Caso sintético, no motor medido. No utiliza los datos del proyecto abierto.')
        case = self.inputs['case']
        geometry = case['project_geometry']
        regime = f"{geometry['cycle']} · {case['rpm']:g} rpm"
        if self.active and self._running_sweep:regime='Barrido '+', '.join(map(str,self._captured_rpms))+' rpm'
        elif self.sweep and self.result is None:regime='Barrido '+', '.join(map(str,self.sweep['index']['rpms']))+' rpm'
        self.parameters_label.setText(f"{regime} · {geometry['bore_mm']:g} × {geometry['stroke_mm']:g} mm · "
            f"Compresión {geometry['compression_ratio']:g}:1 · Banda {self.inputs['variant']['delta_p_Pa']} Pa · Perfil {self.inputs['profile']['name']}")
        self.identity_label.setText((f"Proyecto utilizado: {origin['project_name']} · "
            + ('con cambios sin guardar' if origin['dirty'] else 'sin cambios pendientes')
            + f"\nArchivo al ejecutar: {origin['source_path'] or 'sin archivo asociado'}") if origin else '')
        self.identity_label.setVisible(bool(origin) and (self.result is not None or self.active or self.sweep is not None))
        self.parameters_text.setPlainText(json.dumps(self.inputs,ensure_ascii=False,indent=2))
        context={'Caso / proyecto':origin['project_name'] if origin else case['identifier'],
            'Ciclo':geometry['cycle'],'Geometría':f"{geometry['cylinder_count']} cil · {geometry['bore_mm']:g} × {geometry['stroke_mm']:g} mm",
            'Compresión':f"{geometry['compression_ratio']:g}:1",'Modelo':'0D · '+('3' if geometry['cycle']=='4T' else '4')+' volúmenes',
            'Integración':'RK4 adaptativo','Perfil':self.inputs['profile']['name'],
            'Regularización':f"{self.inputs['variant']['delta_p_Pa']} Pa",'Aporte térmico':'Energía prescrita',
            'Procedencia':(origin['source_path'] or 'Proyecto sin archivo asociado') if origin else 'Referencia sintética · no medida'}
        for name,value in context.items():self.context_table.set_value(name,value)
        self.context_panel.set_summary(' · '.join(context[k] for k in ('Ciclo','Geometría','Compresión','Integración','Perfil','Regularización')))
        if self.result is None:self._empty_axes(geometry)
        self.project_changed()

    def project_changed(self):
        stale = False
        if self.inputs.get('origin') and (self.active or self.result is not None or self.sweep is not None):
            try:
                current, origin = self.project_snapshot()
                stale = (configuration_key(current) != configuration_key(Project.from_dict(self.inputs['project_snapshot']))
                         or origin['source_path'] != self.inputs['origin']['source_path'])
                expected = (self._captured_rpms if self.active else
                    (self.sweep['index']['rpms'] if self.sweep and (self.result is None or
                        self.inputs.get('series_context',{}).get('series_id')==self.sweep['index']['series_id']) else [self.inputs['case']['rpm']]))
                stale = stale or self._rpms() != expected
            except (ProjectError, TypeError):
                stale = True
        self.stale_label.setText('El resultado corresponde a una configuración anterior' if stale else '')
        self.stale_label.setVisible(stale)
        self.context_stale.setText(self.stale_label.text());self.context_stale.setVisible(stale)
        if self.sweep_dialog:self.sweep_dialog.stale_label.setText(self.stale_label.text())
        self.context_changed.emit()

    @property
    def active(self):
        return self.process is not None

    def _arrange(self):
        wide = self.result_panel.width() >= 800
        self.plots_grid.addWidget(self.angle_plot, 0, 0)
        self.plots_grid.addWidget(self.pv_plot, 0 if wide else 1, 1 if wide else 0)
        self.plots_grid.setColumnStretch(0, 1)
        self.plots_grid.setColumnStretch(1, 1 if wide else 0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'plots_grid'):
            self._arrange()

    def show_details(self):
        if self.result is None and self.sweep is None and not self.active:
            try:
                self.inputs = self._capture()
                self._describe_inputs()
            except (ProjectError, ResultError) as exc:
                self.error_label.setText(str(exc))
                return
        self.parameters_text.setPlainText(json.dumps(self.inputs,ensure_ascii=False,indent=2))
        self.result_tabs.setCurrentIndex(2)
        if self.workspace_router:self.workspace_router('results')
        else:self.ensureWidgetVisible(self.result_panel)

    def start(self, checked=False, *, output=None, completion_workspace='sweep'):
        if self.active:
            return
        try:
            inputs = self._capture()
            executable,prefix,working_directory=worker_command()
            rpms = self._rpms() if 'origin' in inputs else [3000]
            running_sweep = len(rpms)>1
            target = Path(output) if output is not None else new_output_path()
            if target.exists():raise ProjectError('El destino ya existe; elegí una carpeta nueva. No se sobrescriben resultados.')
            request = None
            if 'origin' in inputs:
                target.parent.mkdir(parents=True, exist_ok=True)
                with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', prefix='motorsim-input-',
                        suffix='.json', dir=target.parent, delete=False) as stream:
                    request = Path(stream.name)
                    json.dump(dict(common_inputs=inputs,rpms=rpms) if running_sweep else inputs, stream, ensure_ascii=False, allow_nan=False)
        except (OSError, ProjectError, ResultError) as exc:
            self.error_label.setText(str(exc))
            return
        self.inputs = inputs
        self.sweep = None
        self._series_id = None
        self._finished_manifest = None
        self._running_sweep = running_sweep
        self._completion_workspace = completion_workspace
        self.finished_points = {}
        self._captured_rpms = rpms
        self._point_caption = ""
        if self.sweep_dialog:self.sweep_dialog.hide()
        self._request_path = request
        self._describe_inputs()

        self.output = target
        self.result = None
        self.angle_plot.set_rows([])
        self.pv_plot.set_rows([])
        self.summary_label.clear()
        self.result_status_label.setText('Sin resultado aceptado · cálculo en curso')
        self.balances_text.clear()
        self.error_label.clear()
        self.memory_label.clear()
        self._buffer = self._stderr = b''
        self.cancel_requested = self.forced = False
        self.completed_cycles = 0
        self._started = self._point_started = time.monotonic()
        self.state_label.setText('En ejecución')
        self.progress_label.setText('Ciclos completos: 0 · Esperando avance del cálculo…')
        self.path_label.setText(str(self.output))
        self.run_button.setEnabled(False)
        self.open_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.origin_combo.setEnabled(False)
        self.check_button.setEnabled(False)
        self.options.setEnabled(False)
        self.open_sweep_button.setEnabled(False)
        self.sweep_button.setEnabled(False)
        process = QProcess(self)
        self.process = process
        process.setWorkingDirectory(working_directory)
        process.setProgram(executable)
        arguments = [*prefix, '--output', str(self.output), '--control-stdin', '--cycle', self.inputs['case']['project_geometry']['cycle']]
        if request:
            arguments += ['--sweep-input' if running_sweep else '--project-input', str(request)]
        process.setArguments(arguments)
        process.readyReadStandardOutput.connect(self._read_progress)
        process.readyReadStandardError.connect(self._read_error)
        process.finished.connect(self._finished)
        process.errorOccurred.connect(self._process_error)
        self.timer.start()
        process.start()
        self._describe_inputs()

    def start_performance(self, *, output=None):
        """La misma captura, planificación, proceso y persistencia del barrido."""
        if self.active:return
        self.origin_combo.setCurrentIndex(1)
        self.mode_combo.setCurrentIndex(1)
        self.start(output=output,completion_workspace='performance')

    def _read_error(self):
        if self.process:
            self._stderr = (self._stderr+bytes(self.process.readAllStandardError()))[-8192:]

    def _read_progress(self):
        if not self.process:
            return
        self._buffer += bytes(self.process.readAllStandardOutput())
        while b'\n' in self._buffer:
            line, self._buffer = self._buffer.split(b'\n', 1)
            try:
                data = json.loads(line)
                if data.get('event') == 'sweep_started':
                    self._series_id=data['series_id']
                elif data.get('event') == 'finished':
                    self._finished_manifest=Path(data['manifest']).resolve()
                elif data.get('event') == 'point_start':
                    self._point_started=time.monotonic()
                    self._point_caption=f"Punto {data['point_index']+1}/{data['point_total']} · {data['rpm']} rpm · "
                    self.progress_label.setText(self._point_caption+'Iniciando…')
                elif data.get('event') == 'point_finished':
                    self.finished_points[data['point_index']]=data['state']
                elif data.get('event') == 'progress':
                    count, seconds = data['completed_cycles'], data['seconds']
                    if type(count) is int and 0 <= count <= 30 and math.isfinite(seconds) and seconds >= 0:
                        self.completed_cycles = count
                        self.progress_label.setText(self._point_caption+f'Ciclos completos: {count} · Integración: {seconds:.1f} s · RHS: {data["rhs"]}')
                elif data.get('event') == 'error':
                    self._stderr += str(data.get('message', '')).encode('utf-8')
            except (ValueError, KeyError, TypeError):
                self.error_label.setText('Se recibió un mensaje de avance ilegible.')
        self._buffer = self._buffer[-8192:]
        self.activity_changed.emit()

    def _tick(self):
        elapsed = time.monotonic()-self._started
        self.memory_label.setText(f'Tiempo de serie/ejecución: {elapsed:.1f} s · Punto: {time.monotonic()-self._point_started:.1f} s · Pico de interfaz: {memory_mib():.1f} MiB (proceso separado)')
        # Límite de supervisión, no ampliación de los 60 s de integración del hijo.
        if time.monotonic()-self._point_started >= 65 and not self.cancel_requested:
            self.cancel()
        self.activity_changed.emit()

    def cancel(self):
        if not self.active or self.cancel_requested:
            return
        self.cancel_requested = True
        self.cancel_button.setEnabled(False)
        self.state_label.setText('Cancelando…')
        self.activity_changed.emit()
        process = self.process
        process.write(b'cancel\n')
        QTimer.singleShot(3000, lambda: self._kill_if_active(process))

    def _kill_if_active(self, process):
        if self.process is process:
            self.forced = True
            self.error_label.setText('El cálculo no respondió a la cancelación; se detuvo el proceso.')
            process.kill()
            self._save_error_diagnostic()

    def _process_error(self, error):
        if error == QProcess.ProcessError.FailedToStart:
            self.error_label.setText('No se pudo iniciar el auxiliar de cálculo: '+self.process.errorString())
            self._save_error_diagnostic()
            self._finish_cleanup('Error de ejecución')

    def _save_error_diagnostic(self):
        try:
            path=diagnostic(self.error_label.text()+'\n'+self._stderr.decode('utf-8',errors='replace')
                +f'\nSalida: {self.output}\nProgreso: {self.progress_label.text()}'
                +(f'\nPID: {self.process.processId()}\nPrograma: {self.process.program()}' if self.process else ''))
            self.error_label.setText(self.error_label.text()+f'\nDiagnóstico: {path}')
        except OSError as exc:
            self.error_label.setText(self.error_label.text()+f'\nNo se pudo guardar diagnóstico: {exc}')

    def _finished(self, code, exit_status):
        self._read_progress()
        self._read_error()
        if self._running_sweep:
            try:
                if self._series_id is None:raise ResultError('El proceso no confirmó una carpeta de serie propia.')
                loaded=load_sweep(self.output/'series.json')
                if loaded['index']['series_id']!=self._series_id:raise ResultError('Índice ajeno a la ejecución iniciada.')
                if loaded['index']['state']=='running':
                    reason='Cancelación forzada' if self.cancel_requested else 'El proceso terminó sin cerrar la serie'
                    loaded['index'].update(state='cancelled' if self.cancel_requested else 'stopped',reason=reason)
                    for point in loaded['index']['points']:
                        if point['state']=='running':point.update(state='error',reason=reason)
                        elif point['state']=='not_executed':point['reason']='No ejecutado: '+reason
                if loaded['index']['state']=='converged' and (code!=0 or exit_status!=QProcess.ExitStatus.NormalExit):
                    raise ResultError('Salida del proceso incompatible con un barrido convergido.')
                loaded['index']['interface_wall_seconds']=time.monotonic()-self._started
                write_index(self.output,loaded['index'])
                self.sweep=loaded;self.result=None
                self.state_label.setText('Barrido: '+loaded['index']['reason'])
                self.progress_label.setText(f"Integración total: {loaded['index']['integration_seconds']:.3f} s")
                self._finish_cleanup()
                if self.window().isEnabled():
                    if self._completion_workspace=='performance' and self.workspace_router:self.workspace_router('performance')
                    else:self.show_sweep()
                self.project_changed()
            except (ResultError,OSError) as exc:
                self.error_label.setText(str(exc)+' '+self._stderr.decode('utf-8',errors='replace')[:2000])
                self._save_error_diagnostic()
                self._finish_cleanup('Cancelado / índice incompleto' if self.cancel_requested else 'Error de barrido')
            return
        if self.cancel_requested:
            try:
                result = load_result(self.output/'manifest.json')
                if result['status'] == 'cancelled':
                    self._record_timing(result)
                    self._display(result)
            except (ResultError, OSError) as exc:
                # Puede faltar el manifiesto tras una parada forzada o fallar su escritura.
                self.error_label.setText(self.error_label.text()+' '+str(exc))
                self._save_error_diagnostic()
            self._finish_cleanup('Cancelado')
            self.summary_label.setText('Diagnóstico no aceptado. La ejecución fue cancelada.')
            return
        try:
            if exit_status != QProcess.ExitStatus.NormalExit:
                raise ResultError('El proceso de cálculo terminó inesperadamente.')
            result = load_result(self.output/'manifest.json')
            if result['status'] == 'converged' and code != 0:
                raise ResultError('Código de salida incompatible con el resultado.')
            self._record_timing(result)
            self._display(result)
            self._finish_cleanup()
        except (ResultError,OSError) as exc:
            self.error_label.setText(str(exc)+' '+self._stderr.decode('utf-8', errors='replace')[:2000])
            self._save_error_diagnostic()
            self._finish_cleanup('Error de ejecución o resultado ilegible')

    def _record_timing(self, result):
        # Solo el resultado recién confirmado por el worker; abrir históricos no escribe.
        if self._finished_manifest == result['path'] and 'timings' in result['manifest']:
            result['manifest']['timings']['interface_wall_seconds'] = time.monotonic()-self._started
            write_json(result['path'], result['manifest'])

    def _finish_cleanup(self, state=None):
        process, self.process = self.process, None
        if process:
            process.deleteLater()
        self.timer.stop()
        if state:
            self.state_label.setText(state)
        self.run_button.setEnabled(True)
        self.open_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        self.origin_combo.setEnabled(True)
        self.check_button.setEnabled(True)
        self.options.setEnabled(True)
        self.open_sweep_button.setEnabled(True)
        self.sweep_button.setEnabled(self.sweep is not None)
        if self._request_path:
            try:
                self._request_path.unlink(missing_ok=True)
            except OSError as exc:
                self.error_label.setText(f'No se pudo retirar la copia temporal {self._request_path}: {exc}')
            self._request_path = None
        self.idle.emit()

    def _display(self, result):
        self.result = result
        self.inputs = result['inputs']
        self._describe_inputs()
        state = result['status']
        r = result['result']
        self.result_status_label.setText(f"{self.inputs['case']['project_geometry']['cycle']} · {self.inputs['case']['rpm']} rpm · {state}")
        last=r['cycles'][-1] if r['cycles'] else {}
        self.balances_text.setPlainText(json.dumps({key:last[key] for key in ('discrete','independent','balances_passed') if key in last},ensure_ascii=False,indent=2))
        self.state_label.setText(dict(converged='Convergencia numérica alcanzada', cancelled='Cancelado',
            not_converged='Sin convergencia / presupuesto agotado', error='Error de ejecución')[state])
        self.progress_label.setText(f'Ciclos completos: {len(r["cycles"])} · Integración: {r["seconds"]:.3f} s')
        self.memory_label.setText(f'Pico del cálculo: {r["peak_process_MiB"]:.1f} MiB · Pico de interfaz: {memory_mib():.1f} MiB')
        timing=result['manifest'].get('timings')
        if timing:
            self.memory_label.setText(self.memory_label.text()+f" · Preparación: {timing['setup_seconds']:.3f} s · Escritura: {timing['writing_seconds']:.3f} s · Total del punto: {timing['wall_seconds']:.3f} s"+
                (f" · Percibido: {timing['interface_wall_seconds']:.3f} s" if 'interface_wall_seconds' in timing else ''))
        self.path_label.setText(str(result['path']))
        self.angle_plot.set_rows([])
        self.pv_plot.set_rows([])
        if state == 'converged':
            cycle = r['cycles'][-1]
            derived=result_metrics(result)
            worst = max(v for b in cycle['independent'].values() for v in b['normalized_m_u_f'])
            self.summary_label.setText(
                f'Último ciclo completo: {cycle["cycle"]} · Trabajo indicado: {cycle["W_C_J"]:.6f} J/ciclo\n'+
                (f'Cárter (diagnóstico): {cycle["W_K_J"]:.6f} J/ciclo · ' if 'W_K_J' in cycle else 'Ciclo 720° · ')+
                f'Potencia indicada: {derived["indicated_power_W"]/1000:.6f} kW · Par indicado equivalente: {derived["indicated_torque_Nm"]:.6f} N·m\n'+
                f'Presión máxima: {cycle["p_max_Pa"]/1000:.3f} kPa abs.\n'+
                f'Balances aprobados · Mayor residuo independiente: {100*worst:.6f} % (límite 0,1 %)\n'
                f'Parada: {r["stop"]}. Esta ejecución individual no comprueba sensibilidad.\n'+NOTICE)
            layout=FOUR_LAYOUT if self.inputs['case']['project_geometry']['cycle']=='4T' else TWO_LAYOUT
            self.summary_label.setText(self.summary_label.text()+'\nFracciones frescas: '+', '.join(f'{name}={y:.8f}' for name,y in zip(layout.cv,cycle['Y'])))
            rows = result['samples']['cycles'][-1]
            self.angle_plot.set_rows(rows,layout)
            self.pv_plot.set_rows(rows,layout)
        else:
            self.summary_label.setText(f'Diagnóstico no aceptado. Motivo: {r["stop"]}.\n'
                                       'Los datos parciales se conservan en la carpeta; no se presentan como ciclo aceptado.')

    def open_result(self, checked=False, *, path=None):
        if self.active:
            return
        if path is None:
            name, _ = QFileDialog.getOpenFileName(self, 'Abrir resultado de simulación',
                str(new_output_path().parent), 'Manifiesto (manifest.json)')
            if not name:
                return
            path = Path(name)
        try:
            result = load_result(path)
        except ResultError as exc:
            self.error_label.setText(str(exc)+(' Se conserva el resultado previamente abierto.' if self.result else ''))
            return
        self.error_label.clear()
        self._display(result)
        if self.workspace_router:self.workspace_router('results')
