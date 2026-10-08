"""Consulta de una serie validada, sin procesos ni acceso al editor."""
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (QDialog, QFileDialog, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget, QHeaderView, QAbstractItemView, QTabWidget)

from .comparison import ComparisonError, write_csv_files
from .performance import result_metrics


STATES = dict(converged='Convergido', not_converged='No convergido', cancelled='Cancelado',
              error='Error', running='En ejecución', not_executed='No ejecutado', stopped='Interrumpido')


def export_sweep_csv(folder, sweep):
    index=sweep['index']
    rows=[['series_id','point_index','run_id','rpm','state','cycles','integration_seconds',
           'setup_seconds','writing_seconds','wall_seconds','W_C_J_per_cycle','W_K_J_per_cycle',
           'p_max_absolute_Pa','reason','indicated_power_W','indicated_torque_Nm']]
    for i,(point,result) in enumerate(zip(index['points'],sweep['results'])):
        timing=point['timings'] or {}
        cycle=result['result']['cycles'][-1] if point['state']=='converged' else {}
        derived=result_metrics(result) if result else None
        rows.append([index['series_id'],i,point['run_id'],point['rpm'],point['state'],
            len(result['result']['cycles']) if result else None,
            *[timing.get(k) for k in ('integration_seconds','setup_seconds','writing_seconds','wall_seconds')],
            *[cycle.get(k) for k in ('W_C_J','W_K_J','p_max_Pa')],point['reason'],
            (derived or {}).get('indicated_power_W'),(derived or {}).get('indicated_torque_Nm')])
    if index['common_inputs']['case']['project_geometry']['cycle']=='4T':
        for row in rows:del row[11]
        rows[0][10]='W_C_J_per_720deg_cycle'
    return write_csv_files(folder,[('serie.csv',rows)])


class RpmPlot(QWidget):
    def __init__(self, key, title):
        super().__init__()
        self.key,self.title,self.points=key,title,[]
        self.setMinimumHeight(230)

    def set_sweep(self,sweep):
        self.rpms=sweep['index']['rpms']
        self.points=[(p['rpm'],r['result']['cycles'][-1][self.key])
            for p,r in zip(sweep['index']['points'],sweep['results']) if p['state']=='converged']
        self.update()

    def paintEvent(self,event):
        p=QPainter(self);p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(QColor('#b4d9f5'));p.drawText(QRectF(10,5,self.width()-20,30),self.title)
        if not self.points:
            p.drawText(QRectF(10,45,self.width()-20,45),'Sin puntos convergidos.');return
        values=[v for _,v in self.points];low,high=min(values),max(values)
        margin=max((high-low)*.15,abs(high)*.02,1e-6);low-=margin;high+=margin
        fmt=lambda v:f'{v:.4g}'
        left=max(70,p.fontMetrics().horizontalAdvance(fmt(high))+15)
        box=QRectF(left,45,max(1,self.width()-left-35),max(1,self.height()-100))
        p.setPen(QColor('#61758f'));p.drawLine(box.topLeft(),box.bottomLeft());p.drawLine(box.bottomLeft(),box.bottomRight())
        for f in (0,.5,1):
            p.drawText(QRectF(0,box.bottom()-f*box.height()-12,left-8,25),Qt.AlignmentFlag.AlignRight,fmt(low+f*(high-low)))
        lo,hi=self.rpms[0],self.rpms[-1]
        for rpm in self.rpms:
            x=box.left()+(rpm-lo)/(hi-lo)*box.width()
            p.drawText(QRectF(x-30,box.bottom()+5,60,25),Qt.AlignmentFlag.AlignCenter,str(rpm))
        p.setPen(QPen(QColor('#69baf0'),2));p.setBrush(QColor('#69baf0'))
        for rpm,value in self.points:
            p.drawEllipse(QPointF(box.left()+(rpm-lo)/(hi-lo)*box.width(),box.bottom()-(value-low)/(high-low)*box.height()),4,4)
        p.drawText(QRectF(left,self.height()-25,box.width(),25),Qt.AlignmentFlag.AlignCenter,'Régimen [rpm] · puntos calculados, sin ajuste')


class SweepDialog(QDialog):
    def reject(self):
        if self.isWindow():super().reject()

    def __init__(self,parent,show_point):
        super().__init__(parent)
        self.show_point=show_point;self.sweep=None
        self.controller=parent
        self.setWindowTitle('Barrido de RPM · resultados guardados');self.resize(1020,580)
        layout=QVBoxLayout(self)
        self.identity=QLabel();self.identity.setWordWrap(True);self.identity.setTextFormat(Qt.TextFormat.PlainText)
        layout.addWidget(self.identity)
        self.stale_label=QLabel();self.stale_label.setWordWrap(True);self.stale_label.setObjectName('fieldError');layout.addWidget(self.stale_label)
        tabs=QTabWidget();layout.addWidget(tabs)
        summary=QWidget();sl=QVBoxLayout(summary);tabs.addTab(summary,'Puntos')
        self.table=QTableWidget(0,7);self.table.setHorizontalHeaderLabels(['RPM','Estado','Ciclos','Integración [s]','W_C [J/ciclo]','W_K [J/ciclo]','pmax [Pa abs.]'])
        self.table.verticalHeader().hide()
        self.table.setStyleSheet('QTableWidget { selection-color: #edf5ff; selection-background-color: #234a69; } QTableWidget::item:selected { color: #edf5ff; background: #234a69; }')
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setStretchLastSection(True)
        sl.addWidget(self.table)
        self.reason=QLabel();self.reason.setWordWrap(True);self.reason.setTextFormat(Qt.TextFormat.PlainText);sl.addWidget(self.reason)
        self.plots=[RpmPlot('W_C_J','Trabajo indicado del cilindro [J/ciclo]'),RpmPlot('p_max_Pa','Presión máxima absoluta [Pa]')]
        for plot,title in zip(self.plots,('Trabajo / RPM','Presión / RPM')):tabs.addTab(plot,title)
        buttons=QHBoxLayout();layout.addLayout(buttons)
        self.point_button=QPushButton('Consultar punto convergido');self.export_button=QPushButton('Exportar CSV…')
        buttons.addWidget(self.point_button);buttons.addWidget(self.export_button);buttons.addStretch()
        close=QPushButton('Cerrar');buttons.addWidget(close);close.clicked.connect(self.close)
        self.error=QLabel();self.error.setWordWrap(True);self.error.setTextFormat(Qt.TextFormat.PlainText);layout.addWidget(self.error)
        notice=QLabel('Modelo 0D con energía prescrita, sin ondas ni sintonía. Estos puntos no son una curva de rendimiento completa.')
        notice.setWordWrap(True);layout.addWidget(notice)
        self.table.itemSelectionChanged.connect(self.selection_changed)
        self.point_button.clicked.connect(self.open_point);self.export_button.clicked.connect(self.export)
        self.selection_changed()

    def set_sweep(self,sweep):
        self.sweep=sweep;index=sweep['index'];origin=index['common_inputs']['origin']
        self.stale_label.setText(self.controller.stale_label.text())
        self.identity.setText(f"{origin['project_name']} · Serie {index['series_id']}\n"
            f"{STATES[index['state']]} · {index['reason']}\nIntegración total: {index['integration_seconds']:.3f} s · "
            f"Proceso de serie: {index['wall_seconds']:.3f} s"+
            (f" · Tiempo percibido: {index['interface_wall_seconds']:.3f} s" if 'interface_wall_seconds' in index else ''))
        self.table.setColumnHidden(5,index['common_inputs']['case']['project_geometry']['cycle']=='4T')
        four=index['common_inputs']['case']['project_geometry']['cycle']=='4T'
        self.identity.setText(self.identity.text()+('\n4T · ciclo completo 720°' if four else '\n2T · ciclo completo 360°'))
        self.table.horizontalHeaderItem(4).setText('W_C [J/720°]' if four else 'W_C [J/ciclo]')
        self.plots[0].title='Trabajo indicado del cilindro [J/720°]' if four else 'Trabajo indicado del cilindro [J/ciclo]'
        self.table.setRowCount(len(index['points']))
        for i,(point,result) in enumerate(zip(index['points'],sweep['results'])):
            cycle=result['result']['cycles'][-1] if point['state']=='converged' else {}
            row=[str(point['rpm']),STATES[point['state']],str(len(result['result']['cycles'])) if result else '',
                 f"{point['timings']['integration_seconds']:.3f}" if point['timings'] else '',
                 *[f'{cycle[k]:.6f}' if k in cycle else '' for k in ('W_C_J','W_K_J','p_max_Pa')]]
            for j,text in enumerate(row):
                item=QTableWidgetItem(text);item.setToolTip(point['reason']);self.table.setItem(i,j,item)
        for plot in self.plots:plot.set_sweep(sweep)
        self.table.resizeRowsToContents()
        self.table.selectRow(0);self.selection_changed()

    def selection_changed(self):
        i=self.table.currentRow();valid=self.sweep is not None and i>=0
        point=self.sweep['index']['points'][i] if valid else None
        self.point_button.setEnabled(bool(point and point['state']=='converged'))
        self.export_button.setEnabled(self.sweep is not None)
        self.reason.setText(point['reason'] if point else '')

    def open_point(self):
        i=self.table.currentRow()
        if self.sweep and i>=0 and self.sweep['index']['points'][i]['state']=='converged':
            self.show_point(self.sweep['results'][i])
            if self.isWindow():self.hide()

    def export(self,checked=False,*,folder=None):
        if not self.sweep:return
        if folder is None:
            folder,_=QFileDialog.getSaveFileName(self,'Carpeta nueva para serie.csv','','Carpeta (*)')
        if not folder:return
        try:
            export_sweep_csv(folder,self.sweep);self.error.setText('CSV guardado en '+str(folder))
        except ComparisonError as exc:self.error.setText(str(exc))
