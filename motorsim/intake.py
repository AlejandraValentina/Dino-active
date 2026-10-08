"""Admisión rectangular al cárter controlada por una falda recta."""
from decimal import Decimal, localcontext
import math

from .kinematics import piston_position
from .ports import PortResult, crossing_angle, uncovered_area
from .project import NUMBER_LABELS, ProjectError, validate_number


def intake_results(intake, stroke, rod, errors=None):
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
        if intake.mode != 'piston_port':
            raise ProjectError('Admisión sin definir.')
        stroke = require(stroke, 'stroke_mm')
        rod = require(rod, 'rod_length_mm')
        top = require(intake.top_mm, 'top_mm')
        height = require(intake.height_mm, 'height_mm')
        skirt = require(intake.skirt_mm, 'skirt_mm')
        piston_position(stroke, rod, 90)
        if stroke / 2 == 0:
            raise ProjectError('Carrera fuera del rango de cálculo.')
        if top < stroke:
            raise ProjectError('Fuera del modelo: u debe ser mayor o igual que la carrera.')
        # Evita desbordar u+h y perder h por cancelación cuando u=f.
        with localcontext() as context:
            context.prec = 1100
            distance = Decimal.from_float(top) + Decimal.from_float(height) - Decimal.from_float(skirt)
        if distance >= Decimal.from_float(stroke):
            raise ProjectError('Fuera del modelo: no existe un intervalo de cierre alrededor de PMI (d >= S).')
        d = float(distance)
        if not math.isfinite(d) or (distance > 0 and d == 0):
            raise ProjectError('Distancia de apertura fuera del rango de cálculo.')
        if d <= 0:
            result.never_opens = True
            result.duration = 0.0
        else:
            beta = crossing_angle(stroke, rod, d)
            result.opening, result.closing, result.duration = 360 - beta, beta, 2 * beta
    except (ProjectError, ValueError, OverflowError) as exc:
        result.event_error = result.area_error = str(exc)
        return result
    try:
        width = require(intake.width_mm, 'width_mm')
        uncovered = max(0, min(height, d))
        maximum = width * uncovered
        if uncovered > 0 and maximum == 0:
            raise ProjectError('Área fuera del rango de cálculo; las dimensiones se conservan.')
        areas = tuple(uncovered_area(width, height, d - piston_position(stroke, rod, angle))
                      for angle in range(361))
        if not all(math.isfinite(value) for value in (*areas, maximum)):
            raise ProjectError('Área fuera del rango de cálculo; las dimensiones se conservan.')
        result.maximum, result.areas = maximum, areas
    except (ProjectError, ValueError, OverflowError) as exc:
        result.area_error = str(exc)
    return result
