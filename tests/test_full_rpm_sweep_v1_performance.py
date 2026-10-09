from dataclasses import dataclass

import pytest

from scripts.analyze_full_rpm_sweep_v1_rejections import _category
from motorsim.performance_geometry_cache_v1 import install_immutable_geometry_cache_v1


@dataclass(frozen=True)
class _GeometryRow:
    angle: float
    rpm: float


class _GeometryStub:
    reference_rpm = 4000.0

    def __init__(self):
        self.calls = 0

    def _geometry(self, angle, rpm=None):
        self.calls += 1
        return _GeometryRow(float(angle) % 360.0,
                            self.reference_rpm if rpm is None else float(rpm))


def test_geometry_cache_keys_angle_and_rpm_without_mutating_geometry():
    engine = _GeometryStub()
    cache = install_immutable_geometry_cache_v1(engine)
    first = engine._geometry(10.0, 4000.0)
    repeated_periodic_angle = engine._geometry(370.0, 4000.0)
    other_rpm = engine._geometry(10.0, 4100.0)
    assert first is repeated_periodic_angle
    assert other_rpm == _GeometryRow(10.0, 4100.0)
    assert engine.calls == 2
    assert cache.receipt() == {"hits": 1, "misses": 2, "entries": 2}
    cache.restore()
    assert engine._geometry(10.0, 4000.0) == first
    assert engine.calls == 3


@pytest.mark.parametrize(
    "reason,expected",
    [("CFL limit exceeded: 0.41 > 0.4", "CFL_LIMIT"),
     ("inadmissible species mass", "SPECIES_MASS_ADMISSIBILITY"),
     ("rho/p/Y inadmissible", "DENSITY_PRESSURE_SPECIES_ADMISSIBILITY"),
     ("unknown solver rejection", "OTHER")],
)
def test_rejection_cause_categories_are_causal(reason, expected):
    assert _category(reason) == expected
