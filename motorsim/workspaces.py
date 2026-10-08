"""Composición por tareas. No contiene validadores, persistencia ni cálculo físico."""
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QGridLayout,QLabel,
    QTreeWidget,QTreeWidgetItem,QStackedWidget,QScrollArea,QTabWidget,QPushButton,
    QPlainTextEdit,QSizePolicy,QMenu,QToolButton,QComboBox)
from .project import ProjectError
from .ui import Header, Panel, Columns, Badge, PropertyTable
from .examples import EXAMPLES


def label(text='',style=''):
    w=QLabel(text);w.setWordWrap(True);w.setTextFormat(Qt.TextFormat.PlainText)
    w.setObjectName(style);w.setMinimumWidth(0);return w


def scroll(widget):
    w=QScrollArea();w.setWidgetResizable(True);w.setFrameShape(QScrollArea.Shape.NoFrame)
    w.setWidget(widget);return w


class Navigation(QWidget):
    selected=Signal(str)
    def __init__(self):
        super().__init__();layout=QHBoxLayout(self);layout.setContentsMargins(0,0,0,0);layout.setSpacing(0)
        self.tree=QTreeWidget();self.tree.setObjectName('navigation');self.tree.setHeaderHidden(True)
        self.tree.setAccessibleName('Navegación principal');self.tree.setRootIsDecorated(False)
        self.tree.setIndentation(10);self.tree.setMinimumWidth(145);self.tree.setMaximumWidth(200)
        self.tree.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.stack=QStackedWidget();self.stack.setMinimumWidth(0)
        layout.addWidget(self.tree);layout.addWidget(self.stack,1)
        self.items={};self.pages={};self.aliases={};self.groups={};self.cycle='2T';self.current=''
        self.tree.currentItemChanged.connect(self._select)
    def add_page(self,group,key,title,page):
        if group not in self.groups:
            node=QTreeWidgetItem(self.tree,[group]);node.setFlags(Qt.ItemFlag.ItemIsEnabled)
            font=self.tree.font();font.setPointSize(8);font.setBold(True)
            node.setFont(0,font);node.setForeground(0,QColor('#8ba2be'))
            node.setExpanded(True);self.groups[group]=node
        item=QTreeWidgetItem(self.groups[group],[title]);item.setData(0,Qt.ItemDataRole.UserRole,key)
        item.setToolTip(0,title);self.items[key]=item;self.pages[key]=page;self.stack.addWidget(page)
    def _select(self,item,previous):
        key=item.data(0,Qt.ItemDataRole.UserRole) if item else None
        if key in self.pages:
            self.current=key;self.stack.setCurrentWidget(self.pages[key]);self.selected.emit(key)
    def go(self,key):
        if key in ('motor2','motor4'):key='motor2' if self.cycle=='2T' else 'motor4'
        self.tree.setCurrentItem(self.items[key])
        if self.current==key:self.selected.emit(key)
    def set_cycle(self,cycle):
        self.cycle=cycle;self.items['motor2'].setHidden(cycle!='2T');self.items['motor4'].setHidden(cycle!='4T')
        if self.current in ('motor2','motor4'):self.go('motor2' if cycle=='2T' else 'motor4')
    def setCurrentWidget(self,widget):
        # Conserva accesos internos a editores; no existe una segunda navegación visible.
        key,callback=self.aliases.get(widget,('summary',None));self.go(key)
        if callback:callback()
    def setCurrentIndex(self,index):self.go(list(self.pages)[index])
    def currentWidget(self):return self.stack.currentWidget()


class SummaryPage(QScrollArea):
    def __init__(self,owner):
        super().__init__();self.owner=owner;self.setWidgetResizable(True);self.setFrameShape(QScrollArea.Shape.NoFrame)
        body=QWidget();box=QVBoxLayout(body);box.setContentsMargins(24,20,24,20);box.setSpacing(16)
        box.addWidget(Header('Resumen','Identidad, geometría y preparación del proyecto.'))
        self.tabs=QTabWidget();box.addWidget(self.tabs)
        summary=QWidget();layout=QVBoxLayout(summary);layout.setContentsMargins(0,14,0,0);layout.setSpacing(16)
        identity=Panel('PROYECTO ACTIVO');geometry=Panel('GEOMETRÍA ESENCIAL')
        self.identity_table=PropertyTable(('Nombre','Fabricante / modelo','Ciclo','Archivo','Estado'))
        identity.content.addWidget(self.identity_table)
        self.identity=self.identity_table.values['Nombre'];self.file=self.identity_table.values['Archivo']
        self.geometry_table=PropertyTable(('Cilindros','Diámetro × carrera','Compresión','Por cilindro','Cilindrada total'))
        geometry.content.addWidget(self.geometry_table)
        self.facts=label();self.facts.hide()
        for title,key in (('Configurar geometría','geometry'),('Configurar motor','motor2')):
            button=QPushButton(title+' →');button.clicked.connect(lambda checked=False,k=key:owner.navigation.go(k));geometry.content.addWidget(button)
            if key=='motor2':self.motor_button=button
        preparation=Panel('PREPARACIÓN Y ESTADO');actions=Panel('EJEMPLOS SINTÉTICOS')
        self.ready_badge=Badge();preparation.content.addWidget(self.ready_badge)
        self.ready=label();preparation.content.addWidget(self.ready)
        self.attention=QVBoxLayout();preparation.content.addLayout(self.attention)
        preparation.content.addWidget(label('La convergencia no está garantizada.','unit'))
        self.simulate_button=QPushButton('Ir a simulación →');self.simulate_button.setObjectName('primaryAction')
        self.simulate_button.clicked.connect(lambda:owner.navigation.go('simulation'));preparation.content.addWidget(self.simulate_button)
        actions.content.addWidget(label('EJEMPLO SINTÉTICO — NO MEDIDO','unit'))
        self.example_combo=QComboBox();self.example_combo.setAccessibleName('Proyecto de ejemplo sintético')
        for key,(title,_) in EXAMPLES.items():self.example_combo.addItem(title,key)
        actions.content.addWidget(self.example_combo)
        self.example_button=QPushButton('Cargar copia editable')
        self.example_button.clicked.connect(lambda:owner.load_example_file(self.example_combo.currentData()))
        actions.content.addWidget(self.example_button)
        actions.content.addWidget(label('Sin resultados precalculados. Guardar solicitará un archivo nuevo.','unit'))
        columns=[]
        for panels in ((identity,preparation),(geometry,actions)):
            column=QWidget();column_box=QVBoxLayout(column);column_box.setContentsMargins(0,0,0,0);column_box.setSpacing(12)
            for panel in panels:column_box.addWidget(panel)
            column_box.addStretch();columns.append(column)
        layout.addWidget(Columns(*columns,800))
        layout.addStretch()
        self.tabs.addTab(summary,'Resumen');self.tabs.addTab(owner.general_group,'Datos del proyecto')
        box.addStretch();self.setWidget(body);self.issue_routes={}
    def refresh(self):
        w=self.owner;cycle=w.cycle_combo.currentText();name=w.name_edit.text() or 'Sin nombre'
        for key,value in {'Nombre':name,'Fabricante / modelo':' / '.join(x.text() or '—' for x in w.text_edits.values()),
                          'Ciclo':cycle,'Archivo':str(w.path) if w.path else 'Sin archivo asociado','Estado':w.state_label.text()}.items():
            self.identity_table.set_value(key,value)
        def value(key):return w.numeric_edits[key].text() or '—'
        facts={'Cilindros':value('cylinder_count'),'Diámetro × carrera':f'{value("bore_mm")} × {value("stroke_mm")} mm',
               'Compresión':value('compression_ratio')+':1','Por cilindro':w.volume_label.text()+' cm³',
               'Cilindrada total':w.total_volume_label.text()+' cm³'}
        for key,val in facts.items():self.geometry_table.set_value(key,val)
        self.facts.setText('\n'.join(f'{k}: {v}' for k,v in facts.items()))
        self.motor_button.setText('Configurar motor '+cycle+' →')
        try:
            w.execution_snapshot()
            errors=[]
        except ProjectError as exc:errors=str(exc).splitlines()
        self.ready_badge.set_state('ENTRADAS ADMITIDAS' if not errors else 'DATOS INCOMPLETOS','success' if not errors else 'warning')
        self.ready.setText('Listo para simular' if not errors else 'Faltan datos · revisar configuración')
        while self.attention.count():
            item=self.attention.takeAt(0)
            if item.widget():
                item.widget().hide()
                item.widget().deleteLater()
        self.issue_routes={}
        for error in errors:
            lower=error.lower()
            key=('motor2' if cycle=='2T' else 'motor4') if any(t in lower for t in ('lumbr','ventana','falda','admis','cárter','conduct','válv','escape','transfer','distribu','alzada','garganta','asiento')) else 'geometry'
            if 'nombre' in lower:key='summary'
            self.issue_routes.setdefault(key,[]).append(error)
        for key,messages in self.issue_routes.items():
            title={'geometry':'Geometría','summary':'Datos del proyecto'}.get(key,'Motor '+cycle)
            button=QPushButton(title+' · '+str(len(messages))+' observaciones →')
            button.setToolTip('\n'.join(dict.fromkeys(messages)));button.clicked.connect(lambda checked=False,k=key:w.navigation.go(k))
            if key=='summary':button.clicked.connect(lambda:self.tabs.setCurrentIndex(1))
            self.attention.addWidget(button)
        for page in (w.motor2_page,w.motor4_page):
            page.errors.setText('\n'.join(self.issue_routes.get(page.key,[])))


class MotorPage(QScrollArea):
    def __init__(self,cycle,sections):
        super().__init__();self.key='motor2' if cycle=='2T' else 'motor4'
        self.setWidgetResizable(True);self.setFrameShape(QScrollArea.Shape.NoFrame)
        body=QWidget();self.setWidget(body);box=QVBoxLayout(body);box.setContentsMargins(20,18,20,18);box.setSpacing(16)
        box.addWidget(Header('Motor '+cycle,'Configuración admitida · '+('Lumbreras, admisión y cárter; conductos del motor.' if cycle=='2T' else 'Válvulas, distribución y conductos del motor.'),'Geometría idealizada · Sin validación experimental.'))
        self.tabs=QTabWidget();self.tabs.setMinimumHeight(440)
        for title,widget in sections:
            for heading in widget.findChildren(QLabel,'pageTitle'):heading.hide()
            self.tabs.addTab(widget,title)
        context_panel=Panel('CONTEXTO DEL MOTOR')
        self.overview=label('','unit');self.overview.hide()
        self.context=QPlainTextEdit();self.context.setReadOnly(True);self.context.setMinimumHeight(240)
        context_panel.content.addWidget(self.context)
        self.errors=label('','fieldError');self.errors.hide()
        self.context_button=QPushButton('Contexto y observaciones');self.context_button.hide()
        self.context_state=label('','sectionTitle');context_panel.content.insertWidget(1,self.context_state)
        box.addWidget(Columns(self.tabs,context_panel,1080,(3,1)),1)
    def refresh_context(self,text):
        self.overview.setText('\n'.join(text.splitlines()[:2]))
        self.context.setPlainText(text+'\n\nEjecutabilidad\n'+(self.errors.text() or 'Sin observaciones en esta sección.'))
        count=len(self.errors.text().splitlines()) if self.errors.text() else 0
        self.context_button.setText('Contexto y observaciones'+(f' · {count} por revisar' if count else ''))
        self.context_state.setText(f'{count} observaciones por revisar' if count else 'Sin observaciones en esta sección')


class ResultWorkspace(QWidget):
    def __init__(self,simulation):
        super().__init__();self.simulation=simulation;layout=QVBoxLayout(self);layout.setContentsMargins(18,12,18,12)
        layout.addWidget(Header('Resultados','Consultá una ejecución o los puntos de un barrido guardado.','Los archivos conservan su procedencia; consultarlos no ejecuta cálculos.'))
        source=Panel('FUENTE DE DATOS');actions=QGridLayout();source.content.addLayout(actions);layout.addWidget(source)
        for i,button in enumerate((simulation.open_button,simulation.open_sweep_button,simulation.sweep_button)):
            actions.addWidget(button,i//2,i%2)
        simulation.open_button.setObjectName('primaryAction')
        self.message_host=QVBoxLayout();layout.addLayout(self.message_host)
        self.tabs=QTabWidget();layout.addWidget(self.tabs,1)
        self.detail=QWidget();self.detail_layout=QVBoxLayout(self.detail);self.detail_layout.setContentsMargins(0,0,0,0)
        self.tabs.addTab(scroll(self.detail),'Resultado actual')
        self.series=QWidget();self.series_layout=QVBoxLayout(self.series);self.series_layout.setContentsMargins(0,0,0,0)
        self.tabs.addTab(scroll(self.series),'Barrido cargado')
        self.empty=Panel('NO HAY BARRIDO ABIERTO');self.empty.content.addWidget(label('Abrí un barrido guardado. Podrás seleccionar un punto convergido y consultar sus curvas, entradas y balances.','unit'));self.series_layout.addWidget(self.empty)
    def show_series(self,dialog):
        self.empty.hide()
        dialog.setWindowFlags(Qt.WindowType.Widget);self.series_layout.addWidget(dialog)
        for button in dialog.findChildren(QPushButton):
            if button.text()=='Cerrar':button.hide()
        dialog.show();self.tabs.setCurrentIndex(1)
    def show_result(self):self.tabs.setCurrentIndex(0)


def refresh_motor_context(owner):
    """Formatea salidas de las funciones geométricas existentes, sin otras reglas."""
    from .ports import port_results
    from .ducts import route_geometry, format_geometry
    from .valves import area
    w=owner
    try:
        try:project=w.project()
        except ProjectError:project,_=w.execution_snapshot()
    except ProjectError:
        w.motor2_page.refresh_context('Borrador con entradas inválidas · revisar campos\n'+w.ports_view.input_error.text())
        w.motor4_page.refresh_context('Borrador con entradas inválidas · revisar campos\n'+w.valves_view.crossing.text())
        return
    two=[f'Lumbreras: {len(project.ports)}', 'Cárter PMI: '+(str(project.crankcase_volume_bdc_cm3) if project.crankcase_volume_bdc_cm3 is not None else '—')+' cm³']
    for p in project.ports:
        r=port_results(p,project.stroke_mm,project.rod_length_mm)
        two.append(f'{p.function or "Sin función"} · {p.name or "Sin nombre"}: '+
            (f'{r.opening:g}°–{r.closing:g}°' if r.opening is not None and r.closing is not None else '—'))
    two.append(w.ports_view.intake.results.text())
    four=[w.valves_view.crossing.text()]
    for route,title in (('intake','Admisión'),('exhaust','Escape')):
        valve=getattr(project.four_stroke,route)
        four.append(title+': '+w.valves_view.outputs[route].text())
        if w.valves_view.plots[route][0].values:
            four.append(f'Alzada máxima: {valve.lift_mm:g} mm · Área máxima: {area(valve,valve.opening_deg+valve.duration_deg/2):.2f} mm²')
    for target,ducts in ((two,project.ducts),(four,project.four_stroke.ducts)):
        for route,title in (('intake','Admisión'),('exhaust','Escape')):
            data=route_geometry(getattr(ducts,route))
            target.append(f'Conducto {title}: {format_geometry(data.length)} mm · {format_geometry(data.volume)} cm³')
    w.motor2_page.refresh_context('\n'.join(two));w.motor4_page.refresh_context('\n'.join(four))
