from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import threading
import uuid
from datetime import datetime,timezone

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QPlainTextEdit, QFileDialog, QMessageBox, QDoubleSpinBox, QSpinBox, QLineEdit,
    QFormLayout, QGroupBox, QComboBox)

from ..engine_configuration import identity
from ..exploratory_workflow import preflight, run_exploratory
from .services import run_background
from .preferences import artifact_root, set_artifact_root


class ExecutionPage(QWidget):
    """Single-point EXPLORATORY controls; VERIFIED remains unavailable."""
    progress_signal=Signal(object)
    open_runs_requested=Signal(object)
    resume_run_requested=Signal(object)
    def __init__(self, context):
        super().__init__(); self.context=context; self.task=None; self.cancel_event=None
        self.artifact_root=artifact_root()
        root=QVBoxLayout(self); root.setContentsMargins(24,20,24,20)
        title=QLabel("Simulación local"); title.setObjectName("title"); root.addWidget(title)
        notice=QLabel("EXPLORATORY produce evidencia provisional, sin claim de validación. VERIFIED permanece bloqueado hasta contar con contrato, preregistro y autorización coincidentes. No se ejecutan campañas históricas.")
        notice.setWordWrap(True); notice.setObjectName("notice"); root.addWidget(notice)
        box=QGroupBox("Configuración y presupuesto"); form=QFormLayout(box); root.addWidget(box)
        self.engine_label=QLabel(); self.engine_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        form.addRow("Motor / variante",self.engine_label)
        self.rpm=QDoubleSpinBox(); self.rpm.setRange(100,10000); self.rpm.setDecimals(3); self.rpm.setValue(3000); self.rpm.setSuffix(" RPM")
        form.addRow("RPM",self.rpm)
        self.cycles=QSpinBox(); self.cycles.setRange(1,111); self.cycles.setValue(1); form.addRow("Horizonte (máx. 111 ciclos)",self.cycles)
        self.preset=QComboBox();self.preset.addItem("Diagnóstico breve · 1 ciclo",1)
        self.preset.addItem("Observar periodicidad · 24 ciclos",24)
        self.preset.addItem("Configuración avanzada · elegir horizonte",-1)
        form.addRow("Preset de horizonte",self.preset)
        self.expected=QLabel();self.expected.setWordWrap(True);form.addRow("Resultados esperables",self.expected)
        self.budget=QDoubleSpinBox(); self.budget.setRange(1,600); self.budget.setDecimals(0); self.budget.setValue(60); self.budget.setSuffix(" s")
        form.addRow("Presupuesto de tiempo",self.budget)
        self.memory=QSpinBox(); self.memory.setRange(256,4096); self.memory.setValue(1024); self.memory.setSuffix(" MiB · RSS máximo supervisado")
        form.addRow("Memoria",self.memory)
        self.mode=QLabel("EXPLORATORY · 1 worker · pipeline convencional + auditoría independiente")
        form.addRow("Modo",self.mode)
        root_row=QHBoxLayout(); root.addLayout(root_row)
        self.root_label=QLabel(str(self.artifact_root)); self.root_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.root_label.setWordWrap(True); root_row.addWidget(self.root_label,1)
        choose=QPushButton("Elegir artifact root…"); choose.clicked.connect(self.choose_root); root_row.addWidget(choose)
        runrow=QHBoxLayout(); root.addLayout(runrow)
        self.run_id=QLineEdit(); self.run_id.setPlaceholderText("Se genera un identificador para una ejecución nueva; para resume, pegar el existente")
        runrow.addWidget(QLabel("Run ID")); runrow.addWidget(self.run_id,1)
        actions=QHBoxLayout(); root.addLayout(actions)
        self.preflight_label=QLabel(); self.preflight_label.setWordWrap(True); actions.addWidget(self.preflight_label,1)
        self.start=QPushButton("Simular…"); self.start.setObjectName("primaryAction"); self.start.clicked.connect(lambda: self.start_run(resume=False)); actions.addWidget(self.start)
        self.resume=QPushButton("Reanudar…"); self.resume.clicked.connect(lambda: self.start_run(resume=True)); actions.addWidget(self.resume)
        self.cancel=QPushButton("Cancelar"); self.cancel.setEnabled(False); self.cancel.clicked.connect(self.cancel_run); actions.addWidget(self.cancel)
        self.request=QPushButton("Guardar solicitud de revisión…"); self.request.clicked.connect(self.save_request); actions.addWidget(self.request)
        self.output=QPlainTextEdit(); self.output.setReadOnly(True); root.addWidget(self.output,1)
        from .widgets.run_history import RunHistoryWidget
        self.history=RunHistoryWidget(self.context,self.artifact_root)
        self.history.open_runs.connect(self.open_runs_requested.emit)
        self.history.resume_run.connect(self.resume_from_entry)
        self.history.setMinimumHeight(210);self.history.setMaximumHeight(340);root.addWidget(self.history)
        self.context.changed.connect(self.refresh)
        self.progress_signal.connect(self._progress)
        self.rpm.valueChanged.connect(self.refresh); self.cycles.valueChanged.connect(self.refresh)
        self.preset.currentIndexChanged.connect(self._apply_preset)
        self.budget.valueChanged.connect(self.refresh); self.memory.valueChanged.connect(self.refresh)
        self.run_id.textChanged.connect(self.refresh)
        self.refresh()

    def _apply_preset(self,index):
        value=self.preset.itemData(index)
        if value and value>0:
            self.cycles.blockSignals(True);self.cycles.setValue(value);self.cycles.blockSignals(False)
        self.refresh()

    def _engine(self): return self.context.engine()

    def _preflight(self):
        return preflight(self._engine(),rpm=self.rpm.value(),max_cycles=self.cycles.value(),
                         budget_seconds=self.budget.value(),memory_limit_mib=self.memory.value())

    def refresh(self,*_):
        try:
            engine=self._engine(); self.engine_label.setText(f"{engine['display_name']} · identity {identity(engine)[:16]}…")
            check=self._preflight()
            self.preflight_label.setText(f"Preflight PASS · {check['rpm']:g} RPM · 0 pasos · {check['total_finite_volume_cells']} celdas · pérdidas explícitas · fuel {check['fuel_id']} · AFR {check['afr_kg_air_per_kg_fuel']:g}")
            self.expected.setText("Se guardarán primarias por ciclo para auditar presión y flujos. Un solo ciclo no permite potencia o torque periódicos admisibles. Un horizonte mayor sólo permite observar el detector; no garantiza periodicidad ni convergencia. Las magnitudes no identificables permanecerán sin valor.")
            self.start.setEnabled(self.task is None)
            candidate=self.artifact_root/'exploratory-workflow-v1'/self.context.project['project_id']/self.run_id.text().strip()
            resumable=(bool(self.run_id.text().strip()) and (candidate/'run.json').is_file() and (candidate/'checkpoint.json').is_file())
            self.resume.setEnabled(self.task is None and resumable)
        except Exception as exc:
            self.preflight_label.setText(f"Preflight FAIL-CLOSED: {type(exc).__name__}: {exc}")
            self.start.setEnabled(False); self.resume.setEnabled(False)

    def choose_root(self):
        path=QFileDialog.getExistingDirectory(self,"Artifact root de ejecuciones locales",str(self.artifact_root))
        if path:
            self.artifact_root=set_artifact_root(path);self.root_label.setText(path)
            self.history.artifact_root=self.artifact_root;self.history.refresh();self.refresh()

    def resume_from_entry(self,entry):
        """Populate the existing guarded resume path from a read-only index row."""
        if self.task is not None:return
        try:
            matches=[]
            for name,engine in [(None,self.context.project["base_engine"]),*self.context.project["variants"].items()]:
                if identity(engine)==entry.get("identity_sha256"):matches.append(name)
            if len(matches)!=1:
                raise ValueError("No hay una única variante del proyecto con la identidad exacta del checkpoint.")
            self.context.select_variant(matches[0])
            from pathlib import Path
            self.artifact_root=Path(entry["artifact_root"])
            self.root_label.setText(str(self.artifact_root));set_artifact_root(self.artifact_root)
            self.run_id.setText(str(entry["run_id"]))
            if entry.get("rpm") is not None:self.rpm.setValue(float(entry["rpm"]))
            cycles=entry.get("details",{}).get("cycles_requested")
            if cycles is not None:self.cycles.setValue(int(cycles))
            self.history.artifact_root=self.artifact_root;self.history.refresh()
            self.start_run(resume=True)
        except Exception as exc:
            QMessageBox.warning(self,"No se puede reanudar este checkpoint",f"FAIL-CLOSED: {type(exc).__name__}: {exc}")

    def save_request(self):
        target,_=QFileDialog.getSaveFileName(self,"Guardar solicitud","dino-execution-request.json","JSON (*.json)")
        if not target:return
        engine=self._engine()
        doc={"schema":"DINO_EXPLORATORY_EXECUTION_REQUEST_V1",
            "created_at":datetime.now(timezone.utc).isoformat(),
            "project_id":self.context.project["project_id"],
            "variant":self.context.selected_variant or "base",
            "configuration_identity_sha256":identity(engine),
            "selected_rpm":self.rpm.value(),"requested_max_cycles":self.cycles.value(),
            "budget_seconds":self.budget.value(),"memory_limit_mib":self.memory.value(),
            "mode":"EXPLORATORY","preregistration_match":False,
            "authorization_match":False,"execution_started":False,
            "verified_mode":"UNAVAILABLE",
            "required_next_steps":["review this local exploratory configuration",
                "a separate explicit in-app confirmation is required for any EXPLORATORY run",
                "VERIFIED requires a matching contract, preregistration and owner authorization"]}
        path=Path(target);temp=None
        try:
            path.parent.mkdir(parents=True,exist_ok=True)
            fd,name=tempfile.mkstemp(prefix=path.name+".",suffix=".tmp",dir=path.parent);temp=Path(name)
            with os.fdopen(fd,"w",encoding="utf-8",newline="\n") as stream:
                stream.write(json.dumps(doc,indent=2,ensure_ascii=False,allow_nan=False)+"\n");stream.flush();os.fsync(stream.fileno())
            os.replace(temp,path)
        except OSError as exc:
            QMessageBox.warning(self,"No se pudo guardar la solicitud",str(exc));return
        finally:
            if temp is not None:
                try:temp.unlink(missing_ok=True)
                except OSError:pass
        QMessageBox.information(self,"Solicitud guardada","La solicitud no inició ninguna ejecución.")

    def _confirmation_text(self, run_id, resume):
        check=self._preflight()
        return (f"{'Reanudar' if resume else 'Iniciar'} una simulación EXPLORATORY local?\n\n"
            f"Proyecto: {self.context.project['project_id']}\nMotor: {self._engine()['display_name']}\n"
            f"RPM: {check['rpm']:g}\nHorizonte máximo: {check['max_cycles']} ciclos\n"
            f"Presupuesto: {check['budget_seconds']:g} s · memoria RSS supervisada: {check['memory_limit_mib']} MiB · workers: 1\n"
            f"Artifact máximo: {check['artifact_limit_bytes']//1048576} MiB · celdas finitas: {check['total_finite_volume_cells']}\n"
            f"Artifact root: {self.artifact_root}\nRun ID: {run_id}\n\n"
            "Los resultados serán provisionales, con periodicidad aún no evaluada hasta cumplir el detector. No se usará autorización IMPL2 ni el runner de campañas.")

    def start_run(self, *, resume):
        if self.task is not None:return
        run_id=self.run_id.text().strip()
        if not resume:
            run_id=run_id or uuid.uuid4().hex
            self.run_id.setText(run_id)
        try:
            self._preflight()
            from ..exploratory_workflow import _run_directory
            _run_directory(self.artifact_root,self.context.project['project_id'],run_id)
        except Exception as exc:
            QMessageBox.warning(self,"Preflight bloqueado",str(exc));return
        if QMessageBox.question(self,"Confirmación de ejecución",self._confirmation_text(run_id,resume),
            QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No)!=QMessageBox.StandardButton.Yes:return
        document=json.loads(json.dumps(self._engine(),allow_nan=False))
        project_id=self.context.project['project_id']; self.cancel_event=threading.Event()
        self.output.appendPlainText(f"{'Resume' if resume else 'Inicio'} autorizado explícitamente · run {run_id}")
        variant_label=self.context.selected_variant or "base"
        self.task=run_background(run_exploratory,document,project_id=project_id,run_id=run_id,
            artifact_root=self.artifact_root,rpm=self.rpm.value(),max_cycles=self.cycles.value(),
            budget_seconds=self.budget.value(),memory_limit_mib=self.memory.value(),resume=resume,
            cancel_event=self.cancel_event,variant_label=variant_label,
            progress=self.progress_signal.emit,on_done=self._done,on_error=self._failed)
        self.cancel.setEnabled(True); self.start.setEnabled(False); self.resume.setEnabled(False)

    def _progress(self,row):
        self.output.appendPlainText(f"Ciclo {row['cycle']} · {row['angle_deg']:.1f}° · RSS {row['rss_bytes']/1048576:.0f} MiB")

    def _done(self,result):
        summary={k:result.get(k) for k in ("status","classification","mode","scientific_validation","cycles_completed","periodicity","failure","elapsed_seconds","artifact_directory","result_sha256")}
        summary["cycles"]=[{"cycle":r["cycle"],"primary_sha256":r["primary_sha256"],"audit_recomputed":r["audit"].get("recomputed"),"conservation":r["conservation"],"metric_statuses":{k:v.get("status") for k,v in r["engineering_output"].get("cycle_metrics",{}).items() if isinstance(v,dict)}} for r in result.get("cycles",[])]
        self.output.appendPlainText(json.dumps(summary,indent=2,ensure_ascii=False))
        self._release_task()

    def _failed(self,message):
        self.output.appendPlainText("FAIL-CLOSED: "+message); self._release_task()

    def _release_task(self):
        self.task=None; self.cancel_event=None; self.cancel.setEnabled(False); self.refresh();self.history.refresh()

    def cancel_run(self):
        if self.cancel_event is not None:
            self.cancel_event.set(); self.output.appendPlainText("Cancelación solicitada; se detendrá en un límite de paso y conservará el último checkpoint completo.")
