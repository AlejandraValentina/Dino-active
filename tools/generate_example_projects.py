"""Regenera solo los cuatro proyectos sintéticos versionados, sin solver."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from motorsim.examples import PROJECT_FILES, example_file_project
from motorsim.project import ProjectError
from motorsim.project_case import execution_errors
from motorsim.storage import save_project


def generate():
    projects = {filename: example_file_project(key) for key, filename in PROJECT_FILES.items()}
    # Validar todos antes de reemplazar el primero.
    for project in projects.values():
        project.validate()
        errors = execution_errors(project)
        if errors:
            raise ProjectError('\n'.join(errors))
    directory = ROOT / 'examples' / 'projects'
    directory.mkdir(parents=True, exist_ok=True)
    for filename, project in projects.items():
        save_project(directory / filename, project)
        print(directory / filename)


if __name__ == '__main__':
    generate()
