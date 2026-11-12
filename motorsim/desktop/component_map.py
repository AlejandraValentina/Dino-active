"""Topological component navigator. Routes only to public frontend editors."""
from dataclasses import dataclass
from PySide6.QtCore import Qt, QPointF, QObject, QEvent
from PySide6.QtGui import QPainter,QColor,QPen,QAction
from PySide6.QtWidgets import QWidget,QToolButton,QLabel,QVBoxLayout,QDockWidget,QLineEdit,QAbstractSpinBox,QScrollArea


@dataclass(frozen=True)
class Component:
    key: str
    label: str
    x: float
    y: float


COMMON=(Component('intake','Admisión',.03,.27),Component('cylinder','Cilindro / pistón',.35,.43),Component('exhaust','Escape',.68,.27))
TWO=(*COMMON,Component('ports','Lumbreras',.35,.17),Component('crankcase','Cárter / biela',.35,.74),Component('transfer','Transferencias',.03,.62),Component('combustion','Combustión',.68,.04))
FOUR=(*COMMON,Component('intake_valve','Válvula adm.',.03,.04),Component('exhaust_valve','Válvula esc.',.68,.04),Component('geometry','Biela / compresión',.35,.74))


class ComponentMap(QWidget):
    def __init__(self,components,activate,parent=None):
        super().__init__(parent);self.components=components;self.buttons={};self.selected=None
        self.setMinimumSize(270,280)
        for component in components:
            button=QToolButton(self);button.setText({'cylinder':'Cilindro /\npistón','crankcase':'Cárter /\nbiela','transfer':'Transf.','intake_valve':'Válvula\nadmisión','exhaust_valve':'Válvula\nescape','geometry':'Biela /\ncompresión'}.get(component.key,component.label));button.setCheckable(True)
            button.setAccessibleName('Editar '+component.label);button.setToolTip('Seleccionar '+component.label+' y abrir sus parámetros')
            button.clicked.connect(lambda _,key=component.key:activate(key));self.buttons[component.key]=button

    def select(self,key):
        self.selected=key
        for name,button in self.buttons.items():button.setChecked(name==key)
        self.update()

    def resizeEvent(self,event):
        width=self.width();height=self.height()
        for c in self.components:self.buttons[c.key].setGeometry(round(c.x*width),round(c.y*height),round(width*.31),40)
        super().resizeEvent(event)

    def paintEvent(self,event):
        painter=QPainter(self);painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(),QColor('#101a28'));painter.setPen(QPen(QColor('#718ba6'),2))
        w,h=self.width(),self.height()
        # Schematic connectivity, not dimensional or simulated positions.
        edges=(('intake','crankcase'),('crankcase','transfer'),('transfer','ports'),('ports','cylinder'),('cylinder','exhaust'),('combustion','cylinder')) if 'crankcase' in self.buttons else (('intake','intake_valve'),('intake_valve','cylinder'),('cylinder','exhaust_valve'),('exhaust_valve','exhaust'),('cylinder','geometry'))
        for a,b in edges:
            energy=a=='combustion';mechanical=b=='geometry'
            painter.setPen(QPen(QColor('#f6bd60' if energy else '#718ba6' if mechanical else '#43c5f5'),2,Qt.PenStyle.DashLine if energy or mechanical else Qt.PenStyle.SolidLine))
            painter.drawLine(QPointF(self.buttons[a].geometry().center()),QPointF(self.buttons[b].geometry().center()))
        painter.setPen(QPen(QColor('#718ba6'),2));painter.drawRect(round(.44*w),round(.58*h),round(.14*w),round(.08*h))
        painter.drawLine(round(.51*w),round(.66*h),round(.51*w),round(.75*h))
        painter.end()


class ComponentNavigator(QObject):
    def __init__(self,window):
        super().__init__(window);self._field_components={}
        self.window=window;self.dock=QDockWidget('Componentes del motor',window)
        self.dock.setObjectName('physicalComponentNavigator');self.dock.setMinimumWidth(285)
        body=QWidget();layout=QVBoxLayout(body)
        self.family=QLabel();self.family.setWordWrap(True);layout.addWidget(self.family)
        self.map=ComponentMap(TWO,self.activate);layout.addWidget(self.map,1)
        self.detail=QLabel();self.detail.setWordWrap(True);self.detail.setTextFormat(Qt.TextFormat.PlainText);self.detail.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse);layout.addWidget(self.detail)
        legend=QLabel('Gas: azul · combustión: ámbar · cinemática: gris');legend.setWordWrap(True);layout.addWidget(legend)
        note=QLabel('Esquema funcional, sin escala. Seleccioná un componente para editar. Los valores son los aplicados; el borrador permanece en el formulario.');note.setWordWrap(True);layout.addWidget(note)
        self.dock.setWidget(body);window.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea,self.dock)
        self.action=self.dock.toggleViewAction();self.action.setText('Componentes del motor');self.action.setShortcut('Ctrl+Shift+M');next(a.menu() for a in window.menuBar().actions() if a.text()=='Vista').addAction(self.action)
        for context in (window.context,window.native_four_stroke.context,window.four_stroke_context):context.changed.connect(self.refresh)
        window.engine_family_changed.connect(self.refresh)
        window.pages[0].component_tabs.currentChanged.connect(lambda *_:self.follow_editor())
        window.native_four_stroke.editor.sections.currentChanged.connect(lambda *_:self.follow_editor())
        window.four_stroke_workspace.tabs.currentChanged.connect(lambda *_:self.follow_editor())
        self.refresh();self.dock.hide()  # Explicitly opened; compact layouts retain editor width.

    def routes(self):
        w=self.window
        if w._native_four_stroke_active():
            return {k:(w.native_four_stroke.editor.sections,section) for k,section in dict(cylinder='geometry',geometry='geometry',intake='intake_duct',exhaust='exhaust_duct',intake_valve='intake_valve',exhaust_valve='exhaust_valve').items()}
        if w._four_stroke_active():return {k:(w.four_stroke_workspace.tabs,i) for k,i in dict(cylinder=0,geometry=0,intake_valve=1,exhaust_valve=1,intake=2,exhaust=2).items()}
        tabs=w.pages[0].component_tabs
        return {**{k:(tabs,i) for k,i in dict(cylinder=0,ports=1,combustion=3,intake=4,crankcase=5,transfer=8).items()},'exhaust':(None,None)}

    def activate(self,key):
        w=self.window;w.set_workspace_mode(0)
        route=self.routes().get(key)
        if route is None:return
        tabs,index=route
        if tabs is None:
            w.component_nav.setCurrentIndex(2)
            target=w.pages[1]
        else:
            if isinstance(index,str):
                keys=list(w.native_four_stroke.editor.tables)
                if index not in keys:return
                index=keys.index(index)
            if not w._native_four_stroke_active() and not w._four_stroke_active():
                w.component_nav.setCurrentIndex({0:0,1:1,2:3,3:4,4:6,5:7,6:8,7:9,8:10}[index])
            tabs.setCurrentIndex(index);target=tabs.currentWidget()
        fields=target.findChildren(QLineEdit)+target.findChildren(QAbstractSpinBox)
        field=next((f for f in fields if f.isVisible() and f.isEnabled()),None)
        if w._four_stroke_active():
            workspace=w.four_stroke_workspace
            if key in ('intake_valve','exhaust_valve'):field=next(iter(workspace.valves.fields[key.split('_')[0]].values()))
            elif key in ('intake','exhaust'):
                duct=getattr(workspace.ducts,key);field=duct.table if duct.table.rowCount() else duct.add_button
            elif key=='geometry':field=workspace.geometry.rod
            elif key=='cylinder':field=workspace.geometry.bore
        if isinstance(target,QScrollArea) and field:target.ensureWidgetVisible(field)
        if field:field.setFocus(Qt.FocusReason.ShortcutFocusReason)
        self.map.select(key);self.refresh_detail(key)

    def follow_editor(self):
        w=self.window
        for key,(tabs,index) in self.routes().items():
            if tabs is None:continue
            if isinstance(index,str):
                keys=list(w.native_four_stroke.editor.tables)
                if index not in keys:continue
                index=keys.index(index)
            if tabs.currentIndex()==index:self.map.select(key);self.refresh_detail(key);break

    def refresh(self,*_):
        w=self.window;native=w._native_four_stroke_active();reference=w._four_stroke_active()
        components=FOUR if native or reference else TWO
        if self.map.components!=components:
            layout=self.map.parentWidget().layout();old=self.map;self.map=ComponentMap(components,self.activate);layout.replaceWidget(old,self.map);old.deleteLater()
        self.family.setText('4T nativo' if native else '4T 0D · referencia sintética' if reference else '2T integrado')
        self._bind_fields();self.follow_editor()

    def refresh_detail(self,key):
        from .component_adapters import applied_component_summary
        self.detail.setText(applied_component_summary(self.window,key))

    def _bind_fields(self):
        w=self.window;self._field_components={}
        for side,fields in w.four_stroke_workspace.valves.fields.items():
            for field in fields.values():self._field_components[id(field)]=side+'_valve';field.installEventFilter(self)
        for path,field in w.native_four_stroke.editor.fields.items():
            key=dict(geometry='geometry' if path[-1]=='rod_mm' else 'cylinder',intake_valve='intake_valve',exhaust_valve='exhaust_valve',intake_duct='intake',exhaust_duct='exhaust').get(path[0])
            if key:self._field_components[id(field)]=key;field.installEventFilter(self)

    def eventFilter(self,watched,event):
        if event.type()==QEvent.Type.FocusIn:
            key=self._field_components.get(id(watched))
            if key and key in self.map.buttons:self.map.select(key);self.refresh_detail(key)
        return False
