"""Physical parameter presentation over the native editor's exact source cells."""
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QFormLayout,QLineEdit,QComboBox,
    QCheckBox,QPushButton,QScrollArea,QLabel)

ENUMS={
    'provenance':['SYNTHETIC_ASSUMPTION','STANDARD_V1','MEASURED','DOCUMENTED','CALIBRATED'],
    'zone_model':['single_zone','two_zone_equilibrium'],
    'restriction_model':['V1','V2'],
    'limiter':['minmod','van_leer','mc','unlimited_central'],
}


def section_form(editor,section,table):
    from .four_stroke_desktop import _path_label,DISPLAY_VALUES
    page=QWidget();layout=QVBoxLayout(page);layout.setContentsMargins(12,8,12,8)
    hint=QLabel('Magnitudes del componente · las unidades y las fuentes se conservan. Aplicá los cambios antes de guardar o ejecutar.')
    hint.setWordWrap(True);layout.addWidget(hint)
    form=QFormLayout();form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
    form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
    layout.addLayout(form)
    for row in range(table.rowCount()):
        item=table.item(row,1);path=tuple(item.data(256));value=editor._original[path]
        label=_path_label(path).split(' · ',1)[-1]
        if path[-1]=='provenance':label='Fuente declarada de estos datos'
        if isinstance(value,bool):
            field=QCheckBox('Activado');field.setChecked(value)
            field.toggled.connect(lambda v,cell=item:cell.setText('true' if v else 'false'))
        elif isinstance(value,str) and path[-1] in ENUMS:
            field=QComboBox()
            for option in dict.fromkeys([value,*ENUMS[path[-1]]]):field.addItem(DISPLAY_VALUES.get(option,option),option)
            field.setCurrentIndex(field.findData(value))
            field.currentIndexChanged.connect(lambda _,w=field,cell=item:cell.setText(DISPLAY_VALUES.get(str(w.currentData()),str(w.currentData()))))
        else:
            field=QLineEdit()
            # Presentation rounding never writes into the source document.
            field.setText(format(value,'.10g') if isinstance(value,float) else editor._display(value))
            field.textEdited.connect(lambda text,cell=item:cell.setText(text))
        field.setObjectName('nativeField_'+'_'.join(path));field.setAccessibleName(label)
        field.setToolTip(_path_label(path)+'\nValor aplicado exacto: '+editor._display(value)+
            '\nLa validación de aplicación usa el contrato del modelo; no acredita validación experimental.')
        editor.fields[path]=field
        def sync(changed,cell=item,w=field):
            if changed is not cell:return
            if isinstance(w,QLineEdit):w.setText(cell.text())
            elif isinstance(w,QCheckBox):w.setChecked(cell.text()=='true')
            elif isinstance(w,QComboBox):
                index=w.findText(cell.text())
                if index>=0:w.setCurrentIndex(index)
        table.itemChanged.connect(sync)
        form.addRow(label[:1].upper()+label[1:],field)
    advanced=QPushButton('Ver datos avanzados del componente')
    advanced.setCheckable(True);layout.addWidget(advanced)
    table.setVisible(False);layout.addWidget(table)
    advanced.toggled.connect(table.setVisible)
    layout.addStretch(1)
    scroll=QScrollArea();scroll.setWidgetResizable(True);scroll.setFrameShape(QScrollArea.Shape.NoFrame);scroll.setWidget(page)
    return scroll
