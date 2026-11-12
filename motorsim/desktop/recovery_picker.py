"""Read-only recovery selection; deferring never deletes drafts."""
import json
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog,QVBoxLayout,QHBoxLayout,QTableWidget,QTableWidgetItem,QPlainTextEdit,QPushButton,QLabel,QHeaderView


class RecoveryPicker(QDialog):
    def __init__(self,entries,parent=None):
        super().__init__(parent);self.entries=list(entries);self.selected_entry=None
        self.setWindowTitle('Borradores de recuperación');self.resize(850,560)
        layout=QVBoxLayout(self);label=QLabel('Elegí un borrador para abrirlo como copia sin ruta. Posponer conserva todos los borradores. El archivo original nunca se sobrescribe al recuperar.');label.setWordWrap(True);layout.addWidget(label)
        self.table=QTableWidget(len(entries),4);self.table.setHorizontalHeaderLabels(['Modelo','Proyecto','Guardado automático','Archivo original'])
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers);self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows);self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setAccessibleName('Borradores disponibles');self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        for r,e in enumerate(entries):
            for c,key in enumerate(('family','project_id','saved_at','original_path')):
                value=e.get(key)
                if key=='project_id' and isinstance(e.get('project'),dict):value=e['project'].get('project_id') or e['project'].get('name') or value
                self.table.setItem(r,c,QTableWidgetItem(str(value or 'Sin archivo')))
        layout.addWidget(self.table,1);self.preview=QPlainTextEdit();self.preview.setReadOnly(True);self.preview.setAccessibleName('Vista previa de configuración recuperable');layout.addWidget(self.preview,1)
        row=QHBoxLayout();layout.addLayout(row);self.open_button=QPushButton('Abrir copia recuperada');self.open_button.clicked.connect(self.open_selected);row.addWidget(self.open_button)
        later=QPushButton('Posponer');later.clicked.connect(self.reject);row.addWidget(later)
        self.table.itemSelectionChanged.connect(self.refresh);self.table.cellDoubleClicked.connect(lambda *_:self.open_selected())
        if entries:self.table.selectRow(0)
        self.refresh()

    def refresh(self):
        index=self.table.currentRow();self.open_button.setEnabled(0<=index<len(self.entries))
        if 0<=index<len(self.entries):
            entry=self.entries[index];project=entry.get('project',{})
            # Preview only; no model deserialization, simulation or document mutation.
            self.preview.setPlainText(json.dumps(project,ensure_ascii=False,indent=2)[:40000])

    def open_selected(self):
        index=self.table.currentRow()
        if 0<=index<len(self.entries):self.selected_entry=self.entries[index];self.accept()
