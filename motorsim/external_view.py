"""Datos externos: declaración, vista previa y contraste de archivos guardados."""
from decimal import Decimal, localcontext

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QComboBox, QDialog, QFileDialog,
    QFormLayout, QGridLayout, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QMessageBox, QPlainTextEdit,
    QPushButton, QScrollArea, QTableWidget, QTableWidgetItem, QTabWidget, QVBoxLayout, QWidget)

from .external_data import (CANONICAL, DEFINITIONS, PROVENANCES, TITLES, SIM_KEYS, ExternalDataError,
    declarations, prepare_import, read_csv, save_import, load_import, contrast, export_contrast)
from .comparison import ComparisonError, geometry_fields
from .reference_results import ResultError
from .sweep import load_sweep
from .ui import Header, Panel, Columns


def label(text=''):
    widget=QLabel(text);widget.setWordWrap(True);widget.setTextFormat(Qt.TextFormat.PlainText)
    widget.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    return widget


def table(headers):
    widget=QTableWidget(0,len(headers));widget.setHorizontalHeaderLabels(headers)
    widget.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    widget.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    widget.verticalHeader().hide()
    widget.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
    widget.horizontalHeader().setStretchLastSection(True)
    widget.setObjectName('externalTable')
    return widget


def fill(widget,rows):
    widget.setRowCount(len(rows))
    for i,row in enumerate(rows):
        for j,value in enumerate(row):
            text='' if value is None else str(value)
            item=QTableWidgetItem(text);item.setToolTip(text);widget.setItem(i,j,item)


def describe_sources(external,sweep):
    meta=external['metadata']
    lines=['DATOS EXTERNOS',f"Identificador: {external['manifest']['dataset_id']}"]
    for key,title in (('name','Conjunto'),('provenance','Procedencia'),('source','Fuente'),
                      ('engine','Motor'),('configuration','Configuración'),('conditions','Condiciones del ensayo'),('notes','Observaciones')):
        lines.append(f'{title}: {meta[key]}')
    lines.extend([f"Magnitud: {TITLES[meta['magnitude']]}",
        f"Unidad original: {meta['original_unit']} · Canónica: {meta['canonical_unit']}",
        'Definición: '+meta['definition'],
        'Medición declarada registra una declaración; no acredita autenticidad ni trazabilidad metrológica.'])
    if sweep:
        index=sweep['index'];inputs=index['common_inputs'];case=inputs['case'];origin=inputs['origin']
        lines.extend(['','BARRIDO GUARDADO — no son condiciones declaradas del ensayo externo',
            f"Identificador: {index['series_id']}",f"Proyecto utilizado: {origin['project_name']}",
            f"Archivo al ejecutar: {origin['source_path'] or 'sin archivo asociado'}",
            'Copia con cambios sin guardar: '+('sí' if origin['dirty'] else 'no'),
            'RPM solicitadas: '+', '.join(str(p['rpm']) for p in index['points']),
            f"Modelo: {inputs['model_version']}",
            f"Perfil numérico {inputs['profile']['name']} · Regularización exterior {inputs['variant']['delta_p_Pa']} Pa",
            f"Gas R: {case['gas_r']} J/(kg K) · Gamma: {case['gamma']}",
            f"Aporte prescrito: inicio {case['heat_start_deg']}°, duración {case['heat_duration_deg']}°, {case['fresh_energy_j_kg']} J/kg fresco",
            'Coeficientes de descarga (orden de enlaces): '+', '.join(map(str,case['discharge_coefficients']))])
        for title,names,states in (('Inicial',case['cv_order'],case['initial_pty']),
                                   ('Contorno',('admisión','escape'),case['reservoirs_pty'])):
            lines.extend(f'{title} {name}: p={p} Pa absolutos, T={t} K, Y={y}' for name,(p,t,y) in zip(names,states))
        lines.extend(['','Geometría de la copia utilizada'])
        physical,_=geometry_fields(dict(inputs=inputs))
        for (section,title,unit),value in physical.items():lines.append(f'{section} · {title}: {value} {unit}'.rstrip())
    return '\n'.join(lines)


class ImportDialog(QDialog):
    def __init__(self,raw,parent=None):
        super().__init__(parent)
        self.raw=raw;self.prepared=None;self.imported=None
        self.setWindowTitle('Importar CSV · declaración y vista previa');self.resize(760,590)
        layout=QVBoxLayout(self);self.tabs=QTabWidget();layout.addWidget(self.tabs)
        scroll=QScrollArea();scroll.setWidgetResizable(True);self.tabs.addTab(scroll,'Declaración')
        body=QWidget();form=QFormLayout(body);scroll.setWidget(body)
        self.magnitude=QComboBox();self.magnitude.addItem('Elegí magnitud…',None)
        for key,title in TITLES.items():
            if key!='p_max_Pa':self.magnitude.addItem(title,key)
        self.unit=QComboBox();self.unit.addItem('Elegí unidad…',None)
        self.provenance=QComboBox();self.provenance.addItems(PROVENANCES)
        form.addRow('Magnitud',self.magnitude);form.addRow('Unidad original',self.unit)
        help_button=QPushButton('Definición y límites…');help_button.clicked.connect(self.help)
        self.confirm_definition=QCheckBox('Declaro que los datos cumplen esta definición completa')
        form.addRow(help_button);form.addRow(self.confirm_definition)
        form.addRow('Procedencia',self.provenance)
        form.addRow(label('Medición declarada registra tu declaración; no verifica autenticidad ni trazabilidad metrológica.'))
        self.texts={}
        for key,title in (('name','Nombre del conjunto'),('source','Fuente / referencia'),('engine','Motor'),
                          ('configuration','Configuración'),('conditions','Condiciones del ensayo'),('notes','Observaciones')):
            edit=QLineEdit();edit.setMaxLength(4096);edit.setPlaceholderText('No informado')
            form.addRow(title,edit);self.texts[key]=edit;edit.textChanged.connect(self.invalidate)
        self.preview_table=table(['RPM (ordenadas)','Valor original','Valor canónico'])
        preview=QWidget();box=QVBoxLayout(preview);self.preview_info=label();box.addWidget(self.preview_info)
        box.addWidget(self.preview_table);self.tabs.addTab(preview,'Vista previa')
        self.error=label();self.error.setObjectName('fieldError');layout.addWidget(self.error)
        buttons=QHBoxLayout();layout.addLayout(buttons)
        self.preview_button=QPushButton('Revisar vista previa');self.preview_button.clicked.connect(self.preview)
        self.confirm_button=QPushButton('Confirmar y guardar…');self.confirm_button.setEnabled(False)
        self.confirm_button.clicked.connect(self.confirm)
        cancel=QPushButton('Cancelar');cancel.clicked.connect(self.reject)
        for button in (self.preview_button,self.confirm_button,cancel):buttons.addWidget(button)
        self.magnitude.currentIndexChanged.connect(self.magnitude_changed)
        self.unit.currentIndexChanged.connect(self.invalidate);self.provenance.currentIndexChanged.connect(self.invalidate)
        self.confirm_definition.toggled.connect(self.invalidate)

    def invalidate(self,*args):
        self.prepared=None;self.confirm_button.setEnabled(False)
        self.preview_table.setRowCount(0);self.preview_info.clear()

    def magnitude_changed(self):
        self.unit.clear();self.unit.addItem('Elegí unidad…',None)
        key=self.magnitude.currentData()
        for unit in (('J/ciclo',) if SIM_KEYS.get(key)=='W_C_J' else ('Pa','bar') if SIM_KEYS.get(key)=='p_max_Pa' else ()):
            self.unit.addItem(unit,unit)
        self.confirm_definition.setChecked(False)
        self.confirm_definition.setToolTip(DEFINITIONS.get(key,''));self.invalidate()

    def help(self):
        text=DEFINITIONS.get(self.magnitude.currentData(),'Seleccioná una magnitud admitida.')
        QMessageBox.information(self,'Definición de los datos',text+'\n\nFuera de alcance: potencia/par al eje, trabajo parcial y presión manométrica. No se convierten a partir de RPM.')

    def preview(self):
        self.invalidate()
        try:
            key=self.magnitude.currentData()
            meta=declarations(key,self.unit.currentData(),DEFINITIONS.get(key) if self.confirm_definition.isChecked() else None,
                self.provenance.currentText(),**{k:edit.text() for k,edit in self.texts.items()})
            self.prepared=prepare_import(self.raw,meta)
        except ExternalDataError as exc:self.error.setText(str(exc));return
        fill(self.preview_table,[[r['rpm'],r['original'],r['value']] for r in self.prepared['rows']])
        self.preview_info.setText(f"{meta['name']} · {meta['provenance']} · {len(self.prepared['rows'])} puntos\n"
            f"{TITLES[key]}: {meta['original_unit']} → {meta['canonical_unit']}\n{meta['definition']}")
        self.error.clear();self.confirm_button.setEnabled(True);self.tabs.setCurrentIndex(1)

    def confirm(self,checked=False,*,folder=None):
        if self.prepared is None:return
        if folder is None:folder,_=QFileDialog.getSaveFileName(self,'Carpeta nueva para la importación','','Carpeta (*)')
        if not folder:return
        try:imported=save_import(folder,self.prepared)
        except ExternalDataError as exc:self.error.setText(str(exc));return
        self.imported=imported;self.accept()


class ExternalPlot(QWidget):
    def __init__(self):
        super().__init__();self.data=None;self.external=None;self.setMinimumHeight(260)

    def set_data(self,external,data):
        self.external,self.data=external,data;self.update()

    def paintEvent(self,event):
        p=QPainter(self);p.setRenderHint(QPainter.RenderHint.Antialiasing)
        if not self.external:return
        meta=self.external['metadata'];p.setPen(QColor('#d9e8f6'))
        p.drawText(QRectF(10,4,self.width()-20,30),f"{TITLES[meta['magnitude']]} [{meta['canonical_unit']}]")
        rows=self.data['rows'] if self.data else [dict(rpm=r['rpm'],external=r['value'],simulated=None,difference=None) for r in self.external['rows']]
        points=[(r['rpm'],r[k],k,r['difference'] is not None) for r in rows for k in ('external','simulated') if r[k] is not None]
        if not points:return
        with localcontext() as context:
            context.prec=800
            xs=[v[0] for v in points];ys=[v[1] for v in points]
            xlo,xhi=min(xs),max(xs);ylo,yhi=min(ys),max(ys)
            dx=(xhi-xlo)*Decimal('.05') or max(abs(xlo)*Decimal('.05'),Decimal(1))
            dy=(yhi-ylo)*Decimal('.1') or max(abs(ylo)*Decimal('.05'),Decimal(1))
            xlo-=dx;xhi+=dx;ylo-=dy;yhi+=dy
            box=QRectF(100,55,max(1,self.width()-135),max(1,self.height()-130))
            p.setPen(QColor('#8da9c2'));p.drawLine(box.topLeft(),box.bottomLeft());p.drawLine(box.bottomLeft(),box.bottomRight())
            for f in (Decimal(0),Decimal('.5'),Decimal(1)):
                y=box.bottom()-float(f)*box.height();x=box.left()+float(f)*box.width()
                p.drawText(QRectF(0,y-12,92,25),Qt.AlignmentFlag.AlignRight,f'{ylo+f*(yhi-ylo):.5g}')
                p.drawText(QRectF(x-45,box.bottom()+5,90,25),Qt.AlignmentFlag.AlignCenter,f'{xlo+f*(xhi-xlo):.6g}')
            for rpm,value,kind,matched in points:
                point=QPointF(box.left()+float((rpm-xlo)/(xhi-xlo))*box.width(),box.bottom()-float((value-ylo)/(yhi-ylo))*box.height())
                color=QColor('#69baf0' if kind=='simulated' else '#ffb36b')
                p.setPen(QPen(color,2));p.setBrush(color if kind=='simulated' or matched else Qt.BrushStyle.NoBrush)
                if kind=='simulated':p.drawRect(QRectF(point.x()-4,point.y()-4,8,8))
                else:p.drawEllipse(point,5,5)
        p.setPen(QColor('#c7dbea'))
        p.drawText(QRectF(10,self.height()-38,self.width()-20,34),Qt.TextFlag.TextWordWrap,
            'RPM · Azul □ simulado · Naranja ○ '+meta['provenance']+' · Círculo vacío: sin diferencia calculada')


class ExternalDialog(QDialog):
    def reject(self):
        if not self.embedded:super().reject()

    def __init__(self,parent=None,*,embedded=False):
        super().__init__(parent);self.embedded=embedded
        if embedded:self.setWindowFlags(Qt.WindowType.Widget)
        self.external=None;self.sweep=None;self.data=None
        self.setWindowTitle('Datos externos · contraste descriptivo');self.resize(1060,630)
        layout=QVBoxLayout(self);layout.setContentsMargins(20,18,20,18);layout.setSpacing(16)
        self.header=Header('Datos externos','Importá un CSV y contrastalo con un barrido simulado.','Contraste descriptivo · No es validación experimental.')
        layout.addWidget(self.header)
        imported=Panel('01 · IMPORTACIÓN');series=Panel('02 · BARRIDO SIMULADO')
        self.import_button=QPushButton('Importar CSV…');self.open_button=QPushButton('Abrir importación…')
        self.import_button.setObjectName('primaryAction')
        self.sweep_button=QPushButton('Seleccionar barrido…');self.export_button=QPushButton('Exportar contraste…')
        imported.content.addWidget(self.import_button);imported.content.addWidget(self.open_button)
        series.content.addWidget(self.sweep_button)
        self.import_button.clicked.connect(self.import_csv);self.open_button.clicked.connect(self.open_import)
        self.sweep_button.clicked.connect(self.open_sweep);self.export_button.clicked.connect(self.export)
        self.identity=label('Sin datos importados. Empezá con un CSV o una importación confirmada.');imported.content.addWidget(self.identity)
        self.sweep_info=label('Sin barrido seleccionado. Primero cargá los datos externos.');series.content.addWidget(self.sweep_info)
        layout.addWidget(Columns(imported,series,800))
        self.contrast_panel=Panel('03 · CONTRASTE');layout.addWidget(self.contrast_panel)
        self.status=label('No hay contraste disponible. Importá los datos y seleccioná un barrido guardado.');self.contrast_panel.content.addWidget(self.status)
        self.tabs=QTabWidget();self.tabs.setMinimumHeight(310);self.contrast_panel.content.addWidget(self.tabs)
        self.table=table(['RPM','Externo','Simulado','Simulado − externo','Relativa %','Estado'])
        self.tabs.addTab(self.table,'Tabla');self.plot=ExternalPlot();self.tabs.addTab(self.plot,'Puntos / RPM')
        self.details=QPlainTextEdit();self.details.setReadOnly(True);self.tabs.addTab(self.details,'Procedencia y condiciones')
        exported=Panel('04 · EXPORTACIÓN');layout.addWidget(exported)
        exported.content.addWidget(self.export_button,alignment=Qt.AlignmentFlag.AlignLeft)
        exported.content.addWidget(label('Disponible cuando el contraste sea compatible. Se crea una carpeta nueva con los datos del contraste.'))
        self.error=label();self.error.setObjectName('fieldError');exported.content.addWidget(self.error)
        methodology=Panel('ALCANCE DEL CONTRASTE');layout.addWidget(methodology)
        methodology.content.addWidget(label('Sin interpolación ni cálculos nuevos. Coincidir en RPM y unidades no acredita mismo motor ni condiciones. Equivalencia no acreditada; no es calibración ni validación experimental.'))
        self.refresh()

    def import_csv(self,checked=False,*,path=None):
        if path is None:path,_=QFileDialog.getOpenFileName(self,'Seleccionar CSV externo','','CSV (*.csv)')
        if not path:return
        try:raw=read_csv(path)
        except ExternalDataError as exc:self.error.setText(str(exc));return
        dialog=ImportDialog(raw,self)
        if self.embedded:
            self.import_button.setEnabled(False);self.open_button.setEnabled(False);self.sweep_button.setEnabled(False);self.export_button.setEnabled(False)
            self.import_dialog=dialog;dialog.setWindowFlags(Qt.WindowType.Widget)
            for i in range(self.layout().count()):
                widget=self.layout().itemAt(i).widget()
                if widget and widget is not self.header:widget.hide()
            self.layout().addWidget(dialog);dialog.show()
            dialog.finished.connect(lambda code:self._import_finished(dialog))
            return
        if dialog.exec()==QDialog.DialogCode.Accepted and dialog.imported:
            self.external=dialog.imported;self.error.clear();self.refresh()

    def _import_finished(self,dialog):
        self.import_button.setEnabled(True);self.open_button.setEnabled(True)
        if dialog.imported:self.external=dialog.imported;self.error.clear()
        dialog.hide();self.layout().removeWidget(dialog);dialog.deleteLater()
        for i in range(self.layout().count()):
            widget=self.layout().itemAt(i).widget()
            if widget:widget.show()
        self.refresh()

    def open_import(self,checked=False,*,path=None):
        if path is None:path,_=QFileDialog.getOpenFileName(self,'Abrir importación','','Metadatos (metadata.json)')
        if not path:return
        try:loaded=load_import(path)
        except ExternalDataError as exc:self.error.setText(str(exc)+' Se conserva la selección anterior.');return
        self.external=loaded;self.error.clear();self.refresh()

    def open_sweep(self,checked=False,*,path=None):
        if path is None:path,_=QFileDialog.getOpenFileName(self,'Seleccionar barrido guardado','','Índice (series.json)')
        if not path:return
        try:loaded=load_sweep(path)
        except ResultError as exc:self.error.setText(str(exc)+' Se conserva el barrido anterior.');return
        self.sweep=loaded;self.error.clear();self.refresh()

    def refresh(self):
        self.data=None;self.export_button.setEnabled(False)
        self.sweep_button.setEnabled(self.external is not None)
        self.tabs.setVisible(self.external is not None)
        if self.sweep:
            index=self.sweep['index']
            self.sweep_info.setText(str(self.sweep.get('path','Ruta no informada'))+'\nRPM disponibles: '+', '.join(str(p['rpm']) for p in index['points']))
        else:self.sweep_info.setText('Sin barrido seleccionado. '+('Seleccioná una serie guardada para contrastar RPM coincidentes.' if self.external else 'Primero cargá los datos externos.'))
        if not self.external:return
        meta=self.external['metadata'];self.plot.set_data(self.external,None)
        self.identity.setText(f"{meta['name']} · {meta['provenance']}\n{TITLES[meta['magnitude']]} · {meta['canonical_unit']} · {len(self.external['rows'])} puntos externos")
        self.status.setText('Datos externos cargados. Seleccioná un barrido guardado para consultar coincidencias.')
        fill(self.table,[[r['rpm'],r['value'],None,None,None,'solo externo'] for r in self.external['rows']])
        if self.sweep:
            try:self.data=contrast(self.external,self.sweep)
            except ExternalDataError as exc:
                self.status.setText(str(exc));self.details.setPlainText(describe_sources(self.external,self.sweep));return
            index=self.sweep['index']
            self.status.setText(f"Barrido {index['series_id']} · {index['common_inputs']['origin']['project_name']}\n"
                f"{self.data['simulated_count']} puntos solicitados en el barrido · {self.data['matches']} coincidencias convergidas")
            fill(self.table,[[r['rpm'],r['external'],r['simulated'],r['difference'],
                format(r['relative_percent'],'.8g') if r['relative_percent'] is not None else None,r['state']] for r in self.data['rows']])
            for i,row in enumerate(self.data['rows']):self.table.item(i,5).setToolTip(row['reason'])
            self.plot.set_data(self.external,self.data);self.export_button.setEnabled(True)
        self.details.setPlainText(describe_sources(self.external,self.sweep))

    def export(self,checked=False,*,folder=None):
        if self.data is None:return
        if folder is None:folder,_=QFileDialog.getSaveFileName(self,'Carpeta nueva para contraste.csv','','Carpeta (*)')
        if not folder:return
        try:export_contrast(folder,self.data);self.error.setText('Contraste guardado en '+str(folder))
        except ComparisonError as exc:self.error.setText(str(exc))
