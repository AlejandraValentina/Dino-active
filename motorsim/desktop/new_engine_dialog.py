from __future__ import annotations

import math

from PySide6.QtWidgets import (QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox,
    QFormLayout, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QVBoxLayout, QWidget)

from .services import new_design_project


class NewEngineDialog(QDialog):
    """Guided starter design. All template values remain explicitly assumed."""
    FIELDS=(
        ("bore_mm","Diámetro", "mm",1.0,250.0,56.0),
        ("stroke_mm","Carrera", "mm",1.0,250.0,50.6),
        ("rod_length_mm","Longitud de biela", "mm",1.0,500.0,110.0),
        ("volume_bdc_cm3","Volumen de cárter en PMI", "cm³",0.1,5000.0,356.08),
        ("cylinder_compression_ratio","Relación de compresión geométrica", ":1",1.01,40.0,17.71),
        ("reference_rpm","RPM de referencia", "rpm",100.0,30000.0,9000.0),
    )
    SOURCES=(("Medido","MEASURED"),("Estimado","ESTIMATED"),("Supuesto","SYNTHETIC_ASSUMPTION"))

    def __init__(self,parent=None):
        super().__init__(parent);self.setWindowTitle("Crear motor 2T");self.setMinimumWidth(560)
        root=QVBoxLayout(self)
        intro=QLabel("Configurá un motor monocilíndrico de dos tiempos. Los valores iniciales son supuestos sintéticos. La cámara, los eventos de lumbreras y la compresión primaria se calculan desde la geometría indicada.")
        intro.setWordWrap(True);intro.setObjectName("notice");root.addWidget(intro)
        form=QFormLayout();root.addLayout(form)
        self.project_name=QLineEdit("dino-2t-nuevo");form.addRow("Nombre del proyecto",self.project_name)
        self.engine_name=QLineEdit("Motor nuevo");form.addRow("Nombre del motor",self.engine_name)
        self.inputs={};self.sources={}
        for key,label,unit,low,high,default in self.FIELDS:
            row=QWidget();layout=QHBoxLayout(row);layout.setContentsMargins(0,0,0,0)
            spin=QDoubleSpinBox();spin.setRange(low,high);spin.setDecimals(2);spin.setValue(default);spin.setSuffix(" "+unit);spin.setMaximumWidth(220)
            source=QComboBox()
            for visible,value in self.SOURCES:source.addItem(visible,value)
            source.setCurrentIndex(2);source.setToolTip("Clasificación de provenance de este dato")
            layout.addWidget(spin);layout.addWidget(QLabel("Origen"));layout.addWidget(source);layout.addStretch(1)
            form.addRow(label,row);self.inputs[key]=spin;self.sources[key]=source
            spin.valueChanged.connect(self._update_derived)
        self.intake=QComboBox();self.intake.addItem("Láminas (reed)","reed");self.intake.addItem("Control por pistón","piston_port")
        form.addRow("Tipo de admisión",self.intake)
        self.derived=QLabel();self.derived.setWordWrap(True);self.derived.setObjectName("notice");form.addRow("Magnitudes derivadas",self.derived)
        detail=QLabel("La plantilla estructural parte de un caso sintético existente para conservar conexiones admitidas; no incluye sus corridas ni resultados. Las lumbreras, el tipo de admisión y el escape se pueden revisar en Motor y Escape. Sus valores iniciales quedan clasificados como supuestos.")
        detail.setWordWrap(True);root.addWidget(detail)
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel|QDialogButtonBox.StandardButton.Ok)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Crear motor")
        buttons.accepted.connect(self._create);buttons.rejected.connect(self.reject);root.addWidget(buttons)
        self.project=None;self._update_derived()

    def _update_derived(self,*_):
        bore=self.inputs["bore_mm"].value();stroke=self.inputs["stroke_mm"].value()
        swept=math.pi*bore*bore*stroke/4000.0
        ratio=self.inputs["cylinder_compression_ratio"].value()
        clearance=swept/(ratio-1.0)
        crankcase=self.inputs["volume_bdc_cm3"].value()
        primary=1.0+(swept/crankcase)
        self.derived.setText(f"Cilindrada: {swept:.2f} cm³ · Volumen de cámara compatible con CR: {clearance:.2f} cm³ · Compresión primaria: {primary:.2f}:1")

    def _create(self):
        try:
            name=self.project_name.text().strip()
            if not name:raise ValueError("Ingresá un nombre de proyecto.")
            if self.inputs["rod_length_mm"].value()<=self.inputs["stroke_mm"].value()/2:
                raise ValueError("La longitud de biela debe superar el radio de manivela.")
            values={key:spin.value() for key,spin in self.inputs.items()};values["intake_control"]=self.intake.currentData()
            sources={key:combo.currentData() for key,combo in self.sources.items()}
            self.project=new_design_project(name,values,sources)
            self.project["base_engine"]["display_name"]=self.engine_name.text().strip() or "Motor nuevo"
            from ..engine_configuration import identity
            self.project["base_identity_sha256"]=identity(self.project["base_engine"])
            self.accept()
        except Exception as exc:
            QMessageBox.warning(self,"Configuración no válida",f"Revisá los datos del motor. {type(exc).__name__}: {exc}")
