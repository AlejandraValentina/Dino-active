"""Integrated Dino Desktop workbench for the native single-cylinder 4T API.

The 4T workspace shares Desktop project storage, variant context, charts and
artifact conventions while keeping the DINO4T_API_V1 configuration/result
contracts intact.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import threading
import uuid

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal, Qt
from PySide6.QtWidgets import (QApplication, QComboBox, QDoubleSpinBox, QFileDialog,
    QFormLayout, QHBoxLayout, QLabel, QMainWindow, QMessageBox, QPushButton,
    QSpinBox, QTabWidget, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
    QListWidget, QListWidgetItem, QHeaderView, QLineEdit, QSplitter, QAbstractItemView)
from PySide6.QtGui import QDesktopServices
from PySide6.QtCore import QUrl

from .. import engine_platform
from ..engine_project import load_project, save_project
from .context import DesktopContext
from .four_stroke_project import SCHEMA, project_from_example
from .four_stroke_comparison import build_comparison, ComparisonIneligible
from .plot import CurvePlot
from .preferences import artifact_root
from .presentation import format_number, state_label

SECTION_LABELS={"geometry":"Cilindro y geometría","intake_valve":"Válvula de admisión",
    "exhaust_valve":"Válvula de escape","intake_duct":"Admisión","exhaust_duct":"Escape",
    "ambient":"Ambiente","combustion":"Combustión","heat_transfer":"Transferencia de calor",
    "friction":"Pérdidas mecánicas","operating_point":"Punto operativo",
    "initial_conditions":"Condiciones iniciales","numerics":"Numerics"}
FIELD_LABELS={"provenance":"procedencia","bore_mm":"diámetro (mm)","stroke_mm":"carrera (mm)",
    "rod_mm":"biela (mm)","compression_ratio":"relación de compresión","count":"cantidad",
    "diameter_mm":"diámetro (mm)","open_deg":"apertura (°)","close_deg":"cierre (°)",
    "duration_deg":"duración (°)","max_lift_mm":"alzada máxima (mm)","seat_mm":"asiento (mm)",
    "throat_mm":"garganta (mm)","length_mm":"longitud (mm)","start_diameter_mm":"diámetro inicial (mm)",
    "end_diameter_mm":"diámetro final (mm)","wall_temperature_K":"temperatura de pared (K)",
    "intake_pressure_pa":"presión de admisión (Pa)","exhaust_pressure_pa":"presión de escape (Pa)",
    "intake_temperature_K":"temperatura de admisión (K)","exhaust_temperature_K":"temperatura de escape (K)",
    "reference_area":"área de referencia","l_over_d":"alzada / diámetro","forward":"flujo directo",
    "reverse":"flujo inverso","start_deg":"inicio de combustión (°)","efficiency":"eficiencia de combustión",
    "fuel":"combustible","zone_model":"modelo de zonas","restriction_model":"modelo de restricción",
    "limiter":"limitador espacial","max_cycles":"máximo de ciclos","rpm":"rpm",
    "equivalence_ratio":"relación de equivalencia","dx_mm":"espaciamiento (mm)",
    "cfl":"CFL","max_dtheta_deg":"paso angular máximo (°)"}
DISPLAY_VALUES={"SYNTHETIC_ASSUMPTION":"Supuesto sintético","STANDARD_V1":"Estándar V1",
    "MEASURED":"Medido","DOCUMENTED":"Documentado","CALIBRATED":"Calibrado",
    "two_zone_equilibrium":"Equilibrio de dos zonas","single_zone":"Zona única",
    "WOSCHNI_1967":"Woschni (1967)","CHEN_FLYNN":"Chen–Flynn","IC8H18":"Isooctano (IC8H18)",
    "harmonic":"Alzada armónica","Wiebe":"Wiebe","WIEBE_SINGLE_ZONE_V1":"Wiebe, zona única V1",
    "V1":"V1","V2":"V2","minmod":"Minmod","van_leer":"Van Leer","mc":"MC",
    "unlimited_central":"Centrado sin limitador"}
REVERSE_DISPLAY_VALUES={shown:raw for raw,shown in DISPLAY_VALUES.items()}
STATUS_LABELS={"completed":"Ejecución terminada","incomplete":"Ejecución incompleta",
    "failed_numerical":"Fallo numérico","PERIODIC_CONVERGED":"Periódico",
    "NOT_CONVERGED":"No periódico","NOT_REPORTED":"No informado"}
SCIENTIFIC_LABELS={"NOT_PERFORMED":"No realizado","NOT_CLAIMED":"No declarado",
    "NOT_REPORTED":"No informado","L1_ENGINEERING_RUN":"Corrida de ingeniería L1"}
ERROR_LABELS={"CONFIG_INVALID":"Configuración rechazada","OPTION_INVALID":"Opción de ejecución inválida",
    "MODEL_OUT_OF_VALIDITY":"Punto fuera del dominio del modelo","WALL_LIMIT":"Límite de tiempo alcanzado",
    "NOT_PERIODIC":"Ciclo completado sin periodicidad","CANCELLED":"Cancelación solicitada",
    "INTERNAL":"Error interno de ejecución"}
METRIC_LABELS={"work_net_J":"Trabajo neto por ciclo","work_gross_J":"Trabajo indicado bruto",
    "work_pumping_J":"Trabajo de bombeo","imep_net_bar":"IMEP neta","imep_gross_bar":"IMEP bruta",
    "pmep_bar":"PMEP","fmep_bar":"FMEP","bmep_bar":"BMEP de freno",
    "indicated_power_kW":"Potencia indicada","indicated_torque_Nm":"Torque indicado",
    "brake_power_kW":"Potencia de freno","brake_torque_Nm":"Torque de freno",
    "mechanical_efficiency":"Eficiencia mecánica","volumetric_efficiency_intake_valve":"Eficiencia volumétrica en válvula",
    "volumetric_efficiency_system_inlet":"Eficiencia volumétrica del sistema","air_per_cycle_mg":"Aire por ciclo",
    "fuel_per_cycle_mg":"Combustible por ciclo","fuel_burned_per_cycle_mg":"Combustible quemado por ciclo",
    "trapped_mass_mg":"Masa atrapada","residual_gas_fraction_ivc":"Fracción residual en IVC",
    "trapping_efficiency":"Eficiencia de atrapamiento","fresh_short_circuit_fraction":"Fracción de carga fresca en cortocircuito",
    "intake_backflow_mg":"Retorno por admisión","exhaust_backflow_mg":"Retorno por escape",
    "indicated_fuel_conversion_efficiency":"Conversión del combustible indicada","brake_fuel_conversion_efficiency":"Conversión del combustible al freno",
    "isfc_g_kWh":"ISFC","bsfc_g_kWh":"BSFC","heat_loss_J":"Pérdida de calor",
    "heat_loss_fraction_of_fuel_energy":"Fracción de energía del combustible perdida como calor",
    "p_max_bar":"Presión máxima","theta_p_max_deg":"Ángulo de presión máxima",
    "T_max_K":"Temperatura máxima","T_burned_max_K":"Temperatura máxima de gases quemados",
    "T_unburned_max_K":"Temperatura máxima de gases no quemados",
    "exhaust_valve_mean_enthalpy_temperature_K":"Temperatura media de entalpía en válvula de escape",
    "lower_heating_value_MJ_kg":"Poder calorífico inferior","mass_balance":"Balance de masa",
    "thermo_fit_range_exceeded":"Rango de ajuste termoquímico excedido","steps":"Pasos aceptados",
    "rejected_steps":"Pasos rechazados","CA10_deg":"CA10","CA50_deg":"CA50","CA90_deg":"CA90"}


def _walk_scalars(value, path=()):
    if isinstance(value, dict):
        for key, child in value.items():
            yield from _walk_scalars(child, path + (str(key),))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _walk_scalars(child, path + (str(index),))
    else:
        yield path, value


def _get_path(document, path):
    value = document
    for key in path:
        value = value[int(key)] if isinstance(value, list) else value[key]
    return value


def _set_path(document, path, value):
    target = document
    for key in path[:-1]:
        target = target[int(key)] if isinstance(target, list) else target[key]
    last = path[-1]
    if isinstance(target, list): target[int(last)] = value
    else: target[last] = value


def _as_typed(text, original, path):
    if isinstance(original,str) and original in DISPLAY_VALUES:
        text=REVERSE_DISPLAY_VALUES.get(text.strip(),text)
    if isinstance(original, bool):
        value = text.strip().lower()
        if value not in {"true", "false"}: raise ValueError(f"{path}: ingresar true o false")
        return value == "true"
    if isinstance(original, int):
        return int(text.strip())
    if isinstance(original, float):
        value = float(text.strip().replace(",", "."))
        if not math.isfinite(value): raise ValueError(f"{path}: el valor debe ser finito")
        return value
    return text


def _path_label(path):
    first=SECTION_LABELS.get(path[0],path[0].replace("_"," ").capitalize()) if path else ""
    tail=[]
    for part in path[1:]:
        if part.isdigit():tail.append(f"sección {int(part)+1}")
        else:tail.append(FIELD_LABELS.get(part,part.replace("_"," ")))
    return " · ".join([first,*tail])


def _curve_binding(config):
    from .four_stroke_artifacts import curve_binding
    return curve_binding(config)


def _outcome_label(summary):
    if summary.get("status")!="completed":return "Incompleto"
    return "Periódico" if summary.get("periodicity",{}).get("status")=="PERIODIC_CONVERGED" else "Transitorio · no periódico"


class FourStrokeConfigEditor(QWidget):
    configApplied = Signal()

    def __init__(self, context):
        super().__init__(); self.context=context; self.tables={}; self._loading=False
        root=QVBoxLayout(self);self.notice=QLabel();self.notice.setWordWrap(True);root.addWidget(self.notice)
        self.sections=QTabWidget();root.addWidget(self.sections,1)
        self.validate_button=QPushButton("Validar y aplicar configuración")
        self.validate_button.clicked.connect(self.apply);root.addWidget(self.validate_button)
        self.context.changed.connect(self.refresh);self.refresh()

    def refresh(self):
        config=self.context.engine();self._loading=True
        while self.sections.count(): self.sections.removeTab(0)
        self.tables.clear()
        for section, value in config.items():
            if section in {"schema", "identifier", "description"}: continue
            table=QTableWidget();table.setColumnCount(3);table.setHorizontalHeaderLabels(["Parámetro del esquema 4T", "Valor", "Procedencia del grupo"])
            table.setAlternatingRowColors(True);table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectItems)
            rows=list(_walk_scalars(value,(section,)));table.setRowCount(len(rows));table.verticalHeader().hide()
            table.horizontalHeader().setSectionResizeMode(0,QHeaderView.ResizeMode.Stretch)
            table.horizontalHeader().setSectionResizeMode(1,QHeaderView.ResizeMode.ResizeToContents)
            table.horizontalHeader().setSectionResizeMode(2,QHeaderView.ResizeMode.ResizeToContents)
            for row,(path,original) in enumerate(rows):
                key=QTableWidgetItem(_path_label(path));key.setFlags(key.flags() & ~Qt.ItemFlag.ItemIsEditable)
                cell=QTableWidgetItem(self._display(original));cell.setData(256,path)
                provenance=value.get("provenance","sin provenance declarada por el esquema") if isinstance(value,dict) else "sin provenance declarada por el esquema"
                provenance_item=QTableWidgetItem(DISPLAY_VALUES.get(str(provenance),str(provenance)));provenance_item.setFlags(provenance_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                table.setItem(row,0,key);table.setItem(row,1,cell);table.setItem(row,2,provenance_item)
            self.tables[section]=table;self.sections.addTab(table,SECTION_LABELS.get(section,section.replace("_"," ").title()))
        checked=engine_platform.validate_config("4T",config)
        unknown=checked.get("unknown_keys",[])
        label="Válida para ejecución" if checked["valid"] and not unknown else "Requiere corrección"
        sources={}
        for group in ("geometry","intake_valve","exhaust_valve","intake_duct","exhaust_duct","ambient","combustion","heat_transfer","friction"):
            sources[group]=config.get(group,{}).get("provenance","sin declarar")
        provenance=" · ".join(f"{SECTION_LABELS.get(key,key)}: {DISPLAY_VALUES.get(value,value)}" for key,value in sources.items())
        self.notice.setText(f"{config.get('identifier','Motor 4T')} · {label} · {provenance}\n"
            "El formulario usa el esquema versionado de configuración 4T. No agrega ni elimina válvulas, secciones o parámetros fuera del esquema del solver. Una configuración ejecutable no equivale a validación física.")
        self._loading=False

    @staticmethod
    def _display(value):
        if isinstance(value,float): return format(value,".12g")
        if isinstance(value,bool): return "true" if value else "false"
        if value is None: return ""
        return DISPLAY_VALUES.get(str(value),str(value))

    def apply(self):
        if self._loading:return
        doc=json.loads(json.dumps(self.context.engine()))
        try:
            for table in self.tables.values():
                for row in range(table.rowCount()):
                    item=table.item(row,1);path=item.data(256);original=_get_path(self.context.engine(),path)
                    _set_path(doc,path,_as_typed(item.text(),original,_path_label(path)))
            checked=engine_platform.validate_config("4T",doc)
            if not checked["valid"] or checked["unknown_keys"]:
                details="\n".join(item.get("message",item.get("path","clave desconocida")) for item in checked["issues"])
                if checked["unknown_keys"]: details += "\nClaves no reconocidas: "+", ".join(checked["unknown_keys"])
                raise ValueError(details or "La API 4T rechazó la configuración.")
            self.context.replace_engine(doc)
            self.notice.setText(f"Configuración válida · SHA-256 {checked['config_sha256']} · La API confirma que es ejecutable; no expresa adecuación física ni validación experimental.")
            self.configApplied.emit()
        except Exception as exc:
            QMessageBox.warning(self,"Configuración 4T inválida",str(exc))


class _RunSignals(QObject):
    progress=Signal(dict);finished=Signal(dict);failed=Signal(str)


class _RunTask(QRunnable):
    def __init__(self,config,out_dir,max_cycles,wall_limit):
        super().__init__();self.config=config;self.out_dir=out_dir;self.max_cycles=max_cycles;self.wall_limit=wall_limit;self.signals=_RunSignals();self.cancel_event=threading.Event()
    def run(self):
        try:
            result=engine_platform.run_api("4T",self.config,out_dir=self.out_dir,max_cycles=self.max_cycles,
                wall_limit_s=self.wall_limit,on_progress=self.signals.progress.emit,cancel_event=self.cancel_event)
            engine_platform.check_result("4T",result);self.signals.finished.emit(result)
        except Exception as exc:self.signals.failed.emit(f"{type(exc).__name__}: {exc}")


class FourStrokeSimulation(QWidget):
    runFinished=Signal(dict)
    def __init__(self,context):
        super().__init__();self.context=context;self.thread_pool=QThreadPool.globalInstance();self.task=None;self.run_dir=None
        root=QVBoxLayout(self);form=QFormLayout();root.addLayout(form)
        self.rpm=QDoubleSpinBox();self.rpm.setRange(1,30000);self.rpm.setDecimals(0);self.rpm.setSuffix(" rpm")
        self.rpm.setValue(float(context.engine()["operating_point"]["rpm"]))
        self.cycles=QSpinBox();self.cycles.setRange(1,100);self.cycles.setValue(int(context.engine()["numerics"]["max_cycles"]))
        self.wall=QSpinBox();self.wall.setRange(10,600);self.wall.setValue(120);self.wall.setSuffix(" s")
        form.addRow("Punto operativo",self.rpm);form.addRow("Máximo de ciclos",self.cycles);form.addRow("Límite de pared",self.wall)
        row=QHBoxLayout();root.addLayout(row);self.start=QPushButton("Ejecutar punto 4T");self.start.clicked.connect(self.execute);row.addWidget(self.start);self.cancel=QPushButton("Cancelar al final del ciclo");self.cancel.setEnabled(False);self.cancel.clicked.connect(self.cancel_run);row.addWidget(self.cancel)
        self.progress=QLabel("Listo · solo se ejecuta mediante DINO4T_API_V1");self.progress.setWordWrap(True);root.addWidget(self.progress)
        self.last_label=QLabel();self.last_label.setWordWrap(True);root.addWidget(self.last_label);root.addStretch(1)

    def execute(self):
        if self.task is not None:return
        config=json.loads(json.dumps(self.context.engine()));config["operating_point"]["rpm"]=float(self.rpm.value())
        checked=engine_platform.validate_config("4T",config)
        if not checked["valid"] or checked["unknown_keys"]:
            QMessageBox.warning(self,"Preflight 4T","La configuración requiere correcciones antes de ejecutarse.");return
        run_id=uuid.uuid4().hex;project_key=hashlib.sha256(self.context.project["project_id"].encode("utf-8")).hexdigest()[:20]
        self.run_variant_id=self.context.selected_variant or "";self.run_project_id=self.context.project["project_id"]
        root=artifact_root()/"dino-4t-desktop-v1"/project_key/run_id
        out=root/"artifacts";out.mkdir(parents=True,exist_ok=False);self.run_dir=root
        self.task=_RunTask(config,out,int(self.cycles.value()),float(self.wall.value()))
        self.task.signals.progress.connect(self._progress);self.task.signals.finished.connect(self._finished);self.task.signals.failed.connect(self._failed)
        self.start.setEnabled(False);self.cancel.setEnabled(True);self.progress.setText(f"Ejecutando {run_id} · DINO4T_API_V1 · límite {self.wall.value()} s")
        self.thread_pool.start(self.task)

    def _progress(self,record):
        suffix=" · se detendrá al completar este ciclo" if self.task is not None and self.task.cancel_event.is_set() else ""
        self.progress.setText(f"Ciclo {record.get('cycle')} · trabajo neto {format_number(record.get('work_net_J'))} J · p máx. {format_number(record.get('p_max_bar'))} bar{suffix}")

    def cancel_run(self):
        if self.task is None:return
        self.task.cancel_event.set();self.cancel.setEnabled(False)
        self.progress.setText("Cancelación solicitada · se conservarán los ciclos completos al cerrar el actual; no hay checkpoint serializable.")

    def _finished(self,envelope):
        task=self.task;self.task=None;self.start.setEnabled(True);self.cancel.setEnabled(False)
        summary=envelope.get("summary")
        if summary is None:
            error=envelope.get("error") or {};record={"schema":"DINO4T_DESKTOP_API_ERROR_V1","run_id":self.run_dir.name,
                "api":envelope.get("api"),"error":error,
                "config_identity_sha256":engine_platform.validate_config("4T",task.config).get("config_sha256") if task else None,
                "input_configuration":task.config if task else None,
                "persisted_artifact":str((self.run_dir/"api-error.json").resolve())}
            (self.run_dir/"api-error.json").write_text(json.dumps(record,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
            code=error.get("code","UNKNOWN");label=ERROR_LABELS.get(code,"Error de ejecución")
            self.progress.setText(f"{label} · {error.get('message','sin detalle')} · registro: {record['persisted_artifact']}")
            return
        from .four_stroke_artifacts import publish_desktop_run
        ref=publish_desktop_run(self.run_dir,envelope,self.run_project_id,self.run_variant_id)
        result_hash=ref["result_sha256"]
        self.context.add_run_reference(ref)
        self.runFinished.emit(ref)
        if summary.get("termination")=="cancelled_by_user":state="CANCELADA AL FIN DE CICLO · primario parcial conservado"
        else:state="PERIÓDICO · simulación no validada" if summary["periodicity"]["status"]=="PERIODIC_CONVERGED" else "NO PERIÓDICO · resultado incompleto para prestaciones"
        if envelope.get("error"):
            code=envelope["error"].get("code");state+=f" · {ERROR_LABELS.get(code,'Aviso de ejecución')}"
        self.progress.setText(f"{state} · {summary['cycles_run']} ciclos · {summary['evidence_level']}")
        if (envelope.get("error") or {}).get("code")=="RESULT_INVALID":
            self.last_label.setText("Datos calculados conservados · contrato o dominio incompatible; no son prestaciones elegibles.")
            return
        final=summary.get("final_cycle") or {}
        self.last_label.setText(f"RPM {format_number(summary['operating_point']['rpm'])} · Potencia freno {format_number(final.get('brake_power_kW'))} kW · Torque {format_number(final.get('brake_torque_Nm'))} N·m\nValidación experimental: {summary['claims'].get('experimental_validation')} · Capacidad predictiva: {summary['claims'].get('predictive_capability')} · SHA-256 {result_hash}")

    def _failed(self,message):
        self.task=None;self.start.setEnabled(True);self.cancel.setEnabled(False)
        if self.run_dir is not None:
            record={"schema":"DINO4T_DESKTOP_INTERNAL_ERROR_V1","run_id":self.run_dir.name,"message":message}
            (self.run_dir/"internal-error.json").write_text(json.dumps(record,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        self.progress.setText("Error de integración 4T: "+message)


class FourStrokeResults(QWidget):
    def __init__(self,context):
        super().__init__();self.context=context;self.loaded={};root=QVBoxLayout(self)
        top=QHBoxLayout();root.addLayout(top);self.refresh_button=QPushButton("Actualizar historial");self.refresh_button.clicked.connect(self.refresh);top.addWidget(self.refresh_button)
        self.import_button=QPushButton("Importar histórico 4T…");self.import_button.clicked.connect(self.import_historical);top.addWidget(self.import_button)
        self.export_button=QPushButton("Exportar CSV");self.export_button.clicked.connect(self.export_csv);top.addWidget(self.export_button)
        self.report_button=QPushButton("Informe técnico HTML");self.report_button.clicked.connect(self.export_report);top.addWidget(self.report_button);top.addStretch()
        splitter=QSplitter();root.addWidget(splitter,1)
        self.history=QListWidget();self.history.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff);self.history.currentRowChanged.connect(self.select_run);splitter.addWidget(self.history)
        detail=QTabWidget();self.result_tabs=detail;splitter.addWidget(detail);splitter.setStretchFactor(1,1)
        self.summary=QTableWidget(0,3);self.summary.setHorizontalHeaderLabels(["Indicador", "Valor", "Unidad"]);self.summary.horizontalHeader().setSectionResizeMode(0,QHeaderView.ResizeMode.Stretch);self.summary.horizontalHeader().setSectionResizeMode(1,QHeaderView.ResizeMode.Fixed);self.summary.horizontalHeader().setSectionResizeMode(2,QHeaderView.ResizeMode.Fixed);self.summary.setColumnWidth(1,130);self.summary.setColumnWidth(2,76);self.summary.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded);detail.addTab(self.summary,"Métricas del último ciclo")
        self.trace_table=QTableWidget(0,2);self.trace_table.setHorizontalHeaderLabels(["Procedencia","Dato verificado"]);self.trace_table.horizontalHeader().setSectionResizeMode(0,QHeaderView.ResizeMode.ResizeToContents);self.trace_table.horizontalHeader().setSectionResizeMode(1,QHeaderView.ResizeMode.Stretch);self.trace_table.setWordWrap(True);self.trace_table.verticalHeader().hide();detail.addTab(self.trace_table,"Trazabilidad")
        self.power_plot=CurvePlot();detail.addTab(self.power_plot,"Potencia de freno")
        self.torque_plot=CurvePlot();detail.addTab(self.torque_plot,"Torque de freno")
        self.pressure_plot=CurvePlot();detail.addTab(self.pressure_plot,"Presiones de cilindro y conductos")
        self.compare_tab=QWidget();compare_layout=QVBoxLayout(self.compare_tab);self.comparison=None
        controls=QHBoxLayout();self.compare_a=QComboBox();self.compare_b=QComboBox();self.compare_button=QPushButton("Comparar corridas");self.compare_button.clicked.connect(self.compare);controls.addWidget(QLabel("A"));controls.addWidget(self.compare_a,1);controls.addWidget(QLabel("B"));controls.addWidget(self.compare_b,1);controls.addWidget(self.compare_button);compare_layout.addLayout(controls)
        self.compare_status=QLabel("La comparación requiere dos diseños distintos, corridas periódicas y contexto de cálculo idéntico.");self.compare_status.setWordWrap(True);compare_layout.addWidget(self.compare_status)
        self.compare_table=QTableWidget(0,5);self.compare_table.setHorizontalHeaderLabels(["Métrica","A","B","Δ absoluto · B − A","Δ relativo a A"]);self.compare_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch);compare_layout.addWidget(self.compare_table,1)
        exports=QHBoxLayout();self.compare_json_button=QPushButton("Exportar ficha A/B JSON");self.compare_json_button.clicked.connect(self.export_comparison_json);self.compare_json_button.setEnabled(False);exports.addWidget(self.compare_json_button);self.compare_csv_button=QPushButton("Exportar diferencias CSV");self.compare_csv_button.clicked.connect(self.export_comparison_csv);self.compare_csv_button.setEnabled(False);exports.addWidget(self.compare_csv_button);self.compare_report_button=QPushButton("Informe técnico A/B HTML");self.compare_report_button.clicked.connect(self.export_comparison_report);self.compare_report_button.setEnabled(False);exports.addWidget(self.compare_report_button);compare_layout.addLayout(exports);detail.addTab(self.compare_tab,"Comparar")
        self.compare_a.currentIndexChanged.connect(self._invalidate_comparison)
        self.compare_b.currentIndexChanged.connect(self._invalidate_comparison)
        self.context.changed.connect(self.refresh);self.refresh()

    def _read(self,ref):
        from .four_stroke_artifacts import assess_run_reference
        return assess_run_reference(ref)

    def refresh(self):
        refs=self.context.project["run_references"];self.history.clear();self.loaded.clear()
        self.assessments={};self.legacy_loaded={}
        self.summary.setRowCount(0);self.trace_table.setRowCount(0);self.pressure_plot.set_series([])
        self._invalidate_comparison();self.compare_a.clear();self.compare_b.clear()
        for index,ref in enumerate(refs):
            assessed=self._read(ref);self.assessments[index]=assessed
            if assessed.verified or assessed.classification=="LEGACY_UNVERIFIED":
                summary,meta=assessed.summary,assessed.meta
                outcome=_outcome_label(summary);period=summary.get("periodicity",{}).get("status","NOT_REPORTED")
                variant=ref.get("variant_id") or "Motor base"
                prefix="" if assessed.verified else "Histórico no verificado · "
                label=prefix+f"{summary['operating_point']['rpm']:.0f} rpm · {outcome} · {variant}"
                item=QListWidgetItem(label)
                item.setToolTip(f"Integridad: {assessed.classification}\nPeriodicidad: {STATUS_LABELS.get(period,period)}\nRun ID: {ref['run_id']}\n"+"; ".join(assessed.issues))
                self.history.addItem(item)
                if assessed.verified:
                    self.loaded[index]=(summary,meta,ref);self.compare_a.addItem(label,index);self.compare_b.addItem(label,index)
                else:self.legacy_loaded[index]=(summary,meta,ref)
            else:
                self.history.addItem(f"Datos conservados · {assessed.classification} · {ref.get('run_id','?')} · "+"; ".join(assessed.issues))
        if self.history.count():self.history.setCurrentRow(self.history.count()-1)
        self._refresh_plots()

    def _refresh_plots(self):
        power_groups={};torque_groups={}
        for index,(summary,meta,ref) in self.loaded.items():
            row=summary.get("final_cycle") or {};period=summary.get("periodicity",{}).get("status")
            if period!="PERIODIC_CONVERGED":continue
            rpm=float(summary["operating_point"]["rpm"]);name=ref.get("variant_id") or "Motor base"
            key=(name,meta.get("curve_binding_sha256"),json.dumps(summary["models"],sort_keys=True))
            power_groups.setdefault(key,[]).append({"rpm":rpm,"value":row.get("brake_power_kW")})
            torque_groups.setdefault(key,[]).append({"rpm":rpm,"value":row.get("brake_torque_Nm")})
        power=[{"name":key[0],"x_key":"rpm","unit":"kW","points":sorted(points,key=lambda p:p["rpm"]),"connect":len(points)>1} for key,points in power_groups.items()]
        torque=[{"name":key[0],"x_key":"rpm","unit":"N·m","points":sorted(points,key=lambda p:p["rpm"]),"connect":len(points)>1} for key,points in torque_groups.items()]
        self.power_plot.set_series(power,y_scale_mode="data_margin");self.torque_plot.set_series(torque,y_scale_mode="data_margin")

    def select_run(self,index):
        self.summary.setRowCount(0);self.trace_table.setRowCount(0);self.pressure_plot.set_series([])
        selected=self.loaded.get(index) or getattr(self,"legacy_loaded",{}).get(index)
        if selected is None:return
        summary,meta,ref=selected;final=summary.get("final_cycle") or {}
        rows=[]
        for key,value in final.items():
            label=METRIC_LABELS.get(key,key.replace("_"," ").capitalize())
            rows.append((label,value,engine_platform.indicator_unit("4T",key) or "—"))
        self.summary.setRowCount(len(rows))
        for row,(name,value,unit) in enumerate(rows):
            shown=format_number(value) if isinstance(value,(int,float)) else str(value)
            for column,text in enumerate((name,shown,unit)):
                item=QTableWidgetItem(text);item.setFlags(item.flags() & ~item.flags().ItemIsEditable);self.summary.setItem(row,column,item)
        trace_rows=(("Integridad de artefactos",self.assessments[index].classification),("Run ID",ref["run_id"]),("Estado de periodicidad",STATUS_LABELS.get(summary["periodicity"]["status"],summary["periodicity"]["status"])),
            ("Estado de ejecución",STATUS_LABELS.get(summary["status"],summary["status"])),("Nivel de evidencia",SCIENTIFIC_LABELS.get(summary.get("evidence_level"),summary.get("evidence_level"))),
            ("Calibración",SCIENTIFIC_LABELS.get(summary.get("claims",{}).get("calibration"),summary.get("claims",{}).get("calibration"))),
            ("Validación experimental",SCIENTIFIC_LABELS.get(summary.get("claims",{}).get("experimental_validation"),summary.get("claims",{}).get("experimental_validation"))),
            ("Capacidad predictiva",SCIENTIFIC_LABELS.get(summary.get("claims",{}).get("predictive_capability"),summary.get("claims",{}).get("predictive_capability"))),("SHA-256 de configuración",summary["config_sha256"]),
            ("Commit del código",summary.get("code_commit")),("Código empaquetado modificado",summary.get("code_dirty")),
            ("Artefacto de resumen",meta["summary_path"]),("SHA-256 del resultado",ref["result_sha256"]))
        self.trace_table.setRowCount(len(trace_rows))
        for row,(name,value) in enumerate(trace_rows):
            for column,text in enumerate((name,str(value))):
                item=QTableWidgetItem(text);item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable);self.trace_table.setItem(row,column,item)
        pressure=[];self.result_tabs.setTabText(4,"Presiones y ondas del último ciclo")
        try:
            import io
            assessed=self.assessments[index]
            raw=assessed.snapshot.get("raw",{}).get("trace") if assessed.verified else None
            trace=list(csv.DictReader(io.StringIO(raw.decode("utf-8")))) if raw is not None else []
            for key,label in (("p","Cilindro"),("p_intake_port","Admisión"),("p_exhaust_port","Escape")):
                points=[]
                for point in trace:
                    try:value=float(point[key])/100000.0;theta=float(point["theta"])
                    except (KeyError,ValueError,TypeError):continue
                    if math.isfinite(value) and math.isfinite(theta):points.append({"theta":theta,"value":value})
                if points:pressure.append({"name":label,"x_key":"theta","x_label":"Ángulo de cigüeñal (°)","unit":"bar","points":points})
            period=summary["periodicity"]["status"]
            title="Presiones de último ciclo" if period=="PERIODIC_CONVERGED" else "Presión transitoria · no periódica"
            self.result_tabs.setTabText(4,title)
        except (OSError,KeyError,ValueError):
            pressure=[]
        self.pressure_plot.set_series(pressure,y_scale_mode="data_margin")

    def compare(self):
        self.comparison=None;self.compare_table.setRowCount(0)
        self.compare_json_button.setEnabled(False);self.compare_csv_button.setEnabled(False);self.compare_report_button.setEnabled(False)
        aidx=self.compare_a.currentData();bidx=self.compare_b.currentData()
        if aidx not in self.loaded or bidx not in self.loaded:return
        if aidx==bidx:self.compare_status.setText("Elegí dos corridas distintas para comparar.");return
        a,_,ra=self.loaded[aidx];b,_,rb=self.loaded[bidx]
        try:
            endpoint_a=self._comparison_endpoint(a,ra)
            endpoint_b=self._comparison_endpoint(b,rb)
            comparison=build_comparison(endpoint_a,endpoint_b)
        except (ComparisonIneligible, OSError, ValueError, KeyError, TypeError) as exc:
            self.compare_status.setText("No comparable: "+str(exc));return
        self.comparison=comparison
        self.compare_table.setRowCount(len(comparison["metrics"]))
        for row,metric in enumerate(comparison["metrics"]):
            relative="No definido" if metric["relative_percent_to_abs_a"] is None else format_number(metric["relative_percent_to_abs_a"])+"%"
            values=(f"{metric['label']} ({metric['unit']})",format_number(metric["a"]),format_number(metric["b"]),
                    format_number(metric["delta_b_minus_a"]),relative)
            for column,text in enumerate(values):self.compare_table.setItem(row,column,QTableWidgetItem(text))
        self.compare_status.setText(f"Diferencia del modelo 4T · {format_number(comparison['operating_point']['rpm'])} RPM exactas · contexto, modelos, numerics, versión y termodinámica coinciden · A/B periódicos · diferencias calculadas, no validadas experimentalmente · ID {comparison['comparison_id'][:12]}")
        self.compare_json_button.setEnabled(True);self.compare_csv_button.setEnabled(True);self.compare_report_button.setEnabled(True)

    def _invalidate_comparison(self,*_):
        self.comparison=None
        if not hasattr(self,"compare_table"):return
        self.compare_table.setRowCount(0)
        self.compare_json_button.setEnabled(False);self.compare_csv_button.setEnabled(False);self.compare_report_button.setEnabled(False)
        self.compare_status.setText("Seleccioná dos corridas y pulsá Comparar corridas.")

    def _comparison_endpoint(self,summary,reference):
        from .four_stroke_artifacts import require_verified_run
        return require_verified_run(reference).endpoint()

    def export_comparison_json(self):
        if not self._comparison_export_ready():return
        target,_=QFileDialog.getSaveFileName(self,"Guardar ficha A/B",str(Path.home()/"dino-4t-ab-comparison.json"),"JSON (*.json)")
        if not target:return
        if not target.lower().endswith(".json"):target+=".json"
        Path(target).write_text(json.dumps(self.comparison,ensure_ascii=False,indent=2,allow_nan=False)+"\n",encoding="utf-8")

    def export_comparison_csv(self):
        if not self._comparison_export_ready():return
        target,_=QFileDialog.getSaveFileName(self,"Exportar diferencias A/B",str(Path.home()/"dino-4t-ab-differences.csv"),"CSV (*.csv)")
        if not target:return
        if not target.lower().endswith(".csv"):target+=".csv"
        a,b=self.comparison["endpoints"]
        with open(target,"w",newline="",encoding="utf-8-sig") as stream:
            writer=csv.writer(stream);writer.writerow(["schema","comparison_id","rpm","model_id","code_commit",
                "run_a","config_sha256_a","result_sha256_a","run_b","config_sha256_b","result_sha256_b",
                "metric_key","metric","unit","a_full_precision","b_full_precision","delta_b_minus_a","relative_percent_to_abs_a",
                "comparison_policy","classification","source_qualification_a","source_qualification_b",
                "run_manifest_sha256_a","run_manifest_sha256_b","artifacts_manifest_sha256_a","artifacts_manifest_sha256_b",
                "artifact_origin_a_json","artifact_origin_b_json"])
            for row in self.comparison["metrics"]:
                writer.writerow([self.comparison["schema"],self.comparison["comparison_id"],
                    repr(self.comparison["operating_point"]["rpm"]),self.comparison["model_id"],a["code_commit"],
                    a["run_id"],a["config_sha256"],a["result_sha256"],b["run_id"],b["config_sha256"],b["result_sha256"],
                    row["key"],row["label"],row["unit"],repr(row["a"]),repr(row["b"]),repr(row["delta_b_minus_a"]),
                    "" if row["relative_percent_to_abs_a"] is None else repr(row["relative_percent_to_abs_a"]),
                    self.comparison["comparison_policy"],self.comparison["classification"],a["source_qualification"],b["source_qualification"],
                    a["run_manifest_sha256"],b["run_manifest_sha256"],a["artifacts_manifest_sha256"],b["artifacts_manifest_sha256"],
                    json.dumps(a["artifact_origin"],sort_keys=True,ensure_ascii=False),json.dumps(b["artifact_origin"],sort_keys=True,ensure_ascii=False)])

    def export_comparison_report(self):
        if not self._comparison_export_ready():return
        target,_=QFileDialog.getSaveFileName(self,"Informe técnico A/B",str(Path.home()/"dino-4t-ab-report.html"),"HTML (*.html)")
        if not target:return
        if not target.lower().endswith(".html"):target+=".html"
        from .technical_report import write_four_stroke_ab_report
        path=write_four_stroke_ab_report(target,self.comparison)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(path.resolve())))

    def _verified_export_rows(self):
        """Recheck original references before exporting any cached result."""
        from .four_stroke_artifacts import require_verified_run
        try:
            for summary,_,reference in self.loaded.values():
                current=require_verified_run(reference)
                if current.summary!=summary:raise ValueError("El resultado cambió desde su lectura")
        except (ValueError,OSError,KeyError,TypeError) as exc:
            QMessageBox.warning(self,"Procedencia no verificable",str(exc))
            return False
        return bool(self.loaded)

    def _comparison_export_ready(self):
        if self.comparison is None:return False
        try:
            by_id={reference["run_id"]:(summary,reference) for summary,_,reference in self.loaded.values()}
            endpoints=[self._comparison_endpoint(*by_id[item["run_id"]]) for item in self.comparison["endpoints"]]
            current=build_comparison(*endpoints,policy=self.comparison["comparison_policy"])
            if current["comparison_id"]!=self.comparison["comparison_id"]:
                raise ValueError("La comparación cambió desde su lectura")
        except (ValueError,OSError,KeyError,TypeError) as exc:
            self._invalidate_comparison()
            QMessageBox.warning(self,"Procedencia no verificable",str(exc))
            return False
        return True

    def export_csv(self):
        if not self._verified_export_rows():return
        target,_=QFileDialog.getSaveFileName(self,"Exportar resultados 4T",str(Path.home()/"dino-4t-results.csv"),"CSV (*.csv)")
        if not target:return
        if not target.lower().endswith(".csv"):target += ".csv"
        keys=sorted({key for summary,_,_ in self.loaded.values() for key in (summary.get("final_cycle") or {})})
        with open(target,"w",newline="",encoding="utf-8-sig") as stream:
            writer=csv.writer(stream);writer.writerow(["schema","run_id","variant_id","rpm","status","periodicity","evidence_level","config_sha256","result_sha256",*keys])
            for summary,meta,ref in self.loaded.values():
                final=summary.get("final_cycle") or {};writer.writerow([summary["schema"],ref["run_id"],ref["variant_id"],repr(summary["operating_point"]["rpm"]),summary["status"],summary["periodicity"]["status"],summary["evidence_level"],summary["config_sha256"],ref["result_sha256"],*[repr(final.get(k,"")) for k in keys]])
        QMessageBox.information(self,"CSV exportado",f"Se exportaron {len(self.loaded)} resultados con precisión de ida y procedencia.")

    def export_report(self):
        if not self._verified_export_rows():return
        target,_=QFileDialog.getSaveFileName(self,"Informe técnico 4T",str(Path.home()/"dino-4t-report.html"),"HTML (*.html)")
        if not target:return
        if not target.lower().endswith(".html"):target += ".html"
        from .technical_report import render_four_stroke_report
        report=render_four_stroke_report(self.context.project["project_id"],[
            {"summary":summary,"meta":meta,"reference":ref} for summary,meta,ref in self.loaded.values()])
        Path(target).write_text(report,encoding="utf-8")
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(Path(target).resolve())))

    def import_historical(self):
        source,_=QFileDialog.getOpenFileName(self,"Importar resumen nativo 4T",str(Path.home()),"DINO4T_OPERATING_POINT_RESULT_V1 (*.json)")
        if not source:return
        src=Path(source)
        try:
            from ..dino4t.artifacts import parse_json
            selected=parse_json(src.read_bytes())
            if selected.get("schema")=="DINO4T_RUN_REFERENCE_V2":
                from .four_stroke_artifacts import import_reference_bundle
                root=artifact_root()/"dino-4t-desktop-v1"/hashlib.sha256(self.context.project["project_id"].encode()).hexdigest()[:20]/uuid.uuid4().hex
                ref=import_reference_bundle(src,root);self.context.add_run_reference(ref)
                QMessageBox.information(self,"Referencia importada","Se verificó la cadena original de referencia, metadatos y artefactos. La integridad no acredita validación física ni autenticidad externa.")
                return
            summary_raw=src.read_bytes();summary=json.loads(summary_raw);engine_platform.check_result("4T",summary)
            config_src=src.parent/"config_resolved.json"
            if not config_src.is_file():raise ValueError("Falta config_resolved.json; no se importan resultados sin su entrada exacta.")
            config_raw=config_src.read_bytes();config=json.loads(config_raw);check=engine_platform.validate_config("4T",config)
            if not check["valid"] or check["unknown_keys"] or check["config_sha256"]!=summary["config_sha256"]:
                raise ValueError("La configuración asociada no coincide con config_sha256 del resultado.")
            run_id=uuid.uuid4().hex;root=artifact_root()/"dino-4t-desktop-v1"/hashlib.sha256(self.context.project["project_id"].encode()).hexdigest()[:20]/run_id
            artifacts=root/"artifacts";artifacts.mkdir(parents=True,exist_ok=False)
            summary_dst=artifacts/"summary.json";config_dst=artifacts/"config_resolved.json"
            shutil.copy2(src,summary_dst);shutil.copy2(config_src,config_dst)
            trace_src=src.parent/"trace_last_cycle.csv";trace_dst=artifacts/"trace_last_cycle.csv"
            if trace_src.is_file():shutil.copy2(trace_src,trace_dst)
            digest=hashlib.sha256(summary_dst.read_bytes()).hexdigest()
            meta={"schema":"DINO4T_DESKTOP_RUN_V1","run_id":run_id,"project_id":self.context.project["project_id"],
                "variant_id":"","api":"DINO4T_API_V1","result_sha256":digest,"config_sha256":summary["config_sha256"],
                "config_identity_sha256":check["config_sha256"],"summary_path":str(summary_dst.resolve()),
                "curve_binding_sha256":_curve_binding(config),
                "config_path":str(config_dst.resolve()),"trace_path":str(trace_dst.resolve()) if trace_dst.exists() else "",
                "status":summary["status"],"periodicity_status":summary["periodicity"]["status"],
                "evidence_level":summary["evidence_level"],"claims":summary["claims"],
                "imported_from":str(src.resolve()),"source_result_sha256":hashlib.sha256(summary_raw).hexdigest()}
            (root/"run.json").write_text(json.dumps(meta,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
            self.context.add_run_reference({"run_id":run_id,"path":str(summary_dst.resolve()),"result_sha256":digest,
                "config_sha256":summary["config_sha256"],"status":summary["status"],
                "periodicity_status":summary["periodicity"]["status"],"variant_id":""})
            QMessageBox.information(self,"Histórico conservado","LEGACY_UNVERIFIED: copia conservada sin vínculo original completo de trazas/código. No habilita curvas ni comparación verificadas. La fuente original permanece intacta.")
        except Exception as exc:QMessageBox.warning(self,"Importación rechazada",f"{type(exc).__name__}: {exc}")


class FourStrokeDesktopWindow(QMainWindow):
    """Cycle-specific workspace hosted by the Dino Desktop executable."""
    def __init__(self,project=None,parent_2t=None,path=None):
        super().__init__();self.context=DesktopContext(project or project_from_example());self.context.path=Path(path) if path else None;self.parent_2t=parent_2t
        from .theme import stylesheet
        self.setStyleSheet(stylesheet())
        self.setWindowTitle(f"Dino Desktop · 4T · {self.context.project['project_id']}");self.resize(1240,860);self.setMinimumSize(900,620)
        central=QWidget();root=QVBoxLayout(central);root.setContentsMargins(12,10,12,10)
        header=QHBoxLayout();self.title=QLabel(f"DINO DESKTOP  ·  MOTOR 4T  ·  {self.context.project['project_id']}");self.title.setObjectName("title");header.addWidget(self.title,1)
        for text,callback in (("Guardar",self.save),("Abrir…",self.open_project),("2T",self.switch_to_2t)):
            button=QPushButton(text);button.clicked.connect(callback);header.addWidget(button)
        root.addLayout(header)
        self.tabs=QTabWidget();root.addWidget(self.tabs,1)
        self.model_page=self._build_model_page();self.tabs.addTab(self.model_page,"MODELO")
        self.simulation=FourStrokeSimulation(self.context);self.tabs.addTab(self.simulation,"SIMULAR")
        self.results=FourStrokeResults(self.context);self.tabs.addTab(self.results,"RESULTADOS")
        self.context.changed.connect(self._refresh_title);self.setCentralWidget(central)
        self._refresh_title()

    def _build_model_page(self):
        page=QWidget();layout=QHBoxLayout(page);split=QSplitter();layout.addWidget(split)
        left=QWidget();left_layout=QVBoxLayout(left);self.variant_list=QListWidget();left_layout.addWidget(QLabel("Variantes del proyecto"));left_layout.addWidget(self.variant_list,1)
        for label,callback in (("Motor base",lambda:self.context.select_variant(None)),("Duplicar…",self.duplicate_variant),("Eliminar",self.delete_variant)):
            button=QPushButton(label);button.clicked.connect(callback);left_layout.addWidget(button)
        split.addWidget(left)
        self.editor=FourStrokeConfigEditor(self.context);split.addWidget(self.editor);split.setStretchFactor(1,1)
        self.variant_list.currentTextChanged.connect(self._select_variant);self.context.changed.connect(self._refresh_variants)
        self._refresh_variants();return page

    def _refresh_variants(self):
        current=self.context.selected_variant;self.variant_list.blockSignals(True);self.variant_list.clear()
        for name in sorted(self.context.project["variants"]):self.variant_list.addItem(name)
        if current is not None:
            matches=self.variant_list.findItems(current,Qt.MatchFlag.MatchExactly)
            if matches:self.variant_list.setCurrentItem(matches[0])
        self.variant_list.blockSignals(False)

    def _select_variant(self,name):
        if name in self.context.project["variants"]:self.context.select_variant(name)

    def duplicate_variant(self):
        from PySide6.QtWidgets import QInputDialog
        name,ok=QInputDialog.getText(self,"Duplicar diseño 4T","Nombre de la variante:")
        if ok:
            try:self.context.duplicate_variant(self.context.selected_variant,name)
            except Exception as exc:QMessageBox.warning(self,"No se pudo duplicar",str(exc))

    def delete_variant(self):
        name=self.context.selected_variant
        if name is None:return
        try:self.context.delete_variant(name)
        except Exception as exc:QMessageBox.warning(self,"No se pudo eliminar",str(exc))

    def _refresh_title(self):
        mark=" · cambios sin guardar" if self.context.dirty else ""
        self.setWindowTitle(f"Dino Desktop · 4T · {self.context.project['project_id']}{mark}")
        self.title.setText(f"DINO DESKTOP  ·  MOTOR 4T  ·  {self.context.project['project_id']}{mark}")

    def save(self):
        if self.context.path is None:
            path,_=QFileDialog.getSaveFileName(self,"Guardar proyecto 4T",str(Path.home()/"nuevo-4t.dino.json"),"Dino project (*.dino.json)")
            if not path:return False
            if not path.endswith(".json"):path+=".dino.json"
            self.context.path=Path(path)
        try:
            save_project(self.context.path,self.context.project);self.context.dirty=False;self.context.changed.emit();return True
        except Exception as exc:QMessageBox.warning(self,"No se pudo guardar",str(exc));return False

    def open_project(self):
        if self._guard_active_run():return
        path,_=QFileDialog.getOpenFileName(self,"Abrir proyecto Dino",str(Path.home()),"Dino project (*.json)")
        if not path:return
        try:
            project=load_project(path)
            if project.get("engine_family","2T")=="4T":
                if not self._confirm_discard():return
                self.context.replace_project(project,Path(path));self.editor.refresh();self.results.refresh()
            else:
                if not self._confirm_discard():return
                from .app import DinoDesktopWindow
                window=DinoDesktopWindow(project);window.show();self.close()
        except Exception as exc:QMessageBox.warning(self,"No se pudo abrir",str(exc))

    def switch_to_2t(self):
        if self._guard_active_run():return
        from PySide6.QtWidgets import QFileDialog
        path,_=QFileDialog.getOpenFileName(self,"Abrir proyecto Dino 2T",str(Path.home()),"Dino 2T (*.json)")
        if not path:return
        try:
            project=load_project(path)
            if project.get("engine_family","2T")!="2T":raise ValueError("Elegí un proyecto 2T.")
            if not self._confirm_discard():return
            from .app import DinoDesktopWindow
            window=DinoDesktopWindow(project);window.show();self.close()
        except Exception as exc:QMessageBox.warning(self,"No se pudo cambiar a 2T",str(exc))

    def _confirm_discard(self):
        if not self.context.dirty:return True
        answer=QMessageBox.question(self,"Cambios sin guardar","¿Guardar los cambios antes de cambiar de proyecto?",QMessageBox.StandardButton.Save|QMessageBox.StandardButton.Discard|QMessageBox.StandardButton.Cancel,QMessageBox.StandardButton.Save)
        if answer==QMessageBox.StandardButton.Cancel:return False
        return self.save() if answer==QMessageBox.StandardButton.Save else True

    def _guard_active_run(self):
        if self.simulation.task is None:return False
        self.simulation.cancel_run()
        QMessageBox.information(self,"Ejecución 4T en curso",
            "Se solicitó detener al completar el ciclo actual. El proyecto no se cerrará hasta guardar el resultado parcial; volvé a intentar la acción cuando termine.")
        return True

    def closeEvent(self,event):
        if self._guard_active_run():event.ignore();return
        if self.context.dirty:
            result=QMessageBox.question(self,"Cambios sin guardar","¿Guardar el proyecto antes de cerrar?",QMessageBox.StandardButton.Save|QMessageBox.StandardButton.Discard|QMessageBox.StandardButton.Cancel,QMessageBox.StandardButton.Save)
            if result==QMessageBox.StandardButton.Cancel:event.ignore();return
            if result==QMessageBox.StandardButton.Save and not self.save():event.ignore();return
        super().closeEvent(event)
        if self.parent_2t is not None:self.parent_2t.close()
