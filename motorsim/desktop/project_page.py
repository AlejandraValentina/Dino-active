from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QLabel,QComboBox,QPushButton,QTableWidget,QTableWidgetItem,QHeaderView
from ..engine_configuration import identity
from ..engine_variants import compare_configurations

class ProjectPage(QWidget):
    def __init__(self,context):
        super().__init__();self.context=context;root=QVBoxLayout(self);root.setContentsMargins(24,20,24,20)
        title=QLabel("Proyecto y variantes");title.setObjectName('title');root.addWidget(title)
        self.info=QLabel();self.info.setWordWrap(True);root.addWidget(self.info)
        row=QHBoxLayout();root.addLayout(row);self.selector=QComboBox();self.selector.currentIndexChanged.connect(self.select);row.addWidget(self.selector)
        self.duplicate=QPushButton("Duplicar motor base como variante");self.duplicate.clicked.connect(self.make_variant);row.addWidget(self.duplicate)
        self.compare=QPushButton("Comparar con motor base");self.compare.clicked.connect(self.show_diff);row.addWidget(self.compare);row.addStretch()
        self.table=QTableWidget(0,4);self.table.setHorizontalHeaderLabels(["Ruta","Unidad","Base","Variante"]);self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch);root.addWidget(self.table,1)
        self.context.changed.connect(self.refresh);self.refresh()
    def refresh(self):
        project=self.context.project;self.info.setText(f"Proyecto: {project['project_id']} · {len(project['variants'])} variantes\nBase: {project['base_engine']['display_name']}\nHash: {project['base_identity_sha256']}\nEstado científico: {project['scientific_validation_status']}")
        current=self.context.selected_variant;self.selector.blockSignals(True);self.selector.clear();self.selector.addItem("Motor base",None)
        for name in sorted(project['variants']):self.selector.addItem(name,name)
        index=self.selector.findData(current);self.selector.setCurrentIndex(max(index,0));self.selector.blockSignals(False)
    def select(self,index):
        self.context.selected_variant=self.selector.itemData(index);self.context.changed.emit()
    def make_variant(self):
        source=self.context.project['base_engine'];name=f"Variante {len(self.context.project['variants'])+1}"
        import copy
        doc=copy.deepcopy(source);doc['display_name']=name;doc['provenance']={**doc['provenance'],'variant_parent_identity':identity(source)}
        self.context.project['variants'][name]=doc;self.context.selected_variant=name;self.context.dirty=True;self.context.changed.emit()
    def show_diff(self):
        name=self.context.selected_variant;self.table.setRowCount(0)
        if name is None:return
        from ..engine_variants import compare_configurations
        changes=compare_configurations(self.context.project['base_engine'],self.context.project['variants'][name]);self.table.setRowCount(len(changes))
        for i,row in enumerate(changes):
            for j,key in enumerate(('path','unit','before','after')):self.table.setItem(i,j,QTableWidgetItem(str(row[key])))
