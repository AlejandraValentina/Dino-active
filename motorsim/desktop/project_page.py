from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QLabel,QComboBox,QPushButton,
    QTableWidget,QTableWidgetItem,QHeaderView,QInputDialog,QMessageBox)
from ..engine_variants import compare_configurations

class ProjectPage(QWidget):
    def __init__(self,context):
        super().__init__();self.context=context;root=QVBoxLayout(self);root.setContentsMargins(24,20,24,20)
        title=QLabel("Proyecto y variantes");title.setObjectName('title');root.addWidget(title)
        self.info=QLabel();self.info.setWordWrap(True);root.addWidget(self.info)
        row=QHBoxLayout();root.addLayout(row);self.selector=QComboBox();self.selector.currentIndexChanged.connect(self.select);row.addWidget(self.selector)
        self.create=QPushButton("Crear variante…");self.create.clicked.connect(self.make_variant);row.addWidget(self.create)
        self.duplicate=QPushButton("Duplicar selección…");self.duplicate.clicked.connect(self.duplicate_variant);row.addWidget(self.duplicate)
        self.rename=QPushButton("Renombrar…");self.rename.clicked.connect(self.rename_variant);row.addWidget(self.rename)
        self.delete=QPushButton("Eliminar…");self.delete.clicked.connect(self.delete_variant);row.addWidget(self.delete)
        self.compare=QPushButton("Comparar con motor base");self.compare.clicked.connect(self.show_diff);row.addWidget(self.compare);row.addStretch()
        self.table=QTableWidget(0,4);self.table.setHorizontalHeaderLabels(["Ruta","Unidad","Base","Variante"]);self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch);root.addWidget(self.table,1)
        self.context.changed.connect(self.refresh);self.refresh()
    def refresh(self):
        project=self.context.project;self.info.setText(f"Proyecto: {project['project_id']} · {len(project['variants'])} variantes\nBase: {project['base_engine']['display_name']}\nEstado científico: {project['scientific_validation_status']} · identidades disponibles en Trazabilidad")
        current=self.context.selected_variant;self.selector.blockSignals(True);self.selector.clear();self.selector.addItem("Motor base",None)
        for name in sorted(project['variants']):self.selector.addItem(name,name)
        index=self.selector.findData(current);self.selector.setCurrentIndex(max(index,0));self.selector.blockSignals(False)
        self.rename.setEnabled(current is not None);self.delete.setEnabled(current is not None);self.duplicate.setEnabled(True)
        self.show_diff()
    def select(self,index):
        self.context.selected_variant=self.selector.itemData(index);self.context.changed.emit()
    def make_variant(self):
        name,ok=QInputDialog.getText(self,"Crear variante","Nombre de la variante:")
        if ok:self._variant_action(lambda:self.context.duplicate_variant(None,name))
    def duplicate_variant(self):
        source=self.context.selected_variant
        title="Duplicar motor base" if source is None else f"Duplicar {source}"
        name,ok=QInputDialog.getText(self,title,"Nombre de la nueva variante:")
        if ok:self._variant_action(lambda:self.context.duplicate_variant(source,name))
    def rename_variant(self):
        old=self.context.selected_variant
        if old is None:return
        name,ok=QInputDialog.getText(self,"Renombrar variante","Nuevo nombre:",text=old)
        if ok:self._variant_action(lambda:self.context.rename_variant(old,name))
    def delete_variant(self):
        name=self.context.selected_variant
        if name is None:return
        answer=QMessageBox.question(self,"Eliminar variante",f"¿Quitar {name} del proyecto? Los artifacts de corridas se conservarán.",QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,QMessageBox.StandardButton.No)
        if answer==QMessageBox.StandardButton.Yes:self._variant_action(lambda:self.context.delete_variant(name))
    def _variant_action(self,callback):
        try:callback()
        except Exception as exc:QMessageBox.warning(self,"No se pudo cambiar la variante",str(exc))
    def show_diff(self):
        name=self.context.selected_variant;self.table.setRowCount(0)
        if name is None:return
        from ..engine_variants import compare_configurations
        changes=compare_configurations(self.context.project['base_engine'],self.context.project['variants'][name]);self.table.setRowCount(len(changes))
        for i,row in enumerate(changes):
            for j,key in enumerate(('path','unit','before','after')):self.table.setItem(i,j,QTableWidgetItem(str(row[key])))
