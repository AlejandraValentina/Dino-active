"""Vista de resultados 4T 0D; lectura estricta, sin claim predictivo."""
from __future__ import annotations

from PySide6.QtCore import QLineF, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QGroupBox, QFormLayout, QTabWidget)

from ..reference_results import ResultError, load_result
from ..simulation import FOUR_LAYOUT
from .four_stroke_workspace import REFERENCE_BANNER


class FourStrokeCurve(QWidget):
    def __init__(self, title, xlabel, ylabel, parent=None):
        super().__init__(parent)
        self.title = title
        self.xlabel = xlabel
        self.ylabel = ylabel
        self.points = []
        self.setMinimumHeight(240)
        self.setObjectName("fourStrokeCurve")

    def set_points(self, points):
        self.points = list(points)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.fillRect(self.rect(), QColor("#101a28"))
        painter.setPen(QColor("#d8edff"))
        painter.drawText(12, 20, self.title)
        area = self.rect().adjusted(62, 32, -18, -48)
        if not self.points:
            painter.setPen(QColor("#8ba3bd"))
            painter.drawText(area, Qt.AlignmentFlag.AlignCenter, "Sin muestras 4T")
            return
        xs = [point[0] for point in self.points]
        ys = [point[1] for point in self.points]
        xmin, xmax = min(xs), max(xs)
        ymin, ymax = min(ys), max(ys)
        if xmax == xmin:
            xmax = xmin + 1.0
        if ymax == ymin:
            ymax = ymin + 1.0
        painter.setPen(QPen(QColor("#45607a"), 1))
        painter.drawLine(area.left(), area.bottom(), area.right(), area.bottom())
        painter.drawLine(area.left(), area.top(), area.left(), area.bottom())
        painter.setPen(QColor("#8ba3bd"))
        painter.drawText(area.left(), self.rect().bottom() - 18, self.xlabel)
        painter.drawText(8, area.top() + 12, self.ylabel)
        painter.drawText(area.left() - 8, area.bottom() + 18, f"{xmin:.4g}")
        painter.drawText(area.right() - 42, area.bottom() + 18, f"{xmax:.4g}")
        painter.drawText(8, area.top() + 30, f"{ymax:.4g}")
        painter.drawText(8, area.bottom() - 2, f"{ymin:.4g}")
        def screen(point):
            x = area.left() + (point[0] - xmin) / (xmax - xmin) * area.width()
            y = area.bottom() - (point[1] - ymin) / (ymax - ymin) * area.height()
            return x, y
        painter.setPen(QPen(QColor("#6fd3ff"), 2))
        previous = None
        for point in self.points:
            current = screen(point)
            if previous is not None:
                painter.drawLine(QLineF(previous[0], previous[1], current[0], current[1]))
            previous = current


class FourStrokeResultsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.result = None
        self.setObjectName("fourStrokeResults")
        layout = QVBoxLayout(self)
        banner = QLabel(REFERENCE_BANNER)
        banner.setObjectName("fourStrokeResultsBanner")
        banner.setWordWrap(True)
        layout.addWidget(banner)
        self.error = QLabel()
        self.error.setWordWrap(True)
        self.error.setObjectName("fourStrokeResultsError")
        layout.addWidget(self.error)
        summary = QGroupBox("Resumen 4T 0D")
        form = QFormLayout(summary)
        self.status = QLabel("Sin resultado 4T cargado.")
        self.cycles = QLabel("-")
        self.work = QLabel("-")
        self.pmax = QLabel("-")
        self.seconds = QLabel("-")
        self.memory = QLabel("-")
        self.model = QLabel("-")
        for label, widget in (("Estado", self.status), ("Ciclos", self.cycles),
                              ("W_C [J/ciclo]", self.work), ("p_max [kPa]", self.pmax),
                              ("Integración [s]", self.seconds), ("Pico [MiB]", self.memory),
                              ("Modelo", self.model)):
            form.addRow(label, widget)
        layout.addWidget(summary)
        self.tabs = QTabWidget()
        self.pv = FourStrokeCurve("P-V del último ciclo", "V [cm³]", "p [kPa]")
        self.angle = FourStrokeCurve("p-θ del último ciclo", "θ [°]", "p [kPa]")
        self.tabs.addTab(self.pv, "P-V")
        self.tabs.addTab(self.angle, "p-θ")
        layout.addWidget(self.tabs, 1)
        self.notice = QLabel(
            "Resultado 0D de referencia. No es validación experimental ni claim predictivo."
        )
        self.notice.setWordWrap(True)
        layout.addWidget(self.notice)

    def clear_result(self):
        self.result = None
        self.status.setText("Sin resultado 4T cargado.")
        for label in (self.cycles, self.work, self.pmax, self.seconds, self.memory, self.model):
            label.setText("-")
        self.pv.set_points([])
        self.angle.set_points([])
        self.error.clear()

    def load_manifest(self, path) -> bool:
        try:
            result = load_result(path)
        except (ResultError, OSError, ValueError, KeyError, TypeError) as exc:
            self.clear_result()
            self.error.setText(str(exc))
            return False
        self.show_result(result)
        return True

    def show_result(self, result: dict) -> None:
        self.result = result
        self.error.clear()
        status = result.get("status", "desconocido")
        cycles = (result.get("result") or {}).get("cycles") or []
        last = cycles[-1] if cycles else {}
        self.status.setText(str(status))
        self.cycles.setText(str(len(cycles)))
        self.work.setText(self._number(last.get("W_C_J")))
        self.pmax.setText(self._number((last.get("p_max_Pa") or 0) / 1000))
        self.seconds.setText(self._number((result.get("result") or {}).get("seconds")))
        self.memory.setText(self._number((result.get("result") or {}).get("peak_process_MiB")))
        self.model.setText(str((result.get("manifest") or {}).get("model_version", "-")))
        rows = ((result.get("samples") or {}).get("cycles") or [])
        rows = rows[-1] if rows else []
        cylinder = FOUR_LAYOUT.cylinder
        pv, angle = [], []
        for row in rows:
            pressure = row["p_T_Y"][cylinder][0] / 1000
            volume = row["V_m3"][cylinder] * 1e6
            pv.append((volume, pressure))
            angle.append((row["angle_deg"], pressure))
        self.pv.set_points(pv)
        self.angle.set_points(angle)
        if not rows:
            self.status.setText(f"{status} · sin muestras del último ciclo")

    @staticmethod
    def _number(value):
        if value is None:
            return "-"
        try:
            return f"{float(value):.6g}"
        except (TypeError, ValueError):
            return str(value)
