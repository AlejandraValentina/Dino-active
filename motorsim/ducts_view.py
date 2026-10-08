"""Editor de recorridos y perfil longitudinal Qt; conserva borradores por sistema."""
from decimal import Decimal
from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (QComboBox, QFormLayout, QGridLayout, QHBoxLayout,
                               QLabel, QLineEdit, QListWidget, QPushButton,
                               QScrollArea, QVBoxLayout, QWidget)
from .project import DUCT_REFERENCE, FOUR_DUCT_REFERENCE, Ducts, DuctSegment, DUCT_FIELDS, ProjectError, parse_number
from .ducts import RouteGeometry, route_geometry, format_geometry


class DuctProfile(QWidget):
    def __init__(self):
        super().__init__()
        self.data = RouteGeometry()
        self.selected = -1
        self.setMinimumHeight(280)
        self.setAccessibleName('Perfil longitudinal interior de conductos, ejes en mm')

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(QColor('#b4d9f5'))
        p.drawText(QRectF(8, 5, self.width()-16, 30), 'Perfil longitudinal interior · x / radio [mm]')
        if not self.data.profile:
            p.drawText(QRectF(8, 50, self.width()-16, self.height()-60),
                       Qt.TextFlag.TextWordWrap, self.data.errors.get('profile', 'Sin tramos'))
            return
        total = self.data.profile[-1][1]
        radius = max(max(piece[2:]) for piece in self.data.profile)
        width, height = max(1, self.width()-80), max(1, self.height()-130)
        # Normalizar antes de convertir a float admite dimensiones finitas muy grandes.
        scale = min(Decimal(width)/total, Decimal(height)/(2*radius))
        points = [(float(x1*scale), float(x2*scale), float(r1*scale), float(r2*scale))
                  for x1,x2,r1,r2 in self.data.profile]
        if any(x2 <= x1 or r1 <= 0 or r2 <= 0 for x1,x2,r1,r2 in points):
            p.drawText(QRectF(8, 50, self.width()-16, self.height()-60), Qt.TextFlag.TextWordWrap,
                       'Perfil fuera del rango de representación; dimensiones conservadas.')
            return
        left, center = 42.0, 60 + height/2
        for i,(x1,x2,r1,r2) in enumerate(points):
            polygon = QPainterPath(QPointF(left+x1, center-r1))
            polygon.lineTo(left+x2, center-r2)
            polygon.lineTo(left+x2, center+r2)
            polygon.lineTo(left+x1, center+r1)
            polygon.closeSubpath()
            p.fillPath(polygon, QColor('#24415b' if i == self.selected else '#101b2e'))
            p.setPen(QPen(QColor('#8bcfff' if i == self.selected else '#7390ab'), 2 if i == self.selected else 1))
            p.drawPath(polygon)
        p.setPen(QPen(QColor('#40546e'), 1, Qt.PenStyle.DashLine))
        p.drawLine(QPointF(left,center),QPointF(left+float(total*scale),center))
        for i, continuous in enumerate(self.data.joints):
            x = left + points[i][1]
            extent = max(points[i][3],points[i+1][2])
            p.setPen(QPen(QColor('#7390ab' if continuous else '#ffafa6'), 1, Qt.PenStyle.DashLine))
            p.drawLine(QPointF(x,center-extent-8),QPointF(x,center+extent+8))
            if not continuous:
                p.drawText(QRectF(x-10,center-extent-30,20,22),Qt.AlignmentFlag.AlignCenter,'!')
        p.setPen(QColor('#9eb1c7'))
        p.drawText(QRectF(8,self.height()-52,self.width()-16,20),
                   f'Posición axial: 0 → {format_geometry(total)} mm')
        p.drawText(QRectF(8,30,self.width()-16,25), f'Radio máximo ±{format_geometry(radius)} mm')
        p.drawText(QRectF(8,self.height()-26,self.width()-16,22),
                   'Escala igual en ambos ejes · selección en azul')


class DuctsView(QScrollArea):
    changed = Signal()

    def __init__(self, supported_cycle="2T"):
        super().__init__()
        self.setWidgetResizable(True)
        self.setFrameShape(QScrollArea.Shape.NoFrame)
        self.drafts = {'intake': [], 'exhaust': []}
        self.selected_rows = {'intake': -1, 'exhaust': -1}
        self.route = 'intake'
        self.supported_cycle = supported_cycle
        self.cycle = supported_cycle
        body = QWidget(); layout = QVBoxLayout(body)
        layout.setContentsMargins(24,16,24,16)
        title = QLabel('Conductos'); title.setObjectName('pageTitle'); layout.addWidget(title)
        self.availability = QLabel(); self.availability.setWordWrap(True); layout.addWidget(self.availability)
        self.panel = QWidget(); panel = QVBoxLayout(self.panel); panel.setContentsMargins(0,0,0,0)
        route_row = QHBoxLayout()
        self.route_combo = QComboBox(); self.route_combo.addItem('Admisión','intake'); self.route_combo.addItem('Escape','exhaust')
        self.route_combo.setMaximumWidth(220)
        route_label = QLabel('&Recorrido'); route_label.setBuddy(self.route_combo)
        route_row.addWidget(route_label); route_row.addWidget(self.route_combo); route_row.addStretch()
        panel.addLayout(route_row)
        self.direction = QLabel(); self.direction.setWordWrap(True); panel.addWidget(self.direction)
        self.grid = QGridLayout(); self.grid.setSpacing(22)
        self.editor = QWidget(); editor = QVBoxLayout(self.editor); editor.setContentsMargins(0,0,0,0)
        self.list = QListWidget(); self.list.setAccessibleName('Tramos ordenados del recorrido seleccionado')
        self.list.setMinimumHeight(90); self.list.setMaximumHeight(140); editor.addWidget(self.list)
        buttons = QGridLayout()
        self.add_button = QPushButton('&Añadir tramo'); self.remove_button = QPushButton('&Eliminar')
        self.up_button = QPushButton('&Subir'); self.down_button = QPushButton('&Bajar')
        for i,button in enumerate((self.add_button,self.remove_button,self.up_button,self.down_button)):
            buttons.addWidget(button,i//2,i%2)
        editor.addLayout(buttons)
        self.form_widget = QWidget(); form = QFormLayout(self.form_widget); form.setContentsMargins(0,0,0,0)
        form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
        self.name_edit = QLineEdit(); self.name_edit.setMaxLength(2147483647)
        self.edits = {key:QLineEdit() for key in DUCT_FIELDS}
        labels = ('Longitud axial, &L [mm]','Diámetro interior inicial, D&1 [mm]','Diámetro interior final, D&2 [mm]')
        for caption,widget in [('&Nombre',self.name_edit),*zip(labels,self.edits.values())]:
            widget.setMaximumWidth(290)
            label=QLabel(caption);label.setWordWrap(True);label.setBuddy(widget)
            form.addRow(label,widget)
        self.form_widget.setToolTip('Diámetros interiores, no radios. Sección circular y diámetro lineal. '
            'El orden define el sentido de dibujo, no condiciones de flujo. No se calcula transición '
            'con lumbreras ni se añade volumen al cárter. Vacío significa sin informar.')
        for edit in self.edits.values():edit.setPlaceholderText('Sin informar')
        editor.addWidget(self.form_widget)
        self.input_error=QLabel();self.input_error.setWordWrap(True);self.input_error.setObjectName('fieldError')
        editor.addWidget(self.input_error);editor.addStretch()
        self.output=QWidget();output=QVBoxLayout(self.output);output.setContentsMargins(0,0,0,0)
        self.totals=QLabel();self.totals.setWordWrap(True);self.totals.setTextFormat(Qt.TextFormat.PlainText)
        output.addWidget(self.totals)
        self.joints=QLabel();self.joints.setWordWrap(True);output.addWidget(self.joints)
        self.profile=DuctProfile();output.addWidget(self.profile)
        self.piece_results=QLabel();self.piece_results.setWordWrap(True)
        self.piece_results.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        output.addWidget(self.piece_results)
        panel.addLayout(self.grid)
        notice=QLabel('Perfil idealizado, no CAD de fabricación. No calcula flujo ni sintonía.')
        notice.setWordWrap(True);panel.addWidget(notice)
        layout.addWidget(self.panel);layout.addStretch();self.setWidget(body)
        self._wide=None;self._arrange()
        self.route_combo.currentIndexChanged.connect(self._switch)
        self.list.currentRowChanged.connect(self._select)
        self.add_button.clicked.connect(self.add_segment);self.remove_button.clicked.connect(self.remove_segment)
        self.up_button.clicked.connect(lambda:self.move_segment(-1));self.down_button.clicked.connect(lambda:self.move_segment(1))
        for edit in (self.name_edit,*self.edits.values()):edit.textChanged.connect(self._edit)
        self._rebuild()

    def resizeEvent(self,event):
        super().resizeEvent(event)
        if hasattr(self,'grid'):self._arrange()

    def _arrange(self):
        wide=self.viewport().width()>=900
        if self._wide==wide:return
        self._wide=wide
        for widget in (self.editor,self.output):self.grid.removeWidget(widget)
        self.grid.addWidget(self.editor,0,0)
        self.grid.addWidget(self.output,0 if wide else 1,1 if wide else 0)
        self.grid.setColumnStretch(0,1);self.grid.setColumnStretch(1,1 if wide else 0)

    def load(self,ducts):
        self.drafts={route:[dict(name=s.name,**{key:'' if getattr(s,key) is None else str(getattr(s,key))
                                               for key in DUCT_FIELDS}) for s in getattr(ducts,route)]
                     for route in ('intake','exhaust')}
        self.selected_rows={route:0 if rows else -1 for route,rows in self.drafts.items()}
        self._rebuild()

    def _switch(self):
        self.route=self.route_combo.currentData()
        self._rebuild()

    @staticmethod
    def _title(index,draft):
        return f'{index+1}. '+(draft['name'] or 'Sin nombre')

    def _rebuild(self):
        self.list.blockSignals(True);self.list.clear()
        for i,draft in enumerate(self.drafts[self.route]):self.list.addItem(self._title(i,draft))
        self.list.setCurrentRow(self.selected_rows[self.route]);self.list.blockSignals(False)
        self._select(self.list.currentRow())

    def _select(self,index):
        self.selected_rows[self.route]=index
        draft=self.drafts[self.route][index] if index>=0 else dict(name='',**{key:'' for key in DUCT_FIELDS})
        for key,edit in [('name',self.name_edit),*self.edits.items()]:
            edit.blockSignals(True);edit.setText(draft[key]);edit.blockSignals(False)
        self.form_widget.setEnabled(index>=0)
        self.remove_button.setEnabled(index>=0);self.up_button.setEnabled(index>0)
        self.down_button.setEnabled(0<=index<len(self.drafts[self.route])-1)
        self.refresh()

    def _edit(self):
        index=self.list.currentRow()
        if index<0:return
        draft=dict(name=self.name_edit.text(),**{key:edit.text() for key,edit in self.edits.items()})
        self.drafts[self.route][index]=draft
        self.list.item(index).setText(self._title(index,draft))
        self.refresh();self.changed.emit()

    def add_segment(self):
        rows=self.drafts[self.route]
        rows.append(dict(name='',**{key:'' for key in DUCT_FIELDS}))
        self.selected_rows[self.route]=len(rows)-1
        self._rebuild();self.name_edit.setFocus();self.changed.emit()

    def remove_segment(self):
        index=self.list.currentRow()
        if index<0:return
        rows=self.drafts[self.route];del rows[index]
        self.selected_rows[self.route]=min(index,len(rows)-1)
        self._rebuild();self.changed.emit()

    def move_segment(self,delta):
        index=self.list.currentRow();rows=self.drafts[self.route];target=index+delta
        if index<0 or not 0<=target<len(rows):return
        rows[index],rows[target]=rows[target],rows[index]
        self.selected_rows[self.route]=target
        self._rebuild();self.changed.emit()

    def snapshot(self):
        values={}
        for route,rows in self.drafts.items():
            segments=[]
            for i,draft in enumerate(rows):
                try:
                    segments.append(DuctSegment(draft['name'],**{key:parse_number(draft[key],key) for key in DUCT_FIELDS}))
                except ProjectError as exc:
                    label='Admisión' if route=='intake' else 'Escape'
                    raise ProjectError(f'{label}, tramo {i+1}: {exc}') from exc
            values[route]=tuple(segments)
        return Ducts(**values, reference=FOUR_DUCT_REFERENCE if self.supported_cycle=="4T" else DUCT_REFERENCE)

    def set_cycle(self,cycle):
        self.cycle=cycle;self.panel.setVisible(cycle==self.supported_cycle)
        self.availability.setText(f'Un recorrido por sistema · Cilindro de referencia {self.supported_cycle}' if cycle==self.supported_cycle else
                                  'Conductos específicos 2T no disponibles en 4T. Datos conservados.')
        self.refresh()

    def refresh(self):
        self.direction.setText(('Entrada exterior → válvula de admisión' if self.supported_cycle=='4T' else 'Entrada exterior → ventana de admisión al cárter') if self.route=='intake' else
                               'Salida del cilindro → extremo exterior del escape')
        self.profile.data=RouteGeometry();self.piece_results.clear();self.totals.clear();self.joints.clear();self.input_error.clear()
        if self.cycle!=self.supported_cycle:
            self.profile.update();return
        pieces,errors=[],[]
        for draft in self.drafts[self.route]:
            values,row_errors={},{}
            for key in DUCT_FIELDS:
                try:values[key]=parse_number(draft[key],key)
                except ProjectError as exc:values[key]=None;row_errors[key]=str(exc)
            pieces.append(DuctSegment(draft['name'],**values));errors.append(row_errors)
        data=route_geometry(pieces,errors)
        self.profile.data=data;self.profile.selected=self.list.currentRow()
        self.profile.setAccessibleDescription(data.errors.get('profile','Perfil calculado a partir de los tramos actuales.'))
        if not pieces:self.totals.setText('Sin tramos')
        else:
            self.totals.setText(f'Longitud total: {format_geometry(data.length)} mm\n'
                               f'Suma de volúmenes: {format_geometry(data.volume)} cm³'+
                               ''.join('\n'+message for message in dict.fromkeys(data.errors[k] for k in ('length','volume') if k in data.errors)))
            bad=[f'{i+1}–{i+2}' for i,v in enumerate(data.joints) if v is False]
            unknown=[f'{i+1}–{i+2}' for i,v in enumerate(data.joints) if v is None]
            messages=[]
            if bad:messages.append('Unión discontinua '+', '.join(bad)+': fuera del modelo continuo.')
            if unknown:messages.append('Unión sin verificar '+', '.join(unknown)+': faltan diámetros válidos.')
            if not messages:messages.append('Uniones continuas.' if data.joints else 'Un tramo; sin uniones internas.')
            self.joints.setText('\n'.join(messages))
        index=self.list.currentRow()
        if index>=0:
            piece=data.segments[index]
            self.input_error.setText('\n'.join(errors[index].values()))
            self.piece_results.setText(f'Tramo {index+1} · {piece.kind}\n'
                f'Área inicial: {format_geometry(piece.start_area)} mm² · Área final: {format_geometry(piece.end_area)} mm²\n'
                f'Volumen interior: {format_geometry(piece.volume)} cm³'+
                ''.join('\n'+message for message in dict.fromkeys(piece.errors.values())))
        self.profile.update()
