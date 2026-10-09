"""Opt-in memoization for immutable IntegratedEngine2T geometry.

This decorator is separate from the hash-bound solver implementation. It may
only be enabled by a future, versioned runner that records the producer hash.
"""
from __future__ import annotations

from typing import Any


class ImmutableGeometryCacheV1:
    def __init__(self, engine: Any):
        original = getattr(engine, "_geometry", None)
        if not callable(original):
            raise TypeError("engine must expose callable _geometry(angle, rpm=None)")
        if not hasattr(engine, "reference_rpm"):
            raise TypeError("engine must expose reference_rpm")
        self.engine = engine
        self._original = original
        self._cache: dict[tuple[float, float], Any] = {}
        self.hits = 0
        self.misses = 0

        def cached(angle: float, rpm: float | None = None):
            resolved_rpm = (float(engine.reference_rpm) if rpm is None
                            else float(rpm))
            key = (float(angle) % 360.0, resolved_rpm)
            if key not in self._cache:
                value = original(angle, rpm)
                if not getattr(type(value), "__dataclass_params__", None) or not \
                        type(value).__dataclass_params__.frozen:
                    raise TypeError("geometry result must be an immutable frozen dataclass")
                self._cache[key] = value
                self.misses += 1
            else:
                self.hits += 1
            return self._cache[key]

        self._cached_method = cached
        engine._geometry = cached

    def receipt(self) -> dict[str, int]:
        return {"hits": self.hits, "misses": self.misses,
                "entries": len(self._cache)}

    def clear(self) -> None:
        self._cache.clear()

    def restore(self) -> None:
        if getattr(self.engine, "_geometry", None) is not self._cached_method:
            raise RuntimeError("engine geometry method changed after cache installation")
        self.engine._geometry = self._original


def install_immutable_geometry_cache_v1(engine: Any) -> ImmutableGeometryCacheV1:
    return ImmutableGeometryCacheV1(engine)
