"""Editable, versioned configurations for the supported integrated 2T engine.

This is a data/validation adapter. Constructing it never advances the solver.
Native physics remains owned by :mod:`motorsim.integrated_2t`.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import math
from typing import Any

from .integrated_2t import IntegratedEngine2T
from .mechanical import MechanicalLossModel

SCHEMA = "MOTORSIM_ENGINE_CONFIGURATION_V1"
_FIELDS = {"schema", "display_name", "provenance", "native_configuration",
           "native_configuration_sha256", "mechanical_loss_model",
           "operating_conditions", "units", "validation_state"}
UNITS = {"length": "SI; native geometry fields ending _mm are millimetres",
         "pressure": "Pa", "temperature": "K", "volume": "m^3",
         "mass": "kg", "time": "s", "angle": "degree unless field is explicitly radians",
         "speed": "rpm", "energy": "J", "power": "W", "torque": "N*m",
         "species_mass": "kg", "afr": "kg_air/kg_fuel", "load": "dimensionless"}


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False)


def sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _finite_tree(value: Any, path: str = "configuration") -> None:
    if isinstance(value, bool):
        return
    if isinstance(value, (float, int)):
        if not math.isfinite(float(value)):
            raise ValueError(f"{path} must be finite")
    elif isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValueError(f"{path} has a non-string key")
            _finite_tree(item, f"{path}.{key}")
    elif isinstance(value, (list, tuple)):
        for i, item in enumerate(value):
            _finite_tree(item, f"{path}[{i}]")


def validate_native(native: dict[str, Any]) -> IntegratedEngine2T:
    if not isinstance(native, dict):
        raise ValueError("native_configuration must be an object")
    _finite_tree(native)
    # The native constructor is the authoritative supported-capability and
    # geometry/topology validator. No solver integration occurs here.
    return IntegratedEngine2T.from_configuration_dict(deepcopy(native))


def _validate_operating_conditions(value: dict[str, Any]) -> None:
    if not isinstance(value, dict) or set(value) != {"reference_rpm", "load", "fuel_id", "afr"}:
        raise ValueError("operating_conditions schema must declare reference_rpm, load, fuel_id, afr")
    _finite_tree(value, "operating_conditions")
    rpm, load, afr = (value[k] for k in ("reference_rpm", "load", "afr"))
    if type(rpm) not in (int, float) or rpm <= 0:
        raise ValueError("operating_conditions.reference_rpm must be positive RPM")
    if type(load) not in (int, float) or load < 0:
        raise ValueError("operating_conditions.load must be a nonnegative dimensionless load")
    if type(afr) not in (int, float) or afr <= 0:
        raise ValueError("operating_conditions.afr must be positive kg_air/kg_fuel")
    if not isinstance(value["fuel_id"], str) or not value["fuel_id"].strip():
        raise ValueError("operating_conditions.fuel_id is required")


def create(*, native_configuration: dict[str, Any],
           mechanical_loss_model: dict[str, Any],
           operating_conditions: dict[str, Any],
           provenance: dict[str, Any], display_name: str = "Engine") -> dict[str, Any]:
    native = deepcopy(native_configuration)
    engine = validate_native(native)
    loss = MechanicalLossModel.from_dict(deepcopy(mechanical_loss_model))
    _validate_operating_conditions(operating_conditions)
    if not isinstance(provenance, dict) or not provenance:
        raise ValueError("provenance must be an explicit nonempty object")
    if "configuration_source" not in provenance or "fuel" not in provenance:
        raise ValueError("provenance must explicitly identify configuration_source and fuel")
    if not isinstance(provenance["configuration_source"], (str, dict)) or not isinstance(provenance["fuel"], dict):
        raise ValueError("configuration_source/fuel provenance types are invalid")
    if not provenance["fuel"].get("provenance"):
        raise ValueError("fuel provenance classification is required")
    _finite_tree(provenance, "provenance")
    doc = {"schema": SCHEMA, "display_name": str(display_name),
           "provenance": deepcopy(provenance), "native_configuration": native,
           "native_configuration_sha256": sha256(native),
           "mechanical_loss_model": loss.to_dict(),
           "operating_conditions": deepcopy(operating_conditions),
           "units": dict(UNITS),
           "validation_state": "VALIDATED_NO_SOLVER_STEPS"}
    validate(doc)
    return doc


def validate(document: dict[str, Any]) -> IntegratedEngine2T:
    if not isinstance(document, dict) or set(document) != _FIELDS or document.get("schema") != SCHEMA:
        raise ValueError("engine configuration schema/fields are invalid")
    if not isinstance(document["display_name"], str) or not isinstance(document["provenance"], dict):
        raise ValueError("display_name/provenance types are invalid")
    if document["units"] != UNITS:
        raise ValueError("unit declaration is missing or incompatible with the native adapter")
    _finite_tree(document)
    native = document["native_configuration"]
    if sha256(native) != document["native_configuration_sha256"]:
        raise ValueError("native configuration identity hash mismatch")
    engine = validate_native(native)
    MechanicalLossModel.from_dict(document["mechanical_loss_model"])
    _validate_operating_conditions(document["operating_conditions"])
    if document["validation_state"] != "VALIDATED_NO_SOLVER_STEPS":
        raise ValueError("unsupported validation_state")
    return engine


def identity(document: dict[str, Any]) -> str:
    validate(document)
    # Human-facing name is intentionally excluded from semantic identity.
    semantic = {k: v for k, v in document.items() if k != "display_name"}
    return sha256(semantic)


def to_solver_configuration(document: dict[str, Any]) -> dict[str, Any]:
    validate(document)
    return deepcopy(document["native_configuration"])
