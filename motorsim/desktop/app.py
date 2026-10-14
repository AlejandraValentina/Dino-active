from __future__ import annotations
import json
import os
import tempfile
from pathlib import Path
from PySide6.QtCore import QSettings,Qt,QThreadPool,QTimer
from PySide6.QtGui import QAction,QKeySequence,QGuiApplication
from PySide6.QtWidgets import (QMainWindow,QWidget,QHBoxLayout,QVBoxLayout,QListWidget,QListWidgetItem,
    QStackedWidget,QLabel,QToolBar,QFileDialog,QMessageBox,QApplication,QSplitter,QScrollArea,
    QGroupBox,QFormLayout,QTreeWidget,QTreeWidgetItem)
from ..engine_configuration import validate
from ..engine_project import load_project,save_project
from .services import new_project
from .context import DesktopContext
from .engine_page import EnginePage
from .exhaust_page import ExhaustPage
from .project_page import ProjectPage
from .results_page import ResultsPage
from .execution_page import ExecutionPage
from .widgets.context_bar import ContextBar

PAGES=(('Motor',EnginePage),('Escape',ExhaustPage),('Proyecto',ProjectPage),('Simulación',ExecutionPage),('Resultados',ResultsPage))

class DinoDesktopWindow(QMainWindow):
    def __init__(self,project=None):
        super().__init__();self.settings=QSettings('Dino2T','DinoDesktop');self.context=DesktopContext(project or new_project())
        self.setWindowTitle('Dino 2T')
        screen=QApplication.primaryScreen();available=screen.availableGeometry() if screen else None
        width=min(1360,available.width()) if available else 1360
        height=min(900,available.height()) if available else 900
        self.setMinimumSize(min(980,width),min(680,height));self.resize(width,height)
        self.setStyleSheet("""
            QMainWindow,QWidget { background:#101722; color:#e5edf6; font-family:'Segoe UI'; font-size:10pt; }
            QLabel#title {font-size:22pt;font-weight:600;color:#f3f8ff;padding:4px 0;}
            QGroupBox {border:1px solid #2a3b50;border-radius:8px;margin-top:12px;padding:12px 10px 10px;font-weight:600;}
            QGroupBox::title {subcontrol-origin:margin;left:12px;padding:0 5px;color:#91cbed;}
            QPushButton {background:#1b293a;border:1px solid #344b65;border-radius:6px;padding:8px 12px;}
            QPushButton:hover {background:#263a51;} QPushButton:disabled {color:#708296;}
            QPushButton#primaryAction {background:#1479ad;border-color:#219bd7;font-weight:600;}
            QLineEdit,QDoubleSpinBox,QComboBox,QTableWidget,QPlainTextEdit,QListWidget {background:#0c121b;border:1px solid #30435a;border-radius:4px;padding:5px;selection-background-color:#17638c;}
            QHeaderView::section {background:#1a2838;padding:6px;border:0;color:#afc7dd;}
            QListWidget#nav {background:#0c121b;border:0;border-right:1px solid #2b3b4d;padding:8px;}
            QListWidget#nav::item {padding:14px;border-radius:5px;} QListWidget#nav::item:selected {background:#19334a;color:#57c4f5;}
            QLabel#notice {color:#9eb7cf;background:#162332;border:1px solid #263e55;border-radius:5px;padding:9px;}
            QWidget#contextBar {background:#152130;border-bottom:1px solid #31455b;}
            QLabel#modeBadge {background:#4b3514;color:#ffd58a;border:1px solid #76551d;border-radius:8px;padding:4px 9px;font-weight:600;}
            QGroupBox#inspector {border:0;border-left:1px solid #2b3b4d;border-radius:0;margin:0;padding:12px;}
            QStatusBar {background:#0b1119;color:#9db2c7;}
        """)
        saved_variant=self.settings.value(f"active_variant/{self.context.project['project_id']}")
        if saved_variant in self.context.project["variants"]: self.context.select_variant(saved_variant)
        self._build_ui();self._build_actions();self.context.changed.connect(self._state_changed)
        self.context.variant_changed.connect(self._variant_changed)
        self._restore_settings();self._state_changed()
    def _build_ui(self):
        shell=QWidget();layout=QVBoxLayout(shell);layout.setContentsMargins(0,0,0,0);layout.setSpacing(0)
        self.context_bar=ContextBar();self.context_bar.setObjectName("contextBar")
        self.context_bar.variant_selected.connect(self.context.select_variant);layout.addWidget(self.context_bar)
        self.body_splitter=QSplitter(Qt.Orientation.Horizontal);self.body_splitter.setChildrenCollapsible(False)
        self.nav_panel=QWidget();nav_layout=QVBoxLayout(self.nav_panel);nav_layout.setContentsMargins(0,4,4,4);nav_layout.setSpacing(5)
        nav_layout.addWidget(QLabel("Proyecto"))
        self.project_tree=QTreeWidget();self.project_tree.setHeaderHidden(True);self.project_tree.setMaximumHeight(180)
        self.project_tree.itemClicked.connect(self._project_tree_clicked);nav_layout.addWidget(self.project_tree)
        nav_layout.addWidget(QLabel("Vistas"))
        self.nav=QListWidget();self.nav.setObjectName('nav');self.nav.setMinimumWidth(128);self.nav.setMaximumWidth(260)
        for title,_ in PAGES:self.nav.addItem(QListWidgetItem(title))
        nav_layout.addWidget(self.nav,1)
        self.stack=QStackedWidget();self.pages=[]
        for _,page_type in PAGES:
            page=page_type(self.context);self.pages.append(page)
            scroll=QScrollArea();scroll.setWidgetResizable(True);scroll.setFrameShape(QScrollArea.Shape.NoFrame);scroll.setWidget(page)
            self.stack.addWidget(scroll)
        execution=self.pages[3];results=self.pages[4]
        execution.open_runs_requested.connect(self._open_indexed_runs)
        self.inspector=QGroupBox("Preparación y estado");self.inspector.setObjectName("inspector");self.inspector.setMinimumWidth(145);self.inspector.setMaximumWidth(320)
        inspector_layout=QVBoxLayout(self.inspector);inspector_layout.setContentsMargins(12,12,10,12)
        self.inspector_variant=QLabel();self.inspector_variant.setWordWrap(True);self.inspector_variant.setStyleSheet("font-size:12pt;font-weight:600;color:#d8edff")
        self.inspector_diff=QLabel();self.inspector_diff.setWordWrap(True)
        self.inspector_validity=QLabel();self.inspector_validity.setWordWrap(True)
        self.inspector_science=QLabel("Modo EXPLORATORIO. Los diagnósticos de escape no demostraron independencia espacial.");self.inspector_science.setWordWrap(True)
        inspector_layout.addWidget(QLabel("Variante activa"));inspector_layout.addWidget(self.inspector_variant)
        inspector_layout.addWidget(self.inspector_diff);inspector_layout.addWidget(self.inspector_validity);inspector_layout.addStretch(1);inspector_layout.addWidget(self.inspector_science)
        self.body_splitter.addWidget(self.nav_panel);self.body_splitter.addWidget(self.stack);self.body_splitter.addWidget(self.inspector)
        self.body_splitter.setStretchFactor(0,0);self.body_splitter.setStretchFactor(1,1);self.body_splitter.setStretchFactor(2,0)
        self.body_splitter.setSizes([175,930,230]);layout.addWidget(self.body_splitter,1);self.setCentralWidget(shell)
        self.nav.currentRowChanged.connect(self.stack.setCurrentIndex)
        last=int(self.settings.value('last_page',0));self.nav.setCurrentRow(max(0,min(last,len(PAGES)-1)))
        self.statusBar().showMessage('Listo')
        self.toolbar=QToolBar('Proyecto',self);self.toolbar.setMovable(False);self.addToolBar(self.toolbar)
    def _open_indexed_runs(self,paths):
        self.nav.setCurrentRow(4);self.pages[4].open_runs(paths)
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
        self._action('Nuevo',self.new_file);self._action('Abrir',self.open_file);self._action('Guardar',self.save_file,QKeySequence.StandardKey.Save)
        self._action('Guardar como',self.save_as)
    def _state_changed(self):
        mark=' • Cambios sin guardar' if self.context.dirty else ''
        self.setWindowTitle(f"Dino 2T — {self.context.project['project_id']}{mark}")
        if hasattr(self,"context_bar"):
            self._refresh_project_tree()
            self.context_bar.set_context(self.context.project,self.context.selected_variant,self.context.dirty)
            engine=self.context.engine()
            self.inspector_variant.setText(engine.get("display_name","Motor base"))
            selected=self.context.selected_variant
            if selected is None:
                self.inspector_diff.setText("Motor base del proyecto")
            else:
                from ..engine_variants import compare_configurations
                changes=compare_configurations(self.context.project["base_engine"],engine)
                self.inspector_diff.setText(f"Difiere del motor base en {len(changes)} propiedades.")
            self.inspector_validity.setText("Configuración cargada · el preflight completo se muestra en Simular.")
            self.settings.setValue(f"active_variant/{self.context.project['project_id']}",selected or "")

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
        if hasattr(self,"inspector"):
            # Keep the inspector available at desktop widths and reclaim its
            # space below the supported 980 px breakpoint.
            self.inspector.setVisible(event.size().width()>=1120)
    def _restore_settings(self):
        geometry=self.settings.value('window_geometry')
        if geometry:self.restoreGeometry(geometry)
        splitter=self.settings.value('workspace_splitter')
        if splitter:self.body_splitter.restoreState(splitter)
    def _confirm_discard(self):
        if not self.context.dirty:return True
        result=QMessageBox.question(self,'Cambios pendientes','¿Guardar los cambios del proyecto antes de continuar?',QMessageBox.StandardButton.Save|QMessageBox.StandardButton.Discard|QMessageBox.StandardButton.Cancel,QMessageBox.StandardButton.Save)
        if result==QMessageBox.StandardButton.Cancel:return False
        if result==QMessageBox.StandardButton.Save:return self.save_file()
        return True
    def new_file(self):
        if not self._confirm_discard():return
        self.context.replace_project(new_project(f"dino-{Path.cwd().name.lower()}"),None);self.statusBar().showMessage('Proyecto nuevo basado en fixture sintético',5000)
    def open_file(self):
        if not self._confirm_discard():return
        path,_=QFileDialog.getOpenFileName(self,'Abrir proyecto',str(Path.home()),'Dino 2T (*.dino2t.json *.json)')
        if not path:return
        self._open(Path(path))
    def _open(self,path):
        try:
            project=load_project(path);self.context.replace_project(project,path)
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
        self.settings.setValue('window_geometry',self.saveGeometry());self.settings.setValue('last_page',self.nav.currentRow())
        self.settings.setValue('workspace_splitter',self.body_splitter.saveState());super().closeEvent(event)
    def showEvent(self,event):
        super().showEvent(event)
        QTimer.singleShot(0,self._fit_initial_window)
    def _fit_initial_window(self):
        screen=QApplication.primaryScreen()
        if screen and QGuiApplication.platformName()=="windows" and not self.isMaximized():
            available=screen.availableGeometry();frame=self.frameGeometry()
            if frame.width()>available.width() or frame.height()>available.height():
                self.showMaximized()
