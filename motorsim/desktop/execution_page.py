from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import threading
import uuid
from types import SimpleNamespace
from datetime import datetime,timezone

from PySide6.QtCore import Qt, Signal, QElapsedTimer
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QPlainTextEdit, QFileDialog, QMessageBox, QDoubleSpinBox, QSpinBox, QLineEdit,
    QFormLayout, QGroupBox, QComboBox, QDialog, QDialogButtonBox)

from ..engine_configuration import identity
from ..exploratory_workflow import preflight, run_exploratory
from .services import run_background
from .preferences import artifact_root, set_artifact_root, repository_root_containing, default_artifact_root


class ExecutionPage(QWidget):
    """Single-point EXPLORATORY controls; VERIFIED remains unavailable."""
    progress_signal=Signal(object)
    open_runs_requested=Signal(object)
    resume_run_requested=Signal(object)
    state_changed=Signal()
    artifact_root_changed=Signal(object)
    refresh_history_requested=Signal()
    def __init__(self, context):
        super().__init__(); self.context=context; self.task=None; self.cancel_event=None
        self.elapsed_timer=QElapsedTimer();self.progress_latest=None;self.status_text="LISTO · preparado";self.checkpoint_summary=None
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
        self.budget_estimate=QLabel();self.budget_estimate.setWordWrap(True);form.addRow("Estimación orientativa",self.budget_estimate)
        self.apply_budget_estimate=QPushButton("Aplicar presupuesto sugerido (máx. 600 s)");self.apply_budget_estimate.clicked.connect(self._apply_budget_estimate)
        form.addRow("",self.apply_budget_estimate)
        self.memory=QSpinBox(); self.memory.setRange(256,4096); self.memory.setValue(1024); self.memory.setSuffix(" MiB · RSS máximo supervisado")
        self.mode=QLabel("EXPLORATORY · 1 worker · pipeline convencional + auditoría independiente")
        form.addRow("Modo",self.mode)
        self.advanced_toggle=QPushButton("Configuración avanzada ▸");self.advanced_toggle.setCheckable(True);root.addWidget(self.advanced_toggle)
        self.advanced_panel=QWidget();advanced_layout=QVBoxLayout(self.advanced_panel);advanced_layout.setContentsMargins(8,4,8,4)
        advanced_form=QFormLayout();advanced_form.addRow("Límite de memoria",self.memory);advanced_layout.addLayout(advanced_form)
        root_row=QHBoxLayout()
        self.root_label=QLabel(str(self.artifact_root)); self.root_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.root_label.setWordWrap(True); root_row.addWidget(self.root_label,1)
        choose=QPushButton("Elegir artifact root…"); choose.clicked.connect(self.choose_root); root_row.addWidget(choose);advanced_layout.addLayout(root_row)
        self.root_warning=QLabel();self.root_warning.setWordWrap(True);self.root_warning.setObjectName("notice");advanced_layout.addWidget(self.root_warning)
        runrow=QHBoxLayout()
        self.run_id=QLineEdit(); self.run_id.setPlaceholderText("Se genera un identificador para una ejecución nueva; para resume, pegar el existente")
        runrow.addWidget(QLabel("Run ID")); runrow.addWidget(self.run_id,1)
        self.request=QPushButton("Guardar solicitud de revisión…"); self.request.clicked.connect(self.save_request);runrow.addWidget(self.request);advanced_layout.addLayout(runrow)
        self.output=QPlainTextEdit(); self.output.setReadOnly(True);self.output.setMaximumHeight(150);advanced_layout.addWidget(self.output)
        root.addWidget(self.advanced_panel);self.advanced_panel.hide()
        self.advanced_toggle.toggled.connect(self.advanced_panel.setVisible)
        self.advanced_toggle.toggled.connect(lambda checked:self.advanced_toggle.setText("Configuración avanzada ▾" if checked else "Configuración avanzada ▸"))
        actions=QHBoxLayout(); root.addLayout(actions)
        self.preflight_label=QLabel(); self.preflight_label.setWordWrap(True); actions.addWidget(self.preflight_label,1)
        self.start=QPushButton("Simular…"); self.start.setObjectName("primaryAction"); self.start.clicked.connect(lambda: self.start_run(resume=False)); actions.addWidget(self.start)
        self.resume=QPushButton("Reanudar…"); self.resume.clicked.connect(lambda: self.start_run(resume=True)); actions.addWidget(self.resume)
        self.sweep=QPushButton("Curva RPM…");self.sweep.setToolTip("Preflight y barrido exploratorio acotado con el motor integrado")
        self.sweep.clicked.connect(self.start_power_curve);actions.addWidget(self.sweep)
        self.resume_sweep=QPushButton("Reanudar curva…");self.resume_sweep.clicked.connect(self.resume_power_curve);actions.addWidget(self.resume_sweep)
        self.cancel=QPushButton("Cancelar"); self.cancel.setEnabled(False); self.cancel.clicked.connect(self.cancel_run); actions.addWidget(self.cancel)
        self.history=SimpleNamespace(entries=[],artifact_root=self.artifact_root)
        self.context.changed.connect(self.refresh)
        self.progress_signal.connect(self._progress)
        self.rpm.valueChanged.connect(self.refresh); self.cycles.valueChanged.connect(self.refresh)
        self.cycles.valueChanged.connect(self._cycles_changed)
        self.preset.currentIndexChanged.connect(self._apply_preset)
        self.budget.valueChanged.connect(self.refresh); self.memory.valueChanged.connect(self.refresh)
        self.run_id.textChanged.connect(self.refresh)
        self.refresh()

    def _apply_preset(self,index):
        value=self.preset.itemData(index)
        if value and value>0:
            self.cycles.blockSignals(True);self.cycles.setValue(value);self.cycles.blockSignals(False)
        self.refresh()

    def _cycles_changed(self,value):
        preset_index=0 if value==1 else (1 if value==24 else 2)
        if self.preset.currentIndex()!=preset_index:
            self.preset.blockSignals(True);self.preset.setCurrentIndex(preset_index);self.preset.blockSignals(False)
        self.refresh()

    def _cycle_seconds(self,cell_count):
        """Estimate from runs with the same finite-volume cell count; otherwise use fallback."""
        rates=[]
        try:
            for entry in self.history.entries:
                details=entry.get("details",{})
                if details.get("total_finite_volume_cells")==cell_count and details.get("cycles_completed",0)>0 and details.get("elapsed_seconds",0)>0:
                    rates.append(float(details["elapsed_seconds"])/int(details["cycles_completed"]))
        except (AttributeError,TypeError,ValueError):pass
        return (sum(rates)/len(rates),f"estimación basada en {len(rates)} corridas con {cell_count} celdas") if rates else (30.0,"fallback conservador de 30 s/ciclo; aún sin historial comparable")

    def _apply_budget_estimate(self):
        try:
            check=self._preflight();seconds,source=self._cycle_seconds(check["total_finite_volume_cells"])
            suggested=min(600,max(1,int(__import__("math").ceil(self.cycles.value()*seconds*1.2))))
            self.budget.setValue(suggested)
            self.output.appendPlainText(f"Presupuesto sugerido aplicado explícitamente: {suggested} s ({source}).")
        except Exception as exc:
            QMessageBox.warning(self,"No se pudo estimar el presupuesto",str(exc))

    def _engine(self): return self.context.engine()

    def set_history_entries(self,entries):
        self.history.entries=list(entries or [])

    def _preflight(self):
        return preflight(self._engine(),rpm=self.rpm.value(),max_cycles=self.cycles.value(),
                         budget_seconds=self.budget.value(),memory_limit_mib=self.memory.value())

    def refresh(self,*_):
        try:
            engine=self._engine();visible_variant=self.context.selected_variant or "Motor base"
            self.engine_label.setText(visible_variant)
            check=self._preflight()
            repository=repository_root_containing(self.artifact_root)
            unsafe=repository is not None
            self.root_warning.setText((f"Esta raíz está dentro del repositorio ({repository}). Los artifacts existentes se conservan. Elegí una ubicación externa antes de iniciar una corrida nueva." if unsafe else "La raíz de artifacts está fuera del repositorio."))
            self.root_warning.setProperty("unsafeRoot",unsafe)
            self.preflight_label.setText(f"Preflight PASS · {check['rpm']:g} RPM · 0 pasos · {check['total_finite_volume_cells']} celdas · pérdidas explícitas · combustible configurado · AFR {check['afr_kg_air_per_kg_fuel']:g}")
            self.expected.setText("Se guardarán primarias por ciclo para auditar presión y flujos. Un solo ciclo no permite potencia o torque periódicos admisibles. Un horizonte mayor sólo permite observar el detector; no garantiza periodicidad ni convergencia. Las magnitudes no identificables permanecerán sin valor.")
            seconds,source=self._cycle_seconds(check["total_finite_volume_cells"])
            import math
            raw_estimate=max(1,int(math.ceil(self.cycles.value()*seconds*1.2)));estimate=min(600,raw_estimate)
            if self.budget.value()<estimate:
                status=f"Presupuesto actual {self.budget.value():g} s posiblemente insuficiente; sugerencia {estimate} s con tope de 600 s."
            else:status=f"Presupuesto actual {self.budget.value():g} s alcanza la estimación orientativa de hasta {estimate} s; no garantiza terminar."
            if raw_estimate>600:status+=f" El tope no alcanza la estimación sin margen ({raw_estimate} s); no se alteró el horizonte ni el presupuesto."
            self.budget_estimate.setText(f"{self.cycles.value()} ciclos · {status} {source}. Cambiar el preset nunca cambia el presupuesto.")
            self.start.setEnabled(self.task is None and not unsafe)
            self.sweep.setEnabled(self.task is None and not unsafe)
            self.resume_sweep.setEnabled(self.task is None and not unsafe)
            candidate=self.artifact_root/'exploratory-workflow-v1'/self.context.project['project_id']/self.run_id.text().strip()
            resumable=(bool(self.run_id.text().strip()) and (candidate/'run.json').is_file() and (candidate/'checkpoint.json').is_file())
            self.resume.setEnabled(self.task is None and resumable and not unsafe)
        except Exception as exc:
            self.preflight_label.setText(f"Preflight FAIL-CLOSED: {type(exc).__name__}: {exc}")
            self.start.setEnabled(False); self.resume.setEnabled(False);self.sweep.setEnabled(False);self.resume_sweep.setEnabled(False)
        self.state_changed.emit()

    def choose_root(self):
        path=QFileDialog.getExistingDirectory(self,"Artifact root de ejecuciones locales",str(self.artifact_root))
        if path:
            if repository_root_containing(path) is not None:
                QMessageBox.warning(self,"Raíz dentro del repositorio","Elegí una ubicación externa para una corrida nueva. No se modificó la raíz guardada ni se movieron artifacts.");return
            self.artifact_root=set_artifact_root(path);self.root_label.setText(path)
            self.history.artifact_root=self.artifact_root;self.artifact_root_changed.emit(self.artifact_root);self.refresh()

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
            self.root_label.setText(str(self.artifact_root));self.history.artifact_root=self.artifact_root;set_artifact_root(self.artifact_root)
            self.run_id.setText(str(entry["run_id"]))
            if entry.get("rpm") is not None:self.rpm.setValue(float(entry["rpm"]))
            cycles=entry.get("details",{}).get("cycles_requested")
            if cycles is not None:self.cycles.setValue(int(cycles))
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
            f"Proyecto: {self.context.project['project_id']}\nMotor: {self.context.selected_variant or 'Motor base'}\n"
            f"RPM: {check['rpm']:g}\nHorizonte máximo: {check['max_cycles']} ciclos\n"
            f"Presupuesto: {check['budget_seconds']:g} s · memoria RSS supervisada: {check['memory_limit_mib']} MiB · workers: 1\n"
            f"Artifact máximo: {check['artifact_limit_bytes']//1048576} MiB · celdas finitas: {check['total_finite_volume_cells']}\n"
            f"Artifact root: {self.artifact_root}\nRun ID: {run_id}\n\n"
            "Los resultados serán provisionales, con periodicidad aún no evaluada hasta cumplir el detector. No se usará autorización IMPL2 ni el runner de campañas.")

    @staticmethod
    def confirmation_button_labels(resume=False):
        return ("Reanudar corrida" if resume else "Iniciar corrida", "Cancelar")

    def _confirm_run(self,run_id,resume):
        primary,cancel=self.confirmation_button_labels(resume)
        dialog=QMessageBox(QMessageBox.Icon.Question,"Confirmación de ejecución",self._confirmation_text(run_id,resume),QMessageBox.StandardButton.NoButton,self)
        accept=dialog.addButton(primary,QMessageBox.ButtonRole.AcceptRole)
        reject=dialog.addButton(cancel,QMessageBox.ButtonRole.RejectRole);dialog.setDefaultButton(reject);dialog.exec()
        return dialog.clickedButton() is accept

    def start_run(self, *, resume):
        if self.task is not None:return
        if repository_root_containing(self.artifact_root) is not None:
            QMessageBox.warning(self,"Artifact root bloqueado","No se permiten ejecuciones ni reanudaciones que escriban dentro del repositorio. Elegí una raíz externa.");return
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
        if not self._confirm_run(run_id,resume):return
        document=json.loads(json.dumps(self._engine(),allow_nan=False))
        project_id=self.context.project['project_id']; self.cancel_event=threading.Event()
        self.output.appendPlainText(f"{'Resume' if resume else 'Inicio'} autorizado explícitamente · run {run_id}")
        variant_label=self.context.selected_variant or "base"
        self.task=run_background(run_exploratory,document,project_id=project_id,run_id=run_id,
            artifact_root=self.artifact_root,rpm=self.rpm.value(),max_cycles=self.cycles.value(),
            budget_seconds=self.budget.value(),memory_limit_mib=self.memory.value(),resume=resume,
            cancel_event=self.cancel_event,variant_label=variant_label,
            progress=self.progress_signal.emit,on_done=self._done,on_error=self._failed)
        self.elapsed_timer.start();self.progress_latest=None;self.status_text="CORRIENDO";self.checkpoint_summary="se conserva al completar cada ciclo"
        self.cancel.setEnabled(True); self.start.setEnabled(False); self.resume.setEnabled(False)
        self.state_changed.emit()

    def start_power_curve(self):
        """Prepare and explicitly confirm a bounded exploratory RPM sweep."""
        if self.task is not None:return
        from ..power_curve import plan_rpm_range
        from ..power_curve_sweep import prepare_power_curve,run_power_curve
        dialog=QDialog(self);dialog.setWindowTitle("Preparar curva RPM · EXPLORATORY")
        form=QFormLayout(dialog)
        start=QSpinBox();start.setRange(2500,15000);start.setSingleStep(100);start.setValue(3000)
        stop=QSpinBox();stop.setRange(2500,15000);stop.setSingleStep(100);stop.setValue(6000)
        step=QSpinBox();step.setRange(1,5000);step.setSingleStep(100);step.setValue(500)
        cycles=QSpinBox();cycles.setRange(1,111);cycles.setValue(24)
        point_budget=QSpinBox();point_budget.setRange(1,600);point_budget.setValue(int(self.budget.value()))
        total_budget=QSpinBox();total_budget.setRange(1,3600);total_budget.setValue(1800)
        memory=QSpinBox();memory.setRange(256,4096);memory.setValue(self.memory.value())
        for label,widget in (("RPM inicial",start),("RPM final",stop),("Incremento",step),
            ("Horizonte máximo por punto",cycles),("Presupuesto por punto (s)",point_budget),
            ("Presupuesto total de esta invocación (s)",total_budget),("Memoria RSS máxima (MiB)",memory)):
            form.addRow(label,widget)
        form.addRow(QLabel("Cada punto usa el solver integrado y su checkpoint/auditoría independientes. No se extrapolan gaps."))
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Preflight y continuar…")
        buttons.accepted.connect(dialog.accept);buttons.rejected.connect(dialog.reject);form.addRow(buttons)
        if dialog.exec()!=QDialog.DialogCode.Accepted:return
        try:
            grid=plan_rpm_range(start.value(),stop.value(),step.value())
            if len(grid)>30:raise ValueError("Una invocación admite como máximo 30 puntos.")
            document=json.loads(json.dumps(self._engine(),allow_nan=False))
            project_id=self.context.project["project_id"];variant=self.context.selected_variant or "base"
            prepared=prepare_power_curve(document,project_id=project_id,variant_label=variant,
                artifact_root=self.artifact_root,start_rpm=start.value(),stop_rpm=stop.value(),
                step_rpm=step.value(),max_cycles=cycles.value(),point_budget_seconds=point_budget.value(),
                total_budget_seconds=total_budget.value(),memory_limit_mib=memory.value())
            confirmation=(f"Preflight PASS · 0 pasos del solver\n\nVariante: {variant}\n"
                f"RPM: {', '.join(map(str,grid))}\nPuntos: {len(grid)} · serial, 1 worker\n"
                f"Horizonte: hasta {cycles.value()} ciclos/punto\nPresupuesto: {total_budget.value()} s agregado; "
                f"hasta {point_budget.value()} s/punto\nMemoria RSS: {memory.value()} MiB\n"
                f"Identidad: {prepared['identity_sha256']}\nArtifact root: {self.artifact_root}\n\n"
                "EXPLORATORY; no implica periodicidad, convergencia ni aceptación científica.")
            answer=QMessageBox.question(self,"Confirmar barrido RPM",confirmation,
                QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,QMessageBox.StandardButton.No)
            if answer!=QMessageBox.StandardButton.Yes:return
        except Exception as exc:
            QMessageBox.warning(self,"Preflight de curva bloqueado",f"FAIL-CLOSED: {type(exc).__name__}: {exc}");return
        self.cancel_event=threading.Event();self.progress_latest=None
        self.output.appendPlainText(f"Barrido EXPLORATORY iniciado · {len(grid)} RPM · sin autorización VERIFIED.")
        self.task=run_background(run_power_curve,document,project_id=project_id,variant_label=variant,
            artifact_root=self.artifact_root,start_rpm=start.value(),stop_rpm=stop.value(),step_rpm=step.value(),
            max_cycles=cycles.value(),point_budget_seconds=point_budget.value(),
            total_budget_seconds=total_budget.value(),memory_limit_mib=memory.value(),
            cancel_event=self.cancel_event,progress=self.progress_signal.emit,
            on_done=self._done,on_error=self._failed)
        self.elapsed_timer.start();self.status_text="CORRIENDO BARRIDO";self.checkpoint_summary="manifiesto guardado por punto"
        self.cancel.setEnabled(True);self.start.setEnabled(False);self.resume.setEnabled(False);self.sweep.setEnabled(False)
        self.resume_sweep.setEnabled(False)
        self.state_changed.emit()

    def resume_power_curve(self):
        """Resume only an explicitly selected, binding-compatible sweep manifest."""
        if self.task is not None:return
        from ..power_curve_sweep import run_power_curve
        selected,_=QFileDialog.getOpenFileName(self,"Elegir manifiesto de curva para reanudar",
            str(self.artifact_root),"Manifiesto de curva (series.json)")
        if not selected:return
        try:
            manifest_path=Path(selected).resolve()
            if manifest_path.name!="series.json":raise ValueError("Seleccioná el archivo series.json de una curva.")
            manifest=json.loads(manifest_path.read_text(encoding="utf-8"))
            binding=manifest.get("bindings",{})
            document=json.loads(json.dumps(self._engine(),allow_nan=False))
            if binding.get("project_id")!=self.context.project["project_id"]:
                raise ValueError("El proyecto activo no coincide con la curva.")
            if binding.get("variant_label")!=(self.context.selected_variant or "base"):
                raise ValueError("La variante activa no coincide con la curva.")
            from ..power_curve_sweep import prepare_power_curve
            prepared=prepare_power_curve(document,project_id=binding["project_id"],
                variant_label=binding["variant_label"],artifact_root=binding["artifact_root"],
                start_rpm=binding["rpms"][0],stop_rpm=binding["rpms"][-1],
                step_rpm=binding["rpms"][1]-binding["rpms"][0] if len(binding["rpms"])>1 else 1,
                max_cycles=binding["max_cycles"],point_budget_seconds=binding["point_budget_seconds"],
                total_budget_seconds=binding["total_budget_seconds"],memory_limit_mib=binding["memory_limit_mib"])
            if manifest.get("schema")!="DINO_POWER_CURVE_SWEEP_V1" or prepared["identity_sha256"]!=binding.get("identity_sha256") or str(manifest_path.parent)!=str((Path(binding["artifact_root"])/"dino-power-curve-v1"/binding["project_id"]/manifest_path.parent.name).resolve()):
                raise ValueError("La identidad o ubicación del manifiesto no coincide; reanudación bloqueada.")
            answer=QMessageBox.question(self,"Reanudar curva RPM",
                f"Reanudar {len(binding['rpms'])} puntos desde el manifiesto seleccionado?\n"
                f"RPM: {binding['rpms']}\nConsumido previamente: {manifest.get('elapsed_seconds',0):.1f} s\n"
                f"Presupuesto agregado: {binding['total_budget_seconds']} s\n"
                "Se conservarán los checkpoints válidos; no se reiniciarán puntos completos.",
                QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,QMessageBox.StandardButton.No)
            if answer!=QMessageBox.StandardButton.Yes:return
        except Exception as exc:
            QMessageBox.warning(self,"Reanudación bloqueada",f"FAIL-CLOSED: {type(exc).__name__}: {exc}");return
        self.cancel_event=threading.Event();self.output.appendPlainText(f"Reanudación solicitada · curva {manifest_path.parent.name}")
        self.task=run_background(run_power_curve,document,project_id=binding["project_id"],
            variant_label=binding["variant_label"],artifact_root=binding["artifact_root"],
            start_rpm=binding["rpms"][0],stop_rpm=binding["rpms"][-1],
            step_rpm=(binding["rpms"][1]-binding["rpms"][0] if len(binding["rpms"])>1 else 1),
            max_cycles=binding["max_cycles"],point_budget_seconds=binding["point_budget_seconds"],
            total_budget_seconds=binding["total_budget_seconds"],memory_limit_mib=binding["memory_limit_mib"],
            sweep_id=manifest_path.parent.name,resume=True,cancel_event=self.cancel_event,
            progress=self.progress_signal.emit,on_done=self._done,on_error=self._failed)
        self.elapsed_timer.start();self.status_text="REANUDANDO BARRIDO";self.checkpoint_summary="se validan hashes y checkpoints antes de continuar"
        self.cancel.setEnabled(True);self.start.setEnabled(False);self.resume.setEnabled(False);self.sweep.setEnabled(False);self.resume_sweep.setEnabled(False)
        self.state_changed.emit()

    def _progress(self,row):
        self.progress_latest=dict(row);self.status_text="CORRIENDO"
        if "point_index" in row:
            if "point" in row:
                self.output.appendPlainText(f"Punto {row['point_index']}/{row['point_count']} · {row['rpm']} RPM · {row['point'].get('classification')}")
            elif "solver_progress" in row:
                p=row["solver_progress"]
                self.output.appendPlainText(f"{row['rpm']} RPM · ciclo {p['cycle']} · {p['angle_deg']:.1f}° · RSS {p['rss_bytes']/1048576:.0f} MiB")
        else:
            self.output.appendPlainText(f"Ciclo {row['cycle']} · {row['angle_deg']:.1f}° · RSS {row['rss_bytes']/1048576:.0f} MiB")
        self.state_changed.emit()

    def _done(self,result):
        self.status_text=f"TERMINADA · {result.get('classification','clasificación no informada')}"
        if isinstance(result.get("points"),list):
            complete=sum(row.get("status")=="COMPLETE" for row in result["points"])
            interrupted=sum(row.get("status")=="INTERRUPTED_CHECKPOINTED" for row in result["points"])
            not_started=sum(row.get("status")=="NOT_STARTED" for row in result["points"])
            self.checkpoint_summary=(f"{complete} puntos ejecutados · {interrupted} interrumpidos con checkpoint · "
                f"{not_started} sin iniciar · {result.get('curve_availability','curva parcial')}")
        else:
            self.checkpoint_summary=f"{result.get('cycles_completed',0)} ciclos guardados · {result.get('periodicity','periodicidad no evaluada')}"
        summary={k:result.get(k) for k in ("status","classification","mode","scientific_validation","cycles_completed","periodicity","failure","elapsed_seconds","artifact_directory","result_sha256","bindings","points")}
        summary["cycles"]=[{"cycle":r["cycle"],"primary_sha256":r["primary_sha256"],"audit_recomputed":r["audit"].get("recomputed"),"conservation":r["conservation"],"metric_statuses":{k:v.get("status") for k,v in r["engineering_output"].get("cycle_metrics",{}).items() if isinstance(v,dict)}} for r in result.get("cycles",[])]
        self.output.appendPlainText(json.dumps(summary,indent=2,ensure_ascii=False))
        self._release_task()

    def _failed(self,message):
        self.status_text="BLOQUEADA · error FAIL-CLOSED";self.checkpoint_summary="evidencia previa conservada"
        self.output.appendPlainText("FAIL-CLOSED: "+message); self._release_task()

    def _release_task(self):
        self.task=None; self.cancel_event=None; self.cancel.setEnabled(False); self.refresh();self.refresh_history_requested.emit();self.state_changed.emit()

    def cancel_run(self):
        if self.cancel_event is not None:
            self.cancel_event.set();self.status_text="CANCELACIÓN SOLICITADA"; self.output.appendPlainText("Cancelación solicitada; se detendrá en un límite de paso y conservará el último checkpoint completo.");self.state_changed.emit()
