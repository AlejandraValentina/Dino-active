from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,
    QTableWidget,QTableWidgetItem,QHeaderView,QMessageBox,QComboBox)

from ..run_history import list_project_runs


class RunHistoryWidget(QWidget):
    open_runs = Signal(object)
    resume_run = Signal(object)
    def __init__(self, context, artifact_root):
        super().__init__();self.context=context;self.artifact_root=artifact_root;self.entries=[]
        layout=QVBoxLayout(self);layout.setContentsMargins(0,8,0,0)
        header=QHBoxLayout();layout.addLayout(header)
        title=QLabel("Historial local de corridas");title.setStyleSheet("font-size:13pt;font-weight:600")
        header.addWidget(title);self.variant_filter=QComboBox();self.variant_filter.setObjectName("historyVariantFilter");header.addWidget(self.variant_filter);header.addStretch()
        refresh=QPushButton("Actualizar");refresh.clicked.connect(self.refresh);header.addWidget(refresh)
        self.table=QTableWidget(0,7);self.table.setHorizontalHeaderLabels(
            ["Variante","RPM","Actualizada","Clasificación","Periodicidad","Auditoría","Conservación"])
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table,1)
        actions=QHBoxLayout();layout.addLayout(actions)
        self.open_button=QPushButton("Ver selección");self.open_button.clicked.connect(self.open_selected);actions.addWidget(self.open_button)
        self.compare_button=QPushButton("Comparar 2 corridas");self.compare_button.clicked.connect(self.compare_selected);actions.addWidget(self.compare_button)
        self.resume_button=QPushButton("Reanudar checkpoint…");self.resume_button.clicked.connect(self.resume_selected);actions.addWidget(self.resume_button)
        self.status=QLabel("El índice lee manifests; ‘Ver’ vuelve a auditar primarias.");self.status.setWordWrap(True);actions.addWidget(self.status,1)
        self.table.itemSelectionChanged.connect(self._selection_changed)
        self.variant_filter.currentIndexChanged.connect(self.refresh)
        self.context.changed.connect(self.refresh);self.refresh()

    def refresh(self,*_):
        try:
            all_entries=list_project_runs(self.context.project,self.artifact_root)
            previous=self.variant_filter.currentData()
            self.variant_filter.blockSignals(True);self.variant_filter.clear()
            self.variant_filter.addItem("Variante activa","__active__");self.variant_filter.addItem("Todas las variantes","__all__")
            for name in sorted({entry.get("variant") for entry in all_entries if entry.get("variant")}):
                if name not in {"base","No informado"}:self.variant_filter.addItem(name,name)
            index=self.variant_filter.findData(previous)
            self.variant_filter.setCurrentIndex(index if index>=0 else 0);self.variant_filter.blockSignals(False)
            selected=self.variant_filter.currentData();active=self.context.selected_variant or "base"
            self.entries=[entry for entry in all_entries if selected=="__all__" or entry.get("variant")==(
                active if selected=="__active__" else selected)]
        except Exception as exc:
            self.entries=[];self.status.setText(f"No se pudo leer el historial: {type(exc).__name__}: {exc}")
        self.table.setRowCount(len(self.entries))
        for row,entry in enumerate(self.entries):
            values=[entry.get("variant"),entry.get("rpm"),entry.get("updated_at"),
                    entry.get("classification") or entry.get("status"),entry.get("periodicity"),
                    (entry.get("audit","NOT_REPORTED")+ (" · recomputada" if entry.get("audit_recomputed") else "")),
                    entry.get("conservation")]
            for col,value in enumerate(values):
                item=QTableWidgetItem("—" if value is None else str(value));item.setData(Qt.ItemDataRole.UserRole,row)
                item.setToolTip("\n".join((f"Ruta: {entry.get('run_directory')}",
                    f"Artifact root: {entry.get('artifact_root')}",
                    f"Identidad: {entry.get('identity_sha256')}",
                    f"Configuración: {entry.get('configuration_sha256')}",
                    f"Resultado SHA-256: {entry.get('result_sha256')}",
                    f"Checkpoint SHA-256: {entry.get('checkpoint_sha256')}",
                    f"Estado: {entry.get('status')}")))
                self.table.setItem(row,col,item)
        active=self.context.selected_variant or "base"
        label=f"variante activa {active}" if self.variant_filter.currentData()=="__active__" else "filtro seleccionado"
        self.status.setText(f"{len(self.entries)} registros · {label} · índice de sólo lectura; ‘Ver’ vuelve a auditar primarias.")
        self._selection_changed()

    def _selected(self):
        return sorted({index.row() for index in self.table.selectionModel().selectedRows()})
    def _selection_changed(self):
        selected=self._selected()
        self.open_button.setEnabled(bool(selected) and all(self.entries[i].get("result_path") for i in selected))
        self.compare_button.setEnabled(len(selected)==2 and all(self.entries[i].get("result_path") for i in selected))
        self.resume_button.setEnabled(len(selected)==1 and self.entries[selected[0]].get("resumable",False))
    def open_selected(self):
        selected=self._selected()
        if selected:self.open_runs.emit([self.entries[i]["result_path"] for i in selected])
    def compare_selected(self):
        selected=self._selected()
        if len(selected)==2:self.open_runs.emit([self.entries[i]["result_path"] for i in selected])
    def resume_selected(self):
        selected=self._selected()
        if len(selected)==1 and self.entries[selected[0]].get("resumable"):
            self.resume_run.emit(self.entries[selected[0]])
