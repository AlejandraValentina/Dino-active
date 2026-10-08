"""Vista de dos resultados guardados. No recibe proyecto ni inicia procesos."""
from pathlib import Path

from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QPushButton, QGroupBox, QWidget, QTabWidget, QScrollArea, QTableWidget,
    QTableWidgetItem, QHeaderView, QAbstractItemView, QPlainTextEdit, QFileDialog)

from .reference_results import load_result, ResultError, new_output_path
from .comparison import compare_results, export_csv, ComparisonError, STATES


def label(text='', style=''):
    widget=QLabel(text)
    widget.setTextFormat(Qt.TextFormat.PlainText)
    widget.setWordWrap(True)
    widget.setObjectName(style)
    widget.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    return widget


class ComparisonPlot(QWidget):
    def __init__(self,pv=False):
        super().__init__()
        self.pv=pv
        self.series=[]
        self.setMinimumSize(270,290)
        self.setAccessibleName('Comparación presión-volumen' if pv else 'Comparación presión-ángulo')

    def set_curves(self,curves):
        self.series=[[(r['volume_m3']*1e6 if self.pv else r['angle_cycle_deg'],r['pressure_absolute_Pa']/1000)
                      for r in rows] for rows in curves]
        self.update()

    def paintEvent(self,event):
        p=QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        fm=p.fontMetrics();line=fm.height()+4
        p.setPen(QColor('#c7d9ef'))
        p.drawText(QRectF(8,0,self.width()-16,line),'Presión–volumen' if self.pv else 'Presión–ángulo de ciclo')
        p.drawText(QRectF(8,line,self.width()-16,line),'Presión absoluta [kPa]')
        styles=(('A','#69baf0',Qt.PenStyle.SolidLine),('B','#ffb36b',Qt.PenStyle.DashLine))
        for i,(name,color,style) in enumerate(styles):
            x=12+i*100
            p.setPen(QPen(QColor(color),2,style))
            p.drawLine(QPointF(x,2.6*line),QPointF(x+30,2.6*line))
            p.drawText(QRectF(x+38,2.1*line,45,line),name)
        if not self.series:
            p.setPen(QColor('#a4b6cc'))
            p.drawText(QRectF(8,4*line,self.width()-16,2*line),Qt.TextFlag.TextWordWrap,'Cargá dos resultados compatibles.')
            return
        xs=[x for rows in self.series for x,y in rows]
        ys=[y for rows in self.series for x,y in rows]
        lo,hi=(0,max(xs)*1.05) if self.pv else (min(xs),max(xs))
        top=max(ys)*1.05
        margin=max(55,fm.horizontalAdvance(f'{top:.0f}')+12)
        box=QRectF(margin,3*line+8,max(1,self.width()-margin-25),max(1,self.height()-6*line-22))
        p.setPen(QColor('#8196b1'))
        p.drawLine(box.topLeft(),box.bottomLeft());p.drawLine(box.bottomLeft(),box.bottomRight())
        for f in (0,.5,1):
            y=box.bottom()-box.height()*f;x=box.left()+box.width()*f
            p.drawText(QRectF(0,y-line/2,margin-7,line),Qt.AlignmentFlag.AlignRight,f'{top*f:.0f}')
            caption=f'{lo+(hi-lo)*f:.0f}'
            if not self.pv:caption+='\n'+('PMS' if lo==0 or f==.5 else 'PMI')
            p.drawText(QRectF(x-30,box.bottom()+4,60,2*line),Qt.AlignmentFlag.AlignHCenter,caption)
        for rows,(_,color,style) in zip(self.series,styles):
            path=QPainterPath()
            for i,(x,y) in enumerate(rows):
                point=QPointF(box.left()+(x-lo)/(hi-lo)*box.width(),box.bottom()-y/top*box.height())
                path.moveTo(point) if i==0 else path.lineTo(point)
            p.setPen(QPen(QColor(color),2,style));p.drawPath(path)
        p.setPen(QColor('#c7d9ef'))
        p.drawText(QRectF(margin,self.height()-line,box.width(),line),Qt.AlignmentFlag.AlignCenter,
                   'Volumen [cm³] · orden temporal' if self.pv else 'Ángulo de ciclo [°]')


from .ui import Header, Panel


class ComparisonDialog(QDialog):
    def reject(self):
        if self.isWindow():super().reject()

    def __init__(self,parent=None,*,embedded=False):
        super().__init__(parent)
        if embedded:self.setWindowFlags(Qt.WindowType.Widget)
        self.setWindowTitle('MotorSim — Comparar resultados')
        self.resize(1040,780)
        self.results=[None,None]
        self.comparison=None
        layout=QVBoxLayout(self)
        scroll=QScrollArea();scroll.setWidgetResizable(True);scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        layout.addWidget(scroll)
        body=QWidget();content=QVBoxLayout(body);content.setContentsMargins(16,12,16,12);content.setSpacing(12)
        scroll.setWidget(body);self.scroll=scroll
        content.addWidget(Header('Comparar','Seleccioná la configuración base A y la alternativa B.','La compatibilidad se comprueba antes de mostrar diferencias.'))
        self.cards_grid=QGridLayout();self.cards=[];self.info=[];self.select_buttons=[]
        for i,title in enumerate(('A · configuración base','B · configuración modificada')):
            card=Panel(title);box=card.content
            button=QPushButton(f'Abrir resultado {"AB"[i]}…')
            button.clicked.connect(lambda checked=False,index=i:self.select_result(index))
            box.addWidget(button,alignment=Qt.AlignmentFlag.AlignLeft)
            info=label('No hay resultado seleccionado. Abrí un manifest.json guardado.');box.addWidget(info)
            self.cards.append(card);self.info.append(info);self.select_buttons.append(button)
        content.addLayout(self.cards_grid)
        self.compatibility_label=label('Seleccioná A y B para comprobar compatibilidad.','sectionTitle')
        compatibility=Panel('COMPATIBILIDAD');compatibility.content.addWidget(self.compatibility_label);content.addWidget(compatibility)
        self.error_label=label('','fieldError');self.error_label.hide();content.addWidget(self.error_label)
        self.empty=Panel('SIN COMPARACIÓN');self.empty.content.addWidget(label('Cargá ambos resultados. Si son compatibles, aquí se mostrarán magnitudes, diferencias de entradas y curvas superpuestas.','unit'));content.addWidget(self.empty)
        self.tabs=QTabWidget();content.addWidget(self.tabs);self.tabs.hide()
        summary=QWidget();summary_layout=QVBoxLayout(summary)
        summary_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.table=QTableWidget(0,6)
        self.table.setHorizontalHeaderLabels(['Magnitud','Unidad','A','B','B − A','Relativa %'])
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.verticalHeader().hide()
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(0,QHeaderView.ResizeMode.Stretch)
        self.table.setMinimumHeight(255)
        summary_layout.addWidget(self.table)
        self.differences=QPlainTextEdit();self.differences.setReadOnly(True);self.differences.setMinimumHeight(120)
        self.tabs.addTab(summary,'&Resumen')
        plots=QWidget();self.plots_grid=QGridLayout(plots)
        self.angle_plot=ComparisonPlot();self.pv_plot=ComparisonPlot(True)
        self.tabs.addTab(plots,'&Curvas superpuestas')
        self.tabs.addTab(self.differences,'&Entradas utilizadas')
        actions=QHBoxLayout()
        self.export_button=QPushButton('&Exportar CSV…');self.export_button.setEnabled(False)
        self.export_button.clicked.connect(self.export)
        actions.addWidget(self.export_button);actions.addStretch()
        close=QPushButton('Cerrar');close.clicked.connect(self.close);actions.addWidget(close)
        close.setVisible(not embedded)
        content.addLayout(actions)
        content.addWidget(label('Modelo 0D con energía prescrita, sin ondas ni validación experimental. La diferencia no acredita un motor mejor ni potencia al eje.','unit'))
        self._arrange()

    def _arrange(self):
        wide=self.width()>=850
        for i,card in enumerate(self.cards):self.cards_grid.addWidget(card,0 if wide else i,i if wide else 0)
        self.cards_grid.setColumnStretch(0,1);self.cards_grid.setColumnStretch(1,1 if wide else 0)
        self.plots_grid.addWidget(self.angle_plot,0,0)
        self.plots_grid.addWidget(self.pv_plot,0 if wide else 1,1 if wide else 0)
        self.plots_grid.setColumnStretch(0,1);self.plots_grid.setColumnStretch(1,1 if wide else 0)

    def resizeEvent(self,event):
        super().resizeEvent(event)
        if hasattr(self,'cards_grid'):
            self._arrange()
            self._fit_table()

    def _fit_table(self):
        if self.table.rowCount():
            self.table.resizeRowsToContents()
            height=self.table.horizontalHeader().height()+sum(self.table.rowHeight(i) for i in range(self.table.rowCount()))
            self.table.setFixedHeight(height+2*self.table.frameWidth()+4)

    def select_result(self,index,*,path=None):
        if path is None:
            name,_=QFileDialog.getOpenFileName(self,f'Abrir resultado {"AB"[index]}',str(new_output_path().parent),'Manifiesto (manifest.json)')
            if not name:return
            path=Path(name)
        try:result=load_result(path)
        except ResultError as exc:
            self.error_label.setText(f'{exc} Se conserva la selección anterior.')
            self.error_label.show()
            return
        self.results[index]=result
        inputs=result['inputs'];case=inputs['case'];origin=inputs.get('origin')
        name=origin['project_name'] if origin else case['identifier']
        self.info[index].setText(f"{name}\nEjecución: {result['manifest']['run_id']}\n"
            f"Origen: {'proyecto' if origin else 'referencia'} · {case['rpm']:g} rpm · Perfil {inputs['profile']['name']} · Banda {inputs['variant']['delta_p_Pa']} Pa\n"
            f"Modelo: {inputs['model_version']}\nEstado: {STATES[result['status']]}")
        self.info[index].setToolTip(str(result['path']))
        self.error_label.clear();self.error_label.hide();self._refresh()

    def _refresh(self):
        self.comparison=None;self.export_button.setEnabled(False)
        self.tabs.setVisible(all(self.results));self.empty.setVisible(not all(self.results))
        self.table.setRowCount(0);self.differences.clear()
        self.angle_plot.set_curves([]);self.pv_plot.set_curves([])
        if not all(self.results):return
        try:self.comparison=compare_results(*self.results)
        except (ComparisonError,ResultError) as exc:
            self.compatibility_label.setText('No se habilita comparación cuantitativa:\n'+str(exc))
            return
        self.compatibility_label.setText('Compatibles · mismas condiciones, modelo, perfil y variante. Diferencias B − A.')
        self.export_button.setEnabled(True)
        for i,row in enumerate(self.comparison['metrics']):
            self.table.insertRow(i)
            factor=1000 if row['magnitude']=='indicated_power_W' else 1
            values=[row['title'],'kW' if factor==1000 else row['unit'],*[f'{row[k]/factor:.9g}' for k in ('a','b','difference')],
                    ('—' if row['magnitude'].startswith('Y_') else 'No definida') if row['relative_percent'] is None else f"{row['relative_percent']:.7g}"]
            for j,value in enumerate(values):
                item=QTableWidgetItem(value)
                item.setToolTip(value)
                if j>=2:item.setTextAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignVCenter)
                self.table.setItem(i,j,item)
        self._fit_table()
        lines=[]
        for group,title in (('geometry','Geometría utilizada'),('descriptive','Cambios descriptivos (no geométricos)')):
            entries=self.comparison['differences'][group]
            lines.append(title+(':' if entries else ': sin diferencias.'))
            for row in entries:
                lines.append(f"  {row['section']} · {row['field']}: {row['a'] if row['a'] is not None else 'ausente'} → {row['b'] if row['b'] is not None else 'ausente'} {row['unit']}")
        if len(self.comparison['differences']['geometry'])>1:
            lines.append('Hay varias modificaciones; el resultado no se atribuye a una sola.')
        lines.append('Y: diferencia absoluta; no es un porcentaje relativo.')
        self.differences.setPlainText('\n'.join(lines))
        self.angle_plot.set_curves(self.comparison['curves']);self.pv_plot.set_curves(self.comparison['curves'])

    def export(self,checked=False,*,folder=None):
        if self.comparison is None:return
        if folder is None:
            name,_=QFileDialog.getSaveFileName(self,'Crear carpeta nueva para los dos CSV',str(new_output_path().with_name('comparacion-'+new_output_path().name)),
                options=QFileDialog.Option.DontConfirmOverwrite)
            if not name:return
            folder=Path(name)
        try:paths=export_csv(folder,self.comparison)
        except ComparisonError as exc:
            self.error_label.setText(str(exc));self.error_label.show();return
        self.error_label.setText('CSV exportados: '+', '.join(str(p) for p in paths))
        self.error_label.show()
        return paths
