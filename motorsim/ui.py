"""Contenedores visuales compartidos; sin estado ni reglas del dominio."""
from PySide6.QtCore import Qt, QSize, Signal
from PySide6.QtWidgets import QWidget, QFrame, QLabel, QVBoxLayout, QHBoxLayout, QGridLayout, QSizePolicy, QToolButton, QLayout


def text(value='',role=''):
    widget=QLabel(value);widget.setObjectName(role)
    widget.setTextFormat(Qt.TextFormat.PlainText);widget.setWordWrap(True)
    widget.setMinimumWidth(0)
    return widget


class Header(QWidget):
    def __init__(self,title,subtitle,notice=''):
        super().__init__();box=QVBoxLayout(self);box.setContentsMargins(0,0,0,6);box.setSpacing(5)
        box.addWidget(text(title,'pageTitle'));box.addWidget(text(subtitle,'subtitle'))
        if notice:box.addWidget(text(notice,'unit'))
        line=QFrame();line.setObjectName('separator');line.setFixedHeight(1);box.addWidget(line)


class Panel(QFrame):
    def __init__(self,title):
        super().__init__();self.setObjectName('panel')
        box=QVBoxLayout(self);box.setContentsMargins(0,0,0,0);box.setSpacing(0)
        self.heading=text(title,'panelHeader');self.heading.setSizePolicy(QSizePolicy.Policy.Expanding,QSizePolicy.Policy.Fixed);box.addWidget(self.heading)
        body=QWidget();body.setObjectName('panelBody');box.addWidget(body)
        self.content=QVBoxLayout(body);self.content.setContentsMargins(12,12,12,12);self.content.setSpacing(8)
        self.content.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.content.setVerticalSizeConstraint(QLayout.SizeConstraint.SetMinimumSize)
        box.setVerticalSizeConstraint(QLayout.SizeConstraint.SetMinimumSize)
        self.setSizePolicy(QSizePolicy.Policy.Expanding,QSizePolicy.Policy.Preferred)


class Columns(QWidget):
    """Dos paneles adyacentes o apilados según el ancho realmente disponible."""
    def __init__(self,left,right,threshold=850,ratios=(1,1)):
        super().__init__();self.left,self.right=left,right;self.threshold=threshold;self.ratios=ratios
        self.grid=QGridLayout(self);self.grid.setContentsMargins(0,0,0,0);self.grid.setSpacing(12)
        self.wide=None;self.arrange()
    def arrange(self):
        wide=self.width()>=self.threshold
        if wide==self.wide:return
        self.wide=wide
        self.grid.addWidget(self.left,0,0)
        self.grid.addWidget(self.right,0 if wide else 1,1 if wide else 0)
        self.grid.setColumnStretch(0,self.ratios[0] if wide else 1)
        self.grid.setColumnStretch(1,self.ratios[1] if wide else 0)
    def resizeEvent(self,event):
        super().resizeEvent(event);self.arrange()
    def minimumSizeHint(self):
        # El mínimo de la disposición ancha no debe impedir que colapse.
        hint=super().minimumSizeHint()
        return QSize(0,hint.height())


def visual_state(widget, state):
    widget.setProperty('state',state)
    widget.style().unpolish(widget);widget.style().polish(widget)


class Badge(QLabel):
    def __init__(self,value='',state='neutral'):
        super().__init__();self.setObjectName('badge')
        self.setSizePolicy(QSizePolicy.Policy.Maximum,QSizePolicy.Policy.Preferred)
        self.set_state(value,state)
    def set_state(self,value,state):
        self.setText(value);visual_state(self,state)


class Message(QLabel):
    """Texto compartido entre presentación de ejecución y consulta, sin copiar datos."""
    changed=Signal(str)
    def __init__(self,value='',role=''):
        super().__init__();self.setObjectName(role);self.setWordWrap(True);self.setMinimumWidth(0)
        self.setTextFormat(Qt.TextFormat.PlainText);self.setText(value)
    def setText(self,value):
        super().setText(value);self.changed.emit(value)
    def clear(self):self.setText('')


class ValidationMessage(Message):
    def __init__(self):super().__init__('','fieldError')
    def setText(self,value):
        super().setText(value)
        visual_state(self,'success' if value.startswith('Entradas admitidas') else 'error')


class NumericUnit(QWidget):
    def __init__(self,edit,unit,error=None):
        super().__init__();box=QVBoxLayout(self);box.setContentsMargins(0,0,0,0);box.setSpacing(4)
        row=QHBoxLayout();row.setContentsMargins(0,0,0,0);row.setSpacing(8)
        row.addWidget(edit,1);row.addWidget(text(unit,'unit'));box.addLayout(row)
        if error is not None:box.addWidget(error)


class PropertyTable(QWidget):
    def __init__(self,names):
        super().__init__();grid=QGridLayout(self);grid.setContentsMargins(0,0,0,0)
        grid.setHorizontalSpacing(14);grid.setVerticalSpacing(8);grid.setColumnStretch(1,1)
        self.values={}
        for row,name in enumerate(names):
            grid.addWidget(text(name,'unit'),row,0,Qt.AlignmentFlag.AlignTop)
            value=text('—','propertyValue');value.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTop)
            value.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            grid.addWidget(value,row,1);self.values[name]=value
    def set_value(self,name,value):self.values[name].setText(str(value))


class ContextPanel(QFrame):
    def __init__(self):
        super().__init__();self.setObjectName('panel');self.summary='';self.compact=None
        box=QVBoxLayout(self);box.setContentsMargins(0,0,0,0);box.setSpacing(0)
        self.toggle=QToolButton();self.toggle.setObjectName('contextHeader');self.toggle.setCheckable(True)
        self.toggle.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.toggle.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Fixed)
        self.toggle.setAccessibleName('Expandir o contraer contexto del modelo')
        box.addWidget(self.toggle);self.body=QWidget();self.body.setObjectName('panelBody');box.addWidget(self.body)
        self.content=QVBoxLayout(self.body);self.content.setContentsMargins(12,12,12,12)
        self.toggle.toggled.connect(self._toggle)
    def set_summary(self,value):self.summary=value;self.toggle.setToolTip(value);self._caption()
    def set_compact(self,compact):
        if self.compact==compact:return
        self.compact=compact;self.toggle.setChecked(not compact);self._toggle(not compact)
    def _toggle(self,opened):
        self.body.setVisible(opened);self.toggle.setArrowType(Qt.ArrowType.DownArrow if opened else Qt.ArrowType.RightArrow);self._caption()
    def _caption(self):
        caption='03 · CONTEXTO DEL MODELO'
        if not self.toggle.isChecked():caption+=' · '+self.summary
        self.toggle.setText(self.fontMetrics().elidedText(caption,Qt.TextElideMode.ElideRight,max(40,self.width()-40)))
    def resizeEvent(self,event):super().resizeEvent(event);self._caption()


class SimulationColumns(QWidget):
    def __init__(self,preparation,center,context):
        super().__init__();self.parts=(preparation,center,context);self.mode=None
        self.grid=QGridLayout(self);self.grid.setContentsMargins(0,0,0,0);self.grid.setSpacing(12)
        self.arrange()
    def arrange(self):
        width=self.width();mode=3 if width>=1400 else 2 if width>=850 else 1
        if mode==self.mode:return
        self.mode=mode
        for part in self.parts:self.grid.removeWidget(part)
        for column in range(3):self.grid.setColumnStretch(column,0)
        for row in range(3):self.grid.setRowStretch(row,0)
        prep,center,context=self.parts
        self.grid.addWidget(prep,0,0,Qt.AlignmentFlag.AlignTop)
        self.grid.addWidget(center,1 if mode==1 else 0,0 if mode==1 else 1)
        if mode==3:
            self.grid.addWidget(context,0,2,Qt.AlignmentFlag.AlignTop)
            for i,stretch in enumerate((3,8,3)):self.grid.setColumnStretch(i,stretch)
        else:
            self.grid.addWidget(context,2 if mode==1 else 1,0,1,mode,Qt.AlignmentFlag.AlignTop)
            self.grid.setColumnStretch(0,1 if mode==1 else 3)
            self.grid.setColumnStretch(1,0 if mode==1 else 7)
        context.set_compact(mode!=3)
    def resizeEvent(self,event):super().resizeEvent(event);self.arrange()
    def minimumSizeHint(self):return QSize(0,super().minimumSizeHint().height())
