"""Desktop-facing adapters and cancellable background task primitive."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal, Slot

from ..engine_configuration import create, identity, validate
from ..engine_project import create_project, load_project, save_project, validate_project
from ..engine_results import import_report

ROOT = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2]))
FIXTURE = ROOT / "results/2t-commercial-core-20261002/fixtures/v1-prime-mesh/fixture_a_prime-mesh-0.json"
DEFAULT_REPORT = Path(os.environ.get("DINO_ARTIFACT_ROOT", r"E:\Dino-artifacts")) / "engine-physics-v1/full-rpm-sweep-v1-impl2/authorized-extension-26-v1/reports/impl2-full-rpm-sweep-30-points.json"


def fixture_engine():
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    return create(native_configuration=data["engine_configuration"],
        mechanical_loss_model=data["mechanical_loss_model"],
        operating_conditions={"reference_rpm": 3000, "load": 1.0,
                              "fuel_id": data["fuel_surrogate_snapshot"]["sha256"], "afr": 49.0},
        provenance={"configuration_source": {"path": str(FIXTURE.relative_to(ROOT)),
            "classification": data["classification"]}, "fuel": data["fuel_surrogate_snapshot"]},
        display_name="Fixture A — sintético")


def new_project(project_id="dino-project"):
    return create_project(project_id, fixture_engine(), scientific_validation_status="SYNTHETIC_UNVALIDATED")


def load_results(path: str | Path):
    path = Path(path)
    if path.suffix.lower() == ".csv":
        return import_report(path, metadata_path=path.with_suffix(".json"))
    return import_report(path)


class _Signals(QObject):
    finished = Signal(object)
    failed = Signal(str)
    cancelled = Signal()
    completed = Signal(object)


class _TaskRegistry(QObject):
    """Keep QRunnable wrappers alive until their queued completion is delivered."""
    def __init__(self):
        super().__init__(); self.tasks=set()

    @Slot(object)
    def release(self, task):
        self.tasks.discard(task)


_TASKS = _TaskRegistry()


class BackgroundTask(QRunnable):
    """Run I/O/service work off the UI thread; cooperative cancellation is explicit."""
    def __init__(self, function, *args, **kwargs):
        super().__init__(); self.function=function; self.args=args; self.kwargs=kwargs
        self.signals=_Signals(); self.cancel_requested=False

    def cancel(self): self.cancel_requested=True

    @Slot()
    def run(self):
        try:
            if self.cancel_requested:
                self.signals.cancelled.emit(); return
            value=self.function(*self.args,**self.kwargs)
            if self.cancel_requested: self.signals.cancelled.emit()
            else: self.signals.finished.emit(value)
        except Exception as exc:
            self.signals.failed.emit(f"{type(exc).__name__}: {exc}")
        finally:
            self.signals.completed.emit(self)


def run_background(function, *args, on_done=None, on_error=None, **kwargs):
    task=BackgroundTask(function,*args,**kwargs)
    _TASKS.tasks.add(task)
    task.signals.completed.connect(_TASKS.release)
    if on_done: task.signals.finished.connect(on_done)
    if on_error: task.signals.failed.connect(on_error)
    QThreadPool.globalInstance().start(task)
    return task
