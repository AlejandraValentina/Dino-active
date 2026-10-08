"""Geometría directa de un cilindro; sin integración temporal ni persistencia."""

from dataclasses import dataclass, field
import math

from .project import NUMERIC_FIELDS, ProjectError, displacements, validate_number


def piston_position(stroke: float, rod: float, angle: float) -> float:
    """Distancia desde PMS en mm. Ángulo horario en grados; L > S/2."""
    if not all(math.isfinite(v) for v in (stroke, rod, angle)) or stroke <= 0 or rod <= stroke / 2:
        raise ValueError("El mecanismo requiere carrera positiva y biela > carrera / 2.")
    phase = angle % 360
    if phase == 0:
        return 0.0
    if phase == 180:
        return stroke
    theta = math.radians(phase)
    radius = stroke / 2
    ratio = radius / rod
    sine = math.sin(theta)
    root = math.sqrt(max(0.0, 1 - (ratio * sine) ** 2))
    # Forma racionalizada: evita restar dos longitudes de biela casi iguales.
    return radius * (1 - math.cos(theta)) + radius * ratio * sine**2 / (1 + root)


@dataclass
class Geometry:
    end_angle: int
    angles: tuple[int, ...] = ()
    positions: tuple[float, ...] = ()
    volumes: tuple[float, ...] = ()
    stroke: float | None = None
    rod: float | None = None
    displacement: float | None = None
    chamber: float | None = None
    maximum: float | None = None
    errors: dict[str, str] = field(default_factory=dict)


def calculate_geometry(values: dict, cycle: str, input_errors: dict | None = None) -> Geometry:
    """Resultados independientes; los errores de edición nunca se vuelven datos."""
    result = Geometry(720 if cycle == "4T" else 360)
    result.angles = tuple(range(result.end_angle + 1))
    errors = input_errors or {}

    def require(*fields):
        numbers = []
        for name in fields:
            if errors.get(name):
                raise ValueError(errors[name])
            value = values.get(name)
            if value is None:
                raise ValueError(f"Falta: {NUMERIC_FIELDS[name]}.")
            validate_number(value, name)
            number = float(value)
            if not math.isfinite(number):
                raise ValueError("Datos fuera del rango de cálculo geométrico.")
            numbers.append(number)
        return numbers

    try:
        stroke, rod = require("stroke_mm", "rod_length_mm")
        if rod <= stroke / 2:
            raise ValueError("Biela incompatible: debe superar la mitad de la carrera (L > S/2).")
        if stroke / 2 == 0:
            raise ValueError("Carrera fuera del rango de cálculo geométrico.")
        positions = tuple(piston_position(stroke, rod, angle) for angle in result.angles)
        if not all(math.isfinite(x) for x in positions):
            raise ValueError("Posición fuera del rango de cálculo geométrico.")
        result.stroke, result.rod, result.positions = stroke, rod, positions
    except (ProjectError, ValueError, OverflowError) as exc:
        result.errors["position"] = str(exc)

    try:
        bore, stroke = require("bore_mm", "stroke_mm")
        displacement = float(displacements(bore, stroke, None)[0])
        if not math.isfinite(displacement) or displacement <= 0:
            raise ValueError("Cilindrada fuera del rango de cálculo geométrico.")
        result.displacement = displacement
    except (ProjectError, ValueError, OverflowError) as exc:
        result.errors["displacement"] = str(exc)

    try:
        if result.displacement is None:
            raise ValueError(result.errors["displacement"])
        compression, = require("compression_ratio")
        chamber = result.displacement / (compression - 1)
        maximum = chamber + result.displacement
        if not all(math.isfinite(v) and v > 0 for v in (chamber, maximum)):
            raise ValueError("Volumen fuera del rango de cálculo geométrico.")
        result.chamber, result.maximum = chamber, maximum
    except (ProjectError, ValueError, OverflowError) as exc:
        result.errors["chamber"] = str(exc)

    if result.positions and result.chamber is not None:
        # x/S evita elevar D al cuadrado en float; Vd ya fue calculada de forma segura.
        result.volumes = tuple(result.chamber + result.displacement * (x / result.stroke)
                               for x in result.positions)
        if not all(math.isfinite(v) for v in result.volumes):
            result.volumes = ()
            result.errors["volume"] = "Volumen fuera del rango de cálculo geométrico."
    else:
        result.errors["volume"] = result.errors.get("chamber", result.errors.get("position", ""))
    return result
