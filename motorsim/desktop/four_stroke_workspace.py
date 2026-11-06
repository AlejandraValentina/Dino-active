"""Workspace 4T 0D de referencia: geometría, válvulas y conductos."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
                               QPushButton, QFormLayout, QGroupBox, QTabWidget,
                               QTableWidget, QTableWidgetItem, QHeaderView)

from ..four_stroke_project import FourStrokeProject, FourStrokeProjectError
from ..project import (DUCT_FIELDS, FOUR_DUCT_REFERENCE, DuctSegment, Ducts,
                       VALVE_FIELDS, Valve, ProjectError, parse_number)

REFERENCE_BANNER = "4T 0D REFERENCIA · SYNTHETIC_REFERENCE_0D · NOT_VALIDATED"


def _line(value) -> QLineEdit:
    field = QLineEdit("" if value is None else f"{value:g}" if isinstance(value, (int, float)) else str(value))
    field.setMinimumWidth(120)
    return field


def _value(field: QLineEdit, key: str):
    return parse_number(field.text(), key)


class FourStrokeGeometryPage(QWidget):
    def __init__(self, context, parent=None):
        super().__init__(parent)
        self.context = context
        layout = QVBoxLayout(self)
        box = QGroupBox("Geometría del motor 4T")
        form = QFormLayout(box)
        self.name = QLineEdit()
        self.name.setObjectName("fsName")
        form.addRow("Nombre", self.name)
        self.cylinder = QLabel("1 cilindro (modelo 4T 0D)")
        form.addRow("Cilindros", self.cylinder)
        self.bore = _line(None)
        self.stroke = _line(None)
        self.rod = _line(None)
        self.compression = _line(None)
        self.notes = QLineEdit()
        for widget in (self.bore, self.stroke, self.rod, self.compression):
            widget.setObjectName("fsGeometry")
        for label, widget in (("Diámetro [mm]", self.bore), ("Carrera [mm]", self.stroke),
                              ("Biela [mm]", self.rod), ("Compresión : 1", self.compression)):
            form.addRow(label, widget)
        form.addRow("Notas", self.notes)
        self.rpm = QLineEdit("3000")
        self.rpm.setObjectName("fsRpm")
        form.addRow("RPM de ejecución (2500–3500)", self.rpm)
        layout.addWidget(box)
        self.error = QLabel()
        self.error.setWordWrap(True)
        self.error.setObjectName("fsGeometryError")
        layout.addWidget(self.error)
        self.apply_button = QPushButton("Aplicar geometría")
        self.apply_button.clicked.connect(self.apply)
        layout.addWidget(self.apply_button)
        layout.addStretch(1)
        self.load(context.project)

    def load(self, project: FourStrokeProject):
        self.name.setText(project.name)
        for widget, value in ((self.bore, project.bore_mm), (self.stroke, project.stroke_mm),
                              (self.rod, project.rod_length_mm),
                              (self.compression, project.compression_ratio)):
            widget.setText("" if value is None else f"{value:g}")
        self.notes.setText(project.notes)
        self.rpm.setText("" if project.rpm is None else str(project.rpm))
        self.error.clear()

    def apply(self) -> bool:
        try:
            name = self.name.text().strip()
            if not name:
                raise FourStrokeProjectError("El nombre no puede estar vacío.")
            values = {
                "bore_mm": _value(self.bore, "bore_mm"),
                "stroke_mm": _value(self.stroke, "stroke_mm"),
                "rod_length_mm": _value(self.rod, "rod_length_mm"),
                "compression_ratio": _value(self.compression, "compression_ratio"),
            }
            rpm_text = self.rpm.text().strip()
            if not rpm_text:
                rpm = None
            else:
                try:
                    rpm = int(rpm_text)
                except ValueError as exc:
                    raise FourStrokeProjectError("RPM debe ser un entero entre 2500 y 3500.") from exc
            self.context.update(name=name, notes=self.notes.text(), rpm=rpm, **values)
        except (ProjectError, FourStrokeProjectError, ValueError) as exc:
            self.error.setText(str(exc))
            return False
        self.error.clear()
        return True


class FourStrokeValvesPage(QWidget):
    def __init__(self, context, parent=None):
        super().__init__(parent)
        self.context = context
        layout = QVBoxLayout(self)
        self.fields = {}
        for side, title in (("intake", "Admisión"), ("exhaust", "Escape")):
            box = QGroupBox(f"Válvula de {title}")
            form = QFormLayout(box)
            self.fields[side] = {}
            for key in VALVE_FIELDS:
                widget = _line(None)
                widget.setObjectName(f"fsValve_{side}_{key}")
                self.fields[side][key] = widget
                form.addRow(f"{key} [mm/°]", widget)
            layout.addWidget(box)
        self.error = QLabel()
        self.error.setWordWrap(True)
        self.error.setObjectName("fsValvesError")
        layout.addWidget(self.error)
        self.apply_button = QPushButton("Aplicar válvulas")
        self.apply_button.clicked.connect(self.apply)
        layout.addWidget(self.apply_button)
        layout.addStretch(1)
        self.load(context.project)

    def load(self, project: FourStrokeProject):
        for side, valve in (("intake", project.intake), ("exhaust", project.exhaust)):
            for key in VALVE_FIELDS:
                value = getattr(valve, key)
                self.fields[side][key].setText("" if value is None else f"{value:g}")
        self.error.clear()

    def _valve(self, side):
        values = {key: _value(self.fields[side][key], key) for key in VALVE_FIELDS}
        return Valve(**values)

    def apply(self) -> bool:
        try:
            intake, exhaust = self._valve("intake"), self._valve("exhaust")
            self.context.update(intake=intake, exhaust=exhaust)
        except (ProjectError, FourStrokeProjectError) as exc:
            self.error.setText(str(exc))
            return False
        self.error.clear()
        return True


class _DuctTable(QWidget):
    def __init__(self, title, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(QLabel(title))
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Nombre", "Longitud [mm]", "Ø inicial [mm]", "Ø final [mm]"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table)
        row = QHBoxLayout()
        self.add_button = QPushButton("Agregar tramo")
        self.remove_button = QPushButton("Quitar tramo")
        row.addWidget(self.add_button)
        row.addWidget(self.remove_button)
        row.addStretch(1)
        layout.addLayout(row)
        self.add_button.clicked.connect(self.add_row)
        self.remove_button.clicked.connect(self.remove_row)

    def add_row(self, name="", length=None, start=None, end=None):
        row = self.table.rowCount()
        self.table.insertRow(row)
        def text(value):
            if value is None:
                return ""
            return f"{value:g}" if isinstance(value, (int, float)) else str(value)
        values = (name, text(length), text(start), text(end))
        for column, value in enumerate(values):
            self.table.setItem(row, column, QTableWidgetItem(value))

    def remove_row(self):
        row = self.table.currentRow()
        if row < 0 and self.table.rowCount():
            row = self.table.rowCount() - 1
        if row >= 0:
            self.table.removeRow(row)

    def set_segments(self, segments):
        self.table.setRowCount(0)
        for segment in segments:
            self.add_row(segment.name, segment.length_mm, segment.start_diameter_mm,
                         segment.end_diameter_mm)

    def segments(self):
        result = []
        for row in range(self.table.rowCount()):
            name = self.table.item(row, 0).text() if self.table.item(row, 0) else ""
            values = []
            for column, key in ((1, "length_mm"), (2, "start_diameter_mm"), (3, "end_diameter_mm")):
                item = self.table.item(row, column)
                values.append(parse_number(item.text() if item else "", key))
            result.append(DuctSegment(name, *values))
        return tuple(result)


class FourStrokeDuctsPage(QWidget):
    def __init__(self, context, parent=None):
        super().__init__(parent)
        self.context = context
        layout = QVBoxLayout(self)
        self.intake = _DuctTable("Conducto de admisión")
        self.exhaust = _DuctTable("Conducto de escape")
        layout.addWidget(self.intake)
        layout.addWidget(self.exhaust)
        self.error = QLabel()
        self.error.setWordWrap(True)
        self.error.setObjectName("fsDuctsError")
        layout.addWidget(self.error)
        self.apply_button = QPushButton("Aplicar conductos")
        self.apply_button.clicked.connect(self.apply)
        layout.addWidget(self.apply_button)
        layout.addStretch(1)
        self.load(context.project)

    def load(self, project: FourStrokeProject):
        self.intake.set_segments(project.ducts.intake)
        self.exhaust.set_segments(project.ducts.exhaust)
        self.error.clear()

    def apply(self) -> bool:
        try:
            ducts = Ducts(self.intake.segments(), self.exhaust.segments(),
                          reference=FOUR_DUCT_REFERENCE)
            ducts.validate()
            self.context.update(ducts=ducts)
        except (ProjectError, FourStrokeProjectError) as exc:
            self.error.setText(str(exc))
            return False
        self.error.clear()
        return True


class FourStrokeWorkspace(QWidget):
    """Workspace 4T autocontenido; el shell 2T no comparte sus páginas."""

    def __init__(self, context, parent=None):
        super().__init__(parent)
        self.context = context
        self.setObjectName("fourStrokeWorkspace")
        layout = QVBoxLayout(self)
        banner = QLabel(REFERENCE_BANNER)
        banner.setObjectName("fourStrokeReferenceBanner")
        banner.setWordWrap(True)
        layout.addWidget(banner)
        self.tabs = QTabWidget()
        self.geometry = FourStrokeGeometryPage(context)
        self.valves = FourStrokeValvesPage(context)
        self.ducts = FourStrokeDuctsPage(context)
        self.tabs.addTab(self.geometry, "Geometría")
        self.tabs.addTab(self.valves, "Válvulas")
        self.tabs.addTab(self.ducts, "Conductos")
        layout.addWidget(self.tabs, 1)
        self.status = QLabel()
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        context.project_changed.connect(self.refresh)
        context.changed.connect(self._refresh_status)
        self.refresh(context.project)

    def refresh(self, project: FourStrokeProject):
        self.geometry.load(project)
        self.valves.load(project)
        self.ducts.load(project)
        self._refresh_status()

    def apply_all(self) -> bool:
        for page in (self.geometry, self.valves, self.ducts):
            if not page.apply():
                self.tabs.setCurrentWidget(page)
                return False
        return True

    def _refresh_status(self):
        errors = self.context.execution_errors()
        if errors:
            self.status.setText("No calculable todavía: " + " · ".join(errors[:3]))
        else:
            self.status.setText("Proyecto 4T completo para ejecutar.")
