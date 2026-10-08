"""Vista Qt especializada: esquema y dos curvas geométricas, sin dependencias."""

import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (QGridLayout, QHBoxLayout, QLabel, QScrollArea,
                               QSlider, QVBoxLayout, QWidget)

from .kinematics import Geometry, calculate_geometry, piston_position


class GeometryPlot(QWidget):
    def __init__(self, title, unit, parent=None):
        super().__init__(parent)
        self.title, self.unit = title, unit
        self.values = ()
        self.end_angle = 360
        self.angle = 0
        self.error = "Datos sin informar."
        self.setMinimumHeight(235)
        self.setAccessibleName(f"{title}, {unit}, según ángulo en grados")

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(QColor("#b4d9f5"))
        p.drawText(QRectF(12, 5, self.width()-24, 25), self.title + f" [{self.unit}]")
        if not self.values:
            p.setPen(QColor("#9eb1c7"))
            p.drawText(QRectF(12, 45, self.width()-24, self.height()-60),
                       Qt.AlignmentFlag.AlignTop | Qt.TextFlag.TextWordWrap, self.error)
            return
        fm = p.fontMetrics()
        peak = max(self.values)
        scale_peak = peak if peak > 0 else 1.0
        def number(v):
            return f"{v:.2f}" if abs(v) < 100000 else f"{v:.2e}"
        margin = max(56, fm.horizontalAdvance(number(peak)) + 12)
        box = QRectF(margin, 56, max(1, self.width()-margin-18), self.height()-108)
        if self.end_angle == 720:
            second = QRectF(box.center().x(), box.top(), box.width()/2, box.height())
            p.fillRect(second, QColor("#14243b"))
        p.setPen(QColor("#6c819b"))
        p.drawLine(box.bottomLeft(), box.bottomRight())
        p.drawLine(box.topLeft(), box.bottomLeft())
        for fraction in (0, .5, 1):
            y = box.bottom() - fraction * box.height()
            p.drawText(QRectF(0, y-10, margin-8, 22), Qt.AlignmentFlag.AlignRight, number(peak*fraction))
        for angle in range(0, self.end_angle+1, 180):
            x = box.left() + angle/self.end_angle*box.width()
            p.drawLine(QPointF(x, box.bottom()), QPointF(x, box.bottom()+4))
            p.drawText(QRectF(x-22, box.bottom()+6, 44, 20), Qt.AlignmentFlag.AlignCenter, str(angle))
        p.drawText(QRectF(box.left(), self.height()-25, box.width(), 22),
                   Qt.AlignmentFlag.AlignCenter, "Ángulo del cigüeñal [°]")
        p.setPen(QColor("#9eb1c7"))
        caption = "PMS 0° / 360° · PMI 180°" if self.end_angle == 360 else "1.ª vuelta 0–360°  |  2.ª vuelta 360–720°"
        p.drawText(QRectF(12, 30, self.width()-24, 20), Qt.AlignmentFlag.AlignCenter, caption)
        curve = QPainterPath()
        for i, value in enumerate(self.values):
            point = QPointF(box.left()+i/self.end_angle*box.width(), box.bottom()-value/scale_peak*box.height())
            if i == 0:
                curve.moveTo(point)
            else:
                curve.lineTo(point)
        p.setPen(QPen(QColor("#69baf0"), 2))
        p.drawPath(curve)
        cursor_x = box.left()+self.angle/self.end_angle*box.width()
        p.setPen(QPen(QColor("#ffbf83"), 1, Qt.PenStyle.DashLine))
        p.drawLine(QPointF(cursor_x, box.top()), QPointF(cursor_x, box.bottom()))


class Mechanism(QWidget):
    def __init__(self):
        super().__init__()
        self.editor=None
        self.data = Geometry(360)
        self.angle = 0
        self.setMinimumHeight(225)
        self.setAccessibleName("Esquema geométrico biela-manivela sin descentrado")

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(QColor("#b4d9f5"))
        p.drawText(12, 23, "Biela-manivela · esquema 2D")
        if not self.data.positions:
            p.setPen(QColor("#9eb1c7"))
            p.drawText(QRectF(12, 48, self.width()-24, self.height()-65),
                       Qt.AlignmentFlag.AlignTop | Qt.TextFlag.TextWordWrap,
                       self.data.errors.get("position", "Datos sin informar."))
            return
        # Normalización previa: nunca sumar L+r en mm potencialmente enormes.
        rod, radius = self.data.rod, self.data.stroke/2
        ratio = radius/rod
        scale = min((self.height()-75)/(1+2*ratio), (self.width()-150)/2)
        origin = QPointF(self.width()/2, 45+(1+ratio)*scale)
        theta = math.radians(self.angle % 360)
        crank = origin + QPointF(ratio*scale*math.sin(theta), -ratio*scale*math.cos(theta))
        position = piston_position(self.data.stroke, rod, self.angle)
        pin = QPointF(origin.x(), origin.y()-(1+ratio-position/rod)*scale)
        top = origin.y()-(1+ratio)*scale
        bottom = top+2*ratio*scale
        p.setPen(QPen(QColor("#40546e"), 1))
        p.drawLine(QPointF(origin.x(), top-5), QPointF(origin.x(), origin.y()+ratio*scale))
        for y, text in ((top, "PMS"), (bottom, "PMI")):
            p.drawLine(QPointF(origin.x()-45, y), QPointF(origin.x()+45, y))
            p.drawText(QPointF(origin.x()+50, y+5), text)
        p.setPen(QPen(QColor("#69baf0"), 4))
        p.drawLine(origin, crank)
        p.setPen(QPen(QColor("#b4d9f5"), 4))
        p.drawLine(crank, pin)
        p.setBrush(QColor("#24415b"))
        p.drawRect(QRectF(pin.x()-26, pin.y()-6, 52, 12))
        for point in (origin, crank, pin):
            p.drawEllipse(point, 4, 4)


class GeometryView(QScrollArea):
    def __init__(self):
        super().__init__()
        self.setWidgetResizable(True)
        self.setFrameShape(QScrollArea.Shape.NoFrame)
        self.editor=None
        self.data = Geometry(360)
        self.body = QWidget()
        layout = QVBoxLayout(self.body)
        layout.setContentsMargins(24, 16, 24, 16)
        title = QLabel("Geometría")
        title.setObjectName("pageTitle")
        layout.addWidget(title)
        notice = QLabel("Un cilindro de geometría común · Esquema geométrico, no CAD ni comprobación de holguras.")
        notice.setWordWrap(True)
        layout.addWidget(notice)
        self.grid = QGridLayout()
        self.grid.setSpacing(16)
        self.mechanism = Mechanism()
        self.position_plot = GeometryPlot("Posición desde PMS", "mm")
        self.volume_plot = GeometryPlot("Volumen del cilindro", "cm³")
        from .ui import Panel
        self.details = Panel('DERIVADOS Y POSICIÓN')
        info = self.details.content
        info.setContentsMargins(12, 12, 12, 12)
        self.project_label = QLabel()
        self.project_label.setTextFormat(Qt.TextFormat.PlainText)
        self.project_label.setWordWrap(True)
        info.addWidget(self.project_label)
        self.summary = QLabel()
        self.summary.setWordWrap(True)
        self.summary.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        info.addWidget(self.summary)
        self.angle_label = QLabel("Ángulo: 0°")
        self.angle_slider = QSlider(Qt.Orientation.Horizontal)
        self.angle_slider.setRange(0, 360)
        self.angle_slider.setPageStep(30)
        self.angle_slider.setAccessibleName("Ángulo del cigüeñal en grados")
        self.angle_label.setBuddy(self.angle_slider)
        info.addWidget(self.angle_label)
        info.addWidget(self.angle_slider)
        self.current = QLabel()
        self.current.setWordWrap(True)
        info.addWidget(self.current)
        self.angle_slider.valueChanged.connect(self._angle_changed)
        layout.addLayout(self.grid)
        layout.addStretch()
        self.setWidget(self.body)
        self._wide = None
        self._arrange()

    def attach_editor(self,editor,derived=None):
        self.editor=editor;self.body.layout().removeItem(self.grid)
        if derived is not None:self.details.content.insertWidget(1,derived)
        self.visual=QWidget();self.visual.setLayout(self.grid)
        self.combined=QGridLayout();self.combined.setSpacing(22)
        self.body.layout().insertLayout(2,self.combined);self._wide=None;self._arrange()

    def _arrange(self):
        if self.editor is not None:
            self.editor_wide=self.viewport().width()>=850
            self.combined.addWidget(self.editor,0,0,Qt.AlignmentFlag.AlignTop)
            self.combined.addWidget(self.visual,0 if self.editor_wide else 1,1 if self.editor_wide else 0)
            self.combined.setColumnStretch(0,2 if self.editor_wide else 1)
            self.combined.setColumnStretch(1,3 if self.editor_wide else 0)
        available=self.viewport().width()-48
        if self.editor is not None and self.editor_wide:available=(available-22)*3/5
        wide = available >= max(600, self.fontMetrics().horizontalAdvance("M")*42)
        if wide == self._wide:
            return
        self._wide = wide
        widgets = (self.mechanism, self.details, self.position_plot, self.volume_plot)
        for widget in widgets:
            self.grid.removeWidget(widget)
        for i, widget in enumerate(widgets):
            self.grid.addWidget(widget, i//2 if wide else i, i%2 if wide else 0)
        self.grid.setColumnStretch(0, 1)
        self.grid.setColumnStretch(1, 1 if wide else 0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "grid"):
            self._arrange()

    def set_inputs(self, values, cycle, errors, name):
        self.data = calculate_geometry(values, cycle, errors)
        self.project_label.setText(name)
        self.mechanism.data = self.data
        self.angle_slider.setMaximum(self.data.end_angle)
        for plot, values, key in ((self.position_plot, self.data.positions, "position"),
                                  (self.volume_plot, self.data.volumes, "volume")):
            plot.values = values
            plot.end_angle = self.data.end_angle
            plot.error = self.data.errors.get(key, "")
            plot.setAccessibleDescription(plot.error or "Curva calculada a partir de la ficha actual.")
        def value(v):
            return "—" if v is None else f"{v:.2f}" if abs(v)<1e6 else f"{v:.3e}"
        summary = (f"Cámara / mínimo: {value(self.data.chamber)} cm³\n"
                   f"Volumen máximo: {value(self.data.maximum)} cm³")
        if self.editor is None:summary += f"\nCilindrada por cilindro: {value(self.data.displacement)} cm³"
        if self.data.errors.get("chamber"):
            summary += "\n" + self.data.errors["chamber"]
        summary += "\nPMS: 0° / 360°" + (" / 720° · PMI: 180° / 540°" if cycle == "4T" else " · PMI: 180°")
        self.summary.setText(summary)
        self._angle_changed()

    def _angle_changed(self):
        angle = self.angle_slider.value()
        self.angle_label.setText(f"Ángulo: {angle}° · " + ("2.ª revolución" if angle>360 else "1.ª revolución"))
        self.mechanism.angle = angle
        self.mechanism.update()
        for plot in (self.position_plot, self.volume_plot):
            plot.angle = angle
            plot.update()
        x = f"{self.data.positions[angle]:.2f}" if self.data.positions else "—"
        v = f"{self.data.volumes[angle]:.2f}" if self.data.volumes else "—"
        self.current.setText(f"Posición: {x} mm · Volumen: {v} cm³")
