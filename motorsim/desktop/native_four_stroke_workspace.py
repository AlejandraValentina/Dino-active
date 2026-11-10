"""Native 4T workspaces embedded in Dino Desktop's shared navigation.

The 4T scientific API and project schema stay independent from the 2T solver
and from the 4T 0D synthetic reference workflow.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QListWidget, QLabel,
    QPushButton, QStackedWidget, QTabWidget, QMessageBox, QInputDialog,
)

from .context import DesktopContext
from .four_stroke_project import project_from_example
from .four_stroke_desktop import FourStrokeConfigEditor, FourStrokeSimulation, FourStrokeResults
from .native_four_stroke_curve import NativeFourStrokeCurvePage


class NativeFourStrokeWorkspace(QWidget):
    """Native 4T design, execution and results under the shared 2T/4T shell."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("nativeFourStrokeWorkspace")
        self.context = DesktopContext(project_from_example("nuevo-motor-4t"))
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        self.banner = QLabel(
            "MOTOR 4T NATIVO · DINO4T_API_V1 · "
            "VALIDACIÓN EXPERIMENTAL NO REALIZADA"
        )
        self.banner.setObjectName("nativeFourStrokeIndicator")
        self.banner.setWordWrap(True)
        layout.addWidget(self.banner)
        self.stack = QStackedWidget()
        layout.addWidget(self.stack, 1)

        model = QWidget()
        model_layout = QHBoxLayout(model)
        split = QSplitter(Qt.Orientation.Horizontal)
        model_layout.addWidget(split)
        variants = QWidget()
        variants_layout = QVBoxLayout(variants)
        variants_layout.addWidget(QLabel("Variantes del motor 4T"))
        self.variant_list = QListWidget()
        self.variant_list.setObjectName("nativeFourStrokeVariants")
        variants_layout.addWidget(self.variant_list, 1)
        self.variant_buttons = []
        for label, callback in (
            ("Motor base", lambda: self.context.select_variant(None)),
            ("Duplicar variante…", self.duplicate_variant),
            ("Eliminar variante", self.delete_variant),
        ):
            button = QPushButton(label)
            button.clicked.connect(callback)
            variants_layout.addWidget(button)
            self.variant_buttons.append(button)
        split.addWidget(variants)
        self.editor = FourStrokeConfigEditor(self.context)
        split.addWidget(self.editor)
        split.setStretchFactor(1, 1)
        self.stack.addWidget(model)

        self.results = FourStrokeResults(self.context)
        self.stack.addWidget(self.results)
        self.simulation = FourStrokeSimulation(self.context)
        self.curve = NativeFourStrokeCurvePage(self.context, self.simulation)
        self.simulation_pages = QTabWidget()
        self.simulation_pages.setObjectName('nativeFourStrokeSimulationTabs')
        self.simulation_pages.addTab(self.simulation, 'Punto operativo')
        self.simulation_pages.addTab(self.curve, 'Curva de potencia / torque')
        self.stack.addWidget(self.simulation_pages)
        self.curve.runningChanged.connect(self._curve_running_changed)
        self.simulation.runFinished.connect(lambda *_: self.results.refresh())
        self.variant_list.currentTextChanged.connect(self._select_variant)
        self.context.changed.connect(self._refresh_variants)
        self.context.variant_changed.connect(lambda *_: self._refresh_variants())
        self._refresh_variants()

    @property
    def running(self):
        return self.simulation.task is not None or self.curve.running

    def _curve_running_changed(self, running):
        self.editor.setEnabled(not running)
        self.variant_list.setEnabled(not running)
        for button in self.variant_buttons:button.setEnabled(not running)
        self.simulation.start.setEnabled(not running)

    def shutdown(self, timeout_ms=10000):
        if self.curve.running and not self.curve.shutdown(timeout_ms):
            return False
        if self.simulation.task is not None and not self.simulation.shutdown(timeout_ms):
            return False
        return True

    def set_workspace_mode(self, index):
        if index not in (0, 1, 2):
            raise ValueError("Modo de trabajo desconocido")
        self.stack.setCurrentIndex(index)

    def replace_project(self, project, path=None):
        if self.running:
            raise RuntimeError("La corrida 4T debe terminar antes de cambiar de proyecto.")
        self.context.replace_project(project, path)
        self.editor.refresh()
        self.results.refresh()
        self.curve.table.setRowCount(0)
        self.curve.power_plot.set_points([])
        self.curve.torque_plot.set_points([])
        self.curve.status.setText('Nuevo proyecto 4T · sin curva calculada')
        config = self.context.engine()
        self.simulation.rpm.setValue(float(config["operating_point"]["rpm"]))
        self.simulation.cycles.setValue(int(config["numerics"]["max_cycles"]))
        self._refresh_variants()

    def _refresh_variants(self):
        selected = self.context.selected_variant
        self.variant_list.blockSignals(True)
        self.variant_list.clear()
        for name in sorted(self.context.project["variants"]):
            self.variant_list.addItem(name)
            if name == selected:
                self.variant_list.setCurrentRow(self.variant_list.count() - 1)
        self.variant_list.blockSignals(False)

    def _select_variant(self, name):
        if name in self.context.project["variants"]:
            self.context.select_variant(name)

    def duplicate_variant(self):
        name, accepted = QInputDialog.getText(self, "Nueva variante 4T", "Nombre:")
        if accepted:
            try:
                self.context.duplicate_variant(self.context.selected_variant, name)
            except Exception as exc:
                QMessageBox.warning(self, "Variante inválida", str(exc))

    def delete_variant(self):
        name = self.context.selected_variant
        if name is None:
            return
        try:
            self.context.delete_variant(name)
        except Exception as exc:
            QMessageBox.warning(self, "No se pudo eliminar la variante", str(exc))
