from __future__ import annotations
from copy import deepcopy
import math
from PySide6.QtCore import QPointF,Qt
from PySide6.QtGui import QColor,QPainter,QPen
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QLabel,QTableWidget,QTableWidgetItem,
    QHeaderView,QPushButton,QMessageBox,QGroupBox,QFormLayout,QDoubleSpinBox)
from ..engine_configuration import identity
from ..engine_variants import escape_sections,replace_escape_sections,compare_configurations


class ExhaustProfile(QWidget):
    def __init__(self,parent=None):super().__init__(parent);self.sections=[];self.setMinimumHeight(220)
    def set_sections(self,sections):self.sections=sections;self.update()
    def paintEvent(self,event):
        p=QPainter(self);p.setRenderHint(QPainter.RenderHint.Antialiasing);p.fillRect(self.rect(),QColor('#101a28'))
        r=self.rect().adjusted(34,20,-18,-30);p.setPen(QPen(QColor('#34475c'),1));p.drawRect(r)
        if not self.sections:p.end();return
        total=sum(s['length_mm'] for s in self.sections);maxd=max(max(s['inlet_diameter_mm'],s['outlet_diameter_mm']) for s in self.sections)
        span=max(1.0,maxd*1.25);center=r.center().y();scale=min(r.height()*.8/span,r.width()/max(total,1))
        x=float(r.left());upper=[];lower=[]
        for s in self.sections:
            length=s['length_mm'];d0=s['inlet_diameter_mm'];d1=s['outlet_diameter_mm'];x0=x;x1=x+length/total*r.width()
            upper.extend([QPointF(x0,center-d0*scale/2),QPointF(x1,center-d1*scale/2)])
            lower.extend([QPointF(x0,center+d0*scale/2),QPointF(x1,center+d1*scale/2)])
            p.setPen(QPen(QColor('#526a82'),1,Qt.PenStyle.DashLine));p.drawLine(round(x1),r.top(),round(x1),r.bottom());x=x1
        p.setPen(QPen(QColor('#43c5f5'),3));p.drawPolyline(upper);p.drawPolyline(list(reversed(lower)))
        p.setPen(QColor('#cad8e7'));p.drawText(r.left(),r.bottom()+20,f"Longitud total: {total:.1f} mm · Ø máximo: {maxd:.1f} mm")
        p.end()


class ExhaustPage(QWidget):
    def __init__(self,context):
        super().__init__();self.context=context;self.loading=False
        root=QVBoxLayout(self);root.setContentsMargins(24,20,24,20)
        title=QLabel("Diseñador de escape");title.setObjectName('title');root.addWidget(title)
        root.addWidget(QLabel("Perfil axisimétrico de secciones cónicas lineales. El gráfico muestra geometría; no predice ondas ni potencia."))
        self.profile=ExhaustProfile();root.addWidget(self.profile)
        self.table=QTableWidget(0,6);self.table.setHorizontalHeaderLabels(["Sección","Tipo","Longitud (mm)","Ø entrada (mm)","Ø salida (mm)","Provenance"]);self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch);self.table.cellChanged.connect(self._cell_changed);root.addWidget(self.table,1)
        row=QHBoxLayout();root.addLayout(row)
        self.diff=QLabel("Base sin modificar");self.diff.setWordWrap(True);row.addWidget(self.diff,1)
        self.apply_button=QPushButton("Crear / actualizar variante de escape");self.apply_button.setObjectName('primaryAction');self.apply_button.clicked.connect(self.apply);row.addWidget(self.apply_button)
        self.context.changed.connect(self.refresh);self.refresh()
    def refresh(self):
        try:
            sections=escape_sections(self.context.engine());self.loading=True;self.table.blockSignals(True);self.table.setRowCount(len(sections))
            for i,s in enumerate(sections):
                values=[s['name'],s['kind'],s['length_mm'],s['inlet_diameter_mm'],s['outlet_diameter_mm'],s['provenance']]
                for j,v in enumerate(values):
                    item=QTableWidgetItem(str(v));
                    if j in (0,1,5):item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    self.table.setItem(i,j,item)
            self.table.blockSignals(False);self.profile.set_sections(sections);self.diff.setText(f"Identidad activa: {identity(self.context.engine())}\nLos cambios todavía no se aplicaron.")
        except Exception as exc:self.diff.setText(f"Escape no disponible: {exc}")
        finally:self.loading=False
    def _cell_changed(self,*_):
        if not self.loading:
            try:self.profile.set_sections(self._rows());self.diff.setText("Perfil actualizado en edición; requiere validación del motor antes de guardar.")
            except Exception as exc:self.diff.setText(f"Sección inválida: {exc}")
    def _rows(self):
        rows=[]
        for i in range(self.table.rowCount()):
            vals=[self.table.item(i,j).text().strip() for j in range(6)]
            try:rows.append({"name":vals[0],"kind":vals[1],"length_mm":float(vals[2]),"inlet_diameter_mm":float(vals[3]),"outlet_diameter_mm":float(vals[4]),"provenance":vals[5]})
            except (ValueError,TypeError) as exc:raise ValueError(f"Fila {i+1}: longitudes y diámetros deben ser números finitos") from exc
        if any(not math.isfinite(r[k]) for r in rows for k in ('length_mm','inlet_diameter_mm','outlet_diameter_mm')):raise ValueError("Dimensiones no finitas")
        return rows
    def apply(self):
        try:
            base=self.context.engine();edited=replace_escape_sections(base,self._rows(),display_name=base['display_name']+" · escape")
            parent=self.context.selected_variant
            name=f"Escape {len(self.context.project['variants'])+1}"
            self.context.project['variants'][name]=edited;self.context.selected_variant=name
            changes=compare_configurations(base,edited);self.context.dirty=True;self.context.changed.emit()
            self.diff.setText(f"Variante {name} validada sin solver · {len(changes)} campos derivados modificados.\n"
                +"\n".join(f"{x['path']} ({x['unit']}): {x['before']} → {x['after']}" for x in changes[:8]))
        except Exception as exc:self.diff.setText(f"No se aplicó la variante: {type(exc).__name__}: {exc}")
