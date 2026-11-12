"""Small interactive gap-preserving Qt plot; no scientific interpolation."""
from __future__ import annotations
import math
from PySide6.QtCore import QPointF, Signal, Qt, QSize
from PySide6.QtGui import QColor, QPainter, QPen, QFont, QFontMetrics
from PySide6.QtWidgets import (QWidget, QHBoxLayout, QToolButton, QLabel, QFileDialog,
    QDialog, QVBoxLayout, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox, QMenu, QApplication)
from .presentation import format_number


class CurvePlot(QWidget):
    pointSelected = Signal(object)
    COLORS=["#43c5f5","#f59e0b","#a78bfa","#34d399","#fb7185"]
    def __init__(self,parent=None,*,expanded=False):
        super().__init__(parent); self.series=[]; self.selected=None;self.y_scale_mode="include_zero";self.axis_y_bounds=None;self.y_ticks=();self.setMinimumHeight(180 if not expanded else 320); self.setMouseTracking(True); self._viewport=None; self._drag=None; self._selection_key=None
        self.setMinimumWidth(350)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAccessibleName("Gráfico de muestras: flechas inspeccionan; más/menos amplían; Inicio restaura")
        self.tools=QWidget(self); row=QHBoxLayout(self.tools); row.setContentsMargins(2,0,2,0)
        row.setSpacing(4)
        commands=[('+','Ampliar vista (+)',lambda:self.zoom(.7)),('−','Alejar vista (-)',lambda:self.zoom(1/.7)),('Restablecer','Restablecer vista (Inicio)',self.reset_view),('Muestras…','Inspeccionar muestras y ausencias',self.show_samples)]
        if not expanded:commands.append(('Ampliar','Abrir exploración en ventana amplia',self.show_expanded))
        for text,tip,callback in commands:
            button=QToolButton();button.setText(text);button.setToolTip(tip);button.setAccessibleName(tip);button.clicked.connect(callback);row.addWidget(button)
        export=QToolButton();export.setText('Exportar');export.setAccessibleName('Exportar muestras CSV o vista PNG');export.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup);menu=QMenu(export);export.setMenu(menu)
        menu.addAction('Muestras originales CSV…',self.export_samples);menu.addAction('Vista actual PNG…',self.export_image);row.addWidget(export)
        row.addStretch()
        self.readout=QLabel("Flechas: muestras · rueda: zoom · arrastrar con botón central: desplazar",self)
        self.readout.setTextFormat(Qt.TextFormat.PlainText);self.readout.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.pointSelected.connect(self._inspect_selected)
    def set_series(self,series,*,y_scale_mode="include_zero"):
        if y_scale_mode not in {"include_zero","data_margin","nonnegative_data_margin"}:raise ValueError("unknown y-axis scale mode")
        self.series=list(series);self.selected=None;self._selection_key=None;self._viewport=None;self.readout.setText("Flechas: muestras · rueda: zoom · botón central: desplazar");self.y_scale_mode=y_scale_mode;self.update()
    def _points(self):
        return [(s,i,p) for s in self.series for i,p in enumerate(s.get('points',[])) if self._finite(s,p)]

    def _axis_ranges(self,allp):
        if not allp:self.axis_y_bounds=None;self.y_ticks=();return None
        xs=[float(p[s.get("x_key","rpm")]) for s,_,p in allp]
        xs.extend(float(p[s.get("x_key","rpm")]) for s,_,p in self._missing_points())
        ys=[float(p["value"]) for _,_,p in allp]
        xmin,xmax=min(xs),max(xs);raw_min,raw_max=min(ys),max(ys)
        if self.y_scale_mode in {"data_margin","nonnegative_data_margin"}:
            span=raw_max-raw_min
            margin=span*.05 if span>0 else max(abs(raw_min)*.05,1.0)
            ymin,ymax=raw_min-margin,raw_max+margin
            if self.y_scale_mode=="nonnegative_data_margin" and raw_min>=0:ymin=max(0.0,ymin)
        else:ymin,ymax=min(0.0,raw_min),max(0.0,raw_max)
        if xmax==xmin:xmax=xmin+1
        if ymax==ymin:
            margin=max(abs(ymin)*.05,1.0);ymin-=margin;ymax+=margin
        if self._viewport is not None:xmin,xmax,ymin,ymax=self._viewport
        self.axis_y_bounds=(ymin,ymax)
        self.y_ticks=tuple(ymin+(ymax-ymin)*i/4 for i in range(5))
        return xmin,xmax,ymin,ymax
    def _missing_points(self):
        return [(s,i,p) for s in self.series for i,p in enumerate(s.get("points",[]))
                if p.get("value") is None and p.get(s.get("x_key","rpm")) is not None
                and math.isfinite(float(p[s.get("x_key","rpm")]))]
    def paintEvent(self,event):
        painter=QPainter(self); painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(),QColor("#101a28")); rect=self.rect().adjusted(76,56,-18,-64)
        allp=self._points()
        if self.series:
            painter.setFont(QFont("Segoe UI",8));metrics=QFontMetrics(painter.font())
            legend_x=rect.left();legend_y=32;legend_right=rect.right()
            for index,series in enumerate(self.series):
                color=QColor("#f6bd60" if series.get("role")=="baseline" else self.COLORS[index%len(self.COLORS)])
                label=str(series.get("name") or f"Serie {index+1}")
                available=legend_right-legend_x-14
                if available<20:break
                label=metrics.elidedText(label,Qt.TextElideMode.ElideRight,available)
                width=metrics.horizontalAdvance(label)
                painter.setPen(QPen(color,2));painter.drawLine(legend_x,legend_y+7,legend_x+8,legend_y+7)
                painter.setPen(QColor("#cad8e7"));painter.drawText(
                    legend_x+11,legend_y,max(0,width),14,
                    Qt.AlignmentFlag.AlignLeft|Qt.AlignmentFlag.AlignVCenter,label)
                legend_x+=width+28
        painter.setPen(QPen(QColor("#34475c"),1))
        for i in range(5):
            y=rect.top()+i*rect.height()/4; painter.drawLine(rect.left(),round(y),rect.right(),round(y))
        painter.setPen(QPen(QColor("#9fb3c8"),1)); painter.drawRect(rect)
        missing=self._missing_points()
        if not allp:
            self.axis_y_bounds=None;self.y_ticks=()
            if missing:
                xs=[float(p[s.get("x_key","rpm")]) for s,_,p in missing];xmin,xmax=min(xs),max(xs)
                if xmin==xmax:xmax=xmin+1
                reasons=sorted({str(p.get("reason")) for _,_,p in missing if p.get("reason")})
                painter.setPen(QColor("#cad8e7"));painter.drawText(rect.adjusted(12,12,-12,-24),Qt.AlignmentFlag.AlignCenter,"Sin valores numéricos definidos\n"+(reasons[0] if reasons else "La métrica requiere un estado de corrida que aún no está disponible."))
                painter.drawText(rect.left(),rect.bottom()+26,f"RPM  {format_number(xmin)} — {format_number(xmax)}")
            else:painter.drawText(rect,Qt.AlignmentFlag.AlignCenter,"Sin valores válidos para graficar")
            painter.end(); return
        xlabel=self.series[0].get("x_label","RPM") if self.series else "RPM"
        xmin,xmax,ymin,ymax=self._axis_ranges(allp)
        painter.setPen(QPen(QColor('#34475c'),1))
        for i in range(5):
            value=xmin+(xmax-xmin)*i/4;x=rect.left()+rect.width()*i/4
            painter.drawLine(round(x),rect.top(),round(x),rect.bottom())
            painter.setPen(QColor('#cad8e7'));painter.drawText(round(x)-32,rect.bottom()+3,64,14,Qt.AlignmentFlag.AlignCenter,format_number(value,5))
            painter.setPen(QPen(QColor('#34475c'),1))
        def pos(series,point): return QPointF(rect.left()+(float(point[series.get("x_key","rpm")])-xmin)/(xmax-xmin)*rect.width(),rect.bottom()-(float(point["value"])-ymin)/(ymax-ymin)*rect.height())
        painter.setFont(QFont("Segoe UI",8));painter.setPen(QColor("#9fb3c8"))
        for tick in self.y_ticks:
            y=rect.bottom()-(tick-ymin)/(ymax-ymin)*rect.height()
            label=format_number(tick,5)
            painter.drawText(2,round(y)-7,68,14,Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignVCenter,label)
        painter.save();painter.setClipRect(rect.adjusted(-1,-1,1,1))
        for si,series in enumerate(self.series):
            baseline=series.get("role")=="baseline"
            pen=QPen(QColor("#f6bd60" if baseline else self.COLORS[si%len(self.COLORS)]),2,
                     Qt.PenStyle.DashLine if baseline else Qt.PenStyle.SolidLine); painter.setPen(pen)
            previous=None
            for index,point in enumerate(series.get("points",[])):
                if not self._finite(series,point): previous=None; continue
                current=pos(series,point)
                if previous is not None and series.get("connect",True):painter.drawLine(previous,current)
                if index % max(1,len(series.get('points',[]))//35)==0:
                    painter.setBrush(QColor(self.COLORS[si%len(self.COLORS)]));painter.drawEllipse(current,2.5,2.5)
                if self._selection_key==(id(series),index):painter.drawEllipse(current,7,7)
                previous=current
        painter.restore()
        painter.setFont(QFont("Segoe UI",9));painter.setPen(QColor("#cad8e7"))
        painter.drawText(rect.left(),rect.bottom()+26,f"{xlabel}  {format_number(xmin)} — {format_number(xmax)}")
        if missing:painter.drawText(rect.left(),rect.bottom()+38,"Los puntos sin valor se omiten; la curva no se conecta ni se interpola.")
        painter.drawText(6,rect.top()+12,self.series[0].get("unit","") if self.series else "")
        painter.end()
    def mousePressEvent(self,event):
        if event.button()==Qt.MouseButton.MiddleButton:
            self._drag=event.position();return
        if event.button()!=Qt.MouseButton.LeftButton:return
        self.setFocus()
        rect=self.rect().adjusted(76,56,-18,-64); allp=self._points()
        if not allp:return
        xmin,xmax,ymin,ymax=self._axis_ranges(allp)
        near=None;distance=1e9
        for s,i,p in allp:
            x=rect.left()+(float(p[s.get("x_key","rpm")])-xmin)/(xmax-xmin)*rect.width();y=rect.bottom()-(float(p["value"])-ymin)/(ymax-ymin)*rect.height()
            d=(event.position().x()-x)**2+(event.position().y()-y)**2
            if d<distance:near=(s,i,p);distance=d
        if near and distance<400:
            self._selection_key=(id(near[0]),near[1]);self.selected=(near[0].get("name"),near[1]);self.pointSelected.emit(near[2]);self.update()

    @staticmethod
    def _finite(series,point):
        try:return math.isfinite(float(point['value'])) and math.isfinite(float(point[series.get('x_key','rpm')]))
        except (ValueError,TypeError,KeyError):return False

    def resizeEvent(self,event):
        self.tools.setGeometry(0,0,self.width(),28)
        self.readout.setGeometry(6,max(0,self.height()-24),max(0,self.width()-12),22)
        super().resizeEvent(event)

    def reset_view(self,*_):
        self._viewport=None;self.update()

    def zoom(self,factor,anchor=None):
        bounds=self._axis_ranges(self._points())
        if not bounds:return
        x0,x1,y0,y1=bounds
        ax,ay=anchor or ((x0+x1)/2,(y0+y1)/2)
        candidate=(ax+(x0-ax)*factor,ax+(x1-ax)*factor,ay+(y0-ay)*factor,ay+(y1-ay)*factor)
        if all(math.isfinite(v) for v in candidate) and candidate[1]-candidate[0]>1e-12 and candidate[3]-candidate[2]>1e-12:
            self._viewport=candidate;self.update()

    def wheelEvent(self,event):
        area=self.rect().adjusted(76,56,-18,-64);bounds=self._axis_ranges(self._points())
        if not bounds or not area.contains(event.position().toPoint()):return super().wheelEvent(event)
        x0,x1,y0,y1=bounds
        anchor=(x0+(event.position().x()-area.left())/area.width()*(x1-x0),y1-(event.position().y()-area.top())/area.height()*(y1-y0))
        self.zoom(.8 if event.angleDelta().y()>0 else 1.25,anchor);event.accept()

    def mouseMoveEvent(self,event):
        if self._drag is None:return super().mouseMoveEvent(event)
        bounds=self._axis_ranges(self._points())
        if not bounds:return
        area=self.rect().adjusted(76,56,-18,-64);x0,x1,y0,y1=bounds
        dx=(event.position().x()-self._drag.x())/max(1,area.width())*(x1-x0)
        dy=(event.position().y()-self._drag.y())/max(1,area.height())*(y1-y0)
        self._viewport=(x0-dx,x1-dx,y0+dy,y1+dy);self._drag=event.position();self.update()

    def mouseReleaseEvent(self,event):
        self._drag=None;super().mouseReleaseEvent(event)

    def keyPressEvent(self,event):
        key=event.key()
        if key==Qt.Key.Key_Home:self.reset_view();return
        if key in (Qt.Key.Key_Plus,Qt.Key.Key_Equal):self.zoom(.7);return
        if key==Qt.Key.Key_Minus:self.zoom(1/.7);return
        if key in (Qt.Key.Key_Left,Qt.Key.Key_Right):
            points=self._points()
            if not points:return
            current=next((n for n,(s,i,p) in enumerate(points) if self._selection_key==(id(s),i)), -1 if key==Qt.Key.Key_Right else 0)
            s,i,p=points[(current+(1 if key==Qt.Key.Key_Right else -1))%len(points)]
            self._selection_key=(id(s),i);self.selected=(s.get('name'),i);self.pointSelected.emit(p);self.update();return
        super().keyPressEvent(event)

    def _inspect_selected(self,point):
        series=next((s for s in self.series if id(s)==(self._selection_key or (None,))[0]),{})
        key=series.get('x_key','rpm');label=series.get('x_label','RPM')
        status=point.get('reason') or point.get('status') or point.get('classification') or ''
        self.readout.setText(f"{series.get('name','')} · {label}: {point.get(key)} · {point.get('value')} {series.get('unit','')} · {status}")
        self.readout.setToolTip(self.readout.text());self.setAccessibleDescription(self.readout.text())

    def sample_rows(self):
        return [(str(s.get('name','')),str(s.get('x_label','RPM')),p.get(s.get('x_key','rpm')),p.get('value'),s.get('unit',''),p.get('reason') or p.get('status') or p.get('classification') or '',p)
                for s in self.series for p in s.get('points',[])]

    def show_samples(self,*_):
        dialog=QDialog(self);dialog.setWindowTitle('Muestras originales · sin interpolación');dialog.resize(850,450)
        layout=QVBoxLayout(dialog);layout.addWidget(QLabel('Valores recibidos del resultado; vacío significa ausente. La selección no modifica su calificación.'))
        rows=self.sample_rows();table=QTableWidget(len(rows),6);table.setHorizontalHeaderLabels(['Serie','Eje X','X','Valor','Unidad','Estado / motivo'])
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers);table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        for r,row in enumerate(rows):
            for c,value in enumerate(row[:6]):table.setItem(r,c,QTableWidgetItem('' if value is None else str(value)))
        layout.addWidget(table);dialog.exec()

    def export_samples(self,*_):
        path,_=QFileDialog.getSaveFileName(self,'Exportar muestras originales','','CSV (*.csv)')
        if not path:return
        try:self.write_samples(path)
        except (OSError,ValueError) as exc:QMessageBox.warning(self,'No se pudo exportar',str(exc))

    def write_samples(self,path):
        import csv,json,os,tempfile
        from pathlib import Path
        target=Path(path)
        fd,temporary=tempfile.mkstemp(prefix=target.name+'.',suffix='.tmp',dir=target.parent)
        try:
            with os.fdopen(fd,'w',encoding='utf-8-sig',newline='') as stream:
                writer=csv.writer(stream);writer.writerow(['series','x_label','x','value','unit','status_or_reason','original_sample_json'])
                for row in self.sample_rows():writer.writerow([*row[:6],json.dumps(row[6],ensure_ascii=False,sort_keys=True,allow_nan=False)])
            os.replace(temporary,target)
        finally:
            Path(temporary).unlink(missing_ok=True)

    def export_image(self,*_):
        path,_=QFileDialog.getSaveFileName(self,'Exportar vista del gráfico','','PNG (*.png)')
        if path and not self.grab().save(path,'PNG'):QMessageBox.warning(self,'No se pudo exportar','No se pudo escribir la imagen.')

    def sizeHint(self):return QSize(650,320)

    def minimumSizeHint(self):return QSize(350,180)

    def show_expanded(self,*_):
        from copy import deepcopy
        snapshot=deepcopy(self.series)
        dialog=QDialog(self);dialog.setWindowTitle('Explorar gráfico · instantánea sin interpolación');dialog.resize(1050,650)
        screen=QApplication.primaryScreen()
        if screen:
            area=screen.availableGeometry();dialog.resize(min(1050,area.width()-40),min(650,area.height()-60))
        root=QVBoxLayout(dialog);label=QLabel('Instantánea de las muestras al abrir. Las unidades y calificaciones se conservan. Flechas: cursor · rueda: zoom · botón central: desplazar.');label.setWordWrap(True);root.addWidget(label)
        plot=CurvePlot(dialog,expanded=True);plot.set_series(snapshot,y_scale_mode=self.y_scale_mode);plot._viewport=self._viewport;root.addWidget(plot,1)
        def selected(point):
            if self.series!=snapshot:return
            series_index=next((i for i,s in enumerate(plot.series) if id(s)==plot._selection_key[0]),None)
            if series_index is None:return
            index=plot._selection_key[1];series=self.series[series_index];self._selection_key=(id(series),index);self.selected=(series.get('name'),index);self.pointSelected.emit(series['points'][index]);self.update()
        plot.pointSelected.connect(selected);dialog.exec()
        if self.series==snapshot:self._viewport=plot._viewport;self.update()
