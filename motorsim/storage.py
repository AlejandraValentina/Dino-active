"""Lectura validada y reemplazo de archivos solo tras completar la escritura."""

import json
import os
import tempfile
from pathlib import Path

from .project import Project, ProjectError


def load_project(path: Path) -> Project:
    try:
        with Path(path).open("r", encoding="utf-8") as stream:
            data = json.load(stream)
    except (OSError, UnicodeError, ValueError, RecursionError) as exc:
        raise ProjectError(f"No se pudo leer el proyecto «{path}»: {exc}") from exc
    return Project.from_dict(data)


def save_project(path: Path, project: Project) -> None:
    data = project.to_dict()
    destination = Path(path)
    temporary = None
    try:
        # El temporal está en el mismo volumen. En Windows debe cerrarse antes
        # de os.replace; nunca se trunca el destino para escribir sobre él.
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=destination.parent,
            prefix=".motorsim-", suffix=".tmp", delete=False,
        ) as stream:
            temporary = Path(stream.name)
            json.dump(data, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, destination)
    except (OSError, UnicodeError) as exc:
        raise ProjectError(f"No se pudo guardar el proyecto «{path}»: {exc}") from exc
    finally:
        if temporary is not None:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                # Un fallo de limpieza no debe ocultar el error de escritura.
                pass
