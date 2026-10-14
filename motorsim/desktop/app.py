from __future__ import annotations
import json
import os
import tempfile
from pathlib import Path
from PySide6.QtCore import QSettings,Qt,QThreadPool
from PySide6.QtGui import QAction,QKeySequence
from PySide6.QtWidgets import (QMainWindow,QWidget,QHBoxLayout,QVBoxLayout,QListWidget,QListWidgetItem,
    QStackedWidget,QLabel,QToolBar,QFileDialog,QMessageBox,QApplication)
from ..engine_configuration import validate
from ..engine_project import load_project,save_project
from .services import new_project
from .context import DesktopContext
from .engine_page import EnginePage
from .exhaust_page import ExhaustPage
from .project_page import ProjectPage
from .results_page import ResultsPage
from .execution_page import ExecutionPage

PAGES=(('Motor',EnginePage),('Escape',ExhaustPage),('Proyecto',ProjectPage),('Simulación',ExecutionPage),('Resultados',ResultsPage))

class DinoDesktopWindow(QMainWindow):
    def __init__(self,project=None):
        super().__init__();self.settings=QSettings('Dino2T','DinoDesktop');self.context=DesktopContext(project or new_project())
        self.setWindowTitle('Dino 2T');self.resize(1360,900);self.setMinimumSize(980,680)
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
            QListWidget#nav {background:#0c121b;border:0;border-right:1px solid #2b3b4d;padding:10px;}
            QListWidget#nav::item {padding:14px;border-radius:5px;} QListWidget#nav::item:selected {background:#19334a;color:#57c4f5;}
            QLabel#notice {color:#9eb7cf;background:#162332;border:1px solid #263e55;border-radius:5px;padding:9px;}
            QStatusBar {background:#0b1119;color:#9db2c7;}
        """)
        self._build_ui();self._build_actions();self.context.changed.connect(self._state_changed)
        self._restore_settings();self._state_changed()
    def _build_ui(self):
        shell=QWidget();layout=QHBoxLayout(shell);layout.setContentsMargins(0,0,0,0);layout.setSpacing(0)
        self.nav=QListWidget();self.nav.setObjectName('nav');self.nav.setFixedWidth(200)
        for title,_ in PAGES:self.nav.addItem(QListWidgetItem(title))
        self.stack=QStackedWidget();self.pages=[]
        for _,page_type in PAGES:
            page=page_type(self.context);self.pages.append(page);self.stack.addWidget(page)
        layout.addWidget(self.nav);layout.addWidget(self.stack,1);self.setCentralWidget(shell)
        self.nav.currentRowChanged.connect(self.stack.setCurrentIndex)
        last=int(self.settings.value('last_page',0));self.nav.setCurrentRow(max(0,min(last,len(PAGES)-1)))
        self.statusBar().showMessage('Listo')
        self.toolbar=QToolBar('Proyecto',self);self.toolbar.setMovable(False);self.addToolBar(self.toolbar)
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
        self.state=QLabel();self.state.setContentsMargins(14,0,14,0);self.toolbar.addWidget(self.state)
    def _state_changed(self):
        mark=' • Cambios sin guardar' if self.context.dirty else ''
        self.setWindowTitle(f"Dino 2T — {self.context.project['project_id']}{mark}")
        self.state.setText('Modificado' if self.context.dirty else 'Guardado')
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
        self.context.replace_project(new_project(f"dino-{Path.cwd().name.lower()}"),None);self.statusBar().showMessage('Proyecto nuevo basado en fixture sintético',5000)
    def open_file(self):
        if not self._confirm_discard():return
        path,_=QFileDialog.getOpenFileName(self,'Abrir proyecto',str(Path.home()),'Dino 2T (*.dino2t.json *.json)')
        if not path:return
        self._open(Path(path))
    def _open(self,path):
        try:self.context.replace_project(load_project(path),path)
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
        self.settings.setValue('window_geometry',self.saveGeometry());self.settings.setValue('last_page',self.nav.currentRow());super().closeEvent(event)
