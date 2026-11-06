"""Estado editable del proyecto 4T 0D de referencia, separado del contexto 2T."""
from __future__ import annotations

from dataclasses import fields, replace
from pathlib import Path

from PySide6.QtCore import QObject, Signal

from ..four_stroke_project import (FourStrokeProject, FourStrokeProjectError,
                                   load_project, save_project, starter_project)


class FourStrokeContext(QObject):
    """Proyecto 4T mutable por reemplazo; no comparte estado con DesktopContext."""

    changed = Signal()
    project_changed = Signal(object)
    saved = Signal(object)

    def __init__(self, project: FourStrokeProject | None = None,
                 path: str | Path | None = None):
        super().__init__()
        self.project = project or starter_project()
        self.project.validate()
        self.path = Path(path) if path is not None else None
        self.dirty = False

    @property
    def name(self) -> str:
        return self.project.name

    @property
    def rpm(self) -> int | None:
        return self.project.rpm

    @property
    def is_runnable(self) -> bool:
        return not self.project.execution_errors()

    def execution_errors(self) -> list[str]:
        return self.project.execution_errors()

    def validate_for_execution(self) -> None:
        self.project.validate_for_execution()

    def update(self, **changes) -> FourStrokeProject:
        allowed = {item.name for item in fields(FourStrokeProject)}
        unknown = set(changes) - allowed
        if unknown:
            raise FourStrokeProjectError(f"Campos 4T desconocidos: {sorted(unknown)}")
        candidate = replace(self.project, **changes)
        candidate.validate()
        self.project = candidate
        self.dirty = True
        self.changed.emit()
        return candidate

    def replace_project(self, project: FourStrokeProject,
                        path: str | Path | None = None) -> None:
        project.validate()
        self.project = project
        self.path = Path(path) if path is not None else None
        self.dirty = False
        self.project_changed.emit(project)
        self.changed.emit()

    def new_project(self, *, name: str | None = None, rpm: int | None = 3000) -> None:
        self.replace_project(starter_project(name=name, rpm=rpm), None)

    def open(self, path: str | Path) -> FourStrokeProject:
        target = Path(path)
        project = load_project(target)
        self.replace_project(project, target)
        return project

    def save(self, path: str | Path | None = None) -> Path:
        target = Path(path) if path is not None else self.path
        if target is None:
            raise FourStrokeProjectError("Elegí un archivo para guardar el proyecto 4T.")
        save_project(target, self.project)
        self.path = target
        self.dirty = False
        self.saved.emit(target)
        self.changed.emit()
        return target
