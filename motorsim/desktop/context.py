from __future__ import annotations

from copy import deepcopy
from PySide6.QtCore import QObject, Signal

from ..engine_configuration import validate, identity
from ..engine_project import validate_project


class DesktopContext(QObject):
    changed = Signal()
    variant_changed = Signal(object)
    def __init__(self, project):
        super().__init__(); self.project=deepcopy(project); self.path=None; self.dirty=False
        self._selected_variant=None; validate_project(self.project)

    @property
    def selected_variant(self):
        return self._selected_variant

    @selected_variant.setter
    def selected_variant(self, name):
        self.select_variant(name)

    def select_variant(self, name):
        if name is not None and name not in self.project["variants"]:
            raise KeyError(f"unknown variant {name!r}")
        if name == self._selected_variant:
            return
        self._selected_variant=name
        self.variant_changed.emit(name)
        self.changed.emit()

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

    @staticmethod
    def _variant_name(name, variants, *, current=None):
        name=name.strip() if isinstance(name,str) else ""
        if not name:
            raise ValueError("El nombre de variante no puede quedar vacío")
        if name != current and name in variants:
            raise ValueError(f"Ya existe la variante {name!r}")
        return name

    def duplicate_variant(self, source_name, new_name):
        from copy import deepcopy
        from ..engine_configuration import identity, validate
        if source_name is None:
            source=self.project["base_engine"]
        else:
            try: source=self.project["variants"][source_name]
            except KeyError as exc: raise KeyError(f"No existe la variante {source_name!r}") from exc
        name=self._variant_name(new_name,self.project["variants"])
        variant=deepcopy(source);variant["display_name"]=name
        variant["provenance"]={**variant["provenance"],"variant_parent_identity":identity(source)}
        validate(variant)
        self.project["variants"][name]=variant
        self.dirty=True
        self.select_variant(name)
        return name

    def rename_variant(self, old_name, new_name):
        from ..engine_configuration import validate
        if old_name not in self.project["variants"]:
            raise KeyError(f"No existe la variante {old_name!r}")
        name=self._variant_name(new_name,self.project["variants"],current=old_name)
        variant=self.project["variants"].pop(old_name)
        variant["display_name"]=name;validate(variant)
        self.project["variants"][name]=variant
        if self._selected_variant==old_name:
            self._selected_variant=name
            self.variant_changed.emit(name)
        self.dirty=True;self.changed.emit()
        return name

    def delete_variant(self, name):
        if name not in self.project["variants"]:
            raise KeyError(f"No existe la variante {name!r}")
        refs=self.project.get("result_references",[])
        if refs:
            raise ValueError("El proyecto contiene referencias externas de corridas sin asociación de variante verificable; no se quitará la variante. Los artifacts se conservan.")
        del self.project["variants"][name]
        if self._selected_variant==name:
            self._selected_variant=None
            self.variant_changed.emit(None)
        self.dirty=True;self.changed.emit()

    def set_project_name(self, name):
        name=self._variant_name(name,{},current=self.project["project_id"])
        self.project["project_id"]=name
        self.dirty=True;self.changed.emit()

    def replace_project(self, project, path=None):
        validate_project(project); self.project=deepcopy(project); self.path=path
        self._selected_variant=None; self.dirty=False
        self.variant_changed.emit(None); self.changed.emit()
