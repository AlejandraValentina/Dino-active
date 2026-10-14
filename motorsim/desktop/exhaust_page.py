from __future__ import annotations
from copy import deepcopy
import math
from PySide6.QtCore import QPointF,Qt
from PySide6.QtGui import QColor,QPainter,QPen
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QLabel,QTableWidget,QTableWidgetItem,
    QHeaderView,QPushButton,QMessageBox,QComboBox)
from ..engine_configuration import identity,validate
from ..engine_variants import escape_sections,replace_escape_sections,compare_configurations
from ..exhaust_mesh_v1 import refine_exhaust_configuration


class ExhaustProfile(QWidget):
    def __init__(self,parent=None):super().__init__(parent);self.sections=[];self.refinements=[];self.setMinimumHeight(220)
    def set_sections(self,sections,refinements=None):
        self.sections=deepcopy(sections);self.refinements=list(refinements or [1]*len(sections));self.update()
    def paintEvent(self,event):
        p=QPainter(self);p.setRenderHint(QPainter.RenderHint.Antialiasing);p.fillRect(self.rect(),QColor('#101a28'))
        r=self.rect().adjusted(34,20,-18,-30);p.setPen(QPen(QColor('#34475c'),1));p.drawRect(r)
        if not self.sections:p.end();return
        total=sum(s['length_mm'] for s in self.sections);maxd=max(max(s['inlet_diameter_mm'],s['outlet_diameter_mm']) for s in self.sections)
        span=max(1.0,maxd*1.25);center=r.center().y();scale=min(r.height()*.8/span,r.width()/max(total,1))
        x=float(r.left());upper=[];lower=[]
        for si,s in enumerate(self.sections):
            length=s['length_mm'];d0=s['inlet_diameter_mm'];d1=s['outlet_diameter_mm'];x0=x;x1=x+length/total*r.width()
            upper.extend([QPointF(x0,center-d0*scale/2),QPointF(x1,center-d1*scale/2)])
            lower.extend([QPointF(x0,center+d0*scale/2),QPointF(x1,center+d1*scale/2)])
            n=self.refinements[si] if si<len(self.refinements) else 1
            p.setPen(QPen(QColor('#91a4b9'),1,Qt.PenStyle.DotLine))
            for k in range(1,n):
                xx=round(x0+(x1-x0)*k/n);dd=d0+(d1-d0)*k/n
                p.drawLine(xx,round(center-dd*scale/2),xx,round(center+dd*scale/2))
            p.setPen(QPen(QColor('#526a82'),1,Qt.PenStyle.DashLine));p.drawLine(round(x1),r.top(),round(x1),r.bottom());x=x1
        p.setPen(QPen(QColor('#43c5f5'),3));p.drawPolyline(upper);p.drawPolyline(list(reversed(lower)))
        p.setPen(QColor('#cad8e7'));p.drawText(r.left(),r.bottom()+20,f"Longitud total: {total:.1f} mm · Ø máximo: {maxd:.1f} mm · celdas: {sum(self.refinements)}")
        p.end()


class ExhaustPage(QWidget):
    def __init__(self,context):
        super().__init__();self.context=context;self.loading=False
        root=QVBoxLayout(self);root.setContentsMargins(24,20,24,20)
        title=QLabel("Diseñador de escape");title.setObjectName('title');root.addWidget(title)
        root.addWidget(QLabel("Perfil axisimétrico de secciones cónicas lineales. La malla representa geometría cuasi-1D y no implica validación física."))
        self.profile=ExhaustProfile();root.addWidget(self.profile)
        self.table=QTableWidget(0,7);self.table.setHorizontalHeaderLabels(["Sección","Tipo","Longitud (mm)","Ø entrada (mm)","Ø salida (mm)","Provenance","Celdas/ sección"]);self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch);self.table.cellChanged.connect(self._cell_changed);root.addWidget(self.table,1)
        row=QHBoxLayout();root.addLayout(row)
        self.diff=QLabel("Base sin modificar");self.diff.setWordWrap(True);row.addWidget(self.diff,1)
        self.apply_button=QPushButton("Crear / actualizar variante de escape");self.apply_button.setObjectName('primaryAction');self.apply_button.clicked.connect(self.apply);row.addWidget(self.apply_button)
        self.context.changed.connect(self.refresh);self.refresh()
    def _counts(self,engine):
        native=engine['native_configuration'];meta=native['geometry_identity'].get('exhaust_mesh_discretization')
        sections=escape_sections(engine)
        return list(meta['cells_per_section']) if meta else [1]*len(sections)
    def refresh(self):
        try:
            engine=self.context.engine();sections=escape_sections(engine);counts=self._counts(engine)
            self.loading=True;self.table.blockSignals(True);self.table.setRowCount(len(sections))
            for i,s in enumerate(sections):
                values=[s['name'],s['kind'],s['length_mm'],s['inlet_diameter_mm'],s['outlet_diameter_mm'],s['provenance']]
                for j,v in enumerate(values):
                    item=QTableWidgetItem(str(v))
                    if j in (0,1,5):item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    self.table.setItem(i,j,item)
                combo=QComboBox();combo.addItems(['1','2','4']);combo.setCurrentText(str(counts[i]));combo.currentIndexChanged.connect(self._cell_changed);self.table.setCellWidget(i,6,combo)
            self.table.blockSignals(False);self.profile.set_sections(sections,counts);self.diff.setText(self._mesh_summary(engine))
        except Exception as exc:self.diff.setText(f"Escape no disponible: {exc}")
        finally:self.loading=False
    def _rows(self):
        rows=[]
        for i in range(self.table.rowCount()):
            vals=[self.table.item(i,j).text().strip() for j in range(6)]
            try:rows.append({"name":vals[0],"kind":vals[1],"length_mm":float(vals[2]),"inlet_diameter_mm":float(vals[3]),"outlet_diameter_mm":float(vals[4]),"provenance":vals[5]})
            except (ValueError,TypeError) as exc:raise ValueError(f"Fila {i+1}: longitudes y diámetros deben ser números finitos") from exc
        if any(not math.isfinite(r[k]) for r in rows for k in ('length_mm','inlet_diameter_mm','outlet_diameter_mm')):raise ValueError("Dimensiones no finitas")
        return rows
    def _resolutions(self):return [int(self.table.cellWidget(i,6).currentText()) for i in range(self.table.rowCount())]
    def _draft(self):
        base=self.context.engine();sections=self._rows();counts=self._resolutions()
        current=self._counts(base)
        if current!=[1]*len(current):base=refine_exhaust_configuration(base,[1]*len(current))
        legacy=replace_escape_sections(base,sections,display_name=base['display_name']+" · escape geometry")
        legacy["native_configuration"]["geometry_identity"].pop("exhaust_mesh_discretization",None)
        from ..engine_configuration import sha256
        legacy["native_configuration_sha256"]=sha256(legacy["native_configuration"])
        return refine_exhaust_configuration(legacy,counts,display_name=base['display_name']+" · exhaust mesh")
    def _mesh_summary(self,engine):
        native=engine['native_configuration'];duct=next(d for d in native['ducts'] if d['id']=='exhaust');mesh=duct['mesh'];counts=self._counts(engine);sections=escape_sections(engine)
        positions=mesh['faces'];rows=[];offset=0
        for section,count in zip(sections,counts):
            volumes=mesh['volumes'][offset:offset+count];rows.append(f"{section['name']}: {count} celdas, L={section['length_mm']:.2f} mm, A={mesh['areas'][offset]:.6g}→{mesh['areas'][offset+count]:.6g} m², V={sum(volumes):.6g} m³, x={positions[offset]:.6g}–{positions[offset+count]:.6g} m");offset+=count
        return f"Identidad: {identity(engine)} | total {len(mesh['volumes'])} celdas\n"+"\n".join(rows)
    def _cell_changed(self,*_):
        if self.loading:return
        try:
            self.profile.set_sections(self._rows(),self._resolutions());draft=self._draft();validate(draft)
            self.diff.setText("Vista previa validada sin avanzar el solver\n"+self._mesh_summary(draft))
        except Exception as exc:self.diff.setText(f"Malla inválida: {type(exc).__name__}: {exc}")
    def apply(self):
        try:
            base=self.context.engine();edited=self._draft();validate(edited)
            name=f"Escape {len(self.context.project['variants'])+1}"
            self.context.project['variants'][name]=edited;self.context.selected_variant=name
            changes=compare_configurations(base,edited);self.context.dirty=True;self.context.changed.emit()
            self.diff.setText(f"Variante {name} guardada como configuración; sin pasos del solver. {len(changes)} cambios.\n"+self._mesh_summary(edited))
        except Exception as exc:self.diff.setText(f"No se aplicó la variante: {type(exc).__name__}: {exc}")
