"""Sección de admisión; los widgets conservan el borrador sin normalizarlo."""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QFormLayout, QGridLayout,
                               QLabel, QLineEdit, QComboBox, QToolButton)
from .project import Intake, INTAKE_FIELDS, ProjectError, parse_number
from .intake import intake_results
from .geometry_view import GeometryPlot


class IntakeView(QWidget):
    changed = Signal()

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 16, 0, 0)
        title = QLabel('Admisión'); title.setObjectName('sectionTitle')
        layout.addWidget(title)
        self.grid = QGridLayout(); self.grid.setSpacing(22)
        self.editor = QWidget(); editor = QVBoxLayout(self.editor)
        editor.setContentsMargins(0, 0, 0, 0)
        form = QFormLayout(); form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
        self.mode_combo = QComboBox()
        self.mode_combo.addItem('Sin definir', None)
        self.mode_combo.addItem('Falda del pistón', 'piston_port')
        self.edits = {key: QLineEdit() for key in INTAKE_FIELDS}
        labels = ('Borde superior, &u [mm]', 'Altura, &h [mm]',
                  'Ancho desarrollado, &w [mm]', 'Borde inferior de falda, &f [mm]')
        for caption, widget in [('&Modalidad', self.mode_combo), *zip(labels, self.edits.values())]:
            label = QLabel(caption); label.setWordWrap(True); label.setBuddy(widget)
            widget.setMaximumWidth(260)
            form.addRow(label, widget)
        for edit in self.edits.values():
            edit.setPlaceholderText('Sin informar')
            edit.textChanged.connect(lambda _: self.changed.emit())
        self.mode_combo.currentIndexChanged.connect(lambda _: self.changed.emit())
        editor.addLayout(form)
        self.input_error = QLabel(); self.input_error.setWordWrap(True)
        self.input_error.setObjectName('fieldError'); editor.addWidget(self.input_error)
        references = ('Ventana rectangular y borde de falda recto, sin recortes. '
                      'u: hacia abajo desde el borde superior periférico del pistón en PMS. '
                      'f: distancia axial desde ese borde hasta el borde inferior de la falda, '
                      'en el lado de admisión; no es biela, cúpula ni distancia al bulón. '
                      'w: ancho desarrollado sobre la pared, no cuerda. '
                      'PMS: 0°/360°; PMI: 180°. Un cilindro y su cárter individual, sin multiplicar por N.')
        self.help_button = QToolButton(); self.help_button.setText('Referencias de medida')
        self.help_button.setCheckable(True); self.help_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.help_button.setArrowType(Qt.ArrowType.RightArrow)
        help_label = QLabel(references); help_label.setWordWrap(True); help_label.hide()
        def toggle(checked):
            help_label.setVisible(checked)
            self.help_button.setArrowType(Qt.ArrowType.DownArrow if checked else Qt.ArrowType.RightArrow)
        self.help_button.toggled.connect(toggle)
        editor.addWidget(self.help_button); editor.addWidget(help_label); editor.addStretch()
        for edit in self.edits.values(): edit.setToolTip(references)
        self.output = QWidget(); output = QVBoxLayout(self.output)
        output.setContentsMargins(0, 0, 0, 0)
        self.results = QLabel(); self.results.setWordWrap(True)
        self.results.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        output.addWidget(self.results)
        self.plot = GeometryPlot('Área geométrica de admisión', 'mm²'); output.addWidget(self.plot)
        layout.addLayout(self.grid)
        warning = QLabel('Área geométrica de admisión; no calcula caudal'); warning.setWordWrap(True)
        layout.addWidget(warning)
        self._wide = None
        self.arrange(True)

    def arrange(self, wide):
        if wide == self._wide: return
        self._wide = wide
        for widget in (self.editor, self.output): self.grid.removeWidget(widget)
        self.grid.addWidget(self.editor, 0, 0)
        self.grid.addWidget(self.output, 0 if wide else 1, 1 if wide else 0)
        self.grid.setColumnStretch(0, 1); self.grid.setColumnStretch(1, 1 if wide else 0)

    def load(self, intake):
        self.mode_combo.blockSignals(True)
        self.mode_combo.setCurrentIndex(self.mode_combo.findData(intake.mode))
        self.mode_combo.blockSignals(False)
        for key, edit in self.edits.items():
            edit.blockSignals(True)
            value = getattr(intake, key)
            edit.setText('' if value is None else str(value))
            edit.blockSignals(False)

    def snapshot(self):
        return Intake(mode=self.mode_combo.currentData(),
                      **{key: parse_number(edit.text(), key) for key, edit in self.edits.items()})

    def refresh(self, values, cycle, common_errors):
        numbers, errors = {}, {}
        for key, edit in self.edits.items():
            try: numbers[key] = parse_number(edit.text(), key)
            except ProjectError as exc: numbers[key] = None; errors[key] = str(exc)
        self.input_error.setText('\n'.join(errors.values()))
        self.plot.values = (); self.results.clear()
        if cycle != '2T':
            self.plot.error = 'Sección exclusiva de 2T.'
        else:
            intake = Intake(mode=self.mode_combo.currentData(), **numbers)
            result = intake_results(intake, values.get('stroke_mm'), values.get('rod_length_mm'),
                                    {**common_errors, **errors})
            def fmt(value):
                return '—' if value is None else f'{value:.2f}' if abs(value) < 1e6 else f'{value:.3e}'
            lines = ['No se abre'] if result.never_opens else []
            lines += [f'Apertura: {fmt(result.opening)}° · Cierre: {fmt(result.closing)}°',
                      f'Duración: {fmt(result.duration)}°',
                      f'Área máxima descubierta: {fmt(result.maximum)} mm²']
            if result.opening is not None:
                lines.append(f'[{fmt(result.opening)}°, 360°] ∪ [0°, {fmt(result.closing)}°] · atraviesa PMS')
            if result.event_error: lines.append(result.event_error)
            self.results.setText('\n'.join(lines))
            self.plot.values, self.plot.error = result.areas, result.area_error
        self.plot.update()
