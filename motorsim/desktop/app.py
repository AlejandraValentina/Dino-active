from __future__ import annotations
import json
import os
import tempfile
from pathlib import Path
from PySide6.QtCore import QSettings,Qt,QThreadPool,QTimer,QElapsedTimer
from PySide6.QtGui import QAction,QKeySequence,QGuiApplication
from PySide6.QtWidgets import (QMainWindow,QWidget,QHBoxLayout,QVBoxLayout,QListWidget,QListWidgetItem,
    QStackedWidget,QLabel,QToolBar,QFileDialog,QMessageBox,QApplication,QSplitter,QScrollArea,
    QGroupBox,QFormLayout,QTreeWidget,QTreeWidgetItem,QDockWidget,QDoubleSpinBox,QSpinBox,QPushButton,QPlainTextEdit,QTabBar,QProgressBar,QTableWidget,QDialog,QTabWidget,QButtonGroup,QComboBox)
from ..engine_configuration import validate
from ..engine_project import load_project,save_project
from .services import new_design_project
from .new_engine_dialog import NewEngineDialog
from .context import DesktopContext
from .engine_page import EnginePage
from .exhaust_page import ExhaustPage
from .project_page import ProjectPage
from .results_page import ResultsPage
from .execution_page import ExecutionPage
from .four_stroke_context import FourStrokeContext
from .four_stroke_workspace import FourStrokeWorkspace
from .four_stroke_execution import FourStrokeExecution
from .four_stroke_results import FourStrokeResultsPage
from .widgets.context_bar import ContextBar
from .preferences import settings, repository_root_containing
from .theme import stylesheet
from .presentation import state_label

PAGES=(('Motor',EnginePage),('Escape',ExhaustPage),('Proyecto',ProjectPage),('Simulación',ExecutionPage),('Resultados',ResultsPage))

class DinoDesktopWindow(QMainWindow):
    def __init__(self,project=None):
        super().__init__();self.settings=settings();self.context=DesktopContext(project or new_design_project())
        self.setWindowTitle('Dino Desktop · 2T')
        screen=QApplication.primaryScreen();available=screen.availableGeometry() if screen else None
        width=min(1360,available.width()) if available else 1360
        height=min(900,available.height()) if available else 900
        # Keep a 980×680 outer window usable on Windows, where Qt's requested
        # size excludes the native frame (about 16×39 px on the supported style).
        self.setMinimumSize(min(960,width),min(630,height));self.resize(width,height)
        self.setStyleSheet(stylesheet())
        saved_variant=self.settings.value(f"active_variant/{self.context.project['project_id']}")
        if saved_variant in self.context.project["variants"]: self.context.select_variant(saved_variant)
        self._build_ui();self._build_actions();self.toolbar.hide();self.context.changed.connect(self._state_changed)
        self.context.variant_changed.connect(self._variant_changed)
        self._restore_settings();self._state_changed();self._select_baseline(self.context_bar.baseline.currentData())
        if project is None:self._ensure_safe_artifact_root_for_new_project()
    def _build_ui(self):
        shell=QWidget();layout=QVBoxLayout(shell);layout.setContentsMargins(0,0,0,0);layout.setSpacing(0)
        self.context_bar=ContextBar();self.context_bar.setObjectName("contextBar")
        self.context_bar.variant_selected.connect(self.context.select_variant);layout.addWidget(self.context_bar)
        mode_row=QHBoxLayout();mode_row.setContentsMargins(18,9,18,10);mode_row.setSpacing(12)
        mode_label=QLabel("MODO DE TRABAJO");mode_label.setObjectName("workspaceModeLabel");mode_row.addWidget(mode_label)
        self.design_mode=QPushButton("MODELO");self.design_mode.setCheckable(True);self.design_mode.setChecked(True);self.design_mode.setObjectName("modeDesign")
        self.simulate_mode=QPushButton("SIMULAR");self.simulate_mode.setCheckable(True);self.simulate_mode.setObjectName("modeSimulate")
        self.analysis_mode=QPushButton("RESULTADOS");self.analysis_mode.setCheckable(True);self.analysis_mode.setObjectName("modeAnalysis")
        for button in (self.design_mode,self.simulate_mode,self.analysis_mode):
            button.setProperty("class","workspaceModeButton");button.setMinimumSize(112,36)
        self.mode_group=QButtonGroup(self);self.mode_group.setExclusive(True);self.mode_group.addButton(self.design_mode,0);self.mode_group.addButton(self.analysis_mode,1)
        self.mode_group.addButton(self.simulate_mode,2)
        mode_row.addWidget(self.design_mode);mode_row.addWidget(self.simulate_mode);mode_row.addWidget(self.analysis_mode);mode_row.addStretch(1);layout.addLayout(mode_row)
        project_actions=QHBoxLayout();project_actions.setContentsMargins(14,2,14,5)
        for text,callback in (("Nuevo motor…",self.new_file),("Abrir proyecto…",self.open_file),("Guardar",self.save_file)):
            button=QPushButton(text);button.clicked.connect(callback);project_actions.addWidget(button)
        self.explorer_button=QPushButton("Variantes y corridas…");self.explorer_button.clicked.connect(self._toggle_explorer);project_actions.addWidget(self.explorer_button)
        self.traceability_button=QPushButton("Trazabilidad…");self.traceability_button.clicked.connect(self._toggle_traceability);project_actions.addWidget(self.traceability_button)
        self.four_stroke_button=QPushButton("Modo 4T 0D…");self.four_stroke_button.setToolTip("Abrir el modo 4T 0D de referencia sintética");self.four_stroke_button.clicked.connect(self.show_four_stroke_mode);project_actions.addWidget(self.four_stroke_button)
        project_actions.addStretch();layout.addLayout(project_actions)
        self.mode_stack=QStackedWidget();layout.addWidget(self.mode_stack,1)
        self.pages=[page_type(self.context) for _,page_type in PAGES]
        self.pages[0].component_state_changed.connect(self._refresh_component_states)
        self.pages[1].component_state_changed.connect(self._refresh_component_states)
        self.results=self.pages[4]
        for page in self.pages:
            for table in page.findChildren(QTableWidget):
                table.setAlternatingRowColors(True)
                table.horizontalHeader().setMinimumSectionSize(48)
                for column in range(table.columnCount()):
                    item=table.horizontalHeaderItem(column)
                    if item:item.setToolTip(item.text())
        self.context_bar.baseline_selected.connect(self._select_baseline)
        self.results.baseline_selector.currentIndexChanged.connect(lambda *_: self._sync_baseline_bar())
        self.design_workspace=QWidget()
        self.component_nav=QTabBar();self.component_nav.setObjectName("designSectionNav");self.component_nav.setShape(QTabBar.Shape.RoundedNorth);self.component_nav.setExpanding(False);self.component_nav.setUsesScrollButtons(True);self.component_nav.setMovable(False)
        self.component_nav.setDocumentMode(True);self.component_nav.setElideMode(Qt.TextElideMode.ElideNone)
        self.component_stack=QStackedWidget();self.component_stack.setObjectName("designComponentStack")
        self.project_tree=QTreeWidget();self.project_tree.setHeaderHidden(True);self.project_tree.setMaximumHeight(120);self.project_tree.itemClicked.connect(self._project_tree_clicked)
        for index in range(4):
            title=PAGES[index][0];page=self.pages[index]
            if index in (0,1):
                self.component_stack.addWidget(page)
                continue
            scroll=QScrollArea();scroll.setWidgetResizable(True);scroll.setFrameShape(QScrollArea.Shape.NoFrame);scroll.setWidget(page)
            self.component_stack.addWidget(scroll)
            if index==3:self.execution_scroll=scroll
        for label in ("Cilindro y culata","Lumbreras y transferencias","Escape","Pérdidas","Combustión","Proyecto","Admisión","Cárter","Resumen","Avanzado","Conductos de transferencia"):
            self.component_nav.addTab(label)
        # The section bar is the only visible navigation inside Design. The
        # EnginePage keeps its stack as an implementation detail, but its
        # second visible tab bar is hidden to avoid duplicate section systems.
        self.pages[0].component_tabs.tabBar().hide()
        self.design_layout=QVBoxLayout();self.design_layout.setContentsMargins(14,0,14,8);self.design_layout.setSpacing(7)
        chooser=QHBoxLayout();chooser.addWidget(QLabel('Componente del motor'))
        self.model_selector=QComboBox();self.model_selector.setObjectName('modelComponentSelector');self.model_selector.setMinimumWidth(270)
        for index in (8,0,7,6,10,1,2,4,3,5,9):self.model_selector.addItem(self.component_nav.tabText(index),index)
        self.model_selector.currentIndexChanged.connect(lambda i:self.component_nav.setCurrentIndex(self.model_selector.itemData(i)))
        chooser.addWidget(self.model_selector);chooser.addStretch()
        self.design_workspace.setLayout(self.design_layout);self.design_layout.addLayout(chooser);self.component_nav.hide();self.design_layout.addWidget(self.component_stack,1)
        self.mode_stack.addWidget(self.design_workspace)
        self.analysis_workspace=QWidget();analysis_layout=QVBoxLayout(self.analysis_workspace);analysis_layout.setContentsMargins(6,4,6,4)
        self.analysis_splitter=QSplitter(Qt.Orientation.Vertical);self.analysis_splitter.setChildrenCollapsible(False)
        self.analysis_splitter.addWidget(self.results)
        from .widgets.run_history import RunHistoryWidget
        self.analysis_history=RunHistoryWidget(self.context,self.pages[3].artifact_root,async_load=True,auto_refresh=False);self.analysis_history.setMinimumHeight(110);self.analysis_history.setMaximumHeight(190)
        self.analysis_history.open_runs.connect(self._open_indexed_runs)
        self.analysis_history.resume_run.connect(self.pages[3].resume_from_entry)
        self.analysis_history.entries_changed.connect(self.pages[3].set_history_entries)
        self.pages[3].set_history_entries(self.analysis_history.entries)
        self.pages[3].artifact_root_changed.connect(self._artifact_root_changed)
        self.pages[3].refresh_history_requested.connect(self.analysis_history.refresh)
        self.analysis_splitter.addWidget(self.analysis_history);self.analysis_splitter.setSizes([710,130]);analysis_layout.addWidget(self.analysis_splitter)
        self.history_toggle=QPushButton("Ocultar corridas")
        self.history_toggle.clicked.connect(lambda checked=False:self._toggle_history())
        self.history_toggle.hide()
        mode_row.addWidget(self.history_toggle)
        self.mode_stack.addWidget(self.analysis_workspace)
        # Reuse the execution page as a first-class workspace, rather than
        # moving it in and out of a modal preparation dialog.
        self.simulation_workspace=QWidget();simulation_layout=QVBoxLayout(self.simulation_workspace)
        simulation_layout.setContentsMargins(14,4,14,6)
        simulation_layout.addWidget(self.execution_scroll)
        self.execution_scroll.show()
        self.mode_stack.addWidget(self.simulation_workspace)
        self.explorer_dock=QDockWidget("Proyecto · variantes, corridas y comparaciones",self)
        explorer=QWidget();explorer_layout=QVBoxLayout(explorer)
        self.explorer_tabs=QTabWidget();explorer_layout.addWidget(self.explorer_tabs)
        variants_page=QWidget();variants_layout=QVBoxLayout(variants_page)
        variants_layout.addWidget(self.project_tree)
        manage=QPushButton("Gestionar / duplicar variantes…");manage.clicked.connect(self._show_project);variants_layout.addWidget(manage)
        self.analysis_history.setMaximumHeight(16777215);self.analysis_history.setMinimumHeight(160)
        self.explorer_tabs.addTab(self.analysis_history,"Corridas y comparaciones")
        self.explorer_tabs.addTab(variants_page,"Variantes")
        self.explorer_dock.setWidget(explorer);self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea,self.explorer_dock);self.explorer_dock.hide()
        self.history_toggle.hide()
        execution=self.pages[3];results=self.pages[4]
        execution.open_runs_requested.connect(self._open_indexed_runs)
        execution.design_study_completed.connect(self.results.open_design_study)
        results.resume_project_study_requested.connect(self._resume_project_study)
        results.evidence_updated.connect(self._update_evidence)
        self.inspector=QGroupBox("Motor y evidencia");self.inspector.setObjectName("inspector");self.inspector.setMinimumWidth(145);self.inspector.setMaximumWidth(320)
        inspector_layout=QVBoxLayout(self.inspector);inspector_layout.setContentsMargins(12,12,10,12)
        self.inspector_variant=QLabel();self.inspector_variant.setWordWrap(True);self.inspector_variant.setStyleSheet("font-size:12pt;font-weight:600;color:#d8edff")
        self.inspector_diff=QLabel();self.inspector_diff.setWordWrap(True)
        self.inspector_validity=QLabel();self.inspector_validity.setWordWrap(True)
        self.inspector_science=QLabel("Modo EXPLORATORIO. Los diagnósticos de escape no demostraron independencia espacial.");self.inspector_science.setWordWrap(True)
        inspector_layout.addWidget(QLabel("Variante activa"));inspector_layout.addWidget(self.inspector_variant)
        inspector_layout.addWidget(self.inspector_diff);inspector_layout.addWidget(self.inspector_validity);inspector_layout.addStretch(1);inspector_layout.addWidget(self.inspector_science)
        self.evidence_dock=QDockWidget("Evidencia y provenance",self);self.evidence_dock.setObjectName("evidenceDrawer")
        self.evidence_content=QWidget();evidence_layout=QVBoxLayout(self.evidence_content);evidence_layout.addWidget(self.inspector)
        self.evidence_text=QPlainTextEdit();self.evidence_text.setReadOnly(True);self.evidence_text.setPlaceholderText("Elegí una corrida para ver hashes, provenance, auditoría y conservación.");evidence_layout.addWidget(self.evidence_text,1)
        self.evidence_dock.setWidget(self.evidence_content)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea,self.evidence_dock);self.evidence_dock.hide()
        self.simulation_strip=QWidget();self.simulation_strip.setObjectName("simulationStatusStrip")
        strip=QHBoxLayout(self.simulation_strip);strip.setContentsMargins(12,5,12,5)
        self.run_state=QLabel("LISTO · sin corrida activa");self.run_state.setMinimumWidth(105);strip.addWidget(self.run_state)
        self.run_state.setMaximumWidth(220);self.run_state.setWordWrap(True)
        self.run_progress=QProgressBar();self.run_progress.setRange(0,100);self.run_progress.setValue(0);self.run_progress.setMaximumWidth(160);self.run_progress.setFormat("Sin actividad");strip.addWidget(self.run_progress)
        self.run_clock=QLabel("—");strip.addWidget(self.run_clock)
        self.run_config_summary=QLabel();strip.addWidget(self.run_config_summary)
        self.checkpoint_state=QLabel("Checkpoint: —");strip.addWidget(self.checkpoint_state,1)
        self.prepare_button=QPushButton("Preparar…");self.prepare_button.setObjectName("prepareRunPanel");self.prepare_button.clicked.connect(self._show_execution_panel);strip.addWidget(self.prepare_button)
        self.strip_run=execution.start;self.strip_run.setText("Iniciar corrida…");self.strip_run.setMinimumWidth(150);strip.addWidget(self.strip_run)
        self.strip_cancel=QPushButton("Cancelar");self.strip_cancel.setEnabled(False);self.strip_cancel.clicked.connect(execution.cancel_run);strip.addWidget(self.strip_cancel)
        self.strip_more=QPushButton('Más opciones');self.strip_more.setToolTip('Barrido RPM y recuperación')
        from PySide6.QtWidgets import QMenu
        menu=QMenu(self.strip_more)
        for label,callback in (('Barrido RPM / A/B…',execution.start_power_curve),('Estudio paramétrico geométrico…',execution.start_design_study),('Estudio paramétrico por RPM…',execution.start_design_rpm_envelope),('Estudio factorial de diseño 2×2…',execution.start_factorial_design_study),('Reanudar estudio paramétrico…',execution.resume_design_study),('Reanudar checkpoint seleccionado…',lambda:execution.start_run(resume=True)),('Reanudar barrido…',execution.resume_power_curve)):
            action=menu.addAction(label);action.triggered.connect(callback)
        self.resume_action=menu.actions()[1]
        self.strip_more.setMenu(menu);strip.addWidget(self.strip_more)
        execution.state_changed.connect(self._update_strip);execution.progress_signal.connect(self._update_progress)
        execution.progress_signal.connect(lambda *_: self._update_strip())
        execution.rpm.valueChanged.connect(self._update_strip);execution.cycles.valueChanged.connect(self._update_strip);execution.budget.valueChanged.connect(self._update_strip)
        self.design_mode.clicked.connect(lambda:self.set_workspace_mode(0));self.analysis_mode.clicked.connect(lambda:self.set_workspace_mode(1));self.simulate_mode.clicked.connect(lambda:self.set_workspace_mode(2))
        execution.cancel.hide()
        self.execution_dialog=QDialog(self);self.execution_dialog.setWindowTitle("Preparar prueba")
        screen=QApplication.primaryScreen();available=screen.availableGeometry() if screen else None
        self.execution_dialog.resize(min(900,available.width()) if available else 900,min(650,available.height()) if available else 650)
        execution_dialog_layout=QVBoxLayout(self.execution_dialog);self.execution_dialog_tabs=QTabWidget();execution_dialog_layout.addWidget(self.execution_dialog_tabs)
        self.execution_dialog_scroll=QScrollArea();self.execution_dialog_scroll.setWidgetResizable(True);self.execution_dialog_scroll.setFrameShape(QScrollArea.Shape.NoFrame);self.execution_dialog_tabs.addTab(self.execution_dialog_scroll,"Preparar")
        self.execution_dialog.finished.connect(self._restore_execution_page)
        self.component_nav.currentChanged.connect(self._component_selected)
        self._refresh_component_states();layout.addWidget(self.simulation_strip)
        self._build_four_stroke_shell(shell)
        self.stack=self.component_stack
        self.nav=self.component_nav
        self.nav.setCurrentIndex(8)
        self.statusBar().showMessage('Listo')
        self.toolbar=QToolBar('Proyecto',self);self.toolbar.setMovable(False);self.addToolBar(self.toolbar)
    def _build_four_stroke_shell(self,shell):
        self.four_stroke_context=FourStrokeContext()
        self.four_stroke_workspace=FourStrokeWorkspace(self.four_stroke_context)
        self.four_stroke_results=FourStrokeResultsPage()
        self.four_stroke_execution=FourStrokeExecution(self.four_stroke_context,self)
        page=QWidget();page.setObjectName("fourStrokeShell")
        layout=QVBoxLayout(page);layout.setContentsMargins(12,8,12,8);layout.setSpacing(8)
        top=QHBoxLayout()
        self.four_stroke_indicator=QLabel("MODO 4T 0D · REFERENCIA SINTÉTICA · NOT_VALIDATED")
        self.four_stroke_indicator.setObjectName("fourStrokeModeIndicator")
        top.addWidget(self.four_stroke_indicator)
        self.four_stroke_dirty=QLabel()
        top.addWidget(self.four_stroke_dirty)
        top.addStretch(1)
        for text,callback in (("Volver a 2T",self.show_two_stroke_mode),
                              ("Nuevo 4T…",self.new_four_stroke_file),
                              ("Abrir 4T…",self.open_four_stroke_file),
                              ("Guardar 4T",self.save_four_stroke_file)):
            button=QPushButton(text);button.clicked.connect(callback);top.addWidget(button)
        layout.addLayout(top)
        run_row=QHBoxLayout()
        self.four_stroke_run_button=QPushButton("Ejecutar 4T")
        self.four_stroke_run_button.setObjectName("fourStrokeRun")
        self.four_stroke_run_button.clicked.connect(self.start_four_stroke_run)
        self.four_stroke_cancel_button=QPushButton("Cancelar 4T")
        self.four_stroke_cancel_button.setEnabled(False)
        self.four_stroke_cancel_button.clicked.connect(lambda *_: self.four_stroke_execution.cancel())
        self.four_stroke_progress=QProgressBar();self.four_stroke_progress.setRange(0,0)
        self.four_stroke_progress.setVisible(False);self.four_stroke_progress.setMaximumWidth(220)
        self.four_stroke_status=QLabel("4T listo · sin corrida activa")
        self.four_stroke_status.setWordWrap(True)
        run_row.addWidget(self.four_stroke_run_button);run_row.addWidget(self.four_stroke_cancel_button)
        run_row.addWidget(self.four_stroke_progress);run_row.addWidget(self.four_stroke_status,1)
        layout.addLayout(run_row)
        self.four_stroke_tabs=QTabWidget()
        self.four_stroke_tabs.addTab(self.four_stroke_workspace,"Diseño 4T")
        self.four_stroke_tabs.addTab(self.four_stroke_results,"Resultados 4T")
        layout.addWidget(self.four_stroke_tabs,1)
        self.four_stroke_context.changed.connect(self._four_stroke_state_changed)
        self.four_stroke_execution.started.connect(self._four_stroke_started)
        self.four_stroke_execution.progress.connect(self._four_stroke_progress)
        self.four_stroke_execution.finished.connect(self._four_stroke_finished)
        self.four_stroke_execution.failed.connect(self._four_stroke_failed)
        self.project_mode_stack=QStackedWidget()
        self.project_mode_stack.addWidget(shell)
        self.project_mode_stack.addWidget(page)
        self.setCentralWidget(self.project_mode_stack)
    def _four_stroke_active(self):
        return hasattr(self,"project_mode_stack") and self.project_mode_stack.currentIndex()==1
    def show_four_stroke_mode(self,*_):
        self.project_mode_stack.setCurrentIndex(1)
        self._four_stroke_state_changed()
        self.statusBar().showMessage("Modo 4T 0D de referencia · SYNTHETIC_REFERENCE_0D · NOT_VALIDATED",6000)
    def show_two_stroke_mode(self,*_):
        self.project_mode_stack.setCurrentIndex(0)
        self._state_changed()
    def _four_stroke_state_changed(self,*_):
        if not hasattr(self,"four_stroke_context"):return
        mark=' · cambios sin guardar' if self.four_stroke_context.dirty else ''
        self.four_stroke_dirty.setText(mark)
        if self._four_stroke_active():
            self.setWindowTitle(f"Dino 4T 0D — {self.four_stroke_context.name}{mark}")
    def _confirm_discard_four_stroke(self):
        if not self.four_stroke_context.dirty:return True
        result=QMessageBox.question(self,'Cambios 4T pendientes','¿Guardar los cambios del proyecto 4T antes de continuar?',QMessageBox.StandardButton.Save|QMessageBox.StandardButton.Discard|QMessageBox.StandardButton.Cancel,QMessageBox.StandardButton.Save)
        if result==QMessageBox.StandardButton.Cancel:return False
        if result==QMessageBox.StandardButton.Save:return self.save_four_stroke_file()
        return True
    def new_four_stroke_file(self):
        if not self._confirm_discard_four_stroke():return
        self.four_stroke_context.new_project()
        self.four_stroke_results.clear_result()
        self.show_four_stroke_mode()
        self.statusBar().showMessage('Proyecto 4T nuevo · referencia sintética sin validación experimental',6000)
    def open_four_stroke_file(self):
        if not self._confirm_discard_four_stroke():return
        path,_=QFileDialog.getOpenFileName(self,'Abrir proyecto 4T',str(Path.home()),'Dino 4T 0D (*.dino4t.json *.json)')
        if not path:return
        try:
            self.four_stroke_context.open(path)
            self.four_stroke_results.clear_result()
            self.show_four_stroke_mode()
            self.statusBar().showMessage(f"Proyecto 4T {self.four_stroke_context.name} abierto",4000)
        except Exception as exc:QMessageBox.warning(self,'No se pudo abrir el proyecto 4T',f'{type(exc).__name__}: {exc}')
    def save_four_stroke_file(self):
        if self.four_stroke_context.path is None:return self.save_four_stroke_as()
        try:
            target=self.four_stroke_context.save()
            self.statusBar().showMessage(f'Proyecto 4T guardado en {target}',4000)
            return True
        except Exception as exc:QMessageBox.warning(self,'No se pudo guardar el proyecto 4T',f'{type(exc).__name__}: {exc}');return False
    def save_four_stroke_as(self):
        path,_=QFileDialog.getSaveFileName(self,'Guardar proyecto 4T como',str(Path.home()/'nuevo.dino4t.json'),'Dino 4T 0D (*.dino4t.json)')
        if not path:return False
        target=Path(path)
        if target.suffix.lower()!='.json':target=Path(str(target)+'.dino4t.json')
        try:
            target=self.four_stroke_context.save(target)
            self.statusBar().showMessage(f'Proyecto 4T guardado en {target}',4000)
            return True
        except Exception as exc:QMessageBox.warning(self,'No se pudo guardar el proyecto 4T',f'{type(exc).__name__}: {exc}');return False
    def start_four_stroke_run(self):
        for page in (self.four_stroke_workspace.geometry,self.four_stroke_workspace.valves,self.four_stroke_workspace.ducts):
            if not page.apply():
                self.four_stroke_tabs.setCurrentWidget(self.four_stroke_workspace)
                self.four_stroke_workspace.tabs.setCurrentWidget(page)
                self.four_stroke_status.setText('Corregí los campos 4T antes de ejecutar.')
                return
        try:
            self.four_stroke_execution.start()
        except Exception as exc:
            self.four_stroke_status.setText(f'No se pudo iniciar la corrida 4T: {exc}')
    def _four_stroke_started(self,output):
        self.four_stroke_run_button.setEnabled(False);self.four_stroke_cancel_button.setEnabled(True)
        self.four_stroke_progress.setVisible(True);self.four_stroke_status.setText(f'Ejecutando 4T · {output}')
    def _four_stroke_progress(self,event):
        cycle=event.get('cycle');angle=event.get('angle_deg')
        if cycle is None:self.four_stroke_status.setText('Ejecutando 4T…')
        else:
            try:angle_text=f"{float(angle):.0f}°"
            except (TypeError,ValueError):angle_text='—'
            self.four_stroke_status.setText(f'Ejecutando 4T · ciclo {cycle} · {angle_text}')
    def _four_stroke_finished(self,result):
        self.four_stroke_run_button.setEnabled(True);self.four_stroke_cancel_button.setEnabled(False)
        self.four_stroke_progress.setVisible(False)
        if result.get('cancelled'):
            self.four_stroke_status.setText('Corrida 4T cancelada; se conserva el último checkpoint completo.')
            return
        if result.get('error'):
            self.four_stroke_status.setText(f"La corrida 4T falló: {result['error']}")
            return
        manifest=result.get('manifest')
        if manifest and self.four_stroke_results.load_manifest(manifest):
            self.four_stroke_tabs.setCurrentWidget(self.four_stroke_results)
            self.four_stroke_status.setText(f"4T terminado ({result.get('status') or 'sin estado'}) · resultado de referencia cargado")
        elif manifest:
            self.four_stroke_status.setText('La corrida 4T terminó, pero el manifiesto no se pudo leer.')
        else:
            self.four_stroke_status.setText(f"La corrida 4T terminó sin manifiesto ({result.get('status') or 'sin estado'}).")
    def _four_stroke_failed(self,message):
        self.four_stroke_run_button.setEnabled(True);self.four_stroke_cancel_button.setEnabled(False)
        self.four_stroke_progress.setVisible(False);self.four_stroke_status.setText(f'La corrida 4T falló: {message}')
    def _update_strip(self,*_):
        if not hasattr(self,"pages"):return
        execution=self.pages[3]
        active=execution.task is not None
        self.run_config_summary.setText(f"{execution.rpm.value():g} rpm · {execution.cycles.value()} ciclos · {execution.budget.value():g} s")
        self.strip_cancel.setEnabled(active and execution.cancel_event is not None)
        self.run_state.setText(state_label(execution.status_text) if not active else ("CANCELACIÓN SOLICITADA" if execution.cancel_event and execution.cancel_event.is_set() else "CORRIENDO"))
        self.run_state.setToolTip(execution.status_text)
        if hasattr(self,'resume_action'):self.resume_action.setEnabled(execution.resume.isEnabled() and not active)
        if hasattr(self,'strip_more'):self.strip_more.setEnabled(not active)
        self.run_progress.setVisible(active or execution.progress_latest is not None)
        if active and execution.progress_latest:
            outer=execution.progress_latest;row=outer.get('solver_progress',outer)
            sweep=getattr(execution,'active_sweep_settings',None) or {}
            horizon=sweep.get('max_cycles',execution.cycles.value())
            point_index=outer.get('point_index',1);point_count=outer.get('point_count',1)
            in_cycle='cycle' in row and 'angle_deg' in row
            fraction=(((max(0,int(row['cycle'])-1)*360)+float(row['angle_deg']))/max(1,horizon*360)) if in_cycle else 1.0
            fraction=(point_index-1+fraction)/point_count
            self.run_progress.setValue(max(0,min(100,int(fraction*100))))
            prefix=f"{outer['rpm']:g} RPM · punto {point_index}/{point_count} · " if 'point_index' in outer else ''
            detail=(f"ciclo {row['cycle']}/{horizon} · {row['angle_deg']:.0f}° · {row.get('rss_bytes',0)/1048576:.0f} MiB" if in_cycle else 'resultado guardado')
            self.run_progress.setFormat(prefix+detail)
            if sweep:self.run_config_summary.setText(f"Barrido {sweep['rpms']} RPM · {horizon} ciclos/punto · {sweep['total_budget_seconds']:g} s agregado")
            elapsed=execution.elapsed_timer.elapsed()/1000 if execution.elapsed_timer.isValid() else 0
            remaining=max(0,sweep.get('total_budget_seconds',execution.budget.value())-elapsed)
            self.run_clock.setText(f"{elapsed:.0f} s · quedan {remaining:.0f} s")
            self.checkpoint_state.setText(f"Checkpoint: último cierre de ciclo {max(0,int(row['cycle'])-1)}; el siguiente es conservador." if in_cycle else f"Checkpoint: punto {point_index}/{point_count} guardado.")
        elif not active:
            self.run_progress.setValue(0);self.run_progress.setFormat("Sin actividad")
            self.run_clock.setText("—")
            self.checkpoint_state.setText(f"Checkpoint: {state_label(execution.checkpoint_summary or '—')}")
            self.checkpoint_state.setToolTip(execution.checkpoint_summary or '—')
    def _update_progress(self,row):
        self._update_strip()
    def set_workspace_mode(self,index):
        index=index if index in (0,1,2) else 0
        self.mode_stack.setCurrentIndex(index);self.design_mode.setChecked(index==0);self.analysis_mode.setChecked(index==1);self.simulate_mode.setChecked(index==2)
        self.history_toggle.hide()
        self.settings.setValue("workspace_mode",index)
        if index==1:self.analysis_history.activate()
        if index==0:self._component_selected(max(0,self.component_nav.currentIndex()))
        if index==2:self.analysis_history.activate();self.pages[3].refresh()

    def _resume_project_study(self,reference):
        self.set_workspace_mode(2)
        self.pages[3].resume_design_study(reference)

    def _show_project(self):
        self.set_workspace_mode(0);self.component_nav.setCurrentIndex(5);self.explorer_dock.hide()

    def _toggle_explorer(self):
        visible=not self.explorer_dock.isVisible()
        if visible:self.analysis_history.activate();self.analysis_history.refresh()
        self.explorer_dock.setVisible(visible)
        if visible:
            # Docking can violate child minimums when the central form owns
            # most of the available height. Keep this temporary explorer out
            # of the editor layout at every supported size.
            self.explorer_dock.setFloating(True)
            if self.explorer_dock.isFloating():
                self.explorer_dock.resize(min(self.width()-30,1200),420)
                self.explorer_dock.move(self.x()+15,self.y()+180)
            else:self.resizeDocks([self.explorer_dock],[350],Qt.Orientation.Vertical)

    def _toggle_traceability(self):
        self._update_evidence()
        self.evidence_dock.setVisible(not self.evidence_dock.isVisible())
    def _component_selected(self,index):
        selector_index=self.model_selector.findData(index)
        self.model_selector.blockSignals(True);self.model_selector.setCurrentIndex(selector_index);self.model_selector.blockSignals(False)
        if index in (0,1,3,4,6,7,8,9,10):
            self.component_stack.setCurrentIndex(0)
            self.pages[0].component_tabs.setCurrentIndex({0:0,1:1,3:2,4:3,6:4,7:5,8:6,9:7,10:8}[index])
        elif index==2:self.component_stack.setCurrentIndex(1)
        elif index==5:self.component_stack.setCurrentIndex(2)

    def _show_execution_panel(self):
        self.set_workspace_mode(2)

    def _restore_execution_page(self,*_):
        if self.pages[3].parentWidget() is self.execution_dialog_scroll.viewport():
            self.execution_dialog_scroll.takeWidget();self.execution_scroll.setWidget(self.pages[3])
        index=self.execution_dialog_tabs.indexOf(self.analysis_history)
        if index>=0:
            self.execution_dialog_tabs.removeTab(index);self.analysis_history.setMaximumHeight(190);self.analysis_splitter.addWidget(self.analysis_history)

    def _toggle_history(self):
        visible=not self.analysis_history.isVisible()
        self.analysis_history.setVisible(visible)
        self.history_toggle.setText("Ocultar corridas" if visible else "Mostrar corridas")
    def _run_started(self):
        self.pages[3].status_text="CORRIENDO";self._update_strip()
    def _refresh_component_states(self):
        labels=("Cilindro y culata","Lumbreras y transferencias","Escape","Pérdidas","Combustión","Proyecto","Admisión","Cárter","Resumen","Avanzado","Conductos de transferencia")
        validation=self.pages[0].validation.text().lower()
        valid="no se pudo presentar" not in validation and "rechazada" not in validation
        engine_status=[self.pages[0].component_tabs.tabText(i).lower() for i in range(9)]
        status_by_tab=(engine_status[0],engine_status[1],self.pages[1].edit_state,engine_status[2],engine_status[3],"complete",engine_status[4],engine_status[5],engine_status[6],engine_status[7],engine_status[8])
        for i in range(self.component_nav.count()):
            title=labels[i] if i<len(labels) else PAGES[i][0]
            state=status_by_tab[i] if i<len(status_by_tab) else "complete"
            invalid=(not valid) or "rechazada" in state or state=="invalid"
            modified=("modificado" in state) or state=="modified" or (self.context.dirty and i==self.component_nav.currentIndex())
            state="Revisar" if invalid else ("Editado" if modified else "Listo")
            self.component_nav.setTabText(i,f"{state} · {title}")
            self.model_selector.setItemText(self.model_selector.findData(i),f'{state} · {title}')
            self.component_nav.setTabToolTip(i,"Error o configuración no válida" if invalid else ("Cambios pendientes de aplicar" if modified else "Configuración disponible"))
    def _update_evidence(self,*_):
        if not hasattr(self,"evidence_text"):return
        kind=getattr(self.results,"source_kind",None)
        source_labels={"EXPLORATORY":"Corridas EXPLORATORY importadas",
            "HISTORICAL_IMPL2":"Evidencia histórica IMPL2 sintética",
            "LEGACY_HISTORICAL":"Resumen de corrida histórica heredada",
            "IMPORTED_EXTERNAL":"Datos importados externamente"}
        lines=["Proyecto abierto: "+self.context.project["project_id"],
            "Origen del conjunto: "+source_labels.get(kind,"No informado por la fuente"),
            "Archivo de importación: "+(str(self.results.source) if self.results.source else "No hay una ruta de importación única declarada")]
        for row in range(self.results.details.rowCount()):
            key=self.results.details.item(row,0);value=self.results.details.item(row,1)
            if key and value:lines.append(f"{key.text()}: {value.text()}")
        self.evidence_text.setPlainText("\n".join(lines))
    def _start_from_strip(self,execution):
        execution.start_run(resume=False);self._update_strip()
    def _open_indexed_runs(self,paths):
        if self.execution_dialog.isVisible():self.execution_dialog.reject()
        self.explorer_dock.hide()
        self.set_workspace_mode(1);self.pages[4].open_runs(paths)
    def _select_baseline(self,name):
        selector=self.results.baseline_selector;index=selector.findData(name)
        if index>=0:selector.setCurrentIndex(index)
        exhaust=self.pages[1].overlay_selector;overlay_index=exhaust.findData(name)
        if overlay_index>=0:exhaust.setCurrentIndex(overlay_index)
    def _sync_baseline_bar(self):
        if not hasattr(self,"context_bar"):return
        index=self.context_bar.baseline.findData(self.results.baseline_selector.currentData())
        if index>=0 and index!=self.context_bar.baseline.currentIndex():self.context_bar.baseline.setCurrentIndex(index)
    def _artifact_root_changed(self,path):
        self.analysis_history.artifact_root=path;self.analysis_history.refresh()
    def _ensure_safe_artifact_root_for_new_project(self):
        execution=self.pages[3]
        if repository_root_containing(execution.artifact_root) is None:return
        path=execution.use_safe_default_root()
        self.statusBar().showMessage(f"Las nuevas corridas se guardarán en {path}. Los artifacts existentes siguen en su carpeta anterior.",9000)
    def _action(self,label,callback,shortcut=None):
        action=QAction(label,self)
        if shortcut:action.setShortcut(shortcut)
        action.triggered.connect(callback);self.toolbar.addAction(action);return action
    def _build_actions(self):
        menu=self.menuBar().addMenu('Archivo');self.actions={}
        for key,label,shortcut,callback in [('new','Nuevo proyecto',QKeySequence.StandardKey.New,self.new_file),('open','Abrir…',QKeySequence.StandardKey.Open,self.open_file),('save','Guardar',QKeySequence.StandardKey.Save,self.save_file),('save_as','Guardar como…',QKeySequence.StandardKey.SaveAs,self.save_as)]:
            action=QAction(label,self);action.setShortcut(shortcut);action.triggered.connect(callback);menu.addAction(action);self.actions[key]=action
            if key=='open':menu.addSeparator()
        menu.addSeparator();imp=menu.addAction('Importar configuración…',self.import_configuration);exp=menu.addAction('Exportar configuración…',self.export_configuration)
        menu.addSeparator()
        for label,callback in (('Nuevo 4T 0D…',self.new_four_stroke_file),('Abrir 4T 0D…',self.open_four_stroke_file),('Guardar 4T 0D…',self.save_four_stroke_file)):
            menu.addAction(label,callback)
        self._action('Nuevo',self.new_file);self._action('Abrir',self.open_file);self._action('Guardar',self.save_file,QKeySequence.StandardKey.Save)
        self._action('Guardar como',self.save_as)
        view=self.menuBar().addMenu('Vista');toggle=view.addAction('Evidencia y provenance');toggle.setCheckable(True);toggle.toggled.connect(self.evidence_dock.setVisible)
        self.evidence_dock.visibilityChanged.connect(toggle.setChecked)
    def _state_changed(self):
        mark=' • Cambios sin guardar' if self.context.dirty else ''
        if not self._four_stroke_active():
            self.setWindowTitle(f"Dino 2T — {self.context.project['project_id']}{mark}")
        if hasattr(self,"context_bar"):
            self._refresh_project_tree()
            self.context_bar.set_context(self.context.project,self.context.selected_variant,self.context.dirty)
            engine=self.context.engine()
            selected=self.context.selected_variant
            self.inspector_variant.setText(selected if selected is not None else engine.get("display_name","Motor base"))
            if selected is None:
                self.inspector_diff.setText("Motor base del proyecto")
            else:
                from ..engine_variants import compare_configurations
                changes=compare_configurations(self.context.project["base_engine"],engine)
                self.inspector_diff.setText(f"Difiere del motor base en {len(changes)} propiedades.")
            self.inspector_validity.setText("Configuración cargada · el preflight completo se muestra en Simular.")
            self.settings.setValue(f"active_variant/{self.context.project['project_id']}",selected or "")
            if hasattr(self,"component_nav"):self._refresh_component_states()

    def _refresh_project_tree(self):
        tree=self.project_tree;tree.blockSignals(True);tree.clear()
        project=QTreeWidgetItem([self.context.project["project_id"]]);project.setData(0,Qt.ItemDataRole.UserRole,"project");tree.addTopLevelItem(project)
        base=QTreeWidgetItem([self.context.project["base_engine"].get("display_name","Motor base")]);base.setData(0,Qt.ItemDataRole.UserRole,None);project.addChild(base)
        for name in sorted(self.context.project["variants"]):
            item=QTreeWidgetItem([name]);item.setData(0,Qt.ItemDataRole.UserRole,name);project.addChild(item)
        project.setExpanded(True)
        selected=self.context.selected_variant
        for i in range(project.childCount()):
            child=project.child(i)
            if child.data(0,Qt.ItemDataRole.UserRole)==selected:tree.setCurrentItem(child);break
        tree.blockSignals(False)

    def _project_tree_clicked(self,item,_column):
        if item.data(0,Qt.ItemDataRole.UserRole)!="project":
            self.context.select_variant(item.data(0,Qt.ItemDataRole.UserRole))

    def _variant_changed(self,_name):
        self._state_changed()
    def resizeEvent(self,event):
        super().resizeEvent(event)
        if hasattr(self,"component_nav"):
            compact=self.width()<=1120
            self.menuBar().setVisible(True)
            if hasattr(self,"pages"):
                self.pages[1].set_compact_layout(compact, self.width()<=1000)
                self.results.set_compact_layout(compact)
            if compact:
                self.checkpoint_state.hide();self.run_progress.setMaximumWidth(110);self.run_clock.setMinimumWidth(48)
                self.run_config_summary.hide();self.prepare_button.hide();self.strip_run.setMinimumWidth(120)
            else:
                self.checkpoint_state.show();self.run_progress.setMaximumWidth(220)
                self.run_config_summary.show();self.prepare_button.show();self.strip_run.setMinimumWidth(150)
            if hasattr(self,"history_toggle"):self.history_toggle.hide()
            self._refresh_component_states()
    def _restore_settings(self):
        geometry=self.settings.value('window_geometry')
        if geometry:self.restoreGeometry(geometry)
    def _confirm_discard(self):
        if not self.context.dirty:return True
        result=QMessageBox.question(self,'Cambios pendientes','¿Guardar los cambios del proyecto antes de continuar?',QMessageBox.StandardButton.Save|QMessageBox.StandardButton.Discard|QMessageBox.StandardButton.Cancel,QMessageBox.StandardButton.Save)
        if result==QMessageBox.StandardButton.Cancel:return False
        if result==QMessageBox.StandardButton.Save:return self.save_file()
        return True
    def new_file(self):
        if not self._confirm_discard():return
        dialog=NewEngineDialog(self)
        if dialog.exec()!=QDialog.DialogCode.Accepted or dialog.project is None:return
        if dialog.project.get("engine_family")=="4T":
            self._launch_four_stroke(dialog.project,None);return
        self.context.replace_project(dialog.project,None);self._ensure_safe_artifact_root_for_new_project();self.statusBar().showMessage('Diseño nuevo creado · valores de plantilla identificados como supuestos',6000)
    def _launch_four_stroke(self,project,path):
        from .four_stroke_desktop import FourStrokeDesktopWindow
        window=FourStrokeDesktopWindow(project,parent_2t=self,path=path);self._four_stroke_window=window
        window.show();self.hide()
    def open_file(self):
        if not self._confirm_discard():return
        path,_=QFileDialog.getOpenFileName(self,'Abrir proyecto',str(Path.home()),'Dino 2T (*.dino2t.json *.json)')
        if not path:return
        self._open(Path(path))
    def _open(self,path):
        try:
            project=load_project(path)
            if project.get("engine_family")=="4T":
                self._launch_four_stroke(project,path);return
            self.context.replace_project(project,path)
            saved_variant=self.settings.value(f"active_variant/{project['project_id']}")
            if saved_variant in project["variants"]:self.context.select_variant(saved_variant)
            self.statusBar().showMessage(f"Proyecto {project['project_id']} abierto",4000)
        except Exception as exc:QMessageBox.warning(self,'No se pudo abrir el proyecto',f'{type(exc).__name__}: {exc}')
    def save_file(self):
        if self.context.path is None:return self.save_as()
        try:save_project(self.context.path,self.context.project);self.context.dirty=False;self.context.changed.emit();self.statusBar().showMessage('Proyecto guardado',3500);return True
        except Exception as exc:QMessageBox.warning(self,'No se pudo guardar',f'{type(exc).__name__}: {exc}');return False
    def save_as(self):
        path,_=QFileDialog.getSaveFileName(self,'Guardar proyecto como',str(Path.home()/'nuevo.dino2t.json'),'Dino 2T (*.dino2t.json)')
        if not path:return False
        target=Path(path)
        if target.suffix.lower()!='.json':target=Path(str(target)+'.dino2t.json')
        try:save_project(target,self.context.project);self.context.path=target;self.context.dirty=False;self.context.changed.emit();self.statusBar().showMessage('Proyecto guardado',3500);return True
        except Exception as exc:QMessageBox.warning(self,'No se pudo guardar',f'{type(exc).__name__}: {exc}');return False
    def import_configuration(self):
        path,_=QFileDialog.getOpenFileName(self,'Importar configuración de motor',str(Path.home()),'Engine configuration (*.json)')
        if not path:return
        try:doc=json.loads(Path(path).read_text(encoding='utf-8'));validate(doc);self.context.replace_engine(doc)
        except Exception as exc:QMessageBox.warning(self,'Configuración inválida',f'{type(exc).__name__}: {exc}')
    def export_configuration(self):
        path,_=QFileDialog.getSaveFileName(self,'Exportar configuración de motor',str(Path.home()/'engine-config.json'),'JSON (*.json)')
        if not path:return
        target=Path(path);tmp=None
        try:
            target.parent.mkdir(parents=True,exist_ok=True)
            fd,name=tempfile.mkstemp(prefix=target.name+'.',suffix='.tmp',dir=target.parent);tmp=Path(name)
            with os.fdopen(fd,'w',encoding='utf-8',newline='\n') as stream:
                stream.write(json.dumps(self.context.engine(),indent=2,ensure_ascii=False,allow_nan=False)+'\n');stream.flush();os.fsync(stream.fileno())
            os.replace(tmp,target)
        except (OSError,ValueError) as exc:QMessageBox.warning(self,'No se pudo exportar',str(exc))
        finally:
            if tmp is not None:
                try:tmp.unlink(missing_ok=True)
                except OSError:pass
    def closeEvent(self,event):
        if not self._confirm_discard():event.ignore();return
        if hasattr(self,"four_stroke_context") and self.four_stroke_context.dirty and not self._confirm_discard_four_stroke():event.ignore();return
        if hasattr(self,"four_stroke_execution") and self.four_stroke_execution.running:
            self.four_stroke_execution.cancel()
        execution=self.pages[3]
        if getattr(execution,"task",None) is not None:
            # Closing the application is an explicit stop request; the engine
            # persists only its last complete-cycle checkpoint before exit.
            execution.cancel_run()
        # Results imports are read-only, but allow their worker callbacks to finish
        # before Qt destroys the widgets they target.
        if not QThreadPool.globalInstance().waitForDone(10000):
            self.statusBar().showMessage('Una lectura sigue activa; cierre cancelado para conservar la interfaz estable.')
            event.ignore();return
        self.settings.setValue('window_geometry',self.saveGeometry());self.settings.setValue('last_page',self.component_nav.currentIndex())
        super().closeEvent(event)
    def showEvent(self,event):
        super().showEvent(event)
        QTimer.singleShot(0,self._fit_initial_window)
    def _fit_initial_window(self):
        screen=QApplication.primaryScreen()
        if screen and QGuiApplication.platformName()=="windows" and not self.isMaximized():
            available=screen.availableGeometry();frame=self.frameGeometry()
            if frame.width()>available.width() or frame.height()>available.height():
                self.showMaximized()
