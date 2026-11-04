"""Common platform contract for engine-model families (Dino 2T, Dino 4T, ...).

The platform shares *interfaces*, never physical models: each family keeps
its own solver, thermodynamics and boundary laws.  A family is registered by
a lazy loader so importing the platform never imports a solver.

Contract (``ENGINE_PLATFORM_CONTRACT_V1``):
  run_operating_point(config: dict, *, out_dir=None, **options) -> dict with
    schema, model_id, status, periodicity.status, final_cycle (indicators
    with SI/bar names), conservation, evidence_level and claims
    {numerical_verification, calibration, experimental_validation,
     predictive_capability}.
The Dino 2T adapter is intentionally not registered yet: wrapping it must
not alter its frozen contracts and requires its own reviewed adapter.
"""
from __future__ import annotations

from importlib import import_module
from typing import Callable, Protocol

CONTRACT = "ENGINE_PLATFORM_CONTRACT_V1"
REQUIRED_KEYS = ("schema", "model_id", "status", "periodicity", "final_cycle", "conservation",
                 "evidence_level", "claims")
REQUIRED_CLAIMS = ("numerical_verification", "calibration", "experimental_validation", "predictive_capability")


class EngineFamily(Protocol):
    cycle: str

    def run_operating_point(self, config: dict, *, out_dir=None, **options) -> dict: ...


_REGISTRY: dict[str, Callable[[], Callable]] = {
    "4T": lambda: import_module("motorsim.dino4t.runner").run_operating_point,
}


def families() -> tuple[str, ...]:
    return tuple(sorted(_REGISTRY))


def run_operating_point(cycle: str, config: dict, **options) -> dict:
    if cycle not in _REGISTRY:
        raise KeyError(f"no engine family registered for cycle {cycle!r}; available: {families()}")
    result = _REGISTRY[cycle]()(config, **options)
    summary = result["summary"] if "summary" in result else result
    check_summary(summary)
    return summary


def check_summary(summary: dict) -> None:
    missing = [k for k in REQUIRED_KEYS if k not in summary]
    missing += [f"claims.{k}" for k in REQUIRED_CLAIMS if k not in summary.get("claims", {})]
    if missing:
        raise ValueError(f"result violates {CONTRACT}: missing {missing}")
