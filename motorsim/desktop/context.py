from __future__ import annotations

from copy import deepcopy
from PySide6.QtCore import QObject, Signal

from ..engine_configuration import validate, identity
from ..engine_project import validate_project


class DesktopContext(QObject):
    changed = Signal()
    def __init__(self, project):
        super().__init__(); self.project=deepcopy(project); self.path=None; self.dirty=False
        self.selected_variant=None; validate_project(self.project)

    def engine(self, variant_name=None):
        name=self.selected_variant if variant_name is None else variant_name
        return self.project["base_engine"] if name is None else self.project["variants"][name]

    def replace_engine(self, engine, variant_name=None):
        validate(engine)
        name=self.selected_variant if variant_name is None else variant_name
        if name is None:
            self.project["base_engine"]=deepcopy(engine)
            self.project["base_identity_sha256"]=identity(engine)
        else: self.project["variants"][name]=deepcopy(engine)
        self.dirty=True; self.changed.emit()

    def replace_project(self, project, path=None):
        validate_project(project); self.project=deepcopy(project); self.path=path
        self.selected_variant=None; self.dirty=False; self.changed.emit()
