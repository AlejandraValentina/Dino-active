from __future__ import annotations

import math

from PySide6.QtWidgets import (QComboBox,QDialog,QDialogButtonBox,QDoubleSpinBox,
    QFormLayout,QHBoxLayout,QLabel,QLineEdit,QMessageBox,QVBoxLayout,QWidget)

from .services import new_design_project


class NewEngineDialog(QDialog):
    """Create a 2T or 4T project from its own versioned starter configuration."""
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
        super().__init__(parent);self.setWindowTitle("Crear proyecto de motor");self.setMinimumWidth(560)
        root=QVBoxLayout(self)
        intro=QLabel("Elegí el ciclo del motor. Dino Desktop conserva proyectos y solvers 2T y 4T separados. Las plantillas iniciales son sintéticas.")
        intro.setWordWrap(True);intro.setObjectName("notice");root.addWidget(intro)
        form=QFormLayout();root.addLayout(form)
        self.project_name=QLineEdit("dino-proyecto-nuevo");form.addRow("Nombre del proyecto",self.project_name)
        self.engine_name=QLineEdit("Motor nuevo");form.addRow("Nombre del motor",self.engine_name)
        self.cycle=QComboBox();self.cycle.addItem("Dos tiempos (2T)","2T");self.cycle.addItem("Cuatro tiempos (4T)","4T");form.addRow("Familia",self.cycle)
        self.two_stroke_panel=QWidget();two_form=QFormLayout(self.two_stroke_panel);root.addWidget(self.two_stroke_panel)
        self.inputs={};self.sources={}
        for key,label,unit,low,high,default in self.FIELDS:
            row=QWidget();layout=QHBoxLayout(row);layout.setContentsMargins(0,0,0,0)
            spin=QDoubleSpinBox();spin.setRange(low,high);spin.setDecimals(2);spin.setValue(default);spin.setSuffix(" "+unit);spin.setMaximumWidth(220)
            source=QComboBox()
            for visible,value in self.SOURCES:source.addItem(visible,value)
            source.setCurrentIndex(2);source.setToolTip("Clasificación de procedencia de este dato")
            layout.addWidget(spin);layout.addWidget(QLabel("Origen"));layout.addWidget(source);layout.addStretch(1)
            two_form.addRow(label,row);self.inputs[key]=spin;self.sources[key]=source;spin.valueChanged.connect(self._update_derived)
        self.intake=QComboBox();self.intake.addItem("Láminas (reed)","reed");self.intake.addItem("Control por pistón","piston_port")
        two_form.addRow("Tipo de admisión",self.intake)
        self.derived=QLabel();self.derived.setWordWrap(True);self.derived.setObjectName("notice");two_form.addRow("Magnitudes derivadas",self.derived)
        self.four_info=QLabel("El proyecto 4T comienza con la configuración DINO4T_API_V1 de ejemplo, etiquetada como sintética. En MODELO se editan válvulas, distribución, cilindro, admisión, escape y combustión.")
        self.four_info.setWordWrap(True);root.addWidget(self.four_info)
        self.cycle.currentIndexChanged.connect(self._cycle_changed)
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel|QDialogButtonBox.StandardButton.Ok)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Crear proyecto")
        buttons.accepted.connect(self._create);buttons.rejected.connect(self.reject);root.addWidget(buttons)
        self.project=None;self._update_derived();self._cycle_changed()

    def _update_derived(self,*_):
        bore=self.inputs["bore_mm"].value();stroke=self.inputs["stroke_mm"].value()
        swept=math.pi*bore*bore*stroke/4000.0;ratio=self.inputs["cylinder_compression_ratio"].value()
        clearance=swept/(ratio-1.0);crankcase=self.inputs["volume_bdc_cm3"].value();primary=1.0+(swept/crankcase)
        self.derived.setText(f"Cilindrada: {swept:.2f} cm³ · Cámara compatible con CR: {clearance:.2f} cm³ · Compresión primaria: {primary:.2f}:1")

    def _cycle_changed(self,*_):
        four=self.cycle.currentData()=="4T";self.two_stroke_panel.setVisible(not four);self.four_info.setVisible(four)
        self.engine_name.setText("Motor 4T nuevo" if four else "Motor 2T nuevo")

    def _create(self):
        try:
            name=self.project_name.text().strip()
            if not name:raise ValueError("Ingresá un nombre de proyecto.")
            if self.cycle.currentData()=="4T":
                from .four_stroke_project import project_from_example,config_identity
                self.project=project_from_example(name)
                self.project["base_engine"]["identifier"]=self.engine_name.text().strip() or f"{name}-motor"
                self.project["base_identity_sha256"]=config_identity(self.project["base_engine"])
                self.accept();return
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
