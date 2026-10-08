"""Identidad y rutas de distribución; sin Qt ni búsqueda de Python externo."""
from datetime import datetime
import json
import os
from pathlib import Path
import sys
import traceback
import uuid

APP_VERSION = '0.1.0-rc6'


def resource(name):
    return Path(__file__).resolve().parent/name


def build_info():
    path=resource('build.json')
    if getattr(sys,'frozen',False):
        data=json.loads(path.read_text(encoding='utf-8'))
        if data['app_version']!=APP_VERSION:raise ValueError('Versión de compilación incoherente.')
        return data
    return dict(app_version=APP_VERSION,source_commit='fuentes; sin identificación de paquete')


def worker_command():
    if getattr(sys,'frozen',False):
        executable=Path(sys.executable).resolve().with_name('MotorSimWorker.exe')
        if not executable.is_file():
            raise FileNotFoundError(f'Falta el auxiliar de cálculo: {executable}. Extraé la carpeta completa del ZIP.')
        return str(executable),[],str(executable.parent)
    executable=Path(sys.executable).resolve()
    if executable.name.lower()=='pythonw.exe':executable=executable.with_name('python.exe')
    return str(executable),['-u','-m','motorsim.reference_run'],str(Path(__file__).resolve().parent.parent)


def diagnostic(message):
    """Archivo exclusivo; nunca borra errores anteriores ni datos del proyecto."""
    root=Path(os.environ.get('LOCALAPPDATA',str(Path.home()/'.local/share')))/'MotorSim'/'Diagnostico'
    root.mkdir(parents=True,exist_ok=True)
    path=root/(datetime.now().strftime('%Y%m%d-%H%M%S-')+uuid.uuid4().hex[:8]+'.txt')
    path.write_text(f'MotorSim {APP_VERSION}\n{message}\n',encoding='utf-8')
    return path


def unexpected_error(exc_type,exc,tb):
    # Importación tardía: el auxiliar no carga Qt por importar rutas/identidad.
    from PySide6.QtWidgets import QMessageBox
    text=''.join(traceback.format_exception(exc_type,exc,tb))
    try:detail=f'Diagnóstico local: {diagnostic(text)}'
    except OSError as error:detail=f'No se pudo guardar diagnóstico: {error}\n{text}'
    box=QMessageBox(QMessageBox.Icon.Critical,'MotorSim — Error inesperado',
        'La operación no pudo completarse. Revisá los datos antes de continuar.\n'+str(exc))
    box.setDetailedText(detail);box.exec()
