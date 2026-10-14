"""Small interactive gap-preserving Qt plot; no scientific interpolation."""
from __future__ import annotations
import math
from PySide6.QtCore import QPointF, Signal, Qt
from PySide6.QtGui import QColor, QPainter, QPen, QFont
from PySide6.QtWidgets import QWidget


class CurvePlot(QWidget):
    pointSelected = Signal(object)
    COLORS=["#43c5f5","#f59e0b","#a78bfa","#34d399","#fb7185"]
    def __init__(self,parent=None):
        super().__init__(parent); self.series=[]; self.selected=None;self.y_scale_mode="include_zero";self.axis_y_bounds=None;self.y_ticks=();self.setMinimumHeight(260); self.setMouseTracking(True)
    def set_series(self,series,*,y_scale_mode="include_zero"):
        if y_scale_mode not in {"include_zero","data_margin"}:raise ValueError("unknown y-axis scale mode")
        self.series=series;self.selected=None;self.y_scale_mode=y_scale_mode;self.update()
    def _points(self):
        return [(s, i, p) for s in self.series for i,p in enumerate(s.get("points",[]))
                if p.get("value") is not None and
                math.isfinite(float(p["value"])) and
                p.get(s.get("x_key","rpm")) is not None and
                math.isfinite(float(p[s.get("x_key","rpm")]))]
    def _axis_ranges(self,allp):
        if not allp:self.axis_y_bounds=None;self.y_ticks=();return None
        xs=[float(p[s.get("x_key","rpm")]) for s,_,p in allp]
        xs.extend(float(p[s.get("x_key","rpm")]) for s,_,p in self._missing_points())
        ys=[float(p["value"]) for _,_,p in allp]
        xmin,xmax=min(xs),max(xs);raw_min,raw_max=min(ys),max(ys)
        if self.y_scale_mode=="data_margin":
            span=raw_max-raw_min
            margin=span*.05 if span>0 else max(abs(raw_min)*.05,1.0)
            ymin,ymax=raw_min-margin,raw_max+margin
        else:ymin,ymax=min(0.0,raw_min),max(0.0,raw_max)
        if xmax==xmin:xmax=xmin+1
        if ymax==ymin:
            margin=max(abs(ymin)*.05,1.0);ymin-=margin;ymax+=margin
        self.axis_y_bounds=(ymin,ymax)
        self.y_ticks=tuple(ymin+(ymax-ymin)*i/4 for i in range(5))
        return xmin,xmax,ymin,ymax
    def _missing_points(self):
        return [(s,i,p) for s in self.series for i,p in enumerate(s.get("points",[]))
                if p.get("value") is None and p.get(s.get("x_key","rpm")) is not None
                and math.isfinite(float(p[s.get("x_key","rpm")]))]
    def paintEvent(self,event):
        painter=QPainter(self); painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(),QColor("#101a28")); rect=self.rect().adjusted(58,18,-18,-40)
        allp=self._points()
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
                for s,_,p in missing:
                    x=rect.left()+(float(p[s.get("x_key","rpm")])-xmin)/(xmax-xmin)*rect.width();y=rect.center().y()
                    painter.setPen(QPen(QColor("#fb7185"),2));painter.drawLine(round(x)-5,round(y)-5,round(x)+5,round(y)+5);painter.drawLine(round(x)-5,round(y)+5,round(x)+5,round(y)-5)
                painter.setPen(QColor("#cad8e7"));painter.drawText(rect,Qt.AlignmentFlag.AlignCenter,"Sin valores numéricos definidos · las × indican puntos no graficables")
                painter.drawText(rect.left(),rect.bottom()+26,f"RPM  {xmin:g} — {xmax:g}")
            else:painter.drawText(rect,Qt.AlignmentFlag.AlignCenter,"Sin valores válidos para graficar")
            painter.end(); return
        xlabel=self.series[0].get("x_label","RPM") if self.series else "RPM"
        xmin,xmax,ymin,ymax=self._axis_ranges(allp)
        def pos(series,point): return QPointF(rect.left()+(float(point[series.get("x_key","rpm")])-xmin)/(xmax-xmin)*rect.width(),rect.bottom()-(float(point["value"])-ymin)/(ymax-ymin)*rect.height())
        painter.setFont(QFont("Segoe UI",8));painter.setPen(QColor("#9fb3c8"))
        for tick in self.y_ticks:
            y=rect.bottom()-(tick-ymin)/(ymax-ymin)*rect.height()
            painter.drawText(2,round(y)-7,52,14,Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignVCenter,f"{tick:g}")
        for si,series in enumerate(self.series):
            pen=QPen(QColor(self.COLORS[si%len(self.COLORS)]),2); painter.setPen(pen)
            previous=None
            for index,point in enumerate(series.get("points",[])):
                if point.get("value") is None: previous=None; continue
                current=pos(series,point)
                if previous is not None:painter.drawLine(previous,current)
                painter.setBrush(QColor(self.COLORS[si%len(self.COLORS)]));painter.drawEllipse(current,3.5,3.5)
                if self.selected==(series.get("name"),index):painter.drawEllipse(current,7,7)
                previous=current
            for _,point_index,point in (entry for entry in missing if entry[0] is series):
                x=rect.left()+(float(point[series.get("x_key","rpm")])-xmin)/(xmax-xmin)*rect.width();y=rect.bottom()
                painter.setPen(QPen(QColor("#fb7185"),2));painter.drawLine(round(x)-5,round(y)-5,round(x)+5,round(y)+5);painter.drawLine(round(x)-5,round(y)+5,round(x)+5,round(y)-5)
        painter.setFont(QFont("Segoe UI",9));painter.setPen(QColor("#cad8e7"))
        painter.drawText(rect.left(),rect.bottom()+26,f"{xlabel}  {xmin:g} — {xmax:g}")
        if missing:painter.drawText(rect.left(),rect.bottom()+38,"× = sin métrica numérica; posición vertical simbólica")
        painter.drawText(6,rect.top()+12,self.series[0].get("unit","") if self.series else "")
        painter.end()
    def mousePressEvent(self,event):
        if event.button()!=Qt.MouseButton.LeftButton:return
        rect=self.rect().adjusted(58,18,-18,-40); allp=self._points()
        if not allp:return
        xmin,xmax,ymin,ymax=self._axis_ranges(allp)
        near=None;distance=1e9
        for s,i,p in allp:
            x=rect.left()+(float(p[s.get("x_key","rpm")])-xmin)/(xmax-xmin)*rect.width();y=rect.bottom()-(float(p["value"])-ymin)/(ymax-ymin)*rect.height()
            d=(event.position().x()-x)**2+(event.position().y()-y)**2
            if d<distance:near=(s,i,p);distance=d
        if near and distance<400:
            self.selected=(near[0].get("name"),near[1]);self.pointSelected.emit(near[2]);self.update()
