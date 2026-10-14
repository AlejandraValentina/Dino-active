from __future__ import annotations
import json
import os
import tempfile
from datetime import datetime,timezone
from pathlib import Path
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QPlainTextEdit,QFileDialog,QMessageBox
from ..engine_configuration import identity

class ExecutionPage(QWidget):
    def __init__(self,context):
        super().__init__();self.context=context;root=QVBoxLayout(self);root.setContentsMargins(24,20,24,20)
        title=QLabel("Simulación y autorización");title.setObjectName('title');root.addWidget(title)
        self.summary=QLabel();self.summary.setWordWrap(True);root.addWidget(self.summary)
        self.output=QPlainTextEdit();self.output.setReadOnly(True);root.addWidget(self.output,1)
        row=QHBoxLayout();root.addLayout(row);self.request=QPushButton("Guardar solicitud de preregistro / ejecución");self.request.setObjectName('primaryAction');self.request.clicked.connect(self.save_request);row.addWidget(self.request)
        self.start=QPushButton("Iniciar supervisor");self.start.setEnabled(False);self.start.setToolTip("Sin autorización y preregistro nuevos para esta configuración.");row.addWidget(self.start);row.addStretch()
        self.context.changed.connect(self.refresh);self.refresh()
    def refresh(self):
        try:
            engine=self.context.engine();sha=identity(engine)
            self.summary.setText(f"Configuración seleccionada: {engine['display_name']}\nIdentity: {sha}\n"
                "Preflight de ejecución: configuración local validable; no consta preregistro para esta identidad.\n"
                "Autorización: ausente para esta variante · Supervisor: bloqueado · Campañas iniciadas por DINO_DESKTOP_V1: 0")
            self.output.setPlainText(json.dumps({"campaign":"FULL_RPM_SWEEP_V1","status":"PARTIAL / REVIEW",
                "registered_points":"No autorizado desde esta configuración local",
                "workers":"Sin ejecución; no se crea ningún proceso",
                "budget":"No asignado a esta configuración",
                "checkpoints":"No se inspeccionan ni reutilizan checkpoints de otra identidad",
                "note":"PERIOD_1 no es PASS científico. Abrí Resultados para consultar la evidencia histórica IMPL2."},indent=2,ensure_ascii=False)
                +"\n\nLa configuración editada puede guardarse como solicitud. El supervisor sólo puede ser habilitado por el runner con preregistro y autorización coincidentes.")
            self.start.setEnabled(False)
        except Exception as exc:self.summary.setText(f"Preflight de visualización falló; supervisor bloqueado: {exc}")
    def save_request(self):
        target,_=QFileDialog.getSaveFileName(self,"Guardar solicitud","dino-execution-request.json","JSON (*.json)")
        if not target:return
        engine=self.context.engine();doc={"schema":"DINO_EXECUTION_REQUEST_V1","created_at":datetime.now(timezone.utc).isoformat(),
          "project_id":self.context.project['project_id'],"configuration_identity_sha256":identity(engine),
          "native_configuration_sha256":engine['native_configuration_sha256'],
          "preregistration_match":False,"authorization_match":False,"execution_started":False,
          "required_next_steps":["create and review a preregistration for this exact configuration identity","obtain explicit owner authorization bound to that preregistration","run existing fail-closed campaign preflight and supervisor"]}
        path=Path(target);tmp=None
        try:
            path.parent.mkdir(parents=True,exist_ok=True)
            fd,name=tempfile.mkstemp(prefix=path.name+'.',suffix='.tmp',dir=path.parent);tmp=Path(name)
            with os.fdopen(fd,'w',encoding='utf-8',newline='\n') as stream:
                stream.write(json.dumps(doc,indent=2,ensure_ascii=False,allow_nan=False)+'\n');stream.flush();os.fsync(stream.fileno())
            os.replace(tmp,path)
        except OSError as exc:
            QMessageBox.warning(self,"No se pudo guardar",str(exc));return
        finally:
            if tmp is not None:
                try:tmp.unlink(missing_ok=True)
                except OSError:pass
        QMessageBox.information(self,"Solicitud guardada","La solicitud no inició ninguna ejecución.")
