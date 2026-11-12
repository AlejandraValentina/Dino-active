"""Vista de resultados 4T 0D; lectura estricta, sin claim predictivo."""
from __future__ import annotations

from PySide6.QtCore import QLineF, QPointF, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QGroupBox, QFormLayout, QTabWidget)

from ..reference_results import ResultError, load_result
from ..simulation import FOUR_LAYOUT
from .four_stroke_workspace import REFERENCE_BANNER


from .plot import CurvePlot


class FourStrokeCurve(CurvePlot):
    """Presentation adapter for the existing 4T tuple contract."""
    def __init__(self,title,xlabel,ylabel,parent=None):
        super().__init__(parent)
        self.title=title;self.xlabel=xlabel;self.ylabel=ylabel;self.points=[]
        self.connect_points=True;self.setObjectName('fourStrokeCurve')

    def set_points(self,points):
        self.points=list(points)
        self.set_series([dict(name=self.title,x_key='x',x_label=self.xlabel,unit=self.ylabel,
            connect=self.connect_points,points=[dict(x=x,value=y) for x,y in self.points])],y_scale_mode='data_margin')


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
