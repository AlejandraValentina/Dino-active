from __future__ import annotations
from .presentation import EngineeringNumberDelegate,PortRoleDelegate,format_number,state_label
from copy import deepcopy
import math
from PySide6.QtCore import Qt,QPointF,Signal
from PySide6.QtGui import QColor,QPainter,QPen,QFont
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QFormLayout,QGroupBox,QLabel,QTabWidget,
    QDoubleSpinBox,QPushButton,QComboBox,QTableWidget,QTableWidgetItem,QHeaderView,QMessageBox,QDialog,QDialogButtonBox,QSplitter,QScrollArea,QFrame)
from ..engine_configuration import validate,identity,sha256
from ..two_stroke_ports import TwoStrokePortSet,DuctBinding,PortDefinition
from ..crankcase import CrankcaseGeometry
from ..integrated_2t import SliderCrankChambers2T
from ..gas1d.mesh import Mesh
from .model_diagrams import PortGeometryView,PortTimingView,can_edit_opening,top_from_opening

_PORT_LABELS={"inlet-window":"Admisión","primary-window":"Transferencia primaria",
    "secondary-window":"Transferencia secundaria","boost-window":"Transferencia auxiliar",
    "main-exhaust":"Escape principal","aux-exhaust":"Escape auxiliar"}
_DUCT_LABELS={"intake":"Conducto de admisión","primary":"Transferencia primaria",
    "secondary":"Transferencia secundaria","boost":"Transferencia auxiliar","exhaust":"Escape"}
_LOSS_LABELS={"synthetic-piston-ring":"Pérdida de pistón y segmentos (sintética)",
    "synthetic-bearing-accessory":"Pérdidas de cojinetes y accesorios (sintéticas)"}

def _port_label(port_id,index=None):
    return _PORT_LABELS.get(str(port_id),f"Lumbrera {index+1}" if index is not None else "Lumbrera")


class CylinderSketch(QWidget):
    def __init__(self,parent=None):
        super().__init__(parent);self.bore=50.0;self.stroke=50.0;self.rod=100.0;self.setMinimumHeight(60);self.setMaximumHeight(66);self.setMinimumWidth(220)
    def set_geometry(self,bore,stroke,rod):self.bore=float(bore);self.stroke=float(stroke);self.rod=float(rod);self.update()
    def paintEvent(self,event):
        p=QPainter(self);p.setRenderHint(QPainter.RenderHint.Antialiasing);p.fillRect(self.rect(),QColor("#101a28"))
        scale=min(100/self.bore,(self.height()-35)/self.stroke);w=self.bore*scale;h=self.stroke*scale
        x=self.width()*.58-w/2;top=10;bottom=top+h
        p.setPen(QPen(QColor('#91a8bf'),2));p.drawLine(round(x),top,round(x),round(bottom));p.drawLine(round(x+w),top,round(x+w),round(bottom))
        p.setPen(QPen(QColor('#547088'),1,Qt.PenStyle.DashLine));p.drawLine(round(x),top,round(x+w),top)
        p.setPen(QPen(QColor('#7dd3fc'),3));p.drawLine(round(x),round(bottom),round(x+w),round(bottom))
        p.setPen(QColor('#cad8e7'));p.drawText(round(x+w)+8,top+10,'PMS');p.drawText(round(x+w)+8,round(bottom),'PMI')
        p.setPen(QColor("#e5edf6"));p.setFont(QFont("Segoe UI",9));p.drawText(8,16,f"Ø {format_number(self.bore)} mm");p.drawText(8,self.height()-5,f"Carrera {format_number(self.stroke)} mm · biela {format_number(self.rod)} mm")
        p.end()


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
        super().__init__();self.context=context;self.loading=False;self._last_edited_component=None;self._applying=False
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
        for col in (6,):self.ports.setColumnHidden(col,True)
        for col in range(2,10):self.ports.setItemDelegateForColumn(col,EngineeringNumberDelegate(self.ports))
        self.ports.setItemDelegateForColumn(1,PortRoleDelegate(self.ports))
        for col,width in enumerate((145,70,95,70,70,55,65,55,55,55)):self.ports.setColumnWidth(col,width)
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
        self.ducts.setItemDelegateForColumn(1,PortRoleDelegate(self.ducts))
        self.ducts.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.intake_duct_slot=QWidget();self.intake_duct_layout=QVBoxLayout(self.intake_duct_slot);self.intake_duct_layout.setContentsMargins(0,0,0,0);self.intake_duct_layout.addWidget(self.ducts)
        self.ducts.cellChanged.connect(self._duct_changed);intake_layout.addWidget(self.intake_duct_slot)
        self.reed_group=QGroupBox("Láminas · modelo cuasiestático activo");reed_layout=QVBoxLayout(self.reed_group)
        reed_layout.addWidget(QLabel("Masa, amortiguamiento y restitución no se editan: la configuración actual no usa el vínculo dinámico de láminas."))
        self.reeds=QTableWidget(0,6);self.reeds.setObjectName("effectiveStaticReedParameters")
        self.reeds.setHorizontalHeaderLabels(["Lámina","Área presión (cm²)","Ancho (mm)","Rigidez (N/m)","Tope (mm)","Cd"])
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
        self.revert_button=QPushButton("Descartar edición");self.revert_button.clicked.connect(self.discard_draft);buttons.addWidget(self.revert_button);buttons.addStretch(1)
        # Separate the existing editors without introducing project fields.
        title.hide()
        def move_field(widget,target):
            taken=form.takeRow(widget)
            label=taken.labelItem.widget() if taken.labelItem else None
            if label:target.addRow(label,widget)
            else:target.addRow(widget)
        crank_page=QWidget();crank_form=QFormLayout(crank_page)
        move_field(self.controls['volume_bdc_cm3'],crank_form)
        crank_note=QLabel('Se representa el volumen libre en PMI y su variación cinemática. La forma del cárter no está identificada.');crank_note.setWordWrap(True);crank_form.addRow(crank_note)
        self.crank_derived=QLabel();self.crank_derived.setWordWrap(True);crank_form.addRow(self.crank_derived)
        intake_form=QFormLayout();move_field(self.intake_control,intake_form);intake_layout.insertLayout(0,intake_form)
        advanced_page=QWidget();advanced_layout=QVBoxLayout(advanced_page)
        advanced_form_display=QFormLayout();advanced_layout.addLayout(advanced_form_display)
        move_field(self.provenance_label,advanced_form_display);move_field(self.provenance_button,advanced_form_display)
        form.removeWidget(self.advanced_operation_toggle);self.advanced_operation_toggle.hide()
        form.removeWidget(self.advanced_operation);advanced_layout.addWidget(self.advanced_operation);self.advanced_operation.show();advanced_layout.addStretch()
        # Reparent the geometry and port widgets from the old combined page.
        integrated_layout.removeWidget(self.area_plot)
        cylinder_page=QWidget();cylinder_layout=QVBoxLayout(cylinder_page);cylinder_layout.addWidget(self.geometry_group);cylinder_layout.addStretch()
        self.component_tabs.removeTab(0);self.component_tabs.insertTab(0,cylinder_page,'Cilindro y culata')
        self.port_views=QTabWidget()
        dimension_page=QWidget();dimension_layout=QVBoxLayout(dimension_page);dimension_layout.setContentsMargins(0,0,0,0);dimension_layout.addWidget(self.ports)
        self.port_views.addTab(dimension_page,'Dimensiones');self.port_views.setCornerWidget(self.port_advanced_toggle)
        self.port_geometry=PortGeometryView();self.port_views.addTab(self.port_geometry,'Cotas desde PMS')
        self.port_timeline=PortTimingView();self.port_views.addTab(self.port_timeline,'Distribución')
        areas_page=QWidget();areas_layout=QVBoxLayout(areas_page);areas_layout.addWidget(self.area_plot);areas_layout.addWidget(self.port_areas)
        areas_scroll=QScrollArea();areas_scroll.setWidgetResizable(True);areas_scroll.setFrameShape(QFrame.Shape.NoFrame);areas_scroll.setWidget(areas_page)
        self.port_views.addTab(areas_scroll,'Áreas efectivas')
        self.component_tabs.removeTab(1);self.component_tabs.insertTab(1,self.port_views,'Lumbreras y transferencias')
        self.component_tabs.addTab(crank_page,'Cárter')
        summary_page=QWidget();summary_layout=QVBoxLayout(summary_page)
        self.summary=QLabel();self.summary.setWordWrap(True);summary_layout.addWidget(self.summary)
        self.timing.show();summary_layout.addWidget(self.timing)
        self.component_tabs.addTab(summary_page,'Resumen')
        self.component_tabs.addTab(advanced_page,'Datos y operación avanzados')
        transfer_page=QWidget();transfer_layout=QVBoxLayout(transfer_page)
        transfer_note=QLabel('Conductos de transferencia · sección circular constante. Longitud y diámetro se aplican al modelo existente; se conserva la malla.');transfer_note.setWordWrap(True);transfer_layout.addWidget(transfer_note)
        self.transfer_duct_slot=QWidget();self.transfer_duct_layout=QVBoxLayout(self.transfer_duct_slot);self.transfer_duct_layout.setContentsMargins(0,0,0,0);transfer_layout.addWidget(self.transfer_duct_slot);transfer_layout.addStretch()
        self.component_tabs.addTab(transfer_page,'Conductos de transferencia')
        self.component_names=('Cilindro y culata','Lumbreras y transferencias','Pérdidas','Combustión','Admisión','Cárter','Resumen','Avanzado','Conductos de transferencia')
        self.geometry_group.setTitle('Cilindro y culata · compresión y volumen derivados')
        self.cylinder_diagram.setMinimumHeight(80);self.cylinder_diagram.setMaximumHeight(90)
        self.derived.setParent(cylinder_page);cylinder_layout.insertWidget(1,self.derived)
        self.ducts.setMaximumHeight(135);self.reeds.setMaximumHeight(170)
        self.ports.setMinimumHeight(140);self.ports.setMaximumHeight(210);self.ports.verticalHeader().setDefaultSectionSize(24)
        self.ports.horizontalHeaderItem(2).setText('Cota PMS (mm)');self.ports.setColumnWidth(2,110)
        # A long inactive section must not force every section to scroll along
        # with the Apply/Discard actions. Each component owns its scroll area.
        for index in range(self.component_tabs.count()):
            pane=self.component_tabs.widget(index);label=self.component_tabs.tabText(index)
            self.component_tabs.removeTab(index)
            scroll=QScrollArea();scroll.setWidgetResizable(True);scroll.setFrameShape(QFrame.Shape.NoFrame);scroll.setWidget(pane)
            self.component_tabs.insertTab(index,scroll,label)
        for control in self.controls.values():control.valueChanged.connect(self._preview_geometry)
        self.intake_control.currentIndexChanged.connect(self._preview_geometry)
        self._angle_error=None
        self.component_tabs.currentChanged.connect(self._duct_section_changed)
        self.context.changed.connect(self.refresh);self.refresh()

    def _duct_section_changed(self,index):
        if index not in (4,8):return
        target=self.intake_duct_layout if index==4 else self.transfer_duct_layout
        target.addWidget(self.ducts)
        role='intake' if index==4 else 'transfer'
        for row in range(self.ducts.rowCount()):self.ducts.setRowHidden(row,self.ducts.item(row,1).text()!=role)
        self.ducts.setMaximumHeight(135 if index==4 else 240)

    def _duct_changed(self,row,_column):
        item=self.ducts.item(row,1)
        self._mark_component(8 if item and item.text()=='transfer' else 4,'modificado')

    def discard_draft(self):
        self._last_edited_component=None
        self.refresh(force=True)

    def refresh(self,*_,force=False):
        if self._last_edited_component is not None and not force and not self._applying:return
        self.loading=True
        self._angle_error=None
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
                for col,value in enumerate((_DUCT_LABELS.get(entry["id"],"Conducto configurado"),entry["role"],shown_length,shown_diameter)):
                    item=QTableWidgetItem(str(value));item.setData(Qt.ItemDataRole.UserRole,entry["id"])
                    if col==0:item.setToolTip(f"ID original: {entry['id']}")
                    if col<2:item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    if col>=2 and not constant_area:
                        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                        item.setToolTip("La malla representa una sección variable; esta pantalla sólo edita conductos de sección circular constante.")
                    self.ducts.setItem(row,col,item)
            self.ducts.blockSignals(False)
            self._duct_section_changed(self.component_tabs.currentIndex())
            petals=n.get("reed_petals",[]);self.reeds.blockSignals(True);self.reeds.setRowCount(len(petals))
            for row,petal in enumerate(petals):
                values=(f"Lámina {row+1}",petal["pressure_area_m2"]*1e4,petal["effective_width_m"]*1000,petal["stiffness_n_m"],petal["lift_stop_m"]*1000,petal["discharge_coefficient"])
                for col,value in enumerate(values):
                    item=QTableWidgetItem(str(value));item.setData(Qt.ItemDataRole.UserRole,petal["id"])
                    if col==0:item.setToolTip(f"ID original: {petal['id']}")
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
                names={'primary':'Transferencia primaria','secondary':'Transferencia secundaria','boost':'Transferencia auxiliar','main_exhaust':'Escape principal','main':'Escape principal','auxiliary':'Escape auxiliar','piston_port':'Admisión'}
                label=names.get(p.get('feature'),p.get('name') or p['id'])
                vals=[label,p['role'],p["top_mm"],p["height_mm"],p["width_mm"],p["discharge_coefficient"],p["roof_travel_mm"],*timing_by_id.get(p["id"],(None,None,None))]
                reed_intake=(p["role"]=="intake" and n["geometry_identity"].get("gas_exchange_model",{}).get("intake_control")=="reed")
                if reed_intake:vals[7:]=[None,None,None]
                for j,value in enumerate(vals):
                    display="—" if value is None else (f"{value:.12g}" if isinstance(value,(int,float)) else str(value))
                    item=QTableWidgetItem(display);item.setData(Qt.ItemDataRole.UserRole,p["id"])
                    item.setToolTip(f"ID: {p['id']}\nValor completo: {display}")
                    if j<2 or j>=7 or p["family"]=="effective_profile" or value is None:item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    if j>=7 and value is None:item.setToolTip('No hay un intervalo único identificado; consultar Distribución. La admisión por láminas depende de Δp.')
                    if j==7 and value is not None and can_edit_opening(port_set.ports[i]):
                        item.setFlags(item.flags()|Qt.ItemFlag.ItemIsEditable)
                        item.setToolTip('Abrir en grados modifica sólo la cota superior. Cierre y duración son derivados; techo fijo, altura y ancho conservados.')
                    if reed_intake:
                        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                        item.setToolTip("Admisión por láminas: conexión sin distribución de pistón. El área efectiva depende de Δp y de las láminas, no de esta ventana histórica.")
                    self.ports.setItem(i,j,item)
            self.ports.blockSignals(False)
            bore=cc["bore_mm"];stroke=cc["stroke_mm"];swept=math.pi*(bore/2)**2*stroke/1000
            profile_rows=[]
            for profile in port_set.compile_profiles():
                if profile.event_angles_deg:
                    profile_rows.append(f"{_port_label(profile.port_id)}: " + ", ".join(f"{format_number(angle)}°" for angle in profile.event_angles_deg))
            ratio=stroke/bore;rod_ratio=cc["rod_length_mm"]/stroke;mean_speed=2*stroke/1000*cond["reference_rpm"]/60
            compression=float(slider["cylinder_compression_ratio"])
            clearance=swept/(compression-1.0)
            primary=1.0+swept/float(cc["volume_bdc_cm3"])
            self.derived.setText(f"Cilindrada {format_number(swept)} cm³ · cámara derivada {format_number(clearance)} cm³ · compresión primaria {format_number(primary)}:1 · S/D {format_number(ratio)} · biela/carrera {format_number(rod_ratio)} · Vm pistón {format_number(mean_speed)} m/s")
            self.derived.setToolTip("Distribución calculada por transiciones de área efectiva del backend; no son controles inversos.")
            timing_rows=[];area_series=[];area_rows=[]
            for port in port_set.ports:
                if port.role=="intake" and n["geometry_identity"].get("gas_exchange_model",{}).get("intake_control")=="reed":
                    timing_rows.append(("Admisión por láminas · Δp",None,None,None))
                    continue
                opening,closing,duration=self._area_timing(port_set,port)
                timing_rows.append((_port_label(port.id,len(timing_rows)),opening,closing,duration))
                area_series.append({"name":_port_label(port.id,len(area_series)),"points":[(angle,port_set.area_at(port,angle)) for angle in (*range(0,360,2),360)]})
                events=port_set.event_angles(port)
                for angle in events:
                    area_rows.append((_port_label(port.id,len(area_rows)),angle,port_set.area_at(port,angle),port.id))
            self.timing.setRowCount(len(timing_rows))
            for i,row in enumerate(timing_rows):
                values=(row[0],*("—" if value is None else format_number(value) for value in row[1:]))
                for j,value in enumerate(values):
                    item=QTableWidgetItem(str(value));item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    if j==0:item.setData(Qt.ItemDataRole.UserRole,port_set.ports[i].id);item.setToolTip(f"ID original: {port_set.ports[i].id}")
                    self.timing.setItem(i,j,item)
            self.area_plot.set_series(area_series)
            reed=self.intake_control.currentData()=='reed'
            self.port_geometry.set_geometry(port_set,reed);self.port_timeline.set_events(port_set,reed)
            self._set_summary(port_set,values=None)
            self.port_areas.setRowCount(len(area_rows))
            for i,(port_id,angle,area,original_id) in enumerate(area_rows):
                for j,value in enumerate((port_id,format_number(angle),format_number(area))):
                    item=QTableWidgetItem(str(value));item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    if j==0:item.setData(Qt.ItemDataRole.UserRole,original_id);item.setToolTip(f"ID original: {original_id}")
                    self.port_areas.setItem(i,j,item)
            terms=doc["mechanical_loss_model"]["terms"];self.loss_model_draft=deepcopy(doc["mechanical_loss_model"])
            self.controls["load"].setEnabled(any(term["operating_map"] is not None for term in terms))
            self.losses.blockSignals(True);self.losses.setRowCount(len(terms))
            for i,term in enumerate(terms):
                model="Fixed MEP" if term["mep_pa"] is not None else f"Mapa {len(term['operating_map']['rpm'])}×{len(term['operating_map']['load'])} (doble clic)"
                for j,value in enumerate((_LOSS_LABELS.get(term["id"],"Término de pérdida"),state_label(term["source"]),term["mep_pa"] if term["mep_pa"] is not None else model,state_label(term["provenance"]))):
                    item=QTableWidgetItem(str(value))
                    if j==0:item.setData(Qt.ItemDataRole.UserRole,term["id"]);item.setToolTip(f"ID original: {term['id']}")
                    if j!=2 or term["mep_pa"] is None:item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    self.losses.setItem(i,j,item)
            self.losses.blockSignals(False)
            self.validation.setText('Configuración cargada · sin validación experimental');self.validation.setToolTip(doc['validation_state'])
            self.apply_button.setEnabled(True)
            for i,name in enumerate(self.component_names):self.component_tabs.setTabText(i,f"{name} · válido")
        except Exception as exc:
            self.validation.setText(f"No se pudo presentar la configuración: {exc}");self.apply_button.setEnabled(False)
        finally:
            self.loading=False
            self._last_edited_component=None
            self.component_state_changed.emit()

    def _port_changed(self,row,column):
        if not self.loading:
            if column==7:
                try:
                    native=deepcopy(self.context.engine()['native_configuration']);self._edited_ports(native)
                    raw=native['port_binding']['port_set']
                    port=PortDefinition.from_dict(raw['ports'][row])
                    top=top_from_opening(port,self.controls['stroke_mm'].value(),self.controls['rod_length_mm'].value(),self._decimal(self.ports.item(row,7).text()))
                    self.ports.blockSignals(True);self.ports.item(row,2).setText(f'{top:.12g}');self.ports.blockSignals(False);self._angle_error=None
                except Exception as exc:
                    self._angle_error=str(exc);self.validation.setText('Apertura rechazada: '+str(exc)+' · diagramas: última geometría válida.');self._mark_component(1,'rechazada');return
            self._mark_component(1,"modificado")
            self.validation.setText("Edición pendiente. Aplicá para ejecutar la validación completa del backend.")
            self._preview_geometry()

    def _set_summary(self,port_set,values=None):
        v={key:widget.value() for key,widget in self.controls.items()}
        bore=v['bore_mm'];stroke=v['stroke_mm'];rod=v['rod_length_mm']
        if rod<=stroke/2:raise ValueError('Biela incompatible: debe superar la mitad de la carrera.')
        swept=math.pi*bore*bore/4*stroke/1000;clearance=swept/(v['cylinder_compression_ratio']-1)
        primary=1+swept/v['volume_bdc_cm3']
        self.cylinder_diagram.set_geometry(bore,stroke,rod)
        description=f'Ø {format_number(bore)} × {format_number(stroke)} mm · biela {format_number(rod)} mm · {format_number(swept)} cm³\nCompresión {format_number(v["cylinder_compression_ratio"])}:1 · cámara derivada {format_number(clearance)} cm³\nCárter PMI {format_number(v["volume_bdc_cm3"])} cm³ · compresión primaria {format_number(primary)}:1'
        self.derived.setText(description)
        self.crank_derived.setText(f'Cilindrada {format_number(swept)} cm³ · V(PMS) {format_number(v["volume_bdc_cm3"]+swept)} cm³ · compresión primaria {format_number(primary)}:1')
        state='Configuración cargada' if self.loading else 'BORRADOR SIN APLICAR'
        self.summary.setText(self.context.engine().get('display_name','Motor')+'\n'+description+'\nAdmisión: '+self.intake_control.currentText()+'\n'+state+' · sin validación experimental. Fuentes desconocidas conservadas en Avanzado.')

    def _preview_geometry(self,*_):
        if self.loading:return
        try:
            if self._angle_error:raise ValueError(self._angle_error)
            native=deepcopy(self.context.engine()['native_configuration']);self._edited_ports(native)
            port_set=TwoStrokePortSet.from_dict(native['port_binding']['port_set'])
            reed=self.intake_control.currentData()=='reed'
            self._set_summary(port_set)
            self.port_geometry.set_geometry(port_set,reed);self.port_timeline.set_events(port_set,reed)
            self.area_plot.set_series([{'name':p.name,'points':[(a,port_set.area_at(p,a)) for a in (*range(0,360,2),360)]} for p in port_set.ports if not (reed and p.role=='intake')])
            self.ports.blockSignals(True)
            for i,port in enumerate(port_set.ports):
                events=(None,None,None) if reed and port.role=='intake' else self._area_timing(port_set,port)
                item=self.ports.item(i,7);flags=item.flags() & ~Qt.ItemFlag.ItemIsEditable
                if events[0] is not None and can_edit_opening(port):flags|=Qt.ItemFlag.ItemIsEditable
                item.setFlags(flags)
                for j,value in enumerate(events,7):self.ports.item(i,j).setText('—' if value is None else f'{value:.8g}')
                for j,value in enumerate((_port_label(port.id,i),*events)):
                    cell=QTableWidgetItem('—' if value is None else format_number(value) if isinstance(value,(int,float)) else str(value));cell.setFlags(cell.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    if j==0:cell.setData(Qt.ItemDataRole.UserRole,port.id);cell.setToolTip(f"ID original: {port.id}")
                    self.timing.setItem(i,j,cell)
            self.ports.blockSignals(False)
            areas=[(_port_label(port.id,index),angle,port_set.area_at(port,angle),port.id) for index,port in enumerate(port_set.ports) if not (reed and port.role=='intake') for angle in port_set.event_angles(port)]
            self.port_areas.setRowCount(len(areas))
            for i,(port_id,angle,area,original_id) in enumerate(areas):
                for j,value in enumerate((port_id,format_number(angle),format_number(area))):
                    cell=QTableWidgetItem(value);cell.setFlags(cell.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    if j==0:cell.setData(Qt.ItemDataRole.UserRole,original_id);cell.setToolTip(f"ID original: {original_id}")
                    self.port_areas.setItem(i,j,cell)
        except Exception as exc:
            self.ports.blockSignals(False);self.validation.setText('Borrador inválido: '+str(exc)+' · diagramas: última geometría válida.');self._mark_component(1,'rechazada')

    def _mark_component(self,index,status):
        if self.loading:return
        self._last_edited_component=index
        self.component_tabs.setTabText(index,f"{self.component_names[index]} · {status}")
        self.component_state_changed.emit()

    def _toggle_advanced_operation(self):
        visible=not self.advanced_operation.isVisible()
        self.advanced_operation.setVisible(visible);self.advanced_operation_toggle.setText("Avanzado ▾" if visible else "Avanzado ▸")

    def _toggle_advanced_ports(self):
        visible=self.ports.isColumnHidden(6)
        for column in (6,):self.ports.setColumnHidden(column,not visible)
        self.port_advanced_toggle.setText("Más dimensiones ▾" if visible else "Más dimensiones ▸")

    def _refresh_provenance(self,doc):
        inputs=doc.get("provenance",{}).get("design_inputs",{})
        labels={"MEASURED":"medido","ESTIMATED":"estimado","SYNTHETIC_ASSUMPTION":"supuesto","UNKNOWN":"sin clasificar","DOCUMENTED":"documentado","DERIVED_FROM_DOCUMENTED":"derivado de documentación"}
        names=("bore_mm","stroke_mm","rod_length_mm","volume_bdc_cm3","cylinder_compression_ratio","reference_rpm","port_dimensions","intake_control","intake_transfer_geometry","reed_static_parameters","mixed_outflow_fraction","exhaust_sections","fuel_model")
        parts=[f"{name}: {labels.get(inputs.get(name,{}).get('classification','UNKNOWN'),'sin clasificar')}" for name in names]
        self.provenance_label.setText(" · ".join(parts))

    def edit_provenance(self):
        if not self.context.prepare_operation('Clasificar fuentes de datos'):return
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
                    # Keep the source precision when a displayed value was not
                    # edited; formatting a table must not rewrite geometry.
                    if p.get(key) is not None and value==float(f'{p[key]:.12g}'):continue
                    p[key]=value
        stroke=self.controls["stroke_mm"].value();rod=self.controls["rod_length_mm"].value()
        profile=TwoStrokePortSet(stroke,rod,tuple(DuctBinding.from_dict(x) for x in raw["ducts"]),tuple(PortDefinition.from_dict(x) for x in ports)).to_dict()
        native["port_binding"]["port_set"]=profile
        native["geometry_identity"]["ports"]=deepcopy(profile)

    def apply(self):
        try:
            if self._angle_error:raise ValueError(self._angle_error)
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
                original_id=self.reeds.item(row,0).data(Qt.ItemDataRole.UserRole)
                petal=next((p for p in native.get("reed_petals",[]) if p["id"]==original_id),None)
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
            validate(doc)
            self._applying=True
            try:self.context.replace_engine(doc)
            finally:self._applying=False
            self.validation.setText("Validación correcta sin pasos de solver.\nCambios aplicados como borrador sintético; provenance disponible en Evidencia.")
            for i,name in enumerate(self.component_names):self.component_tabs.setTabText(i,f"{name} · válido")
            self._last_edited_component=None
            self.component_state_changed.emit()
        except Exception as exc:
            self.validation.setText(f"Edición rechazada; no se guardó como válida. {type(exc).__name__}: {exc}")
            index=self._last_edited_component
            if index is None:index=self.component_tabs.currentIndex()
            self.component_tabs.setTabText(index,f"{self.component_names[index]} · rechazada")
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
        if len(opens)!=1 or len(closes)!=1:return None,None,None
        # Only one connected periodic interval has a single opening/closing pair.
        opening=min(opens);later=[angle for angle in closes if angle>=opening]
        closing=min(later) if later else min(closes)
        duration=(closing-opening)%360.0
        return opening,closing,duration
