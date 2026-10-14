from __future__ import annotations
import csv,json
import math
from pathlib import Path
from PySide6.QtCore import Qt,Signal
from PySide6.QtGui import QPixmap
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QLabel,QComboBox,QPushButton,
    QFileDialog,QCheckBox,QGroupBox,QListWidget,QListWidgetItem,QTableWidget,QTableWidgetItem,QHeaderView,QMessageBox)
from .plot import CurvePlot
from .services import load_results,run_background
from .preferences import artifact_root,impl2_historical_report_candidate,settings
from ..exploratory_workflow import import_exploratory_runs

METRICS={"Potencia de freno (kW)":"brake_power","Torque (N·m)":"brake_torque","IMEP (kPa)":"IMEP","FMEP (kPa)":"FMEP","BMEP (kPa)":"BMEP","BSFC (g/kWh)":"BSFC"}

def _state_label(value):
    return {"EXPLORATORY_COMPLETE_PERIODICITY_NOT_IDENTIFIED":"Terminada · sin periodicidad identificada",
        "INTERRUPTED_CHECKPOINTED":"Interrumpida; checkpoint disponible",
        "PERIOD_1":"Periódica observada · orden 1","PERIOD_2":"Periódica observada · orden 2",
        "NOT_EVALUATED":"No evaluada","NOT_IDENTIFIABLE":"No identificable",
        "UNDEFINED":"No definido","NUMERICAL_INVALID":"Inválido numéricamente",
        "EXPLORATORY":"Exploratoria · no validada"}.get(value,value)

class ResultsPage(QWidget):
    evidence_updated=Signal()
    def __init__(self,context):
        super().__init__();self.context=context;self.dataset=None;self.source=None;self.loading=False
        root=QVBoxLayout(self);root.setContentsMargins(24,20,24,20)
        title=QLabel("Resultados y comparación");title.setObjectName('title');root.addWidget(title)
        self.source_notice=QLabel("No hay una corrida seleccionada. Elegila desde el historial o abrí datos importados; todavía no se cargó evidencia histórica.")
        self.source_notice.setWordWrap(True);self.source_notice.setObjectName("notice");root.addWidget(self.source_notice)
        explanation=QLabel("PERIOD_1 describe periodicidad observada; no representa aprobación científica PASS. Los valores no definidos quedan como huecos y no se interpolan.");explanation.setWordWrap(True);root.addWidget(explanation)
        bar=QHBoxLayout();root.addLayout(bar);self.metric_selector=QComboBox();self.metric_selector.addItems(METRICS);bar.addWidget(self.metric_selector)
        self.path_label=QLabel("Sin fuente seleccionada");self.path_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse);self.path_label.setWordWrap(True);bar.addWidget(self.path_label,1)
        actions=QHBoxLayout();root.addLayout(actions)
        browse=QPushButton("Abrir datos…");browse.clicked.connect(self.choose);actions.addWidget(browse)
        historical=QPushButton("Evidencia IMPL2 histórica…");historical.clicked.connect(self.choose_historical);actions.addWidget(historical)
        browse_runs=QPushButton("Abrir corridas EXPLORATORY…");browse_runs.clicked.connect(self.choose_exploratory);actions.addWidget(browse_runs);actions.addStretch()
        self.variants=QListWidget();self.variants.setMaximumHeight(80);self.variants.setFlow(QListWidget.Flow.LeftToRight);self.variants.setWrapping(True);root.addWidget(self.variants)
        baseline_row=QHBoxLayout();root.addLayout(baseline_row);baseline_row.addWidget(QLabel("Baseline del proyecto"));self.baseline_selector=QComboBox();baseline_row.addWidget(self.baseline_selector)
        self.baseline_notice=QLabel("La baseline identifica la referencia de comparación; las curvas usan sólo puntos realmente disponibles.");self.baseline_notice.setWordWrap(True);baseline_row.addWidget(self.baseline_notice,1)
        self.condition_notice=QLabel();self.condition_notice.setWordWrap(True);self.condition_notice.setObjectName("notice");root.addWidget(self.condition_notice)
        self.plot=CurvePlot();root.addWidget(self.plot,2)
        controls=QHBoxLayout();root.addLayout(controls)
        self.unit=QLabel();controls.addWidget(self.unit);controls.addStretch()
        export_table=QPushButton("Exportar tabla CSV");export_table.clicked.connect(self.export_csv);controls.addWidget(export_table)
        export_plot=QPushButton("Exportar gráfico PNG");export_plot.clicked.connect(self.export_png);controls.addWidget(export_plot)
        self.point_table=QTableWidget(0,8);self.point_table.setHorizontalHeaderLabels(["Variante","RPM","Clasificación","Periodicidad","Auditoría","Ciclos","Conservación","BMEP"]);self.point_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch);self.point_table.setMinimumHeight(180);self.point_table.currentCellChanged.connect(self._point_row_selected);root.addWidget(self.point_table)
        self.trace_group=QGroupBox("Señales de presión, ondas y flujo EXPLORATORY")
        trace_layout=QVBoxLayout(self.trace_group)
        trace_bar=QHBoxLayout();trace_layout.addLayout(trace_bar)
        self.trace_metric=QComboBox();self.trace_metric.currentIndexChanged.connect(self.redraw_trace);trace_bar.addWidget(self.trace_metric)
        self.trace_status=QLabel("Las trazas sólo se muestran después de re-auditar cada primario.");trace_bar.addWidget(self.trace_status,1)
        self.trace_legend=QLabel();self.trace_legend.setWordWrap(True);trace_layout.addWidget(self.trace_legend)
        self.trace_plot=CurvePlot();self.trace_plot.setMinimumHeight(220);trace_layout.addWidget(self.trace_plot)
        self.trace_map_legend=QLabel("Mapa discreto de posición × ángulo · celdas reales · sin interpolación.");self.trace_map_legend.setWordWrap(True);trace_layout.addWidget(self.trace_map_legend)
        self.trace_map=QTableWidget(0,0);self.trace_map.setObjectName("traceAngleCellMap");self.trace_map.setMinimumHeight(140);self.trace_map.setMaximumHeight(260);trace_layout.addWidget(self.trace_map)
        self.trace_group.hide();root.addWidget(self.trace_group)
        self.details=QTableWidget(0,2);self.details.setHorizontalHeaderLabels(["Detalle del punto","Valor"]);self.details.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch);self.details.setMaximumHeight(190);root.addWidget(self.details)
        self.metric_selector.currentIndexChanged.connect(self.redraw);self.variants.itemChanged.connect(self.redraw);self.plot.pointSelected.connect(self.show_point)
        self.baseline_selector.currentIndexChanged.connect(self._baseline_changed)
        self.context.changed.connect(self._project_context_changed);self._project_context_changed()

    def _project_context_changed(self,*_):
        names={"base",*self.context.project["variants"]}
        data_names=set()
        if self.dataset:
            data_names={str(row.get("variant_id")) for row in self.dataset.get("points",[]) if row.get("variant_id")};names.update(data_names)
        prefs=settings();key=f"baseline_variant/{self.context.project['project_id']}"
        preferred=prefs.value(key)
        if not preferred:preferred=self.context.selected_variant or (sorted(data_names)[0] if data_names else "base")
        self.baseline_selector.blockSignals(True);self.baseline_selector.clear();self.baseline_selector.addItem("Sin baseline",None)
        self.baseline_selector.addItem("Motor base","base")
        for name in sorted(names-{"base"}):self.baseline_selector.addItem(name,name)
        index=self.baseline_selector.findData(preferred)
        if index<0:index=self.baseline_selector.findData(self.context.selected_variant or "base")
        self.baseline_selector.setCurrentIndex(index if index>=0 else 0);self.baseline_selector.blockSignals(False)

    def _baseline_changed(self,*_):
        name=self.baseline_selector.currentData()
        prefs=settings();pref_key=f"baseline_variant/{self.context.project['project_id']}"
        if name is None:prefs.remove(pref_key)
        else:prefs.setValue(pref_key,name)
        if name is None:
            self.baseline_notice.setText("Sin baseline seleccionada. Las curvas muestran sólo los puntos realmente disponibles.");self.redraw();return
        base=self.context.project["base_engine"] if name=="base" else self.context.project["variants"].get(name)
        if base is None:
            self.baseline_notice.setText(f"Baseline {name}: configuración del proyecto no disponible; se conserva únicamente la comparación de observables cargados.");self.redraw();return
        from ..engine_variants import compare_configurations
        diffs=[]
        baseline_hashes={row.get("point_configuration_sha256") for row in (self.dataset or {}).get("points",[]) if row.get("variant_id")==name}
        baseline_matches=bool(base.get("native_configuration_sha256") and base.get("native_configuration_sha256") in baseline_hashes)
        for i in range(self.variants.count()):
            candidate=self.variants.item(i).text()
            if candidate==name or self.variants.item(i).checkState()!=Qt.CheckState.Checked:continue
            other=self.context.project["base_engine"] if candidate=="base" else self.context.project["variants"].get(candidate)
            hashes={row.get("point_configuration_sha256") for row in (self.dataset or {}).get("points",[]) if row.get("variant_id")==candidate}
            if other is not None and baseline_matches and other.get("native_configuration_sha256") in hashes:
                changes=compare_configurations(base,other);descriptions=[]
                for change in changes[:4]:
                    path=change["path"].replace("/native_configuration/","",1)
                    descriptions.append(f"{path}: {change['before']} → {change['after']} {change['unit']}")
                suffix="; …" if len(changes)>4 else ""
                diffs.append(f"{candidate}: {len(changes)} diferencias nativas ({'; '.join(descriptions)}{suffix}) · hashes coinciden")
            elif other is not None:diffs.append(f"{candidate}: corridas presentes; diff de geometría no confirmado contra sus hashes")
        self.baseline_notice.setText(f"Baseline {name} · " + ("; ".join(diffs) if diffs else ("hash de geometría de corrida verificado." if baseline_matches else "configuración actual sin hash de corrida verificable.")))
        self._update_condition_notice()
        self.redraw()

    def _update_condition_notice(self):
        if not self.dataset or not isinstance(self.dataset.get("points"),list):
            self.condition_notice.setText("Condiciones entre corridas: sin datos cargados.");return
        selected={self.variants.item(i).text() for i in range(self.variants.count()) if self.variants.item(i).checkState()==Qt.CheckState.Checked}
        points=[row for row in self.dataset["points"] if row.get("variant_id") in selected]
        fields=("rpm","fuel_id","afr_kg_air_per_kg_fuel","mesh_resolution","total_finite_volume_cells")
        differing=[]
        for key in fields:
            values={json.dumps(row.get(key),sort_keys=True) for row in points if row.get(key) is not None}
            if len(values)>1:differing.append(key)
        self.condition_notice.setText(("Advertencia: las corridas difieren en "+", ".join(differing)+"; la comparación no aísla sólo el cambio de escape." ) if differing else "Condiciones comparables disponibles en los campos reportados; los campos ausentes no se asumen iguales." )
    def choose(self):
        path,_=QFileDialog.getOpenFileName(self,"Abrir datos de resultados",str(artifact_root()),"Reportes y datos (*.json *.csv)")
        if path:self.load(Path(path))
    def choose_historical(self):
        candidate=impl2_historical_report_candidate()
        if candidate.is_file():self.load(candidate,historical=True);return
        path,_=QFileDialog.getOpenFileName(self,"Abrir evidencia IMPL2 histórica",str(artifact_root()),"Reporte IMPL2 (*.json *.csv)")
        if path:self.load(Path(path),historical=True)
    def choose_exploratory(self):
        paths,_=QFileDialog.getOpenFileNames(self,"Abrir corridas EXPLORATORY",str(artifact_root()),"Ejecución Dino (result.json)")
        if paths:self.open_runs(paths)
    def open_runs(self,paths):
        """Load one or more indexed runs through the full independent importer."""
        if paths:
            self.path_label.setText("Verificando artifacts EXPLORATORY…")
            run_background(import_exploratory_runs,paths,on_done=self._loaded_exploratory,on_error=self._exploratory_failed)
    def _loaded_exploratory(self,data):
        self.dataset=data;self.source=None;self.source_kind="EXPLORATORY";self.path_label.setText(f"{len(data['points'])} ciclos EXPLORATORY · provisional · no interpolación · no validación experimental")
        runs=sorted({str(r.get("run_id")) for r in data["points"] if r.get("run_id")})
        variants_shown=sorted({str(r.get("variant_id")) for r in data["points"]})
        self.source_notice.setText(f"Proyecto abierto: {self.context.project['project_id']} · corridas EXPLORATORY importadas: {', '.join(runs) or 'sin identificador'} · variantes: {', '.join(variants_shown)}. Son artifacts de sólo lectura y no se asocian ni guardan automáticamente en el proyecto.")
        variants=sorted({r['variant_id'] for r in data['points']});self.variants.blockSignals(True);self.variants.clear()
        for name in variants:
            item=QListWidgetItem(name);item.setFlags(item.flags()|Qt.ItemFlag.ItemIsUserCheckable);item.setCheckState(Qt.CheckState.Checked);self.variants.addItem(item)
        self._project_context_changed()
        self.variants.blockSignals(False)
        self.trace_metric.blockSignals(True);self.trace_metric.clear()
        traces=data.get("traces",[])
        common=(set.intersection(*(set(row.get("channels",{})) for row in traces)
                                 if traces else [set()]))
        options=[]
        if "cylinder_pressure_pa" in common:
            options.append(("Presión absoluta del cilindro (Pa)","cylinder_pressure_pa"))
        for key in sorted(common):
            if key.startswith("duct:exhaust:cell:") and key.endswith(":pressure_pa"):
                options.append((f"Presión absoluta escape · celda {key.split(':')[3]} (Pa)",key))
            elif key.startswith("duct:exhaust:face:") and key.endswith(":mass_flow_kg_s"):
                options.append((f"Flujo escape · cara {key.split(':')[3]} (kg/s)",key))
        for label,key in options:self.trace_metric.addItem(label,key)
        self.trace_metric.blockSignals(False)
        self.trace_group.setVisible(bool(traces and options))
        if traces and options:self.trace_status.setText("Primarios re-auditados · ángulos comunes exactos · sin interpolación")
        elif not traces:self.trace_status.setText("Los primarios seleccionados no contienen trazas de presión/flujo disponibles.")
        else:self.trace_status.setText("No hay canales de presión/flujo comunes en los primarios seleccionados.")
        if not traces or not options:
            reason="No hay trazas auditadas de presión/flujo disponibles." if not traces else "No hay canales de presión/flujo comunes para superponer."
            self.source_notice.setText(self.source_notice.text()+" "+reason)
        self.redraw();self.redraw_trace();self._redraw_trace_map();self._update_condition_notice();self.evidence_updated.emit()
    def _exploratory_failed(self,message):
        self.path_label.setText("Ejecución EXPLORATORY inválida");self.trace_group.hide();QMessageBox.warning(self,"Artifact exploratorio inválido",message)
    def load(self,path,*,historical=False):
        path=Path(path)
        if path.suffix.lower()==".json":
            try:
                raw=json.loads(path.read_text(encoding="utf-8"))
                historical=historical or raw.get("schema")=="FULL_RPM_SWEEP_V1_IMPL2_AGGREGATE_REPORT_V1"
            except (OSError,ValueError):pass
        self.loading=True;self.trace_group.hide();self.path_label.setText(f"Cargando {path}…")
        def done(data):
            self.dataset=data;self.source=path;self.source_kind="HISTORICAL_IMPL2" if historical else "IMPORTED_EXTERNAL"
            if historical:
                self.source_notice.setText("EVIDENCIA HISTÓRICA IMPL2 · sintética · importada explícitamente · no pertenece a la corrida actual de este proyecto · validación experimental no realizada.")
            else:
                self.source_notice.setText(f"Datos importados desde fuera del proyecto {self.context.project['project_id']}. Se conservan su provenance, identidades, huecos y clasificaciones originales.")
            self.path_label.setText(f"{path} · {len(data['points'])} puntos · {data['provenance']} · validación experimental {data['experimental_validation']}")
            variants=sorted({r['variant_id'] for r in data['points']});self.variants.blockSignals(True);self.variants.clear()
            for name in variants:
                item=QListWidgetItem(name);item.setFlags(item.flags()|Qt.ItemFlag.ItemIsUserCheckable);item.setCheckState(Qt.CheckState.Checked);self.variants.addItem(item)
            self.variants.blockSignals(False);self._project_context_changed();self.loading=False;self.redraw();self._baseline_changed();self.evidence_updated.emit()
        def fail(message):self.loading=False;self.path_label.setText("No se pudieron cargar los datos");QMessageBox.warning(self,"Reporte inválido",message)
        run_background(load_results,path,on_done=done,on_error=fail)
    def redraw(self,*_):
        if not self.dataset:return
        metric=METRICS[self.metric_selector.currentText()];unit=self.metric_selector.currentText().split('(')[-1].rstrip(')')
        selected={self.variants.item(i).text() for i in range(self.variants.count()) if self.variants.item(i).checkState()==Qt.CheckState.Checked}
        series=[]
        baseline=self.baseline_selector.currentData();ordered_names=sorted(selected)
        if baseline in ordered_names:ordered_names=[baseline]+[name for name in ordered_names if name!=baseline]
        for name in ordered_names:
            points=[]
            for row in sorted((r for r in self.dataset['points'] if r['variant_id']==name),key=lambda r:r['rpm']):
                status=row.get(metric+'_status');value=row.get(metric) if status=='DEFINED' else None
                points.append({"rpm":row['rpm'],"value":value,"classification":row['classification'],"status":status,"reason":row.get(metric+'_reason'),"point":row})
            series.append({"name":("Baseline · " if name==baseline else "")+name,"unit":unit,"points":points})
        self.unit.setText(f"{unit} · los estados sin valor permanecen como huecos · sin interpolación")
        self.plot.set_series(series)
        rows=sorted((r for r in self.dataset['points'] if r['variant_id'] in selected),key=lambda r:(r['variant_id'],r['rpm']))
        self.point_table.blockSignals(True);self.point_table.setRowCount(len(rows))
        for i,row in enumerate(rows):
            periodicity=row.get('periodicity')
            if periodicity is None:
                periodicity=row.get('classification') if row.get('classification') in {"PERIOD_1","PERIOD_2"} else "NOT_REPORTED"
            cons=row.get('conservation')
            if isinstance(cons,dict) and cons and all(value in ("PASS",True) for value in cons.values()):cons_state="PASS"
            elif isinstance(cons,dict) and any(value=="FAIL" or (isinstance(value,dict) and value.get("status")=="FAIL") for value in cons.values()):cons_state="FAIL"
            else:cons_state="REPORTADA" if cons else "NO REPORTADA"
            values=[row['variant_id'],row['rpm'],_state_label(row['classification']),_state_label(periodicity),
                    _state_label(row.get('audit_status','NOT_REPORTED')),row.get('cycles_completed'),cons_state,
                    row.get('BMEP') if row.get('BMEP_status')=='DEFINED' else None]
            for j,value in enumerate(values):
                item=QTableWidgetItem('—' if value is None else str(value));item.setData(Qt.ItemDataRole.UserRole,row);self.point_table.setItem(i,j,item)
        self.point_table.blockSignals(False)
        self._update_condition_notice()
    def redraw_trace(self,*_):
        if not self.dataset or self.dataset.get("schema")!="DINO_EXPLORATORY_COMPARISON_V1":
            self.trace_plot.set_series([]);self.trace_legend.setText("");return
        key=self.trace_metric.currentData()
        if not key:
            self.trace_plot.set_series([]);self.trace_legend.setText("");self._redraw_trace_map();return
        selected={self.variants.item(i).text() for i in range(self.variants.count())
                  if self.variants.item(i).checkState()==Qt.CheckState.Checked}
        series=[];labels=[]
        for trace in self.dataset.get("traces",[]):
            if trace.get("variant_id") not in selected:continue
            channel=trace.get("channels",{}).get(key)
            if not isinstance(channel,dict):continue
            name=f"{trace['variant_id']} · {trace['rpm']:g} RPM · ciclo {trace['cycle']}"
            labels.append(name)
            series.append({"name":name,"unit":channel.get("unit",""),
                "x_key":"angle_deg","x_label":"Ángulo de cigüeñal (°)",
                "points":[{"angle_deg":angle,"value":value}
                           for angle,value in zip(trace["angles_deg"],channel["values"])]})
        self.trace_plot.set_series(series,y_scale_mode="data_margin")
        self.trace_legend.setText("Series: " + " | ".join(labels) if labels else "Sin trazas disponibles")
        self._redraw_trace_map()

    def _redraw_trace_map(self):
        """Tabulate exact angle/cell observations; blank entries are never interpolated."""
        self.trace_map.clear();self.trace_map.setRowCount(0);self.trace_map.setColumnCount(0)
        if not self.dataset or self.dataset.get("schema")!="DINO_EXPLORATORY_COMPARISON_V1":return
        selected={self.variants.item(i).text() for i in range(self.variants.count()) if self.variants.item(i).checkState()==Qt.CheckState.Checked}
        key=self.trace_metric.currentData();
        if not key or not key.startswith("duct:exhaust:"):return
        family="cell" if ":cell:" in key else ("face" if ":face:" in key else None)
        if family is None:return
        suffix=key.rsplit(":",1)[-1];channels=[];angles=set()
        traces=[trace for trace in self.dataset.get("traces",[]) if trace.get("variant_id") in selected]
        for trace in traces:
            for channel,channel_doc in (trace.get("channels") or {}).items():
                if channel.startswith(f"duct:exhaust:{family}:") and channel.endswith(":"+suffix):
                    values=channel_doc.get("values",[]) if isinstance(channel_doc,dict) else channel_doc
                    channels.append((trace,channel,values));angles.update(trace.get("angles_deg",[]))
        ordered=sorted(angles);self.trace_map.setColumnCount(len(ordered)+1);self.trace_map.setRowCount(len(channels))
        self.trace_map.setHorizontalHeaderLabels(["Señal / celda"]+[f"{angle:g}°" for angle in ordered])
        observed=[float(value) for _,_,values in channels for value in values if value is not None and math.isfinite(float(value))]
        low=min(observed) if observed else None;high=max(observed) if observed else None
        for row,(trace,channel,values) in enumerate(channels):
            index=int(channel.split(":")[3]);positions=self._trace_positions(trace,family)
            position=f" · x={float(positions[index]):.6g} m" if index<len(positions) else " · posición no reportada"
            label=f"{trace.get('variant_id','variante')} · {family} {index}{position} · {trace.get('run_id','run')}"
            item=QTableWidgetItem(label);item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable);self.trace_map.setItem(row,0,item)
            value_by_angle={float(a):v for a,v in zip(trace.get("angles_deg",[]),values)}
            for col,angle in enumerate(ordered,1):
                value=value_by_angle.get(float(angle));cell=QTableWidgetItem("—" if value is None else f"{value:.6g}")
                cell.setFlags(cell.flags() & ~Qt.ItemFlag.ItemIsEditable)
                if value is not None and low is not None:
                    fraction=0.5 if high==low else (float(value)-low)/(high-low)
                    cell.setBackground(QColor(round(19+236*fraction),round(59+99*fraction),round(92-49*fraction)))
                self.trace_map.setItem(row,col,cell)
        self.trace_map_legend.setText((f"Mapa discreto posición × ángulo · escala de color {low:.6g}–{high:.6g} · cada celda es una muestra exacta; huecos sin interpolar." if observed else "Mapa discreto posición × ángulo · no hay muestras numéricas disponibles."))
        self.trace_map.setToolTip("Mapa tabular de observaciones discretas. Cada columna corresponde a un ángulo presente; los valores ausentes se dejan vacíos y no se interpolan.")

    def _trace_positions(self,trace,family):
        """Resolve positions only when the loaded run hash matches this project config exactly."""
        point=next((row for row in (self.dataset or {}).get("points",[]) if row.get("point_id")==trace.get("point_id")),None)
        variant=trace.get("variant_id");engine=(self.context.project["base_engine"] if variant=="base" else self.context.project["variants"].get(variant))
        if not point or not engine or point.get("point_configuration_sha256")!=engine.get("native_configuration_sha256"):
            return []
        duct=next((d for d in engine["native_configuration"].get("ducts",[]) if d.get("id")=="exhaust"),None)
        mesh=(duct or {}).get("mesh",{})
        return mesh.get("centers" if family=="cell" else "faces",[])
    def _point_row_selected(self,row,*_):
        if row<0 or self.point_table.item(row,0) is None:return
        data=self.point_table.item(row,0).data(Qt.ItemDataRole.UserRole)
        if data:self.show_point({"point":data,"rpm":data['rpm'],"value":None})
    def show_point(self,point):
        row=point.get('point',point)
        periodicity=row.get('periodicity')
        if periodicity is None:
            periodicity=row.get('classification') if row.get('classification') in {"PERIOD_1","PERIOD_2"} else "NOT_REPORTED"
        items=[("Proyecto abierto",self.context.project["project_id"]), ("RPM",row.get('rpm')), ("Variante",row.get('variant_id')),
            ("Modo",row.get('mode','NOT_REPORTED · historical aggregate')),
            ("Clasificación",row.get('classification')), ("Periodicidad",periodicity),
            ("Auditoría primaria",row.get('audit_status','NOT_REPORTED')),
            ("Auditoría recomputada",row.get('audit_recomputed','NOT_REPORTED')),
            ("Resultado SHA-256",row.get('result_sha256')), ("Primario SHA-256",row.get('primary_sha256')),
            ("Configuración SHA-256",row.get('point_configuration_sha256')),
            ("Checkpoint SHA-256",row.get('checkpoint_sha256')),
            ("Artifact directory",row.get('artifact_directory')),
            ("Condiciones de operación",json.dumps(row.get('operating_conditions'),ensure_ascii=False,sort_keys=True)),
            ("Ciclos completados",row.get('cycles_completed')),
            ("Métrica",row.get(METRICS[self.metric_selector.currentText()])),
            ("Estado métrica",row.get(METRICS[self.metric_selector.currentText()]+'_status')),
            ("Motivo",row.get(METRICS[self.metric_selector.currentText()]+'_reason')),
            ("Conservación",json.dumps(row.get('conservation'),ensure_ascii=False,sort_keys=True)),
            ("Hard gates",json.dumps(row.get('hard_gates'),ensure_ascii=False,sort_keys=True)),
            ("Validación experimental",row.get('experimental_validation',self.dataset.get('experimental_validation','NOT_REPORTED'))),
            ("Provenance",self.dataset['provenance'])]
        gates=row.get('hard_gates')
        if isinstance(gates,dict) and "status" not in gates:
            items.extend((f"Hard gate · {name}",json.dumps(value,ensure_ascii=False,sort_keys=True))
                         for name,value in sorted(gates.items()))
        self.details.setRowCount(len(items))
        for i,(a,b) in enumerate(items):self.details.setItem(i,0,QTableWidgetItem(str(a)));self.details.setItem(i,1,QTableWidgetItem("—" if b is None else str(b)))
        self.evidence_updated.emit()
    def export_csv(self):
        if not self.dataset:return
        path,_=QFileDialog.getSaveFileName(self,"Exportar tabla","dino-resultados.csv","CSV (*.csv)")
        if not path:return
        try:
            keys=sorted(set().union(*(row.keys() for row in self.dataset['points'])))
            with open(path,'w',encoding='utf-8-sig',newline='') as stream:
                writer=csv.DictWriter(stream,fieldnames=keys,extrasaction='ignore');writer.writeheader()
                for row in self.dataset['points']:writer.writerow({k:json.dumps(row[k],ensure_ascii=False) if isinstance(row.get(k),(dict,list)) else row.get(k) for k in keys})
        except OSError as exc:QMessageBox.warning(self,"Error de escritura",str(exc))
    def export_png(self):
        path,_=QFileDialog.getSaveFileName(self,"Exportar gráfico","dino-curva.png","PNG (*.png)")
        if path:
            pix=QPixmap(self.plot.size());self.plot.render(pix)
            if not pix.save(path,"PNG"):QMessageBox.warning(self,"Error de escritura","No se pudo guardar el gráfico.")
