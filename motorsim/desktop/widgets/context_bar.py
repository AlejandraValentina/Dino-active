from __future__ import annotations

from PySide6.QtCore import Signal,Qt
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QWidget


class ContextBar(QWidget):
    """Persistent project/variant/mode context shared by every desktop page."""

    variant_selected = Signal(object)
    baseline_selected = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.project = QLabel(); self.project.setObjectName("contextProject")
        self.variant_label = QLabel("Variante activa")
        self.variant = QComboBox(); self.variant.setMinimumContentsLength(18)
        self.variant.currentIndexChanged.connect(self._selected)
        self.baseline_label=QLabel("Baseline ···")
        self.baseline=QComboBox();self.baseline.setMinimumContentsLength(14);self.baseline.currentIndexChanged.connect(self._baseline_selected)
        self.baseline_label.setStyleSheet("color:#f6bd60;font-weight:600")
        self.mode = QLabel("EXPLORATORIO")
        self.mode.setObjectName("modeBadge")
        self.saved = QLabel()
        layout=QHBoxLayout(self);layout.setContentsMargins(12,7,12,7);layout.setSpacing(10)
        layout.addWidget(self.project,1);layout.addWidget(self.variant_label);layout.addWidget(self.variant);layout.addWidget(self.baseline_label);layout.addWidget(self.baseline)
        layout.addWidget(self.mode);layout.addWidget(self.saved)

    def set_context(self, project, selected_variant, dirty):
        self.project.setText(f"Proyecto: {project['project_id']}")
        self.variant.blockSignals(True);self.variant.clear()
        self.variant.addItem(project["base_engine"].get("display_name","Motor base"),None)
        for name in sorted(project["variants"]): self.variant.addItem(name,name)
        index=self.variant.findData(selected_variant)
        self.variant.setCurrentIndex(max(index,0));self.variant.blockSignals(False)
        from ..preferences import settings
        key=f"baseline_variant/{project['project_id']}";preferred=settings().value(key,"base") or "base"
        self.baseline.blockSignals(True);self.baseline.clear();self.baseline.addItem("Motor base","base")
        for name in sorted(project["variants"]):self.baseline.addItem(name,name)
        baseline_index=self.baseline.findData(preferred)
        self.baseline.setCurrentIndex(baseline_index if baseline_index>=0 else 0);self.baseline.blockSignals(False)
        self.saved.setText("● Cambios sin guardar" if dirty else "✓ Guardado")

    def _selected(self,index):
        if index>=0:self.variant_selected.emit(self.variant.itemData(index))

    def _baseline_selected(self,index):
        if index>=0:self.baseline_selected.emit(self.baseline.itemData(index))
