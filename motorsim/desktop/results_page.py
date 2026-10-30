from __future__ import annotations
import csv,json
import hashlib
import math
from pathlib import Path
import uuid
from PySide6.QtCore import Qt,Signal,QRect
from PySide6.QtGui import QPixmap,QColor,QPainter,QPen,QImage
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QLabel,QComboBox,QPushButton,
    QFileDialog,QCheckBox,QGroupBox,QListWidget,QListWidgetItem,QTableWidget,QTableWidgetItem,QHeaderView,QMessageBox,
    QDialog,QDialogButtonBox,QFormLayout,QLineEdit,QTabWidget,QScrollArea,QFrame)
from .plot import CurvePlot
from .performance_curves import PowerCurvePanel
from .services import load_results,run_background
from .preferences import artifact_root,impl2_historical_report_candidate,settings
from ..exploratory_workflow import import_exploratory_runs
from .. import measurement_data
from ..engine_project import validate_project

METRICS={"Potencia de freno (kW)":"brake_power","Torque (N·m)":"brake_torque","IMEP (kPa)":"IMEP","FMEP (kPa)":"FMEP","BMEP (kPa)":"BMEP","BSFC (g/kWh)":"BSFC"}

def _state_label(value):
    return {"EXPLORATORY_COMPLETE_PERIODICITY_NOT_IDENTIFIED":"Terminada · sin periodicidad identificada",
        "NOT_CONVERGED":"No convergida","MAX_CYCLES_NONCONVERGED":"Límite de ciclos · no convergida",
        "INSUFFICIENT_CYCLES":"Ciclos insuficientes","NOT_PERFORMED":"No realizada",
        "INTERRUPTED_CHECKPOINTED":"Interrumpida; checkpoint disponible",
        "PERIOD_1":"Periódica observada · orden 1","PERIOD_2":"Periódica observada · orden 2",
        "NOT_EVALUATED":"No evaluada","NOT_IDENTIFIABLE":"No identificable",
        "UNDEFINED":"No definido","NUMERICAL_INVALID":"Inválido numéricamente",
        "EXPLORATORY":"Exploratoria · no validada"}.get(value,value)


def _nonconverged(point):
    """Treat both explicit non-convergence and too-short horizons as transient."""
    return (point.get("classification") in {
        "MAX_CYCLES_NONCONVERGED", "NOT_CONVERGED",
        "EXPLORATORY_COMPLETE_PERIODICITY_NOT_IDENTIFIED",
    } or point.get("periodicity") in {"NOT_CONVERGED", "INSUFFICIENT_CYCLES"})


def _referenced_curve_rpms(project,data):
    """Return a saved RPM grid only for results referenced by this project.

    A recipe must not add NOT_STARTED points to unrelated local history runs;
    that made a valid same-RPM exploratory pair look incompatible at empty RPMs.
    """
    recipe=project.get("simulation_recipes",{}).get("rpm_curve_v1",{})
    rpms=recipe.get("rpms")
    if not isinstance(rpms,list) or not rpms:return None
    referenced={ref.get("artifact_sha256") for ref in project.get("result_references",[])
                if isinstance(ref,dict) and isinstance(ref.get("artifact_sha256"),str)}
    imported={row.get("result_sha256") for row in data.get("points",[])
              if isinstance(row,dict)}
    if not imported or None in imported or not imported.issubset(referenced):return None
    return list(rpms)


class DiscreteAngleCellMap(QWidget):
    """QImage view of exact cell/angle observations; each pixel band holds one sample."""
    def __init__(self,parent=None):
        super().__init__(parent);self.setObjectName("traceAngleCellMap");self.setMinimumHeight(240)
        self.angles=[];self.rows=[];self.image=QImage();self.value_range=None;self.raw_samples=[]
    def set_grid(self,angles,rows):
        self.angles=list(angles);self.rows=list(rows);self.raw_samples=[]
        finite=[float(v) for row in self.rows for v in row.get("values",[]) if v is not None and math.isfinite(float(v))]
        if not finite:
            self.value_range=None;self.image=QImage();self.update();return
        low=min(finite);high=max(finite);self.value_range=(low,high)
        width=max(2,min(1200,len(self.angles)*2));height=max(2,min(600,len(self.rows)*8));self.image=QImage(width,height,QImage.Format.Format_RGB32);self.image.fill(QColor("#182536"))
        raster=QPainter(self.image);xmin=self.angles[0] if self.angles else 0.;span=max(1e-9,(self.angles[-1]-xmin) if len(self.angles)>1 else 1.)
        groups={}
        for row in self.rows:groups.setdefault(row.get("group","run"),[]).append(row)
        group_height=height/max(1,len(groups));group_index=0
        for group,group_rows in groups.items():
            total=sum(max(1e-9,float(row.get("length_mm",1.))) for row in group_rows);cursor=group_index*group_height
            for row in group_rows:
                band=group_height*max(1e-9,float(row.get("length_mm",1.)))/total;y0=round(cursor);y1=max(y0+1,round(cursor+band));cursor+=band
                vals=row.get("values",[]);self.raw_samples.append({'label':row.get('label'),'values':list(vals),'angles_deg':list(self.angles),'position_m':row.get('position_m')})
                for j,value in enumerate(vals):
                    if value is None or not math.isfinite(float(value)):continue
                    x0=0 if j==0 else round((((self.angles[j-1]+self.angles[j])/2-xmin)/span)*width)
                    x1=width if j==len(vals)-1 else round((((self.angles[j]+self.angles[j+1])/2-xmin)/span)*width)
                    f=.5 if high==low else (float(value)-low)/(high-low);color=self._color(f)
                    raster.fillRect(QRect(max(0,x0),y0,max(1,min(width,x1)-max(0,x0)),min(height,y1)-y0),color)
            group_index+=1
        raster.end()
        self.update()
    @staticmethod
    def _color(value):
        stops=((0.,(35,55,110)),(.45,(29,155,174)),(.72,(150,205,87)),(1.,(252,210,73)))
        for i in range(len(stops)-1):
            if stops[i][0]<=value<=stops[i+1][0]:
                a,ca=stops[i];b,cb=stops[i+1];f=(value-a)/(b-a)
                return QColor(*(round(ca[j]+(cb[j]-ca[j])*f) for j in range(3)))
        return QColor(*stops[-1][1])
    def paintEvent(self,event):
        p=QPainter(self);p.fillRect(self.rect(),QColor("#101a28"));r=self.rect().adjusted(100,14,-72,-46)
        p.setPen(QPen(QColor("#536b82"),1));p.drawRect(r)
        if self.image.isNull():p.setPen(QColor("#cad8e7"));p.drawText(r,Qt.AlignmentFlag.AlignCenter,"No hay muestras de celda y ángulo disponibles.");p.end();return
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform,False);p.drawImage(r,self.image)
        p.setPen(QColor("#cad8e7"));p.drawText(6,r.center().y(),90,18,Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignVCenter,"Celdas reales")
        low_angle=self.angles[0] if self.angles else 0.;high_angle=self.angles[-1] if self.angles else 0.
        for i in range(5):
            angle=low_angle+(high_angle-low_angle)*i/4;x=r.left()+i/4*r.width();p.drawText(round(x)-28,r.bottom()+18,56,16,Qt.AlignmentFlag.AlignCenter,f"{angle:g}°")
        p.drawText(r.left(),self.height()-5,"Ángulo muestreado · bandas discretas, sin interpolación")
        low,high=self.value_range or (0,1);bar=r.adjusted(r.width()+22,0,r.width()+52,0)
        for y in range(max(0,bar.top()),min(self.height(),bar.bottom()+1)):
            f=1-(y-bar.top())/max(bar.height(),1);p.setPen(self._color(f));p.drawLine(bar.left(),y,bar.right(),y)
        p.setPen(QColor("#cad8e7"));p.drawText(bar.left()-70,bar.top(),64,15,Qt.AlignmentFlag.AlignRight,f"{high:.4g}");p.drawText(bar.left()-70,bar.bottom(),64,15,Qt.AlignmentFlag.AlignRight,f"{low:.4g}");p.end()

class ResultsPage(QWidget):
    evidence_updated=Signal()
    def __init__(self,context):
        super().__init__();self.context=context;self.dataset=None;self.source=None;self.loading=False
        self._project_reference_signature=None
        root=QVBoxLayout(self);root.setContentsMargins(12,10,12,10);root.setSpacing(6)
        title=QLabel("Resultados");title.setObjectName('title');root.addWidget(title)
        self.source_notice=QLabel("No hay una corrida seleccionada. Elegila desde el historial o abrí datos importados; todavía no se cargó evidencia histórica.")
        self.source_notice.setWordWrap(True);self.source_notice.setObjectName("notice");root.addWidget(self.source_notice)
        self.run_summary=QLabel("Sin una corrida seleccionada · las métricas de desempeño no están definidas.");self.run_summary.setWordWrap(True);self.run_summary.setObjectName("notice");root.addWidget(self.run_summary)
        self.metric_cards=[];cards=QHBoxLayout();root.addLayout(cards)
        for name in ("Potencia","Torque","BMEP","Auditoría"):
            card=QLabel(f"{name}\n—");card.setObjectName("metricCard");card.setWordWrap(True);card.setMinimumHeight(50);cards.addWidget(card);self.metric_cards.append(card)
        explanation=QLabel("Los estados científicos se conservan. Métricas no definidas se explican; no se interpolan.");explanation.setWordWrap(True);root.addWidget(explanation)
        bar=QHBoxLayout();root.addLayout(bar);self.metric_selector=QComboBox();self.metric_selector.addItems(METRICS);bar.addWidget(self.metric_selector)
        self.path_label=QLabel("Sin fuente seleccionada");self.path_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse);self.path_label.setWordWrap(True);bar.addWidget(self.path_label,1)
        actions=QHBoxLayout();root.addLayout(actions)
        browse=QPushButton("Abrir datos…");browse.clicked.connect(self.choose);actions.addWidget(browse)
        historical=QPushButton("Evidencia IMPL2 histórica…");historical.clicked.connect(self.choose_historical);actions.addWidget(historical)
        browse_runs=QPushButton("Abrir corridas EXPLORATORY…");browse_runs.clicked.connect(self.choose_exploratory);actions.addWidget(browse_runs);actions.addStretch()
        self.variants=QListWidget();self.variants.setMaximumHeight(80);self.variants.setFlow(QListWidget.Flow.LeftToRight);self.variants.setWrapping(True);root.addWidget(self.variants)
        baseline_row=QHBoxLayout();root.addLayout(baseline_row);baseline_row.addWidget(QLabel("Baseline del proyecto"));self.baseline_selector=QComboBox();baseline_row.addWidget(self.baseline_selector)
        self.baseline_notice=QLabel("La baseline identifica la referencia de comparación; las curvas usan sólo puntos realmente disponibles.");self.baseline_notice.setWordWrap(True);baseline_row.addWidget(self.baseline_notice,1)
        measured=QGroupBox("Mediciones externas · contraste descriptivo");measured_layout=QVBoxLayout(measured)
        measured_row=QHBoxLayout();measured_layout.addLayout(measured_row)
        self.measurement_import_button=QPushButton("Importar CSV de banco…");self.measurement_import_button.clicked.connect(self.import_measurement);measured_row.addWidget(self.measurement_import_button)
        self.measurement_selector=QComboBox();self.measurement_selector.currentIndexChanged.connect(self.compare_measurement);measured_row.addWidget(self.measurement_selector)
        self.measurement_compare_button=QPushButton("Comparar RPM exactas");self.measurement_compare_button.clicked.connect(self.compare_measurement);measured_row.addWidget(self.measurement_compare_button)
        self.measurement_export_button=QPushButton("Exportar contraste CSV");self.measurement_export_button.clicked.connect(self.export_measurement_comparison);measured_row.addWidget(self.measurement_export_button)
        self.measurement_notice=QLabel("Las mediciones conservan unidades, origen e incertidumbre. Sin interpolación; no es validación experimental preregistrada.")
        self.measurement_notice.setWordWrap(True);measured_layout.addWidget(self.measurement_notice)
        self.measurement_plot=CurvePlot();self.measurement_plot.setObjectName("measuredRunOverlay");self.measurement_plot.setMinimumHeight(160);measured_layout.addWidget(self.measurement_plot)
        self.measurement_table=QTableWidget(0,5);self.measurement_table.setObjectName("measuredRunComparison")
        self.measurement_table.setHorizontalHeaderLabels(["RPM","Medido","Incertidumbre","Simulado","Simulado − medido"])
        self.measurement_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch);self.measurement_table.setMaximumHeight(170);measured_layout.addWidget(self.measurement_table)
        root.addWidget(measured)
        self.condition_notice=QLabel();self.condition_notice.setWordWrap(True);self.condition_notice.setObjectName("notice");root.addWidget(self.condition_notice)
        self.plot=CurvePlot();root.addWidget(self.plot,2)
        self.power_curves=PowerCurvePanel();root.addWidget(self.power_curves)
        controls=QHBoxLayout();root.addLayout(controls)
        self.unit=QLabel();controls.addWidget(self.unit);controls.addStretch()
        export_table=QPushButton("Exportar tabla CSV");export_table.setToolTip("Reportes históricos: CSV + JSON compañero para reabrir. Corridas exploratorias: tabla de consulta; conservar los artifacts originales.");export_table.clicked.connect(self.export_csv);controls.addWidget(export_table)
        export_plot=QPushButton("Exportar gráfico PNG");export_plot.clicked.connect(self.export_png);controls.addWidget(export_plot)
        self.point_table=QTableWidget(0,8);self.point_table.setHorizontalHeaderLabels(["Variante","RPM","Estado","Período","Auditoría","Ciclos","Balance","BMEP"]);self.point_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch);self.point_table.horizontalHeader().setMinimumSectionSize(48);self.point_table.setMinimumHeight(125);self.point_table.setMaximumHeight(190);self.point_table.currentCellChanged.connect(self._point_row_selected);root.addWidget(self.point_table)
        self.trace_group=QGroupBox("Señales de presión, ondas y flujo EXPLORATORY")
        trace_layout=QVBoxLayout(self.trace_group)
        trace_bar=QHBoxLayout();trace_layout.addLayout(trace_bar)
        self.trace_metric=QComboBox();self.trace_metric.currentIndexChanged.connect(self.redraw_trace);trace_bar.addWidget(self.trace_metric)
        self.trace_rpm=QComboBox();self.trace_rpm.addItem('Todas las RPM',None);self.trace_rpm.currentIndexChanged.connect(self.redraw_trace);trace_bar.addWidget(self.trace_rpm)
        self.trace_status=QLabel("Las trazas sólo se muestran después de re-auditar cada primario.");trace_bar.addWidget(self.trace_status,1)
        self.trace_legend=QLabel();self.trace_legend.setWordWrap(True);trace_layout.addWidget(self.trace_legend)
        self.trace_plot=CurvePlot();self.trace_plot.setMinimumHeight(220);trace_layout.addWidget(self.trace_plot)
        self.trace_map_legend=QLabel("Mapa discreto de posición × ángulo · celdas reales · sin interpolación.");self.trace_map_legend.setWordWrap(True);trace_layout.addWidget(self.trace_map_legend)
        self.trace_map=DiscreteAngleCellMap();trace_layout.addWidget(self.trace_map)
        self.export_trace_map=QPushButton("Exportar muestras x–θ CSV");self.export_trace_map.clicked.connect(self.export_trace_csv);trace_layout.addWidget(self.export_trace_map)
        self.trace_group.hide();root.addWidget(self.trace_group)
        self.compare_group=QGroupBox("Comparación de ingeniería")
        compare_layout=QVBoxLayout(self.compare_group);self.compare_notice=QLabel("Seleccioná dos variantes con corridas para comparar.");self.compare_notice.setWordWrap(True);compare_layout.addWidget(self.compare_notice)
        self.compare_table=QTableWidget(0,5);self.compare_table.setObjectName("engineeringComparisonTable");self.compare_table.setHorizontalHeaderLabels(["Elemento","Baseline","Variante","Δ","Estado"]);self.compare_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch);self.compare_table.setMaximumHeight(220);compare_layout.addWidget(self.compare_table);root.addWidget(self.compare_group)
        self.details=QTableWidget(0,2);self.details.setHorizontalHeaderLabels(["Detalle del punto","Valor"]);self.details.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch);self.details.setMaximumHeight(190);root.addWidget(self.details)
        # Preserve all existing controls and contracts; organize presentation
        # around the designer's question rather than one long audit document.
        self.result_tabs=QTabWidget();self.result_tabs.setObjectName('resultViews')
        self.view_layouts=[]
        def view(label,widgets,layouts=()):
            page=QWidget();box=QVBoxLayout(page);box.setContentsMargins(4,5,4,4)
            for widget in widgets:
                root.removeWidget(widget);box.addWidget(widget)
            for section in layouts:
                root.removeItem(section);box.addLayout(section)
            scroll=QScrollArea();scroll.setWidgetResizable(True);scroll.setFrameShape(QFrame.Shape.NoFrame);scroll.setWidget(page)
            self.result_tabs.addTab(scroll,label);self.view_layouts.append(box)
            return box
        view('Curvas',[self.power_curves])
        view('Variables',[self.plot,self.point_table])
        waves=view('Presiones y ondas',[self.trace_group])
        wave_help=QLabel('Las señales se muestran cuando las corridas contienen primarios compatibles. Un reporte agregado de curvas no contiene trazas ni geometría adicional.');wave_help.setWordWrap(True);waves.insertWidget(0,wave_help)
        view('Comparar',[self.compare_group])
        view('Mediciones',[measured])
        view('Trazabilidad',[self.source_notice,self.path_label,self.details])
        # Source paths and identifiers stay available in Trazabilidad. Keep
        # provenance and scientific status visible in the normal workspace.
        bar.removeWidget(self.path_label)
        self.source_notice.setWordWrap(True)
        root.removeItem(cards)
        self.view_layouts[5].addLayout(cards)
        root.removeItem(bar)
        self.view_layouts[1].insertLayout(0,bar)
        root.removeItem(baseline_row)
        self.view_layouts[3].insertLayout(0,baseline_row)
        root.removeWidget(self.condition_notice);self.view_layouts[3].insertWidget(1,self.condition_notice)
        title.hide();explanation.hide()
        self.variants.setFixedHeight(36)
        self.result_tabs.setMinimumHeight(240)
        root.removeItem(controls)
        root.addWidget(self.result_tabs,1);root.addLayout(controls)
        self.power_curves.plot.setMinimumHeight(200)
        self.metric_selector.currentIndexChanged.connect(self.redraw);self.variants.itemChanged.connect(self.redraw);self.variants.itemChanged.connect(self._update_engineering_compare);self.plot.pointSelected.connect(self.show_point);self.power_curves.pointSelected.connect(self.show_point)
        self.baseline_selector.currentIndexChanged.connect(self._baseline_changed)
        self.context.changed.connect(self._project_context_changed);self._project_context_changed()

    def _project_context_changed(self,*_):
        refs=self.context.project.get("result_references",[])
        signature=(self.context.project.get("project_id"),tuple(
            (str(ref.get("path","")),ref.get("artifact_sha256"),ref.get("identity_sha256"))
            for ref in refs))
        if signature!=self._project_reference_signature:
            self._project_reference_signature=signature
            paths=[Path(ref["path"]) for ref in refs if ref.get("path") and Path(ref["path"]).is_file()]
            if paths:self.open_runs(paths)
        names={"base",*self.context.project["variants"]}
        data_names=set()
        if self.dataset:
            data_names={str(row.get("variant_id")) for row in self.dataset.get("points",[]) if row.get("variant_id")};names.update(data_names)
        prefs=settings();key=f"baseline_variant/{self.context.project['project_id']}"
        preferred=prefs.value(key)
        if not preferred:preferred="base"
        self.baseline_selector.blockSignals(True);self.baseline_selector.clear();self.baseline_selector.addItem("Sin baseline",None)
        self.baseline_selector.addItem("Motor base","base")
        for name in sorted(names-{"base"}):self.baseline_selector.addItem(name,name)
        index=self.baseline_selector.findData(preferred)
        if index<0:index=self.baseline_selector.findData(self.context.selected_variant or "base")
        self.baseline_selector.setCurrentIndex(index if index>=0 else 0);self.baseline_selector.blockSignals(False)
        self._reload_measurement_references()

    def _reload_measurement_references(self):
        loaded=[];errors=[]
        for ref in self.context.project.get("measurement_references",[]):
            try:
                path=Path(ref["path"])
                if not path.is_absolute() and self.context.path and ref["path"].startswith(("./", ".\\")):
                    path=(Path(self.context.path).resolve().parent/ref["path"][2:]).resolve()
                data=measurement_data.load_import(path)
                meta_hash=hashlib.sha256(path.read_bytes()).hexdigest()
                if (data["manifest"]["dataset_id"]!=ref["dataset_id"] or
                        data["manifest"]["csv_sha256"]!=ref["csv_sha256"] or meta_hash!=ref["metadata_sha256"]):
                    raise ValueError("La medición no coincide con los hashes guardados en el proyecto.")
                loaded.append(data)
            except Exception as exc:errors.append(f"{ref.get('path','medición')}: {exc}")
        self.measurement_datasets=loaded;self.measurement_selector.blockSignals(True);self.measurement_selector.clear()
        for data in loaded:
            meta=data["metadata"];self.measurement_selector.addItem(f"{meta['kind']} · {meta['engine']} · {meta['provenance']}",data["manifest"]["dataset_id"])
        self.measurement_selector.blockSignals(False)
        self.measurement_import_button.setEnabled(bool(self.context.path))
        if errors:self.measurement_notice.setText("No se pudieron recuperar algunas mediciones: "+"; ".join(errors))
        elif loaded:self.measurement_notice.setText(f"{len(loaded)} conjunto(s) medido(s) ligado(s) al proyecto. Contraste exacto · no es validación experimental.")
        self.compare_measurement()

    def import_measurement(self):
        if not self.context.path:
            QMessageBox.information(self,"Guardar proyecto","Guardá primero el proyecto para ligar la medición a una ruta que pueda recuperarse al reabrirlo.");return False
        csv_path,_=QFileDialog.getOpenFileName(self,"Importar medición de banco",str(Path(self.context.path).parent),"CSV (*.csv)")
        if not csv_path:return False
        dialog=QDialog(self);dialog.setWindowTitle("Declarar medición externa");form=QFormLayout(dialog)
        kind=QComboBox();kind.addItem("Potencia de freno","dyno_power");kind.addItem("Torque","dyno_torque");kind.addItem("Presión de cilindro por ciclo","pressure_trace")
        unit=QComboBox()
        cycle_period=QComboBox();cycle_period.addItem("360°",360);cycle_period.addItem("720°",720)
        def update_units():
            choices={"dyno_power":("kW","W","hp"),"dyno_torque":("N*m","lb-ft"),"pressure_trace":("Pa","kPa","bar")}[kind.currentData()]
            unit.clear();unit.addItems(choices);cycle_period.setEnabled(kind.currentData()=="pressure_trace")
        kind.currentIndexChanged.connect(update_units);update_units()
        provenance=QComboBox();provenance.addItem("Desconocido","UNKNOWN");provenance.addItem("Medido","MEASURED");provenance.addItem("Documentado","DOCUMENTED");provenance.addItem("Sintético de prueba","SYNTHETIC")
        fields={key:QLineEdit() for key in ("engine","configuration","conditions","source","notes")}
        form.addRow("Magnitud",kind);form.addRow("Unidad del CSV",unit);form.addRow("Clasificación",provenance)
        form.addRow("Período de ciclo",cycle_period)
        for key,label in (("engine","Motor"),("configuration","Configuración"),("conditions","Condiciones"),("source","Fuente"),("notes","Notas")):form.addRow(label,fields[key])
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel|QDialogButtonBox.StandardButton.Save);buttons.accepted.connect(dialog.accept);buttons.rejected.connect(dialog.reject);form.addRow(buttons)
        if dialog.exec()!=QDialog.DialogCode.Accepted:return False
        try:
            period=cycle_period.currentData() if kind.currentData()=="pressure_trace" else None
            meta=measurement_data.declarations(kind.currentData(),unit.currentText(),cycle_period_deg=period,provenance=provenance.currentData(),**{key:edit.text() for key,edit in fields.items()})
            raw=Path(csv_path).read_bytes();prepared=measurement_data.prepare_import(raw,meta)
            project_path=Path(self.context.path).resolve();root=project_path.parent/(project_path.stem+".measurements")
            root.mkdir(parents=True,exist_ok=True)
            imported=measurement_data.save_import(root/uuid.uuid4().hex,prepared);manifest_path=Path(imported["path"])
            try:stored_path="./"+manifest_path.parent.relative_to(project_path.parent).as_posix()+"/metadata.json"
            except ValueError:stored_path=str(manifest_path)
            ref={"path":stored_path,"dataset_id":imported["manifest"]["dataset_id"],
                 "metadata_sha256":hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
                 "csv_sha256":imported["manifest"]["csv_sha256"],"classification":meta["provenance"]}
            project=self.context.project;project.setdefault("measurement_references",[]).append(ref);validate_project(project)
            self.context.dirty=True;self.context.changed.emit();self.measurement_notice.setText("Medición importada y ligada al proyecto. Guardá el proyecto para persistir la referencia. Datos sintéticos de prueba no validan el solver.")
            return True
        except Exception as exc:
            QMessageBox.warning(self,"No se pudo importar la medición",str(exc));return False

    def compare_measurement(self,*_):
        self.measurement_table.setRowCount(0)
        if not getattr(self,"measurement_datasets",None) or self.measurement_selector.currentIndex()<0 or not self.dataset:return
        external=self.measurement_datasets[self.measurement_selector.currentIndex()];meta=external["metadata"]
        variant=self.baseline_selector.currentData() or "base";simulated=[]
        if meta["kind"]=="pressure_trace":
            rpm=self.trace_rpm.currentData()
            if rpm is None:
                self.measurement_notice.setText("Elegí una RPM de la corrida para contrastar la traza; no se mezclan condiciones ni ciclos.");return
            traces=[trace for trace in self.dataset.get("traces",[]) if trace.get("variant_id")==variant and trace.get("rpm")==rpm]
            for trace in traces:
                channel=trace.get("channels",{}).get("cylinder_pressure_pa",{})
                for angle,value in zip(trace.get("angles_deg",[]),channel.get("values",[])):
                    if value is not None:simulated.append({"cycle":trace["cycle"],"x":angle,"value":value})
            unit=meta["canonical_value_unit"]
            if not simulated:
                self.measurement_notice.setText("La corrida seleccionada no tiene trazas de presión del cilindro para esa RPM.");return
        else:
            metric="brake_power" if meta["kind"]=="dyno_power" else "brake_torque" if meta["kind"]=="dyno_torque" else None
            if metric is None:return
            for point in self.dataset.get("points",[]):
                if point.get("variant_id")!=variant or point.get(metric+"_status")!="DEFINED":continue
                value=point.get(metric)
                if value is not None:simulated.append({"x":point["rpm"],"value":float(value)*(1000 if metric=="brake_power" else 1)})
            unit=meta["canonical_value_unit"]
        comparison=measurement_data.exploratory_overlay(external,simulated,simulated_unit=unit)
        self.measurement_table.setHorizontalHeaderLabels(["Ciclo / ángulo (°CA)" if meta["kind"]=="pressure_trace" else "RPM",
            "Medido", "Incertidumbre", "Simulado", "Simulado − medido"])
        if meta["kind"]=="pressure_trace":
            measured_points=[{"angle_deg":row["x"],"value":row["value"]} for row in external["rows"]]
            simulated_points=[{"angle_deg":row["key"][1],"value":row["simulated"]} for row in comparison["rows"] if row["simulated"] is not None]
            x_key="angle_deg";x_label="Ángulo de cigüeñal (°)"
        else:
            measured_points=[{"rpm":row["x"],"value":row["value"]} for row in external["rows"]]
            simulated_points=[{"rpm":row["key"],"value":row["simulated"]} for row in comparison["rows"] if row["simulated"] is not None]
            x_key="rpm";x_label="RPM"
        self.measurement_plot.set_series([
            {"name":"Medido · "+meta["provenance"],"unit":unit,"x_label":x_label,"x_key":x_key,"points":measured_points},
            {"name":"Corrida · coordenadas coincidentes","unit":unit,"x_label":x_label,"x_key":x_key,"points":simulated_points}])
        self.measurement_table.setRowCount(len(comparison["rows"]))
        for row,data in enumerate(comparison["rows"]):
            values=(data["key"],data["measured"],data["uncertainty"],data["simulated"],data["difference"])
            for column,value in enumerate(values):
                shown="—" if value is None else (str(value) if isinstance(value,tuple) else f"{value:g}")
                item=QTableWidgetItem(shown);item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable);self.measurement_table.setItem(row,column,item)
        self.measurement_notice.setText(f"{meta['kind']} · {meta['canonical_value_unit']} · {meta['provenance']} · {meta['engine']} · {meta['configuration']} · {meta['conditions']} · {comparison['metrics']['matched_count']} coincidencias exactas · sin interpolación. {comparison['notice']}")
        run_ids=sorted({str(row.get("run_id")) for row in self.dataset.get("points",[]) if row.get("variant_id")==variant and row.get("run_id")})
        self._measurement_export_metadata={"dataset_id":comparison["dataset_id"],"provenance":meta["provenance"],
            "source":meta["source"],"engine":meta["engine"],"configuration":meta["configuration"],
            "conditions":meta["conditions"],"variant":variant,"run_ids":";".join(run_ids),
            "comparison_status":comparison["status"],"interpolation":comparison["interpolation"]}

    def export_measurement_comparison(self):
        if self.measurement_table.rowCount()==0:return False
        path,_=QFileDialog.getSaveFileName(self,"Exportar contraste de mediciones",str(Path(self.context.path).parent if self.context.path else Path.cwd()),"CSV (*.csv)")
        if not path:return False
        try:
            with Path(path).open("w",encoding="utf-8-sig",newline="") as stream:
                writer=csv.writer(stream);metadata=self._measurement_export_metadata
                context_fields=["dataset_id","provenance","source","engine","configuration","conditions","variant","run_ids","comparison_status","interpolation"]
                writer.writerow(context_fields+[self.measurement_table.horizontalHeaderItem(c).text() for c in range(self.measurement_table.columnCount())])
                for row in range(self.measurement_table.rowCount()):writer.writerow([metadata[key] for key in context_fields]+[self.measurement_table.item(row,c).text() for c in range(self.measurement_table.columnCount())])
            return True
        except OSError as exc:
            QMessageBox.warning(self,"No se pudo exportar el contraste",str(exc));return False

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
                    descriptions.append(self._engineering_change(change,base,other))
                suffix="; …" if len(changes)>4 else ""
                diffs.append(f"{candidate}: {len(changes)} diferencias nativas ({'; '.join(descriptions)}{suffix}) · hashes coinciden")
            elif other is not None:diffs.append(f"{candidate}: corridas presentes; diff de geometría no confirmado contra sus hashes")
        self.baseline_notice.setText(f"Baseline {name} · " + ("; ".join(diffs) if diffs else ("hash de geometría de corrida verificado." if baseline_matches else "configuración actual sin hash de corrida verificable.")))
        self._update_condition_notice()
        self._update_engineering_compare()
        self.redraw()

    def _update_engineering_compare(self,*_):
        self.compare_table.setRowCount(0)
        baseline_name=self.baseline_selector.currentData() if hasattr(self,"baseline_selector") else None
        selected=[self.variants.item(i).text() for i in range(self.variants.count()) if self.variants.item(i).checkState()==Qt.CheckState.Checked]
        candidate_run=next((name for name in selected if self._project_variant_for_run(name) not in (None,baseline_name)),None)
        candidate_name=self._project_variant_for_run(candidate_run) if candidate_run else None
        if not baseline_name or not candidate_name:
            self.compare_notice.setText("Seleccioná baseline y variante para ver diferencias geométricas y métricas.")
            return
        base=self.context.project["base_engine"] if baseline_name=="base" else self.context.project["variants"].get(baseline_name)
        candidate=self.context.project["base_engine"] if candidate_name=="base" else self.context.project["variants"].get(candidate_name)
        rows=[]
        if base is not None and candidate is not None:
            from ..engine_variants import compare_configurations
            for change in compare_configurations(base,candidate):
                path=change.get("path","").replace("/native_configuration/","")
                # The native ducts, species, and their discretization are
                # derived backend state. Report the editable source geometry,
                # not dozens of low-level mesh coordinates and inventories.
                if path.startswith(("ducts/","duct_species/","initial_duct_states/")) or any(
                    part in f"/{path}/" for part in ("/ducts/","/duct_species/","/initial_duct_states/")
                ):
                    continue
                parts=path.split("/");tail=parts[-1]
                labels={"length_mm":"longitud","inlet_diameter_mm":"Ø entrada",
                    "outlet_diameter_mm":"Ø salida","bore_mm":"Ø cilindro",
                    "stroke_mm":"carrera","rod_length_mm":"biela",
                    "volume_bdc_cm3":"volumen PMI","cylinder_compression_ratio":"relación de compresión",
                    "reference_rpm":"RPM de referencia"}
                label=labels.get(tail,tail.replace("_mm"," ").replace("_"," "))
                if "geometry_identity/chamber/sections" in path:
                    try:
                        section_index=int(parts[parts.index("sections")+1])
                        from ..engine_variants import escape_sections
                        label=f"{escape_sections(candidate)[section_index]['name']} · {label}"
                    except (ValueError,IndexError,KeyError):pass
                before=change.get("before");after=change.get("after");unit=change.get("unit","")
                fmt=lambda x: f"{x:g}" if isinstance(x,(int,float)) else str(x)
                delta=f"{after-before:+g} {unit}".strip() if isinstance(before,(int,float)) and isinstance(after,(int,float)) else "—"
                state="Geometría del proyecto" if any(k in path for k in ("geometry_identity","slider_crank","port_binding")) else "Configuración declarada"
                rows.append((label,f"{fmt(before)} {unit}".strip(),f"{fmt(after)} {unit}".strip(),delta,state))
                if len(rows)>=12:break
        points=(self.dataset or {}).get("points",[])
        baseline_runs={name for name in selected if self._project_variant_for_run(name)==baseline_name}
        candidate_runs={name for name in selected if self._project_variant_for_run(name)==candidate_name}
        bpoints=[r for r in points if r.get("variant_id") in baseline_runs]
        cpoints=[r for r in points if r.get("variant_id") in candidate_runs]
        pairs=[]
        for b in bpoints:
            for c in cpoints:
                if b.get("rpm")!=c.get("rpm"):continue
                fields=("fuel_id","afr_kg_air_per_kg_fuel","mesh_resolution","total_finite_volume_cells","cycles_requested","solver_identity_sha256","implementation_identity_sha256")
                mismatches=[key for key in fields if b.get(key) is not None and c.get(key) is not None and b.get(key)!=c.get(key)]
                pairs.append((len(mismatches),b,c,mismatches))
        pair=min(pairs,key=lambda p:(p[0],p[1].get("rpm",0))) if pairs else None
        if pair:
            _,b,c,mismatches=pair
            for label,key in (("Potencia de freno","brake_power"),("Torque","brake_torque"),("BMEP","BMEP"),("IMEP","IMEP"),("FMEP","FMEP")):
                bval=b.get(key);cval=c.get(key);bs=b.get(key+"_status");cs=c.get(key+"_status")
                defined=bs=="DEFINED" and cs=="DEFINED" and isinstance(bval,(int,float)) and isinstance(cval,(int,float))
                unit={"Potencia de freno":"kW","Torque":"N·m","BMEP":"kPa","IMEP":"kPa","FMEP":"kPa"}[label]
                reason="Definido" if defined else str(c.get(key+"_reason") or b.get(key+"_reason") or "No definido por el artifact")
                rows.append((label,f"{bval:g} {unit}" if defined else "—",f"{cval:g} {unit}" if defined else "—",f"{cval-bval:+g} {unit}" if defined else "—",reason))
            if b.get('transient_estimates') is not None and c.get('transient_estimates') is not None:
                for label,key,unit in (("Potencia transitoria","brake_power","kW"),("Torque transitorio","brake_torque","N·m")):
                    x=b['transient_estimates'].get(key);y=c['transient_estimates'].get(key)
                    if isinstance(x,(int,float)) and isinstance(y,(int,float)):
                        rows.append((label,f"{x:.4g} {unit}",f"{y:.4g} {unit}",f"{y-x:+.4g} {unit}","NO CONVERGIDO; diferencia transitoria, no ganancia confirmada" if _nonconverged(b) or _nonconverged(c) else "Estimación de ingeniería"))
                for label in ("Trabajo indicado (J/ciclo)","Aire atrapado al cierre (mg)","Calor de combustión (J/ciclo)"):
                    x=b.get('engineering_diagnostics',{}).get(label);y=c.get('engineering_diagnostics',{}).get(label)
                    if isinstance(x,(int,float)) and isinstance(y,(int,float)):
                        rows.append((label,f"{x:.4g}",f"{y:.4g}",f"{y-x:+.4g}","Último ciclo; no atribución estacionaria"))
            identity_fields=("solver_identity_sha256","implementation_identity_sha256")
            identity_known=any(b.get(key) is not None and c.get(key) is not None for key in identity_fields)
            identity_matches=identity_known and all(b.get(key)==c.get(key) for key in identity_fields if b.get(key) is not None and c.get(key) is not None)
            condition="Mismo RPM; condiciones declaradas coinciden" if not mismatches else "Advertencia: difieren "+", ".join(mismatches)
            if not identity_known:condition+="; identidad del solver por punto no informada"
            elif not identity_matches:condition+="; identidad del solver distinta"
            if _nonconverged(b) or _nonconverged(c):condition+="; TRANSITORIOS: no demuestra ganancia de potencia del escape"
            self.compare_notice.setText(f"{baseline_name} vs {candidate_name} · {b.get('rpm'):g} RPM · {condition}. La identidad de configuración conserva las diferencias geométricas mostradas.")
        else:
            self.compare_notice.setText(f"{baseline_name} vs {candidate_name}: sin par de corridas a la misma RPM. Se muestra sólo el diff geométrico del proyecto; no se comparan métricas entre condiciones distintas.")
        self.compare_table.setRowCount(len(rows))
        for i,row in enumerate(rows):
            for j,value in enumerate(row):
                item=QTableWidgetItem(str(value));item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable);self.compare_table.setItem(i,j,item)

    def _project_variant_for_run(self,variant_id):
        """Resolve imported history labels to this project's immutable variants."""
        if not variant_id:return None
        label=str(variant_id)
        prefix=f"{self.context.project.get('project_id')} / "
        if label.startswith(prefix):label=label[len(prefix):]
        # Prefer an explicit project variant label over configuration hash
        # matching. A named variant may intentionally equal base geometry;
        # hash-first matching would then alias its imported run to "base" and
        # make the selected baseline appear to have no matching RPM point.
        if label in self.context.project.get("variants",{}):return label
        if label in {"base","Motor base"}:return "base"
        configurations=[("base",self.context.project.get("base_engine",{}))]
        configurations.extend(self.context.project.get("variants",{}).items())
        data_points=[r for r in (self.dataset or {}).get("points",[]) if r.get("variant_id")==variant_id]
        hashes={r.get("point_configuration_sha256") or r.get("configuration_sha256") for r in data_points}
        hashes.discard(None)
        for name,configuration in configurations:
            native_hash=configuration.get("native_configuration_sha256")
            if native_hash and native_hash in hashes:return name
        return "base" if label in {"base","Motor base"} else None

    @staticmethod
    def _engineering_change(change,baseline,candidate):
        path=change.get("path","").replace("/native_configuration/","")
        unit=change.get("unit") or ""
        before,after=change.get("before"),change.get("after")
        label=path
        parts=path.split("/")
        if "chamber/sections" in path:
            try:
                i=int(parts[parts.index("sections")+1]);name=__import__("motorsim.engine_variants",fromlist=["escape_sections"]).escape_sections(candidate)[i]["name"]
                tail=parts[-1];label=f"{name} · "+({"length_mm":"longitud","inlet_diameter_mm":"Ø entrada","outlet_diameter_mm":"Ø salida"}.get(tail,tail))
            except (ValueError,IndexError,KeyError):pass
        elif parts[-1]=="bore_mm":label="Diámetro de cilindro"
        elif parts[-1]=="stroke_mm":label="Carrera"
        elif parts[-1]=="rod_length_mm":label="Longitud de biela"
        def fmt(value):return f"{value:g}" if isinstance(value,(int,float)) else str(value)
        return f"{label}: {fmt(before)} → {fmt(after)} {unit}".strip()

    def _update_condition_notice(self):
        if not self.dataset or not isinstance(self.dataset.get("points"),list):
            self.condition_notice.setText("Condiciones entre corridas: sin datos cargados.");return
        selected={self.variants.item(i).text() for i in range(self.variants.count()) if self.variants.item(i).checkState()==Qt.CheckState.Checked}
        points=[row for row in self.dataset["points"] if row.get("variant_id") in selected]
        fields=("rpm","fuel_id","afr_kg_air_per_kg_fuel","mesh_resolution","total_finite_volume_cells","cycles_requested","point_configuration_sha256")
        differing=[]
        for key in fields:
            values={json.dumps(row.get(key),sort_keys=True) for row in points if row.get(key) is not None}
            if len(values)>1:differing.append(key)
        labels={"rpm":"RPM","fuel_id":"combustible","afr_kg_air_per_kg_fuel":"AFR","mesh_resolution":"resolución de malla","total_finite_volume_cells":"cantidad de celdas","cycles_requested":"horizonte","point_configuration_sha256":"identidad de configuración"}
        named=[labels.get(key,key) for key in differing]
        if differing==['point_configuration_sha256']:
            self.condition_notice.setText("Configuraciones distintas: consultar el diff geométrico. Los demás campos reportados coinciden; esto no demuestra igualdad de parámetros no informados ni convergencia.")
        else:
            self.condition_notice.setText(("Advertencia: las corridas difieren en "+", ".join(named)+"; la comparación no aísla sólo el cambio de escape." ) if differing else "Condiciones comparables en los campos reportados; los campos ausentes no se asumen iguales." )
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
            from ..power_curve import import_curve_runs
            run_background(import_curve_runs,paths,on_done=self._loaded_exploratory,on_error=self._exploratory_failed)
    def _loaded_exploratory(self,data):
        requested_rpms=_referenced_curve_rpms(self.context.project,data)
        if requested_rpms:data['requested_rpms']=requested_rpms
        self.dataset=data;self.source=None;self.source_kind="EXPLORATORY";self.path_label.setText(f"{len(data['points'])} ciclos EXPLORATORY · provisional · no interpolación · no validación experimental")
        runs=sorted({str(r.get("run_id")) for r in data["points"] if r.get("run_id")})
        variants_shown=sorted({str(r.get("variant_id")) for r in data["points"]})
        self.source_notice.setText(f"Corridas exploratorias · variantes: {', '.join(variants_shown)} · sólo lectura, sin asociación automática al proyecto · sin validación experimental.")
        variants=sorted({r['variant_id'] for r in data['points']});self.variants.blockSignals(True);self.variants.clear()
        for name in variants:
            item=QListWidgetItem(name);item.setFlags(item.flags()|Qt.ItemFlag.ItemIsUserCheckable);item.setCheckState(Qt.CheckState.Checked);self.variants.addItem(item)
        self._project_context_changed()
        self.variants.blockSignals(False)
        self.trace_metric.blockSignals(True);self.trace_metric.clear()
        traces=data.get("traces",[])
        self.trace_rpm.blockSignals(True);self.trace_rpm.clear();self.trace_rpm.addItem('Todas las RPM',None)
        for rpm in sorted({t['rpm'] for t in traces}):self.trace_rpm.addItem(f'{rpm:g} RPM',rpm)
        self.trace_rpm.blockSignals(False)
        common=(set.intersection(*(set(row.get("channels",{})) for row in traces)
                                 if traces else [set()]))
        options=[]
        for key in sorted(common):
            if key.startswith("duct:exhaust:cell:") and key.endswith(":pressure_pa"):
                options.append((f"Presión absoluta escape · celda {key.split(':')[3]} (bar abs)",key))
            elif key.startswith("duct:exhaust:face:") and key.endswith(":mass_flow_kg_s"):
                options.append((f"Flujo escape · cara {key.split(':')[3]} (kg/s)",key))
        if "cylinder_pressure_pa" in common:
            options.append(("Presión absoluta cilindro (bar abs)","cylinder_pressure_pa"))
        for label,key in options:self.trace_metric.addItem(label,key)
        self.trace_metric.blockSignals(False)
        self.trace_group.setVisible(bool(traces and options))
        if traces and options:self.trace_status.setText("Conservación interna · sin auditoría independiente · muestras aceptadas" if data.get("audit_method")=="INTERNAL_CONSERVATION_NO_REPLAY" else "Integridad según formato · consultar auditoría por corrida" if data.get("audit_method")=="MIXED_SCHEMAS" else "Primarios re-auditados · ángulos comunes exactos · sin interpolación")
        elif not traces:self.trace_status.setText("Los primarios seleccionados no contienen trazas de presión/flujo disponibles.")
        else:self.trace_status.setText("No hay canales de presión/flujo comunes en los primarios seleccionados.")
        if not traces or not options:
            reason="No hay trazas auditadas de presión/flujo disponibles." if not traces else "No hay canales de presión/flujo comunes para superponer."
            self.source_notice.setText(self.source_notice.text()+" "+reason)
        self.redraw();self.redraw_trace();self._redraw_trace_map();self._update_condition_notice();self._update_engineering_compare();self._dataset_summary();self.evidence_updated.emit()
    def _exploratory_failed(self,message):
        self.path_label.setText("Ejecución EXPLORATORY inválida");self.trace_group.hide();QMessageBox.warning(self,"Artifact exploratorio inválido",message)
    def load(self,path,*,historical=False):
        path=Path(path)
        if path.suffix.lower() in {".json",".csv"}:
            try:
                metadata=path.with_suffix('.json') if path.suffix.lower()=='.csv' else path
                raw=json.loads(metadata.read_text(encoding="utf-8"))
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
            self.variants.blockSignals(False);self._project_context_changed();self.loading=False;self.redraw();self._baseline_changed();self._dataset_summary();self.evidence_updated.emit()
        def fail(message):self.loading=False;self.path_label.setText("No se pudieron cargar los datos");QMessageBox.warning(self,"Reporte inválido",message)
        run_background(load_results,path,on_done=done,on_error=fail)

    def _dataset_summary(self):
        rows=self.dataset.get('points',[]) if self.dataset else []
        states=sorted({_state_label(row.get('classification')) or 'Sin clasificación' for row in rows})
        kind='Histórico sintético' if getattr(self,'source_kind',None)=='HISTORICAL_IMPL2' else 'Resultados exploratorios / importados'
        self.run_summary.setText(f"{kind} · {len(rows)} puntos · {'; '.join(states)}")
        for table in (self.point_table,self.power_curves.points):
            table.setCurrentCell(-1,-1);table.clearSelection()
        self.details.setRowCount(0)
        for card,name in zip(self.metric_cards,('Potencia','Torque','BMEP','Auditoría')):card.setText(name+'\n—')
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
            series.append({"name":("Baseline · " if name==baseline else "")+name,"unit":unit,"role":"baseline" if name==baseline else "variant","points":points})
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
        self._update_engineering_compare()
        self.power_curves.set_dataset(self.dataset, selected)
        self.compare_measurement()
    def redraw_trace(self,*_):
        if not self.dataset or self.dataset.get("schema") not in {"DINO_EXPLORATORY_COMPARISON_V1","DINO_DESKTOP_ENGINEERING_DATA_V1"}:
            self.trace_plot.set_series([]);self.trace_legend.setText("");return
        key=self.trace_metric.currentData()
        if not key:
            self.trace_plot.set_series([]);self.trace_legend.setText("");self._redraw_trace_map();return
        selected={self.variants.item(i).text() for i in range(self.variants.count())
                  if self.variants.item(i).checkState()==Qt.CheckState.Checked}
        series=[];labels=[]
        for trace in self.dataset.get("traces",[]):
            if trace.get("variant_id") not in selected:continue
            if self.trace_rpm.currentData() is not None and trace.get('rpm')!=self.trace_rpm.currentData():continue
            channel=trace.get("channels",{}).get(key)
            if not isinstance(channel,dict):continue
            name=f"{trace['variant_id']} · {trace['rpm']:g} RPM · ciclo {trace['cycle']}"
            labels.append(name)
            pressure=key.endswith("pressure_pa")
            unit="bar abs" if pressure else channel.get("unit","")
            values=[(float(value)/100000.0 if value is not None else None) for value in channel.get("values",[])] if pressure else channel.get("values",[])
            baseline=self.baseline_selector.currentData()==trace.get("variant_id")
            series.append({"name":name,"unit":unit,"role":"baseline" if baseline else "variant",
                "x_key":"angle_deg","x_label":"Ángulo de cigüeñal (°)",
                "points":[{"angle_deg":angle,"value":value}
                           for angle,value in zip(trace["angles_deg"],values)]})
        pressure=key.endswith("pressure_pa")
        self.trace_plot.set_series(series,y_scale_mode="nonnegative_data_margin" if pressure else "data_margin")
        self.trace_legend.setText("Series: " + " | ".join(labels) if labels else "Sin trazas disponibles")
        self._redraw_trace_map()

    def _redraw_trace_map(self):
        """Render exact cell/angle samples into a discrete QImage without interpolation."""
        if not self.dataset or self.dataset.get("schema") not in {"DINO_EXPLORATORY_COMPARISON_V1","DINO_DESKTOP_ENGINEERING_DATA_V1"}:
            self.trace_map.set_grid([],[]);return
        selected={self.variants.item(i).text() for i in range(self.variants.count()) if self.variants.item(i).checkState()==Qt.CheckState.Checked}
        key=self.trace_metric.currentData()
        if not key or not key.startswith("duct:exhaust:"):
            self.trace_map.set_grid([],[]);return
        family="cell" if ":cell:" in key else ("face" if ":face:" in key else None)
        if family is None:self.trace_map.set_grid([],[]);return
        suffix=key.rsplit(":",1)[-1];channels=[];angles=set()
        traces=[trace for trace in self.dataset.get("traces",[]) if trace.get("variant_id") in selected and
                (self.trace_rpm.currentData() is None or trace.get('rpm')==self.trace_rpm.currentData())]
        for trace in traces:
            for channel,channel_doc in (trace.get("channels") or {}).items():
                if not (channel.startswith(f"duct:exhaust:{family}:") and channel.endswith(":"+suffix)):continue
                values=channel_doc.get("values",[]) if isinstance(channel_doc,dict) else channel_doc
                angles.update(float(a) for a in trace.get("angles_deg",[]))
                index=int(channel.split(":")[3]);positions=self._trace_positions(trace,family)
                if family=="cell" and index+1<len(positions):length=abs(float(positions[index+1])-float(positions[index]))*1000;position=(float(positions[index])+float(positions[index+1]))/2
                elif index<len(positions):length=1.;position=float(positions[index])
                else:length=1.;position=None
                label=f"{trace.get('variant_id','variante')} · {family} {index} · {trace.get('run_id','run')}"
                channels.append({"trace":trace,"label":label,"index":index,"values_by_angle":{float(a):v for a,v in zip(trace.get("angles_deg",[]),values)},"length_mm":length,"position_m":position})
        ordered=sorted(angles);rows=[]
        for entry in channels:
            rows.append({"label":entry["label"],"group":f"{entry['trace'].get('variant_id')} · {entry['trace'].get('run_id')} · {entry['trace'].get('cycle')}","length_mm":entry["length_mm"],"position_m":entry["position_m"],"values":[entry["values_by_angle"].get(angle) for angle in ordered]})
        self.trace_map.set_grid(ordered,rows)
        value_range=self.trace_map.value_range
        self.trace_map_legend.setText((f"Mapa discreto posición × ángulo · escala {value_range[0]:.6g}–{value_range[1]:.6g} · celdas reales en bandas proporcionales · muestras exactas, sin interpolar." if value_range else "Mapa discreto posición × ángulo · no hay muestras numéricas disponibles; no se interpolan ni se sustituyen datos ausentes."))
        self.trace_map.setToolTip("QImage construido con muestras originales. Cada banda representa una celda espacial y cada bloque coloreado conserva un valor muestreado; las ausencias quedan vacías.")

    def _trace_positions(self,trace,family):
        """Resolve positions only when the loaded run hash matches this project config exactly."""
        point=next((row for row in (self.dataset or {}).get("points",[]) if row.get("point_id")==trace.get("point_id")),None)
        variant=trace.get("variant_id");engine=(self.context.project["base_engine"] if variant=="base" else self.context.project["variants"].get(variant))
        if not point or not engine or point.get("point_configuration_sha256")!=engine.get("native_configuration_sha256"):
            return []
        duct=next((d for d in engine["native_configuration"].get("ducts",[]) if d.get("id")=="exhaust"),None)
        mesh=(duct or {}).get("mesh",{})
        return mesh.get("faces" if family=="cell" else "centers",[])
    def _point_row_selected(self,row,*_):
        if row<0 or self.point_table.item(row,0) is None:return
        data=self.point_table.item(row,0).data(Qt.ItemDataRole.UserRole)
        if data:self.show_point({"point":data,"rpm":data['rpm'],"value":None})
    def show_point(self,point):
        row=point.get('point',point)
        if row.get('rpm') is not None:
            index=self.trace_rpm.findData(row['rpm'])
            if index>=0:self.trace_rpm.setCurrentIndex(index)
        def card(label,key,unit):
            status=row.get(key+"_status");value=row.get(key)
            if status=="DEFINED" and value is not None:return f"{label}\n{float(value):.4g} {unit} · Δ vs baseline disponible si comparable"
            transient=row.get("transient_estimates",{}).get(key)
            if transient is not None:return f"{label}\n{transient:.4g} {unit} · TRANSITORIO, NO CONVERGIDO"
            reason=row.get(key+"_reason") or row.get(key+"_status") or "No reportado"
            return f"{label}\nNo definido · {reason}"
        self.metric_cards[0].setText(card("Potencia","brake_power","kW"))
        self.metric_cards[1].setText(card("Torque","brake_torque","N·m"))
        self.metric_cards[2].setText(card("BMEP","BMEP","kPa"))
        self.metric_cards[3].setText(f"Auditoría\n{_state_label(row.get('audit_status','NOT_REPORTED'))} · recomputada: {row.get('audit_recomputed','NOT_REPORTED')}")
        conservation=row.get('conservation')
        conservation_label=("balance interno · máx. residuo relativo "+format(max(conservation['relative'].values()),'.2g') if isinstance(conservation,dict) and conservation.get('relative') else 'reportada' if conservation else 'no reportada')
        self.run_summary.setText(f"{row.get('variant_id','Variante no informada')} · {row.get('rpm','—')} RPM · {_state_label(row.get('classification'))} · periodicidad {_state_label(row.get('periodicity') or row.get('classification'))} · {conservation_label}")
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
            ("Tiempo acumulado (s)",row.get('elapsed_seconds')),
            ("Estabilidad observada; no sustituye periodicidad global",json.dumps(row.get('stability_observed'),ensure_ascii=False)),
            ("Métrica",row.get(METRICS[self.metric_selector.currentText()])),
            ("Estado métrica",row.get(METRICS[self.metric_selector.currentText()]+'_status')),
            ("Motivo",row.get(METRICS[self.metric_selector.currentText()]+'_reason')),
            ("Conservación",json.dumps(row.get('conservation'),ensure_ascii=False,sort_keys=True)),
            ("Hard gates",json.dumps(row.get('hard_gates'),ensure_ascii=False,sort_keys=True)),
            ("Validación experimental",row.get('experimental_validation',self.dataset.get('experimental_validation','NOT_REPORTED'))),
            ("Provenance",self.dataset['provenance'])]
        gates=row.get('hard_gates')
        items=list(row.get("engineering_diagnostics",{}).items())+items
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
            companion=Path(path).with_suffix('.json')
            reusable=self.dataset.get('schema')=='MOTORSIM_IMPORTED_CURVE_DATASET_V1'
            if reusable and companion.exists():
                raise FileExistsError(f"Ya existe {companion.name}. Elegí otro nombre para conservar ese archivo.")
            if reusable:json.dumps(self.dataset,allow_nan=False)
            keys=sorted(set().union(*(row.keys() for row in self.dataset['points'])))
            with open(path,'w',encoding='utf-8-sig',newline='') as stream:
                writer=csv.DictWriter(stream,fieldnames=keys,extrasaction='ignore');writer.writeheader()
                for row in self.dataset['points']:writer.writerow({k:json.dumps(row[k],ensure_ascii=False) if isinstance(row.get(k),(dict,list)) else row.get(k) for k in keys})
            if reusable:
                from ..engine_results import SCHEMA
                report={"schema":SCHEMA,**self.dataset['identity'],
                    "experimental_validation":"NOT_PERFORMED","units":self.dataset['units'],
                    "points":self.dataset['points'],"campaign_status":self.dataset.get('campaign_status'),
                    "csv":Path(path).name,"csv_sha256":hashlib.sha256(Path(path).read_bytes()).hexdigest()}
                with companion.open('x',encoding='utf-8') as stream:
                    json.dump(report,stream,ensure_ascii=False,allow_nan=False,indent=2)
                self.path_label.setText(f"Exportado: {Path(path).name} + {companion.name}. Conservá ambos para reabrir los resultados.")
            else:
                self.path_label.setText("Tabla CSV exportada para consulta. Para reabrir corridas exploratorias, conservá result.json y sus artifacts originales.")
        except (OSError,ValueError) as exc:QMessageBox.warning(self,"Error de escritura",str(exc))
    def export_png(self):
        path,_=QFileDialog.getSaveFileName(self,"Exportar gráfico","dino-curva.png","PNG (*.png)")
        if path:
            pix=QPixmap(self.plot.size());self.plot.render(pix)
            if not pix.save(path,"PNG"):QMessageBox.warning(self,"Error de escritura","No se pudo guardar el gráfico.")
    def export_trace_csv(self):
        if not self.trace_map.raw_samples:return
        path,_=QFileDialog.getSaveFileName(self,"Exportar muestras originales x–θ","dino-mapa-ondas.csv","CSV (*.csv)")
        if not path:return
        angles=self.trace_map.angles
        try:
            with open(path,"w",encoding="utf-8-sig",newline="") as stream:
                writer=csv.writer(stream);writer.writerow(["Señal/celda","Posición (m)","Ángulo (deg)","Valor"])
                for row in self.trace_map.raw_samples:
                    for angle,value in zip(angles,row["values"]):writer.writerow([row["label"],row["position_m"],angle,value])
        except OSError as exc:QMessageBox.warning(self,"Error de escritura",str(exc))
