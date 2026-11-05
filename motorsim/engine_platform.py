"""Cycle-aware application boundary for Dino Desktop.

This module shares project metadata and dispatch only. Native configuration,
execution results, convergence and claims remain owned by each engine family.
The 4T adapter depends exclusively on ``DINO4T_API_V1``; 2T Desktop retains its
existing engineering workflow and frozen result contracts.
"""
from __future__ import annotations

from importlib import import_module
from typing import Callable, Protocol

CONTRACT = "DINO_ENGINE_PLATFORM_ADAPTER_V1"
FOUR_STROKE_CONFIG = "DINO4T_ENGINE_CONFIG_V1"


class EngineFamily(Protocol):
    cycle: str

    def run_operating_point(self, config: dict, *, out_dir=None, **options) -> dict: ...


_REGISTRY: dict[str, Callable[[], object]] = {
    "4T": lambda: import_module("motorsim.dino4t.api"),
}


def families() -> tuple[str, ...]:
    return tuple(sorted(_REGISTRY))


def run_operating_point(cycle: str, config: dict, **options) -> dict:
    """Compatibility call returning the native summary when one exists.

    New Desktop code should use :func:`run_api` so structured errors and the
    opaque continuation state are retained.
    """
    result = run_api(cycle, config, **options)
    return result.get("summary") if result.get("summary") is not None else result


def run_api(cycle: str, config: dict, **options) -> dict:
    """Return the engine family's native API envelope without normalization."""
    if cycle not in _REGISTRY:
        raise KeyError(f"no engine family registered for cycle {cycle!r}; available: {families()}")
    if cycle == "4T":
        api = _REGISTRY[cycle]()
        return api.run(config, **options)
    raise NotImplementedError("2T Desktop execution remains on its versioned engineering workflow")


def validate_config(cycle: str, config: dict) -> dict:
    """Validate native configuration through the owning engine contract."""
    if cycle == "4T":
        return _REGISTRY[cycle]().validate(config)
    if cycle == "2T":
        from .engine_configuration import validate
        try:
            validate(config)
            return {"valid": True, "issues": [], "unknown_keys": [],
                    "config_sha256": identity(cycle, config)}
        except (TypeError, ValueError, KeyError) as exc:
            return {"valid": False, "issues": [{"code": "CONFIG_INVALID", "message": str(exc)}],
                    "unknown_keys": [], "config_sha256": None}
    raise ValueError(f"unsupported engine family {cycle!r}")


def identity(cycle: str, config: dict) -> str:
    if cycle == "4T":
        checked = _REGISTRY[cycle]().validate(config)
        if not checked["valid"]:
            raise ValueError(f"invalid 4T engine configuration: {checked['issues']}")
        return checked["config_sha256"]
    if cycle == "2T":
        from .engine_configuration import identity as two_stroke_identity
        return two_stroke_identity(config)
    raise ValueError(f"unsupported engine family {cycle!r}")


def indicator_unit(cycle: str, key: str) -> str | None:
    if cycle == "4T":
        return _REGISTRY[cycle]().indicator_unit(key)
    return None


def cycle_of(config: dict) -> str:
    schema = config.get("schema") if isinstance(config, dict) else None
    if schema == FOUR_STROKE_CONFIG:
        return "4T"
    if schema == "MOTORSIM_ENGINE_CONFIGURATION_V1":
        return "2T"
    raise ValueError(f"unsupported engine configuration schema {schema!r}")


def check_result(cycle: str, result: dict) -> None:
    """Check the native result against its family-specific public API."""
    if cycle == "4T":
        api = _REGISTRY[cycle]()
        if "summary" in result and "api" in result:
            summary = result.get("summary")
            if summary is not None and api.check_summary(summary):
                raise ValueError(f"{api.API_VERSION} result invalid: {api.check_summary(summary)}")
            if result.get("api") != api.API_VERSION:
                raise ValueError("4T result does not declare DINO4T_API_V1")
        else:
            problems = api.check_summary(result)
            if problems:
                raise ValueError(f"{api.RESULT_SCHEMA} invalid: {problems}")
        return
    raise NotImplementedError("2T result validation remains owned by its engineering workflow")


def check_summary(summary: dict) -> None:
    """Backward-compatible family-native summary check."""
    check_result("4T", summary)
