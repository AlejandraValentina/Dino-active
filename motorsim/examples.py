"""Proyectos editables sintéticos derivados de las referencias canónicas."""
from dataclasses import replace

from .simulation_case import geometry as geometry2
from .four_stroke import geometry as geometry4

NOTICE = 'EJEMPLO SINTÉTICO — NO MEDIDO'
EXAMPLES = {
    '2t-reference': ('2T referencia', 'EJEMPLO_SINTETICO_2T.json'),
    '2t-compression': ('2T compresión 8.2', 'EJEMPLO_SINTETICO_2T_COMPRESION_8_2.json'),
    '4t-reference': ('4T referencia', 'EJEMPLO_SINTETICO_4T.json'),
    '4t-compression': ('4T compresión 8.2', 'EJEMPLO_SINTETICO_4T_COMPRESION_8_2.json'),
}


def example_project(key):
    title, _ = EXAMPLES[key]
    project = (geometry2 if key.startswith('2t-') else geometry4)()
    return replace(project, name=f'{NOTICE} · {title.upper()}',
        notes=f'{NOTICE}. Sin calibración ni validación experimental.',
        compression_ratio=8.2 if key.endswith('-compression') else project.compression_ratio)


# Archivos de demostración: una variante difiere en un único valor, incluso
# al comparar el JSON completo. La identificación del menú previo se conserva.
PROJECT_FILES = {key: filename.replace(f'_{key[:2].upper()}.json',
    f'_{key[:2].upper()}_REFERENCIA.json') for key, (_, filename) in EXAMPLES.items()}


def example_file_project(key):
    project = example_project(key)
    return replace(project, name=f'EJEMPLO SINTÉTICO {project.cycle} — REFERENCIA',
        notes='EJEMPLO SINTÉTICO — NO MEDIDO.\n'
              'Caso de demostración de MotorSim. No representa validación experimental.')
