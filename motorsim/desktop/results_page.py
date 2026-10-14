from __future__ import annotations
import csv,json
from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QLabel,QComboBox,QPushButton,
    QFileDialog,QCheckBox,QGroupBox,QListWidget,QListWidgetItem,QTableWidget,QTableWidgetItem,QHeaderView,QMessageBox)
from .plot import CurvePlot
from .services import load_results,run_background
from .preferences import artifact_root,impl2_historical_report_candidate
from ..exploratory_workflow import import_exploratory_runs

METRICS={"Potencia de freno (kW)":"brake_power","Torque (N·m)":"brake_torque","IMEP (kPa)":"IMEP","FMEP (kPa)":"FMEP","BMEP (kPa)":"BMEP","BSFC (g/kWh)":"BSFC"}

class ResultsPage(QWidget):
    def __init__(self,context):
        super().__init__();self.context=context;self.dataset=None;self.source=None;self.loading=False
        root=QVBoxLayout(self);root.setContentsMargins(24,20,24,20)
        title=QLabel("Resultados y comparación");title.setObjectName('title');root.addWidget(title)
        self.source_notice=QLabel("No hay una corrida seleccionada. Elegila desde el historial o abrí datos importados; todavía no se cargó evidencia histórica.")
        self.source_notice.setWordWrap(True);self.source_notice.setObjectName("notice");root.addWidget(self.source_notice)
        root.addWidget(QLabel("PERIOD_1 describe periodicidad observada; no representa aprobación científica PASS. Los valores no definidos quedan como huecos y no se interpolan."))
        bar=QHBoxLayout();root.addLayout(bar);self.metric=QComboBox();self.metric.addItems(METRICS);bar.addWidget(self.metric)
        self.path_label=QLabel("Sin fuente seleccionada");self.path_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse);self.path_label.setWordWrap(True);bar.addWidget(self.path_label,1)
        browse=QPushButton("Abrir datos…");browse.clicked.connect(self.choose);bar.addWidget(browse)
        historical=QPushButton("Evidencia IMPL2 histórica…");historical.clicked.connect(self.choose_historical);bar.addWidget(historical)
        browse_runs=QPushButton("Abrir corridas EXPLORATORY…");browse_runs.clicked.connect(self.choose_exploratory);bar.addWidget(browse_runs)
        self.variants=QListWidget();self.variants.setMaximumHeight(80);self.variants.setFlow(QListWidget.Flow.LeftToRight);self.variants.setWrapping(True);root.addWidget(self.variants)
        self.plot=CurvePlot();root.addWidget(self.plot,2)
        controls=QHBoxLayout();root.addLayout(controls)
        self.unit=QLabel();controls.addWidget(self.unit);controls.addStretch()
        export_table=QPushButton("Exportar tabla CSV");export_table.clicked.connect(self.export_csv);controls.addWidget(export_table)
        export_plot=QPushButton("Exportar gráfico PNG");export_plot.clicked.connect(self.export_png);controls.addWidget(export_plot)
        self.point_table=QTableWidget(0,7);self.point_table.setHorizontalHeaderLabels(["Variante","RPM","Clasificación","Periodicidad","Auditoría","Ciclos","BMEP"]);self.point_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch);self.point_table.setMaximumHeight(170);self.point_table.currentCellChanged.connect(self._point_row_selected);root.addWidget(self.point_table)
        self.trace_group=QGroupBox("Señales de presión, ondas y flujo EXPLORATORY")
        trace_layout=QVBoxLayout(self.trace_group)
        trace_bar=QHBoxLayout();trace_layout.addLayout(trace_bar)
        self.trace_metric=QComboBox();self.trace_metric.currentIndexChanged.connect(self.redraw_trace);trace_bar.addWidget(self.trace_metric)
        self.trace_status=QLabel("Las trazas sólo se muestran después de re-auditar cada primario.");trace_bar.addWidget(self.trace_status,1)
        self.trace_legend=QLabel();self.trace_legend.setWordWrap(True);trace_layout.addWidget(self.trace_legend)
        self.trace_plot=CurvePlot();self.trace_plot.setMinimumHeight(220);trace_layout.addWidget(self.trace_plot)
        self.trace_group.hide();root.addWidget(self.trace_group)
        self.details=QTableWidget(0,2);self.details.setHorizontalHeaderLabels(["Detalle del punto","Valor"]);self.details.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch);self.details.setMaximumHeight(190);root.addWidget(self.details)
        self.metric.currentIndexChanged.connect(self.redraw);self.variants.itemChanged.connect(self.redraw);self.plot.pointSelected.connect(self.show_point)
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
        if paths:
            self.path_label.setText("Verificando artifacts EXPLORATORY…")
            run_background(import_exploratory_runs,paths,on_done=self._loaded_exploratory,on_error=self._exploratory_failed)
    def _loaded_exploratory(self,data):
        self.dataset=data;self.source=None;self.source_kind="EXPLORATORY";self.path_label.setText(f"{len(data['points'])} ciclos EXPLORATORY · provisional · no interpolación · no validación experimental")
        self.source_notice.setText(f"Corridas exploratorias importadas · no asociadas automáticamente al proyecto {self.context.project['project_id']}. Auditoría y periodicidad se muestran por separado.")
        variants=sorted({r['variant_id'] for r in data['points']});self.variants.blockSignals(True);self.variants.clear()
        for name in variants:
            item=QListWidgetItem(name);item.setFlags(item.flags()|Qt.ItemFlag.ItemIsUserCheckable);item.setCheckState(Qt.CheckState.Checked);self.variants.addItem(item)
        self.variants.blockSignals(False)
        self.trace_metric.blockSignals(True);self.trace_metric.clear()
        traces=data.get("traces",[])
        common=(set.intersection(*(set(row.get("channels",{})) for row in traces)
                                 if traces else [set()]))
        options=[]
        if "cylinder_pressure_pa" in common:
            options.append(("Presión del cilindro (Pa)","cylinder_pressure_pa"))
        for key in sorted(common):
            if key.startswith("duct:exhaust:cell:") and key.endswith(":pressure_pa"):
                options.append((f"Presión escape · celda {key.split(':')[3]} (Pa)",key))
            elif key.startswith("duct:exhaust:face:") and key.endswith(":mass_flow_kg_s"):
                options.append((f"Flujo escape · cara {key.split(':')[3]} (kg/s)",key))
        for label,key in options:self.trace_metric.addItem(label,key)
        self.trace_metric.blockSignals(False)
        self.trace_group.setVisible(bool(traces and options))
        self.trace_status.setText("Primarios re-auditados · ángulos comunes exactos · sin interpolación")
        self.redraw();self.redraw_trace()
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
            self.variants.blockSignals(False);self.loading=False;self.redraw()
        def fail(message):self.loading=False;self.path_label.setText("No se pudieron cargar los datos");QMessageBox.warning(self,"Reporte inválido",message)
        run_background(load_results,path,on_done=done,on_error=fail)
    def redraw(self,*_):
        if not self.dataset:return
        metric=METRICS[self.metric.currentText()];unit=self.metric.currentText().split('(')[-1].rstrip(')')
        selected={self.variants.item(i).text() for i in range(self.variants.count()) if self.variants.item(i).checkState()==Qt.CheckState.Checked}
        series=[]
        for name in sorted(selected):
            points=[]
            for row in sorted((r for r in self.dataset['points'] if r['variant_id']==name),key=lambda r:r['rpm']):
                status=row.get(metric+'_status');value=row.get(metric) if status=='DEFINED' else None
                points.append({"rpm":row['rpm'],"value":value,"classification":row['classification'],"status":status,"reason":row.get(metric+'_reason'),"point":row})
            series.append({"name":name,"unit":unit,"points":points})
        self.unit.setText(f"{unit} · los estados sin valor permanecen como huecos · sin interpolación")
        self.plot.set_series(series)
        rows=sorted((r for r in self.dataset['points'] if r['variant_id'] in selected),key=lambda r:(r['variant_id'],r['rpm']))
        self.point_table.blockSignals(True);self.point_table.setRowCount(len(rows))
        for i,row in enumerate(rows):
            periodicity=row.get('periodicity')
            if periodicity is None:
                periodicity=row.get('classification') if row.get('classification') in {"PERIOD_1","PERIOD_2"} else "NOT_REPORTED"
            values=[row['variant_id'],row['rpm'],row['classification'],periodicity,
                    row.get('audit_status','NOT_REPORTED'),row.get('cycles_completed'),
                    row.get('BMEP') if row.get('BMEP_status')=='DEFINED' else None]
            for j,value in enumerate(values):
                item=QTableWidgetItem('—' if value is None else str(value));item.setData(Qt.ItemDataRole.UserRole,row);self.point_table.setItem(i,j,item)
        self.point_table.blockSignals(False)
    def redraw_trace(self,*_):
        if not self.dataset or self.dataset.get("schema")!="DINO_EXPLORATORY_COMPARISON_V1":
            self.trace_plot.set_series([]);self.trace_legend.setText("");return
        key=self.trace_metric.currentData()
        if not key:
            self.trace_plot.set_series([]);self.trace_legend.setText("");return
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
        self.trace_plot.set_series(series)
        self.trace_legend.setText("Series: " + " | ".join(labels) if labels else "Sin trazas disponibles")
    def _point_row_selected(self,row,*_):
        if row<0 or self.point_table.item(row,0) is None:return
        data=self.point_table.item(row,0).data(Qt.ItemDataRole.UserRole)
        if data:self.show_point({"point":data,"rpm":data['rpm'],"value":None})
    def show_point(self,point):
        row=point.get('point',point)
        periodicity=row.get('periodicity')
        if periodicity is None:
            periodicity=row.get('classification') if row.get('classification') in {"PERIOD_1","PERIOD_2"} else "NOT_REPORTED"
        items=[("RPM",row.get('rpm')), ("Variante",row.get('variant_id')),
            ("Modo",row.get('mode','NOT_REPORTED · historical aggregate')),
            ("Clasificación",row.get('classification')), ("Periodicidad",periodicity),
            ("Auditoría primaria",row.get('audit_status','NOT_REPORTED')),
            ("Auditoría recomputada",row.get('audit_recomputed','NOT_REPORTED')),
            ("Resultado SHA-256",row.get('result_sha256')), ("Primario SHA-256",row.get('primary_sha256')),
            ("Configuración SHA-256",row.get('point_configuration_sha256')),
            ("Ciclos completados",row.get('cycles_completed')),
            ("Métrica",row.get(METRICS[self.metric.currentText()])),
            ("Estado métrica",row.get(METRICS[self.metric.currentText()]+'_status')),
            ("Motivo",row.get(METRICS[self.metric.currentText()]+'_reason')),
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
