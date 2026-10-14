from __future__ import annotations

from copy import deepcopy
import math

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QLabel,QTableWidget,QTableWidgetItem,
    QHeaderView,QPushButton,QMessageBox,QComboBox,QGroupBox,QInputDialog,QAbstractItemView)

from ..engine_configuration import identity,validate
from ..engine_variants import escape_sections,replace_escape_sections,compare_configurations
from ..exhaust_mesh_v1 import refine_exhaust_configuration


def _number(text: str, label: str) -> float:
    value=text.strip().replace(" ","")
    if "," in value and "." in value:
        raise ValueError(f"{label}: usá coma o punto decimal, no ambos")
    if value.count(",")>1 or value.count(".")>1:
        raise ValueError(f"{label}: número decimal ambiguo")
    try:result=float(value.replace(",","."))
    except ValueError as exc:raise ValueError(f"{label}: ingresá un número válido") from exc
    if not math.isfinite(result):raise ValueError(f"{label}: el número debe ser finito")
    return result


class ExhaustProfile(QWidget):
    """Dimensionally scaled (equal mm/px on both axes) conical profile."""
    def __init__(self,parent=None):
        super().__init__(parent);self.sections=[];self.overlay=[];self.refinements=[];self.changed_sections=set();self.setMinimumHeight(220)

    def set_sections(self,sections,refinements=None,overlay=None,changed_sections=None):
        self.sections=deepcopy(sections);self.overlay=deepcopy(overlay or [])
        self.refinements=list(refinements or [1]*len(sections));self.changed_sections=set(changed_sections or ());self.update()

    def _draw_profile(self,painter,sections,rect,color,width=2,style=Qt.PenStyle.SolidLine):
        if not sections:return
        total=sum(s["length_mm"] for s in sections);maxd=max(max(s["inlet_diameter_mm"],s["outlet_diameter_mm"]) for s in sections)
        scale=min(rect.width()/max(total,1e-9),rect.height()*.74/max(maxd,1e-9))
        used=total*scale;x=rect.left()+(rect.width()-used)/2;center=rect.center().y()
        upper=[];lower=[];cursor=0
        painter.setPen(QPen(QColor(color),width,style))
        for i,s in enumerate(sections):
            x0=x+cursor*scale;x1=x+(cursor+s["length_mm"])*scale
            upper.extend((QPointF(x0,center-s["inlet_diameter_mm"]*scale/2),QPointF(x1,center-s["outlet_diameter_mm"]*scale/2)))
            lower.extend((QPointF(x0,center+s["inlet_diameter_mm"]*scale/2),QPointF(x1,center+s["outlet_diameter_mm"]*scale/2)))
            if sections is self.sections:
                painter.setPen(QPen(QColor("#50657c"),1,Qt.PenStyle.DashLine));painter.drawLine(round(x1),rect.top(),round(x1),rect.bottom())
                if i<len(self.refinements):
                    n=self.refinements[i];painter.setPen(QPen(QColor("#98aabd"),1,Qt.PenStyle.DotLine))
                    for k in range(1,n):
                        xx=round(x0+(x1-x0)*k/n);d=s["inlet_diameter_mm"]+(s["outlet_diameter_mm"]-s["inlet_diameter_mm"])*k/n
                        painter.drawLine(xx,round(center-d*scale/2),xx,round(center+d*scale/2))
                if i in self.changed_sections:
                    painter.fillRect(round(x0),rect.top(),max(2,round(x1-x0)),rect.height(),QColor(245,158,11,24))
                painter.setPen(QColor("#cad8e7"));painter.drawText(round((x0+x1)/2)-35,rect.bottom()+17,s["name"][:9])
            cursor+=s["length_mm"]
        painter.setPen(QPen(QColor(color),width,style));painter.drawPolyline(upper);painter.drawPolyline(list(reversed(lower)))

    def paintEvent(self,event):
        painter=QPainter(self);painter.setRenderHint(QPainter.RenderHint.Antialiasing);painter.fillRect(self.rect(),QColor("#101a28"))
        rect=self.rect().adjusted(42,14,-18,-54);painter.setPen(QPen(QColor("#34475c"),1));painter.drawRect(rect)
        if not self.sections:painter.end();return
        self._draw_profile(painter,self.sections,rect,"#43c5f5",3)
        if self.overlay:self._draw_profile(painter,self.overlay,rect,"#f59e0b",2,Qt.PenStyle.DashLine)
        total=sum(s["length_mm"] for s in self.sections)
        painter.setPen(QColor("#cad8e7"));painter.drawText(rect.left(),self.height()-8,f"Largo total: {total:.1f} mm · escala axial/radial idéntica")
        painter.end()


class ExhaustPage(QWidget):
    def __init__(self,context):
        super().__init__();self.context=context;self.loading=False
        root=QVBoxLayout(self);root.setContentsMargins(20,16,20,16);root.setSpacing(9)
        title=QLabel("Diseñador de escape");title.setObjectName("title");root.addWidget(title)
        intro=QLabel("Perfil axisimétrico de tramos cónicos lineales. El solver conserva el número y tipo de tramos admitidos; la continuidad se define en estaciones compartidas.")
        intro.setWordWrap(True);root.addWidget(intro)
        self.profile=ExhaustProfile();root.addWidget(self.profile)
        self.overlay_selector=QComboBox();self.overlay_selector.addItem("Sin superposición",None)
        for name in sorted(context.project["variants"]):self.overlay_selector.addItem(f"Superponer: {name}",name)
        self.overlay_selector.currentIndexChanged.connect(self.refresh_overlay)
        overlay_row=QHBoxLayout();overlay_row.addWidget(QLabel("Comparación visual"));overlay_row.addWidget(self.overlay_selector);overlay_row.addStretch();root.addLayout(overlay_row)

        self.stations=QTableWidget(0,3);self.stations.setObjectName("exhaustStations")
        self.stations.setHorizontalHeaderLabels(["Estación","Posición (mm)","Diámetro compartido (mm)"])
        self.stations.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.stations.setMaximumHeight(185);self.stations.cellChanged.connect(self._cell_changed)
        station_group=QGroupBox("Estaciones · cada diámetro se edita una sola vez")
        station_layout=QVBoxLayout(station_group);station_layout.addWidget(self.stations);root.addWidget(station_group)

        self.table=QTableWidget(0,4);self.table.setObjectName("exhaustSegments");self.segments=self.table
        self.table.setHorizontalHeaderLabels(["Tramo","Tipo admitido","Longitud (mm)","Provenance"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setMaximumHeight(220);self.table.cellChanged.connect(self._cell_changed)
        segment_group=QGroupBox("Tramos · la cantidad no se puede cambiar")
        segment_layout=QVBoxLayout(segment_group);segment_layout.addWidget(self.table);root.addWidget(segment_group)

        self.mesh_group=QGroupBox("Opciones avanzadas · malla numérica");self.mesh_group.setCheckable(True);self.mesh_group.setChecked(False)
        mesh_layout=QVBoxLayout(self.mesh_group)
        self.mesh_notice=QLabel("La independencia espacial NO está demostrada. La resolución cambia la discretización, no valida la geometría ni el desempeño.")
        self.mesh_notice.setWordWrap(True);self.mesh_notice.setObjectName("notice");mesh_layout.addWidget(self.mesh_notice)
        self.mesh_table=QTableWidget(0,2);self.mesh_table.setHorizontalHeaderLabels(["Tramo","Celdas por tramo (1/2/4)"])
        self.mesh_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch);self.mesh_table.setMaximumHeight(180)
        mesh_layout.addWidget(self.mesh_table);root.addWidget(self.mesh_group)

        self.diff=QLabel("Motor base seleccionado. Guardá la geometría como una variante para conservar el base.");self.diff.setWordWrap(True);root.addWidget(self.diff)
        actions=QHBoxLayout();root.addLayout(actions)
        self.save_current_button=QPushButton("Guardar en variante actual");self.save_current_button.clicked.connect(self.save_current);actions.addWidget(self.save_current_button)
        self.apply_button=QPushButton("Guardar como nueva variante…");self.apply_button.setObjectName("primaryAction");self.apply_button.clicked.connect(self.save_as_new);actions.addWidget(self.apply_button)
        self.context.changed.connect(self.refresh);self.context.variant_changed.connect(self.refresh);self.refresh()

    def _counts(self,engine):
        meta=engine["native_configuration"]["geometry_identity"].get("exhaust_mesh_discretization")
        return list(meta["cells_per_section"]) if meta else [1]*len(escape_sections(engine))

    def _clear_widgets(self):
        for row in range(self.mesh_table.rowCount()):
            widget=self.mesh_table.cellWidget(row,1)
            if widget:self.mesh_table.removeCellWidget(row,1);widget.deleteLater()

    def refresh(self):
        try:
            engine=self.context.engine();sections=escape_sections(engine);counts=self._counts(engine)
            self.loading=True;self._clear_widgets();self.stations.blockSignals(True);self.table.blockSignals(True);self.mesh_table.blockSignals(True)
            self.stations.setRowCount(len(sections)+1);position=0.0
            diameters=[sections[0]["inlet_diameter_mm"]]+[s["outlet_diameter_mm"] for s in sections]
            for i,diameter in enumerate(diameters):
                label="Entrada" if i==0 else ("Salida" if i==len(sections) else f"Unión {i}")
                self.stations.setItem(i,0,QTableWidgetItem(label));pos=QTableWidgetItem(f"{position:.2f}");pos.setFlags(pos.flags() & ~Qt.ItemFlag.ItemIsEditable);self.stations.setItem(i,1,pos)
                self.stations.setItem(i,2,QTableWidgetItem(f"{diameter:.3f}"))
                if i<len(sections):position+=sections[i]["length_mm"]
            self.table.setRowCount(len(sections));self.mesh_table.setRowCount(len(sections))
            for i,s in enumerate(sections):
                for col,value in enumerate((s["name"],s["kind"],f"{s['length_mm']:.3f}",s["provenance"])):
                    item=QTableWidgetItem(str(value))
                    if col in (0,1,3):item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    self.table.setItem(i,col,item)
                item=QTableWidgetItem(s["name"]);item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable);self.mesh_table.setItem(i,0,item)
                combo=QComboBox();combo.setObjectName(f"meshResolution_{i}");combo.addItems(["1","2","4"]);combo.setCurrentText(str(counts[i]));combo.currentIndexChanged.connect(self._cell_changed)
                self.mesh_table.setCellWidget(i,1,combo)
            self.stations.blockSignals(False);self.table.blockSignals(False);self.mesh_table.blockSignals(False)
            self.profile.set_sections(self._rows(),self._resolutions(),self._overlay_sections(),self._changed_sections())
            self.diff.setText(self._mesh_summary(engine));self.save_current_button.setEnabled(self.context.selected_variant is not None)
            self._update_station_positions()
        except Exception as exc:self.diff.setText(f"Escape no disponible: {type(exc).__name__}: {exc}")
        finally:self.loading=False

    def _update_station_positions(self):
        self.stations.blockSignals(True)
        position=0.0
        for i in range(self.stations.rowCount()):
            if i:
                position+=_number(self.table.item(i-1,2).text(),f"Longitud del tramo {i}")
                self.stations.item(i,1).setText(f"{position:.2f}")
        self.stations.blockSignals(False)

    def _rows(self):
        rows=[]
        for i in range(self.table.rowCount()):
            try:
                length=_number(self.table.item(i,2).text(),f"Longitud del tramo {i+1}")
                d0=_number(self.stations.item(i,2).text(),f"Diámetro de estación {i}")
                d1=_number(self.stations.item(i+1,2).text(),f"Diámetro de estación {i+1}")
            except AttributeError as exc:raise ValueError(f"Tramo {i+1}: falta un dato geométrico") from exc
            rows.append({"name":self.table.item(i,0).text(),"kind":self.table.item(i,1).text(),
                "length_mm":length,"inlet_diameter_mm":d0,"outlet_diameter_mm":d1,
                "provenance":self.table.item(i,3).text()})
        return rows

    def _resolutions(self):
        return [int(self.mesh_table.cellWidget(i,1).currentText()) for i in range(self.mesh_table.rowCount())]

    def _overlay_sections(self):
        name=self.overlay_selector.currentData() if hasattr(self,"overlay_selector") else None
        if not name or name not in self.context.project["variants"]:return []
        try:return escape_sections(self.context.project["variants"][name])
        except (ValueError,KeyError):return []

    def _changed_sections(self):
        if self.context.selected_variant is None:return set()
        changes=compare_configurations(self.context.project["base_engine"],self.context.engine())
        changed=set()
        for item in changes:
            path=item.get("path","")
            if "sections" in path:
                for section in escape_sections(self.context.engine()):
                    if section["name"] in path:changed.add(section["name"])
        return {i for i,row in enumerate(self._rows()) if row["name"] in changed}

    def _draft(self):
        base=self.context.engine();sections=self._rows();counts=self._resolutions()
        current=self._counts(base)
        if current!=[1]*len(current):base=refine_exhaust_configuration(base,[1]*len(current))
        legacy=replace_escape_sections(base,sections,display_name=base["display_name"]+" · escape geometry")
        legacy["native_configuration"]["geometry_identity"].pop("exhaust_mesh_discretization",None)
        from ..engine_configuration import sha256
        legacy["native_configuration_sha256"]=sha256(legacy["native_configuration"])
        return refine_exhaust_configuration(legacy,counts,display_name=base["display_name"]+" · exhaust mesh")

    def _mesh_summary(self,engine):
        native=engine["native_configuration"];duct=next(d for d in native["ducts"] if d["id"]=="exhaust");mesh=duct["mesh"]
        sections=escape_sections(engine);counts=self._counts(engine);rows=[];offset=0
        for section,count in zip(sections,counts):
            rows.append(f"{section['name']}: {section['length_mm']:.1f} mm, Ø {section['inlet_diameter_mm']:.1f}→{section['outlet_diameter_mm']:.1f} mm")
            offset+=count
        length=sum(s["length_mm"] for s in sections);volume=math.fsum(mesh["volumes"])
        return f"Longitud total {length:.1f} mm · volumen interno {volume*1e6:.3f} cm³\n"+" · ".join(rows)+f"\nConfiguración {identity(engine)[:16]}… · {len(mesh['volumes'])} celdas"

    def _cell_changed(self,*_):
        if self.loading:return
        try:
            rows=self._rows();validate(self._draft());self._update_station_positions()
            self.profile.set_sections(rows,self._resolutions(),self._overlay_sections(),self._changed_sections())
            self.diff.setText("Geometría continua · validación correcta sin pasos del solver\n"+self._mesh_summary(self.context.engine()))
        except Exception as exc:self.diff.setText(f"Geometría rechazada: {type(exc).__name__}: {exc}")

    def refresh_overlay(self,*_):
        if hasattr(self,"profile"):self.profile.set_sections(self._rows(),self._resolutions(),self._overlay_sections(),self._changed_sections())

    def save_current(self):
        name=self.context.selected_variant
        if name is None:
            QMessageBox.information(self,"Motor base","El motor base se conserva. Usá ‘Guardar como nueva variante’ para crear una copia editable.");return False
        try:
            edited=self._draft();edited["display_name"]=name;validate(edited);self.context.replace_engine(edited,variant_name=name)
            self.diff.setText(f"Geometría guardada en {name}. No se ejecutó el solver.\n"+self._mesh_summary(edited));return True
        except Exception as exc:self.diff.setText(f"No se aplicó la geometría: {type(exc).__name__}: {exc}");return False

    def save_as_new(self,*,name=None):
        if name is None:
            name,ok=QInputDialog.getText(self,"Nueva variante de escape","Nombre de la variante:",text=f"Escape {len(self.context.project['variants'])+1}")
            if not ok:return False
        try:
            source=self.context.engine();edited=self._draft();edited["display_name"]=name.strip()
            edited["provenance"]={**edited["provenance"],"variant_parent_identity":identity(source)};validate(edited)
            self.context.duplicate_variant(self.context.selected_variant,name)
            self.context.replace_engine(edited,variant_name=name.strip())
            changes=compare_configurations(source,edited)
            self.diff.setText(f"Variante {name.strip()} guardada · {len(changes)} diferencias · sin pasos del solver.\n"+self._mesh_summary(edited));return True
        except Exception as exc:self.diff.setText(f"No se guardó la variante: {type(exc).__name__}: {exc}");return False

    def apply(self,*,name=None):
        """Compatibility slot; UI action always requests an explicit variant name."""
        return self.save_as_new(name=name)
