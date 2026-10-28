from __future__ import annotations
from copy import deepcopy
import math
from PySide6.QtCore import Qt,QPointF,Signal
from PySide6.QtGui import QColor,QPainter,QPen,QFont
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QFormLayout,QGroupBox,QLabel,QTabWidget,
    QDoubleSpinBox,QPushButton,QComboBox,QTableWidget,QTableWidgetItem,QHeaderView,QMessageBox,QDialog,QDialogButtonBox,QSplitter)
from ..engine_configuration import validate,identity,sha256
from ..two_stroke_ports import TwoStrokePortSet,DuctBinding,PortDefinition
from ..crankcase import CrankcaseGeometry
from ..integrated_2t import SliderCrankChambers2T
from ..gas1d.mesh import Mesh


class CylinderSketch(QWidget):
    def __init__(self,parent=None):
        super().__init__(parent);self.bore=50.0;self.stroke=50.0;self.rod=100.0;self.setMinimumHeight(60);self.setMaximumHeight(66);self.setMinimumWidth(220)
    def set_geometry(self,bore,stroke,rod):self.bore=float(bore);self.stroke=float(stroke);self.rod=float(rod);self.update()
    def paintEvent(self,event):
        p=QPainter(self);p.setRenderHint(QPainter.RenderHint.Antialiasing);p.fillRect(self.rect(),QColor("#101a28"))
        mid=self.width()*.42;top=18;bottom=self.height()-24;w=min(self.width()*.22,100);p.setPen(QPen(QColor("#91a8bf"),2));p.drawLine(round(mid-w/2),top,round(mid-w/2),bottom-18);p.drawLine(round(mid+w/2),top,round(mid+w/2),bottom-18)
        piston_y=top+(bottom-top)*.52;p.setBrush(QColor("#287ca4"));p.setPen(QPen(QColor("#7dd3fc"),2));p.drawRect(round(mid-w/2+2),round(piston_y-10),round(w-4),20)
        crank=QPointF(mid+w*.55,bottom-18);p.setPen(QPen(QColor("#f6bd60"),4));p.drawLine(QPointF(mid,piston_y+10),crank);p.setBrush(QColor("#f6bd60"));p.drawEllipse(crank,5,5)
        p.setPen(QColor("#e5edf6"));p.setFont(QFont("Segoe UI",9));p.drawText(8,16,f"Ø {self.bore:g} mm");p.drawText(8,self.height()-5,f"Carrera {self.stroke:g} mm · biela {self.rod:g} mm")
        p.setPen(QPen(QColor("#547088"),1,Qt.PenStyle.DashLine));p.drawLine(round(mid+w/2+10),round(top+(bottom-top)*.24),round(mid+w/2+28),round(top+(bottom-top)*.24));p.drawLine(round(mid+w/2+10),round(top+(bottom-top)*.76),round(mid+w/2+28),round(top+(bottom-top)*.76));p.drawLine(round(mid+w/2+24),round(top+(bottom-top)*.24),round(mid+w/2+24),round(top+(bottom-top)*.76));p.end()


class PortAreaPlot(QWidget):
    COLORS=("#43c5f5","#f6bd60","#a78bfa","#34d399","#fb7185","#f97316")
    def __init__(self,parent=None):super().__init__(parent);self.series=[];self.setMinimumHeight(170)
    def set_series(self,series):self.series=series;self.update()
    def paintEvent(self,event):
        p=QPainter(self);p.setRenderHint(QPainter.RenderHint.Antialiasing);p.fillRect(self.rect(),QColor("#101a28"));r=self.rect().adjusted(48,14,-14,-28)
        p.setPen(QPen(QColor("#43576b"),1));p.drawRect(r)
        maximum=max((float(v) for s in self.series for _,v in s["points"]),default=1.0);maximum=max(maximum,1e-9)
        for a in range(0,361,90):
            x=r.left()+a/360*r.width();p.setPen(QColor("#a8bbcd"));p.drawText(round(x)-16,r.bottom()+19,36,14,Qt.AlignmentFlag.AlignCenter,str(a));p.setPen(QPen(QColor("#27394d"),1,Qt.PenStyle.DotLine));p.drawLine(round(x),r.top(),round(x),r.bottom())
        for i,s in enumerate(self.series):
            color=QColor(self.COLORS[i%len(self.COLORS)]);p.setPen(QPen(color,2));points=[QPointF(r.left()+a/360*r.width(),r.bottom()-v/maximum*r.height()) for a,v in s["points"]]
            if len(points)>1:p.drawPolyline(points)
            p.drawText(r.left()+8,r.top()+14+i*16,s["name"])
        p.setPen(QColor("#cad8e7"));p.drawText(2,r.top()+12,42,14,Qt.AlignmentFlag.AlignRight,"mm²");p.drawText(r.left(),self.height()-3,"Ángulo de cigüeñal (°)");p.end()


class EnginePage(QWidget):
    component_state_changed=Signal()
    def __init__(self,context):
        super().__init__();self.context=context;self.loading=False
        root=QVBoxLayout(self);root.setContentsMargins(12,10,12,10);root.setSpacing(7)
        title=QLabel("Motor");title.setObjectName("title");root.addWidget(title)
        title.setToolTip("Geometría y distribución derivada del modelo actual.")
        self.component_tabs=QTabWidget();root.addWidget(self.component_tabs,1)
        self.geometry_group=QGroupBox("Geometría y operación");form=QFormLayout(self.geometry_group)
        self.cylinder_diagram=CylinderSketch();form.addRow("Esquema del cilindro",self.cylinder_diagram)
        self.advanced_operation=QGroupBox("Avanzado · operación y metadata")
        self.advanced_operation_toggle=QPushButton("Avanzado ▸")
        self.advanced_operation_toggle.clicked.connect(self._toggle_advanced_operation)
        self.advanced_operation.hide()
        advanced_form=QFormLayout(self.advanced_operation)
        self.controls={}
        definitions=[("bore_mm","Diámetro cilindro","mm",1,250),("stroke_mm","Carrera","mm",1,250),
          ("rod_length_mm","Longitud biela","mm",1,500),("volume_bdc_cm3","Cárter en PMI","cm³",0.1,5000),
          ("cylinder_compression_ratio","Compresión geométrica",":1",1.01,40),("reference_rpm","RPM de referencia","rpm",100,30000),
          ("load","Carga del mapa MEP","relativa",0,10),
          ("afr","AFR declarada · metadata","kg/kg",0.01,1000)]
        for key,label,unit,low,high in definitions:
            spin=QDoubleSpinBox();spin.setObjectName("engine_"+key);spin.setRange(low,high);spin.setDecimals(0 if key=="reference_rpm" else (1 if key=="afr" else 2));spin.setSingleStep(0.1);spin.setMaximumWidth(150);spin.setMaximumHeight(28)
            self.controls[key]=spin
            (advanced_form if key in {"reference_rpm","load","afr"} else form).addRow(f"{label} ({unit})",spin)
            spin.valueChanged.connect(lambda _v:self._mark_component(0,"modificado"))
        self.intake_control=QComboBox();self.intake_control.setObjectName("engine_intake_control")
        self.intake_control.addItem("Láminas (reed)","reed");self.intake_control.addItem("Controlado por pistón","piston_port")
        self.intake_control.setToolTip("Selecciona uno de los dos controles declarados por GAS_EXCHANGE_V2.")
        form.addRow("Control de admisión",self.intake_control)
        self.intake_control.currentIndexChanged.connect(lambda *_:self._mark_component(0,"modificado"))
        self.controls["load"].setToolTip(
            "Sólo selecciona pérdidas si el modelo mecánico declara un mapa dependiente de carga; "
            "no controla mariposa, admisión ni la carga del flujo de gas.")
        self.controls["afr"].setEnabled(False)
        self.controls["afr"].setToolTip(
            "El AFR de operación se conserva como metadata. La entrega de aire/combustible "
            "la determina el estado de especies del modelo; este campo no modifica el solver.")
        afr_note=QLabel("AFR guardado como metadata; no es una consigna de mezcla.");afr_note.setWordWrap(True);advanced_form.addRow(afr_note)
        self.provenance_label=QLabel();self.provenance_label.setWordWrap(True);self.provenance_label.setObjectName("notice");form.addRow("Origen de los datos",self.provenance_label)
        self.provenance_button=QPushButton("Clasificar datos…");self.provenance_button.clicked.connect(self.edit_provenance);form.addRow("",self.provenance_button)
        form.addRow(self.advanced_operation_toggle);form.addRow(self.advanced_operation)
        self.port_group=QGroupBox("Lumbreras y distribución");v=QVBoxLayout(self.port_group)
        v.addWidget(QLabel("Lumbreras · dimensiones y eventos derivados"))
        self.ports=QTableWidget(0,10);self.ports.setObjectName("integratedPortTiming");self.ports.setHorizontalHeaderLabels(["Lumbrera","Rol","Ø borde","Alt. (mm)","Ancho (mm)","Cd","Rec. (mm)","Abre (°)","Cierra (°)","Dur. (°)"])
        self.ports.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        for col,width in enumerate((105,56,78,64,55,43,55,58,58,68)):self.ports.setColumnWidth(col,width)
        for col in (4,5,6):self.ports.setColumnHidden(col,True)
        self.port_advanced_toggle=QPushButton("Más dimensiones ▸");self.port_advanced_toggle.clicked.connect(self._toggle_advanced_ports);v.addWidget(self.port_advanced_toggle)
        self.ports.setAlternatingRowColors(True);self.ports.setMinimumHeight(248);self.ports.setMaximumHeight(254);self.ports.cellChanged.connect(self._port_changed);v.addWidget(self.ports)
        self.derived=QLabel();self.derived.setWordWrap(True);v.addWidget(self.derived)
        self.timing=QTableWidget(0,4);self.timing.setObjectName("portTiming");self.timing.setHorizontalHeaderLabels(["Lumbrera","Abre °","Cierra °","Duración °"]);self.timing.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch);self.timing.hide()
        self.area_plot=PortAreaPlot();self.area_plot.setObjectName("portAreaAnglePlot");self.area_plot.setMinimumHeight(130);self.area_plot.setMaximumHeight(165)
        self.port_areas=QTableWidget(0,3);self.port_areas.setHorizontalHeaderLabels(["Lumbrera","Evento existente (°)","Área efectiva (mm²)"])
        self.port_areas.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch);self.port_areas.setMaximumHeight(350)
        intake_page=QWidget();intake_layout=QVBoxLayout(intake_page)
        intake_layout.addWidget(QLabel("Conductos rectos de sección circular constante. Se conserva la cantidad de volúmenes de la malla existente; el escape se edita en su pantalla."))
        self.ducts=QTableWidget(0,4);self.ducts.setObjectName("editableIntakeTransferDucts")
        self.ducts.setHorizontalHeaderLabels(["Conducto","Rol","Longitud (mm)","Diámetro (mm)"])
        self.ducts.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.ducts.cellChanged.connect(lambda *_:self._mark_component(4,"modificado"));intake_layout.addWidget(self.ducts)
        self.reed_group=QGroupBox("Láminas · modelo cuasiestático activo");reed_layout=QVBoxLayout(self.reed_group)
        reed_layout.addWidget(QLabel("Masa, amortiguamiento y restitución no se editan: la configuración actual no usa el vínculo dinámico de láminas."))
        self.reeds=QTableWidget(0,6);self.reeds.setObjectName("effectiveStaticReedParameters")
        self.reeds.setHorizontalHeaderLabels(["ID","Área presión (cm²)","Ancho (mm)","Rigidez (N/m)","Tope (mm)","Cd"])
        self.reeds.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.reeds.cellChanged.connect(lambda *_:self._mark_component(4,"modificado"));reed_layout.addWidget(self.reeds)
        intake_layout.addWidget(self.reed_group)
        mixed_form=QFormLayout();self.mixed_outflow=QDoubleSpinBox();self.mixed_outflow.setObjectName("mixedOutflowFraction")
        self.mixed_outflow.setRange(0,1);self.mixed_outflow.setDecimals(4);self.mixed_outflow.setSingleStep(.05)
        self.mixed_outflow.valueChanged.connect(lambda *_:self._mark_component(4,"modificado"))
        mixed_form.addRow("Fracción de mezcla de salida (0–1)",self.mixed_outflow);intake_layout.addLayout(mixed_form)
        intake_layout.addWidget(QLabel("Geometrías variables, curvas, rugosidad y condiciones de borde no representadas en esta edición no se infieren ni se muestran como controles."))
        self.loss_group=QGroupBox("Pérdidas mecánicas explícitas");loss_layout=QVBoxLayout(self.loss_group)
        loss_layout.addWidget(QLabel("Editá la MEP de cada término declarado. Se conserva modelo, fuente y provenance; no se insertan defaults."))
        self.losses=QTableWidget(0,4);self.losses.setHorizontalHeaderLabels(["Término","Fuente","MEP (Pa)","Provenance"])
        self.losses.cellDoubleClicked.connect(self._edit_loss_map)
        self.losses.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        for col,width in enumerate((150,140,90,260)):self.losses.setColumnWidth(col,width)
        self.losses.cellChanged.connect(lambda *_:self._mark_component(2,"modificado"));loss_layout.addWidget(self.losses)
        self.combust_group=QGroupBox("Combustión y combustible");f=QFormLayout(self.combust_group)
        self.comb={}
        for key,label,unit,lo,hi in [("combustion_efficiency","Eficiencia declarada","1",0,1),("ignition_timing_deg","Inicio/encendido","°",0,720),("duration_deg","Duración","°",0,720),("shape_a","Forma A","—",0.01,100),("shape_m","Forma M","—",0.01,100)]:
            spin=QDoubleSpinBox();spin.setRange(lo,hi);spin.setDecimals(2);self.comb[key]=spin;f.addRow(f"{label} ({unit})",spin);spin.valueChanged.connect(lambda _v:self._mark_component(3,"modificado"))
        self.combustion_notice=QLabel();self.combustion_notice.setWordWrap(True);f.addRow(self.combustion_notice)
        self.fuel=QLabel();self.fuel.setWordWrap(True);self.fuel.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        f.addRow("Fuel snapshot",self.fuel)
        self.component_names=("Cilindro y distribución","Eventos de área","Pérdidas","Combustión y combustible")
        integrated=QWidget();integrated_layout=QVBoxLayout(integrated);integrated_layout.setContentsMargins(0,0,0,0)
        split=QSplitter(Qt.Orientation.Horizontal,integrated);split.setChildrenCollapsible(False)
        split.addWidget(self.geometry_group);split.addWidget(self.port_group);split.setStretchFactor(0,1);split.setStretchFactor(1,2)
        integrated_layout.addWidget(split,1);integrated_layout.addWidget(self.area_plot,1);self.component_tabs.addTab(integrated,self.component_names[0])
        event_page=QWidget();event_layout=QVBoxLayout(event_page);event_layout.addWidget(QLabel("Eventos y áreas efectivas reportados por el modelo existente. La edición habitual y sus grados de apertura/cierre están en Cilindro y distribución."));event_layout.addWidget(self.port_areas,1);self.component_tabs.addTab(event_page,self.component_names[1])
        for name,widget in ((self.component_names[2],self.loss_group),(self.component_names[3],self.combust_group)):
            pane=QWidget();layout=QVBoxLayout(pane);layout.addWidget(widget);layout.addStretch(1);self.component_tabs.addTab(pane,name)
        self.component_names=(*self.component_names,"Admisión y conductos")
        self.component_tabs.addTab(intake_page,self.component_names[4])
        self.validation=QLabel();self.validation.setWordWrap(True);self.validation.setObjectName("notice");root.addWidget(self.validation)
        buttons=QHBoxLayout();root.addLayout(buttons)
        self.apply_button=QPushButton("Validar y aplicar cambios");self.apply_button.setObjectName("primaryAction");self.apply_button.clicked.connect(self.apply);buttons.addWidget(self.apply_button)
        self.revert_button=QPushButton("Descartar edición");self.revert_button.clicked.connect(self.refresh);buttons.addWidget(self.revert_button);buttons.addStretch(1)
        self.context.changed.connect(self.refresh);self.refresh()

    def refresh(self):
        self.loading=True
        try:
            doc=self.context.engine();n=doc["native_configuration"];slider=n["slider_crank"];cc=slider["crankcase"];cond=doc["operating_conditions"]
            values={"bore_mm":cc["bore_mm"],"stroke_mm":cc["stroke_mm"],"rod_length_mm":cc["rod_length_mm"],"volume_bdc_cm3":cc["volume_bdc_cm3"],"cylinder_compression_ratio":slider["cylinder_compression_ratio"],"reference_rpm":cond["reference_rpm"],"load":cond["load"],"afr":cond["afr"]}
            self._loaded_design_inputs={key:float(values[key]) for key in ("bore_mm","stroke_mm","rod_length_mm","volume_bdc_cm3","cylinder_compression_ratio","reference_rpm")}
            for key,value in values.items():self.controls[key].setValue(float(value))
            exchange=n["geometry_identity"].get("gas_exchange_model")
            self.intake_control.blockSignals(True)
            control=(exchange or {}).get("intake_control","piston_port")
            self.intake_control.setCurrentIndex(max(0,self.intake_control.findData(control)))
            self._loaded_intake_control=control
            self.intake_control.setEnabled(exchange is not None)
            self.intake_control.blockSignals(False)
            if exchange is None:self.intake_control.setToolTip("Este proyecto anterior no declara GAS_EXCHANGE_V2; no se habilita un control que no tenga efecto físico.")
            self.mixed_outflow.blockSignals(True);self.mixed_outflow.setValue(float((exchange or {}).get("mixed_outflow_fraction",0.0)));self.mixed_outflow.blockSignals(False)
            self.mixed_outflow.setEnabled(exchange is not None and "mixed_outflow_fraction" in exchange)
            ducts=n.get("ducts",[]);editable=[entry for entry in ducts if entry.get("role") in {"intake","transfer"}]
            self.ducts.blockSignals(True);self.ducts.setRowCount(len(editable));self._duct_ids=[];self._editable_duct_ids=set()
            for row,entry in enumerate(editable):
                mesh=entry["mesh"];area=sum(mesh["areas"])/len(mesh["areas"]);length=mesh["faces"][-1]-mesh["faces"][0]
                constant_area=all(math.isclose(value,mesh["areas"][0],rel_tol=1e-10,abs_tol=1e-14) for value in mesh["areas"])
                self._duct_ids.append(entry["id"])
                if constant_area:self._editable_duct_ids.add(entry["id"])
                diameter=math.sqrt(4*area/math.pi)
                shown_length=f"{length*1000:.6g}" if constant_area else "Sección variable · no editable"
                shown_diameter=f"{diameter*1000:.6g}" if constant_area else "—"
                for col,value in enumerate((entry["id"],entry["role"],shown_length,shown_diameter)):
                    item=QTableWidgetItem(str(value));item.setData(Qt.ItemDataRole.UserRole,entry["id"])
                    if col<2:item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    if col>=2 and not constant_area:
                        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                        item.setToolTip("La malla representa una sección variable; esta pantalla sólo edita conductos de sección circular constante.")
                    self.ducts.setItem(row,col,item)
            self.ducts.blockSignals(False)
            petals=n.get("reed_petals",[]);self.reeds.blockSignals(True);self.reeds.setRowCount(len(petals))
            for row,petal in enumerate(petals):
                values=(petal["id"],petal["pressure_area_m2"]*1e4,petal["effective_width_m"]*1000,petal["stiffness_n_m"],petal["lift_stop_m"]*1000,petal["discharge_coefficient"])
                for col,value in enumerate(values):
                    item=QTableWidgetItem(str(value));item.setData(Qt.ItemDataRole.UserRole,petal["id"])
                    if col==0:item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    self.reeds.setItem(row,col,item)
            self.reeds.blockSignals(False);self.reed_group.setEnabled(control=="reed" and n.get("dynamic_reed_binding") is None)
            self._refresh_provenance(doc)
            self.cylinder_diagram.set_geometry(cc["bore_mm"],cc["stroke_mm"],cc["rod_length_mm"])
            combustion=n.get("fuel_coupled_combustion") or {};component=(combustion.get("components") or [{}])[0]
            for key,value in (("combustion_efficiency",combustion.get("combustion_efficiency",0.0)),("ignition_timing_deg",combustion.get("ignition_timing_deg",0.0)),("duration_deg",component.get("duration_deg",0.0)),("shape_a",component.get("shape_a",1.0)),("shape_m",component.get("shape_m",1.0))):self.comb[key].setValue(float(value))
            combustion_editable=bool(n.get("fuel_coupled_combustion")) and bool(n["fuel_coupled_combustion"].get("components"))
            for control in self.comb.values():control.setEnabled(combustion_editable)
            self.combustion_notice.setText(
                "Estos parámetros son supuestos sintéticos acoplados al solver."
                if combustion_editable else
                "La configuración no tiene un modelo de combustión fuel-coupled; "
                "estos campos no tendrían efecto físico y quedan deshabilitados.")
            snapshot=combustion.get("fuel_snapshot") or {}
            self.fuel.setText(f"{snapshot.get('schema','Sin snapshot')} · {snapshot.get('provenance','provenance no declarada')}\nLos datos de combustible son de solo lectura; importá un snapshot validado para cambiarlo.")
            self.fuel.setToolTip(f"Fuel snapshot SHA-256: {snapshot.get('sha256','no informado')}")
            ports=n["port_binding"]["port_set"]["ports"];port_set=TwoStrokePortSet.from_dict(n["port_binding"]["port_set"])
            timing_by_id={port.id:self._area_timing(port_set,port) for port in port_set.ports}
            self.ports.blockSignals(True);self.ports.setRowCount(len(ports))
            for i,p in enumerate(ports):
                vals=[p["id"],p["role"],p["top_mm"],p["height_mm"],p["width_mm"],p["discharge_coefficient"],p["roof_travel_mm"],*timing_by_id.get(p["id"],(None,None,None))]
                reed_intake=(p["role"]=="intake" and n["geometry_identity"].get("gas_exchange_model",{}).get("intake_control")=="reed")
                if reed_intake:vals[7:]=[None,None,None]
                for j,value in enumerate(vals):
                    display="—" if value is None else (f"{value:.1f}" if isinstance(value,(int,float)) else str(value))
                    item=QTableWidgetItem(display);item.setData(Qt.ItemDataRole.UserRole,p["id"])
                    if j<2 or j>=7 or p["family"]=="effective_profile" or value is None:item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    if reed_intake:
                        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                        item.setToolTip("Admisión por láminas: conexión sin distribución de pistón. El área efectiva depende de Δp y de las láminas, no de esta ventana histórica.")
                    self.ports.setItem(i,j,item)
            self.ports.blockSignals(False)
            bore=cc["bore_mm"];stroke=cc["stroke_mm"];swept=math.pi*(bore/2)**2*stroke/1000
            profile_rows=[]
            for profile in port_set.compile_profiles():
                if profile.event_angles_deg:
                    profile_rows.append(f"{profile.port_id}: " + ", ".join(f"{angle:g}°" for angle in profile.event_angles_deg))
            ratio=stroke/bore;rod_ratio=cc["rod_length_mm"]/stroke;mean_speed=2*stroke/1000*cond["reference_rpm"]/60
            compression=float(slider["cylinder_compression_ratio"])
            clearance=swept/(compression-1.0)
            primary=1.0+swept/float(cc["volume_bdc_cm3"])
            self.derived.setText(f"Cilindrada {swept:.1f} cm³ · cámara derivada {clearance:.2f} cm³ · compresión primaria {primary:.2f}:1 · S/D {ratio:.2f} · biela/carrera {rod_ratio:.2f} · Vm pistón {mean_speed:.2f} m/s")
            self.derived.setToolTip("Distribución calculada por transiciones de área efectiva del backend; no son controles inversos.")
            timing_rows=[];area_series=[];area_rows=[]
            for port in port_set.ports:
                if port.role=="intake" and n["geometry_identity"].get("gas_exchange_model",{}).get("intake_control")=="reed":
                    timing_rows.append(("Admisión por láminas · Δp",None,None,None))
                    continue
                opening,closing,duration=self._area_timing(port_set,port)
                timing_rows.append((port.id,opening,closing,duration))
                area_series.append({"name":port.name,"points":[(angle,port_set.area_at(port,angle)) for angle in (*range(0,360,2),360)]})
                events=port_set.event_angles(port)
                for angle in events:
                    area_rows.append((port.id,angle,port_set.area_at(port,angle)))
            self.timing.setRowCount(len(timing_rows))
            for i,row in enumerate(timing_rows):
                values=(row[0],*("—" if value is None else f"{value:.1f}" for value in row[1:]))
                for j,value in enumerate(values):
                    item=QTableWidgetItem(str(value));item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable);self.timing.setItem(i,j,item)
            self.area_plot.set_series(area_series)
            self.port_areas.setRowCount(len(area_rows))
            for i,(port_id,angle,area) in enumerate(area_rows):
                for j,value in enumerate((port_id,f"{angle:g}",f"{area:.2f}")):
                    item=QTableWidgetItem(str(value));item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable);self.port_areas.setItem(i,j,item)
            terms=doc["mechanical_loss_model"]["terms"];self.loss_model_draft=deepcopy(doc["mechanical_loss_model"])
            self.controls["load"].setEnabled(any(term["operating_map"] is not None for term in terms))
            self.losses.blockSignals(True);self.losses.setRowCount(len(terms))
            for i,term in enumerate(terms):
                model="Fixed MEP" if term["mep_pa"] is not None else f"Mapa {len(term['operating_map']['rpm'])}×{len(term['operating_map']['load'])} (doble clic)"
                for j,value in enumerate((term["id"],term["source"],term["mep_pa"] if term["mep_pa"] is not None else model,term["provenance"])):
                    item=QTableWidgetItem(str(value))
                    if j!=2 or term["mep_pa"] is None:item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    self.losses.setItem(i,j,item)
            self.losses.blockSignals(False)
            self.validation.setText(f"{doc['validation_state']} · Configuración de ingeniería; validación física experimental no realizada.")
            self.apply_button.setEnabled(True)
            for i,name in enumerate(self.component_names):self.component_tabs.setTabText(i,f"{name} · válido")
        except Exception as exc:
            self.validation.setText(f"No se pudo presentar la configuración: {exc}");self.apply_button.setEnabled(False)
        finally:self.loading=False

    def _port_changed(self,*_):
        if not self.loading:
            self._mark_component(1,"modificado")
            self.validation.setText("Edición pendiente. Aplicá para ejecutar la validación completa del backend.")

    def _mark_component(self,index,status):
        if self.loading:return
        self.component_tabs.setTabText(index,f"{self.component_names[index]} · {status}")
        self.component_state_changed.emit()

    def _toggle_advanced_operation(self):
        visible=not self.advanced_operation.isVisible()
        self.advanced_operation.setVisible(visible);self.advanced_operation_toggle.setText("Avanzado ▾" if visible else "Avanzado ▸")

    def _toggle_advanced_ports(self):
        visible=self.ports.isColumnHidden(4)
        for column in (4,5,6):self.ports.setColumnHidden(column,not visible)
        self.port_advanced_toggle.setText("Más dimensiones ▾" if visible else "Más dimensiones ▸")

    def _refresh_provenance(self,doc):
        inputs=doc.get("provenance",{}).get("design_inputs",{})
        labels={"MEASURED":"medido","ESTIMATED":"estimado","SYNTHETIC_ASSUMPTION":"supuesto","UNKNOWN":"sin clasificar","DOCUMENTED":"documentado","DERIVED_FROM_DOCUMENTED":"derivado de documentación"}
        names=("bore_mm","stroke_mm","rod_length_mm","volume_bdc_cm3","cylinder_compression_ratio","reference_rpm","port_dimensions","intake_control","intake_transfer_geometry","reed_static_parameters","mixed_outflow_fraction","exhaust_sections","fuel_model")
        parts=[f"{name}: {labels.get(inputs.get(name,{}).get('classification','UNKNOWN'),'sin clasificar')}" for name in names]
        self.provenance_label.setText(" · ".join(parts))

    def edit_provenance(self):
        doc=deepcopy(self.context.engine());current=doc.setdefault("provenance",{}).setdefault("design_inputs",{})
        dialog=QDialog(self);dialog.setWindowTitle("Origen de los datos del motor");layout=QVBoxLayout(dialog)
        layout.addWidget(QLabel("Clasificá cada dato según su fuente. Los cambios se guardan en la provenance del motor."))
        form=QFormLayout();layout.addLayout(form)
        names=(("bore_mm","Diámetro"),("stroke_mm","Carrera"),("rod_length_mm","Biela"),("volume_bdc_cm3","Volumen del cárter"),("cylinder_compression_ratio","Compresión geométrica"),("reference_rpm","RPM"),("port_dimensions","Lumbreras y distribución"),("intake_control","Control de admisión"),("intake_transfer_geometry","Conductos de admisión y transferencia"),("reed_static_parameters","Láminas estáticas"),("mixed_outflow_fraction","Fracción de mezcla"),("exhaust_sections","Secciones del escape"),("fuel_model","Combustible y combustión"))
        choices=(("Medido","MEASURED"),("Estimado","ESTIMATED"),("Supuesto","SYNTHETIC_ASSUMPTION"),("Sin clasificar","UNKNOWN"))
        selectors={}
        for key,label in names:
            combo=QComboBox()
            for text,value in choices:combo.addItem(text,value)
            classification=current.get(key,{}).get("classification","UNKNOWN")
            index=combo.findData(classification);combo.setCurrentIndex(index if index>=0 else combo.findData("UNKNOWN"))
            selectors[key]=combo;form.addRow(label,combo)
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel|QDialogButtonBox.StandardButton.Save)
        buttons.accepted.connect(dialog.accept);buttons.rejected.connect(dialog.reject);layout.addWidget(buttons)
        if dialog.exec()!=QDialog.DialogCode.Accepted:return
        for key,combo in selectors.items():
            previous=current.get(key,{})
            current[key]={"classification":combo.currentData(),"rationale":previous.get("rationale","Clasificado en el editor de motor." )}
        try:
            from ..engine_configuration import validate
            validate(doc);self.context.replace_engine(doc)
        except Exception as exc:QMessageBox.warning(self,"No se pudo guardar provenance",str(exc))

    def _edit_loss_map(self,row,_column):
        if row>=len(self.loss_model_draft["terms"]):return
        term=self.loss_model_draft["terms"][row];model=term["operating_map"]
        if model is None:return
        dialog=QDialog(self);dialog.setWindowTitle(f"Mapa de pérdidas · {term['id']}");layout=QVBoxLayout(dialog)
        table=QTableWidget(len(model["rpm"]),len(model["load"])+1,dialog)
        table.setHorizontalHeaderLabels(["RPM"]+[f"Carga {x:g}" for x in model["load"]])
        for i,rpm in enumerate(model["rpm"]):
            fixed=QTableWidgetItem(f"{rpm:g}");fixed.setFlags(fixed.flags() & ~Qt.ItemFlag.ItemIsEditable);table.setItem(i,0,fixed)
            for j,value in enumerate(model["values_pa"][i],1):table.setItem(i,j,QTableWidgetItem(str(value)))
        layout.addWidget(QLabel("Editar MEP (Pa). Los ejes declarados por el modelo se conservan."));layout.addWidget(table)
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel);layout.addWidget(buttons)
        buttons.accepted.connect(dialog.accept);buttons.rejected.connect(dialog.reject)
        if dialog.exec()!=QDialog.DialogCode.Accepted:return
        try:
            values=[[float(table.item(i,j).text()) for j in range(1,table.columnCount())] for i in range(table.rowCount())]
            if any(not math.isfinite(value) or value<0 for line in values for value in line):raise ValueError("MEP debe ser finita y no negativa")
            model["values_pa"]=values;self.losses.item(row,2).setText(f"Mapa {len(model['rpm'])}×{len(model['load'])} (editado)")
            self.validation.setText("Mapa mecánico editado en borrador; aplicá para validar y actualizar la identidad.")
        except Exception as exc:self.validation.setText(f"Mapa mecánico rechazado: {exc}")

    def _edited_ports(self,native):
        raw=native["port_binding"]["port_set"];ports=deepcopy(raw["ports"])
        for i,p in enumerate(ports):
            if p["family"]=="effective_profile":continue
            for j,key in ((2,"top_mm"),(3,"height_mm"),(4,"width_mm"),(5,"discharge_coefficient"),(6,"roof_travel_mm")):
                item=self.ports.item(i,j)
                if item and item.flags() & Qt.ItemFlag.ItemIsEditable:
                    text=item.text().strip()
                    try:value=self._decimal(text)
                    except ValueError as exc:raise ValueError(f"Lumbrera {p['name']}: {key} debe ser numérico") from exc
                    if not math.isfinite(value):raise ValueError(f"Lumbrera {p['name']}: valor no finito")
                    p[key]=value
        stroke=self.controls["stroke_mm"].value();rod=self.controls["rod_length_mm"].value()
        profile=TwoStrokePortSet(stroke,rod,tuple(DuctBinding.from_dict(x) for x in raw["ducts"]),tuple(PortDefinition.from_dict(x) for x in ports)).to_dict()
        native["port_binding"]["port_set"]=profile
        native["geometry_identity"]["ports"]=deepcopy(profile)

    def apply(self):
        try:
            doc=deepcopy(self.context.engine());native=doc["native_configuration"];slider=native["slider_crank"];cc=slider["crankcase"]
            design_inputs=doc.setdefault("provenance",{}).setdefault("design_inputs",{})
            source_fields=("bore_mm","stroke_mm","rod_length_mm","volume_bdc_cm3","cylinder_compression_ratio","reference_rpm")
            current_values={key:self.controls[key].value() for key in source_fields}
            for key,value in current_values.items():
                if value!=self._loaded_design_inputs.get(key,value):
                    design_inputs[key]={"classification":"UNKNOWN","rationale":"El valor cambió en el editor; reclasificá su fuente en Clasificar datos."}
            cc.update({key:self.controls[key].value() for key in ("bore_mm","stroke_mm","rod_length_mm","volume_bdc_cm3")})
            slider["cylinder_compression_ratio"]=self.controls["cylinder_compression_ratio"].value()
            exchange=native["geometry_identity"].get("gas_exchange_model")
            if exchange is not None:
                selected=self.intake_control.currentData()
                if selected!=exchange.get("intake_control"):
                    design_inputs["intake_control"]={"classification":"UNKNOWN","rationale":"El control de admisión cambió; reclasificá su fuente en Clasificar datos."}
                exchange["intake_control"]=selected
                if selected=="piston_port":
                    native["reed_petals"]=[];native["dynamic_reed_binding"]=None
                elif selected=="reed" and not native.get("reed_petals"):
                    from .services import starter_reed_petals
                    petals=starter_reed_petals()
                    if not petals:raise ValueError("La plantilla no declara una geometría de láminas compatible.")
                    native["reed_petals"]=petals
                    native["dynamic_reed_binding"]=None
            self._edited_ports(native)
            changed_ducts=False
            by_id={entry["id"]:entry for entry in native.get("ducts",[])}
            for row,path_id in enumerate(getattr(self,"_duct_ids",[])):
                if path_id not in getattr(self,"_editable_duct_ids",set()):continue
                if path_id not in by_id:continue
                entry=by_id[path_id];old=entry["mesh"]
                try:length_mm=self._decimal(self.ducts.item(row,2).text());diameter_mm=self._decimal(self.ducts.item(row,3).text())
                except (ValueError,AttributeError) as exc:raise ValueError(f"Conducto {path_id}: longitud y diámetro deben ser numéricos") from exc
                if not all(math.isfinite(v) and v>0 for v in (length_mm,diameter_mm)):raise ValueError(f"Conducto {path_id}: longitud y diámetro deben ser positivos")
                length_m=length_mm/1000;area=math.pi*(diameter_mm/1000)**2/4
                start,end=old["faces"][0],old["faces"][-1];span=end-start
                faces=[length_m*(face-start)/span for face in old["faces"]]
                volumes=[area*(right-left) for left,right in zip(faces,faces[1:])]
                new=Mesh(tuple(faces),(area,)*(len(faces)),tuple(volumes),
                         tuple((left+right)/2 for left,right in zip(faces,faces[1:]))).as_dict()
                if new!=old:
                    species=native["duct_species"][path_id]
                    for cell,(before,after) in enumerate(zip(old["volumes"],new["volumes"])):
                        species[cell]=[mass*after/before for mass in species[cell]]
                    entry["mesh"]=new;changed_ducts=True
            if changed_ducts:design_inputs["intake_transfer_geometry"]={"classification":"UNKNOWN","rationale":"Geometría editada en Desktop; clasificá la fuente antes de usarla como evidencia."}
            exchange=native["geometry_identity"].get("gas_exchange_model")
            if exchange is not None:
                mix=self.mixed_outflow.value()
                if mix!=exchange.get("mixed_outflow_fraction"):
                    exchange["mixed_outflow_fraction"]=mix;design_inputs["mixed_outflow_fraction"]={"classification":"UNKNOWN","rationale":"Parámetro editado en Desktop; clasificá la fuente."}
            for row in range(self.reeds.rowCount()):
                petal=next((p for p in native.get("reed_petals",[]) if p["id"]==self.reeds.item(row,0).text()),None)
                if petal is None:continue
                fields=((1,"pressure_area_m2",1e-4),(2,"effective_width_m",1e-3),(3,"stiffness_n_m",1.0),(4,"lift_stop_m",1e-3),(5,"discharge_coefficient",1.0))
                changed=False
                for col,key,scale in fields:
                    try:value=self._decimal(self.reeds.item(row,col).text())*scale
                    except (ValueError,AttributeError) as exc:raise ValueError(f"Lámina {petal['id']}: parámetro debe ser numérico") from exc
                    if not math.isfinite(value) or value<=0:raise ValueError(f"Lámina {petal['id']}: parámetros deben ser positivos")
                    changed|=value!=petal[key];petal[key]=value
                if changed:design_inputs["reed_static_parameters"]={"classification":"UNKNOWN","rationale":"Parámetros editados en Desktop; clasificá la fuente."}
            doc["mechanical_loss_model"]=deepcopy(self.loss_model_draft)
            for i,term in enumerate(doc["mechanical_loss_model"]["terms"]):
                if term["mep_pa"] is None:continue
                try:value=float(self.losses.item(i,2).text())
                except (ValueError,AttributeError) as exc:raise ValueError(f"Pérdida mecánica {term['id']}: MEP debe ser numérica") from exc
                if not math.isfinite(value) or value<0:raise ValueError(f"Pérdida mecánica {term['id']}: MEP debe ser finita y no negativa")
                term["mep_pa"]=value
            conditions=doc["operating_conditions"]
            conditions["reference_rpm"]=self.controls["reference_rpm"].value()
            if self.controls["load"].isEnabled():
                conditions["load"]=self.controls["load"].value()
            combustion=native.get("fuel_coupled_combustion")
            if combustion:
                combustion["combustion_efficiency"]=self.comb["combustion_efficiency"].value();combustion["ignition_timing_deg"]=self.comb["ignition_timing_deg"].value()
                combustion["components"][0].update({"duration_deg":self.comb["duration_deg"].value(),"shape_a":self.comb["shape_a"].value(),"shape_m":self.comb["shape_m"].value()})
            crank=CrankcaseGeometry.from_dict(cc);model=SliderCrankChambers2T(crank,slider["cylinder_compression_ratio"])
            volumes=model.resolve(0.0,conditions["reference_rpm"])
            for name,volume in (("crankcase",volumes[0]),("cylinder",volumes[1])):
                old=native["initial_chambers"]["species"][name];total=math.fsum(old)
                target=native["initial_chambers"][name][0]*volume
                if total<=0:raise ValueError(f"Inventario inicial de {name} no positivo")
                native["initial_chambers"]["species"][name]=[mass*target/total for mass in old]
            doc["native_configuration_sha256"]=sha256(native)
            doc["provenance"]={**doc["provenance"],"desktop_initial_state_policy":"PRESERVE_PRIMITIVE_STATE_AND_SPECIES_FRACTIONS_ON_GEOMETRY_EDIT; SYNTHETIC_ASSUMPTION"}
            validate(doc);self.context.replace_engine(doc);self.validation.setText("Validación correcta sin pasos de solver.\nCambios aplicados como borrador sintético; provenance disponible en Evidencia.")
            for i,name in enumerate(self.component_names):self.component_tabs.setTabText(i,f"{name} · válido")
            self.component_state_changed.emit()
        except Exception as exc:
            self.validation.setText(f"Edición rechazada; no se guardó como válida. {type(exc).__name__}: {exc}")
            self.component_state_changed.emit()

    @staticmethod
    def _decimal(text):
        value=text.strip()
        if "," in value and "." in value:
            raise ValueError("Usá coma o punto decimal, no ambos")
        return float(value.replace(",","."))

    @staticmethod
    def _area_timing(port_set,port):
        """Find opening/closing from actual backend area transitions, including TDC wrap."""
        epsilon=1e-4;transitions=[]
        for event in sorted({float(value)%360.0 for value in port_set.event_angles(port)}):
            left=float(port_set.area_at(port,(event-epsilon)%360.0))
            right=float(port_set.area_at(port,(event+epsilon)%360.0))
            if left<=1e-9<right:transitions.append((event,True))
            elif left>1e-9>=right:transitions.append((event,False))
        opens=[angle for angle,is_open in transitions if is_open];closes=[angle for angle,is_open in transitions if not is_open]
        if not opens or not closes:return None,None,None
        # A single connected open interval is represented by the opening whose next close is nearest in crank order.
        opening=min(opens);later=[angle for angle in closes if angle>=opening]
        closing=min(later) if later else min(closes)
        duration=(closing-opening)%360.0
        return opening,closing,duration
