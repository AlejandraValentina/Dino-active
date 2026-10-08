"""Geometría de piezas circulares de diámetro lineal, sin cálculo de flujo."""
from dataclasses import dataclass, field
from decimal import Decimal, localcontext
import math

from .project import DUCT_FIELDS, ProjectError, validate_number


@dataclass
class SegmentGeometry:
    start_area: Decimal | None = None
    end_area: Decimal | None = None
    volume: Decimal | None = None
    kind: str = 'Sin determinar'
    errors: dict = field(default_factory=dict)


@dataclass
class RouteGeometry:
    segments: tuple[SegmentGeometry, ...] = ()
    length: Decimal | None = None
    volume: Decimal | None = None
    # (x inicial, x final, radio inicial, radio final), una pieza por entrada.
    profile: tuple = ()
    # Unión i enlaza tramos i e i+1: True, False o None si faltan datos válidos.
    joints: tuple = ()
    errors: dict = field(default_factory=dict)


def route_geometry(segments, draft_errors=None):
    result = RouteGeometry()
    if not segments:
        result.errors = dict(length='Sin tramos', volume='Sin tramos', profile='Sin tramos')
        return result
    draft_errors = draft_errors or [{} for _ in segments]
    dimensions, pieces = [], []
    with localcontext() as context:
        context.prec = 50
        pi = Decimal(str(math.pi))
        for index, segment in enumerate(segments):
            values, errors = {}, {}
            for key in DUCT_FIELDS:
                try:
                    if draft_errors[index].get(key):
                        raise ProjectError(draft_errors[index][key])
                    value = getattr(segment, key)
                    if value is None:
                        raise ProjectError(f'Falta: {DUCT_FIELDS[key]}.')
                    validate_number(value, key)
                    values[key] = Decimal(str(value))
                except ProjectError as exc:
                    values[key] = None
                    errors[key] = f'Tramo {index+1}: {exc}'
            length, d1, d2 = (values[key] for key in DUCT_FIELDS)
            piece = SegmentGeometry()
            if d1 is not None:
                piece.start_area = pi*d1*d1/4
            else:
                piece.errors['start_area'] = errors['start_diameter_mm']
            if d2 is not None:
                piece.end_area = pi*d2*d2/4
            else:
                piece.errors['end_area'] = errors['end_diameter_mm']
            if d1 is not None and d2 is not None:
                piece.kind = 'Tubo cilíndrico' if d1 == d2 else ('Troncocónico · expansión' if d2 > d1 else 'Troncocónico · contracción')
            if all(v is not None for v in (length, d1, d2)):
                piece.volume = pi*length*(d1*d1+d1*d2+d2*d2)/12000
            else:
                piece.errors['volume'] = next(iter(errors.values()))
            dimensions.append((length, d1, d2))
            pieces.append(piece)
            for key, message in errors.items():
                result.errors.setdefault('profile', message)
                result.errors.setdefault('volume', message)
                if key == 'length_mm': result.errors.setdefault('length', message)
        result.segments = tuple(pieces)
        if 'length' not in result.errors:
            result.length = sum((d[0] for d in dimensions), Decimal(0))
        if 'volume' not in result.errors:
            result.volume = sum((p.volume for p in pieces), Decimal(0))
        result.joints = tuple(None if left[2] is None or right[1] is None else left[2] == right[1]
                              for left, right in zip(dimensions, dimensions[1:]))
        if 'profile' not in result.errors:
            x, profile = Decimal(0), []
            for length, d1, d2 in dimensions:
                end = x + length
                if end == x:
                    result.errors['profile'] = 'Perfil fuera del rango de representación; dimensiones conservadas.'
                    break
                profile.append((x, end, d1/2, d2/2))
                x = end
            else:
                result.profile = tuple(profile)
    return result


def format_geometry(value):
    if value is None:
        return '—'
    return f'{value:.2f}' if value == 0 or Decimal('.01') <= abs(value) < Decimal('1e6') else f'{value:.3e}'
