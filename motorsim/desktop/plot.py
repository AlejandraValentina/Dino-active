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
        super().__init__(parent); self.series=[]; self.selected=None; self.setMinimumHeight(260); self.setMouseTracking(True)
    def set_series(self,series): self.series=series; self.selected=None; self.update()
    def _points(self):
        return [(s, i, p) for s in self.series for i,p in enumerate(s.get("points",[]))
                if p.get("value") is not None and
                math.isfinite(float(p["value"])) and
                p.get(s.get("x_key","rpm")) is not None and
                math.isfinite(float(p[s.get("x_key","rpm")]))]
    def paintEvent(self,event):
        painter=QPainter(self); painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(),QColor("#101a28")); rect=self.rect().adjusted(58,18,-18,-40)
        allp=self._points()
        painter.setPen(QPen(QColor("#34475c"),1))
        for i in range(5):
            y=rect.top()+i*rect.height()/4; painter.drawLine(rect.left(),round(y),rect.right(),round(y))
        painter.setPen(QPen(QColor("#9fb3c8"),1)); painter.drawRect(rect)
        if not allp:
            painter.drawText(rect,Qt.AlignmentFlag.AlignCenter,"Sin valores válidos para graficar")
            painter.end(); return
        xlabel=self.series[0].get("x_label","RPM") if self.series else "RPM"
        xs=[float(p[s.get("x_key","rpm")]) for s,_,p in allp]; ys=[float(p["value"]) for _,_,p in allp]
        xmin,xmax=min(xs),max(xs); ymin,ymax=min(0.0,min(ys)),max(ys)
        if xmax==xmin:xmax=xmin+1
        if ymax==ymin:ymax=ymin+1
        def pos(series,point): return QPointF(rect.left()+(float(point[series.get("x_key","rpm")])-xmin)/(xmax-xmin)*rect.width(),rect.bottom()-(float(point["value"])-ymin)/(ymax-ymin)*rect.height())
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
        painter.setFont(QFont("Segoe UI",9));painter.setPen(QColor("#cad8e7"))
        painter.drawText(rect.left(),rect.bottom()+26,f"{xlabel}  {xmin:g} — {xmax:g}")
        painter.drawText(6,rect.top()+12,self.series[0].get("unit","") if self.series else "")
        painter.end()
    def mousePressEvent(self,event):
        if event.button()!=Qt.MouseButton.LeftButton:return
        rect=self.rect().adjusted(58,18,-18,-40); allp=self._points()
        if not allp:return
        xs=[float(p[s.get("x_key","rpm")]) for s,_,p in allp]; ys=[float(p["value"]) for _,_,p in allp]
        xmin,xmax=min(xs),max(xs);ymin,ymax=min(0.0,min(ys)),max(ys)
        if xmax==xmin:xmax+=1
        if ymax==ymin:ymax+=1
        near=None;distance=1e9
        for s,i,p in allp:
            x=rect.left()+(float(p[s.get("x_key","rpm")])-xmin)/(xmax-xmin)*rect.width();y=rect.bottom()-(float(p["value"])-ymin)/(ymax-ymin)*rect.height()
            d=(event.position().x()-x)**2+(event.position().y()-y)**2
            if d<distance:near=(s,i,p);distance=d
        if near and distance<400:
            self.selected=(near[0].get("name"),near[1]);self.pointSelected.emit(near[2]);self.update()
