from __future__ import annotations
import csv,json
import math
from pathlib import Path
from PySide6.QtCore import Qt,Signal,QRect
from PySide6.QtGui import QPixmap,QColor,QPainter,QPen,QImage
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QLabel,QComboBox,QPushButton,
    QFileDialog,QCheckBox,QGroupBox,QListWidget,QListWidgetItem,QTableWidget,QTableWidgetItem,QHeaderView,QMessageBox)
from .plot import CurvePlot
from .performance_curves import PowerCurvePanel
from .services import load_results,run_background
from .preferences import artifact_root,impl2_historical_report_candidate,settings
from ..exploratory_workflow import import_exploratory_runs

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
        title=QLabel("Análisis");title.setObjectName('title');root.addWidget(title)
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
        self.condition_notice=QLabel();self.condition_notice.setWordWrap(True);self.condition_notice.setObjectName("notice");root.addWidget(self.condition_notice)
        self.plot=CurvePlot();root.addWidget(self.plot,2)
        self.power_curves=PowerCurvePanel();root.addWidget(self.power_curves)
        controls=QHBoxLayout();root.addLayout(controls)
        self.unit=QLabel();controls.addWidget(self.unit);controls.addStretch()
        export_table=QPushButton("Exportar tabla CSV");export_table.clicked.connect(self.export_csv);controls.addWidget(export_table)
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
        self.metric_selector.currentIndexChanged.connect(self.redraw);self.variants.itemChanged.connect(self.redraw);self.variants.itemChanged.connect(self._update_engineering_compare);self.plot.pointSelected.connect(self.show_point);self.power_curves.pointSelected.connect(self.show_point)
        self.baseline_selector.currentIndexChanged.connect(self._baseline_changed)
        root.removeWidget(self.trace_group);root.insertWidget(root.indexOf(self.plot),self.trace_group)
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
                        rows.append((label,f"{x:.4g} {unit}",f"{y:.4g} {unit}",f"{y-x:+.4g} {unit}","NO CONVERGIDO; diferencia transitoria, no ganancia confirmada" if b.get('periodicity')=='NOT_CONVERGED' or c.get('periodicity')=='NOT_CONVERGED' else "Estimación de ingeniería"))
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
            if b.get('periodicity')=='NOT_CONVERGED' or c.get('periodicity')=='NOT_CONVERGED':condition+="; TRANSITORIOS: no demuestra ganancia de potencia del escape"
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
        self.source_notice.setText(f"Proyecto abierto: {self.context.project['project_id']} · corridas EXPLORATORY importadas: {', '.join(runs) or 'sin identificador'} · variantes: {', '.join(variants_shown)}. Son artifacts de sólo lectura y no se asocian ni guardan automáticamente en el proyecto.")
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
        self.redraw();self.redraw_trace();self._redraw_trace_map();self._update_condition_notice();self._update_engineering_compare();self.evidence_updated.emit()
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
