"""Eventos y área descubierta de una ventana rectangular de un cilindro."""

from dataclasses import dataclass
import math
from .project import Port, ProjectError, validate_number, NUMBER_LABELS
from .kinematics import piston_position


@dataclass
class PortResult:
    opening: float | None = None
    closing: float | None = None
    duration: float | None = None
    maximum: float | None = None
    areas: tuple[float, ...] = ()
    event_error: str = ""
    area_error: str = ""
    never_opens: bool = False


def uncovered_area(width, height, distance):
    """Área rectangular en mm²; distancia descubierta firmada en mm."""
    return width * max(0, min(height, distance))


def port_results(port: Port, stroke, rod, errors=None) -> PortResult:
    result = PortResult()
    errors = errors or {}
    def require(value, key):
        if errors.get(key):
            raise ProjectError(errors[key])
        if value is None:
            raise ProjectError(f"Falta: {NUMBER_LABELS[key]}.")
        validate_number(value, key)
        return float(value)
    try:
        stroke = require(stroke, "stroke_mm")
        rod = require(rod, "rod_length_mm")
        top = require(port.top_mm, "top_mm")
        # Misma validación de mecanismo, sin duplicar posición del pistón.
        piston_position(stroke, rod, 90)
        if stroke / 2 == 0:
            raise ProjectError("Carrera fuera del rango de cálculo.")
        if top >= stroke:
            result.never_opens = True
            result.duration = 0.0
        else:
            result.opening = crossing_angle(stroke, rod, top)
            result.closing = 360 - result.opening
            result.duration = result.closing - result.opening
    except (ProjectError, ValueError, OverflowError) as exc:
        result.event_error = str(exc)
        result.area_error = str(exc)
        return result
    try:
        height = require(port.height_mm, "height_mm")
        width = require(port.width_mm, "width_mm")
        uncovered = max(0, min(height, stroke - top))
        maximum = width * uncovered
        if uncovered > 0 and maximum == 0:
            raise ProjectError("Área fuera del rango de cálculo; las dimensiones se conservan.")
        areas = tuple(uncovered_area(width, height, piston_position(stroke, rod, angle) - top)
                      for angle in range(361))
        if not all(math.isfinite(area) for area in (*areas, maximum)):
            raise ProjectError("Área fuera del rango de cálculo; las dimensiones se conservan.")
        result.maximum, result.areas = maximum, areas
    except (ProjectError, ValueError, OverflowError) as exc:
        result.area_error = str(exc)
    return result


def crossing_angle(stroke, rod, distance):
    """Cruce en la rama descendente; el llamador valida 0 < distancia < S."""
    low, high = 0.0, 180.0
    for _ in range(60):
        middle = (low + high) / 2
        if piston_position(stroke, rod, middle) < distance:
            low = middle
        else:
            high = middle
    return (low + high) / 2
