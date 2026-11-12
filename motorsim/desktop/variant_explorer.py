"""Exact configuration differences, independent of numerical result comparison."""
import json
from PySide6.QtWidgets import QDialog,QVBoxLayout,QLabel,QTableWidget,QTableWidgetItem,QHeaderView


def differences(before,after,path=()):
    if isinstance(before,dict) and isinstance(after,dict):
        return [row for key in sorted(set(before)|set(after)) for row in differences(before.get(key),after.get(key),(*path,str(key)))]
    if isinstance(before,list) and isinstance(after,list):
        return [row for i in range(max(len(before),len(after))) for row in differences(before[i] if i<len(before) else None,after[i] if i<len(after) else None,(*path,str(i)))]
    return [] if before==after else [('.'.join(path),before,after)]


def show_variant_diff(parent,before,after,name):
    dialog=QDialog(parent);dialog.setWindowTitle('Diferencias de configuración');dialog.resize(850,480)
    layout=QVBoxLayout(dialog);label=QLabel(f'Motor base → {name}. Valores aplicados exactos; no predicen diferencias de prestaciones. Las unidades están identificadas en las rutas y formularios.');label.setWordWrap(True);layout.addWidget(label)
    rows=differences(before,after);table=QTableWidget(len(rows),3);table.setHorizontalHeaderLabels(['Parámetro','Motor base','Variante'])
    table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers);table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
    for r,row in enumerate(rows):
        for c,value in enumerate(row):table.setItem(r,c,QTableWidgetItem(value if c==0 else json.dumps(value,ensure_ascii=False)))
    layout.addWidget(table)
    if not rows:layout.addWidget(QLabel('No hay diferencias en la configuración aplicada.'))
    dialog.exec()
