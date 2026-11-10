"""CP1 bounded 4T 0D batch queue: budget, cancel, resume and persistence."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from pathlib import Path

import desktop_qsettings_isolation  # noqa: F401
from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication

from motorsim.desktop.batch_queue import (BatchQueueDialog, BatchQueueError,
                                          FourStrokeBatchQueue,
                                          parse_curve_text)
from motorsim.desktop.four_stroke_context import FourStrokeContext
from motorsim.desktop.four_stroke_curve import FourStrokeCurvePage
from motorsim.four_stroke_project import starter_project

APP = QApplication.instance() or QApplication([])


class FakeExecution(QObject):
    finished = Signal(object)
    failed = Signal(str)
    started = Signal(object)

    def __init__(self):
        super().__init__()
        self.running = False
        self.rpms = None
        self.cancelled = False

    def start(self, rpms, output=None):
        self.rpms = list(rpms)
        self.running = True
        self.started.emit("fake")

    def cancel(self):
        self.cancelled = True
        self.running = False
        self.finished.emit({"cancelled": True, "series": None})

    def shutdown(self, timeout_ms=10000):
        if self.running:
            self.cancel()
        return True

    def complete(self, series):
        self.running = False
        self.finished.emit({"cancelled": False, "series": Path(series)})


def make_queue(tmp_path):
    created = []

    def factory():
        fake = FakeExecution()
        created.append(fake)
        return fake

    queue = FourStrokeBatchQueue(starter_project(rpm=3000), path=tmp_path / "queue.json",
                                 execution_factory=factory)
    return queue, created


def test_curve_text_validation_and_limits():
    assert parse_curve_text("2500, 3000, 3500") == [2500, 3000, 3500]
    try:
        parse_curve_text("3000,2500")
    except BatchQueueError as exc:
        assert "ascendentes" in str(exc)
    else:
        raise AssertionError("non-ascending RPM accepted")
    try:
        parse_curve_text("2400,3000")
    except Exception as exc:
        assert "2500" in str(exc) or "Rango" in str(exc)
    else:
        raise AssertionError("RPM outside domain accepted")


def test_queue_runs_curves_sequentially_and_persists(tmp_path):
    queue, created = make_queue(tmp_path)
    queue.add_curve([2500, 3000])
    queue.add_curve([3000, 3500])
    queue.start(300)
    assert queue.state == "RUNNING"
    assert queue.items[0]["status"] == "RUNNING"
    created[0].complete(tmp_path / "first-series.json")
    assert queue.items[0]["status"] == "DONE"
    assert queue.items[0]["series_path"].endswith("first-series.json")
    assert queue.items[1]["status"] == "RUNNING"
    created[1].complete(tmp_path / "second-series.json")
    assert queue.state == "DONE"
    assert queue.items[1]["status"] == "DONE"
    assert Path(queue.path).is_file()
    loaded = FourStrokeBatchQueue.load(queue.path, queue.context)
    assert len(loaded.items) == 2
    assert all(item["status"] == "DONE" for item in loaded.items)


def test_cancel_and_resume_keep_pending_items(tmp_path):
    queue, created = make_queue(tmp_path)
    queue.add_curve([2500, 3000])
    queue.add_curve([3000, 3500])
    queue.start(300)
    queue.cancel()
    assert queue.state == "CANCELLED"
    assert queue.items[0]["status"] == "CANCELLED"
    assert queue.items[1]["status"] == "PENDING"
    queue.reset_incomplete()
    queue.start(300)
    assert queue.items[0]["status"] == "RUNNING"
    assert queue.items[1]["status"] == "PENDING"


def test_batch_dialog_adds_curves_and_opens_from_4t_page(tmp_path, monkeypatch):
    monkeypatch.setenv("DINO_ARTIFACT_ROOT", str(tmp_path / "artifacts"))
    context = FourStrokeContext(starter_project(rpm=3000))
    page = FourStrokeCurvePage(context)
    assert page.batch_button.text() == "Cola de curvas…"
    dialog = BatchQueueDialog(context)
    try:
        dialog.input.setText("2500,3000")
        dialog.add_curve()
        assert dialog.table.rowCount() == 1
        assert dialog.table.item(0, 0).text() == "2500, 3000"
    finally:
        dialog.close()
        page.close()
