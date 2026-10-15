from __future__ import annotations

from copy import deepcopy
import math

from PySide6.QtCore import QPointF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QLabel,QTableWidget,QTableWidgetItem,
    QHeaderView,QPushButton,QMessageBox,QComboBox,QGroupBox,QInputDialog,QAbstractItemView,QSplitter)

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
        super().__init__(parent);self.sections=[];self.overlay=[];self.refinements=[];self.changed_sections=set();self.setMinimumHeight(340)

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
                painter.setPen(QColor("#cad8e7"))
                painter.drawText(round((x0+x1)/2)-70,rect.top()+13,140,16,Qt.AlignmentFlag.AlignCenter,
                                 f"Ø {s['inlet_diameter_mm']:.1f} → {s['outlet_diameter_mm']:.1f} mm")
                painter.setPen(QPen(QColor("#91a8bf"),1));painter.drawLine(round(x0),rect.bottom()+8,round(x1),rect.bottom()+8)
                painter.drawLine(round(x0),rect.bottom()+4,round(x0),rect.bottom()+12);painter.drawLine(round(x1),rect.bottom()+4,round(x1),rect.bottom()+12)
                painter.setPen(QColor("#cad8e7"));painter.drawText(round((x0+x1)/2)-76,rect.bottom()+26,152,16,Qt.AlignmentFlag.AlignCenter,
                                 f"{s['name']} · {s['length_mm']:.1f} mm")
            cursor+=s["length_mm"]
        painter.setPen(QPen(QColor(color),width,style));painter.drawPolyline(upper);painter.drawPolyline(list(reversed(lower)))

    def paintEvent(self,event):
        painter=QPainter(self);painter.setRenderHint(QPainter.RenderHint.Antialiasing);painter.fillRect(self.rect(),QColor("#101a28"))
        rect=self.rect().adjusted(42,14,-18,-54);painter.setPen(QPen(QColor("#34475c"),1));painter.drawRect(rect)
        if not self.sections:painter.end();return
        self._draw_profile(painter,self.sections,rect,"#43c5f5",3)
        if self.overlay:self._draw_profile(painter,self.overlay,rect,"#f59e0b",2,Qt.PenStyle.DashLine)
        painter.end()


class ExhaustPage(QWidget):
    component_state_changed=Signal()
    def __init__(self,context):
        super().__init__();self.context=context;self.loading=False;self.edit_state="complete"
        root=QVBoxLayout(self);root.setContentsMargins(12,10,12,10);root.setSpacing(6)
        self.title=QLabel("Escape");self.title.setObjectName("title");root.addWidget(self.title)
        self.intro=QLabel("Perfil y tabla por tramo. Los deltas geométricos no estiman prestaciones.");root.addWidget(self.intro)
        self.profile=ExhaustProfile()
        self.diff=QLabel("Elegí una baseline para ver diferencias de ingeniería.");self.diff.setWordWrap(True)
        diff_panel=QGroupBox("Cambios vs baseline");diff_layout=QVBoxLayout(diff_panel);diff_layout.addWidget(self.diff)
        profile_split=QSplitter(Qt.Orientation.Horizontal);profile_split.setChildrenCollapsible(False);profile_split.addWidget(self.profile);profile_split.addWidget(diff_panel);profile_split.setStretchFactor(0,4);profile_split.setStretchFactor(1,1);root.addWidget(profile_split)
        self.overlay_selector=QComboBox();self.overlay_selector.addItem("Motor base", "base")
        for name in sorted(context.project["variants"]):self.overlay_selector.addItem(name,name)
        self.overlay_selector.currentIndexChanged.connect(self.refresh_overlay)
        self.station_toggle=QPushButton("Estaciones avanzadas ▸");self.station_toggle.clicked.connect(self._toggle_stations)
        overlay_row=QHBoxLayout();overlay_row.addWidget(QLabel("Baseline"));overlay_row.addWidget(self.overlay_selector);overlay_row.addWidget(self.station_toggle);overlay_row.addStretch();root.addLayout(overlay_row)

        self.stations=QTableWidget(0,3);self.stations.setObjectName("exhaustStations")
        self.stations.setHorizontalHeaderLabels(["Estación compartida","Posición (mm)","Ø (mm)"])
        self.stations.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.stations.setMaximumHeight(150);self.stations.cellChanged.connect(self._cell_changed)
        station_group=QGroupBox("Avanzado · estaciones compartidas");station_group.setObjectName("stationsAdvanced");self.station_group=station_group
        station_layout=QVBoxLayout(station_group);station_layout.addWidget(self.stations)
        self.stations.hide();station_group.setMaximumHeight(190);station_group.hide()
        self.table=QTableWidget(0,7);self.table.setObjectName("exhaustSegments");self.segments=self.table
        self.table.setHorizontalHeaderLabels(["Tramo","Largo (mm)","Ø entrada (mm)","Ø salida (mm)","Semiángulo (°)","Volumen (cm³)","Δ baseline"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setMaximumHeight(260);self.table.cellChanged.connect(self._cell_changed)
        segment_group=QGroupBox("Tramos · editá largo y Ø de salida; la estación compartida actualiza el tramo siguiente")
        segment_layout=QVBoxLayout(segment_group);segment_layout.addWidget(self.table);root.addWidget(segment_group);root.addWidget(station_group)

        self.mesh_group=QGroupBox("Opciones avanzadas · malla numérica");self.mesh_group.setCheckable(True);self.mesh_group.setChecked(False)
        mesh_layout=QVBoxLayout(self.mesh_group)
        self.mesh_notice=QLabel("La independencia espacial NO está demostrada. La resolución cambia la discretización, no valida la geometría ni el desempeño.")
        self.mesh_notice.setWordWrap(True);self.mesh_notice.setObjectName("notice");mesh_layout.addWidget(self.mesh_notice)
        self.mesh_table=QTableWidget(0,2);self.mesh_table.setHorizontalHeaderLabels(["Tramo","Celdas por tramo (1/2/4)"])
        self.mesh_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch);self.mesh_table.setMaximumHeight(180)
        mesh_layout.addWidget(self.mesh_table);root.addWidget(self.mesh_group)

        actions=QHBoxLayout();root.addLayout(actions)
        self.save_current_button=QPushButton("Guardar en variante actual");self.save_current_button.clicked.connect(self.save_current);actions.addWidget(self.save_current_button)
        self.apply_button=QPushButton("Guardar como nueva variante…");self.apply_button.setObjectName("primaryAction");self.apply_button.clicked.connect(self.save_as_new);actions.addWidget(self.apply_button)
        self.context.changed.connect(self.refresh);self.context.variant_changed.connect(self.refresh);self.refresh()

    def _refresh_overlay_options(self):
        """Keep the selector bound to the currently open project's variants."""
        selected=self.overlay_selector.currentData()
        names=["base",*sorted(self.context.project["variants"])]
        if names==[self.overlay_selector.itemData(i) for i in range(self.overlay_selector.count())]:
            return
        self.overlay_selector.blockSignals(True);self.overlay_selector.clear()
        self.overlay_selector.addItem("Motor base","base")
        for name in names[1:]:self.overlay_selector.addItem(name,name)
        index=self.overlay_selector.findData(selected)
        self.overlay_selector.setCurrentIndex(index if index>=0 else self.overlay_selector.findData("base"))
        self.overlay_selector.blockSignals(False)

    def _counts(self,engine):
        meta=engine["native_configuration"]["geometry_identity"].get("exhaust_mesh_discretization")
        return list(meta["cells_per_section"]) if meta else [1]*len(escape_sections(engine))

    def _clear_widgets(self):
        for row in range(self.mesh_table.rowCount()):
            widget=self.mesh_table.cellWidget(row,1)
            if widget:self.mesh_table.removeCellWidget(row,1);widget.deleteLater()

    def refresh(self):
        try:
            self.edit_state="complete"
            self._refresh_overlay_options()
            engine=self.context.engine();sections=escape_sections(engine);counts=self._counts(engine)
            self.loading=True;self._clear_widgets();self.table.blockSignals(True);self.stations.blockSignals(True);self.mesh_table.blockSignals(True)
            self.table.setRowCount(len(sections));self.stations.setRowCount(len(sections)+1)
            changed_sections=self._changed_sections()
            diameters=[sections[0]["inlet_diameter_mm"]]+[s["outlet_diameter_mm"] for s in sections]
            for i,diameter in enumerate(diameters):
                label="Entrada" if i==0 else ("Salida" if i==len(sections) else f"Unión {i}")
                for col,value in enumerate((label,"0.00",f"{diameter:.3f}")):
                    item=QTableWidgetItem(value)
                    if col<2 or i==0:item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    self.stations.setItem(i,col,item)
            self.mesh_table.setRowCount(len(sections))
            for i,s in enumerate(sections):
                angle=math.degrees(math.atan2((s["outlet_diameter_mm"]-s["inlet_diameter_mm"])/2,s["length_mm"]))
                r0=s["inlet_diameter_mm"]/2;r1=s["outlet_diameter_mm"]/2
                volume=math.pi*s["length_mm"]*(r0*r0+r0*r1+r1*r1)/3/1000
                for col in range(self.table.columnCount()):
                    item=QTableWidgetItem("");item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable);self.table.setItem(i,col,item)
                values=((0,s["name"]),(1,f"{s['length_mm']:.1f}"),(2,f"{s['inlet_diameter_mm']:.1f}"),
                        (3,f"{s['outlet_diameter_mm']:.1f}"),(4,f"{angle:.2f}"),(5,f"{volume:.1f}"),(6,self._section_delta(i,s)))
                for col,value in values:
                    item=QTableWidgetItem(str(value))
                    if col not in (1,3):item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    self.table.setItem(i,col,item)
                item=QTableWidgetItem(s["name"]);item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable);self.mesh_table.setItem(i,0,item)
                combo=QComboBox();combo.setObjectName(f"meshResolution_{i}");combo.addItems(["1","2","4"]);combo.setCurrentText(str(counts[i]));combo.currentIndexChanged.connect(self._cell_changed)
                self.mesh_table.setCellWidget(i,1,combo)
            self.table.blockSignals(False);self.stations.blockSignals(False);self.mesh_table.blockSignals(False)
            self._update_station_positions()
            self.profile.set_sections(self._rows(),self._resolutions(),self._overlay_sections(),self._changed_sections())
            self.diff.setText(self._engineering_diff(engine));self.save_current_button.setEnabled(self.context.selected_variant is not None)
        except Exception as exc:self.diff.setText(f"Escape no disponible: {type(exc).__name__}: {exc}")
        finally:self.loading=False

    def _update_station_positions(self):
        self.stations.blockSignals(True)
        position=0.0
        sections=len(escape_sections(self.context.engine()))
        for i in range(sections+1):
            self.stations.item(i,1).setText(f"{position:.2f}")
            if i<sections:position+=_number(self.table.item(i,1).text(),f"Longitud del tramo {i+1}")
        self.stations.blockSignals(False)

    def _toggle_stations(self):
        visible=not self.station_group.isVisible()
        self.station_group.setVisible(visible);self.station_toggle.setText("Estaciones ▾" if visible else "Estaciones avanzadas ▸")

    def resizeEvent(self,event):
        super().resizeEvent(event)
        compact=self.width()<=1120
        self.set_compact_layout(compact,self.width()<=1000)

    def set_compact_layout(self,compact,very_compact=False):
        self.title.setVisible(not compact);self.intro.setVisible(not compact)
        self.profile.setMinimumHeight(125 if very_compact else 220 if compact else 300)

    def _rows(self):
        rows=[];source_sections=escape_sections(self.context.engine())
        for i in range(len(source_sections)):
            try:
                length=_number(self.table.item(i,1).text(),f"Longitud del tramo {i+1}")
                d0=_number(self.stations.item(i,2).text(),f"Diámetro de estación {i}")
                d1=_number(self.table.item(i,3).text(),f"Diámetro de salida del tramo {i+1}")
            except AttributeError as exc:raise ValueError(f"Tramo {i+1}: falta un dato geométrico") from exc
            rows.append({"name":self.table.item(i,0).text(),"kind":source_sections[i]["kind"],
                "length_mm":length,"inlet_diameter_mm":d0,"outlet_diameter_mm":d1,
                "provenance":source_sections[i]["provenance"]})
        return rows

    def _section_delta(self,index,current):
        name=self.overlay_selector.currentData() if hasattr(self,"overlay_selector") else None
        baseline=self.context.project["base_engine"] if name=="base" else self.context.project["variants"].get(name)
        if baseline is None:return "—"
        try:old=escape_sections(baseline)[index]
        except (IndexError,KeyError,ValueError):return "—"
        parts=[]
        for key,label in (("length_mm","L"),("inlet_diameter_mm","Øin"),("outlet_diameter_mm","Øout")):
            before=float(old[key]);after=float(current[key])
            if not math.isclose(before,after,abs_tol=1e-9):parts.append(f"{label} {after-before:+g} mm")
        def derived(section):
            length=float(section["length_mm"]);d0=float(section["inlet_diameter_mm"]);d1=float(section["outlet_diameter_mm"])
            angle=math.degrees(math.atan2((d1-d0)/2,length))
            r0=d0/2;r1=d1/2;volume=math.pi*length*(r0*r0+r0*r1+r1*r1)/3/1000
            return angle,volume
        old_angle,old_volume=derived(old);new_angle,new_volume=derived(current)
        if not math.isclose(old_angle,new_angle,abs_tol=1e-9):parts.append(f"θ {new_angle-old_angle:+.2f}°")
        if not math.isclose(old_volume,new_volume,abs_tol=1e-9):parts.append(f"V {new_volume-old_volume:+.1f} cm³")
        return " · ".join(parts) if parts else "—"

    def _resolutions(self):
        return [int(self.mesh_table.cellWidget(i,1).currentText()) for i in range(self.mesh_table.rowCount())]

    def _overlay_sections(self):
        name=self.overlay_selector.currentData() if hasattr(self,"overlay_selector") else None
        if not name:return []
        engine=self.context.project["base_engine"] if name=="base" else self.context.project["variants"].get(name)
        if engine is None:return []
        if identity(engine)==identity(self.context.engine()):return []
        try:return escape_sections(engine)
        except (ValueError,KeyError):return []

    def _changed_sections(self):
        if self.context.selected_variant is None:return set()
        baseline_name=self.overlay_selector.currentData()
        baseline=self.context.project["base_engine"] if baseline_name=="base" else self.context.project["variants"].get(baseline_name)
        if baseline is None:return set()
        changes=compare_configurations(baseline,self.context.engine())
        changed=set()
        for item in changes:
            path=item.get("path","")
            marker="/chamber/sections/"
            if marker in path:
                remainder=path.split(marker,1)[1].split("/",1)[0]
                if remainder.isdigit():changed.add(int(remainder))
        return {index for index in changed if 0<=index<len(escape_sections(self.context.engine()))}

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
        return f"Longitud total {length:.1f} mm · volumen interno {volume*1e6:.3f} cm³\n"+" · ".join(rows)+f"\nConfiguración activa · {len(mesh['volumes'])} celdas"

    def _engineering_diff(self,engine):
        name=self.overlay_selector.currentData();baseline=(self.context.project["base_engine"] if name=="base" else self.context.project["variants"].get(name))
        if baseline is None:return "No hay una baseline compatible seleccionada."
        before=escape_sections(baseline);after=escape_sections(engine);lines=[]
        for old,new in zip(before,after):
            if old["length_mm"]!=new["length_mm"]:
                lines.append(f"{new['name']}: longitud {old['length_mm']:g} → {new['length_mm']:g} mm")
        old_length=math.fsum(section["length_mm"] for section in before);new_length=math.fsum(section["length_mm"] for section in after)
        old_mesh=next(d for d in baseline["native_configuration"]["ducts"] if d["id"]=="exhaust")["mesh"]
        new_mesh=next(d for d in engine["native_configuration"]["ducts"] if d["id"]=="exhaust")["mesh"]
        old_volume=math.fsum(old_mesh["volumes"])*1e6;new_volume=math.fsum(new_mesh["volumes"])*1e6
        if len(before)==len(after):
            for old,new in zip(before,after):
                old_angle=math.degrees(math.atan2((old["outlet_diameter_mm"]-old["inlet_diameter_mm"])/2,old["length_mm"]))
                new_angle=math.degrees(math.atan2((new["outlet_diameter_mm"]-new["inlet_diameter_mm"])/2,new["length_mm"]))
                if not math.isclose(old_angle,new_angle,abs_tol=1e-6):lines.append(f"{new['name']}: semiángulo {old_angle:.2f}° → {new_angle:.2f}°")
        prefix="\n".join(lines) if lines else "Geometría coincidente con la baseline."
        return (f"Baseline: {name or 'no seleccionada'}\n{prefix}\nLongitud total: {old_length:.1f} → {new_length:.1f} mm\n"
                f"Volumen interno: {old_volume:.2f} → {new_volume:.2f} cm³\nDiferencia geométrica únicamente; no estima prestaciones.")

    def _cell_changed(self,*args):
        if self.loading:return
        try:
            source=self.sender()
            row,column=(args[:2] if len(args)>=2 else (-1,-1))
            if source is self.table and column==3:
                if 0<=row<self.stations.rowCount()-1:
                    self.stations.blockSignals(True);self.stations.item(row+1,2).setText(self.table.item(row,3).text());self.stations.blockSignals(False)
            elif source is self.stations and column==2:
                if 0<row<=self.table.rowCount():
                    self.table.blockSignals(True);self.table.item(row-1,3).setText(self.stations.item(row,2).text());self.table.blockSignals(False)
            rows=self._rows();validate(self._draft());self._update_station_positions()
            self.table.blockSignals(True)
            for index,section in enumerate(rows):
                angle=math.degrees(math.atan2((section["outlet_diameter_mm"]-section["inlet_diameter_mm"])/2,section["length_mm"]))
                r0=section["inlet_diameter_mm"]/2;r1=section["outlet_diameter_mm"]/2
                volume=math.pi*section["length_mm"]*(r0*r0+r0*r1+r1*r1)/3/1000
                self.table.item(index,2).setText(f"{section['inlet_diameter_mm']:.1f}")
                self.table.item(index,4).setText(f"{angle:.2f}");self.table.item(index,5).setText(f"{volume:.1f}")
                self.table.item(index,6).setText(self._section_delta(index,section))
            self.table.blockSignals(False)
            self.edit_state="modified"
            self.profile.set_sections(rows,self._resolutions(),self._overlay_sections(),self._changed_sections())
            self.diff.setText("Geometría continua · validación correcta sin pasos del solver\n"+self._engineering_diff(self._draft()))
        except Exception as exc:self.edit_state="invalid";self.diff.setText(f"Geometría rechazada: {type(exc).__name__}: {exc}")
        self.component_state_changed.emit()

    def refresh_overlay(self,*_):
        if hasattr(self,"profile"):
            self.profile.set_sections(self._rows(),self._resolutions(),self._overlay_sections(),self._changed_sections())
            for row in range(self.table.rowCount()):
                section=self._rows()[row]
                self.table.item(row,6).setText(self._section_delta(row,section))
            self.diff.setText(self._engineering_diff(self.context.engine()))

    def save_current(self):
        name=self.context.selected_variant
        if name is None:
            QMessageBox.information(self,"Motor base","El motor base se conserva. Usá ‘Guardar como nueva variante’ para crear una copia editable.");return False
        try:
            edited=self._draft();edited["display_name"]=name;validate(edited);self.context.replace_engine(edited,variant_name=name)
            self.edit_state="complete"
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
            self.edit_state="complete"
            changes=compare_configurations(source,edited)
            self.diff.setText(f"Variante {name.strip()} guardada · {len(changes)} diferencias · sin pasos del solver.\n"+self._mesh_summary(edited));return True
        except Exception as exc:self.diff.setText(f"No se guardó la variante: {type(exc).__name__}: {exc}");return False

    def apply(self,*,name=None):
        """Compatibility slot; UI action always requests an explicit variant name."""
        return self.save_as_new(name=name)
