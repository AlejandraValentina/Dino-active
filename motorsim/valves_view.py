"""Editor compacto de distribución fija; las curvas no se persisten."""
from PySide6.QtCore import Signal
from PySide6.QtWidgets import (QScrollArea, QWidget, QVBoxLayout, QGridLayout,
                              QGroupBox, QFormLayout, QLineEdit, QLabel, QTabWidget)
from .project import Valve, VALVE_FIELDS, parse_number, ProjectError
from .valves import errors, lift, area, overlap
from .geometry_view import GeometryPlot


class ValvesView(QScrollArea):
    changed = Signal()

    def __init__(self):
        super().__init__()
        self.setWidgetResizable(True)
        body = QWidget(); layout = QVBoxLayout(body)
        layout.setContentsMargins(24, 16, 24, 16)
        title = QLabel('Configuración 4T'); title.setObjectName('pageTitle')
        layout.addWidget(title)
        note = QLabel('Un cilindro · distribución fija · alzada idealizada seno cuadrado.\n'
                      '0° PMS intercambio · 180° PMI · 360° PMS compresión · 540° PMI · 720° PMS intercambio.\n'
                      'Área: cortina cilíndrica limitada por garganta anular; no medida ni CAD.')
        note.setWordWrap(True); layout.addWidget(note)
        gate = QLabel('Modelo 0D disponible en Simulación: alzada idealizada, energía prescrita, sin ondas ni validación experimental.')
        gate.setWordWrap(True); layout.addWidget(gate)
        self.grid = QGridLayout(); layout.addLayout(self.grid)
        self.groups = []; self.edits = {}; self.outputs = {}; self.plots = {}
        for route, caption in (('intake', 'Admisión'), ('exhaust', 'Escape')):
            group = QGroupBox(caption); column = QVBoxLayout(group); form = QFormLayout()
            form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
            self.edits[route] = {}
            for key, label in VALVE_FIELDS.items():
                edit = QLineEdit(); edit.setPlaceholderText('Sin informar'); edit.setMaximumWidth(190)
                unit = '°' if key.endswith('_deg') else 'mm'
                form.addRow(label+' ['+unit+']', edit); self.edits[route][key] = edit
                edit.textChanged.connect(self._edited)
            column.addLayout(form)
            output = QLabel(); output.setWordWrap(True); column.addWidget(output)
            self.outputs[route] = output
            tabs = QTabWidget(); self.plots[route] = []
            for caption, unit in (('Alzada', 'mm'), ('Área geométrica', 'mm²')):
                plot = GeometryPlot(caption, unit); plot.end_angle = 720
                tabs.addTab(plot, caption); self.plots[route].append(plot)
            column.addWidget(tabs); self.groups.append(group)
        self.crossing = QLabel(); self.crossing.setWordWrap(True); layout.addWidget(self.crossing)
        layout.addStretch(); self.setWidget(body); self.refresh(); self._arrange()

    def _arrange(self):
        wide = self.viewport().width() >= 850
        for group in self.groups: self.grid.removeWidget(group)
        for i, group in enumerate(self.groups): self.grid.addWidget(group, 0 if wide else i, i if wide else 0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'groups'): self._arrange()

    def load(self, config):
        for route, fields in self.edits.items():
            for key, edit in fields.items():
                value = getattr(getattr(config, route), key)
                edit.blockSignals(True); edit.setText('' if value is None else str(value)); edit.blockSignals(False)
        self.refresh()

    def snapshot(self):
        return {route: Valve(**{key: parse_number(edit.text(), key) for key, edit in fields.items()})
                for route, fields in self.edits.items()}

    def _edited(self):
        self.refresh(); self.changed.emit()

    def refresh(self):
        valid = {}
        for route, fields in self.edits.items():
            values = {}; messages = []
            for key, edit in fields.items():
                try:
                    values[key] = parse_number(edit.text(), key); message = ''
                except ProjectError as exc:
                    values[key] = None; message = str(exc); messages.append(message)
                edit.setProperty('invalid', bool(message)); edit.setAccessibleDescription(message)
                edit.style().unpolish(edit); edit.style().polish(edit)
            valve = Valve(**values); messages += errors(valve)
            for plot in self.plots[route]: plot.values = (); plot.error = '\n'.join(dict.fromkeys(messages))
            if messages:
                self.outputs[route].setText('\n'.join(dict.fromkeys(messages)))
            else:
                valid[route] = valve
                close = valve.opening_deg+valve.duration_deg; peak = valve.opening_deg+valve.duration_deg/2
                self.outputs[route].setText(f'Apertura {valve.opening_deg:g}° · duración {valve.duration_deg:g}°\n'
                    f'Cierre {close:g}° (fase {close%720:g}°) · máximo {peak:g}° (fase {peak%720:g}°)')
                self.plots[route][0].values = tuple(lift(valve, a) for a in range(721))
                self.plots[route][1].values = tuple(area(valve, a) for a in range(721))
            for plot in self.plots[route]: plot.update()
        if len(valid) == 2:
            spans = overlap(valid['intake'], valid['exhaust'])
            self.crossing.setText('Cruce: '+(', '.join(f'{a:g}–{b:g}°' for a,b in spans) or 'sin cruce')+
                                  f' · total {sum(b-a for a,b in spans):g}°')
        else: self.crossing.setText('Cruce: — · requiere ambas válvulas válidas.')
