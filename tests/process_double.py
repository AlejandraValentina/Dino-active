"""QProcess con hijo sin integrador para los controles de interfaz."""
from pathlib import Path
from PySide6.QtCore import QProcess


class DiagnosticProcess(QProcess):
    def setArguments(self,args):
        assert args[:3]==['-u','-m','motorsim.reference_run'],args
        super().setArguments(['-u',str(Path(__file__).with_name('calculation_double.py')),*args[3:]])
