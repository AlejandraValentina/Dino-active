"""Ejecución 4T 0D en segundo plano con el worker de referencia existente."""
from __future__ import annotations

import json
from pathlib import Path
import tempfile

from PySide6.QtCore import QObject, QProcess, QTimer, Signal

from ..four_stroke_project import FourStrokeProjectError
from ..reference_results import ResultError, new_output_path, project_inputs
from ..runtime import worker_command


class FourStrokeRunError(RuntimeError):
    pass


class FourStrokeExecution(QObject):
    """Prepara la solicitud 4T y supervisa `reference_run --cycle 4T`."""

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
        self._manifest = None
        self._finished_data = None
        self._last_error = None
        self._cancel_requested = False
        self._forced = False
        self._reservation = None
        self._terminal = False

    @property
    def running(self) -> bool:
        return self._process is not None

    @property
    def output(self):
        return self._output

    @property
    def manifest(self):
        return self._manifest

    def _origin(self) -> dict:
        project = self.context.project
        return {
            "kind": "project",
            "project_name": project.name,
            "source_path": str(self.context.path) if self.context.path is not None else None,
            "dirty": bool(self.context.dirty),
        }

    def prepare(self, output: str | Path | None = None):
        project = self.context.project
        try:
            project.validate_for_execution()
        except FourStrokeProjectError as exc:
            raise FourStrokeRunError(str(exc)) from exc
        if project.rpm is None:
            raise FourStrokeRunError("RPM requerido para ejecutar (2500–3500).")
        try:
            inputs = project_inputs(project.to_project(), self._origin(), rpm=project.rpm)
        except (FourStrokeProjectError, ResultError, ValueError) as exc:
            raise FourStrokeRunError(str(exc)) from exc
        payload = json.dumps(inputs, sort_keys=True, ensure_ascii=False, allow_nan=False)
        if len(payload.encode("utf-8")) > 16 * 1024 * 1024:
            raise FourStrokeRunError("La solicitud 4T supera el límite de 16 MiB.")
        fd, name = tempfile.mkstemp(prefix="dino-4t-", suffix=".json")
        try:
            with open(fd, "w", encoding="utf-8", newline="") as stream:
                stream.write(payload)
        except Exception:
            Path(name).unlink(missing_ok=True)
            raise
        self._request_path = Path(name)
        self._output = Path(output) if output is not None else new_output_path()
        return self._output, self._request_path, inputs

    def start(self, output: str | Path | None = None):
        if self.running:
            raise FourStrokeRunError("Ya hay una ejecución 4T en curso.")
        try:
            self._reservation = self.context.begin_execution("punto 4T")
        except Exception as exc:
            raise FourStrokeRunError(str(exc)) from exc
        try:
            target, request, _ = self.prepare(output)
            executable, prefix, working_directory = worker_command()
            process = QProcess(self)
            process.setWorkingDirectory(working_directory)
            process.setProgram(executable)
            process.setArguments([*prefix, "--output", str(target), "--control-stdin",
                                  "--cycle", "4T", "--project-input", str(request)])
            process.readyReadStandardOutput.connect(self._read_stdout)
            process.readyReadStandardError.connect(self._read_stderr)
            process.finished.connect(self._on_finished)
            process.errorOccurred.connect(self._on_error)
            self._process = process
            self._buffer = b""
            self._stderr = b""
            self._manifest = None
            self._finished_data = None
            self._last_error = None
            self._cancel_requested = False
            self._forced = False
            self._terminal = False
            process.start()
        except Exception:
            self._discard_request()
            self._release()
            raise
        self.started.emit(str(target))
        return target

    def _discard_request(self):
        if self._request_path is not None:
            try:
                self._request_path.unlink()
            except OSError:
                pass
            self._request_path = None

    def _release(self):
        if self._reservation is not None:
            self.context.end_execution(self._reservation)
            self._reservation = None

    def shutdown(self, timeout_ms: int = 10000) -> bool:
        """Cancel and wait for the worker process; never leave an orphan behind."""
        process = self._process
        if process is None:
            self._discard_request()
            self._release()
            return True
        self._cancel_requested = True
        try:
            process.write(b"cancel\n")
        except Exception:
            pass
        if process.state() != QProcess.ProcessState.NotRunning:
            if not process.waitForFinished(timeout_ms):
                self._forced = True
                process.kill()
                process.waitForFinished(3000)
        if self._process is process:
            self._on_finished(process.exitCode(), process.exitStatus())
        return self._process is None

    def cancel(self):
        if not self.running or self._cancel_requested:
            return
        self._cancel_requested = True
        process = self._process
        process.write(b"cancel\n")
        QTimer.singleShot(3000, lambda: self._kill_if_active(process))

    def _kill_if_active(self, process):
        if self._process is process and process.state() != QProcess.ProcessState.NotRunning:
            self._forced = True
            process.kill()

    def _read_stderr(self):
        if self._process is not None:
            self._stderr = (self._stderr + bytes(self._process.readAllStandardError()))[-8192:]

    def _read_stdout(self):
        if self._process is None:
            return
        self._buffer += bytes(self._process.readAllStandardOutput())
        while b"\n" in self._buffer:
            raw, self._buffer = self._buffer.split(b"\n", 1)
            if not raw.strip():
                continue
            try:
                event = json.loads(raw)
            except (TypeError, ValueError):
                self._last_error = "El worker 4T emitió una línea ilegible."
                continue
            kind = event.get("event")
            if kind == "progress":
                self.progress.emit(event)
            elif kind == "finished":
                self._finished_data = event
                if event.get("manifest"):
                    self._manifest = Path(event["manifest"])
            elif kind == "error":
                self._last_error = str(event.get("message") or "Error del worker 4T.")

    def _on_finished(self, code, exit_status):
        if self._terminal:
            return
        self._terminal = True
        self._read_stdout()
        self._read_stderr()
        status = (self._finished_data or {}).get("status")
        error = self._last_error
        if error is None and code != 0 and not self._cancel_requested:
            error = self._stderr.decode("utf-8", "replace").strip() or f"El worker 4T terminó con código {code}."
        result = {
            "code": code,
            "exit_status": int(getattr(exit_status, "value", exit_status)),
            "status": status,
            "manifest": self._manifest,
            "output": self._output,
            "cancelled": self._cancel_requested,
            "forced": self._forced,
            "error": error,
        }
        process = self._process
        self._process = None
        self._discard_request()
        self._release()
        if process is not None:
            process.deleteLater()
        self.finished.emit(result)

    def _on_error(self, error):
        if self._terminal:
            return
        self._terminal = True
        message = self._process.errorString() if self._process is not None else str(error)
        self._last_error = message
        process = self._process
        self._process = None
        self._discard_request()
        self._release()
        if process is not None:
            process.deleteLater()
        self.failed.emit(message)

    def load_result(self):
        if self._manifest is None:
            raise FourStrokeRunError("La ejecución 4T no produjo un manifiesto.")
        from ..reference_results import load_result
        return load_result(self._manifest)
