"""Bounded 4T 0D curve queue with persistence, budget, cancel and resume."""
from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import tempfile
import time

from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtWidgets import (QComboBox, QDialog, QDialogButtonBox, QFileDialog,
                               QFormLayout, QHBoxLayout, QLabel, QLineEdit,
                               QMessageBox, QPushButton, QSpinBox, QTableWidget,
                               QTableWidgetItem, QVBoxLayout)

from ..project import ProjectError
from ..rpm_domain import validate_rpm
from .four_stroke_curve import FourStrokeCurveExecution, FourStrokeCurveRunError
from .preferences import default_artifact_root

SCHEMA = "DINO_4T_BATCH_QUEUE_V1"
MAX_ITEMS = 20
MAX_TOTAL_POINTS = 100
STATUSES = {"PENDING", "RUNNING", "DONE", "FAILED", "CANCELLED", "SKIPPED_BUDGET"}


class BatchQueueError(ValueError):
    pass


def _normalise_curve(rpms) -> list[int]:
    values = list(rpms)
    if not 2 <= len(values) <= 5:
        raise BatchQueueError("Cada curva requiere entre 2 y 5 RPM.")
    if any(type(value) is not int for value in values):
        raise BatchQueueError("Los RPM deben ser enteros.")
    for value in values:
        validate_rpm(value, "4T")
    if any(b <= a for a, b in zip(values, values[1:])):
        raise BatchQueueError("Los RPM deben ser ascendentes.")
    return values


class FourStrokeBatchQueue(QObject):
    changed = Signal()
    finished = Signal(dict)
    itemChanged = Signal(int)

    def __init__(self, context, path=None, parent=None, execution_factory=None):
        super().__init__(parent)
        self.context = context
        self.path = Path(path) if path is not None else None
        self.items: list[dict] = []
        self.budget_seconds = 600
        self.state = "IDLE"
        self._execution = None
        self._factory = execution_factory or (lambda: FourStrokeCurveExecution(context, self))
        self._started_at = None
        self._current = None
        self._cancelled = False
        self._budget_timer = QTimer(self)
        self._budget_timer.setSingleShot(True)
        self._budget_timer.timeout.connect(self._budget_expired)

    def to_dict(self) -> dict:
        return {"schema": SCHEMA, "state": self.state,
                "budget_seconds": int(self.budget_seconds), "items": self.items}

    def load_dict(self, data: dict) -> None:
        if not isinstance(data, dict) or data.get("schema") != SCHEMA:
            raise BatchQueueError("cola 4T no reconocida")
        budget = data.get("budget_seconds", 600)
        if type(budget) is not int or budget <= 0:
            raise BatchQueueError("presupuesto de cola inválido")
        items = data.get("items")
        if not isinstance(items, list) or len(items) > MAX_ITEMS:
            raise BatchQueueError("lista de cola inválida")
        checked = []
        total = 0
        for item in items:
            if not isinstance(item, dict) or set(item) != {"kind", "rpms", "status", "series_path", "error"}:
                raise BatchQueueError("ítem de cola inválido")
            if item["kind"] != "curve":
                raise BatchQueueError("tipo de ítem de cola no admitido")
            rpms = _normalise_curve(item["rpms"])
            total += len(rpms)
            if item["status"] not in STATUSES:
                raise BatchQueueError("estado de ítem de cola inválido")
            checked.append({"kind": "curve", "rpms": rpms, "status": item["status"],
                            "series_path": item["series_path"], "error": item["error"]})
        if total > MAX_TOTAL_POINTS:
            raise BatchQueueError("la cola excede el número máximo de puntos")
        self.items = checked
        self.budget_seconds = budget
        self.state = data.get("state", "IDLE")
        if self.state == "RUNNING":
            self.state = "IDLE"
        self.changed.emit()

    def save(self, path=None) -> Path:
        target = Path(path) if path is not None else self.path
        if target is None:
            target = default_artifact_root() / "dino-4t-batches" / (
                datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S") + "-cola.json")
        self.path = target
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = (json.dumps(self.to_dict(), sort_keys=True, indent=2,
                              ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")
        fd, tmp = tempfile.mkstemp(prefix=target.name + ".", suffix=".tmp", dir=target.parent)
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(payload); stream.flush(); os.fsync(stream.fileno())
            os.replace(tmp, target)
        finally:
            try:
                os.unlink(tmp)
            except FileNotFoundError:
                pass
        return target

    @classmethod
    def load(cls, path, context, parent=None, execution_factory=None):
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        queue = cls(context, path=path, parent=parent, execution_factory=execution_factory)
        queue.load_dict(data)
        return queue

    def add_curve(self, rpms) -> int:
        if self.state == "RUNNING":
            raise BatchQueueError("No se edita la cola durante una ejecución.")
        if len(self.items) >= MAX_ITEMS:
            raise BatchQueueError("La cola alcanzó el máximo de curvas.")
        rpms = _normalise_curve(rpms)
        if sum(len(item["rpms"]) for item in self.items) + len(rpms) > MAX_TOTAL_POINTS:
            raise BatchQueueError("La cola excede el máximo de puntos.")
        self.items.append({"kind": "curve", "rpms": rpms, "status": "PENDING",
                           "series_path": None, "error": None})
        self.save()
        self.changed.emit()
        return len(self.items) - 1

    def remove(self, index: int) -> None:
        if self.state == "RUNNING":
            raise BatchQueueError("No se edita la cola durante una ejecución.")
        if index < 0 or index >= len(self.items):
            raise IndexError(index)
        del self.items[index]
        self.save(); self.changed.emit()

    def reset_incomplete(self) -> None:
        for item in self.items:
            if item["status"] in {"FAILED", "CANCELLED", "SKIPPED_BUDGET", "RUNNING"}:
                item["status"] = "PENDING"; item["error"] = None
        self.state = "IDLE"; self.save(); self.changed.emit()

    def start(self, budget_seconds=None) -> None:
        if self.state == "RUNNING":
            raise BatchQueueError("La cola ya está en ejecución.")
        if not self.items:
            raise BatchQueueError("La cola está vacía.")
        if budget_seconds is not None:
            if type(budget_seconds) is not int or budget_seconds <= 0:
                raise BatchQueueError("presupuesto inválido")
            self.budget_seconds = budget_seconds
        for item in self.items:
            if item["status"] in {"RUNNING", "CANCELLED", "SKIPPED_BUDGET"}:
                item["status"] = "PENDING"
        self.state = "RUNNING"; self._cancelled = False; self._started_at = time.monotonic()
        self._current = None; self.save(); self.changed.emit()
        self._start_next()

    def cancel(self) -> None:
        if self.state != "RUNNING":
            return
        self._cancelled = True
        if self._execution is not None and self._execution.running:
            self._execution.cancel()
        elif self._current is None:
            self._finish("CANCELLED")

    def shutdown(self, timeout_ms=10000) -> bool:
        self._budget_timer.stop()
        if self.state == "RUNNING":
            self._cancelled = True
            if self._execution is not None and self._execution.running:
                return self._execution.shutdown(timeout_ms)
            self._finish("CANCELLED")
        return True

    def _remaining(self):
        if self._started_at is None:
            return self.budget_seconds
        return self.budget_seconds - (time.monotonic() - self._started_at)

    def _start_next(self):
        if self._cancelled:
            self._finish("CANCELLED"); return
        if self._remaining() <= 0:
            for item in self.items:
                if item["status"] == "PENDING":
                    item["status"] = "SKIPPED_BUDGET"
            self._finish("BUDGET_EXCEEDED"); return
        item = next((item for item in self.items if item["status"] == "PENDING"), None)
        if item is None:
            self._finish("DONE"); return
        index = self.items.index(item)
        item["status"] = "RUNNING"; item["error"] = None
        self._current = item; self.itemChanged.emit(index); self.save()
        self._execution = self._factory()
        self._execution.finished.connect(self._on_finished)
        self._execution.failed.connect(self._on_failed)
        try:
            self._execution.start(item["rpms"])
        except (BatchQueueError, FourStrokeCurveRunError, ProjectError, ValueError, RuntimeError) as exc:
            item["status"] = "FAILED"; item["error"] = str(exc)
            self._current = None
            self._finish("FAILED")
            return
        self._budget_timer.start(max(1, int(self._remaining() * 1000)))

    def _budget_expired(self):
        if self.state == "RUNNING" and self._remaining() <= 0:
            self._cancelled = True
            if self._execution is not None and self._execution.running:
                self._execution.cancel()
            else:
                self._finish("BUDGET_EXCEEDED")

    def _on_finished(self, result):
        if self._current is None:
            return
        item = self._current; self._current = None
        if result.get("error"):
            item["status"] = "FAILED"; item["error"] = str(result["error"])
            self._finish("FAILED"); return
        if result.get("cancelled"):
            item["status"] = "CANCELLED"
            self._finish("BUDGET_EXCEEDED" if self._remaining() <= 0 else "CANCELLED")
            return
        item["status"] = "DONE"
        item["series_path"] = str(result["series"]) if result.get("series") else None
        self.save(); self.changed.emit()
        self._start_next()

    def _on_failed(self, message):
        if self._current is not None:
            self._current["status"] = "FAILED"; self._current["error"] = str(message)
            self._current = None
        self._finish("FAILED")

    def _finish(self, state):
        self._budget_timer.stop()
        self.state = state
        if self._execution is not None:
            self._execution.deleteLater()
            self._execution = None
        self.save(); self.changed.emit()
        self.finished.emit({"state": state, "items": self.items, "path": str(self.path) if self.path else None})


def parse_curve_text(text: str) -> list[int]:
    groups = [group.strip() for group in str(text).split(";") if group.strip()]
    if len(groups) != 1:
        raise BatchQueueError("Ingrese una curva por ítem, separando RPM con comas.")
    return _normalise_curve([int(part.strip()) for part in groups[0].split(",") if part.strip()])


class BatchQueueDialog(QDialog):
    def __init__(self, context, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Cola de curvas 4T 0D")
        self.resize(760, 520)
        self.queue = FourStrokeBatchQueue(context, parent=self)
        layout = QVBoxLayout(self)
        notice = QLabel("Cola acotada de curvas 4T 0D. Cada curva usa 2-5 RPM; "
                        "el presupuesto y la cancelación son límites de ejecución, no validación científica.")
        notice.setWordWrap(True); layout.addWidget(notice)
        form = QFormLayout(); layout.addLayout(form)
        self.input = QLineEdit("2500,3000,3500"); form.addRow("RPM de la curva", self.input)
        self.budget = QSpinBox(); self.budget.setRange(1, 86400); self.budget.setValue(600)
        self.budget.setSuffix(" s"); form.addRow("Presupuesto de cola", self.budget)
        buttons = QHBoxLayout(); layout.addLayout(buttons)
        self.add_button = QPushButton("Agregar curva"); self.add_button.clicked.connect(self.add_curve)
        self.remove_button = QPushButton("Quitar seleccionada"); self.remove_button.clicked.connect(self.remove_item)
        self.open_button = QPushButton("Abrir cola guardada…"); self.open_button.clicked.connect(self.open_saved)
        buttons.addWidget(self.add_button); buttons.addWidget(self.remove_button); buttons.addWidget(self.open_button); buttons.addStretch(1)
        self.start_button = QPushButton("Iniciar cola"); self.start_button.clicked.connect(self.start)
        self.cancel_button = QPushButton("Cancelar"); self.cancel_button.setEnabled(False); self.cancel_button.clicked.connect(self.queue.cancel)
        self.resume_button = QPushButton("Reanudar pendientes"); self.resume_button.clicked.connect(self.resume)
        buttons.addWidget(self.start_button); buttons.addWidget(self.cancel_button); buttons.addWidget(self.resume_button)
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Curva RPM", "Estado", "Serie / error"])
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table, 1)
        self.status = QLabel("Cola vacía."); self.status.setWordWrap(True); layout.addWidget(self.status)
        close = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        close.rejected.connect(self.reject); close.accepted.connect(self.accept); layout.addWidget(close)
        self.queue.changed.connect(self.refresh)
        self.queue.finished.connect(self.on_queue_finished)
        self.refresh()

    def add_curve(self):
        try:
            self.queue.add_curve(parse_curve_text(self.input.text()))
        except (BatchQueueError, ProjectError, ValueError) as exc:
            QMessageBox.warning(self, "Curva no válida", str(exc))
        self.refresh()

    def open_saved(self):
        default = str(default_artifact_root() / "dino-4t-batches")
        path, _ = QFileDialog.getOpenFileName(self, "Abrir cola 4T", default,
                                              "Cola JSON (*.json)")
        if not path:
            return
        try:
            queue = FourStrokeBatchQueue.load(path, self.queue.context, parent=self)
        except (OSError, ValueError, TypeError, KeyError) as exc:
            QMessageBox.warning(self, "No se pudo abrir la cola", str(exc)); return
        self.queue.shutdown()
        try:
            self.queue.changed.disconnect(); self.queue.finished.disconnect()
        except (RuntimeError, TypeError):
            pass
        self.queue = queue
        self.queue.changed.connect(self.refresh)
        self.queue.finished.connect(self.on_queue_finished)
        self.budget.setValue(self.queue.budget_seconds)
        self.refresh()

    def remove_item(self):
        try:
            self.queue.remove(self.table.currentRow())
        except (BatchQueueError, IndexError) as exc:
            QMessageBox.warning(self, "No se pudo quitar", str(exc))
        self.refresh()

    def start(self):
        try:
            self.queue.start(self.budget.value())
            self.cancel_button.setEnabled(True); self.start_button.setEnabled(False)
        except (BatchQueueError, ProjectError, ValueError, RuntimeError) as exc:
            QMessageBox.warning(self, "No se pudo iniciar la cola", str(exc))

    def resume(self):
        self.queue.reset_incomplete(); self.start()

    def on_queue_finished(self, summary):
        self.cancel_button.setEnabled(False); self.start_button.setEnabled(True)
        self.status.setText(f"Cola {summary['state']} � {summary.get('path') or 'sin archivo'}")
        self.refresh()

    def refresh(self):
        self.table.setRowCount(len(self.queue.items))
        for row, item in enumerate(self.queue.items):
            self.table.setItem(row, 0, QTableWidgetItem(", ".join(str(value) for value in item["rpms"])))
            self.table.setItem(row, 1, QTableWidgetItem(item["status"]))
            detail = item.get("series_path") or item.get("error") or ""
            self.table.setItem(row, 2, QTableWidgetItem(detail))
        if self.queue.state == "IDLE" and not self.queue.items:
            self.status.setText("Cola vacía. Agregue curvas para ejecutar.")
        elif self.queue.state != "RUNNING":
            self.status.setText(f"Cola {self.queue.state} � {len(self.queue.items)} ítem(s).")
        self.cancel_button.setEnabled(self.queue.state == "RUNNING")
        self.start_button.setEnabled(self.queue.state != "RUNNING" and bool(self.queue.items))

    def closeEvent(self, event):
        if not self.queue.shutdown():
            QMessageBox.warning(self, "Cola activa", "La ejecución 4T no terminó; cierre cancelado.")
            event.ignore(); return
        super().closeEvent(event)
