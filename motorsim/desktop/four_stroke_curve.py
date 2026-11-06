"""Curva RPM 4T de referencia: barrido QProcess sobre el worker existente."""
from __future__ import annotations

import json
from pathlib import Path
import tempfile

from PySide6.QtCore import QObject, QProcess, QTimer, Signal
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QLineEdit, QPushButton, QTableWidget,
                               QTableWidgetItem, QHeaderView, QProgressBar,
                               QGroupBox, QFormLayout)

from ..four_stroke_project import FourStrokeProjectError
from ..project import ProjectError
from ..reference_results import ResultError, new_output_path, project_inputs
from ..rpm_domain import validate_rpm
from ..runtime import worker_command
from ..sweep import load_sweep, plan_rpms
from .four_stroke_results import FourStrokeCurve
from .four_stroke_workspace import REFERENCE_BANNER


class FourStrokeCurveRunError(RuntimeError):
    pass


class FourStrokeCurveExecution(QObject):
    """Supervisa `reference_run --sweep-input` para un proyecto 4T."""

    started = Signal(object)
    progress = Signal(object)
    finished = Signal(object)
    failed = Signal(str)

    def __init__(self, context, parent=None):
        super().__init__(parent)
        self.context = context
        self._process = None
        self._buffer = b""
        self._stderr = b""
        self._request_path = None
        self._output = None
        self._series_path = None
        self._finished_data = None
        self._last_error = None
        self._cancel_requested = False

    @property
    def running(self) -> bool:
        return self._process is not None

    @property
    def output(self):
        return self._output

    @property
    def series(self):
        return self._series_path

    def _origin(self) -> dict:
        project = self.context.project
        return {
            "kind": "project",
            "project_name": project.name,
            "source_path": str(self.context.path) if self.context.path is not None else None,
            "dirty": bool(self.context.dirty),
        }

    def prepare(self, rpms, output=None):
        try:
            rpms = list(rpms)
            if not 2 <= len(rpms) <= 5:
                raise ProjectError("La curva 4T requiere entre 2 y 5 puntos RPM.")
            for rpm in rpms:
                validate_rpm(rpm, "4T")
            if plan_rpms(rpms[0], rpms[-1], rpms[1] - rpms[0], "4T") != rpms:
                raise ProjectError("Curva 4T: RPM ascendentes y paso exacto.")
            project = self.context.project
            project.validate_for_execution()
            inputs = project_inputs(project.to_project(), self._origin(), rpm=rpms[0])
        except (FourStrokeProjectError, ResultError, ProjectError, ValueError) as exc:
            raise FourStrokeCurveRunError(str(exc)) from exc
        payload = json.dumps({"common_inputs": inputs, "rpms": rpms},
                             sort_keys=True, ensure_ascii=False, allow_nan=False)
        if len(payload.encode("utf-8")) > 16 * 1024 * 1024:
            raise FourStrokeCurveRunError("La solicitud de curva 4T supera 16 MiB.")
        fd, name = tempfile.mkstemp(prefix="dino-4t-curve-", suffix=".json")
        try:
            with open(fd, "w", encoding="utf-8", newline="") as stream:
                stream.write(payload)
        except Exception:
            Path(name).unlink(missing_ok=True)
            raise
        self._request_path = Path(name)
        self._output = Path(output) if output is not None else new_output_path()
        return self._output, self._request_path, rpms

    def start(self, rpms, output=None):
        if self.running:
            raise FourStrokeCurveRunError("Ya hay una curva 4T en curso.")
        target, request, normalized = self.prepare(rpms, output)
        executable, prefix, working_directory = worker_command()
        process = QProcess(self)
        process.setWorkingDirectory(working_directory)
        process.setProgram(executable)
        process.setArguments([*prefix, "--output", str(target), "--control-stdin",
                              "--sweep-input", str(request)])
        process.readyReadStandardOutput.connect(self._read_stdout)
        process.readyReadStandardError.connect(self._read_stderr)
        process.finished.connect(self._on_finished)
        process.errorOccurred.connect(self._on_error)
        self._process = process
        self._buffer = b""
        self._stderr = b""
        self._series_path = None
        self._finished_data = None
        self._last_error = None
        self._cancel_requested = False
        process.start()
        self.started.emit(str(target))
        return target

    def cancel(self):
        if not self.running or self._cancel_requested:
            return
        self._cancel_requested = True
        process = self._process
        process.write(b"cancel\n")
        QTimer.singleShot(3000, lambda: self._kill_if_active(process))

    def _kill_if_active(self, process):
        if self._process is process and process.state() != QProcess.ProcessState.NotRunning:
            process.kill()

    def _read_stderr(self):
        if self._process is None:
            return
        self._stderr += bytes(self._process.readAllStandardError())

    def _read_stdout(self):
        if self._process is None:
            return
        self._buffer += bytes(self._process.readAllStandardOutput())
        while b"\n" in self._buffer:
            line, self._buffer = self._buffer.split(b"\n", 1)
            try:
                event = json.loads(line.decode("utf-8", "replace"))
            except json.JSONDecodeError:
                continue
            if not isinstance(event, dict):
                continue
            kind = event.get("event")
            if kind in ("sweep_started", "point_start", "progress", "point_finished"):
                self.progress.emit(event)
            elif kind == "sweep_finished":
                self._finished_data = event
                if event.get("path"):
                    self._series_path = Path(event["path"])
            elif kind == "error":
                self._last_error = str(event.get("message") or "Error del worker 4T.")

    def _on_finished(self, code, exit_status):
        self._read_stdout()
        self._read_stderr()
        state = (self._finished_data or {}).get("state")
        error = self._last_error
        if error is None and code != 0 and not self._cancel_requested and state is None:
            error = self._stderr.decode("utf-8", "replace").strip() or (
                f"El worker de curva 4T terminó con código {code}.")
        series = None
        if self._series_path is not None and self._series_path.is_file():
            try:
                series = load_sweep(self._series_path)
            except ResultError as exc:
                error = str(exc)
        result = {
            "code": code,
            "exit_status": int(getattr(exit_status, "value", exit_status)),
            "status": state,
            "path": self._series_path,
            "series": series,
            "output": self._output,
            "cancelled": self._cancel_requested,
            "error": error,
        }
        process = self._process
        self._process = None
        if self._request_path is not None:
            try:
                self._request_path.unlink()
            except OSError:
                pass
            self._request_path = None
        if process is not None:
            process.deleteLater()
        self.finished.emit(result)

    def _on_error(self, error):
        message = self._process.errorString() if self._process is not None else str(error)
        self._last_error = message
        self.failed.emit(message)
        if self._process is not None:
            process = self._process
            self._process = None
            process.deleteLater()


class FourStrokeCurvePage(QWidget):
    """Página 4T autocontenida; no comparte resultados con el 2T."""

    def __init__(self, context, workspace=None, parent=None):
        super().__init__(parent)
        self.context = context
        self.workspace = workspace
        self.execution = FourStrokeCurveExecution(context, self)
        self.setObjectName("fourStrokeCurvePage")
        layout = QVBoxLayout(self)
        banner = QLabel(REFERENCE_BANNER)
        banner.setObjectName("fourStrokeCurveBanner")
        banner.setWordWrap(True)
        layout.addWidget(banner)
        controls = QGroupBox("Barrido RPM 4T")
        form = QFormLayout(controls)
        row = QHBoxLayout()
        self.start_edit = QLineEdit("2500")
        self.end_edit = QLineEdit("3500")
        self.step_edit = QLineEdit("500")
        for edit in (self.start_edit, self.end_edit, self.step_edit):
            edit.setMaximumWidth(90)
        row.addWidget(QLabel("Inicio")); row.addWidget(self.start_edit)
        row.addWidget(QLabel("Fin")); row.addWidget(self.end_edit)
        row.addWidget(QLabel("Paso")); row.addWidget(self.step_edit)
        row.addStretch(1)
        self.run_button = QPushButton("Calcular curva")
        self.run_button.setObjectName("fourStrokeCurveRun")
        self.run_button.clicked.connect(self.start_curve)
        self.cancel_button = QPushButton("Cancelar")
        self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(lambda *_: self.execution.cancel())
        row.addWidget(self.run_button); row.addWidget(self.cancel_button)
        form.addRow(row)
        self.progress = QProgressBar(); self.progress.setRange(0, 0)
        self.progress.setVisible(False); self.progress.setMaximumWidth(220)
        form.addRow("Progreso", self.progress)
        self.status = QLabel("Curva 4T lista · sin barrido activo")
        self.status.setWordWrap(True)
        form.addRow("Estado", self.status)
        layout.addWidget(controls)
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(
            ["RPM", "Estado", "W_C [J]", "p_max [kPa]", "Integración [s]", "Punto"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setAlternatingRowColors(True)
        layout.addWidget(self.table, 1)
        self.plot = FourStrokeCurve("W_C vs RPM · referencia 4T", "RPM", "W_C [J]")
        self.plot.setMinimumHeight(230)
        layout.addWidget(self.plot, 1)
        self.execution.started.connect(self._started)
        self.execution.progress.connect(self._progress)
        self.execution.finished.connect(self._finished)
        self.execution.failed.connect(self._failed)

    def _rpms(self):
        def integer(edit, label):
            text = edit.text().strip()
            if not text or not text.isascii() or not text.isdigit():
                raise ProjectError(f"{label}: ingresá un entero, sin separadores ni unidades.")
            return int(text)
        return plan_rpms(integer(self.start_edit, "Inicio"),
                         integer(self.end_edit, "Fin"),
                         integer(self.step_edit, "Paso"), "4T")

    def start_curve(self):
        if self.workspace is not None and not self.workspace.apply_all():
            self.status.setText("Corregí Geometría, Válvulas o Conductos antes de calcular.")
            return
        try:
            rpms = self._rpms()
            self.execution.start(rpms)
        except (ProjectError, FourStrokeProjectError, FourStrokeCurveRunError, ValueError) as exc:
            self.status.setText(str(exc))

    def _started(self, target):
        self.run_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.progress.setVisible(True)
        self.status.setText(f"Ejecutando curva 4T · {target}")

    def _progress(self, event):
        kind = event.get("event")
        if kind == "point_start":
            self.status.setText(
                f"Curva 4T · punto {event.get('point_index', 0) + 1}/{event.get('point_total', '?')} · "
                f"{event.get('rpm')} rpm")
        elif kind == "progress":
            self.status.setText(
                f"Curva 4T · {event.get('rpm')} rpm · ciclo {event.get('cycle', '?')}")
        elif kind == "point_finished":
            self.status.setText(f"Curva 4T · {event.get('rpm')} rpm · {event.get('state')}")

    def _finished(self, result):
        self.run_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        self.progress.setVisible(False)
        if result.get("error"):
            self.status.setText(f"La curva 4T falló: {result['error']}")
            return
        if result.get("cancelled"):
            self.status.setText("Curva 4T cancelada; se conservan los puntos completos.")
        series = result.get("series")
        if series is None:
            if not result.get("cancelled"):
                self.status.setText("La curva 4T terminó sin series legibles.")
            return
        self.show_series(series)
        self.status.setText(f"Curva 4T · {series['index']['state']} · "
                            f"{len(series['results'])} puntos")

    def _failed(self, message):
        self.run_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        self.progress.setVisible(False)
        self.status.setText(f"La curva 4T falló: {message}")

    def show_series(self, loaded):
        index = loaded["index"]
        results = loaded["results"]
        self.table.setRowCount(len(index["rpms"]))
        points = []
        for row, (rpm, record, result) in enumerate(zip(index["rpms"], index["points"], results)):
            self.table.setItem(row, 0, QTableWidgetItem(str(rpm)))
            self.table.setItem(row, 1, QTableWidgetItem(str(record["state"])))
            w_c = p_max = None
            if result is not None and result.get("result", {}).get("cycles"):
                last = result["result"]["cycles"][-1]
                w_c = last.get("W_C_J")
                p_max = last.get("p_max_Pa")
            self.table.setItem(row, 2, QTableWidgetItem("-" if w_c is None else f"{w_c:.6g}"))
            self.table.setItem(row, 3, QTableWidgetItem(
                "-" if p_max is None else f"{p_max / 1000:.6g}"))
            timing = record.get("timings") or {}
            self.table.setItem(row, 4, QTableWidgetItem(
                "-" if not timing else f"{timing.get('integration_seconds', 0):.6g}"))
            self.table.setItem(row, 5, QTableWidgetItem(str(record.get("result") or "-")))
            if w_c is not None:
                points.append((rpm, w_c))
        self.plot.set_points(points)

    def clear(self):
        self.table.setRowCount(0)
        self.plot.set_points([])
        self.status.setText("Curva 4T lista · sin barrido activo")
