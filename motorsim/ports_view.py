"""Editor específico 2T: borradores conservados incluso con texto inválido."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QComboBox, QFormLayout, QGridLayout, QHBoxLayout,
                               QLabel, QLineEdit, QListWidget, QPushButton,
                               QScrollArea, QVBoxLayout, QWidget)
from .project import Port, PORT_FIELDS, ProjectError, parse_number
from .ports import port_results
from .geometry_view import GeometryPlot
from .intake_view import IntakeView


class PortsView(QScrollArea):
    changed = Signal()

    def __init__(self):
        super().__init__()
        self.setWidgetResizable(True)
        self.setFrameShape(QScrollArea.Shape.NoFrame)
        self.drafts = []
        self.values, self.errors = {}, {}
        self.cycle = "2T"
        body = QWidget()
        layout = QVBoxLayout(body)
        layout.setContentsMargins(24, 16, 24, 16)
        title = QLabel("Configuración 2T"); title.setObjectName("pageTitle")
        layout.addWidget(title)
        self.availability = QLabel("Un cilindro de referencia · Aproximación rectangular")
        self.availability.setWordWrap(True)
        layout.addWidget(self.availability)
        self.panel = QWidget()
        panel = QVBoxLayout(self.panel); panel.setContentsMargins(0, 0, 0, 0)
        note = QLabel("Aproximación rectangular · Un cilindro de referencia. Distancia hacia abajo desde el borde superior periférico del pistón en PMS; no desde la cara del cilindro ni una cúpula. Ancho desarrollado sobre la pared, no cuerda.")
        note.setWordWrap(True); self.availability.setToolTip(note.text())
        self.crankcase_edit = QLineEdit(); self.crankcase_edit.setMaximumWidth(220)
        self.crankcase_edit.setPlaceholderText("Sin informar")
        self.crankcase_error = QLabel(); self.crankcase_error.setObjectName("fieldError");self.crankcase_error.setWordWrap(True)
        self.crank_widget = QWidget()
        crank = QFormLayout(self.crank_widget)
        caption = QLabel("Volumen libre del &cárter con el pistón en PMI [cm³]")
        caption.setWordWrap(True); caption.setBuddy(self.crankcase_edit)
        crank.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
        crank.addRow(caption, self.crankcase_edit)
        panel.addWidget(self.crank_widget)
        hint = QLabel("Cárter individual, sin conductos externos. Procedencia o medición: usar Observaciones en Ficha.")
        self.crankcase_edit.setToolTip(hint.text()); panel.addWidget(self.crankcase_error)
        self.grid = QGridLayout(); self.grid.setSpacing(22)
        self.editor = QWidget(); edit_layout = QVBoxLayout(self.editor); edit_layout.setContentsMargins(0, 0, 0, 0)
        self.list = QListWidget(); self.list.setAccessibleName("Lumbreras del cilindro de referencia")
        self.list.setMinimumHeight(70); self.list.setMaximumHeight(95)
        edit_layout.addWidget(self.list)
        buttons = QHBoxLayout()
        self.add_button = QPushButton("&Añadir lumbrera")
        self.remove_button = QPushButton("&Eliminar seleccionada")
        buttons.addWidget(self.add_button); buttons.addWidget(self.remove_button); buttons.addStretch()
        edit_layout.addLayout(buttons)
        self.form_widget = QWidget(); form = QFormLayout(self.form_widget); form.setContentsMargins(0,0,0,0)
        form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
        self.name_edit = QLineEdit(); self.name_edit.setMaxLength(2147483647)
        self.function_combo = QComboBox()
        for label, value in (("Sin elegir",None),("Escape","escape"),("Transferencia","transfer")):
            self.function_combo.addItem(label,value)
        self.edits = {key: QLineEdit() for key in PORT_FIELDS}
        for title, widget in (("&Nombre",self.name_edit),("&Función",self.function_combo),
                              ("Distancia al borde &superior [mm]",self.edits['top_mm']),
                              ("&Altura de ventana [mm]",self.edits['height_mm']),
                              ("Ancho &desarrollado [mm]",self.edits['width_mm'])):
            widget.setMaximumWidth(300)
            label=QLabel(title); label.setWordWrap(True); label.setBuddy(widget)
            form.addRow(label,widget)
        edit_layout.addWidget(self.form_widget)
        self.input_error = QLabel(); self.input_error.setObjectName('fieldError');self.input_error.setWordWrap(True)
        edit_layout.addWidget(self.input_error); edit_layout.addStretch()
        self.output = QWidget(); output = QVBoxLayout(self.output); output.setContentsMargins(0,0,0,0)
        self.results = QLabel(); self.results.setWordWrap(True)
        self.results.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        output.addWidget(self.results)
        self.plot = GeometryPlot("Área geométrica descubierta", "mm²")
        output.addWidget(self.plot)
        area_note = QLabel("Área sobre la pared: no es área efectiva de flujo, caudal, eficiencia de barrido ni potencia.")
        area_note.setWordWrap(True); output.addWidget(area_note)
        panel.addLayout(self.grid)
        self.intake = IntakeView(); panel.addWidget(self.intake)
        self.intake.changed.connect(self.changed.emit)
        layout.addWidget(self.panel);layout.addStretch();self.setWidget(body)
        self._wide=None; self._arrange()
        self.add_button.clicked.connect(self.add_port)
        self.remove_button.clicked.connect(self.remove_port)
        self.list.currentRowChanged.connect(self._select)
        for widget in (self.name_edit,*self.edits.values()): widget.textChanged.connect(self._edit)
        self.function_combo.currentIndexChanged.connect(self._edit)
        self.crankcase_edit.textChanged.connect(lambda _: self.changed.emit())
        self._select(-1)

    def resizeEvent(self,event):
        super().resizeEvent(event)
        if hasattr(self,'grid'): self._arrange()

    def _arrange(self):
        wide=self.viewport().width()>=900
        if wide==self._wide:return
        self._wide=wide
        self.intake.arrange(wide)
        for widget in (self.editor,self.output): self.grid.removeWidget(widget)
        self.grid.addWidget(self.editor,0,0)
        self.grid.addWidget(self.output,0 if wide else 1,1 if wide else 0)
        self.grid.setColumnStretch(0,1);self.grid.setColumnStretch(1,1 if wide else 0)

    def load(self, project):
        self.intake.load(project.intake)
        self.drafts=[dict(name=p.name,function=p.function,
                          **{key:'' if getattr(p,key) is None else str(getattr(p,key)) for key in PORT_FIELDS})
                     for p in project.ports]
        self.list.blockSignals(True);self.list.clear()
        for draft in self.drafts:self.list.addItem(self._title(draft))
        self.list.blockSignals(False)
        self.crankcase_edit.blockSignals(True)
        v=project.crankcase_volume_bdc_cm3
        self.crankcase_edit.setText('' if v is None else str(v))
        self.crankcase_edit.blockSignals(False)
        if self.drafts:self.list.setCurrentRow(0)
        self._select(self.list.currentRow())

    @staticmethod
    def _title(draft):
        kind={None:'Sin función','escape':'Escape','transfer':'Transferencia'}[draft['function']]
        return (draft['name'] or 'Sin nombre')+' · '+kind

    def add_port(self):
        self.drafts.append(dict(name='',function=None,**{key:'' for key in PORT_FIELDS}))
        self.list.addItem(self._title(self.drafts[-1]));self.list.setCurrentRow(len(self.drafts)-1)
        self.name_edit.setFocus();self.changed.emit()

    def remove_port(self):
        index=self.list.currentRow()
        if index<0:return
        del self.drafts[index]
        self.list.blockSignals(True);self.list.takeItem(index);self.list.blockSignals(False)
        self.list.setCurrentRow(min(index,len(self.drafts)-1))
        self._select(self.list.currentRow());self.changed.emit()

    def _select(self,index):
        draft=self.drafts[index] if 0<=index<len(self.drafts) else dict(name='',function=None,**{key:'' for key in PORT_FIELDS})
        widgets=[self.name_edit,self.function_combo,*self.edits.values()]
        for w in widgets:w.blockSignals(True)
        self.name_edit.setText(draft['name'])
        self.function_combo.setCurrentIndex(self.function_combo.findData(draft['function']))
        for key,w in self.edits.items():w.setText(draft[key])
        for w in widgets:w.blockSignals(False)
        self.form_widget.setEnabled(index>=0);self.remove_button.setEnabled(index>=0)
        self.refresh()

    def _edit(self):
        index=self.list.currentRow()
        if index<0:return
        draft=dict(name=self.name_edit.text(),function=self.function_combo.currentData(),
                   **{key:w.text() for key,w in self.edits.items()})
        self.drafts[index]=draft;self.list.item(index).setText(self._title(draft))
        self.changed.emit()

    def snapshot(self):
        ports=[]
        for i,draft in enumerate(self.drafts):
            try:
                ports.append(Port(draft['name'],draft['function'],
                                  **{key:parse_number(draft[key],key) for key in PORT_FIELDS}))
            except ProjectError as exc:
                raise ProjectError(f"Lumbrera {i+1}: {exc}") from exc
        return tuple(ports),parse_number(self.crankcase_edit.text(),'crankcase_volume_bdc_cm3'),self.intake.snapshot()

    def set_common(self,values,cycle,errors):
        self.values,self.cycle,self.errors=values,cycle,errors
        self.panel.setVisible(cycle=='2T')
        self.availability.setText('Un cilindro de referencia · Aproximación rectangular' if cycle=='2T' else
                                  'Configuración 2T no disponible en proyectos 4T. Datos conservados.')
        self.refresh()

    def refresh(self):
        self.intake.refresh(self.values,self.cycle,self.errors)
        self.plot.values=();self.plot.error='Seleccioná o añadí una lumbrera.'
        self.results.setText('Sin lumbrera seleccionada.');self.input_error.clear()
        try:
            parse_number(self.crankcase_edit.text(),'crankcase_volume_bdc_cm3');message=''
        except ProjectError as exc:message=str(exc)
        self.crankcase_error.setText(message);self.crankcase_error.setVisible(bool(message))
        if self.cycle!='2T':
            self.results.clear();self.plot.error='Sección exclusiva de 2T.';self.plot.update();return
        index=self.list.currentRow()
        if index>=0:
            draft=self.drafts[index];numbers={};errors=dict(self.errors)
            for key in PORT_FIELDS:
                try:numbers[key]=parse_number(draft[key],key)
                except ProjectError as exc:numbers[key]=None;errors[key]=str(exc)
            self.input_error.setText('\n'.join(errors[key] for key in PORT_FIELDS if key in errors))
            port=Port(draft['name'],draft['function'],**numbers)
            result=port_results(port,self.values.get('stroke_mm'),self.values.get('rod_length_mm'),errors)
            def fmt(value):return '—' if value is None else f'{value:.2f}' if abs(value)<1e6 else f'{value:.3e}'
            self.results.setText(('No se abre\n' if result.never_opens else '')+
                                 f'Apertura: {fmt(result.opening)}° · Cierre: {fmt(result.closing)}°\n'
                                 f'Duración: {fmt(result.duration)}°\nÁrea máxima descubierta: {fmt(result.maximum)} mm²'+
                                 ('\n'+result.event_error if result.event_error else ''))
            self.plot.values=result.areas;self.plot.error=result.area_error
        self.plot.update()
