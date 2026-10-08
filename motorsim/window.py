"""Editor de la ficha del motor."""

from pathlib import Path
import sys

from PySide6.QtCore import Qt, QSize, QTimer
from PySide6.QtGui import (
    QAction, QCloseEvent, QColor, QIcon, QKeySequence, QPainter, QPainterPath,
    QPalette, QPen, QPixmap,
)
from PySide6.QtWidgets import (
    QComboBox, QDialog, QFileDialog, QFormLayout, QFrame, QGridLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit,
    QMainWindow, QMessageBox, QPlainTextEdit, QScrollArea, QSizePolicy,
    QTabWidget, QStackedWidget, QToolBar, QVBoxLayout, QWidget,
)

from .project import (NUMERIC_FIELDS, PORT_FIELDS, INTAKE_FIELDS, DUCT_FIELDS, VALVE_FIELDS, Project,
                      Port, Intake, FourStroke, Valve, Ducts, DuctSegment, ProjectError, displacements, parse_number)
from .project_case import execution_errors
from .storage import load_project, save_project
from .geometry_view import GeometryView
from .ports_view import PortsView
from .ducts_view import DuctsView
from .valves_view import ValvesView
from .simulation_view import SimulationView
from .runtime import APP_VERSION, build_info, resource
from .workspaces import Navigation, SummaryPage, MotorPage, ResultWorkspace, scroll, refresh_motor_context
from .comparison_view import ComparisonDialog
from .external_view import ExternalDialog
from .examples import EXAMPLES, PROJECT_FILES, example_project
from .ui import NumericUnit
from .performance_view import PerformanceView


class _FilePathLabel(QLabel):
    """Ruta abreviada en la barra; la ruta completa queda en la ayuda emergente."""

    def __init__(self) -> None:
        super().__init__()
        self.full_text = ""
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.setMinimumWidth(100)
        self.setTextFormat(Qt.TextFormat.PlainText)

    def set_path_text(self, text: str) -> None:
        self.full_text = text
        self.setToolTip(text)
        self.setAccessibleName(text)
        self._fit_text()

    def _fit_text(self) -> None:
        self.setText(self.fontMetrics().elidedText(
            self.full_text, Qt.TextElideMode.ElideLeft, self.contentsRect().width()))

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._fit_text()


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.path: Path | None = None
        self.dirty = False
        self._closing_after_simulation = False
        self.resize(1080, 760)
        self.setMinimumSize(640, 480)
        self.setWindowTitle("MotorSim")
        self.setStyleSheet(Path(__file__).with_name("theme.qss").read_text(encoding="utf-8"))
        palette = self.palette()
        for role, color in (
            (QPalette.ColorRole.Window, "#131b2e"),
            (QPalette.ColorRole.Base, "#060e20"),
            (QPalette.ColorRole.AlternateBase, "#171f33"),
            (QPalette.ColorRole.Text, "#dae2fd"),
            (QPalette.ColorRole.WindowText, "#dae2fd"),
            (QPalette.ColorRole.Button, "#171f33"),
            (QPalette.ColorRole.ButtonText, "#dae2fd"),
            (QPalette.ColorRole.Highlight, "#24415b"),
            (QPalette.ColorRole.HighlightedText, "#ffffff"),
        ):
            palette.setColor(role, QColor(color))
        self.setPalette(palette)

        self.name_edit = QLineEdit()
        self.name_edit.setMaxLength(2147483647)
        self.name_edit.setObjectName("project_name")
        self.cycle_combo = QComboBox()
        self.cycle_combo.addItems(["2T", "4T"])
        self.cycle_combo.setMaximumWidth(140)
        self.text_edits = {field: QLineEdit() for field in ("manufacturer", "model")}
        for edit in self.text_edits.values():
            edit.setMaxLength(2147483647)
            edit.setPlaceholderText("Opcional")
        self.notes_edit = QPlainTextEdit()
        self.notes_edit.setPlaceholderText("Opcional")
        self.notes_edit.setTabChangesFocus(True)
        self.notes_edit.setMinimumHeight(96)
        self.notes_edit.setMaximumHeight(160)
        self.numeric_edits = {field: QLineEdit() for field in NUMERIC_FIELDS}
        self.numeric_errors = {field: self._label("", "fieldError") for field in NUMERIC_FIELDS}
        self.volume_label = self._label("—", "resultValue")
        self.total_volume_label = self._label("—", "resultValue")
        self._edit_widgets = [self.name_edit, self.cycle_combo, *self.text_edits.values(),
                              self.notes_edit, *self.numeric_edits.values()]
        self._wide_layout = None
        self.file_label = _FilePathLabel()
        self.state_label = QLabel()
        self.state_label.setObjectName("projectState")
        self.notice = QLabel("Simulación · modelo 0D")
        self.notice.setObjectName("availability")

        menu = self.menuBar().addMenu("&Archivo")
        self.actions = {}
        for key, title, shortcut, callback in (
            ("new", "&Nuevo", QKeySequence.StandardKey.New, self.new_project),
            ("open", "&Abrir…", QKeySequence.StandardKey.Open, self.open_project),
            ("save", "&Guardar", QKeySequence.StandardKey.Save, self.save),
            ("save_as", "Guardar &como…", QKeySequence.StandardKey.SaveAs, self.save_as),
            ("exit", "&Salir", QKeySequence("Alt+F4"), self.close),
        ):
            action = QAction(title, self)
            action.setShortcut(shortcut)
            action.triggered.connect(callback)
            action.setToolTip(f"{title.replace('&', '')}  ·  {action.shortcut().toString()}")
            menu.addAction(action)
            self.actions[key] = action
            if key in ("open", "save_as"):
                menu.addSeparator()

        examples_menu = menu.addMenu('Cargar &ejemplo')
        menu.insertMenu(self.actions['exit'], examples_menu)
        self.example_actions = {}
        for key, (title, _) in EXAMPLES.items():
            action = examples_menu.addAction(title)
            action.triggered.connect(lambda checked=False, key=key: self.load_example(key))
            self.example_actions[key] = action

        self._build_toolbar()
        self._build_workspace()
        self._build_statusbar()
        help_menu=self.menuBar().addMenu('A&yuda')
        help_menu.addAction('Guía breve…',self.show_help)
        help_menu.addAction('Acerca de MotorSim…',self.show_about)

        self.name_edit.textChanged.connect(self._edited)
        self.cycle_combo.currentTextChanged.connect(self._edited)
        for edit in (*self.text_edits.values(), *self.numeric_edits.values()):
            edit.textChanged.connect(self._edited)
        self.notes_edit.textChanged.connect(self._edited)
        self._activate(Project(), None)

    def show_help(self):
        dialog=QDialog(self);dialog.setWindowTitle('MotorSim — Guía breve');dialog.resize(650,450)
        layout=QVBoxLayout(dialog);text=QPlainTextEdit();text.setReadOnly(True)
        text.setPlainText(resource('ayuda.txt').read_text(encoding='utf-8'));layout.addWidget(text)
        dialog.exec()

    def show_about(self):
        info=build_info()
        QMessageBox.about(self,'Acerca de MotorSim',f'MotorSim {APP_VERSION}\nCandidata Windows x64\n'
            f'Fuente: {info["source_commit"]}\nProyecto JSON v6; resultados 2T v1–v3 / 4T v4.\n'
            'Modelos 0D 2T/360° y 4T/720°, energía prescrita; sin ondas ni validación experimental.\n'
            'Ejecutable no firmado. Ayuda y avisos de dependencias incluidos en la carpeta.')

    @staticmethod
    def _label(text: str, style: str = "") -> QLabel:
        label = QLabel(text)
        label.setObjectName(style)
        label.setWordWrap(True)
        return label

    def _build_toolbar(self) -> None:
        self.file_toolbar = QToolBar("Acciones de proyecto", self)
        self.file_toolbar.setMovable(False)
        self.file_toolbar.setFloatable(False)
        self.file_toolbar.setContextMenuPolicy(Qt.ContextMenuPolicy.PreventContextMenu)
        self.file_toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.file_toolbar.setIconSize(QSize(16, 16))
        for key in ("new", "open", "save"):
            self.actions[key].setIcon(self._action_icon(key))
            self.file_toolbar.addAction(self.actions[key])
            if key == "open":
                self.file_toolbar.addSeparator()
        self.file_toolbar.widgetForAction(self.actions["save"]).setObjectName("primaryAction")
        self.addToolBar(self.file_toolbar)

    @staticmethod
    def _action_icon(key: str) -> QIcon:
        """Pictogramas de archivo dibujados con Qt, sin recursos externos."""
        outlines = {
            "new": [((4, 2), (10, 2), (14, 6), (14, 16), (4, 16), (4, 2)),
                    ((10, 2), (10, 6), (14, 6))],
            "open": [((2, 8), (2, 4), (7, 4), (9, 6), (16, 6), (14, 15), (2, 15), (2, 8), (15, 8))],
            "save": [((3, 2), (13, 2), (16, 5), (16, 16), (3, 16), (3, 2)),
                     ((6, 2), (6, 7), (12, 7), (12, 2)), ((6, 16), (6, 11), (13, 11), (13, 16))],
            "save_as": [((4, 2), (10, 2), (14, 6), (14, 9)),
                        ((9, 16), (4, 16), (4, 2)), ((10, 2), (10, 6), (14, 6)),
                        ((10, 13), (16, 13)), ((13, 10), (13, 16))],
        }
        pixmap = QPixmap(36, 36)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.scale(2, 2)
        painter.setPen(QPen(QColor("#002c47" if key == "save" else "#93ccff"), 1.2))
        for points in outlines[key]:
            path = QPainterPath()
            path.moveTo(*points[0])
            for point in points[1:]:
                path.lineTo(*point)
            painter.drawPath(path)
        painter.end()
        return QIcon(pixmap)

    def _build_workspace(self) -> None:
        self.general_group = QGroupBox("Datos generales")
        general = QVBoxLayout(self.general_group)
        general.setContentsMargins(18, 28, 18, 18)
        general.setSpacing(9)
        for label, edit in (("&Nombre del proyecto", self.name_edit),
                            ("&Tipo de motor", self.cycle_combo),
                            ("&Fabricante", self.text_edits["manufacturer"]),
                            ("&Modelo", self.text_edits["model"]),
                            ("&Observaciones", self.notes_edit)):
            caption = self._label(label)
            caption.setBuddy(edit)
            general.addWidget(caption)
            general.addWidget(edit)
        self.geometry_group = QGroupBox("Datos básicos")
        geometry = QVBoxLayout(self.geometry_group)
        geometry.setContentsMargins(18, 28, 18, 18)
        geometry.setSpacing(18)
        fields = QFormLayout()
        fields.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
        fields.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        fields.setHorizontalSpacing(18)
        fields.setVerticalSpacing(12)
        captions = {
            "cylinder_count": ("Número de &cilindros", "cil."),
            "bore_mm": ("&Diámetro del cilindro", "mm"),
            "stroke_mm": ("Ca&rrera", "mm"),
            "rod_length_mm": ("&Biela entre centros", "mm"),
            "compression_ratio": ("Compresión &geométrica", ":1"),
        }
        for field, (title, unit) in captions.items():
            edit = self.numeric_edits[field]
            edit.setObjectName(field)
            edit.setMinimumWidth(70)
            edit.setMaximumWidth(200)
            caption = self._label(title)
            caption.setBuddy(edit)
            container = NumericUnit(edit,unit,self.numeric_errors[field])
            fields.addRow(caption, container)
        geometry.addLayout(fields)
        results = QFormLayout()
        results.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
        results.setVerticalSpacing(10)
        for title, result in (("Cilindrada por cilindro", self.volume_label),
                              ("Cilindrada total", self.total_volume_label)):
            result.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            result.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
            result.setMinimumWidth(100)
            row = QHBoxLayout()
            row.addWidget(result, 1)
            row.addWidget(self._label("cm³", "unit"))
            results.addRow(self._label(title), row)
        self.geometry_derived=QWidget();derived=QVBoxLayout(self.geometry_derived);derived.setContentsMargins(0,0,0,0)
        derived.addLayout(results)
        derived.addWidget(self._label("Cilindrada total: todos los cilindros comparten geometría.", "unit"))
        self.geometry_view = GeometryView()
        self.ports_view = PortsView();self.ports_view.changed.connect(self._edited)
        self.ducts_view = DuctsView();self.ducts4_view = DuctsView('4T')
        self.ducts_view.changed.connect(self._edited);self.ducts4_view.changed.connect(self._edited)
        self.valves_view = ValvesView();self.valves_view.changed.connect(self._edited)
        self.simulation_view = SimulationView(self.execution_snapshot,lambda:self.cycle_combo.currentText())
        self.simulation_view.idle.connect(self._simulation_idle)
        self.navigation=Navigation();self.tabs=self.navigation
        self.simulation_view.workspace_router=self._navigate_analysis
        intake_body=QWidget();intake_layout=QVBoxLayout(intake_body)
        for widget in (self.ports_view.crank_widget,self.ports_view.crankcase_error,self.ports_view.intake):intake_layout.addWidget(widget)
        intake_layout.addStretch()
        self.motor2_page=MotorPage('2T',[('Lumbreras',self.ports_view),('Admisión y cárter',scroll(intake_body)),('Conductos',self.ducts_view)])
        self.motor4_page=MotorPage('4T',[('Válvulas y distribución',self.valves_view),('Conductos',self.ducts4_view)])
        self.duct_stack=self.ducts_view  # Alias de navegación interna; los editores siguen separados por ciclo.
        self.geometry_view.attach_editor(self.geometry_group,self.geometry_derived)
        self.geometry_page=self.geometry_view
        self.summary_page=SummaryPage(self);self.workspace_scroll=self.summary_page
        self.result_workspace=ResultWorkspace(self.simulation_view)
        self.performance_page=PerformanceView(self.simulation_view)
        self.comparison_page=ComparisonDialog(self,embedded=True)
        self.external_page=ExternalDialog(self,embedded=True)
        self.simulation_view.comparison_dialog=self.comparison_page
        self.simulation_view.external_dialog=self.external_page
        for group,key,title,page in (
            ('PROYECTO','summary','Resumen',self.summary_page),
            ('CONFIGURACIÓN','geometry','Geometría',self.geometry_page),
            ('CONFIGURACIÓN','motor2','Motor 2T',self.motor2_page),
            ('CONFIGURACIÓN','motor4','Motor 4T',self.motor4_page),
            ('CÁLCULO','simulation','Simulación',self.simulation_view),
            ('CÁLCULO','performance','Rendimiento',self.performance_page),
            ('ANÁLISIS','results','Resultados',self.result_workspace),
            ('ANÁLISIS','compare','Comparar',self.comparison_page),
            ('ANÁLISIS','external','Datos externos',scroll(self.external_page))):
            self.navigation.add_page(group,key,title,page)
        self.navigation.aliases={self.geometry_view:('geometry',None),self.ports_view:('motor2',lambda:self.motor2_page.tabs.setCurrentIndex(0)),
            self.ducts_view:('motor2',lambda:(self.motor2_page.tabs.setCurrentIndex(2) if self.cycle_combo.currentText()=='2T' else self.motor4_page.tabs.setCurrentIndex(1))),
            self.valves_view:('motor4',lambda:self.motor4_page.tabs.setCurrentIndex(0)),self.simulation_view:('simulation',None)}
        self.navigation.selected.connect(self._workspace_selected)
        self.setCentralWidget(self.navigation);self.navigation.go('summary')
        self.ui_status_timer=QTimer(self);self.ui_status_timer.setInterval(250)
        self.simulation_view.state_label.changed.connect(self._calculation_status)
        self.ui_status_timer.timeout.connect(self._calculation_status);self.ui_status_timer.start()
        for previous, following in zip(self._edit_widgets, self._edit_widgets[1:]):
            QWidget.setTabOrder(previous, following)

    def _workspace_selected(self,key):
        view=self.simulation_view
        if key=='performance':self.performance_page.sync_session()
        if key=='results':
            self.result_workspace.detail_layout.addWidget(view.result_panel)
            self.result_workspace.message_host.addWidget(view.error_label)
        elif key=='simulation':
            if not view.active and view.result is None and view.sweep is None:view._origin_changed()
            view.result_host.addWidget(view.result_panel)
            view.message_host.addWidget(view.error_label)
        view.result_panel.setVisible(key=='results');view._arrange()

    def _navigate_analysis(self,key):
        self.navigation.go('results' if key=='sweep' else key)
        if key=='sweep':self.result_workspace.show_series(self.simulation_view.sweep_dialog)
        if key=='results':self.result_workspace.show_result()

    def _calculation_status(self):
        view=self.simulation_view
        state=view.state_badge.text()
        self.notice.setText(f'{self.cycle_combo.currentText()} · {state} · {APP_VERSION}')

    def _arrange_groups(self):
        if hasattr(self,'geometry_view'):self.geometry_view._arrange()

    def resizeEvent(self,event):
        super().resizeEvent(event)
        self._arrange_groups()

    def _update_geometry(self) -> None:
        cycle = self.cycle_combo.currentText()
        self.navigation.set_cycle(cycle)
        self.ducts_view.set_cycle('2T')
        self.ducts4_view.set_cycle('4T')
        self.valves_view.setEnabled(cycle == '4T')
        parsed = {}
        for field, edit in self.numeric_edits.items():
            try:
                parsed[field] = parse_number(edit.text(), field)
                message = ""
            except ProjectError as exc:
                # Ausente solo para este cálculo; el texto inválido sigue en el
                # widget y project() volverá a rechazarlo antes de guardar.
                parsed[field] = None
                message = str(exc)
            self.numeric_errors[field].setText(message)
            self.numeric_errors[field].setVisible(bool(message))
            edit.setProperty("invalid", bool(message))
            edit.setAccessibleDescription(message)
            edit.style().unpolish(edit)
            edit.style().polish(edit)
        per_cylinder, total = displacements(parsed["bore_mm"], parsed["stroke_mm"], parsed["cylinder_count"])
        for label, value in ((self.volume_label, per_cylinder), (self.total_volume_label, total)):
            label.setText("—" if value is None else f"{value:.2f}")
            label.setToolTip(label.text())

        self.geometry_view.set_inputs(parsed, self.cycle_combo.currentText(),
                                      {field: label.text() for field, label in self.numeric_errors.items()},
                                      self.name_edit.text())

        self.ports_view.set_common(parsed, self.cycle_combo.currentText(),
                                   {field: label.text() for field, label in self.numeric_errors.items()})

    def _build_statusbar(self) -> None:
        information = QWidget()
        layout = QHBoxLayout(information)
        layout.setContentsMargins(8, 0, 8, 0)
        layout.setSpacing(14)
        layout.addWidget(self.file_label, 1)
        layout.addWidget(self.state_label)
        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.VLine)
        divider.setObjectName("statusDivider")
        divider.setFixedHeight(14)
        layout.addWidget(divider)
        layout.addWidget(self.notice)
        self.statusBar().addPermanentWidget(information, 1)

    def project(self) -> Project:
        ports, crankcase, intake = self.ports_view.snapshot()
        return Project(
            ports=ports, crankcase_volume_bdc_cm3=crankcase, intake=intake,
            ducts=self.ducts_view.snapshot(),
            four_stroke=FourStroke(**self.valves_view.snapshot(), ducts=self.ducts4_view.snapshot()),
            name=self.name_edit.text(), cycle=self.cycle_combo.currentText(),
            manufacturer=self.text_edits["manufacturer"].text(),
            model=self.text_edits["model"].text(), notes=self.notes_edit.toPlainText(),
            **{field: parse_number(edit.text(), field) for field, edit in self.numeric_edits.items()},
        )

    def execution_snapshot(self):
        """Leer todos los borradores; nunca sustituir texto inválido al ejecutar."""
        errors = []
        def number(text, key, context=''):
            try:
                return parse_number(text, key)
            except ProjectError as exc:
                errors.append(context+str(exc))
                return None  # Solo para reunir errores: la copia no sale si hay alguno.
        if self.cycle_combo.currentText()=='4T':
            valves={role:Valve(**{k:number(edit.text(),k,role+': ') for k,edit in fields.items()})
                    for role,fields in self.valves_view.edits.items()}
            from .project import FOUR_DUCT_REFERENCE
            ducts4=Ducts(**{role:tuple(DuctSegment(d['name'],**{k:number(d[k],k,role+': ') for k in DUCT_FIELDS})
                    for d in rows) for role,rows in self.ducts4_view.drafts.items()},reference=FOUR_DUCT_REFERENCE)
            project=Project(name=self.name_edit.text(),cycle='4T',
                manufacturer=self.text_edits['manufacturer'].text(),model=self.text_edits['model'].text(),
                notes=self.notes_edit.toPlainText(),four_stroke=FourStroke(**valves,ducts=ducts4),
                **{k:number(edit.text(),k) for k,edit in self.numeric_edits.items()})
            errors.extend(execution_errors(project))
            if errors:raise ProjectError('\n'.join(dict.fromkeys(errors)))
            return project,dict(kind='project',project_name=project.name,source_path=str(self.path) if self.path else None,dirty=self.dirty)
        ports = tuple(Port(d['name'], d['function'], **{
            k:number(d[k], k, f'Lumbrera {i+1}: ') for k in PORT_FIELDS})
            for i, d in enumerate(self.ports_view.drafts))
        intake = self.ports_view.intake
        ducts = Ducts(**{route:tuple(DuctSegment(d['name'], **{
            k:number(d[k], k, f'Conducto {"admisión" if route == "intake" else "escape"}, tramo {i+1}: ')
            for k in DUCT_FIELDS}) for i, d in enumerate(rows))
            for route, rows in self.ducts_view.drafts.items()})
        project = Project(name=self.name_edit.text(), cycle=self.cycle_combo.currentText(),
            manufacturer=self.text_edits['manufacturer'].text(), model=self.text_edits['model'].text(),
            notes=self.notes_edit.toPlainText(), ports=ports, ducts=ducts,
            four_stroke=FourStroke(**self.valves_view.snapshot(), ducts=self.ducts4_view.snapshot()),
            intake=Intake(mode=intake.mode_combo.currentData(), **{
                k:number(intake.edits[k].text(), k, 'Admisión: ') for k in INTAKE_FIELDS}),
            crankcase_volume_bdc_cm3=number(self.ports_view.crankcase_edit.text(), 'crankcase_volume_bdc_cm3'),
            **{k:number(edit.text(), k) for k, edit in self.numeric_edits.items()})
        errors.extend(execution_errors(project))
        if errors:
            raise ProjectError('\n'.join(dict.fromkeys(errors)))
        return project, dict(kind='project', project_name=project.name,
                             source_path=str(self.path) if self.path else None, dirty=self.dirty)

    def _edited(self) -> None:
        self.dirty = True
        self.performance_page._historical_context=None
        self._update_geometry()
        self._refresh_status()

    def _refresh_status(self) -> None:
        self.file_label.set_path_text(str(self.path) if self.path else "Sin archivo asociado")
        self.state_label.setText("Cambios pendientes" if self.dirty else
                                 ("Guardado" if self.path else "Sin cambios pendientes"))
        self.state_label.setProperty("pending", self.dirty)
        self.state_label.style().unpolish(self.state_label)
        self.state_label.style().polish(self.state_label)
        self.simulation_view.project_changed()
        self.setWindowTitle(f'MotorSim — {self.name_edit.text() or "Sin nombre"} · {self.cycle_combo.currentText()} · {self.state_label.text()}')
        self._calculation_status()
        self.summary_page.refresh()
        refresh_motor_context(self)

    def _activate(self, project: Project, path: Path | None) -> None:
        self.performance_page.clear_sweep()
        blocked = [widget.blockSignals(True) for widget in self._edit_widgets]
        try:
            self.name_edit.setText(project.name)
            self.cycle_combo.setCurrentText(project.cycle)
            for field, edit in self.text_edits.items():
                edit.setText(getattr(project, field))
            self.notes_edit.setPlainText(project.notes)
            for field, edit in self.numeric_edits.items():
                value = getattr(project, field)
                edit.setText("" if value is None else str(value))
        finally:
            for widget, was_blocked in zip(self._edit_widgets, blocked):
                widget.blockSignals(was_blocked)
        self.ports_view.load(project)
        self.ducts_view.load(project.ducts)
        self.ducts4_view.load(project.four_stroke.ducts)
        self.valves_view.load(project.four_stroke)
        self.path = path
        self.dirty = False
        self._update_geometry()
        self._refresh_status()

    def _error(self, error: ProjectError) -> None:
        box = QMessageBox(QMessageBox.Icon.Critical, "MotorSim — Error", str(error), parent=self)
        box.addButton("Aceptar", QMessageBox.ButtonRole.AcceptRole)
        box.exec()

    def _ask_changes(self) -> str:
        box = QMessageBox(QMessageBox.Icon.Warning, "Cambios pendientes",
                          "¿Querés guardar los cambios del proyecto antes de continuar?", parent=self)
        save = box.addButton("Guardar", QMessageBox.ButtonRole.AcceptRole)
        discard = box.addButton("Descartar", QMessageBox.ButtonRole.DestructiveRole)
        cancel = box.addButton("Cancelar", QMessageBox.ButtonRole.RejectRole)
        box.setDefaultButton(cancel)
        box.setEscapeButton(cancel)
        box.exec()
        if box.clickedButton() is save:
            return "save"
        if box.clickedButton() is discard:
            return "discard"
        return "cancel"

    def _can_leave(self) -> bool:
        if not self.dirty:
            return True
        choice = self._ask_changes()
        return choice == "discard" or (choice == "save" and self.save())

    def new_project(self) -> None:
        if self._can_leave():
            self._activate(Project(), None)

    def load_example_file(self, key: str) -> None:
        root=(Path(sys.executable).resolve().parent/'Ejemplos' if getattr(sys,'frozen',False)
              else Path(__file__).resolve().parent.parent/'examples'/'projects')
        try:
            project=load_project(root/PROJECT_FILES[key])
        except (OSError,ProjectError) as exc:
            QMessageBox.warning(self,'No se pudo cargar el ejemplo',str(exc));return
        self.load_example(key,project=project)

    def load_example(self, key: str, *, project=None) -> None:
        if not self._can_leave():
            return
        self._activate(project if project is not None else example_project(key), None)
        self.dirty = True
        self._refresh_status()
        if self.simulation_view.origin_combo.currentIndex() == 1:
            self.simulation_view._origin_changed()
        else:
            self.simulation_view.origin_combo.setCurrentIndex(1)
        self.navigation.go('summary')
        self.summary_page.tabs.setCurrentIndex(0)

    def _choose_file(self, saving: bool) -> Path | None:
        dialog = QFileDialog(self, "Guardar proyecto como" if saving else "Abrir proyecto")
        # Diálogo Qt para mantener etiquetas en español en cualquier Windows.
        dialog.setOption(QFileDialog.Option.DontUseNativeDialog)
        dialog.setNameFilters(["Proyectos JSON (*.json)", "Todos los archivos (*)"])
        dialog.setLabelText(QFileDialog.DialogLabel.LookIn, "Carpeta:")
        dialog.setLabelText(QFileDialog.DialogLabel.FileName, "Archivo:")
        dialog.setLabelText(QFileDialog.DialogLabel.FileType, "Tipo de archivo:")
        dialog.setLabelText(QFileDialog.DialogLabel.Accept, "Guardar" if saving else "Abrir")
        dialog.setLabelText(QFileDialog.DialogLabel.Reject, "Cancelar")
        if saving:
            dialog.setAcceptMode(QFileDialog.AcceptMode.AcceptSave)
            dialog.setFileMode(QFileDialog.FileMode.AnyFile)
            dialog.setDefaultSuffix("json")
            # La confirmación explícita también se usa en los tests.
            dialog.setOption(QFileDialog.Option.DontConfirmOverwrite)
            if self.path:
                dialog.selectFile(str(self.path))
        else:
            dialog.setFileMode(QFileDialog.FileMode.ExistingFile)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            return Path(dialog.selectedFiles()[0]).absolute()
        return None

    def open_project(self) -> None:
        # Elegir y validar primero: cancelar o rechazar un archivo no altera
        # siquiera el estado pendiente, aunque después se decida guardar.
        path = self._choose_file(False)
        if path is None:
            return
        try:
            project = load_project(path)
        except ProjectError as exc:
            self._error(exc)
            return
        if self._can_leave():
            # Guardar antes de abrir puede haber actualizado ese mismo archivo.
            try:
                project = load_project(path)
            except ProjectError as exc:
                self._error(exc)
                return
            self._activate(project, path)

    def _confirm_overwrite(self, path: Path) -> bool:
        box = QMessageBox(QMessageBox.Icon.Warning, "Confirmar sobrescritura",
                          f"Ya existe «{path}». ¿Querés reemplazarlo?", parent=self)
        replace = box.addButton("Reemplazar", QMessageBox.ButtonRole.AcceptRole)
        cancel = box.addButton("Cancelar", QMessageBox.ButtonRole.RejectRole)
        box.setDefaultButton(cancel)
        box.setEscapeButton(cancel)
        box.exec()
        return box.clickedButton() is replace

    def _save_to(self, path: Path) -> bool:
        try:
            save_project(path, self.project())
        except ProjectError as exc:
            self._error(exc)
            return False
        self.path = path
        self.dirty = False
        self._refresh_status()
        return True

    def save(self) -> bool:
        return self._save_to(self.path) if self.path else self.save_as()

    def save_as(self) -> bool:
        try:
            self.project().validate()
        except ProjectError as exc:
            self._error(exc)
            return False
        path = self._choose_file(True)
        if path is None:
            return False
        if path.exists() and not self._confirm_overwrite(path):
            return False
        return self._save_to(path)

    def closeEvent(self, event: QCloseEvent) -> None:
        if not self._closing_after_simulation and not self._can_leave():
            event.ignore()
            return
        if self.simulation_view.active:
            self._closing_after_simulation = True
            self.setEnabled(False)
            self.simulation_view.cancel()
            event.ignore()
            return
        event.accept()

    def _simulation_idle(self):
        if self._closing_after_simulation:
            QTimer.singleShot(0, self.close)
