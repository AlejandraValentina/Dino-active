from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QWidget


class ContextBar(QWidget):
    """Persistent project/variant/mode context shared by every desktop page."""

    variant_selected = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.project = QLabel(); self.project.setObjectName("contextProject")
        self.variant_label = QLabel("Variante activa")
        self.variant = QComboBox(); self.variant.setMinimumContentsLength(18)
        self.variant.currentIndexChanged.connect(self._selected)
        self.mode = QLabel("EXPLORATORIO")
        self.mode.setObjectName("modeBadge")
        self.saved = QLabel()
        layout=QHBoxLayout(self);layout.setContentsMargins(12,7,12,7);layout.setSpacing(10)
        layout.addWidget(self.project,1);layout.addWidget(self.variant_label);layout.addWidget(self.variant)
        layout.addWidget(self.mode);layout.addWidget(self.saved)

    def set_context(self, project, selected_variant, dirty):
        self.project.setText(f"Proyecto: {project['project_id']}")
        self.variant.blockSignals(True);self.variant.clear()
        self.variant.addItem(project["base_engine"].get("display_name","Motor base"),None)
        for name in sorted(project["variants"]): self.variant.addItem(name,name)
        index=self.variant.findData(selected_variant)
        self.variant.setCurrentIndex(max(index,0));self.variant.blockSignals(False)
        self.saved.setText("● Cambios sin guardar" if dirty else "✓ Guardado")

    def _selected(self,index):
        if index>=0:self.variant_selected.emit(self.variant.itemData(index))
