"""Distribución idealizada 720°; eventos analíticos, dimensiones en mm."""
import math
from .project import VALVE_FIELDS, ProjectError


def errors(valve):
    try:
        valve.validate()
    except ProjectError as exc:
        return [str(exc)]
    if any(getattr(valve, key) is None for key in VALVE_FIELDS):
        return ['Faltan datos de válvula.']
    if not 0 <= valve.stem_mm < valve.throat_mm <= valve.seat_mm:
        return ['Se requiere 0 ≤ s < d ≤ D.']
    try:
        area = math.pi * (valve.throat_mm**2-valve.stem_mm**2)/4
        curtain = math.pi * valve.seat_mm * valve.lift_mm
        if not math.isfinite(area) or not math.isfinite(curtain):
            return ['Área fuera del rango calculable.']
    except OverflowError:
        return ['Área fuera del rango calculable.']
    return []


def lift(valve, angle):
    phase = (angle-valve.opening_deg) % 720
    # Reconocer el evento analítico incluso tras sumar/restar vueltas en float.
    # Solo resolución de máquina, nunca redondeo a la malla de representación.
    tolerance = 8*max(math.ulp(angle), math.ulp(valve.opening_deg), math.ulp(valve.duration_deg))
    if min(phase, 720-phase) <= tolerance or abs(phase-valve.duration_deg) <= tolerance:
        return 0.
    return (valve.lift_mm * math.sin(math.pi*phase/valve.duration_deg)**2
            if 0 < phase < valve.duration_deg else 0.)


def area_at_lift(valve, height):
    return min(math.pi*valve.seat_mm*height,
               math.pi*(valve.throat_mm**2-valve.stem_mm**2)/4)


def area(valve, angle):
    return area_at_lift(valve, lift(valve, angle))


def intervals(valve):
    a, b = valve.opening_deg, valve.opening_deg+valve.duration_deg
    return [(a, b)] if b <= 720 else [(0., b-720), (a, 720.)]


def overlap(intake, exhaust):
    return sorted((max(a, c), min(b, d)) for a, b in intervals(intake)
                  for c, d in intervals(exhaust) if max(a, c) < min(b, d))


def closed_during_heat(valve):
    return not any(max(a, 350) < min(b, 390) for a, b in intervals(valve))
