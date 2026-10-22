"""Dual-axis brake power/torque view backed by validated result rows."""
from __future__ import annotations

import csv
import json
import math

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (QCheckBox, QComboBox, QFileDialog, QGroupBox,
    QHBoxLayout, QLabel, QMessageBox, QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QVBoxLayout, QWidget)

from ..power_curve import build_curve_series, exact_rpm_differences, peak_points


class PowerTorquePlot(QWidget):
    pointSelected = Signal(object)
    COLORS = ("#43c5f5", "#f59e0b", "#a78bfa", "#34d399", "#fb7185")

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(270)
        self.series = []
        self.show_power = True
        self.show_torque = True
        self.power_unit = "HP"

    def set_series(self, series, *, power_unit="HP", show_power=True, show_torque=True):
        self.series = list(series)
        self.power_unit = power_unit
        self.show_power = bool(show_power)
        self.show_torque = bool(show_torque)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor("#101a28"))
        rect = self.rect().adjusted(78, 46, -78, -46)
        points = [point for curve in self.series for point in curve.get("points", [])]
        rpms = [float(point["rpm"]) for point in points if point.get("rpm") is not None]
        powers = [point["power"] for point in points if point.get("power") is not None] if self.show_power else []
        torques = [point["torque"] for point in points if point.get("torque") is not None] if self.show_torque else []
        painter.setPen(QPen(QColor("#34475c"), 1))
        for index in range(5):
            y = rect.top() + index * rect.height() / 4
            painter.drawLine(round(rect.left()), round(y), round(rect.right()), round(y))
        painter.setPen(QPen(QColor("#8ba0b8"), 1))
        painter.drawLine(rect.left(), rect.top(), rect.left(), rect.bottom())
        painter.drawLine(rect.left(), rect.bottom(), rect.right(), rect.bottom())
        painter.drawLine(rect.right(), rect.top(), rect.right(), rect.bottom())
        if not rpms or (not powers and not torques):
            painter.setPen(QColor("#cad8e7"))
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter,
                "No hay valores definidos de potencia o torque para graficar.\n"
                "Los puntos fallidos o no periódicos quedan como huecos.")
            painter.end()
            return
        xmin, xmax = min(rpms), max(rpms)
        if xmin == xmax:
            xmax = xmin + 1

        def bounds(values):
            if not values:
                return None
            low, high = min(values), max(values)
            margin = (high - low) * .08 if high != low else max(abs(low) * .08, 1.0)
            low, high = low - margin, high + margin
            if low >= 0:
                low = 0.0
            return low, high

        power_bounds, torque_bounds = bounds(powers), bounds(torques)
        for values, axis_bounds, side in ((powers, power_bounds, "left"), (torques, torque_bounds, "right")):
            if axis_bounds is None:
                continue
            low, high = axis_bounds
            for index in range(5):
                value = high - index * (high - low) / 4
                y = rect.top() + index * rect.height() / 4
                text = f"{value:.4g}"
                if side == "left":
                    painter.drawText(QRectF(0, y - 9, rect.left() - 9, 18), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, text)
                else:
                    painter.drawText(QRectF(rect.right() + 9, y - 9, self.width() - rect.right() - 9, 18), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, text)

        def map_point(rpm, value, axis_bounds):
            low, high = axis_bounds
            return QPointF(rect.left() + (float(rpm) - xmin) / (xmax - xmin) * rect.width(),
                           rect.bottom() - (float(value) - low) / (high - low) * rect.height())

        for curve_index, curve in enumerate(self.series):
            color = QColor(self.COLORS[curve_index % len(self.COLORS)])
            for metric, enabled, axis_bounds, style in (
                    ("power", self.show_power, power_bounds, Qt.PenStyle.SolidLine),
                    ("torque", self.show_torque, torque_bounds, Qt.PenStyle.DashLine)):
                if not enabled or axis_bounds is None:
                    continue
                previous = None
                for point in curve.get("points", []):
                    value = point.get(metric)
                    if value is None:
                        previous = None
                        continue
                    current = map_point(point["rpm"], value, axis_bounds)
                    exploratory=point.get('exploratory',False)
                    painter.setPen(QPen(color,2,Qt.PenStyle.DotLine if exploratory else style))
                    if previous is not None and previous[1]==exploratory:
                        painter.drawLine(previous[0], current)
                    painter.setBrush(Qt.BrushStyle.NoBrush if exploratory else color)
                    if metric == "power":
                        painter.drawEllipse(current, 3.5, 3.5)
                    else:
                        painter.drawRect(QRectF(current.x() - 3, current.y() - 3, 6, 6))
                    previous = (current,exploratory)

        painter.setPen(QColor("#cad8e7"))
        painter.drawText(QRectF(0, 2, self.width(), 20), Qt.AlignmentFlag.AlignCenter, "○ Potencia · □ Torque · punteado/hueco: EXPLORATORIO no periódico · lleno: valor periódico declarado")
        legend_x = rect.left()
        for index, curve in enumerate(self.series):
            color = QColor(self.COLORS[index % len(self.COLORS)])
            painter.setPen(QPen(color, 3))
            painter.drawLine(round(legend_x), round(rect.top() - 5), round(legend_x + 16), round(rect.top() - 5))
            painter.setPen(QColor("#cad8e7"))
            painter.drawText(QRectF(legend_x + 20, rect.top() - 13, 140, 18),
                             Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                             curve["name"][:22])
            legend_x += min(170, max(75, 24 + len(curve["name"]) * 7))
        for rpm in sorted(set(rpms)):
            x=rect.left()+(rpm-xmin)/(xmax-xmin)*rect.width()
            painter.drawLine(round(x),round(rect.bottom()),round(x),round(rect.bottom()+4))
            painter.drawText(QRectF(x-35,rect.bottom()+3,70,16),Qt.AlignmentFlag.AlignCenter,f'{rpm:g}')
        painter.drawText(QRectF(0, rect.bottom() + 23, self.width(), 18), Qt.AlignmentFlag.AlignCenter,
                         f"RPM  {xmin:g} — {max(rpms):g}  ·  potencia: {self.power_unit}  ·  torque: N·m")
        if power_bounds:
            painter.drawText(QRectF(2, rect.top() - 19, rect.left() - 4, 18), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, self.power_unit)
        if torque_bounds:
            painter.drawText(QRectF(rect.right() + 4, rect.top() - 19, self.width() - rect.right() - 4, 18), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, "N·m")
        painter.end()


class PowerCurvePanel(QGroupBox):
    pointSelected = Signal(object)

    def __init__(self, parent=None):
        super().__init__("Curvas de rendimiento", parent)
        self.dataset = None
        self.curves = []
        self.rows = []
        layout = QVBoxLayout(self)
        controls = QHBoxLayout()
        self.power_toggle = QCheckBox("Potencia")
        self.power_toggle.setChecked(True)
        self.torque_toggle = QCheckBox("Torque")
        self.torque_toggle.setChecked(True)
        self.unit_selector = QComboBox()
        for unit in ("HP", "kW", "CV"):
            self.unit_selector.addItem(unit, unit)
        controls.addWidget(self.power_toggle)
        controls.addWidget(self.unit_selector)
        controls.addWidget(self.torque_toggle)
        self.exploratory_toggle=QCheckBox("Mostrar transitorios · EXPLORATORIO")
        self.exploratory_toggle.setChecked(True);controls.addWidget(self.exploratory_toggle)
        controls.addStretch(1)
        self.export_button = QPushButton("Exportar curva CSV…")
        self.export_button.clicked.connect(self.choose_export)
        controls.addWidget(self.export_button)
        layout.addLayout(controls)
        self.provenance = QLabel("Cargá corridas auditadas o un reporte de barrido para ver valores disponibles.")
        self.provenance.setWordWrap(True)
        layout.addWidget(self.provenance)
        self.plot = PowerTorquePlot()
        layout.addWidget(self.plot)
        self.peaks = QLabel("Potencia máxima: —    Torque máximo: —")
        self.peaks.setWordWrap(True)
        layout.addWidget(self.peaks)
        self.compare_label = QLabel("La comparación usa sólo RPM comunes exactos; no interpola puntos.")
        self.compare_label.setWordWrap(True)
        layout.addWidget(self.compare_label)
        self.stability_notice=QLabel('Seleccioná un punto para separar periodicidad global, variación observada y variables pendientes.')
        self.stability_notice.setWordWrap(True);layout.addWidget(self.stability_notice)
        self.comparison = QTableWidget(0, 5)
        self.comparison.setHorizontalHeaderLabels(["RPM", "Δ Potencia", "Δ Torque", "Estado", "Advertencia"])
        self.comparison.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.comparison.horizontalHeader().setStretchLastSection(True)
        self.comparison.setMaximumHeight(155)
        layout.addWidget(self.comparison)
        self.points = QTableWidget(0, 9)
        self.points.setHorizontalHeaderLabels(["Variante / serie", "RPM", "Clasificación", "Periodicidad", "Potencia", "Torque", "Estado", "Tiempo (s)", "Variación últimos ciclos"])
        self.points.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.points.horizontalHeader().setStretchLastSection(True)
        self.points.setMaximumHeight(210)
        self.points.itemSelectionChanged.connect(self._selected_point)
        layout.addWidget(self.points)
        self.power_toggle.toggled.connect(self.refresh)
        self.torque_toggle.toggled.connect(self.refresh)
        self.unit_selector.currentIndexChanged.connect(self.refresh)
        self.exploratory_toggle.toggled.connect(self.refresh)

    def set_dataset(self, dataset, selected_variants):
        self.dataset = dataset
        self.selected_variants = set(selected_variants or ())
        self.refresh()

    def refresh(self, *_):
        if not self.dataset:
            self.curves = []
            self.rows = []
            self.plot.set_series([], power_unit=self.unit_selector.currentData())
            self.points.setRowCount(0)
            self.comparison.setRowCount(0)
            self.peaks.setText("Potencia máxima: —    Torque máximo: —")
            return
        unit = self.unit_selector.currentData()
        self.curves = build_curve_series(self.dataset, self.selected_variants, power_unit=unit,
            include_exploratory=self.exploratory_toggle.isChecked())
        self.plot.set_series(self.curves, power_unit=unit,
            show_power=self.power_toggle.isChecked(), show_torque=self.torque_toggle.isChecked())
        self.rows = [point for curve in self.curves for point in curve["points"]]
        self.provenance.setText(
            f"{self.dataset.get('provenance', 'sin provenance')} · "
            f"validación experimental {self.dataset.get('experimental_validation', 'NOT_REPORTED')} · "
            "los puntos sin valor no se conectan ni se interpolan.")
        if any(row.get('mode')=='ENGINEERING_EXPLORATORY' for row in self.dataset.get('points',[])):
            self.provenance.setText(self.provenance.text()+" Misma cantidad de celdas no demuestra independencia espacial; no atribuir ganancias definitivas al escape.")
        self._refresh_peaks()
        self._refresh_comparison()
        self._refresh_table(unit)

    def _refresh_peaks(self):
        power, torque = peak_points(self.curves, "power"), peak_points(self.curves, "torque")
        def describe(label, values, unit):
            if not values:
                return f"{label}: sin valores definidos"
            return " · ".join(f"{row['series']} {row['value']:.4g} {unit} @ {row['rpm']:g} RPM" for row in values)
        self.peaks.setText(describe("Potencia máxima", power, self.unit_selector.currentData()) +
                           "    " + describe("Torque máximo", torque, "N·m")+
                           (" · Máximos de estimaciones exploratorias; no prestaciones definitivas" if any(p.get('exploratory') for c in self.curves for p in c['points']) else ""))

    def _refresh_comparison(self):
        deltas = exact_rpm_differences(self.curves)
        self.comparison.setRowCount(len(deltas))
        if len(self.curves) >= 2:
            self.compare_label.setText(f"{self.curves[0]['name']} → {self.curves[1]['name']} · sólo RPM comunes exactos; sin interpolación.")
        else:
            self.compare_label.setText("Seleccioná dos series para comparar; sólo se usan RPM comunes exactos y no se interpola.")
        power_unit = self.unit_selector.currentData()
        for index, row in enumerate(deltas):
            power = "—" if row["power_delta"] is None else f"{row['power_delta']:+.4g} {power_unit}"
            torque = "—" if row["torque_delta"] is None else f"{row['torque_delta']:+.4g} N·m"
            state = "EXPLORATORIO" if row.get('exploratory') else "COMPARABLE" if row["compatible"] else "INCOMPATIBLE"
            warning = ", ".join(row["warnings"]) or ("Valores indefinidos en uno o ambos puntos" if row["power_delta"] is None and row["torque_delta"] is None else "")
            for column, value in enumerate((f"{row['rpm']:g}", power, torque, state, warning)):
                self.comparison.setItem(index, column, QTableWidgetItem(value))

    def _refresh_table(self, unit):
        self.points.setRowCount(len(self.rows))
        for index, point in enumerate(self.rows):
            row = point["row"]
            power = "—" if point["power"] is None else f"{point['power']:.5g} {unit}"
            torque = "—" if point["torque"] is None else f"{point['torque']:.5g} N·m"
            statuses = []
            if point["power"] is None:
                statuses.append(str(point["power_reason"] or point["power_status"]))
            if point["torque"] is None:
                statuses.append(str(point["torque_reason"] or point["torque_status"]))
            status = "EXPLORATORIO · no periódico" if point.get('exploratory') else "DEFINIDO" if not statuses else " · ".join(statuses)
            observed=row.get('stability_observed',{})
            stability=(f"ΔW {observed['work_range_J']:.3g} J; Δaire {observed['trapped_air_range_mg']:.3g} mg; no cota de error" if observed else 'No informada')
            values = (row.get("variant_id", "—"), f"{point['rpm']:g}",
                      str(point.get("classification") or "—"),
                      str(point.get("periodicity") or "NOT_REPORTED"), power, torque, status,
                      f"{row['elapsed_seconds']:.2f}" if row.get('elapsed_seconds') is not None else '—',stability)
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setData(Qt.ItemDataRole.UserRole, row)
                item.setToolTip("\n".join((f"Power: {point['power_status']} · {point['power_reason'] or ''}",
                    f"Torque: {point['torque_status']} · {point['torque_reason'] or ''}",
                    f"Resultado SHA-256: {row.get('result_sha256')}",
                    f"Configuración SHA-256: {row.get('point_configuration_sha256')}",
                    f"Implementación SHA-256: {row.get('implementation_identity_sha256')}",
                    f"Solver SHA-256: {row.get('solver_identity_sha256')}",
                    f"Producer SHA-256: {row.get('producer_sha256')}",
                    f"Fuel ID: {row.get('fuel_id')}",
                    f"Mechanical loss SHA-256: {row.get('mechanical_loss_model_sha256')}",
                    f"Mesh resolution: {row.get('mesh_resolution')}",
                    f"Tiempo: {row.get('elapsed_seconds')} s",
                    f"Estabilidad observada (no incertidumbre estacionaria): {row.get('stability_observed')}")))
                self.points.setItem(index, column, item)

    def _selected_point(self):
        row = self.points.currentRow()
        if row >= 0 and self.points.item(row, 0):
            value = self.points.item(row, 0).data(Qt.ItemDataRole.UserRole)
            if value:
                observed=value.get('stability_observed',{})
                if observed:
                    regions=observed['regions']
                    self.stability_notice.setText(f"Periodicidad global: {value.get('periodicity')}. "
                        f"Ciclos {observed['window_cycles']}: rango W {observed['work_range_J']:.4g} J; "
                        f"rango aire atrapado {observed['trapped_air_range_mg']:.4g} mg. "
                        f"Indicadores pendientes: cilindro {regions['cylinder']['failed']}, escape {regions['exhaust']['failed']}, "
                        f"inventario de especies {regions['global_species']['failed']}. "
                        "La variación observada NO es una cota de incertidumbre estacionaria.")
                self.pointSelected.emit(value)

    def choose_export(self):
        if not self.rows:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Exportar curvas", "dino-curva-potencia-torque.csv", "CSV (*.csv)")
        if path:
            try:
                self.export_csv(path)
            except OSError as exc:
                QMessageBox.warning(self, "Error de escritura", str(exc))

    def export_csv(self, path):
        unit = self.unit_selector.currentData()
        with open(path, "w", encoding="utf-8-sig", newline="") as stream:
            writer = csv.writer(stream)
            writer.writerow(["variant_or_series", "rpm", "classification", "periodicity",
                f"brake_power_{unit}", "brake_power_status", "brake_power_reason",
                "brake_torque_Nm", "brake_torque_status", "brake_torque_reason",
                "result_sha256", "point_configuration_sha256", "implementation_identity_sha256",
                "solver_identity_sha256", "producer_sha256", "fuel_id",
                "mechanical_loss_model_sha256", "periodicity_contract", "mesh_resolution", "exploratory_transient", "elapsed_seconds", "observed_stability_not_stationary_uncertainty"])
            for point in self.rows:
                row = point["row"]
                writer.writerow([row.get("variant_id"), point["rpm"], row.get("classification"),
                    point.get("periodicity"), point["power"], point["power_status"], point["power_reason"],
                    point["torque"], point["torque_status"], point["torque_reason"],
                    row.get("result_sha256"), row.get("point_configuration_sha256"),
                    row.get("implementation_identity_sha256"), row.get("solver_identity_sha256"),
                    row.get("producer_sha256"), row.get("fuel_id"),
                    row.get("mechanical_loss_model_sha256"), json.dumps(row.get("periodicity_contract"), ensure_ascii=False),
                    json.dumps(row.get("mesh_resolution"), ensure_ascii=False),point.get('exploratory',False),
                    row.get('elapsed_seconds'),json.dumps(row.get('stability_observed'),ensure_ascii=False)])
