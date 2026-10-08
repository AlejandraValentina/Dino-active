"""P5-A isolated intake/transfer duct foundation.

The module composes the existing mesh and Riemann coupling primitives.  It
does not run an engine campaign or add a second 1D solver.
"""
from dataclasses import dataclass
from math import isfinite, pi
from .gas1d.mesh import segments_mesh
from .coupling import interface_flux


def _positive(value, name):
    if not isinstance(value, (int, float)) or not isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be positive and finite")
    return float(value)


@dataclass(frozen=True)
class DuctGeometry:
    name: str
    segments: tuple
    direction: str

    def __post_init__(self):
        if self.direction not in ("external_to_crankcase", "crankcase_to_cylinder"):
            raise ValueError("unsupported duct direction")
        if not self.segments:
            raise ValueError("a duct needs at least one segment")

    def mesh(self, dx_target):
        segments = [dict(length=s.length_mm, start_diameter=s.start_diameter_mm,
                          end_diameter=s.end_diameter_mm) for s in self.segments]
        return segments_mesh(segments, _positive(dx_target, "dx_target"))


@dataclass(frozen=True)
class PortInterface:
    width_mm: float
    height_mm: float
    top_mm: float
    offset_mm: float = 0.0

    def __post_init__(self):
        for n in ("width_mm", "height_mm"):
            _positive(getattr(self, n), n)
        if not isinstance(self.top_mm, (int, float)) or not isfinite(self.top_mm) or self.top_mm < 0:
            raise ValueError("top_mm must be finite and nonnegative")

    def transfer_area(self, x_mm):
        return self.width_mm * max(0.0, min(self.height_mm, x_mm - self.offset_mm))

    def intake_area(self, x_mm, skirt_mm):
        d = self.offset_mm + self.height_mm - _positive(skirt_mm, "skirt_mm")
        return self.width_mm * max(0.0, min(self.height_mm, d - x_mm))

    def area_m2(self, area_mm2):
        return max(0.0, float(area_mm2)) * 1e-6


@dataclass(frozen=True)
class NetworkState:
    intake: DuctGeometry | None = None
    transfers: tuple = ()

    def __post_init__(self):
        if any(not isinstance(x, DuctGeometry) for x in self.transfers):
            raise ValueError("transfers must be DuctGeometry instances")


def interface_exchange(chamber, interior, area_m2, normal, *, eos=None):
    """Return the existing bidirectional Riemann exchange.

    A zero area is a closed port and produces an exact zero flux without a
    one-way valve or direction clamp.
    """
    area = float(area_m2)
    if not isfinite(area) or area < 0 or normal not in (-1, 1):
        raise ValueError("invalid port interface")
    if area == 0:
        return {"outward": (0.0, 0.0, 0.0, 0.0), "closed": True, "normal": normal}
    result = interface_flux(chamber, interior, area, normal, eos=eos)
    return {"outward": result.outward, "closed": False, "normal": normal,
            "wave_speeds": result.wave_speeds, "fallback_reason": result.fallback_reason}


def validate_state(state, *, eos):
    """Validate rho/u/p/Y tuples without clipping or converting failures."""
    eos.validate(state)
    return True


def volume_of_segment(length_mm, start_diameter_mm, end_diameter_mm):
    length = _positive(length_mm, "length_mm") * 1e-3
    d0 = _positive(start_diameter_mm, "start_diameter_mm") * 1e-3
    d1 = _positive(end_diameter_mm, "end_diameter_mm") * 1e-3
    return pi * length * (d0*d0 + d0*d1 + d1*d1) / 12.0
