from __future__ import annotations
import csv,json
from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QLabel,QComboBox,QPushButton,
    QFileDialog,QCheckBox,QListWidget,QListWidgetItem,QTableWidget,QTableWidgetItem,QHeaderView,QMessageBox)
from .plot import CurvePlot
from .services import DEFAULT_REPORT,load_results,run_background
from ..exploratory_workflow import import_exploratory_runs

METRICS={"Potencia de freno (kW)":"brake_power","Torque (N·m)":"brake_torque","IMEP (kPa)":"IMEP","FMEP (kPa)":"FMEP","BMEP (kPa)":"BMEP","BSFC (g/kWh)":"BSFC"}

class ResultsPage(QWidget):
    def __init__(self,context):
        super().__init__();self.context=context;self.dataset=None;self.source=None;self.loading=False
        root=QVBoxLayout(self);root.setContentsMargins(24,20,24,20)
        title=QLabel("Resultados y comparación");title.setObjectName('title');root.addWidget(title)
        root.addWidget(QLabel("Los reportes IMPL2 históricos se muestran separados de ejecuciones EXPLORATORY provisionales. PERIOD_1 describe periodicidad observada; no representa aprobación científica PASS. Los valores no definidos quedan como huecos."))
        bar=QHBoxLayout();root.addLayout(bar);self.metric=QComboBox();self.metric.addItems(METRICS);bar.addWidget(self.metric)
        self.path_label=QLabel(str(DEFAULT_REPORT));self.path_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse);bar.addWidget(self.path_label,1)
        browse=QPushButton("Abrir reporte…");browse.clicked.connect(self.choose);bar.addWidget(browse)
        browse_runs=QPushButton("Comparar ejecuciones EXPLORATORY…");browse_runs.clicked.connect(self.choose_exploratory);bar.addWidget(browse_runs)
        self.variants=QListWidget();self.variants.setMaximumHeight(80);self.variants.setFlow(QListWidget.Flow.LeftToRight);self.variants.setWrapping(True);root.addWidget(self.variants)
        self.plot=CurvePlot();root.addWidget(self.plot,2)
        controls=QHBoxLayout();root.addLayout(controls)
        self.unit=QLabel();controls.addWidget(self.unit);controls.addStretch()
        export_table=QPushButton("Exportar tabla CSV");export_table.clicked.connect(self.export_csv);controls.addWidget(export_table)
        export_plot=QPushButton("Exportar gráfico PNG");export_plot.clicked.connect(self.export_png);controls.addWidget(export_plot)
        self.point_table=QTableWidget(0,5);self.point_table.setHorizontalHeaderLabels(["Variante","RPM","Clasificación","Ciclos","BMEP"]);self.point_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch);self.point_table.setMaximumHeight(170);self.point_table.currentCellChanged.connect(self._point_row_selected);root.addWidget(self.point_table)
        self.details=QTableWidget(0,2);self.details.setHorizontalHeaderLabels(["Detalle del punto","Valor"]);self.details.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch);self.details.setMaximumHeight(190);root.addWidget(self.details)
        self.metric.currentIndexChanged.connect(self.redraw);self.variants.itemChanged.connect(self.redraw);self.plot.pointSelected.connect(self.show_point)
        if DEFAULT_REPORT.is_file():self.load(DEFAULT_REPORT)
        else:self.path_label.setText("No se encontró el reporte externo. Elegí el aggregate JSON de IMPL2.")
    def choose(self):
        path,_=QFileDialog.getOpenFileName(self,"Abrir reporte de resultados",str(DEFAULT_REPORT.parent),"IMPL2 report (*.json *.csv)")
        if path:self.load(Path(path))
    def choose_exploratory(self):
        paths,_=QFileDialog.getOpenFileNames(self,"Comparar resultados EXPLORATORY",str(Path.home()),"Ejecución Dino (result.json)")
        if paths:
            self.path_label.setText("Verificando artifacts EXPLORATORY…")
            run_background(import_exploratory_runs,paths,on_done=self._loaded_exploratory,on_error=self._exploratory_failed)
    def _loaded_exploratory(self,data):
        self.dataset=data;self.source=None;self.path_label.setText(f"{len(data['points'])} ciclos EXPLORATORY · provisional · no interpolación · no validación experimental")
        variants=sorted({r['variant_id'] for r in data['points']});self.variants.blockSignals(True);self.variants.clear()
        for name in variants:
            item=QListWidgetItem(name);item.setFlags(item.flags()|Qt.ItemFlag.ItemIsUserCheckable);item.setCheckState(Qt.CheckState.Checked);self.variants.addItem(item)
        self.variants.blockSignals(False);self.redraw()
    def _exploratory_failed(self,message):
        self.path_label.setText("Ejecución EXPLORATORY inválida");QMessageBox.warning(self,"Artifact exploratorio inválido",message)
    def load(self,path):
        self.loading=True;self.path_label.setText(f"Cargando {path}…")
        def done(data):
            self.dataset=data;self.source=Path(path);self.path_label.setText(f"{path} · {len(data['points'])} puntos · {data['provenance']} · validación experimental {data['experimental_validation']}")
            variants=sorted({r['variant_id'] for r in data['points']});self.variants.blockSignals(True);self.variants.clear()
            for name in variants:
                item=QListWidgetItem(name);item.setFlags(item.flags()|Qt.ItemFlag.ItemIsUserCheckable);item.setCheckState(Qt.CheckState.Checked);self.variants.addItem(item)
            self.variants.blockSignals(False);self.loading=False;self.redraw()
        def fail(message):self.loading=False;self.path_label.setText("No se pudo cargar el reporte");QMessageBox.warning(self,"Reporte inválido",message)
        run_background(load_results,path,on_done=done,on_error=fail)
    def redraw(self,*_):
        if not self.dataset:return
        metric=METRICS[self.metric.currentText()];unit=self.metric.currentText().split('(')[-1].rstrip(')')
        selected={self.variants.item(i).text() for i in range(self.variants.count()) if self.variants.item(i).checkState()==Qt.CheckState.Checked}
        series=[]
        for name in sorted(selected):
            points=[]
            for row in sorted((r for r in self.dataset['points'] if r['variant_id']==name),key=lambda r:r['rpm']):
                status=row.get(metric+'_status');value=row.get(metric) if status=='DEFINED' else None
                points.append({"rpm":row['rpm'],"value":value,"classification":row['classification'],"status":status,"reason":row.get(metric+'_reason'),"point":row})
            series.append({"name":name,"unit":unit,"points":points})
        self.unit.setText(f"{unit} · los estados sin valor permanecen como huecos · sin interpolación")
        self.plot.set_series(series)
        rows=sorted((r for r in self.dataset['points'] if r['variant_id'] in selected),key=lambda r:(r['variant_id'],r['rpm']))
        self.point_table.blockSignals(True);self.point_table.setRowCount(len(rows))
        for i,row in enumerate(rows):
            values=[row['variant_id'],row['rpm'],row['classification'],row.get('cycles_completed'),row.get('BMEP') if row.get('BMEP_status')=='DEFINED' else None]
            for j,value in enumerate(values):
                item=QTableWidgetItem('—' if value is None else str(value));item.setData(Qt.ItemDataRole.UserRole,row);self.point_table.setItem(i,j,item)
        self.point_table.blockSignals(False)
    def _point_row_selected(self,row,*_):
        if row<0 or self.point_table.item(row,0) is None:return
        data=self.point_table.item(row,0).data(Qt.ItemDataRole.UserRole)
        if data:self.show_point({"point":data,"rpm":data['rpm'],"value":None})
    def show_point(self,point):
        row=point.get('point',point);items=[("RPM",row.get('rpm')), ("Variante",row.get('variant_id')),("Clasificación",row.get('classification')),("Resultado SHA-256",row.get('result_sha256')),("Configuración SHA-256",row.get('point_configuration_sha256')),("Ciclos completados",row.get('cycles_completed')),("Periodicidad",row.get('classification')),("Métrica",row.get(METRICS[self.metric.currentText()])),("Estado métrica",row.get(METRICS[self.metric.currentText()]+'_status')),("Motivo",row.get(METRICS[self.metric.currentText()]+'_reason')),("Hard gates",json.dumps(row.get('hard_gates'),ensure_ascii=False,sort_keys=True)),("Provenance",self.dataset['provenance'])]
        self.details.setRowCount(len(items))
        for i,(a,b) in enumerate(items):self.details.setItem(i,0,QTableWidgetItem(str(a)));self.details.setItem(i,1,QTableWidgetItem("—" if b is None else str(b)))
    def export_csv(self):
        if not self.dataset:return
        path,_=QFileDialog.getSaveFileName(self,"Exportar tabla","dino-resultados.csv","CSV (*.csv)")
        if not path:return
        try:
            keys=sorted(set().union(*(row.keys() for row in self.dataset['points'])))
            with open(path,'w',encoding='utf-8-sig',newline='') as stream:
                writer=csv.DictWriter(stream,fieldnames=keys,extrasaction='ignore');writer.writeheader()
                for row in self.dataset['points']:writer.writerow({k:json.dumps(row[k],ensure_ascii=False) if isinstance(row.get(k),(dict,list)) else row.get(k) for k in keys})
        except OSError as exc:QMessageBox.warning(self,"Error de escritura",str(exc))
    def export_png(self):
        path,_=QFileDialog.getSaveFileName(self,"Exportar gráfico","dino-curva.png","PNG (*.png)")
        if path:
            pix=QPixmap(self.plot.size());self.plot.render(pix)
            if not pix.save(path,"PNG"):QMessageBox.warning(self,"Error de escritura","No se pudo guardar el gráfico.")
