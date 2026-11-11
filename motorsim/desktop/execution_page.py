from __future__ import annotations

import json
import hashlib
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
    QFormLayout, QGroupBox, QComboBox, QDialog, QDialogButtonBox,QCheckBox,QInputDialog)

from ..engine_configuration import identity, resolve_for_operating_point
from ..exploratory_workflow import preflight, run_exploratory
from .services import run_background,run_parallel_curve_points
from .preferences import artifact_root, set_artifact_root, repository_root_containing, default_artifact_root
from .presentation import format_number,state_label


class ExecutionPage(QWidget):
    """Single-point EXPLORATORY controls; VERIFIED remains unavailable."""
    progress_signal=Signal(object)
    open_runs_requested=Signal(object)
    resume_run_requested=Signal(object)
    state_changed=Signal()
    artifact_root_changed=Signal(object)
    refresh_history_requested=Signal()
    design_study_completed=Signal(object)
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
        self.mode=QLabel("EXPLORATORY · 1 worker · conservación; auditoría según modo de ejecución")
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
        self.last_result_paths=[];self.last_result_project_id=None
        self.view_result=QPushButton('Ver resultado de la última corrida')
        self.view_result.setEnabled(False);self.view_result.clicked.connect(lambda *_:self.open_runs_requested.emit(self.last_result_paths))
        root.addWidget(self.view_result)
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
        if self.last_result_project_id is not None and self.last_result_project_id!=self.context.project['project_id']:
            self.last_result_paths=[];self.last_result_project_id=None;self.view_result.setEnabled(False)
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
            if engine["native_configuration"]["geometry_identity"].get("gas_exchange_model") is not None:
                self.expected.setText("Modo de ingeniería: balances internos, muestras físicas y checkpoints. Sin replay ni auditoría independiente. Potencia transitoria identificada como no convergida; sin validación predictiva.")
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

    def use_safe_default_root(self):
        """Redirect new-project output away from a stale repository-local setting."""
        self.artifact_root=set_artifact_root(default_artifact_root())
        self.root_label.setText(str(self.artifact_root))
        self.history.artifact_root=self.artifact_root
        self.artifact_root_changed.emit(self.artifact_root)
        self.refresh()
        return self.artifact_root

    def resume_from_entry(self,entry):
        """Populate the existing guarded resume path from a read-only index row."""
        if self.task is not None:return
        try:
            matches=[]
            for name,engine in [(None,self.context.project["base_engine"]),*self.context.project["variants"].items()]:
                effective=resolve_for_operating_point(engine,rpm=entry.get("rpm"))
                if effective["identity_sha256"]==entry.get("identity_sha256"):matches.append(name)
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
        if not self.context.prepare_operation('Ejecutar simulación 2T'):return
        self.active_sweep_settings=None
        if self.task is not None:return
        if repository_root_containing(self.artifact_root) is not None:
            QMessageBox.warning(self,"Artifact root bloqueado","No se permiten ejecuciones ni reanudaciones que escriban dentro del repositorio. Elegí una raíz externa.");return
        run_id=self.run_id.text().strip()
        if not resume:
            # A normal run is always a new attempt. The field retains the last
            # generated ID for display/resume context; reusing it after changing
            # a variant would otherwise attach a new design to an old checkpoint.
            run_id=uuid.uuid4().hex
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
        if not self.context.prepare_operation('Preparar curva RPM 2T'):return
        if self.task is not None:return
        from ..power_curve import plan_rpm_range
        from ..power_curve_sweep import prepare_power_curve,run_power_curve
        dialog=QDialog(self);dialog.setWindowTitle("Preparar curva RPM · EXPLORATORY")
        form=QFormLayout(dialog)
        from ..rpm_domain import PUBLIC_DOMAINS
        low_rpm,high_rpm=PUBLIC_DOMAINS['2T']
        start=QSpinBox();start.setRange(low_rpm,high_rpm);start.setSingleStep(500);start.setValue(low_rpm)
        stop=QSpinBox();stop.setRange(low_rpm,high_rpm);stop.setSingleStep(500);stop.setValue(min(13000,high_rpm))
        step=QSpinBox();step.setRange(1,5000);step.setSingleStep(100);step.setValue(500)
        for spin in (start,stop):spin.setToolTip(f'Dominio público 2T habilitado: {low_rpm}–{high_rpm} RPM; no es un límite físico universal.')
        cycles=QSpinBox();cycles.setRange(1,111);cycles.setValue(24)
        point_budget=QSpinBox();point_budget.setRange(1,600);point_budget.setValue(int(self.budget.value()))
        total_budget=QSpinBox();total_budget.setRange(1,3600);total_budget.setValue(1800)
        memory=QSpinBox();memory.setRange(256,4096);memory.setValue(self.memory.value())
        for widget,name in ((start,'curveStartRpm'),(stop,'curveStopRpm'),(step,'curveStepRpm'),
                            (cycles,'curveCycles'),(point_budget,'curvePointBudget'),(total_budget,'curveTotalBudget'),(memory,'curveMemory')):
            widget.setObjectName(name)
        reuse=QCheckBox('Reutilizar puntos completos de esta variante desde el historial, con identidad verificada')
        reuse.setObjectName('curveReuseCompleted');reuse.setChecked(True);form.addRow(reuse)
        hold=QCheckBox('Extender extremo ya totalmente abierto de válvula hasta RPM final · SYNTHETIC_ASSUMPTION')
        hold.setObjectName('curveOpenEndpointHold')
        hold.setChecked(self.context.project['simulation_recipes'].get('rpm_control_policy',{}).get('schema')=='POWERVALVE_OPEN_ENDPOINT_HOLD_V1')
        form.addRow(hold)
        parallel_variant=QComboBox();parallel_variant.setObjectName("curveABParallelVariant")
        parallel_variant.addItem("Solo variante activa · serial",None)
        active=self.context.selected_variant or "base"
        for name in ["base",*self.context.project["variants"]]:
            if name!=active:parallel_variant.addItem(f"A/B con {name} · puntos independientes",name)
        form.addRow("Despacho A/B",parallel_variant)
        for label,widget in (("RPM inicial",start),("RPM final",stop),("Incremento",step),
            ("Horizonte máximo por punto",cycles),("Presupuesto por punto (s)",point_budget),
            ("Presupuesto total de esta invocación (s)",total_budget),("Memoria RSS máxima (MiB)",memory)):
            form.addRow(label,widget)
        plan_label=QLabel();plan_label.setWordWrap(True);form.addRow('Plan de ejecución',plan_label)
        def update_plan(*_):
            try:
                grid=plan_rpm_range(start.value(),stop.value(),step.value())
                count=len(grid)*(2 if parallel_variant.currentData() is not None else 1)
                plan_label.setText(f'{count} puntos · RPM {grid} · presupuesto por punto {point_budget.value()} s · total {total_budget.value()} s. El presupuesto no es una estimación de duración.')
            except Exception as exc:plan_label.setText('Revisá el rango: '+str(exc))
        for spin in (start,stop,step,point_budget,total_budget):spin.valueChanged.connect(update_plan)
        parallel_variant.currentIndexChanged.connect(update_plan);update_plan()
        domain_note=QLabel(f'Dominio 2T habilitado actualmente: {low_rpm}–{high_rpm} RPM. '
                           'No es el límite físico universal de un motor 2T; valores inferiores requieren ampliar la validación del solver.')
        domain_note.setWordWrap(True);form.addRow(domain_note)
        form.addRow(QLabel("Cada punto usa el solver integrado y su checkpoint. Auditoría según el modo del motor; no se extrapolan gaps."))
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Preflight y continuar…")
        buttons.accepted.connect(dialog.accept);buttons.rejected.connect(dialog.reject);form.addRow(buttons)
        parallel_variant.currentIndexChanged.connect(lambda *_:reuse.setEnabled(parallel_variant.currentData() is None))
        if dialog.exec()!=QDialog.DialogCode.Accepted:return
        try:
            grid=plan_rpm_range(start.value(),stop.value(),step.value())
            if len(grid)>30:raise ValueError("Una invocación admite como máximo 30 puntos.")
            document=json.loads(json.dumps(self._engine(),allow_nan=False))
            project_id=self.context.project["project_id"];variant=self.context.selected_variant or "base"
            control_policy=dict(schema='POWERVALVE_OPEN_ENDPOINT_HOLD_V1',maximum_rpm=stop.value()) if hold.isChecked() else None
            selected_parallel=parallel_variant.currentData()
            engines=[(variant,document)]
            if selected_parallel is not None:
                other=self.context.project["base_engine"] if selected_parallel=="base" else self.context.project["variants"][selected_parallel]
                if identity(other)==identity(document):raise ValueError("La variante A/B debe tener una identidad de solver distinta.")
                engines.append((selected_parallel,json.loads(json.dumps(other,allow_nan=False))))
                import psutil
                workers=min(3,psutil.cpu_count(logical=True) or 1,
                    psutil.virtual_memory().available//(memory.value()*1024**2+128*1024**2))
                if workers<2:raise ValueError("No hay memoria/CPU disponible para al menos dos workers seguros.")
                from ..storage_preflight import check_storage_requirements
                check_storage_requirements([(self.artifact_root,512*1024**2)])
            reused=[] if selected_parallel else [e['run_directory'] for e in self.history.entries if reuse.isChecked() and
                    e.get('variant')==variant and e.get('rpm') in grid and e.get('status')=='COMPLETE']
            prepared=prepare_power_curve(document,project_id=project_id,variant_label=variant,
                artifact_root=self.artifact_root,start_rpm=start.value(),stop_rpm=stop.value(),
                step_rpm=step.value(),max_cycles=cycles.value(),point_budget_seconds=point_budget.value(),
                total_budget_seconds=total_budget.value(),memory_limit_mib=memory.value(),control_policy=control_policy)
            from ..power_curve_sweep import _reused_points
            verified_reuse=_reused_points(reused,prepared)
            prepared_items=[prepared]
            if selected_parallel:
                prepared_items.append(prepare_power_curve(engines[1][1],project_id=project_id,variant_label=engines[1][0],
                    artifact_root=self.artifact_root,start_rpm=start.value(),stop_rpm=stop.value(),step_rpm=step.value(),
                    max_cycles=cycles.value(),point_budget_seconds=point_budget.value(),total_budget_seconds=total_budget.value(),
                    memory_limit_mib=memory.value(),control_policy=control_policy))
            worker_text=f"{workers} procesos · 1 run/checkpoint independiente por RPM" if selected_parallel else "serial, 1 worker"
            reuse_text=("No se reutilizan puntos en despacho A/B paralelo." if selected_parallel else
                        f"Reutilizar sin cálculo: {[p['rpm'] for p in verified_reuse]} RPM")
            confirmation=(f"Preflight PASS · 0 pasos del solver\n\nVariantes: {', '.join(name for name,_ in engines)}\n"
                f"RPM: {', '.join(map(str,grid))}\nPuntos: {len(grid)} por variante · {worker_text}\n"
                f"Horizonte: hasta {cycles.value()} ciclos/punto\nPresupuesto: {total_budget.value()} s agregado; "
                f"hasta {point_budget.value()} s/punto\nMemoria RSS: {memory.value()} MiB por worker\n"
                f"{reuse_text}\n"
                f"Política de control RPM: {control_policy or 'mapa original sin extensión'}\n"
                f"Identidad: {prepared['identity_sha256']}\nArtifact root: {self.artifact_root}\n\n"
                "EXPLORATORY; no implica periodicidad, convergencia ni aceptación científica.")
            answer=QMessageBox.question(self,"Confirmar barrido RPM",confirmation,
                QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,QMessageBox.StandardButton.No)
            if answer!=QMessageBox.StandardButton.Yes:return
        except Exception as exc:
            QMessageBox.warning(self,"Preflight de curva bloqueado",f"FAIL-CLOSED: {type(exc).__name__}: {exc}");return
        self.cancel_event=threading.Event();self.progress_latest=None
        # The persistent application status strip consumes the sweep recipe as
        # one mapping; keep it mapping-shaped for both serial and A/B dispatch.
        self.active_sweep_settings=prepared
        self.context.project['simulation_recipes']['rpm_curve_v1']=dict(rpms=grid,max_cycles=cycles.value(),
            point_budget_seconds=point_budget.value(),total_budget_seconds=total_budget.value(),memory_limit_mib=memory.value())
        if selected_parallel:self.context.project['simulation_recipes']['rpm_ab_parallel_v1']={"variants":[name for name,_ in engines],"rpms":grid,"workers":workers,"max_cycles":cycles.value()}
        if control_policy is not None:self.context.project['simulation_recipes']['rpm_control_policy']=control_policy
        self.context.dirty=True
        self.output.appendPlainText(f"Barrido EXPLORATORY iniciado · {len(grid)} RPM por variante · {worker_text} · sin autorización VERIFIED.")
        if selected_parallel:
            group=uuid.uuid4().hex;specs=[]
            for variant_index,(label,engine_doc) in enumerate(engines):
                source=prepared_items[variant_index]
                for rpm_index,rpm in enumerate(grid):
                    check=source['point_preflights'][rpm_index]
                    specs.append({"document":engine_doc,"project_id":project_id,"variant_label":label,"rpm":rpm,
                        "artifact_root":str(self.artifact_root),"run_id":f"ab-{group[:12]}-{variant_index}-{rpm}",
                        "max_cycles":cycles.value(),"point_budget_seconds":point_budget.value(),
                        "memory_limit_mib":memory.value(),"control_policy":control_policy,
                        "identity_sha256":check["identity_sha256"]})
            self.task=run_background(run_parallel_curve_points,specs,max_workers=workers,
                total_budget_seconds=total_budget.value(),cancel_event=self.cancel_event,progress=self.progress_signal.emit,
                on_done=self._done,on_error=self._failed)
        else:
            self.task=run_background(run_power_curve,document,project_id=project_id,variant_label=variant,
                artifact_root=self.artifact_root,start_rpm=start.value(),stop_rpm=stop.value(),step_rpm=step.value(),
                max_cycles=cycles.value(),point_budget_seconds=point_budget.value(),
                total_budget_seconds=total_budget.value(),memory_limit_mib=memory.value(),
                cancel_event=self.cancel_event,progress=self.progress_signal.emit,reuse_runs=reused,control_policy=control_policy,
                on_done=self._done,on_error=self._failed)
        self.elapsed_timer.start();self.status_text="CORRIENDO BARRIDO";self.checkpoint_summary="manifiesto guardado por punto"
        self.cancel.setEnabled(True);self.start.setEnabled(False);self.resume.setEnabled(False);self.sweep.setEnabled(False)
        self.resume_sweep.setEnabled(False)
        self.state_changed.emit()

    def start_design_study(self):
        """Prepare one bounded geometry factor study through the existing solver workflow."""
        if self.task is not None:return
        from ..design_study import available_parameters,prepare_design_study,run_design_study
        if repository_root_containing(self.artifact_root) is not None:
            QMessageBox.warning(self,"Artifact root bloqueado","Elegí una carpeta externa al repositorio antes de crear el estudio.");return
        dialog=QDialog(self);dialog.setWindowTitle("Exploración paramétrica de diseño · EXPLORATORY")
        form=QFormLayout(dialog)
        try:parameters=available_parameters(self._engine())
        except Exception as exc:
            QMessageBox.warning(self,"Exploración paramétrica no disponible",
                f"La geometría activa no tiene un adaptador paramétrico seguro: {type(exc).__name__}: {exc}\n\nNo se modificó la configuración ni se inició el solver.")
            return
        if not parameters:
            QMessageBox.information(self,"Sin parámetros compatibles","Esta geometría todavía no ofrece ejes paramétricos seguros.");return
        parameter=QComboBox();parameter.setObjectName("designStudyParameter")
        for item in parameters:parameter.addItem(item["label"],item["id"])
        form.addRow("Parámetro compatible",parameter)
        baseline=QLabel();baseline.setObjectName("designStudyBaseline");baseline.setWordWrap(True);form.addRow("Valor baseline",baseline)
        alternatives=QLineEdit();alternatives.setObjectName("designStudyValues")
        alternatives.setPlaceholderText(f"Valores alternativos en {parameters[0]['unit']}, separados por coma")
        form.addRow("Valores a probar",alternatives)
        notice=QLabel("El baseline se agrega automáticamente. Máximo 5 puntos. Sólo se ofrecen parámetros con adaptadores compatibles; las lumbreras se regeneran con TwoStrokePortSet y el cárter actualiza geometría e inventarios iniciales. No se cambia la topología del solver. Resultados EXPLORATORY; no son predicciones validadas.")
        notice.setWordWrap(True);form.addRow(notice)
        cycles=QSpinBox();cycles.setRange(1,111);cycles.setValue(1);cycles.setObjectName("designStudyCycles")
        point_budget=QSpinBox();point_budget.setRange(1,600);point_budget.setValue(min(60,int(self.budget.value())))
        point_budget.setObjectName("designStudyPointBudget")
        total_budget=QSpinBox();total_budget.setRange(2,600);total_budget.setValue(min(600,max(2,3*point_budget.value())))
        total_budget.setObjectName("designStudyTotalBudget")
        form.addRow("Horizonte máximo por diseño",cycles);form.addRow("Presupuesto máximo por diseño (s)",point_budget)
        form.addRow("Presupuesto agregado del estudio (s)",total_budget)
        def update_parameter_info(index):
            selected=parameters[index]
            baseline.setText(f"{selected['baseline']:g} {selected['unit']} · valor actual del proyecto")
            alternatives.setPlaceholderText(f"Valores alternativos explícitos en {selected['unit']}, separados por coma")
        parameter.currentIndexChanged.connect(update_parameter_info)
        update_parameter_info(0)
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Preflight y ejecutar…")
        buttons.accepted.connect(dialog.accept);buttons.rejected.connect(dialog.reject);form.addRow(buttons)
        if dialog.exec()!=QDialog.DialogCode.Accepted:return
        try:
            raw=alternatives.text().replace(";",",").replace("\n",",")
            entered=[float(part.strip()) for part in raw.split(",") if part.strip()]
            selected=parameters[parameter.currentIndex()]
            values=[selected["baseline"],*entered]
            if len(values)>5:raise ValueError("el estudio admite hasta 5 puntos, incluyendo el baseline")
            document=json.loads(json.dumps(self._engine(),allow_nan=False))
        except Exception as exc:
            QMessageBox.warning(self,"Estudio bloqueado",f"FAIL-CLOSED: {type(exc).__name__}: {exc}");return
        arguments={"parameter_id":selected["id"],"values":values,"rpm":self.rpm.value(),
            "max_cycles":cycles.value(),"point_budget_seconds":point_budget.value(),
            "total_budget_seconds":total_budget.value(),"memory_limit_mib":self.memory.value(),
            "project_id":self.context.project["project_id"],"variant_label":self.context.selected_variant or "base"}
        self.cancel_event=None;self.progress_latest=None
        self.active_sweep_settings={"rpms":[self.rpm.value()],"max_cycles":cycles.value(),
            "total_budget_seconds":total_budget.value()}
        self.output.appendPlainText(f"Preflight paramétrico en segundo plano · {len(values)} configuraciones · 0 pasos del solver.")
        self.task=run_background(prepare_design_study,document,on_done=self._design_study_preflight_done,
            on_error=self._failed,**arguments)
        self.elapsed_timer.start();self.status_text="VALIDANDO DISEÑOS · SIN PASOS DEL SOLVER";self.checkpoint_summary="preflight geométrico en segundo plano"
        self.cancel.setEnabled(False);self.start.setEnabled(False);self.resume.setEnabled(False)
        self.sweep.setEnabled(False);self.resume_sweep.setEnabled(False);self.state_changed.emit()

    def start_design_rpm_envelope(self):
        """Prepare a small geometry × RPM grid through existing curve sweeps."""
        if self.task is not None:return
        from ..design_study import available_parameters,prepare_design_rpm_envelope
        if repository_root_containing(self.artifact_root) is not None:
            QMessageBox.warning(self,"Artifact root bloqueado","Elegí una carpeta externa al repositorio antes de crear el estudio.");return
        try:parameters=available_parameters(self._engine())
        except Exception as exc:
            QMessageBox.warning(self,"Envolvente paramétrica no disponible",f"No hay adaptadores geométricos compatibles: {type(exc).__name__}: {exc}");return
        if not parameters:
            QMessageBox.information(self,"Sin parámetros compatibles","Esta geometría no ofrece adaptadores paramétricos seguros.");return
        dialog=QDialog(self);dialog.setWindowTitle("Estudio de diseño × RPM · EXPLORATORY")
        form=QFormLayout(dialog);parameter=QComboBox();parameter.setObjectName("rpmEnvelopeParameter")
        for item in parameters:parameter.addItem(item["label"],item["id"])
        form.addRow("Parámetro compatible",parameter)
        baseline=QLabel();baseline.setWordWrap(True);form.addRow("Valor baseline",baseline)
        alternatives=QLineEdit();alternatives.setObjectName("rpmEnvelopeValues")
        form.addRow("Valores alternativos",alternatives)
        start_rpm=QSpinBox();start_rpm.setObjectName("rpmEnvelopeStart");start_rpm.setRange(500,15000);start_rpm.setSingleStep(500);start_rpm.setValue(min(14000,max(500,int(self.rpm.value()/1000)*1000)))
        stop_rpm=QSpinBox();stop_rpm.setObjectName("rpmEnvelopeStop");stop_rpm.setRange(500,15000);stop_rpm.setSingleStep(500);stop_rpm.setValue(min(15000,start_rpm.value()+1000))
        step_rpm=QSpinBox();step_rpm.setObjectName("rpmEnvelopeStep");step_rpm.setRange(100,5000);step_rpm.setSingleStep(100);step_rpm.setValue(1000)
        form.addRow("RPM inicial",start_rpm);form.addRow("RPM final inclusivo",stop_rpm);form.addRow("Incremento RPM",step_rpm)
        cycles=QSpinBox();cycles.setRange(1,111);cycles.setValue(1)
        point_budget=QSpinBox();point_budget.setRange(1,600);point_budget.setValue(min(15,int(self.budget.value())))
        total_budget=QSpinBox();total_budget.setRange(4,600);total_budget.setValue(min(600,max(4,4*point_budget.value())))
        form.addRow("Máximo de ciclos por punto",cycles);form.addRow("Presupuesto por diseño × RPM (s)",point_budget)
        form.addRow("Presupuesto agregado (s, máximo 600)",total_budget)
        note=QLabel("Máximo 5 geometrías × 6 RPM = 30 puntos. La cuadrícula debe alcanzar exactamente el RPM final. Se reutiliza el barrido existente; periodicidad y métricas siguen clasificadas por punto. EXPLORATORY, sin validación predictiva.")
        note.setWordWrap(True);form.addRow(note)
        def sync(index):
            selected=parameters[index];baseline.setText(f"{selected['baseline']:g} {selected['unit']} · valor actual")
            alternatives.setPlaceholderText(f"Valores adicionales en {selected['unit']}, separados por coma")
        parameter.currentIndexChanged.connect(sync);sync(0)
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Preflight de la matriz…")
        buttons.accepted.connect(dialog.accept);buttons.rejected.connect(dialog.reject);form.addRow(buttons)
        if dialog.exec()!=QDialog.DialogCode.Accepted:return
        try:
            raw=alternatives.text().replace(";",",").replace("\n",",")
            entered=[float(part.strip()) for part in raw.split(",") if part.strip()]
            selected=parameters[parameter.currentIndex()];values=[selected["baseline"],*entered]
            if len(values)>5:raise ValueError("el estudio admite hasta 5 diseños incluyendo baseline")
            rpms=list(range(start_rpm.value(),stop_rpm.value()+1,step_rpm.value()))
            if not rpms or rpms[-1]!=stop_rpm.value():raise ValueError("el incremento debe alcanzar exactamente el RPM final")
            if len(rpms)>6:raise ValueError("el estudio admite hasta 6 puntos RPM")
            document=json.loads(json.dumps(self._engine(),allow_nan=False))
        except Exception as exc:
            QMessageBox.warning(self,"Envolvente bloqueada",f"FAIL-CLOSED: {type(exc).__name__}: {exc}");return
        arguments={"parameter_id":selected["id"],"values":values,"rpms":rpms,
            "max_cycles":cycles.value(),"point_budget_seconds":point_budget.value(),
            "total_budget_seconds":total_budget.value(),"memory_limit_mib":self.memory.value(),
            "project_id":self.context.project["project_id"],"variant_label":self.context.selected_variant or "base",
            "artifact_root":self.artifact_root}
        self.cancel_event=None;self.progress_latest=None
        self.active_sweep_settings={"rpms":rpms,"max_cycles":cycles.value(),"total_budget_seconds":total_budget.value()}
        self.output.appendPlainText(f"Preflight diseño × RPM en segundo plano · {len(values)*len(rpms)} combinaciones · 0 pasos del solver.")
        self.task=run_background(prepare_design_rpm_envelope,document,on_done=self._design_study_preflight_done,
            on_error=self._failed,**arguments)
        self.elapsed_timer.start();self.status_text="VALIDANDO MATRIZ DISEÑO × RPM · SIN PASOS DEL SOLVER"
        self.checkpoint_summary="preflight geométrico y de todos los RPM"
        self.cancel.setEnabled(False);self.start.setEnabled(False);self.resume.setEnabled(False)
        self.sweep.setEnabled(False);self.resume_sweep.setEnabled(False);self.state_changed.emit()

    def start_factorial_design_study(self):
        if self.task is not None:return
        from ..design_study import available_parameters,prepare_factorial_design_study
        try:parameters=available_parameters(self._engine())
        except Exception as exc:
            QMessageBox.warning(self,"Estudio factorial no disponible",
                f"La geometría no ofrece adaptadores paramétricos seguros: {type(exc).__name__}: {exc}")
            return
        if len(parameters)<2:
            QMessageBox.information(self,"Se requieren dos parámetros","La configuración no ofrece dos parámetros compatibles distintos.")
            return
        dialog=QDialog(self);dialog.setWindowTitle("Estudio factorial de diseño 2×2 · EXPLORATORY")
        form=QFormLayout(dialog)
        axes=[];editors=[]
        for index,title in enumerate(("Factor A","Factor B")):
            combo=QComboBox();combo.setObjectName(f"factorialParameter{index}")
            for item in parameters:combo.addItem(item["label"],item["id"])
            editor=QLineEdit();editor.setObjectName(f"factorialAlternative{index}")
            editor.setPlaceholderText("Un nivel alternativo; el baseline se agrega automáticamente")
            baseline=QLabel();baseline.setWordWrap(True)
            form.addRow(f"{title} compatible",combo);form.addRow(f"{title} baseline",baseline)
            form.addRow(f"{title} nivel alternativo",editor)
            def sync(item_index,selector=combo,label=baseline,entry=editor,axis_index=index):
                selected=parameters[selector.currentIndex()]
                label.setText(f"{selected['baseline']:g} {selected['unit']} · valor actual")
                entry.setPlaceholderText(f"Un nivel alternativo en {selected['unit']}")
            combo.currentIndexChanged.connect(sync);sync(0)
            axes.append(combo);editors.append(editor)
        notice=QLabel("Se ejecutan las cuatro combinaciones baseline/alternativo con los adaptadores existentes. Máximo 4 diseños; sin topologías nuevas, interpolación ni efectos derivados. Cada punto sigue siendo EXPLORATORY y no constituye predicción validada.")
        notice.setWordWrap(True);form.addRow(notice)
        cycles=QSpinBox();cycles.setRange(1,111);cycles.setValue(1)
        point_budget=QSpinBox();point_budget.setRange(1,150);point_budget.setValue(min(60,150,int(self.budget.value())))
        total_budget=QSpinBox();total_budget.setRange(4,600);total_budget.setValue(min(600,max(4,4*point_budget.value())))
        form.addRow("Horizonte máximo por diseño",cycles)
        form.addRow("Presupuesto máximo por diseño (s)",point_budget)
        form.addRow("Presupuesto agregado (s)",total_budget)
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Preflight factorial…")
        buttons.accepted.connect(dialog.accept);buttons.rejected.connect(dialog.reject);form.addRow(buttons)
        if dialog.exec()!=QDialog.DialogCode.Accepted:return
        try:
            ids=[combo.currentData() for combo in axes]
            if ids[0]==ids[1]:raise ValueError("seleccioná dos parámetros diferentes")
            factors=[]
            for combo,editor in zip(axes,editors):
                selected=parameters[combo.currentIndex()]
                alternative=float(editor.text().strip())
                factors.append({"parameter_id":selected["id"],"values":[selected["baseline"],alternative]})
            document=json.loads(json.dumps(self._engine(),allow_nan=False))
        except Exception as exc:
            QMessageBox.warning(self,"Estudio factorial bloqueado",f"FAIL-CLOSED: {type(exc).__name__}: {exc}");return
        arguments={"factors":factors,"rpm":self.rpm.value(),"max_cycles":cycles.value(),
            "point_budget_seconds":point_budget.value(),"total_budget_seconds":total_budget.value(),
            "memory_limit_mib":self.memory.value(),"project_id":self.context.project["project_id"],
            "variant_label":self.context.selected_variant or "base"}
        self.cancel_event=None;self.progress_latest=None
        self.active_sweep_settings={"rpms":[self.rpm.value()],"max_cycles":cycles.value(),
            "total_budget_seconds":total_budget.value()}
        self.output.appendPlainText("Preflight factorial 2×2 en segundo plano · 4 configuraciones · 0 pasos del solver.")
        self.task=run_background(prepare_factorial_design_study,document,
            on_done=self._design_study_preflight_done,on_error=self._failed,**arguments)
        self.elapsed_timer.start();self.status_text="VALIDANDO FACTORIAL · SIN PASOS DEL SOLVER"
        self.checkpoint_summary="cuatro diseños factoriales en preflight"
        self.cancel.setEnabled(False);self.start.setEnabled(False);self.resume.setEnabled(False)
        self.sweep.setEnabled(False);self.resume_sweep.setEnabled(False);self.state_changed.emit()

    def _design_study_preflight_done(self,prepared):
        from ..design_study import run_design_study,run_design_rpm_envelope
        try:
            from ..storage_preflight import check_storage_requirements
            point_count=prepared.get("combination_count",len(prepared["points"]))
            check_storage_requirements([(self.artifact_root,512*1024**2*point_count)])
            if prepared.get("design_method")=="FACTORIAL_2X2_V1":
                values_text="\n".join(row["label"] for row in prepared["points"])
            elif prepared.get("design_method")=="RPM_ENVELOPE_V1":
                values_text=", ".join(f"{value:g} {prepared['parameter']['unit']}" for value in prepared["values"])
            else:
                unit=prepared["parameter"]["unit"]
                values_text=", ".join(f"{value:g} {unit}" for value in prepared["values"])
            rpm_text=(", ".join(map(str,prepared["rpms"]))+" RPM" if prepared.get("design_method")=="RPM_ENVELOPE_V1" else f"{prepared['rpm']:g} RPM")
            summary=(f"Proyecto: {prepared['project_id']} · variante: {prepared['variant_label']}\n"
                f"Parámetro: {prepared['parameter']['label']}\nValores: {values_text}\n"
                f"RPM: {rpm_text} · hasta {prepared['max_cycles']} ciclos/punto · {prepared['total_budget_seconds']:g} s agregados\n"
                f"Preflight: {point_count} configuraciones válidas · 0 pasos del solver\n"
                f"Salida durable: {self.artifact_root / 'design-studies-v1' / prepared['project_id']}\n\n"
                "Cada punto usará el EXPLORATORY integrado con identidad y checkpoint propios. Los resultados periódicos se clasifican por punto; la corrida terminada o el estado COMPLETE del estudio no garantiza periodicidad ni validación.")
            if QMessageBox.question(self,"Confirmar estudio paramétrico",summary,
                QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,QMessageBox.StandardButton.No)!=QMessageBox.StandardButton.Yes:
                self.status_text="ESTUDIO NO INICIADO · PREFLIGHT COMPLETO";self.checkpoint_summary="0 pasos del solver; no se creó estudio"
                self._release_task();return
        except Exception as exc:
            self._failed(f"{type(exc).__name__}: {exc}");return
        self.cancel_event=threading.Event();self.progress_latest=None
        design_count=len(prepared.get("design_points",prepared.get("points",[])))
        self.output.appendPlainText(f"Estudio paramétrico EXPLORATORY iniciado · {prepared['study_id']} · {design_count} diseños.")
        if prepared.get("design_method")=="RPM_ENVELOPE_V1":
            self.task=run_background(run_design_rpm_envelope,prepared,
                reuse_runs=[item["path"] for item in self.context.project.get("result_references",[])],
                cancel_event=self.cancel_event,progress=self.progress_signal.emit,on_done=self._done,on_error=self._failed)
        else:
            self.task=run_background(run_design_study,prepared,artifact_root=self.artifact_root,
                history_references=self.context.project.get("result_references",[]),
                cancel_event=self.cancel_event,progress=self.progress_signal.emit,
                on_done=self._done,on_error=self._failed)
        self.status_text="CORRIENDO ESTUDIO DE DISEÑO";self.checkpoint_summary="manifiesto y checkpoint independientes por diseño"
        self.cancel.setEnabled(True);self.start.setEnabled(False);self.resume.setEnabled(False)
        self.sweep.setEnabled(False);self.resume_sweep.setEnabled(False);self.state_changed.emit()

    def resume_design_study(self, reference=None):
        if self.task is not None:return
        from ..design_study import (load_prepared_study,run_design_study,
            load_prepared_rpm_envelope,run_design_rpm_envelope)
        if reference is None:
            selected,_=QFileDialog.getOpenFileName(self,"Reanudar estudio paramétrico",str(self.artifact_root),"Estudio Dino (study.json)")
        else:
            selected=reference.get("path") if isinstance(reference,dict) else None
        if not selected:return
        try:
            manifest_path=Path(selected).resolve()
            raw=manifest_path.read_bytes()
            saved_manifest=json.loads(raw.decode("utf-8"))
            if reference is not None:
                registered=next((item for item in self.context.project.get("study_references",[])
                    if isinstance(item,dict) and item==reference),None)
                if registered is None:
                    raise ValueError("el manifiesto seleccionado ya no está registrado en el proyecto activo")
                if hashlib.sha256(raw).hexdigest()!=reference.get("manifest_sha256"):
                    raise ValueError("el SHA-256 no coincide con la referencia guardada en el proyecto")
                if (saved_manifest.get("schema")!=reference.get("schema") or
                        saved_manifest.get("study_id")!=reference.get("study_id") or
                        saved_manifest.get("project_id")!=reference.get("source_project_id")):
                    raise ValueError("la identidad del manifiesto no coincide con la referencia del proyecto")
            envelope=saved_manifest.get("design_method")=="RPM_ENVELOPE_V1"
            prepared=(load_prepared_rpm_envelope(manifest_path) if envelope
                else load_prepared_study(manifest_path))
            if prepared["project_id"]!=self.context.project["project_id"]:
                raise ValueError("el estudio pertenece a otro proyecto")
            if prepared["variant_label"]!=(self.context.selected_variant or "base"):
                raise ValueError("seleccioná la variante baseline con la que se creó el estudio")
            if identity(self._engine())!=prepared["baseline_engine_identity_sha256"]:
                raise ValueError("la configuración actual no coincide con el baseline guardado")
            if envelope:
                extension=0
                prompt=(f"Estudio {prepared['study_id']} · {prepared['combination_count']} combinaciones diseño × RPM\n"
                    f"Presupuesto agregado original: {prepared['total_budget_seconds']:g} s\n"
                    "No se agrega presupuesto. Cada sub-barrido verificará sus bindings y checkpoints antes de continuar.")
            else:
                extension,ok=QInputDialog.getInt(self,"Presupuesto de reanudación",
                    "Segundos adicionales para el estudio (se suman al límite total y por punto):",60,0,600)
                if not ok:return
                prompt=(f"Estudio {prepared['study_id']} · {len(prepared['points'])} diseños\n"
                    f"Presupuesto adicional: {extension} s\nLos puntos completos se reutilizan sólo tras verificar sus artifacts; los interrumpidos continúan desde checkpoints válidos.")
            answer=QMessageBox.question(self,"Confirmar reanudación",prompt,
                QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,QMessageBox.StandardButton.No)
            if answer!=QMessageBox.StandardButton.Yes:return
            # The study file is its durable index; continuation always writes beside it.
            self.artifact_root=(Path(prepared["artifact_root"]) if envelope else manifest_path.parents[3])
            from .preferences import set_artifact_root,repository_root_containing
            if repository_root_containing(self.artifact_root) is not None:
                raise ValueError("el artifact root del estudio está dentro del repositorio")
            expected=(self.artifact_root/"design-studies-v1"/prepared["project_id"]/prepared["study_id"])
            if envelope:expected=expected/"rpm-envelope"
            expected=expected/"study.json"
            if manifest_path!=expected.resolve():raise ValueError("ruta del manifiesto no coincide con su raíz durable")
            set_artifact_root(self.artifact_root);self.root_label.setText(str(self.artifact_root))
            self.history.artifact_root=self.artifact_root;self.artifact_root_changed.emit(self.artifact_root)
        except Exception as exc:
            QMessageBox.warning(self,"Reanudación bloqueada",f"FAIL-CLOSED: {type(exc).__name__}: {exc}");return
        self.cancel_event=threading.Event()
        if envelope:
            self.active_sweep_settings={"rpms":prepared["rpms"],"max_cycles":prepared["max_cycles"],
                "total_budget_seconds":prepared["total_budget_seconds"]}
            self.task=run_background(run_design_rpm_envelope,prepared,resume=True,
                reuse_runs=[item["path"] for item in self.context.project.get("result_references",[])],
                cancel_event=self.cancel_event,progress=self.progress_signal.emit,
                on_done=self._done,on_error=self._failed)
        else:
            self.active_sweep_settings={"rpms":[prepared["rpm"]],
                "max_cycles":prepared["max_cycles"],"total_budget_seconds":max(1,extension)}
            self.task=run_background(run_design_study,prepared,artifact_root=self.artifact_root,
                cancel_event=self.cancel_event,progress=self.progress_signal.emit,resume=True,
                additional_budget_seconds=extension,
                history_references=self.context.project.get("result_references",[]),
                on_done=self._done,on_error=self._failed)
        self.elapsed_timer.start();self.status_text="REANUDANDO ESTUDIO";self.checkpoint_summary="checkpoints por diseño"
        self.cancel.setEnabled(True);self.start.setEnabled(False);self.resume.setEnabled(False)
        self.sweep.setEnabled(False);self.resume_sweep.setEnabled(False);self.state_changed.emit()

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
                total_budget_seconds=binding["total_budget_seconds"],memory_limit_mib=binding["memory_limit_mib"],control_policy=binding.get('control_policy'))
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
        self.active_sweep_settings=prepared
        self.task=run_background(run_power_curve,document,project_id=binding["project_id"],
            variant_label=binding["variant_label"],artifact_root=binding["artifact_root"],
            start_rpm=binding["rpms"][0],stop_rpm=binding["rpms"][-1],
            step_rpm=(binding["rpms"][1]-binding["rpms"][0] if len(binding["rpms"])>1 else 1),
            max_cycles=binding["max_cycles"],point_budget_seconds=binding["point_budget_seconds"],
            total_budget_seconds=binding["total_budget_seconds"],memory_limit_mib=binding["memory_limit_mib"],
            sweep_id=manifest_path.parent.name,resume=True,cancel_event=self.cancel_event,
            reuse_runs=[item['path'] for item in binding.get('reuse_runs',[])],
            control_policy=binding.get('control_policy'),
            progress=self.progress_signal.emit,on_done=self._done,on_error=self._failed)
        self.elapsed_timer.start();self.status_text="REANUDANDO BARRIDO";self.checkpoint_summary="se validan hashes y checkpoints antes de continuar"
        self.cancel.setEnabled(True);self.start.setEnabled(False);self.resume.setEnabled(False);self.sweep.setEnabled(False);self.resume_sweep.setEnabled(False)
        self.state_changed.emit()

    def _progress(self,row):
        self.progress_latest=dict(row);self.status_text="En ejecución"
        if "point_index" in row:
            if "point" in row:
                self.output.appendPlainText(f"Punto {row['point_index']}/{row['point_count']} · {format_number(row['rpm'])} RPM · {state_label(row['point'].get('classification'))}")
            elif "solver_progress" in row:
                p=row["solver_progress"]
                self.output.appendPlainText(f"{format_number(row['rpm'])} RPM · ciclo {p['cycle']} · {format_number(p['angle_deg'])}° · memoria {format_number(p['rss_bytes']/1048576)} MiB")
        else:
            self.output.appendPlainText(f"Ciclo {row['cycle']} · {format_number(row['angle_deg'])}° · memoria {format_number(row['rss_bytes']/1048576)} MiB")
        self.state_changed.emit()

    def _done(self,result):
        import hashlib,json
        self.last_result_project_id=result.get('bindings',{}).get('project_id',self.context.project['project_id'])
        self.last_result_paths=[str(p['run_directory']) for p in result.get('points',[]) if p.get('run_directory')]
        if not self.last_result_paths and result.get('artifact_directory'):
            directory=Path(result['artifact_directory']);result_file=directory/'result.json'
            self.last_result_paths=[str(directory)]
            try:
                raw=result_file.read_bytes();stored=json.loads(raw)
                if stored.get('bindings',{}).get('project_id')==self.context.project['project_id']:
                    self.context.add_result_reference(dict(path=str(result_file),
                        identity_sha256=stored['bindings']['identity_sha256'],
                        artifact_sha256=hashlib.sha256(raw).hexdigest(),classification=stored['classification']))
            except (OSError,ValueError,KeyError) as exc:
                self.output.appendPlainText('Resultado conservado; no se pudo vincular al proyecto: '+str(exc))
        self.view_result.setEnabled(bool(self.last_result_paths))
        self.status_text=f"Terminada · {state_label(result.get('classification','clasificación no informada'))}"
        if isinstance(result.get("points"),list):
            if result.get('bindings',{}).get('project_id')==self.context.project['project_id']:
                import hashlib
                refs=self.context.project['result_references'];known={r['path'] for r in refs}
                for point in result['points']:
                    if not point.get('run_directory') or not point.get('result_artifact_sha256'):continue
                    path=Path(point['run_directory'])/'result.json'
                    if str(path) in known:continue
                    if hashlib.sha256(path.read_bytes()).hexdigest()!=point['result_artifact_sha256']:
                        self.output.appendPlainText('Referencia rechazada: cambió la identidad del resultado.');continue
                    refs.append(dict(path=str(path),identity_sha256=point['identity_sha256'],
                        artifact_sha256=point['result_artifact_sha256'],classification=point['classification']))
                    known.add(str(path));self.context.dirty=True
            complete=sum(row.get("status")=="COMPLETE" for row in result["points"])
            interrupted=sum(row.get("status")=="INTERRUPTED_CHECKPOINTED" for row in result["points"])
            not_started=sum(row.get("status")=="NOT_STARTED" for row in result["points"])
            self.checkpoint_summary=(f"{complete} puntos ejecutados · {interrupted} interrumpidos con checkpoint · "
                f"{not_started} sin iniciar · {state_label(result.get('curve_availability','curva parcial'))}")
            if result.get("schema")=="DINO_PARAMETRIC_DESIGN_STUDY_RESULT_V1":
                self.output.appendPlainText(f"Estudio paramétrico {result.get('study_id')} · {result.get('status')} · {complete} diseños con corrida terminada · {interrupted} interrumpidos con checkpoint · {not_started} no iniciados. Los estados periódicos se muestran por separado; EXPLORATORY, sin validación predictiva.")
                manifest_value=result.get("design_study_manifest")
                if manifest_value:
                    try:
                        import hashlib,json
                        manifest_path=Path(manifest_value).resolve()
                        raw=manifest_path.read_bytes();manifest=json.loads(raw.decode("utf-8"))
                        project_id=self.context.project["project_id"]
                        if (manifest.get("schema")!="DINO_PARAMETRIC_DESIGN_STUDY_V1" or
                                manifest.get("study_id")!=result.get("study_id") or
                                manifest.get("project_id")!=project_id or
                                result.get("bindings",{}).get("project_id")!=project_id):
                            raise ValueError("el manifiesto no coincide con el estudio o proyecto activo")
                        reference={"path":str(manifest_path),"study_id":manifest["study_id"],
                            "manifest_sha256":hashlib.sha256(raw).hexdigest(),
                            "schema":manifest["schema"],"source_project_id":manifest["project_id"]}
                        self.context.add_study_reference(reference)
                        self.design_study_completed.emit(reference)
                    except Exception as exc:
                        self.output.appendPlainText(f"Estudio completado, pero no se pudo registrar su manifiesto en el proyecto: {type(exc).__name__}: {exc}")
            else:
                self.output.appendPlainText(f"Barrido finalizado · {complete} puntos completados · {interrupted} con checkpoint · {not_started} sin iniciar · {state_label(result.get('curve_availability','curva parcial'))}. Evidencia íntegra disponible en Resultados y Trazabilidad.")
        else:
            cycles=result.get('cycles_completed',0)
            periodicity=state_label(result.get('periodicity','periodicidad no evaluada'))
            classification=state_label(result.get('classification','clasificación no informada'))
            self.checkpoint_summary=f"{cycles} ciclos guardados · {periodicity}"
            self.output.appendPlainText(f"Corrida terminada · {classification} · {cycles} ciclos guardados · {periodicity}. Evidencia íntegra disponible en Resultados y Trazabilidad.")
        self._release_task()

    def _failed(self,message):
        self.status_text="Bloqueada · ejecución detenida por error";self.checkpoint_summary="evidencia previa conservada"
        self.output.appendPlainText("Ejecución detenida por error: "+state_label(message)); self._release_task()

    def _release_task(self):
        self.task=None; self.cancel_event=None; self.cancel.setEnabled(False); self.refresh();self.refresh_history_requested.emit();self.state_changed.emit()

    def cancel_run(self):
        if self.cancel_event is not None:
            self.cancel_event.set();self.status_text="CANCELACIÓN SOLICITADA"; self.output.appendPlainText("Cancelación solicitada; se detendrá en un límite de paso y conservará el último checkpoint completo.");self.state_changed.emit()
