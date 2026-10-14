from __future__ import annotations
from copy import deepcopy
import math
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QFormLayout,QGroupBox,QLabel,QTabWidget,
    QDoubleSpinBox,QPushButton,QComboBox,QTableWidget,QTableWidgetItem,QHeaderView,QMessageBox,QDialog,QDialogButtonBox)
from ..engine_configuration import validate,identity,sha256
from ..two_stroke_ports import TwoStrokePortSet,DuctBinding,PortDefinition
from ..crankcase import CrankcaseGeometry
from ..integrated_2t import SliderCrankChambers2T


class EnginePage(QWidget):
    def __init__(self,context):
        super().__init__();self.context=context;self.loading=False
        root=QVBoxLayout(self);root.setContentsMargins(24,20,24,20);root.setSpacing(14)
        title=QLabel("Configuración del motor");title.setObjectName("title");root.addWidget(title)
        intro=QLabel("Editor del modelo integrado 2T · las unidades y la procedencia se conservan en el proyecto.");intro.setWordWrap(True);root.addWidget(intro)
        self.component_tabs=QTabWidget();root.addWidget(self.component_tabs,1)
        self.geometry_group=QGroupBox("Geometría y operación");form=QFormLayout(self.geometry_group)
        self.controls={}
        definitions=[("bore_mm","Diámetro cilindro","mm",1,250),("stroke_mm","Carrera","mm",1,250),
          ("rod_length_mm","Longitud biela","mm",1,500),("volume_bdc_cm3","Cárter en PMI","cm³",0.1,5000),
          ("cylinder_compression_ratio","Compresión geométrica",":1",1.01,40),("reference_rpm","RPM de referencia","rpm",100,30000),
          ("load","Carga del mapa MEP","relativa",0,10),
          ("afr","AFR declarada · metadata","kg/kg",0.01,1000)]
        for key,label,unit,low,high in definitions:
            spin=QDoubleSpinBox();spin.setObjectName("engine_"+key);spin.setRange(low,high);spin.setDecimals(5);spin.setSingleStep(0.1);spin.setMaximumWidth(170)
            self.controls[key]=spin;form.addRow(f"{label} ({unit})",spin);spin.valueChanged.connect(lambda _v:self._mark_component(0,"modificado"))
        self.controls["load"].setToolTip(
            "Sólo selecciona pérdidas si el modelo mecánico declara un mapa dependiente de carga; "
            "no controla mariposa, admisión ni la carga del flujo de gas.")
        self.controls["afr"].setEnabled(False)
        self.controls["afr"].setToolTip(
            "El AFR de operación se conserva como metadata. La entrega de aire/combustible "
            "la determina el estado de especies del modelo; este campo no modifica el solver.")
        afr_note=QLabel(
            "El AFR editable aún no está acoplado a una ley de alimentación; "
            "no usarlo como consigna simulada.");afr_note.setWordWrap(True);form.addRow(afr_note)
        self.port_group=QGroupBox("Lumbreras y distribución");v=QVBoxLayout(self.port_group)
        v.addWidget(QLabel("Dimensiones geométricas editables; los perfiles efectivos derivados se regeneran con el modelo existente."))
        self.ports=QTableWidget(0,7);self.ports.setHorizontalHeaderLabels(["Lumbrera","Rol","Borde (mm)","Altura (mm)","Ancho (mm)","Cd","Recorrido techo (mm)"])
        self.ports.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        for col,width in enumerate((88,62,68,68,68,50,75)):self.ports.setColumnWidth(col,width)
        self.ports.setAlternatingRowColors(True);self.ports.setMinimumHeight(220);self.ports.cellChanged.connect(self._port_changed);v.addWidget(self.ports)
        self.derived=QLabel();self.derived.setWordWrap(True);v.addWidget(self.derived)
        self.port_areas=QTableWidget(0,3);self.port_areas.setHorizontalHeaderLabels(["Lumbrera","Evento existente (°)","Área efectiva (mm²)"])
        self.port_areas.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch);self.port_areas.setMaximumHeight(180);v.addWidget(self.port_areas)
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
            spin=QDoubleSpinBox();spin.setRange(lo,hi);spin.setDecimals(5);self.comb[key]=spin;f.addRow(f"{label} ({unit})",spin);spin.valueChanged.connect(lambda _v:self._mark_component(3,"modificado"))
        self.combustion_notice=QLabel();self.combustion_notice.setWordWrap(True);f.addRow(self.combustion_notice)
        self.fuel=QLabel();self.fuel.setWordWrap(True);self.fuel.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        f.addRow("Fuel snapshot",self.fuel)
        self.component_names=("Cilindro y operación","Lumbreras y distribución","Pérdidas","Combustión y combustible")
        for name,widget in zip(self.component_names,(self.geometry_group,self.port_group,self.loss_group,self.combust_group)):
            pane=QWidget();layout=QVBoxLayout(pane);layout.addWidget(widget);layout.addStretch(1);self.component_tabs.addTab(pane,name)
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
            for key,value in values.items():self.controls[key].setValue(float(value))
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
            self.fuel.setText(f"{snapshot.get('schema','Sin snapshot')} · {snapshot.get('sha256','sin hash')} · {snapshot.get('provenance','provenance no declarada')}\nLos datos de combustible son de solo lectura; importá un snapshot validado para cambiarlo.")
            ports=n["port_binding"]["port_set"]["ports"];self.ports.blockSignals(True);self.ports.setRowCount(len(ports))
            for i,p in enumerate(ports):
                vals=[p["id"],p["role"],p["top_mm"],p["height_mm"],p["width_mm"],p["discharge_coefficient"],p["roof_travel_mm"]]
                for j,value in enumerate(vals):
                    item=QTableWidgetItem("—" if value is None else str(value));item.setData(Qt.ItemDataRole.UserRole,p["id"])
                    if j<2 or p["family"]=="effective_profile" or value is None:item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    self.ports.setItem(i,j,item)
            self.ports.blockSignals(False)
            bore=cc["bore_mm"];stroke=cc["stroke_mm"];swept=math.pi*(bore/2)**2*stroke/1000
            port_set=TwoStrokePortSet.from_dict(n["port_binding"]["port_set"])
            profile_rows=[]
            for profile in port_set.compile_profiles():
                if profile.event_angles_deg:
                    profile_rows.append(f"{profile.port_id}: " + ", ".join(f"{angle:g}°" for angle in profile.event_angles_deg))
            self.derived.setText(f"Cilindrada geométrica derivada: {swept:.2f} cm³ · eventos angulares del perfil existente: " + ("; ".join(profile_rows) if profile_rows else "no declarados"))
            area_rows=[]
            for port in port_set.ports:
                events=port_set.event_angles(port)
                for angle in events:
                    area_rows.append((port.id,angle,port_set.area_at(port,angle)))
            self.port_areas.setRowCount(len(area_rows))
            for i,(port_id,angle,area) in enumerate(area_rows):
                for j,value in enumerate((port_id,f"{angle:g}",f"{area:.4f}")):
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
            self.validation.setText(f"Config hash: {identity(doc)}\n{doc['validation_state']} · Fixture sintético; validación física experimental no realizada.")
            self.apply_button.setEnabled(True)
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
            cc.update({key:self.controls[key].value() for key in ("bore_mm","stroke_mm","rod_length_mm","volume_bdc_cm3")})
            slider["cylinder_compression_ratio"]=self.controls["cylinder_compression_ratio"].value()
            self._edited_ports(native)
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
            validate(doc);self.context.replace_engine(doc);self.validation.setText(f"Validación correcta sin pasos de solver.\nConfig hash: {identity(doc)}\nCambios aplicados como borrador sintético.")
            for i,name in enumerate(self.component_names):self.component_tabs.setTabText(i,f"{name} · válido")
        except Exception as exc:
            self.validation.setText(f"Edición rechazada; no se guardó como válida. {type(exc).__name__}: {exc}")

    @staticmethod
    def _decimal(text):
        value=text.strip()
        if "," in value and "." in value:
            raise ValueError("Usá coma o punto decimal, no ambos")
        return float(value.replace(",","."))
