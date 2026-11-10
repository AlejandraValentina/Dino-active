"""Bounded native 4T RPM sweep using DINO4T_API_V1.

This intentionally does not use the synthetic 4T 0D reference model, does not
interpolate missing points and makes no experimental/predictive claims.
Each operating point is published through the existing native Desktop run
reference, preserving project provenance without changing its frozen schema.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import threading
import uuid

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QSpinBox, QTableWidget, QTableWidgetItem, QHeaderView, QGroupBox,
    QFormLayout, QTabWidget, QMessageBox, QFileDialog,
)

from .. import engine_platform
from .four_stroke_desktop import artifact_root
from .four_stroke_results import FourStrokeCurve


NATIVE_CURVE_SCHEMA = "DINO4T_NATIVE_RPM_CURVE_V1"
NATIVE_RPM_UI_RANGE = (500, 15000)
NATIVE_MAX_POINTS = 30


def plan_native_rpms(start, stop, step):
    """Operational UI guard, not a physical/validated RPM envelope."""
    if any(type(x) is not int for x in (start, stop, step)):
        raise ValueError("RPM e incremento deben ser enteros.")
    low, high = NATIVE_RPM_UI_RANGE
    if start < low or stop > high or start >= stop or step <= 0:
        raise ValueError(f"Elegí RPM ascendentes entre {low} y {high}; incremento positivo.")
    if (stop-start) % step:
        raise ValueError("El incremento debe alcanzar exactamente la RPM final.")
    count = (stop-start)//step+1
    if count > NATIVE_MAX_POINTS:
        raise ValueError(f"Máximo {NATIVE_MAX_POINTS} puntos por barrido 4T.")
    return list(range(start, stop+1, step))



def load_native_curve_series(path, context):
    """Reopen a saved curve, re-verifying every plotted point from primary artifacts.

    The sidecar is a locator, not a trusted source of power/torque values.
    In particular, edited CSV/JSON cannot upgrade a nonperiodic run to VERIFIED.
    """
    from .four_stroke_artifacts import REFERENCE_SCHEMA, assess_run_reference, curve_binding

    path = Path(path).resolve()
    if path.name != "series.json" or not path.is_file() or path.stat().st_size > 2 * 1024 * 1024:
        raise ValueError("Seleccioná un series.json nativo válido (máximo 2 MiB).")
    raw = json.loads(path.read_text(encoding="utf-8"))
    if (not isinstance(raw, dict) or raw.get("schema") != NATIVE_CURVE_SCHEMA
            or raw.get("source") != "DINO4T_API_V1"
            or raw.get("state") not in ("COMPLETE", "PARTIAL", "CANCELLED", "FAILED")):
        raise ValueError("Contrato de curva nativa 4T inválido o todavía en ejecución.")
    if raw.get("claims") != {"experimental_validation":"NOT_PERFORMED",
                              "predictive_capability":"NOT_CLAIMED"}:
        raise ValueError("Las declaraciones científicas de la curva no son las originales.")
    if raw.get("project_id") != context.project["project_id"]:
        raise ValueError("La serie pertenece a otro proyecto.")
    config = context.engine()
    if raw.get("config_sha256") != engine_platform.identity("4T", config):
        raise ValueError("La configuración 4T cambió; esta serie no está vigente.")
    rpms = raw.get("rpms")
    if (not isinstance(rpms, list) or len(rpms) < 2
            or plan_native_rpms(rpms[0], rpms[-1], rpms[1] - rpms[0]) != rpms):
        raise ValueError("Secuencia RPM de la serie inválida.")
    records = raw.get("rows")
    if not isinstance(records, list) or len(records) > len(rpms):
        raise ValueError("La serie contiene puntos inconsistentes.")
    if raw["state"] == "COMPLETE" and len(records) != len(rpms):
        raise ValueError("Una curva completa no puede omitir puntos.")
    out = []
    binding = curve_binding(config)
    for i, record in enumerate(records):
        if not isinstance(record, dict) or record.get("rpm") != rpms[i]:
            raise ValueError("Orden de puntos RPM inconsistente.")
        rpm = rpms[i]
        run_dir = (path.parent/f"point-{i+1:02d}-{rpm}").resolve()
        if Path(record.get("run_path", "")).resolve() != run_dir:
            raise ValueError("La serie refiere una carpeta ajena a su origen.")
        row = {"rpm":rpm, "state":record.get("state", "UNKNOWN"),
               "brake_power_kW":None, "brake_torque_Nm":None,
               "reason":record.get("reason", ""), "run_path":str(run_dir),
               "reference":None}
        if record.get("state") == "PERIODIC_CONVERGED":
            try:
                ref_path = run_dir/"reference.json"
                reference = json.loads(ref_path.read_text(encoding="utf-8"))
                if reference.get("schema") != REFERENCE_SCHEMA:
                    raise ValueError("Referencia original 4T no verificada.")
                for key in ("path", "run_manifest_path"):
                    rel = reference.get(key)
                    if not isinstance(rel, str) or not rel.startswith("./"):
                        raise ValueError("Ruta de referencia no portable.")
                    dest = (run_dir/rel[2:]).resolve()
                    if not dest.is_relative_to(run_dir):
                        raise ValueError("La referencia escapa del directorio de corrida.")
                    reference[key] = str(dest)
                verified = assess_run_reference(reference)
                if not verified.verified or verified.meta.get("curve_binding_sha256") != binding:
                    raise ValueError("Primario 4T inválido o ajeno a esta configuración.")
                summary = verified.summary
                final = summary.get("final_cycle") or {}
                power = final.get("brake_power_kW")
                torque = final.get("brake_torque_Nm")
                if (summary.get("periodicity", {}).get("status") != "PERIODIC_CONVERGED"
                        or summary.get("operating_point", {}).get("rpm") != rpm
                        or any(type(v) not in (int,float) or not math.isfinite(v)
                               for v in (power,torque))
                        or not math.isclose(power,record.get("brake_power_kW",float("nan")),rel_tol=1e-12,abs_tol=1e-12)
                        or not math.isclose(torque,record.get("brake_torque_Nm",float("nan")),rel_tol=1e-12,abs_tol=1e-12)):
                    raise ValueError("Punto no coincide con su primario verificado.")
                row.update(brake_power_kW=power,brake_torque_Nm=torque,reference=reference)
            except (OSError,ValueError,KeyError,TypeError) as exc:
                row.update(state="CORRUPT",reason=f"{type(exc).__name__}: {exc}")
        out.append(row)
    if raw["state"] == "COMPLETE" and any(row["state"] != "PERIODIC_CONVERGED" for row in out):
        raise ValueError("No se puede abrir como completa una curva con puntos no verificados.")
    return {"state":raw["state"],"rows":out,"rpms":rpms,"folder":str(path.parent)}


class _NativeCurveSignals(QObject):
    progress = Signal(object)
    point = Signal(object)
    completed = Signal(object)


class _NativeCurveTask(QRunnable):
    """Serialized 4T API points with cooperative cancellation at cycle boundaries."""
    def __init__(self, config, project_id, variant, rpms, max_cycles, wall_limit, folder):
        super().__init__()
        self.setAutoDelete(False)
        self.signals = _NativeCurveSignals()
        self.cancel_event = threading.Event()
        self.token = uuid.uuid4().hex
        self.config = deepcopy(config)
        self.project_id = project_id
        self.variant = variant
        self.rpms = list(rpms)
        self.max_cycles = int(max_cycles)
        self.wall_limit = float(wall_limit)
        self.folder = Path(folder)
        self.rows = []

    def _save(self, state):
        payload = {
            "schema": NATIVE_CURVE_SCHEMA,
            "state": state,
            "project_id": self.project_id,
            "config_sha256": engine_platform.identity("4T", self.config),
            "rpms": self.rpms,
            "rows": [{k: value for k, value in row.items() if k != "reference"} for row in self.rows],
            "source": "DINO4T_API_V1",
            "claims": {"experimental_validation": "NOT_PERFORMED",
                       "predictive_capability": "NOT_CLAIMED"},
        }
        pending = self.folder/"series.json.tmp"
        pending.write_text(json.dumps(payload, indent=2, ensure_ascii=False,
                                      allow_nan=False)+"\n", encoding="utf-8")
        pending.replace(self.folder/"series.json")

    def run(self):
        state = "INCOMPLETE"
        try:
            self.folder.mkdir(parents=True, exist_ok=False)
            self._save("RUNNING")
            from .four_stroke_artifacts import publish_desktop_run
            for index, rpm in enumerate(self.rpms):
                if self.cancel_event.is_set():
                    state = "CANCELLED"
                    break
                config = deepcopy(self.config)
                config["operating_point"]["rpm"] = float(rpm)
                checked = engine_platform.validate_config("4T", config)
                if not checked["valid"] or checked["unknown_keys"]:
                    raise ValueError(f"{rpm} RPM: configuración 4T incompatible: {checked['issues']}")
                run_dir = self.folder/f"point-{index+1:02d}-{rpm}"
                run_dir.mkdir(parents=True, exist_ok=False)
                self.signals.progress.emit({"rpm":rpm, "index":index+1,
                                            "total":len(self.rpms)})
                try:
                    def on_cycle(event):
                        if isinstance(event,dict) and 'cycle' in event:
                            self.signals.progress.emit({'rpm':rpm,'index':index+1,
                                                        'total':len(self.rpms),'cycle':event['cycle']})
                    envelope = engine_platform.run_api(
                        "4T", config, out_dir=run_dir/"artifacts",
                        max_cycles=self.max_cycles, wall_limit_s=self.wall_limit,
                        cancel_event=self.cancel_event, progress=on_cycle,
                    )
                    summary = envelope.get("summary")
                    if summary is not None:
                        engine_platform.check_result("4T", envelope)
                    reference = None
                    status = "NO_RESULT"
                    power = torque = None
                    reason = str((envelope.get("error") or {}).get("code") or "")
                    if summary is not None:
                        reference = publish_desktop_run(
                            run_dir, envelope, self.project_id, self.variant,
                        )
                        periodicity = summary.get("periodicity") or {}
                        status = str(periodicity.get("status") or "NOT_REPORTED")
                        if (status == "PERIODIC_CONVERGED"
                                and not envelope.get("error")
                                and not (envelope.get("result_validation") or {}).get("issues")):
                            final = summary.get("final_cycle") or {}
                            power = final.get("brake_power_kW")
                            torque = final.get("brake_torque_Nm")
                            if not all(type(v) in (int,float) and math.isfinite(v)
                                       for v in (power,torque)):
                                power = torque = None
                                status = "NUMERICAL_INVALID"
                    row = {"rpm": rpm, "state": status,
                           "brake_power_kW": power,
                           "brake_torque_Nm": torque,
                           "reason": reason,
                           "run_path": str(run_dir),
                           "reference": reference}
                except Exception as exc:
                    row = {"rpm":rpm, "state":"ERROR", "brake_power_kW":None,
                           "brake_torque_Nm":None, "reason":f"{type(exc).__name__}: {exc}",
                           "run_path":str(run_dir), "reference":None}
                self.rows.append(row)
                self._save("RUNNING")
                self.signals.point.emit(row)
                if self.cancel_event.is_set():
                    state = "CANCELLED"
                    break
            else:
                state = ("COMPLETE" if len(self.rows)==len(self.rpms)
                         and all(row["state"]=="PERIODIC_CONVERGED" for row in self.rows)
                         else "PARTIAL")
        except Exception as exc:
            state = "FAILED"
            self.signals.progress.emit({"error":f"{type(exc).__name__}: {exc}"})
        finally:
            if self.folder.is_dir():
                try:self._save(state)
                except Exception as exc:
                    state="FAILED"
                    self.signals.progress.emit({"error":f"No se pudo registrar la curva: {exc}"})
            self.signals.completed.emit({
                "token":self.token, "state":state,
                "rows":list(self.rows),
                "folder":str(self.folder),
                "rpms":self.rpms,
            })


class NativeFourStrokeCurvePage(QWidget):
    """Native 4T RPM grid, displaying only independently converged power points."""
    runningChanged = Signal(bool)

    def __init__(self, context, native_simulation, parent=None):
        super().__init__(parent)
        self.setObjectName("nativeFourStrokeCurvePage")
        self.context = context
        self.native_simulation = native_simulation
        self.task = None
        self._token = None
        self._rows = []
        self._source_project_id = None
        self._source_config_sha256 = None
        root = QVBoxLayout(self)
        notice = QLabel(
            "4T NATIVO · DINO4T_API_V1 · barrido exploratorio no validado. "
            "500–15.000 RPM es un rango de interfaz, NO un dominio de fiabilidad "
            "física demostrado. Cada punto requiere convergencia propia."
        )
        notice.setObjectName("nativeFourStrokeCurveNotice")
        notice.setWordWrap(True)
        root.addWidget(notice)
        controls = QGroupBox("Curva de potencia y torque · 4T nativo")
        form = QFormLayout(controls)
        row = QHBoxLayout()
        self.start_rpm = QSpinBox();self.start_rpm.setObjectName("nativeCurveStartRpm")
        self.end_rpm = QSpinBox();self.end_rpm.setObjectName("nativeCurveEndRpm")
        self.step_rpm = QSpinBox();self.step_rpm.setObjectName("nativeCurveStepRpm")
        for item in (self.start_rpm,self.end_rpm):
            item.setRange(*NATIVE_RPM_UI_RANGE);item.setSuffix(" RPM")
        self.start_rpm.setValue(1000);self.end_rpm.setValue(13000)
        self.step_rpm.setRange(1,5000);self.step_rpm.setValue(500);self.step_rpm.setSuffix(" RPM")
        for label,item in (("Inicio",self.start_rpm),("Fin",self.end_rpm),("Paso",self.step_rpm)):
            row.addWidget(QLabel(label));row.addWidget(item)
        self.cycles = QSpinBox();self.cycles.setRange(1,100);self.cycles.setValue(24)
        self.wall = QSpinBox();self.wall.setRange(10,600);self.wall.setValue(120)
        row.addWidget(QLabel("Ciclos máx."));row.addWidget(self.cycles)
        row.addWidget(QLabel("Tiempo/punto (s)"));row.addWidget(self.wall)
        form.addRow(row)
        commands = QHBoxLayout()
        self.start_button = QPushButton("Calcular curva nativa")
        self.start_button.setObjectName("nativeCurveRun")
        self.start_button.clicked.connect(self.start_curve)
        commands.addWidget(self.start_button)
        self.cancel_button = QPushButton("Cancelar")
        self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(self.cancel)
        commands.addWidget(self.cancel_button)
        self.open_button=QPushButton('Abrir curva guardada…')
        self.open_button.setObjectName('nativeCurveOpen')
        self.open_button.clicked.connect(self.open_curve)
        commands.addWidget(self.open_button)
        commands.addStretch(1)
        form.addRow(commands)
        root.addWidget(controls)
        self.status = QLabel("Sin barrido nativo 4T. Los resultados no convergidos no se grafican.")
        self.status.setWordWrap(True)
        root.addWidget(self.status)
        self.table = QTableWidget(0,4)
        self.table.setHorizontalHeaderLabels(["RPM","Periodicidad","Potencia freno [kW]","Torque freno [N·m]"])
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        root.addWidget(self.table,1)
        plots = QTabWidget()
        self.power_plot = FourStrokeCurve("Potencia de freno 4T nativo","RPM","kW")
        self.torque_plot = FourStrokeCurve("Torque de freno 4T nativo","RPM","N·m")
        # Only disconnected sample markers: never interpolate through omitted RPM.
        self.power_plot.connect_points = False
        self.torque_plot.connect_points = False
        plots.addTab(self.power_plot,"Potencia")
        plots.addTab(self.torque_plot,"Torque")
        root.addWidget(plots,1)
        self.context.changed.connect(self._check_stale)

    @property
    def running(self):
        return self.task is not None

    def start_curve(self):
        if self.running or self.native_simulation.task is not None:
            self.status.setText("Ya hay una ejecución 4T activa.")
            return
        try:
            rpms=plan_native_rpms(
                self.start_rpm.value(),self.end_rpm.value(),self.step_rpm.value()
            )
            config=deepcopy(self.context.engine())
            validated=engine_platform.validate_config("4T",config)
            if not validated["valid"] or validated["unknown_keys"]:
                raise ValueError("Configuración nativa 4T inválida.")
            project_id=self.context.project["project_id"]
            variant=self.context.selected_variant or ""
            project_key=hashlib.sha256(project_id.encode("utf-8")).hexdigest()[:20]
            directory=(artifact_root()/"dino-4t-native-curves"/project_key/
                       (datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-")+uuid.uuid4().hex[:10]))
            if str(directory.resolve()).upper().startswith("C:\\"):
                raise ValueError("Elegí una raíz de resultados en E: para esta campaña.")
            from ..storage_preflight import check_storage_requirements
            # One independent primary bundle per RPM, with reserved disk headroom.
            check_storage_requirements([(directory,len(rpms)*64*1024**2)])
            task=_NativeCurveTask(config,project_id,variant,rpms,
                                  self.cycles.value(),self.wall.value(),directory)
            self._source_project_id=project_id
            self._source_config_sha256=engine_platform.identity("4T",config)
            self.task=task;self._token=task.token
            task.signals.progress.connect(lambda event,token=task.token:self._progress(token,event))
            task.signals.point.connect(lambda record,token=task.token:self._point(token,record))
            task.signals.completed.connect(lambda result,token=task.token:self._completed(token,result))
            self._rows=[];self.table.setRowCount(0)
            self.power_plot.set_points([]);self.torque_plot.set_points([])
            self.start_button.setEnabled(False);self.cancel_button.setEnabled(True)
            self.runningChanged.emit(True)
            self.status.setText(f"Calculando {len(rpms)} puntos nativos · resultados en {directory}")
            QThreadPool.globalInstance().start(task)
        except Exception as exc:
            self.status.setText(f"No se pudo iniciar el barrido: {exc}")

    def _progress(self,token,event):
        if token!=self._token:return
        if event.get("error"):self.status.setText("Error de barrido: "+event["error"])
        elif "rpm" in event:
            cycle=f" · ciclo {event['cycle']}" if 'cycle' in event else ''
            self.status.setText(f"Ejecutando 4T nativo · {event['index']}/{event['total']} · {event['rpm']} RPM{cycle}")

    def _source_matches(self):
        if self._source_project_id != self.context.project["project_id"]:
            return False
        try:
            return (engine_platform.identity("4T",self.context.engine())
                    == self._source_config_sha256)
        except Exception:
            return False

    def _check_stale(self,*_):
        if self.task is not None and not self._source_matches():
            self.status.setText("Proyecto o configuración modificada durante la curva; no se vincularán resultados ajenos.")

    def open_curve(self):
        if self.running or self.native_simulation.task is not None:
            self.status.setText('Terminá la ejecución 4T antes de abrir otra curva.')
            return
        selected,_=QFileDialog.getOpenFileName(
            self,'Abrir curva nativa 4T',str(artifact_root()),'Curvas nativas (series.json)')
        if not selected:return
        try:
            self.load_saved_curve(selected)
        except Exception as exc:
            self.status.setText(f'No se pudo abrir la curva: {exc}')

    def load_saved_curve(self,path):
        if self.running or self.native_simulation.task is not None:
            raise RuntimeError('No se puede abrir una curva durante una ejecución activa.')
        loaded=load_native_curve_series(path,self.context)
        self._source_project_id=self.context.project['project_id']
        self._source_config_sha256=engine_platform.identity('4T',self.context.engine())
        self._rows=[]
        self.table.setRowCount(0)
        self.power_plot.set_points([]);self.torque_plot.set_points([])
        for row in loaded['rows']:
            self._display_row(row,attach=False)
        accepted=sum(1 for row in loaded['rows'] if row['state']=='PERIODIC_CONVERGED')
        self.status.setText(
            f"Curva nativa {loaded['state']} recuperada · {accepted}/{len(loaded['rows'])} "
            'puntos verificados y periódicos · otros puntos omitidos del gráfico')
        return loaded

    def _point(self,token,row):
        if token!=self._token:return
        self._display_row(row,attach=True)

    def _display_row(self,row,*,attach=False):
        self._rows.append(row)
        reference=row.get('reference')
        if attach and reference and self._source_matches():
            try:
                self.context.add_run_reference(reference)
            except Exception as exc:
                self.status.setText(f'No se pudo asociar la referencia: {exc}')
        index=self.table.rowCount()
        self.table.insertRow(index)
        for column,value in enumerate((
            row["rpm"],row["state"],
            "-" if row["brake_power_kW"] is None else f"{row['brake_power_kW']:.6g}",
            "-" if row["brake_torque_Nm"] is None else f"{row['brake_torque_Nm']:.6g}",
        )):
            self.table.setItem(index,column,QTableWidgetItem(str(value)))
        points=[row for row in self._rows if row["state"]=="PERIODIC_CONVERGED"]
        self.power_plot.set_points([(r["rpm"],r["brake_power_kW"]) for r in points
                                    if r["brake_power_kW"] is not None])
        self.torque_plot.set_points([(r["rpm"],r["brake_torque_Nm"]) for r in points
                                     if r["brake_torque_Nm"] is not None])

    def _completed(self,token,result):
        if token!=self._token:return
        self.task=None;self._token=None
        self.start_button.setEnabled(True);self.cancel_button.setEnabled(False)
        self.runningChanged.emit(False)
        self.status.setText(
            f"Curva 4T nativa {result['state']} · "
            f"{len(result['rows'])}/{len(result['rpms'])} puntos ejecutados · "
            f"solo convergidos graficados · {result['folder']}"
        )

    def cancel(self):
        if self.task is not None:
            self.task.cancel_event.set()
            self.cancel_button.setEnabled(False)
            self.status.setText("Cancelación solicitada; se detendrá al terminar el ciclo actual.")

    def shutdown(self,timeout_ms=10000):
        if self.task is None:return True
        self.cancel()
        done=QThreadPool.globalInstance().waitForDone(timeout_ms)
        if done:QApplication.processEvents()
        return done and self.task is None
